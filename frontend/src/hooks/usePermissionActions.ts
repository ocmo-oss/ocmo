import { useQuery } from "@tanstack/react-query";
import { fetchConfigDataSchema } from "../api/schema";
import {
  extractPermissionActionEnum,
  FALLBACK_PERMISSION_ACTIONS,
  PERMISSIONS_POLICY_CONFIG_PATH,
} from "../lib/permissionSchema";

export function usePermissionActions(
  namespace: string | undefined,
  enabled = true,
) {
  const { data, isLoading } = useQuery({
    queryKey: ["permission-actions", namespace],
    queryFn: async ({ signal }) => {
      const schema = await fetchConfigDataSchema(
        namespace!,
        PERMISSIONS_POLICY_CONFIG_PATH,
        undefined,
        signal,
      );
      if (!schema) {
        return [...FALLBACK_PERMISSION_ACTIONS];
      }
      const actions = extractPermissionActionEnum(schema);
      return actions.length > 0 ? actions : [...FALLBACK_PERMISSION_ACTIONS];
    },
    enabled: enabled && !!namespace,
    staleTime: Number.POSITIVE_INFINITY,
  });

  return {
    isLoading,
    actions: data ?? FALLBACK_PERMISSION_ACTIONS,
  };
}
