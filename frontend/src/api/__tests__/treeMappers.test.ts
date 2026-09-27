import { describe, expect, it } from "vitest";
import { mapResolveResponse } from "../treeMappers";

describe("mapResolveResponse", () => {
  it("maps skipped optional extend trace entries without a version", () => {
    const result = mapResolveResponse({
      items: [
        {
          name: "output.yaml",
          version: 1,
          format: "yaml",
          trace: {
            "optional/base@latest": { skipped: true, reason: "not_found" },
            "shared/required@2": { version: 2 },
          },
        },
      ],
    });

    expect(result.trace?.["optional/base@latest"]).toEqual({
      resource_type: "config",
      path: "optional/base",
      resolve_role: "transitive",
      from_cache: false,
      skipped: true,
    });
    expect(result.trace?.["shared/required@2"]?.version).toBe(2);
    expect(result.trace?.["shared/required@2"]?.skipped).toBeUndefined();
  });
});
