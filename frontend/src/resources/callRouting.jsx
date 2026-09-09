import { useEffect, useState } from "react";
import { List, Datagrid, FunctionField, Show, useRecordContext } from "react-admin";
import { Box, Card, CardContent, Typography } from "@mui/material";
import PhoneInTalkIcon from "@mui/icons-material/PhoneInTalk";
import VerifiedIcon from "@mui/icons-material/Verified";
import StatusPill from "../components/StatusPill";
import IconTag from "../components/IconTag";
import WeeklyPoolShareChart from "../components/WeeklyPoolShareChart";
import ResourceExplainer from "../components/ResourceExplainer";
import PageHeader from "../components/PageHeader";
import { fetchCallEvents } from "../dataProvider";

// A campaign's non-certified-pool share sitting meaningfully above the
// PLANNING.md §9 baseline (~10%) but not yet all the way to the scenario's
// spike (~35%) is worth a human's attention before it becomes a CPL problem.
const ELEVATED_UNCERTIFIED_PCT = 20;

const OUTCOME_TONE = {
  conversion: "success",
  voicemail: "neutral",
  dropped: "error",
  no_answer: "warning",
};

const OUTCOME_LABEL = {
  conversion: "Conversion",
  voicemail: "Voicemail",
  dropped: "Dropped",
  no_answer: "No Answer",
};

const PoolTag = ({ name, certified }) => (
  <span style={{ display: "inline-flex", alignItems: "center", gap: 8, verticalAlign: "middle", minWidth: 0 }}>
    <IconTag icon={<PhoneInTalkIcon fontSize="small" />} color={certified ? "#166534" : "#B42318"} />
    {name}
    {certified && <VerifiedIcon fontSize="inherit" sx={{ color: "#166534" }} titleAccess="Medicare-certified" />}
  </span>
);

export const CallRoutingList = () => (
  <>
    <PageHeader
      title="Call Routing"
      subtitle="Each row is one campaign’s call-center summary. Opened from Maestro360."
    />
    <ResourceExplainer
      icon={<PhoneInTalkIcon fontSize="small" />}
      color="#6E11B0"
      platform="Maestro360"
      role="inbound call routing"
      summary="Each row is one campaign’s call-center summary. Click through to see which teams answered the phones and how those calls ended."
      terms={[
        { term: "Agent pool", def: "A team of call-center people. Pool A is Medicare-certified and converts ~31% of calls; Pool B is not certified and converts ~18%." },
        { term: "Routing", def: "Which team a new inbound call is sent to. Rule 1: Pool A first. Rule 2: overflow to Pool B when A is full." },
        { term: "Call event", def: "One phone call: when it came in, which pool got it, wait time, duration, and how it ended." },
        { term: "Outcome", def: "Conversion (the person signed up), no answer, voicemail, or dropped." },
      ]}
    />
    <List title="Call Routing" sort={{ field: "uncertified_pct", order: "DESC" }} actions={false}>
    <Datagrid rowClick="show" bulkActionButtons={false}>
      <FunctionField
        label="Campaign"
        cellClassName="col-campaign"
        headerClassName="col-campaign"
        render={(record) => record.campaign_name}
      />
      <FunctionField
        label="Total Calls"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) => record.total_calls.toLocaleString()}
      />
      <FunctionField
        label="Top Pool"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) => {
          const top = record.pool_distribution[0];
          return top ? <PoolTag name={top.pool_name} certified={top.is_certified_medicare} /> : "—";
        }}
      />
      <FunctionField
        label="Non-certified share"
        cellClassName="col-fit"
        headerClassName="col-fit"
        render={(record) =>
          record.total_calls === 0 ? (
            "—"
          ) : (
            <StatusPill
              label={`${record.uncertified_pct.toFixed(1)}%`}
              tone={record.uncertified_pct > ELEVATED_UNCERTIFIED_PCT ? "warning" : "success"}
            />
          )
        }
      />
    </Datagrid>
  </List>
  </>
);

const RoutingDetail = () => {
  const record = useRecordContext();
  const [events, setEvents] = useState(null);

  useEffect(() => {
    if (!record || record.total_calls === 0) return;
    let cancelled = false;
    fetchCallEvents(record.campaign_id)
      .then((e) => !cancelled && setEvents(e))
      .catch(() => !cancelled && setEvents([]));
    return () => {
      cancelled = true;
    };
  }, [record]);

  if (!record) return null;

  if (record.total_calls === 0) {
    return (
      <div style={{ padding: "16px 0", color: "#5B6270" }}>
        No Maestro360 call data seeded for this campaign yet.
      </div>
    );
  }

  const totalOutcomes = Object.values(record.outcome_breakdown).reduce((a, b) => a + b, 0);
  const pools = record.pool_distribution.map((p) => ({
    id: p.pool_id,
    name: p.pool_name,
    is_certified_medicare: p.is_certified_medicare,
  }));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24, padding: "8px 0 8px" }}>
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "#5B6270", marginBottom: 8 }}>
          Pool distribution (lifetime)
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {record.pool_distribution.map((p) => (
            <div
              key={p.pool_id}
              style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0, flexWrap: "wrap" }}
            >
              <div style={{ width: 180, flexShrink: 0 }}>
                <PoolTag name={p.pool_name} certified={p.is_certified_medicare} />
              </div>
              <div style={{ flex: "1 1 160px", minWidth: 80, background: "#EEF0F4", borderRadius: 4, height: 10, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${p.pct_of_total}%`,
                    height: "100%",
                    backgroundColor: p.is_certified_medicare ? "#0A21C7" : "#B42318",
                  }}
                />
              </div>
              <div style={{ fontSize: 13, color: "#5B6270", whiteSpace: "nowrap" }}>
                {p.call_count.toLocaleString()} calls ({p.pct_of_total}%) · {(p.conversion_rate * 100).toFixed(1)}% conv.
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "#5B6270", marginBottom: 8 }}>
          Call outcomes (lifetime)
        </div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {Object.entries(record.outcome_breakdown).map(([outcome, count]) => (
            <div key={outcome} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <StatusPill label={OUTCOME_LABEL[outcome] || outcome} tone={OUTCOME_TONE[outcome] || "neutral"} />
              <span style={{ fontSize: 13, color: "#5B6270" }}>
                {count.toLocaleString()} ({totalOutcomes ? ((count / totalOutcomes) * 100).toFixed(0) : 0}%)
              </span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.05em", textTransform: "uppercase", color: "#5B6270", marginBottom: 8 }}>
          Weekly pool share
        </div>
        <p style={{ fontSize: 13, color: "#5B6270", margin: "0 0 8px", lineHeight: 1.5 }}>
          Share of calls going to each team, week by week. A rise in the red bar is overflow drifting to the uncertified pool.
        </p>
        {events && events.length > 0 ? (
          <WeeklyPoolShareChart events={events} pools={pools} />
        ) : events ? (
          <div style={{ color: "#5B6270" }}>Couldn’t load weekly call events.</div>
        ) : (
          <div style={{ color: "#5B6270" }}>Loading weekly trend…</div>
        )}
      </div>
    </div>
  );
};

const CallRoutingDetail = () => {
  const record = useRecordContext();
  if (!record) return null;
  return (
    <Box>
      <PageHeader
        title={record.campaign_name || "Call routing"}
        subtitle={`${(record.total_calls || 0).toLocaleString()} inbound calls`}
        backTo="/call_routing"
        backLabel="All campaigns"
      />
      <Card>
        <CardContent>
          <RoutingDetail />
        </CardContent>
      </Card>
    </Box>
  );
};

export const CallRoutingShow = () => (
  <Show actions={false}>
    <CallRoutingDetail />
  </Show>
);
