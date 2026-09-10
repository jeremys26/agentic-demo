# 03 — Postgres Schema Design

**Status**: complete. All five logical databases (four Django services + the MCP server) exist and are seeded. Audit-table wipe-on-boot is covered at the end.

## What it is

PostgreSQL is a relational database: tables, typed columns, primary keys, foreign keys, unique constraints, and SQL. In Agent360 that's layered on something less ordinary:

> **One Postgres *server* (one Docker container), five *logical databases*.**

Each Django service and the MCP gateway connect to the same host (`postgres`) but a different `DB_NAME`. They cannot `JOIN` across those databases. That is the concrete mechanism behind "independent systems, HTTP-only."

Terminology trap: Postgres also has *schemas* inside a database (`public`, etc.). Agent360 uses the default `public` schema in each logical database. When this doc says "schema design," it means table design — not Postgres schema namespaces.

## Why this piece of the stack is used here

`PLANNING.md` §5's claim — four standalone services, not four apps in one project — only survives if each service is physically unable to see another's tables. One Postgres container is cheap locally (one process, one volume). A logical database boundary still gives real isolation: credentials for `onesource360` have no visibility into `smartspot360`, even on the same server.

The MCP server gets its own fifth database (`mcp_server`) for agent audit/approval state (`AgentToolCall`, `ProposedAction`, `ExecutedAction`, `FlaggedCampaign`). The four sims know nothing about agents.

## Where it lives in this repo

| Piece | Role |
|---|---|
| `docker-compose.yml` → `postgres` | `postgres:16-alpine`; `POSTGRES_DB: onesource360` creates the *first* database only |
| `infra/postgres-init/01-create-databases.sh` | Runs once on empty volume via `/docker-entrypoint-initdb.d/`; creates `smartspot360`, `captivator360`, `maestro360`, `mcp_server` |
| Each service's `DATABASES` in `settings.py` | Points at its own `DB_NAME` |
| `mcp_server/guardrails/models.py` + `db.py` | SQLAlchemy models + `create_all` / `reset_audit_tables` (not Django) |
| `<app>/migrations/*.py` | Django schema history per service |

### Why the init script needs `--dbname`

An earlier version of `01-create-databases.sh` omitted `--dbname` and broke: without it, `psql` defaults to a database named after the connecting user, which doesn't exist here. The script connects with `--dbname "$POSTGRES_DB"` (the one database guaranteed to exist), then `CREATE DATABASE` for the rest. Init scripts run **only when the data volume is empty** — `docker compose down -v` is how you re-run them.

## Within-service relationships: real foreign keys

Every service has at least one FK tying a daily/event table back to its parent — both tables live in the same database, so referential integrity is exactly what FKs are for:

| Service | Parent | Child(ren), FK'd |
|---|---|---|
| OneSource360-sim | `Campaign` | `DailyPerformanceRollup` |
| SmartSpot360-sim | `Spot` | `SpotPerformance` (one-to-one); `Station` / `Daypart` also FK'd from `Spot` |
| Captivator360-sim | `CreativeAsset` | `CreativePerformanceDaily`, `CreativeRefreshRequest` |
| Maestro360-sim | `ClientAgentPool` | `RoutingRule`, `CallEvent` |

`unique_together` (or equivalent constraints) enforce one row per entity per day where that matters — e.g. `(campaign, date)` on rollups, `(creative, date)` on creative performance.

## Cross-service relationships: plain integer ids

`Spot.campaign_id`, `CreativeAsset.campaign_id`, and `CallEvent.campaign_id` are `PositiveIntegerField`s pointing at a `Campaign.id` that lives in **another** database. Postgres cannot enforce that FK. Comments in those models say so explicitly so it isn't misread as a missing relationship.

**Join key for the whole demo:** campaign id `1` ("Medicare Advantage – Southeast TV"). Every investigation, GraphQL query, and seed scenario hangs off that integer across four databases.

If you ever needed to validate "does this campaign exist?" from SmartSpot360, you'd call OneSource360's REST API — not a SQL join. That's the architecture talking.

## What the tables actually store (business meaning)

These services don't run a real media buyer, creative studio, or call center. They store the records those systems would have produced, because that's what an agent needs to read.

| Database | Tables | One row means |
|---|---|---|
| `onesource360` | `Campaign` | A named advertising effort (product + region + channel) plus a target cost-per-lead |
| `onesource360` | `DailyPerformanceRollup` | That campaign's scoreboard for one day: spend, leads, calls, conversions, CPL = spend ÷ leads |
| `smartspot360` | `Station`, `Daypart` | Where and when ads can air (WSVN Miami; Daytime vs Prime) |
| `smartspot360` | `Spot` + `SpotPerformance` | One paid airing on a date, and how many calls/conversions it produced |
| `smartspot360` | `BudgetRecommendation` | A proposed split of a budget across station/daypart combos |
| `captivator360` | `CreativeAsset` | One ad version (CR-114) belonging to a campaign |
| `captivator360` | `CreativePerformanceDaily` | That ad's daily impressions, CTR, and conversion rate. CTR decline is *computed* from this table, not stored as a column. |
| `captivator360` | `CreativeRefreshRequest` | A request to replace a stale ad |
| `maestro360` | `ClientAgentPool`, `RoutingRule` | Call-center teams and the priority order for sending calls to them |
| `maestro360` | `CallEvent` | One inbound phone call: timestamp, which pool got it, wait/duration, outcome |
| `mcp_server` | `agent_tool_calls` | Every MCP tool invocation (read or write), with outcome |
| `mcp_server` | `proposed_actions` | Write actions waiting on a human |
| `mcp_server` | `executed_actions` | Auto-executed (or later approved) writes, including `pre_action_state` snapshot |
| `mcp_server` | `flagged_campaigns` | Anomaly-sweep hits |

### Seed volume (so inspect pages make sense)

- OneSource360: 6 campaigns × 28 days of rollups
- Maestro360: thousands of `CallEvent` rows (pool-shift story needs volume)
- Inspect endpoints page large tables (Maestro360 snapshots 50 rows at a time)

## MCP audit DB: SQLAlchemy, not Django

The gateway is FastAPI/async (`11-fastapi-pydantic-sqlalchemy.md`). Its tables are declared with SQLAlchemy 2.0 style (`Mapped[...]`, `mapped_column`) in `guardrails/models.py`, created with `Base.metadata.create_all()` at startup — proportionate for a local demo, not a full Alembic migration history.

**Demo hygiene:** `reset_audit_tables()` truncates those four tables on every `mcp_server` boot. The schema stays on the Postgres volume; the demo log does not. Then the startup anomaly sweep re-flags campaign 1. Same idea as the Django sims' reseed-on-start.

## Indexes and constraints worth noticing

You don't need to be a DBA for this project, but these ideas show up:

- **Primary keys** — Django/`BigAutoField` and SQLAlchemy integer PKs on every table
- **Unique constraints** — prevent duplicate daily rollups if a webhook retries
- **Foreign keys** — within one DB only; cascade deletes on warehouse children
- **No cross-DB transactions** — Simulate Next Day posts four separate HTTP webhooks; a failure mid-way is possible (demo accepts that; a production saga would be a different design)

## Inspect endpoints — schema made visible

Each Django service exposes `GET /api/inspect/`; the gateway exposes `GET /inspect`. The Systems UI (`08`) joins that with `GET /catalog` so a demo can point at: *this table → this REST path → this MCP tool handler*. That's pedagogy as a feature, not just docs.

## Key vocabulary

- **Logical database** — a named database within one Postgres server (`CREATE DATABASE x;`). Distinct from a *schema* in Postgres's narrower sense.
- **Foreign key (FK)** — DB-enforced reference from child row → parent row, same database only.
- **`unique_together` / unique constraint** — DB rejects a second row with the same key combo.
- **`docker-entrypoint-initdb.d`** — official Postgres image runs `.sh`/`.sql` here once on first volume init.
- **ORM vs. SQL** — Django ORM and SQLAlchemy both generate SQL; isolation rules still come from Postgres.
- **Audit tables** — gateway-owned records of what the agent did; separate from business data in the sims.

## Try this yourself

```bash
# List the five databases
docker compose exec postgres psql -U agent360 -l

# Only Captivator360's tables
docker compose exec postgres psql -U agent360 -d captivator360 -c '\dt'

# Prove campaign 1 exists in the warehouse
docker compose exec postgres psql -U agent360 -d onesource360 \
  -c "SELECT id, name, target_cpl FROM campaigns_campaign WHERE id = 1;"

# Same id referenced (not FK'd) from Maestro
docker compose exec postgres psql -U agent360 -d maestro360 \
  -c "SELECT COUNT(*) FROM calls_callevent WHERE campaign_id = 1;"

# Gateway audit tables (SQLAlchemy names)
docker compose exec postgres psql -U agent360 -d mcp_server -c '\dt'
```

The same snapshots appear in the console at `http://localhost:3000/#/systems/onesource360` (and siblings).

**Next:** `04-celery-and-async.md` for the scheduled reader that scans these warehouses without an LLM.
