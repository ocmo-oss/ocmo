# Extend

`_ocmo.extend` merges other configs into the current one before the artifact is produced. It implements config inheritance and composition — define base defaults once, override at each layer.

---

## Quick example (`accumulate` mode)

```yaml
# apps/api/prod
_ocmo:
  extend:
    configs:
      - ../../../base/database@stable
      - ../../../base/logging
    mode: accumulate

# Current config data (wins over merged values on conflict)
database:
  pool_size: 20
log_level: warn
```

Resolve fetches both base configs (in order), deep-merges them, then merges the current data on top. Keys in the current config always win.

---

## Configuration syntax

```yaml
_ocmo:
  extend:
    configs:
      - path/to/config@tag-or-version
      - path: shared/all@stable
        key: .database               # extract a subtree before merging
        as: .database                # place it at a different key
    mode: accumulate                 # accumulate | distribute | align
    by: .some.key                    # used by distribute and align modes
```

### Top-level fields

| Field | Required | Description |
|-------|----------|-------------|
| `configs` | Yes | List of config references to merge |
| `mode` | No | Merge strategy. Default: `accumulate`. |
| `by` | No | JSON path into the current config's data. Used by `distribute` and `align`. |

### Config reference (per entry)

Each entry is either a plain path string or an object:

**String form** — whole document, latest version:
```yaml
- ../base-config
```

**String with version** — whole document at a tag or number:
```yaml
- ../base-config@stable
- ../base-config@3
```

**Object form** — partial reference:

| Field | Required | Description |
|-------|----------|-------------|
| `path` | Yes | Config path with optional `@version` suffix. Accepts `{!param}` substitution. |
| `key` | No | Dot-path into the resolved base data to extract a subset (e.g. `.database`). Append `?` to make it optional. |
| `as` | No | Dot-path describing where to place the value in the merge document. |

`key` selects *what* to take; `as` selects *where* to put it.

Example — extract `.database` from a shared config and merge it under `.persistence`:
```yaml
- path: shared/all@stable
  key: .database
  as: .persistence
```

---

## Mode: `accumulate` (default)

Each config is merged into the previous one, then the current config's data is merged on top. **One output document.**

```
base[0] → base[1] → ... → base[N] → current data  →  single output
```

Current config values always win on conflicts. Base configs further left in the list are overridden by those further right.

**Use case:** classic layered inheritance — global → per-region → per-environment → per-service.

```yaml
# global base
database:
  host: db.internal
  port: 5432
  pool_size: 5
log_level: info
```

```yaml
# prod/api
_ocmo:
  extend:
    configs:
      - ../../base/global@stable
      - ../../base/prod
    mode: accumulate

database:
  host: db.prod.example.com
  pool_size: 20
log_level: warn
```

Resolved:

```yaml
database:
  host: db.prod.example.com  # from current (wins)
  port: 5432                 # from base/global
  pool_size: 20              # from current (wins)
log_level: warn              # from current (wins)
```

---

## Mode: `distribute`

Apply **the same** patch (from `by`, or the entire document data) to **each** config listed in `configs`. **One output per config in the list.**

```
configs[0] + patch  →  output[0]
configs[1] + patch  →  output[1]
```

**Use case:** broadcast a shared overlay (feature flags, rollout settings) to multiple independently-named services.

```yaml
# services/rollout-overlay
_ocmo:
  extend:
    configs:
      - services/api-config
      - services/worker-config
    mode: distribute
    by: .overlay               # only the "overlay" key is used as the patch

overlay:
  replicas: 3
  log_level: debug
  region: eu-west
```

Resolved (2 outputs):
- `api-config` — `services/api-config` merged with `{replicas: 3, log_level: debug, region: eu-west}`
- `worker-config` — `services/worker-config` merged with the same patch

If `by` is omitted, the entire document (minus `_ocmo`) is used as the patch.

---

## Mode: `align`

Each config is matched 1-to-1 with the corresponding element in the list at `by`. **One output per pair.** The number of entries in `configs` must equal the number of elements in the `by` list.

```
configs[0] + by[0]  →  output[0]
configs[1] + by[1]  →  output[1]
```

**Use case:** each base config gets its own specific patch — e.g., per-cluster configs extended with per-cluster override data.

```yaml
# project/clusters
_ocmo:
  extend:
    configs:
      - clusters/eu-base
      - clusters/us-base
    mode: align
    by: .patches

patches:
  - name: eu-cluster
    endpoint: k8s.eu.example.com
  - name: us-cluster
    endpoint: k8s.us.example.com
```

Resolved (2 outputs):
- `eu-base` — `clusters/eu-base` merged with `{name: eu-cluster, endpoint: k8s.eu.example.com}`
- `us-base` — `clusters/us-base` merged with `{name: us-cluster, endpoint: k8s.us.example.com}`

---

## Deep-merge behaviour

OCMO uses deep-merge. The later value wins on key conflicts in mappings. Lists replace entirely (not appended).

```yaml
# base
a: 1
b:
  x: 10
  y: 20
tags:
  - foo
  - bar
```

```yaml
# override
b:
  y: 99    # overwrites y; x is preserved
  z: 30    # new key added
tags:
  - baz    # replaces entire list
```

Merged:

```yaml
a: 1
b:
  x: 10
  y: 99
  z: 30
tags:
  - baz
```

---

## Path resolution

Paths in `configs` can be:
- **Absolute** within the namespace: `apps/api/base` (no leading `/`)
- **Relative** using `./` and `../`: `../base`, `./sibling`
- **Pinned**: `apps/base@stable`, `apps/base@3`
- **With parameter substitution** in the `path` field: `{!region}/base-config`

---

## Limits and safety

| Limit | Default | Env var |
|-------|---------|---------|
| Max total extend depth | 20 | `OCMO_MAX_CONFIG_RESOLVE_DEPTH` |
| Max configs in one `extend.configs` list | 50 | `OCMO_MAX_EXTEND_CONFIGS` |

Circular references are detected at resolve time and reported with the full cycle path. Hitting the depth limit also returns a descriptive error.

---

## Multi-output bases (chained extends)

When a base config itself produces multiple outputs (via `align` or `distribute`), those outputs expand in-place. This means an `accumulate` config that references a multi-output base will also produce multiple outputs.

---

## Walkthrough: four surfaces

### REST

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~resolve/apps/api/prod"
```

### Web UI

Navigate to the config → **Resolve** panel → resolve to see all outputs. Use **Trace** to inspect which bases participated.

### CLI

```bash
ocmo -n prod resolve apps/api/prod --cast json
ocmo -n prod resolve apps/api/prod --trace-only -o json   # inspect dependency chain
```

### SDK

```python
result = prod.resolve("apps/api/prod", cast="json")
for key, item in result.items():
    print(key, item.data)
```

---

## Related

- [Parameters](parameters.md) — applied before extend
- [Render](render.md) — applied after extend
- [Resolving overview](README.md)
