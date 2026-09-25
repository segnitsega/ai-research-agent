# 00. Product Requirements Document

## 1. Summary

Deep Research Agent turns a research question into a cited, verifiable report. A team of specialized agents plans, searches, reads, verifies and writes. The user watches the work live, can click any claim back to the exact source passage, and benefits from memory of earlier research and personal preferences.

## 2. Goals

1. **Trustworthy output:** every claim in a report is backed by a verbatim quote from a fetched source.
2. **Visible agent work:** the UI shows what each agent is doing in real time.
3. **Memory that helps:** repeated or related questions are faster and cheaper; preferences persist.
4. **Production-ready engineering:** typed, tested, observable, secure, containerized, with CI and evals.
5. **Bounded cost:** every run has hard budgets, and the user sees cost as it accrues.

## 3. Non-goals (v1)

- Multi-tenant SaaS (auth is a single-user API key; the schema is user-ready)
- Collaboration, sharing, or comments
- Image, audio, or video research
- Paywalled or logged-in content
- Mobile app
- Fine-tuning or training models

## 4. Users and scenarios

Primary user: a technically comfortable individual doing research (developer, analyst, student). Example questions:

- "Compare the current state of open-source vector databases for production RAG."
- "What does recent evidence say about intermittent fasting and cardiovascular risk?"
- "Summarize the main approaches to LLM agent memory published in the last year."

## 5. User stories and acceptance criteria

### Research runs
- **US-1** As a user I submit a question with a depth (quick, standard, deep) and optional budget limits, and get a run page immediately.
  - AC: `POST /v1/runs` returns 202 with `run_id` in under 500 ms; UI navigates to `/runs/{id}`.
- **US-2** As a user I see the research plan as soon as it exists.
  - AC: sub-questions render within the live view when the `plan.created` event arrives.
- **US-3** As a user I watch sources being found, fetched, and mined for findings.
  - AC: timeline shows `source.found`, `source.fetched`, `finding.extracted` events grouped by agent, with counts updating live.
- **US-4** As a user I can cancel a running run.
  - AC: cancel stops further LLM and fetch calls within 5 seconds and marks the run `cancelled`; partial results remain viewable.
- **US-5** As a user I can reload or reconnect mid-run without losing progress.
  - AC: SSE reconnect with `Last-Event-ID` replays missed events; the final UI state is identical to an uninterrupted viewer.

### Report quality
- **US-6** As a user I get a structured report: title, executive summary, sections, limitations, numbered citations.
- **US-7** As a user I can hover or click a citation to see the exact evidence quote, source title, domain, and fetch date, and open the source.
  - AC: 100% of citations in a completed report resolve to an accepted finding with a verified quote.
- **US-8** As a user I am told what the report could not establish (gaps, contradictions, budget cut-offs).
  - AC: `limitations` is populated whenever the Critic's last review still listed gaps or a budget stopped the run.
- **US-9** As a user I can export the report as Markdown.

### Memory
- **US-10** As a user, related past research is reused: sources already fetched within the freshness window are not re-fetched, and prior findings are surfaced to the agents.
  - AC: a repeated question uses at least 50% fewer fetches in the eval suite (measured in `docs/08`).
- **US-11** As a user, my stated preferences (for example "concise", "prefer primary sources", "I'm a backend engineer") are remembered and applied.
- **US-12** As a user I can view, edit, and delete everything the system remembers about me, and disable memory per run.
  - AC: `/memory` page lists memories with kind, content, source run, and delete/edit controls.

### History and feedback
- **US-13** As a user I can browse past runs with status, question, date, cost.
- **US-14** As a user I can rate a report and flag individual findings as wrong; feedback influences user memory.

### Operability
- **US-15** As an operator I can see per-run token usage and cost, and traces of every agent call.
- **US-16** As an operator I can run the whole stack with `docker compose up`.

## 6. Functional requirements summary

| ID | Requirement |
|---|---|
| FR-1 | Six agents with typed outputs (see `03-AGENT-SPECS.md`) |
| FR-2 | Iterative loop: Critic can send the run back for more research until sufficient or budget exhausted |
| FR-3 | Verbatim quote verification of every finding |
| FR-4 | Hard budgets: iterations, fetches, tokens, cost, wall clock |
| FR-5 | Three memory layers (see `04-MEMORY-DESIGN.md`) |
| FR-6 | REST API and SSE event stream (see `05-API-SPEC.md`) |
| FR-7 | Next.js UI (see `06-FRONTEND-SPEC.md`) |
| FR-8 | Resumable runs: checkpoint after each phase; recoverable after an API restart |
| FR-9 | Configurable models per agent via environment |
| FR-10 | Pluggable search providers and embedders |

## 7. Non-functional requirements

| Area | Requirement |
|---|---|
| Performance | Quick run p50 under 90 s; standard under 4 min; deep under 12 min (provider-dependent) |
| Cost | Typical targets: quick under $0.15, standard under $0.60, deep under $2.00. Hard caps per depth are higher (0.25 / 0.75 / 2.50 USD, see `02-DATA-MODELS.md` §2) and configurable |
| Reliability | Tool calls have timeouts and retries with backoff; one failed source never fails a run |
| Security | SSRF protection, quarantined Reader, API key auth, no secrets in logs (see `07`) |
| Observability | Structured logs, OpenTelemetry traces, per-run usage and cost |
| Accessibility | WCAG 2.2 AA for the web app |
| Quality | Type-checked, 85%+ backend line coverage, evals run in CI |
| Portability | Runs locally with Docker; no vendor lock-in beyond chosen LLM and search APIs |

## 8. Success metrics

Measured by the eval suite (`docs/08-TESTING-EVALS.md`) on a golden set of 20 questions:

| Metric | Target |
|---|---|
| Citation validity (quote found in source) | 100% (enforced by construction) |
| Claim support rate (LLM judge: claim supported by quote) | 90% or higher |
| Coverage (rubric: expected sub-topics covered) | 80% or higher |
| Memory savings (fetches on repeat question) | 50% or lower than first run |
| Cost per standard run | under $0.60 median |
| Failed runs (non-budget) | under 2% |

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| LLM hallucinated citations | Verbatim quote check; Writer limited to accepted findings |
| Prompt injection from web pages | Quarantined Reader with no tools; structured output; findings validated |
| Runaway cost or loops | Hard budgets enforced in code; iteration cap |
| Search provider rate limits or outages | Provider abstraction, retries, graceful degradation |
| Memory poisoning or stale facts | Curated memory only from agent summaries; freshness windows; user can delete |
| Library churn (PydanticAI, Next.js) | Pin versions, `docs/VERSIONS.md`, API rule in `AGENTS.md` |

## 10. Open questions (decide during build, record in ADRs)

1. Default LLM and search providers (the specs assume Anthropic models plus Tavily, both swappable)
2. Whether to add the "chat with this report" feature (Phase 13, optional)
3. Hosting target for the demo deployment
