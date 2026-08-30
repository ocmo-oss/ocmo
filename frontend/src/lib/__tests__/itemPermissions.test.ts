import { describe, expect, it } from "vitest";
import { FALLBACK_PERMISSION_ACTIONS } from "../permissionSchema";
import { allPermissionOps, permissionOpsForType } from "../itemPermissions";

describe("itemPermissions", () => {
  it("includes audit operation for configs", () => {
    const ops = permissionOpsForType("config", FALLBACK_PERMISSION_ACTIONS);
    expect(ops.audit).toBe("config:audit");
    expect(allPermissionOps("config", FALLBACK_PERMISSION_ACTIONS)).toContain(
      "config:audit",
    );
  });

  it("maps folder audit to folder:audit", () => {
    expect(
      permissionOpsForType("folder", FALLBACK_PERMISSION_ACTIONS).audit,
    ).toBe("folder:audit");
  });

  it("maps resolver audit to resolver:audit", () => {
    expect(
      permissionOpsForType("resolver", FALLBACK_PERMISSION_ACTIONS).audit,
    ).toBe("resolver:audit");
  });
});
