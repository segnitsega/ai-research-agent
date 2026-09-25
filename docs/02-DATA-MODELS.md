# 02. Data Models

All models live in `apps/api/src/research_agent/schemas/`. They are the single source of truth: agents' `output_type`, API request/response bodies, DB JSON columns, and (via OpenAPI) the frontend types.

Conventions: Pydantic v2, `model_config = ConfigDict(extra="forbid", frozen=True)` for agent outputs; IDs are UUIDv7 or UUIDv4 strings; timestamps are timezone-aware UTC.

## 1. Enums

```python
class Depth(StrEnum):         QUICK="quick"; STANDARD="standard"; DEEP="deep"
class RunStatus(StrEnum):     QUEUED="queued"; RUNNING="running"; COMPLETED="completed"; FAILED="failed"; CANCELLED="cancelled"
class Phase(StrEnum):         RECALL="recall"; PLAN="plan"; SEARCH="search"; READ="read"; CRITIQUE="critique"; WRITE="write"; MEMORIZE="memorize"
class AgentName(StrEnum):     PLANNER="planner"; SEARCHER="searcher"; READER="reader"; CRITIC="critic"; WRITER="writer"; CURATOR="curator"; SYSTEM="system"
class FindingStatus(StrEnum): ACCEPTED="accepted"; REJECTED="rejected"; FLAGGED="flagged"   # flagged = user said wrong
class MemoryKind(StrEnum):    PREFERENCE="preference"; FACT="fact"; EPISODE="episode"
```

## 2. Request and budget

```python
class Budget(BaseModel):
    max_iterations: int = Field(ge=1, le=6)
    max_fetches: int = Field(ge=1, le=200)
    max_cost_usd: float = Field(gt=0, le=20)
    max_tokens: int = Field(gt=0)            # total across all agents
    max_wall_seconds: int = Field(gt=0)

class BudgetOverrides(BaseModel):            # every field optional; unset fields use the depth preset
    max_iterations: int | None = Field(default=None, ge=1, le=6)
    max_fetches: int | None = Field(default=None, ge=1, le=200)
    max_cost_usd: float | None = Field(default=None, gt=0, le=20)
    max_tokens: int | None = Field(default=None, gt=0)
    max_wall_seconds: int | None = Field(default=None, gt=0)
    # the server rejects (422) any value above the SERVER_MAX_* settings

class RunRequest(BaseModel):
    question: str = Field(min_length=8, max_length=2000)
    depth: Depth = Depth.STANDARD
    use_memory: bool = True
    budget: BudgetOverrides | None = None
    language: str = "en"
```

Depth presets (server-side defaults, overridable up to server maximums). These are **hard caps**; typical spend is lower (see cost targets in `00-PRD.md` §7):

| Depth | sub-questions | max_iterations | max_fetches | max_cost_usd | max_tokens | max_wall_seconds |
|---|---|---|---|---|---|---|
| quick | 3 | 1 | 10 | 0.25 | 300,000 | 180 |
| standard | 5 | 2 | 30 | 0.75 | 1,000,000 | 420 |
| deep | 8 | 4 | 80 | 2.50 | 3,000,000 | 900 |

## 3. Agent I/O models

```python
class SubQuestion(BaseModel):
    id: str                       # "q1", "q2", ...
    question: str
    rationale: str
    priority: Literal[1, 2, 3]    # 1 = essential
    preferred_source_types: list[Literal["academic","official","news","industry","community","any"]] = ["any"]

class ResearchPlan(BaseModel):
    objective: str
    sub_questions: list[SubQuestion] = Field(min_length=1, max_length=8)
    success_criteria: list[str] = Field(min_length=1, max_length=6)
    out_of_scope: list[str] = []

class SearchHit(BaseModel):
    url: HttpUrl
    title: str
    snippet: str
    provider: str
    published_at: datetime | None = None
    score: float | None = None

class SourceCandidate(BaseModel):          # Searcher output element
    url: HttpUrl
    title: str
    sub_question_id: str
    reason: str                            # why this is worth reading
    expected_quality: Literal["high","medium","low"]

class SearcherOutput(BaseModel):
    candidates: list[SourceCandidate] = Field(max_length=12)
    queries_used: list[str]

class FindingDraft(BaseModel):             # Reader output element
    sub_question_id: str
    claim: str = Field(max_length=500)           # one atomic factual statement, in the Reader's own words
    evidence_quote: str = Field(min_length=20, max_length=400)   # must be verbatim from the source text
    confidence: float = Field(ge=0, le=1)
    stance: Literal["supports","contradicts","context"] = "supports"

class ReaderOutput(BaseModel):
    findings: list[FindingDraft] = Field(max_length=8)
    source_quality_note: str | None = None
    off_topic: bool = False

class Finding(BaseModel):                  # persisted, verified
    id: str
    run_id: str
    source_id: str
    sub_question_id: str
    claim: str
    evidence_quote: str
    confidence: float
    stance: Literal["supports","contradicts","context"]
    status: FindingStatus
    reject_reason: str | None = None
    from_memory: bool = False

class Gap(BaseModel):
    sub_question_id: str
    description: str
    suggested_queries: list[str] = Field(max_length=4)

class Contradiction(BaseModel):
    finding_ids: list[str] = Field(min_length=2)
    description: str

class Review(BaseModel):                   # Critic output
    verdict: Literal["sufficient","needs_more"]
    coverage_by_sub_question: dict[str, Literal["none","partial","good"]]
    gaps: list[Gap] = []
    contradictions: list[Contradiction] = []
    weak_finding_ids: list[str] = []       # single-source, low-quality, or vague
    rationale: str

class ReportSection(BaseModel):
    heading: str
    body_markdown: str                     # uses [1], [2] ... citation markers
    finding_ids: list[str]

class Citation(BaseModel):
    n: int
    source_id: str
    finding_ids: list[str]

class Report(BaseModel):                   # Writer output
    title: str
    executive_summary: str                 # also uses citation markers
    sections: list[ReportSection] = Field(min_length=1)
    limitations: list[str]
    citations: list[Citation]
```

Writer output validators (see `03-AGENT-SPECS.md` §5): every `[n]` marker has a `Citation`, every `finding_id` is an accepted finding of this run, every section has at least one citation.

## 4. Memory models

```python
class MemoryItem(BaseModel):
    id: str
    kind: MemoryKind
    content: str                 # short, self-contained, third-person ("User prefers concise reports")
    importance: float            # 0..1
    source_run_id: str | None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None

class MemoryOp(BaseModel):                 # Curator output element
    op: Literal["add","update","delete","noop"]
    target_id: str | None = None           # required for update/delete
    kind: MemoryKind | None = None
    content: str | None = None
    importance: float | None = None
    reason: str

class CuratorOutput(BaseModel):
    ops: list[MemoryOp] = Field(max_length=10)
    run_summary: str = Field(max_length=600)   # stored as an EPISODE memory
```

## 5. Run state, usage, events

```python
class AgentUsage(BaseModel):
    requests: int; input_tokens: int; output_tokens: int; cost_usd: float

class RunUsage(BaseModel):
    requests: int; input_tokens: int; output_tokens: int
    fetches: int; cost_usd: float
    by_agent: dict[AgentName, AgentUsage]

class PriorFinding(BaseModel):             # a finding recalled from earlier runs (see 04-MEMORY-DESIGN §3.3)
    finding_id: str
    claim: str
    evidence_quote: str
    source_id: str
    source_url: str
    source_title: str | None
    fetched_at: datetime
    similarity: float
    stale: bool                            # source older than SOURCE_TTL_DAYS

class MemoryContext(BaseModel):            # result of the recall phase
    preferences: list[MemoryItem]
    episodes: list[MemoryItem]
    facts: list[MemoryItem]
    prior_findings: list[PriorFinding]

class FindingView(BaseModel):              # compact read-only view of a Finding given to Critic/Writer
    id: str
    sub_question_id: str
    claim: str
    evidence_quote: str
    confidence: float
    stance: Literal["supports","contradicts","context"]
    source_domain: str
    source_title: str | None
    source_published_at: datetime | None
    source_fetched_at: datetime
    from_memory: bool

class RunState(BaseModel):                 # checkpoint stored in runs.state
    phase_done: list[Phase]
    iteration: int
    plan: ResearchPlan | None
    pending_gaps: list[Gap]
    last_review: Review | None
    memory_context: MemoryContext | None
    usage: RunUsage

class RunEvent(BaseModel):                 # envelope; full catalog in 05-API-SPEC.md
    seq: int
    run_id: str
    ts: datetime
    type: str
    agent: AgentName
    data: dict            # typed per event via discriminated union in code
```

The code defines `EventData` as a discriminated union keyed on `type`, one model per event in `05-API-SPEC.md` §4, so the schema and OpenAPI reflect every payload.

## 6. Database schema (Postgres 16 + pgvector)

Embedding dimension is set by `EMBEDDING_DIM` (default 384, matching the default local embedder). Changing it later requires a re-embedding migration; record the choice in an ADR.

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE users (
  id uuid PRIMARY KEY,
  email text UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);
-- v1 seeds one fixed user: 00000000-0000-0000-0000-000000000001

CREATE TABLE runs (
  id uuid PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES users(id),
  question text NOT NULL,
  depth text NOT NULL,
  use_memory boolean NOT NULL DEFAULT true,
  status text NOT NULL,                       -- RunStatus
  phase text,                                 -- current Phase
  budget jsonb NOT NULL,                      -- Budget
  state jsonb NOT NULL DEFAULT '{}',          -- RunState checkpoint
  plan jsonb,
  report jsonb,
  usage jsonb NOT NULL DEFAULT '{}',
  error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  finished_at timestamptz
);
CREATE INDEX runs_user_created ON runs (user_id, created_at DESC);

CREATE TABLE run_events (
  run_id uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  seq integer NOT NULL,
  ts timestamptz NOT NULL DEFAULT now(),
  type text NOT NULL,
  agent text NOT NULL,
  data jsonb NOT NULL,
  PRIMARY KEY (run_id, seq)
);

-- global, user-independent cache of public web documents
CREATE TABLE sources (
  id uuid PRIMARY KEY,
  canonical_url text NOT NULL,
  content_hash text NOT NULL,
  title text,
  domain text NOT NULL,
  text text NOT NULL,
  published_at timestamptz,
  fetched_at timestamptz NOT NULL,
  content_type text,
  UNIQUE (canonical_url, content_hash)
);
CREATE INDEX sources_url ON sources (canonical_url, fetched_at DESC);

CREATE TABLE run_sources (
  run_id uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  source_id uuid NOT NULL REFERENCES sources(id),
  sub_question_id text NOT NULL,
  rank integer,
  status text NOT NULL,                       -- found | fetched | failed | skipped
  error text,
  from_cache boolean NOT NULL DEFAULT false,
  PRIMARY KEY (run_id, source_id, sub_question_id)
);

CREATE TABLE source_chunks (
  id uuid PRIMARY KEY,
  source_id uuid NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  chunk_index integer NOT NULL,
  text text NOT NULL,
  embedding vector(384) NOT NULL,
  UNIQUE (source_id, chunk_index)
);
CREATE INDEX source_chunks_embedding ON source_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE findings (
  id uuid PRIMARY KEY,
  run_id uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id),
  source_id uuid NOT NULL REFERENCES sources(id),
  sub_question_id text NOT NULL,
  claim text NOT NULL,
  evidence_quote text NOT NULL,
  confidence real NOT NULL,
  stance text NOT NULL,
  status text NOT NULL,
  reject_reason text,
  from_memory boolean NOT NULL DEFAULT false,
  embedding vector(384),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX findings_run ON findings (run_id);
CREATE INDEX findings_embedding ON findings USING hnsw (embedding vector_cosine_ops);

CREATE TABLE memories (
  id uuid PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES users(id),
  kind text NOT NULL,
  content text NOT NULL,
  importance real NOT NULL DEFAULT 0.5,
  embedding vector(384) NOT NULL,
  source_run_id uuid REFERENCES runs(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz,
  deleted_at timestamptz
);
CREATE INDEX memories_user_kind ON memories (user_id, kind) WHERE deleted_at IS NULL;
CREATE INDEX memories_embedding ON memories USING hnsw (embedding vector_cosine_ops);

CREATE TABLE feedback (
  id uuid PRIMARY KEY,
  run_id uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  rating smallint CHECK (rating BETWEEN 1 AND 5),
  comment text,
  flagged_finding_ids uuid[] NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
```

Notes:
- `sources` has no `user_id` because it only holds public web content. Everything user-specific (`runs`, `findings`, `memories`, `feedback`) is scoped by `user_id`, and **every repository query must filter by it**.
- Verify pgvector index syntax and operators against the installed pgvector version.
- Soft-delete `memories` (set `deleted_at`); hard-delete via a purge job after 30 days or on user request.
