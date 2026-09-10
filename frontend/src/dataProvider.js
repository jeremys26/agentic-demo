// Custom data provider (PLANNING.md §10): the five backends don't share a
// pagination/sort/filter convention (no json-server or simple-rest style
// headers), and retrofitting one onto five services for a local demo with
// a handful of records each isn't worth it — so this fetches each
// resource's full list and paginates/sorts client-side instead. Reasonable
// at this scale (6 campaigns, a handful of agent actions); would need
// revisiting before this pattern scaled to real data volume.

const ONESOURCE360_URL = import.meta.env.VITE_ONESOURCE360_URL || "http://localhost:8001";
const SMARTSPOT360_URL = import.meta.env.VITE_SMARTSPOT360_URL || "http://localhost:8002";
const CAPTIVATOR360_URL = import.meta.env.VITE_CAPTIVATOR360_URL || "http://localhost:8003";
const MAESTRO360_URL = import.meta.env.VITE_MAESTRO360_URL || "http://localhost:8004";
const MCP_SERVER_URL = import.meta.env.VITE_MCP_SERVER_URL || "http://localhost:8100";
const RANKPULSE_URL = import.meta.env.VITE_RANKPULSE_URL || "http://localhost:8005";

export { ONESOURCE360_URL, SMARTSPOT360_URL, CAPTIVATOR360_URL, MAESTRO360_URL, MCP_SERVER_URL, RANKPULSE_URL };

function paginate(records, pagination) {
  if (!pagination) return records;
  const { page, perPage } = pagination;
  const start = (page - 1) * perPage;
  return records.slice(start, start + perPage);
}

// DRF's DecimalField serializes as a JSON string (e.g. target_cpl: "45.00"),
// so a plain `<`/`>` comparison sorts numeric columns lexicographically
// ("9.00" > "45.00"). Compare numerically whenever both values parse as
// numbers; fall back to string comparison for genuinely non-numeric fields.
function compareValues(a, b) {
  const na = typeof a === "number" ? a : Number(a);
  const nb = typeof b === "number" ? b : Number(b);
  const bothNumeric = a !== "" && b !== "" && a != null && b != null && !Number.isNaN(na) && !Number.isNaN(nb);
  if (bothNumeric) return na - nb;
  if (a < b) return -1;
  if (a > b) return 1;
  return 0;
}

function sortRecords(records, sort) {
  if (!sort || !sort.field) return records;
  const { field, order } = sort;
  const dir = order === "DESC" ? -1 : 1;
  return [...records].sort((a, b) => {
    const cmp = compareValues(a[field], b[field]);
    if (cmp !== 0) return cmp * dir;
    return a.id - b.id;
  });
}

// PLANNING.md §9's own flagging rule ("rollup CPL crosses target by >15%")
// — reused here so the frontend flags campaigns by the same definition the
// project's own scenario is built around, not an invented UI threshold.
export const ANOMALY_THRESHOLD_PCT = 15;

async function fetchCampaignsRaw() {
  const response = await fetch(`${ONESOURCE360_URL}/api/campaigns/`);
  if (!response.ok) throw new Error("Failed to fetch campaigns");
  return response.json();
}

// Full daily rollups + summary for one campaign — exported for the Campaign
// Show page's performance chart, and reused below to decorate the list with
// each campaign's current CPL variance (PLANNING.md §10: "React-Admin shows
// it flagged").
export async function fetchCampaignPerformance(campaignId) {
  const response = await fetch(`${ONESOURCE360_URL}/api/performance/?campaign_id=${campaignId}`);
  if (!response.ok) throw new Error(`Failed to fetch performance for campaign ${campaignId}`);
  return response.json();
}

// Mirrors get_performance_anomalies' own math (mcp_server/tools/onesource360.py)
// exactly: a blended CPL over the trailing `windowDays` rollups, not a
// lifetime average — a short spike gets diluted into noise if averaged
// across a campaign's whole history, which is what made the lifetime
// `summary.cpl_variance_pct` from /api/performance/ under-report campaign 1's
// real, current anomaly. Exported so the Show page's flagged banner uses the
// identical definition as the List's badge.
export function windowedCplVariance(dailyRollups, targetCpl, windowDays = 7) {
  const window = dailyRollups.slice(-windowDays);
  const totalSpend = window.reduce((sum, r) => sum + parseFloat(r.spend), 0);
  const totalLeads = window.reduce((sum, r) => sum + r.leads, 0);
  if (window.length === 0 || totalLeads === 0) return { windowedCpl: null, variancePct: null };
  const windowedCpl = totalSpend / totalLeads;
  const variancePct = ((windowedCpl - targetCpl) / targetCpl) * 100;
  return { windowedCpl, variancePct };
}

async function fetchCampaigns() {
  const campaigns = await fetchCampaignsRaw();
  const performances = await Promise.all(
    campaigns.map((c) => fetchCampaignPerformance(c.id).catch(() => null))
  );
  return campaigns.map((c, i) => {
    const perf = performances[i];
    const { windowedCpl, variancePct } = perf
      ? windowedCplVariance(perf.daily_rollups, Number(c.target_cpl))
      : { windowedCpl: null, variancePct: null };
    return {
      ...c,
      avg_cpl: windowedCpl,
      cpl_variance_pct: variancePct != null ? Math.round(variancePct * 10) / 10 : null,
      flagged: variancePct != null && variancePct > ANOMALY_THRESHOLD_PCT,
    };
  });
}

// --- Captivator360 (creative performance) drill-down ---

// Full daily CTR history + summary for one creative — exported for
// the Creatives Show page's trend chart.
export async function fetchCreativePerformance(creativeId) {
  const response = await fetch(`${CAPTIVATOR360_URL}/api/creatives/${creativeId}/performance/`);
  if (!response.ok) throw new Error(`Failed to fetch performance for creative ${creativeId}`);
  return response.json();
}

async function fetchSpots() {
  const [spotsResponse, namesById] = await Promise.all([
    fetch(`${SMARTSPOT360_URL}/api/spots/`),
    campaignNameById(),
  ]);
  if (!spotsResponse.ok) throw new Error("Failed to fetch spots");
  const spots = await spotsResponse.json();
  const withPerf = await Promise.all(
    spots.map((spot) =>
      fetch(`${SMARTSPOT360_URL}/api/spots/${spot.id}/performance/`)
        .then((r) => (r.ok ? r.json() : null))
        .then((detail) => ({
          ...spot,
          campaign_name: namesById[spot.campaign_id] ?? null,
          station_medium: detail?.station_medium,
          calls: detail?.performance?.calls,
          conversions: detail?.performance?.conversions,
          cpl: detail?.performance?.cpl,
        }))
        .catch(() => ({ ...spot, campaign_name: namesById[spot.campaign_id] ?? null }))
    )
  );
  return withPerf;
}

async function fetchCreatives() {
  const campaigns = await fetchCampaignsRaw();
  const perCampaign = await Promise.all(
    campaigns.map((c) =>
      fetch(`${CAPTIVATOR360_URL}/api/creatives/?campaign_id=${c.id}`)
        .then((r) => (r.ok ? r.json() : []))
        .then((creatives) => creatives.map((cr) => ({ ...cr, campaign_name: c.name })))
        .catch(() => [])
    )
  );
  const flat = perCampaign.flat();
  const withLatest = await Promise.all(
    flat.map((cr) =>
      fetchCreativePerformance(cr.id)
        .then((p) => ({ ...cr, ...p.summary }))
        .catch(() => cr)
    )
  );
  return withLatest;
}

// --- Maestro360 (call routing) drill-down — one record per campaign, since
// the meaningful unit here is "how is this campaign's call volume being
// routed," not an individual call. ---

export async function fetchCallSummary(campaignId) {
  const response = await fetch(`${MAESTRO360_URL}/api/calls/summary/?campaign_id=${campaignId}`);
  if (!response.ok) throw new Error(`Failed to fetch call summary for campaign ${campaignId}`);
  return response.json();
}

// Raw call events for one campaign — exported for the Show page's weekly
// pool-share trend chart (a few hundred KB for a fully-seeded campaign;
// fetched once per Show view, not from the List).
export async function fetchCallEvents(campaignId) {
  const response = await fetch(`${MAESTRO360_URL}/api/calls/?campaign_id=${campaignId}`);
  if (!response.ok) throw new Error(`Failed to fetch call events for campaign ${campaignId}`);
  return response.json();
}

async function fetchCallRouting() {
  const campaigns = await fetchCampaignsRaw();
  const summaries = await Promise.all(campaigns.map((c) => fetchCallSummary(c.id).catch(() => null)));
  return campaigns.map((c, i) => {
    const summary = summaries[i];
    const uncertified = summary?.pool_distribution?.find((p) => !p.is_certified_medicare);
    return {
      id: c.id,
      campaign_id: c.id,
      campaign_name: c.name,
      total_calls: summary?.total_calls ?? 0,
      pool_distribution: summary?.pool_distribution ?? [],
      outcome_breakdown: summary?.outcome_breakdown ?? {},
      uncertified_pct: uncertified?.pct_of_total ?? 0,
    };
  });
}

// Shared id->name lookup so Agent Actions / Tool Calls rows can show which
// campaign they're about (most tool arguments carry a campaign_id already;
// this just resolves it to a readable name) without pulling in the heavier
// performance-decorated fetchCampaigns() above.
async function campaignNameById() {
  const campaigns = await fetchCampaignsRaw();
  return Object.fromEntries(campaigns.map((c) => [c.id, c.name]));
}

function withCampaignName(records, namesById) {
  return records.map((r) => {
    const campaignId = r.campaign_id ?? r.arguments?.campaign_id ?? null;
    return {
      ...r,
      campaign_id: campaignId,
      campaign_name: campaignId ? namesById[campaignId] ?? null : null,
    };
  });
}

async function fetchAgentActions() {
  const [response, namesById] = await Promise.all([
    fetch(`${MCP_SERVER_URL}/agent-actions`),
    campaignNameById(),
  ]);
  if (!response.ok) throw new Error("Failed to fetch agent actions");
  const body = await response.json();
  return withCampaignName(body.data, namesById);
}

async function fetchToolCalls() {
  const [response, namesById] = await Promise.all([
    fetch(`${MCP_SERVER_URL}/tool-calls`),
    campaignNameById(),
  ]);
  if (!response.ok) throw new Error("Failed to fetch tool calls");
  const body = await response.json();
  return withCampaignName(body.data, namesById);
}

const FETCHERS = {
  campaigns: fetchCampaigns,
  agent_actions: fetchAgentActions,
  tool_calls: fetchToolCalls,
  creatives: fetchCreatives,
  call_routing: fetchCallRouting,
  spots: fetchSpots,
};

function notSupported(method) {
  return async () => {
    throw new Error(`${method} is not supported — this frontend is read-only plus approve/reject`);
  };
}

export const dataProvider = {
  getList: async (resource, params) => {
    const fetcher = FETCHERS[resource];
    if (!fetcher) throw new Error(`Unknown resource: ${resource}`);
    const all = sortRecords(await fetcher(), params.sort);
    return { data: paginate(all, params.pagination), total: all.length };
  },

  getOne: async (resource, params) => {
    const fetcher = FETCHERS[resource];
    if (!fetcher) throw new Error(`Unknown resource: ${resource}`);
    const all = await fetcher();
    const record = all.find((r) => String(r.id) === String(params.id));
    if (!record) throw new Error(`${resource} record ${params.id} not found`);
    return { data: record };
  },

  getMany: async (resource, params) => {
    const fetcher = FETCHERS[resource];
    if (!fetcher) throw new Error(`Unknown resource: ${resource}`);
    const all = await fetcher();
    return { data: all.filter((r) => params.ids.some((id) => String(id) === String(r.id))) };
  },

  getManyReference: async () => ({ data: [], total: 0 }),
  create: notSupported("create"),
  update: notSupported("update"),
  updateMany: notSupported("updateMany"),
  delete: notSupported("delete"),
  deleteMany: notSupported("deleteMany"),
};

// --- Anomaly sweep (PLANNING.md §8) — not a react-admin resource,
// just two direct calls the Overview page uses to show the automated,
// LLM-free Celery sweep's own audit log alongside the frontend's own live
// client-side flagging above. ---

export async function fetchFlaggedCampaigns() {
  const response = await fetch(`${MCP_SERVER_URL}/flagged-campaigns`);
  if (!response.ok) throw new Error("Failed to fetch flagged campaigns");
  const body = await response.json();
  return body.data;
}

export async function triggerAnomalySweep() {
  const response = await fetch(`${MCP_SERVER_URL}/flagged-campaigns/sweep`, { method: "POST" });
  return response.json();
}

export async function simulateNextDay() {
  const response = await fetch(`${MCP_SERVER_URL}/simulate-next-day`, { method: "POST" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Failed to simulate next day");
  }
  return response.json();
}

// Not part of the react-admin dataProvider contract — these back the
// Agent Actions view's Approve/Reject buttons directly (PLANNING.md §7:
// plain REST, not an MCP tool, since only a human approves/rejects).
export async function approveAction(proposedActionId) {
  const response = await fetch(`${MCP_SERVER_URL}/agent-actions/${proposedActionId}/approve`, {
    method: "POST",
  });
  return response.json();
}

export async function rejectAction(proposedActionId) {
  const response = await fetch(`${MCP_SERVER_URL}/agent-actions/${proposedActionId}/reject`, {
    method: "POST",
  });
  return response.json();
}

export async function fetchCatalog() {
  const response = await fetch(`${MCP_SERVER_URL}/catalog`);
  if (!response.ok) throw new Error("Failed to fetch catalog");
  return response.json();
}

const PLATFORM_BASE_BY_SLUG = {
  onesource360: ONESOURCE360_URL,
  smartspot360: SMARTSPOT360_URL,
  captivator360: CAPTIVATOR360_URL,
  maestro360: MAESTRO360_URL,
  rankpulse: RANKPULSE_URL,
  agent360: MCP_SERVER_URL,
};

export function inspectBase(platform) {
  return PLATFORM_BASE_BY_SLUG[platform?.slug] || "";
}

export function inspectUrl(platform) {
  const base = inspectBase(platform);
  if (!base) return null;
  const path = platform.inspect_path || "/api/inspect/";
  return `${base}${path}`;
}

export async function fetchInspect(platform, { table, limit = 50, offset = 0 } = {}) {
  const base = inspectUrl(platform);
  if (!base) throw new Error("Platform has no inspect URL");
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (table) params.set("table", table);
  const response = await fetch(`${base}?${params.toString()}`);
  if (!response.ok) throw new Error(`Failed to inspect ${platform.slug || "platform"}`);
  return response.json();
}
