# 13 — Webhooks and Simulate Next Day

**Status**: complete. Live event simulation from Overview's "Advance one day" button. Celery sweep that runs afterward: `04`. Auth on webhook POSTs: `07`.

## What it is

A **webhook** is an HTTP callback: system A POSTs to system B when something happens, instead of B polling A. In marketing/martech stacks, warehouses and channel systems often ingest daily rollups this way.

In Agent360, each of the four Django sims owns its own webhook receiver. The MCP gateway's **Simulate Next Day** feature builds a plausible next calendar day's payloads and POSTs them to those four endpoints — then re-runs the anomaly sweep. The gateway never writes directly into the sims' databases.

## Why this piece of the stack is used here

1. **Honesty to the architecture** — "each service owns its data" means ingestion enters through that service's API, not a shared SQL backdoor (`PLANNING.md` Decisions Log).
2. **Demo motion** — seed data is a fixed 28-day window; Advance one day shows the stack reacting to *new* events while keeping campaign 1 in the spiked-CPL pattern.
3. **Auth exercise** — webhooks require `X-Service-Token` (or JWT), same as other writes.

## Where it lives

| Piece | Role |
|---|---|
| `mcp_server/simulator.py` | Builds payloads; `run_simulate_next_day()` fans out POSTs |
| `mcp_server/main.py` | `POST /simulate-next-day` |
| `services/*/…/views.py` | Per-service `POST /api/webhooks/...` receivers |
| `frontend/src/pages/Overview.jsx` | "Advance one day" button |

### Receivers (one per sim)

| Service | Path | Payload gist |
|---|---|---|
| OneSource360 | `/api/webhooks/daily-performance/` | `rollups[]` of campaign/date/spend/leads/… |
| SmartSpot360 | `/api/webhooks/spot-performance/` | new spots + performance for the sim date |
| Captivator360 | `/api/webhooks/creative-metrics/` | daily creative metrics rows |
| Maestro360 | `/api/webhooks/call-events/` | batch of call events |

Receivers are **idempotent by date** where it matters: replaying the same date is skipped so double-clicks don't duplicate warehouse days.

### Simulator behavior (`simulator.py`)

1. Read current campaigns / latest rollup date from OneSource360
2. Choose `next_sim_date` (day after latest, or default `2026-08-29` after the seeded window)
3. Build rows that **continue the §9 pattern**:
   - Campaign 1: elevated CPL / soft leads (still spiked)
   - Other campaigns: steady around target
   - Creatives: continuing CTR pressure on the declining variant
   - Calls: Pool B overflow regime continues
4. POST each payload with `service_client()` (service token attached)
5. Caller (`main.py`) then runs `run_anomaly_sweep()` so Overview's flagged list updates

Randomness is seeded enough to look alive but constrained enough that the demo story doesn't randomly heal.

## Sequence diagram

```text
Overview "Advance one day"
  → POST http://localhost:8100/simulate-next-day
    → POST onesource360:/api/webhooks/daily-performance/   (+ X-Service-Token)
    → POST smartspot360:/api/webhooks/spot-performance/
    → POST captivator360:/api/webhooks/creative-metrics/
    → POST maestro360:/api/webhooks/call-events/
    → run_anomaly_sweep()
  ← summary JSON (dates, counts, sweep result)
```

Partial failure is possible (four independent HTTP calls, no distributed transaction). Acceptable for a demo; a production design might use an outbox/saga.

## What this is not

- Not a message bus (Kafka/SNS) — plain HTTPS POSTs
- Not Celery tasks doing the inserts — Celery only re-detects anomalies after data lands
- Not the MCP tool path — Simulate Next Day is gateway REST for humans/operators

## Key vocabulary

- **Webhook** — inbound POST notifying a system of new data/events.
- **Idempotent receiver** — processing the same event twice doesn't create duplicate business rows.
- **Fan-out** — one operator action becomes many downstream HTTP calls.
- **Seed window vs live edge** — 28-day `seed_data` history vs days appended by the simulator.
- **Service token on ingress** — machines push data with the same credential the gateway uses for tools (`07`).

## Try this yourself

```bash
# Before
curl -s http://localhost:8100/flagged-campaigns | python -m json.tool | head -30

# Advance
curl -s -X POST http://localhost:8100/simulate-next-day | python -m json.tool

# Without token, a direct webhook should fail
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  http://localhost:8001/api/webhooks/daily-performance/ \
  -H 'Content-Type: application/json' -d '{"rollups":[]}'
```

Or click **Advance one day** on Overview and watch Systems → OneSource360 pick up a new rollup date.

**Related:** `04` (sweep), `09` (who calls whom on the network), `03` (why not SQL from the gateway).
