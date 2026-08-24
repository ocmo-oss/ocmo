import { useEffect, useRef } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from './useAuth'
import { pushNotification } from '../store/notifications'

export function RequireGlobalAdmin({ children }: { children: React.ReactNode }) {
  const { isGlobalAdmin, loading } = useAuth()
  const notified = useRef(false)

  useEffect(() => {
    if (loading || isGlobalAdmin || notified.current) return
    notified.current = true
    pushNotification(
      'info',
      'Access denied',
      'Global administrator access is required for this page.',
    )
  }, [loading, isGlobalAdmin])

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    )
  }

  if (!isGlobalAdmin) {
    return <Navigate to="/namespaces" replace />
  }

  return <>{children}</>
}
