# 03 — Postgres Schema Design

**Status**: complete. All five logical databases (four Django services + the MCP server) exist and are seeded. The MCP server's own tables (`AgentToolCall`, `ProposedAction`, `ExecutedAction`, `FlaggedCampaign`) live in the `mcp_server` database (`PLANNING.md` §7). Those audit rows are wiped on every `mcp_server` boot (`reset_audit_tables` in `guardrails/db.py`) so a restart matches the Django sims' reseed-on-start — the schema stays on the Postgres volume; the demo log does not.

## What it is

Each Django service owns its own Postgres **schema** in the ordinary sense (a set of tables with foreign keys between them), but in Agent360 that's layered on top of something less ordinary: all five services share one *Postgres server process* while each gets its own *logical database* on that server — five separate namespaces, no shared tables, no cross-database queries possible even if someone tried.

## Why this piece of the stack is used here

This is the concrete mechanism behind the architectural claim in `PLANNING.md` §5 — "four standalone services, not four apps in one project." One Postgres container is cheap to run locally (one process, one Docker volume) instead of five, but it only counts as genuine separation if each service is physically unable to see another's tables. A logical database boundary in Postgres provides exactly that: `services/onesource360` connects to the `onesource360` database with credentials that have no visibility into `smartspot360`, `captivator360`, `maestro360`, or `mcp_server`'s tables, even though all four live on the same server.

## Where it lives in this repo

- `docker-compose.yml` — one `postgres:16-alpine` service, with `POSTGRES_DB: onesource360` creating the *first* of the five databases automatically (that's all the standard Postgres image's `POSTGRES_DB` variable does — one database). Each of the four Django services and the MCP server point at the same Postgres host but a different `DB_NAME` via their own environment block.
- `infra/postgres-init/01-create-databases.sh` — mounted into the Postgres container at `/docker-entrypoint-initdb.d/`, which the official Postgres image runs automatically, once, the first time its data volume is initialized. This script creates the other four databases (`smartspot360`, `captivator360`, `maestro360`, `mcp_server`) that `POSTGRES_DB` alone doesn't. It connects with `--dbname "$POSTGRES_DB"` (the one database guaranteed to already exist) rather than relying on the client's implicit default. An earlier version of this script omitted `--dbname` entirely and broke: without it, `psql` defaults to a database named after the connecting user, which doesn't exist here.
- Each service's own `<app>/models.py` and `<app>/migrations/0001_initial.py` define and create that service's tables inside its one logical database.

**Within-service relationships use real foreign keys.** Every service has at least one FK tying a "daily/event" table back to its parent record, since both tables live in the same database and referential integrity is exactly what FKs are for:

| Service | Parent | Child(ren), FK'd |
|---|---|---|
| OneSource360-sim | `Campaign` | `DailyPerformanceRollup` |
| SmartSpot360-sim | `Spot` | `SpotPerformance` (one-to-one); `Station`/`Daypart` also FK'd from `Spot` |
| Captivator360-sim | `CreativeAsset` | `CreativePerformanceDaily`, `CreativeRefreshRequest` |
| Maestro360-sim | `ClientAgentPool` | `RoutingRule`, `CallEvent` |

**Cross-service relationships are deliberately *not* foreign keys.** `Spot.campaign_id`, `CreativeAsset.campaign_id`, and `CallEvent.campaign_id` are all plain `PositiveIntegerField`s referencing a `Campaign` row that lives in OneSource360-sim's *separate* database — Postgres can't enforce a foreign key across databases even if this repo wanted one to. Every model that does this says so directly in a comment (e.g. `services/maestro360/calls/models.py`'s `CallEvent`), because it's easy to misread a plain integer field as a missing FK rather than an intentional one. This is the schema-level expression of the same "own database, HTTP-only" independence principle from `01-django-basics.md`: if a campaign id from OneSource360-sim ever needed validating from another service, that has to happen over its REST API, not a database join.

**What the tables actually store (business meaning, not schema).** These services don't run a real media buyer, creative studio, or call center. They store the records those systems would have produced, because that's what an agent needs to read. Campaign 1 is the join key across all four databases.

| Database | Tables | One row means |
|---|---|---|
| `onesource360` | `Campaign` | A named advertising effort (product + region + channel) plus a target cost-per-lead |
| `onesource360` | `DailyPerformanceRollup` | That campaign's scoreboard for one day: spend, leads, calls, conversions, CPL = spend ÷ leads |
| `smartspot360` | `Station`, `Daypart` | Where and when ads can air (WSVN Miami; Daytime vs Prime) |
| `smartspot360` | `Spot` + `SpotPerformance` | One paid airing on a date, and how many calls/conversions it produced |
| `smartspot360` | `BudgetRecommendation` | A proposed split of a budget across station/daypart combos |
| `captivator360` | `CreativeAsset` | One ad version (CR-114) belonging to a campaign |
| `captivator360` | `CreativePerformanceDaily` | That ad's daily impressions, CTR, and conversion rate. CTR decline is computed from this table, not stored. |
| `captivator360` | `CreativeRefreshRequest` | A request to replace a stale ad |
| `maestro360` | `ClientAgentPool`, `RoutingRule` | Call-center teams and the priority order for sending calls to them |
| `maestro360` | `CallEvent` | One inbound phone call: timestamp, which pool got it, wait/duration, outcome |

## Key vocabulary

- **Logical database** — a named database within one Postgres server instance (`CREATE DATABASE x;`). Distinct from a *schema* in Postgres's other, narrower sense (a namespace within one database) — Agent360 uses one schema (`public`) per logical database, not multiple schemas within a shared database.
- **`docker-entrypoint-initdb.d`** — the directory the official Postgres Docker image scans for `.sh`/`.sql` files to run automatically on first container startup (only when the data volume is empty). This is how `01-create-databases.sh` runs without any service having to call it explicitly.
- **`unique_together`** — used on `DailyPerformanceRollup` (campaign, date) and `CreativePerformanceDaily` (creative, date) to enforce one row per entity per day at the database level, not just in application code.

## Try this yourself

```bash
docker compose exec postgres psql -U agent360 -l
```
lists all five databases on the one Postgres server. Connecting to any one of them (`docker compose exec postgres psql -U agent360 -d captivator360`) and running `\dt` shows only that service's tables — a direct look at the isolation this doc describes. The same snapshot is in the console at `http://localhost:3000/#/systems/captivator360` (`GET /api/inspect/` on that service).
