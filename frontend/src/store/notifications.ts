import { create } from "zustand";
import { ApiError } from "../api/client";
import { isApiUnavailableError } from "../lib/apiAvailability";
import { getTopModalId } from "./modalStack";

export type Severity = "error" | "warning" | "info";

export interface Notification {
  id: string;
  severity: Severity;
  message: string;
  detail?: string;
  auditEventId?: string;
  timestamp: number;
  count: number;
}

interface NotificationsState {
  notifications: Notification[];
  modalNotifications: Record<string, Notification>;
  trayOpen: boolean;
  shakeGeneration: number;
  successPulseGeneration: number;
  openTray: () => void;
  closeTray: () => void;
  toggleTray: () => void;
  push: (
    severity: Severity,
    message: string,
    detail?: string,
    auditEventId?: string,
  ) => void;
  signalSuccess: () => void;
  dismiss: (id: string) => void;
  dismissAll: () => void;
  clearModalNotification: (modalId: string) => void;
}

const MAX_NOTIFICATIONS = 100;

let idCounter = 0;
function nextId() {
  return String(++idCounter);
}

function withModalNotification(
  state: NotificationsState,
  notification: Notification,
): Partial<Pick<NotificationsState, "modalNotifications" | "trayOpen">> {
  const topModalId = getTopModalId();
  if (!topModalId) {
    return {
      trayOpen: notification.severity === "error" ? true : state.trayOpen,
    };
  }
  return {
    modalNotifications: {
      ...state.modalNotifications,
      [topModalId]: notification,
    },
    trayOpen: state.trayOpen,
  };
}

export function formatNotificationCopy(
  notification: Pick<Notification, "message" | "detail" | "auditEventId">,
): string {
  const lines = [notification.message];
  if (notification.detail) lines.push(notification.detail);
  if (notification.auditEventId)
    lines.push(`Audit event ID: ${notification.auditEventId}`);
  return lines.join("\n");
}

export const useNotifications = create<NotificationsState>((set) => ({
  notifications: [],
  modalNotifications: {},
  trayOpen: false,
  shakeGeneration: 0,
  successPulseGeneration: 0,

  openTray: () => set({ trayOpen: true }),
  closeTray: () => set({ trayOpen: false }),
  toggleTray: () => set((s) => ({ trayOpen: !s.trayOpen })),

  signalSuccess: () =>
    set((s) => ({ successPulseGeneration: s.successPulseGeneration + 1 })),

  push: (severity, message, detail, auditEventId) => {
    set((state) => {
      const existing = state.notifications.find(
        (n) =>
          n.severity === severity &&
          n.message === message &&
          n.detail === detail,
      );
      if (existing) {
        const notification = {
          ...existing,
          count: existing.count + 1,
          timestamp: Date.now(),
          auditEventId: auditEventId ?? existing.auditEventId,
        };
        const updated = state.notifications.map((n) =>
          n.id === existing.id ? notification : n,
        );
        return {
          notifications: updated,
          shakeGeneration: state.shakeGeneration + 1,
          ...withModalNotification(state, notification),
        };
      }

      const notification: Notification = {
        id: nextId(),
        severity,
        message,
        detail,
        auditEventId,
        timestamp: Date.now(),
        count: 1,
      };

      let list = [notification, ...state.notifications];
      if (list.length > MAX_NOTIFICATIONS) {
        list = list.slice(0, MAX_NOTIFICATIONS);
      }

      return {
        notifications: list,
        shakeGeneration: state.shakeGeneration + 1,
        ...withModalNotification(state, notification),
      };
    });
  },

  dismiss: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  dismissAll: () => set({ notifications: [] }),

  clearModalNotification: (modalId) =>
    set((state) => {
      if (!(modalId in state.modalNotifications)) return state;
      const { [modalId]: _removed, ...modalNotifications } =
        state.modalNotifications;
      return { modalNotifications };
    }),
}));

/** Helper — call from outside React to push a notification. */
export function pushNotification(
  severity: Severity,
  message: string,
  detail?: string,
  auditEventId?: string,
) {
  useNotifications.getState().push(severity, message, detail, auditEventId);
}

/** Push an error notification from an API or unknown failure. */
export function pushApiError(
  title: string,
  error: unknown,
  detailOverride?: string,
) {
  if (isApiUnavailableError(error)) {
    const detail =
      detailOverride ?? (error instanceof ApiError ? error.detail : undefined);
    pushNotification("error", "API unavailable", detail);
    return;
  }
  if (error instanceof ApiError) {
    pushNotification(
      "error",
      title,
      detailOverride ?? error.detail,
      error.auditEventId,
    );
    return;
  }
  const detail =
    detailOverride ?? (error instanceof Error ? error.message : undefined);
  pushNotification("error", title, detail);
}

/** Brief success feedback on the top-bar notification bell (no toast). */
export function signalOperationSuccess() {
  useNotifications.getState().signalSuccess();
}
