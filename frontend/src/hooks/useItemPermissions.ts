import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { authApi } from '../api/auth'
import type { ItemType } from '../api/types'
import { allPermissionOps, permissionOpsForType } from '../lib/itemPermissions'
import { usePermissionActions } from './usePermissionActions'

export function useItemPermissions(namespace: string, path: string, type: ItemType, enabled = true) {
  const { actions } = usePermissionActions(namespace, enabled)
  const ops = allPermissionOps(type, actions)
  const opMap = permissionOpsForType(type, actions)

  const { data, isLoading } = useQuery({
    queryKey: ['can-i', namespace, path, type, ops],
    queryFn: ({ signal }) => authApi.canI({ namespace, resource: path, operations: ops }, signal),
    enabled: enabled && !!namespace && !!path,
    staleTime: 30_000,
    placeholderData: keepPreviousData,
  })

  const allowed = data?.allowed ?? {}

  return {
    isLoading,
    canRead: allowed[opMap.read] ?? false,
    canWrite: allowed[opMap.write] ?? false,
    canDelete: allowed[opMap.delete] ?? false,
    canMove: (allowed[opMap.read] ?? false) && (allowed[opMap.delete] ?? false),
    canCopy: allowed[opMap.read] ?? false,
    canDescribe: allowed[opMap.describe] ?? false,
    canTag: allowed[opMap.tag] ?? false,
    canAudit: allowed[opMap.audit] ?? false,
    canResolve: opMap.resolve ? (allowed[opMap.resolve] ?? false) : false,
  }
}
