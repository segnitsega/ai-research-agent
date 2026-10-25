import { cn, statusLabel } from "@/lib/format";

const TONE: Record<string, string> = {
  queued: "bg-warn-soft text-warn",
  running: "bg-accent-soft text-accent",
  completed: "bg-accent-soft text-ok",
  failed: "bg-danger-soft text-danger",
  cancelled: "bg-copper-soft text-copper",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn("inline-flex min-h-8 items-center gap-2 rounded-full px-3 text-xs font-semibold", TONE[status] ?? "bg-line text-ink")}>
      <StatusMark status={status} />
      {statusLabel(status)}
    </span>
  );
}

function StatusMark({ status }: { status: string }) {
  if (status === "running") {
    return <span className="relative inline-flex h-2.5 w-2.5" aria-hidden><span className="absolute inline-flex h-full w-full animate-pulse rounded-full bg-accent" /></span>;
  }
  if (status === "completed") {
    return (
      <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" aria-hidden>
        <path d="M3 8.5 6.2 12 13 4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    );
  }
  if (status === "failed") {
    return (
      <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" aria-hidden>
        <path d="M8 3.2 13.2 13H2.8L8 3.2Z" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <path d="M8 7v3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    );
  }
  if (status === "cancelled") {
    return (
      <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" aria-hidden>
        <circle cx="8" cy="8" r="5.2" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <path d="M5.2 5.2 10.8 10.8" stroke="currentColor" strokeWidth="1.4" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" aria-hidden>
      <circle cx="8" cy="8" r="5.2" fill="none" stroke="currentColor" strokeWidth="1.4" />
      <path d="M8 5.2V8l2 1.4" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}
