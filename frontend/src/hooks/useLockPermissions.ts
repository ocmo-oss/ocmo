import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { authApi } from '../api/auth'
import { lockPermissionOps } from '../lib/permissionSchema'
import { usePermissionActions } from './usePermissionActions'

export function useLockPermissions(namespace: string | undefined, enabled = true) {
  const queryEnabled = enabled && !!namespace
  const { actions } = usePermissionActions(namespace, queryEnabled)
  const lockOps = useMemo(() => lockPermissionOps(actions), [actions])

  const { data, isFetched } = useQuery({
    queryKey: ['can-i', 'locks', namespace, lockOps],
    queryFn: ({ signal }) =>
      authApi.canI(
        { namespace: namespace!, resource: '', operations: lockOps },
        signal,
      ),
    enabled: queryEnabled && lockOps.length > 0,
    staleTime: 30_000,
  })

  const allowed = isFetched ? (data?.allowed ?? {}) : {}

  return {
    isLoading: queryEnabled && !isFetched,
    isReady: isFetched,
    canRead: allowed['lock:read'] ?? false,
    canWrite: allowed['lock:write'] ?? false,
    canDelete: allowed['lock:delete'] ?? false,
  }
}
