// Plain-language labels for tool names, action kinds, and risk scores.
// The APIs speak snake_case; the console should not.

export const TOOL_LABELS = {
  reallocate_budget: "Reallocate budget",
  request_creative_refresh: "Refresh creative",
  get_campaign_performance: "Get campaign performance",
  list_campaigns: "List campaigns",
  get_performance_anomalies: "Find performance anomalies",
  get_spot_performance: "Get spot performance",
  get_budget_recommendation: "Get budget recommendation",
  get_creative_performance: "Get creative performance",
  get_declining_creatives: "Find declining creatives",
  get_fatigued_creatives: "Find declining creatives", // older tool name still present in some audit logs
  get_call_quality: "Get call quality",
  get_routing_summary: "Get routing summary",
  get_organic_performance: "Get organic performance",
};

export function formatToolName(name) {
  if (!name) return "—";
  return TOOL_LABELS[name] || name.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export function formatKind(kind) {
  if (kind === "read") return "Lookup";
  if (kind === "write") return "Change";
  return kind || "—";
}

export function sentenceCase(value) {
  if (!value) return "—";
  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// Matches mcp_server/guardrails/policy.py defaults. Used only to color the
// number — the Status column is the source of truth for what actually happened.
export const RISK_AUTO_EXECUTE = 30;
export const RISK_BLOCK = 70;

export function riskColor(score) {
  const n = Number(score);
  if (Number.isNaN(n)) return "#5B6270";
  if (n >= RISK_BLOCK) return "#B42318";
  if (n >= RISK_AUTO_EXECUTE) return "#9A6700";
  return "#166534";
}

export function formatRisk(score) {
  if (score == null || score === "") return null;
  const n = Number(score);
  if (Number.isNaN(n)) return null;
  return n.toFixed(0);
}
