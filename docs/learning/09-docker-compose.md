# 09 — Docker Compose

**Status**: complete. Compose is how every process in this repo runs together — four Django sims, RankPulse, MCP server, Redis, Celery worker + beat, frontend, and one Postgres with five logical databases.

## What it is

**Docker** packages an app plus its runtime into an **image**; a running instance is a **container**.

**Docker Compose** reads one YAML file (`docker-compose.yml`) and:

- starts many containers as named **services**
- puts them on a shared **network** so they reach each other by service name (`http://onesource360:8000`)
- can wait for **healthchecks** before starting dependents
- mounts **volumes** for durable data (Postgres) or live source (frontend `src`)

That is the difference between "MCP booted" and "MCP booted *after* OneSource360 finished migrating and seeding."

## Why this piece of the stack is used here

The architecture claim is **runtime independence**: own process, own database, HTTP-only. Compose makes that true on a laptop without five terminals and a local Postgres install. It also makes the demo reproducible: `docker compose up --build` is the whole boot path, including seed data.

## Topology (what Compose starts)

| Service | Image / build | Host port | Role |
|---|---|---|---|
| `postgres` | `postgres:16-alpine` | 5433 → 5432 | Five logical DBs |
| `onesource360` | `./services/onesource360` | 8001 → 8000 | Warehouse API |
| `smartspot360` | `./services/smartspot360` | 8002 → 8000 | Spots / budget API |
| `captivator360` | `./services/captivator360` | 8003 → 8000 | Creatives API |
| `maestro360` | `./services/maestro360` | 8004 → 8000 | Calls API |
| `rankpulse` | `./services/rankpulse_sim` | 8005 → 8000 | Fifth-platform FastAPI |
| `mcp_server` | `./mcp_server` | 8100 → 8100 | Governed gateway |
| `redis` | `redis:7-alpine` | 6380 → 6379 | Celery broker |
| `celery_worker` | same as mcp_server | — | Runs sweep task |
| `celery_beat` | same as mcp_server | — | Schedules sweep |
| `frontend` | `./frontend` | 3000 → 3000 | Vite + React-Admin |

Host ports 5433 / 6380 avoid clashing with common local Postgres/Redis on 5432 / 6379. **Inside** the Docker network, services still use `postgres:5432` and `redis:6379`.

## YAML anchors — DRY for four identical Django boots

```yaml
x-django-start: &django-start
  sh -c "python manage.py migrate && python manage.py seed_data && python manage.py runserver 0.0.0.0:8000"

x-service-auth: &service-auth
  SERVICE_TOKEN: agent360-service
  JWT_SIGNING_KEY: agent360-jwt-dev

x-django-health: &django-health
  interval: 5s
  # ...
```

Each Django service sets `command: *django-start` and merges `<<: *service-auth`. One place to change migrate/seed/runserver or shared secrets — the four services cannot drift apart by accident.

## Networking mental model

```text
Browser on your Mac
  → localhost:3000  (frontend JS)
  → localhost:8001–8005, 8100  (APIs; VITE_* points here)

Inside Compose network
  mcp_server → http://onesource360:8000
  celery_worker → http://captivator360:8000
  * → postgres:5432 / redis:6379
```

Two different DNS worlds: **host localhost** (browser) vs **Compose service names** (container-to-container). Mixing them up is the most common "it works in curl but not in Docker" mistake.

## Healthchecks and `depends_on`

Early versions used `depends_on: service_started` for `mcp_server`, which raced Django's `migrate`. Now each sim exposes `GET /health/` (unauthenticated), and Compose waits for `condition: service_healthy`.

```text
postgres healthy
  → Django sims migrate + seed + healthy
    → mcp_server healthy (init DB, wipe audit, startup sweep)
      → celery_worker / frontend
redis healthy → celery_beat (after worker started)
```

Celery worker also waits for `mcp_server` healthy so the first sweep doesn't hit a half-booted API.

## Volumes and demo hygiene

| Volume / mount | Effect |
|---|---|
| `postgres_data` | Survives `docker compose down`; wiped by `down -v` |
| `infra/postgres-init` → `/docker-entrypoint-initdb.d` | Creates extra DBs **once** on empty volume |
| `./frontend/src` → `/app/src` | Edit React code without rebuilding the image |

Django containers re-seed on every container start (Compose `command:`). MCP clears audit tables on every process boot (`reset_audit_tables`). So:

| Goal | Command |
|---|---|
| Clean Agent Actions / re-flag campaign 1 | `docker compose restart mcp_server` |
| Re-seed four sim DBs | `docker compose restart onesource360 smartspot360 captivator360 maestro360` |
| Full clean slate | `docker compose down -v && docker compose up --build` |

## Dockerfiles (what "build" means)

Each service has a `Dockerfile`: base image (Python or Node), `pip install` / `npm ci`, copy source, default CMD. Compose `build: ./path` uses that context. `--build` forces image rebuild after code/dependency changes; bind mounts can still override `src` for the frontend.

MCP and Celery worker/beat share the **same image** with different `command:` — same code, different process role (`04`).

## Key vocabulary

- **Image vs container** — recipe vs running instance.
- **Service** — named recipe in Compose; may scale to N containers (here usually 1).
- **Healthcheck** — command Compose runs inside the container; gates `service_healthy`.
- **Logical database** — one Postgres server, multiple `CREATE DATABASE` catalogs (`03`).
- **Anchor / alias** — YAML `x-foo: &foo` then `<<: *foo` or `command: *foo`.
- **Bind mount vs named volume** — host path vs Docker-managed volume.
- **Published port** — `HOST:CONTAINER` mapping for access from the Mac/browser.

## Try this yourself

```bash
docker compose ps
docker compose logs -f mcp_server celery_worker
curl -s http://localhost:8100/health
curl -s http://localhost:8001/api/campaigns/ | head

# DNS from inside the network
docker compose exec mcp_server python -c \
  "import urllib.request; print(urllib.request.urlopen('http://onesource360:8000/health/').read())"
```

From a clean volume, `docker compose up --build` exercises Postgres init + every `seed_data`.

**Next:** `10-architecture-recap.md` to tie the whole system together, then optional deep dives `11`–`15` for FastAPI, GraphQL, webhooks, pytest, and CI.
