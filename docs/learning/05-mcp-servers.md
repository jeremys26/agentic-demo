# 05 — MCP Servers

**Status**: complete. Full tool registry (11 tools across all four services) and risk-scoring guardrail, including the human-approval path — all three autonomy tiers closed-loop end to end. Tier 2: RankPulse-sim ready to onboard live but unregistered by default; Celery anomaly sweep (`04-celery-and-async.md`).

## What it is

MCP (Model Context Protocol) is a standard way for an LLM-driven agent — Claude Code, Cursor, or anything else that speaks the protocol — to discover and call **tools** exposed by a server, without the agent's vendor needing custom integration code for every backend it might touch. A tool is a typed function: a name, a description, an input schema, and code that runs when it's called. Agent360 uses the **Streamable HTTP** transport — a persistent, network-reachable server rather than a spawned local process — since multiple clients (Claude Code and Cursor) need to connect to the same long-lived server.

## Why this piece of the stack is used here

This *is* the project, architecturally: the MCP server is the **governed gateway** (`PLANNING.md` §7) — every tool call flows through it, gets logged, and for write actions, gets risk-scored before anything executes. No custom agent-orchestration loop was built (`PLANNING.md` §5) — Claude Code already has one; the only code Agent360 needs is the tools themselves and the policy that governs them.

## Where it lives in this repo

- `mcp_server/registry.py` — the config-driven tool registry. Each tool module registers its handlers via a `@register(name, service, kind)` decorator; `registry.all_tools()` returns every registered `ToolSpec`. `main.py` loops over it once to wire every tool into both the MCP server and the `/tools` REST introspection endpoint, so the two can't drift apart.
- `mcp_server/tools/{onesource360,smartspot360,captivator360,maestro360}.py` — one module per backing service, 11 tools total:

  | Service | Read tools | Write tools |
  |---|---|---|
  | OneSource360-sim | `list_campaigns`, `get_campaign_performance`, `get_performance_anomalies` | — |
  | SmartSpot360-sim | `get_spot_performance`, `get_budget_recommendation` | `reallocate_budget` |
  | Captivator360-sim | `get_creative_performance`, `get_declining_creatives` | `request_creative_refresh` |
  | Maestro360-sim | `get_call_quality`, `get_routing_summary` | — |

  Every tool is a thin proxy to its service's REST API (`httpx` calls) — the interesting logic lives one layer up, in the guardrail.

- `mcp_server/guardrails/` — the risk-scoring guardrail (`PLANNING.md` §7), split deliberately by what kind of bug each half can have:
  - `scoring.py` — `compute_score()` is pure math, no I/O: takes `magnitude_pct`, `confidence`, `recency_flag`, `vertical` (plus a separately-computed `hard_cap_exceeded` flag) and returns a 0–100 `RiskResult`. Weighted 50% magnitude / 35% confidence / 15% recency, then multiplied by a regulatory-sensitivity multiplier (1.4×) for regulated verticals (currently just `medicare_advantage`), capped at 100. Confidence is *inverted* before weighting — low confidence means high risk, not low risk, which is the whole point of a confidence input. The same file's `gather_reallocate_budget_inputs()` and `gather_creative_refresh_inputs()` do the I/O: calling each sim service's REST API and the MCP server's own DB to turn a proposed action into those four numbers, using the per-tool definitions from `PLANNING.md` §7 (e.g. `reallocate_budget`'s magnitude is the recommendation's dollar amount as a % of the campaign's trailing weekly spend; `request_creative_refresh`'s magnitude is `100 / active-creative-count`, so refreshing a campaign's only active creative scores maximally disruptive).
  - `policy.py` — the configurable dials: `AUTO_EXECUTE_THRESHOLD` (30), `BLOCK_THRESHOLD` (70), `REALLOCATE_BUDGET_HARD_CAP_PCT` (5%), `REGULATORY_MULTIPLIER` (1.4), `RECENCY_WINDOW_HOURS` (24) — all overridable via environment variables rather than hardcoded, so tuning them is a deployment config change, not a code change. `route(score, hard_cap_exceeded)` applies `PLANNING.md` §7's three-tier logic: `score >= 70` → `blocked` (checked first — a block-tier score blocks regardless of the hard cap flag); `score < 30` and the hard cap wasn't exceeded → `auto_execute`; anything else → `pending_approval`.
  - `models.py` — the MCP server's own SQLAlchemy tables: `agent_tool_calls`, `proposed_actions`, `executed_actions`, and `flagged_campaigns` (reserved through Phase 3, now written to by the Tier 2 Celery anomaly sweep — see `04-celery-and-async.md`). Built with SQLAlchemy + `asyncpg` rather than Django, since the MCP server is a FastAPI/async process, not a Django one; tables are created via `Base.metadata.create_all()` at startup (`db.py`) rather than a full migration system, proportionate to Tier 1 scope. `db.py` also exposes `reset_audit_tables()`, which truncates those four tables on every MCP server boot so Agent Actions / Tool Calls start clean (same idea as the Django sims' reseed-on-start).
  - `engine.py` — ties it together. `guard_reallocate_budget()` and `guard_request_creative_refresh()` gather the risk inputs, score them, route them, and log an `AgentToolCall` no matter what. On `auto_execute`, it snapshots `pre_action_state` before making the real write call to the backing service (the pre-action audit snapshot from §7) and records an `ExecutedAction`. On `pending_approval`, it creates a `ProposedAction` and returns that status *without executing anything*. On `blocked`, it returns the rejection with no record beyond the `AgentToolCall` log. Separately, `wrap_read_tool()` gives every read tool the same `AgentToolCall` logging as write tools, just without a risk score. This file also holds `run_anomaly_sweep()` and `get_all_flagged_campaigns()`, the Celery sweep's logic (`04-celery-and-async.md`) — unrelated to the guardrail logic above, and living here only because it shares this file's DB session pattern and imports, not because it's part of the write-tool guardrail path.

- `mcp_server/main.py` — wires `registry.all_tools()` into `mcp.tool()` calls at import time (read tools wrapped via `wrap_read_tool`, write tools registered directly since they log their own risk score internally), and in the FastAPI lifespan runs `init_db()` → `reset_audit_tables()` → `run_anomaly_sweep()` before the MCP session manager starts (so a restart clears prior demo traffic and immediately re-flags campaign 1). Exposes plain REST alongside the MCP endpoint at `/mcp`: `/health`, `/tools`, `/catalog`, `/inspect`, `/agent-actions`, `/agent-actions/pending`, `POST /agent-actions/{id}/approve`\|`/reject`, `/tool-calls`, `/flagged-campaigns`, `POST /flagged-campaigns/sweep`, `POST /simulate-next-day`, and `/graphql`.

## A subtlety worth understanding: how a wrapped read tool keeps its real type signature

`wrap_read_tool()` wraps every read tool in a generic `async def wrapper(**kwargs)` for uniform logging — which would normally lose the original function's typed parameters (`campaign_id: int`, etc.) and register a useless generic schema with MCP clients. It doesn't, because the wrapper is built with `@functools.wraps(func)`, which sets `wrapper.__wrapped__ = func`. `inspect.signature()` — what the SDK uses internally to build each tool's Pydantic input schema — follows `__wrapped__` by default and returns the *original* function's signature, not the wrapper's `(**kwargs)`. Confirmed live: a real MCP `initialize` + `tools/list` handshake against the running server shows all 11 tools with correct, fully-typed input schemas (e.g. `get_campaign_performance` requires `campaign_id: integer` and takes optional `start_date` / `end_date` strings), not a generic kwargs blob.

## Closing the loop: how a queued action actually gets resolved

- `POST /agent-actions/{id}/approve` and `POST /agent-actions/{id}/reject` on the MCP server (`main.py`) — plain REST, **deliberately not MCP tools**. An agent must never be able to approve its own proposed action; only a human, via this endpoint (which React-Admin calls), can. `guardrails/engine.py`'s `resolve_proposed_action()` backs both: it updates the **original** `AgentToolCall` row (`rejected` or `approved_executed`) rather than inserting a second log line, so the Agent Actions list doesn't keep a stale pending row with live Approve/Reject buttons after the human has already decided.
- The real execution logic — the SmartSpot360 "apply" call, the Captivator360 create-then-resolve call — lives in shared `_execute_reallocate_budget()` / `_execute_request_creative_refresh()` helpers in `engine.py`, used by **both** the `auto_execute` path and the approve path, so the two routes can't drift apart.
- Idempotency: `resolve_proposed_action()` returns cleanly if the row isn't still `pending_approval`, and loads it `with_for_update` so two near-simultaneous approve clicks can't both execute. Captivator360's refresh endpoint also returns an existing pending request instead of creating a duplicate, so a retry of the create-then-resolve path is safe.

## Live-verified three-tier scenario (campaign 1, baseline weekly spend ≈ $50,300)

| Proposed action | Magnitude | Score | Outcome |
|---|---|---|---|
| Reallocate $500 | ≈1% of baseline | 0.69 | `auto_execute` |
| Reallocate $20,000 | ≈40% of baseline, hard cap exceeded, campaign recently touched | 48.85 | `pending_approval` |
| Reallocate $60,000 | ≈120% of baseline (clamped), hard cap exceeded, recently touched | 91.0 | `blocked` |

All three replayed as fixed-input pytest cases in `mcp_server/tests/test_scoring.py`'s `TestLiveDemoScenarioReplay`. The full `mcp_server/` suite also covers logging helpers, the simulator's next-day math, and GraphQL blending — heaviest coverage remains the pure-function scoring/policy tests, the safety-critical part of the system per §7.

## Tier 2: onboarding a fifth platform live

`PLANNING.md` §14 phase 10 asks for a concrete demonstration of the registry's config-driven design: register a brand-new platform live, with no MCP server core changes, to dramatize how fast a newly-acquired tool could join the agent's toolset (§2's structural business problem). `mcp_server/tools/rankpulse.py` is that tool, fully built and `@register`-decorated exactly like the other four modules — proxying to `services/rankpulse_sim`, a standalone single-file FastAPI service (deliberately *not* another Django project, since the point is that an acquisition brings its own pre-existing stack) that's running the whole time in `docker-compose.yml`. What's different is `main.py`: its import is commented out —

```python
# import tools.rankpulse  # noqa: F401 — ... onboard it live: uncomment this one
# line, then `docker compose up -d --build mcp_server` ...
```

— so the tool doesn't exist in the registry (`GET /tools` shows 11, not 12) until that one line is uncommented and the container rebuilt. Verified live: uncommenting it took the registry to 12 tools, a real MCP `tools/call` for `get_organic_performance` succeeded and logged to `AgentToolCall` exactly like any other read tool (`service: "rankpulse"`), and re-commenting it dropped the registry back to 11 — confirming the "on" and "off" states both work cleanly, so this is a real live-demo moment, not a scripted illusion.

## Two clients, one server

`PLANNING.md` §8's Tier 2 vendor-agnostic proof: the same server, unmodified, works with a second, genuinely independent MCP client. `.cursor/mcp.json` in the repo root already points Cursor at `http://localhost:8100/mcp` — the identical URL Claude Code uses. Cursor also ships a headless CLI (`cursor-agent -p`), which can drive this same proof non-interactively (`cursor-agent -p --approve-mcps --trust "..."` from the repo root), but requires its own one-time `cursor-agent login` first; that's a step for whoever's account runs the demo, not something scriptable in advance. Either path — the Cursor app or the CLI — talks to the exact same governed gateway (§7's scoring, policy, and logging) that Claude Code does; nothing server-side knows or cares which client is asking. See `06-claude-code-as-agent.md` for why that's the actual point.

## Key vocabulary

- **Tool** — a typed, callable function an MCP server exposes to a client.
- **Read tool vs. write tool** — Agent360's own convention: reads execute immediately and just get logged; writes go through the risk-scoring guardrail.
- **Hard cap** — a fixed, score-independent ceiling (e.g. never auto-execute a reallocation above 5% of baseline weekly spend) that can force `pending_approval` even when the computed score alone would have allowed `auto_execute` — defense in depth against a bug in the scoring math itself.
- **`__wrapped__` / signature-following** — the `functools.wraps` mechanism that lets `wrap_read_tool`'s generic wrapper still expose the original function's real parameter types to schema-introspecting code.

## Try this yourself

`curl http://localhost:8100/tools` lists every registered tool's plain-REST schema. Seeing the real MCP protocol view requires a full session handshake (`initialize` → `notifications/initialized` → `tools/list`) rather than a bare POST — that's what the "Missing session ID" error means if you try to skip straight to `tools/list`.
