# Agent360 — Live Demo Script (CTO / Internal Stakeholder)

**Audience**: a CTO or other internal technical/business stakeholder seeing Agent360 for the first time.
**Length**: ~18–20 min for the core walkthrough; up to ~40 min if you run the optional flourishes.
**What this demo needs to prove, in one sentence**: an AI agent can safely investigate and act across systems that don't talk to each other, with its autonomy automatically calibrated to risk — not because the model is trustworthy, but because a deterministic layer outside the model enforces limits on it.

Don't read this doc verbatim in the room — it's a script to rehearse from, not a teleprompter. The "Why this matters" callouts are the point; the click-by-click steps are just how you get there.

---

## 1. Before you're in the room (15–30 min prep)

**1. Start the stack** (skip if already running — check with `docker compose ps`):
```bash
docker compose up -d
```
First boot takes ~1–2 min (Maestro360 seeds several thousand call events). Confirm all 11 containers are healthy:
```bash
docker compose ps
```
You want `onesource360`, `smartspot360`, `captivator360`, `maestro360`, `rankpulse`, `mcp_server`, `redis`, `postgres` all showing `(healthy)`. `frontend`, `celery_worker`, `celery_beat` don't have healthchecks configured — "Up" is enough.

**2. Confirm a clean audit trail.** Restarting `mcp_server` truncates its audit tables and re-runs the anomaly sweep on boot — same idea as the four sims reseeding — so Agent Actions / Tool Calls start empty and campaign 1 is already flagged. If the stack has been running through earlier test sessions without a restart, bounce just the gateway:
```bash
docker compose restart mcp_server
```
Wait a few seconds for `/health`, then check Overview: flagged campaign present, Agent Actions empty (until the live investigation writes new rows).

**3. Connect Claude Code to the MCP server** (if this session/terminal hasn't already):
```bash
claude mcp add --transport http agent360 http://localhost:8100/mcp
```
Then start a **fresh** Claude Code session for the demo — an existing long session may have stale context or a cached tool list from earlier testing.

**4. Pre-open browser tabs**, in this order, so you're not navigating live:
- `http://localhost:3000/#/` — Overview dashboard (note the `#` — this app uses hash routing; a bookmark/typed URL without the `#` silently lands on the dashboard instead of the resource you meant)
- A second tab or window with your Claude Code terminal, sized to sit side-by-side with the browser

**5. Decide your time budget up front.** Core walkthrough (§3) is the whole pitch and takes ~18–20 min. Everything in §4 is additive — pick based on the room and the clock, don't try to cram all of it in.

**6. Know your fallback.** The agent’s exact dollar amounts and risk scores will vary slightly run-to-run (Claude decides what to propose; the *routing logic* is deterministic, the *proposal sizes* aren’t). If a live investigation doesn’t naturally produce all three outcome tiers, just ask explicitly — see the note in Step 3 below. Worst case, `docs/for-marketers.md` has the exact numbers from a full prior run, so you’re never fully unscripted.

---

## 2. The one sentence to keep coming back to

> "The model doesn't decide how much authority it has — a scoring function outside the model does, and that function is enforced by the server, not by asking the model nicely."

Every highlight in this demo is a specific instance of that sentence. If a question knocks you off track, that sentence is how you get back.

---

## 3. Core walkthrough (~18–20 min)

### Step 1 — Open the Overview dashboard
Go to `http://localhost:3000/#/`. Point at:
- The stat tiles (flagged campaigns / pending approval / auto-executed / blocked counts)
- The flagged campaign — "Medicare Advantage – Southeast TV" should show a CPL variance around **+50%**
- If you skipped the pre-flag step, click **Run sweep now** here — this is a real backend call (`POST /flagged-campaigns/sweep`), not a canned animation.

**Why this matters**: nothing here required an LLM. A scheduled job checks every active campaign against target CPL every 5 minutes and writes what it finds — the same detection logic an agent conversation would use, just triggered by a clock. **Monitoring is free and always-on; the LLM only gets invoked for the expensive part — figuring out *why*.**

### Step 2 — Point at the flagged campaign, then at the actual tables
Click into **Campaigns**, then the flagged one. Show the performance panel: 7-day CPL vs. target, the trend chart with the week-4 spike visible, spend/leads.

Then open **Systems → OneSource360**. Scroll to **Live tables** — `campaigns_campaign` (6 rows) and `campaigns_dailyperformancerollup` (the daily scoreboard). Point at campaign 1's week-4 rollups. Then **REST endpoints** and **MCP tools**: `get_campaign_performance` is a `GET /api/performance/?campaign_id=…` plus the Python that issues it.

**Why this matters**: this is a real, seeded scenario (not cherry-picked for the demo) — $50k/week spend, ~1,100 leads/week steady for 3 weeks, then leads drop to ~735 in week 4 with spend unchanged. A human would see this exact chart in a normal BI dashboard. What they can't see from Campaigns alone is *why* — that requires the other three systems. Systems is how you prove the agent is not a black box: every later tool call is going to hit one of these endpoints and read one of these tables.

### Step 3 — Ask Claude Code to investigate
Switch to the Claude Code terminal and type, in plain language:

> *"Investigate campaign 1 — Medicare Advantage Southeast TV. Cost per lead spiked. What happened, and what should we do?"*

Narrate as tool calls stream by — you don't need to explain each one, just point at the pattern: **it's checking multiple independent systems, not just one.** Typical sequence:
1. `list_campaigns` / `get_performance_anomalies` — confirms the spike
2. `get_spot_performance` (SmartSpot360) — **rules out** a media-buy change (nothing moved here — useful negative evidence)
3. `get_creative_performance` / `get_declining_creatives` (Captivator360) — finds the ad's CTR has dropped well below its own first week
4. `get_call_quality` / `get_routing_summary` (Maestro360) — finds call volume quietly shifted into a lower-converting, non-certified agent pool

**Why this matters**: neither the creative CTR decline nor the routing shift alone explains a ~50% CPL jump. Together they do — and *no single platform's own dashboard shows this*, because the answer lives at the intersection of two systems. This is the actual "why AI here" argument, made concretely instead of asserted.

**If the agent proposes only one or two actions**, ask it directly: *"Propose a few different fixes here — including a couple of options for how much budget to move, and a creative refresh — so I can see how each is evaluated."* This reliably surfaces all three tiers without scripting the agent's language for it.

### Step 4 — The three outcomes land
Switch back to the browser, refresh **Agent Actions** (`/#/agent_actions`). You should see, from one investigation:

| Outcome | What happened | What to say |
|---|---|---|
| **Auto-executed** (small $ reallocation, low risk score) | Already applied — no one clicked anything | "This one just happened. It was small, well-supported by data, and logged — a human can review it after the fact, but nothing was waiting on anyone." |
| **Pending approval** (larger reallocation, mid risk score) | Sitting in the queue with plain-English reasoning attached | "This one is bigger, so it's waiting for a person. Note the reasoning — it's written for a business user, not an engineer." |
| **Blocked** (creative refresh on the campaign's only active creative) | Never created a pending record — refused outright | "This would've left the campaign with zero active creatives. The system said no on its own, and told the agent why, before a human ever had to catch it." |

Also show the **Overview** dashboard's "Needs Your Attention" panel — click **Approve** or **Reject** on the pending item live, right there, with no Claude Code involvement. **This is the moment to land the point that follows.**

**Why this matters (the headline point)**: notice the approval button lives in the human console, not in Claude Code. The agent can *propose* but the write for anything above the auto-execute threshold literally cannot happen without a human clicking a button in a UI the agent has no access to. That's not a policy — it's an architectural fact. There's also a fixed hard cap independent of the score (e.g. never auto-move more than 5% of baseline weekly spend) as defense-in-depth against a bug in the scoring math itself — so a single miscalculation can't quietly let something large through unsupervised.

### Step 5 — Tool Calls trace
Click **Tool Calls**. Point out this includes every *read*, not just the three writes just shown — every check the agent made, successful or not, timestamped. Click one row. The Show page's **technical trace** reconstructs: tool name → MCP handler file → the REST URL the container sent (`http://onesource360:8000/...`) and the same path on localhost you can open in a browser → arguments → logged result → the Python source.

**Why this matters**: full auditability, not just of what changed but of everything the agent looked at along the way. This is the difference between "trust the summary" and "here's the actual transcript plus the code that ran," available to anyone who wants to verify the agent's reasoning rather than take it on faith.

### Step 6 — Optional drill-downs
From **Systems**, open **Captivator360** (CR-114's `creatives_creativeperformancedaily` rows, CTR falling) and **Maestro360** (Pool A / Pool B in `calls_clientagentpool`, then the Call Routing explorer for the weekly stacked-bar chart — the clearest single visual of the routing shift).

**Why this matters**: the regulatory angle is free context here — Medicare Advantage call handling has real compliance requirements, and the system already tracks pool certification status as a first-class fact, feeding directly into the risk score (regulated verticals get stricter thresholds automatically).

---

## 4. Optional flourishes (pick based on time and audience)

### A. Automated sweep, on demand (~1 min, already covered if you ran it in Step 1)
`POST /flagged-campaigns/sweep` / the **Run sweep now** button. Emphasize: **zero LLM cost**, pure SQL/math, runs on a timer regardless of whether anyone's watching.

### B. Simulate Next Day (~2 min)
Overview's **Advance one day** button posts a new day of warehouse rollups, spot performance, call events, and creative metrics to each service's own webhook receiver, then re-runs the sweep.

**Why this matters**: exercises the event-driven ingestion path live instead of just showing static seeded history — this is closer to how the real system would receive data day-to-day.

### C. GraphQL join query (~2 min, technical audience)
Open `http://localhost:8100/graphql` (GraphiQL) and run:
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
**Why this matters**: one query, one round trip, data from all four systems joined server-side. Useful for a technical stakeholder who wants to see the gateway is a real API surface, not just a chat wrapper.

### D. Live onboarding of a fifth platform (~3–5 min, the acquisition story)
This is the single best answer to "what happens when we acquire a company with its own tooling."

1. Open `mcp_server/main.py`, uncomment line 14 (`import tools.rankpulse`).
2. `docker compose up -d --build mcp_server` (usually well under a minute — the image is already built once).
3. Refresh `/tools` or ask Claude Code "what tools do you have access to now?" — a new `get_organic_performance` tool (RankPulse, a stand-in SEO analytics platform) is live, with **zero changes to the MCP server's core routing code.**

**Why this matters**: BMG360-style agencies grow partly by acquisition, and every acquisition tends to bring its own disconnected tooling. This demo moment shows a newly acquired platform joining the existing governed agent ecosystem as a config change, not a re-architecture.

**Afterward**: re-comment the import and rebuild (`docker compose up -d --build mcp_server`) so the next demo still has a genuine “not yet onboarded” moment.

### E. Cursor as a second, independent client
The same MCP server already ships a working `.cursor/mcp.json`, and the pitch — “governance lives on the server, so it doesn’t matter which vendor’s agent is asking” — is real and provable. For a live Cursor demo, complete a one-time `cursor-agent login` (or use Cursor’s MCP UI) under whichever account is driving the session, and rehearse beforehand. If you haven’t logged in yet, mention it verbally instead: *“This same server already works identically with Cursor, a completely independent implementation by a different company — happy to show that in a follow-up.”*

---

## 5. The five things to make sure land

If the room only remembers five things:

1. **Governance lives outside the model.** A deterministic scoring function decides how much autonomy an action gets — the LLM doesn't grant itself permission.
2. **Three tiers, not one gate.** Auto-execute / human approval / hard block, calibrated per-action — not a single repetitive "please approve everything" loop that trains people to click "yes" without reading.
3. **A hard cap that can't be out-scored.** Defense in depth against a bug in the scoring math itself, independent of the numeric result.
4. **It's vendor-agnostic by construction**, not by policy — the same server works with any MCP-compatible agent, because none of the safety logic lives in the client.
5. **The extensibility story is real, not aspirational** — a new backend system joins as one small adapter and a config line, demoed live, not asserted in a slide.

---

## 6. Anticipated questions

| Question | Answer |
|---|---|
| Can it spend money without anyone knowing? | Only below the auto-execute threshold *and* under the hard cap — and every auto-executed action is logged with a pre-action snapshot for audit, not just silently applied. |
| What if the model recommends something wrong? | The model's job is to propose and explain; it never grants itself execution rights above the low-risk tier. A wrong large proposal lands in the approval queue or gets blocked — same as a bad proposal from a junior analyst would go through review before anything changes. |
| What happens if we switch to a different AI vendor? | Nothing, on the governance side — it's not implemented in the agent, it's implemented in the gateway. Cursor (§4E) is the concrete proof of this, not just a claim. |
| Can this be made stricter, or turned off? | The auto-execute/approval/block thresholds are configurable policy values (environment variables today), not constants baked into the agent — the business sets the dial. |
| How much does this cost to run? | $0 for the core system — it runs entirely on infrastructure you already have (Claude Code's existing subscription, local Docker). The only place a real dollar cost could reappear is a second AI vendor's own usage costs, if that's ever run at volume. |
| What's actually novel here vs. "just calling an LLM with some APIs"? | Any system can call tools. The risk-scored, three-tier autonomy model — with a score-independent hard cap and pre-action snapshotting for audit — is the part that answers "how do you deploy this responsibly," which is the actual blocker to letting an agent touch production systems at all. |
| How long would this take to point at our real systems? | Each backend system needs one adapter (a handful of tool definitions mapping to that system's real API) and a registry entry — the RankPulse onboarding flourish (§4D) is a live, timed demonstration of exactly that step. |

---

## 7. If something breaks live

- **A tool call errors out mid-investigation**: don't debug it live. Say "let's come back to that" and move to the next talking point — you have the full narrative memorized, not just this one run.
- **The frontend shows stale data**: hard-refresh; remember the `#` in the URL (react-admin's hash router — a plain path without `#` silently resolves to the dashboard).
- **A container isn't healthy**: `docker compose ps` to see which one, `docker compose logs <service> --tail 50` to see why. Don't restart mid-demo unless you have to — it's more disruptive than a visibly-broken tab you can talk past.
- **You're genuinely stuck**: `docs/for-marketers.md` has the exact numbers from a prior full run you can reference verbally while you sort out the live environment.

---

## 8. Quick reference

| What | URL / command |
|---|---|
| React-Admin console | http://localhost:3000/#/ |
| Systems inspector (OneSource360) | http://localhost:3000/#/systems/onesource360 |
| MCP catalog | http://localhost:8100/catalog |
| OneSource360 table snapshot | http://localhost:8001/api/inspect/ |
| MCP server health | http://localhost:8100/health |
| Tool registry (introspection) | http://localhost:8100/tools |
| GraphQL playground | http://localhost:8100/graphql |
| Start the stack | `docker compose up -d` |
| Check container health | `docker compose ps` |
| Reset the audit trail (and re-flag campaign 1) | `docker compose restart mcp_server` |
| Trigger the anomaly sweep manually | `curl -X POST http://localhost:8100/flagged-campaigns/sweep` |
| Connect Claude Code | `claude mcp add --transport http agent360 http://localhost:8100/mcp` |
| Onboard RankPulse live | uncomment line 14 of `mcp_server/main.py`, then `docker compose up -d --build mcp_server` |
| Run the test suite (if asked "is this tested?") | `cd mcp_server && pytest` — heaviest coverage on the risk-scoring function |
