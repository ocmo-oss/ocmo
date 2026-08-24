# Resolving

Resolving transforms a config (or a folder of configs) into ready-to-consume artifacts. The API returns signed download URLs; your service fetches the artifact with a plain HTTP GET — no credentials required on the download step.

---

## What resolving produces

- **One artifact per config** — the YAML body after the pipeline runs (no `_ocmo` block), serialized to the requested format.
- **Signed download URL** per artifact, valid for `OCMO_RESOLVE_URL_TTL` seconds (default 300 s). The URL is identity-bound and cannot be shared across namespaces.
- **Trace** — every response includes a dependency map of which configs participated.

---

## Pipeline order

For each config, steps run in this order:

```
1. Load config body → strip _ocmo block
2. Parameters       → substitute {!name} placeholders
3. Output name      → apply _ocmo.name if set
4. Extend           → deep-merge referenced configs
5. Render           → apply Jinja2 templates
6. Cast             → serialize to output format
7. Store artifact   → write to backend, mint download URL
```

Each stage is optional — a config with no `_ocmo` block simply passes through and is cast to YAML.

---

## The resolve call

```
GET /api/v1/ns/{namespace}/~resolve/{path}
```

`{path}` can be a single config or a folder path. A trailing path that resolves to a folder triggers [folder resolve](folders.md) (all configs under that path, recursively).

### Query parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `version` | `latest` | Tag or version number for the root config(s). For configs, `stable` is valid. |
| `cast` | _(from _ocmo or yaml)_ | Output format. Highest precedence. |
| `trace_only` | `false` | Return trace metadata only — no artifact produced, no `url` returned. |
| `mark-stable` | `false` | After a successful resolve, advance the `stable` tag on the root config(s). Requires `config:write`. |
| `ignore-configs-with-missing-tags` | `false` | Folder resolve: skip configs that don't have the requested tag instead of failing. |
| `no-creds` | `false` | Replace secret parameter values with `<secret-value-placeholder>`; `secret:resolve` permission not required. |
| `param_<name>` | — | Override a dynamic parameter. Example: `?param_env=staging`. |
| `cast_option_<key>` | — | Pass a cast format option. Example: `?cast_option_indent=2`. |

### Response shape

```json
{
  "items": [
    {
      "name": "app/web",
      "version": 7,
      "format": "json",
      "url": "https://ocmo.example.com/api/v1/ns/prod/~resolve/app/web/~download/eyJ...",
      "checksum": "sha256:a3f5...d9b1",
      "trace": {
        "base/database@3": {},
        "base/logging@12": {}
      }
    }
  ],
  "length": 1,
  "trace_only": false,
  "resolver": null
}
```

The SDK and CLI download each URL automatically. Raw REST callers must fetch `item.url` as a second request.

---

## Walkthrough: resolve a config to JSON

### REST

```bash
# Step 1: resolve — get the signed download URL
RESPONSE=$(curl -s \
  -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~resolve/app/web?cast=json")

# Step 2: download the artifact (no auth header needed)
curl -s "$(echo $RESPONSE | python3 -c "import sys,json; print(json.load(sys.stdin)['items'][0]['url'])")" \
  -o app.json
```

### Web UI

Namespace → **Configs** → select `app/web` → **Resolve** panel (right side) → choose cast format → **Resolve** → download or copy-curl.

The UI also shows a copy-able `curl` command, CLI snippet, and Python SDK snippet.

### CLI

```bash
# Print resolved output
ocmo -n prod resolve app/web --cast json

# Write to file
ocmo -n prod resolve app/web --cast json -O ./app.json

# Dynamic parameter override
ocmo -n prod resolve app/web --cast json --param env=staging

# Mark stable after resolve
ocmo api resolve_config --param path=app/web --param mark-stable=true --param cast=json -n prod
```

### SDK

```python
from ocmo import OcmoClient

with OcmoClient() as client:
    result = client.ns("prod").resolve(
        "app/web",
        version="stable",
        cast="json",
        params={"env": "staging"},
        cast_options={"indent": "2"},
        mark_stable=True,
    )

    print(result.cache_status)          # "hit" | "cast" | "miss"
    data = result["app/web"].data       # lazy download + parse
    host = result["app/web"].get("database.host")  # dot-path access
    result.save_all("./configs/")       # write all to directory
```

---

## Artifact caching

OCMO caches resolved artifacts to avoid redundant pipeline work. When the cache key hits (same config version + same parameters + same cast format), OCMO issues a fresh download token for the cached bytes without re-running any pipeline stage.

| Setting | Env var | Default |
|---------|---------|---------|
| Cache backend | `OCMO_RESOLVE_CACHE_BACKEND` | `locmem` (use `redis` for multi-worker) |
| Cache TTL | `OCMO_RESOLVE_CACHE_TTL` | 3600 s |

**Cache bust:** changing any parameter, version, or cast option produces a cache miss. Updating the config content (even to the same version string) also busts the cache.

---

## Trace-only mode (debugging)

`trace_only=true` walks the full dependency graph — detecting missing references, loops, and depth violations — but produces **no artifact**. The `url` field in each item is absent.

```bash
# REST
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~resolve/app/web?trace_only=true" | python3 -m json.tool

# CLI
ocmo -n prod resolve app/web --trace-only -o json

# SDK
result = prod.resolve("app/web", trace_only=True)
print(result["app/web"].trace)
```

Use trace-only to:
- Confirm which configs and tags participate before promoting `stable`
- Debug unexpected override sources
- Share a diagnostic payload in tickets (no secret values appear in trace output)

---

## Draft resolve (preview before saving)

Run the full pipeline on **unsaved YAML** — useful for previewing from the UI editor or testing locally before committing.

```bash
# REST
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/yaml" \
  "https://ocmo.example.com/api/v1/ns/prod/~resolve-draft/app/web?cast=json" \
  --data-binary @draft.yaml

# CLI
ocmo -n prod resolve draft app/web -f draft.yaml --cast json

# SDK
result = prod.resolve_draft_config("app/web", content=open("draft.yaml").read(), cast="json")
```

- Resolver token auth is not supported; OIDC only.
- No cache read or write.
- `version` is `0` in response items (draft marker).
- The config path does not need to exist (supports create-preview).

---

## Download the artifact

```bash
# Direct download (no Authorization header)
curl "https://ocmo.example.com/api/v1/ns/prod/~resolve/app/web/~download/eyJ..." -o app.json
```

The download token is:
- **Short-lived** — TTL set by `OCMO_RESOLVE_URL_TTL` (default 300 s)
- **Identity-bound** — the same identity that resolved must download
- **Path-bound** — cannot be used for other configs or namespaces

---

## mark-stable

After a successful resolve, OCMO can advance the `stable` tag on the resolved root config(s):

```bash
# REST
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~resolve/app/web?mark-stable=true"

# CLI (via escape hatch — no direct flag yet)
ocmo api resolve_config --param path=app/web --param mark-stable=true -n prod

# SDK
result = prod.resolve("app/web", mark_stable=True)
```

Requires `config:write` (specifically `config:tag`) on each affected root config.

---

## Artifact backends

| Backend | Env var value | Description |
|---------|--------------|-------------|
| Filesystem (default) | `OCMO_RESOLVE_ARTIFACT_BACKEND=fs` | Writes to `OCMO_RESOLVE_ARTIFACT_DIR`. Content-addressed (SHA-256). |
| Redis | `OCMO_RESOLVE_ARTIFACT_BACKEND=redis` | Use for multi-node deployments. Artifact bytes stored at a Redis key. |

For Nginx offload (X-Accel-Redirect), set `OCMO_RESOLVE_DOWNLOAD_XACCEL_LOCATION`.

---

## Pipeline stages (detail)

| Stage | Page |
|-------|------|
| Parameters — `{!name}` substitution | [Parameters](parameters.md) |
| Extend — deep-merge other configs | [Extend](extend.md) |
| Render — Jinja2 templates | [Render](render.md) |
| Cast — output format | [Cast](cast.md) |
| Output naming — `_ocmo.name` | [Output naming](output-naming.md) |
| Folder resolve | [Folder resolve](folders.md) |

---

## Related

- [The `_ocmo` block](../../concepts/ocmo-metadata.md)
- [Resolvers](../resolvers.md)
- [Troubleshoot resolving](../../how-to/troubleshoot-resolve.md)
