import { describe, expect, it } from "vitest";
import { isSingleLineDescription } from "../description";

describe("isSingleLineDescription", () => {
  it("returns true for non-empty text without line breaks", () => {
    expect(isSingleLineDescription("Short summary")).toBe(true);
    expect(isSingleLineDescription("  padded single line  ")).toBe(true);
  });

  it("returns false for empty or multi-line text", () => {
    expect(isSingleLineDescription("")).toBe(false);
    expect(isSingleLineDescription("   ")).toBe(false);
    expect(isSingleLineDescription("Line one\nLine two")).toBe(false);
    expect(isSingleLineDescription("Line one\r\nLine two")).toBe(false);
  });
});
