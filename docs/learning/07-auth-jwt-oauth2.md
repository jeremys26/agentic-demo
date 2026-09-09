# 07 — JWT and client-credentials auth

**Status**: complete. JWT issuance and a service token are live on all four sim services; the MCP server authenticates to them as a service, not as a logged-in user.

## What it is

Two different identities need to call these APIs:

1. **A person** — logging into a Django API to browse or mutate data. That's a **JWT** (JSON Web Token): the server checks username/password once, then hands back a signed token the client sends on later requests. This repo uses `djangorestframework-simplejwt` for that — `POST /api/token/` with `{"username":"demo","password":"demo"}` returns an access token.
2. **A machine** — the MCP server calling the four sim services on every tool call. That's a **client-credentials-style service token**: a shared secret the MCP server holds (`SERVICE_TOKEN`) and sends as `X-Service-Token`. It is *not* a full OAuth2 authorization server (the Decisions Log explicitly skipped that); it's the same pattern with proportionate machinery.

They are deliberately different headers. simplejwt looks at `Authorization: Bearer <jwt>` and **raises** if that value isn't a JWT. A service token in `Authorization` would 401 every MCP call. `X-Service-Token` keeps the two authenticators from colliding.

## Why this piece of the stack is used here

`PLANNING.md` §7 puts governance at the gateway, but the four Django services still shouldn't accept unauthenticated writes. Webhooks ("Simulate Next Day") and mutations (`POST /api/recommendations/`, creative refresh) require either a valid JWT or the service token. **GET stays `AllowAny`** so the local React-Admin console and Docker healthchecks don't need a login wall — this is a standup demo, not a production lockdown. Tightening reads to `IsAuthenticated` is a one-line permission change once you want that.

## Where it lives in this repo

| File | Role |
|---|---|
| `services/*/config/authentication.py` | `ServiceTokenAuthentication` — identical copy in each service (no shared package; the services don't import each other) |
| `services/*/config/settings.py` | `SIMPLE_JWT` (shared `JWT_SIGNING_KEY` so a token issued by one service verifies on the others), DRF auth classes, `drf_spectacular` schema |
| `services/*/config/urls.py` | `/health/`, `/api/token/`, `/api/token/refresh/`, `/api/schema/`, `/api/docs/` |
| `mcp_server/http_client.py` | Every outbound MCP → Django call attaches `X-Service-Token` when `SERVICE_TOKEN` is set |
| `docker-compose.yml` | `SERVICE_TOKEN` + `JWT_SIGNING_KEY` on the four Django services; `SERVICE_TOKEN` on `mcp_server` and `celery_worker` |
| Seed commands | Create user `demo` / password `demo` |

Write views (`@api_view(["POST"])` webhooks and mutations) stack `@authentication_classes` + `@permission_classes([IsAuthenticated])`. GET viewsets keep the default `AllowAny`. The React-Admin console does not send a JWT — it relies on those open GETs, and talks to the MCP server's approve/sweep/simulate endpoints without a token. JWT is there for API clients (and for tightening reads later); it is not a login wall on the local demo UI.

## Key vocabulary

- **JWT** — a signed blob that says "this user authenticated at this time." Stateless: the receiving service verifies the signature with `JWT_SIGNING_KEY` instead of looking up a session.
- **Client credentials** — a service authenticating as itself, not on behalf of a user. Here: `SERVICE_TOKEN` via `X-Service-Token`.
- **`IsAuthenticated`** — DRF permission that accepts any principal with `is_authenticated = True`, including the MCP server's `ServicePrincipal`.

## Try this yourself

```bash
# User JWT (any of the four services; they share a signing key)
curl -s http://localhost:8001/api/token/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"demo"}'

# Webhook without a token should 403
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8001/api/webhooks/daily-performance/ \
  -H 'Content-Type: application/json' -d '{"rollups":[]}'

# Same webhook with the service token (MCP does this)
curl -s -X POST http://localhost:8001/api/webhooks/daily-performance/ \
  -H 'Content-Type: application/json' \
  -H 'X-Service-Token: agent360-service' \
  -d '{"rollups":[]}'
```

OpenAPI for each service: `http://localhost:8001/api/docs/` (8002 SmartSpot, 8003 Captivator, 8004 Maestro).
