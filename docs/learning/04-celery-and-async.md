# 04 — Celery and Async

**Status**: complete. The deterministic anomaly sweep from `PLANNING.md` §8 is built and live-verified. Related: webhooks / Simulate Next Day in `13-webhooks-and-simulation.md`.

## What it is

Celery is a **distributed task queue** for Python. It lets you run a function *outside* the HTTP request/response cycle — either soon after something happens, or on a schedule. Three moving parts:

| Piece | Job |
|---|---|
| **Broker** | Holds "please run this task" messages. Here: **Redis** (used as a queue, not a cache). |
| **Worker** | Process that pulls messages and executes task code (`celery_worker` container). |
| **Beat** | Scheduler that only *enqueues* periodic tasks on a timer (`celery_beat` container). Beat never runs task bodies. |

Why two containers for worker vs. beat? So a crash or deploy of one doesn't take down the other, and so you can scale workers independently. Compose mirrors that split even for a laptop demo.

## Why this piece of the stack is used here

`PLANNING.md` §8 needs campaigns with anomalous CPL flagged **without an LLM in the loop** — pure SQL/math on a timer. Celery is the standard Django/Python answer for that.

**Where it lives matters as much as that it exists.** The Decisions Log put Celery alongside the MCP server, reusing the gateway's own code, because only the gateway already has a clean reason to read across all four sim services. Concretely: the scheduled sweep calls the same `get_performance_anomalies()` function a live agent conversation would call — the raw Python function in `tools/onesource360.py`, not the MCP-wrapped handler (wrapping would falsely log a sweep as an agent tool call).

> **Scheduled monitoring and agent-driven investigation are the same code path — a timer instead of a conversation.**

## Where it lives in this repo

### `mcp_server/celery_app.py`

Defines the Celery app (`agent360`), points it at Redis (`REDIS_URL`, default `redis://redis:6379/0`) as both broker and result backend, and declares `beat_schedule`:

- one entry: `sweep-for-anomalies`
- every `ANOMALY_SWEEP_INTERVAL_SECONDS` (default **300** = 5 minutes)

Standard multi-file layout: `celery_app.py` imports `tasks` at the bottom so `@celery_app.task` registration happens as an import side effect; `tasks.py` imports `celery_app` back. That looks circular but works — by the time `tasks` runs `from celery_app import celery_app`, the app object already exists in the partially loaded module.

### `mcp_server/tasks.py`

`sweep_for_anomalies()` is a sync Celery task wrapping async helpers via `asyncio.run(...)`. Celery's default worker model is synchronous; the MCP/httpx/SQLAlchemy stack is async. Bridging with `asyncio.run` is a deliberate, small boundary — cleaner here than running Celery in async mode for one task.

### `mcp_server/guardrails/engine.py` → `run_anomaly_sweep()`

The real logic, callable from **three** places identically:

1. Celery beat → worker (periodic)
2. `POST /flagged-campaigns/sweep` (manual / Overview button)
3. MCP server lifespan on startup (so flagged data exists immediately, not after ≤5 minutes)

Startup lifespan order in `main.py`: `init_db` → `reset_audit_tables` → `run_anomaly_sweep`. Restarting `mcp_server` therefore clears Agent Actions / Tool Calls and re-flags campaign 1 — demo prep in one command.

The sweep:

1. Calls `tools.onesource360.get_performance_anomalies()` directly
2. For each anomaly, checks `FlaggedCampaign` for an existing `(campaign_id, variance_pct)` row
3. Inserts only if new — **idempotent** against unchanged seed data (the common case until someone clicks Advance one day)

### Compose services

| Service | Command | Needs |
|---|---|---|
| `redis` | Redis 7 Alpine; host port **6380** → container 6379 | — |
| `celery_worker` | `celery -A celery_app worker` | Redis + sim URLs + MCP DB creds + `SERVICE_TOKEN` (it runs the sweep) |
| `celery_beat` | `celery -A celery_app beat` | Mostly Redis + interval env (enqueues only) |

Worker waits for `mcp_server` healthy so the first tick doesn't hit a half-booted API.

### Frontend

`Overview.jsx` surfaces "Automated Anomaly Sweep" (log + "Run sweep now") and "Simulate Next Day" (which posts webhooks then re-runs the same sweep — `13`).

## Two flagging mechanisms, on purpose

| Mechanism | Where | Persistence |
|---|---|---|
| Client-side "flagged" | `dataProvider.js` `windowedCplVariance` on every Campaigns/Overview load | None — computed live |
| Celery / startup / manual sweep | `FlaggedCampaign` rows in `mcp_server` DB | Persisted audit trail with timestamps |

Both use the same trailing-window CPL math (>15% over target by default). They are **additive**: the sweep proves a real system-of-record is detecting anomalies, not only a page doing arithmetic when someone looks. Client-side tiles still work even if Redis/Celery were down.

## Redis in this project (narrow role)

Redis can be a cache, session store, pub/sub bus, or broker. Here it is **only a Celery broker/result backend**. No application code reads Redis for campaign data. If you see Redis in the architecture diagram, think "task queue," not "second database."

## Sync vs async — mental model

```text
HTTP request (FastAPI)     → async handlers, await httpx, await SQLAlchemy
Celery worker process      → sync task entrypoint → asyncio.run(async sweep)
Claude Code tool call      → MCP async path → same get_performance_anomalies()
```

Three triggers, one detection function. That sameness is the design goal.

## Key vocabulary

- **Broker** — queue between enqueuer and worker. Redis here.
- **Worker** — process that executes task code.
- **Beat** — process that enqueues periodic tasks; never executes them.
- **Idempotent sweep** — re-running against unchanged data doesn't create duplicate `FlaggedCampaign` rows.
- **Result backend** — where Celery can store return values; configured to Redis here (handy for debugging, not critical to the demo UI).
- **`asyncio.run`** — starts an event loop to drive async code from a sync context (the Celery task).

## Try this yourself

```bash
# On-demand (same code path as beat)
curl -X POST http://localhost:8100/flagged-campaigns/sweep

# See the scheduler tick
docker compose logs -f celery_beat

# See the worker execute
docker compose logs -f celery_worker

# List flagged rows the UI reads
curl -s http://localhost:8100/flagged-campaigns | python -m json.tool
```

Compare a manual POST against a beat tick in the logs — identical result, different trigger.

**Next:** `05-mcp-servers.md` for the gateway the sweep sits beside.
