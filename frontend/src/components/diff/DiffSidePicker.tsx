import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { treeApi } from "../../api/tree";
import type { ItemType } from "../../api/types";
import { isDiffableType } from "../../lib/diffableTypes";
import { ItemIcon, ITEM_TYPE_LABELS } from "../../lib/itemTypes";
import { VersionTagSelector } from "../items/VersionTagSelector";
import { PathSearchCombobox } from "./PathSearchCombobox";
import { Skeleton } from "../ui/Skeleton";
import { cn } from "../ui/cn";

interface DiffSidePickerProps {
  namespace: string;
  label: string;
  path: string;
  itemType: ItemType | null;
  onPathChange: (path: string) => void;
  onItemTypeChange: (type: ItemType | null) => void;
  versionRef: string;
  onVersionRefChange: (ref: string) => void;
  compact?: boolean;
}

export function DiffSidePicker({
  namespace,
  label,
  path,
  itemType,
  onPathChange,
  onItemTypeChange,
  versionRef,
  onVersionRefChange,
  compact = false,
}: DiffSidePickerProps) {
  const trimmedPath = path.trim();

  const { data, isLoading, error } = useQuery({
    queryKey: ["item", namespace, trimmedPath, "diff-side"],
    queryFn: ({ signal }) => treeApi.get(namespace, trimmedPath, {}, signal),
    enabled: Boolean(trimmedPath),
    staleTime: 30_000,
  });

  useEffect(() => {
    if (!trimmedPath) {
      onItemTypeChange(null);
      return;
    }
    if (data) {
      onItemTypeChange(data.type);
    }
  }, [trimmedPath, data, onItemTypeChange]);

  const resolvedType = data?.type ?? itemType;
  const showVersionSelector =
    data &&
    !isLoading &&
    !error &&
    (data.type === "config" ||
      data.type === "template" ||
      data.type === "secret");

  return (
    <div
      className={cn(
        "space-y-2.5 rounded-lg border border-slate-300 dark:border-gray-700",
        compact ? "p-3" : "space-y-3 p-4",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-gray-800 dark:text-gray-200">
          {label}
        </h2>
        {resolvedType && (
          <span className="flex items-center gap-1.5 rounded-md bg-slate-200 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-800 dark:text-gray-300">
            <ItemIcon type={resolvedType} size="sm" showTooltip={false} />
            {ITEM_TYPE_LABELS[resolvedType]}
          </span>
        )}
      </div>

      <PathSearchCombobox
        namespace={namespace}
        value={path}
        filterItem={(item) => isDiffableType(item.type)}
        emptyMessage="No matching configs, templates, secrets, or resolvers"
        onInputChange={(nextPath) => {
          onPathChange(nextPath);
          onItemTypeChange(null);
        }}
        onSelect={(item) => {
          onPathChange(item.path);
          onItemTypeChange(item.type);
        }}
      />

      {trimmedPath && isLoading && <Skeleton className="h-8 w-36" />}

      {trimmedPath && !isLoading && error && (
        <p className="text-xs text-red-500">{(error as Error).message}</p>
      )}

      {trimmedPath && !isLoading && data && !isDiffableType(data.type) && (
        <p className="text-xs text-gray-400">
          Diff is only supported for configs, templates, secrets, and resolvers.
        </p>
      )}

      {showVersionSelector && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Version
          </p>
          <VersionTagSelector
            namespace={namespace}
            path={trimmedPath}
            currentVersion={data.version}
            tags={data.tags}
            deletedAt={data.deleted_at}
            value={versionRef}
            onChange={onVersionRefChange}
          />
        </div>
      )}
    </div>
  );
}
