# Folder Resolve

Passing a **folder path** to the resolve endpoint resolves all configs found recursively under that path in a single call. Templates, secrets, and resolvers are skipped. Namespace builtin configs (`_permissions`, `_webhooks`, `_git_sync`) are also excluded.

---

## How it works

```
GET /api/v1/ns/{namespace}/~resolve/{folder-path}?version=stable
```

If the tree under `folder-path` contains configs at `apps/api/web` and `apps/api/worker`, the response has two items — one per config, each independently resolved, each with its own download URL.

Each config's own `_ocmo` block (parameters, extend, render, cast, name) applies individually, exactly as in single-config resolution.

---

## Walkthrough

### REST

```bash
# Resolve all configs under apps/api/ at tag "stable"
RESPONSE=$(curl -s \
  -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~resolve/apps/api/?version=stable&cast=json")

echo $RESPONSE | python3 -m json.tool   # inspect names, versions, urls

# Download all artifacts
echo $RESPONSE | python3 -c "
import sys, json, urllib.request, pathlib
for item in json.load(sys.stdin)['items']:
    dest = pathlib.Path('output') / item['name']
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(urllib.request.urlopen(item['url']).read())
    print('saved', dest)
"
```

### Web UI

Navigate to a folder → **Resolve** panel on the right → select tag/version and cast → **Resolve**. The panel shows all output items; click each to download.

### CLI

```bash
# Resolve and write each artifact preserving folder structure
ocmo -n prod resolve apps/api/ --version stable --cast json -O ./output/

# Skip configs that don't have the "stable" tag instead of failing
ocmo -n prod resolve apps/api/ --version stable \
  --ignore-configs-with-missing-tags -O ./output/
```

The CLI writes each item using its `name` (relative path) under `--target`/`-O`, recreating the folder structure.

### SDK

```python
result = prod.resolve(
    "apps/api/",
    version="stable",
    cast="json",
    ignore_configs_with_missing_tags=True,
)
result.prefetch()                         # download all in parallel
result.save_all("./output/")             # preserves folder structure

# Iterate
for name, item in result.items():
    data = item.data
    print(name, data.get("database", {}).get("host"))
```

---

## Version parameter in folder resolve

`?version=` applies uniformly to every config in the subtree. If any config does not have the requested tag, the whole request fails by default.

Use `?ignore-configs-with-missing-tags=true` to skip configs that lack the tag and return only the ones that have it:

```bash
# REST
curl "https://ocmo.example.com/api/v1/ns/prod/~resolve/apps/?version=stable&ignore-configs-with-missing-tags=true" \
  -H "Authorization: Bearer $TOKEN"

# CLI
ocmo -n prod resolve apps/ --version stable --ignore-configs-with-missing-tags

# SDK
result = prod.resolve("apps/", version="stable", ignore_configs_with_missing_tags=True)
```

---

## Output names in folder resolve

Each item's `name` is the **relative path from the folder resolve base**:

| Config path | Resolve base | Default name |
|-------------|-------------|--------------|
| `apps/api/web` | `apps/api/` | `web` |
| `apps/api/worker` | `apps/api/` | `worker` |
| `apps/api/db/main` | `apps/api/` | `db/main` |

`_ocmo.name` on individual configs overrides this (see [Output naming](output-naming.md)).

---

## Resolver-scoped folder resolve

A resolver token whose scope is `apps/api` can use the special path `.` to folder-resolve its entire scope:

```bash
# CLI (with resolver token)
export OCMO_TOKEN=ocmort-abc123...
ocmo -n prod resolve . -O ./configs/

# REST
curl "https://ocmo.example.com/api/v1/ns/prod/~resolve/.?cast=json" \
  -H "X-Ocmo-Resolver-Token: ocmort-abc123..."
```

The path `.` means "scope root". Using `.` with a user/OIDC token is rejected.

---

## mark-stable on folder resolve

`?mark-stable=true` advances the `stable` tag on **each** config in the folder that was successfully resolved. Requires `config:write` on each.

---

## Limits

| Limit | Notes |
|-------|-------|
| No built-in per-folder item limit | Very large folders may take longer; use trace-only first to see how many configs will be resolved |
| Depth limit applies per config | `OCMO_MAX_CONFIG_RESOLVE_DEPTH` — each config's own extend chain is checked independently |

---

## Related

- [Resolving overview](README.md)
- [Output naming](output-naming.md)
- [Resolvers](../resolvers.md)
- [Deliver config to a host](../../how-to/deliver-config-to-a-host.md)
