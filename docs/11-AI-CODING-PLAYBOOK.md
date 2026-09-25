# 11. AI Coding Playbook

How to drive an AI coding agent (Claude Code, Cursor, Codex, Copilot agent mode, or similar) through this project without it drifting, inventing APIs, or quietly weakening your guardrails. You are the tech lead; the agent is a fast, literal junior engineer with a good memory for common patterns and a poor memory for recent APIs.

## 1. Setup (once)

1. Put the pack in the repo: `AGENTS.md`, `CLAUDE.md`, `README.md`, `docs/`.
2. Commit it as `docs: add specification pack` so every later diff is reviewable.
3. Make sure the agent can run shell commands (tests, `make`), read files, and use the web or docs lookup if available. Library docs lookup matters a lot here (PydanticAI and Next.js move fast).
4. Create `docs/BACKLOG.md` (empty) for deferred items.
5. Use a feature branch per phase (`phase-3-agents`). Merge via PR even if you are solo; CI is your second reviewer.

## 2. The loop for every phase

```
1. READ     Tell the agent which docs to read (the phase prompt already does).
2. PLAN     Ask for a short plan first. Approve or correct it.
3. TEST     For logic-heavy parts, tests first; confirm they fail for the right reason.
4. BUILD    Implement in small steps. Commit per logical unit.
5. VERIFY   Agent runs `make check` and reports. You re-run it yourself.
6. REVIEW   You read the diff (see checklist below). Ask for changes.
7. RECORD   Update docs/adr/ and docs/VERSIONS.md if anything deviated. Merge.
```

Never skip step 6. Passing tests do not prove the code matches the spec.

## 3. Prompt patterns that work

**Scope it:** "Implement only Phase 4 tasks 1 to 3. Do not touch the API layer."

**Make it plan:** "Before coding, list the files you will create or change and the order. Wait for my OK." (Skip the wait for small tasks.)

**Make it verify library APIs:** "Check the installed PydanticAI version's real API for output validators and usage limits (read the installed package or official docs). Quote the signature you will use."

**Make it test first:** "Write failing tests for X from the spec, show them failing, then implement."

**Make it report honestly:** "End with: what you changed, what you verified and how, what you did not do, and any spec conflicts."

**Make it ask:** "If the spec is ambiguous, ask me instead of choosing."

**Review prompt (separate pass):** "Review the diff of this branch against docs/03 and docs/07. List violations of the spec, security rules, or AGENTS.md section 6. Do not fix anything yet."

## 4. Context hygiene

- Keep sessions focused: **one phase (or sub-phase) per session**. Start a fresh session for the next phase; `AGENTS.md` and the docs rebuild the context.
- If a session gets long and the agent starts forgetting rules, restart and say: "Read AGENTS.md and the docs for this phase, then continue from the current git state."
- Reference documents by path and section rather than pasting them in.
- When the agent makes a decision worth keeping, have it write an ADR (`docs/adr/00NN-title.md`) so the reasoning survives sessions.
- Keep `docs/VERSIONS.md` current; it is the first place to look when something behaves oddly after an upgrade.

## 5. Review checklist for every diff

Spec and design
- [ ] Matches the referenced spec sections (names, fields, event types, status codes)?
- [ ] No features beyond the phase scope?
- [ ] No new dependency without a reason?

Safety (from `AGENTS.md` §6)
- [ ] Only the Reader handles raw page text; it has no tools
- [ ] All fetches go through `tools/fetch.py`
- [ ] Quote verification and citation validation intact
- [ ] Budgets enforced in code
- [ ] Every user-data query filtered by `user_id`
- [ ] No secrets in code, logs, tests, or fixtures; nothing secret exposed to the browser

Quality
- [ ] Tests assert behavior (not just that code runs); error paths covered
- [ ] No weakened or skipped tests, no `# type: ignore` or `any` without a comment
- [ ] No blocking calls in async code; no unbounded loops or lists
- [ ] Names, structure, and file placement follow the layout in `01-ARCHITECTURE.md` §9
- [ ] Docs updated if behavior changed

## 6. Common failure modes and fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| Code uses a PydanticAI or Next.js API that does not exist | Agent relied on outdated memory | Tell it to inspect the installed package/docs; add the correct usage to `docs/VERSIONS.md` notes |
| Agent "fixes" a failing test by editing the test | Pressure to be green | Say: "Do not change the test. Explain why it fails." Review test diffs separately |
| Agent adds a heavy framework (LangChain, Redux, ORMs) unprompted | Over-eager | Point to `AGENTS.md` §8 and §10; ask for removal |
| Orchestrator grows giant methods | Missing structure | Ask for one method per phase and extraction of helpers; add a unit test per method |
| Agents return free text or untyped dicts | Skipped schemas | Insist on `output_type` models from `schemas/` |
| Tests secretly call the real LLM | Missing global guard | Confirm `ALLOW_MODEL_REQUESTS=False` in `conftest.py`; add a test that a real call raises |
| Flaky async tests | `sleep` waits or shared state | Use events/`wait_for`, isolate DB per test |
| Generated frontend types stale | Forgot `make types` | CI contract job catches it; run `make types` and commit |
| Agent drifts from spec silently | Long session, no re-read | Fresh session; ask it to diff its implementation against the spec and list differences |
| Cost surprises during manual runs | No budget set | Use `--depth quick` and `SERVER_MAX_COST_USD` low while developing |

## 7. Cost and safety while developing

- Use small, cheap models and `quick` depth while building. Set low `SERVER_MAX_COST_USD` (for example 0.50) in your `.env` until you trust the budget code.
- Never let the coding agent run live evals or loops unattended until Phase 11; keep `eval` and `live` markers out of default test runs.
- Keep provider spend limits configured in the provider dashboards.
- Use throwaway API keys for development and rotate them if they ever appear in a log or a diff.

## 8. When to use more than one agent session in parallel

Safe to parallelize (separate branches, separate directories):
- Phase 8 (frontend scaffold) alongside Phases 5 to 7 once `openapi.json` exists and a recorded event fixture is available
- Test-writing sessions (for example SSRF tables) alongside implementation, as long as they do not edit the same files

Do not parallelize: anything touching `schemas/`, the DB migrations, or the orchestrator.

## 9. Final-mile checklist

- [ ] Fresh clone: README quick start works end to end
- [ ] `make check` green, CI green on `main`
- [ ] Real run of each depth recorded with cost and duration in `docs/EVAL-RESULTS.md`
- [ ] Security checklist (`07` §9) fully proven
- [ ] ADRs reflect the final design; `docs/VERSIONS.md` current
- [ ] Demo script ready: one question, live timeline, citation click-through, repeat-question memory win
