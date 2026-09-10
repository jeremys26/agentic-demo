# 08 — React-Admin, Vite, and the Console

**Status**: complete. Overview, Campaigns, Agent Actions, Tool Calls, Systems, operational explorers, and the in-app Guide at `http://localhost:3000`.

## What it is

Three frontend layers stack here:

1. **React** — UI library (components, state, DOM updates)
2. **Vite** — dev server + production bundler (`npm run dev` / `npm run build`)
3. **React-Admin** — framework for admin UIs on top of a data API
4. **MUI (Material UI)** — component/theme library React-Admin builds on

React-Admin's core idea: you declare **`Resource`s** (list/show/edit views for a named collection) and a **`dataProvider`** — an adapter with a fixed contract (`getList`, `getOne`, `getMany`, `create`, `update`, `delete`, …). The framework owns tables, routing, notifications, and layout chrome.

## Why this piece of the stack is used here

Agent360 has **five backends** (four Django sims + MCP gateway). A from-scratch SPA would mean reinventing list/detail/pagination for every resource. React-Admin turns that into "write one adapter." Vite keeps the DX fast (HMR) and the Docker story simple (dev server in a container with `src` bind-mounted).

## Where it lives in this repo

| Path | Role |
|---|---|
| `frontend/package.json` | React 18, react-admin 5, MUI 6, Vite 6 |
| `frontend/vite.config.js` | `host: 0.0.0.0`, port 3000 (reachable from Docker port map) |
| `frontend/src/main.jsx` | Mounts `<App />` |
| `frontend/src/App.jsx` | `<Admin>` + resources + custom routes |
| `frontend/src/dataProvider.js` | Multi-backend adapter |
| `frontend/src/theme.js` | MUI `createTheme` |
| `frontend/src/layout/AppLayout.jsx` / `TopBar.jsx` | Top nav; `sidebar={NoSidebar}` |
| `frontend/src/pages/Overview.jsx` | Dashboard |
| `frontend/src/pages/systems/*` | Per-platform inspector |
| `frontend/src/pages/Faq.jsx` | In-app Guide |
| `frontend/src/resources/*.jsx` | Campaigns, Agent Actions, Tool Calls, Spots, Creatives, Call Routing |
| `frontend/src/trace.js` | Reconstructs MCP → REST from catalog + logged args |
| `frontend/src/components/*` | Charts, StatusPill, TechnicalTrace, SnapshotTable, … |

### Vite env vars (browser-resolved)

Compose sets `VITE_*_URL` to **localhost** host ports (`8001`…`8100`), not Docker DNS names. The JS runs *in your browser*; `fetch()` must hit published ports. Inside the frontend container, Vite only serves assets — it does not proxy API calls.

```js
const ONESOURCE360_URL = import.meta.env.VITE_ONESOURCE360_URL || "http://localhost:8001";
```

### Hash routing

React-Admin defaults to hash URLs: `/#/campaigns`, `/#/systems/onesource360`. A path without `#` silently lands on Overview. Bookmark the hash form.

## The dataProvider — deliberate deviation from the plan

`PLANNING.md` §10 notes React-Admin's `combineDataProviders`. This repo **does not use it**. `dataProvider.js` hand-rolls the contract:

- each resource has a fetcher (`fetchCampaigns` → OneSource360, `fetchAgentActions` → MCP, …)
- `getList` / `getOne` / `getMany` fetch the full collection and **paginate/sort/filter in the browser**

Why: the five backends don't share pagination/sort conventions, and demo volume is tiny (6 campaigns, handful of actions). Teaching five services a json-server-shaped API just to please `combineDataProviders` isn't worth it here. At real scale you'd add server-side pagination and revisit.

Also deliberate:

- `create` / `update` / `delete` / `*Many` → `notSupported()` — console is read-only plus approve/reject
- Approve/reject are **exported helpers**, not `dataProvider` methods — plain `POST` to MCP (`05`: not MCP tools)
- `getManyReference` stubs empty — no reference fields wired

## Resources and custom pages

| UI | Backing API |
|---|---|
| Campaigns | OneSource360 `/api/campaigns/`, `/api/performance/` |
| Agent Actions | MCP `/agent-actions` |
| Tool Calls | MCP `/tool-calls` |
| Spots / Creatives / Call Routing | SmartSpot / Captivator / Maestro |
| Overview | Mix: campaigns + MCP flagged/pending + sweep/simulate |
| Systems | MCP `/catalog` + each service `/api/inspect/` (gateway `/inspect`) |
| Guide | Static FAQ page |

### Agent Actions (three tiers made visible)

`OUTCOME_META` maps stored outcomes (`auto_execute`, `pending_approval`, `blocked`, `approved_executed`, `rejected`, `error`) to labels/tones. Note: stored key `auto_execute` vs tool JSON status `auto_executed` — don't confuse them.

- List: plain-language `rationale` for the approver
- Show: `TechnicalTrace` reconstructs tool → REST URL(s) → handler source; writes also show scoring/policy
- `ApprovalButtons` only when `outcome === "pending_approval"`

### Systems inspector

Custom route (not a `Resource`). Each platform page joins:

1. Catalog (purpose, seed expectations, endpoints, tool source)
2. Live table snapshot (`inspect`)
3. Links to operational explorers

Maestro360's `CallEvent` table is huge; inspect pages 50 rows at a time.

## Theme notes (inspired, not cloned)

Custom MUI theme: accent sampled from BMG360's public site as *inspiration*, Fraunces + Inter (licensed free) echoing a serif/grotesk pairing without using Klim commercial fonts, soft tinted background. Logo/marketing layout intentionally omitted — this is an admin console. Details and rationale remain in `theme.js` / earlier project notes; the learning point is: **theme tokens live in one `createTheme` object**, and React-Admin picks them up via `<Admin theme={theme}>`.

## Charts and explainers

| Component | Used for |
|---|---|
| `LineTrendChart` | Campaign CPL vs target |
| `VarianceBarChart` | Overview portfolio variance |
| `WeeklyPoolShareChart` | Maestro pool shift story |
| `ResourceExplainer` | Short "what is this page" blurbs |
| `StatusPill` / `IconTag` | Shared status and row icons |

## Build & CI

```bash
cd frontend && npm ci && npm run build
```

GitHub Actions runs that production build on every push (`15-ci-github-actions.md`). Docker Compose runs the **dev** server with `src` bind-mounted for live edits.

## Key vocabulary

- **`dataProvider`** — required adapter; React-Admin expects `{ data, total }` for lists, `{ data }` for one record.
- **`Resource`** — name + list/show components registered on `<Admin>`.
- **`Datagrid` / `FunctionField`** — table columns; `FunctionField` for custom render (badges, buttons).
- **`useRecordContext` / `useRefresh` / `useNotify`** — current row, refetch after approve, toast.
- **Vite / `import.meta.env`** — build-time env exposed to client code (`VITE_` prefix).
- **HMR** — hot module replacement; save a file, browser updates without full reload.
- **Hash router** — routing via `location.hash`; works well without server path rewrites.

## Try this yourself

With Compose up, open `http://localhost:3000`:

1. Overview — one flagged campaign after a clean `mcp_server` restart
2. Systems → OneSource360 — live `campaigns_campaign` tables
3. Run an investigation in Claude Code, then Tool Calls → Show → technical trace
4. Agent Actions — Approve/Reject on a `pending_approval` row if the demo produced one

**Next:** `09-docker-compose.md` for how this frontend container sits in the network with everyone else.
