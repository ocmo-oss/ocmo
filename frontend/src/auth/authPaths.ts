/** Paths used by the OIDC login and silent-renew flows (no RequireAuth). */
export const LOGIN_PATH = '/login'
export const LOGIN_CALLBACK_PATH = '/login/callback'
export const SILENT_CALLBACK_PATH = '/auth/silent-callback'

export function isOidcCallbackPath(pathname: string): boolean {
  return pathname === LOGIN_CALLBACK_PATH || pathname === SILENT_CALLBACK_PATH
}

/** Paths where we should not attempt silent OIDC renew on startup. */
export function shouldSkipSilentRenew(pathname: string): boolean {
  return pathname === LOGIN_PATH || isOidcCallbackPath(pathname)
}
