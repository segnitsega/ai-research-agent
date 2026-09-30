"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export default function HomePage() {
  const router = useRouter();
  const [question, setQuestion] = useState("Who develops the Gemini models?");
  const [depth, setDepth] = useState("quick");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (question.trim().length < 8) {
      setError("Ask a question of at least 8 characters.");
      return;
    }
    setPending(true);
    const response = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, depth, use_memory: true }),
    });
    setPending(false);
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail || "The run could not be started.");
      return;
    }
    const created = (await response.json()) as { id: string };
    router.push(`/runs/${created.id}`);
  }

  return (
    <section>
      <h1 className="text-3xl font-semibold">Ask a research question</h1>
      <p className="mt-2 max-w-2xl text-zinc-600 dark:text-zinc-300">
        Planner, searcher, reader, critic, writer, and curator run on Gemini. Quotes are checked against the source
        before they can be cited.
      </p>
      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        <label className="block">
          <span className="text-sm font-medium">Question</span>
          <textarea
            className="mt-1 w-full rounded border border-zinc-300 bg-transparent p-3 dark:border-zinc-700"
            rows={4}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            required
            minLength={8}
            maxLength={2000}
          />
        </label>
        <label className="block">
          <span className="text-sm font-medium">Depth</span>
          <select
            className="mt-1 rounded border border-zinc-300 bg-transparent px-3 py-2 dark:border-zinc-700"
            value={depth}
            onChange={(event) => setDepth(event.target.value)}
          >
            <option value="quick">Quick</option>
            <option value="standard">Standard</option>
            <option value="deep">Deep</option>
          </select>
        </label>
        {error ? <p className="text-red-700">{error}</p> : null}
        <button type="submit" className="rounded bg-zinc-900 px-4 py-2 text-white dark:bg-zinc-100 dark:text-zinc-900" disabled={pending}>
          {pending ? "Starting" : "Start research"}
        </button>
      </form>
    </section>
  );
}
