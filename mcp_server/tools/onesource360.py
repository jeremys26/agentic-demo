import asyncio
import os

from http_client import service_client
from registry import RestCall, register

ONESOURCE360_URL = os.environ.get("ONESOURCE360_URL", "http://onesource360:8000")

# Shared with graphql_api.py's campaign_investigation query, so the REST/MCP
# anomaly check and the GraphQL "flagged" field can't silently drift apart.
DEFAULT_ANOMALY_THRESHOLD_PCT = 15.0


@register(
    "get_campaign_performance",
    service="onesource360",
    rest=[
        RestCall(
            "GET",
            "/api/performance/",
            query_from={"campaign_id": "campaign_id", "start_date": "start", "end_date": "end"},
        )
    ],
)
async def get_campaign_performance(campaign_id: int, start_date: str = "", end_date: str = "") -> dict:
    """
    Get daily spend/leads/CPL performance for a campaign, plus a summary
    comparing actual CPL against the campaign's target CPL. start_date and
    end_date are optional (YYYY-MM-DD); omit both to get the full history.

    This is a read tool: it proxies directly to OneSource360-sim's REST API
    and doesn't touch anything (PLANNING.md §7 — only write tools go through
    the risk-scoring guardrail).
    """
    params: dict = {"campaign_id": campaign_id}
    if start_date:
        params["start"] = start_date
    if end_date:
        params["end"] = end_date

    async with service_client() as client:
        response = await client.get(
            f"{ONESOURCE360_URL}/api/performance/",
            params=params,
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


@register(
    "list_campaigns",
    service="onesource360",
    rest=[
        RestCall(
            "GET",
            "/api/campaigns/",
            notes="MCP filters vertical/channel/status in Python after this unfiltered list returns.",
        )
    ],
)
async def list_campaigns(vertical: str = "", channel: str = "", status: str = "") -> dict:
    """
    List campaigns, optionally filtered by vertical, channel, and/or status
    (each an empty string means "no filter"). Filtering happens here rather
    than server-side since OneSource360-sim's /api/campaigns/ endpoint is a
    plain read-only viewset with no query-param filtering backend.
    """
    async with service_client() as client:
        response = await client.get(f"{ONESOURCE360_URL}/api/campaigns/", timeout=10.0)
        response.raise_for_status()
        campaigns = response.json()

    if vertical:
        campaigns = [c for c in campaigns if c["vertical"] == vertical]
    if channel:
        campaigns = [c for c in campaigns if c["channel"] == channel]
    if status:
        campaigns = [c for c in campaigns if c["status"] == status]

    return {"count": len(campaigns), "campaigns": campaigns}


@register(
    "get_performance_anomalies",
    service="onesource360",
    rest=[
        RestCall("GET", "/api/campaigns/", notes="Then keep only status=active."),
        RestCall(
            "GET",
            "/api/performance/",
            query_from={"campaign_id": "campaign_id"},
            when="per_active_campaign",
            notes="One request per active campaign; trailing-window CPL is computed in the tool.",
        ),
    ],
)
async def get_performance_anomalies(
    threshold_pct: float = DEFAULT_ANOMALY_THRESHOLD_PCT, window_days: int = 7
) -> dict:
    """
    Flag campaigns whose most recent `window_days` of performance have a
    blended CPL (total spend / total leads over that window) more than
    `threshold_pct` percent above target_cpl. This is the plain-SQL-style
    threshold check from PLANNING.md §9 — checking a trailing window rather
    than lifetime average matters, since a short spike gets diluted into
    noise if averaged across a campaign's whole history. The Celery anomaly
    sweep (§8) calls this same function on a timer rather than wrapping it as
    an agent tool call, so scheduled monitoring and live investigation share
    one detection path.
    """
    async with service_client() as client:
        campaigns_response = await client.get(f"{ONESOURCE360_URL}/api/campaigns/", timeout=10.0)
        campaigns_response.raise_for_status()
        campaigns = [c for c in campaigns_response.json() if c["status"] == "active"]

        async def check(campaign: dict) -> dict | None:
            perf_response = await client.get(
                f"{ONESOURCE360_URL}/api/performance/",
                params={"campaign_id": campaign["id"]},
                timeout=10.0,
            )
            perf_response.raise_for_status()
            data = perf_response.json()
            rollups = data["daily_rollups"][-window_days:]
            if not rollups:
                return None

            total_spend = sum(float(r["spend"]) for r in rollups)
            total_leads = sum(r["leads"] for r in rollups)
            target_cpl = float(campaign["target_cpl"])
            if total_leads == 0 or target_cpl <= 0:
                return None

            windowed_cpl = round(total_spend / total_leads, 2)
            variance_pct = round((windowed_cpl - target_cpl) / target_cpl * 100, 1)

            # Only flag CPL *above* target (PLANNING.md §9). Beating target
            # is not an anomaly — the frontend uses the same one-sided check.
            if variance_pct <= threshold_pct:
                return None
            return {
                "campaign_id": campaign["id"],
                "campaign_name": campaign["name"],
                "vertical": campaign["vertical"],
                "window_days": len(rollups),
                "window_cpl": windowed_cpl,
                "target_cpl": target_cpl,
                "variance_pct": variance_pct,
            }

        # return_exceptions=True so one campaign's bad data (or a transient
        # per-request failure) can't take down the whole scan — this same
        # function backs the Celery anomaly sweep, which would otherwise stop
        # monitoring every campaign because of one.
        results = await asyncio.gather(*[check(c) for c in campaigns], return_exceptions=True)
        anomalies = [row for row in results if row is not None and not isinstance(row, BaseException)]
        return {"threshold_pct": threshold_pct, "window_days": window_days, "anomalies": anomalies}
