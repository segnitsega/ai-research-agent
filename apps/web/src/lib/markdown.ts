import type { ReportView } from "@/lib/reduce";

export type TextPart = { type: "text"; value: string } | { type: "cite"; n: number } | { type: "strong"; value: string };

export function citationParts(text: string): TextPart[] {
  const parts: TextPart[] = [];
  const pattern = /\[(\d+)\]|\*\*([^*]+)\*\*/g;
  let cursor = 0;
  for (const match of text.matchAll(pattern)) {
    const index = match.index ?? 0;
    if (index > cursor) parts.push({ type: "text", value: text.slice(cursor, index) });
    if (match[1]) parts.push({ type: "cite", n: Number(match[1]) });
    else if (match[2]) parts.push({ type: "strong", value: match[2] });
    cursor = index + match[0].length;
  }
  if (cursor < text.length) parts.push({ type: "text", value: text.slice(cursor) });
  return parts;
}

export function reportMarkdown(report: ReportView): string {
  const lines = [`# ${report.title}`, "", report.executiveSummary, ""];
  for (const section of report.sections) {
    lines.push(`## ${section.heading}`, "", section.body, "");
  }
  if (report.limitations.length > 0) {
    lines.push("## Limitations", ...report.limitations.map((item) => `- ${item}`), "");
  }
  if (report.citations.length > 0) {
    lines.push("## References");
    for (const citation of report.citations) {
      lines.push(`[${citation.n}] source ${citation.sourceId}`);
    }
  }
  return lines.join("\n").trim() + "\n";
}
