# 08 — React-Admin

**Status**: complete. Overview dashboard, Campaigns, Agent Actions, Tool Calls, Systems (per-platform inspector), the operational explorers (Spots, Creatives, Call Routing), and the in-app Guide, running via Docker Compose at `http://localhost:3000`.

## What it is

React-Admin is a frontend framework for building admin/back-office UIs on top of a data API. You describe your data as `Resource`s (roughly: "here's a thing with a list view and a detail view") and point the framework at a `dataProvider` — an adapter object with a fixed contract (`getList`, `getOne`, `getMany`, `create`, `update`, `delete`, etc.) that translates React-Admin's generic calls into whatever your actual backend expects. React-Admin ships prebuilt providers for common backend shapes (REST conventions like json-server, GraphQL, Supabase); when none of those fit, you write your own — which is what this repo does.

## Why this piece of the stack is used here

Agent360 doesn't have one backend — it has five (`PLANNING.md` §5/§13): four independent Django services, plus the MCP server's own API for the approval queue. A hand-rolled single-page app would mean writing list/detail/pagination UI from scratch for every resource. React-Admin gives all of that (tables, sorting, routing, detail views, notifications) for free, as long as a `dataProvider` can answer its questions — which turns the frontend problem into "write one adapter object" instead of "build a UI."

## Where it lives in this repo

| File | Role |
|---|---|
| `frontend/src/main.jsx` | Entry point — mounts `<App />` |
| `frontend/src/App.jsx` | Registers `<Resource>`s (`campaigns`, `agent_actions`, `tool_calls`, `spots`, `creatives`, `call_routing`) plus the Overview `dashboard`, `/faq`, and `/systems/:slug` |
| `frontend/src/pages/Overview.jsx` | Landing page: flagged/pending tiles, Systems shortcuts, approval queue, Simulate Next Day, Celery sweep log |
| `frontend/src/pages/systems/SystemsIndex.jsx` | One card per simulated application + the gateway |
| `frontend/src/pages/systems/SystemPage.jsx` | Live Postgres snapshot, REST catalog, MCP tools with handler source |
| `frontend/src/pages/Faq.jsx` | The in-app Guide (FAQ/glossary), mounted at `/faq` |
| `frontend/src/trace.js` | Reconstructs the actual HTTP request(s) an MCP tool call sends, from the catalog's REST mapping + logged arguments — shared by `TechnicalTrace.jsx` and `SystemPage.jsx` |
| `frontend/src/components/TechnicalTrace.jsx` | Reconstructs MCP → REST → source for an Agent Action / Tool Call |
| `frontend/src/components/CodeBlock.jsx` | Monospace source-code display, used for tool handler source on Systems pages and in the technical trace |
| `frontend/src/components/SnapshotTable.jsx` | Renders one live Postgres table's rows on a Systems page |
| `frontend/src/components/Collapsible.jsx` | Expand/collapse section wrapper, used for MCP tool entries on Systems pages so opening "MCP tools" doesn't dump every handler's source at once |
| `frontend/src/components/LineTrendChart.jsx` | CPL-vs-target trend line, used on `CampaignShow` |
| `frontend/src/components/VarianceBarChart.jsx` | Portfolio-wide CPL variance bar chart, used on Overview |
| `frontend/src/components/WeeklyPoolShareChart.jsx` | Weekly stacked pool-share chart, used on the Call Routing resource |
| `frontend/src/components/ResourceExplainer.jsx` | Short "what am I looking at" blurb shown at the top of a resource list |
| `frontend/src/dataProvider.js` | The custom adapter — see below |
| `frontend/src/resources/campaigns.jsx` | `CampaignList` / `CampaignShow` — read-only view of OneSource360-sim data |
| `frontend/src/resources/agentActions.jsx` | `AgentActionList` / `AgentActionShow` — the approval queue, with a status badge per risk tier and Approve/Reject buttons |
| `frontend/src/resources/toolCalls.jsx` | Live MCP trace across all four (plus RankPulse, once registered) backing services |
| `frontend/src/resources/creatives.jsx` | Captivator360-sim creative performance |
| `frontend/src/resources/spots.jsx` | SmartSpot360-sim station/daypart spots |
| `frontend/src/resources/callRouting.jsx` | Maestro360-sim pool distribution and weekly share chart |
| `frontend/src/theme.js` | Custom MUI theme passed to `<Admin theme={theme}>` — see below |
| `frontend/src/layout/AppLayout.jsx` | Top-bar layout; `sidebar={NoSidebar}` so nav lives in `TopBar`, not an icon rail |
| `frontend/src/layout/TopBar.jsx` | Horizontal nav across Campaigns / Agent Actions / Tool Calls / Systems / Guide |
| `frontend/src/components/StatusPill.jsx` | Shared colored-dot status pill, used by both Campaigns' `status` and Agent Actions' `outcome` |
| `frontend/src/components/IconTag.jsx` | Shared rounded-square colored icon badge, used as a leading visual on table rows (campaign channel, agent action tool) |

### The theme: inspired by BMG360’s public site, not a clone of it

`App.jsx` passes a custom theme object (built with `@mui/material/styles`’ `createTheme`) instead of using React-Admin’s built-in default. The brief: bring some of BMG360’s visual identity into the frontend, since the four sim services are modeled on BMG360’s real platforms — without cloning a live company’s exact branding into a portfolio piece they didn’t commission. Scope was deliberately narrowed to **inspired, not cloned**.

What was actually reused, and why each is safe to reuse:
- **Accent color** (`#0D2BFF`) — sampled directly from BMG360's site via `getComputedStyle` on their "Contact Us" button. A color value isn't the kind of thing trademark/copyright protects on its own; using it as one accent among a broader palette (not as a stand-in for their brand identity) keeps it in "inspired by" territory.
- **Serif-headline + grotesk-body font pairing** — BMG360 pairs a serif (Signifier) with a grotesk (Founders Grotesk). Both are commercial Klim Type Foundry typefaces Agent360 has no license to use, so they aren't used here — the theme reproduces the *pairing structure* with **Fraunces** (free, serif, similar character) and **Inter** (free, grotesk), loaded via Google Fonts in `index.html`. This is the one place "copy the fonts" got a direct no rather than a workaround-and-proceed: it's a licensing constraint, not a style opinion.
- **Generous whitespace / soft tinted section backgrounds** — `background.default` is a soft periwinkle tint (`#F4F5FC`) rather than neutral grey, echoing BMG360's alternating light-tint sections without reusing their exact value. This is a common editorial pattern, not brand-exclusive.

What was deliberately left out: their logo/wordmark, actual marketing copy, and the marketing-homepage layout itself (full-bleed hero photography, "Start Your 360" CTA pattern) — Agent360's frontend is a data-dense admin dashboard, not a marketing site, so that layout language doesn't transfer anyway.

### Second pass: general modern-dashboard patterns

A follow-up pass widened the brief beyond BMG360 specifically. Generic dashboard patterns that landed:

- **Light top-bar navigation against a tinted content area** — `AppLayout.jsx` passes `sidebar={NoSidebar}` and `TopBar.jsx` renders the resource links as a horizontal nav. An earlier pass tried a dark icon-rail sidebar; it was dropped because a data-dense admin at this width is easier to scan with the nav on top.
- **Uppercase, letter-spaced, muted table headers** and **subtle row hover tint** — `MuiTableCell`'s `head` slot and a `MuiTableRow` hover override in `theme.js`.
- **Rounded, soft-shadow card containers** — `MuiCard` override (react-admin wraps every `<List>`'s content in a `Card`, class `RaList-content`, so this alone re-skins every list/show page).
- **Status pills with a leading colored dot, and colored icon-square tags per row** — extracted into `StatusPill.jsx` and `IconTag.jsx` so Campaigns and Agent Actions share one implementation. `OUTCOME_META` remains as a label/tone map; `StatusBadge` wraps `StatusPill` rather than painting hex colors inline.
- **Removed the bulk-select checkbox column from `CampaignList`** — it had no bulk action wired to it (dead UI chrome); `agentActions.jsx` already had `bulkActionButtons={false}`, so this just brought Campaigns in line.
- **Approve/Reject buttons** in `agentActions.jsx` were switched from raw hand-styled `<button>` elements to MUI's `<Button variant="outlined">`, picking up the theme's focus-visible ring and hover states for free instead of hand-maintaining them.

### The dataProvider: a deliberate deviation from the plan

`PLANNING.md` §10 documents this as a deliberate deviation: React-Admin ships `combineDataProviders` for routing by resource name, but `dataProvider.js` doesn't use it. Instead it hand-rolls the whole contract: each resource has a `fetcher` (`fetchCampaigns` hits OneSource360-sim's `/api/campaigns/`, `fetchAgentActions` hits the MCP server's `/agent-actions`), and `getList`/`getOne`/`getMany` all fetch the *full* resource and paginate/sort/filter client-side in JS.

The reason, documented directly in the file's header comment: none of the five backends share a pagination/sort/filter convention (no `json-server`- or `simple-rest`-style headers to standardize on), and building that convention onto five services just to satisfy `combineDataProviders`' expected shape isn't worth it at this data volume — 6 campaigns, a handful of agent actions. `combineDataProviders` would still route *which* fetcher to call per resource; it wouldn't remove the need to handle each backend's actual response shape, so the savings at this scale are smaller than they look. Worth knowing as a real trade-off, not an oversight: this pattern would need revisiting (real server-side pagination) before it scaled past a demo's worth of data.

Two more things worth naming:
- `create`/`update`/`delete`/`updateMany`/`deleteMany` all reject via a shared `notSupported()` helper — deliberate, since Tier 1's frontend is read-only-plus-approve/reject, not general CRUD. Approve/reject don't go through the `dataProvider` contract at all; `approveAction`/`rejectAction` are plain exported functions that call the MCP server's `POST /agent-actions/{id}/approve|reject` directly (`PLANNING.md` §7: deliberately plain REST, not MCP tools, so an agent can never approve its own proposed action).
- `getManyReference` returns an empty result unconditionally — nothing in Tier 1's resource set uses reference fields (e.g. showing a campaign's related agent actions inline), so it's a stub rather than a real implementation.

### The Agent Actions view

`agentActions.jsx` is where `PLANNING.md` §10's "status badge per risk tier... with the agent's plain-language reasoning attached, full technical trace a click away" gets built:

- `OUTCOME_META` maps each stored `AgentToolCall.outcome` value (`auto_execute`, `approved_executed`, `pending_approval`, `blocked`, `rejected`, `error`) to a label and tone for `StatusBadge` (a thin wrapper around `StatusPill`). The stored key is `auto_execute` (matching `policy.route()`); the tool's JSON `status` field uses `auto_executed`. Don't confuse the two.
- The list view's `rationale` column is the plain-language explanation from `05-mcp-servers.md` §7 (written for the approver, not another engineer) — the `Show` page mounts `TechnicalTrace`, which reconstructs the MCP tool → REST call(s) → handler source from `GET /catalog`, and for writes also shows `compute_score` / `policy.route`.
- `ApprovalButtons` only renders when `record.outcome === "pending_approval"` — so the buttons simply don't exist on rows that are already resolved, rather than being present-but-disabled.

### Systems inspector

`/systems` is a custom route (not a react-admin `Resource`). Each platform page joins three things:

1. **Catalog** — `GET http://localhost:8100/catalog` (purpose, expected seed data, endpoint list, tool source, REST mapping)
2. **Live tables** — `GET {service}/api/inspect/` on each Django service (and `/inspect` on the gateway), which serializes that process's own models. This is a snapshot of the logical Postgres database, not the aggregated explorer views.
3. **Operational explorers** — Spots / Creatives / Call Routing / Campaigns remain as `Resource`s for charted, campaign-level views; the Systems page links to them.

The inspect endpoints stay `AllowAny` GET, same as the rest of the local console's reads. Maestro360's `CallEvent` table is thousands of rows; the snapshot pages 50 at a time.

## Key vocabulary

- **`dataProvider`** — the one required adapter object; React-Admin calls its methods (`getList(resource, params)`, etc.) and expects a fixed return shape back (`{ data, total }` for lists, `{ data }` for a single record). Everything else in React-Admin is built on top of this contract.
- **`Resource`** — one entry in `<Admin>` mapping a resource name (must match what the `dataProvider` expects) to the components that render its list/show/edit/create views.
- **`Datagrid`** — the table component used inside `List`; each child field component (`TextField`, `DateField`, `FunctionField`) becomes one column.
- **`FunctionField`** — an escape hatch field type that takes a `render(record)` function instead of just reading one `source` key — used here for the status badge, the risk score fallback (`—` when `null`), and the approve/reject buttons, none of which are plain data display.
- **`useRecordContext` / `useRefresh` / `useNotify`** — React-Admin hooks: the first reads the current row/record inside a field or custom component, the second triggers a data refetch (used after an approve/reject call resolves), the third shows a toast notification.

## Try this yourself

With `docker compose up` running, visit `http://localhost:3000`. React-Admin uses **hash routing** (`/#/campaigns`, `/#/agent_actions`, `/#/systems/onesource360`, …) — a typed path without the `#` silently lands on Overview. Open **Systems → OneSource360** to see the `campaigns_campaign` and `campaigns_dailyperformancerollup` tables live (`GET http://localhost:8001/api/inspect/`). Click a Tool Call (or run an investigation first) and the Show page reconstructs the exact REST URL the MCP container sent. The Campaigns resource is read-only — click into one to see OneSource360-sim's target CPL and dates. The Agent Actions resource is where the guardrail tiers become visible: a `pending_approval` row (if one exists — the demo scenario in `PLANNING.md` §9 produces one via a real `reallocate_budget` call) shows Approve/Reject buttons; clicking either calls the MCP server directly and refreshes the list to show the new outcome.
