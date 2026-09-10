# 01 — Django Basics

**Status**: complete. All four sim platforms are standalone Django projects; this doc covers the shared Django patterns they use. Read this before `02-drf-rest-apis.md`.

## What it is

Django is a batteries-included Python web framework. It gives you:

- A **project** — the deployable unit: settings, root URL config, WSGI/ASGI entrypoint
- **Apps** — self-contained bundles of models, views, admin, and management commands inside a project
- An **ORM** — Python classes that map to Postgres tables, plus a query API so you rarely write raw SQL
- **Migrations** — version-controlled Python files that turn model changes into real schema changes
- **Admin** — an auto-generated CRUD UI for any registered model
- **Management commands** — CLI scripts invoked as `python manage.py <name>`

A request walks a fixed path: URL pattern → view (or DRF viewset) → optional ORM query → HTTP response. Middleware runs on the way in and out (CORS, sessions, auth, CSRF). You do not need to invent that plumbing.

## Why this piece of the stack is used here

Django + its ORM is the backbone of every "sim platform" service in Agent360 (`PLANNING.md` §6) — a fast way to get a real, migration-backed Postgres schema and a browsable admin UI without hand-rolling either.

**Why four separate Django projects instead of one project with four apps**: Agent360's pitch is that these systems didn't originally talk to each other, and Agent360 is what connects them. If all four platforms lived as apps inside one Django project sharing one settings file and one database, that claim wouldn't survive scrutiny — it would just be one app with internal modules importing each other directly. Running `django-admin startproject` four separate times, each with its own `manage.py`, `settings.py`, and (per `docker-compose.yml`) its own Postgres database, makes "independent systems, connected over HTTP only" literally true. See `PLANNING.md` §5.

RankPulse-sim (`services/rankpulse_sim`) is deliberately *not* Django — it's a one-file FastAPI stand-in for a newly-acquired platform that brought its own stack. That's the point of the fifth-platform demo, not a fifth copy of this pattern. FastAPI itself is covered in `11-fastapi-pydantic-sqlalchemy.md`.

## Anatomy of one service (OneSource360 as the template)

Each of `services/onesource360`, `services/smartspot360`, `services/captivator360`, and `services/maestro360` is a full Django project. OneSource360 is the walking skeleton everything else copied (`PLANNING.md` §14 phase 1):

```
services/onesource360/
├── manage.py                 # CLI: migrate, runserver, seed_data, shell
├── Dockerfile
├── requirements.txt
└── config/                   # the "project" package
    ├── settings.py           # apps, DB, DRF, JWT, CORS, OpenAPI
    ├── urls.py               # /health/, /api/, /admin/, /api/docs/
    ├── wsgi.py               # production-style entrypoint (runserver uses this path)
    ├── authentication.py     # ServiceTokenAuthentication (see 07)
    └── inspect.py            # shared helper used by GET /api/inspect/
└── campaigns/                # the one "app"
    ├── models.py
    ├── serializers.py        # DRF — see 02
    ├── views.py
    ├── urls.py
    ├── admin.py
    ├── apps.py
    ├── migrations/
    └── management/commands/seed_data.py
```

| Path | Role |
|---|---|
| `<service>/manage.py` | Command-line entrypoint (`migrate`, `runserver`, `seed_data`, `shell`) |
| `<service>/config/settings.py` | Installed apps, Postgres from env vars, DRF, CORS, JWT |
| `<service>/config/urls.py` | Top-level routing; `/api/` delegates to the service's one app |
| `<service>/<app>/models.py` | That platform's tables |
| `<service>/<app>/admin.py` | Registers models with Django admin |
| `<service>/<app>/management/commands/seed_data.py` | `python manage.py seed_data` — the PLANNING.md §9 scenario |

Compose does not call `runserver` alone. Every Django container's command is:

```text
python manage.py migrate && python manage.py seed_data && python manage.py runserver 0.0.0.0:8000
```

So a container restart re-applies migrations (no-ops if already applied) and re-seeds the §9 scenario. That is intentional demo hygiene, not how you'd run a production Django app.

## Models and the ORM — the core idea

A model is a Python class that becomes a table. Fields become columns; `ForeignKey` becomes a real Postgres FK. From `services/onesource360/campaigns/models.py`:

```python
class Campaign(models.Model):
    class Vertical(models.TextChoices):
        MEDICARE_ADVANTAGE = "medicare_advantage", "Medicare Advantage"
        # ...

    name = models.CharField(max_length=200)
    vertical = models.CharField(max_length=32, choices=Vertical.choices)
    target_cpl = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)

class DailyPerformanceRollup(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="rollups")
    date = models.DateField()
    spend = models.DecimalField(max_digits=10, decimal_places=2)
    # ...
    class Meta:
        unique_together = ("campaign", "date")
```

What that buys you in the shell:

```python
Campaign.objects.filter(status="active")
campaign.rollups.filter(date__gte="2026-08-01")  # related_name="rollups"
DailyPerformanceRollup.objects.create(campaign=campaign, date=..., spend=..., ...)
```

Django translates those into SQL. You still need to understand indexes, uniqueness, and FKs (`03-postgres-schema-design.md`), but day-to-day you think in objects.

### Design choices baked into these models

- **Vertical / Channel / Status as `TextChoices`, not lookup tables.** PLANNING.md §6 listed Vertical and Channel as models; they stayed as choices because they have no attributes of their own. Promoting them to tables wouldn't change anything the rest of the system does.
- **Cross-service `campaign_id` is a plain integer, not a ForeignKey.** SmartSpot360's `Spot`, Captivator360's `CreativeAsset`, and Maestro360's `CallEvent` all store `campaign_id` as `PositiveIntegerField`. They cannot FK to OneSource360's `Campaign` — different logical databases. See `03`.
- **`on_delete=models.CASCADE`** on rollups: delete a campaign and its daily rows go with it. Fine for a sim warehouse; think carefully before using CASCADE on anything with audit value in production.
- **`related_name="rollups"`** lets you write `campaign.rollups.all()` instead of the default `dailyperformancerollup_set`.

## Migrations — how schema changes ship

1. Edit `models.py`
2. `python manage.py makemigrations` — Django diffs models vs. prior migrations and writes a new file under `migrations/`
3. Commit that file
4. `python manage.py migrate` — applies pending migrations to the database

Migrations are the source of truth for schema history. Never "fix" production schema by hand and forget to capture it — the next `migrate` will fight you. In this repo, each service's `0001_initial.py` (and occasional follow-ups like Captivator360's `0002_remove_fatigue_score.py`) is applied on every Compose boot before seed.

## Settings that matter in this repo

Open any `services/*/config/settings.py`. The patterns that recur:

| Setting | What it does here |
|---|---|
| `INSTALLED_APPS` | Django builtins + `rest_framework` + `rest_framework_simplejwt` + `drf_spectacular` + `corsheaders` + the one domain app |
| `DATABASES["default"]` | Postgres via `DB_HOST` / `DB_NAME` / … env vars from Compose |
| `REST_FRAMEWORK` | Auth classes, default `AllowAny`, OpenAPI auto-schema |
| `SIMPLE_JWT` | Shared `JWT_SIGNING_KEY` across all four services |
| `CORS_ALLOW_ALL_ORIGINS` | Local demo: React-Admin on `:3000` can call `:8001`–`:8004` |
| `MIDDLEWARE` | `CorsMiddleware` must sit high in the list so preflight requests succeed |

`SECRET_KEY` and `DEBUG` are also env-driven with insecure defaults — acceptable for a local demo, not for the public internet.

## Django admin vs. the React console

Django admin (`/admin/` on each service, e.g. `http://localhost:8001/admin/`) is the framework's built-in CRUD for developers. The React-Admin console (`:3000`) is the product surface for the demo. Both can read the same Postgres data; admin talks to Django ORM directly, React talks over HTTP/DRF. You need a superuser before admin works:

```bash
docker compose exec onesource360 python manage.py createsuperuser
```

Seed already creates the API demo user `demo`/`demo` for JWT — that is *not* automatically a Django admin superuser.

## The request path in one sentence

Browser or MCP hits `http://onesource360:8000/api/campaigns/` → `config/urls.py` includes `campaigns.urls` under `/api/` → DRF router matches `CampaignViewSet` → serializer turns queryset rows into JSON → response. CORS middleware has already allowed the Origin. Auth middleware may attach a JWT user or a `ServicePrincipal` (see `07`), but GET viewsets in this demo don't require them.

## Key vocabulary

- **Project vs. app** — a project is the whole deployable unit (settings, URLs); an app is one bundle of related models/views/admin inside it. `onesource360` is a project; `campaigns` is an app inside it.
- **ORM** — object-relational mapper: Python classes ↔ tables, queryset API ↔ SQL.
- **Migration** — a generated Python file describing a schema change (`makemigrations` creates it, `migrate` applies it). Migrations are committed to the repo so schema history is reproducible.
- **Management command** — a custom script invoked as `python manage.py <name>`, living in `<app>/management/commands/`. `seed_data` is the one every sim service ships.
- **`TextChoices`** — Django's way of defining an enum-like set of valid string values for a `CharField`, without a separate lookup table.
- **`ForeignKey` / `related_name` / `on_delete`** — how tables relate inside one database; cascade behavior when the parent is deleted.
- **WSGI** — the sync Python web server interface Django's `runserver` and most traditional deployments use. (The MCP server uses ASGI/uvicorn instead — see `11`.)
- **Middleware** — hooks that wrap every request/response (CORS, CSRF, auth, security headers).

## Common pitfalls (learned in this repo)

1. **Assuming four apps in one project equals "independent systems."** It doesn't. Shared DB + shared imports = one system.
2. **Putting a ForeignKey to another service's model.** Impossible across logical databases; use a plain id and validate over HTTP if needed.
3. **Editing the database by hand and skipping migrations.** Next boot's `migrate` or a teammate's clone will diverge.
4. **Forgetting `0.0.0.0` in `runserver`.** Binding to `127.0.0.1` inside Docker makes the port unreachable from other containers / the host mapping.

## Try this yourself

With the stack running (`docker compose up`):

```bash
# ORM shell inside OneSource360
docker compose exec onesource360 python manage.py shell
>>> from campaigns.models import Campaign, DailyPerformanceRollup
>>> Campaign.objects.count()
>>> c = Campaign.objects.get(pk=1)
>>> c.rollups.order_by("-date")[:3]

# See applied migrations
docker compose exec onesource360 python manage.py showmigrations

# Compare: same data over HTTP (DRF)
curl -s http://localhost:8001/api/campaigns/1/ | python -m json.tool
```

Or open Django admin at `http://localhost:8001/admin/` after creating a superuser.

**Next:** `02-drf-rest-apis.md` — how those models become JSON APIs.
