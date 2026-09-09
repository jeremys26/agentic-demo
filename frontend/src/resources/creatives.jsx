import { useEffect, useState } from "react";
import {
  List,
  Datagrid,
  TextField,
  DateField,
  FunctionField,
  Show,
  useRecordContext,
} from "react-admin";
import { Box, Card, CardContent, Typography } from "@mui/material";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import TvIcon from "@mui/icons-material/Tv";
import RadioIcon from "@mui/icons-material/Radio";
import MailIcon from "@mui/icons-material/MailOutline";
import StatusPill from "../components/StatusPill";
import IconTag from "../components/IconTag";
import LineTrendChart from "../components/LineTrendChart";
import ResourceExplainer from "../components/ResourceExplainer";
import PageHeader from "../components/PageHeader";
import { fetchCreativePerformance } from "../dataProvider";

// Same 20% CTR-vs-own-baseline trigger the MCP tool get_declining_creatives
// and Captivator360's /api/creatives/declining/ default to.
const CTR_DECLINE_THRESHOLD_PCT = 20;
const CTR_DECLINE_WATCH_PCT = 10;

const CHANNEL_ICON = {
  tv: { icon: <TvIcon fontSize="small" />, color: "#0A21C7" },
  radio: { icon: <RadioIcon fontSize="small" />, color: "#9A6700" },
  direct_mail: { icon: <MailIcon fontSize="small" />, color: "#166534" },
};

const CHANNEL_LABEL = { tv: "TV", radio: "Radio", direct_mail: "Direct mail" };

const ChannelTag = ({ channel }) => {
  const meta = CHANNEL_ICON[channel] || { icon: <AutorenewIcon fontSize="small" />, color: "#5B6270" };
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 10, verticalAlign: "middle" }}>
      <IconTag icon={meta.icon} color={meta.color} />
      {CHANNEL_LABEL[channel] || channel}
    </span>
  );
};

const DeclineBadge = ({ declinePct, declining }) => {
  if (declinePct == null) return "—";
  const value = Number(declinePct);
  const tone = declining || value >= CTR_DECLINE_THRESHOLD_PCT ? "error" : value >= CTR_DECLINE_WATCH_PCT ? "warning" : "success";
  const label = declining || value >= CTR_DECLINE_THRESHOLD_PCT ? "Declining" : value >= CTR_DECLINE_WATCH_PCT ? "Watch" : "Stable";
  const signed = `${value > 0 ? "−" : value < 0 ? "+" : ""}${Math.abs(value).toFixed(1)}%`;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8, verticalAlign: "middle" }}>
      <StatusPill label={label} tone={tone} />
      <span style={{ color: "#5B6270", fontSize: 13 }}>{signed} vs launch</span>
    </span>
  );
};

export const CreativeList = () => (
  <>
    <PageHeader
      title="Creatives"
      subtitle="Each row is one ad — the 30-second spot people actually see. Opened from Captivator360."
    />
    <ResourceExplainer
      icon={<AutorenewIcon fontSize="small" />}
      color="#166534"
      platform="Captivator360"
      role="ad creative performance"
      summary="Each row is one ad — the actual 30-second spot people see. Click a row to see click-through rate versus this ad's own first week."
      terms={[
        { term: "Creative", def: "The ad itself. CR-114 is a version name, like “v3 of the Medicare TV spot.”" },
        { term: "Impressions", def: "How many times the ad was shown that day." },
        { term: "CTR", def: "Click-through rate = people who responded ÷ people who saw it. 2.1% means 21 responses per 1,000 views." },
        { term: "CTR decline", def: "(first-week CTR − last-week CTR) ÷ first-week CTR. A drop of 20% or more is the refresh trigger — the same rule the agent uses." },
      ]}
    />
    <List title="Creatives" sort={{ field: "ctr_decline_pct", order: "DESC" }} actions={false}>
    <Datagrid rowClick="show" bulkActionButtons={false}>
      <FunctionField
        label="Campaign"
        cellClassName="col-campaign"
        headerClassName="col-campaign"
        render={(record) => record.campaign_name || "—"}
      />
      <TextField source="variant_label" label="Creative" cellClassName="col-fit" headerClassName="col-fit" />
      <FunctionField
        label="Channel"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) => <ChannelTag channel={record.channel} />}
      />
      <FunctionField
        label="Status"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) => <StatusPill label={record.is_active ? "Active" : "Inactive"} tone={record.is_active ? "success" : "neutral"} />}
      />
      <FunctionField
        label="Latest CTR"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) => (record.latest_ctr != null ? `${(Number(record.latest_ctr) * 100).toFixed(2)}%` : "—")}
      />
      <FunctionField
        label="CTR vs launch"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) => <DeclineBadge declinePct={record.ctr_decline_pct} declining={record.declining} />}
      />
      <FunctionField
        label="Days of data"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) => record.days_of_data ?? "—"}
      />
      <DateField source="created_date" label="Launched" cellClassName="col-fit" headerClassName="col-fit" />
    </Datagrid>
  </List>
  </>
);

const CreativeCharts = () => {
  const record = useRecordContext();
  const [performance, setPerformance] = useState(null);

  useEffect(() => {
    if (!record) return;
    let cancelled = false;
    fetchCreativePerformance(record.id).then((p) => !cancelled && setPerformance(p));
    return () => {
      cancelled = true;
    };
  }, [record]);

  if (!record) return null;
  if (!performance) return <div style={{ padding: "16px 0", color: "#5B6270" }}>Loading performance…</div>;

  const { daily_performance, summary } = performance;
  const ctrData = daily_performance.map((d) => ({ date: d.date, value: Number(d.ctr) * 100 }));
  const baselinePct = summary?.baseline_ctr != null ? Number(summary.baseline_ctr) * 100 : null;
  const recentPct = summary?.recent_ctr != null ? Number(summary.recent_ctr) * 100 : null;
  const declinePct = summary?.ctr_decline_pct;

  const Stat = ({ label, value, warn }) => (
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "#5B6270" }}>
        {label}
      </div>
      <div style={{ fontSize: 22, fontWeight: 600, color: warn ? "#B42318" : "#14161F", fontFamily: '"Fraunces", Georgia, serif' }}>
        {value}
      </div>
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, padding: "8px 0 8px" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: 20,
        }}
      >
        <Stat label="First-week CTR" value={baselinePct != null ? `${baselinePct.toFixed(2)}%` : "—"} />
        <Stat label="Last 7 days CTR" value={recentPct != null ? `${recentPct.toFixed(2)}%` : "—"} warn={summary?.declining} />
        <Stat
          label="Decline vs launch"
          value={declinePct != null ? `${declinePct > 0 ? "−" : ""}${Math.abs(declinePct).toFixed(1)}%` : "—"}
          warn={summary?.declining}
        />
      </div>
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "#5B6270", marginBottom: 8 }}>
          Click-through rate
        </div>
        <p style={{ fontSize: 13, color: "#5B6270", margin: "0 0 8px", lineHeight: 1.5 }}>
          The dashed line is this ad&apos;s first-week CTR. A 20% drop from that baseline is the refresh trigger.
        </p>
        <LineTrendChart
          data={ctrData}
          valueFormat={(v) => `CTR ${v.toFixed(2)}%`}
          yTickFormat={(v) => `${v.toFixed(1)}%`}
          referenceLine={
            baselinePct != null
              ? { value: baselinePct, label: `First-week ${baselinePct.toFixed(2)}%` }
              : undefined
          }
          ariaLabel="Creative CTR trend"
        />
      </div>
    </div>
  );
};

const CreativeDetail = () => {
  const record = useRecordContext();
  if (!record) return null;
  return (
    <Box>
      <PageHeader
        title={record.variant_label || "Creative"}
        subtitle={record.campaign_name || "Unknown campaign"}
        backTo="/creatives"
        backLabel="All creatives"
      />
      <Card>
        <CardContent>
          <Box sx={{ display: "flex", gap: 1.5, alignItems: "center", flexWrap: "wrap", mb: 2 }}>
            <StatusPill label={record.is_active ? "Active" : "Inactive"} tone={record.is_active ? "success" : "neutral"} />
            <ChannelTag channel={record.channel} />
            {record.created_date ? (
              <Typography sx={{ fontSize: 13, color: "text.secondary" }}>Launched {record.created_date}</Typography>
            ) : null}
          </Box>
          <CreativeCharts />
        </CardContent>
      </Card>
    </Box>
  );
};

export const CreativeShow = () => (
  <Show actions={false}>
    <CreativeDetail />
  </Show>
);
