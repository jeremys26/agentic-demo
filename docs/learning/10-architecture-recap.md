# 10 — Architecture Recap

**Status**: complete. End-to-end synthesis and presentation talking points (`PLANNING.md` §14). Deep dives on individual technologies: docs `01`–`09` and `11`–`15`.

## The governed-gateway principle, end to end

Everything in this repo supports one sentence:

> An agent's autonomy should be calibrated to risk — not gated behind a blanket "ask a human every time" — and that governance should live at the **tool layer**, not the agent layer, so it does not care which vendor's agent is asking.

Tracing one request through the stack:

1. **Four independent systems, actually independent.** `services/{onesource360,smartspot360,captivator360,maestro360}` — separate Django projects, separate logical databases, HTTP-only. That makes "these systems didn't talk to each other, and this project connects them" a true claim (`PLANNING.md` §5; `01`, `03`, `09`).
2. **One gateway, not four bespoke integrations.** `mcp_server/` is the only component that talks to all four. The tool registry is config-driven; RankPulse proves a fifth platform joins with one import (`05`).
3. **Every tool call is logged.** `AgentToolCall` captures reads and writes regardless of outcome — Tool Calls is a complete transcript, not a highlight reel.
4. **Write tools never execute unconditionally.** `compute_score` → `route` → auto-execute / pending / blocked, plus a score-independent hard cap (`05`, `14`).
5. **The three outcomes are structurally different.** Auto-execute snapshots pre-action state and writes. Pending creates a queue row and returns without executing. Blocked logs and refuses. Live-verified on campaign 1.
6. **The dial belongs to the business.** Thresholds are env-overridable policy, not agent whim.
7. **Scheduled monitoring and agent investigation share one code path.** Celery calls the same `get_performance_anomalies()` (`04`). Boot wipes audit tables then re-sweeps for demo hygiene.
8. **Live data joins through each service's own door.** Simulate Next Day POSTs four webhooks with the service token — no gateway backdoor into four databases (`07`, `13`).
9. **Nothing is Claude-specific.** Claude Code and Cursor are MCP clients of the same server (`06`).
10. **Humans see a console that tells the truth.** React-Admin routes across five backends; Systems pages join catalog + inspect + handler source (`08`).

## Technology map (what to study where)

| Technology | Learning doc |
|---|---|
| Django projects, ORM, migrations | `01` |
| DRF, serializers, OpenAPI | `02`, `07` |
| Postgres, logical DBs, FKs vs plain ids | `03` |
| Celery, Redis, beat, anomaly sweep | `04` |
| MCP, registry, guardrails | `05` |
| Claude Code / Cursor as clients | `06` |
| JWT, service token, CORS | `07` |
| React-Admin, Vite, MUI, dataProvider | `08` |
| Docker Compose, healthchecks, networking | `09` |
| FastAPI, Pydantic, SQLAlchemy, httpx, uvicorn | `11` |
| GraphQL (Strawberry) | `12` |
| Webhooks, Simulate Next Day | `13` |
| pytest | `14` |
| GitHub Actions CI | `15` |

## What a live demo shows, in order

Not a script to read verbatim — the sequence that makes each piece land:

1. **Overview** — after `docker compose restart mcp_server`: one flagged campaign, empty Agent Actions, recent sweep.
2. **Flagged campaign** — Campaigns list, ~+49% CPL on "Medicare Advantage – Southeast TV" (`PLANNING.md` §9).
3. **Ask Claude Code to investigate** in plain language. It rules out SmartSpot (media buy unchanged), finds Captivator CTR decline + Maestro Pool B shift — compound cause.
4. **Three outcomes from one session** — small reallocation auto-executes; larger one pending; creative refresh blocked (would leave zero active creatives).
5. **Tool Calls** — full technical detail one click away; plain-language rationale is the default.
6. **Onboard RankPulse** — uncomment one import, rebuild `mcp_server`, new tool appears (new agent session required — `06`).
7. **Same question in Cursor** — identical governance.
8. **Advance one day** — webhooks + sweep; optional GraphiQL at `/graphql`.

Stakeholder narrative with screenshots: `docs/field-notes.md`. Non-technical users: `docs/for-marketers.md`.

## Design decisions worth defending out loud

From `PLANNING.md` Decisions Log — short, but each is a real trade-off:

- **Risk-scored three-tier autonomy** instead of binary human-approval-for-everything
- **Hard cap + pre-action snapshots + env thresholds** as defense in depth / policy ownership
- **Per-tool magnitude/confidence definitions** (budget % ≠ creative disruption)
- **Celery beside the MCP server**, reusing anomaly code — not a floating fifth owner
- **Per-service webhooks**, not one central write-into-all-DBs endpoint
- **Walking skeleton first** (one service, one tool, Claude Code round-trip) before four-service slog
- **Four standalone projects in one monorepo** — runtime independence ≠ four git remotes

If you can explain those without notes, you understand the architecture — not just the file tree.

## Key vocabulary (cumulative)

- **Governed gateway** — MCP server scores, logs, and routes before side effects.
- **Three-tier autonomy** — auto-execute / human approval / hard block.
- **Hard cap** — fixed ceiling that cannot be out-scored.
- **Config-driven tool registry** — new systems join via adapter + register, not core rewrites.
- **Vendor-agnostic gateway** — client vendor irrelevant to enforcement.
- **Logical database isolation** — HTTP is the only legal cross-system join.

## Try this yourself

1. Read Decisions Log rows for "Auto-execute safety" and "Risk-scoring inputs" in `PLANNING.md`.
2. Trace campaign 1 through all four `models.py` files and the matching MCP tools.
3. Run the demo sequence above once end to end.
4. Skim `11`–`15` for any stack piece that still feels fuzzy.

That is the curriculum. The rest of `docs/learning/` is the textbook.
