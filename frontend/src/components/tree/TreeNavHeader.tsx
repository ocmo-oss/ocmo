import { RefreshCw } from "lucide-react";
import { useParams } from "react-router-dom";
import { useReloadTreeBranch } from "../../hooks/useReloadTreeBranch";
import { Tooltip } from "../ui/Tooltip";
import { cn } from "../ui/cn";

export function TreeNavHeader() {
  const { namespace } = useParams<{ namespace: string }>();
  const { reloadBranch, reloading } = useReloadTreeBranch(namespace);

  return (
    <div
      className="flex shrink-0 items-center justify-between border-b px-2 py-0.5 dark:border-gray-700"
    >
      <span className="text-[11px] font-medium text-gray-500 dark:text-gray-400">
        Tree
      </span>
      <Tooltip content="Reload tree" side="bottom" align="end">
        <button
          type="button"
          onClick={() => void reloadBranch()}
          disabled={reloading}
          className={cn(
            "flex h-5 w-5 items-center justify-center rounded text-gray-500",
            "hover:bg-slate-200 hover:text-gray-700",
            "dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-200",
            "disabled:cursor-wait disabled:opacity-60",
          )}
          aria-label="Reload tree"
        >
          <RefreshCw
            className={cn("h-3 w-3", reloading && "animate-spin")}
          />
        </button>
      </Tooltip>
    </div>
  );
}
