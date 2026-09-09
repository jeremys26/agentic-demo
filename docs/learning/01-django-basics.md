# 01 — Django Basics

**Status**: complete. All four sim platforms are standalone Django projects; this doc covers the shared Django patterns they use.

## What it is

Django is a Python web framework. A **project** is the overall configuration — settings, URL routing, WSGI entrypoint. An **app** is a self-contained bundle of functionality (models, views, admin config) that lives inside a project; a project can hold several apps. Django's **ORM** (Object-Relational Mapper) lets you define database tables as Python classes (`models.py`) instead of writing SQL directly, and **migrations** are auto-generated, version-controlled files that translate changes to those classes into actual database schema changes.

## Why this piece of the stack is used here

Django + its ORM is the backbone of every "sim platform" service in Agent360 (`PLANNING.md` §6) — a fast way to get a real, migration-backed Postgres schema and a browsable admin UI without hand-rolling either.

**Why four separate Django projects instead of one project with four apps**: Agent360's whole pitch is "these systems didn't originally talk to each other, and Agent360 is the thing that connects them." If all four platforms lived as apps inside one Django project sharing one settings file and one database, that claim wouldn't survive scrutiny — it would just be one app with internal modules importing each other directly. Running `django-admin startproject` four separate times, each with its own `manage.py`, `settings.py`, and (per `docker-compose.yml`) its own Postgres database, makes the "independent systems, connected over HTTP only" claim literally true. See `PLANNING.md` §5.

RankPulse-sim (`services/rankpulse_sim`) is deliberately *not* Django — it's a one-file FastAPI stand-in for a newly-acquired platform that brought its own stack. That's the point of the fifth-platform demo, not a fifth copy of this pattern.

## Where it lives in this repo

Each of `services/onesource360`, `services/smartspot360`, `services/captivator360`, and `services/maestro360` is a full Django project:

| Path | Role |
|---|---|
| `<service>/manage.py` | Command-line entrypoint (`migrate`, `runserver`, `seed_data`) |
| `<service>/config/settings.py` | Installed apps, Postgres connection from env vars, CORS |
| `<service>/config/urls.py` | Top-level routing; `/api/` delegates to the service's one app |
| `<service>/<app>/models.py` | That platform's tables |
| `<service>/<app>/management/commands/seed_data.py` | `python manage.py seed_data` — the PLANNING.md §9 scenario |

OneSource360-sim's app is `campaigns` (`Campaign`, `DailyPerformanceRollup`). Vertical and Channel stayed as Django `TextChoices` rather than becoming their own lookup tables — a walking-skeleton shortcut that earned its keep: those values are labels, not entities with their own attributes, and promoting them to models wouldn't have changed anything the rest of the system does. Cross-service campaign references in the other three platforms are plain integer `campaign_id` fields, not ForeignKeys, because they don't share a database (`docs/learning/03-postgres-schema-design.md`).

## Key vocabulary

- **Project vs. app** — a project is the whole deployable unit (settings, URLs); an app is one bundle of related models/views/admin inside it. `onesource360` is a project; `campaigns` is an app inside it.
- **Migration** — a generated Python file describing a schema change (`makemigrations` creates it, `migrate` applies it). Migrations are committed to the repo so schema history is reproducible.
- **Management command** — a custom script invoked as `python manage.py <name>`, living in `<app>/management/commands/`. `seed_data` is the one every sim service ships.
- **`TextChoices`** — Django's way of defining an enum-like set of valid string values for a `CharField`, without a separate lookup table.

## Try this yourself

With the stack running (`docker compose up`):

```bash
docker compose exec onesource360 python manage.py shell
>>> from campaigns.models import Campaign
>>> Campaign.objects.all()
```

Or open Django admin at `http://localhost:8001/admin/` after `docker compose exec onesource360 python manage.py createsuperuser`.
