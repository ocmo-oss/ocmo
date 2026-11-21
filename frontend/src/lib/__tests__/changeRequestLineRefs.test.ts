import { describe, expect, it } from "vitest";
import {
  formatCrLineHash,
  linkifyCrLineRefsInMarkdown,
  parseCrLineHash,
} from "../changeRequestLineRefs";

describe("parseCrLineHash", () => {
  it("parses single line and ranges", () => {
    expect(parseCrLineHash("#10")).toEqual({ start: 10, end: 10 });
    expect(parseCrLineHash("10-15")).toEqual({ start: 10, end: 15 });
    expect(parseCrLineHash("#10-15")).toEqual({ start: 10, end: 15 });
  });

  it("normalizes reversed ranges", () => {
    expect(parseCrLineHash("15-10")).toEqual({ start: 10, end: 15 });
  });
});

describe("formatCrLineHash", () => {
  it("formats single and range", () => {
    expect(formatCrLineHash({ start: 3, end: 3 })).toBe("3");
    expect(formatCrLineHash({ start: 3, end: 7 })).toBe("3-7");
  });
});

describe("linkifyCrLineRefsInMarkdown", () => {
  it("linkifies common patterns", () => {
    expect(linkifyCrLineRefsInMarkdown("see lines 10-15 here")).toBe(
      "see [lines 10-15](#10-15) here",
    );
    expect(linkifyCrLineRefsInMarkdown("check #10:15")).toBe(
      "check [#10:15](#10-15)",
    );
    expect(linkifyCrLineRefsInMarkdown("at #10-15")).toBe(
      "at [#10-15](#10-15)",
    );
    expect(linkifyCrLineRefsInMarkdown("line 42 only")).toBe(
      "[line 42](#42) only",
    );
  });

  it("skips fenced code", () => {
    const input = "```yaml\nlines 1-2\n#3-4\n```\nlines 5-6";
    expect(linkifyCrLineRefsInMarkdown(input)).toBe(
      "```yaml\nlines 1-2\n#3-4\n```\n[lines 5-6](#5-6)",
    );
  });
});
