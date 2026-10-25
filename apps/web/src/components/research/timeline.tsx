"use client";

import { useEffect, useRef, useState } from "react";
import { agentLabel, agentMark, cn, formatWhen } from "@/lib/format";
import { eventSummary, type RunEvent } from "@/lib/reduce";

const MILESTONES = new Set([
  "plan.created",
  "critic.review",
  "report.completed",
  "run.completed",
  "run.failed",
  "run.cancelled",
  "budget.exhausted",
]);

export function ActivityTimeline({ events }: { events: RunEvent[] }) {
  const scroller = useRef<HTMLDivElement>(null);
  const [follow, setFollow] = useState(true);
  const visible = events.filter((event) => event.type !== "usage.updated");
  const groups = groupEvents(visible);
  const latest = [...events].reverse().find((event) => MILESTONES.has(event.type));

  useEffect(() => {
    if (follow && scroller.current) scroller.current.scrollTop = scroller.current.scrollHeight;
  }, [visible.length, follow]);

  return (
    <section className="flex min-h-0 flex-col" aria-label="Activity">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-2xl">Activity</h2>
        {follow ? null : (
          <button type="button" className="text-sm font-semibold text-accent" onClick={() => setFollow(true)}>
            Jump to latest
          </button>
        )}
      </div>
      <p className="sr-only" aria-live="polite">
        {latest ? eventSummary(latest) : ""}
      </p>
      <div
        ref={scroller}
        className="min-h-64 flex-1 space-y-4 overflow-y-auto pr-1 xl:max-h-[calc(100vh-16rem)]"
        onScroll={(event) => {
          const node = event.currentTarget;
          const distance = node.scrollHeight - node.scrollTop - node.clientHeight;
          setFollow(distance < 48);
        }}
      >
        {visible.length === 0 ? <p className="text-sm text-muted">The desk is quiet. Events will appear here as the agents work.</p> : null}
        {groups.map((group) => (
          <details key={group.key} open className="rounded-2xl border border-line bg-paper/70">
            <summary className="cursor-pointer px-3 py-3 text-sm font-semibold">{group.label}</summary>
            <ol className="space-y-2 px-3 pb-3">
              {group.events.map((event) => (
                <li key={event.seq} className="event-in grid grid-cols-[2rem_1fr] gap-2">
                  <span className="mt-0.5 grid h-8 w-8 place-items-center rounded-full bg-accent-soft text-xs font-bold text-accent" title={agentLabel(event.agent)}>
                    {agentMark(event.agent)}
                  </span>
                  <span>
                    <span className="block text-xs font-semibold uppercase tracking-wide text-muted">{agentLabel(event.agent)}</span>
                    <span className="block text-sm leading-5">{eventSummary(event)}</span>
                    {event.ts ? <span className="text-xs text-muted">{formatWhen(event.ts)}</span> : null}
                  </span>
                </li>
              ))}
            </ol>
          </details>
        ))}
      </div>
    </section>
  );
}

function groupEvents(events: RunEvent[]): { key: string; label: string; events: RunEvent[] }[] {
  const groups: { key: string; label: string; events: RunEvent[] }[] = [];
  let iteration = 0;
  for (const event of events) {
    if (event.type === "iteration.started") {
      const value = event.data.iteration;
      iteration = typeof value === "number" ? value : iteration + 1;
    }
    const key = iteration === 0 ? "opening" : `iteration-${iteration}`;
    const label = iteration === 0 ? "Opening" : `Iteration ${iteration}`;
    const current = groups[groups.length - 1];
    if (!current || current.key !== key) groups.push({ key, label, events: [event] });
    else current.events.push(event);
  }
  return groups;
}

function phaseProgress(phase: string, status: string): { id: string; label: string; state: "done" | "current" | "upcoming" }[] {
  const order = ["recall", "plan", "search", "read", "critique", "write", "memorize"];
  const labels = ["Recall", "Plan", "Search", "Read", "Critique", "Write", "Memorize"];
  const index = order.indexOf(phase);
  return order.map((id, position) => {
    let state: "done" | "current" | "upcoming" = "upcoming";
    if (status === "completed") state = "done";
    else if (index === -1 && status === "running" && position === 0) state = "current";
    else if (position < index) state = "done";
    else if (position === index) state = "current";
    return { id, label: labels[position], state };
  });
}

export function PhaseStepper({ phase, status }: { phase: string; status: string }) {
  const steps = phaseProgress(phase, status);
  return (
    <ol className="flex flex-wrap gap-2" aria-label="Research phases">
      {steps.map((step, index) => (
        <li key={step.id} className={cn("min-w-28 flex-1 rounded-2xl border px-3 py-2", step.state === "current" ? "border-accent bg-accent-soft" : "border-line")}>
          <span className="block text-[0.65rem] font-semibold uppercase tracking-wider text-muted">
            {String(index + 1).padStart(2, "0")} · {step.state === "done" ? "Done" : step.state === "current" ? "Now" : "Waiting"}
          </span>
          <span className="font-display text-lg">{step.label}</span>
        </li>
      ))}
    </ol>
  );
}
