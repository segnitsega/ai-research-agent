import { citationParts } from "@/lib/markdown";

export function MarkdownBody({ text, onCite }: { text: string; onCite: (n: number) => void }) {
  const blocks = text.replaceAll("\r\n", "\n").split(/\n{2,}/);
  return (
    <div className="space-y-4">
      {blocks.map((block, index) => (
        <Block key={`${index}-${block.slice(0, 24)}`} block={block} onCite={onCite} />
      ))}
    </div>
  );
}

function Block({ block, onCite }: { block: string; onCite: (n: number) => void }) {
  const lines = block.split("\n").filter((line) => line.length > 0);
  if (lines.length === 0) return null;
  if (lines.every((line) => /^[-*]\s+/.test(line))) {
    return (
      <ul className="list-disc space-y-2 pl-5">
        {lines.map((line) => (
          <li key={line}>
            <Inline text={line.replace(/^[-*]\s+/, "")} onCite={onCite} />
          </li>
        ))}
      </ul>
    );
  }
  const heading = /^(#{1,3})\s+(.*)$/.exec(lines[0]);
  if (heading && lines.length === 1) {
    const Tag = heading[1].length === 1 ? "h3" : "h4";
    return (
      <Tag className="font-display text-2xl leading-tight">
        <Inline text={heading[2]} onCite={onCite} />
      </Tag>
    );
  }
  return (
    <p className="whitespace-pre-wrap">
      <Inline text={lines.join("\n")} onCite={onCite} />
    </p>
  );
}

function Inline({ text, onCite }: { text: string; onCite: (n: number) => void }) {
  return (
    <>
      {citationParts(text).map((part, index) => {
        if (part.type === "cite") {
          return (
            <button key={`${part.n}-${index}`} type="button" className="citation" onClick={() => onCite(part.n)} aria-label={`Open citation ${part.n}`}>
              {part.n}
            </button>
          );
        }
        if (part.type === "strong") return <strong key={`${part.value}-${index}`}>{part.value}</strong>;
        return <span key={`${index}-${part.value.slice(0, 12)}`}>{part.value}</span>;
      })}
    </>
  );
}
