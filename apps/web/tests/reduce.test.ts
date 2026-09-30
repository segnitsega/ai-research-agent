import { describe, expect, it } from "vitest";
import { emptyRunState, reduce } from "../src/lib/reduce";

describe("reduce", () => {
  it("ignores a repeated sequence number", () => {
    const event = { seq: 1, type: "run.started", data: {} };
    const once = reduce(emptyRunState(), event);
    const twice = reduce(once, event);
    expect(twice.events).toHaveLength(1);
    expect(twice.status).toBe("running");
  });
});
