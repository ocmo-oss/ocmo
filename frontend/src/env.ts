/** Runtime and optional build-time frontend configuration. */

function optionalEnv(key: string): string | undefined {
  const value = import.meta.env[key]
  return typeof value === 'string' && value.length > 0 ? value : undefined
}

function appOrigin(): string {
  return window.location.origin
}

export const env = {
  /** API origin prefix; empty string means same origin as the SPA. */
  apiBase: optionalEnv('VITE_API_BASE_URL') ?? '',
  /** SPA OAuth redirect URIs — client-specific, not returned by the API. */
  oidcRedirectUri:
    optionalEnv('VITE_OIDC_REDIRECT_URI') ?? `${appOrigin()}/login/callback`,
  oidcSilentRedirectUri:
    optionalEnv('VITE_OIDC_SILENT_REDIRECT_URI') ?? `${appOrigin()}/auth/silent-callback`,
  oidcPostLogoutRedirectUri:
    optionalEnv('VITE_OIDC_POST_LOGOUT_REDIRECT_URI') ?? `${appOrigin()}/login`,
} as const
