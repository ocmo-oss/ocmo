import { beforeEach, describe, expect, it } from "vitest";
import { ApiError } from "../../api/client";
import { getTopModalId, registerModal, unregisterModal } from "../modalStack";
import {
  formatNotificationCopy,
  pushApiError,
  pushNotification,
  useNotifications,
} from "../notifications";

function resetNotificationsStore() {
  useNotifications.setState({
    notifications: [],
    modalNotifications: {},
    trayOpen: false,
    shakeGeneration: 0,
    successPulseGeneration: 0,
  });
}

describe("notifications with open modal", () => {
  beforeEach(() => {
    resetNotificationsStore();
    while (getTopModalId()) {
      unregisterModal(getTopModalId()!);
    }
  });

  it("opens tray on error when no modal is open", () => {
    pushNotification("error", "Request failed", "timeout");
    expect(useNotifications.getState().trayOpen).toBe(true);
    expect(useNotifications.getState().modalNotifications).toEqual({});
  });

  it("does not open tray on error when a modal is open", () => {
    registerModal("modal-1");
    pushNotification("error", "Delete failed", "forbidden");
    const state = useNotifications.getState();
    expect(state.trayOpen).toBe(false);
    expect(state.notifications).toHaveLength(1);
    expect(state.modalNotifications["modal-1"]).toMatchObject({
      severity: "error",
      message: "Delete failed",
      detail: "forbidden",
    });
  });

  it("routes warning and info notifications to the open modal", () => {
    registerModal("modal-1");
    pushNotification("warning", "Heads up");
    pushNotification("info", "Saved draft");
    const state = useNotifications.getState();
    expect(state.trayOpen).toBe(false);
    expect(state.modalNotifications["modal-1"]).toMatchObject({
      severity: "info",
      message: "Saved draft",
    });
  });

  it("clears modal notification when modal closes", () => {
    registerModal("modal-1");
    pushNotification("error", "Move failed", "conflict");
    useNotifications.getState().clearModalNotification("modal-1");
    expect(useNotifications.getState().modalNotifications).toEqual({});
    expect(useNotifications.getState().notifications).toHaveLength(1);
  });
});

describe("formatNotificationCopy", () => {
  it("includes audit event id only in copied text", () => {
    expect(
      formatNotificationCopy({
        message: "Save failed",
        detail: "conflict",
        auditEventId: "550e8400-e29b-41d4-a716-446655440000",
      }),
    ).toBe(
      "Save failed\nconflict\nAudit event ID: 550e8400-e29b-41d4-a716-446655440000",
    );
  });

  it("omits audit line when id is absent", () => {
    expect(
      formatNotificationCopy({
        message: "Save failed",
        detail: "conflict",
      }),
    ).toBe("Save failed\nconflict");
  });
});

describe("pushApiError", () => {
  beforeEach(() => {
    useNotifications.setState({
      notifications: [],
      modalNotifications: {},
      trayOpen: false,
      shakeGeneration: 0,
      successPulseGeneration: 0,
    });
  });

  it("stores audit event id from ApiError", () => {
    const error = new ApiError(
      409,
      '{"error":"conflict","audit_event_id":"550e8400-e29b-41d4-a716-446655440000"}',
      "conflict",
      "550e8400-e29b-41d4-a716-446655440000",
    );
    pushApiError("Save failed", error);
    expect(useNotifications.getState().notifications[0]).toMatchObject({
      message: "Save failed",
      detail: "conflict",
      auditEventId: "550e8400-e29b-41d4-a716-446655440000",
    });
  });

  it("reports API unavailability for gateway failures", () => {
    const error = new ApiError(
      502,
      "<html>",
      "The API is temporarily unavailable.",
    );
    pushApiError("Failed to load item", error);
    expect(useNotifications.getState().notifications[0]).toMatchObject({
      message: "API unavailable",
      detail: "The API is temporarily unavailable.",
    });
  });
});
