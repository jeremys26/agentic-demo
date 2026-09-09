"""
One GraphQL join query across the four sim platforms (PLANNING.md §11 / §14
phase 12). Lives on the MCP server — the only component that already talks
to all four — and fans out to their REST APIs. Not a parallel full GraphQL
API; one investigation-shaped query is the point.
"""

from __future__ import annotations

import os

import strawberry
from strawberry.fastapi import GraphQLRouter

from http_client import service_client
from tools.onesource360 import DEFAULT_ANOMALY_THRESHOLD_PCT

ONESOURCE360_URL = os.environ.get("ONESOURCE360_URL", "http://onesource360:8000")
SMARTSPOT360_URL = os.environ.get("SMARTSPOT360_URL", "http://smartspot360:8000")
CAPTIVATOR360_URL = os.environ.get("CAPTIVATOR360_URL", "http://captivator360:8000")
MAESTRO360_URL = os.environ.get("MAESTRO360_URL", "http://maestro360:8000")


@strawberry.type
class PoolShare:
    pool_name: str
    is_certified_medicare: bool
    pct_of_total: float
    conversion_rate: float


@strawberry.type
class CampaignInvestigation:
    campaign_id: int
    name: str
    vertical: str
    channel: str
    target_cpl: float
    window_cpl: float | None
    cpl_variance_pct: float | None
    flagged: bool
    spot_count: int
    latest_ctr_decline_pct: float | None
    declining_variant_labels: list[str]
    uncertified_pool_pct: float | None
    pool_distribution: list[PoolShare]


def _windowed_cpl(rollups: list[dict], target_cpl: float, window_days: int = 7) -> tuple[float | None, float | None]:
    window = rollups[-window_days:]
    if not window:
        return None, None
    spend = sum(float(r["spend"]) for r in window)
    leads = sum(r["leads"] for r in window)
    if leads == 0:
        return None, None
    window_cpl = round(spend / leads, 2)
    variance = round((window_cpl - target_cpl) / target_cpl * 100, 1)
    return window_cpl, variance


async def fetch_campaign_investigation(campaign_id: int) -> CampaignInvestigation:
    async with service_client() as client:
        campaign_resp = await client.get(f"{ONESOURCE360_URL}/api/campaigns/{campaign_id}/")
        campaign_resp.raise_for_status()
        campaign = campaign_resp.json()

        perf_resp = await client.get(
            f"{ONESOURCE360_URL}/api/performance/", params={"campaign_id": campaign_id}
        )
        perf_resp.raise_for_status()
        rollups = perf_resp.json().get("daily_rollups") or []
        target = float(campaign["target_cpl"])
        window_cpl, variance = _windowed_cpl(rollups, target)

        spots_resp = await client.get(
            f"{SMARTSPOT360_URL}/api/spots/", params={"campaign_id": campaign_id}
        )
        spots_resp.raise_for_status()
        spots = spots_resp.json()

        creatives_resp = await client.get(
            f"{CAPTIVATOR360_URL}/api/creatives/", params={"campaign_id": campaign_id}
        )
        creatives_resp.raise_for_status()
        declining: list[str] = []
        latest_decline = None
        for creative in creatives_resp.json():
            detail_resp = await client.get(
                f"{CAPTIVATOR360_URL}/api/creatives/{creative['id']}/performance/"
            )
            detail_resp.raise_for_status()
            summary = detail_resp.json().get("summary") or {}
            decline = summary.get("ctr_decline_pct")
            if decline is not None:
                decline_f = float(decline)
                latest_decline = decline_f if latest_decline is None else max(latest_decline, decline_f)
                if summary.get("declining"):
                    declining.append(creative["variant_label"])

        calls_resp = await client.get(
            f"{MAESTRO360_URL}/api/calls/summary/", params={"campaign_id": campaign_id}
        )
        calls_resp.raise_for_status()
        distribution = calls_resp.json().get("pool_distribution") or []
        pools = [
            PoolShare(
                pool_name=row["pool_name"],
                is_certified_medicare=row["is_certified_medicare"],
                pct_of_total=float(row["pct_of_total"]),
                conversion_rate=float(row["conversion_rate"]),
            )
            for row in distribution
        ]
        uncertified = next((p for p in pools if not p.is_certified_medicare), None)

    return CampaignInvestigation(
        campaign_id=campaign["id"],
        name=campaign["name"],
        vertical=campaign["vertical"],
        channel=campaign["channel"],
        target_cpl=target,
        window_cpl=window_cpl,
        cpl_variance_pct=variance,
        flagged=variance is not None and variance > DEFAULT_ANOMALY_THRESHOLD_PCT,
        spot_count=len(spots),
        latest_ctr_decline_pct=latest_decline,
        declining_variant_labels=declining,
        uncertified_pool_pct=uncertified.pct_of_total if uncertified else None,
        pool_distribution=pools,
    )


@strawberry.type
class Query:
    @strawberry.field
    async def campaign_investigation(self, campaign_id: int) -> CampaignInvestigation:
        """Join OneSource + SmartSpot + Captivator + Maestro for one campaign."""
        return await fetch_campaign_investigation(campaign_id)


schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema)
