// Reconstruct the HTTP the MCP server sends for a tool call, from the
// catalog's rest mapping + the logged arguments. Empty-string optional
// args are omitted, matching the Python tools.

const WHEN_LABEL = {
  always: "Every invocation",
  on_execute: "Only if the guardrail allows execution",
  per_active_campaign: "Once per active campaign",
  per_spot: "Once per spot",
  per_creative: "Once per creative",
};

export function whenLabel(when) {
  return WHEN_LABEL[when] || when || "Every invocation";
}

export function reconstructRequests(tool, args, platform) {
  if (!tool?.rest?.length) return [];
  const arguments_ = args || {};
  return tool.rest.map((call) => {
    let path = call.path;
    path = path.replace(/\{(\w+)\}/g, (_, key) => {
      const value = arguments_[key];
      return value != null && value !== "" ? String(value) : `{${key}}`;
    });
    const params = new URLSearchParams();
    for (const [arg, queryKey] of Object.entries(call.query_from || {})) {
      const value = arguments_[arg];
      if (value != null && value !== "") params.set(queryKey, String(value));
    }
    const query = params.toString();
    const relative = query ? `${path}?${query}` : path;
    let body = null;
    if (call.body_from?.length) {
      body = {};
      for (const key of call.body_from) {
        if (arguments_[key] != null) body[key] = arguments_[key];
      }
    }
    return {
      method: call.method,
      when: call.when || "always",
      notes: call.notes || "",
      path: relative,
      mcpUrl: platform ? `${platform.internal_base}${relative}` : relative,
      body,
    };
  });
}

export function requestFired(when, outcome) {
  if (when !== "on_execute") return true;
  return outcome === "auto_execute" || outcome === "approved_executed";
}
