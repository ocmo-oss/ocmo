# Install the Server

## Docker Compose (recommended)

The fastest path to a working stack. Everything — Postgres, Dex OIDC, API, frontend, and nginx gateway — starts with one command.

### Prerequisites

- Docker Engine 24+ and Docker Compose v2
- Ports 8080, 8000, 5432 free on your machine

### Start

```bash
# From the repo root (where docker-compose.dev.yml lives)
docker compose -f docker-compose.dev.yml up --build
```

To also enable the Vite HMR frontend dev server (recommended for UI development):

```bash
docker compose -f docker-compose.dev.yml -f docker-compose.hmr.yml up --build
```

To enable the async worker (required for Git sync, if used):

```bash
docker compose -f docker-compose.dev.yml --profile worker up --build
```

### Services started

| Service | Host port | Purpose |
|---------|-----------|---------|
| `gateway` (nginx) | **8080** | Single public entry: routes `/api/*` to API, `/dex/*` to Dex, `/*` to frontend |
| `api` | 8000 | Django + django-ninja REST API |
| `postgres` | 5432 | Primary database |
| `oidc-provider` (Dex) | _internal_ | OIDC identity provider |
| `frontend` | _internal_ | Static SPA served via gateway |
| `redis` | 6379 | Profile `worker` or `resolve-redis` |
| `rq-worker` | — | Profile `worker` only |

### Verify

```bash
curl http://localhost:8080/api/health
# → {"status": "ok", ...}
```

OpenAPI/Swagger UI: <http://localhost:8080/api/docs>

### Default dev credentials

> ⚠️ **For local development only.** These credentials and keys must never be used in production.

| Item | Value |
|------|-------|
| Admin user | `admin@example.com` / `password` |
| Developer user | `developer@example.com` / `password` |
| OIDC client (browser/SPA) | `ocmo-api` (public) |
| OIDC client (SDK/CLI) | `ocmo-sdk` / `dev-only-ocmo-sdk-secret` |
| Postgres password | `ocmoapi1906031218435` |
| `DJANGO_SECRET_KEY` | `django-insecure-dev-key` |
| `OCMO_MASTER_KEY` | `ZDPuvW6Hx/1UxDK7K/CydLouVKtJl24nbHyb2EkvTzs=` |

---

## Standalone (no Docker)

Use this when you already have Postgres and an OIDC provider running.

### Prerequisites

- Python 3.13+
- `uv` ([install](https://docs.astral.sh/uv/getting-started/installation/))
- PostgreSQL 14+
- An OIDC provider (Dex, Keycloak, Okta, Auth0, etc.)

### Install

```bash
cd api/
uv sync
```

### Configure

Set environment variables. At minimum:

```bash
export DJANGO_SECRET_KEY="<random-secret>"
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=ocmoapi
export POSTGRES_USER=ocmoapi-user
export POSTGRES_PASSWORD=<your-db-password>
export OIDC_DISCOVERY_DOCUMENT_URL=https://your-idp.example.com/.well-known/openid-configuration
export OIDC_CLIENT_ID=ocmo-api
export OIDC_JWT_AUDIENCES=ocmo-api
export OIDC_ISSUER=https://your-idp.example.com
export OCMO_PUBLIC_URL=https://ocmo.example.com
export OCMO_MASTER_KEY=<base64-32-byte-key>
```

Generate a master key:

```bash
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

### Run migrations

```bash
cd api/
uv run python manage.py migrate --noinput
```

### Start the API

```bash
uv run python manage.py runserver 0.0.0.0:8000     # development
# or for production (gunicorn via ocmo-api wrapper):
uv run ocmo-api serve                               # binds :8000
```

---

## Connecting your own OIDC provider

OCMO does not store users. Identity comes entirely from JWT claims on every request.

### Required environment variables

| Variable | Description |
|----------|-------------|
| `OIDC_DISCOVERY_DOCUMENT_URL` | `/.well-known/openid-configuration` URL. When set, all other OIDC URLs are auto-discovered. |
| `OIDC_ISSUER` | Expected `iss` claim in access tokens. Must match exactly (Dex adds a trailing `/`). |
| `OIDC_JWT_AUDIENCES` | Comma-separated `aud` values accepted. Example: `ocmo-api,ocmo-sdk` |

### Optional overrides (when not using discovery)

| Variable | Description |
|----------|-------------|
| `OIDC_JWKS_URL` | JWKS endpoint for signature validation |
| `OIDC_AUTHORIZATION_URL` | OAuth2 authorization URL (shown in Swagger and used by CLI/UI) |
| `OIDC_TOKEN_URL` | OAuth2 token URL |

### Identity claim mapping

| Variable | Default | Description |
|----------|---------|-------------|
| `OIDC_USER_ID_CLAIM` | `sub` | Unique, stable user identifier |
| `OIDC_USER_EMAIL_CLAIM` | `email` | User email (shown in audit and whoami) |
| `OIDC_USER_DISPLAY_NAME_CLAIM` | `name` | Display name |

### Global admin mapping

One OIDC claim value identifies the global administrator:

| Variable | Default | Description |
|----------|---------|-------------|
| `OIDC_GLOBAL_ADMIN_CLAIM` | `email` | Which claim to check |
| `OIDC_GLOBAL_ADMIN_VALUE` | `admin@example.com` | Expected value for global admin |

Example — use a group membership claim:

```bash
export OIDC_GLOBAL_ADMIN_CLAIM=groups
export OIDC_GLOBAL_ADMIN_VALUE=ocmo-admins
```

### SDK/CLI OAuth clients

The CLI and SDK use the OAuth2 `client_credentials` grant (or `password` grant against Dex). Register a confidential client in your IdP:

- Grant types: `client_credentials` (or `password` for Dex dev)
- Client ID → `OCMO_CLIENT_ID` in SDK/CLI config
- Client secret → `OCMO_CLIENT_SECRET` in SDK/CLI config
- Add the client ID to `OIDC_JWT_AUDIENCES` on the API

---

## Production checklist

Before going to production, replace every default value:

- [ ] `DJANGO_SECRET_KEY` — random 50+ char string
- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_ALLOWED_HOSTS` — your domain(s)
- [ ] `OCMO_MASTER_KEY` — freshly generated base64 32-byte key; back it up
- [ ] `POSTGRES_PASSWORD` — strong password
- [ ] OIDC config pointing at your real IdP
- [ ] `OCMO_PUBLIC_URL` — your public base URL (needed for signed artifact download links)
- [ ] `OCMO_RESOLVE_ARTIFACT_BACKEND=redis` + `OCMO_RESOLVE_CACHE_BACKEND=redis` if running multiple API workers
- [ ] `DJANGO_LOG_LEVEL=WARNING`

## Related

- [Configuration reference](configuration.md)
- [Install the web UI](install-web-ui.md)
- [Install the CLI](install-cli.md)
