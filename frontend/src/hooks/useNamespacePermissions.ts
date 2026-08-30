import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { authApi } from "../api/auth";

const NAMESPACE_OPS = [
  "namespace:read",
  "namespace:write",
  "namespace:delete",
  "namespace:audit",
] as const;

export function useNamespacePermissions(
  namespace: string | undefined,
  enabled = true,
) {
  const { data, isLoading } = useQuery({
    queryKey: ["can-i", "namespace", namespace],
    queryFn: ({ signal }) =>
      authApi.canI(
        { namespace: namespace!, operations: [...NAMESPACE_OPS] },
        signal,
      ),
    enabled: enabled && !!namespace,
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  });

  const allowed = data?.allowed ?? {};

  return {
    isLoading,
    canRead: allowed["namespace:read"] ?? false,
    canWrite: allowed["namespace:write"] ?? false,
    canDelete: allowed["namespace:delete"] ?? false,
    canAudit: allowed["namespace:audit"] ?? false,
  };
}
