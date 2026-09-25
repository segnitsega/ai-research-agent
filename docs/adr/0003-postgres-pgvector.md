# ADR-0003: Postgres with pgvector for all persistence

- **Status:** Accepted
- **Date:** 2026-10-25

## Context
We need relational storage (runs, events, findings), JSON checkpoints, and vector search for semantic memory. Options: Postgres + pgvector, separate vector DB (Qdrant, Chroma, Weaviate), SQLite.

## Decision
Use a single Postgres 16 instance with the `pgvector` extension and HNSW indexes.

## Rationale
- One datastore: transactional consistency between findings, sources, and their embeddings.
- Simple local development (one container) and wide managed support.
- Scale is modest (per-user research data); pgvector is sufficient well beyond that.
- JSONB handles checkpoints and event payloads.

## Consequences
- Embedding dimension is fixed in the schema (default 384 for the local embedder). Changing it needs a re-embedding migration; record any change in a new ADR.
- Vector queries must still respect `user_id` filters; we test isolation explicitly.
- If scale or filtering needs outgrow pgvector, the `MemoryStore` interface allows moving vectors elsewhere.
