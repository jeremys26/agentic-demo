import { useCallback, useEffect, useMemo, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";
import { Title } from "react-admin";
import { Box, CircularProgress, Link as MuiLink, Typography } from "@mui/material";
import StatusPill from "../../components/StatusPill";
import CodeBlock from "../../components/CodeBlock";
import SnapshotTable from "../../components/SnapshotTable";
import Collapsible from "../../components/Collapsible";
import PageHeader, { JUMP_CHIP_SX } from "../../components/PageHeader";
import { fetchCatalog, fetchInspect, inspectBase } from "../../dataProvider";
import { reconstructRequests, whenLabel } from "../../trace";
import { formatKind, formatToolName } from "../../labels";

const METHOD_TONE = { GET: "info", POST: "warning", PUT: "neutral", PATCH: "neutral", DELETE: "error" };

const NAV_ITEMS = [
  ["what", "What it does"],
  ["tables", "Live tables"],
  ["endpoints", "REST endpoints"],
  ["tools", "MCP tools"],
];

// Each MCP tool ships full request/response mechanics plus its Python
// source — collapsed by default so opening "MCP tools" doesn't dump every
// tool's handler source onto the page at once.
const ToolEntry = ({ tool, platform }) => {
  const requests = reconstructRequests(tool, { campaign_id: 1 }, platform);
  return (
    <Collapsible
      layout="row"
      defaultExpanded={false}
      subtitle={tool.description}
      title={
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
          <Typography sx={{ fontWeight: 700, fontSize: 14 }}>
            {formatToolName(tool.name)}
          </Typography>
          <Typography sx={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace", fontSize: 12, color: "text.secondary" }}>
            {tool.name}
          </Typography>
          <StatusPill label={formatKind(tool.kind)} tone={tool.kind === "write" ? "warning" : "info"} />
        </Box>
      }
    >
      <Typography sx={{ fontSize: 13, color: "text.secondary", lineHeight: 1.55, mb: 1, whiteSpace: "pre-wrap" }}>
        {tool.description}
      </Typography>
      <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 1 }}>
        Parameters:{" "}
        {tool.parameters?.length
          ? tool.parameters.map((param) => `${param.name}: ${param.type}${param.required ? "" : "?"}`).join(", ")
          : "none"}
      </Typography>
      {requests.map((call, index) => (
        <Box key={`${call.method}-${call.mcpUrl}-${index}`} sx={{ mb: 1, pl: 1.5, borderLeft: "3px solid", borderColor: "primary.main" }}>
          <Box sx={{ display: "flex", gap: 1, alignItems: "center", mb: 0.25, flexWrap: "wrap" }}>
            <StatusPill label={call.method} tone={METHOD_TONE[call.method] || "neutral"} />
            <StatusPill label={whenLabel(call.when)} tone="neutral" />
          </Box>
          <Typography sx={{ fontSize: 12, fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace", wordBreak: "break-all" }}>
            {call.mcpUrl}
          </Typography>
          {call.notes ? (
            <Typography sx={{ fontSize: 12, color: "text.secondary", mt: 0.25 }}>{call.notes}</Typography>
          ) : null}
          {call.body ? <pre style={{ marginTop: 6 }}>{JSON.stringify(call.body, null, 2)}</pre> : null}
        </Box>
      ))}
      <CodeBlock label="Handler" file={tool.source_file}>
        {tool.source}
      </CodeBlock>
    </Collapsible>
  );
};

const SystemPage = () => {
  const { slug } = useParams();
  const [catalog, setCatalog] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState({ what: true, tables: false, endpoints: false, tools: false });

  const platform = catalog?.platforms?.find((item) => item.slug === slug);

  useEffect(() => {
    setCatalog(null);
    setSnapshot(null);
    setError(null);
    fetchCatalog()
      .then(setCatalog)
      .catch((err) => setError(err.message || "Failed to load catalog"));
  }, [slug]);

  useEffect(() => {
    if (!platform) return undefined;
    let cancelled = false;
    fetchInspect(platform)
      .then((payload) => {
        if (!cancelled) setSnapshot(payload);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Failed to load tables");
      });
    return () => {
      cancelled = true;
    };
  }, [platform]);

  const pageTable = useCallback(
    async (dbTable, offset) => {
      if (!platform) return;
      const payload = await fetchInspect(platform, { table: dbTable, offset });
      const next = payload.tables?.[0];
      if (!next) return;
      setSnapshot((current) => ({
        ...payload,
        tables: (current?.tables || []).map((table) => (table.db_table === dbTable ? next : table)),
      }));
    },
    [platform]
  );

  const tools = useMemo(() => {
    if (!catalog || !platform) return [];
    return catalog.tools.filter((tool) => platform.tools.includes(tool.name));
  }, [catalog, platform]);

  const purposeByTable = useMemo(() => {
    const map = {};
    for (const table of platform?.tables || []) map[table.db_table] = table.purpose;
    return map;
  }, [platform]);

  const expandAndScroll = useCallback((id) => {
    setExpanded((prev) => ({ ...prev, [id]: true }));
    requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, []);

  if (error && !catalog) {
    return (
      <Box sx={{ p: 1 }}>
        <Title title="Systems" />
        <Typography sx={{ color: "#B42318", fontSize: 14 }}>{error}</Typography>
      </Box>
    );
  }

  if (!catalog) {
    return (
      <Box sx={{ p: 1, color: "text.secondary", display: "flex", alignItems: "center", gap: 1.5 }}>
        <Title title="Systems" />
        <CircularProgress size={18} />
        Loading…
      </Box>
    );
  }

  if (!platform) {
    return (
      <Box sx={{ p: 1 }}>
        <Title title="Systems" />
        <Typography>
          Unknown system.{" "}
          <MuiLink component={RouterLink} to="/systems">
            Back to Systems
          </MuiLink>
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ width: "100%", maxWidth: 1200, mx: "auto" }}>
      <Title title={platform.name} />
      <PageHeader
        title={platform.name}
        subtitle={`${platform.role}${platform.database ? ` · Postgres database \`${platform.database}\`` : " · no Postgres (in-memory)"}`}
        backTo="/systems"
        backLabel="All systems"
      />

      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 3 }}>
        {NAV_ITEMS.map(([id, label]) => (
          <MuiLink
            key={id}
            component="button"
            type="button"
            onClick={() => expandAndScroll(id)}
            sx={JUMP_CHIP_SX}
          >
            {label}
          </MuiLink>
        ))}
        {platform.operational_path ? (
          <MuiLink component={RouterLink} to={platform.operational_path} sx={JUMP_CHIP_SX}>
            {platform.operational_label} →
          </MuiLink>
        ) : null}
        {platform.docs_path ? (
          <MuiLink
            href={`${inspectBase(platform)}${platform.docs_path}`}
            target="_blank"
            rel="noreferrer"
            sx={JUMP_CHIP_SX}
          >
            OpenAPI →
          </MuiLink>
        ) : null}
      </Box>

      <Collapsible
        id="what"
        title="What this system is"
        expanded={expanded.what}
        onToggle={() => setExpanded((prev) => ({ ...prev, what: !prev.what }))}
      >
        <Typography sx={{ fontSize: 14, lineHeight: 1.65, mb: 1.5 }}>{platform.purpose}</Typography>
        <Typography sx={{ fontSize: 13, color: "text.secondary", lineHeight: 1.65 }}>
          <strong>What the seeded data is supposed to look like. </strong>
          {platform.expected_data}
        </Typography>
        {platform.slug === "rankpulse" && !platform.registered ? (
          <Typography sx={{ fontSize: 13, color: "#9A6700", mt: 1.5 }}>
            RankPulse is running but not in the agent&apos;s tool list yet. Uncomment{" "}
            <code>import tools.rankpulse</code> in <code>mcp_server/main.py</code> and rebuild{" "}
            <code>mcp_server</code> to register <code>get_organic_performance</code>.
          </Typography>
        ) : null}
      </Collapsible>

      <Collapsible
        id="tables"
        title="Live tables"
        subtitle={snapshot ? `${(snapshot.tables || []).length} table${(snapshot.tables || []).length === 1 ? "" : "s"}` : undefined}
        expanded={expanded.tables}
        onToggle={() => setExpanded((prev) => ({ ...prev, tables: !prev.tables }))}
      >
        <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2, lineHeight: 1.6 }}>
          Direct snapshot of {platform.database ? `the \`${platform.database}\` Postgres database` : "the in-memory dataset"} via{" "}
          <code>GET {platform.inspect_path}</code>
          . This is the data an MCP tool reads — not a chart, the rows.
        </Typography>
        {error ? (
          <Typography sx={{ color: "#B42318", fontSize: 13, mb: 1 }}>{error}</Typography>
        ) : null}
        {!snapshot && !error ? (
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, color: "text.secondary" }}>
            <CircularProgress size={16} /> Loading tables…
          </Box>
        ) : null}
        {snapshot
          ? (snapshot.tables || []).map((table) => (
              <SnapshotTable
                key={table.db_table}
                table={{ ...table, database: snapshot.database }}
                purpose={purposeByTable[table.db_table]}
                onPage={(offset) => pageTable(table.db_table, offset)}
              />
            ))
          : null}
      </Collapsible>

      <Collapsible
        id="endpoints"
        title="REST endpoints"
        subtitle={`${(platform.endpoints || []).length} endpoint${(platform.endpoints || []).length === 1 ? "" : "s"}`}
        expanded={expanded.endpoints}
        onToggle={() => setExpanded((prev) => ({ ...prev, endpoints: !prev.endpoints }))}
      >
        <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2, lineHeight: 1.6 }}>
          These are the HTTP paths this process actually serves. MCP tools never query Postgres
          themselves — they call one of these. Writes (webhooks, apply, refresh) require a JWT or{" "}
          <code>X-Service-Token</code>; list/detail GETs stay open so this console can read them.
        </Typography>
        <Box sx={{ overflowX: "auto" }}>
          <Box
            component="table"
            sx={{
              borderCollapse: "collapse",
              width: "100%",
              minWidth: 640,
              fontSize: 13,
              "& th, & td": { padding: "10px 12px", borderBottom: "1px solid rgba(20, 22, 31, 0.08)", verticalAlign: "top" },
              "& th": {
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.04em",
                textTransform: "uppercase",
                color: "text.secondary",
                textAlign: "left",
              },
            }}
          >
            <thead>
              <tr>
                <th>Method</th>
                <th>Path</th>
                <th>Auth</th>
                <th>What it returns / does</th>
              </tr>
            </thead>
            <tbody>
              {(platform.endpoints || []).map((endpoint) => (
                <tr key={`${endpoint.method}-${endpoint.path}`}>
                  <td>
                    <StatusPill label={endpoint.method} tone={METHOD_TONE[endpoint.method] || "neutral"} />
                  </td>
                  <td style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace", wordBreak: "break-all" }}>
                    {endpoint.path}
                  </td>
                  <td>{endpoint.auth}</td>
                  <td>{endpoint.purpose}</td>
                </tr>
              ))}
            </tbody>
          </Box>
        </Box>
      </Collapsible>

      <Collapsible
        id="tools"
        title="MCP tools"
        subtitle={platform.slug === "agent360" ? "Gateway + guardrail scoring" : `${tools.length} tool${tools.length === 1 ? "" : "s"}`}
        expanded={expanded.tools}
        onToggle={() => setExpanded((prev) => ({ ...prev, tools: !prev.tools }))}
      >
        {platform.slug === "agent360" ? (
          <>
            <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2, lineHeight: 1.6 }}>
              The gateway does not expose domain tools of its own — it <em>is</em> the tool
              layer. Every other platform&apos;s tools are registered here. Write tools go through
              the scoring function below before any REST write fires.
            </Typography>
            {catalog.guardrail ? (
              <>
                <Typography sx={{ fontSize: 13, mb: 1 }}>
                  Thresholds: auto-execute &lt; {catalog.guardrail.auto_execute_threshold}, block ≥{" "}
                  {catalog.guardrail.block_threshold}, reallocate hard cap{" "}
                  {catalog.guardrail.reallocate_hard_cap_pct}% of weekly spend.
                </Typography>
                <CodeBlock label="policy.route" file={catalog.guardrail.policy_file}>
                  {catalog.guardrail.policy_source}
                </CodeBlock>
                <CodeBlock label="compute_score" file={catalog.guardrail.scoring_file}>
                  {catalog.guardrail.scoring_source}
                </CodeBlock>
              </>
            ) : null}
          </>
        ) : tools.length === 0 ? (
          <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
            No MCP tools registered for this service right now.
          </Typography>
        ) : (
          tools.map((tool) => <ToolEntry key={tool.name} tool={tool} platform={platform} />)
        )}
      </Collapsible>
    </Box>
  );
};

export default SystemPage;
