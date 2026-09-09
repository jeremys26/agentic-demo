# 02 — DRF (Django REST Framework)

**Status**: complete. Covers the four services’ DRF APIs, plus the webhook receivers and OpenAPI docs. JWT/service-token write protection is covered in `07-auth-jwt-oauth2.md`.

## What it is

Django REST Framework (DRF) sits on top of Django and turns models into JSON APIs. Three pieces do most of the work: **serializers** (convert model instances ↔ JSON, and validate incoming data), **viewsets** (bundle up the standard list/retrieve/create/update/delete behavior for a model), and **routers** (auto-generate URL patterns for a viewset, so you don't hand-write `/spots/`, `/spots/1/`, etc.).

## Why this piece of the stack is used here

Every one of the four sim services needs a REST API for two different clients: the MCP server (machine-to-machine, proxying tool calls) and React-Admin (human-facing). DRF gives both a consistent JSON contract without writing serialization/routing code four times by hand.

## Where it lives in this repo

Each service follows the identical shape — `<service>/<app>/{models,serializers,views,urls}.py` — a deliberate outcome of the walking-skeleton sequencing principle (`PLANNING.md` §14): prove the pattern once with OneSource360-sim, then repeat it three times rather than inventing a new shape per service.

| Service | App | Serializers | Notable views |
|---|---|---|---|
| OneSource360-sim | `campaigns` | `CampaignSerializer`, `DailyPerformanceRollupSerializer` | `performance` — aggregates daily rollups into spend/leads/cpl totals + variance vs. `target_cpl`; `inspect_tables` (`GET /api/inspect/`) — live Postgres snapshot for the Systems UI |
| SmartSpot360-sim | `spots` | `SpotSerializer`, `SpotDetailSerializer` (nests performance), `BudgetRecommendationSerializer` | `recommend_budget` / `apply_recommendation` — create a ranked allocation, then apply it (the MCP write tool calls apply after the guardrail) |
| Captivator360-sim | `creatives` | `CreativeAssetSerializer`, `CreativePerformanceDailySerializer`, `CreativeRefreshRequestSerializer` | `declining_creatives` — filters by CTR drop vs each creative's own first-week average (default 20%); `refresh_request` + `resolve_refresh_request` is the two-step write |
| Maestro360-sim | `calls` | `CallEventSerializer`, `ClientAgentPoolSerializer`, `RoutingRuleSerializer` | `call_summary` — the pool-distribution breakdown the demo scenario's compliance angle depends on |

Two patterns worth naming explicitly, since they're used consistently across all four services:

- **`ReadOnlyModelViewSet` + `DefaultRouter`** for anything that's just list/retrieve (campaigns, spots, creatives, routing rules) — e.g. `services/smartspot360/spots/urls.py` registers `SpotViewSet` under `spots/` and DRF generates `GET /api/spots/` and `GET /api/spots/{id}/` automatically.
- **`@api_view(["GET"])` / `@api_view(["POST"])` function-based views** for anything that doesn't map cleanly to CRUD on one model — aggregation endpoints (`performance`, `call_summary`), nested-detail endpoints (`spot_performance`, `creative_performance`), mutations (`recommend_budget`, `apply_recommendation`, `refresh_request`, `resolve_refresh_request`), and each service's webhook receiver. These are wired into `urlpatterns` directly rather than through a router.

## Key vocabulary

- **Serializer** — the translation layer between a Django model instance and JSON. `ModelSerializer` (used everywhere in this repo) auto-generates fields from the model, but the `fields` list is still written explicitly per serializer rather than using `"__all__"`, so adding a sensitive field to a model later doesn't silently expose it over the API.
- **ViewSet vs. view** — a viewset bundles multiple related endpoints (list, retrieve, etc.) behind one class; a plain `@api_view` function handles exactly one URL. This repo uses viewsets only where the built-in CRUD shape actually fits, and plain views everywhere else, rather than forcing every endpoint into a viewset.
- **Router** — maps a viewset to URL patterns automatically. `DefaultRouter().register("spots", SpotViewSet)` is what produces `/api/spots/` and `/api/spots/<pk>/` without writing `path()` calls by hand.
- **`get_object_or_404`** — DRF/Django shortcut used in the detail views (`spot_performance`, `creative_performance`, `refresh_request`) to return a clean 404 instead of an unhandled exception when an id doesn't exist.

## Try this yourself

Every service exposes Django's browsable API — visit any endpoint directly in a browser (e.g. `http://localhost:8003/api/creatives/?campaign_id=1`) instead of curling it, and DRF renders an interactive HTML form for it, including one for the `recommend_budget` POST endpoint at `http://localhost:8002/api/recommendations/`.
