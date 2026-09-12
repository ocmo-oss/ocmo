import { describe, expect, it } from "vitest";
import { isPathUnderFolder } from "../treeBranch";

describe("isPathUnderFolder", () => {
  it("matches the folder path itself", () => {
    expect(isPathUnderFolder("apps", "apps")).toBe(true);
  });

  it("matches descendants", () => {
    expect(isPathUnderFolder("apps", "apps/web/prod")).toBe(true);
  });

  it("rejects siblings and unrelated paths", () => {
    expect(isPathUnderFolder("apps", "app")).toBe(false);
    expect(isPathUnderFolder("apps", "apps-extra")).toBe(false);
    expect(isPathUnderFolder("apps", "other/web")).toBe(false);
  });
});
