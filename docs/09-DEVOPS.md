# 09. DevOps

## 1. Environments

| Env | How it runs | Notes |
|---|---|---|
| Local dev | `make up` (Postgres in Docker) + `make dev` (api and web with reload) | Uses `.env` |
| CI | GitHub Actions | Postgres service container; no real LLM calls except gated evals |
| Demo/prod | Docker images behind a reverse proxy, or a PaaS | Secrets from the platform; managed Postgres with pgvector |

## 2. Configuration

`.env.example` (committed, placeholders only):

```bash
# --- App ---
APP_ENV=development            # development | test | production
LOG_LEVEL=INFO
API_KEY=change-me-dev-key
CORS_ORIGINS=http://localhost:3000

# --- Database ---
DATABASE_URL=postgresql+asyncpg://research:research@localhost:5432/research

# --- Models (provider:model strings) ---
MODEL_PLANNER=anthropic:claude-sonnet-5-5
MODEL_SEARCHER=anthropic:claude-haiku-5-5
MODEL_READER=anthropic:claude-haiku-5-5
MODEL_CRITIC=anthropic:claude-sonnet-5-5
MODEL_WRITER=anthropic:claude-sonnet-5-5
MODEL_CURATOR=anthropic:claude-haiku-5-5
ANTHROPIC_API_KEY=
OPENAI_API_KEY=                # optional (other models or embeddings)

# --- Embeddings ---
EMBEDDER=fastembed             # fastembed | openai
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_DIM=384

# --- Search ---
SEARCH_PROVIDER=tavily         # tavily | brave | fake
TAVILY_API_KEY=
BRAVE_API_KEY=

# --- Budgets and limits (server maximums and defaults) ---
MAX_ACTIVE_RUNS_PER_USER=2
MAX_CONCURRENT_FETCHES=5
MAX_CONCURRENT_LLM_CALLS=8
FETCH_TIMEOUT_S=15
FETCH_MAX_BYTES=2000000
SOURCE_TTL_DAYS=14
RESPECT_ROBOTS=true
SERVER_MAX_COST_USD=5.0
SERVER_MAX_FETCHES=150
SERVER_MAX_ITERATIONS=6

# --- Observability (optional) ---
LOGFIRE_TOKEN=
OTEL_EXPORTER_OTLP_ENDPOINT=

# --- Web (apps/web/.env.local) ---
API_BASE_URL=http://localhost:8000
# API_KEY is read server-side from the same value; never prefix with NEXT_PUBLIC_
```

Model names above come from the model lineup at the time of writing; check provider docs for current identifiers and PydanticAI's model string format before relying on them.

## 3. Makefile targets

```
setup        uv sync + pnpm install + pre-commit install
up / down    docker compose up -d db / down
migrate      alembic upgrade head
dev          run api (uvicorn --reload) and web (next dev) together
lint         ruff check + ruff format --check + eslint + prettier --check
fmt          ruff format + prettier --write
typecheck    pyright + tsc --noEmit
test         pytest -m "unit"   + vitest run
test-int     pytest -m integration   (requires db)
e2e          playwright test
eval         python -m evals.run_evals --smoke
types        export openapi.json + openapi-typescript -> src/types/api.d.ts
check        lint + typecheck + test + test-int + types-drift check
```

## 4. Docker

- **API image** (`infra/api.Dockerfile`): multi-stage with `uv`; builder installs deps from `uv.lock`; runtime is `python:3.12-slim`, non-root user, no build tools, `HEALTHCHECK` on `/healthz`. Command: `uvicorn research_agent.main:app --host 0.0.0.0 --port 8000` with **one worker** in v1 (run ownership lives in-process; see architecture §5).
- **Web image** (`infra/web.Dockerfile`): multi-stage; Next.js `output: "standalone"`; non-root; build args only for non-secret values; runtime env supplies `API_BASE_URL` and `API_KEY`.
- **Compose** (`docker-compose.yml`):
  - `db`: `pgvector/pgvector:pg16` (or current pgvector tag), volume, healthcheck (`pg_isready`)
  - `api`: depends on `db` healthy; runs migrations on start via an entrypoint step (`alembic upgrade head`) in dev; in production run migrations as a separate job
  - `web`: depends on `api`
  - Profiles: default (db only for local dev), `full` (db, api, web)
- Pin base image digests in production builds; scan images with Trivy in CI.

## 5. CI (`.github/workflows/ci.yml`)

Jobs (run in parallel where possible):

1. **api**: setup uv with cache; `ruff`, `pyright`, `pytest -m unit` with coverage; start Postgres service (pgvector image); `alembic upgrade head`; `pytest -m integration`; upload coverage.
2. **web**: setup pnpm and Node (current LTS); `eslint`, `tsc --noEmit`, `vitest`, `next build`; grep build for `API_KEY` leakage.
3. **contract**: regenerate `openapi.json` and TS types; `git diff --exit-code` to detect drift.
4. **e2e**: build web, run the fake SSE backend and Playwright (cache browsers); upload traces on failure.
5. **docker**: build both images (no push on PRs); Trivy scan.
6. **evals** (nightly cron and PR label `run-evals`): recorded-mode smoke evals with repository secrets; compare to baseline; upload report as artifact. Never runs on forks.
7. **security** (weekly and on PR): `pip-audit`, `pnpm audit`, CodeQL.

Branch protection: required checks `api`, `web`, `contract`, `e2e`, `docker`. Squash merge with Conventional Commit titles.

## 6. Pre-commit

`ruff` (lint + format), `pyright` (optional, slower: pre-push), `prettier`, `eslint`, `detect-secrets` or `gitleaks`, end-of-file/trailing-whitespace, large-file check.

## 7. Database operations

- Migrations: Alembic, linear history, one migration per change, reviewed. Never edit an applied migration.
- pgvector: create the extension in the first migration; index parameters (HNSW `m`, `ef_construction`) documented in the migration comments.
- Backups: daily logical backup (`pg_dump`) retained 14 days for prod; test a restore once.
- Retention: runs and events retained 180 days by default (setting); the `sources` cache pruned when older than 90 days and not referenced by any run.

## 8. Observability in production

- JSON logs to stdout; collect with the platform.
- OTel traces: set `OTEL_EXPORTER_OTLP_ENDPOINT` or `LOGFIRE_TOKEN`. Each run is a root span with child spans per phase and per agent call; attributes: `run_id`, `agent`, `model`, tokens, cost.
- Alerts (if hosted): error rate on `/v1/runs`, run failure ratio, p95 run duration, daily cost over threshold.

## 9. Deployment guidance

| Piece | Options | Notes |
|---|---|---|
| API | Fly.io, Render, Railway, a VM with Docker | Long-lived SSE connections and in-process runs: use a **long-running container**, not serverless functions |
| Web | Same host (standalone), or Vercel | If on Vercel, SSE proxying through route handlers is subject to function duration limits; prefer a short-lived signed stream token so the browser connects to the API directly for `/events` (a Phase 12 option, see ADR-0005) |
| Postgres | Neon, Supabase, RDS, self-hosted `pgvector` | Confirm pgvector support and version |
| Secrets | Platform secret store | Never in images or the repo |
| TLS and proxy | Caddy or Traefik; disable proxy buffering for the SSE route | `X-Accel-Buffering: no` is already sent |

## 10. Release process

- Trunk-based: short-lived branches, PRs, squash merges.
- Tag `vX.Y.Z` triggers image builds and pushes to the registry (GitHub Container Registry).
- `CHANGELOG.md` generated from Conventional Commits (e.g. `git-cliff`).
- `docs/VERSIONS.md` records the pinned versions of PydanticAI, Next.js, Postgres/pgvector, Python, Node, and the model identifiers used in the last eval baseline.
