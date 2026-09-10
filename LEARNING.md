# Agent360 — Learning Docs

Index for `docs/learning/` — topic docs written alongside the code, covering a stack that was largely new when this project started. See `PLANNING.md` §12.1 for the rationale.

**How to use this.** Each doc follows the same shape: what the technology is in plain English, why it’s used *here*, where it lives in this repo (real file paths), key vocabulary, and something to try yourself. Read **01 → 10** in order if you’re new to the stack; use **11 → 15** as deep dives on pieces that span or sit beside those core topics. Jump around freely if you’re not.

**Suggested path for a full-stack pass:** `01` Django → `02` DRF → `03` Postgres → `11` FastAPI/SQLAlchemy → `05` MCP → `07` Auth → `04` Celery → `13` Webhooks → `12` GraphQL → `06` Agents → `08` React-Admin → `09` Docker → `14` pytest → `15` CI → `10` Recap.

| # | Doc | Covers |
|---|---|---|
| 01 | [django-basics](docs/learning/01-django-basics.md) | Projects vs apps, ORM, migrations, settings, management commands, why four standalone Django projects |
| 02 | [drf-rest-apis](docs/learning/02-drf-rest-apis.md) | Serializers, viewsets vs `@api_view`, routers, browsable API, OpenAPI/Swagger, CORS |
| 03 | [postgres-schema-design](docs/learning/03-postgres-schema-design.md) | One Postgres server / five logical databases, in-service FKs vs cross-service plain ids, MCP audit tables, inspect |
| 04 | [celery-and-async](docs/learning/04-celery-and-async.md) | Redis broker, workers, beat; anomaly sweep reusing `get_performance_anomalies`; sync/async boundary |
| 05 | [mcp-servers](docs/learning/05-mcp-servers.md) | MCP + Streamable HTTP, tool registry, risk-scoring guardrail, approve/reject REST, RankPulse onboarding |
| 06 | [claude-code-as-agent](docs/learning/06-claude-code-as-agent.md) | Claude Code / Cursor as MCP clients, tool-call lifecycle, tool-list caching, vendor-agnostic proof |
| 07 | [auth-jwt-oauth2](docs/learning/07-auth-jwt-oauth2.md) | JWT vs `X-Service-Token`, `ServicePrincipal`, OpenAPI docs, local-demo security posture |
| 08 | [react-admin](docs/learning/08-react-admin.md) | React-Admin resources, Vite, MUI theme, hand-rolled `dataProvider`, Systems inspector, Agent Actions UI |
| 09 | [docker-compose](docs/learning/09-docker-compose.md) | Services, healthchecks, networking (localhost vs Docker DNS), volumes, YAML anchors, demo reset commands |
| 10 | [architecture-recap](docs/learning/10-architecture-recap.md) | Governed-gateway principle end to end; technology map; demo sequence; talking points |
| 11 | [fastapi-pydantic-sqlalchemy](docs/learning/11-fastapi-pydantic-sqlalchemy.md) | FastAPI/uvicorn, Pydantic/type-hint schemas, SQLAlchemy async + asyncpg, httpx, RankPulse |
| 12 | [graphql-strawberry](docs/learning/12-graphql-strawberry.md) | One Strawberry join query, GraphiQL, HTTP fan-out vs SQL join, when GraphQL earns its place |
| 13 | [webhooks-and-simulation](docs/learning/13-webhooks-and-simulation.md) | Per-service webhooks, Simulate Next Day, idempotent receivers, fan-out from the gateway |
| 14 | [testing-pytest](docs/learning/14-testing-pytest.md) | pytest suite layout, pure-function scoring tests, coverage honesty, how to run locally |
| 15 | [ci-github-actions](docs/learning/15-ci-github-actions.md) | GitHub Actions workflow, parallel jobs, what CI does and does not run |

**Also useful (not in this numbered series):** [`docs/for-marketers.md`](docs/for-marketers.md) (non-technical approval-queue guide), [`docs/field-notes.md`](docs/field-notes.md) (illustrated stakeholder walkthrough), [`PLANNING.md`](PLANNING.md) (design rationale and decisions log), [`README.md`](README.md) (setup and demo scenario).
