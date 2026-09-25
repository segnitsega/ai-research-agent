# ADR-0004: Server-Sent Events with our own typed event contract

- **Status:** Accepted
- **Date:** 2026-10-25

## Context
The UI must show multi-agent progress live. Options: WebSockets, SSE with a custom event schema, or PydanticAI's built-in UI adapters (Vercel AI Data Stream Protocol, AG-UI).

## Decision
Use **SSE** with our own event catalog (`05-API-SPEC.md` §4), persisted in `run_events` and replayable via `Last-Event-ID`.

## Rationale
- Communication is one-way (server to client); SSE is simpler than WebSockets and reconnects natively.
- Our events are workflow-level (plan created, source fetched, finding rejected, critic review) and do not map cleanly onto a chat transcript, which is what the Vercel AI protocol models.
- Persisting events makes runs replayable, debuggable, and resumable, and lets finished runs render from the same reducer as live ones.
- Typed discriminated unions give the frontend exact generated types.

## Consequences
- We build and test the SSE endpoint and the frontend reducer ourselves.
- The PydanticAI UI adapters remain a good fit for the optional "chat with this report" extension (Phase 13), where a conversational protocol is appropriate. Those adapter endpoints are not an authentication boundary; authenticate separately.
