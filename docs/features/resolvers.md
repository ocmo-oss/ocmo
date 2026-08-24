# Resolvers

A **Resolver** is an OCMO service account for automated consumers. Services, CI pipelines, and scripts that need to pull configs at runtime should authenticate with a resolver token rather than an OIDC user token.

A resolver is a tree item — it lives at a path in the namespace, and its **parent path is its access scope**.

---

## How resolvers work

```
Resolver at:  myapp/prod/deployer
Scope:        myapp/prod/

When the deployer calls:  GET /~resolve/web
Effective path:           myapp/prod/web
```

The resolver can only resolve configs within its scope. Paths in resolve requests are automatically prefixed with the scope. To resolve the scope root folder, use the special path `.`.

A resolver has **two token slots** for zero-downtime rotation.

---

## Create

```bash
# REST
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~resolver/~create/myapp/prod/deployer" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Production deployment service",
    "config": {
      "cast": "json",
      "cast_options": {"indent": "2"}
    }
  }'

# CLI
ocmo -n prod create resolver myapp/prod/deployer \
  --description "Production deployment service" \
  --default-cast json

# SDK
prod.create_resolver(
    "myapp/prod/deployer",
    description="Production deployment service",
    config={"cast": "json"},
)
```

On creation, `token1` is returned **in full once**. `token2` is null. Store the token immediately — it is masked on subsequent reads.

## Token format

```
ocmort-abc123def456...
```

The `ocmort-` prefix identifies resolver tokens everywhere (CLI, SDK, logs, audit).

## Read

```bash
# REST
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~get/myapp/prod/deployer"

# CLI
ocmo -n prod get item myapp/prod/deployer
```

Tokens are shown masked: `ocmort-abc123***` on all reads after creation.

## Regenerate a token

```bash
# REST — regenerate token slot 2
curl -X PATCH "https://ocmo.example.com/api/v1/ns/prod/~resolver/~update/myapp/prod/deployer" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"regenerate_token": 2}'

# CLI
ocmo -n prod rotate resolver myapp/prod/deployer --slot 2
```

The regenerated token is returned in full once. Only one slot can be regenerated per request.

## Zero-downtime rotation

1. `rotate --slot 2` — new token2 returned.
2. Deploy token2 to the service (or update `OCMO_TOKEN`).
3. Wait until the old token1 is no longer used (check audit log).
4. `rotate --slot 1` — invalidates the old token1.

Both tokens remain valid simultaneously during the transition window.

## Update resolver config

A resolver can carry default pipeline configuration applied to all resolve calls made with its token:

```bash
# REST
curl -X PATCH "https://ocmo.example.com/api/v1/ns/prod/~resolver/~update/myapp/prod/deployer" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "cast": "env",
      "cast_options": {"type": "unix", "export": true},
      "param_defaults": {"region": "eu-west-1"}
    }
  }'

# CLI
ocmo -n prod update resolver myapp/prod/deployer \
  --default-cast env \
  --param-default region=eu-west-1
```

The resolver config sets defaults that individual resolve calls can override.

## Delete

```bash
# CLI
ocmo -n prod delete item myapp/prod/deployer -y

# REST
curl -X DELETE "https://ocmo.example.com/api/v1/ns/prod/~delete/myapp/prod/deployer?preview=false" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Using a resolver token

**Resolver tokens are never OAuth Bearer tokens.** They use a dedicated header (or query parameter):

```bash
# Header (preferred)
curl -H "X-Ocmo-Resolver-Token: ocmort-abc123..." \
  "https://ocmo.example.com/api/v1/ns/prod/~resolve/web"

# Query parameter
curl "https://ocmo.example.com/api/v1/ns/prod/~resolve/web?token=ocmort-abc123..."

# CLI (token in env var)
export OCMO_TOKEN=ocmort-abc123...
ocmo -n prod resolve web --cast json

# SDK
from ocmo import OcmoClient
client = OcmoClient()  # reads OCMO_TOKEN from env
result = client.ns("prod").resolve("web", cast="json")
```

When both header and query parameter are present, the **query parameter takes precedence**.

---

## Scope and access

A resolver can resolve (and navigate/search) anything inside its scope by default — no additional namespace policy is needed. To allow it to resolve configs **outside** its scope (e.g., for extend chains that reference shared base configs), add an explicit Allow rule in `_permissions`.

**Namespace validation:** a resolver token presented to the wrong namespace is rejected immediately with HTTP 403, before any tree lookup occurs.

**Resolver tokens cannot:**
- Write, create, update, or delete items
- Read the audit log
- Create or manage namespaces or global permissions
- Set tags

---

## Resolver navigation and search

When authenticated with a resolver token, `navigate` and `search` are scoped to the resolver's access scope:

```bash
# List items in scope (from the resolver's perspective)
export OCMO_TOKEN=ocmort-abc123...
ocmo -n prod ls             # lists myapp/prod/
ocmo -n prod ls services/   # lists myapp/prod/services/
```

Out-of-scope paths return HTTP 404 — same as permission-denied paths.

---

## Required permissions

| Operation | Permission |
|-----------|-----------|
| Read resolver metadata | `resolver:read` |
| Create resolver | `resolver:write` |
| Update / rotate | `resolver:write` |
| Delete resolver | `resolver:delete` |
| Set description | `resolver:describe` |

Resolvers do not need `config:resolve` on their own scope — that is implicit. They do need explicit policies for out-of-scope access (e.g., for cross-scope extend bases).

---

## Related

- [Authentication](authentication.md) — token lifecycle, header/param formats
- [Authorization](authorization.md) — adding extra permissions for a resolver
- [Deliver config to a host](../how-to/deliver-config-to-a-host.md)
- [CI/CD guide](../how-to/ci-cd.md)
