import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Info,
  X,
  ChevronDown,
  Trash2,
} from "lucide-react";
import { formatUserDateTimeRelative } from "../lib/datetime";
import {
  formatNotificationCopy,
  useNotifications,
} from "../store/notifications";
import type { Severity } from "../store/notifications";
import { cn } from "../components/ui/cn";
import { NotificationCopyButton } from "../components/ui/NotificationCopyButton";

function severityIcon(s: Severity) {
  if (s === "error")
    return <AlertCircle className="h-4 w-4 text-red-500 shrink-0" />;
  if (s === "warning")
    return <AlertTriangle className="h-4 w-4 text-yellow-500 shrink-0" />;
  return <Info className="h-4 w-4 text-blue-500 shrink-0" />;
}

function severityBg(s: Severity) {
  if (s === "error") return "border-l-red-500";
  if (s === "warning") return "border-l-yellow-500";
  return "border-l-blue-500";
}

function NotificationRow({
  id,
  severity,
  message,
  detail,
  auditEventId,
  timestamp,
  count,
  onDismiss,
  defaultExpanded = false,
}: {
  id: string;
  severity: Severity;
  message: string;
  detail?: string;
  auditEventId?: string;
  timestamp: number;
  count: number;
  onDismiss: (id: string) => void;
  defaultExpanded?: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const showExpandToggle = Boolean(detail) || message.length > 80;

  return (
    <div
      className={cn(
        "border-l-2 bg-surface-elevated dark:bg-gray-800 rounded-r px-3 py-2 text-sm shadow-sm",
        severityBg(severity),
      )}
    >
      <div className="flex items-start gap-2">
        {severityIcon(severity)}
        <div className="flex-1 min-w-0">
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            className={cn(
              "w-full text-left text-gray-800 dark:text-gray-200",
              !expanded && "line-clamp-2",
            )}
          >
            {message}
          </button>
          {expanded && detail && (
            <pre className="mt-1 whitespace-pre-wrap text-xs text-gray-500 dark:text-gray-400 font-mono">
              {detail}
            </pre>
          )}
          <div className="mt-0.5 flex items-center gap-2 text-xs text-gray-400">
            <span>{formatUserDateTimeRelative(timestamp)}</span>
            {count > 1 && (
              <span className="rounded-full bg-slate-300 dark:bg-gray-600 px-1.5 py-0.5 text-xs">
                ×{count}
              </span>
            )}
            {showExpandToggle && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setExpanded((v) => !v);
                }}
                className="flex items-center gap-0.5 hover:text-gray-600 dark:hover:text-gray-300"
                aria-expanded={expanded}
              >
                <ChevronDown
                  className={cn(
                    "h-3 w-3 transition-transform",
                    expanded && "rotate-180",
                  )}
                />
                {expanded ? "Less" : "More"}
              </button>
            )}
          </div>
        </div>
        <NotificationCopyButton
          className="ml-1"
          getText={() =>
            formatNotificationCopy({ message, detail, auditEventId })
          }
        />
        <button
          onClick={() => onDismiss(id)}
          className="shrink-0 rounded p-0.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          aria-label="Dismiss"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

export function NotificationsTray() {
  const { notifications, trayOpen, closeTray, dismiss, dismissAll } =
    useNotifications();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!trayOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeTray();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [trayOpen, closeTray]);

  useEffect(() => {
    if (!trayOpen) return;
    const onClick = (e: MouseEvent) => {
      if (!panelRef.current?.contains(e.target as Node)) {
        closeTray();
      }
    };
    const t = setTimeout(() => document.addEventListener("click", onClick), 0);
    return () => {
      clearTimeout(t);
      document.removeEventListener("click", onClick);
    };
  }, [trayOpen, closeTray]);

  if (!trayOpen) return null;

  return (
    <div
      ref={panelRef}
      className="fixed right-0 top-12 z-40 flex h-[calc(100vh-3rem)] w-80 flex-col bg-surface shadow-xl border-l border-slate-300 dark:border-gray-700 dark:bg-gray-900"
      role="complementary"
      aria-label="Notifications"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b dark:border-gray-700">
        <span className="font-semibold text-sm text-gray-800 dark:text-gray-200">
          Notifications{" "}
          {notifications.length > 0 && `(${notifications.length})`}
        </span>
        <div className="flex items-center gap-1">
          {notifications.length > 0 && (
            <button
              onClick={dismissAll}
              className="flex items-center gap-1 rounded px-2 py-1 text-xs text-gray-500 hover:bg-slate-300 dark:hover:bg-gray-700"
            >
              <Trash2 className="h-3 w-3" />
              Clear all
            </button>
          )}
          <button
            onClick={closeTray}
            className="rounded p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            aria-label="Close notifications"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {notifications.length === 0 ? (
          <p className="text-center text-sm text-gray-400 mt-8">
            No notifications
          </p>
        ) : (
          notifications.map((n, index) => (
            <NotificationRow
              key={n.id}
              {...n}
              defaultExpanded={index === 0}
              onDismiss={dismiss}
            />
          ))
        )}
      </div>
    </div>
  );
}
