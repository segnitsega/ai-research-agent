# 10. Implementation Plan

Fourteen phases (0 to 13). Each phase has: goal, docs to read, tasks, acceptance criteria, and a **ready-to-paste prompt** for your AI coding agent. Do phases in order. Finish and verify one before starting the next.

Rough effort with an AI agent driving and you reviewing: 0 to 2 about half a day each, 3 to 7 about one day each, 8 to 10 about one day each, 11 to 12 about one day each. Treat these as planning guesses.

**How to use a prompt:** paste it into the agent at the repo root. The agent already has `AGENTS.md`. After it finishes, run the acceptance checks yourself (see the playbook, `11-AI-CODING-PLAYBOOK.md`), then commit and move on.

---

## Phase 0. Repository bootstrap and tooling

**Goal:** empty repo becomes a working monorepo with CI, Docker Postgres, and green placeholder tests.

**Read:** `AGENTS.md`, `01-ARCHITECTURE.md` §9, `09-DEVOPS.md`.

**Tasks**
1. Create the folder layout from `01-ARCHITECTURE.md` §9 (empty packages with `__init__.py`).
2. `apps/api`: `uv init`, Python 3.12, add deps (fastapi, uvicorn, pydantic-settings, pydantic-ai, sqlalchemy[asyncio], asyncpg, alembic, structlog, httpx; dev: pytest, pytest-asyncio, pytest-cov, respx, ruff, pyright). Latest stable versions. Configure `ruff`, `pyright` strict, `pytest` markers.
3. `apps/web`: create the Next.js app (latest stable, TypeScript, Tailwind, App Router, `src/` dir, ESLint), add shadcn/ui, TanStack Query, Zod, Vitest, Testing Library, Playwright, `openapi-typescript`.
4. Root: `Makefile` (targets in `09-DEVOPS.md` §3), `docker-compose.yml` (db with pgvector), `.env.example`, `.gitignore`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml` (api and web jobs for now).
5. Minimal FastAPI app with `/healthz`, one passing unit test; minimal Next.js home page, one passing Vitest test.
6. Write `docs/VERSIONS.md` with the exact installed versions of Python, Node, pnpm, uv, PydanticAI, Next.js, React, FastAPI, SQLAlchemy, Postgres image tag.

**Acceptance**
- `make setup && make up && make check` passes on a clean clone
- `make dev` serves API on :8000 (`/healthz` returns 200) and web on :3000
- CI green on a pushed branch
- `docs/VERSIONS.md` filled in

**Prompt**
```
Read AGENTS.md and docs/01-ARCHITECTURE.md (section 9) and docs/09-DEVOPS.md. Execute Phase 0 of docs/10-IMPLEMENTATION-PLAN.md: bootstrap the monorepo exactly per the layout, with uv for apps/api and pnpm for apps/web, a Makefile with the listed targets, docker-compose with a pgvector Postgres, pre-commit, and a CI workflow. Use the latest stable versions of every dependency (check them, do not rely on memory) and record them in docs/VERSIONS.md. Add one trivial passing test on each side. Do not implement any feature code. First give me your plan in a few bullets, then implement. When done, run `make check` and report the result.
```

---

## Phase 1. Config, schemas, database

**Goal:** typed foundation: settings, all Pydantic schemas, DB models and migrations, repositories.

**Read:** `02-DATA-MODELS.md`, `09-DEVOPS.md` §2.

**Tasks**
1. `config.py` with `Settings` (pydantic-settings, `SecretStr`), all env vars from `.env.example`, depth presets, server maximums.
2. `schemas/`: every model in `02-DATA-MODELS.md` (enums, Budget, RunRequest, agent I/O, Finding, Review, Report, Memory models, RunState, RunUsage, RunEvent and the event data union from `05-API-SPEC.md` §4).
3. `db/`: SQLAlchemy 2 async models for all tables, session factory, Alembic setup, first migration (extensions, tables, indexes, seed user).
4. Repositories with `user_id` scoping: `RunRepo`, `EventRepo`, `SourceRepo`, `FindingRepo`, `MemoryRepo`, `FeedbackRepo`.
5. Test fixtures: Postgres test database, per-test rollback.

**Acceptance**
- Schema unit tests: validation limits and unions parse/serialize round-trip
- Migration up/down works on a clean DB; `make test-int` covers every repo method
- A test proves user A cannot read user B's rows through any repository
- pyright strict clean

**Prompt**
```
Read docs/02-DATA-MODELS.md and docs/05-API-SPEC.md section 4. Implement Phase 1: config.py, all Pydantic schemas (including the event discriminated union), SQLAlchemy async models, the Alembic first migration (pgvector, tables, indexes, seeded user), and the repositories. Every repository query must filter by user_id where the table has it. Write unit tests for schemas and integration tests for repositories, including a cross-user isolation test. Verify pgvector index syntax against the installed pgvector. Plan first, then implement test-first where practical. Run `make check` at the end.
```

---

## Phase 2. Tools layer: safety, fetch, extract, search

**Goal:** safe, tested building blocks with no LLM involved.

**Read:** `07-SECURITY-GUARDRAILS.md` §2, `04-MEMORY-DESIGN.md` §3.1, `03-AGENT-SPECS.md` §3 (verification).

**Tasks**
1. `tools/safety.py`: URL parsing/canonicalization, IP classification, text normalization for quote matching.
2. `tools/fetch.py`: guarded fetch with pinned IP, manual redirects, limits, content-type allowlist, robots, per-domain politeness. Returns a typed `FetchResult` or raises typed errors mapped to `source.failed` reasons.
3. `tools/extract.py`: HTML to clean text (trafilatura), PDF to text, chunking with overlap, title and date extraction.
4. `tools/search.py`: `SearchProvider` protocol, `TavilyProvider`, `ArxivProvider`, `FakeSearchProvider`; retries with backoff and timeouts.
5. `workflow/verify.py` part 1: `verify_quote(quote, source_text) -> bool` with normalization.

**Acceptance**
- The full SSRF table from `07` §2 passes (including redirect-to-private and rebinding simulation)
- Extraction fixtures (article, docs page, PDF, weird encoding) produce expected text
- Quote verification passes smart quotes, whitespace and dash variants; rejects altered quotes
- No test touches the real internet

**Prompt**
```
Read docs/07-SECURITY-GUARDRAILS.md section 2 and docs/04-MEMORY-DESIGN.md section 3.1. Implement Phase 2 tools: safety.py, fetch.py (all ten requirements in section 2, including IP pinning and per-hop redirect checks), extract.py, search.py (Tavily, arXiv, Fake providers behind a SearchProvider Protocol), and verify_quote in workflow/verify.py. Start by writing the table-driven SSRF tests and the quote-normalization tests, watch them fail, then implement. Use respx or a local test server; no real network. Report any requirement you could not meet and why.
```

---

## Phase 3. Agents (no orchestration yet)

**Goal:** all six agents built, typed, validated, unit-tested with fake models.

**Read:** `03-AGENT-SPECS.md` in full.

**Tasks**
1. `agents/prompts/*.md` from the spec (Planner, Searcher, Reader, Critic, Writer, Curator).
2. One factory per agent with typed `Deps`, `output_type`, output validators (`ModelRetry`), per-agent model from settings.
3. Searcher tools (`web_search`, `arxiv_search`, `recall_sources` stub) with URL tracking for the "only tool-returned URLs" validator.
4. Writer validators (citations) and Critic validators (coverage ids, gaps).
5. Shared helpers: `UsageTracker` hooks, dynamic-instruction block builders for preferences and prior knowledge (delimited).

**Acceptance**
- Tests per `03` §7 all pass with `TestModel`/`FunctionModel`
- Each validator has an accept test and a reject test
- Reader has zero tools; guard test checks the untrusted-content notice
- `ALLOW_MODEL_REQUESTS=False` active; suite passes offline

**Prompt**
```
Read docs/03-AGENT-SPECS.md fully. Implement Phase 3: the six PydanticAI agents with factories, typed deps, output types from schemas/, validators using ModelRetry, and prompt files. Check the installed PydanticAI version's API (Agent constructor args, output validators, usage handling, override, TestModel/FunctionModel) before coding; do not rely on memory. Do not build the orchestrator yet. Tests must use TestModel/FunctionModel only, with ALLOW_MODEL_REQUESTS disabled globally. Provide a table at the end mapping each spec requirement to the test that covers it.
```

---

## Phase 4. Orchestrator v1 (linear) and CLI

**Goal:** an end-to-end run from the command line: recall (stub) → plan → search → read → write, with events, budget, and persistence.

**Read:** `01-ARCHITECTURE.md` §3, §5, §6; `05-API-SPEC.md` §4; `07` §5.

**Tasks**
1. `workflow/events.py`: `EventBus` protocol, in-process bus, persistence subscriber assigning `seq`.
2. `workflow/budget.py`: `BudgetTracker` with all five limits, warnings, `UsageLimits` mapping, cost calculation from usage.
3. `workflow/state.py` + checkpoint writes.
4. `workflow/orchestrator.py`: phases plan → search → fetch/read → verify → write. Parallelism with `TaskGroup` and semaphores. Document cache usage (store sources, chunks later). Failure isolation per source.
5. `cli.py` (Typer + Rich): `research-agent run "question" --depth quick` streams events as a live table and prints the report.
6. Composition root: dependency wiring in one place.

**Acceptance**
- With fakes (FunctionModel + FakeSearchProvider + local fixture pages), a run produces the exact expected event sequence and a valid report
- Rejected findings (altered quotes) are excluded from the report
- Each budget limit halts work and still yields a report with `limitations`
- Manual smoke test with real keys: `research-agent run "…" --depth quick` completes and prints a cited report (record cost)

**Prompt**
```
Read docs/01-ARCHITECTURE.md sections 3, 5, 6 and docs/05-API-SPEC.md section 4 and docs/07 section 5. Implement Phase 4: the event bus and persistence subscriber, BudgetTracker, RunState checkpointing, the linear RunOrchestrator (plan, search, fetch+read with quote verification, write), and a Typer/Rich CLI. Orchestrator code must be pure orchestration: agents and tools are injected. Write the integration test first using fake models, a fake search provider and fixture pages, asserting the full event sequence. Then implement. Finally run one real quick-depth run and tell me the cost and any issues.
```

---

## Phase 5. Critic loop, cancellation, resume

**Goal:** the agentic loop and run lifecycle robustness.

**Read:** `01-ARCHITECTURE.md` §3, `03-AGENT-SPECS.md` §4, `04-MEMORY-DESIGN.md` §2.

**Tasks**
1. Add the critique phase and the `needs_more` loop with gap-targeted searching; stop conditions (sufficient, max iterations, budget).
2. Dedupe of near-duplicate findings; finding recall of `weak_finding_ids` handling (second-source search).
3. `RunRegistry` (task registry), cancel support (checked between steps and inside loops).
4. Resume from checkpoints; startup recovery for `running` runs; stuck-run sweeper.
5. Events: `iteration.started/completed`, `critic.review`, `budget.*`, `run.cancelled`.

**Acceptance**
- Loop tests: Critic returns `needs_more` ×2 then `sufficient`; gaps drive targeted searches; iteration cap enforced even if the Critic never says sufficient
- Cancellation test at every phase boundary and during fetch; no report after cancel
- Resume test: terminate after each phase, restart, finish with no duplicate rows or events
- Looping fake Critic is stopped by budget

**Prompt**
```
Read docs/03-AGENT-SPECS.md section 4, docs/01-ARCHITECTURE.md section 3 and docs/04-MEMORY-DESIGN.md section 2. Implement Phase 5: the Critic phase and iteration loop, finding dedupe, cancellation via a RunRegistry, checkpoint-based resume with startup recovery, and the stuck-run sweeper. Write the loop, cancel and resume tests first (including a fake Critic that never says sufficient). Keep the orchestrator readable: one method per phase.
```

---

## Phase 6. API layer

**Goal:** REST + SSE per `05-API-SPEC.md`.

**Read:** `05-API-SPEC.md`, `07` §8.

**Tasks**
1. App factory, lifespan (DB, registry, recovery), auth dependency, problem+json handlers, request-id middleware, rate limiting, body size limit.
2. Routers: runs (create, list, detail, cancel, delete, sources, findings, report.md, feedback), `/v1/config`, health.
3. SSE endpoint with replay + live tail + dedupe by `seq`, keep-alive, terminal close, `Last-Event-ID` and `?after=`.
4. OpenAPI export script (`make types` backend half) and committed `openapi.json`. Ensure the event union appears in the schema (add a documented schema-only endpoint or `responses` model if needed).
5. Idempotency key support.

**Acceptance**
- Contract tests per `05` §7 pass: auth, validation, pagination, SSE replay and ordering, no duplicates, close on terminal, user isolation
- `curl -N` against a running fake run shows correctly formatted SSE
- Real quick run via `POST /v1/runs` then `GET …/events` works end to end

**Prompt**
```
Read docs/05-API-SPEC.md fully and docs/07 section 8. Implement Phase 6: the FastAPI app factory and routers, auth, problem+json errors, rate limiting, the SSE endpoint with replay-then-tail semantics (subscribe first, then replay, dedupe by seq), idempotency keys, and OpenAPI export to apps/api/openapi.json. Write SSE and contract tests first using httpx ASGI client and a fake orchestrator. Show me a curl -N transcript of a real run at the end.
```

---

## Phase 7. Memory

**Goal:** semantic and user memory working through the orchestrator.

**Read:** `04-MEMORY-DESIGN.md` in full.

**Tasks**
1. `memory/embeddings.py`: `Embedder` protocol, FastEmbed default, OpenAI optional, fake for tests. (Check whether the installed PydanticAI embedding support fits.)
2. Semantic: document cache with TTL decisions, chunk indexing, `recall_sources` tool implementation, finding recall and re-verification against cached text, `from_memory` findings.
3. User memory: `PgMemoryStore` with recall (preferences, facts, episodes), Curator ops application with dedupe, caps, secret scanner, eviction.
4. Orchestrator integration: `recall` phase before plan, `memorize` phase after write, `use_memory=false` bypass, events `memory.recalled` and `memory.updated`.
5. API: `/v1/memories` CRUD, search, forget-all, and feedback-triggered curation.

**Acceptance**
- Tests per `04` §7 pass (including cross-user attack on `target_id`)
- Repeat-question integration test: second run performs at most 50% of the fetches
- `use_memory=false` produces zero reads and zero writes of user memory
- Memory CRUD API contract tests pass; OpenAPI regenerated

**Prompt**
```
Read docs/04-MEMORY-DESIGN.md fully. Implement Phase 7: embeddings abstraction with a local default, the document cache with TTL, chunk indexing, finding recall with re-verification against cached text, PgMemoryStore for preferences/facts/episodes, Curator op application (dedupe, caps, secret scanner, user-scoped target checks), orchestrator recall and memorize phases, and the /v1/memories API. Write the repeat-question test and the isolation tests first. Delimit recalled memory as data, never instructions. Regenerate openapi.json.
```

---

## Phase 8. Frontend scaffold, typed client, BFF

**Goal:** the web app talks to the API safely and is typed from OpenAPI.

**Read:** `06-FRONTEND-SPEC.md` §1 to §4, §9; `docs/adr/0005`.

**Tasks**
1. App shell (nav, theme toggle, layout), design tokens, base shadcn components.
2. `make types` frontend half: `openapi-typescript` generation, committed `src/types/api.d.ts`.
3. API clients (`server.ts` with `server-only`, `client.ts`), error parsing for problem+json.
4. BFF route handlers for all `/api/*` calls; SSE proxy that streams without buffering and aborts upstream on disconnect.
5. Pages: `/` (QuestionForm with `/v1/config` driven presets), `/runs` (history), skeleton `/runs/[id]`.
6. Build-time and test-time check that `API_KEY` is not in client bundles.

**Acceptance**
- Creating a run from the form navigates to `/runs/{id}` and the proxy streams raw events (visible in a debug panel)
- Form validation matches server limits; server errors surface as field messages
- Vitest and component tests pass; `next build` passes; leakage grep passes

**Prompt**
```
Read docs/06-FRONTEND-SPEC.md sections 1-4 and 9 and docs/adr/0005. Implement Phase 8 in apps/web: app shell with theme toggle, generated API types from apps/api/openapi.json, server-only and browser API clients, the BFF route handlers including a non-buffering SSE proxy, and the pages / and /runs plus a skeleton /runs/[id]. Check the installed Next.js version's docs for route handler streaming, async params and the proxy/middleware conventions before writing code. API_KEY must never reach the browser; add a test or script that proves it. Plan first.
```

---

## Phase 9. Live run view

**Goal:** the core screen: timeline, plan, sources, findings, report with citations, inspector, budget meters.

**Read:** `06-FRONTEND-SPEC.md` §5, §6, §11.

**Tasks**
1. `reduce()` + `useRunStream` with seq idempotency, batching, reconnect backoff; Zod event parsing.
2. Record a real event stream from the backend into `tests/fixtures/events/run-standard.ndjson`; reducer tests (every event type, replay equivalence, idempotency).
3. Components: ActivityTimeline, PhaseStepper, PlanView, SourcesTable, FindingsList/FindingCard, ReportView (sanitized Markdown with citation plugin), Inspector, BudgetMeters, run header with cancel and export.
4. Terminal and error states; reconnect indicator.
5. Accessibility pass: live region, focus management, keyboard flows.

**Acceptance**
- Reducer tests green incl. "mid-run reload equals uninterrupted" test
- Playwright E2E with a fake SSE server replaying the fixture: timeline updates, report shows citations, citation click opens the Inspector with the exact quote, cancel works, disconnect/reconnect resumes with `Last-Event-ID`
- axe finds no serious violations on the run page
- XSS fixture (script tags and `javascript:` links in report text) is neutralized

**Prompt**
```
Read docs/06-FRONTEND-SPEC.md sections 5, 6 and 11. Implement Phase 9: the pure event reducer and useRunStream hook (seq-idempotent, batched updates, reconnect backoff), Zod parsing of SSE payloads, and all run-page components including the sanitized Markdown report renderer with clickable citations feeding an Inspector. First capture a real event stream fixture from the running backend. Write reducer tests (including replay-equals-live) and the Playwright E2E with a fake SSE server before building the UI. Add axe checks. Keep components small and accessible.
```

---

## Phase 10. History, memory manager, feedback, polish

**Goal:** complete the UI feature set.

**Read:** `06-FRONTEND-SPEC.md` §4, §7, §8, §10.

**Tasks**
1. `/runs` filters and pagination; delete run; "Retry as new run".
2. `/memory` manager (tabs, edit, delete, add, semantic search, forget-all dialog with type-to-confirm).
3. Feedback UI (rating, comment, flag finding) wired to the API.
4. `/settings`, empty/loading/error states everywhere, responsive layout (mobile tabs).
5. Visual design pass (use the `frontend-design` skill if available): typography, spacing, dark mode, reduced motion.

**Acceptance**
- E2E: memory CRUD and forget-all; feedback flow; history filters
- Lighthouse accessibility 95 or higher on `/`, `/runs/[id]`, `/memory`
- Mobile layout verified at 390px width

**Prompt**
```
Read docs/06-FRONTEND-SPEC.md sections 4, 7, 8 and 10. Implement Phase 10: run history with filters and pagination, delete and retry actions, the /memory manager with the forget-all dialog, feedback UI (rating, comment, flag finding), settings, empty/loading/error states, responsive layout, and a visual polish pass with dark mode and reduced-motion support. Add Playwright tests for memory CRUD, feedback and history filters. Report Lighthouse accessibility scores.
```

---

## Phase 11. Evals, observability, cost tracking

**Goal:** measurable quality and operational visibility.

**Read:** `08-TESTING-EVALS.md` §5, `01-ARCHITECTURE.md` §8, `09-DEVOPS.md` §8.

**Tasks**
1. Golden dataset (20 questions) and recorded-mode cassettes; smoke subset of 5.
2. Evaluators: citation validity, claim support (LLM judge), coverage (LLM judge), efficiency, memory benefit, robustness (injection pages).
3. `make eval` runner, JSON + Markdown reports, `baseline.json`, CI gating, nightly workflow.
4. Observability: OTel instrumentation with PydanticAI, optional Logfire, structlog fields, per-run cost in `usage.updated`.
5. A first full eval run; commit the baseline and a short results note to `docs/EVAL-RESULTS.md`.

**Acceptance**
- `make eval` produces a report; citation validity 100%
- CI nightly job runs and compares to baseline
- A trace of one run shows spans for each phase and agent with tokens and cost

**Prompt**
```
Read docs/08-TESTING-EVALS.md section 5, docs/01-ARCHITECTURE.md section 8 and docs/09-DEVOPS.md section 8. Implement Phase 11: a 20-question golden dataset with a 5-question smoke subset, recorded-mode cassettes for search and pages, evaluators (citation validity, claim support judge, coverage judge, efficiency, memory benefit, robustness), the make eval runner with JSON and Markdown output, baseline comparison for CI, and OpenTelemetry instrumentation with optional Logfire. Check pydantic-evals and PydanticAI instrumentation APIs in the installed versions first. Run the evals once and summarize results and weaknesses you see.
```

---

## Phase 12. Hardening and production readiness

**Goal:** ship-quality security, containers, CI, docs.

**Read:** `07-SECURITY-GUARDRAILS.md` §9, `09-DEVOPS.md`.

**Tasks**
1. Run the security checklist (`07` §9); fix gaps; add missing tests (log redaction, XSS, isolation, looping Critic).
2. Dockerfiles (non-root, multi-stage), full compose, healthchecks; Trivy and audit jobs in CI.
3. Rate limits and quotas verified; security headers and CSP on the web app.
4. Optional: short-lived signed stream token so the browser can connect directly to the API for SSE (for Vercel-style deployments), per ADR-0005.
5. Load test: 10 concurrent quick runs with fakes; fix issues (connection pools, bus backpressure).
6. Docs: finalize README quick start, runbook (`docs/RUNBOOK.md`: common failures, how to rotate keys, restore a backup), update ADRs.

**Acceptance**
- Every box in the `07` §9 checklist is ticked with a test or script reference
- `docker compose --profile full up` brings up a working system from scratch
- CI fully green including docker, e2e, contract, security jobs
- A new developer can follow the README and have a run completing in 15 minutes

**Prompt**
```
Read docs/07-SECURITY-GUARDRAILS.md section 9 and docs/09-DEVOPS.md. Implement Phase 12: work through the security checklist item by item, adding the missing tests; write production Dockerfiles and the full compose profile; add CSP and security headers; add Trivy/audit/CodeQL CI jobs; run a 10-concurrent-run load test with fakes and fix what breaks; write docs/RUNBOOK.md. For each checklist item, state the test or script that proves it. Do not mark an item done without proof.
```

---

## Phase 13. Optional extensions

Pick any, each as its own mini-phase with spec update first:

| Extension | Notes |
|---|---|
| **Chat with this report** | Use PydanticAI's Vercel AI UI adapter (`VercelAIAdapter`) with AI SDK UI `useChat`; agent answers only from stored findings; authenticate the route yourself (see `07` §8) |
| **Redis `EventBus` + job queue** | Enables multiple API workers; implement the existing `EventBus` protocol; consider ARQ/Celery |
| **Real auth** | Auth.js/Clerk/Supabase Auth; map to `users`; per-user API keys |
| **CrewAI comparison branch** | Re-implement the orchestrator with CrewAI behind the same interface and compare with the eval suite; write findings in an ADR |
| **Streaming report text** | Add `report.delta` events |
| **Source credibility scoring** | Domain reputation table plus Critic hints |
| **Export** | PDF and DOCX export of reports |
| **pydantic-graph variant** | Re-express the workflow as a graph for diagrams and persistence; compare with the plain version |

---

## Cross-phase checklist

Before declaring v1 done:
- [ ] All PRD user stories (US-1 to US-16) have a passing automated test or a documented manual check
- [ ] Success metrics in `00-PRD.md` §8 measured and recorded in `docs/EVAL-RESULTS.md`
- [ ] `docs/VERSIONS.md` current; ADRs updated for any deviation
- [ ] README quick start verified on a clean machine
