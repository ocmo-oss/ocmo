import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getUserManager } from '../auth/oidc'
import { useAuth } from '../auth/useAuth'
import { Button } from '../components/ui/Button'

export function LoginPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!loading && user?.access_token && !user.expired) {
      navigate('/', { replace: true })
    }
  }, [user, loading, navigate])

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 px-4">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-600 text-white text-3xl font-bold select-none shadow-lg">
        O
      </div>
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">OCMO</h1>
        <p className="mt-1 text-sm text-gray-500">Config management platform</p>
      </div>
      <Button
        variant="primary"
        size="lg"
        onClick={() => void getUserManager().signinRedirect()}
      >
        Sign in with SSO
      </Button>
    </div>
  )
}

/** Handles the OIDC redirect callback — token exchange runs in AuthProvider. */
export function LoginCallbackPage() {
  const { user, loading, bootError } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (loading) return
    if (bootError || !user?.access_token || user.expired) {
      navigate('/login', { replace: true })
      return
    }
    const returnUrl = typeof user.state === 'string' ? user.state : '/'
    navigate(returnUrl, { replace: true })
  }, [user, loading, bootError, navigate])

  return (
    <div className="flex h-full items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
    </div>
  )
}
