import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { refreshTreeQueries } from "../lib/treeQuery";

export function useReloadTreeBranch(namespace: string | undefined) {
  const qc = useQueryClient();
  const [reloading, setReloading] = useState(false);

  const reloadBranch = useCallback(
    async (branchPath?: string) => {
      if (!namespace || reloading) return;
      setReloading(true);
      try {
        await refreshTreeQueries(
          qc,
          namespace,
          ...(branchPath ? [branchPath] : []),
        );
      } finally {
        setReloading(false);
      }
    },
    [namespace, qc, reloading],
  );

  return { reloadBranch, reloading };
}
