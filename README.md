# Deep Research Agent

A multi-agent research system. You ask a question; a team of typed AI agents plans the research, searches the web, reads sources, verifies claims, and writes a cited report. Memory lets it reuse earlier research and learn your preferences.

- **Backend:** Python 3.12, FastAPI, PydanticAI, Postgres + pgvector
- **Frontend:** Next.js (App Router), TypeScript, Tailwind, shadcn/ui
- **Streaming:** Server-Sent Events with a typed event contract

> This folder is the **specification pack**. Copy it into the root of your repo (the `docs/` folder, `AGENTS.md`, `CLAUDE.md`, and this README), then work through `docs/10-IMPLEMENTATION-PLAN.md` with your AI coding agent.

## How to use this pack

1. Create an empty repo and copy these files in, keeping the folder layout.
2. Read `docs/11-AI-CODING-PLAYBOOK.md` once. It explains how to drive the coding agent phase by phase.
3. Open your coding agent (Claude Code, Cursor, Codex, etc.) in the repo root. It will pick up `AGENTS.md` (or `CLAUDE.md`, which points to it).
4. Paste the **Phase 0 prompt** from `docs/10-IMPLEMENTATION-PLAN.md`. Finish each phase and check its acceptance criteria before starting the next.

## Document map

| File | Purpose | Read when |
|---|---|---|
| `AGENTS.md` | Standing instructions for the coding agent | Always loaded by the agent |
| `docs/00-PRD.md` | What we are building and why; scope, user stories, success metrics | Start |
| `docs/01-ARCHITECTURE.md` | System design, components, data flow, repo layout | Phase 0 onward |
| `docs/02-DATA-MODELS.md` | Pydantic schemas and database schema | Phase 1 |
| `docs/03-AGENT-SPECS.md` | Each agent: role, inputs, outputs, tools, prompts | Phases 3 to 5 |
| `docs/04-MEMORY-DESIGN.md` | Working, semantic and user memory | Phase 7 |
| `docs/05-API-SPEC.md` | REST endpoints and the SSE event contract | Phase 6 |
| `docs/06-FRONTEND-SPEC.md` | Pages, components, stream handling | Phases 8 to 10 |
| `docs/07-SECURITY-GUARDRAILS.md` | SSRF, prompt injection, budgets, auth | Phases 2, 5, 12 |
| `docs/08-TESTING-EVALS.md` | Test strategy and evaluation harness | Every phase |
| `docs/09-DEVOPS.md` | Docker, CI, environments, deployment | Phases 0 and 12 |
| `docs/10-IMPLEMENTATION-PLAN.md` | Phased build plan with ready-to-paste prompts | Throughout |
| `docs/11-AI-CODING-PLAYBOOK.md` | How to work with the coding agent without it going off the rails | Before Phase 0 |
| `docs/adr/` | Architecture Decision Records (why we chose what we chose) | When questioning a decision |

## Version notes (checked 25 Oct 2026)

Library versions move fast. At the time this pack was written:

- PydanticAI was on the 2.x line (a search of the package index showed 2.57.0 released 16 Oct 2026)
- Next.js was on the 16.x line (16.3.x reported in September 2026)

**Do not pin from this README.** In Phase 0 the coding agent must install the latest stable versions, then record the exact pinned versions in `docs/VERSIONS.md`. Whenever a spec in this pack conflicts with the library's current official docs, the official docs win and the agent should note the deviation in an ADR.

## Quick start

The language model is Gemini only. Set `GOOGLE_API_KEY` or `GEMINI_API_KEY` in `.env`. Also set `API_KEY` to any private string. `make dev` forwards that `API_KEY` to the Next.js server. The browser never sees the Gemini key.

```bash
cp .env.example .env
make setup
make up
make migrate
make dev
```

Open http://localhost:3000, ask a question, and watch the run. With `SEARCH_PROVIDER=fake` (the default), search returns a local Gemini overview page and Gemini still plans, reads, critiques, and writes. Set `SEARCH_PROVIDER=tavily` and `TAVILY_API_KEY` when you want live web search.

Check the install:

```bash
make test
make eval
curl -s http://localhost:8000/healthz
```

A command-line run, from `apps/api` after Postgres is up:

```bash
uv run research-agent run "Who develops the Gemini models?" --depth quick
```
