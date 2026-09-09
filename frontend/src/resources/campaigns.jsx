import { useEffect, useState } from "react";
import {
  List,
  Datagrid,
  TextField,
  NumberField,
  DateField,
  FunctionField,
  Show,
  useRecordContext,
} from "react-admin";
import { Box, Card, CardContent, Typography } from "@mui/material";
import TvIcon from "@mui/icons-material/Tv";
import RadioIcon from "@mui/icons-material/Radio";
import MailIcon from "@mui/icons-material/MailOutline";
import CampaignIcon from "@mui/icons-material/Campaign";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import StatusPill from "../components/StatusPill";
import IconTag from "../components/IconTag";
import LineTrendChart from "../components/LineTrendChart";
import ResourceExplainer from "../components/ResourceExplainer";
import PageHeader from "../components/PageHeader";
import { sentenceCase } from "../labels";
import { fetchCampaignPerformance, windowedCplVariance, ANOMALY_THRESHOLD_PCT } from "../dataProvider";

const STATUS_TONE = {
  active: "success",
  paused: "warning",
  ended: "neutral",
  completed: "neutral",
};

const CHANNEL_ICON = {
  tv: { icon: <TvIcon fontSize="small" />, color: "#0A21C7" },
  radio: { icon: <RadioIcon fontSize="small" />, color: "#9A6700" },
  direct_mail: { icon: <MailIcon fontSize="small" />, color: "#166534" },
};

const CHANNEL_LABEL = { tv: "TV", radio: "Radio", direct_mail: "Direct mail" };

const VERTICAL_LABEL = {
  medicare_advantage: "Medicare Advantage",
  insurance: "Insurance",
  home_services: "Home Services",
};

const ChannelTag = ({ channel }) => {
  const meta = CHANNEL_ICON[channel] || { icon: <CampaignIcon fontSize="small" />, color: "#5B6270" };
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 10, verticalAlign: "middle" }}>
      <IconTag icon={meta.icon} color={meta.color} />
      {CHANNEL_LABEL[channel] || channel}
    </span>
  );
};

// PLANNING.md §9/§10: "React-Admin shows it flagged" — a campaign whose
// blended CPL has crossed its target by more than ANOMALY_THRESHOLD_PCT
// (dataProvider.js, same number the project's own scenario is built
// around), computed from the same onesource360 performance summary the MCP
// server's get_performance_anomalies tool reads.
const FlaggedTag = ({ variancePct }) => (
  <span style={{ display: "inline-flex", alignItems: "center", gap: 6, color: "#B42318", fontWeight: 600 }}>
    <WarningAmberIcon fontSize="small" />
    +{variancePct.toFixed(0)}% CPL
  </span>
);

export const CampaignList = () => (
  <>
    <PageHeader
      title="Campaigns"
      subtitle="Every campaign Agent360 is watching. Click a row for the daily scoreboard — spend, leads, and cost per lead."
    />
    <ResourceExplainer
      icon={<CampaignIcon fontSize="small" />}
      color="#0A21C7"
      platform="OneSource360"
      role="performance warehouse"
      summary="Each row is one advertising campaign. Click a row to see the daily scoreboard — that's where spend, leads, and cost-per-lead actually live."
      terms={[
        { term: "Campaign", def: "A named advertising effort. “Medicare Advantage – Southeast TV” means: sell Medicare plans, in the Southeast, by buying TV ads." },
        { term: "Spend", def: "Dollars paid to run ads that day. Not profit — just the media bill." },
        { term: "Lead", def: "A person who responded (called or filled a form). The thing the campaign is trying to generate." },
        { term: "CPL", def: "Cost per lead = spend ÷ leads. Target $45 means “we’re willing to pay $45 for one inquiry.” Lower is better." },
      ]}
    />
    <List title="Campaigns" sort={{ field: "flagged", order: "DESC" }} actions={false}>
    <Datagrid rowClick="show" bulkActionButtons={false}>
      <TextField source="name" label="Campaign" cellClassName="col-campaign" headerClassName="col-campaign" />
      <FunctionField
        label="Vertical"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) => VERTICAL_LABEL[record.vertical] || record.vertical}
      />
      <FunctionField
        label="Channel"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) => <ChannelTag channel={record.channel} />}
      />
      <NumberField
        source="target_cpl"
        label="Target CPL"
        options={{ style: "currency", currency: "USD" }}
        cellClassName="col-fit"
        headerClassName="col-fit"
      />
      <FunctionField
        label="Status"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) => <StatusPill label={sentenceCase(record.status)} tone={STATUS_TONE[record.status] || "neutral"} />}
      />
      <FunctionField
        label="Performance"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) =>
          record.flagged ? (
            <FlaggedTag variancePct={record.cpl_variance_pct} />
          ) : record.avg_cpl != null ? (
            <span style={{ color: "#5B6270" }}>on target</span>
          ) : (
            "—"
          )
        }
      />
      <DateField source="start_date" label="Started" cellClassName="col-fit" headerClassName="col-fit" />
    </Datagrid>
  </List>
  </>
);

// Fetched separately from the record (rather than through the list's
// already-decorated `flagged`/`avg_cpl` fields) so the Show page always has
// the full daily rollup history to chart, not just the summary.
const CampaignPerformancePanel = () => {
  const record = useRecordContext();
  const [performance, setPerformance] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!record) return;
    let cancelled = false;
    fetchCampaignPerformance(record.id)
      .then((p) => !cancelled && setPerformance(p))
      .catch((e) => !cancelled && setError(e));
    return () => {
      cancelled = true;
    };
  }, [record]);

  if (!record) return null;
  if (error) return null;
  if (!performance) return <div style={{ padding: "16px 0", color: "#5B6270" }}>Loading performance…</div>;

  const { summary, daily_rollups } = performance;
  const targetCpl = Number(summary.target_cpl);
  const { windowedCpl, variancePct } = windowedCplVariance(daily_rollups, targetCpl);
  const flagged = variancePct != null && variancePct > ANOMALY_THRESHOLD_PCT;
  const chartData = daily_rollups.map((r) => ({ date: r.date, cpl: parseFloat(r.cpl) }));

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
    <div style={{ padding: "8px 0 8px", gridColumn: "1 / -1" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: 20,
          marginBottom: 20,
        }}
      >
        <Stat label="Last 7 Days CPL" value={windowedCpl != null ? `$${windowedCpl.toFixed(2)}` : "—"} warn={flagged} />
        <Stat label="Target CPL" value={`$${targetCpl.toFixed(2)}`} />
        <Stat
          label="Variance (7d)"
          value={variancePct != null ? `${variancePct > 0 ? "+" : ""}${variancePct.toFixed(1)}%` : "—"}
          warn={flagged}
        />
        <Stat label="Lifetime Avg CPL" value={summary.avg_cpl != null ? `$${summary.avg_cpl.toFixed(2)}` : "—"} />
        <Stat label="Total Spend" value={summary.total_spend != null ? `$${Number(summary.total_spend).toLocaleString()}` : "—"} />
        <Stat label="Total Leads" value={summary.total_leads != null ? summary.total_leads.toLocaleString() : "—"} />
      </div>
      {flagged && (
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            color: "#B42318",
            backgroundColor: "#FEE4E2",
            borderRadius: 8,
            padding: "8px 12px",
            fontSize: 13,
            fontWeight: 600,
            marginBottom: 16,
          }}
        >
          <WarningAmberIcon fontSize="small" />
          Flagged — last 7 days of cost per lead is {variancePct.toFixed(1)}% over target (the flag threshold is {ANOMALY_THRESHOLD_PCT}%).
        </div>
      )}
      {chartData.length > 0 && (
        <>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "#5B6270", marginBottom: 8 }}>
          Daily cost per lead
        </div>
        <p style={{ fontSize: 13, color: "#5B6270", margin: "0 0 8px", lineHeight: 1.5 }}>
          The dashed line is this campaign&apos;s target. A sustained run above it is what triggers the flag.
        </p>
        <LineTrendChart
          data={chartData.map((d) => ({ date: d.date, value: d.cpl }))}
          valueFormat={(v) => `CPL $${v.toFixed(2)}`}
          yTickFormat={(v) => `$${v.toFixed(0)}`}
          referenceLine={{ value: targetCpl, label: `Target $${targetCpl}` }}
          ariaLabel={`Daily cost per lead trend, target $${targetCpl}`}
        />
        </>
      )}
    </div>
  );
};

const CampaignDetail = () => {
  const record = useRecordContext();
  if (!record) return null;
  return (
    <Box>
      <PageHeader
        title={record.name}
        subtitle={`${VERTICAL_LABEL[record.vertical] || record.vertical} · ${CHANNEL_LABEL[record.channel] || record.channel}`}
        backTo="/campaigns"
        backLabel="All campaigns"
      />
      <Card>
        <CardContent>
          <Box sx={{ display: "flex", gap: 1.5, alignItems: "center", flexWrap: "wrap", mb: 2.5 }}>
            <StatusPill label={sentenceCase(record.status)} tone={STATUS_TONE[record.status] || "neutral"} />
            <ChannelTag channel={record.channel} />
            <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
              Target CPL ${Number(record.target_cpl).toFixed(2)}
              {record.start_date ? ` · started ${record.start_date}` : ""}
              {record.end_date ? ` · ended ${record.end_date}` : ""}
            </Typography>
          </Box>
          <CampaignPerformancePanel />
        </CardContent>
      </Card>
    </Box>
  );
};

export const CampaignShow = () => (
  <Show actions={false}>
    <CampaignDetail />
  </Show>
);
