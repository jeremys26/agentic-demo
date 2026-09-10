# Agent360

A governed MCP gateway that lets an LLM agent investigate and act across four independent marketing-technology systems, with autonomy calibrated to risk — not a blanket “ask a human every time” rule.

This is a **local demo and learning project**, modeled on BMG360’s publicly documented platform stack (OneSource360, SmartSpot360, Captivator360, Maestro360). The four simulated services are standalone Django apps with their own databases; they only talk to each other through the MCP server over HTTP. See [`PLANNING.md`](PLANNING.md) for the full rationale.

**Not affiliated with BMG360.** Data models are inferred from public descriptions and industry-standard martech patterns — not from any non-public knowledge of their systems.

![One investigation, three risk-scored outcomes — auto-executed, pending approval, and blocked, each logged with its reasoning](docs/assets/field-notes/06-agent-actions-three-tiers.jpg)

*One real investigation, three outcomes: a small reallocation auto-executed, a larger one queued for human approval, a creative refresh blocked outright — all scored by the same deterministic guardrail. See [`docs/field-notes.md`](docs/field-notes.md) for the full walkthrough.*

## Setup

From a fresh clone to a running demo. Everything runs in Docker. You do **not** need a local Postgres, Redis, Python venv, or Node install for the default path. Compose already injects the service tokens and URLs — no `.env` file is required unless you run services outside Docker (see [`.env.example`](.env.example)).

**TL;DR**

```bash
git clone https://github.com/jeremys26/agentic-demo.git
cd agentic-demo
docker compose up --build
# in another terminal, once healthy:
claude mcp add --transport http agent360 http://localhost:8100/mcp
```

Then open http://localhost:3000/#/ (note the `#` — this app uses hash routing). Details and gotchas below.

### 1. Prerequisites

| Tool | Why | Check |
|---|---|---|
| [Git](https://git-scm.com/) | Clone the repo | `git --version` |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Mac/Windows) or Docker Engine + Compose v2 (Linux) | Builds and runs the whole stack | `docker --version` and `docker compose version` |
| [Claude Code](https://claude.ai/code) | Primary agent for the live demo | `claude --version` |

Docker must be **running** before you continue (open Docker Desktop and wait until it says it’s ready). First image builds need a few GB of disk and a working network connection.

### 2. Clone the repo

```bash
git clone https://github.com/jeremys26/agentic-demo.git
cd agentic-demo
```

### 3. Start the stack

From the repo root:

```bash
docker compose up --build
```

Leave this terminal open so you can watch logs. First boot builds images, starts Postgres, migrates and seeds each Django service (Maestro360 loads several thousand call events), then brings up the MCP gateway, Redis, Celery, and the React console. **Allow about 1–2 minutes** on a cold start.

Prefer detached mode? Use:

```bash
docker compose up --build -d
docker compose ps
```

You’re looking for `(healthy)` on `postgres`, `onesource360`, `smartspot360`, `captivator360`, `maestro360`, `mcp_server`, and `redis`. `frontend`, `rankpulse`, `celery_worker`, and `celery_beat` only need to show `Up`.

### 4. Confirm it’s up

Open these in a browser (or `curl`). Console paths need the `#` — without it, the app silently lands on the dashboard instead of the page you meant.

| What | URL |
|---|---|
| React-Admin console | http://localhost:3000/#/ |
| Systems (per-platform tables / APIs / tools) | http://localhost:3000/#/systems |
| Agent Actions | http://localhost:3000/#/agent_actions |
| MCP server health | http://localhost:8100/health |
| Tool registry (plain REST) | http://localhost:8100/tools |
| Platform catalog | http://localhost:8100/catalog |
| GraphQL join query | http://localhost:8100/graphql |
| OneSource360 API | http://localhost:8001/api/campaigns/ |
| OneSource360 OpenAPI | http://localhost:8001/api/docs/ |

Quick health check from the terminal:

```bash
curl -s http://localhost:8100/health
curl -s http://localhost:8100/tools | head
```

On Overview you should see **one flagged campaign** (“Medicare Advantage – Southeast TV”) and empty Agent Actions / Tool Calls if this is a fresh gateway boot.

### 5. Connect Claude Code (primary agent)

The MCP endpoint is Streamable HTTP at `http://localhost:8100/mcp`.

```bash
claude mcp add --transport http agent360 http://localhost:8100/mcp
```

(`already exists` is fine — registration is already done.) Then start a **brand-new** Claude Code session in this repo (or any directory), so it isn’t carrying a stale tool list from an older session.

Ask in plain language:

> Investigate campaign 1 — Medicare Advantage Southeast TV. Cost per lead spiked. What happened, and what should we do?

Approve any Claude Code permission prompts when it wants to call Agent360 tools. For the full stakeholder walkthrough (investigate → three risk tiers → approve in the UI), follow [`docs/field-notes.md`](docs/field-notes.md).

### 6. Reset between demo runs

| Goal | Command |
|---|---|
| Clear Agent Actions / Tool Calls and re-flag campaign 1 | `docker compose restart mcp_server` |
| Re-seed the four sim databases to the pristine 28-day scenario | `docker compose restart onesource360 smartspot360 captivator360 maestro360` |
| Rebuild the gateway after code changes | `docker compose up -d --build mcp_server` |
| Stop everything (keep data volumes) | `docker compose down` |
| Stop and wipe databases (full clean slate) | `docker compose down -v` then `docker compose up --build` |

Re-running `docker compose up` (with the sim containers restarting) re-seeds those four databases. Restarting `mcp_server` alone clears its audit/approval tables and re-runs the anomaly sweep so the approval queue starts clean.

### Optional — Cursor as a second client

Same MCP server, different vendor — proves governance isn’t tied to Claude Code. This repo ships [`.cursor/mcp.json`](.cursor/mcp.json) pointing at `http://localhost:8100/mcp`. After the stack is up, restart Cursor (or reload MCP servers) and ask the same investigate question. Cursor’s headless CLI (`cursor-agent`) can run that prompt non-interactively from the repo root after a one-time `cursor-agent login`.

### Troubleshooting

| Symptom | Fix |
|---|---|
| `docker compose` fails / daemon not running | Start Docker Desktop; wait until it’s ready; retry |
| Port already in use (`3000`, `8100`, `8001`–`8005`, `5433`, `6380`) | Stop the other process, or change the left-hand port in `docker-compose.yml` |
| Frontend loads but APIs fail | Wait until sim services are `(healthy)` (`docker compose ps`); refresh the browser |
| Console URL opens the wrong page | Include the hash: `http://localhost:3000/#/agent_actions`, not `/agent_actions` |
| Claude Code sees only 1–2 Agent360 tools | Start a **new** Claude Code session after the server is healthy (MCP clients cache `tools/list` per session) |
| Nothing happens after you ask Claude to investigate | Approve Claude Code’s own tool-permission prompts; Agent360 never sees the call until those are approved |
| Stale Agent Actions from earlier testing | `docker compose restart mcp_server`, wait a few seconds, refresh Overview |
| Want a totally clean database | `docker compose down -v && docker compose up --build` |

## Demo scenario

Campaign **1** (“Medicare Advantage – Southeast TV”) is seeded with a compound-cause CPL spike in week 4:

1. **SmartSpot360** did not change the media buy — useful negative evidence.
2. **Captivator360** shows creative CR-114’s CTR ~25% below its own first week.
3. **Maestro360** shows call volume shifting from Medicare-certified Pool A into uncertified, lower-converting Pool B.

Neither (2) nor (3) alone explains a ~50% CPL jump; together they do. That’s the point of the gateway.

Write actions are risk-scored (`PLANNING.md` §7):

| Risk | What happens |
|---|---|
| Low (and under a hard cap) | Auto-executes, logged with a pre-action snapshot for audit |
| Medium | Queued in **Agent Actions** for a human to approve or reject |
| High | Blocked outright; the agent is told why |

Approve/reject is plain REST, not an MCP tool — an agent cannot approve its own proposal.

## Also in the stack

These are optional extras once the core demo works — details and screenshots live in [`docs/field-notes.md`](docs/field-notes.md).

- **Anomaly sweep** — Celery beat flags campaigns over the CPL threshold every 5 minutes (no LLM). Also runs once on every `mcp_server` boot; Overview has **Run sweep now**.
- **Simulate Next Day** — Overview’s **Advance one day** posts a new day’s data into each sim’s own webhook, then re-sweeps. Campaign 1 stays in the spiked-CPL pattern.
- **GraphQL join** — one investigation-shaped query at http://localhost:8100/graphql (`campaignInvestigation(campaignId: 1)`).
- **Fifth-platform onboarding** — uncomment `import tools.rankpulse` in `mcp_server/main.py`, then `docker compose up -d --build mcp_server`. RankPulse is already running; that one line wires it into the agent’s tool list.

## Tests

From the repo root (uses the `mcp_server` image — no local Python install needed):

```bash
docker compose run --rm --no-deps mcp_server pytest
```

Or locally, if you already have the MCP deps installed: `cd mcp_server && pytest`.

Heaviest coverage is on the risk-scoring function (`mcp_server/tests/test_scoring.py`). GitHub Actions runs the same pytest suite plus a frontend production build on every push.

## Layout

```
services/onesource360/     Django — campaign performance warehouse
services/smartspot360/     Django — TV/radio buying
services/captivator360/    Django — creative performance
services/maestro360/       Django — call routing
services/rankpulse_sim/    FastAPI — fifth-platform onboarding demo (unregistered by default)
mcp_server/                FastAPI + MCP SDK — tool registry, guardrails, Celery anomaly sweep
frontend/                  React-Admin console
docs/                      Learning notes, marketer guide, demo walkthrough & field notes
```

## Docs

| Doc | Audience |
|---|---|
| [`README.md` → Setup](README.md#setup) | First-time setup: clone → Docker → Claude Code |
| [`docs/for-marketers.md`](docs/for-marketers.md) | Non-technical users of the approval queue |
| [`LEARNING.md`](LEARNING.md) | Index of technical learning docs (15 topics: Django through CI) |
| [`docs/field-notes.md`](docs/field-notes.md) | Live demo walkthrough for stakeholders, illustrated with a real run |
| [`PLANNING.md`](PLANNING.md) | Full design rationale and decisions log |
