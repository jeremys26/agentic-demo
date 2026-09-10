# 12 — GraphQL with Strawberry

**Status**: complete. One investigation-shaped join query on the MCP gateway — not a parallel full GraphQL API.

## What it is

**GraphQL** is a query language for APIs. The client asks for exactly the fields it needs in one request; the server resolves them. Contrast with REST, where each URL returns a fixed shape and cross-resource joins often mean multiple round trips.

**Strawberry** is a Python GraphQL library that defines types with dataclasses / type hints and integrates with FastAPI via `GraphQLRouter`.

## Why this piece of the stack is used here

`PLANNING.md` is explicit about judgment: **one join query across four platforms, not a second full API.** The agent already multi-calls MCP tools. GraphQL shows:

1. The gateway is the natural place for a cross-service join (it alone talks to all four)
2. When GraphQL earns its keep (shaped reads for a known investigation), vs when REST/MCP tools are enough

It is a teaching and demo flourish, not the primary agent interface.

## Where it lives

`mcp_server/graphql_api.py`, mounted in `main.py`:

```python
app.include_router(graphql_app, prefix="/graphql")
```

Open **GraphiQL** (interactive IDE): http://localhost:8100/graphql

### Schema (conceptual)

```graphql
type PoolShare {
  poolName: String!
  isCertifiedMedicare: Boolean!
  pctOfTotal: Float!
  conversionRate: Float!
}

type CampaignInvestigation {
  campaignId: Int!
  name: String!
  # ... targetCpl, windowCpl, cplVariancePct, flagged,
  # spotCount, latestCtrDeclinePct, decliningVariantLabels,
  # uncertifiedPoolPct, poolDistribution
}

type Query {
  campaignInvestigation(campaignId: Int!): CampaignInvestigation!
}
```

Strawberry exposes Python `snake_case` fields as camelCase in GraphQL by default.

### Resolver behavior

`fetch_campaign_investigation(campaign_id)` uses `service_client()` to call:

| Service | REST |
|---|---|
| OneSource360 | `/api/campaigns/{id}/`, `/api/performance/` |
| SmartSpot360 | `/api/spots/?campaign_id=` |
| Captivator360 | `/api/creatives/` + per-creative `/performance/` |
| Maestro360 | `/api/calls/summary/` |

It computes windowed CPL / variance with the same threshold constant `DEFAULT_ANOMALY_THRESHOLD_PCT` imported from `tools.onesource360` — so GraphQL `flagged` and the MCP anomaly tool cannot silently disagree.

This is an **HTTP fan-out join**, not a SQL join. Same isolation rules as everywhere else (`03`).

## Example query

```graphql
query {
  campaignInvestigation(campaignId: 1) {
    name
    windowCpl
    cplVariancePct
    flagged
    spotCount
    latestCtrDeclinePct
    decliningVariantLabels
    uncertifiedPoolPct
    poolDistribution {
      poolName
      isCertifiedMedicare
      pctOfTotal
    }
  }
}
```

## GraphQL vs MCP tools vs REST

| Path | Best for |
|---|---|
| MCP tools | Agent investigation + governed writes |
| Per-service REST | Console resources, webhooks, OpenAPI |
| GraphQL `campaignInvestigation` | One shaped read for humans/demos/CI asserting the join |

The agent does not need GraphQL to succeed. You might use it in a slide or a test (`tests/test_graphql.py` covers windowed CPL math).

## Key vocabulary

- **Schema** — the graph of types and fields the server supports.
- **Query / Mutation** — read vs write entry points; this demo only defines Query.
- **Resolver** — function that loads a field's data (here: mostly one big fetch function).
- **GraphiQL** — in-browser IDE for exploring a GraphQL schema.
- **Over-fetching / under-fetching** — REST problems GraphQL addresses; less critical at this demo's scale.
- **N+1** — resolver anti-pattern; Captivator's per-creative detail loop is a mild version — acceptable at seed size, worth noticing.

## Try this yourself

Open http://localhost:8100/graphql, paste the query above, run it. Then compare:

```bash
curl -s 'http://localhost:8001/api/performance/?campaign_id=1' | python -m json.tool | head
curl -s 'http://localhost:8004/api/calls/summary/?campaign_id=1' | python -m json.tool | head
```

Same facts; GraphQL packages them in one round trip from the client's perspective.

**Related:** `05` (gateway), `11` (FastAPI mount), `14` (tests).
