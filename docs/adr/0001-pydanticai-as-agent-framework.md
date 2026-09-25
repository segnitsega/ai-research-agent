# ADR-0001: PydanticAI as the agent framework

- **Status:** Accepted
- **Date:** 2026-10-25

## Context
We need a multi-agent system with typed handoffs, testability, observability, and production-grade engineering. Candidates: PydanticAI, CrewAI, LangGraph/LangChain.

## Decision
Use **PydanticAI** for all agents.

## Rationale
- Typed outputs (`output_type`) with validation and automatic retry align with our schema-first design.
- Dependency injection (`deps_type`, `RunContext`) keeps agents testable and free of globals.
- `TestModel`, `FunctionModel` and a global switch to block real model requests give deterministic, offline tests.
- Model-agnostic (Anthropic, OpenAI, Gemini, Ollama), so per-agent model choice is configuration.
- OpenTelemetry/Logfire instrumentation and `pydantic-evals` cover tracing and evaluation.
- Same ecosystem as Pydantic and FastAPI, so schemas flow end to end (agents, API, OpenAPI, frontend types).

## Consequences
- We write the orchestration ourselves (see ADR-0002).
- The library changes quickly (2.x at time of writing), so we pin versions, track them in `docs/VERSIONS.md`, and follow the "verify the API" rule in `AGENTS.md` §5.
- CrewAI remains an optional comparison (Phase 13) behind the same orchestrator interface.
