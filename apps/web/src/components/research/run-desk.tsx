"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { MarkdownBody } from "@/components/markdown-body";
import { Inspector } from "@/components/research/inspector";
import { ActivityTimeline, PhaseStepper } from "@/components/research/timeline";
import { StatusBadge } from "@/components/status-badge";
import { cn, formatMoney, slugify } from "@/lib/format";
import { reportMarkdown } from "@/lib/markdown";
import { emptyRunState, mergeDetail, reduce, type CitationView, type FindingView, type RunDetailSeed, type RunEvent, type SourceView } from "@/lib/reduce";

const EVENT_TYPES = [
  "run.started",
  "memory.recalled",
  "plan.created",
  "iteration.started",
  "search.started",
  "source.found",
  "source.fetched",
  "source.failed",
  "finding.extracted",
  "finding.rejected",
  "critic.review",
  "iteration.completed",
  "report.started",
  "report.completed",
  "memory.updated",
  "usage.updated",
  "budget.warning",
  "budget.exhausted",
  "run.completed",
  "run.failed",
  "run.cancelled",
];

type Tab = "report" | "plan" | "sources" | "findings";
type Pane = "activity" | "work" | "inspect";
type Selection = { kind: "citation"; n: number } | { kind: "source"; id: string } | { kind: "finding"; id: string };

export function RunDesk({ id }: { id: string }) {
  const [state, setState] = useState(emptyRunState);
  const [missing, setMissing] = useState(false);
  const [tab, setTab] = useState<Tab>("report");
  const [pane, setPane] = useState<Pane>("work");
  const [selection, setSelection] = useState<Selection | null>(null);
  const [showRejected, setShowRejected] = useState(false);
  const [sourceFilter, setSourceFilter] = useState<"all" | "fetched" | "failed">("all");
  const [connection, setConnection] = useState<"connecting" | "live" | "reconnecting">("connecting");
  const [attempt, setAttempt] = useState(0);
  const [copied, setCopied] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [flagged, setFlagged] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let cancelled = false;
    void fetch(`/api/runs/${id}`)
      .then(async (response) => {
        if (response.status === 404) {
          if (!cancelled) setMissing(true);
          return null;
        }
        if (!response.ok) return null;
        return (await response.json()) as RunDetailSeed;
      })
      .then((detail) => {
        if (!cancelled && detail) setState((current) => mergeDetail(current, detail));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    const source = new EventSource(`/api/runs/${id}/events`);
    const onEvent = (message: Event) => {
      if (!(message instanceof MessageEvent)) return;
      try {
        const parsed = JSON.parse(message.data) as RunEvent;
        if (typeof parsed.seq !== "number" || typeof parsed.type !== "string") return;
        const nextEvent = { ...parsed, data: parsed.data ?? {} };
        setState((current) => reduce(current, nextEvent));
        setConnection("live");
        if (parsed.type === "run.completed" || parsed.type === "run.failed" || parsed.type === "run.cancelled") source.close();
      } catch {
        return;
      }
    };
    for (const type of EVENT_TYPES) source.addEventListener(type, onEvent);
    source.onerror = () => setConnection("reconnecting");
    return () => source.close();
  }, [id, attempt]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setSelection(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const terminal = state.status === "completed" || state.status === "failed" || state.status === "cancelled";
  const accepted = state.findings.filter((item) => item.status !== "rejected");
  const rejected = state.findings.filter((item) => item.status === "rejected");
  const citation = selection?.kind === "citation" ? state.report?.citations.find((item) => item.n === selection.n) ?? null : null;
  const selectedFinding = selection?.kind === "finding" ? state.findings.find((item) => item.id === selection.id) ?? null : null;
  const selectedSource = useMemo(() => resolveSource(selection, citation ?? null, selectedFinding, state.sources), [selection, citation, selectedFinding, state.sources]);

  function chooseCitation(n: number) {
    setSelection({ kind: "citation", n });
    setPane("inspect");
  }

  async function copyReport() {
    if (!state.report) return;
    await navigator.clipboard.writeText(reportMarkdown(state.report));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  function downloadReport() {
    if (!state.report) return;
    const blob = new Blob([reportMarkdown(state.report)], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${slugify(state.report.title)}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function flagFinding(findingId: string) {
    const response = await fetch(`/api/runs/${id}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ flagged_finding_ids: [findingId], comment: "Flagged from the desk" }),
    });
    if (response.ok) setFlagged((current) => ({ ...current, [findingId]: true }));
  }

  if (missing && state.events.length === 0) {
    return (
      <section className="mx-auto max-w-xl py-16 text-center">
        <p className="kicker">Missing run</p>
        <h1 className="mt-3 font-display text-4xl">This run is not on the desk.</h1>
        <Link href="/" className="mt-6 inline-flex min-h-11 items-center font-semibold text-accent">
          Ask a new question
        </Link>
      </section>
    );
  }

  const sources = state.sources.filter((item) => sourceFilter === "all" || item.status === sourceFilter);

  return (
    <div className="mx-auto max-w-[88rem]">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 max-w-3xl">
          <p className="kicker">{state.depth || "Research"} run</p>
          <h1 className="mt-2 font-display text-3xl leading-tight sm:text-4xl">{state.question || "Opening the run…"}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <StatusBadge status={state.status} />
            <span className="text-sm text-muted">{formatMoney(state.usage?.costUsd ?? 0)}</span>
            <span className="text-sm text-muted">{accepted.length} findings</span>
            <span className="text-sm text-muted">{state.sources.length} sources</span>
            <ConnectionPill terminal={terminal} connection={connection} onReconnect={() => setAttempt((value) => value + 1)} />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {terminal ? null : (
            <button
              type="button"
              className="min-h-11 rounded-full border border-line px-4 text-sm font-semibold"
              disabled={cancelling}
              onClick={() => {
                setCancelling(true);
                void fetch(`/api/runs/${id}/cancel`, { method: "POST" }).finally(() => setCancelling(false));
              }}
            >
              {cancelling ? "Cancelling…" : "Cancel run"}
            </button>
          )}
          <button type="button" className="min-h-11 rounded-full border border-line px-4 text-sm font-semibold disabled:opacity-50" disabled={!state.report} onClick={() => void copyReport()}>
            {copied ? "Copied" : "Copy Markdown"}
          </button>
          <button type="button" className="min-h-11 rounded-full bg-ink px-4 text-sm font-semibold text-paper disabled:opacity-50" disabled={!state.report} onClick={downloadReport}>
            Download .md
          </button>
        </div>
      </header>

      {state.error ? (
        <div className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger" role="alert">
          <p>{state.error}</p>
          <Link className="mt-2 inline-flex min-h-11 items-center font-semibold" href={`/?question=${encodeURIComponent(state.question)}`}>
            Retry as a new run
          </Link>
        </div>
      ) : null}
      {state.status === "cancelled" ? (
        <p className="mt-4 rounded-2xl bg-copper-soft px-4 py-3 text-sm text-copper">This run was cancelled. You can start it again from the desk.</p>
      ) : null}
      {state.exhausted ? <p className="mt-4 rounded-2xl bg-warn-soft px-4 py-3 text-sm text-warn">The {state.exhausted} budget was used up. The writer is working with the evidence already on the desk.</p> : null}

      <div className="mt-5 xl:hidden">
        <div className="grid grid-cols-3 gap-2" role="tablist" aria-label="Run regions">
          {(["activity", "work", "inspect"] as const).map((item) => (
            <button key={item} type="button" role="tab" aria-selected={pane === item} className={cn("min-h-11 rounded-full text-sm font-semibold", pane === item ? "bg-ink text-paper" : "bg-raised text-muted")} onClick={() => setPane(item)}>
              {item === "activity" ? "Activity" : item === "work" ? "Work" : "Inspector"}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[17rem_minmax(0,1fr)_20rem]">
        <div className={cn(pane === "activity" ? "block" : "hidden", "xl:block")}>
          <ActivityTimeline events={state.events} />
        </div>
        <section className={cn(pane === "work" ? "block" : "hidden", "min-w-0 xl:block")} aria-label="Research work">
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Research sections">
            {(
              [
                ["report", "Report"],
                ["plan", "Plan"],
                ["sources", "Sources"],
                ["findings", "Findings"],
              ] as const
            ).map(([item, label]) => (
              <button key={item} type="button" role="tab" aria-selected={tab === item} className={cn("min-h-11 rounded-full px-4 text-sm font-semibold", tab === item ? "bg-accent text-accent-ink" : "bg-raised text-muted")} onClick={() => setTab(item)}>
                {label}
              </button>
            ))}
          </div>
          <div className="mt-4">
            {tab === "report" ? (
              <ReportPane statePhase={state.phase} status={state.status} report={state.report} iteration={state.iteration} sources={state.sources.length} findings={accepted.length} onCite={chooseCitation} />
            ) : null}
            {tab === "plan" ? <PlanPane plan={state.plan} coverage={state.review?.coverage ?? {}} verdict={state.review?.verdict ?? ""} rationale={state.review?.rationale ?? ""} /> : null}
            {tab === "sources" ? (
              <SourcesPane
                sources={sources}
                filter={sourceFilter}
                findings={state.findings}
                onFilter={setSourceFilter}
                onOpen={(sourceId) => {
                  setSelection({ kind: "source", id: sourceId });
                  setPane("inspect");
                }}
              />
            ) : null}
            {tab === "findings" ? (
              <FindingsPane
                plan={state.plan}
                findings={showRejected ? state.findings : accepted}
                rejectedCount={rejected.length}
                showRejected={showRejected}
                flagged={flagged}
                onToggleRejected={() => setShowRejected((value) => !value)}
                onOpen={(findingId) => {
                  setSelection({ kind: "finding", id: findingId });
                  setPane("inspect");
                }}
                onFlag={(findingId) => void flagFinding(findingId)}
              />
            ) : null}
          </div>
        </section>
        <div className={cn(pane === "inspect" ? "block" : "hidden", "xl:block")}>
          <Inspector
            citation={citation}
            finding={selectedFinding}
            source={selectedSource}
            findings={state.findings}
            usage={state.usage}
            budget={state.budget}
            warnings={state.warnings}
            onClose={() => setSelection(null)}
          />
        </div>
      </div>
    </div>
  );
}

function ConnectionPill({ terminal, connection, onReconnect }: { terminal: boolean; connection: "connecting" | "live" | "reconnecting"; onReconnect: () => void }) {
  if (terminal) return <span className="text-sm text-muted">Stream closed</span>;
  if (connection === "connecting") return <span className="text-sm text-muted">Connecting</span>;
  if (connection === "live") return <span className="text-sm font-semibold text-ok">Live</span>;
  return (
    <button type="button" className="text-sm font-semibold text-warn" onClick={onReconnect}>
      Connection lost. Reconnect
    </button>
  );
}

function resolveSource(selection: Selection | null, citation: CitationView | null, finding: FindingView | null, sources: SourceView[]): SourceView | null {
  const id = selection?.kind === "source" ? selection.id : citation?.sourceId || finding?.sourceId || "";
  if (!id) return null;
  return sources.find((item) => item.id === id) ?? null;
}

function ReportPane({
  statePhase,
  status,
  report,
  iteration,
  sources,
  findings,
  onCite,
}: {
  statePhase: string;
  status: string;
  report: ReturnType<typeof emptyRunState>["report"];
  iteration: number;
  sources: number;
  findings: number;
  onCite: (n: number) => void;
}) {
  if (!report) {
    return (
      <div className="sheet p-5">
        <p className="kicker">In progress</p>
        <h2 className="mt-2 font-display text-3xl">The report is still being made.</h2>
        <p className="mt-2 text-sm text-muted">
          Iteration {iteration || 1} · {sources} sources · {findings} accepted findings
        </p>
        <div className="mt-5">
          <PhaseStepper phase={statePhase} status={status} />
        </div>
      </div>
    );
  }
  return (
    <article className="sheet px-5 py-6 sm:px-8">
      <p className="kicker">Report</p>
      <h2 className="mt-2 max-w-[22ch] font-display text-4xl leading-tight">{report.title}</h2>
      <p className="mt-4 max-w-[68ch] text-lg leading-8 text-ink">{report.executiveSummary}</p>
      <div className="mt-8 max-w-[68ch] space-y-8 font-display text-[1.12rem] leading-8">
        {report.sections.map((section) => (
          <section key={section.heading}>
            <h3 className="font-display text-2xl">{section.heading}</h3>
            <div className="mt-3 font-sans text-base leading-7">
              <MarkdownBody text={section.body} onCite={onCite} />
            </div>
          </section>
        ))}
      </div>
      {report.limitations.length > 0 ? (
        <section className="mt-8 max-w-[68ch]">
          <h3 className="font-display text-2xl">Limitations</h3>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-muted">
            {report.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </article>
  );
}

function PlanPane({
  plan,
  coverage,
  verdict,
  rationale,
}: {
  plan: ReturnType<typeof emptyRunState>["plan"];
  coverage: Record<string, string>;
  verdict: string;
  rationale: string;
}) {
  if (!plan) return <p className="text-sm text-muted">The planner has not filed a plan yet.</p>;
  return (
    <div className="sheet p-5 sm:p-6">
      <p className="kicker">Objective</p>
      <h2 className="mt-2 font-display text-3xl leading-tight">{plan.objective}</h2>
      {verdict ? <p className="mt-3 text-sm font-semibold">Latest critic verdict: {verdict.replaceAll("_", " ")}</p> : null}
      {rationale ? <p className="mt-2 max-w-[68ch] text-sm leading-6 text-muted">{rationale}</p> : null}
      <ol className="mt-6 space-y-3">
        {plan.subQuestions.map((item, index) => (
          <li key={item.id || item.question} className="rounded-2xl border border-line px-4 py-3">
            <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted">
              <span>Q{index + 1}</span>
              <span>Priority {item.priority}</span>
              <CoverageChip value={coverage[item.id]} />
            </div>
            <p className="mt-1 font-display text-xl">{item.question}</p>
            {item.rationale ? <p className="mt-1 text-sm text-muted">{item.rationale}</p> : null}
          </li>
        ))}
      </ol>
      {plan.successCriteria.length > 0 ? (
        <section className="mt-6">
          <h3 className="text-sm font-semibold">Success criteria</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
            {plan.successCriteria.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function CoverageChip({ value }: { value?: string }) {
  if (!value) return <span>Coverage none yet</span>;
  return <span>Coverage {value}</span>;
}

function SourcesPane({
  sources,
  filter,
  findings,
  onFilter,
  onOpen,
}: {
  sources: SourceView[];
  filter: "all" | "fetched" | "failed";
  findings: FindingView[];
  onFilter: (filter: "all" | "fetched" | "failed") => void;
  onOpen: (id: string) => void;
}) {
  return (
    <div>
      <div className="mb-3 flex gap-2">
        {(["all", "fetched", "failed"] as const).map((item) => (
          <button key={item} type="button" className={cn("min-h-11 rounded-full px-4 text-sm font-semibold", filter === item ? "bg-ink text-paper" : "bg-raised")} onClick={() => onFilter(item)}>
            {item === "all" ? "All" : item === "fetched" ? "Fetched" : "Failed"}
          </button>
        ))}
      </div>
      {sources.length === 0 ? <p className="text-sm text-muted">No sources in this view yet.</p> : null}
      <div className="overflow-x-auto rounded-3xl border border-line">
        <table className="w-full min-w-[40rem] text-left text-sm">
          <thead className="bg-raised text-xs uppercase tracking-wide text-muted">
            <tr>
              <th className="px-4 py-3 font-semibold">Source</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              <th className="px-4 py-3 font-semibold">Quality</th>
              <th className="px-4 py-3 font-semibold">Findings</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.id} className="border-t border-line">
                <td className="px-4 py-3">
                  <button type="button" className="text-left font-semibold hover:text-accent" onClick={() => onOpen(source.id)}>
                    {source.title}
                  </button>
                  <span className="mt-1 block text-xs text-muted">
                    {source.domain}
                    {source.fromCache ? " · cache" : ""}
                  </span>
                </td>
                <td className="px-4 py-3 capitalize">{source.status}</td>
                <td className="px-4 py-3 capitalize">{source.quality || "—"}</td>
                <td className="px-4 py-3">{findings.filter((item) => item.sourceId === source.id && item.status !== "rejected").length}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FindingsPane({
  plan,
  findings,
  rejectedCount,
  showRejected,
  flagged,
  onToggleRejected,
  onOpen,
  onFlag,
}: {
  plan: ReturnType<typeof emptyRunState>["plan"];
  findings: FindingView[];
  rejectedCount: number;
  showRejected: boolean;
  flagged: Record<string, boolean>;
  onToggleRejected: () => void;
  onOpen: (id: string) => void;
  onFlag: (id: string) => void;
}) {
  const groups = new Map<string, FindingView[]>();
  for (const finding of findings) {
    const key = finding.subQuestionId || "ungrouped";
    groups.set(key, [...(groups.get(key) ?? []), finding]);
  }
  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-sm text-muted">{rejectedCount} rejected by the quote check</p>
        <button type="button" className="min-h-11 text-sm font-semibold text-accent" onClick={onToggleRejected}>
          {showRejected ? "Hide rejected" : "Show rejected"}
        </button>
      </div>
      {[...groups.entries()].map(([key, items]) => {
        const question = plan?.subQuestions.find((item) => item.id === key)?.question;
        return (
          <section key={key} className="mb-4">
            <h3 className="font-display text-2xl">{question || "Other findings"}</h3>
            <ul className="mt-3 space-y-3">
              {items.map((finding) => (
                <li key={finding.id} className="rounded-3xl border border-line bg-raised p-4">
                  <button type="button" className="text-left font-display text-xl leading-snug hover:text-accent" onClick={() => onOpen(finding.id)}>
                    {finding.claim || "Rejected finding"}
                  </button>
                  {finding.quote ? <blockquote className="mt-3 border-l-2 border-copper pl-3 text-sm leading-6">“{finding.quote}”</blockquote> : null}
                  <div className="mt-3 flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-wide text-muted">
                    <span>{finding.stance}</span>
                    <span>{finding.status}</span>
                    <span className="normal-case tracking-normal">{Math.round(finding.confidence * 100)}% confidence</span>
                  </div>
                  <div className="meter mt-2 max-w-xs" data-tone={finding.confidence < 0.4 ? "warn" : "ok"} aria-hidden>
                    <span style={{ width: `${Math.round(finding.confidence * 100)}%` }} />
                  </div>
                  {finding.status === "accepted" ? (
                    <button type="button" className="mt-3 min-h-11 text-sm font-semibold text-copper" onClick={() => onFlag(finding.id)} disabled={flagged[finding.id]}>
                      {flagged[finding.id] ? "Flagged" : "Flag as wrong"}
                    </button>
                  ) : null}
                  {finding.reason ? <p className="mt-2 text-sm text-danger">{finding.reason.replaceAll("_", " ")}</p> : null}
                </li>
              ))}
            </ul>
          </section>
        );
      })}
      {findings.length === 0 ? <p className="text-sm text-muted">No findings in this view yet.</p> : null}
    </div>
  );
}
