import React, { createContext, useCallback, useEffect, useRef, useState } from 'react'
import type { User } from 'oidc-client-ts'
import { getUserManager, initUserManager } from './oidc'
import { shouldSkipSilentRenew, LOGIN_PATH, LOGIN_CALLBACK_PATH } from './authPaths'
import { ApiError, setTokenProvider, clearTokenProvider } from '../api/client'
import type { WhoAmI } from '../api/types'
import { authApi } from '../api/auth'
import { formatFetchFailureMessage } from '../lib/apiAvailability'

export interface AuthState {
  user: User | null
  whoami: WhoAmI | null
  loading: boolean
  bootError: string | null
  isGlobalAdmin: boolean
  login: () => Promise<void>
  logout: () => Promise<void>
  silentRenew: () => Promise<void>
  /** Re-read OIDC user from storage and refresh whoami (after redirect callback). */
  syncSession: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

/** Survives React StrictMode remounts — OAuth codes are single-use. */
let redirectCallbackHandled = false

async function restoreUser(): Promise<User | null> {
  const userManager = getUserManager()
  const stored = await userManager.getUser()
  if (stored?.access_token && !stored.expired) return stored

  if (shouldSkipSilentRenew(window.location.pathname)) {
    if (stored?.expired) await userManager.removeUser()
    return null
  }

  if (!stored) return null

  if (stored.expired) await userManager.removeUser()

  try {
    return await userManager.signinSilent()
  } catch {
    return null
  }
}

async function bootstrapSession(): Promise<User | null> {
  const userManager = getUserManager()

  if (window.location.pathname === LOGIN_CALLBACK_PATH) {
    if (redirectCallbackHandled) {
      return userManager.getUser()
    }
    redirectCallbackHandled = true
    try {
      return await userManager.signinRedirectCallback()
    } catch (err) {
      redirectCallbackHandled = false
      throw err
    }
  }

  return restoreUser()
}

function isOidcStorageKey(key: string | null): boolean {
  return key?.startsWith('oidc.') ?? false
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [whoami, setWhoami] = useState<WhoAmI | null>(null)
  const [loading, setLoading] = useState(true)
  const [bootError, setBootError] = useState<string | null>(null)

  const accessTokenRef = useRef<string | null>(null)
  const whoamiRequestRef = useRef(0)

  useEffect(() => {
    setTokenProvider(() => accessTokenRef.current)
    return () => clearTokenProvider()
  }, [])

  const loadWhoami = useCallback(async (token: string) => {
    const requestId = ++whoamiRequestRef.current
    try {
      accessTokenRef.current = token
      const data = await authApi.whoami()
      if (requestId !== whoamiRequestRef.current) return
      if (accessTokenRef.current !== token) return
      setWhoami(data)
    } catch (err) {
      if (requestId !== whoamiRequestRef.current) return
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        const current = (await getUserManager().getUser())?.access_token
        if (current !== token) return

        setWhoami(null)
        accessTokenRef.current = null
        clearTokenProvider()
        await getUserManager().removeUser()
        setUser(null)
      }
    }
  }, [])

  const applySession = useCallback(async (session: User | null | undefined) => {
    if (!session?.access_token || session.expired) return
    accessTokenRef.current = session.access_token
    setUser(session)
    await loadWhoami(session.access_token)
  }, [loadWhoami])

  const syncSession = useCallback(async () => {
    const stored = await getUserManager().getUser()
    await applySession(stored)
  }, [applySession])

  useEffect(() => {
    let cancelled = false

    const onUserLoaded = (u: User) => {
      void applySession(u)
    }
    const onUserUnloaded = () => {
      setUser(null)
      setWhoami(null)
      accessTokenRef.current = null
      clearTokenProvider()
    }
    const onTokenExpired = () => {
      void getUserManager().signinSilent().catch(() => {
        void getUserManager().removeUser()
      })
    }

    const init = async () => {
      try {
        const userManager = await initUserManager()

        userManager.events.addUserLoaded(onUserLoaded)
        userManager.events.addUserUnloaded(onUserUnloaded)
        userManager.events.addAccessTokenExpired(onTokenExpired)

        const session = (await bootstrapSession()) ?? (await userManager.getUser())
        if (!cancelled) {
          await applySession(session)
        }
      } catch (err) {
        if (!cancelled) {
          setBootError(formatFetchFailureMessage(err))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void init()

    const onStorage = (event: StorageEvent) => {
      if (!isOidcStorageKey(event.key)) return
      void (async () => {
        try {
          const um = getUserManager()
          const u = await um.getUser()
          if (cancelled) return
          if (u?.access_token && !u.expired) {
            await applySession(u)
            return
          }
          setUser(null)
          setWhoami(null)
          accessTokenRef.current = null
          clearTokenProvider()
        } catch {
          // initUserManager not finished yet
        }
      })()
    }
    window.addEventListener('storage', onStorage)

    return () => {
      cancelled = true
      window.removeEventListener('storage', onStorage)
      try {
        const um = getUserManager()
        um.events.removeUserLoaded(onUserLoaded)
        um.events.removeUserUnloaded(onUserUnloaded)
        um.events.removeAccessTokenExpired(onTokenExpired)
      } catch {
        // not initialized
      }
    }
  }, [applySession])

  // Heal: OIDC session present but whoami missing (race or transient failure).
  useEffect(() => {
    if (loading || !user?.access_token || user.expired || whoami) return
    void loadWhoami(user.access_token)
  }, [loading, user, whoami, loadWhoami])

  const login = useCallback(async () => {
    const returnUrl = window.location.pathname + window.location.search
    await getUserManager().signinRedirect({ state: returnUrl })
  }, [])

  const logout = useCallback(async () => {
    accessTokenRef.current = null
    clearTokenProvider()
    setWhoami(null)
    setUser(null)
    const userManager = getUserManager()
    await userManager.removeUser()
    try {
      await userManager.signoutRedirect()
    } catch {
      window.location.assign(LOGIN_PATH)
    }
  }, [])

  const silentRenew = useCallback(async () => {
    const u = await getUserManager().signinSilent()
    await applySession(u)
  }, [applySession])

  const isGlobalAdmin =
    whoami?.auth_type === 'user' ? whoami.user_details.is_global_admin : false

  if (bootError) {
    return (
      <div className="flex h-screen items-center justify-center px-4">
        <p className="max-w-md text-center text-sm text-red-600 dark:text-red-400">
          {bootError}
        </p>
      </div>
    )
  }

  return (
    <AuthContext.Provider value={{ user, whoami, loading, bootError, isGlobalAdmin, login, logout, silentRenew, syncSession }}>
      {children}
    </AuthContext.Provider>
  )
}
