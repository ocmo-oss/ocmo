import { describe, expect, it } from "vitest";
import { applyCreatePathInput } from "../createItemPath";

describe("applyCreatePathInput", () => {
  it("filters disallowed characters from the active segment", () => {
    expect(applyCreatePathInput([], "", "my item@")).toEqual({
      prefixSegments: [],
      currentInput: "myitem",
    });
  });

  it("commits sanitized folder segments when typing slashes", () => {
    expect(applyCreatePathInput(["app"], "", "sub/cfg")).toEqual({
      prefixSegments: ["app", "sub"],
      currentInput: "cfg",
    });
  });

  it("does not commit dot segments", () => {
    expect(applyCreatePathInput([], "", "../cfg")).toEqual({
      prefixSegments: [],
      currentInput: "cfg",
    });
  });
});
