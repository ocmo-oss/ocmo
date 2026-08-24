# Tree and Items

All items in OCMO live in a hierarchical path tree within a namespace. Understanding the tree is the foundation for everything else.

---

## The tree model

Items live at slash-separated paths: `apps/api/web`, `base/database`, `resolvers/nginx`.

- **Folders** are implicit — they're created automatically when a child item is placed inside them, and disappear when they become empty. You cannot create an empty folder directly.
- All items within a namespace share a single tree. There's no sub-tree isolation within a namespace; use separate namespaces for that.
- Paths are case-sensitive. Path segments use only `[a-zA-Z0-9-_.]+` (letters, digits, hyphens, underscores, dots).
- No leading or trailing slashes; no empty segments.

---

## Item types

| Type | What it stores | Versioned | Resolved? |
|------|---------------|-----------|-----------|
| **Config** | YAML document, optional `_ocmo` block | Yes | Yes (primary resolve type) |
| **Template** | Jinja2 source | Yes | No — referenced by configs via `_ocmo.render` |
| **Secret** | Encrypted YAML | Yes | No — values injected at resolve via `_ocmo.parameters` |
| **Resolver** | Token + pipeline config for a consumer service | No | No — authenticates resolve calls |
| **Folder** | Navigation node | No | Yes (batch-resolves all children) |

### Config

A config is a YAML document. It's the primary unit in OCMO. A config can be resolved alone or composed with other configs via the `_ocmo` block. Example:

```yaml
environment: production
replicas: 3
database:
  host: db.prod.internal
  port: 5432
  pool_size: 10
```

### Template

A template is a Jinja2 source file. It is never resolved on its own — a config pulls it in via `_ocmo.render` and provides the data context. Example:

```jinja2
server {
    listen {{ port }};
    server_name {{ server_name }};
}
```

### Secret

A secret is a YAML document whose content is AES-256-GCM encrypted at rest. It is never exported, never included in artifact output directly. A config references it by declaring a `secret` type parameter, and the value is decrypted and injected at resolve time.

### Resolver

A resolver is an item that holds two rotating access tokens and optional default pipeline configuration (cast format, parameter defaults, include/exclude patterns). Services authenticate with a resolver token to resolve configs within the resolver's scope.

### Folder

A folder groups items under a shared path prefix. Resolving a folder resolves all config children recursively. Folders support descriptions and can be moved/copied/deleted.

---

## Path rules

| Rule | Good | Bad |
|------|------|-----|
| No leading `/` | `apps/api` | `/apps/api` |
| No trailing `/` | `apps/api` | `apps/api/` |
| Alphanumeric + `-_./` segments | `app.v2/web-api` | `app!web` |
| No empty segments | `apps/api` | `apps//api` |
| Unique per namespace | — | Two items at the same path |

---

## Common operations (all types)

### Navigate and search

```bash
# List the tree root
ocmo -n prod ls

# List recursively under a path
ocmo -n prod ls app/ -R

# Tree view with depth control
ocmo -n prod tree app/ --depth 3

# Search by name or path
ocmo -n prod search tree --q "database"

# CLI
ocmo -n prod get item app/web          # item metadata + content at latest
ocmo -n prod get item app/web@stable   # at stable tag
```

```bash
# REST — navigate
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~navigate/app/"

# REST — search
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~search/?q=database"
```

```python
# SDK
prod = client.ns("prod")
nav = prod.navigate_path("app/", recursive=True)
results = prod.search_root(q="database", types=["config"])
```

### Set description (Markdown)

Descriptions are set separately from content — they don't create a new content version.

```bash
ocmo -n prod describe app/web --description "Main web application config"

# REST
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~describe/app/web" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description": "Main web application config"}'

# SDK
prod.describe_item("app/web", description="Main web application config")
```

### Move

```bash
ocmo -n prod move item app/web app/api-web

# REST
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~move/app/web" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_path": "app/api-web"}'
```

### Copy

Copies one tagged version (defaults to `latest`):

```bash
ocmo -n prod copy item app/web app/web-backup

# REST
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~copy/app/web" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_path": "app/web-backup"}'
```

### Delete

```bash
# Preview first (default)
ocmo -n prod delete item app/old --preview

# Execute
ocmo -n prod delete item app/old -y

# REST (preview=true is the default)
curl -X DELETE "https://ocmo.example.com/api/v1/ns/prod/~delete/app/old?preview=false" \
  -H "Authorization: Bearer $TOKEN"
```

For per-version soft-delete, add `?version=3` (REST) or `-V 3` (CLI).

### Diff

Compare two versions of an item, or two different paths:

```bash
ocmo -n prod diff app/web --from-version 2 --to-version 3
ocmo -n prod diff app/web@stable..latest

# Diff two paths
ocmo -n prod diff app/web ..app/web-backup

# REST
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~diff/app/web?from=2&to=3"
```

---

## Related

- [Configs](../features/configs.md)
- [Templates](../features/templates.md)
- [Secrets](../features/secrets.md)
- [Resolvers](../features/resolvers.md)
- [Versions and tags](versions-and-tags.md)
