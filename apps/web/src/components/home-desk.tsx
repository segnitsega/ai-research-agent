"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useState, useSyncExternalStore } from "react";
import { StatusBadge } from "@/components/status-badge";
import { ThemeButton } from "@/components/shell";
import { readApiError } from "@/lib/api-error";
import { cn, formatDuration, formatMoney, formatWhen } from "@/lib/format";
import { defaultPrefs, readPrefs, subscribePrefs, type DepthChoice } from "@/lib/prefs";

type Preset = {
  sub_questions: number;
  max_iterations: number;
  max_fetches: number;
  max_cost_usd: number;
  max_tokens: number;
  max_wall_seconds: number;
};

type PublicConfig = {
  depth_presets: Record<string, Preset>;
  server_max: Record<string, number>;
  models: Record<string, string>;
};

type RunSummary = {
  id: string;
  question: string;
  status: string;
  depth: string;
  created_at: string;
  cost_usd: number;
  accepted_findings: number;
};

const FALLBACK: Record<DepthChoice, Preset> = {
  quick: { sub_questions: 3, max_iterations: 1, max_fetches: 10, max_cost_usd: 0.25, max_tokens: 300000, max_wall_seconds: 180 },
  standard: { sub_questions: 5, max_iterations: 2, max_fetches: 30, max_cost_usd: 0.75, max_tokens: 1000000, max_wall_seconds: 420 },
  deep: { sub_questions: 8, max_iterations: 4, max_fetches: 80, max_cost_usd: 2.5, max_tokens: 3000000, max_wall_seconds: 900 },
};

const EXAMPLES = [
  "Who develops the Gemini models?",
  "What did the EU AI Act change for general-purpose models?",
  "How do researchers evaluate retrieval over long documents?",
];

const DEPTHS: { id: DepthChoice; title: string; blurb: string }[] = [
  { id: "quick", title: "Quick", blurb: "One pass over a short shelf of sources." },
  { id: "standard", title: "Standard", blurb: "A second look where the critic finds gaps." },
  { id: "deep", title: "Deep", blurb: "A longer desk session with a wider net." },
];

export function HomeDesk() {
  const router = useRouter();
  const params = useSearchParams();
  const prefs = useSyncExternalStore(subscribePrefs, readPrefs, () => defaultPrefs);
  const [question, setQuestion] = useState(params.get("question") ?? "");
  const [depth, setDepth] = useState<DepthChoice | null>(null);
  const [memory, setMemory] = useState<boolean | null>(null);
  const [advanced, setAdvanced] = useState(false);
  const [budget, setBudget] = useState({ max_cost_usd: "", max_fetches: "", max_iterations: "" });
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void fetch("/api/config")
      .then(async (response) => (response.ok ? ((await response.json()) as PublicConfig) : null))
      .then((body) => {
        if (!cancelled && body) setConfig(body);
      })
      .catch(() => undefined);
    void fetch("/api/runs?limit=5")
      .then(async (response) => (response.ok ? ((await response.json()) as { items: RunSummary[] }) : null))
      .then((body) => {
        if (!cancelled) setRuns(body?.items ?? []);
      })
      .catch(() => {
        if (!cancelled) setRuns([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const chosen = depth ?? prefs.depth;
  const useMemory = memory ?? prefs.useMemory;
  const preset = config?.depth_presets[chosen] ?? FALLBACK[chosen];
  const serverMax = config?.server_max;
  const count = question.trim().length;
  const countTone = count > 0 && count < 8 ? "text-danger" : "text-muted";

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (count < 8) {
      setError("Ask a question of at least 8 characters.");
      return;
    }
    const overrides: Record<string, number> = {};
    if (advanced) {
      if (budget.max_cost_usd) overrides.max_cost_usd = Number(budget.max_cost_usd);
      if (budget.max_fetches) overrides.max_fetches = Number(budget.max_fetches);
      if (budget.max_iterations) overrides.max_iterations = Number(budget.max_iterations);
      if (Object.values(overrides).some((value) => !Number.isFinite(value) || value <= 0)) {
        setError("Budget overrides need positive numbers.");
        return;
      }
      if (serverMax?.max_cost_usd && overrides.max_cost_usd > serverMax.max_cost_usd) {
        setError(`Cost cannot exceed $${serverMax.max_cost_usd}.`);
        return;
      }
      if (serverMax?.max_fetches && overrides.max_fetches > serverMax.max_fetches) {
        setError(`Fetches cannot exceed ${serverMax.max_fetches}.`);
        return;
      }
      if (serverMax?.max_iterations && overrides.max_iterations > serverMax.max_iterations) {
        setError(`Iterations cannot exceed ${serverMax.max_iterations}.`);
        return;
      }
    }
    setPending(true);
    try {
      const response = await fetch("/api/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question.trim(),
          depth: chosen,
          use_memory: useMemory,
          ...(Object.keys(overrides).length > 0 ? { budget: overrides } : {}),
        }),
      });
      if (!response.ok) {
        setError(await readApiError(response, "The run could not be started."));
        return;
      }
      const created = (await response.json()) as { id: string };
      router.push(`/runs/${created.id}`);
    } catch {
      setError("Could not reach the app server. Check your connection and try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-8 xl:grid-cols-[minmax(0,1.6fr)_minmax(18rem,0.8fr)]">
      <section>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="kicker">Research desk</p>
            <h1 className="mt-3 max-w-xl font-display text-4xl leading-[1.05] sm:text-5xl">Ask something worth a paper trail.</h1>
            <p className="mt-4 max-w-xl text-muted">
              Six agents plan, search, read, critique, write, and file the memory. A claim reaches the report only when its quote is still on the page.
            </p>
          </div>
          <ThemeButton />
        </div>

        <form onSubmit={onSubmit} className="sheet mt-8 p-5 sm:p-7" aria-busy={pending}>
          <label className="block" htmlFor="question">
            <span className="text-sm font-semibold">Question</span>
            <textarea
              id="question"
              className="mt-3 min-h-36 w-full resize-y bg-transparent font-display text-2xl leading-snug text-ink placeholder:text-muted/60 focus:outline-none"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="What should the desk look into?"
              maxLength={2000}
              required
              autoFocus
            />
          </label>
          <div className="flex items-center justify-between gap-3 text-sm">
            <span className={countTone}>{count} / 2000</span>
            <span className="text-muted">8 characters minimum</span>
          </div>

          <fieldset className="mt-6">
            <legend className="text-sm font-semibold">Depth</legend>
            <div className="mt-3 grid gap-3 md:grid-cols-3" role="radiogroup" aria-label="Depth">
              {DEPTHS.map((item) => {
                const itemPreset = config?.depth_presets[item.id] ?? FALLBACK[item.id];
                const selected = chosen === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    role="radio"
                    aria-checked={selected}
                    onClick={() => setDepth(item.id)}
                    className={cn(
                      "min-h-28 rounded-2xl border px-4 py-3 text-left",
                      selected ? "border-accent bg-accent-soft" : "border-line bg-paper hover:border-copper",
                    )}
                  >
                    <span className="block font-display text-2xl">{item.title}</span>
                    <span className="mt-1 block text-sm text-muted">{item.blurb}</span>
                    <span className="mt-3 block text-xs font-semibold text-ink">
                      Up to {formatDuration(itemPreset.max_wall_seconds)} · {formatMoney(itemPreset.max_cost_usd)} · {itemPreset.max_fetches} fetches
                    </span>
                  </button>
                );
              })}
            </div>
          </fieldset>

          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-line px-4 py-3">
            <div>
              <p className="text-sm font-semibold">Use memory</p>
              <p className="text-sm text-muted">Recall preferences, facts, and earlier findings for this question.</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={useMemory}
              onClick={() => setMemory(!useMemory)}
              className={cn("min-h-11 min-w-16 rounded-full px-4 text-sm font-semibold", useMemory ? "bg-accent text-accent-ink" : "bg-line text-ink")}
            >
              {useMemory ? "On" : "Off"}
            </button>
          </div>

          <details className="mt-4 rounded-2xl border border-line px-4 py-3" onToggle={(event) => setAdvanced((event.currentTarget as HTMLDetailsElement).open)}>
            <summary className="cursor-pointer text-sm font-semibold">Advanced budget</summary>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <BudgetField label="Max cost (USD)" value={budget.max_cost_usd} placeholder={String(preset.max_cost_usd)} onChange={(value) => setBudget({ ...budget, max_cost_usd: value })} />
              <BudgetField label="Max fetches" value={budget.max_fetches} placeholder={String(preset.max_fetches)} onChange={(value) => setBudget({ ...budget, max_fetches: value })} />
              <BudgetField label="Max iterations" value={budget.max_iterations} placeholder={String(preset.max_iterations)} onChange={(value) => setBudget({ ...budget, max_iterations: value })} />
            </div>
            <p className="mt-3 text-xs text-muted">Leave a field blank to keep the {chosen} preset. The server still enforces its own ceiling.</p>
          </details>

          {error ? (
            <p className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger" role="alert">
              {error}
            </p>
          ) : null}

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button type="submit" className="min-h-11 rounded-full bg-accent px-6 text-sm font-semibold text-accent-ink disabled:opacity-60" disabled={pending}>
              {pending ? "Opening the desk…" : "Start research"}
            </button>
            <p className="text-sm text-muted">
              {preset.sub_questions} sub-questions · {preset.max_iterations} {preset.max_iterations === 1 ? "iteration" : "iterations"}
            </p>
          </div>
        </form>

        <div className="mt-5 flex flex-wrap gap-2">
          {EXAMPLES.map((example) => (
            <button key={example} type="button" className="min-h-11 rounded-full border border-line bg-raised px-4 text-left text-sm hover:border-copper" onClick={() => setQuestion(example)}>
              {example}
            </button>
          ))}
        </div>
      </section>

      <aside className="space-y-6">
        <section className="sheet p-5">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="font-display text-2xl">On the desk</h2>
            <Link href="/runs" className="text-sm font-semibold text-accent">
              All runs
            </Link>
          </div>
          {runs === null ? <p className="mt-4 text-sm text-muted">Looking through recent runs…</p> : null}
          {runs && runs.length === 0 ? <p className="mt-4 text-sm text-muted">Nothing filed yet. The first question will land here.</p> : null}
          <ul className="mt-4 divide-y divide-line">
            {(runs ?? []).map((run) => (
              <li key={run.id} className="py-4">
                <Link href={`/runs/${run.id}`} className="font-display text-xl leading-snug hover:text-accent">
                  {run.question}
                </Link>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
                  <StatusBadge status={run.status} />
                  <span>{run.depth}</span>
                  <span>{formatMoney(run.cost_usd)}</span>
                  <span>{run.accepted_findings} findings</span>
                  <span>{formatWhen(run.created_at)}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-3xl border border-dashed border-line px-5 py-5">
          <h2 className="font-display text-2xl">How a run moves</h2>
          <ol className="mt-4 space-y-3 text-sm">
            {[
              ["01", "Recall", "Earlier notes come back if memory is on."],
              ["02", "Plan", "The question splits into sub-questions."],
              ["03", "Search and read", "Pages are fetched, then quoted."],
              ["04", "Critique", "Gaps send the desk around again."],
              ["05", "Write", "The report cites only checked quotes."],
              ["06", "Memorize", "A short episode is filed for next time."],
            ].map(([index, title, copy]) => (
              <li key={index} className="grid grid-cols-[2.5rem_1fr] gap-2">
                <span className="font-display text-copper">{index}</span>
                <span>
                  <span className="font-semibold">{title}</span>
                  <span className="mt-0.5 block text-muted">{copy}</span>
                </span>
              </li>
            ))}
          </ol>
        </section>
      </aside>
    </div>
  );
}

function BudgetField({ label, value, placeholder, onChange }: { label: string; value: string; placeholder: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm">
      <span className="font-semibold">{label}</span>
      <input
        inputMode="decimal"
        className="mt-1 min-h-11 w-full rounded-xl border border-line bg-paper px-3"
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
