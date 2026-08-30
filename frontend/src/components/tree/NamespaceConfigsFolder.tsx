import { useState } from "react";
import { ChevronDown, ChevronRight, FolderCog } from "lucide-react";
import { useParams } from "react-router-dom";
import type { Lock, TreeNavigationNode } from "../../api/types";
import { useReloadTreeBranch } from "../../hooks/useReloadTreeBranch";
import { NAMESPACE_CONFIGS_FOLDER_LABEL } from "../../lib/builtinPaths";
import { isTreeNodeVisible } from "../../lib/treeFilter";
import { TreeBranchContextMenu } from "./TreeBranchContextMenu";
import { TreeNodeComponent } from "./TreeNode";

interface NamespaceConfigsFolderProps {
  items: TreeNavigationNode[];
  matchingPaths: Set<string>;
  searchActive: boolean;
  locks: Lock[];
}

export function NamespaceConfigsFolder({
  items,
  matchingPaths,
  searchActive,
  locks,
}: NamespaceConfigsFolderProps) {
  const { namespace } = useParams<{ namespace: string }>();
  const [expanded, setExpanded] = useState(true);
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const { reloadBranch, reloading } = useReloadTreeBranch(namespace);

  const visibleItems = items.filter((item) =>
    isTreeNodeVisible(item.path, matchingPaths, searchActive),
  );
  if (items.length === 0 || (searchActive && visibleItems.length === 0))
    return null;

  return (
    <div>
      <div
        className="group flex items-center gap-1 rounded-sm py-0.5 pr-2 hover:bg-slate-200 dark:hover:bg-gray-800"
        style={{ paddingLeft: "8px" }}
        onContextMenu={(e) => {
          e.preventDefault();
          setContextMenu({ x: e.clientX, y: e.clientY });
        }}
      >
        <button
          type="button"
          onClick={() => setExpanded((e) => !e)}
          className="flex shrink-0 items-center p-0 text-gray-400 hover:text-gray-600 dark:text-gray-500"
          aria-label={expanded ? "Collapse" : "Expand"}
          aria-expanded={expanded}
        >
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" />
          )}
        </button>
        <div
          className="flex items-center gap-1.5 whitespace-nowrap py-0.5 text-xs text-gray-700 dark:text-gray-300"
          onClick={() => setExpanded((e) => !e)}
        >
          <FolderCog
            className="h-4 w-4 shrink-0 text-amber-500"
            aria-hidden="true"
          />
          <span className="font-medium">{NAMESPACE_CONFIGS_FOLDER_LABEL}</span>
        </div>
      </div>

      {contextMenu && (
        <TreeBranchContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          reloading={reloading}
          onClose={() => setContextMenu(null)}
          onReload={() => {
            void reloadBranch().then(() => setContextMenu(null));
          }}
        />
      )}

      {expanded && (
        <div>
          {visibleItems.length === 0 && (
            <p
              className="px-2 py-0.5 text-xs text-gray-400"
              style={{ paddingLeft: "32px" }}
            >
              Empty
            </p>
          )}
          {visibleItems.map((item) => (
            <TreeNodeComponent
              key={item.path}
              item={item}
              depth={1}
              matchingPaths={matchingPaths}
              searchActive={searchActive}
              locks={locks}
            />
          ))}
        </div>
      )}
    </div>
  );
}
