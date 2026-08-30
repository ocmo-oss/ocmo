import { describe, expect, it } from "vitest";
import type { AuditEvent } from "../../api/types";
import {
  formatAuditOperation,
  inferOperationFromLegacyFields,
} from "../auditEvent";

function event(partial: Partial<AuditEvent>): AuditEvent {
  return {
    id: "1",
    occurred_at: "2026-01-01T00:00:00Z",
    auth_id: "user",
    auth_type: "user",
    http_method: "GET",
    api_endpoint: "/api/v1/ns/qa/~get/app/cfg",
    event_kind: "operation",
    ...partial,
  };
}

describe("formatAuditOperation", () => {
  it("prefers persisted operation field", () => {
    expect(formatAuditOperation(event({ operation: "Set tag" }))).toBe(
      "Set tag",
    );
  });

  it("falls back for resolve_request without operation", () => {
    expect(
      formatAuditOperation(
        event({
          event_kind: "resolve_request",
          object_id: "app/cfg",
          operation: null,
        }),
      ),
    ).toBe("Resolve");
  });

  it("falls back for resolve_participant without operation", () => {
    expect(
      formatAuditOperation(
        event({
          event_kind: "resolve_participant",
          resolve_type: "nested",
          operation: null,
        }),
      ),
    ).toBe("Referenced in resolve");
  });
});

describe("inferOperationFromLegacyFields", () => {
  it("maps GET ~get to typed Read label", () => {
    expect(
      inferOperationFromLegacyFields(
        event({
          http_method: "GET",
          api_endpoint: "/api/v1/ns/qa/~get/app/cfg",
          object_type: "config",
        }),
      ),
    ).toBe("Read config");
  });

  it("maps PUT update to Update item", () => {
    expect(
      inferOperationFromLegacyFields(
        event({
          http_method: "PUT",
          api_endpoint: "/api/v1/ns/qa/~config/~update/app/cfg",
        }),
      ),
    ).toBe("Update item");
  });
});
