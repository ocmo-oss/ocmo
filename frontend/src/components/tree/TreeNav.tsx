import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { treeApi } from "../../api/tree";
import { locksApi } from "../../api/locks";
import { partitionBuiltinChildren } from "../../lib/builtinPaths";
import { TreeNodeComponent } from "./TreeNode";
import { NamespaceConfigsFolder } from "./NamespaceConfigsFolder";
import { SkeletonList } from "../ui/Skeleton";
import { useTreeSearchStore } from "../../store/treeSearch";
import { isTreeNodeVisible } from "../../lib/treeFilter";
import { useNamespacePermissions } from "../../hooks/useNamespacePermissions";
import { useLockPermissions } from "../../hooks/useLockPermissions";

export function TreeNav() {
  const { namespace } = useParams<{ namespace: string }>();
  const { canWrite } = useNamespacePermissions(namespace);
  const { canRead: canReadLocks, isReady: lockPermissionsReady } =
    useLockPermissions(namespace);
  const debouncedQuery = useTreeSearchStore((s) => s.debouncedQuery);
  const searchActive = debouncedQuery.length > 0;

  const { data, isLoading, error } = useQuery({
    queryKey: ["tree-nav-root", namespace],
    queryFn: ({ signal }) =>
      treeApi.navigate(namespace!, null, { limit: 200 }, signal),
    enabled: !!namespace,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });

  const { data: searchResults, isLoading: searchLoading } = useQuery({
    queryKey: ["tree-search", namespace, debouncedQuery],
    queryFn: ({ signal }) =>
      treeApi.search(
        namespace!,
        null,
        { q: debouncedQuery, limit: 200 },
        signal,
      ),
    enabled: !!namespace && searchActive,
    staleTime: 10_000,
  });

  const { data: locksData } = useQuery({
    queryKey: ["locks", namespace],
    queryFn: ({ signal }) => locksApi.list(namespace!, { limit: 200 }, signal),
    enabled: !!namespace && lockPermissionsReady && canReadLocks,
    staleTime: 15_000,
  });

  const matchingPaths = useMemo(
    () => new Set(searchResults?.map((item) => item.path) ?? []),
    [searchResults],
  );

  const locks =
    lockPermissionsReady && canReadLocks ? (locksData?.locks ?? []) : [];

  if (isLoading) return <SkeletonList count={6} itemClassName="h-6 w-full" />;
  if (error)
    return <p className="p-2 text-xs text-red-500">Failed to load tree</p>;

  const { builtin, regular } = partitionBuiltinChildren(data?.children ?? []);
  const visibleRegularChildren = regular.filter((child) =>
    isTreeNodeVisible(child.path, matchingPaths, searchActive),
  );

  const noSearchResults =
    searchActive && !searchLoading && matchingPaths.size === 0;

  return (
    <nav aria-label="Configuration tree" className="min-w-max py-1">
      {searchActive && searchLoading ? (
        <SkeletonList count={4} itemClassName="h-6 w-full" />
      ) : noSearchResults ? (
        <p className="px-3 py-2 text-xs text-gray-400">
          No results for "{debouncedQuery}"
        </p>
      ) : (
        <>
          {canWrite && (
            <NamespaceConfigsFolder
              items={builtin}
              matchingPaths={matchingPaths}
              searchActive={searchActive}
              locks={locks}
            />
          )}
          {!searchActive && (data?.children.length ?? 0) === 0 && (
            <p className="px-3 py-2 text-xs text-gray-400">Empty namespace</p>
          )}
          {visibleRegularChildren.map((item) => (
            <TreeNodeComponent
              key={item.path}
              item={item}
              depth={0}
              matchingPaths={matchingPaths}
              searchActive={searchActive}
              locks={locks}
            />
          ))}
        </>
      )}
    </nav>
  );
}
