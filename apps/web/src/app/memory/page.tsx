"use client";

import { FormEvent, useEffect, useState } from "react";

type MemoryItem = { id: string; kind: string; content: string; importance: number };

export default function MemoryPage() {
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [content, setContent] = useState("");
  const [confirm, setConfirm] = useState("");

  async function load() {
    const response = await fetch("/api/memories");
    if (!response.ok) return;
    const body = (await response.json()) as { items: MemoryItem[] };
    setItems(body.items);
  }

  useEffect(() => {
    let cancelled = false;
    void fetch("/api/memories")
      .then(async (response) => {
        if (!response.ok || cancelled) return;
        const body = (await response.json()) as { items: MemoryItem[] };
        if (!cancelled) setItems(body.items);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    await fetch("/api/memories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind: "preference", content, importance: 0.5 }),
    });
    setContent("");
    await load();
  }

  return (
    <section>
      <h1 className="text-2xl font-semibold">Memory</h1>
      <form onSubmit={onCreate} className="mt-4 flex gap-2">
        <input
          className="flex-1 rounded border px-3 py-2"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          aria-label="Memory content"
          placeholder="User prefers concise reports"
        />
        <button type="submit" className="rounded bg-zinc-900 px-3 py-2 text-white dark:bg-zinc-100 dark:text-zinc-900">
          Add
        </button>
      </form>
      <ul className="mt-4 space-y-2">
        {items.map((item) => (
          <li key={item.id} className="flex items-center justify-between rounded border p-3">
            <span>
              {item.kind}: {item.content}
            </span>
            <button type="button" onClick={() => void fetch(`/api/memories/${item.id}`, { method: "DELETE" }).then(load)}>
              Delete
            </button>
          </li>
        ))}
      </ul>
      <form
        className="mt-8 space-y-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (confirm !== "forget") return;
          void fetch("/api/memories?confirm=true", { method: "DELETE" }).then(load);
        }}
      >
        <label>
          Type forget to delete all memories
          <input className="ml-2 rounded border px-2 py-1" value={confirm} onChange={(event) => setConfirm(event.target.value)} />
        </label>
        <button type="submit" className="block rounded border px-3 py-1">
          Forget all
        </button>
      </form>
    </section>
  );
}
