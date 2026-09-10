# 15 — CI with GitHub Actions

**Status**: complete. Every push and pull request runs MCP pytest + a frontend production build.

## What it is

**CI (Continuous Integration)** automatically runs checks on every change so broken tests or an unbuildable frontend get caught before merge — not during a live demo.

**GitHub Actions** is GitHub's built-in CI: YAML workflows under `.github/workflows/` define **jobs** (machines) made of **steps** (checkout, setup language, install, run commands).

## Why this piece of the stack is used here

Two cheap, high-signal gates match the project's risk profile:

1. **`pytest` on `mcp_server/`** — especially scoring/policy (`14`)
2. **`npm run build` on `frontend/`** — Vite production compile (syntax/import errors fail the build)

No Docker Compose-in-CI stack, no browser e2e — proportionate for a local demo repo, while still covering the safety-critical Python and the ship/buildability of the console.

## Where it lives

`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  mcp-tests:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: mcp_server
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pytest

  frontend-build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run build
```

### Reading the workflow

| Key | Meaning |
|---|---|
| `on: push / pull_request` | Triggers |
| `runs-on: ubuntu-latest` | Ephemeral VM image |
| `defaults.run.working-directory` | `cd` for subsequent `run:` steps |
| `actions/checkout` | Clone the repo into the VM |
| `setup-python` / `setup-node` | Language toolchains |
| `npm ci` | Clean install from lockfile (preferred over `npm install` in CI) |
| Two jobs | Run in **parallel**; either can fail the workflow |

## What CI does *not* run

- Full `docker compose up` (heavy; needs Docker-in-Docker or larger runners)
- Live Claude Code / MCP handshake
- Django `manage.py test` per sim (sims are thin; gateway tests carry the policy weight)
- Frontend unit/e2e tests (none packaged yet — `14`)

If a bug only appears when all containers interact, you still catch it locally. CI catches pure scoring regressions and frontend build breaks — the usual "I forgot to run tests" failures.

## Badges and PRs

On GitHub, each PR shows check status for `mcp-tests` and `frontend-build`. Red checks should block merge by social convention (and branch protection if enabled). Locally, run the same commands before pushing when you touch those trees.

## Key vocabulary

- **Workflow** — one YAML automation file.
- **Job** — one runner; jobs in a workflow are parallel by default.
- **Step** — one command or action inside a job.
- **Action** — reusable packaged step (`actions/checkout@v4`).
- **Lockfile** — `package-lock.json` / pinned `requirements.txt` for reproducible installs.
- **`npm ci`** — install exact lockfile versions; fails if lock out of sync with `package.json`.

## Try this yourself

```bash
# Same as CI, locally
cd mcp_server && pip install -r requirements.txt && pytest
cd ../frontend && npm ci && npm run build
```

After pushing, open the repo's Actions tab on GitHub and click the run for your commit — expand failed steps if any.

**Related:** `14` (what pytest covers), `08` (frontend build), `09` (why full Compose isn't in CI yet).
