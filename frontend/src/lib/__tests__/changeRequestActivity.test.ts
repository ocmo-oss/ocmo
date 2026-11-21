import { describe, expect, it } from "vitest";
import { buildChangeRequestActivity } from "../changeRequestActivity";
import type { ChangeRequest } from "../../api/types";

function baseCr(overrides: Partial<ChangeRequest>): ChangeRequest {
  return {
    path: "app/cfg",
    node_type: "config",
    number: 1,
    status: "open",
    base_version: 1,
    title: "",
    description: "",
    created_by: "alice",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    rejected_reason: "",
    approvers: [],
    approval_events: [],
    base_superseded: false,
    latest_version: 1,
    approval_count: 0,
    required_approvals: 1,
    can_apply: false,
    can_approve: false,
    can_unapprove: false,
    projected_version_on_apply: 2,
    has_cr_references: false,
    referenced_by: [],
    depends_on: [],
    ...overrides,
  };
}

describe("buildChangeRequestActivity", () => {
  it("describes auto-reject on new version", () => {
    const items = buildChangeRequestActivity(
      baseCr({
        status: "rejected",
        rejected_at: "2026-01-02T12:00:00Z",
        rejected_reason: "new_version_published",
        rejected_by: "system",
      }),
    );
    expect(items).toHaveLength(1);
    expect(items[0].message).toContain("newer version of the config");
  });

  it("formats manual reject with optional reason", () => {
    const withReason = buildChangeRequestActivity(
      baseCr({
        status: "rejected",
        rejected_at: "2026-01-02T12:00:00Z",
        rejected_by: "admin",
        rejected_reason: "Not ready",
      }),
    );
    expect(withReason[0].message).toBe(
      "Change request was rejected by admin. Reason: Not ready",
    );

    const noReason = buildChangeRequestActivity(
      baseCr({
        status: "rejected",
        rejected_at: "2026-01-02T12:00:00Z",
        rejected_by: "admin",
        rejected_reason: "",
      }),
    );
    expect(noReason[0].message).toBe("Change request was rejected by admin.");
  });

  it("includes approvals and apply", () => {
    const items = buildChangeRequestActivity(
      baseCr({
        status: "applied",
        approval_events: [
          { approver: "bob", created_at: "2026-01-02T10:00:00Z" },
        ],
        applied_at: "2026-01-02T11:00:00Z",
        applied_by: "bob",
        applied_version: 3,
      }),
    );
    expect(items.map((i) => i.message)).toEqual([
      "bob approved this change request.",
      "Change request was applied as version 3 by bob.",
    ]);
  });
});
