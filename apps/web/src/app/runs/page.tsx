"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type RunSummary = {
  id: string;
  question: string;
  status: string;
  depth: string;
  cost_usd: number;
};

export default function RunsPage() {
  const [items, setItems] = useState<RunSummary[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void fetch("/api/runs")
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not load runs");
        return (await response.json()) as { items: RunSummary[] };
      })
      .then((body) => setItems(body.items))
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load runs"));
  }, []);

  return (
    <section>
      <h1 className="text-2xl font-semibold">Run history</h1>
      {error ? <p className="mt-4 text-red-700">{error}</p> : null}
      {items.length === 0 ? <p className="mt-4">No runs yet.</p> : null}
      <ul className="mt-4 space-y-3">
        {items.map((item) => (
          <li key={item.id} className="rounded border border-zinc-200 p-3 dark:border-zinc-800">
            <Link href={`/runs/${item.id}`} className="font-medium underline-offset-4 hover:underline">
              {item.question}
            </Link>
            <p className="text-sm text-zinc-600 dark:text-zinc-300">
              {item.status} · {item.depth} · ${item.cost_usd.toFixed(4)}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
