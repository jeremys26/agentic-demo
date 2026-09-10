import { useState, useEffect, useCallback } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useGetList, Title, useRefresh } from "react-admin";
import { Box, Card, CardContent, Typography, Link as MuiLink, Button, CircularProgress } from "@mui/material";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import PendingActionsIcon from "@mui/icons-material/PendingActions";
import BoltIcon from "@mui/icons-material/Bolt";
import BlockIcon from "@mui/icons-material/Block";
import SensorsIcon from "@mui/icons-material/Sensors";
import FastForwardIcon from "@mui/icons-material/FastForward";
import VarianceBarChart from "../components/VarianceBarChart";
import Collapsible from "../components/Collapsible";
import PageHeader, { JUMP_CHIP_SX } from "../components/PageHeader";
import RiskScore from "../components/RiskScore";
import { ActionTag, ApprovalButtons } from "../resources/agentActions";
import { ServiceTag, OutcomePill } from "../resources/toolCalls";
import { fetchFlaggedCampaigns, triggerAnomalySweep, simulateNextDay } from "../dataProvider";
import { formatToolName } from "../labels";

// Section ids double as scroll targets for the quick-nav row and as keys
// into Overview's `expanded` state map below.
const SECTIONS = [
  { key: "numbers", label: "The four systems" },
  { key: "chart", label: "CPL vs. target" },
  { key: "attention", label: "Needs attention" },
  { key: "simulate", label: "Simulate next day" },
  { key: "sweep", label: "Anomaly sweep" },
  { key: "activity", label: "Recent activity" },
];

// The landing page (react-admin's `dashboard` prop — App.jsx — shown when
// Overview is selected in TopBar). Answers the three questions a marketing
// ops stakeholder actually opens this tool for: what needs my attention,
// what has the agent already done, and can I trust it.

const TILE_META = {
  flagged: {
    label: "Flagged campaigns",
    caption: "CPL more than 15% over target",
    icon: <WarningAmberIcon />,
    tone: "#B42318",
    bg: "#FEE4E2",
  },
  pending: {
    label: "Pending approval",
    caption: "Waiting on you",
    icon: <PendingActionsIcon />,
    tone: "#9A6700",
    bg: "#FEF3C7",
  },
  executed: {
    label: "Auto-executed",
    caption: "Ran on its own",
    icon: <BoltIcon />,
    tone: "#166534",
    bg: "#DCFCE7",
  },
  blocked: {
    label: "Blocked",
    caption: "Stopped by a safety limit",
    icon: <BlockIcon />,
    tone: "#5B6270",
    bg: "#EEF0F4",
  },
};

const StatTile = ({ kind, value, to }) => {
  const meta = TILE_META[kind];
  return (
    <Card
      component={RouterLink}
      to={to}
      sx={{ textDecoration: "none", display: "block", minWidth: 0, height: "100%" }}
    >
      <CardContent sx={{ display: "flex", alignItems: "flex-start", gap: 2, py: 2 }}>
        <Box
          sx={{
            width: 44,
            height: 44,
            borderRadius: "12px",
            backgroundColor: meta.bg,
            color: meta.tone,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          {meta.icon}
        </Box>
        <Box sx={{ minWidth: 0, overflow: "hidden" }}>
          <Typography sx={{ fontSize: 28, fontWeight: 600, fontFamily: '"Fraunces", Georgia, serif', color: "text.primary", lineHeight: 1.1 }}>
            {value}
          </Typography>
          <Typography sx={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "text.secondary" }}>
            {meta.label}
          </Typography>
          <Typography sx={{ fontSize: 12, color: "text.secondary", mt: 0.25, lineHeight: 1.4 }}>
            {meta.caption}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

// Anomaly sweep (PLANNING.md §8): a Celery beat schedule reuses
// get_performance_anomalies' own code path on a timer, with no LLM in the
// loop, and persists what it finds to FlaggedCampaign — this section reads
// that log directly (fetchFlaggedCampaigns), distinct from the stat tiles
// above which recompute flagging live, client-side, on every page load.
const AnomalySweepSection = ({ expanded, onToggle }) => {
  const [flags, setFlags] = useState(null);
  const [running, setRunning] = useState(false);

  const load = useCallback(() => {
    fetchFlaggedCampaigns()
      .then(setFlags)
      .catch(() => setFlags([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runNow = async () => {
    setRunning(true);
    try {
      await triggerAnomalySweep();
      load();
    } finally {
      setRunning(false);
    }
  };

  const lastSweptAt = flags && flags.length > 0 ? flags[0].flagged_at : null;

  return (
    <Collapsible
      id="sweep"
      title="Automated anomaly sweep"
      subtitle={flags && flags.length > 0 ? `${flags.length} flagged · last ${timeAgo(lastSweptAt)}` : flags ? "No campaigns over target" : undefined}
      expanded={expanded}
      onToggle={onToggle}
      action={
        <Button
          size="small"
          variant="outlined"
          startIcon={running ? <CircularProgress size={14} /> : <SensorsIcon fontSize="small" />}
          onClick={runNow}
          disabled={running}
        >
          Run sweep now
        </Button>
      }
    >
      <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 1.5, lineHeight: 1.6 }}>
        Every few minutes a scheduled job checks every active campaign against the same
        15%-over-target rule the agent uses — no AI involved — and logs what it finds here.
        That feeds “needs investigation” without anyone having to notice a chart first.
      </Typography>
      {flags === null ? (
        <Typography sx={{ fontSize: 13, color: "text.secondary" }}>Loading…</Typography>
      ) : flags.length === 0 ? (
        <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
          No campaigns are currently more than 15% over their target CPL.
        </Typography>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
            Last detected {timeAgo(lastSweptAt)}
          </Typography>
          {flags.slice(0, 5).map((f) => (
            <Box
              key={f.id}
              component={RouterLink}
              to={f.campaign_id != null ? `/campaigns/${f.campaign_id}/show` : "/campaigns"}
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr auto", sm: "1fr auto 90px" },
                alignItems: "center",
                gap: 2,
                fontSize: 13,
                minWidth: 0,
                textDecoration: "none",
                color: "inherit",
                "&:hover .campaign-name": { color: "primary.main" },
              }}
            >
              <Box className="campaign-name" sx={{ fontWeight: 600, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {f.campaign_name}
              </Box>
              <Box sx={{ color: "#B42318", fontWeight: 600, whiteSpace: "nowrap" }}>+{f.variance_pct}% CPL</Box>
              <Box sx={{ color: "text.secondary", textAlign: "right", display: { xs: "none", sm: "block" } }}>
                {timeAgo(f.flagged_at)}
              </Box>
            </Box>
          ))}
        </Box>
      )}
    </Collapsible>
  );
};

const SimulateNextDaySection = ({ expanded, onToggle }) => {
  const [running, setRunning] = useState(false);
  const [last, setLast] = useState(null);
  const [error, setError] = useState(null);
  const refresh = useRefresh();

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const result = await simulateNextDay();
      setLast(result);
      refresh();
    } catch (exc) {
      setError(exc.message || "Simulate next day failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <Collapsible
      id="simulate"
      title="Simulate next day"
      subtitle={last ? `Last simulated day: ${last.date}` : "Demo control — adds one more day of data"}
      expanded={expanded}
      onToggle={onToggle}
      action={
        <Button
          size="small"
          variant="outlined"
          startIcon={running ? <CircularProgress size={14} /> : <FastForwardIcon fontSize="small" />}
          onClick={run}
          disabled={running}
        >
          Advance one day
        </Button>
      }
    >
      <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 1.5, lineHeight: 1.6 }}>
        Demo control: appends one more day of warehouse rollups, spots, creative metrics, and
        call events through each platform&apos;s own webhook — the same path a real data drop
        would use — then re-runs the anomaly sweep. Campaign 1 stays in the spiked-CPL pattern.
      </Typography>
      {error ? (
        <Typography sx={{ fontSize: 13, color: "#B42318" }}>{error}</Typography>
      ) : last ? (
        <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
          Last simulated day: <strong>{last.date}</strong>
          {last.onesource?.created ? ` · ${last.onesource.created.length} warehouse rows` : ""}
          {last.maestro?.created_count != null ? ` · ${last.maestro.created_count} calls` : ""}
        </Typography>
      ) : (
        <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
          Seed data ends on 2026-08-28. The first click appends 2026-08-29.
        </Typography>
      )}
    </Collapsible>
  );
};

const Overview = () => {
  const [expanded, setExpanded] = useState({
    numbers: false,
    chart: true,
    attention: true,
    simulate: false,
    sweep: false,
    activity: false,
  });
  const toggleSection = (key) => setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));
  const expandAndScroll = (key) => {
    setExpanded((prev) => ({ ...prev, [key]: true }));
    requestAnimationFrame(() => {
      document.getElementById(key)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  const { data: campaignsRaw, isPending: campaignsLoading } = useGetList("campaigns", {
    pagination: { page: 1, perPage: 100 },
    sort: { field: "id", order: "ASC" },
  });
  const { data: actionsRaw, isPending: actionsLoading } = useGetList("agent_actions", {
    pagination: { page: 1, perPage: 100 },
    sort: { field: "id", order: "DESC" },
  });
  const { data: toolCallsRaw, isPending: toolCallsLoading } = useGetList("tool_calls", {
    pagination: { page: 1, perPage: 8 },
    sort: { field: "id", order: "DESC" },
  });

  if (campaignsLoading || actionsLoading || toolCallsLoading) {
    return (
      <Box sx={{ p: 1, color: "text.secondary", display: "flex", alignItems: "center", gap: 1.5 }}>
        <Title title="Overview" />
        <CircularProgress size={18} />
        Loading overview…
      </Box>
    );
  }

  const campaigns = campaignsRaw ?? [];
  const actions = actionsRaw ?? [];
  const toolCalls = toolCallsRaw ?? [];

  const flaggedCampaigns = campaigns.filter((c) => c.flagged);
  const pending = actions.filter((a) => a.outcome === "pending_approval");
  const executedCount = actions.filter((a) => a.outcome === "auto_execute" || a.outcome === "approved_executed").length;
  const blockedCount = actions.filter((a) => a.outcome === "blocked").length;

  return (
    <Box sx={{ width: "100%", maxWidth: 1200, mx: "auto" }}>
      <Title title="Overview" />
      <PageHeader
        title="Overview"
        subtitle="Campaigns over target, anything waiting on you, and what the agent has already done."
      />

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(4, 1fr)" },
          gap: 2,
          mb: 3,
        }}
      >
        <StatTile kind="flagged" value={flaggedCampaigns.length} to="/campaigns" />
        <StatTile kind="pending" value={pending.length} to="/agent_actions" />
        <StatTile kind="executed" value={executedCount} to="/agent_actions" />
        <StatTile kind="blocked" value={blockedCount} to="/agent_actions" />
      </Box>

      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 3 }}>
        {SECTIONS.map(({ key, label }) => (
          <MuiLink
            key={key}
            component="button"
            type="button"
            onClick={() => expandAndScroll(key)}
            sx={JUMP_CHIP_SX}
          >
            {label}
          </MuiLink>
        ))}
      </Box>

      <Collapsible
        id="numbers"
        title="The four systems"
        expanded={expanded.numbers}
        onToggle={() => toggleSection("numbers")}
        action={
          <MuiLink component={RouterLink} to="/systems" sx={{ fontSize: 13, fontWeight: 600 }}>
            Open Systems →
          </MuiLink>
        }
      >
        <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 1.5, lineHeight: 1.6 }}>
          Campaign data lives in four separate applications that do not talk to each other on
          their own. Open a system to see the live tables, the HTTP endpoints, and the tools the
          agent uses to read or change them.
        </Typography>
        <Box sx={{ display: "flex", gap: 1.5, flexWrap: "wrap" }}>
          {[
            ["/systems/onesource360", "OneSource360"],
            ["/systems/smartspot360", "SmartSpot360"],
            ["/systems/captivator360", "Captivator360"],
            ["/systems/maestro360", "Maestro360"],
            ["/systems/agent360", "Agent360 Gateway"],
          ].map(([to, label]) => (
            <MuiLink key={to} component={RouterLink} to={to} sx={{ fontSize: 13, fontWeight: 600 }}>
              {label}
            </MuiLink>
          ))}
        </Box>
      </Collapsible>

      <Collapsible id="chart" title="Portfolio CPL vs. target" expanded={expanded.chart} onToggle={() => toggleSection("chart")}>
        <VarianceBarChart campaigns={campaigns} />
      </Collapsible>

      <Collapsible
        id="attention"
        title={`Needs your attention (${pending.length})`}
        subtitle={pending.length === 0 ? "Nothing waiting on you right now" : undefined}
        expanded={expanded.attention}
        onToggle={() => toggleSection("attention")}
        action={
          <MuiLink component={RouterLink} to="/agent_actions" sx={{ fontSize: 13, fontWeight: 600 }}>
            View all agent actions →
          </MuiLink>
        }
      >
        {pending.length === 0 ? (
          <Typography sx={{ color: "text.secondary", fontSize: 14 }}>Nothing waiting on you right now.</Typography>
        ) : (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {pending.map((action) => (
              <Box
                key={action.id}
                sx={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  gap: 2,
                  pb: 2,
                  flexWrap: { xs: "wrap", sm: "nowrap" },
                  borderBottom: "1px solid rgba(20, 22, 31, 0.08)",
                  "&:last-of-type": { borderBottom: "none", pb: 0 },
                }}
              >
                <Box
                  component={RouterLink}
                  to={`/agent_actions/${action.id}/show`}
                  sx={{ flex: 1, minWidth: 0, textDecoration: "none", color: "inherit", "&:hover .action-title": { color: "primary.main" } }}
                >
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, mb: 0.5, flexWrap: "wrap" }}>
                    <Box className="action-title" component="span">
                      <ActionTag toolName={action.tool_name} />
                    </Box>
                    <Typography sx={{ fontSize: 13, color: "text.secondary", display: "inline-flex", alignItems: "center", gap: 0.75, flexWrap: "wrap" }}>
                      {action.campaign_name || "—"} · risk{" "}
                      <RiskScore score={action.risk_score} breakdown={action.risk_breakdown} />
                    </Typography>
                  </Box>
                  <Typography sx={{ fontSize: 13, color: "text.primary", lineHeight: 1.55 }}>
                    {action.rationale}
                  </Typography>
                </Box>
                <Box sx={{ flexShrink: 0, ml: { sm: "auto" } }}>
                  <ApprovalButtons record={action} />
                </Box>
              </Box>
            ))}
          </Box>
        )}
      </Collapsible>

      <SimulateNextDaySection expanded={expanded.simulate} onToggle={() => toggleSection("simulate")} />

      <AnomalySweepSection expanded={expanded.sweep} onToggle={() => toggleSection("sweep")} />

      <Collapsible
        id="activity"
        title="Recent activity"
        subtitle={toolCalls.length ? `${toolCalls.length} most recent calls` : "No calls yet"}
        expanded={expanded.activity}
        onToggle={() => toggleSection("activity")}
        action={
          <MuiLink component={RouterLink} to="/tool_calls" sx={{ fontSize: 13, fontWeight: 600 }}>
            View full trace →
          </MuiLink>
        }
      >
        <Box sx={{ overflowX: "auto" }}>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "minmax(140px, 1.1fr) minmax(140px, 1.2fr) minmax(140px, 1.4fr) minmax(120px, 0.9fr) auto",
              gap: 2,
              columnGap: 2,
              rowGap: 1.5,
              alignItems: "center",
              minWidth: 680,
            }}
          >
          {toolCalls.length === 0 ? (
            <Typography sx={{ color: "text.secondary", fontSize: 14, gridColumn: "1 / -1" }}>
              No lookups or changes yet — an investigation will show up here as it runs.
            </Typography>
          ) : (
            <>
            <Box sx={{ display: "contents", fontSize: 11, fontWeight: 700, letterSpacing: "0.04em", textTransform: "uppercase", color: "text.secondary" }}>
              <Box>System</Box>
              <Box>What it did</Box>
              <Box>Campaign</Box>
              <Box>Result</Box>
              <Box sx={{ textAlign: "right" }}>When</Box>
            </Box>
            {toolCalls.map((call) => (
            <Box key={call.id} sx={{ display: "contents", fontSize: 13 }}>
              <Box sx={{ minWidth: 0 }}>
                <ServiceTag service={call.service} />
              </Box>
              <Box title={call.tool_name} sx={{ minWidth: 0, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {formatToolName(call.tool_name)}
              </Box>
              <Box sx={{ minWidth: 0, color: "text.secondary", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {call.campaign_name || "—"}
              </Box>
              <Box sx={{ minWidth: 0 }}>
                <OutcomePill outcome={call.outcome} />
              </Box>
              <Box sx={{ color: "text.secondary", whiteSpace: "nowrap", textAlign: "right" }}>{timeAgo(call.created_at)}</Box>
            </Box>
            ))}
            </>
          )}
          </Box>
        </Box>
      </Collapsible>
    </Box>
  );
};

export default Overview;
