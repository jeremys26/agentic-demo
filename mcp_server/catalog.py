"""Platform catalog for the Systems inspector UI (and /catalog).

Static per-service copy (what the sim is, which Postgres tables, which REST
paths) plus the live tool registry (source code, REST mapping). The frontend
joins this with each service's /api/inspect/ snapshot so a demo can point at
the exact table, endpoint, and MCP handler a tool call used.
"""

from __future__ import annotations

import inspect
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select

from guardrails.db import SessionLocal
from guardrails.models import AgentToolCall, ExecutedAction, FlaggedCampaign, ProposedAction
from guardrails.scoring import compute_score
from guardrails import policy
from registry import all_tools, source_file_for, tool_schema

# Public URLs are what the browser (and this catalog) should show. Internal
# bases are what the MCP container actually calls on the Docker network.
PLATFORMS = [
    {
        "slug": "onesource360",
        "name": "OneSource360",
        "kind": "django",
        "role": "Unified performance warehouse",
        "color": "#0A21C7",
        "database": "onesource360",
        "internal_base": "http://onesource360:8000",
        "inspect_path": "/api/inspect/",
        "docs_path": "/api/docs/",
        "purpose": (
            "The campaign scoreboard. OneSource360 is where spend, leads, calls, "
            "conversions, and cost-per-lead live as daily rollups. A CPL spike "
            "shows up here first; this service cannot explain *why* — that "
            "requires the other three platforms."
        ),
        "expected_data": (
            "6 campaigns across Medicare Advantage, insurance, and home services. "
            "28 days of daily rollups (2026-08-01 through 2026-08-28). Campaign 1 "
            "(Medicare Advantage – Southeast TV, target CPL $45) is seeded with a "
            "week-4 spike: spend stays ~$50k/week while leads drop, so trailing-7-day "
            "CPL lands around $68 (+51%)."
        ),
        "tables": [
            {
                "db_table": "campaigns_campaign",
                "model": "Campaign",
                "purpose": "A named advertising effort (product + region + channel) plus a target cost-per-lead. The id is the join key every other service stores as a plain integer.",
            },
            {
                "db_table": "campaigns_dailyperformancerollup",
                "model": "DailyPerformanceRollup",
                "purpose": "That campaign's scoreboard for one day: spend, leads, calls, conversions, CPL = spend ÷ leads. Unique on (campaign, date).",
            },
        ],
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/campaigns/",
                "auth": "AllowAny",
                "purpose": "List every campaign. Backs list_campaigns (MCP filters vertical/channel/status after this returns).",
            },
            {
                "method": "GET",
                "path": "/api/campaigns/{id}/",
                "auth": "AllowAny",
                "purpose": "Retrieve one campaign.",
            },
            {
                "method": "GET",
                "path": "/api/performance/?campaign_id=&start=&end=",
                "auth": "AllowAny",
                "purpose": "Daily rollups plus a blended-CPL summary vs. target. This is what get_campaign_performance and get_performance_anomalies call.",
            },
            {
                "method": "POST",
                "path": "/api/webhooks/daily-performance/",
                "auth": "JWT or X-Service-Token",
                "purpose": "Ingest a new day's warehouse drop. Used by Simulate Next Day, not by agent tools.",
            },
            {
                "method": "POST",
                "path": "/api/token/",
                "auth": "demo / demo",
                "purpose": "Issue a JWT for write calls. The local console does not log in; MCP uses X-Service-Token instead.",
            },
        ],
        "operational_path": "/campaigns",
        "operational_label": "Campaigns explorer",
    },
    {
        "slug": "smartspot360",
        "name": "SmartSpot360",
        "kind": "django",
        "role": "TV / radio media buying",
        "color": "#9A6700",
        "database": "smartspot360",
        "internal_base": "http://smartspot360:8000",
        "inspect_path": "/api/inspect/",
        "docs_path": "/api/docs/",
        "purpose": (
            "Which stations and dayparts a campaign's TV/radio budget actually "
            "bought, and a deterministic recommender that re-allocates budget "
            "toward lower historical CPL. In the demo scenario this system did "
            "*not* change — useful negative evidence."
        ),
        "expected_data": (
            "Stations (e.g. WSVN Miami) and dayparts (Daytime, Prime, with cost "
            "multipliers). Spots for all 6 campaigns across the 28-day window. "
            "Campaign 1's station/daypart mix is identical in weeks 1–4 — the "
            "media buy did not cause the CPL spike. BudgetRecommendation rows "
            "appear only after get_budget_recommendation is called."
        ),
        "tables": [
            {
                "db_table": "spots_station",
                "model": "Station",
                "purpose": "A TV or radio channel in a market (WSVN Miami).",
            },
            {
                "db_table": "spots_daypart",
                "model": "Daypart",
                "purpose": "A time-of-day window. Prime costs more than Daytime (cost_multiplier).",
            },
            {
                "db_table": "spots_spot",
                "model": "Spot",
                "purpose": "One paid airing: campaign_id (plain integer, not a FK), station, daypart, date, cost. campaign_id points at OneSource360's Campaign.id over HTTP, not a database join.",
            },
            {
                "db_table": "spots_spotperformance",
                "model": "SpotPerformance",
                "purpose": "Calls, conversions, and CPL for that one airing.",
            },
            {
                "db_table": "spots_budgetrecommendation",
                "model": "BudgetRecommendation",
                "purpose": "A proposed split of a budget across station/daypart combos. applied=true only after the MCP guardrail auto-executes or a human approves.",
            },
        ],
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/spots/?campaign_id=",
                "auth": "AllowAny",
                "purpose": "List spots, optionally for one campaign. First hop of get_spot_performance.",
            },
            {
                "method": "GET",
                "path": "/api/spots/{id}/performance/",
                "auth": "AllowAny",
                "purpose": "One spot plus its performance. get_spot_performance calls this once per spot.",
            },
            {
                "method": "POST",
                "path": "/api/recommendations/",
                "auth": "JWT or X-Service-Token",
                "purpose": "Create a deterministic allocation. Body: {campaign_id, budget_amount}. Backs get_budget_recommendation.",
            },
            {
                "method": "GET",
                "path": "/api/recommendations/{id}/",
                "auth": "AllowAny",
                "purpose": "Read a stored recommendation. The guardrail loads this before scoring reallocate_budget.",
            },
            {
                "method": "POST",
                "path": "/api/recommendations/{id}/apply/",
                "auth": "JWT or X-Service-Token",
                "purpose": "Mark a recommendation applied. The execution step of reallocate_budget — only after auto-execute or human approval.",
            },
            {
                "method": "POST",
                "path": "/api/webhooks/spot-performance/",
                "auth": "JWT or X-Service-Token",
                "purpose": "Ingest a new day's spots. Used by Simulate Next Day.",
            },
        ],
        "operational_path": "/spots",
        "operational_label": "Spots explorer",
    },
    {
        "slug": "captivator360",
        "name": "Captivator360",
        "kind": "django",
        "role": "Creative performance",
        "color": "#166534",
        "database": "captivator360",
        "internal_base": "http://captivator360:8000",
        "inspect_path": "/api/inspect/",
        "docs_path": "/api/docs/",
        "purpose": (
            "Ad versions and how they perform over time. CTR vs this creative's "
            "own first-week baseline is what reveals a creative going stale — "
            "half of campaign 1's compound-cause spike."
        ),
        "expected_data": (
            "Creative assets per campaign (campaign 1's CR-114 is the headline). "
            "28 days of CreativePerformanceDaily. CR-114's first-week CTR is ~2.0% "
            "and last-week CTR is ~1.5% (about 25% below its own baseline, past the "
            "20% refresh trigger; latest day ~1.2%). CreativeRefreshRequest rows "
            "appear only after request_creative_refresh clears the guardrail."
        ),
        "tables": [
            {
                "db_table": "creatives_creativeasset",
                "model": "CreativeAsset",
                "purpose": "One ad version (CR-114) belonging to a campaign_id in OneSource360.",
            },
            {
                "db_table": "creatives_creativeperformancedaily",
                "model": "CreativePerformanceDaily",
                "purpose": "That ad's daily impressions, CTR, and conversion rate. Unique on (creative, date). CTR decline is computed from this table, not stored.",
            },
            {
                "db_table": "creatives_creativerefreshrequest",
                "model": "CreativeRefreshRequest",
                "purpose": "A request to replace a stale ad. This service only stores pending/approved/rejected; the MCP guardrail decides whether the request is allowed to be created.",
            },
        ],
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/creatives/?campaign_id=",
                "auth": "AllowAny",
                "purpose": "List creatives for a campaign. First hop of get_creative_performance.",
            },
            {
                "method": "GET",
                "path": "/api/creatives/{id}/performance/",
                "auth": "AllowAny",
                "purpose": "Daily history plus first-week vs last-week CTR and decline %. Also used by the guardrail to score a refresh.",
            },
            {
                "method": "GET",
                "path": "/api/creatives/declining/?campaign_id=&threshold=",
                "auth": "AllowAny",
                "purpose": "Creatives whose CTR has dropped at least threshold % (default 20) vs their own first-week average. Backs get_declining_creatives.",
            },
            {
                "method": "POST",
                "path": "/api/creatives/{id}/refresh-request/",
                "auth": "JWT or X-Service-Token",
                "purpose": "Create a pending refresh. Body: {reason}. Execution step of request_creative_refresh.",
            },
            {
                "method": "POST",
                "path": "/api/creatives/refresh-requests/{id}/resolve/",
                "auth": "JWT or X-Service-Token",
                "purpose": "Approve or reject a pending refresh. Body: {status}. The guardrail sends status=approved immediately after create when execution is allowed.",
            },
            {
                "method": "POST",
                "path": "/api/webhooks/creative-metrics/",
                "auth": "JWT or X-Service-Token",
                "purpose": "Ingest a new day's creative metrics. Used by Simulate Next Day.",
            },
        ],
        "operational_path": "/creatives",
        "operational_label": "Creatives explorer",
    },
    {
        "slug": "maestro360",
        "name": "Maestro360",
        "kind": "django",
        "role": "Real-time call routing",
        "color": "#6E11B0",
        "database": "maestro360",
        "internal_base": "http://maestro360:8000",
        "inspect_path": "/api/inspect/",
        "docs_path": "/api/docs/",
        "purpose": (
            "Which call-center team handled each inbound call, and whether that "
            "team is Medicare-certified. The other half of campaign 1's spike: "
            "volume quietly shifting from certified Pool A into uncertified, "
            "lower-converting Pool B."
        ),
        "expected_data": (
            "A handful of ClientAgentPool rows (Pool A ~31% conversion, Medicare-"
            "certified; Pool B ~18%, not certified) and priority RoutingRules. "
            "Several thousand CallEvent rows across 6 campaigns × 28 days. For "
            "campaign 1, Pool A handles ~90% of calls in weeks 1–3, then ~65% in "
            "week 4 as overflow hits Pool B."
        ),
        "tables": [
            {
                "db_table": "calls_clientagentpool",
                "model": "ClientAgentPool",
                "purpose": "A call-center team: vertical specialty, historical conversion rate, Medicare certification flag.",
            },
            {
                "db_table": "calls_routingrule",
                "model": "RoutingRule",
                "purpose": "Priority order for sending calls to a pool.",
            },
            {
                "db_table": "calls_callevent",
                "model": "CallEvent",
                "purpose": "One inbound phone call: timestamp, which pool got it, wait/duration, outcome. campaign_id is a plain integer pointing at OneSource360.",
            },
        ],
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/calls/?campaign_id=&start=&end=",
                "auth": "AllowAny",
                "purpose": "Raw call events for a campaign. Backs get_call_quality. Can return thousands of rows.",
            },
            {
                "method": "GET",
                "path": "/api/calls/summary/?campaign_id=",
                "auth": "AllowAny",
                "purpose": "Outcome breakdown and per-pool distribution including certification. Backs get_routing_summary — this is the headline routing-shift view.",
            },
            {
                "method": "GET",
                "path": "/api/routing-rules/",
                "auth": "AllowAny",
                "purpose": "List routing rules (priority + pool).",
            },
            {
                "method": "POST",
                "path": "/api/webhooks/call-events/",
                "auth": "JWT or X-Service-Token",
                "purpose": "Ingest a new day's calls. Used by Simulate Next Day.",
            },
        ],
        "operational_path": "/call_routing",
        "operational_label": "Call Routing explorer",
    },
    {
        "slug": "rankpulse",
        "name": "RankPulse",
        "kind": "fastapi",
        "role": "SEO analytics (fifth-platform onboarding demo)",
        "color": "#5B6270",
        "database": None,
        "internal_base": "http://rankpulse:8000",
        "inspect_path": "/api/inspect/",
        "docs_path": "/docs",
        "purpose": (
            "A stand-in for a newly acquired SEO analytics platform. It runs the "
            "whole time but is deliberately left *unregistered* in the MCP tool "
            "list until one import line is uncommented — that's the live "
            "onboarding flourish."
        ),
        "expected_data": (
            "No Postgres. Four weeks of in-memory organic sessions / conversions / "
            "keyword rank per campaign id 1–6. No anomaly is baked in; this "
            "platform exists to demonstrate onboarding, not to add a second "
            "root-cause."
        ),
        "tables": [
            {
                "db_table": "(in-memory — RankPulse-sim has no Postgres)",
                "model": "OrganicPerformanceWeekly",
                "purpose": "Weekly organic search sessions, conversions, and average keyword rank, generated deterministically per campaign_id.",
            }
        ],
        "endpoints": [
            {
                "method": "GET",
                "path": "/api/organic-performance/?campaign_id=",
                "auth": "AllowAny",
                "purpose": "Weekly organic performance. Backs get_organic_performance once the tool is registered.",
            }
        ],
        "operational_path": None,
        "operational_label": None,
    },
    {
        "slug": "agent360",
        "name": "Agent360 Gateway",
        "kind": "fastapi",
        "role": "Governed MCP gateway",
        "color": "#0D2BFF",
        "database": "mcp_server",
        "internal_base": "http://mcp_server:8100",
        "inspect_path": "/inspect",
        "docs_path": "/tools",
        "purpose": (
            "The only component that talks to all four (or five) platforms. "
            "Agents never call the sim APIs directly — they call MCP tools here. "
            "This process logs every call, scores every write, and owns the "
            "approval queue. Governance lives here so it does not matter which "
            "LLM client is asking."
        ),
        "expected_data": (
            "Empty audit tables after mcp_server boot (startup wipe + sweep). As an "
            "investigation runs: AgentToolCall grows with every read and write; "
            "ProposedAction rows appear for mid-risk writes; ExecutedAction rows "
            "appear for anything that actually ran, with a pre-action snapshot; "
            "FlaggedCampaign is written by the Celery sweep, not by the agent."
        ),
        "tables": [
            {
                "db_table": "agent_tool_calls",
                "model": "AgentToolCall",
                "purpose": "Every MCP tool call, read or write, with arguments, outcome, optional risk score, and a summarized result.",
            },
            {
                "db_table": "proposed_actions",
                "model": "ProposedAction",
                "purpose": "A write scored into the human-approval tier. Approve/reject is plain REST, never an MCP tool.",
            },
            {
                "db_table": "executed_actions",
                "model": "ExecutedAction",
                "purpose": "A write that actually ran (auto or after approval), including the pre-action audit snapshot.",
            },
            {
                "db_table": "flagged_campaigns",
                "model": "FlaggedCampaign",
                "purpose": "The Celery anomaly sweep's own audit log. Same detection function the agent uses, triggered by a timer.",
            },
        ],
        "endpoints": [
            {
                "method": "GET",
                "path": "/mcp",
                "auth": "MCP Streamable HTTP",
                "purpose": "The MCP protocol endpoint Claude Code and Cursor call. Not a REST JSON API.",
            },
            {
                "method": "GET",
                "path": "/tools",
                "auth": "AllowAny",
                "purpose": "Plain-REST tool registry (name, kind, parameters, REST mapping, source).",
            },
            {
                "method": "GET",
                "path": "/catalog",
                "auth": "AllowAny",
                "purpose": "This catalog — platforms, endpoints, tools, guardrail source.",
            },
            {
                "method": "GET",
                "path": "/inspect",
                "auth": "AllowAny",
                "purpose": "Live snapshot of the gateway's own Postgres tables.",
            },
            {
                "method": "GET",
                "path": "/agent-actions",
                "auth": "AllowAny",
                "purpose": "Every write-tool call across all risk tiers. Backs the Agent Actions resource.",
            },
            {
                "method": "POST",
                "path": "/agent-actions/{id}/approve",
                "auth": "AllowAny (local demo)",
                "purpose": "Human approval. Deliberately not an MCP tool.",
            },
            {
                "method": "POST",
                "path": "/agent-actions/{id}/reject",
                "auth": "AllowAny (local demo)",
                "purpose": "Human rejection. Deliberately not an MCP tool.",
            },
            {
                "method": "GET",
                "path": "/tool-calls",
                "auth": "AllowAny",
                "purpose": "Full MCP trace, reads and writes.",
            },
            {
                "method": "GET",
                "path": "/flagged-campaigns",
                "auth": "AllowAny",
                "purpose": "Celery sweep audit log.",
            },
            {
                "method": "POST",
                "path": "/flagged-campaigns/sweep",
                "auth": "AllowAny (local demo)",
                "purpose": "Run the anomaly sweep now.",
            },
            {
                "method": "POST",
                "path": "/simulate-next-day",
                "auth": "AllowAny (local demo)",
                "purpose": "Post a new day to each service's webhook, then re-sweep.",
            },
            {
                "method": "POST",
                "path": "/graphql",
                "auth": "AllowAny",
                "purpose": "One investigation-shaped join query across the four platforms.",
            },
        ],
        "operational_path": "/tool_calls",
        "operational_label": "Tool Calls trace",
    },
]


def _source_of(func) -> str:
    try:
        return inspect.getsource(func)
    except (OSError, TypeError):
        return ""


def build_catalog() -> dict:
    tools = [tool_schema(spec) for spec in all_tools()]
    registered_services = {spec.service for spec in all_tools()}
    platforms = []
    for platform in PLATFORMS:
        entry = dict(platform)
        # RankPulse uses service="rankpulse"; agent360 owns no MCP tools of its own.
        if platform["slug"] == "agent360":
            entry["tools"] = []
        else:
            entry["tools"] = [tool["name"] for tool in tools if tool["service"] == platform["slug"]]
        entry["registered"] = platform["slug"] in registered_services or platform["slug"] == "agent360"
        platforms.append(entry)

    return {
        "platforms": platforms,
        "tools": tools,
        "guardrail": {
            "scoring_file": source_file_for(compute_score),
            "scoring_source": _source_of(compute_score),
            "policy_file": source_file_for(policy.route),
            "policy_source": _source_of(policy.route),
            "auto_execute_threshold": policy.AUTO_EXECUTE_THRESHOLD,
            "block_threshold": policy.BLOCK_THRESHOLD,
            "reallocate_hard_cap_pct": policy.REALLOCATE_BUDGET_HARD_CAP_PCT,
        },
    }


def _jsonable(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return value
    return str(value)


def _sqlalchemy_payload(model, rows, total, offset, limit):
    columns = [
        {
            "name": column.key,
            "type": type(column.type).__name__,
            "nullable": column.nullable,
            "primary_key": column.primary_key,
        }
        for column in model.__table__.columns
    ]
    return {
        "model": model.__name__,
        "db_table": model.__tablename__,
        "app_label": "mcp_server",
        "columns": columns,
        "total": total,
        "offset": offset,
        "limit": limit,
        "rows": [
            {column.key: _jsonable(getattr(row, column.key)) for column in model.__table__.columns}
            for row in rows
        ],
    }


async def inspect_gateway_tables(table: str | None = None, limit: int = 50, offset: int = 0) -> dict:
    """Live snapshot of the MCP server's own Postgres tables."""
    specs = [
        AgentToolCall,
        ProposedAction,
        ExecutedAction,
        FlaggedCampaign,
    ]
    if table:
        specs = [model for model in specs if model.__tablename__ == table or model.__name__ == table]
        if not specs:
            return {"error": f"unknown table {table}"}

    tables = []
    async with SessionLocal() as session:
        for model in specs:
            total = await session.scalar(select(func.count()).select_from(model))
            result = await session.execute(
                select(model).order_by(model.id.desc()).offset(offset).limit(limit)
            )
            rows = list(result.scalars())
            tables.append(_sqlalchemy_payload(model, rows, int(total or 0), offset, limit))

    return {"database": "mcp_server", "tables": tables}
