import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { DescriptionMarkdown } from "../ui/DescriptionMarkdown";

interface DescriptionReadModalProps {
  open: boolean;
  onClose: () => void;
  description: string;
}

export function DescriptionReadModal({
  open,
  onClose,
  description,
}: DescriptionReadModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-6 backdrop-blur-sm"
      onClick={(event) => {
        if (event.target === overlayRef.current) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="description-read-modal-title"
    >
      <div className="flex w-full max-w-5xl max-h-[min(48rem,calc(100vh-3rem))] flex-col rounded-lg bg-surface-elevated shadow-xl dark:bg-gray-900">
        <div className="flex shrink-0 items-center justify-between border-b px-6 py-4 dark:border-gray-700">
          <h2
            id="description-read-modal-title"
            className="text-base font-semibold text-gray-900 dark:text-gray-100"
          >
            Description
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
          <DescriptionMarkdown>{description}</DescriptionMarkdown>
        </div>
      </div>
    </div>
  );
}
