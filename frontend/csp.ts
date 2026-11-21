/**
 * Canonical Content-Security-Policy strings for the SPA.
 * Production: nginx-security-headers.inc (keep directive sets in sync).
 * Development / preview: vite.config.ts response headers.
 *
 * `add_header` in nginx uses the standard ngx_http_headers_module (always enabled).
 */

const cspProductionDirectives = [
  // ResolvePanel: programmatic <a download> via blob: URLs.
  "default-src 'self' blob:",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  // Bundled Vite/React modules and lazy chunks only.
  "script-src 'self'",
  // Monaco editor worker (?worker chunk, lib/monacoEnvironment.ts) + OIDC renew iframes.
  "worker-src 'self' blob:",
  // oidc-client-ts signinSilent hidden iframe loads the IdP authorize URL.
  "frame-src 'self' https:",
  // Monaco runtime <style> blocks.
  "style-src 'self' 'unsafe-inline'",
  // React style={{}} across the app.
  "style-src-attr 'unsafe-inline'",
  "font-src 'self' data:",
  // Bundled assets, markdown images, Monaco.
  "img-src 'self' data: blob: https:",
  // API (/api on same origin) and HTTPS OIDC token/userinfo.
  "connect-src 'self' https:",
  "manifest-src 'self'",
] as const

const cspDevelopmentDirectives = [
  "default-src 'self' blob:",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  // Vite dev client bootstrap.
  "script-src 'self' 'unsafe-inline'",
  "worker-src 'self' blob:",
  // Local Dex issuer is often http://localhost:8080/dex/.
  "frame-src 'self' https: http:",
  "style-src 'self' 'unsafe-inline'",
  "style-src-attr 'unsafe-inline'",
  "font-src 'self' data:",
  "img-src 'self' data: blob: https:",
  "connect-src 'self' https: ws: wss:",
  "manifest-src 'self'",
] as const

export const cspProduction = cspProductionDirectives.join('; ')
export const cspDevelopment = cspDevelopmentDirectives.join('; ')

/** App features that must stay aligned with the production CSP (see csp.test.ts). */
export const cspProductionRequirements = [
  {
    feature: 'Vite production bundles (main.tsx, lazy routes)',
    directive: 'script-src',
    tokens: ["'self'"],
  },
  {
    feature: 'Monaco editor worker (monacoEnvironment.ts getWorker, ?worker chunk)',
    directive: 'worker-src',
    tokens: ["'self'", 'blob:'],
  },
  {
    feature: 'OIDC silent renew (auth/oidc.ts, SilentCallbackPage)',
    directive: 'frame-src',
    tokens: ["'self'", 'https:'],
  },
  {
    feature: 'API client + OIDC metadata (api/client.ts, fetch)',
    directive: 'connect-src',
    tokens: ["'self'", 'https:'],
  },
  {
    feature: 'Config YAML autocomplete (useConfigYamlSchema, uriReferenceCompletion)',
    directive: 'connect-src',
    tokens: ["'self'"],
  },
  {
    feature: 'Resolve artifact download (ResolvePanel blob URLs)',
    directive: 'default-src',
    tokens: ["'self'", 'blob:'],
  },
  {
    feature: 'Sanitized markdown images (descriptionMarkdownRender)',
    directive: 'img-src',
    tokens: ['https:'],
  },
  {
    feature: 'React inline layout styles',
    directive: 'style-src-attr',
    tokens: ["'unsafe-inline'"],
  },
] as const