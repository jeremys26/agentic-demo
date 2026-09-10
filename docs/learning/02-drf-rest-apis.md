# 02 — DRF (Django REST Framework)

**Status**: complete. Covers the four services’ DRF APIs, plus webhook receivers and OpenAPI docs. Auth details live in `07-auth-jwt-oauth2.md`; schema design in `03`.

## What it is

Django REST Framework (DRF) sits on top of Django and turns models into JSON APIs. Three pieces do most of the work:

1. **Serializers** — convert model instances ↔ JSON, and validate incoming data
2. **Viewsets / views** — decide what happens for GET/POST/… on a URL
3. **Routers** — auto-generate URL patterns for a viewset (`/spots/`, `/spots/1/`, …)

DRF also ships a **browsable API** (HTML forms in the browser for any endpoint), pagination helpers, permission classes, and — via **drf-spectacular** in this repo — OpenAPI schema + Swagger UI.

Without DRF you'd hand-write `json.dumps`, status codes, and validation for every endpoint. With DRF you declare the shape once and reuse it.

## Why this piece of the stack is used here

Every one of the four sim services needs a REST API for two different clients:

- the **MCP server** (machine-to-machine, proxying tool calls with `X-Service-Token`)
- **React-Admin** (browser, mostly unauthenticated GETs in this local demo)

DRF gives both a consistent JSON contract without writing serialization/routing code four times by hand. The walking-skeleton sequencing (`PLANNING.md` §14) proved the pattern once on OneSource360, then copied it to SmartSpot360, Captivator360, and Maestro360.

## Where it lives in this repo

Each service follows the identical shape — `<service>/<app>/{models,serializers,views,urls}.py`:

| Service | App | Serializers | Notable views |
|---|---|---|---|
| OneSource360-sim | `campaigns` | `CampaignSerializer`, `DailyPerformanceRollupSerializer` | `performance` — aggregates daily rollups into spend/leads/cpl totals + variance vs. `target_cpl`; `inspect_tables` (`GET /api/inspect/`) — live Postgres snapshot for the Systems UI; `daily_performance_webhook` |
| SmartSpot360-sim | `spots` | `SpotSerializer`, `SpotDetailSerializer` (nests performance), `BudgetRecommendationSerializer` | `recommend_budget` / `apply_recommendation` — create a ranked allocation, then apply it (the MCP write tool calls apply after the guardrail); spot webhook |
| Captivator360-sim | `creatives` | `CreativeAssetSerializer`, `CreativePerformanceDailySerializer`, `CreativeRefreshRequestSerializer` | `declining_creatives` — CTR drop vs each creative's own first-week average; `refresh_request` + `resolve_refresh_request`; creative-metrics webhook |
| Maestro360-sim | `calls` | `CallEventSerializer`, `ClientAgentPoolSerializer`, `RoutingRuleSerializer` | `call_summary` — pool-distribution breakdown for the compliance angle; call-events webhook |

### Pattern A — `ReadOnlyModelViewSet` + `DefaultRouter`

For anything that's just list/retrieve (campaigns, spots, creatives, routing rules):

```python
# services/smartspot360/spots/urls.py (shape)
router = DefaultRouter()
router.register("spots", SpotViewSet, basename="spot")
urlpatterns = [
    path("", include(router.urls)),
    path("recommendations/", recommend_budget),
    # ...
]
```

DRF generates:

| Method | Path | ViewSet action |
|---|---|---|
| GET | `/api/spots/` | `list` |
| GET | `/api/spots/{id}/` | `retrieve` |

`ReadOnlyModelViewSet` deliberately omits create/update/delete — the console and agent shouldn't invent spots via generic CRUD; writes go through purpose-built endpoints.

### Pattern B — `@api_view` function-based views

For anything that doesn't map cleanly to CRUD on one model:

- aggregations (`performance`, `call_summary`)
- nested detail (`spot_performance`, `creative_performance`)
- mutations (`recommend_budget`, `apply_recommendation`, `refresh_request`)
- webhooks (`POST /api/webhooks/...`)
- inspect (`GET /api/inspect/`)

These are wired into `urlpatterns` with `path(...)` directly. Example shape:

```python
@api_view(["GET"])
def performance(request):
    campaign_id = request.query_params.get("campaign_id")
    # ... queryset + aggregate ...
    return Response({...})

@api_view(["POST"])
@authentication_classes([ServiceTokenAuthentication, JWTAuthentication])
@permission_classes([IsAuthenticated])
def daily_performance_webhook(request):
    # ... validate + upsert ...
    return Response({...})
```

Writes stack authentication + `IsAuthenticated`. GETs keep the project default `AllowAny` (`07-auth-jwt-oauth2.md`).

## Serializers — the contract

`ModelSerializer` auto-maps model fields, but this repo still lists `fields = [...]` explicitly rather than `"__all__"`. Reason: adding a sensitive field to a model later must not silently expose it over the API.

Nested serializers appear where a detail view should embed related rows (e.g. SmartSpot360's spot + its `SpotPerformance`). List endpoints usually stay flat for speed and simplicity.

Validation: if a POST body fails serializer validation, DRF returns `400` with field errors — the webhook receivers and recommendation endpoints rely on that instead of ad-hoc `if "spend" not in body` checks.

## Query params, filtering, and "no shared pagination convention"

DRF *can* do pagination, filter backends, and ordering out of the box. This repo mostly doesn't standardize them across services:

- list endpoints often return the full (small) collection
- filtering is hand-rolled via `request.query_params` (`?campaign_id=1`)
- the React `dataProvider` paginates client-side (`08-react-admin.md`)

That's a deliberate demo trade-off, not "DRF can't paginate." If these APIs grew, you'd add `PageNumberPagination` (or cursor pagination) and teach the frontend to send `?page=` — and then `combineDataProviders` becomes more attractive.

## OpenAPI / Swagger (drf-spectacular)

Each service's `config/urls.py` mounts:

| Path | What |
|---|---|
| `/api/schema/` | Raw OpenAPI schema |
| `/api/docs/` | Swagger UI |

Settings wire `"DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema"` and a per-service `SPECTACULAR_SETTINGS` title. This is the **machine-readable API reference** — distinct from the pedagogical docs in `docs/learning/`. The MCP server's `/tools` endpoint is the analogous idea for tools, not REST resources.

Try: `http://localhost:8001/api/docs/` (8002 SmartSpot, 8003 Captivator, 8004 Maestro).

## CORS — why the browser needs help

React-Admin runs on `http://localhost:3000`. The APIs run on `8001`–`8004`. Browsers treat that as cross-origin and send a preflight `OPTIONS` request. `django-cors-headers` answers it; `CORS_ALLOW_ALL_ORIGINS = True` is fine for a local demo. `CORS_ALLOW_HEADERS` includes `x-service-token` so a browser-based tool *could* send the service header (the console generally doesn't).

The MCP server uses FastAPI's `CORSMiddleware` for the same reason (`11`).

## How an MCP tool call becomes a DRF response

1. Claude Code calls MCP tool `get_campaign_performance`
2. `mcp_server/tools/onesource360.py` uses `httpx` → `GET http://onesource360:8000/api/performance/?campaign_id=1` with `X-Service-Token`
3. OneSource360's DRF view aggregates rollups, returns JSON
4. The tool returns that payload to the agent; `wrap_read_tool` logs an `AgentToolCall`

The Systems UI reconstructs step 2–3 from the catalog + logged arguments (`frontend/src/trace.js`). Understanding DRF is what makes that reconstruction readable.

## Key vocabulary

- **Serializer** — translation layer between a Django model instance and JSON. Validates input on write.
- **ViewSet vs. view** — a viewset bundles multiple related endpoints (list, retrieve, …) behind one class; a plain `@api_view` function handles exactly one URL. This repo uses viewsets only where CRUD fits.
- **Router** — maps a viewset to URL patterns automatically (`DefaultRouter`).
- **Browsable API** — DRF's HTML UI for the same JSON endpoints; great for exploring without curl.
- **Permission class** — e.g. `AllowAny`, `IsAuthenticated`. Decides *whether* an authenticated principal may proceed.
- **Authentication class** — e.g. JWT, `ServiceTokenAuthentication`. Decides *who* the request is.
- **OpenAPI / Swagger** — standard description of REST endpoints; Swagger UI is the interactive docs page.
- **`get_object_or_404`** — returns a clean 404 instead of an unhandled exception when an id doesn't exist.

## Try this yourself

```bash
# Browsable API (open in a browser)
open http://localhost:8003/api/creatives/?campaign_id=1
open http://localhost:8002/api/docs/

# Aggregation endpoint the agent uses
curl -s 'http://localhost:8001/api/performance/?campaign_id=1' | python -m json.tool | head -40

# Write without auth should fail
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8001/api/webhooks/daily-performance/ \
  -H 'Content-Type: application/json' -d '{"rollups":[]}'
```

**Next:** `03-postgres-schema-design.md` for how the tables behind these APIs are isolated per service.
