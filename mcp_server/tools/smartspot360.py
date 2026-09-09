import asyncio
import os

from http_client import service_client
from registry import RestCall, register

SMARTSPOT360_URL = os.environ.get("SMARTSPOT360_URL", "http://smartspot360:8000")


@register(
    "get_spot_performance",
    service="smartspot360",
    rest=[
        RestCall("GET", "/api/spots/", query_from={"campaign_id": "campaign_id"}),
        RestCall(
            "GET",
            "/api/spots/{spot_id}/performance/",
            when="per_spot",
            notes="One request per spot returned by the list call; results are grouped by station+daypart.",
        ),
    ],
)
async def get_spot_performance(campaign_id: int) -> dict:
    """
    Get every spot for a campaign along with its call/conversion/CPL
    performance, grouped by station+daypart so patterns are easy to spot —
    e.g. whether the media-buy mix changed recently (PLANNING.md §9's
    negative-evidence check: SmartSpot360-sim should look unremarkable when
    the real cause of a CPL spike lives elsewhere).
    """
    async with service_client() as client:
        spots_response = await client.get(
            f"{SMARTSPOT360_URL}/api/spots/", params={"campaign_id": campaign_id}, timeout=10.0
        )
        spots_response.raise_for_status()
        spots = spots_response.json()

        performances = await asyncio.gather(
            *[
                client.get(f"{SMARTSPOT360_URL}/api/spots/{spot['id']}/performance/", timeout=10.0)
                for spot in spots
            ]
        )

    groups: dict[tuple[int, int], dict] = {}
    for resp in performances:
        resp.raise_for_status()
        detail = resp.json()
        perf = detail.get("performance")
        if not perf or perf.get("cpl") is None:
            continue
        key = (detail["station"], detail["daypart"])
        group = groups.setdefault(key, {"station_id": detail["station"], "daypart_id": detail["daypart"], "cpls": []})
        group["cpls"].append(float(perf["cpl"]))

    grouped_summary = [
        {
            "station_id": g["station_id"],
            "daypart_id": g["daypart_id"],
            "sample_size": len(g["cpls"]),
            "avg_cpl": round(sum(g["cpls"]) / len(g["cpls"]), 2),
        }
        for g in groups.values()
    ]

    return {"campaign_id": campaign_id, "spot_count": len(spots), "by_station_daypart": grouped_summary}


@register(
    "get_budget_recommendation",
    service="smartspot360",
    rest=[
        RestCall(
            "POST",
            "/api/recommendations/",
            body_from=("campaign_id", "budget_amount"),
        )
    ],
)
async def get_budget_recommendation(campaign_id: int, budget_amount: float) -> dict:
    """
    Get a deterministic, weighted-scoring budget allocation recommendation
    across this campaign's historical station/daypart combos (PLANNING.md
    §6/§7) — favors combos with lower historical CPL. Returns a rationale
    written in plain business language, plus a confidence score based on how
    much historical data backs the recommendation; that confidence number
    feeds directly into reallocate_budget's risk-scoring guardrail.
    """
    async with service_client() as client:
        response = await client.post(
            f"{SMARTSPOT360_URL}/api/recommendations/",
            json={"campaign_id": campaign_id, "budget_amount": budget_amount},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


@register(
    "reallocate_budget",
    service="smartspot360",
    kind="write",
    rest=[
        RestCall(
            "GET",
            "/api/recommendations/{recommendation_id}/",
            notes="Guardrail loads the recommendation to score it before anything is applied.",
        ),
        RestCall(
            "POST",
            "/api/recommendations/{recommendation_id}/apply/",
            when="on_execute",
            notes="Only after auto-execute, or after a human clicks Approve. Blocked calls never hit this.",
        ),
    ],
)
async def reallocate_budget(campaign_id: int, recommendation_id: int) -> dict:
    """
    Apply a budget recommendation previously computed by
    get_budget_recommendation (pass its id as recommendation_id).
    WRITE TOOL — routed through the risk-scoring guardrail (PLANNING.md §7)
    before anything is applied: auto-executed, queued for human approval, or
    blocked outright depending on the computed risk score. Returns
    {"status": "auto_executed" | "pending_approval" | "blocked" | "error", ...}
    — a pending_approval result is NOT a completed action; nothing changes
    until a human approves it in React-Admin.
    """
    from guardrails.engine import guard_reallocate_budget

    return await guard_reallocate_budget(campaign_id, recommendation_id)
