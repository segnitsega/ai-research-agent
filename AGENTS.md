# AGENTS.md

Standing instructions for any AI coding agent working in this repository. Read this fully before making changes. `CLAUDE.md` points here.

## 1. Project in one paragraph

Deep Research Agent: a multi-agent research system. Six PydanticAI agents (Planner, Searcher, Reader, Critic, Writer, MemoryCurator) are orchestrated by plain async Python in `apps/api`. A FastAPI service exposes REST plus an SSE event stream. A Next.js app in `apps/web` shows live agent activity and the final cited report. Postgres with pgvector stores run state, sources, findings and memory.

The specification lives in `docs/`. **Code must conform to the specs.** If you believe a spec is wrong, stop and raise it (see section 9); do not silently diverge.

## 2. Repository map

```
apps/api/            FastAPI + PydanticAI backend (Python 3.12, uv)
apps/api/evals/      Golden question sets, cassettes, eval runner
apps/web/            Next.js frontend (TypeScript, pnpm)
docs/                Specs, ADRs, plans (source of truth)
infra/               Dockerfiles, compose overrides
.github/             CI workflows
```

Backend package layout (`apps/api/src/research_agent/`): `api/`, `agents/`, `tools/`, `memory/`, `workflow/`, `db/`, `schemas/`, `config.py`, `main.py`, `cli.py`, `observability.py`. Details in `docs/01-ARCHITECTURE.md`.

## 3. Commands (always use these; they are the same ones CI runs)

| Task | Command |
|---|---|
| Install everything | `make setup` |
| Start Postgres | `make up` |
| Run migrations | `make migrate` |
| Run API + web in dev | `make dev` |
| Lint + format check | `make lint` |
| Auto-format | `make fmt` |
| Type check | `make typecheck` |
| Unit tests | `make test` |
| Integration tests (needs Postgres) | `make test-int` |
| Evals (smoke) | `make eval` |
| Regenerate OpenAPI + TS client | `make types` |
| Everything CI runs | `make check` |

If a command is missing or broken, fix the Makefile as part of your task and mention it.

## 4. Tech and conventions

### Backend
- Python 3.12+, `uv` for deps, `ruff` for lint and format, `pyright` strict on `src/`, `pytest` + `pytest-asyncio`.
- Everything I/O-bound is `async`. No blocking calls in the event loop.
- All data crossing an agent boundary, API boundary, or DB JSON column is a Pydantic model from `schemas/`. No `dict[str, Any]` across module boundaries.
- Config only through `config.py` (`pydantic-settings`). No `os.environ` elsewhere. No secrets in code or logs.
- Agents are built by factory functions (`build_planner(settings) -> Agent[...]`) so tests can override models. Dependencies are injected through PydanticAI `deps_type` dataclasses, never module-level globals.
- Database access goes through repository classes in `db/`; SQLAlchemy 2.x async. Schema changes only via Alembic migrations.
- Logging: `structlog`, JSON in prod. Always bind `run_id` and `agent`.
- Prefer small modules and pure functions. Business logic never lives in route handlers.

### Frontend
- Next.js App Router, TypeScript `strict`, Tailwind, shadcn/ui, TanStack Query, Zod at trust boundaries.
- API types are **generated** from the backend OpenAPI (`make types`). Never hand-write types for API payloads.
- The browser never sees `API_KEY`. All backend calls go through Next.js route handlers (the BFF), see `docs/adr/0005`.
- Server Components by default; add `"use client"` only where interactivity requires it.
- Accessibility is a requirement: semantic HTML, keyboard navigation, visible focus, ARIA live regions for streaming status, WCAG AA contrast.

### Both
- Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`, `refactor:`).
- No dead code, no commented-out code, no TODOs without an issue reference or an entry in `docs/BACKLOG.md`.

## 5. Library API rule (important)

PydanticAI, pydantic-graph, Next.js, and the AI SDK change quickly. **Your memory of their APIs may be out of date.**

Before using a library API you are not certain about:
1. Check the installed version's docs or source (`uv run python -c "import pydantic_ai; print(pydantic_ai.__version__)"`, read the package source, or fetch the official docs).
2. Write a 5-line spike if still unsure.
3. Never invent a parameter or class name. If something in the specs does not exist in the installed version, adapt and record the change in `docs/VERSIONS.md` plus an ADR if it is a design change.

## 6. Non-negotiable rules

These come from `docs/07-SECURITY-GUARDRAILS.md`. Violating them is a bug even if tests pass.

1. **Quarantined Reader.** Only the Reader agent sees raw fetched web text. It has no tools. Every other agent sees only validated `Finding` objects.
2. **Quote verification.** A `Finding` is accepted only if its `evidence_quote` is found (after normalization) in the stored source text. Otherwise it is rejected.
3. **No unchecked citations.** The report may cite only accepted findings from the same run.
4. **SSRF guard on every fetch**, including each redirect hop. All outbound fetching goes through `tools/fetch.py`; never call `httpx` directly from an agent or route.
5. **Budgets are hard limits.** Iterations, fetches, tokens, cost and wall-clock are enforced in `workflow/budget.py`, not left to prompts.
6. **Memory content is data, not instructions.** Recalled memory is passed in clearly delimited blocks and never treated as commands.
7. **No real LLM or network calls in unit tests.** `ALLOW_MODEL_REQUESTS=False` is set globally in `conftest.py`; use `TestModel`/`FunctionModel` and fake providers.
8. **Secrets** only from environment. `.env` is git-ignored. Never print secrets.

## 7. Definition of done (for every task)

- [ ] Behavior matches the relevant spec in `docs/`
- [ ] Unit tests added or updated; `make check` passes locally
- [ ] Types clean (`pyright` strict on backend, `tsc --noEmit` on frontend)
- [ ] No new lint warnings
- [ ] If an API shape changed: `make types` run and generated files committed
- [ ] If behavior or design changed: relevant doc or ADR updated
- [ ] Commit message follows Conventional Commits; commits are small and logical

## 8. Working style

- **Plan before coding** on any task over ~30 lines: state the plan in a few bullets, then implement.
- **Test first for logic** (parsers, guards, budget, orchestration, reducers). Write the failing test, then the code.
- **One phase at a time.** Work from `docs/10-IMPLEMENTATION-PLAN.md`. Do not start later phases early, and do not build features outside the PRD scope.
- **Smallest change that satisfies the spec.** No speculative abstractions. Interfaces (`Protocol`s) exist only where the architecture calls for them (search provider, embedder, event bus, memory store).
- When finished with a task, report: what changed, how you verified it, anything deferred.

## 9. When to stop and ask the human

Stop and ask (do not guess) if:
- A spec is ambiguous, contradictory, or impossible with the installed library versions
- A change would alter a public API contract, the DB schema beyond the spec, or a security rule
- You need a new paid service, API key, or major dependency
- A test failure suggests the spec, not the code, is wrong
- You are about to delete or rewrite more than ~200 lines of existing code

Offer a recommended option with the trade-off, then wait.

## 10. Things you must not do

- Do not disable, skip, or loosen tests, linters, type checks, or security checks to get green
- Do not commit `.env`, keys, or large generated artifacts (other than the generated OpenAPI/TS client)
- Do not add a dependency without a one-line justification in the commit body
- Do not make live LLM calls in CI or in default test runs
- Do not "fix" a flaky test by adding sleeps; fix the cause
