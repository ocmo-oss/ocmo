import { useEffect, useRef } from 'react'
import { Navigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { namespacesApi } from '../api/namespaces'
import { useDefaultNamespace } from '../store/defaultNamespace'
import { pushNotification } from '../store/notifications'
import { Skeleton } from '../components/ui/Skeleton'

export function DefaultNamespaceGate() {
  const { namespace: defaultNamespace, clearDefaultNamespace } = useDefaultNamespace()
  const clearedStale = useRef(false)

  const { data, isLoading } = useQuery({
    queryKey: ['namespaces', 'default-gate'],
    queryFn: ({ signal }) => namespacesApi.list({ limit: 500 }, signal),
    staleTime: 30_000,
  })

  const isAccessible =
    defaultNamespace != null &&
    data?.items.some(ns => ns.name === defaultNamespace)

  useEffect(() => {
    if (isLoading || !defaultNamespace || isAccessible || clearedStale.current) return
    clearedStale.current = true
    clearDefaultNamespace()
    pushNotification(
      'info',
      'Default namespace removed',
      `"${defaultNamespace}" is no longer available. Open All namespaces to choose another.`,
    )
  }, [isLoading, defaultNamespace, isAccessible, clearDefaultNamespace])

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl space-y-2 px-6 py-8">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    )
  }

  if (defaultNamespace && isAccessible) {
    return (
      <Navigate
        to={`/ns/${defaultNamespace}/configs`}
        replace
        state={{ defaultNamespaceRedirect: true }}
      />
    )
  }

  return <Navigate to="/namespaces" replace />
}
