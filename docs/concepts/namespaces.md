# Namespaces

A **namespace** is OCMO's top-level isolation boundary. Every config, template, secret, resolver, and folder lives inside exactly one namespace. Configs in different namespaces cannot reference each other.

Think of a namespace as a project workspace: one team, one application, or one environment — with its own access policies, secrets encryption key, and configuration tree.

---

## Namespace fields

| Field | Constraint | Description |
|-------|-----------|-------------|
| `name` | `^[a-zA-Z0-9_-]+$`, case-insensitive unique | Identifier used in all API paths |
| `description` | Markdown, max 4096 chars | Human-readable purpose |
| `permissions_tag` | Tag on `_permissions` config | Which policy version is currently enforced. Default: `latest`. |
| `webhooks_tag` | Tag on `_webhooks` config | Which webhook config version is active. Default: `latest`. |
| `git_sync_tag` | Tag on `_git_sync` config | Reserved (git sync not yet functional). Default: `latest`. |
| `created_at` | UTC | |
| `updated_at` | UTC | |

---

## Builtin configs

Every namespace is initialized with these paths pre-created:

| Path | Type | Purpose |
|------|------|---------|
| `_permissions` | Config | ABAC access policy for all item operations in this namespace |
| `_permissions.schema` | Config | JSON Schema that validates `_permissions` on every write |
| `_webhooks` | Config | Webhook endpoint definitions |
| `_webhooks.schema` | Config | JSON Schema that validates `_webhooks` |
| `_git_sync` | Config | Git sync config _(reserved; `enabled: false` by default)_ |
| `_git_sync.schema` | Config | JSON Schema that validates `_git_sync` |
| `_webhooks_secret` | Secret | HMAC signing key for webhook calls |
| `_git_sync_secret` | Secret | Git credentials _(reserved)_ |

**Rules for builtin paths:**
- Cannot be deleted, moved, copied, or renamed.
- Only visible to identities that hold Global `write` on the namespace.
- Cannot be referenced as `extend` sources or generic secret parameter sources from ordinary configs (companion secrets can only be referenced from their parent builtin config).
- All standard versioning and tag features work on them.
- Writes are schema-validated automatically (even without `_ocmo.validation` declared on the config).

---

## Namespace tags

Each namespace stores three "active tag" pointers. They control which version of the corresponding builtin config is evaluated:

```bash
# Activate a new permissions policy version
ocmo update namespace prod --permissions-tag v2

# REST
curl -X PATCH https://ocmo.example.com/api/v1/ns/prod \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"permissions_tag": "v2"}'
```

**Important:** the active tag cannot be deleted while it is selected. To delete it, first point the namespace to a different tag, then delete the old one.

---

## CRUD walkthrough

### Create a namespace

```bash
# REST
curl -X POST https://ocmo.example.com/api/v1/ns/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "team-alpha", "description": "Alpha team configs"}'

# Web UI
Open OCMO → click "+" next to Namespaces → enter name + description → Create

# CLI
ocmo create namespace team-alpha --description "Alpha team configs"

# SDK
client.create_namespace(name="team-alpha", description="Alpha team configs")
```

### List namespaces

```bash
# REST
curl -H "Authorization: Bearer $TOKEN" https://ocmo.example.com/api/v1/ns/

# CLI
ocmo get namespace -o wide

# SDK
namespaces = client.list_namespaces(limit=50)
```

### Update a namespace

```bash
# REST (PATCH — only send fields to change)
curl -X PATCH https://ocmo.example.com/api/v1/ns/team-alpha \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Alpha team — updated", "permissions_tag": "v2"}'

# CLI
ocmo update namespace team-alpha --description "Alpha team — updated"
ocmo update namespace team-alpha --permissions-tag v2

# SDK
client.update_namespace("team-alpha", description="Alpha team — updated")
```

### Delete a namespace

Cascades: deletes the entire config tree, all versions, all secrets, all resolvers.

```bash
# CLI (prompts for confirmation)
ocmo delete namespace team-alpha

# REST
curl -X DELETE https://ocmo.example.com/api/v1/ns/team-alpha \
  -H "Authorization: Bearer $TOKEN"
```

---

## Who can create a namespace?

Creating a namespace requires either:
- `global:admin` (global administrator), or
- A global permission rule that grants `namespace:create` to the requesting identity.

By default a fresh install has no such rules. The global admin (`OIDC_GLOBAL_ADMIN_VALUE`) can always create namespaces and can create rules granting others the right.

---

## Related

- [Authorization](../features/authorization.md) — global rules and namespace `_permissions`
- [Tree and items](tree-and-items.md)
- [Secrets](../features/secrets.md) — per-namespace encryption key
- [Webhooks](../features/webhooks.md)
