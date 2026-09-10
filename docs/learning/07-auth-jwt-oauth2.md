# 07 — JWT and Service-Token Auth

**Status**: complete. JWT issuance and a service token are live on all four sim services; the MCP server authenticates to them as a service. OpenAPI is included here as the documented API surface those credentials protect.

## What it is

Two different *kinds of caller* need these APIs:

### 1. A person (or user-facing API client) → JWT

**JWT (JSON Web Token)**: after username/password succeed once, the server returns a signed token. Later requests send `Authorization: Bearer <token>`. The server verifies the signature — no session row required (stateless).

This repo uses **`djangorestframework-simplejwt`**:

```bash
POST /api/token/
{"username":"demo","password":"demo"}
→ { "access": "...", "refresh": "..." }
```

### 2. A machine (MCP gateway) → service token

**Client-credentials-style service token**: a shared secret (`SERVICE_TOKEN`) the MCP server sends as **`X-Service-Token`**, not as a Bearer JWT.

They use different headers on purpose. simplejwt looks at `Authorization: Bearer …` and **raises** if that value isn't a JWT. Putting the service secret in `Authorization` would 401 every MCP call. `X-Service-Token` keeps the authenticators from colliding.

## Why this piece of the stack is used here

Governance lives at the gateway (`05`), but the four Django services still shouldn't accept unauthenticated **writes**. Webhooks (Simulate Next Day) and mutations (`POST /recommendations/`, creative refresh) require either a valid JWT or the service token.

**GET stays `AllowAny`** so:

- React-Admin can load without a login wall
- Docker healthchecks (`GET /health/`) work without secrets

This is a standup demo posture, not a production lockdown. Approve/reject/sweep/simulate on the MCP server are likewise unauthenticated local-demo REST.

## Where it lives in this repo

| File | Role |
|---|---|
| `services/*/config/authentication.py` | `ServiceTokenAuthentication` + `ServicePrincipal` — identical copy per service (no shared package; services don't import each other) |
| `services/*/config/settings.py` | `SIMPLE_JWT` with shared `JWT_SIGNING_KEY`; DRF `DEFAULT_AUTHENTICATION_CLASSES`; `drf_spectacular` |
| `services/*/config/urls.py` | `/health/`, `/api/token/`, `/api/token/refresh/`, `/api/schema/`, `/api/docs/` |
| `mcp_server/http_client.py` | Attaches `X-Service-Token` when `SERVICE_TOKEN` is set |
| `docker-compose.yml` | `x-service-auth` anchor: `SERVICE_TOKEN` + `JWT_SIGNING_KEY` on Django services; `SERVICE_TOKEN` on `mcp_server` and `celery_worker` |
| Seed commands | Create user `demo` / password `demo` |

### How DRF applies it

```python
# settings — authentication tries these in order
"DEFAULT_AUTHENTICATION_CLASSES": [
    "config.authentication.ServiceTokenAuthentication",
    "rest_framework_simplejwt.authentication.JWTAuthentication",
],
"DEFAULT_PERMISSION_CLASSES": [
    "rest_framework.permissions.AllowAny",  # default for GETs
],
```

Write views opt into enforcement:

```python
@api_view(["POST"])
@authentication_classes([ServiceTokenAuthentication, JWTAuthentication])
@permission_classes([IsAuthenticated])
def daily_performance_webhook(request):
    ...
```

`IsAuthenticated` accepts any principal with `is_authenticated = True` — including `ServicePrincipal` (not a Django `User`).

### Shared JWT signing key

All four services share `JWT_SIGNING_KEY` via Compose. A token issued by OneSource360 verifies on SmartSpot360. Convenient for a demo; in production each service (or an IdP) would usually own issuance more carefully.

## OpenAPI as part of the auth story

Protected and public endpoints are discoverable at `/api/docs/` (Swagger UI) and `/api/schema/` (raw OpenAPI). That is the **reference** docs track — pedagogical learning docs teach; OpenAPI describes the wire contract. `drf-spectacular` generates both from the same views/serializers.

| Port | Service | Docs |
|---|---|---|
| 8001 | OneSource360 | http://localhost:8001/api/docs/ |
| 8002 | SmartSpot360 | http://localhost:8002/api/docs/ |
| 8003 | Captivator360 | http://localhost:8003/api/docs/ |
| 8004 | Maestro360 | http://localhost:8004/api/docs/ |

## What the React console does (and doesn't)

The local console does **not** log in and does **not** send JWTs. It relies on open GETs. Approve/reject call the MCP server's plain REST without a token. JWT exists so you can exercise real user-style API access with curl or another client; it is not a UI login wall.

## Security boundaries (honest for a demo)

| Path | Auth |
|---|---|
| Django GET APIs + inspect | Open |
| Django POST webhooks / mutations | JWT or `X-Service-Token` |
| MCP `/mcp` tools | Relies on network locality + client permission prompts (no gateway API key in this demo) |
| MCP approve / sweep / simulate | Open (local demo) |

Production would add auth on the gateway's admin routes and likely mTLS or stronger service identity. The patterns here are real; the perimeter is intentionally porous for laptop demos.

## Key vocabulary

- **JWT** — signed blob asserting authentication; verified with a key, typically Bearer.
- **Access vs refresh token** — short-lived access; refresh obtains a new access token (`/api/token/refresh/`).
- **Client credentials** — service authenticates as itself, not on behalf of a user.
- **`ServicePrincipal`** — non-User object DRF treats as authenticated for permission checks.
- **`IsAuthenticated` / `AllowAny`** — permission classes (authorization), distinct from authentication classes (identity).
- **CORS vs auth** — CORS is browser cross-origin policy; it is not authentication. Both are configured; they solve different problems.

## Try this yourself

```bash
# Issue a user JWT (any of the four; shared signing key)
curl -s http://localhost:8001/api/token/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"demo"}'

# Webhook without credentials → 401/403
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  http://localhost:8001/api/webhooks/daily-performance/ \
  -H 'Content-Type: application/json' -d '{"rollups":[]}'

# Same webhook as the MCP server
curl -s -X POST http://localhost:8001/api/webhooks/daily-performance/ \
  -H 'Content-Type: application/json' \
  -H 'X-Service-Token: agent360-service' \
  -d '{"rollups":[]}'
```

**Next:** `08-react-admin.md` for the UI that consumes the open GETs and the gateway's approval API.
