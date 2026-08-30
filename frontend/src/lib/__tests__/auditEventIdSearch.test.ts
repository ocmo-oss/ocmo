import { describe, expect, it } from "vitest";
import {
  applyAuditEventIdFilter,
  extractAuditEventIdInput,
  isCompleteAuditEventId,
} from "../auditEventIdSearch";

const EVENT_ID = "550e8400-e29b-41d4-a716-446655440000";

describe("extractAuditEventIdInput", () => {
  it("returns bare uuid unchanged", () => {
    expect(extractAuditEventIdInput(EVENT_ID)).toBe(EVENT_ID);
  });

  it("extracts id from copied notification body", () => {
    expect(
      extractAuditEventIdInput(
        `Save failed\nconflict\nAudit event ID: ${EVENT_ID}`,
      ),
    ).toBe(EVENT_ID);
  });

  it("extracts id when audit line uses different casing", () => {
    expect(
      extractAuditEventIdInput(`Save failed\nAUDIT EVENT ID: ${EVENT_ID}`),
    ).toBe(EVENT_ID);
  });

  it("prefers audit event id line over other uuids in paste", () => {
    const other = "11111111-1111-1111-1111-111111111111";
    expect(
      extractAuditEventIdInput(
        `Error\nreferenced ${other}\nAudit event ID: ${EVENT_ID}`,
      ),
    ).toBe(EVENT_ID);
  });

  it("keeps partial typing on a single line", () => {
    expect(extractAuditEventIdInput("550e8400-e29b")).toBe("550e8400-e29b");
  });

  it("returns empty for multiline paste without an audit id", () => {
    expect(extractAuditEventIdInput("Save failed\nconflict")).toBe("");
  });
});

describe("isCompleteAuditEventId", () => {
  it("accepts a full uuid", () => {
    expect(isCompleteAuditEventId(EVENT_ID)).toBe(true);
  });

  it("rejects partial uuid", () => {
    expect(isCompleteAuditEventId("550e8400-e29b")).toBe(false);
  });
});

describe("applyAuditEventIdFilter", () => {
  it("drops incomplete event_id from api filters", () => {
    expect(
      applyAuditEventIdFilter({
        event_id: "550e8400-e29b",
        auth_email: "a@b.c",
      }),
    ).toEqual({
      auth_email: "a@b.c",
    });
  });

  it("keeps complete event_id", () => {
    expect(applyAuditEventIdFilter({ event_id: EVENT_ID })).toEqual({
      event_id: EVENT_ID,
    });
  });
});
