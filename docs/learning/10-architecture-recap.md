# 10 — Architecture Recap

**Status**: complete. End-to-end synthesis and presentation talking points for the built system (`PLANNING.md` §14).

## The governed-gateway principle, end to end

Everything in this repo exists to support one sentence: **an agent's autonomy should be calibrated to risk, not gated behind a single blanket "ask a human every time" rule — and that governance should live at the tool layer, not the agent layer, so it doesn't care which vendor's agent is asking.**

Tracing one request all the way through:

1. **Four independent systems, actually independent.** `services/{onesource360,smartspot360,captivator360,maestro360}` are four separate Django projects, each with its own database, talking to nothing but their own REST APIs. This isn't a style choice — it's what makes "these systems didn't talk to each other, and this project connects them" a true claim rather than a rebranded monolith (`PLANNING.md` §5).
2. **One gateway, not four bespoke integrations.** `mcp_server/` is the only thing that talks to all four. Its tool registry (`registry.py` + `tools/*.py`) is config-driven: a new backing service becomes agent-usable by writing one small adapter module and registering it — proven concretely by the RankPulse-sim onboarding demo (`05-mcp-servers.md`), which adds a fifth platform with zero changes to the MCP server's core code.
3. **Every tool call is logged, no exceptions.** `AgentToolCall` (`guardrails/models.py`) captures every read and write, regardless of outcome — this is what makes the Tool Calls trace view a complete, honest transcript rather than a curated highlight reel.
4. **Write tools never execute unconditionally.** `guardrails/scoring.py`'s `compute_score()` turns four per-tool-defined inputs (magnitude, confidence, recency, regulatory sensitivity) into a single 0–100 number; `guardrails/policy.py`'s `route()` turns that number — plus a fixed, score-independent hard cap — into one of three outcomes. This is the actual headline differentiator (`PLANNING.md` §1): not "can an agent call tools," which is table stakes for MCP, but "how much independence has this specific action earned, right now, given what's actually known about it."
5. **The three outcomes are structurally different, not just labeled differently.** `auto_execute` runs immediately and snapshots pre-action state for audit (`ExecutedAction.pre_action_state`). `pending_approval` creates a `ProposedAction` and returns *without executing anything* — the tool call itself does nothing until a human acts. `blocked` never creates a record beyond the audit log; the agent is told why and can propose something smaller instead. All three are real, live-verified behaviors (`05-mcp-servers.md`'s live-demo-scenario table), not three code paths that happen to look different in a diagram.
6. **The dial belongs to the business, not the agent.** `policy.py`'s thresholds are environment-variable-overridable, not hardcoded — the framing that matters here is "the business sets the leash length, the deterministic layer enforces it," not "the AI decided it was safe."
7. **Automated monitoring and agent-driven investigation are the same code path.** The Tier 2 Celery sweep (`04-celery-and-async.md`) calls the identical `get_performance_anomalies()` function a live agent conversation would call — a timer instead of a conversation is the only difference, which is exactly the point: there's one source of truth for "is this campaign anomalous," not two implementations that could quietly drift apart. Demo hygiene lives in the same lifespan: every `mcp_server` boot runs `reset_audit_tables()` then that sweep, so Agent Actions starts empty and campaign 1 is already flagged (`docker compose restart mcp_server`).
8. **Live data joins through each service's own door.** Simulate Next Day (`mcp_server/simulator.py`) does not write into four databases from the gateway. It POSTs webhook payloads to OneSource360, SmartSpot360, Captivator360, and Maestro360 separately, authenticated with the service token (`07-auth-jwt-oauth2.md`). The warehouse is not a backdoor.
9. **Nothing here is Claude-specific.** `06-claude-code-as-agent.md` covers this in depth: Claude Code and Cursor are both just MCP clients hitting the same server, same registry, same guardrail. Governance living server-side, not in a system prompt or an agent framework, is what makes "swap the vendor" a non-event.

## What a live demo actually shows, in order

This is the shape a walkthrough should follow — not a script to read verbatim, but the sequence that makes each piece land before the next one is introduced:

1. **Open the Overview dashboard** (`frontend/src/pages/Overview.jsx`, react-admin's `dashboard` prop, shown at `/`). One flagged campaign, three pending approvals, real recent activity — this is "what needs my attention" answered before clicking into anything, which is the actual point of a stakeholder-facing console.
2. **Point at the flagged campaign** (Campaigns list, `~+50% CPL` badge) — this is what `PLANNING.md` §9 seeded: "Medicare Advantage – Southeast TV," a real compound-cause spike, not a synthetic number picked to look dramatic.
3. **Ask Claude Code to investigate**, in plain language, no tool names needed. It calls `list_campaigns`, then `get_performance_anomalies` (confirms ~+49% trailing-week CPL, about $67 vs a $45 target), then rules out a media-buy change via SmartSpot360 (useful negative evidence), then finds creative CTR decline via Captivator360 (CR-114, last-week CTR ~25% below its own first week) and a call-routing shift via Maestro360 (Pool B share up to ~16% lifetime, visibly spiking further in the final week on the Call Routing Show page's weekly chart) — neither alone explains a ~49% jump; together they do.
4. **Show the three outcomes landing from that one investigation**: a small reallocation auto-executes and shows up in Agent Actions as already-done; a larger one queues in "Needs Your Attention" with its reasoning attached, waiting on a human; a creative-refresh request gets blocked outright because it would leave the campaign with zero active creatives — the agent is told why, not just refused.
5. **Open the Tool Calls trace** to show the full technical detail is one click away — the plain-language rationale is the default view (`agentActions.jsx`), not the only view.
6. **(Tier 2 flourish) Onboard RankPulse-sim live**: uncomment one import line in `mcp_server/main.py`, rebuild the container, and a fifth platform's data is agent-accessible — dramatizing `PLANNING.md` §2's actual structural business problem (BMG360 grows by acquisition; new tooling needs to join fast) rather than just asserting it's solved.
7. **(Tier 2 flourish) Same server, Cursor as the client** — re-run step 3's question in Cursor instead of Claude Code. Identical tool calls, identical guardrail decisions, because none of the governance lives in either client.
8. **(Tier 2 flourish) Advance one day** from Overview — a new day's data lands through each platform's own webhook, then the sweep re-flags campaign 1. GraphiQL at `/graphql` is the one-query version of the same cross-platform picture.

## For a non-technical audience

`docs/for-marketers.md` is the parallel version of this recap aimed at the people who'd actually use the approval queue, not build it — same demo scenario, no MCP/Django/risk-score vocabulary. Point stakeholders there first; this doc and `docs/learning/*` are for anyone who wants to know how it actually works.

## Key vocabulary (cumulative)

- **Governed gateway** — the MCP server's role: not a passthrough to four APIs, but the single place where every action gets scored, logged, and routed before anything happens.
- **Three-tier autonomy** — auto-execute / human approval / hard block, calibrated per-action by a computed risk score, not a single blanket approval gate.
- **Hard cap** — a fixed ceiling that can't be out-scored, independent of the numeric risk score — defense in depth against a bug in the scoring math itself.
- **Config-driven tool registry** — new backing systems join by writing an adapter and registering it, not by changing the MCP server's core routing logic.
- **Vendor-agnostic gateway** — governance lives server-side, so which LLM or client is asking is irrelevant to how a request gets handled.

## Try this yourself

Read the four items in `PLANNING.md`'s Decisions Log table under "Auto-execute safety" and "Risk-scoring inputs" — they're short, but each one is a real design tradeoff this project made and can defend, which is the actual test of whether the architecture is understood rather than memorized.
