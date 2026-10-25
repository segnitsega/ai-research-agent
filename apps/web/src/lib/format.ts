export const PHASES = ["recall", "plan", "search", "read", "critique", "write", "memorize"] as const;

export const PHASE_LABEL: Record<(typeof PHASES)[number], string> = {
  recall: "Recall",
  plan: "Plan",
  search: "Search",
  read: "Read",
  critique: "Critique",
  write: "Write",
  memorize: "Memorize",
};

export const AGENTS = ["planner", "searcher", "reader", "critic", "writer", "curator", "system"] as const;

export function agentLabel(agent: string | undefined): string {
  switch (agent) {
    case "planner":
      return "Planner";
    case "searcher":
      return "Searcher";
    case "reader":
      return "Reader";
    case "critic":
      return "Critic";
    case "writer":
      return "Writer";
    case "curator":
      return "Curator";
    default:
      return "Desk";
  }
}

export function agentMark(agent: string | undefined): string {
  return agentLabel(agent).slice(0, 1);
}

export function cn(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

export function formatMoney(value: number): string {
  if (!Number.isFinite(value)) return "$0.00";
  if (value > 0 && value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat("en").format(Math.round(value));
}

export function formatDuration(seconds: number): string {
  if (seconds < 90) return `${Math.round(seconds)} sec`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 90) return `${minutes} min`;
  const hours = minutes / 60;
  return `${hours.toFixed(hours >= 10 ? 0 : 1)} hr`;
}

export function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function clip(value: string, max: number): string {
  const trimmed = value.trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max - 1).trimEnd()}…`;
}

export function domainOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function slugify(value: string): string {
  const slug = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 60);
  return slug || "research-report";
}

export function toneForRatio(ratio: number): "ok" | "warn" | "danger" {
  if (ratio >= 0.9) return "danger";
  if (ratio >= 0.7) return "warn";
  return "ok";
}

export function statusLabel(status: string): string {
  switch (status) {
    case "queued":
      return "Queued";
    case "running":
      return "Running";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    case "cancelled":
      return "Cancelled";
    default:
      return status ? status.slice(0, 1).toUpperCase() + status.slice(1) : "Unknown";
  }
}
