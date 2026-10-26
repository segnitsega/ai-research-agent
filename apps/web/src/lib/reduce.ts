import { clip, domainOf } from "@/lib/format";

export type RunEvent = {
  seq: number;
  type: string;
  agent?: string;
  ts?: string;
  data: Record<string, unknown>;
};

export type FindingView = {
  id: string;
  claim: string;
  quote: string;
  confidence: number;
  stance: string;
  status: "accepted" | "rejected" | "flagged";
  subQuestionId: string;
  sourceId: string;
  reason: string;
};

export type SourceView = {
  id: string;
  url: string;
  title: string;
  domain: string;
  subQuestionId: string;
  status: "found" | "fetched" | "failed";
  fromCache: boolean;
  quality: string;
  note: string;
};

export type SubQuestionView = {
  id: string;
  question: string;
  rationale: string;
  priority: number;
};

export type PlanView = {
  objective: string;
  subQuestions: SubQuestionView[];
  successCriteria: string[];
  outOfScope: string[];
};

export type ReportSectionView = {
  heading: string;
  body: string;
  findingIds: string[];
};

export type CitationView = {
  n: number;
  sourceId: string;
  findingIds: string[];
};

export type ReportView = {
  title: string;
  executiveSummary: string;
  sections: ReportSectionView[];
  limitations: string[];
  citations: CitationView[];
};

export type UsageView = {
  requests: number;
  inputTokens: number;
  outputTokens: number;
  fetches: number;
  costUsd: number;
  byAgent: { name: string; costUsd: number; requests: number }[];
};

export type BudgetView = {
  maxIterations: number;
  maxFetches: number;
  maxCostUsd: number;
  maxTokens: number;
  maxWallSeconds: number;
};

export type ReviewView = {
  verdict: string;
  coverage: Record<string, string>;
  gaps: { subQuestionId: string; description: string }[];
  contradictions: string[];
  rationale: string;
};

export type BudgetWarning = {
  resource: string;
  used: number;
  limit: number;
};

export type RunState = {
  events: RunEvent[];
  status: string;
  phase: string;
  iteration: number;
  maxIterations: number;
  question: string;
  depth: string;
  useMemory: boolean;
  plan: PlanView | null;
  findings: FindingView[];
  sources: SourceView[];
  report: ReportView | null;
  review: ReviewView | null;
  usage: UsageView | null;
  budget: BudgetView | null;
  error: string | null;
  warnings: BudgetWarning[];
  exhausted: string | null;
  lastSeq: number;
};

const PHASE_BY_TYPE: Record<string, string> = {
  "memory.recalled": "recall",
  "plan.created": "plan",
  "iteration.started": "search",
  "search.started": "search",
  "source.found": "search",
  "source.fetched": "read",
  "source.failed": "search",
  "finding.extracted": "read",
  "finding.rejected": "read",
  "critic.review": "critique",
  "iteration.completed": "critique",
  "report.started": "write",
  "report.completed": "write",
  "memory.updated": "memorize",
};

export function emptyRunState(): RunState {
  return {
    events: [],
    status: "queued",
    phase: "",
    iteration: 0,
    maxIterations: 0,
    question: "",
    depth: "",
    useMemory: true,
    plan: null,
    findings: [],
    sources: [],
    report: null,
    review: null,
    usage: null,
    budget: null,
    error: null,
    warnings: [],
    exhausted: null,
    lastSeq: 0,
  };
}

function record(value: unknown): Record<string, unknown> | null {
  if (value !== null && typeof value === "object" && !Array.isArray(value)) return value as Record<string, unknown>;
  return null;
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function num(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function strings(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

export function parsePlan(value: unknown): PlanView | null {
  const wrapped = record(value);
  const plan = wrapped && record(wrapped.plan) ? record(wrapped.plan) : wrapped;
  if (!plan) return null;
  const subQuestions = Array.isArray(plan.sub_questions)
    ? plan.sub_questions.flatMap((item) => {
        const row = record(item);
        if (!row) return [];
        return [
          {
            id: text(row.id),
            question: text(row.question),
            rationale: text(row.rationale),
            priority: num(row.priority) || 2,
          },
        ];
      })
    : [];
  const objective = text(plan.objective);
  if (!objective && subQuestions.length === 0) return null;
  return {
    objective,
    subQuestions,
    successCriteria: strings(plan.success_criteria),
    outOfScope: strings(plan.out_of_scope),
  };
}

export function parseReport(value: unknown): ReportView | null {
  const wrapped = record(value);
  const report = wrapped && record(wrapped.report) ? record(wrapped.report) : wrapped;
  if (!report || !text(report.title)) return null;
  const sections = Array.isArray(report.sections)
    ? report.sections.flatMap((item) => {
        const row = record(item);
        if (!row) return [];
        return [
          {
            heading: text(row.heading),
            body: text(row.body_markdown),
            findingIds: strings(row.finding_ids),
          },
        ];
      })
    : [];
  const citations = Array.isArray(report.citations)
    ? report.citations.flatMap((item) => {
        const row = record(item);
        if (!row) return [];
        return [{ n: num(row.n), sourceId: text(row.source_id), findingIds: strings(row.finding_ids) }];
      })
    : [];
  return {
    title: text(report.title),
    executiveSummary: text(report.executive_summary),
    sections,
    limitations: strings(report.limitations),
    citations,
  };
}

export function parseUsage(value: unknown): UsageView | null {
  const wrapped = record(value);
  const usage = wrapped && record(wrapped.usage) ? record(wrapped.usage) : wrapped;
  if (!usage) return null;
  const byAgent = record(usage.by_agent);
  return {
    requests: num(usage.requests),
    inputTokens: num(usage.input_tokens),
    outputTokens: num(usage.output_tokens),
    fetches: num(usage.fetches),
    costUsd: num(usage.cost_usd),
    byAgent: byAgent
      ? Object.entries(byAgent).flatMap(([name, raw]) => {
          const row = record(raw);
          if (!row) return [];
          return [{ name, costUsd: num(row.cost_usd), requests: num(row.requests) }];
        })
      : [],
  };
}

export function parseBudget(value: unknown): BudgetView | null {
  const wrapped = record(value);
  const budget = wrapped && record(wrapped.budget) ? record(wrapped.budget) : wrapped;
  if (!budget || !num(budget.max_cost_usd)) return null;
  return {
    maxIterations: num(budget.max_iterations),
    maxFetches: num(budget.max_fetches),
    maxCostUsd: num(budget.max_cost_usd),
    maxTokens: num(budget.max_tokens),
    maxWallSeconds: num(budget.max_wall_seconds),
  };
}

export function parseReview(value: unknown): ReviewView | null {
  const wrapped = record(value);
  const review = wrapped && record(wrapped.review) ? record(wrapped.review) : wrapped;
  if (!review) return null;
  const coverage: Record<string, string> = {};
  const rawCoverage = record(review.coverage_by_sub_question);
  if (rawCoverage) {
    for (const [key, item] of Object.entries(rawCoverage)) {
      if (typeof item === "string") coverage[key] = item;
    }
  }
  const gaps = Array.isArray(review.gaps)
    ? review.gaps.flatMap((item) => {
        const row = record(item);
        if (!row) return [];
        return [{ subQuestionId: text(row.sub_question_id), description: text(row.description) }];
      })
    : [];
  const contradictions = Array.isArray(review.contradictions)
    ? review.contradictions.flatMap((item) => {
        const row = record(item);
        return row && text(row.description) ? [text(row.description)] : [];
      })
    : [];
  if (!text(review.verdict) && gaps.length === 0) return null;
  return { verdict: text(review.verdict), coverage, gaps, contradictions, rationale: text(review.rationale) };
}

function mergeSource(sources: SourceView[], patch: SourceView): SourceView[] {
  const index = sources.findIndex((item) => item.id === patch.id);
  if (index === -1) return [...sources, patch];
  const current = sources[index];
  const next = sources.slice();
  next[index] = {
    id: patch.id,
    url: patch.url || current.url,
    title: patch.title || current.title,
    domain: patch.domain || current.domain,
    subQuestionId: patch.subQuestionId || current.subQuestionId,
    status: patch.status,
    fromCache: patch.fromCache || current.fromCache,
    quality: patch.quality || current.quality,
    note: patch.note || current.note,
  };
  return next;
}

export function eventSummary(event: RunEvent): string {
  const data = event.data ?? {};
  switch (event.type) {
    case "run.started":
      return `Started a ${text(data.depth) || "research"} run`;
    case "memory.recalled": {
      const prefs = Array.isArray(data.preferences) ? data.preferences.length : 0;
      const episodes = Array.isArray(data.episodes) ? data.episodes.length : 0;
      return `Recalled ${prefs + episodes} memories and ${num(data.prior_findings)} prior findings`;
    }
    case "plan.created": {
      const plan = parsePlan(data);
      return plan && plan.subQuestions.length > 0 ? `Plan ready with ${plan.subQuestions.length} sub-questions` : "Plan ready";
    }
    case "iteration.started":
      return `Iteration ${num(data.iteration) || text(data.iteration)} of ${num(data.max_iterations) || text(data.max_iterations)}`;
    case "search.started":
      return `Searching “${text(data.query)}”`;
    case "source.found":
      return `Found ${text(data.domain) || domainOf(text(data.url)) || "a source"}`;
    case "source.fetched":
      return data.from_cache ? `Read ${domainOf(text(data.url)) || "a source"} from cache` : `Read ${domainOf(text(data.url)) || "a source"}`;
    case "source.failed":
      return `Could not fetch ${domainOf(text(data.url)) || "a source"} · ${text(data.reason).replaceAll("_", " ")}`;
    case "finding.extracted":
      return clip(text(data.claim), 110) || "Finding extracted";
    case "finding.rejected":
      return `Rejected a finding · ${text(data.reason).replaceAll("_", " ") || "quote check failed"}`;
    case "critic.review": {
      const review = parseReview(data);
      if (review?.verdict === "sufficient") return "Critic: coverage is sufficient";
      if (review?.verdict === "needs_more") return "Critic: more research needed";
      return "Critic reviewed the findings";
    }
    case "iteration.completed":
      return data.decision === "write" ? "Enough evidence to write" : `Continuing with ${num(data.accepted_findings_total)} findings`;
    case "report.started":
      return `Writing from ${num(data.findings_used)} findings`;
    case "report.completed":
      return "Report is ready";
    case "memory.updated":
      return `Memory updated · ${num(data.added)} added, ${num(data.updated)} revised`;
    case "budget.warning":
      return `${text(data.resource)} is near its limit`;
    case "budget.exhausted":
      return `${text(data.resource)} limit reached, writing with what we have`;
    case "run.completed":
      return "Run completed";
    case "run.failed":
      return "The research run failed.";
    case "run.cancelled":
      return "Run cancelled";
    default:
      return event.type.replaceAll(".", " ");
  }
}

export function reduce(state: RunState, event: RunEvent): RunState {
  if (state.events.some((item) => item.seq === event.seq)) return state;
  const data = event.data ?? {};
  const next: RunState = {
    ...state,
    events: [...state.events, event],
    lastSeq: Math.max(state.lastSeq, event.seq),
    phase: PHASE_BY_TYPE[event.type] ?? state.phase,
  };

  if (event.type === "run.started") {
    next.status = "running";
    next.question = text(data.question) || state.question;
    next.depth = text(data.depth) || state.depth;
    next.useMemory = typeof data.use_memory === "boolean" ? data.use_memory : state.useMemory;
    next.budget = parseBudget(data.budget) ?? state.budget;
  }
  if (event.type === "iteration.started") {
    next.iteration = num(data.iteration) || state.iteration;
    next.maxIterations = num(data.max_iterations) || state.maxIterations;
  }
  if (event.type === "plan.created") next.plan = parsePlan(data) ?? state.plan;
  if (event.type === "source.found") {
    const url = text(data.url);
    next.sources = mergeSource(state.sources, {
      id: text(data.source_id) || url,
      url,
      title: text(data.title) || domainOf(url) || "Untitled source",
      domain: text(data.domain) || domainOf(url),
      subQuestionId: text(data.sub_question_id),
      status: "found",
      fromCache: false,
      quality: text(data.expected_quality),
      note: text(data.reason),
    });
  }
  if (event.type === "source.fetched") {
    const url = text(data.url);
    const id = text(data.source_id) || url;
    const current = state.sources.find((item) => item.id === id);
    next.sources = mergeSource(state.sources, {
      id,
      url,
      title: current?.title || domainOf(url) || "Untitled source",
      domain: current?.domain || domainOf(url),
      subQuestionId: current?.subQuestionId || "",
      status: "fetched",
      fromCache: data.from_cache === true,
      quality: current?.quality || "",
      note: current?.note || "",
    });
  }
  if (event.type === "source.failed") {
    const url = text(data.url);
    const id = text(data.source_id) || url;
    const current = state.sources.find((item) => item.id === id);
    next.sources = mergeSource(state.sources, {
      id,
      url,
      title: current?.title || domainOf(url) || "Untitled source",
      domain: current?.domain || domainOf(url),
      subQuestionId: current?.subQuestionId || "",
      status: "failed",
      fromCache: false,
      quality: current?.quality || "",
      note: text(data.reason).replaceAll("_", " "),
    });
  }
  if (event.type === "finding.extracted") {
    next.findings = [
      ...state.findings,
      {
        id: text(data.finding_id) || `finding-${event.seq}`,
        claim: text(data.claim),
        quote: text(data.evidence_quote),
        confidence: num(data.confidence),
        stance: text(data.stance) || "supports",
        status: "accepted",
        subQuestionId: text(data.sub_question_id),
        sourceId: text(data.source_id),
        reason: "",
      },
    ];
  }
  if (event.type === "finding.rejected") {
    next.findings = [
      ...state.findings,
      {
        id: `rejected-${event.seq}`,
        claim: text(data.claim),
        quote: "",
        confidence: 0,
        stance: "context",
        status: "rejected",
        subQuestionId: text(data.sub_question_id),
        sourceId: text(data.source_id),
        reason: text(data.reason),
      },
    ];
  }
  if (event.type === "critic.review") next.review = parseReview(data) ?? state.review;
  if (event.type === "report.completed") next.report = parseReport(data) ?? state.report;
  if (event.type === "usage.updated" || event.type === "run.completed") {
    next.usage = parseUsage(data.usage) ?? state.usage;
  }
  if (event.type === "budget.warning") {
    next.warnings = [...state.warnings, { resource: text(data.resource), used: num(data.used), limit: num(data.limit) }];
  }
  if (event.type === "budget.exhausted") next.exhausted = text(data.resource) || "budget";
  if (event.type === "run.completed") next.status = "completed";
  if (event.type === "run.failed") {
    next.status = "failed";
    next.error = "The research run failed.";
    next.events = [...state.events, { ...event, data: {} }];
  }
  if (event.type === "run.cancelled") next.status = "cancelled";
  return next;
}

export type RunDetailSeed = {
  question?: string;
  depth?: string;
  status?: string;
  phase?: string | null;
  plan?: unknown;
  report?: unknown;
  usage?: unknown;
  budget?: unknown;
  error?: string | null;
  use_memory?: boolean;
};

export function mergeDetail(state: RunState, detail: RunDetailSeed): RunState {
  const hasEvents = state.events.length > 0;
  return {
    ...state,
    question: state.question || detail.question || "",
    depth: state.depth || detail.depth || "",
    status: hasEvents ? state.status : detail.status || state.status,
    phase: state.phase || detail.phase || "",
    useMemory: detail.use_memory ?? state.useMemory,
    plan: state.plan ?? parsePlan(detail.plan),
    report: state.report ?? parseReport(detail.report),
    usage: state.usage ?? parseUsage(detail.usage),
    budget: state.budget ?? parseBudget(detail.budget),
    error: state.error ?? (detail.error ? "The research run failed." : null),
  };
}
