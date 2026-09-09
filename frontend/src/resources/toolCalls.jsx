import {
  List,
  Datagrid,
  DateField,
  FunctionField,
  Show,
  useRecordContext,
} from "react-admin";
import { Box, Card, CardContent, Typography } from "@mui/material";
import CampaignIcon from "@mui/icons-material/Campaign";
import InsightsIcon from "@mui/icons-material/Insights";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import PhoneInTalkIcon from "@mui/icons-material/PhoneInTalk";
import BuildIcon from "@mui/icons-material/Build";
import TimelineIcon from "@mui/icons-material/Timeline";
import StatusPill from "../components/StatusPill";
import IconTag from "../components/IconTag";
import TechnicalTrace from "../components/TechnicalTrace";
import ResourceExplainer from "../components/ResourceExplainer";
import PageHeader from "../components/PageHeader";
import RiskScore from "../components/RiskScore";
import { formatKind, formatToolName } from "../labels";

const SERVICE_META = {
  onesource360: { label: "OneSource360", icon: <CampaignIcon fontSize="small" />, color: "#0A21C7" },
  smartspot360: { label: "SmartSpot360", icon: <InsightsIcon fontSize="small" />, color: "#9A6700" },
  captivator360: { label: "Captivator360", icon: <AutorenewIcon fontSize="small" />, color: "#166534" },
  maestro360: { label: "Maestro360", icon: <PhoneInTalkIcon fontSize="small" />, color: "#6E11B0" },
  rankpulse: { label: "RankPulse", icon: <InsightsIcon fontSize="small" />, color: "#5B6270" },
  unknown: { label: "Unregistered", icon: <BuildIcon fontSize="small" />, color: "#5B6270" },
};

export const ServiceTag = ({ service }) => {
  const meta = SERVICE_META[service] || {
    label: service || "Unknown",
    icon: <BuildIcon fontSize="small" />,
    color: "#5B6270",
  };
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 10, verticalAlign: "middle" }}>
      <IconTag icon={meta.icon} color={meta.color} />
      {meta.label}
    </span>
  );
};

const KIND_TONE = { read: "info", write: "warning" };
const KindPill = ({ kind }) => <StatusPill label={formatKind(kind)} tone={KIND_TONE[kind] || "neutral"} />;

const OUTCOME_META = {
  auto_execute: { label: "Executed (auto)", tone: "success" },
  approved_executed: { label: "Executed (approved)", tone: "success" },
  pending_approval: { label: "Pending Approval", tone: "warning" },
  blocked: { label: "Blocked", tone: "error" },
  rejected: { label: "Rejected", tone: "neutral" },
  read_ok: { label: "Looked up", tone: "info" },
  error: { label: "Error", tone: "error" },
};
export const OutcomePill = ({ outcome }) => {
  const meta = OUTCOME_META[outcome] || { label: outcome, tone: "neutral" };
  return <StatusPill label={meta.label} tone={meta.tone} />;
};

const LIVE_POLL_MS = 5000;

const EmptyCalls = () => (
  <Box sx={{ p: 3, color: "text.secondary", fontSize: 14 }}>
    No lookups or changes yet. When an investigation runs, every step shows up here.
  </Box>
);

export const ToolCallList = () => (
  <>
    <PageHeader
      title="Tool Calls"
      subtitle="The full step-by-step trail — including lookups that did not become an action. Updates live while an investigation is running."
    />
    <ResourceExplainer
      icon={<TimelineIcon fontSize="small" />}
      color="#0A21C7"
      platform="Agent360"
      role="investigation trace"
      summary="Each row is one lookup or change against one connected system. Agent Actions only shows the conclusions; this is the work that led there."
      terms={[
        { term: "Lookup", def: "A read — the agent asked a system for data and did not change anything." },
        { term: "Change", def: "A write — a proposed or completed action, scored for risk before anything happens." },
        { term: "Looked up", def: "The read succeeded. No change was made." },
      ]}
    />
    <List
      title="Tool Calls"
      sort={{ field: "id", order: "DESC" }}
      queryOptions={{ refetchInterval: LIVE_POLL_MS }}
      actions={false}
      empty={<EmptyCalls />}
    >
      <Datagrid rowClick="show" bulkActionButtons={false}>
        <FunctionField
          label="What it did"
          cellClassName="col-fit"
          headerClassName="col-fit"
          render={(record) => (
            <span title={record.tool_name}>{formatToolName(record.tool_name)}</span>
          )}
        />
        <FunctionField
          label="System"
          cellClassName="col-fit"
          headerClassName="col-fit"
          render={(record) => <ServiceTag service={record.service} />}
        />
        <FunctionField
          label="Campaign"
          cellClassName="col-campaign"
          headerClassName="col-campaign"
          render={(record) => record.campaign_name || "—"}
        />
        <FunctionField
          label="Kind"
          cellClassName="col-fit"
          headerClassName="col-fit"
          render={(record) => <KindPill kind={record.kind} />}
        />
        <FunctionField
          label="Result"
          cellClassName="col-fit"
          headerClassName="col-fit"
          render={(record) => <OutcomePill outcome={record.outcome} />}
        />
        <FunctionField
          label="Risk"
          cellClassName="col-fit"
          headerClassName="col-fit"
          render={(record) => (
            <RiskScore score={record.risk_score} breakdown={record.risk_breakdown} />
          )}
        />
        <DateField source="created_at" label="When" showTime cellClassName="col-fit" headerClassName="col-fit" />
      </Datagrid>
    </List>
  </>
);

const ToolCallDetail = () => {
  const record = useRecordContext();
  if (!record) return null;
  return (
    <Box>
      <PageHeader
        title={formatToolName(record.tool_name)}
        subtitle={record.campaign_name || "No campaign attached"}
        backTo="/tool_calls"
        backLabel="All tool calls"
      />
      <Card>
        <CardContent>
          <Box sx={{ display: "flex", gap: 1.5, alignItems: "center", flexWrap: "wrap", mb: 2 }}>
            <ServiceTag service={record.service} />
            <KindPill kind={record.kind} />
            <OutcomePill outcome={record.outcome} />
            {record.risk_score != null ? (
              <Typography sx={{ fontSize: 13, color: "text.secondary", display: "inline-flex", alignItems: "center", gap: 0.75 }}>
                Risk <RiskScore score={record.risk_score} breakdown={record.risk_breakdown} />
              </Typography>
            ) : null}
            {record.created_at ? (
              <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
                {new Date(record.created_at).toLocaleString()}
              </Typography>
            ) : null}
          </Box>
          {record.rationale ? (
            <>
              <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "text.secondary", mb: 0.75 }}>
                Reasoning
              </Typography>
              <Typography sx={{ fontSize: 15, lineHeight: 1.65 }}>
                {record.rationale}
              </Typography>
            </>
          ) : null}
          <TechnicalTrace includeGuardrail />
        </CardContent>
      </Card>
    </Box>
  );
};

export const ToolCallShow = () => (
  <Show queryOptions={{ refetchInterval: LIVE_POLL_MS }} actions={false}>
    <ToolCallDetail />
  </Show>
);
