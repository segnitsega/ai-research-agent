import { describe, expect, it } from "vitest";
import { citationParts } from "../src/lib/markdown";
import { emptyRunState, eventSummary, reduce } from "../src/lib/reduce";

describe("reduce", () => {
  it("ignores a repeated sequence number", () => {
    const event = { seq: 1, type: "run.started", data: {} };
    const once = reduce(emptyRunState(), event);
    const twice = reduce(once, event);
    expect(twice.events).toHaveLength(1);
    expect(twice.status).toBe("running");
  });

  it("keeps a plan, an accepted finding, and a checked quote", () => {
    let state = emptyRunState();
    state = reduce(state, {
      seq: 1,
      type: "plan.created",
      data: { plan: { objective: "Map the lab", sub_questions: [{ id: "q1", question: "Who builds it?", rationale: "Name the lab", priority: 1 }], success_criteria: ["Name the lab"], out_of_scope: [] } },
    });
    state = reduce(state, {
      seq: 2,
      type: "finding.extracted",
      data: { finding_id: "f1", claim: "Google DeepMind develops Gemini.", evidence_quote: "Gemini is developed by Google DeepMind.", confidence: 0.8, stance: "supports", sub_question_id: "q1", source_id: "s1" },
    });
    state = reduce(state, {
      seq: 3,
      type: "finding.rejected",
      data: { claim: "A loose claim", reason: "quote_mismatch", sub_question_id: "q1", source_id: "s1" },
    });
    expect(state.plan?.objective).toBe("Map the lab");
    expect(state.findings).toHaveLength(2);
    expect(state.findings[0]?.status).toBe("accepted");
    expect(state.findings[1]?.status).toBe("rejected");
    expect(state.phase).toBe("read");
  });

  it("describes a search in one line", () => {
    expect(eventSummary({ seq: 4, type: "search.started", data: { query: "gemini developer" } })).toBe("Searching “gemini developer”");
  });
});

describe("citation parts", () => {
  it("splits citation markers out of prose", () => {
    expect(citationParts("Gemini is a model [1] from **DeepMind**.")).toEqual([
      { type: "text", value: "Gemini is a model " },
      { type: "cite", n: 1 },
      { type: "text", value: " from " },
      { type: "strong", value: "DeepMind" },
      { type: "text", value: "." },
    ]);
  });
});
