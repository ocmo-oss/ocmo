import { Link } from "react-router-dom";
import {
  ChevronRight,
  Copy,
  CopyPlus,
  FolderInput,
  Route,
  Trash2,
} from "lucide-react";
import { ItemIcon } from "../../lib/itemTypes";
import type { ItemType, TagInfo } from "../../api/types";
import { pathSegments } from "../../lib/paths";
import { Button } from "../ui/Button";
import { showToast } from "../ui/Toast";
import { pushNotification } from "../../store/notifications";
import { VersionTagSelector } from "./VersionTagSelector";

interface ItemHeaderProps {
  namespace: string;
  path: string;
  type: ItemType;
  version?: number;
  tags?: TagInfo[];
  showVersionSelector?: boolean;
  deletedAt?: string | null;
  onDelete?: () => void;
  onMove?: () => void;
  onCopy?: () => void;
  onPropagate?: () => void;
}

export function ItemHeader({
  namespace,
  path,
  type,
  version,
  tags,
  showVersionSelector = false,
  deletedAt,
  onDelete,
  onMove,
  onCopy,
  onPropagate,
}: ItemHeaderProps) {
  const segments = pathSegments(path);

  const copyPath = async () => {
    try {
      await navigator.clipboard.writeText(path);
      showToast("Path copied to clipboard");
    } catch {
      pushNotification("error", "Failed to copy path");
    }
  };

  return (
    <div className="border-b px-6 py-4 dark:border-gray-700">
      <nav
        className="mb-2 flex items-center gap-1 text-xs text-gray-400"
        aria-label="Breadcrumbs"
      >
        {segments.map((seg, i) => {
          const segPath = segments.slice(0, i + 1).join("/");
          return (
            <span key={segPath} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="h-3 w-3" />}
              <Link
                to={`/ns/${namespace}/configs/${segPath}`}
                className="font-mono hover:text-gray-600 dark:hover:text-gray-300"
              >
                {seg}
              </Link>
            </span>
          );
        })}
        <button
          type="button"
          onClick={() => void copyPath()}
          title="Copy full path"
          aria-label="Copy full path"
          className="ml-1 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded text-gray-400 hover:bg-slate-200 hover:text-gray-600 dark:hover:bg-gray-800 dark:hover:text-gray-300"
        >
          <Copy className="h-3 w-3" />
        </button>
      </nav>

      <div className="flex items-center gap-3">
        <ItemIcon type={type} />
        <h1 className="font-mono text-base font-semibold text-gray-900 dark:text-gray-100">
          {segments[segments.length - 1]}
        </h1>
        {showVersionSelector && version !== undefined && tags && (
          <VersionTagSelector
            namespace={namespace}
            path={path}
            currentVersion={version}
            tags={tags}
            deletedAt={deletedAt}
          />
        )}

        <div className="ml-auto flex items-center gap-1">
          {onPropagate && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onPropagate}
              title="Manual propagation"
            >
              <Route className="h-3.5 w-3.5" />
            </Button>
          )}
          {onCopy && (
            <Button variant="ghost" size="sm" onClick={onCopy} title="Copy">
              <CopyPlus className="h-3.5 w-3.5" />
            </Button>
          )}
          {onMove && (
            <Button variant="ghost" size="sm" onClick={onMove} title="Move">
              <FolderInput className="h-3.5 w-3.5" />
            </Button>
          )}
          {onDelete && (
            <Button variant="ghost" size="sm" onClick={onDelete} title="Delete">
              <Trash2 className="h-3.5 w-3.5 text-red-500" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
