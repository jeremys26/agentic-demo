import os

from http_client import service_client
from registry import RestCall, register

CAPTIVATOR360_URL = os.environ.get("CAPTIVATOR360_URL", "http://captivator360:8000")


@register(
    "get_creative_performance",
    service="captivator360",
    rest=[
        RestCall("GET", "/api/creatives/", query_from={"campaign_id": "campaign_id"}),
        RestCall(
            "GET",
            "/api/creatives/{creative_id}/performance/",
            when="per_creative",
            notes="One request per creative returned by the list call.",
        ),
    ],
)
async def get_creative_performance(campaign_id: int) -> dict:
    """
    Get every creative asset for a campaign along with its daily performance
    history and a summary (latest CTR, first-week vs last-week CTR, decline %) —
    this is what reveals a creative going stale (PLANNING.md §9).
    """
    async with service_client() as client:
        list_response = await client.get(
            f"{CAPTIVATOR360_URL}/api/creatives/", params={"campaign_id": campaign_id}, timeout=10.0
        )
        list_response.raise_for_status()
        creatives = list_response.json()

        details = []
        for creative in creatives:
            detail_response = await client.get(
                f"{CAPTIVATOR360_URL}/api/creatives/{creative['id']}/performance/", timeout=10.0
            )
            detail_response.raise_for_status()
            details.append(detail_response.json())

        return {"campaign_id": campaign_id, "creatives": details}


@register(
    "get_declining_creatives",
    service="captivator360",
    rest=[
        RestCall(
            "GET",
            "/api/creatives/declining/",
            query_from={"campaign_id": "campaign_id", "decline_threshold_pct": "threshold"},
        )
    ],
)
async def get_declining_creatives(campaign_id: int, decline_threshold_pct: float = 20.0) -> dict:
    """
    Get creatives whose click-through rate has fallen at least
    `decline_threshold_pct` (default 20) below their own first-week average.
    CTR decline = (baseline CTR − recent CTR) / baseline CTR. Proxies
    Captivator360-sim's /api/creatives/declining/ endpoint.
    """
    async with service_client() as client:
        response = await client.get(
            f"{CAPTIVATOR360_URL}/api/creatives/declining/",
            params={"campaign_id": campaign_id, "threshold": decline_threshold_pct},
            timeout=10.0,
        )
        response.raise_for_status()
        return {
            "campaign_id": campaign_id,
            "decline_threshold_pct": decline_threshold_pct,
            "creatives": response.json(),
        }


@register(
    "request_creative_refresh",
    service="captivator360",
    kind="write",
    rest=[
        RestCall(
            "GET",
            "/api/creatives/{creative_id}/performance/",
            notes="Guardrail loads the creative to score it and attach campaign_id.",
        ),
        RestCall(
            "POST",
            "/api/creatives/{creative_id}/refresh-request/",
            body_from=("reason",),
            when="on_execute",
            notes="Only after auto-execute or human approval.",
        ),
        RestCall(
            "POST",
            "/api/creatives/refresh-requests/{refresh_request_id}/resolve/",
            when="on_execute",
            notes="Guardrail immediately sends {status: approved} after create when execution is allowed.",
        ),
    ],
)
async def request_creative_refresh(creative_id: int, reason: str) -> dict:
    """
    Request a creative refresh for an underperforming asset (typically one
    whose CTR has dropped well below its own baseline).
    WRITE TOOL — routed through the risk-scoring guardrail (PLANNING.md §7)
    before anything is created: auto-executed, queued for human approval, or
    blocked outright depending on the computed risk score. Returns
    {"status": "auto_executed" | "pending_approval" | "blocked" | "error", ...}
    — a pending_approval result is NOT a completed action; nothing changes
    until a human approves it in React-Admin.
    """
    from guardrails.engine import guard_request_creative_refresh

    return await guard_request_creative_refresh(creative_id, reason)
