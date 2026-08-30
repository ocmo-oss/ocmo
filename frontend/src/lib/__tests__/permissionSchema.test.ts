import { describe, expect, it } from "vitest";
import {
  extractPermissionActionEnum,
  FALLBACK_PERMISSION_ACTIONS,
  lockPermissionOps,
} from "../permissionSchema";

const permissionsSchema = {
  type: "object",
  properties: {
    policies: {
      type: "array",
      items: {
        type: "object",
        properties: {
          actions: {
            type: "array",
            items: {
              type: "string",
              enum: ["config:read", "lock:read", "lock:write", "lock:delete"],
            },
          },
        },
      },
    },
  },
};

describe("permissionSchema", () => {
  it("extracts action enum from permissions policy schema", () => {
    expect(extractPermissionActionEnum(permissionsSchema)).toEqual([
      "config:read",
      "lock:read",
      "lock:write",
      "lock:delete",
    ]);
  });

  it("includes lock operations in fallback actions", () => {
    expect(FALLBACK_PERMISSION_ACTIONS).toContain("lock:read");
    expect(FALLBACK_PERMISSION_ACTIONS).toContain("lock:write");
    expect(FALLBACK_PERMISSION_ACTIONS).toContain("lock:delete");
  });

  it("selects lock permission probes from schema actions", () => {
    expect(
      lockPermissionOps(["config:read", "lock:read", "lock:delete"]),
    ).toEqual(["lock:read", "lock:delete"]);
  });
});
