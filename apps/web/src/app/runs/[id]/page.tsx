"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { emptyRunState, reduce, type RunEvent, type RunState } from "@/lib/reduce";

export default function RunPage() {
  const params = useParams<{ id: string }>();
  const [state, setState] = useState<RunState>(emptyRunState());
  const [selected, setSelected] = useState<string>("");

  useEffect(() => {
    const source = new EventSource(`/api/runs/${params.id}/events`);
    const onEvent = (event: MessageEvent) => {
      const parsed = JSON.parse(event.data) as RunEvent;
      setState((current) => reduce(current, parsed));
    };
    source.onmessage = onEvent;
    source.addEventListener("run.started", onEvent);
    source.addEventListener("plan.created", onEvent);
    source.addEventListener("finding.extracted", onEvent);
    source.addEventListener("finding.rejected", onEvent);
    source.addEventListener("report.completed", onEvent);
    source.addEventListener("run.completed", onEvent);
    source.addEventListener("run.failed", onEvent);
    source.addEventListener("run.cancelled", onEvent);
    source.addEventListener("critic.review", onEvent);
    source.addEventListener("source.fetched", onEvent);
    source.addEventListener("source.failed", onEvent);
    return () => source.close();
  }, [params.id]);

  const report = state.report;
  const summary = typeof report?.executive_summary === "string" ? report.executive_summary : "";

  return (
    <section>
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">Run</h1>
        <p aria-live="polite">Status: {state.status}</p>
      </div>
      <button
        type="button"
        className="mt-3 rounded border px-3 py-1"
        onClick={() => void fetch(`/api/runs/${params.id}/cancel`, { method: "POST" })}
      >
        Cancel
      </button>
      {state.error ? <p className="mt-3 text-red-700">{state.error}</p> : null}
      <h2 className="mt-6 text-lg font-medium">Activity</h2>
      <ol className="mt-2 space-y-1 text-sm">
        {state.events.map((event) => (
          <li key={event.seq}>
            {event.seq}. {event.type}
          </li>
        ))}
      </ol>
      {summary ? (
        <>
          <h2 className="mt-6 text-lg font-medium">Report</h2>
          <p className="mt-2 whitespace-pre-wrap">{summary}</p>
        </>
      ) : null}
      <h2 className="mt-6 text-lg font-medium">Findings</h2>
      <ul className="mt-2 space-y-2">
        {state.findings.map((finding) => {
          const id = String(finding.finding_id ?? "");
          return (
            <li key={id}>
              <button type="button" className="text-left underline-offset-4 hover:underline" onClick={() => setSelected(String(finding.evidence_quote ?? ""))}>
                {String(finding.claim ?? "")}
              </button>
            </li>
          );
        })}
      </ul>
      {selected ? (
        <aside className="mt-4 rounded border p-3" aria-label="Evidence">
          <h2 className="font-medium">Evidence quote</h2>
          <p>{selected}</p>
        </aside>
      ) : null}
    </section>
  );
}
