# Agent360 — A Guide for the Rest of Us

This is written for anyone who uses Agent360 day to day and doesn’t need — or want — the
engineering details. If you manage campaigns, review budget changes, or just want to understand
what this system is doing before you trust it, this doc is for you.

No background in software is assumed. If a term shows up that isn’t explained where you first see
it, check the glossary at the bottom.

**This is a local demo.** The four “connected systems” below are simulated platforms with seeded
data — enough to investigate and approve real-looking actions, not a live media buy or call center.

---

## What this is, and why it exists

In a performance-marketing stack like this, campaign data often lives in several different places:
one system tracks how a campaign is performing (cost per lead, spend, leads), another decides which
TV and radio spots to buy, another manages the actual ad creative, and another routes and tracks
the phone calls a campaign generates. None of these systems talk to each other on their own. When
something goes wrong — a campaign’s cost per lead suddenly jumps — nobody sees the full picture in
one place. Someone has to manually check each system, one at a time, and piece together what’s
going on. That doesn’t scale as the number of campaigns grows.

Agent360 is built to close that gap. An automated sweep watches all four systems and flags
campaigns when something looks wrong. An agent (or a person) can then check each connected
system in turn to find out why — often the real answer only shows up once you look at two
systems together, which is exactly the kind of thing a single dashboard can't do. Once it has
an answer, it can act on it: some changes it's trusted to make on its own, and anything bigger
stops and waits for a person to say yes. Nothing happens without a clear, plain-language
explanation attached — the goal is a system you can actually supervise, not one you have to
take on faith.

---

## What the three outcomes mean, day to day

Every change Agent360 wants to make — before anything happens — gets scored for how risky it is:
how big the change is, how much data backs it up, and whether the campaign is in a sensitive,
regulated category (Medicare Advantage campaigns get held to a stricter standard than most). That
score is called a **risk score**, and it decides which of three things happens next.

**✅ Executed automatically.** Small, well-supported, low-risk changes happen immediately —
nothing waits on you. This isn't a black box, though: it's logged in the **Agent Actions** screen
the moment it happens, with the reasoning attached and a snapshot of what things looked like right
before the change, so it can always be reviewed after the fact.

**⏳ Needs your approval.** Medium-risk changes stop and wait for a person. You'll find it in
**Agent Actions** with the reasoning written in plain business language, and *Approve* / *Reject*
buttons right on the row. Nothing happens until you decide. Rejecting one is always safe — it
simply declines that specific proposal and doesn't undo or break anything.

**🚫 Blocked.** Anything that would cross a hard safety ceiling gets refused outright, no matter
how the rest of the scoring came out. Agent360 doesn't ask first in this case — it declines and
explains why, and it's free to come back with something smaller instead.

These thresholds aren't something Agent360 decides for itself — they're configuration the business
sets. They can be tightened so more goes to human review, or loosened as trust builds. Agent360
just enforces whatever the current setting is, consistently, every time.

---

## A walkthrough: the Medicare Advantage campaign

This is the seeded demo scenario you’ll see if you run the investigation yourself — not a live
production incident, but the same story the console and agent tools are built around.

**The problem.** “Medicare Advantage – Southeast TV” had a target cost per lead of **$45**. Over
the most recent week of activity, its actual cost per lead had climbed to roughly **$67** —
about **49% over target** — while overall spend hadn’t changed. Something was making each lead
meaningfully more expensive to generate, and no single dashboard showed why.

**The investigation.** Asked to look into it, Agent360 worked through each connected system in
turn:

- It checked the media-buying system first and ruled out an obvious explanation — the TV/radio
  spot mix hadn't changed, so a bad buying decision wasn't the cause.
- It checked the creative system next and found the campaign's only active ad ("CR-114") had gone
  stale: first-week click-through rate around 2.0% had fallen to about 1.5% over
  the last week — roughly a 25% drop versus its own launch, past the 20% refresh trigger.
- It checked the call-routing system and found calls had been quietly drifting toward a
  lower-converting team that isn't Medicare-certified — a compliance-relevant detail given the
  vertical, and a pattern invisible unless you're specifically comparing routing data against
  performance data, which no single platform does on its own.

Neither fact alone fully explained a 49% cost jump. Together, they did — and the answer only
existed at the intersection of two systems that had never previously been checked side by side.

**What it did about it.** Agent360 proposed a set of fixes, and the risk-scoring layer sorted them
into exactly the three outcomes described above, in the same investigation:

- A **$500** shift of media budget toward the better-performing time slot — small relative to
  the campaign's usual spend and backed by solid historical spot data — **executed
  automatically**.
- A **$20,000** version of that same reallocation — the same reasoning, at a scale that crossed
  into "a person should sign off on this" — was **queued for approval**, reasoning attached,
  waiting in the Agent Actions screen.
- A request to refresh the stale creative was **blocked outright**, because — unlike the budget
  case — that creative was the campaign's *only* active one; pulling it for a refresh would have
  left the campaign with nothing running at all. Agent360 was told exactly why and left free to
  propose something smaller instead.

One investigation, three different outcomes, each handled the way its own risk actually called
for — not a single blanket "ask a human every time" rule, and not a system quietly spending real
budget unsupervised either.

**Watching it stay current.** The Overview screen can also **advance one day**: new performance,
spots, creative metrics, and call events land in each platform the same way a real overnight data
drop would. Campaign 1 stays expensive on purpose, so the automated check keeps flagging it
without anyone re-seeding the database.

---

## Frequently asked questions

**Can it spend money without me knowing?**
No. Every action it takes — automatic or not — is logged in Agent Actions the instant it happens,
with its reasoning attached. Auto-executed actions are reserved for small, well-supported,
low-risk changes only, and a fixed safety ceiling applies on top of the scoring itself, so nothing
large can slip through even if the scoring were ever wrong on a particular case. Anything bigger
always waits for a person.

**What happens if it gets something wrong?**
Every auto-executed action is logged together with a snapshot of what the campaign looked like
right beforehand, so you can see exactly what changed and audit it after the fact. And for anything above the
smallest, safest tier of change, it never executes at all without a person approving it first —
there's no path where a large or uncertain change happens unsupervised.

**Can this be turned off, or made stricter?**
Yes. The thresholds that decide what counts as auto-executed, needs-review, or blocked are
configuration values, not behavior baked into how Agent360 works — they can be tightened or
loosened. The business sets the dial.

**Does it decide for itself what counts as "risky"?**
No. The risk score behind every action is a fixed, repeatable calculation — the size of the
change, how much data supports it, whether the campaign was already touched recently, and whether
it's in a regulated category. Given the same inputs, it produces the same score every time. It
isn't a judgment call made on the fly.

**Why does it explain things in plain language instead of technical detail?**
Because the person deciding whether to approve an action usually isn't an engineer. What you see
by default is written the way you'd explain it to a colleague — e.g. "the ad creative has gone
stale and calls are being routed to a lower-performing team" — not a raw metric name. The full
technical detail is still logged and available if you want it; it's just not the default view.

**What if I don't understand why it's recommending something?**
Every proposed action's reasoning is meant to stand on its own. If it's still unclear, rejecting
it is always the safe option — it doesn't undo or break anything, it just declines that one
proposal.

**Can Agent360 touch anything outside these four systems?**
No. It only has access to the four connected systems below, and only through a fixed set of
predefined actions. It can't take any action that isn't explicitly one of those defined tools.

---

## The four connected systems

These systems don't run a real TV buy or a live call center. They store the records those
systems would have produced, which is what Agent360 actually needs to investigate.

- **OneSource360** — the performance data warehouse. Each **campaign** is a named advertising
  effort (e.g. “Medicare Advantage – Southeast TV”). Each day it records **spend** (dollars paid
  to run ads), **leads** (people who responded), and **CPL** (spend ÷ leads). Target CPL is the
  budgeted price we're willing to pay for one inquiry. This is usually the first place a problem
  becomes visible.
- **SmartSpot360** — TV and radio media buying. A **spot** is one paid airing: a station, a
  time of day (**daypart**), a date, and a cost. **Budget allocation** is the plan for how a pile
  of money would be split across those combos. This is what gets adjusted when Agent360 proposes
  a reallocation.
- **Captivator360** — ad creative performance. A **creative** is the ad people actually see
  (CR-114 is a version name). **CTR** is how often viewers respond (responses ÷ impressions).
  **CTR decline** is how far the last week sits below this ad's own first week; 20% or more
  is the refresh trigger. This is what Agent360 checks before requesting a refresh.
- **Maestro360** — inbound call routing. An **agent pool** is a call-center team. **Routing**
  decides which team answers a new call. A **call event** is one phone call and how it ended
  (signed up, no answer, voicemail, dropped). A quiet shift toward a lower-converting or
  non-certified pool is invisible in any single dashboard.

The four systems don't share a database. They correlate by campaign id (campaign 1 in
OneSource360 is the same campaign 1 the other three refer to). Open Campaigns, Spots, Creatives,
or Call Routing in the console to see the actual rows.

---

## Glossary

- **Agent** — the automated system (Agent360) that reads campaign data across the connected
  systems and proposes or takes actions based on what it finds.
- **MCP (Model Context Protocol)** — the standard way Agent360 exposes its capabilities so an AI
  agent can use them. In practice: it's the fixed menu of things Agent360 is allowed to check or
  do — nothing outside that menu is possible.
- **Guardrail** — the safety layer that computes each risk score and enforces the fixed limits an
  action can never cross, no matter what the score itself comes out to.
- **Risk score** — a 0–100 number calculated for every proposed action, based on the size of the
  change, how much data supports it, how recently the campaign was touched, and whether it's in a
  regulated category. This score decides whether the action runs automatically, waits for
  approval, or gets blocked.
- **Auto-executed** — an action that ran immediately, without waiting for a person, because it
  scored as low-risk.
- **Pending approval** — an action that's waiting for a person to approve or reject it before
  anything happens.
- **Blocked** — an action that was refused outright because it would have crossed a hard safety
  limit.
- **Tool call** — one single lookup or action Agent360 performs against one of the four connected
  systems. A full investigation is usually a chain of several of these in sequence.
- **Campaign** — a named advertising effort (product + region + channel).
- **Spend** — dollars paid to run ads that day.
- **Lead** — a person who responded (called or filled a form).
- **CPL** — cost per lead: spend ÷ leads. Lower is better.
- **Spot** — one paid TV or radio airing.
- **Creative** — the ad itself. CTR is how often viewers respond; CTR decline is that rate versus the ad's own first week.
- **Agent pool** — a team of call-center people. Routing is which team gets the next inbound
  call.
