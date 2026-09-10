# 11 — FastAPI, Pydantic, SQLAlchemy, and httpx

**Status**: complete. Covers the MCP server's Python web stack and RankPulse-sim. MCP protocol specifics: `05`. Auth headers on outbound calls: `07`.

## What it is

Four libraries that show up together in modern async Python services:

| Library | Role in Agent360 |
|---|---|
| **FastAPI** | Web framework for the MCP gateway (`mcp_server/main.py`) and RankPulse-sim |
| **Uvicorn** | ASGI server that runs FastAPI |
| **Pydantic** | Data validation / settings; also what the MCP SDK uses to build tool input schemas from type hints |
| **SQLAlchemy 2.0 + asyncpg** | Async ORM for the gateway's audit tables (not Django) |
| **httpx** | Async HTTP client for gateway → sim REST calls |

Django is sync-first and batteries-included (admin, migrations, auth). FastAPI is async-first and minimal — you pick your ORM, migrations, and auth. The gateway chose FastAPI because it hosts the MCP Streamable HTTP app, GraphQL, and a pile of plain REST admin routes in one async process. RankPulse chose FastAPI to dramatize "acquisition brings its own stack."

## Why this piece of the stack is used here

- MCP Python SDK integrates naturally with FastAPI / Starlette-style ASGI apps
- Async `httpx` fans out to four sims without blocking a thread per call
- Gateway audit state doesn't need Django's full stack — SQLAlchemy `create_all` is enough for a demo
- RankPulse as non-Django proves the registry doesn't care what backs a tool

## FastAPI application shape (`mcp_server/main.py`)

```python
app = FastAPI(title="Agent360 MCP Server", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
app.include_router(graphql_app, prefix="/graphql")

@app.get("/health")
def health():
    return {"status": "ok"}
```

### Lifespan

`@asynccontextmanager async def lifespan(app)` runs **startup** before requests and **shutdown** after:

1. `init_db()` — create audit tables if needed
2. `reset_audit_tables()` — truncate demo log
3. `run_anomaly_sweep()` — flag campaign 1 immediately
4. `async with mcp.session_manager.run()` — MCP sessions live for the app lifetime

This replaces older `@app.on_event("startup")` patterns.

### Routes vs MCP mount

Plain REST handlers (`/tools`, `/agent-actions`, …) are normal FastAPI endpoints. The MCP protocol app is mounted at `/mcp`. Same process, two surfaces: browsers and React-Admin use REST; Claude Code uses MCP.

### RankPulse (`services/rankpulse_sim/main.py`)

Single-file FastAPI app: `/health`, organic-performance style GETs, in-memory data, no Postgres. Deliberately small. The interesting part is `mcp_server/tools/rankpulse.py` wrapping it like any other tool once imported.

## Pydantic and type hints

FastAPI uses type annotations on endpoint parameters to validate/coerce request data and generate OpenAPI for *its* routes. Separately, the MCP SDK inspects tool function signatures (`campaign_id: int`, `start_date: str | None = None`, …) and builds **tool** JSON Schemas — also Pydantic under the hood.

You rarely import Pydantic directly in this repo's tool modules; you write typed Python and the frameworks do the rest. When `wrap_read_tool` preserves `__wrapped__` (`05`), it is preserving those annotations for schema generation.

## SQLAlchemy async (gateway DB)

```text
guardrails/models.py  → DeclarativeBase, Mapped columns
guardrails/db.py      → create_async_engine (postgresql+asyncpg://...), async_sessionmaker
```

Patterns to recognize:

- `AsyncSession` + `await session.execute(select(...))`
- `await session.commit()`
- `Base.metadata.create_all` on startup (no Alembic in this demo)
- `reset_audit_tables()` uses `TRUNCATE` for boot hygiene

Django ORM and SQLAlchemy are different ORMs talking to the **same Postgres server**, different logical databases (`03`). Do not import Django models into the MCP server.

## httpx — the glue

`mcp_server/http_client.py`:

```python
def service_client(**kwargs) -> httpx.AsyncClient:
    headers = {**service_headers(), **kwargs.pop("headers", {})}
    return httpx.AsyncClient(timeout=timeout, headers=headers, **kwargs)
```

`service_headers()` adds `X-Service-Token` when set. Every tool, the GraphQL join, the simulator, and scoring gatherers share this client factory so auth cannot be forgotten on one path.

Typical usage:

```python
async with service_client() as client:
    resp = await client.get(f"{ONESOURCE360_URL}/api/campaigns/{campaign_id}/")
    resp.raise_for_status()
    return resp.json()
```

Inside Compose, URLs look like `http://onesource360:8000`. From your Mac browser they look like `http://localhost:8001`. The gateway always uses Docker DNS names via env vars in Compose.

## ASGI vs WSGI (one-liner)

| | Django sims | MCP / RankPulse |
|---|---|---|
| Interface | WSGI (`runserver`) | ASGI (uvicorn) |
| Concurrency model | Sync request threads | Async event loop |

Both speak HTTP. The agent never cares.

## Key vocabulary

- **ASGI** — async Python web server interface (uvicorn speaks it).
- **Lifespan** — startup/shutdown hook for FastAPI apps.
- **Dependency injection** — FastAPI `Depends(...)` pattern (used lightly here; know it exists).
- **`AsyncClient`** — httpx's async HTTP client; prefer `async with` for cleanup.
- **`create_async_engine`** — SQLAlchemy entry point for async DB I/O via asyncpg.
- **OpenAPI (FastAPI)** — auto docs at `/docs` on pure FastAPI apps; RankPulse has this. The gateway leans on custom `/tools` + GraphQL + MCP for discovery instead of emphasizing Swagger.

## Try this yourself

```bash
curl -s http://localhost:8100/health
curl -s http://localhost:8005/health
# RankPulse's own OpenAPI UI (if enabled by default FastAPI):
open http://localhost:8005/docs

# Compare: gateway tools list (custom REST, not Swagger)
curl -s http://localhost:8100/tools | python -m json.tool | head -40
```

Read `http_client.py` then one tool module end to end — that's the whole outbound pattern.

**Related:** `12-graphql-strawberry.md` (also FastAPI-mounted), `05` (MCP), `13` (simulator httpx fan-out).
