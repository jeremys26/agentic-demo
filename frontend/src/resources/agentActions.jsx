import { useState } from "react";
import {
  List,
  Datagrid,
  DateField,
  FunctionField,
  Show,
  useRecordContext,
  useRefresh,
  useNotify,
} from "react-admin";
import { Box, Card, CardContent, Typography } from "@mui/material";
import Button from "@mui/material/Button";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import BuildIcon from "@mui/icons-material/Build";
import GavelIcon from "@mui/icons-material/Gavel";
import { approveAction, rejectAction } from "../dataProvider";
import StatusPill from "../components/StatusPill";
import IconTag from "../components/IconTag";
import TechnicalTrace from "../components/TechnicalTrace";
import ResourceExplainer from "../components/ResourceExplainer";
import PageHeader from "../components/PageHeader";
import RiskScore from "../components/RiskScore";
import { formatToolName } from "../labels";

const ACTION_ICON = {
  reallocate_budget: { icon: <SwapHorizIcon fontSize="small" />, color: "#0A21C7" },
  request_creative_refresh: { icon: <AutorenewIcon fontSize="small" />, color: "#9A6700" },
};

export const ActionTag = ({ toolName }) => {
  const meta = ACTION_ICON[toolName] || { icon: <BuildIcon fontSize="small" />, color: "#5B6270" };
  return (
    <span
      title={toolName}
      style={{ display: "inline-flex", alignItems: "center", gap: 10, verticalAlign: "middle" }}
    >
      <IconTag icon={meta.icon} color={meta.color} />
      {formatToolName(toolName)}
    </span>
  );
};

// PLANNING.md §7/§10: a status badge per risk tier, plain-language
// reasoning as the default view (not the raw risk breakdown), full
// technical trace available a click away on the Show page.
// Keys match guardrails/policy.py's route() return values exactly
// (risk.decision, persisted as-is to AgentToolCall.outcome) — "auto_execute",
// not "auto_executed"; the "-d" spelling only ever appears in a tool's own
// returned `status` field, never in the stored outcome this table reads.
const OUTCOME_META = {
  auto_execute: { label: "Executed (auto)", tone: "success" },
  approved_executed: { label: "Executed (approved)", tone: "success" },
  pending_approval: { label: "Pending Approval", tone: "warning" },
  blocked: { label: "Blocked", tone: "error" },
  rejected: { label: "Rejected", tone: "neutral" },
  error: { label: "Error", tone: "neutral" },
};

export const StatusBadge = ({ outcome }) => {
  const meta = OUTCOME_META[outcome] || { label: outcome, tone: "neutral" };
  return <StatusPill label={meta.label} tone={meta.tone} />;
};

export const ApprovalButtons = ({ record: recordProp }) => {
  const contextRecord = useRecordContext();
  const record = recordProp ?? contextRecord;
  const refresh = useRefresh();
  const notify = useNotify();
  const [busy, setBusy] = useState(false);

  if (!record || record.outcome !== "pending_approval" || !record.proposed_action_id) return null;

  const handle = async (action) => {
    setBusy(true);
    try {
      const result = await action(record.proposed_action_id);
      if (result.status === "error") {
        notify(result.detail || "That action could not be completed", { type: "warning" });
      } else if (result.status === "rejected") {
        notify("Rejected — nothing changed", { type: "info" });
      } else {
        notify("Approved — the change is now in effect", { type: "success" });
      }
      refresh();
    } catch (err) {
      notify(String(err), { type: "warning" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <span onClick={(e) => e.stopPropagation()} style={{ display: "inline-flex", gap: 8, flexShrink: 0, whiteSpace: "nowrap" }}>
      <Button
        size="small"
        variant="outlined"
        color="success"
        disabled={busy}
        onClick={() => handle(approveAction)}
      >
        Approve
      </Button>
      <Button
        size="small"
        variant="outlined"
        color="error"
        disabled={busy}
        onClick={() => handle(rejectAction)}
      >
        Reject
      </Button>
    </span>
  );
};

const LIVE_POLL_MS = 5000;

const EmptyActions = () => (
  <Box sx={{ p: 3, color: "text.secondary", fontSize: 14 }}>
    No actions yet. When the agent proposes or takes a change, it shows up here.
  </Box>
);

export const AgentActionList = () => (
  <>
    <PageHeader
      title="Agent Actions"
      subtitle="Every change the agent has taken or proposed, newest first. Approve or reject anything waiting on you — rejecting is always safe."
    />
    <ResourceExplainer
      icon={<GavelIcon fontSize="small" />}
      color="#0A21C7"
      platform="Agent360"
      role="governed action log"
      summary="Each row is one proposed or completed change. Status tells you what happened; Reasoning is the plain-language why. Click a row for the full technical trace."
      terms={[
        { term: "Executed (auto)", def: "A small, low-risk change that ran immediately. Logged with a pre-action snapshot for audit." },
        { term: "Pending Approval", def: "Waiting on you. Nothing happens until you Approve or Reject." },
        { term: "Blocked", def: "Refused outright because it would cross a hard cap." },
        { term: "Risk", def: "0–100. Below 30 runs automatically; 30–70 waits for your approval; 70+ is blocked. A “hard cap” can still hold a low score for review." },
      ]}
    />
    <List
      title="Agent Actions"
      sort={{ field: "id", order: "DESC" }}
      queryOptions={{ refetchInterval: LIVE_POLL_MS }}
      actions={false}
      empty={<EmptyActions />}
    >
      <Datagrid rowClick="show" bulkActionButtons={false}>
        <FunctionField
          label="Action"
          cellClassName="col-fit"
          headerClassName="col-fit"
          render={(record) => <ActionTag toolName={record.tool_name} />}
        />
        <FunctionField
          label="Campaign"
          cellClassName="col-campaign"
          headerClassName="col-campaign"
          render={(record) => record.campaign_name || "—"}
        />
        <FunctionField
          label="Status"
          cellClassName="col-fit"
          headerClassName="col-fit"
          render={(record) => <StatusBadge outcome={record.outcome} />}
        />
        <FunctionField
          label="Risk"
          cellClassName="col-fit"
          headerClassName="col-fit"
          render={(record) => (
            <RiskScore score={record.risk_score} breakdown={record.risk_breakdown} />
          )}
        />
        <FunctionField
          label="Reasoning"
          cellClassName="col-wide"
          headerClassName="col-wide"
          render={(record) => (
            <span
              title={record.rationale || undefined}
              style={{
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
                overflow: "hidden",
                lineHeight: 1.45,
              }}
            >
              {record.rationale || "—"}
            </span>
          )}
        />
        <DateField source="created_at" label="When" showTime cellClassName="col-fit" headerClassName="col-fit" />
        <FunctionField
          label="Review"
          cellClassName="col-fit"
          headerClassName="col-fit"
          render={() => <ApprovalButtons />}
        />
      </Datagrid>
    </List>
  </>
);

const AgentActionDetail = () => {
  const record = useRecordContext();
  if (!record) return null;
  return (
    <Box>
      <PageHeader
        title={formatToolName(record.tool_name)}
        subtitle={record.campaign_name || "No campaign attached"}
        backTo="/agent_actions"
        backLabel="All agent actions"
      />
      <Card>
        <CardContent>
          <Box sx={{ display: "flex", gap: 1.5, alignItems: "center", flexWrap: "wrap", mb: 2 }}>
            <StatusBadge outcome={record.outcome} />
            <Typography sx={{ fontSize: 13, color: "text.secondary", display: "inline-flex", alignItems: "center", gap: 0.75, flexWrap: "wrap" }}>
              Risk <RiskScore score={record.risk_score} breakdown={record.risk_breakdown} />
              {record.created_at ? ` · ${new Date(record.created_at).toLocaleString()}` : ""}
            </Typography>
            <Box sx={{ ml: { sm: "auto" } }}>
              <ApprovalButtons />
            </Box>
          </Box>
          <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "text.secondary", mb: 0.75 }}>
            Reasoning
          </Typography>
          <Typography sx={{ fontSize: 15, lineHeight: 1.65, mb: 1 }}>
            {record.rationale || "No reasoning was recorded for this action."}
          </Typography>
          <TechnicalTrace includeGuardrail />
        </CardContent>
      </Card>
    </Box>
  );
};

export const AgentActionShow = () => (
  <Show queryOptions={{ refetchInterval: LIVE_POLL_MS }} actions={false}>
    <AgentActionDetail />
  </Show>
);
