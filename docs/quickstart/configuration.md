# Configuration Reference

All environment variables for every OCMO component.

> **Production:** Never use dev-compose defaults (`DJANGO_DEBUG=True`, bundled Dex, sample
> `OCMO_MASTER_KEY`). Copy [`.env.example`](../.env.example) or [`api/.env.example`](../api/.env.example)
> and set strong secrets. See [SECURITY.md](../SECURITY.md).

---

## API server (`ocmo-api`)

### Required in production

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Django signing key and HMAC seed for artifact download tokens. Use a long random string. |
| `POSTGRES_HOST` | PostgreSQL hostname |
| `POSTGRES_PORT` | PostgreSQL port (default: `5432`) |
| `POSTGRES_DB` | Database name (default: `ocmoapi`) |
| `POSTGRES_USER` | Database user (default: `ocmoapi-user`) |
| `POSTGRES_PASSWORD` | Database password |
| `OIDC_DISCOVERY_DOCUMENT_URL` | OIDC well-known config URL. Auto-discovers all other OIDC endpoints. |
| `OIDC_ISSUER` | Expected `iss` claim in access tokens |
| `OIDC_JWT_AUDIENCES` | Comma-separated `aud` values (e.g. `ocmo-api,ocmo-sdk`) |
| `OCMO_MASTER_KEY` | Base64-encoded 32-byte AES key for secret encryption. Required to use secrets. |

Generate a master key:

```bash
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

### Django

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_DEBUG` | `True` | Set `False` in production |
| `DJANGO_ALLOWED_HOSTS` | `*` | Comma-separated hostnames. Set to your domain in production. |
| `DJANGO_LOG_LEVEL` | `INFO` | Python logging level for the `config_api` logger |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | |
| `POSTGRES_PORT` | `5432` | |
| `POSTGRES_DB` | `ocmoapi` | |
| `POSTGRES_USER` | `ocmoapi-user` | |
| `POSTGRES_PASSWORD` | `ocmoapi1906031218435` | **Change in production** |

### OIDC

| Variable | Default | Description |
|----------|---------|-------------|
| `OIDC_DISCOVERY_DOCUMENT_URL` | Dex internal | Well-known config URL |
| `OIDC_JWKS_URL` | _(from discovery)_ | Override JWKS endpoint |
| `OIDC_ISSUER` | `http://localhost:8080/dex/` | Expected `iss` claim |
| `OIDC_CLIENT_ID` | `ocmo-api` | OAuth2 client ID |
| `OIDC_JWT_AUDIENCES` | `ocmo-api,ocmo-sdk` | Accepted `aud` values |
| `OIDC_SCOPES` | `openid profile email groups` | Requested scopes |
| `OIDC_AUTHORIZATION_URL` | _(from issuer)_ | Browser OAuth authorization URL |
| `OIDC_TOKEN_URL` | _(from issuer)_ | OAuth token URL |
| `OIDC_SWAGGER_REDIRECT_URL` | `http://localhost:8080/api/docs/oauth2-redirect.html` | Swagger OAuth redirect URI |
| `OIDC_USER_ID_CLAIM` | `sub` | Claim for unique user ID |
| `OIDC_USER_EMAIL_CLAIM` | `email` | Claim for user email |
| `OIDC_USER_DISPLAY_NAME_CLAIM` | `name` | Claim for display name |
| `OIDC_GLOBAL_ADMIN_CLAIM` | `email` | Claim used to match global admin |
| `OIDC_GLOBAL_ADMIN_VALUE` | `admin@example.com` | Expected value for global admin |

### Secrets

| Variable | Default | Description |
|----------|---------|-------------|
| `OCMO_MASTER_KEY` | _(empty)_ | Base64 32-byte AES key (KEK). Required when using secrets. The API will not start secret operations without it. |

### Resolve and artifacts

| Variable | Default | Description |
|----------|---------|-------------|
| `OCMO_PUBLIC_URL` | _(empty)_ | Public base URL for absolute artifact download links. Required behind reverse proxies. Example: `https://ocmo.example.com` |
| `OCMO_RESOLVE_ARTIFACT_BACKEND` | `fs` | `fs` (filesystem) or `redis`. Use `redis` with multiple API workers. |
| `OCMO_RESOLVE_ARTIFACT_DIR` | `/tmp/ocmo/resolved` | Filesystem artifact directory (when `backend=fs`) |
| `OCMO_RESOLVE_URL_TTL` | `300` | Signed download URL lifetime in seconds |
| `OCMO_RESOLVE_ARTIFACT_MAX_AGE` | `86400` | Artifact retention in seconds (24h) |
| `OCMO_RESOLVE_ARTIFACT_SWEEP_INTERVAL` | `900` | Seconds between artifact sweep runs per worker |
| `OCMO_RESOLVE_CACHE_BACKEND` | `locmem` | `locmem` (in-process) or `redis`. Use `redis` with multiple workers. |
| `OCMO_RESOLVE_CACHE_TTL` | `3600` | Resolve cache TTL in seconds |
| `OCMO_RESOLVE_DOWNLOAD_XACCEL_LOCATION` | _(empty)_ | Nginx `X-Accel-Redirect` prefix for internal artifact serving. When set, API returns the redirect header instead of serving bytes. |
| `OCMO_RESOLVE_ARTIFACT_REDIS_URL` | _(from REDIS_*)_ | Redis URL for artifact backend (overrides `REDIS_HOST/PORT/DB`) |
| `OCMO_RESOLVE_ARTIFACT_REDIS_GZIP` | `false` | Compress artifacts stored in Redis |
| `OCMO_RESOLVE_CACHE_REDIS_URL` | _(from REDIS_*)_ | Redis URL for cache backend |

### Redis

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | |
| `REDIS_PORT` | `6379` | |
| `REDIS_DB` | `0` | |

### Audit

| Variable | Default | Description |
|----------|---------|-------------|
| `OCMO_AUDIT_MODE` | `all` (debug) / `resolve` (prod) | `all` — every request; `modifications-and-resolve` — writes + resolves; `resolve` — resolve calls only |

### Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `OCMO_MAX_CONFIG_UPLOAD_BYTES` | `1048576` (1 MiB) | Max config body size |
| `OCMO_MAX_TEMPLATE_UPLOAD_BYTES` | `1048576` (1 MiB) | Max template body size |
| `OCMO_MAX_SECRET_UPLOAD_BYTES` | `262144` (256 KiB) | Max secret body size |
| `OCMO_MAX_CONFIG_RESOLVE_DEPTH` | `20` | Max extend recursion depth |
| `OCMO_MAX_EXTEND_CONFIGS` | `50` | Max configs in one extend list |
| `OCMO_MAX_RENDER_TEMPLATES` | `50` | Max templates in one render list |
| `OCMO_MAX_CONFIG_PARAMETERS` | `50` | Max `param_<name>` overrides per resolve request |
| `OCMO_MAX_PARAMETER_TRANSFORMERS` | `10` | Max chained transformers per parameter |
| `OCMO_MAX_PROPAGATION_TARGETS` | `5` | Max targets in `_ocmo.propagation.targets` |

### Production server (gunicorn)

| Variable | Default | Description |
|----------|---------|-------------|
| `GUNICORN_BIND` | `0.0.0.0:8000` | Listen address |
| `GUNICORN_WORKERS` | `2 * CPU + 1` | Number of gunicorn workers |
| `GUNICORN_TIMEOUT` | `30` | Worker timeout in seconds |

---

## Frontend (`ocmo` web UI)

Build-time variables (baked into the static build):

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | _(empty = same origin)_ | API origin. Set when UI and API are on different hosts. |
| `VITE_OIDC_REDIRECT_URI` | `{origin}/login/callback` | OAuth2 redirect URI |
| `VITE_OIDC_SILENT_REDIRECT_URI` | `{origin}/auth/silent-callback` | Silent token renew URI |
| `VITE_OIDC_POST_LOGOUT_REDIRECT_URI` | `{origin}/login` | Post-logout redirect URI |

OIDC issuer, client ID, and scopes are fetched from `GET /api/version` at runtime — no additional build-time config needed.

---

## CLI (`ocmo-cli`)

CLI-specific environment variables (in addition to all SDK `OCMO_*` vars):

| Variable | Description |
|----------|-------------|
| `OCMO_CONFIG` | Path to config file (default: `~/.config/ocmo/config.yaml`) |
| `OCMO_CONTEXT` | Override the active context from the config file |
| `OCMO_NAMESPACE` | Override the default namespace for this invocation |
| `OCMO_OUTPUT` | Default output format (`table`, `yaml`, `json`, etc.) |
| `OCMO_NO_COLOR` | Set to `true` to disable ANSI color output |
| `OCMO_EXEC_HOOKS` | Set to `true` to execute resolver hooks in `resolve` commands |
| `OCMO_HOOK_NAMESPACE` | Passed to hook scripts as the active namespace |
| `OCMO_HOOK_PATH` | Passed to hook scripts as the resolved path |
| `OCMO_HOOK_ITEM` | Passed to hook scripts as the resolved item name |
| `OCMO_HOOK_FILES` | Passed to hook scripts as a colon-separated list of output file paths |

---

## SDK (`ocmo-sdk`)

| Variable | Default | Description |
|----------|---------|-------------|
| `OCMO_SERVER` | _(required)_ | API base URL |
| `OCMO_NAMESPACE` | — | Default namespace |
| `OCMO_TIMEOUT` | `30` | Per-request timeout in seconds |
| `OCMO_CONNECT_TIMEOUT` | `10` | Connection timeout in seconds |
| `OCMO_RETRIES` | `3` | Number of retry attempts |
| `OCMO_MAX_CONCURRENCY` | `8` | Max concurrent artifact downloads |
| `OCMO_CA_BUNDLE` | system store | Path to a PEM CA bundle |
| `OCMO_INSECURE_SKIP_TLS_VERIFY` | `false` | Disable TLS verification (insecure; prints warning) |
| `OCMO_AUTH_MODE` | _(inferred)_ | Force auth mode: `oidc`, `resolver-token`, `bearer`, `none` |
| `OCMO_CLIENT_ID` | — | OIDC client ID |
| `OCMO_CLIENT_SECRET` | — | OIDC client secret (inline) |
| `OCMO_CLIENT_SECRET_FILE` | — | Path to file containing OIDC client secret |
| `OCMO_OIDC_ISSUER` | _(from API)_ | Override OIDC issuer |
| `OCMO_OIDC_TOKEN_URL` | _(from discovery)_ | Override OIDC token endpoint |
| `OCMO_OIDC_SCOPE` | `openid` | OAuth2 scopes to request |
| `OCMO_OIDC_AUDIENCE` | _(from API)_ | Override `aud` claim in token requests |
| `OCMO_OIDC_GRANT_TYPE` | `client_credentials` | OAuth2 grant type (`client_credentials` or `password`) |
| `OCMO_OIDC_USERNAME` | — | Username for password grant |
| `OCMO_OIDC_PASSWORD` | — | Password for password grant (inline) |
| `OCMO_OIDC_PASSWORD_FILE` | — | Path to file containing password |
| `OCMO_TOKEN` | — | Resolver token (`ocmort-…`) or Bearer token |
| `OCMO_TOKEN_FILE` | — | Path to file containing token (re-read on 401) |
| `OCMO_CACHE_DIR` | `~/.cache/ocmo` | OIDC token cache directory |
| `OCMO_LOG_LEVEL` | `WARNING` | SDK logger level |
| `OCMO_USER_AGENT_SUFFIX` | — | Appended to the `User-Agent` header |
| `OCMO_SKIP_VERSION_CHECK` | `false` | Skip SDK/server major-version compatibility check |

---

## Related

- [Install the server](install-server.md)
- [Secrets](../features/secrets.md) — `OCMO_MASTER_KEY` details
- [Authentication](../features/authentication.md)
