"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { cn } from "@/lib/format";
import { defaultPrefs, readPrefs, subscribePrefs, writePrefs, type DepthChoice, type ThemeChoice } from "@/lib/prefs";

type PublicConfig = {
  models: Record<string, string>;
  search_providers: string[];
  server_max: Record<string, number>;
};

export function SettingsDesk() {
  const prefs = useSyncExternalStore(subscribePrefs, readPrefs, () => defaultPrefs);
  const [config, setConfig] = useState<PublicConfig | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetch("/api/config")
      .then(async (response) => (response.ok ? ((await response.json()) as PublicConfig) : null))
      .then((body) => {
        if (!cancelled && body) setConfig(body);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-3xl">
      <p className="kicker">Settings</p>
      <h1 className="mt-2 font-display text-4xl sm:text-5xl">The room, not the keys.</h1>
      <p className="mt-4 text-muted">Theme and defaults stay in this browser. The Gemini key never leaves the API server.</p>

      <section className="sheet mt-8 p-5">
        <h2 className="font-display text-2xl">Appearance</h2>
        <div className="mt-4 grid gap-2 sm:grid-cols-3" role="radiogroup" aria-label="Theme">
          {(["light", "dark", "system"] as const).map((theme) => (
            <Choice key={theme} pressed={prefs.theme === theme} label={theme} onClick={() => writePrefs({ ...prefs, theme: theme as ThemeChoice })} />
          ))}
        </div>
      </section>

      <section className="sheet mt-4 p-5">
        <h2 className="font-display text-2xl">Defaults for a new run</h2>
        <div className="mt-4 grid gap-2 sm:grid-cols-3" role="radiogroup" aria-label="Default depth">
          {(["quick", "standard", "deep"] as const).map((depth) => (
            <Choice key={depth} pressed={prefs.depth === depth} label={depth} onClick={() => writePrefs({ ...prefs, depth: depth as DepthChoice })} />
          ))}
        </div>
        <div className="mt-4 flex items-center justify-between gap-3 rounded-2xl border border-line px-4 py-3">
          <div>
            <p className="text-sm font-semibold">Use memory by default</p>
            <p className="text-sm text-muted">You can still turn it off on a single question.</p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={prefs.useMemory}
            className={cn("min-h-11 min-w-16 rounded-full px-4 text-sm font-semibold", prefs.useMemory ? "bg-accent text-accent-ink" : "bg-line text-ink")}
            onClick={() => writePrefs({ ...prefs, useMemory: !prefs.useMemory })}
          >
            {prefs.useMemory ? "On" : "Off"}
          </button>
        </div>
      </section>

      <section className="mt-4 rounded-3xl border border-line p-5">
        <h2 className="font-display text-2xl">Server</h2>
        <p className="mt-2 text-sm text-muted">These names come from the API. The browser only sends the application API key through the Next.js proxy.</p>
        {config ? (
          <dl className="mt-4 divide-y divide-line">
            {Object.entries(config.models).map(([agent, model]) => (
              <div key={agent} className="grid gap-1 py-3 sm:grid-cols-[8rem_1fr]">
                <dt className="text-sm font-semibold capitalize">{agent}</dt>
                <dd className="text-sm text-muted">{model}</dd>
              </div>
            ))}
            <div className="grid gap-1 py-3 sm:grid-cols-[8rem_1fr]">
              <dt className="text-sm font-semibold">Search</dt>
              <dd className="text-sm text-muted">{config.search_providers.join(", ")}</dd>
            </div>
          </dl>
        ) : (
          <p className="mt-4 text-sm text-muted">Waiting for the API configuration.</p>
        )}
      </section>
    </div>
  );
}

function Choice({ pressed, label, onClick }: { pressed: boolean; label: string; onClick: () => void }) {
  return (
    <button type="button" role="radio" aria-checked={pressed} onClick={onClick} className={cn("min-h-11 rounded-2xl border px-3 text-sm font-semibold capitalize", pressed ? "border-accent bg-accent-soft" : "border-line")}>
      {label}
    </button>
  );
}
