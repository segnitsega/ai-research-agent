"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/status-badge";
import { cn, formatMoney, formatWhen } from "@/lib/format";

type RunSummary = {
  id: string;
  question: string;
  status: string;
  depth: string;
  created_at: string;
  cost_usd: number;
  accepted_findings: number;
  sources_used: number;
};

const FILTERS = ["all", "queued", "running", "completed", "failed", "cancelled"] as const;

export function RunsIndex() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");
  const [items, setItems] = useState<RunSummary[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const query = new URLSearchParams({ limit: "20" });
    if (filter !== "all") query.set("status", filter);
    void fetch(`/api/runs?${query.toString()}`)
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load runs");
        return (await response.json()) as { items: RunSummary[]; next_cursor: string | null };
      })
      .then((body) => {
        if (cancelled) return;
        setItems(body.items);
        setCursor(body.next_cursor);
        setError("");
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Could not load runs");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filter]);

  async function loadMore() {
    if (!cursor) return;
    const query = new URLSearchParams({ limit: "20", cursor });
    if (filter !== "all") query.set("status", filter);
    const response = await fetch(`/api/runs?${query.toString()}`);
    if (!response.ok) return;
    const body = (await response.json()) as { items: RunSummary[]; next_cursor: string | null };
    setItems((current) => [...current, ...body.items]);
    setCursor(body.next_cursor);
  }

  return (
    <div className="mx-auto max-w-5xl">
      <p className="kicker">Archive</p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
        <h1 className="font-display text-4xl sm:text-5xl">Run history</h1>
        <Link href="/" className="min-h-11 rounded-full bg-accent px-5 py-2 text-sm font-semibold text-accent-ink">
          New research
        </Link>
      </div>
      <div className="mt-6 flex flex-wrap gap-2" role="radiogroup" aria-label="Filter by status">
        {FILTERS.map((item) => (
          <button
            key={item}
            type="button"
            role="radio"
            aria-checked={filter === item}
            className={cn("min-h-11 rounded-full px-4 text-sm font-semibold capitalize", filter === item ? "bg-ink text-paper" : "bg-raised text-muted")}
            onClick={() => {
              if (item !== filter) setLoading(true);
              setFilter(item);
            }}
          >
            {item}
          </button>
        ))}
      </div>
      {error ? (
        <p className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger" role="alert">
          {error}
        </p>
      ) : null}
      <section className="sheet mt-5 overflow-hidden">
        {loading ? <p className="px-5 py-8 text-sm text-muted">Pulling the archive…</p> : null}
        {!loading && items.length === 0 ? (
          <div className="px-5 py-12">
            <h2 className="font-display text-3xl">No runs in this drawer.</h2>
            <p className="mt-2 max-w-md text-sm text-muted">Start a question on the desk and it will be filed here with its cost, sources, and findings.</p>
          </div>
        ) : null}
        <ul>
          {items.map((item) => (
            <li key={item.id} className="border-t border-line px-5 py-5 first:border-t-0">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={item.status} />
                <span className="text-xs uppercase tracking-wide text-muted">{item.depth}</span>
                <span className="text-xs text-muted">{formatWhen(item.created_at)}</span>
              </div>
              <Link href={`/runs/${item.id}`} className="mt-2 block font-display text-2xl leading-snug hover:text-accent">
                {item.question}
              </Link>
              <p className="mt-2 text-sm text-muted">
                {formatMoney(item.cost_usd)} · {item.accepted_findings} findings · {item.sources_used} sources
              </p>
            </li>
          ))}
        </ul>
      </section>
      {cursor ? (
        <button type="button" className="mt-4 min-h-11 rounded-full border border-line px-5 text-sm font-semibold" onClick={() => void loadMore()}>
          Load more
        </button>
      ) : null}
    </div>
  );
}
