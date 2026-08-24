# Versions and Tags

Every write to a config, template, or secret creates an **immutable version**. Tags are named pointers to specific version numbers, letting you refer to `stable` or `v1.2` instead of a raw integer.

---

## Versions

- Versions are positive integers starting at 1 and incrementing on each content change.
- Version is only created when content actually changes — identical writes are no-ops (no new version, no error).
- Versions are **immutable** — content never changes once written.
- A version can be **soft-deleted** (`DELETE /~delete/{path}?version=N`): content is cleared and `deleted_at` is set, but the version number is preserved in history.
- Old versions are retained indefinitely unless explicitly deleted.

### Reading a specific version

```bash
# CLI
ocmo -n prod get item app/web@3        # explicit version number
ocmo -n prod get item app/web@stable   # tag name

# REST
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~get/app/web?version=3"
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~get/app/web?version=stable"

# SDK
item = prod.get_item("app/web", version="stable")
item = prod.get_item("app/web", version=3)
```

### Version history

```bash
# CLI
ocmo -n prod get version app/web
ocmo -n prod get version app/web --tagged-only   # only versions with at least one tag

# REST
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~versions/app/web"

# SDK
history = prod.list_item_versions("app/web", limit=50)
```

---

## Tags

### Reserved tags

| Tag | Applies to | Who sets it | How |
|-----|-----------|-------------|-----|
| `latest` | Configs, templates, secrets | Server — automatically | Always points to the highest non-deleted version. Cannot be set or deleted manually. |
| `stable` | **Configs only** | Caller-initiated | Advanced via resolve with `mark-stable=true`. Can be deleted manually (except while it is the namespace's active `permissions_tag` / `webhooks_tag`). |

`stable` does not exist on templates. Use custom tags for template promotion workflows.

### Custom tags

Any string matching `[a-zA-Z0-9_.+-]+` (excluding `latest` on any type, and `stable` on configs).

Examples: `v1.0.0`, `canary`, `tested`, `release-2026-08`, `pre-release`.

### Setting a custom tag

```bash
# CLI
ocmo -n prod tag item app/web --tag v1.0.0
ocmo -n prod tag item app/web --tag v1.0.0 --version 3    # explicit version

# REST
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~tag/app/web" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tag": "v1.0.0", "version": 3}'

# SDK
prod.set_tag("app/web", tag="v1.0.0", version=3)
```

Without a `version` field, the tag points to the current `latest`.

### Deleting a custom tag

```bash
# CLI
ocmo -n prod untag item app/web --tag v1.0.0

# REST — send tag name without version field
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~tag/app/web" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tag": "v1.0.0"}'
```

Setting a tag that already points to the same version, or deleting a tag that doesn't exist, returns **HTTP 204** (no error).

### Advancing `stable` via resolve

```bash
# REST — mark-stable=true on a resolve call
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~resolve/app/web?mark-stable=true"

# CLI — escape hatch (no direct flag on ocmo resolve yet)
ocmo api resolve_config --param path=app/web --param mark-stable=true -n prod

# SDK
result = prod.resolve("app/web", mark_stable=True)
```

---

## `@version` syntax in the CLI

| Address | Meaning |
|---------|---------|
| `app/web` | Latest version |
| `app/web@stable` | `stable` tag |
| `app/web@canary` | Custom tag `canary` |
| `app/web@3` | Exact version number 3 |
| `app/web@latest` | Latest (explicit) |

Use this syntax in: `resolve`, `get item`, `diff`, `copy`, `get version`.

---

## Namespace active tags

Namespace-level tag pointers (`permissions_tag`, `webhooks_tag`) are a separate concept from item tags. They tell OCMO which version of a builtin config is currently active:

```bash
# Switch to a new permissions version
ocmo update namespace prod --permissions-tag v2

# REST
curl -X PATCH "https://ocmo.example.com/api/v1/ns/prod" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"permissions_tag": "v2"}'
```

**Constraint:** the active tag cannot be deleted while it is selected. Re-point the namespace first.

---

## Related

- [Configs](../features/configs.md)
- [Resolving overview](../features/resolving/README.md) — `mark-stable`
- [Authorization](../features/authorization.md) — `permissions_tag`
