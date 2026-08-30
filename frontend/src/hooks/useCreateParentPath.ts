import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { treeApi } from "../api/tree";
import { pathParent } from "../lib/paths";

/** Parent folder path for a new item based on the currently open tree item. */
export function useCreateParentPath(): string {
  const { namespace, "*": currentPath } = useParams<{
    namespace: string;
    "*": string;
  }>();
  const isCreateRoute = !!currentPath?.startsWith("new/");

  const { data } = useQuery({
    queryKey: ["item", namespace, currentPath],
    queryFn: ({ signal }) => treeApi.get(namespace!, currentPath!, {}, signal),
    enabled: !!namespace && !!currentPath && !isCreateRoute,
    staleTime: 30_000,
  });

  return useMemo(() => {
    if (!currentPath || isCreateRoute) return "";
    if (data?.type === "folder") return currentPath;
    return pathParent(currentPath);
  }, [currentPath, isCreateRoute, data?.type]);
}
