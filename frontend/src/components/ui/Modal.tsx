import React, { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";
import { registerModal, unregisterModal } from "../../store/modalStack";
import { useNotifications } from "../../store/notifications";
import { cn } from "./cn";
import { ModalNotificationBanner } from "./ModalNotificationBanner";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  size?: "sm" | "md" | "lg" | "xl";
  footer?: React.ReactNode;
}

const sizes = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-2xl",
};

export function Modal({
  open,
  onClose,
  title,
  children,
  size = "md",
  footer,
}: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const modalId = useId();
  const modalNotification = useNotifications(
    (s) => s.modalNotifications[modalId],
  );
  const clearModalNotification = useNotifications(
    (s) => s.clearModalNotification,
  );

  useEffect(() => {
    if (!open) return;
    registerModal(modalId);
    return () => {
      unregisterModal(modalId);
      clearModalNotification(modalId);
    };
  }, [open, modalId, clearModalNotification]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !e.defaultPrevented) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className={cn(
          "flex w-full max-h-[calc(100vh-2rem)] flex-col overflow-hidden rounded-lg bg-surface-elevated shadow-xl dark:bg-gray-900",
          sizes[size],
        )}
      >
        <div className="flex shrink-0 items-center justify-between border-b px-6 py-4 dark:border-gray-700">
          <h2
            id="modal-title"
            className="text-base font-semibold text-gray-900 dark:text-gray-100"
          >
            {title}
          </h2>
          <button
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {modalNotification && (
          <ModalNotificationBanner notification={modalNotification} />
        )}
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
          {children}
        </div>
        {footer && (
          <div className="flex shrink-0 justify-end gap-2 border-t px-6 py-4 dark:border-gray-700">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
