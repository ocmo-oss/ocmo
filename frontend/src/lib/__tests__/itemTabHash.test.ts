import { describe, expect, it } from "vitest";
import { itemTabToHash, parseItemTabHash } from "../../hooks/useItemTabHash";

describe("itemTabHash", () => {
  it("maps change_requests to kebab-case in URL", () => {
    expect(itemTabToHash("change_requests", "editor")).toBe("#change-requests");
    expect(
      parseItemTabHash("#change-requests", ["editor", "change_requests"]),
    ).toBe("change_requests");
  });

  it("omits hash for default tab", () => {
    expect(itemTabToHash("editor", "editor")).toBe("");
  });

  it("returns null for unknown hash", () => {
    expect(parseItemTabHash("#nope", ["editor", "history"])).toBeNull();
    expect(parseItemTabHash("", ["editor"])).toBeNull();
  });
});
