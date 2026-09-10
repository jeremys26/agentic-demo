from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mcp.server import MCPServer

import registry
import tools.captivator360  # noqa: F401 — imported for its @register side effects
import tools.maestro360  # noqa: F401
import tools.onesource360  # noqa: F401
import tools.smartspot360  # noqa: F401

# import tools.rankpulse  # noqa: F401 — PLANNING.md §14 phase 10's live fifth-
# platform onboarding demo. RankPulse-sim (services/rankpulse_sim) is a stand-in
# for a newly-acquired platform: it's already running (docker-compose.yml) and
# fully built (tools/rankpulse.py), just not yet wired into the agent's toolset.
# To onboard it live: uncomment this one line, then
# `docker compose up -d --build mcp_server` — get_organic_performance appears
# in /tools and the MCP tool list immediately. No other code changes needed.
from catalog import build_catalog, inspect_gateway_tables
from guardrails.db import init_db, reset_audit_tables
from guardrails.engine import (
    get_all_agent_actions,
    get_all_flagged_campaigns,
    get_all_tool_calls,
    get_pending_actions,
    resolve_proposed_action,
    run_anomaly_sweep,
    wrap_read_tool,
)
from graphql_api import graphql_app
from simulator import run_simulate_next_day

mcp = MCPServer("agent360")

# Config-driven tool registry (PLANNING.md §7): every tool module registers
# its handlers via @register(...) as a side effect of being imported above;
# this loop is the one place that wires each handler into both the MCP
# server and the /tools introspection endpoint, so the two can't drift
# apart. Read tools get wrapped for uniform AgentToolCall logging; write
# tools (reallocate_budget, request_creative_refresh) already do their own
# logging inside the risk-scoring guardrail (guardrails/engine.py), since
# they need to log the computed risk score alongside the outcome.
for _spec in registry.all_tools():
    handler = wrap_read_tool(_spec.func) if _spec.kind == "read" else _spec.func
    mcp.tool(name=_spec.name)(handler)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await init_db()
    # Match the four sims' reseed-on-start: wipe prior demo runs so Agent
    # Actions / Tool Calls aren't littered with yesterday's test traffic.
    # The startup sweep below then re-flags campaign 1 immediately.
    await reset_audit_tables()
    try:
        # Run once at boot so the Flagged Campaigns log has real data
        # immediately, rather than waiting for Celery beat's first tick
        # (celery_app.py's ANOMALY_SWEEP_INTERVAL_SECONDS) — the periodic
        # sweep then keeps it current the same way a live data feed would.
        await run_anomaly_sweep()
    except Exception as exc:
        print(f"[startup] initial anomaly sweep failed, Celery beat will retry: {exc}")
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Agent360 MCP Server", lifespan=lifespan)

# Local-demo CORS: wide open, same posture as the four sim services'
# django-cors-headers config (PLANNING.md §10). Writes to the Django sims
# still require JWT or X-Service-Token; the console itself does not log in.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graphql_app, prefix="/graphql")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tools")
def list_tools():
    """
    Plain-REST introspection of the tool registry, distinct from the MCP
    protocol's own tools/list (which an MCP client like Claude Code uses
    directly) — this is for anyone browsing the registry without speaking
    MCP, e.g. the React-Admin frontend or a reviewer's browser (PLANNING.md
    §7).
    """
    return {"tools": [registry.tool_schema(spec) for spec in registry.all_tools()]}


@app.get("/catalog")
def catalog():
    """
    Systems inspector payload: each simulated platform (purpose, expected
    data, Postgres tables, REST endpoints) plus every registered MCP tool
    with its backing HTTP calls and handler source. The frontend joins this
    with each service's /api/inspect/ snapshot.
    """
    return build_catalog()


@app.get("/inspect")
async def inspect_tables(table: str | None = None, limit: int = 50, offset: int = 0):
    """Live snapshot of the MCP server's own Postgres tables."""
    payload = await inspect_gateway_tables(table=table, limit=min(max(limit, 1), 200), offset=max(offset, 0))
    if "error" in payload:
        raise HTTPException(status_code=404, detail=payload["error"])
    return payload


@app.get("/agent-actions")
async def agent_actions():
    """
    Every write-tool call ever logged, across all three risk tiers — the
    Agent Actions resource React-Admin's frontend (PLANNING.md §10) reads
    from directly.
    """
    return {"data": await get_all_agent_actions()}


@app.get("/tool-calls")
async def tool_calls():
    """
    Every tool call ever logged, reads and writes alike — the full MCP
    trace. Distinct from /agent-actions, which only surfaces the write
    tier's risk-scored decisions; this is what lets a viewer watch the
    agent's actual MCP traffic (and which sim service each call reached)
    as it happens.
    """
    return {"data": await get_all_tool_calls()}


@app.get("/flagged-campaigns")
async def flagged_campaigns():
    """
    The Celery anomaly sweep's own audit log (PLANNING.md §8) — every
    anomaly the automated, LLM-free sweep has ever detected and persisted,
    most recent first. Distinct from the frontend's own live client-side
    variance recompute on every page load (dataProvider.js), which is
    immediate but not itself a persisted record that a sweep actually ran.
    """
    return {"data": await get_all_flagged_campaigns()}


@app.post("/flagged-campaigns/sweep")
async def trigger_sweep():
    """
    Manually runs the same sweep Celery beat fires on a timer — lets a demo
    show the automated-detection story on demand instead of waiting for the
    next scheduled tick.
    """
    return await run_anomaly_sweep()


@app.post("/simulate-next-day")
async def simulate_next_day():
    """
    Posts a new day of performance, spots, creative metrics, and call events
    to each sim service's own webhook (PLANNING.md §9), then re-runs the
    anomaly sweep so the Overview log stays current.
    """
    return await run_simulate_next_day()


@app.get("/agent-actions/pending")
async def pending_actions():
    """
    Every write action currently sitting in the human-approval tier —
    what React-Admin's Agent Actions view (PLANNING.md §10) filters to for
    the Overview "Needs Your Attention" panel.
    """
    return {"pending": await get_pending_actions()}


@app.post("/agent-actions/{proposed_action_id}/approve")
async def approve_action(proposed_action_id: int):
    """
    A human approving a queued ProposedAction (PLANNING.md §7/§10) — this is
    plain REST, deliberately NOT an MCP tool, since an agent must never be
    able to approve its own proposed action. Triggers the real write call.
    """
    result = await resolve_proposed_action(proposed_action_id, approve=True)
    return result


@app.post("/agent-actions/{proposed_action_id}/reject")
async def reject_action(proposed_action_id: int):
    """A human rejecting a queued ProposedAction — plain REST, same reasoning
    as approve_action above."""
    result = await resolve_proposed_action(proposed_action_id, approve=False)
    return result


# Mounted last and at root so the REST routes registered above
# (/health, /tools, /catalog, /inspect, /agent-actions, /tool-calls,
# /flagged-campaigns, /simulate-next-day, /graphql) take precedence; the
# MCP endpoint is /mcp.
app.mount("/", mcp.streamable_http_app())
