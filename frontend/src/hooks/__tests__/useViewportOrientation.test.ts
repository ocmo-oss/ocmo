import { describe, expect, it } from "vitest";
import { isLandscapeDimensions } from "../useViewportOrientation";

describe("isLandscapeDimensions", () => {
  it("returns true when width exceeds height", () => {
    expect(isLandscapeDimensions(1200, 800)).toBe(true);
  });

  it("returns false when height exceeds width", () => {
    expect(isLandscapeDimensions(600, 900)).toBe(false);
  });

  it("returns false when width equals height", () => {
    expect(isLandscapeDimensions(800, 800)).toBe(false);
  });
});
