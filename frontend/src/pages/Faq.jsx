import { useState } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  Link as MuiLink,
} from "@mui/material";
import HomeIcon from "@mui/icons-material/Home";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import CampaignIcon from "@mui/icons-material/Campaign";
import GavelIcon from "@mui/icons-material/Gavel";
import TimelineIcon from "@mui/icons-material/Timeline";
import InsightsIcon from "@mui/icons-material/Insights";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import PhoneInTalkIcon from "@mui/icons-material/PhoneInTalk";
import HubIcon from "@mui/icons-material/Hub";
import StatusPill from "../components/StatusPill";
import IconTag from "../components/IconTag";
import Collapsible from "../components/Collapsible";
import PageHeader, { JUMP_CHIP_SX } from "../components/PageHeader";

// Same platform color language as toolCalls.jsx's SERVICE_META, kept local
// here rather than extracted/shared — this is the only other place it's
// used, and the labels/copy needed here are FAQ-specific anyway.
const PLATFORMS = [
  {
    name: "OneSource360",
    icon: <CampaignIcon fontSize="small" />,
    color: "#0A21C7",
    role: "Performance data warehouse",
    detail:
      "Where campaign spend, leads, and cost-per-lead come from. This is the source of the numbers shown on the Campaigns tab, and it's usually the first place a problem shows up.",
  },
  {
    name: "SmartSpot360",
    icon: <InsightsIcon fontSize="small" />,
    color: "#9A6700",
    role: "TV & radio media buying",
    detail:
      "Decides which stations and time slots a campaign's TV/radio budget goes to. When Agent360 proposes shifting budget toward better-performing spots, this is the system it's acting on.",
  },
  {
    name: "Captivator360",
    icon: <AutorenewIcon fontSize="small" />,
    color: "#166534",
    role: "Ad creative performance",
    detail:
      "Tracks how well each ad creative is performing over time, using click-through rate versus that ad's own first week. A drop of 20% or more is what Agent360 checks before requesting a creative refresh.",
  },
  {
    name: "Maestro360",
    icon: <PhoneInTalkIcon fontSize="small" />,
    color: "#6E11B0",
    role: "Inbound call routing",
    detail:
      "Routes inbound calls to the right team and tracks how those calls convert. A quiet shift in call routing — calls going to a lower-performing or non-certified team — is exactly the kind of thing that's invisible in any single dashboard but shows up here.",
  },
];

const TABS = [
  {
    icon: <HomeIcon fontSize="small" />,
    color: "#0A21C7",
    name: "Overview",
    detail:
      "The home screen — flagged campaigns, anything waiting on your approval, and a live trail of recent agent activity. Also the first item in the top bar.",
  },
  {
    icon: <CampaignIcon fontSize="small" />,
    color: "#0A21C7",
    name: "Campaigns",
    detail:
      "Every campaign Agent360 is watching — vertical, channel, target cost-per-lead, and current status. This is your at-a-glance view of what's running.",
  },
  {
    icon: <GavelIcon fontSize="small" />,
    color: "#0A21C7",
    name: "Agent Actions",
    detail:
      "Every action Agent360 has taken or proposed, newest first — what it wants to do, why, its risk score, and its status. This is where you approve or reject anything waiting on you, and where you can look back at anything it's already done.",
  },
  {
    icon: <TimelineIcon fontSize="small" />,
    color: "#0A21C7",
    name: "Tool Calls",
    detail:
      "The full step-by-step trace of everything Agent360 checked, including lookups that didn't lead to an action — the reasoning process, not just the conclusion. Updates live while an investigation is in progress.",
  },
  {
    icon: <HubIcon fontSize="small" />,
    color: "#0A21C7",
    name: "Systems",
    detail:
      "One page per simulated application — what it does, a live snapshot of its Postgres tables, every REST endpoint, and the MCP tools that wrap those endpoints. This is where you trace “the agent said X” back to a specific HTTP call and a specific row.",
  },
  {
    icon: <InsightsIcon fontSize="small" />,
    color: "#9A6700",
    name: "Spots / Creatives / Call Routing",
    detail:
      "Still there as operational explorers (charts and campaign-level views). Open them from the matching Systems page — SmartSpot360, Captivator360, Maestro360 — rather than the top bar.",
  },
];

const OUTCOMES = [
  {
    tone: "success",
    label: "Executed (auto)",
    title: "Runs immediately",
    detail:
      "Small, well-supported, low-risk changes happen right away — nothing waits on you. But nothing happens invisibly either: it's logged in Agent Actions the moment it happens, with the reasoning attached and a snapshot of what things looked like beforehand, so it can always be reviewed after the fact.",
  },
  {
    tone: "warning",
    label: "Pending Approval",
    title: "Waits for you",
    detail:
      "Medium-risk changes stop and wait. You'll see it in Agent Actions with plain-language reasoning and Approve / Reject buttons right on the row. Nothing happens until you decide — rejecting it is always safe and simply declines that one action.",
  },
  {
    tone: "error",
    label: "Blocked",
    title: "Refused outright",
    detail:
      "Anything that would cross a hard safety limit — regardless of how the rest of the scoring came out — is refused automatically. Agent360 doesn't ask first; it declines and explains why, and can still propose something smaller instead.",
  },
];

const FAQ_ITEMS = [
  {
    q: "Can Agent360 spend money or make changes without me knowing?",
    a: "No. Every action it takes — automatic or not — is logged in Agent Actions the instant it happens, with its reasoning attached. Auto-execution is reserved for small, well-supported, low-risk changes, and a fixed safety ceiling sits on top of the risk scoring itself, so nothing large can slip through even if the scoring is wrong. Anything bigger always waits for a person.",
  },
  {
    q: "What happens if it gets something wrong?",
    a: "Every auto-executed action is logged with a snapshot of what the campaign looked like right before the change, so you can see exactly what happened and review it later. And for anything above the smallest, safest tier of change, it never executes without a person approving it first — a large change never happens unsupervised.",
  },
  {
    q: "Can this be turned off, or made stricter?",
    a: "Yes. The thresholds that decide what counts as auto-executed, needs-review, or blocked are configuration values, not behavior baked into Agent360 itself — they can be tightened so more goes to human review, or loosened as trust builds. The business sets the dial; Agent360 just enforces it consistently.",
  },
  {
    q: "Does Agent360 decide for itself what counts as \"risky\"?",
    a: "No. The risk score behind every action is a fixed, repeatable calculation — how big the change is, how much data backs it up, whether the campaign was already changed recently, and whether it's in a regulated category like Medicare Advantage. Given the same inputs, it produces the same score every time. It isn't a judgment call Agent360 makes on the fly.",
  },
  {
    q: "Why does it explain things in plain language instead of technical detail?",
    a: "Because the person deciding whether to approve an action usually isn't an engineer. The reasoning you see by default is written the way you'd explain it to a colleague — e.g. \"the ad creative has gone stale and calls are being routed to a lower-performing team\" — rather than raw metric names. The full technical trace (exact figures, raw arguments and results) is always one click away on the record's detail page, if you want it.",
  },
  {
    q: "What if I don't understand why it's recommending something?",
    a: "Every action's Reasoning field is meant to stand on its own without extra context. If it's still unclear, rejecting it is always the safe option — it doesn't undo anything or cause harm, it just declines that particular proposal. Agent360 can always be asked to investigate again or propose something else.",
  },
  {
    q: "What can Agent360 actually do — is it able to touch anything outside these systems?",
    a: "No. It only has access to the connected systems below, and only through a fixed, predefined set of actions — for example, reallocating budget between stations, or requesting a creative refresh. It can't take any action that isn't explicitly one of those defined tools.",
  },
];

const DATA_TERMS = [
  {
    term: "Campaign",
    def: "A named advertising effort. “Medicare Advantage – Southeast TV” means: sell Medicare Advantage plans, in the Southeast, by buying TV ads.",
  },
  {
    term: "Spend",
    def: "Dollars paid to run ads that day. Not profit — just the media bill.",
  },
  {
    term: "Lead",
    def: "A person who responded (called or filled a form). The thing the campaign is trying to generate.",
  },
  {
    term: "CPL (cost per lead)",
    def: "Spend ÷ leads. If we spent $7,200 and got 160 leads, CPL is $45. The campaign’s target CPL is the budgeted price we’re willing to pay for one inquiry. Lower is better.",
  },
  {
    term: "Spot",
    def: "One paid TV or radio airing: a station, a time of day, a date, and a cost. “WSVN Miami / Daytime on Aug 15 for $210” is a spot.",
  },
  {
    term: "Daypart",
    def: "The time-of-day window an ad airs. Prime (evening) costs more than Daytime.",
  },
  {
    term: "Budget allocation",
    def: "A plan for how a pile of money would be split across stations and dayparts — not the airing itself, the recommended mix.",
  },
  {
    term: "Creative",
    def: "The ad people actually see or hear (the 30-second video). CR-114 is a version name.",
  },
  {
    term: "CTR (click-through rate)",
    def: "People who responded ÷ people who saw the ad. 2.1% means 21 responses per 1,000 views.",
  },
  {
    term: "CTR decline",
    def: "(first-week CTR − last-week CTR) ÷ first-week CTR. A 20% or greater drop is the trigger to refresh the ad — the same rule Agent360 uses. Not a stored score; it is computed from daily CTR.",
  },
  {
    term: "Agent pool",
    def: "A team of call-center people who answer inbound calls. Pool A is Medicare-certified and converts more calls; Pool B is overflow, not certified, and converts fewer.",
  },
  {
    term: "Call routing",
    def: "Which team a new inbound call is sent to. When the certified team is full, overflow goes to the other pool.",
  },
  {
    term: "Call outcome",
    def: "How a phone call ended: conversion (the person signed up), no answer, voicemail, or dropped.",
  },
];

const GLOSSARY = [
  {
    term: "Agent",
    def: "The automated system (Agent360) that reads campaign data across the connected platforms and proposes or takes actions based on what it finds.",
  },
  {
    term: "MCP (Model Context Protocol)",
    def: "The standard way Agent360 exposes its capabilities so an AI agent can use them. In practice: the fixed menu of things Agent360 is allowed to check or do — nothing outside that menu is possible.",
  },
  {
    term: "Risk score",
    def: "A 0–100 number calculated for every proposed action — based on the size of the change, how much data supports it, how recently the campaign was touched, and whether it's in a regulated category. This score decides whether the action runs automatically, waits for approval, or gets blocked.",
  },
  {
    term: "Guardrail",
    def: "The safety layer that computes each risk score and enforces the fixed limits an action can never cross, no matter what the score itself comes out to.",
  },
  {
    term: "Tool call",
    def: "One single lookup or action Agent360 performs against one of the four connected systems — e.g. \"check this campaign's call quality.\" A full investigation is usually a chain of several tool calls, visible in the Tool Calls tab.",
  },
  {
    term: "Auto-executed",
    def: "An action that ran immediately, without waiting for a person, because it scored as low-risk.",
  },
  {
    term: "Pending approval",
    def: "An action that's waiting for a person to approve or reject it before anything happens.",
  },
  {
    term: "Blocked",
    def: "An action that was refused outright because it would have crossed a hard safety limit.",
  },
];

// Faq's own quick-nav + expand state — see SECTIONS below for the id/label/
// default-expanded map that both the nav row and each Collapsible read from.
const SECTIONS = [
  { id: "what-is", label: "What is Agent360?", defaultExpanded: true },
  { id: "how-it-works", label: "How it works", defaultExpanded: true },
  { id: "outcomes", label: "What happens to each action", defaultExpanded: true },
  { id: "tabs", label: "What's in each tab", defaultExpanded: false },
  { id: "platforms", label: "The four systems", defaultExpanded: false },
  { id: "data-terms", label: "What the numbers mean", defaultExpanded: false },
  { id: "faq-items", label: "FAQ", defaultExpanded: true },
  { id: "glossary", label: "Glossary", defaultExpanded: false },
];

const PlatformRow = ({ icon, color, name, role, detail }) => (
  <Box sx={{ display: "flex", gap: 2, py: 2, alignItems: "flex-start" }}>
    <IconTag icon={icon} color={color} />
    <Box sx={{ minWidth: 0 }}>
      <Typography sx={{ fontWeight: 700, fontSize: 15 }}>
        {name} <Typography component="span" sx={{ fontWeight: 400, color: "text.secondary", fontSize: 14 }}>— {role}</Typography>
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
        {detail}
      </Typography>
    </Box>
  </Box>
);

const TabRow = ({ icon, color, name, detail }) => (
  <Box sx={{ display: "flex", gap: 2, py: 2, alignItems: "flex-start" }}>
    <IconTag icon={icon} color={color} />
    <Box sx={{ minWidth: 0 }}>
      <Typography sx={{ fontWeight: 700, fontSize: 15 }}>{name}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
        {detail}
      </Typography>
    </Box>
  </Box>
);

const OutcomeCard = ({ tone, label, title, detail }) => (
  <Card variant="outlined" sx={{ flex: "1 1 240px", minWidth: 0, display: "flex", flexDirection: "column" }}>
    <CardContent>
      <StatusPill label={label} tone={tone} />
      <Typography sx={{ fontWeight: 700, fontSize: 15, mt: 1.5 }}>{title}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
        {detail}
      </Typography>
    </CardContent>
  </Card>
);

const FaqAccordion = ({ q, a, expanded, onChange }) => (
  <Accordion expanded={expanded} onChange={onChange} disableGutters elevation={0} variant="outlined">
    <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ "& .MuiAccordionSummary-content": { pr: 1, minWidth: 0 } }}>
      <Typography sx={{ fontWeight: 600, pr: 1 }}>{q}</Typography>
    </AccordionSummary>
    <AccordionDetails>
      <Typography variant="body2" color="text.secondary">
        {a}
      </Typography>
    </AccordionDetails>
  </Accordion>
);

export const FaqPage = () => {
  const [expandedIndex, setExpandedIndex] = useState(null);
  const [expanded, setExpanded] = useState(() =>
    Object.fromEntries(SECTIONS.map((s) => [s.id, s.defaultExpanded]))
  );
  const toggleSection = (id) => setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  const expandAndScroll = (id) => {
    setExpanded((prev) => ({ ...prev, [id]: true }));
    requestAnimationFrame(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  return (
    <Box sx={{ width: "100%", maxWidth: 880, mx: "auto", py: { xs: 1, md: 2 } }}>
      <PageHeader
        title="Guide"
        subtitle="Everything on this page is written for anyone using Agent360 day to day — no technical background assumed. If a term still isn’t clear, check the glossary at the bottom. This is a local demo with simulated platforms and seeded data."
      />

      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 5 }}>
        {SECTIONS.map(({ id, label }) => (
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
      </Box>

      <Collapsible layout="plain" id="what-is" title="What is Agent360?" expanded={expanded["what-is"]} onToggle={() => toggleSection("what-is")}>
        <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
          Agent360 is your team's always-on analyst for campaign performance — in this
          demo, across four simulated systems with seeded data. It continuously watches
          campaign metrics, and when something looks off — like a campaign's cost-per-lead
          jumping well above target — it flags the campaign for investigation. An agent
          (or a person) can then dig across systems, figure out what's going on, and
          propose a fix. It only ever acts with as much independence as the situation has
          earned: small, well-understood changes happen on their own, and anything bigger
          stops and waits for a person.
        </Typography>
      </Collapsible>

      <Collapsible
        layout="plain"
        id="how-it-works"
        title="How it works, in three steps"
        expanded={expanded["how-it-works"]}
        onToggle={() => toggleSection("how-it-works")}
      >
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2.5 }}>
          <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
            <strong>1. Watches.</strong> Every campaign's cost-per-lead, creative performance, and
            call quality is tracked continuously across the four connected platforms below.
          </Typography>
          <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
            <strong>2. Investigates.</strong> When something crosses a threshold — cost-per-lead
            rising well above a campaign's target, for example — the automated sweep flags the
            campaign. An agent then checks each connected system in turn to find the actual cause,
            not just where the symptom showed up. Often the real answer only becomes clear by
            looking at two systems together (see the Tool Calls tab for the full trail).
          </Typography>
          <Typography variant="body1" sx={{ lineHeight: 1.7 }}>
            <strong>3. Acts, carefully.</strong> Once it has an answer, Agent360 proposes one or
            more fixes. Every proposed action is scored for risk before anything happens — see
            below for exactly what that means.
          </Typography>
        </Box>
      </Collapsible>

      <Collapsible
        layout="plain"
        id="outcomes"
        title="What happens to each action it proposes"
        expanded={expanded.outcomes}
        onToggle={() => toggleSection("outcomes")}
      >
        <Typography variant="body1" sx={{ lineHeight: 1.7, mb: 3 }}>
          Every action Agent360 wants to take is scored for risk first — how big the change is,
          how much data supports it, and whether the campaign is in a regulated category like
          Medicare Advantage all factor in. That score decides which of three things happens next:
        </Typography>
        <Box sx={{ display: "flex", gap: 2, flexWrap: "wrap", alignItems: "stretch" }}>
          {OUTCOMES.map((o) => (
            <OutcomeCard key={o.label} {...o} />
          ))}
        </Box>
      </Collapsible>

      <Collapsible layout="plain" id="tabs" title="What you'll find in each tab" expanded={expanded.tabs} onToggle={() => toggleSection("tabs")}>
        <Card variant="outlined">
          <CardContent sx={{ py: 1 }}>
            {TABS.map((t, i) => (
              <Box key={t.name}>
                <TabRow {...t} />
                {i < TABS.length - 1 && <Divider />}
              </Box>
            ))}
          </CardContent>
        </Card>
      </Collapsible>

      <Collapsible
        layout="plain"
        id="platforms"
        title="The four systems it's connected to"
        expanded={expanded.platforms}
        onToggle={() => toggleSection("platforms")}
      >
        <Typography variant="body1" sx={{ lineHeight: 1.7, mb: 1 }}>
          Agent360 doesn't own any campaign data itself — it reads from and acts on four
          independent systems that didn't previously talk to each other. Connecting them is the
          whole point. Open Campaigns in the top bar to see the warehouse rows; open Spots,
          Creatives, or Call Routing from the matching Systems page. Each of those lists starts
          with a short “what this table is” explainer.
        </Typography>
        <Card variant="outlined">
          <CardContent sx={{ py: 1 }}>
            {PLATFORMS.map((p, i) => (
              <Box key={p.name}>
                <PlatformRow {...p} />
                {i < PLATFORMS.length - 1 && <Divider />}
              </Box>
            ))}
          </CardContent>
        </Card>
      </Collapsible>

      <Collapsible
        layout="plain"
        id="data-terms"
        title="What the numbers actually mean"
        expanded={expanded["data-terms"]}
        onToggle={() => toggleSection("data-terms")}
      >
        <Typography variant="body1" sx={{ lineHeight: 1.7, mb: 2 }}>
          These four systems don't run a real TV buy or a live call center. They store the
          records those systems would have produced. That's enough for an agent to investigate —
          it needs the data, not the machinery that created it.
        </Typography>
        <Card variant="outlined">
          <CardContent sx={{ py: 1 }}>
            {DATA_TERMS.map((g, i) => (
              <Box key={g.term}>
                <Box sx={{ py: 1.5 }}>
                  <Typography sx={{ fontWeight: 700, fontSize: 14 }}>{g.term}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
                    {g.def}
                  </Typography>
                </Box>
                {i < DATA_TERMS.length - 1 && <Divider />}
              </Box>
            ))}
          </CardContent>
        </Card>
      </Collapsible>

      <Collapsible layout="plain" id="faq-items" title="Frequently asked questions" expanded={expanded["faq-items"]} onToggle={() => toggleSection("faq-items")}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
          {FAQ_ITEMS.map((item, i) => (
            <FaqAccordion
              key={item.q}
              q={item.q}
              a={item.a}
              expanded={expandedIndex === i}
              onChange={(_, isExpanded) => setExpandedIndex(isExpanded ? i : null)}
            />
          ))}
        </Box>
      </Collapsible>

      <Collapsible layout="plain" id="glossary" title="Glossary" expanded={expanded.glossary} onToggle={() => toggleSection("glossary")}>
        <Card variant="outlined">
          <CardContent sx={{ py: 1 }}>
            {GLOSSARY.map((g, i) => (
              <Box key={g.term}>
                <Box sx={{ py: 1.5 }}>
                  <Typography sx={{ fontWeight: 700, fontSize: 14 }}>{g.term}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
                    {g.def}
                  </Typography>
                </Box>
                {i < GLOSSARY.length - 1 && <Divider />}
              </Box>
            ))}
          </CardContent>
        </Card>
      </Collapsible>
    </Box>
  );
};

export default FaqPage;
