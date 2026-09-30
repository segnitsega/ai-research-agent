export type RunEvent = {
  seq: number;
  type: string;
  agent?: string;
  data: Record<string, unknown>;
};

export type RunState = {
  events: RunEvent[];
  status: string;
  plan: Record<string, unknown> | null;
  findings: Record<string, unknown>[];
  report: Record<string, unknown> | null;
  usage: Record<string, unknown> | null;
  error: string | null;
};

export function emptyRunState(): RunState {
  return { events: [], status: "queued", plan: null, findings: [], report: null, usage: null, error: null };
}

export function reduce(state: RunState, event: RunEvent): RunState {
  if (state.events.some((item) => item.seq === event.seq)) return state;
  const events = [...state.events, event];
  const next = { ...state, events };
  if (event.type === "plan.created") next.plan = event.data.plan as Record<string, unknown>;
  if (event.type === "finding.extracted") next.findings = [...state.findings, event.data];
  if (event.type === "report.completed") next.report = event.data.report as Record<string, unknown>;
  if (event.type === "usage.updated" || event.type === "run.completed") {
    next.usage = (event.data.usage as Record<string, unknown>) ?? state.usage;
  }
  if (event.type === "run.completed") next.status = "completed";
  if (event.type === "run.failed") {
    next.status = "failed";
    next.error = String(event.data.message ?? "Run failed");
  }
  if (event.type === "run.cancelled") next.status = "cancelled";
  if (event.type === "run.started") next.status = "running";
  return next;
}
