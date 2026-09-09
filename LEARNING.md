# Agent360 — Learning Docs

Index for `docs/learning/` — topic docs written alongside the code, covering a stack that was largely new when this project started (Django, DRF, Celery, MCP server development, React-Admin). See `PLANNING.md` §12.1 for the rationale.

**How to use this.** Each doc follows the same shape: what the piece of tech is in plain English, why it’s used *here specifically*, where it lives in this repo (real file paths), key vocabulary, and sometimes something to try yourself. Read them in order if you’re new to this stack; jump to one topic if you’re not.

| # | Doc | Covers |
|---|---|---|
| 01 | [django-basics](docs/learning/01-django-basics.md) | Models, ORM, migrations, settings, what a Django project/app is, why this repo runs four standalone Django projects instead of one |
| 02 | [drf-rest-apis](docs/learning/02-drf-rest-apis.md) | Serializers, viewsets, routers — how DRF sits on top of Django, across all four services |
| 03 | [postgres-schema-design](docs/learning/03-postgres-schema-design.md) | One Postgres server / five logical databases, in-service FKs vs. cross-service plain-id references, MCP audit tables |
| 04 | [celery-and-async](docs/learning/04-celery-and-async.md) | Brokers, workers, beat scheduler; the deterministic anomaly sweep that reuses the MCP server’s own `get_performance_anomalies` code path |
| 05 | [mcp-servers](docs/learning/05-mcp-servers.md) | What MCP is, the tool registry, the risk-scoring guardrail (scoring, policy, engine), the `/agent-actions/{id}/approve`\|`/reject` endpoints, and the RankPulse-sim live fifth-platform onboarding demo |
| 06 | [claude-code-as-agent](docs/learning/06-claude-code-as-agent.md) | How Claude Code connects to a local MCP server, what happens on a tool call, MCP tool-list caching, and the Cursor proof point |
| 07 | [auth-jwt-oauth2](docs/learning/07-auth-jwt-oauth2.md) | JWT for API clients, `X-Service-Token` for MCP → Django, OpenAPI per service; local console GETs stay open |
| 08 | [react-admin](docs/learning/08-react-admin.md) | Resources, top-bar layout, the custom hand-rolled `dataProvider` (and why it skips `combineDataProviders`), the Agent Actions approval-queue view |
| 09 | [docker-compose](docs/learning/09-docker-compose.md) | Networking independent services together in one Compose file: healthchecks, five logical databases, Celery/Redis, RankPulse-sim |
| 10 | [architecture-recap](docs/learning/10-architecture-recap.md) | The governed-gateway principle end to end; presentation talking points |
