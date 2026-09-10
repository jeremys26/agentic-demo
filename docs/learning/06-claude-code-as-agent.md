# 06 — Claude Code as Agent

**Status**: complete. The seeded scenario has been run live with all three risk tiers. Cursor is documented as a second client. Protocol substrate: `05-mcp-servers.md`.

## What it is

An **agent** here means an LLM application that can *choose* which tools to call, read results, and decide what to do next — often in a loop — until it answers the user.

`PLANNING.md` §5 is explicit: **there is no custom agent-orchestration code in this repo.** Claude Code already has a production-grade loop. Connecting it to Agent360 is configuration: point it at a URL; its MCP client handles handshake, discovery, and tool calling. The "agent" in Agent360 is Claude Code (or Cursor); this repo builds what the agent is allowed to *see and do*, not how it thinks.

## Why this piece of the stack is used here

Three reasons:

1. **Zero orchestration to maintain** — no hand-rolled "call the model, parse tool_use, dispatch, repeat" service.
2. **Zero paid API key for the core demo** — Claude Code / Cursor subscriptions already cover the agent runtime (`PLANNING.md` zero-cost constraint).
3. **Governance stays portable** — policy lives in `guardrails/`, not in a system prompt or a vendor-specific agent framework. Switching clients proves that claim instead of asserting it.

Building a custom loop would hide the real differentiator (risk scoring) behind unremarkable plumbing.

## Where it lives in this repo

Almost nowhere as application code — that's the point:

| Artifact | Role |
|---|---|
| Claude CLI registration | `claude mcp add --transport http agent360 http://localhost:8100/mcp` (not a repo file) |
| `.cursor/mcp.json` | Cursor MCP config → same URL |
| `mcp_server/main.py` | Mounts `mcp.streamable_http_app()` at `/mcp` |

## What actually happens on a tool call

```text
User (plain language)
  → Claude Code agent loop (model reasons)
    → MCP client: initialize / tools/list (once per session)
    → MCP client: tools/call { name, arguments }
      → Agent360 gateway (log; if write → score → route)
        → httpx → Django/FastAPI sim
      ← JSON result
    → model reads result, maybe another tools/call …
  ← final answer to user
```

Step by step:

1. **Connect** — HTTP to `/mcp`; handshake `initialize` then `notifications/initialized`.
2. **Discover** — `tools/list`. The Python MCP SDK builds JSON Schema from each handler's signature (including wrapped reads via `functools.wraps` — see `05`).
3. **Reason** — entirely inside the client/model. The server never sees chain-of-thought; it only sees discrete tool calls.
4. **Call** — `tools/call`. Reads go through `wrap_read_tool`; writes through `guard_reallocate_budget` / `guard_request_creative_refresh`.
5. **Repeat** — multi-step investigation is several rounds of 3–4.

Every call lands in `AgentToolCall`. The Tool Calls resource in React-Admin is that table — a live transcript of what the agent checked, without separate tracing infrastructure.

## MCP clients cache their tool list

Clients typically fetch `tools/list` **once per session**, not on every call. If you rebuild `mcp_server` mid-demo to uncomment RankPulse, an already-open Claude Code session may still show 11 tools until you start a **new session** (or otherwise force reconnect).

This bit the project during development: a walking-skeleton session (1 tool) kept searching only that one tool after the registry grew to 11. Fix: new session, or drive the protocol with the SDK's `streamable_http_client` from inside the `mcp_server` container.

**Demo rule:** after any registry change, new Claude Code session.

## Claude Code vs Cursor (vendor-agnostic proof)

| Client | Vendor | How it connects |
|---|---|---|
| Claude Code | Anthropic | `claude mcp add --transport http …` |
| Cursor IDE | Anysphere | `.cursor/mcp.json` |
| `cursor-agent` CLI | Anysphere | Headless; picks up `.cursor/mcp.json` from repo root; needs one-time `cursor-agent login` |

Same server, same registry, same guardrail, same `AgentToolCall` rows. Nothing server-side branches on which client called. That is the portable-governance claim made tangible.

Headless example shape (after login):

```bash
cursor-agent -p --approve-mcps --trust \
  "Investigate campaign 1 — Medicare Advantage Southeast TV. Cost per lead spiked."
```

Credentials stay with the operator — never commit them.

## What the agent is *not* responsible for

| Concern | Owner |
|---|---|
| Which writes auto-execute | `policy.route` + scoring |
| Approving pending actions | Human via REST / React-Admin |
| Flagging CPL anomalies on a timer | Celery sweep (`04`) |
| Cross-service joins in one query | GraphQL on the gateway (`12`) optional; agent can also multi-call REST tools |

The agent investigates and proposes. The gateway governs. The human resolves medium-risk writes.

## Prompting for the demo

You do **not** need to name tools. Plain language works:

> Investigate campaign 1 — Medicare Advantage Southeast TV. Cost per lead spiked. What happened, and what should we do?

Approve Claude Code's own permission prompts when it wants to call Agent360 tools — the gateway never sees a call until the *client* allows it. Full stakeholder walkthrough: `docs/field-notes.md`.

## Key vocabulary

- **MCP client** — connects to an MCP server and drives tool calls (Claude Code, Cursor).
- **Agent loop** — model ↔ tools until a final answer; implemented by the client, not this repo.
- **Tool discovery** — `tools/list` once per session; see caching note.
- **Handshake** — `initialize` / `notifications/initialized` before other MCP methods.
- **Vendor-agnostic gateway** — governance and tools live server-side; client vendor is irrelevant to routing.

## Try this yourself

1. Stack up: `docker compose up --build`
2. Register: `claude mcp add --transport http agent360 http://localhost:8100/mcp`
3. New Claude Code session; ask the investigate question above
4. Watch Tool Calls and Agent Actions at `http://localhost:3000`
5. Optional: same question in Cursor

**Next:** `07-auth-jwt-oauth2.md` for how the gateway authenticates to the sims on each of those HTTP calls.
