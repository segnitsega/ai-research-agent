# ADR-0002: Plain async Python orchestration

- **Status:** Accepted
- **Date:** 2026-10-25

## Context
The workflow (recall, plan, search/read loop, critique, write, memorize) is a small state machine. Options: plain async Python, `pydantic-graph`, LangGraph.

## Decision
Implement orchestration as a `RunOrchestrator` class with one method per phase, using `asyncio.TaskGroup` for parallelism, and our own checkpointing in Postgres.

## Rationale
- Simplest to read, test, and debug; the control flow is ordinary code.
- Persistence for the newer `pydantic-graph` graph API was unclear when this was written (a public issue asked how to persist with the new graph API), and our needs (checkpoints, events, resume) are specific to our tables anyway.
- LangGraph would add a second ecosystem and mental model for little gain at this scale.
- Our requirements (typed events, budgets, cancellation, resume) are easier to guarantee in code we own.

## Consequences
- We maintain resume logic ourselves (documented in `04-MEMORY-DESIGN.md` §2) and test it thoroughly.
- If the workflow grows complex (branching, human-in-the-loop approvals), revisit: a `pydantic-graph` variant is listed as a Phase 13 extension and can be compared on the eval suite.
- The orchestrator is behind an interface so alternative implementations can be swapped.
