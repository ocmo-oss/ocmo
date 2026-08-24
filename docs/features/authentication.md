# Authentication

OCMO supports two authentication mechanisms: **OIDC JWT Bearer tokens** for human users and automated services, and **Resolver tokens** for service accounts scoped to a path in the tree.

---

## OIDC Bearer tokens

Human users and automated services using OAuth client credentials authenticate with a Bearer token from an OIDC provider.

```
Authorization: Bearer <access_token>
```

OCMO validates the JWT signature against the provider's JWKS endpoint on every request. No users are stored locally — identity comes entirely from JWT claims.

### Login flows by surface

| Surface | Flow |
|---------|------|
| Web UI | PKCE authorization code — automatic on page load |
| CLI `ocmo auth login` | OIDC device code — follow printed URL+code |
| CLI `ocmo auth login --browser` | PKCE — opens browser automatically |
| SDK / service (OIDC) | Client credentials or password grant |

### SDK authentication (OIDC client credentials)

```bash
export OCMO_SERVER=https://ocmo.example.com
export OCMO_CLIENT_ID=my-service
export OCMO_CLIENT_SECRET=...   # from your IdP's client registration
```

```python
from ocmo import OcmoClient

# SDK acquires and caches token automatically
with OcmoClient() as client:
    me = client.whoami()
    print(me.identifier)
```

### Local dev (Dex password grant)

```bash
export OCMO_SERVER=http://localhost:8080
export OCMO_CLIENT_ID=ocmo-sdk
export OCMO_CLIENT_SECRET=dev-only-ocmo-sdk-secret
export OCMO_OIDC_GRANT_TYPE=password
export OCMO_OIDC_USERNAME=admin@example.com
export OCMO_OIDC_PASSWORD=password
```

### Token lifetime and refresh

The SDK caches tokens and refreshes them before expiry. OIDC tokens typically expire in 1 hour; the SDK uses the refresh token when available, otherwise re-acquires.

CLI tokens are cached in `~/.cache/ocmo/`. Check status:

```bash
ocmo auth status
```

### Global administrator

One OIDC claim value identifies the global administrator (configured in the API via `OIDC_GLOBAL_ADMIN_CLAIM` and `OIDC_GLOBAL_ADMIN_VALUE`). The global admin:
- Can read all namespaces (no Global Permission rule required)
- Can create, update, and delete Global Permission rules
- Has unconditional full access to all namespace builtin configs (`_permissions`, `_webhooks`, `_git_sync`, companion secrets)
- Cannot be locked out of any namespace via policies

---

## Resolver tokens

Resolver tokens authenticate service accounts scoped to a tree path.

```
X-Ocmo-Resolver-Token: ocmort-abc123...
# or as query parameter (query param takes precedence)
GET /api/v1/ns/prod/~resolve/app/web?token=ocmort-abc123...
```

Token format: `ocmort-` prefix followed by a random suffix.

### Obtaining a resolver token

Resolver tokens are created and managed through the API by users with `resolver:write` permission:

```bash
# Create a resolver — token1 returned once in full
ocmo -n prod create resolver myapp/prod/deployer
# → token1: ocmort-abc123def456...

# Store and export
export OCMO_TOKEN=ocmort-abc123def456...
```

### Zero-downtime rotation

```bash
# 1. Generate token2
ocmo -n prod rotate resolver myapp/prod/deployer --slot 2
# → token2: ocmort-xyz789...

# 2. Deploy token2 to the service
# 3. Wait until token1 is no longer used (monitor audit log)
# 4. Rotate token1 (invalidates old token1)
ocmo -n prod rotate resolver myapp/prod/deployer --slot 1
```

Both tokens are valid simultaneously during the transition window.

### What resolver tokens can do

| Action | Allowed |
|--------|---------|
| Resolve configs in scope | ✓ |
| Navigate/search in scope | ✓ |
| Check identity (`whoami`) | ✓ |
| Probe permissions (`can-i`) | ✓ |
| Write/delete/tag items | ✗ |
| Read audit log | ✗ |
| Access other namespaces | ✗ (token is namespace-bound) |
| Access builtin configs | ✗ |

---

## Signed artifact download URLs

After a resolve call, each artifact has a short-lived signed URL:

```
https://ocmo.example.com/api/v1/ns/prod/~resolve/app/web/~download/eyJ...
```

No `Authorization` header is needed to download. The URL is:
- **Short-lived** — `OCMO_RESOLVE_URL_TTL` seconds (default 300 s)
- **Identity-bound** — only the identity that called `~resolve` can use the URL
- **Path-bound** — cannot be used for other configs or namespaces

```bash
# Plain curl — no credentials needed
curl "https://ocmo.example.com/api/v1/ns/prod/~resolve/app/web/~download/eyJ..." -o app.json
```

---

## Checking identity and permissions

```bash
# Who am I?
ocmo whoami
ocmo whoami -o json

# REST
curl -H "Authorization: Bearer $TOKEN" https://ocmo.example.com/api/v1/auth/whoami/

# Can I do X?
ocmo can-i config:resolve secret:read --resource app/web -n prod

# REST
curl -X POST "https://ocmo.example.com/api/v1/auth/can-i/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"namespace": "prod", "operations": ["config:resolve", "secret:read"], "resource": "app/web"}'
```

---

## Configuring your IdP

Point OCMO at any OIDC-compliant provider:

```bash
export OIDC_DISCOVERY_DOCUMENT_URL=https://sso.example.com/.well-known/openid-configuration
export OIDC_ISSUER=https://sso.example.com
export OIDC_JWT_AUDIENCES=ocmo-api,ocmo-sdk
export OIDC_GLOBAL_ADMIN_CLAIM=groups
export OIDC_GLOBAL_ADMIN_VALUE=ocmo-admins
```

Register two OAuth clients in your IdP:
1. **Public client** (`ocmo-api`) — for the web UI and CLI browser flow (PKCE, redirect URIs: `/login/callback`, `/auth/silent-callback`, `http://127.0.0.1:47291/callback`)
2. **Confidential client** (`ocmo-sdk`) — for SDK/CLI service tokens (`client_credentials` grant)

---

## Related

- [Authorization](authorization.md) — what authenticated identities can do
- [Resolvers](resolvers.md) — resolver token lifecycle
- [Identities and access](../concepts/identities-and-access.md)
- [Configuration reference](../quickstart/configuration.md) — `OIDC_*` variables
