# 01. Architecture

## 1. System overview

```
┌──────────────┐   HTTPS    ┌────────────────────┐   HTTP+SSE   ┌─────────────────────────┐
│   Browser    │ ─────────▶ │  Next.js (apps/web) │ ───────────▶ │  FastAPI (apps/api)     │
│  React UI    │ ◀───────── │  pages + BFF routes │ ◀─────────── │  REST + SSE             │
└──────────────┘    SSE     └────────────────────┘  X-API-Key    │                         │
                                                                 │  ┌───────────────────┐  │
                                                                 │  │ RunOrchestrator   │  │
                                                                 │  │ (plain async)     │  │
                                                                 │  └───┬───────────────┘  │
                                                                 │      │ calls            │
                                                                 │  ┌───▼───────────────┐  │
                                                                 │  │ PydanticAI agents │  │
                                                                 │  │ Planner Searcher  │  │
                                                                 │  │ Reader  Critic    │  │
                                                                 │  │ Writer  Curator   │  │
                                                                 │  └───┬───────────────┘  │
                                                                 │      │ uses             │
                                                                 │  ┌───▼───────┐ ┌──────┐ │
                                                                 │  │ tools/    │ │memory│ │
                                                                 │  │ search    │ │      │ │
                                                                 │  │ fetch     │ │      │ │
                                                                 │  └─────┬─────┘ └──┬───┘ │
                                                                 └────────┼──────────┼─────┘
                                                                          │          │
                                              Search API, web pages ◀─────┘          ▼
                                                                          Postgres + pgvector
```

## 2. Design principles

1. **Typed handoffs.** Every agent returns a Pydantic model; the orchestrator is the only code that wires agents together.
2. **Deterministic spine, agentic edges.** The workflow shape is plain code (testable, debuggable). Agents decide *what* to search, *what* a source says, *whether* evidence suffices, *how* to write.
3. **Untrusted input is quarantined.** Raw web text reaches exactly one tool-less agent (Reader).
4. **Events are the product.** The orchestrator emits typed events; persistence, SSE and the UI are consumers.
5. **Everything resumable.** State is checkpointed in Postgres at phase boundaries.
6. **Budgets in code.** Limits are enforced by `BudgetTracker`, never by prompts.
7. **Swap points are interfaces.** `SearchProvider`, `Embedder`, `EventBus`, `MemoryStore` are Protocols with fakes for tests.

## 3. Workflow (state machine)

```
            ┌────────────┐
 START ───▶ │ recall     │  load user prefs + related prior findings (if memory enabled)
            └─────┬──────┘
                  ▼
            ┌────────────┐
            │ plan       │  Planner → ResearchPlan
            └─────┬──────┘
                  ▼
        ┌──▶ ┌────────────┐
        │    │ search     │  Searcher per sub-question (parallel) → SourceCandidates
        │    └─────┬──────┘
        │          ▼
        │    ┌────────────┐
        │    │ fetch+read │  fetch (guarded, cached) → Reader per (source, sub-question)
        │    │            │  → Findings → deterministic quote verification
        │    └─────┬──────┘
        │          ▼
        │    ┌────────────┐
        │    │ critique   │  Critic → Review (sufficient | needs_more + gaps)
        │    └─────┬──────┘
        │          │ needs_more AND budget remains AND iteration < max
        └──────────┘
                   │ sufficient OR budget exhausted
                   ▼
            ┌────────────┐
            │ write      │  Writer → Report (citations validated)
            └─────┬──────┘
                  ▼
            ┌────────────┐
            │ memorize   │  MemoryCurator → memory updates; index sources/findings
            └─────┬──────┘
                  ▼
                 END   (status = completed | failed | cancelled)
```

Rules:
- A checkpoint (`runs.state`) is written when each phase completes.
- On restart, the orchestrator resumes at the first incomplete phase (see `04-MEMORY-DESIGN.md` §2).
- On budget exhaustion the run goes straight to `write` with `limitations` noting the cut-off.
- Cancellation is checked between steps and inside long loops (`asyncio.CancelledError` is honored).

## 4. Components

### 4.1 `agents/`
One module per agent with a `build_*` factory, an instructions file under `agents/prompts/`, and a typed `Deps` dataclass. See `03-AGENT-SPECS.md`.

### 4.2 `tools/`
| Module | Responsibility |
|---|---|
| `search.py` | `SearchProvider` protocol; `TavilyProvider`, `ArxivProvider`, `FakeSearchProvider` |
| `fetch.py` | Guarded HTTP fetch: SSRF checks, size and time limits, redirects, content-type allowlist, robots |
| `extract.py` | HTML/PDF to clean text (trafilatura, pypdf); chunking |
| `safety.py` | URL canonicalization, SSRF IP checks, text normalization for quote matching |

### 4.3 `workflow/`
| Module | Responsibility |
|---|---|
| `orchestrator.py` | `RunOrchestrator.run(run_id)`: the state machine above |
| `state.py` | `RunState` (typed checkpoint) |
| `events.py` | Event models (discriminated union), `EventBus` protocol, in-process bus |
| `budget.py` | `BudgetTracker`: iterations, fetches, tokens, cost, wall clock |
| `verify.py` | Quote verification, report citation validation |

### 4.4 `memory/`
`working.py` (checkpoint repo), `semantic.py` (documents/chunks/findings with pgvector), `user.py` (preferences and episodes), `embeddings.py` (`Embedder` protocol). See `04-MEMORY-DESIGN.md`.

### 4.5 `db/`
SQLAlchemy models, async session factory, repositories (`RunRepo`, `EventRepo`, `SourceRepo`, `FindingRepo`, `MemoryRepo`), Alembic migrations.

### 4.6 `api/`
FastAPI app factory, routers (`runs`, `memories`, `feedback`, `health`), auth dependency, error handlers (RFC 9457), SSE helper.

## 5. Run execution model

- `POST /v1/runs` inserts a `runs` row (`queued`), starts an `asyncio.Task` running `RunOrchestrator` in the API process, and returns 202.
- The orchestrator publishes events to the `EventBus`. A subscriber persists each event to `run_events` with a monotonic `seq` per run.
- `GET /v1/runs/{id}/events` replays persisted events with `seq > Last-Event-ID`, then tails live events from the bus.
- A registry (`RunRegistry`) keeps `run_id → Task` for cancellation and a per-user concurrency limit.
- **v1 constraint:** one API process owns its runs. On startup, runs left in `running` are resumed (see FR-8). Scaling out requires a Redis-backed `EventBus` and a job queue; this is an optional Phase 13 item and the interfaces already allow it.

## 6. Concurrency model

- Sub-questions are researched concurrently with `asyncio.TaskGroup`, limited by semaphores: `MAX_CONCURRENT_SEARCHES`, `MAX_CONCURRENT_FETCHES`, `MAX_CONCURRENT_LLM_CALLS`.
- Per-domain politeness: at most 2 concurrent requests per domain.
- One slow or failed source is isolated; it emits `source.failed` and the run continues.

## 7. Models and providers

- Model per agent comes from env (`MODEL_PLANNER`, ...), using PydanticAI's `provider:model` strings. Suggested defaults: stronger model for Planner, Critic, Writer; cheaper fast model for Searcher, Reader, Curator.
- All agents use PydanticAI structured output (`output_type`) with automatic validation retries.
- Token usage from every agent run is added to one run-level `RunUsage`, and cost is computed from the model's price table.

## 8. Observability

- Logs: `structlog` JSON with `run_id`, `agent`, `phase`.
- Traces: OpenTelemetry via PydanticAI's instrumentation; optional Logfire export when `LOGFIRE_TOKEN` is set.
- Metrics (log-derived or OTel): run duration per phase, tokens and cost per agent, fetch success rate, findings accepted/rejected ratio.

## 9. Repository layout

```
research-agent/
├── AGENTS.md  CLAUDE.md  README.md  Makefile
├── docker-compose.yml  .env.example  .gitignore  .pre-commit-config.yaml
├── .github/workflows/ci.yml
├── docs/                      # this specification pack
├── infra/
│   ├── api.Dockerfile
│   └── web.Dockerfile
├── apps/
│   ├── api/
│   │   ├── pyproject.toml  uv.lock  alembic.ini  openapi.json
│   │   ├── migrations/
│   │   ├── src/research_agent/
│   │   │   ├── main.py  config.py  cli.py  observability.py
│   │   │   ├── api/        (routers, deps, errors, sse)
│   │   │   ├── agents/     (planner, searcher, reader, critic, writer, curator, prompts/)
│   │   │   ├── tools/      (search, fetch, extract, safety)
│   │   │   ├── workflow/   (orchestrator, state, events, budget, verify)
│   │   │   ├── memory/     (working, semantic, user, embeddings)
│   │   │   ├── db/         (models, session, repos)
│   │   │   └── schemas/    (all Pydantic models)
│   │   ├── tests/          (unit/, integration/, conftest.py)
│   │   └── evals/          (datasets/, run_evals.py)
│   └── web/
│       ├── package.json  next.config.ts  tsconfig.json
│       ├── src/app/        (pages and route handlers)
│       ├── src/components/
│       ├── src/lib/        (api client, stream reducer, utils)
│       ├── src/types/api.d.ts   (generated)
│       └── tests/  e2e/
```

## 10. Key trade-offs

| Decision | Chosen | Alternative | Reason |
|---|---|---|---|
| Orchestration | Plain async Python | pydantic-graph, LangGraph | Fewest moving parts, easiest to test, and graph persistence APIs were still in flux (ADR-0002) |
| Streaming | SSE with own event contract | Vercel AI protocol, WebSockets | Multi-agent workflow events do not map to a chat transcript (ADR-0004) |
| Vector store | pgvector in the same Postgres | Qdrant, Chroma | One datastore, transactional with the rest (ADR-0003) |
| Memory | Own thin layer | Mem0 | Learning value, fewer dependencies, swappable behind `MemoryStore` (ADR-0006) |
| Frontend ↔ API | BFF proxy | Browser calls API directly | Keeps the API key off the browser (ADR-0005) |
