# 05 — MCP Servers

**Status**: complete. Full tool registry (11 tools across four services by default), risk-scoring guardrail, human approval path, RankPulse onboarding demo. Celery sweep: `04`. FastAPI/SQLAlchemy substrate: `11`. Agent clients: `06`.

## What it is

**MCP (Model Context Protocol)** is an open standard for connecting LLM applications to external tools and data. An **MCP server** exposes typed **tools** (and optionally resources/prompts). An **MCP client** (Claude Code, Cursor, …) discovers those tools and calls them during an agent loop.

A tool is: a name, a description, an input schema, and code that runs when called. Agent360 uses the official Python MCP SDK and the **Streamable HTTP** transport — a long-lived, network-reachable server — because multiple clients need to share one gateway. (Stdio transport spawns a process per client; that doesn't fit a Dockerized shared service.)

This project treats the MCP server as a **governed gateway**, not a dumb proxy: every call is logged; every write is risk-scored before execution.

## Why this piece of the stack is used here

This *is* the project architecturally (`PLANNING.md` §7). No custom agent-orchestration loop was built (`PLANNING.md` §5) — Claude Code already has one. Agent360 only needs:

1. Tools that talk to the four sims over HTTP
2. Policy that decides what writes may do
3. Audit storage so humans can see and approve

Governance lives **server-side**. Swap Claude Code for Cursor; scoring and logging stay identical (`06`).

## Where it lives in this repo

```
mcp_server/
├── main.py              # FastAPI app + MCP mount + REST admin API + lifespan
├── registry.py          # @register decorator, ToolSpec, /tools schema helper
├── catalog.py           # Systems UI catalog + gateway inspect
├── http_client.py       # httpx AsyncClient + X-Service-Token
├── celery_app.py / tasks.py
├── simulator.py         # Simulate Next Day payloads
├── graphql_api.py       # one Strawberry join query (12)
├── tools/*.py           # one module per backing service
├── guardrails/
│   ├── scoring.py       # pure compute_score + gather_*_inputs I/O
│   ├── policy.py        # thresholds, hard cap, route()
│   ├── engine.py        # guard_* write paths, wrap_read_tool, sweep, resolve
│   ├── models.py        # SQLAlchemy audit tables
│   └── db.py            # engine, sessions, init_db, reset_audit_tables
└── tests/               # heaviest coverage on scoring (14)
```

### Config-driven registry

Each tool module registers handlers with `@register(name, service, kind, rest=...)`. Importing the module is the registration (side effect). `main.py` loops `registry.all_tools()` once to:

1. Wire each handler into `mcp.tool(...)`
2. Power `GET /tools` and catalog entries

One list — MCP protocol view and REST introspection cannot drift apart.

### Tools (default: 11)

| Service | Read tools | Write tools |
|---|---|---|
| OneSource360-sim | `list_campaigns`, `get_campaign_performance`, `get_performance_anomalies` | — |
| SmartSpot360-sim | `get_spot_performance`, `get_budget_recommendation` | `reallocate_budget` |
| Captivator360-sim | `get_creative_performance`, `get_declining_creatives` | `request_creative_refresh` |
| Maestro360-sim | `get_call_quality`, `get_routing_summary` | — |

Every tool is a thin `httpx` proxy to a DRF (or RankPulse FastAPI) endpoint. Interesting logic lives in the guardrail.

`RestCall` metadata on each registration (`method`, `path`, `query_from`, `when`) is what the frontend's technical trace uses to reconstruct the real HTTP the container sent.

## The risk-scoring guardrail (headline design)

Split deliberately by failure mode:

### `scoring.py` — pure math + separate I/O gatherers

`compute_score(magnitude_pct, confidence, recency_flag, vertical, hard_cap_exceeded)`:

- Weights: **50%** magnitude / **35%** confidence / **15%** recency
- Confidence is **inverted** (low confidence → high risk)
- Regulated verticals (currently `medicare_advantage`) multiply by **1.4×**, capped at 100
- `hard_cap_exceeded` does **not** change the numeric score — it's a separate gate for routing

`gather_reallocate_budget_inputs()` / `gather_creative_refresh_inputs()` hit sim REST APIs + the MCP DB to produce those four numbers using **per-tool** definitions (`PLANNING.md` §7):

| Input | `reallocate_budget` | `request_creative_refresh` |
|---|---|---|
| Magnitude | $ moved as % of trailing weekly spend | `100 / active_creative_count` (only creative ⇒ max disruption) |
| Confidence | sample size behind SmartSpot recommendation | days of creative performance history |
| Recency | campaign modified in last 24h | same |
| Regulatory | vertical multiplier | same |

Pure `compute_score` gets the heaviest pytest coverage — safety-critical and easy to test without HTTP mocks.

### `policy.py` — business dials

Defaults (all overridable via env):

| Knob | Default | Meaning |
|---|---|---|
| `AUTO_EXECUTE_THRESHOLD` | 30 | Below this *and* hard cap OK → auto-execute |
| `BLOCK_THRESHOLD` | 70 | At/above → hard block |
| `REALLOCATE_BUDGET_HARD_CAP_PCT` | 5% | Never auto-execute larger reallocations |
| `REGULATORY_MULTIPLIER` | 1.4 | Medicare Advantage sensitivity |
| `RECENCY_WINDOW_HOURS` | 24 | "Recently modified" window |

`route(score, hard_cap_exceeded)`:

1. `score >= 70` → `blocked` (wins even if hard-cap logic would say otherwise)
2. `score < 30` and not hard-capped → `auto_execute`
3. else → `pending_approval`

Framing that matters for stakeholders: **the business sets the leash; the deterministic layer enforces it; the agent does not choose its own autonomy.**

### `engine.py` — outcomes are structurally different

| Outcome | What happens |
|---|---|
| `auto_execute` | Snapshot `pre_action_state`, perform real write to sim, record `ExecutedAction`, log `AgentToolCall` |
| `pending_approval` | Create `ProposedAction`, return status **without executing**, log tool call |
| `blocked` | Return rejection reason; log only — no pending row |

`wrap_read_tool()` gives reads the same `AgentToolCall` logging without scoring.

Shared `_execute_reallocate_budget()` / `_execute_request_creative_refresh()` run for both auto-execute and human approve — those paths cannot drift.

## Closing the loop: approve / reject

`POST /agent-actions/{id}/approve` and `/reject` are **plain REST, deliberately not MCP tools**. An agent must never approve its own proposal. React-Admin calls these endpoints.

`resolve_proposed_action()`:

- Updates the **original** `AgentToolCall` outcome (`approved_executed` or `rejected`) — no stale pending row left in the list
- Uses `with_for_update` so double-click approve can't execute twice
- No-ops cleanly if the row is no longer `pending_approval`

## Signature preservation on wrapped reads

`wrap_read_tool` uses a generic `async def wrapper(**kwargs)` for logging. That would normally destroy typed parameters for MCP schema generation. `@functools.wraps(func)` sets `__wrapped__`; `inspect.signature()` follows it and exposes the *original* `(campaign_id: int, ...)` to the SDK's Pydantic schema builder. Live `tools/list` shows real typed inputs, not a kwargs blob.

## REST surface beside `/mcp`

| Path | Role |
|---|---|
| `GET /health` | Healthcheck |
| `GET /tools` | Registry introspection |
| `GET /catalog` | Systems UI catalog |
| `GET /inspect` | Gateway table snapshot |
| `GET /agent-actions`, `/pending` | Approval queue |
| `POST /agent-actions/{id}/approve\|reject` | Human resolution |
| `GET /tool-calls` | Full trace |
| `GET /flagged-campaigns`, `POST .../sweep` | Anomaly audit |
| `POST /simulate-next-day` | Live event feed (`13`) |
| `/graphql` | Join query (`12`) |
| `/mcp` | MCP Streamable HTTP |

## Live-verified three-tier scenario (campaign 1)

Baseline weekly spend ≈ $50,300:

| Proposed action | Magnitude | Score | Outcome |
|---|---|---|---|
| Reallocate $500 | ≈1% | 0.69 | `auto_execute` |
| Reallocate $20,000 | ≈40%, hard cap, recently touched | 48.85 | `pending_approval` |
| Reallocate $60,000 | ≈120% clamped, hard cap, recent | 91.0 | `blocked` |

Replayed in `tests/test_scoring.py` (`TestLiveDemoScenarioReplay`).

## Onboarding RankPulse live

`tools/rankpulse.py` is fully `@register`'d. `main.py` keeps `import tools.rankpulse` commented out. Uncomment → `docker compose up -d --build mcp_server` → registry goes 11 → 12 tools. No core gateway changes. Re-comment to reverse. That's the acquisition-integration demo (`PLANNING.md` §2).

## Key vocabulary

- **MCP** — protocol for tool/data access from LLM clients.
- **Streamable HTTP** — network transport for a shared long-lived server (vs stdio).
- **Tool registry** — config-driven map of name → handler → service → schemas.
- **Read vs write tool** — Agent360 convention: reads log+execute; writes score first.
- **Hard cap** — score-independent ceiling blocking unsupervised large actions.
- **`ProposedAction` / `ExecutedAction` / `AgentToolCall`** — approval queue, audit of done work, universal call log.
- **`__wrapped__`** — how wrapped read tools keep real parameter schemas.

## Try this yourself

```bash
curl -s http://localhost:8100/tools | python -m json.tool | head -60
curl -s http://localhost:8100/health
```

A bare `tools/list` without an MCP session handshake fails with a missing session ID — clients must `initialize` first. Claude Code and Cursor do that for you (`06`).

**Next:** `06-claude-code-as-agent.md` for the client side of the same protocol.
