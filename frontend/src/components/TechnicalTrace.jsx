import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useRecordContext } from "react-admin";
import { Box, Link as MuiLink, Typography } from "@mui/material";
import CodeBlock from "./CodeBlock";
import StatusPill from "./StatusPill";
import Collapsible from "./Collapsible";
import { fetchCatalog } from "../dataProvider";
import { reconstructRequests, requestFired, whenLabel } from "../trace";
import { formatKind, formatToolName } from "../labels";

const METHOD_TONE = { GET: "info", POST: "warning", PUT: "neutral", PATCH: "neutral", DELETE: "error" };

function HttpCall({ call, fired }) {
  return (
    <Box
      sx={{
        mb: 1.5,
        opacity: fired ? 1 : 0.55,
        borderLeft: "3px solid",
        borderColor: fired ? "primary.main" : "divider",
        pl: 1.5,
      }}
    >
      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5, flexWrap: "wrap" }}>
        <StatusPill label={call.method} tone={METHOD_TONE[call.method] || "neutral"} />
        <StatusPill label={whenLabel(call.when)} tone={fired ? "success" : "neutral"} />
        {!fired && <StatusPill label="Did not fire" tone="neutral" />}
      </Box>
      <Typography sx={{ fontSize: 13, fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace", wordBreak: "break-all" }}>
        {call.mcpUrl}
      </Typography>
      {call.notes ? (
        <Typography sx={{ fontSize: 12, color: "text.secondary", mt: 0.5 }}>{call.notes}</Typography>
      ) : null}
      {call.body && Object.keys(call.body).length > 0 ? (
        <pre style={{ marginTop: 8 }}>{JSON.stringify(call.body, null, 2)}</pre>
      ) : null}
    </Box>
  );
}

export default function TechnicalTrace({ record: recordProp, includeGuardrail }) {
  const contextRecord = useRecordContext();
  const record = recordProp ?? contextRecord;
  const [catalog, setCatalog] = useState(null);

  useEffect(() => {
    fetchCatalog()
      .then(setCatalog)
      .catch(() => setCatalog(null));
  }, []);

  if (!record) return null;

  const tool = catalog?.tools?.find((item) => item.name === record.tool_name);
  const serviceSlug = record.service || tool?.service;
  const platform = catalog?.platforms?.find((item) => item.slug === serviceSlug);
  const requests = reconstructRequests(tool, record.arguments, platform);
  const risk = record.risk_breakdown;
  const showGuardrail = includeGuardrail && (record.kind === "write" || Boolean(risk));

  return (
    <Box sx={{ mt: 2, gridColumn: "1 / -1" }}>
      <Collapsible
        title="Technical trace"
        defaultExpanded={false}
        subtitle="Exact tool call, REST requests, arguments/result, and guardrail scoring"
      >
        <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2, lineHeight: 1.6 }}>
          Plain-language reasoning is above. This is the deterministic path: which MCP
          tool ran, which REST calls it mapped to, the JSON that went in and came back,
          and the Python that executed.
        </Typography>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          <Box>
            <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "text.secondary", mb: 0.5 }}>
              1. Agent invoked
            </Typography>
            <Typography sx={{ fontWeight: 600 }}>
              {formatToolName(record.tool_name)}
              {tool ? ` · ${formatKind(tool.kind)}` : ""}
              {platform ? (
                <>
                  {" · "}
                  <MuiLink component={RouterLink} to={`/systems/${platform.slug}`}>
                    {platform.name}
                  </MuiLink>
                </>
              ) : null}
            </Typography>
          </Box>

          <Box>
            <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "text.secondary", mb: 0.5 }}>
              2. MCP handler
            </Typography>
            <Typography sx={{ fontSize: 13, fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}>
              {tool?.source_file || "—"}
            </Typography>
          </Box>

          <Box>
            <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "text.secondary", mb: 0.5 }}>
              3. REST calls this tool makes
            </Typography>
            {requests.length === 0 ? (
              <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
                {!catalog
                  ? "Loading catalog…"
                  : tool
                    ? "No REST mapping on this tool."
                    : "This tool is not in the current registry (RankPulse stays unregistered until onboarded). Arguments and result below are still the logged call."}
              </Typography>
            ) : (
              requests.map((call, index) => (
                <HttpCall key={`${call.method}-${call.mcpUrl}-${index}`} call={call} fired={requestFired(call.when, record.outcome)} />
              ))
            )}
          </Box>

          <Box>
            <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "text.secondary", mb: 0.5 }}>
              4. Arguments
            </Typography>
            <pre>{JSON.stringify(record.arguments, null, 2)}</pre>
          </Box>

          <Box>
            <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "text.secondary", mb: 0.5 }}>
              5. Result (logged summary)
            </Typography>
            <pre>{JSON.stringify(record.result_summary, null, 2)}</pre>
          </Box>

          {record.pre_action_state ? (
            <Box>
              <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "text.secondary", mb: 0.5 }}>
                6. Pre-action snapshot (audit)
              </Typography>
              <pre>{JSON.stringify(record.pre_action_state, null, 2)}</pre>
            </Box>
          ) : null}

          {showGuardrail ? (
            <Box>
              <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "text.secondary", mb: 0.5 }}>
                Guardrail
              </Typography>
              {risk ? <pre>{JSON.stringify(risk, null, 2)}</pre> : null}
              {catalog?.guardrail?.policy_source ? (
                <CodeBlock label="policy.route" file={catalog.guardrail.policy_file}>
                  {catalog.guardrail.policy_source}
                </CodeBlock>
              ) : null}
              {catalog?.guardrail?.scoring_source ? (
                <CodeBlock label="compute_score" file={catalog.guardrail.scoring_file}>
                  {catalog.guardrail.scoring_source}
                </CodeBlock>
              ) : null}
            </Box>
          ) : null}

          {tool?.source ? (
            <CodeBlock label="Tool source" file={tool.source_file}>
              {tool.source}
            </CodeBlock>
          ) : null}
        </Box>
      </Collapsible>
    </Box>
  );
}
