# 09 — Docker Compose

**Status**: complete. Compose is how every process in this repo actually runs together — four Django sims, RankPulse-sim, the MCP server, Redis, Celery worker + beat, the frontend, and one Postgres with five logical databases.

## What it is

Docker Compose starts a set of containers from one YAML file, gives them a shared network so they can reach each other by service name, and (with `depends_on` + `healthcheck`) waits until a dependency is actually ready rather than merely started. That's the difference between "the MCP server booted" and "the MCP server booted *after* OneSource360 had finished migrating and seeding."

## Why this piece of the stack is used here

The architecture claim is runtime independence: own process, own database, HTTP-only. Compose is what makes that true on a laptop without five terminals and a local Postgres. It is also what makes the demo reproducible — `docker compose up --build` is the whole boot path, including seed data.

## Where it lives in this repo

- `docker-compose.yml` — the whole topology. YAML anchors (`x-django-start`, `x-django-health`) keep the four Django services' migrate+seed command and healthcheck timings in one place.
- `infra/postgres-init/01-create-databases.sh` — the official Postgres image runs anything in `/docker-entrypoint-initdb.d/` **once**, on first volume init. `POSTGRES_DB` only creates `onesource360`; this script creates `smartspot360`, `captivator360`, `maestro360`, and `mcp_server`.
- Each service's `Dockerfile` — Python/Node image, install deps, copy code. Django containers don't seed themselves in the image; Compose's `command:` override does `migrate && seed_data && runserver` so a restart resets sim data to the §9 scenario. The MCP server mirrors that for its own DB: on every boot, `reset_audit_tables()` clears tool calls / agent actions / flagged campaigns, then the startup anomaly sweep re-flags campaign 1 (`docker compose restart mcp_server` is the demo prep for a clean Agent Actions list).
- `frontend/Dockerfile` + Compose `volumes` on `frontend/src` — Vite runs in the container but picks up local source edits without a rebuild.

Healthchecks matter here specifically: `mcp_server` used to `depends_on: service_started`, which raced Django's `migrate`. It now waits for `service_healthy` on each sim (`GET /health/`, which stays unauthenticated). Celery worker waits for `mcp_server` healthy so the first sweep doesn't hit a half-booted API. The four Django services and the MCP server share `SERVICE_TOKEN` (`x-service-auth` anchor) so webhook POSTs from Simulate Next Day authenticate as the gateway.

Host ports are shifted where a laptop might already be using the default (`5433` for Postgres, `6380` for Redis). Inside the Docker network, services still talk to `postgres:5432` and `redis:6379`.

## Key vocabulary

- **Service vs. container** — a Compose *service* is the recipe; a *container* is a running instance of it.
- **Healthcheck** — a command Compose runs inside the container; `depends_on: condition: service_healthy` waits for it to pass.
- **Logical database** — one Postgres *server* (one container) hosting several `CREATE DATABASE` catalogs. Five catalogs, not five Postgres containers.
- **Anchor / alias** — YAML `x-foo: &foo` then `<<: *foo` or `command: *foo`, so the four Django boot commands can't drift apart.

## Try this yourself

```bash
docker compose ps          # health status per service
docker compose logs -f mcp_server celery_worker
curl http://localhost:8100/health
curl http://localhost:8001/api/campaigns/
```

`docker compose up --build` from a clean volume (`docker compose down -v`) is the full first-boot path, including Postgres init and every `seed_data`.
