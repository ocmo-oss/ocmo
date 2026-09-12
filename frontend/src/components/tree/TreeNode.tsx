import { useEffect, useState, type MouseEvent } from "react";
import { NavLink, useParams } from "react-router-dom";
import { ChevronRight, ChevronDown } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type { Lock, TreeNavigationNode } from "../../api/types";
import { useReloadTreeBranch } from "../../hooks/useReloadTreeBranch";
import { resolveFolderChain } from "../../lib/folderChain";
import {
  isTreeFolderAutoExpanded,
  isTreeNodeVisible,
} from "../../lib/treeFilter";
import { getLockForPath } from "../../lib/treeLocks";
import { treeItemHref } from "../../lib/treeItemHref";
import { ItemIcon } from "../../lib/itemTypes";
import { TreeBranchContextMenu } from "./TreeBranchContextMenu";
import { TreeLockIndicator } from "./TreeLockIndicator";
import { SkeletonList } from "../ui/Skeleton";
import { cn } from "../ui/cn";
import { isPathUnderFolder } from "../../lib/treeBranch";
import { useTreeExpansionStore } from "../../store/treeExpansion";

interface TreeNodeProps {
  item: TreeNavigationNode;
  depth: number;
  matchingPaths: Set<string>;
  searchActive: boolean;
  locks: Lock[];
}

function FolderChainLabel({
  segments,
  namespace,
  onIsolateBranch,
}: {
  segments: Array<{ name: string; path: string }>;
  namespace: string;
  onIsolateBranch?: () => void;
}) {
  return (
    <span className="flex items-center gap-0.5 whitespace-nowrap font-mono">
      {segments.map((seg, index) => (
        <span key={seg.path} className="flex items-center gap-0.5">
          {index > 0 && <span className="shrink-0 text-gray-400">/</span>}
          <NavLink
            to={`/ns/${namespace}/configs/${seg.path}`}
            onClick={(e) => e.stopPropagation()}
            onDoubleClick={(e) => {
              if (index !== segments.length - 1 || !onIsolateBranch) return;
              e.preventDefault();
              onIsolateBranch();
            }}
            className={({ isActive }) =>
              cn(
                "hover:text-brand-700 dark:hover:text-brand-300",
                isActive && "font-medium text-brand-700 dark:text-brand-300",
              )
            }
          >
            {seg.name}
          </NavLink>
        </span>
      ))}
    </span>
  );
}

function TreeItemLabel({
  item,
  segments,
  namespace,
  href,
  isFolder,
  onIsolateBranch,
}: {
  item: TreeNavigationNode;
  segments?: Array<{ name: string; path: string }>;
  namespace: string;
  href: string;
  isFolder: boolean;
  onIsolateBranch?: () => void;
}) {
  const labelClass = ({ isActive }: { isActive: boolean }) =>
    cn(
      "flex items-center gap-1.5 whitespace-nowrap rounded py-0.5 text-xs",
      "text-gray-700 dark:text-gray-300",
      isActive && "font-medium text-brand-700 dark:text-brand-300",
    );

  if (isFolder && segments && segments.length > 1) {
    return (
      <span className={labelClass({ isActive: false })}>
        <ItemIcon type="folder" />
        <FolderChainLabel
          segments={segments}
          namespace={namespace}
          onIsolateBranch={onIsolateBranch}
        />
      </span>
    );
  }

  return (
    <NavLink
      to={href}
      onDoubleClick={(e) => {
        if (!onIsolateBranch) return;
        e.preventDefault();
        onIsolateBranch();
      }}
      className={labelClass}
    >
      <ItemIcon type={isFolder ? "folder" : item.type} />
      {isFolder && segments ? (
        <span className="whitespace-nowrap font-mono">{segments[0].name}</span>
      ) : (
        <span className="whitespace-nowrap font-mono">{item.name}</span>
      )}
    </NavLink>
  );
}

export function TreeNodeComponent({
  item,
  depth,
  matchingPaths,
  searchActive,
  locks,
}: TreeNodeProps) {
  const { namespace, "*": currentItemPath } = useParams<{
    namespace: string;
    "*": string;
  }>();
  const [userExpanded, setUserExpanded] = useState(false);
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const isolateRevision = useTreeExpansionStore((s) => s.isolateRevision);
  const isolatedPath = useTreeExpansionStore((s) => s.isolatedPath);
  const isolateToCurrentPath = useTreeExpansionStore(
    (s) => s.isolateToCurrentPath,
  );
  const { reloadBranch, reloading } = useReloadTreeBranch(namespace);
  const isFolder = item.type === "folder";
  const indent = depth * 12;
  const lockInfo = getLockForPath(item.path, locks);

  const { data: chain, isLoading: chainLoading } = useQuery({
    queryKey: ["folder-chain", namespace, item.path],
    queryFn: ({ signal }) => resolveFolderChain(namespace!, item, signal),
    enabled: isFolder && !!namespace,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });

  const folderTerminalPath = chain?.terminal.path ?? item.path;

  useEffect(() => {
    if (!isFolder || !isolatedPath) return;
    if (!isPathUnderFolder(folderTerminalPath, isolatedPath)) {
      setUserExpanded(false);
    }
  }, [isolateRevision, isolatedPath, folderTerminalPath, isFolder]);

  const rowClass =
    "group flex items-center gap-1 rounded-sm py-0.5 pr-2 hover:bg-slate-200 dark:hover:bg-gray-800";

  if (!isFolder) {
    if (!isTreeNodeVisible(item.path, matchingPaths, searchActive)) return null;

    const href = treeItemHref(namespace!, item.path, false);
    const isCurrent = currentItemPath === item.path;
    return (
      <div className={rowClass} style={{ paddingLeft: `${indent + 8}px` }}>
        <span className="w-3.5 shrink-0" />
        <TreeItemLabel
          item={item}
          namespace={namespace!}
          href={href}
          isFolder={false}
          onIsolateBranch={
            isCurrent ? () => isolateToCurrentPath(item.path) : undefined
          }
        />
        {lockInfo && <TreeLockIndicator lockInfo={lockInfo} />}
      </div>
    );
  }

  const segments = chain?.segments ?? [{ name: item.name, path: item.path }];
  const terminalPath = chain?.terminal.path ?? item.path;
  const children = chain?.children ?? [];

  const nodeVisible =
    segments.some((segment) =>
      isTreeNodeVisible(segment.path, matchingPaths, searchActive),
    ) ||
    children.some((child) =>
      isTreeNodeVisible(child.path, matchingPaths, searchActive),
    );

  if (!nodeVisible) return null;

  const autoExpanded =
    searchActive &&
    (isTreeFolderAutoExpanded(terminalPath, matchingPaths) ||
      segments.some((segment) =>
        isTreeFolderAutoExpanded(segment.path, matchingPaths),
      ));
  const routeExpanded =
    !!currentItemPath &&
    !currentItemPath.startsWith("new/") &&
    isPathUnderFolder(terminalPath, currentItemPath);
  const expanded = searchActive
    ? autoExpanded || userExpanded || routeExpanded
    : userExpanded || routeExpanded;

  const visibleChildren = children.filter((child) =>
    isTreeNodeVisible(child.path, matchingPaths, searchActive),
  );
  const href = treeItemHref(namespace!, terminalPath, true);
  const terminalLockInfo = getLockForPath(terminalPath, locks) ?? lockInfo;
  const isCurrent = currentItemPath === terminalPath;

  const openContextMenu = (e: MouseEvent) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY });
  };

  const handleReload = () => {
    void reloadBranch(item.path).then(() => setContextMenu(null));
  };

  return (
    <div>
      <div
        className={rowClass}
        style={{ paddingLeft: `${indent + 8}px` }}
        onContextMenu={openContextMenu}
      >
        <button
          type="button"
          onClick={() => setUserExpanded((e) => !e)}
          className="flex shrink-0 items-center text-gray-400 hover:text-gray-600 dark:text-gray-500"
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
          className="flex items-center gap-1"
          onClick={() => setUserExpanded((e) => !e)}
        >
          <TreeItemLabel
            item={item}
            segments={segments}
            namespace={namespace!}
            href={href}
            isFolder
            onIsolateBranch={
              isCurrent ? () => isolateToCurrentPath(terminalPath) : undefined
            }
          />
          {terminalLockInfo && (
            <TreeLockIndicator lockInfo={terminalLockInfo} />
          )}
        </div>
      </div>

      {contextMenu && (
        <TreeBranchContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          reloading={reloading}
          onClose={() => setContextMenu(null)}
          onReload={handleReload}
        />
      )}

      {expanded && (
        <div>
          {chainLoading && (
            <SkeletonList count={2} itemClassName="h-5 w-full ml-6" />
          )}
          {!chainLoading &&
            visibleChildren.map((child) => (
              <TreeNodeComponent
                key={child.path}
                item={child}
                depth={depth + 1}
                matchingPaths={matchingPaths}
                searchActive={searchActive}
                locks={locks}
              />
            ))}
          {!chainLoading && visibleChildren.length === 0 && (
            <p
              className="px-2 py-0.5 text-xs text-gray-400"
              style={{ paddingLeft: `${indent + 24}px` }}
            >
              {searchActive ? "No matching items" : "Empty"}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
