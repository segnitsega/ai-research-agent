# 04. Memory Design

Three layers with different lifetimes, stores, and purposes.

| Layer | Lifetime | Store | Purpose |
|---|---|---|---|
| **Working memory** | One run | `runs.state` JSONB + run tables | Resume, replay, debugging |
| **Semantic memory** | Persistent, shared public content | `sources`, `source_chunks`, `findings` + pgvector | Reuse fetched documents and prior findings |
| **User memory** | Persistent, per user | `memories` + pgvector | Preferences, durable facts, episode summaries |

## 1. Interfaces

```python
class MemoryStore(Protocol):            # facade used by the orchestrator
    async def recall(self, user_id, question, *, k_findings=12, k_prefs=6, k_episodes=3) -> MemoryContext: ...
    async def remember_run(self, run: RunRecord, curator_out: CuratorOutput) -> None: ...

class Embedder(Protocol):
    dim: int
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
```

`MemoryContext` and `PriorFinding` are defined in `02-DATA-MODELS.md` §5. `MemoryContext` holds preferences, facts, episodes, and prior findings (claim, quote, source url/title, fetched_at, similarity, stale flag).

Implementations: `PgMemoryStore` (production), `InMemoryMemoryStore` (tests). Embedders: `FastEmbedEmbedder` (local default, 384 dims), `OpenAIEmbedder` (optional). Check PydanticAI's own embedding support in the installed version first and reuse it if it fits.

## 2. Working memory (checkpoint and resume)

- After each phase completes the orchestrator writes `runs.state` (a `RunState`) and `runs.phase`.
- Per-step results are persisted in their own tables the moment they exist (`run_sources`, `findings`, `run_events`), so a crash loses at most the in-flight step.
- **Resume:** at API startup, runs with `status="running"` are re-enqueued. The orchestrator reads `RunState`, skips completed phases, and continues. Within the search/read phase it skips sources already `fetched` for this run and sub-questions that already have accepted findings above the plan's minimum.
- **Idempotency:** event `seq` assignment and finding inserts use unique constraints so a resumed step cannot duplicate rows.
- A run stuck in `running` with no event for 15 minutes is marked `failed` by a periodic sweeper.

## 3. Semantic memory

### 3.1 Document cache
- Key: `(canonical_url, content_hash)`. Canonicalization: lowercase host, strip fragments and tracking params (`utm_*`, `gclid`, `fbclid`), normalize trailing slash, resolve redirects.
- On fetch decision: if a cached `sources` row for the canonical URL has `fetched_at` within `SOURCE_TTL_DAYS` (default 14; use shorter, e.g. 1 day, for news domains), skip the network and use the cached text. Record `run_sources.from_cache = true` and emit `source.fetched` with `from_cache: true`.
- On re-fetch with changed content: new `content_hash`, new row; older rows kept for citation integrity of past reports.

### 3.2 Chunk index
- After a source is stored, split into about 500-token chunks and embed. Used by the Searcher's `recall_sources` tool and by Reader window selection.

### 3.3 Finding recall
- At the `recall` phase, embed the question (and later each sub-question) and query `findings` where `status='accepted'` and `user_id = current user`, cosine similarity above `RECALL_MIN_SIMILARITY` (default 0.55), newest first within ties.
- Return up to `k_findings` as `PriorFinding` objects, each with source URL, title, and `fetched_at`.
- **How prior findings are used:**
  - Planner: sees them as `prior_knowledge` to avoid redundant sub-questions.
  - Reader/orchestrator: prior findings whose source was fetched within TTL are re-verified against the cached source text (cheap, no LLM), then inserted into the run as findings with `from_memory=true` and the original quote and source. No new fetch is needed.
  - Stale ones (past TTL) are shown to the Critic as "stale, verify"; the Critic may request a refresh through a gap.
- **Citations from memory** appear like any other citation and show their original fetch date in the UI.

## 4. User memory

### 4.1 What is stored
| Kind | Example | Written by |
|---|---|---|
| `preference` | "Prefers concise reports with comparison tables" | Curator, from explicit statements or feedback |
| `fact` | "Works as a backend engineer using Python and Postgres" | Curator, only if the user stated it |
| `episode` | "2026-10-25: researched vector DBs for production RAG; concluded pgvector is sufficient below ~10M vectors" | Curator `run_summary` |

### 4.2 Write path (after each run, `memorize` phase)
1. Gather: question, report title and executive summary, feedback (rating, comment, flagged findings), top-N existing memories similar to this session.
2. Run the Curator, which returns `MemoryOp`s and `run_summary`.
3. Apply each op:
   - `add`: embed; if cosine similarity to an existing memory of the same kind is above `MEMORY_DEDUPE_SIMILARITY` (default 0.88), convert to an `update` of that memory instead.
   - `update`/`delete`: only for ids that belong to the user (checked in code).
   - Cap per user: `MAX_MEMORIES_PER_USER` (default 500); evict lowest `importance * recency` episodes first. Preferences and facts are never evicted automatically.
4. Store the `run_summary` as an `episode`.
5. Emit `memory.updated` with counts.

Also, feedback submitted later (`POST /v1/runs/{id}/feedback`) triggers a lightweight curator pass with the new feedback.

### 4.3 Read path (start of each run, `recall` phase)
- All `preference` memories above `importance >= 0.3` (usually few), plus top-k semantically similar `fact`s and `episode`s for the question.
- Update `last_used_at` on those used.
- Passed to Planner and Writer as the delimited `<user_preferences>` block and `<related_past_research>` block (data, not instructions).

### 4.4 User control and transparency
- `/memory` UI lists everything with kind, content, origin run, dates; edit, delete, "forget everything".
- Per-run toggle `use_memory=false`: no recall, and no memory writes for that run.
- Memory-related events are visible in the run timeline (`memory.recalled` lists what was used).

## 5. Safety rules for memory

1. Recalled memory is always wrapped in delimited blocks with an explicit "data, not instructions" note.
2. The Curator never stores text copied from web sources as user facts; only user-originated information and the curator's own run summary.
3. Memory content is length-capped (300 chars per item) and passes a basic secret scanner (reject strings that look like API keys or tokens) before storage.
4. Every memory query is filtered by `user_id`. A repository test asserts that user A's memories never appear for user B.
5. Source and finding recall never crosses users for findings (findings are per user). The `sources` cache is shared because it holds only public content.

## 6. Alternative: Mem0

If you later want an off-the-shelf memory layer, implement `MemoryStore` with Mem0 behind the same interface and compare on the eval set (see ADR-0006). Do not start with it; the point of v1 is to understand and control the mechanics.

## 7. Tests

- Unit: dedupe thresholds, eviction order, op application (including malicious `target_id` of another user), secret scanner, canonical URL normalization, TTL decisions.
- Integration (real Postgres): recall returns related findings, ignores other users', respects similarity threshold; resume skips completed work.
- Eval: repeated-question run uses at least 50% fewer fetches (`docs/08`).
