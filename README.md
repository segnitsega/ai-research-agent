# Research Agent

A reading desk that does the boring parts of research for you: plan the question, hunt sources, pull quotes that actually appear on the page, argue with itself about gaps, then file a cited report.

**Live demo → [ai-research-agent-gxjy.onrender.com](https://ai-research-agent-gxjy.onrender.com/)**

Ask something worth a paper trail. Watch six agents work the desk in real time.

---

## Why it exists

Most “AI research” demos invent citations. This one doesn’t get to cite a line unless that quote is still on the fetched page. The critic can send the desk around again. Budgets (cost, fetches, iterations, wall time) are real ceilings, not vibes. Memory can recall what you preferred last time — if you want it to.

---

## How a run moves

1. **Recall** — optional memory: preferences, facts, earlier episodes  
2. **Plan** — objective + ranked sub-questions  
3. **Search & read** — find pages, fetch them, extract claim + verbatim quote  
4. **Critique** — coverage gaps? another iteration, or stop  
5. **Write** — report with citations tied to accepted findings  
6. **Memorize** — short episode filed for next time  

The UI streams SSE events the whole way: sources found/fetched, findings accepted/rejected, budget warnings, report ready.

### Depth presets

| Depth | Feel | Rough limits |
| --- | --- | --- |
| **Quick** | One pass, short shelf | ~3 sub-Qs · 1 iteration · 10 fetches · $0.25 |
| **Standard** | Critic gets a second look | ~5 sub-Qs · 2 iterations · 30 fetches · $0.75 |
| **Deep** | Wider net, longer session | ~8 sub-Qs · 4 iterations · 80 fetches · $2.50 |

Advanced overrides exist in the UI; the server still enforces its own max ceilings.

### The six agents

| Agent | Job |
| --- | --- |
| **Planner** | Breaks the question into focused sub-questions |
| **Searcher** | Calls web/arxiv tools, returns candidate URLs only from tool hits |
| **Reader** | Writes claims with evidence quotes copied from the source text |
| **Critic** | Scores coverage; can demand another research loop |
| **Writer** | Drafts the report; citations must map to accepted findings |
| **Curator** | Upserts memory (preferences / facts / episode summary) |

Models default to **Gemini** (`google:gemini-3.8-flash`). If both Google and xAI keys are set, Gemini is tried first and **Grok** is the fallback. Only Grok? It uses Grok. Only Gemini? Gemini.

---

## Stack

| Layer | Choices |
| --- | --- |
| API | FastAPI · pydantic-ai · SQLAlchemy async · Postgres + **pgvector** · Alembic |
| Web | Next.js App Router · Express in production (UI + `/v1` proxy) |
| Search | Tavily (+ arxiv helper) |
| Embeddings | Hash (default) or Gemini embeddings |
| Ship | One Docker image · one Render Web Service |

---

## Quick start (local)

```bash
cp .env.example .env
# Required: API_KEY, GOOGLE_API_KEY (or GEMINI_API_KEY), ALLOW_MODEL_REQUESTS=true
# Search: SEARCH_PROVIDER=tavily and TAVILY_API_KEY

make setup      # uv sync + pnpm install
make up         # Postgres+pgvector on localhost:5433
make migrate
make dev        # API :8000 · web :3000
```

Open [http://localhost:3000](http://localhost:3000). Health: `curl -s http://localhost:8000/healthz`.

CLI from `apps/api` (DB up):

```bash
uv run research-agent run "Who develops the Gemini models?" --depth quick
```

### Useful Make targets

| Target | What it does |
| --- | --- |
| `make setup` | Install API + web deps |
| `make up` / `down` | Start/stop local Postgres |
| `make migrate` | Alembic upgrade |
| `make dev` | API + web together |
| `make test` | Unit tests (API + web) |
| `make test-int` | Integration tests (needs DB) |
| `make eval` | Smoke eval suite |
| `make check` | Lint, types, tests |

---

## Configuration

Copy `.env.example`. Highlights:

| Area | Vars |
| --- | --- |
| Auth / CORS | `API_KEY`, `CORS_ORIGINS` |
| Web → API | `API_BASE_URL` (local: `http://localhost:8000`; Docker/Render: `http://127.0.0.1:8000`) |
| Database | `DATABASE_URL` — `postgresql+asyncpg://…` (plain `postgresql://` is auto-rewritten; non-local hosts get `ssl=require`) |
| Models | `MODEL_PLANNER` … `MODEL_CURATOR`, `GOOGLE_API_KEY` / `GEMINI_API_KEY`, `XAI_API_KEY`, `ALLOW_MODEL_REQUESTS` |
| Search | `SEARCH_PROVIDER=tavily`, `TAVILY_API_KEY` |
| Budgets | `SERVER_MAX_COST_USD`, `SERVER_MAX_FETCHES`, `SERVER_MAX_ITERATIONS`, concurrency / fetch limits |

Never commit real `.env` secrets.

---

## Architecture

```
Browser
  │
  ▼
Express  ($PORT)  ──serves──►  Next.js UI
  │  proxies /v1, /healthz
  │  Next BFF /api/*  (+ X-API-Key)
  ▼
FastAPI  (127.0.0.1:8000)
  │
  ├─ Orchestrator + agents (pydantic-ai)
  ├─ Tools (search / fetch / extract)
  └─ Postgres + pgvector
```

**Locally**, `make dev` runs uvicorn and `next dev` as two processes.  
**In production**, `infra/start-all.sh` migrates the DB, starts FastAPI on localhost, waits for `/healthz`, then boots Express on Render’s `$PORT`.

Quote verification and citation checks live in the workflow layer — rejected findings show up in the Activity stream with a reason (e.g. quote mismatch).

---

## Deploy on Render

One Web Service is enough.

1. Create **PostgreSQL 16** in the same region; copy the **Internal Database URL**.  
2. Create a **Web Service** → Language **Docker** → Dockerfile Path `Dockerfile` → Root Directory empty.  
3. Set env (same service):

| Variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `DATABASE_URL` | Internal URL as Render gives it (`postgresql://…` is OK) |
| `API_KEY` | Shared secret |
| `API_BASE_URL` / `API_INTERNAL_URL` | `http://127.0.0.1:8000` |
| `CORS_ORIGINS` | `https://YOUR-SERVICE.onrender.com` |
| `GOOGLE_API_KEY` / `XAI_API_KEY` | At least one; Gemini preferred |
| `ALLOW_MODEL_REQUESTS` | `true` |
| `SEARCH_PROVIDER` | `tavily` |
| `TAVILY_API_KEY` | Your Tavily key |

4. Deploy. Logs should show migrations → `FastAPI is ready` → Express listening.  
5. Open the public URL — you should see the desk, not raw JSON.

Cold starts on the free tier can take a minute after idle.

---

## Repo layout

```
.
├── apps/
│   ├── api/                          # FastAPI research backend
│   │   ├── src/research_agent/
│   │   │   ├── agents/               # Agent factories + prompt markdown
│   │   │   ├── api/                  # Routes, auth, SSE, problem+json errors
│   │   │   ├── db/                   # Models, sessions, SQL store
│   │   │   ├── memory/               # Embeddings + curator apply
│   │   │   ├── schemas/              # API / agent / budget / memory types
│   │   │   ├── tools/                # Search, fetch, extract
│   │   │   ├── workflow/             # Orchestrator, budgets, bus, verify
│   │   │   ├── composition.py        # Wires store, search, agents, runtime
│   │   │   ├── config.py             # Settings, model pick, DB URL normalize
│   │   │   └── main.py               # App factory + lifespan
│   │   ├── migrations/               # Alembic (vector + trigram extensions)
│   │   ├── tests/                    # unit/ · integration/
│   │   ├── evals/                    # Smoke eval datasets + runner
│   │   ├── scripts/                  # OpenAPI export helpers
│   │   ├── alembic.ini
│   │   ├── openapi.json
│   │   └── pyproject.toml            # uv project + lockfile
│   │
│   └── web/                          # Next.js desk
│       ├── src/
│       │   ├── app/                  # Desk · Runs · Memory · Settings
│       │   │   └── api/              # BFF → FastAPI (runs, events, memories)
│       │   ├── components/           # Run desk, timeline, shell, badges
│       │   └── lib/                  # Env, prefs, event reduce, errors, format
│       ├── tests/                    # Vitest
│       ├── server.mjs                # Express: Next + /v1 proxy (production)
│       └── package.json
│
├── infra/
│   ├── start-all.sh                  # migrate → API :8000 → Express $PORT
│   ├── api.Dockerfile                # Optional API-only image
│   └── web.Dockerfile                # Optional web-only image
│
├── Dockerfile                        # Unified image (use this on Render)
├── Dockerfile.web                    # Same unified image (legacy path)
├── docker-compose.yml                # Local DB (+ optional full stack profile)
├── Makefile
├── .env.example
└── README.md
```

| Path | Why it’s there |
| --- | --- |
| `agents/prompts/` | System prompts as markdown — easy to tweak without diving into Python |
| `workflow/verify.py` | Quote-in-page + citation integrity |
| `workflow/errors.py` | Turns provider failures into client-safe messages |
| `web/src/lib/reduce.ts` | Turns SSE events into the live run UI state |
| `web/server.mjs` | Single public port in Docker without a second Render service |

---

## Testing

```bash
make test          # API unit + web Vitest
make test-int      # Needs Postgres from make up
make eval          # Smoke evals
make lint && make typecheck
```

---

## License

Private / all rights reserved unless otherwise noted.
