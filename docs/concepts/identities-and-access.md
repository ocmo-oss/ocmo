# Identities and Access

OCMO recognizes three identity types. Understanding which to use — and what each can do — is fundamental to configuring access correctly.

---

## Three identity types

### 1. OIDC user (human)

Authenticated via a JWT Bearer token from your OIDC provider (Dex, Keycloak, Okta, Auth0, etc.).

```
Authorization: Bearer <access_token>
```

- OCMO never stores users internally. Identity comes entirely from JWT claims on every request.
- User identity: `sub` claim (unique stable ID), `email` claim (shown in audit and whoami), display name from `name` claim.
- **Global admin:** one JWT claim value identifies the global administrator (default: `email` claim equals `admin@example.com`; configurable via `OIDC_GLOBAL_ADMIN_CLAIM` and `OIDC_GLOBAL_ADMIN_VALUE`).
- Permissions enforced via global rules (namespace-level CRUD) and namespace `_permissions` ABAC (item-level).

**Login flows by surface:**

| Surface | Flow |
|---------|------|
| Web UI | PKCE authorization code — automatic |
| CLI | `ocmo auth login` — OIDC device code (no browser) |
| CLI | `ocmo auth login --browser` — PKCE |
| SDK / service | Client credentials: `OCMO_CLIENT_ID` + `OCMO_CLIENT_SECRET` |
| SDK / local dev | Password grant: `OCMO_OIDC_GRANT_TYPE=password` |

### 2. Resolver (service/automation)

Authenticated via a long-lived API token with the `ocmort-` prefix.

```
X-Ocmo-Resolver-Token: ocmort-abc123...
# or as a query parameter:
GET /api/v1/ns/prod/~resolve/app/web?token=ocmort-abc123...
```

Resolvers are tree items: they live at a path in a namespace and their parent path is their **access scope**. A resolver cannot access anything outside its scope.

**Resolver token capabilities:**
- Resolve configs within scope (`GET /~resolve/`)
- Inspect effective parameters (`GET /~resolve-parameters/`)
- Check identity (`GET /auth/whoami/`)
- Probe permissions (`POST /auth/can-i/`)

**What resolver tokens cannot do:** write or delete items, read the audit log, manage namespaces or global permissions.

**Dual token slots:** each resolver has two token slots (1 and 2) for zero-downtime rotation. Rotate slot 2 while slot 1 is still active; update the service; then rotate slot 1.

### 3. Signed artifact URL (download only)

A short-lived, identity-bound token embedded in the resolve response URL:

```
GET /api/v1/ns/prod/~resolve/app/web/~download/eyJhbGci...
```

No `Authorization` header needed. The URL is valid for `OCMO_RESOLVE_URL_TTL` seconds (default 300). It is bound to the namespace, path, and issuing identity. It cannot be used to access other paths or namespaces.

This design keeps artifact download simple — `curl` or `wget` with no credentials — while keeping the data private and expiring.

---

## Permission model summary

```
Request arrives
  │
  ├─ Is it a resolver token?
  │   └─ Check scope, namespace match → implicit config:resolve + secret:resolve within scope
  │
  └─ Is it a OIDC JWT?
      │
      ├─ Global Permission Rules (ordered list, namespace glob match)
      │   └─ Controls: namespace:create / read / write / delete / audit
      │
      └─ Namespace _permissions ABAC (inside the namespace)
          └─ Controls: config:*, template:*, secret:*, resolver:*, folder:*, lock:*, audit
```

Key properties:
- **Deny-over-allow**: an explicit `deny` in `_permissions` overrides any `allow`.
- **Default deny**: no policy = no access.
- **Global admin bypass**: the global admin has implicit access everywhere. Namespace policies cannot deny the global admin.
- **Builtin path bypass**: `_permissions`, `_webhooks`, `_git_sync`, and companion secrets are only accessible to identities with Global `write` on the namespace — namespace policies cannot grant or deny access to these paths.

---

## Checking your own identity and permissions

### whoami

```bash
# CLI
ocmo whoami

# REST
curl -H "Authorization: Bearer $TOKEN" https://ocmo.example.com/api/v1/auth/whoami/

# SDK
me = client.whoami()
print(me.auth_type, me.identifier, me.display_name)
```

Example responses:

```json
// OIDC user
{
  "auth_type": "user",
  "identifier": "user-001",
  "display_name": "admin",
  "access_scope": "",
  "user_details": {
    "email": "admin@example.com",
    "is_global_admin": true,
    "claims": { "sub": "user-001", "email": "admin@example.com", "name": "admin", "groups": ["admins"] }
  }
}

// Resolver
{
  "auth_type": "resolver",
  "identifier": "resolvers/nginx",
  "display_name": "resolvers/nginx",
  "access_scope": "apps/nginx",
  "resolver_details": { "namespace": "prod", "path": "resolvers/nginx" }
}
```

### can-i — batch permission probe

```bash
# CLI
ocmo can-i config:resolve secret:read --resource app/web -n prod

# REST
curl -X POST "https://ocmo.example.com/api/v1/auth/can-i/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "prod",
    "operations": ["config:resolve", "secret:read"],
    "resource": "app/web"
  }'

# SDK
result = client.can_i(
    namespace="prod",
    operations=["config:resolve", "secret:read"],
    resource="app/web",
)
print(result.allowed)
# → {"config:resolve": True, "secret:read": False}
```

---

## Related

- [Authentication](../features/authentication.md) — login flows, token lifecycle
- [Authorization](../features/authorization.md) — policy syntax, global rules
- [Resolvers](../features/resolvers.md) — token slots, rotation
