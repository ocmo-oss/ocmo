import type { ReactNode } from "react";
import { Minimize2 } from "lucide-react";
import { Button } from "../../ui/Button";
import { cn } from "../../ui/cn";

export function EditorFocusToolbar({
  onExit,
  saveButton,
  resolveButton,
  className,
}: {
  onExit: () => void;
  saveButton?: ReactNode;
  resolveButton?: ReactNode;
  className?: string;
}) {
  return (
    <div
      role="toolbar"
      aria-label="Focus editor"
      className={cn(
        "flex shrink-0 items-center gap-2 border-b px-3 py-2 dark:border-gray-700",
        className,
      )}
    >
      <Button
        variant="ghost"
        size="sm"
        type="button"
        onClick={onExit}
        title="Exit focus mode"
        aria-label="Exit focus mode"
      >
        <Minimize2 className="h-4 w-4" />
        <span className="hidden sm:inline">Exit focus</span>
      </Button>
      <div className="flex-1" />
      {saveButton}
      {resolveButton}
    </div>
  );
}
