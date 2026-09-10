# Agent360

A governed MCP gateway that lets an LLM agent investigate and act across four independent marketing-technology systems, with autonomy calibrated to risk — not a blanket “ask a human every time” rule.

This is a **local demo and learning project**, modeled on BMG360’s publicly documented platform stack (OneSource360, SmartSpot360, Captivator360, Maestro360). The four simulated services are standalone Django apps with their own databases; they only talk to each other through the MCP server over HTTP. See [`PLANNING.md`](PLANNING.md) for the full rationale.

**Not affiliated with BMG360.** Data models are inferred from public descriptions and industry-standard martech patterns — not from any non-public knowledge of their systems.

![One investigation, three risk-scored outcomes — auto-executed, pending approval, and blocked, each logged with its reasoning](docs/assets/field-notes/06-agent-actions-three-tiers.jpg)

*One real investigation, three outcomes: a small reallocation auto-executed, a larger one queued for human approval, a creative refresh blocked outright — all scored by the same deterministic guardrail. See [`docs/field-notes.md`](docs/field-notes.md) for the full walkthrough.*

## Quick start

```bash
docker compose up --build
```

First boot migrates and seeds each service (Maestro360 loads several thousand call events — allow about a minute). When it’s up:

| What | URL |
|---|---|
| React-Admin console | http://localhost:3000 |
| Systems (per-platform tables / APIs / tools) | http://localhost:3000/#/systems |
| MCP server health | http://localhost:8100/health |
| Tool registry (plain REST) | http://localhost:8100/tools |
| Platform catalog | http://localhost:8100/catalog |
| GraphQL join query | http://localhost:8100/graphql |
| OneSource360 API | http://localhost:8001/api/campaigns/ |
| OneSource360 OpenAPI | http://localhost:8001/api/docs/ |

Re-running `docker compose up` re-seeds the four sim databases to the demo scenario. Restarting `mcp_server` also clears its audit/approval tables (tool calls, agent actions, flagged campaigns) and re-runs the anomaly sweep, so Agent Actions starts clean — same idea as the sim reseed.

## Connect an agent

The MCP endpoint is Streamable HTTP at `http://localhost:8100/mcp`.

**Claude Code**

```bash
claude mcp add --transport http agent360 http://localhost:8100/mcp
```

**Cursor**

This repo ships [`.cursor/mcp.json`](.cursor/mcp.json) pointing at that URL. After `docker compose up`, restart Cursor (or reload MCP servers), then ask in plain language:

> Investigate campaign 1 — Medicare Advantage Southeast TV. Cost per lead spiked. What happened, and what should we do?

Cursor’s headless CLI (`cursor-agent`) can run the same prompt non-interactively from the repo root — useful for a scripted proof. It needs a one-time `cursor-agent login` first.

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

## Tier 2 extras

**Automated anomaly sweep.** A Celery beat schedule (`redis`, `celery_worker`, `celery_beat` in `docker-compose.yml`) checks every active campaign against the same 15%-over-target rule the agent uses, every 5 minutes, with no LLM involved. On every `mcp_server` boot the gateway clears its audit tables, then runs the sweep once so campaign 1 is flagged immediately (`FlaggedCampaign` via `GET /flagged-campaigns`). Overview has a “Run sweep now” button (`POST /flagged-campaigns/sweep`) to demo it on demand.

**Simulate Next Day.** Overview’s **Advance one day** button (`POST /simulate-next-day`) posts a new day’s warehouse rollups, spots, creative metrics, and call events to **each service’s own webhook**, then re-runs the anomaly sweep. Campaign 1 stays in the spiked-CPL pattern. Writes require the MCP server’s `X-Service-Token`; a replay of the same date is skipped.

**GraphQL join.** One investigation-shaped query on the gateway. In GraphiQL at http://localhost:8100/graphql:

```graphql
query {
  campaignInvestigation(campaignId: 1) {
    name
    windowCpl
    cplVariancePct
    flagged
    spotCount
    latestCtrDeclinePct
    decliningVariantLabels
    uncertifiedPoolPct
    poolDistribution { poolName isCertifiedMedicare pctOfTotal }
  }
}
```

**Onboarding a fifth platform live.** `services/rankpulse_sim` is a small stand-in for a newly acquired SEO analytics platform — already running, but deliberately **not** wired into the agent’s toolset. To onboard it: uncomment the `import tools.rankpulse` line near the top of `mcp_server/main.py`, then `docker compose up -d --build mcp_server`. The new `get_organic_performance` tool appears in `/tools` and the MCP tool list immediately — no other code changes.

## Tests

```bash
cd mcp_server && pytest
```

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
| [`docs/for-marketers.md`](docs/for-marketers.md) | Non-technical users of the approval queue |
| [`LEARNING.md`](LEARNING.md) | Index of technical topic docs |
| [`docs/field-notes.md`](docs/field-notes.md) | Live demo walkthrough for stakeholders, illustrated with a real run |
| [`PLANNING.md`](PLANNING.md) | Full design rationale and decisions log |
