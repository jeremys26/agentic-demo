"""
The adapter for RankPulse-sim (services/rankpulse_sim) — a stand-in for a
newly-acquired SEO analytics platform, per PLANNING.md §14 phase 10's "live
fifth-platform onboarding demo." Fully built and registered via @register,
same as every other tool module, but deliberately NOT imported in main.py
by default — see the commented-out import there. Uncommenting that one
line and rebuilding/restarting the mcp_server container is the entire
onboarding step: no changes to the MCP server's core code, no changes to
this file, which is the point being dramatized (PLANNING.md §2's structural
acquisition-integration problem).
"""

import os

from http_client import service_client
from registry import RestCall, register

RANKPULSE_URL = os.environ.get("RANKPULSE_URL", "http://rankpulse:8000")


@register(
    "get_organic_performance",
    service="rankpulse",
    rest=[
        RestCall("GET", "/api/organic-performance/", query_from={"campaign_id": "campaign_id"})
    ],
)
async def get_organic_performance(campaign_id: int) -> dict:
    """
    Get weekly organic search sessions, conversions, and average keyword
    rank for a campaign from RankPulse-sim.

    This is a read tool: it proxies directly to RankPulse-sim's REST API and
    doesn't touch anything (PLANNING.md §7 — only write tools go through the
    risk-scoring guardrail).
    """
    async with service_client() as client:
        response = await client.get(
            f"{RANKPULSE_URL}/api/organic-performance/",
            params={"campaign_id": campaign_id},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()
