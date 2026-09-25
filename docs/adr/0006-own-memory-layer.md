# ADR-0006: Build a thin memory layer on pgvector instead of adopting Mem0

- **Status:** Accepted
- **Date:** 2026-10-25

## Context
The project needs working, semantic, and user memory. Off-the-shelf options (for example Mem0) exist.

## Decision
Implement memory ourselves behind a `MemoryStore` protocol using Postgres and pgvector, with a dedicated Curator agent deciding what to remember.

## Rationale
- Goals include understanding and controlling memory mechanics (recall thresholds, TTLs, dedupe, user control, isolation).
- Fewer dependencies and a single datastore.
- Our semantic memory is domain-specific (documents, verified findings with quotes), which a general-purpose memory service does not model.

## Consequences
- We own dedupe, eviction, and safety rules and must test them (`04-MEMORY-DESIGN.md` §7).
- The protocol allows adding a Mem0-backed implementation later and comparing it on the eval suite.
