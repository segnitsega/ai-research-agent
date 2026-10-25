"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { cn, formatWhen } from "@/lib/format";

type MemoryItem = {
  id: string;
  kind: string;
  content: string;
  importance: number;
  source_run_id: string | null;
  created_at: string;
  updated_at: string;
};

const KINDS = ["preference", "fact", "episode"] as const;

export function MemoryDesk() {
  const [kind, setKind] = useState<(typeof KINDS)[number]>("preference");
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [content, setContent] = useState("");
  const [importance, setImportance] = useState(0.5);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [forgetOpen, setForgetOpen] = useState(false);
  const [confirm, setConfirm] = useState("");

  async function load(nextKind = kind) {
    const response = await fetch(`/api/memories?kind=${nextKind}&limit=100`);
    if (!response.ok) {
      setError("Memory could not be loaded.");
      return;
    }
    const body = (await response.json()) as { items: MemoryItem[] };
    setItems(body.items);
    setSearching(false);
    setError("");
  }

  useEffect(() => {
    let cancelled = false;
    void fetch(`/api/memories?kind=${kind}&limit=100`)
      .then(async (response) => {
        if (!response.ok || cancelled) return null;
        return (await response.json()) as { items: MemoryItem[] };
      })
      .then((body) => {
        if (!cancelled && body) setItems(body.items);
      })
      .catch(() => {
        if (!cancelled) setError("Memory could not be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, [kind]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setError("");
    const response = await fetch("/api/memories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kind, content: content.trim(), importance }),
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      setError(body?.detail || "That memory could not be saved.");
      return;
    }
    setContent("");
    await load();
  }

  async function onSearch(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) {
      await load();
      return;
    }
    const response = await fetch(`/api/memories/search?q=${encodeURIComponent(query.trim())}`);
    if (!response.ok) {
      setError("Search failed.");
      return;
    }
    setItems((await response.json()) as MemoryItem[]);
    setSearching(true);
  }

  return (
    <div className="mx-auto max-w-4xl">
      <p className="kicker">Memory</p>
      <h1 className="mt-2 font-display text-4xl sm:text-5xl">What the desk keeps.</h1>
      <p className="mt-4 max-w-2xl text-muted">
        Preferences and facts can be written here. Episodes are filed by the curator at the end of a run. Memory is recalled only when a new run has “Use memory” turned on, and you can wipe it from this page.
      </p>

      <div className="mt-6 flex flex-wrap gap-2" role="tablist" aria-label="Memory kinds">
        {KINDS.map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            aria-selected={kind === item}
            className={cn("min-h-11 rounded-full px-4 text-sm font-semibold capitalize", kind === item ? "bg-ink text-paper" : "bg-raised text-muted")}
            onClick={() => {
              setKind(item);
              setSearching(false);
              setQuery("");
            }}
          >
            {item === "preference" ? "Preferences" : item === "fact" ? "Facts" : "Episodes"}
          </button>
        ))}
      </div>

      <form onSubmit={onSearch} className="mt-4 flex flex-wrap gap-2">
        <label className="min-w-0 flex-1">
          <span className="sr-only">Search memory</span>
          <input className="min-h-11 w-full rounded-full border border-line bg-raised px-4" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by meaning" />
        </label>
        <button type="submit" className="min-h-11 rounded-full bg-ink px-5 text-sm font-semibold text-paper">
          Search
        </button>
        {searching ? (
          <button type="button" className="min-h-11 rounded-full border border-line px-4 text-sm" onClick={() => void load()}>
            Clear
          </button>
        ) : null}
      </form>

      {kind === "episode" ? (
        <p className="mt-4 text-sm text-muted">Episodes are written by the curator. You can delete one, but not compose it by hand.</p>
      ) : (
        <form onSubmit={onCreate} className="sheet mt-5 p-4 sm:p-5">
          <label className="block">
            <span className="text-sm font-semibold">New {kind}</span>
            <textarea className="mt-2 min-h-24 w-full rounded-2xl border border-line bg-paper px-3 py-3" value={content} maxLength={300} onChange={(event) => setContent(event.target.value)} required aria-label="Memory content" />
          </label>
          <label className="mt-3 block text-sm">
            <span className="font-semibold">Importance {Math.round(importance * 100)}</span>
            <input className="mt-2 w-full accent-[var(--accent)]" type="range" min={0} max={1} step={0.05} value={importance} onChange={(event) => setImportance(Number(event.target.value))} />
          </label>
          <button type="submit" className="mt-3 min-h-11 rounded-full bg-accent px-5 text-sm font-semibold text-accent-ink">
            Save {kind}
          </button>
        </form>
      )}

      {error ? (
        <p className="mt-4 rounded-2xl bg-danger-soft px-4 py-3 text-sm text-danger" role="alert">
          {error}
        </p>
      ) : null}

      <ul className="mt-5 space-y-3">
        {items.map((item) => (
          <li key={item.id} className="rounded-3xl border border-line bg-raised p-4">
            <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted">
              <span>{item.kind}</span>
              <span>Importance {Math.round(item.importance * 100)}</span>
              <span className="normal-case tracking-normal">{formatWhen(item.updated_at || item.created_at)}</span>
              {item.source_run_id ? (
                <Link href={`/runs/${item.source_run_id}`} className="normal-case tracking-normal text-accent">
                  Origin run
                </Link>
              ) : null}
            </div>
            {editing === item.id ? (
              <form
                className="mt-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  void fetch(`/api/memories/${item.id}`, {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ content: draft }),
                  }).then(() => {
                    setEditing(null);
                    return load();
                  });
                }}
              >
                <textarea className="min-h-24 w-full rounded-2xl border border-line bg-paper px-3 py-3" value={draft} maxLength={300} onChange={(event) => setDraft(event.target.value)} aria-label="Edit memory" />
                <div className="mt-2 flex gap-2">
                  <button type="submit" className="min-h-11 rounded-full bg-accent px-4 text-sm font-semibold text-accent-ink">
                    Save
                  </button>
                  <button type="button" className="min-h-11 rounded-full border border-line px-4 text-sm" onClick={() => setEditing(null)}>
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <p className="mt-2 font-display text-xl leading-snug">{item.content}</p>
            )}
            {editing === item.id ? null : (
              <div className="mt-3 flex gap-2">
                {item.kind === "episode" ? null : (
                  <button
                    type="button"
                    className="min-h-11 text-sm font-semibold"
                    onClick={() => {
                      setEditing(item.id);
                      setDraft(item.content);
                    }}
                  >
                    Edit
                  </button>
                )}
                <button
                  type="button"
                  className="min-h-11 text-sm font-semibold text-danger"
                  onClick={() => {
                    if (!window.confirm("Delete this memory?")) return;
                    void fetch(`/api/memories/${item.id}`, { method: "DELETE" }).then(() => load());
                  }}
                >
                  Delete
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
      {items.length === 0 ? <p className="mt-6 text-sm text-muted">Nothing stored in this drawer.</p> : null}

      <section className="mt-10 rounded-3xl border border-dashed border-danger/40 p-5">
        <h2 className="font-display text-2xl">Forget everything</h2>
        <p className="mt-2 max-w-xl text-sm text-muted">This deletes preferences, facts, and episodes for this desk. Runs you already finished stay in the archive.</p>
        <button type="button" className="mt-4 min-h-11 rounded-full bg-danger px-5 text-sm font-semibold text-white" onClick={() => setForgetOpen(true)}>
          Forget all memory
        </button>
      </section>

      {forgetOpen ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-ink/40 p-4" role="presentation" onClick={() => setForgetOpen(false)}>
          <form
            role="dialog"
            aria-modal="true"
            aria-labelledby="forget-title"
            className="sheet w-full max-w-md p-5"
            onClick={(event) => event.stopPropagation()}
            onSubmit={(event) => {
              event.preventDefault();
              if (confirm !== "forget") return;
              void fetch("/api/memories?confirm=true", { method: "DELETE" }).then(() => {
                setForgetOpen(false);
                setConfirm("");
                return load();
              });
            }}
          >
            <h2 id="forget-title" className="font-display text-3xl">
              Forget the whole shelf?
            </h2>
            <p className="mt-2 text-sm text-muted">Type forget to confirm. This cannot be undone.</p>
            <input className="mt-4 min-h-11 w-full rounded-2xl border border-line bg-paper px-3" value={confirm} onChange={(event) => setConfirm(event.target.value)} aria-label="Type forget to confirm" autoFocus />
            <div className="mt-4 flex gap-2">
              <button type="submit" className="min-h-11 rounded-full bg-danger px-4 text-sm font-semibold text-white" disabled={confirm !== "forget"}>
                Delete all
              </button>
              <button type="button" className="min-h-11 rounded-full border border-line px-4 text-sm" onClick={() => setForgetOpen(false)}>
                Keep them
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  );
}
