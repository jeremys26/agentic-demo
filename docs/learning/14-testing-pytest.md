# 14 — Testing with pytest

**Status**: complete. MCP server test suite; CI runs it on every push (`15`). Heaviest coverage is the risk-scoring guardrail.

## What it is

**pytest** is the standard Python test runner for this ecosystem. You write functions (or methods on classes) named `test_*`; pytest discovers and runs them, reports failures with asserts.

Extras used here:

- **`pytest-asyncio`** — run `async def test_*` coroutines
- Plain **`assert`** — no `unittest.TestCase` required (classes are still used for grouping)

## Why this piece of the stack is used here

The risk-scoring function is safety-critical (`PLANNING.md` §7). Pure functions with no I/O are cheap to test exhaustively — every threshold boundary, hard-cap interaction, and weight contribution. That is where a bug would be most dangerous, so it gets the heaviest suite.

Other tests lock in simulator math, GraphQL window helpers, catalog shape, CTR decline helpers, and logging helpers — so refactors don't silently break demo invariants.

## Where it lives

```
mcp_server/
├── pytest.ini
├── requirements.txt      # pytest, pytest-asyncio
└── tests/
    ├── test_scoring.py   # compute_score + policy.route (primary)
    ├── test_logging.py
    ├── test_simulator.py
    ├── test_graphql.py
    ├── test_ctr_decline.py
    └── test_catalog.py
```

Run from the host (with deps installed) or however CI does it:

```bash
cd mcp_server && pytest
```

GitHub Actions: `pip install -r requirements.txt` then `pytest` with `working-directory: mcp_server` (`15`).

## What `test_scoring.py` teaches

Read the module docstring — it is unusually honest:

- Tests **`compute_score` and `policy.route` only** (pure)
- Does **not** auto-test `gather_*_inputs` HTTP/DB I/O — called out as a real coverage gap worth closing with mocked-httpx tests later
- Includes **`TestLiveDemoScenarioReplay`** — fixed inputs matching the live campaign-1 three-tier demo so the story and the math cannot diverge unnoticed

Examples of assertions you'll see:

- all-zero risk inputs → score 0 → `auto_execute`
- max risk + Medicare multiplier → capped at 100 → `blocked`
- magnitude > 100 preserved in output but clamped for scoring
- confidence inverted (higher confidence → lower risk)
- hard cap forces `pending_approval` even when score alone would auto-execute
- block threshold wins over hard-cap nuances when score is high enough

That file is a good template for testing policy engines: **pure core first, I/O later**.

## How to read a failure

```text
E   AssertionError: assert 48.85 == 30
```

pytest shows the assert line, locals, and traceback. Fix the code or the expectation — for scoring tests, prefer fixing code unless the product policy intentionally changed (then update defaults *and* tests together).

## Frontend testing note

There is no Jest/Vitest suite in `frontend/` today. CI's frontend job is **`npm run build`** — a compile/bundle gate, not unit tests (`15`). That's a deliberate scope choice for a demo console, not a claim that UI tests are unnecessary in production.

## Key vocabulary

- **Test discovery** — pytest finds `test_*.py` / `*_test.py` and `test_*` callables.
- **Assertion** — `assert condition` with rich introspection on failure.
- **Pure function** — same inputs → same outputs, no I/O; easiest and highest-value to test.
- **Fixture** — reusable setup via `@pytest.fixture` (used lightly here; know the concept).
- **Coverage gap** — code paths with no automated test; document them rather than pretending the suite is total.
- **Regression test** — locks a previously fixed bug or a live demo invariant (scenario replay).

## Try this yourself

```bash
cd mcp_server
pytest                         # full suite
pytest tests/test_scoring.py -q
pytest -k hard_cap             # substring match on test names
pytest tests/test_scoring.py::TestLiveDemoScenarioReplay -v
```

Then change `AUTO_EXECUTE_THRESHOLD` in `policy.py` temporarily and re-run — watch which tests fail. That shows how policy and tests are coupled on purpose.

**Related:** `05` (what scoring protects), `15` (CI wiring).
