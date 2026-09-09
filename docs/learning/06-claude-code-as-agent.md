# 06 — Claude Code as Agent

**Status**: complete. The seeded scenario has been run live against the MCP server with all three risk tiers firing on real data. The Cursor proof point is documented below (config verified; the headless CLI needs a one-time login under the demo operator’s Cursor account).

## What it is

`PLANNING.md` §5 is explicit about this: **there is no custom agent-orchestration code in this repo.** Claude Code already has a production-grade agent loop — it decides which tool to call, in what order, reads the result, and decides what to do next, all on its own. Connecting it to Agent360 is pure configuration: point it at a URL, and its existing MCP client handles the protocol handshake, tool discovery, and tool calling. The “agent” in “Agent360” is Claude Code itself; everything this repo builds is what Claude Code is allowed to *see and do* once connected, not how it thinks.

## Why this piece of the stack is used here

This is the answer to "what happens when you switch models or vendors" — nothing has to change, because governance lives at the tool layer (`guardrails/`), not the agent layer. Building a custom orchestration loop would have been wasted effort duplicating something Claude Code (and Cursor) already do well, and would have cost real API money to boot (`PLANNING.md`'s zero-cost constraint). It would also have hidden the actual differentiator — the risk-scoring guardrail — behind a pile of unremarkable "call an LLM, parse its response, decide what to do" plumbing that isn't specific to this project at all.

## Where it lives in this repo

There's no application code for this doc to point at — that's the point. What exists instead:

- `.cursor/mcp.json` (repo root) — Cursor's MCP client config, pointing at `http://localhost:8100/mcp`.
- Claude Code's registration is a CLI command, not a repo file: `claude mcp add --transport http agent360 http://localhost:8100/mcp` (documented in `README.md`).
- `mcp_server/main.py` mounts the actual protocol endpoint (`mcp.streamable_http_app()` at `/mcp`) that both clients hit.

## What actually happens on a tool call

1. **Connect**: the client opens an HTTP connection to `/mcp` and performs the MCP handshake — `initialize`, then `notifications/initialized`.
2. **Discover**: the client calls `tools/list`. The MCP Python SDK auto-generates each tool's JSON Schema from its Python function signature (see `05-mcp-servers.md`'s note on how `wrap_read_tool`'s wrapper still exposes the *original* signature via `functools.wraps`), so every tool the registry loop in `main.py` wired up appears with real, typed parameters — not a generic blob.
3. **Reason**: the agent (Claude Code's own model) reads the available tools' names and descriptions and decides, based on the user's request, which to call and in what order. None of that reasoning is visible to or influenced by the MCP server — the server only sees discrete tool calls arrive.
4. **Call**: each tool call is a `tools/call` request with a tool name and arguments. The server routes it to the matching Python function (read tools go through `wrap_read_tool`'s logging wrapper; write tools go through their own guardrail function, `guard_reallocate_budget` or `guard_request_creative_refresh`), executes it, and returns the result.
5. **Repeat**: the agent reads the result and decides its next move — another tool call, or a final answer — entirely within its own loop. A multi-step investigation (list campaigns → check one system → check another → propose an action) is just several rounds of steps 3–4 back to back.

Every one of those `tools/call` requests lands in `AgentToolCall` (`guardrails/models.py`) identically, regardless of which client sent it — that table is what `frontend/src/resources/toolCalls.jsx`'s Tool Calls trace view reads from, which is effectively a live transcript of an agent's reasoning made visible after the fact, for free, without building any tracing infrastructure — it's just what logging every tool call already gives you.

## Worth knowing: MCP clients cache their tool list

An MCP client typically fetches `tools/list` once, when a session first connects — not on every tool call. If new tools are registered server-side *after* that (e.g. `mcp_server/main.py` gets rebuilt with an added `import tools.rankpulse`, as in the live fifth-platform onboarding demo in `05-mcp-servers.md`), a client whose session predates that change won’t see the new tool until it reconnects — an existing, already-initialized session doesn’t get an automatic push update. This actually happened during this project’s own development: a Claude Code session that had been connected since the walking-skeleton phase (when the registry held exactly one tool) kept surfacing only that one original tool from its own tool search, long after the registry had grown to 11, because its cached tool list was never refreshed. The fix in the moment was to drive the MCP protocol directly with a small script (the Python `mcp` SDK’s `streamable_http_client` + `ClientSession`, called from inside the `mcp_server` container, which already has the SDK installed) rather than trusting the stale session — the same protocol, the same server, just a different client, which is incidentally a nice small preview of the vendor-agnostic point below. **Practical implication for a live demo**: if you rebuild `mcp_server` mid-session to add a tool, start a fresh Claude Code session (or otherwise force a reconnect) afterward rather than continuing in the one that was already connected.

## Tier 2: Cursor as a second, independent client

`PLANNING.md` §8's vendor-agnostic proof calls for re-running the same investigation through **Cursor** — built by Anysphere, not Anthropic, so a genuinely independent implementation of the MCP client side, not just another Anthropic surface. This repo ships `.cursor/mcp.json` pointing at the identical `http://localhost:8100/mcp` URL Claude Code uses; opening Cursor and asking it to investigate campaign 1 exercises the exact same registry, guardrail, and logging code with zero server-side changes.

Cursor also has a headless CLI, `cursor-agent`, which can run a prompt non-interactively (`cursor-agent -p --approve-mcps --trust "..."`, executed from the repo root so it picks up `.cursor/mcp.json`) — a scriptable version of the same proof, rather than a manual click-through. It requires its own one-time `cursor-agent login` first (a personal Cursor account; this repo does not and should not hold those credentials). What’s already confirmed: the CLI is installed, `.cursor/mcp.json` is correctly formed and points at a live, reachable server — the only remaining step for the automated proof is authentication under the operator’s account.

## Key vocabulary

- **MCP client** — the thing that connects to an MCP server and drives tool calls on an agent's behalf; Claude Code and Cursor are both clients of the *same* server here.
- **Tool discovery** — the `tools/list` call a client makes once per session to learn what’s available; see the caching note above for why “once per session” matters.
- **Handshake** — the `initialize` / `notifications/initialized` exchange that must happen before `tools/list` or `tools/call` will work; skipping straight to `tools/call` on a fresh connection produces a "missing session ID" error (mentioned in `05-mcp-servers.md`'s "try this yourself").
- **Vendor-agnostic gateway** — the design property this whole doc demonstrates: governance and tool access live entirely server-side, so which LLM or vendor is asking is irrelevant to how a request gets handled.

## Try this yourself

Register the server with Claude Code (`claude mcp add --transport http agent360 http://localhost:8100/mcp`) and ask it, in plain language, to investigate campaign 1's cost-per-lead spike — no need to mention tool names, it'll figure out which ones to call. Then open Cursor with the same repo (or run `cursor-agent -p` after logging in) and ask the identical question — same answer, same underlying tool calls, same guardrail decisions, different client entirely.
