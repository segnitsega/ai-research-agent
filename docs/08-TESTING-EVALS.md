# 08. Testing and Evaluation

## 1. Test pyramid

| Level | Where | Real LLM? | Real DB? | Runs in CI |
|---|---|---|---|---|
| Unit | `apps/api/tests/unit`, `apps/web/**/*.test.ts` | No | No | Every push |
| Integration | `apps/api/tests/integration` | No | Yes (Postgres + pgvector service) | Every push |
| E2E | `apps/web/e2e` (Playwright) against fake backend | No | No | Every push |
| Evals (smoke) | `apps/api/evals` | Yes (small, cheap model) | Yes | Nightly and on label `run-evals` |
| Live tests | `pytest -m live` | Yes | Optional | Manual only |

Markers: `unit`, `integration`, `eval`, `live`. Default `pytest` excludes `eval` and `live`.

## 2. Backend testing rules

- `conftest.py` sets `pydantic_ai.models.ALLOW_MODEL_REQUESTS = False` globally (verify the exact flag name in the installed version). Any accidental real call fails the test.
- Agents are tested with `TestModel` (schema-valid output generation) and `FunctionModel` (scripted outputs including bad ones) through `agent.override(model=...)`.
- Search is tested with `FakeSearchProvider` (fixture-based). HTTP fetching is tested with `respx` or a local test server; never the real internet.
- DB tests use a real Postgres with pgvector (docker compose service locally, service container in CI), each test in a rolled-back transaction or a fresh schema.
- Time and randomness are injectable (`Clock`, seeded IDs) so tests are deterministic.
- Async tests with `pytest-asyncio` (auto mode); no `sleep`-based waits, use events or `asyncio.wait_for`.

### Must-have tests (checklist)

**Tools and safety**
- [ ] SSRF table (see `07` §2) including redirects and DNS rebinding simulation
- [ ] Size/time/content-type limits; decompression bomb
- [ ] URL canonicalization; quote normalization and matching edge cases (smart quotes, whitespace, hyphens, ligatures)
- [ ] HTML and PDF extraction on fixtures

**Agents**
- [ ] Each agent's output type, tool set, and validators (see `03` §7)
- [ ] Reader prompt contains untrusted-content notice
- [ ] Injection fixture page yields only verified findings

**Workflow**
- [ ] Happy path: fake agents (via `FunctionModel`) run plan → search → read → critique → write; events appear in the expected order
- [ ] Loop: Critic `needs_more` twice then `sufficient`; iteration counter and gap targeting correct
- [ ] Budget: each limit (iterations, fetches, tokens, cost, wall clock) stops the run and still produces a report with limitations
- [ ] Cancellation at each phase boundary and mid-fetch
- [ ] Resume: kill after each phase; restart completes without duplicates
- [ ] Failure isolation: a failing source or provider timeout does not fail the run; total failure produces `run.failed` with sanitized message
- [ ] Report validator rejects unresolved citations, unknown finding ids, uncited sections

**Memory**
- [ ] Recall relevance and threshold; user isolation; TTL cache decisions; dedupe; eviction; secret scanner
- [ ] Curator op application incl. cross-user `target_id` attack

**API**
- [ ] Contract tests from `05` §7: auth, validation errors as problem+json, pagination, SSE replay and ordering, idempotency key, rate limit, cancel races
- [ ] OpenAPI snapshot unchanged unless intentionally updated

## 3. Frontend testing

See `06-FRONTEND-SPEC.md` §13. Add an automated check that the generated types file is current (`make types` then `git diff --exit-code`).

## 4. Coverage and quality gates

- Backend line coverage 85% or higher (excluding `prompts/`, `cli.py`); branch coverage reported.
- Frontend: reducer and lib code 90% or higher; no coverage gate on pure presentational components.
- `pyright` strict on `src/`, `tsc --noEmit`, `ruff`, `eslint` all clean.
- Mutation testing (optional, later) on `verify.py`, `budget.py`, `safety.py` with `mutmut`.

## 5. Evaluation harness

Use `pydantic-evals` (verify API in the installed version) in `apps/api/evals/`.

### 5.1 Golden set
`evals/datasets/golden.yaml`: 20 questions across domains (technical comparison, scientific consensus, recent developments, numeric/factual, contested topic). For each:

```yaml
- id: vecdb-prod-rag
  question: "Compare pgvector, Qdrant, and Milvus for production RAG."
  depth: standard
  expected_topics: ["index types (HNSW, IVF)", "scale limits", "filtering", "operational complexity", "managed offerings"]
  must_cite_domains_any_of: ["github.com", "qdrant.tech", "milvus.io", "postgresql.org"]
  freshness: "needs sources from the last 12 months"
```

For repeatable CI evals, a **recorded mode** replays saved search results and page contents from `evals/cassettes/` (so only LLM behavior varies). A separate **live mode** runs against the real web and is for manual or nightly runs.

### 5.2 Metrics and evaluators

| Metric | How | Target |
|---|---|---|
| Citation validity | Deterministic: every cited finding's quote is in the stored source text | 100% |
| Claim support | LLM judge (different model family than the Writer if possible) given a sentence + its cited quotes returns supported / partial / unsupported | 90% or higher supported |
| Coverage | LLM judge against `expected_topics` | 80% or higher |
| Source quality | Heuristic: share of primary/authoritative domains; diversity (distinct domains) | Track trend |
| Contradiction handling | Judge: contradictions present in the data are surfaced in the report | Track |
| Efficiency | Tokens, cost, fetches, wall time per run | Median under budget |
| Memory benefit | Run the same question twice with memory on; compare fetches and cost | Second run at most 50% of the first run's fetches |
| Robustness | Injection pages, 404s, timeouts, paywalls injected via cassettes | Zero injection-driven behavior; run completes |

### 5.3 Running and reporting
- `make eval` runs the smoke subset (5 questions, quick depth, recorded mode, cheap models) and writes `evals/reports/latest.json` plus a Markdown summary.
- CI compares against `evals/baseline.json`: fail if citation validity less than 100%, or any other metric regresses by more than a set tolerance (default 5 points). Updating the baseline requires a deliberate commit with explanation.
- Prompt or model changes must include before/after eval numbers in the PR description.
- Log eval runs to Logfire (if configured) for trace-level inspection of failures.

## 6. Test data and fixtures

- `tests/fixtures/pages/`: representative HTML (article, docs page, blog, forum), a PDF, a page with injection payloads, a huge page, a page with weird encoding.
- `tests/fixtures/search/`: canned search hit lists per query.
- `tests/fixtures/events/run-standard.ndjson`: recorded event stream, shared with the frontend tests (copy via a script, do not duplicate by hand).

## 7. Definition of done for tests in each phase
Each phase in `10-IMPLEMENTATION-PLAN.md` lists its tests. A phase is not complete until `make check` is green and the listed tests exist.
