import os

from http_client import service_client
from registry import RestCall, register

MAESTRO360_URL = os.environ.get("MAESTRO360_URL", "http://maestro360:8000")


@register(
    "get_call_quality",
    service="maestro360",
    rest=[
        RestCall(
            "GET",
            "/api/calls/",
            query_from={"campaign_id": "campaign_id", "start_date": "start", "end_date": "end"},
        )
    ],
)
async def get_call_quality(campaign_id: int, start_date: str = "", end_date: str = "") -> dict:
    """
    Get raw call events for a campaign, optionally within a date range —
    each event includes which pool it was routed to, wait/duration times,
    and outcome. Read tool: proxies directly to Maestro360-sim's REST API.
    """
    params: dict = {"campaign_id": campaign_id}
    if start_date:
        params["start"] = start_date
    if end_date:
        params["end"] = end_date

    async with service_client() as client:
        response = await client.get(f"{MAESTRO360_URL}/api/calls/", params=params, timeout=10.0)
        response.raise_for_status()
        return {"campaign_id": campaign_id, "calls": response.json()}


@register(
    "get_routing_summary",
    service="maestro360",
    rest=[
        RestCall("GET", "/api/calls/summary/", query_from={"campaign_id": "campaign_id"})
    ],
)
async def get_routing_summary(campaign_id: int) -> dict:
    """
    Get a campaign's outcome breakdown and per-pool call distribution,
    including each pool's Medicare-certification status — this is what
    reveals call volume quietly shifting into a lower-converting,
    non-certified pool (PLANNING.md §9's headline scenario).
    """
    async with service_client() as client:
        response = await client.get(
            f"{MAESTRO360_URL}/api/calls/summary/", params={"campaign_id": campaign_id}, timeout=10.0
        )
        response.raise_for_status()
        return response.json()
