# Authorization

OCMO uses a two-tier access model: **Global Permissions** (namespace-level) and **namespace `_permissions` policies** (tree-level ABAC).

---

## Overview

```
Every request:
  1. Authenticate → who is making this request?
  2. For namespace object (create/list/delete NS):
       Global Permission rules (OIDC users only)
  3. For in-tree operations (configs, secrets, resolve, etc.):
       Namespace _permissions ABAC
```

- **Default deny** at both tiers — no matching rule = no access
- **Deny overrides Allow** (namespace policies only; global rules have no Deny)
- **Global admin bypass** — the global admin has unconditional access everywhere
- **Resolver bypass** — resolvers have implicit `config:resolve` + `secret:resolve` within their scope; namespace policies cannot restrict this

---

## Global Permissions (tier 1)

Controls access to the **namespace object** — who can see, create, update, or delete a namespace. This does **not** grant any access to configs or secrets inside the namespace.

| Operation | Global level required |
|-----------|----------------------|
| List namespaces | `read` on matching namespace glob |
| Get namespace metadata | `read` |
| Create namespace | `write` |
| Update namespace metadata / active tags | `write` |
| Delete namespace | `delete` (independent of `write`) |
| Read/write `_permissions`, `_webhooks`, `_git_sync` | Global `write` on namespace |

### Rule document format

```json
{
  "rules": [
    {
      "id": "devops-namespaces",
      "description": "DevOps team manages app-* namespaces",
      "namespace": "app-*",
      "read": {
        "actors": [
          { "kind": "User", "claims": { "groups": "devops@example.com" } }
        ]
      },
      "write": {
        "actors": [
          { "kind": "User", "claims": { "groups": "devops-admins@example.com" } }
        ]
      }
    },
    {
      "id": "personal-namespaces",
      "description": "Users own their personal-{email} namespace",
      "namespace": "personal-{!user.email}",
      "read": {
        "actors": [{ "kind": "User", "claims": { "email": "{!user.email}" } }]
      },
      "write": {
        "actors": [{ "kind": "User", "claims": { "email": "{!user.email}" } }]
      }
    }
  ]
}
```

**Evaluation:** first matching rule wins. Rules with `namespace: "*"` or `"**"` must be last.

### Managing global rules

Only the global admin can manage global rules.

```bash
# REST — list rules
curl -H "Authorization: Bearer $TOKEN" https://ocmo.example.com/api/v1/global-permissions/

# Add a rule
curl -X POST "https://ocmo.example.com/api/v1/global-permissions/" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{
    "id": "devops-rule",
    "namespace": "app-*",
    "read": {"actors": [{"kind": "User", "claims": {"groups": "devops@example.com"}}]},
    "write": {"actors": [{"kind": "User", "claims": {"groups": "devops-admins@example.com"}}]}
  }'

# Replace a rule
curl -X PUT "https://ocmo.example.com/api/v1/global-permissions/devops-rule" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{...}'

# Delete a rule
curl -X DELETE "https://ocmo.example.com/api/v1/global-permissions/devops-rule" \
  -H "Authorization: Bearer $TOKEN"

# Reorder a rule
curl -X POST "https://ocmo.example.com/api/v1/global-permissions/devops-rule/~move/" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"position": 0}'

# CLI
ocmo get global-permissions
ocmo create global-permission --from-file gp.json
ocmo update global-permission devops-rule --from-file gp.json
ocmo delete global-permission devops-rule
ocmo move global-permission devops-rule --position 0
```

---

## Namespace policies (tier 2)

Controls all in-tree operations. Stored in the `_permissions` builtin config; evaluated against the version pointed to by `permissions_tag`.

### Policy document structure

```json
{
  "policies": [
    {
      "id": "policy-id",
      "description": "Optional human-readable description",
      "effect": "Allow",
      "actors": [ ... ],
      "actions": [ ... ],
      "resources": [ ... ],
      "conditions": { ... }
    }
  ]
}
```

### `effect`

`"Allow"` or `"Deny"`. **`Deny` always wins** over `Allow` regardless of order.

### `actors`

Who the policy applies to. Multiple entries are **OR** (any match triggers the policy).

**User actor** (OIDC, matched by claims — claims within one actor are **AND**):

```json
{ "kind": "User", "claims": { "groups": "devops@example.com", "department": "IT" } }
```

Use `"*"` as a claim value to match any value for that claim.

**Resolver actor** (by path):

```json
{ "kind": "Resolver", "path": "project/prod/deployer" }
```

### `actions`

| Action | Description |
|--------|-------------|
| `config:read` | Read config content and versions |
| `config:write` | Create and update configs |
| `config:delete` | Delete configs or versions |
| `config:resolve` | Call the resolve endpoint |
| `config:tag` | Set or delete custom tags |
| `config:describe` | Set Markdown description |
| `config:audit` | Query audit log entries for the path |
| `config:*` | All config actions |
| `template:read/write/delete/tag/describe/audit` | Same as config for templates |
| `template:*` | All template actions |
| `secret:read` | Read secret metadata (+ content when `reveal=true`) |
| `secret:write` | Create and update secrets |
| `secret:delete` | Delete secrets or versions |
| `secret:tag` | Set or delete tags |
| `secret:describe` | Set Markdown description |
| `secret:resolve` | Reference in `_ocmo.parameters` |
| `secret:audit` | Query audit log for path |
| `secret:*` | All secret actions |
| `resolver:read/write/delete/describe/audit` | Resolver management |
| `resolver:*` | All resolver actions |
| `lock:read/write/delete` | Lock management |
| `lock:*` | All lock actions |
| `folder:describe/audit` | Folder-level description and audit |
| `*:describe` | Set description on any item type |
| `*:audit` | Query audit log for any item type |
| `*:read` | Read access for all item types |
| `*:*` | Full access (use sparingly) |

> Resolver tokens always have implicit `config:resolve` and `secret:resolve` within their scope. Namespace policies cannot revoke this, but can grant out-of-scope access.

### `resources`

Path glob patterns:

| Pattern | Matches |
|---------|---------|
| `**` | Everything in the namespace |
| `project/prod/app` | Exactly that path |
| `project/*/app` | Single-level wildcard |
| `project/prod/**` | Everything under `project/prod/` |
| `project/**/secrets/*` | Any `secrets` folder at any depth |

**Dynamic interpolation in resources:**

```json
"resources": ["personal/{!user.email}/**"]
```

| Expression | Resolves to |
|-----------|------------|
| `{!user.email}` | User's `email` JWT claim (sanitized to path chars) |
| `{!user.sub}` | User's `sub` JWT claim |
| `{!user.<claim>}` | Any JWT claim |
| `{!resolver.name}` | Resolver's name in tree |

Non-path characters in claim values are replaced with `-`. Multi-line values use the first line only.

### `conditions`

Optional constraints:

```json
"conditions": {
  "ip_range": ["10.10.0.0/16", "192.168.0.0/16"],
  "time_of_day": ["09:00-18:00"]
}
```

---

## Policy examples

### DevOps: full access

```json
{
  "id": "devops-full",
  "effect": "Allow",
  "actors": [{"kind": "User", "claims": {"groups": "devops@example.com"}}],
  "actions": ["config:*", "template:*", "resolver:*", "lock:*"],
  "resources": ["**"]
}
```

### Developers: read + resolve in their service area

```json
{
  "id": "devs-read",
  "effect": "Allow",
  "actors": [{"kind": "User", "claims": {"groups": "developers"}}],
  "actions": ["config:read", "config:resolve", "template:read"],
  "resources": ["myservice/**"]
}
```

### Hard deny for sensitive configs

```json
{
  "id": "deny-sensitive",
  "effect": "Deny",
  "actors": [{"kind": "User", "claims": {"*": "*"}}],
  "actions": ["config:read", "config:resolve"],
  "resources": ["**/sensitive/**"]
}
```

### Personal sandbox

```json
{
  "id": "personal-sandbox",
  "effect": "Allow",
  "actors": [{"kind": "User", "claims": {"email": "*"}}],
  "actions": ["config:*"],
  "resources": ["sandbox/{!user.email}/**"]
}
```

### Resolver from outside its scope (for extend chains)

```json
{
  "id": "deployer-shared-bases",
  "effect": "Allow",
  "actors": [{"kind": "Resolver", "path": "app/prod/deployer"}],
  "actions": ["config:resolve"],
  "resources": ["base/**"]
}
```

---

## Updating `_permissions`

```bash
# Update via CLI
cat > permissions.json <<'EOF'
{
  "policies": [
    {
      "id": "devops-full",
      "effect": "Allow",
      "actors": [{"kind": "User", "claims": {"groups": "devops@example.com"}}],
      "actions": ["*:*"],
      "resources": ["**"]
    }
  ]
}
EOF

# Convert to YAML for upload
python3 -c "import sys, json, yaml; print(yaml.dump(json.load(sys.stdin)))" < permissions.json > permissions.yaml
ocmo -n prod update config _permissions -f permissions.yaml

# Switch to specific version
ocmo update namespace prod --permissions-tag v2
```

Every write to `_permissions` is validated against `_permissions.schema`. Invalid policy documents are rejected.

---

## Evaluation algorithm

1. Authenticate → get actor identity
2. Load and compile `_permissions@permissions_tag` (LRU-cached, per-process)
3. For each policy in the document:
   - Actor matches?
   - Action matches?
   - Resource path matches?
   - Conditions satisfied?
4. If any matching policy is `Deny` → **reject**
5. If any matching policy is `Allow` → **allow**
6. Otherwise → **reject** (default deny)

Policy sets are compiled into fast in-memory matchers. Cache size: `OCMO_PERMISSIONS_CACHE_SIZE` (default 1024 entries).

---

## Related

- [Authentication](authentication.md)
- [Identities and access](../concepts/identities-and-access.md)
- [Namespaces](../concepts/namespaces.md)
- [Permissions reference](../reference/permissions.md)
