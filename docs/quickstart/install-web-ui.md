# Install the Web UI

## In the Docker stack (easiest)

The web UI is bundled in `docker-compose.dev.yml`. When the stack is running, navigate to:

```
http://localhost:8080
```

Click **Sign in with SSO** → you are redirected to Dex → sign in with `admin@example.com` / `password`.

---

## Standalone build (production or custom host)

### Prerequisites

- Node.js 24+
- pnpm (`corepack enable && corepack prepare pnpm@latest --activate`)

### Build

```bash
cd frontend/
pnpm install
pnpm build       # outputs to frontend/dist/
```

### Serve

`dist/` is a standard SPA. Serve it from any static file server. The server must send `index.html` for all non-asset paths (HTML5 history mode).

Example with nginx (gunicorn upstream on loopback):

```nginx
server {
    listen 80;
    root /srv/ocmo-frontend/dist;

    # Optional: security headers from frontend/nginx-security-headers.inc in the repo.
    # Requires connect-src to reach the API from the browser — proxy /api/ on this host
    # and build with VITE_API_BASE_URL="" (see below).

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Build environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_BASE_URL` | _(empty = same origin)_ | API origin. Set when the UI and API are on different hosts, e.g. `https://api.ocmo.example.com`. Leave empty when serving both behind the same gateway. |

Example when UI and API share a gateway at the same origin (required when using the frontend CSP headers):

```bash
VITE_API_BASE_URL="" pnpm build
```

Config editor autocomplete loads JSON Schema from `GET /api/v1/~config-metadata-schema` and related routes. If the browser blocks those requests (CSP `connect-src`, mixed content, or a wrong `VITE_API_BASE_URL`), completions stay empty and DevTools reports a CSP violation — often `connect-src` when the bundle still points at `http://localhost:8000` or another non-HTTPS origin.

Example when API is on a separate subdomain:

```bash
VITE_API_BASE_URL=https://api.ocmo.example.com pnpm build
```

---

## Development mode (Vite HMR)

For frontend development with hot-module replacement:

```bash
# Recommended: full stack + Vite HMR (UI at :3000, gateway at :8080)
docker compose -f docker-compose.dev.yml -f docker-compose.hmr.yml up --build

# Or: standalone Vite dev server (need API running separately)
cd frontend/
VITE_API_BASE_URL=http://localhost:8000 pnpm dev
# → http://localhost:3000
```

---

## OIDC configuration

The UI discovers its OIDC settings at runtime from `GET /api/version`. You do **not** need to bake OIDC URLs into the frontend build. The only thing you may need to configure is the redirect URIs:

### Redirect URIs to register in your OIDC client

| Variable | Default |
|----------|---------|
| `VITE_OIDC_REDIRECT_URI` | `{origin}/login/callback` |
| `VITE_OIDC_SILENT_REDIRECT_URI` | `{origin}/auth/silent-callback` |
| `VITE_OIDC_POST_LOGOUT_REDIRECT_URI` | `{origin}/login` |

For a production deployment at `https://ocmo.example.com`, register these redirect URIs in your IdP:

```
https://ocmo.example.com/login/callback
https://ocmo.example.com/auth/silent-callback
```

The Dex dev config (`api/docker/dex-config.yaml`) already registers `http://localhost:8080/login/callback` for local use.

---

## Authentication flow

1. Unauthenticated requests redirect to `/login`.
2. The UI calls `GET /api/version` to get the OIDC issuer, client ID, and scopes.
3. PKCE authorization code flow starts; user is redirected to the IdP.
4. After login, tokens are stored in `localStorage`; `GET /auth/whoami/` is called to confirm identity.
5. Tokens auto-renew via a silent iframe before expiry.
6. A 401 response from the API clears the session and redirects to `/login`.

---

## Related

- [Install the server](install-server.md)
- [Authentication](../features/authentication.md)
