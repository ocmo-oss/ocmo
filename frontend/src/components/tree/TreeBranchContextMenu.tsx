import { RefreshCw } from "lucide-react";
import { cn } from "../ui/cn";

interface TreeBranchContextMenuProps {
  x: number;
  y: number;
  reloading: boolean;
  onClose: () => void;
  onReload: () => void;
}

export function TreeBranchContextMenu({
  x,
  y,
  reloading,
  onClose,
  onReload,
}: TreeBranchContextMenuProps) {
  return (
    <>
      <div
        className="fixed inset-0 z-40"
        onClick={onClose}
        onContextMenu={(e) => e.preventDefault()}
      />
      <div
        role="menu"
        className="fixed z-50 min-w-36 rounded-lg border bg-surface-elevated p-1 shadow-lg dark:border-gray-700 dark:bg-gray-900"
        style={{ left: x, top: y }}
      >
        <button
          type="button"
          role="menuitem"
          disabled={reloading}
          onClick={onReload}
          className={cn(
            "flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-xs text-gray-700",
            "hover:bg-slate-200 dark:text-gray-200 dark:hover:bg-gray-800",
            "disabled:cursor-wait disabled:opacity-60",
          )}
        >
          <RefreshCw
            className={cn("h-3.5 w-3.5 shrink-0", reloading && "animate-spin")}
          />
          Reload
        </button>
      </div>
    </>
  );
}
