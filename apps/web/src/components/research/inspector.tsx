"use client";

import { formatCount, formatMoney, toneForRatio } from "@/lib/format";
import type { BudgetView, CitationView, FindingView, SourceView, UsageView } from "@/lib/reduce";

export function Inspector({
  citation,
  finding,
  source,
  findings,
  usage,
  budget,
  warnings,
  onClose,
}: {
  citation: CitationView | null;
  finding: FindingView | null;
  source: SourceView | null;
  findings: FindingView[];
  usage: UsageView | null;
  budget: BudgetView | null;
  warnings: { resource: string; used: number; limit: number }[];
  onClose: () => void;
}) {
  const related = citation ? findings.filter((item) => citation.findingIds.includes(item.id)) : finding ? [finding] : [];
  const activeSource = source;

  return (
    <aside className="flex min-h-0 flex-col gap-4" aria-label="Inspector">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-display text-2xl">Inspector</h2>
        {citation || finding || source ? (
          <button type="button" className="text-sm font-semibold text-muted" onClick={onClose}>
            Close
          </button>
        ) : null}
      </div>
      <div className="rounded-3xl border border-line bg-paper/70 p-4">
        {!citation && !finding && !source ? (
          <p className="text-sm leading-6 text-muted">Select a citation, finding, or source. The quote, the page, and the budget stay in this margin.</p>
        ) : (
          <div className="space-y-4">
            {citation ? <p className="kicker">Citation {citation.n}</p> : null}
            {related.map((item) => (
              <article key={item.id}>
                <p className="font-display text-xl leading-snug">{item.claim || "Rejected finding"}</p>
                {item.quote ? <blockquote className="mt-3 border-l-2 border-copper pl-3 text-sm leading-6">“{item.quote}”</blockquote> : null}
                <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-muted">
                  {item.stance} · {Math.round(item.confidence * 100)}% confidence
                  {item.status !== "accepted" ? ` · ${item.status}` : ""}
                </p>
                {item.reason ? <p className="mt-2 text-sm text-danger">{item.reason.replaceAll("_", " ")}</p> : null}
              </article>
            ))}
            {activeSource ? (
              <div className="border-t border-line pt-3 text-sm">
                <p className="font-semibold">{activeSource.title}</p>
                <p className="text-muted">{activeSource.domain}</p>
                <p className="mt-1 text-xs uppercase tracking-wide text-muted">
                  {activeSource.status}
                  {activeSource.fromCache ? " · from cache" : ""}
                  {activeSource.quality ? ` · ${activeSource.quality} expected quality` : ""}
                </p>
                {activeSource.url ? (
                  <a className="mt-3 inline-flex min-h-11 items-center font-semibold text-accent" href={activeSource.url} target="_blank" rel="noopener noreferrer">
                    Open source
                  </a>
                ) : null}
              </div>
            ) : null}
          </div>
        )}
      </div>
      <BudgetMeters usage={usage} budget={budget} warnings={warnings} />
    </aside>
  );
}

function BudgetMeters({
  usage,
  budget,
  warnings,
}: {
  usage: UsageView | null;
  budget: BudgetView | null;
  warnings: { resource: string; used: number; limit: number }[];
}) {
  const cost = usage?.costUsd ?? 0;
  const fetches = usage?.fetches ?? 0;
  const tokens = (usage?.inputTokens ?? 0) + (usage?.outputTokens ?? 0);
  return (
    <section className="rounded-3xl border border-line bg-raised p-4" aria-label="Budget">
      <h3 className="text-sm font-semibold">Budget</h3>
      <div className="mt-3 space-y-3">
        <Meter label="Cost" usedLabel={formatMoney(cost)} limitLabel={budget ? formatMoney(budget.maxCostUsd) : "—"} ratio={budget ? cost / budget.maxCostUsd : 0} />
        <Meter label="Fetches" usedLabel={formatCount(fetches)} limitLabel={budget ? formatCount(budget.maxFetches) : "—"} ratio={budget ? fetches / budget.maxFetches : 0} />
        <Meter label="Tokens" usedLabel={formatCount(tokens)} limitLabel={budget ? formatCount(budget.maxTokens) : "—"} ratio={budget ? tokens / budget.maxTokens : 0} />
      </div>
      {warnings.length > 0 ? (
        <ul className="mt-3 space-y-1 text-xs text-warn">
          {warnings.map((warning) => (
            <li key={`${warning.resource}-${warning.used}`}>
              {warning.resource} {formatCount(warning.used)} / {formatCount(warning.limit)}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function Meter({ label, usedLabel, limitLabel, ratio }: { label: string; usedLabel: string; limitLabel: string; ratio: number }) {
  const safe = Number.isFinite(ratio) ? Math.max(0, ratio) : 0;
  const tone = toneForRatio(safe);
  const width = `${Math.min(100, safe * 100)}%`;
  return (
    <div>
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="font-semibold">{label}</span>
        <span>
          {usedLabel} / {limitLabel}
          {tone === "danger" ? " · over the line" : tone === "warn" ? " · getting close" : ""}
        </span>
      </div>
      <div className="meter mt-1" data-tone={tone} role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(Math.min(100, safe * 100))}>
        <span style={{ width }} />
      </div>
    </div>
  );
}
