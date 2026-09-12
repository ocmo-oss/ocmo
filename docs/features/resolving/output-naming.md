# Output Naming

Each resolved artifact has a `name` field in the response. This document is the **canonical guide** for how output filenames are chosen across plain resolve, extend, render, and folder resolve.

---

## Overview

- **Default:** last segment of the **name owner's** config path when `_ocmo.name` is not set.
- **`_ocmo.name`:** optional template evaluated **after extend merge** for that output.
- **Placeholders:** `{.selector}` only (not `{!param}`).
  - **Data:** `{.env}`, `{.database.env}` — merged output data for that artifact.
  - **Metadata:** `{._ocmo.Name}`, `{._ocmo.Path[-2]}`, `{._ocmo.Version.tag}`, `{._ocmo.Version.number}` — name owner's config path/version.
- **Render:** `# ocmo.name:` in a template body **wins** over extend-resolved `_ocmo.name`.
- **Duplicates:** when multiple outputs share a name, later ones get `-1`, `-2`, … before the extension (no replicate auto-suffix).

### Name owner by mode

| Scenario | Who owns `_ocmo.name` |
|----------|----------------------|
| Plain resolve / extend `stack` | **Generating** config |
| Extend `broadcast`, `zip`, `replicate` | Each **target** config in `extend.configs` |
| Render | `# ocmo.name:` in template, else extend/stack name above |

---

## Placeholder reference

| Placeholder | Source |
|-------------|--------|
| `{._ocmo.Name}` | Name owner's leaf path segment |
| `{._ocmo.Path}` | Name owner's full path |
| `{._ocmo.Path[-2]}` | Path segment by index (negative indices supported) |
| `{._ocmo.Version.tag}` | Version ref used in resolve (`latest`, `stable`, …) |
| `{._ocmo.Version.number}` | Resolved integer version |
| `{.any.other.path}` | Merged output data (after `strip_omit`) |

Missing placeholder → resolve fails:

```text
_ocmo.name on configs/business: placeholder {.env} not found in resolved data.
```

---

## Plain resolve (no extend/render)

```yaml
# apps/api/web
_ocmo:
  name: "web-api.json"
```

→ `web-api.json`

With placeholders:

```yaml
_ocmo:
  name: "{._ocmo.Name}-{.tier}.yaml"
tier: prod
```

→ `web-prod.yaml` (path leaf `web` + data field `tier`).

---

## Folder resolve

When `_ocmo.name` **contains `/`**, it can fully override the relative path in folder resolve. When it has no `/`, only the **last segment** is replaced.

| `_ocmo.name` | Folder resolve from `apps/api/` |
|--------------|-----------------------------------|
| `"web-api.json"` | `web-api.json` (replaces leaf only) |
| `"output/web-api.json"` | `output/web-api.json` (full override) |
| _(not set)_ | Default relative path (`web`, `worker`, …) |

See [Folder resolve](folders.md) for path rules.

---

## Extend

Naming runs **after** each output's data is merged. Targets use their own `_ocmo.name`; the generating config's `_ocmo.name` applies only in **`stack`** mode.

### `stack`

Generating config owns the name. ResolveContext = full merged data (bases + generating).

```yaml
# app/prod.yaml
_ocmo:
  extend:
    mode: stack
    configs: [../bases/base]
  name: "app-{.database.env}.yaml"
database:
  env: prod
```

```yaml
# bases/base.yaml
database:
  env: base
  port: 5432
```

→ **`app-prod.yaml`** (generating `env` wins on conflict).

### `broadcast`

Each **target** config owns `_ocmo.name`. Patch from `by` (or whole doc) is merged into each target before naming.

```yaml
# rollout.yaml
_ocmo:
  extend:
    mode: broadcast
    by: .overlay
    configs: [../targets/svc-a]
overlay:
  region: eu
```

```yaml
# targets/svc-a.yaml
_ocmo:
  name: "{._ocmo.Name}-{.region}.yaml"
name: svc-a
```

→ **`svc-a-eu.yaml`** (`region` comes from merged overlay patch).

### `zip`

Each target owns `_ocmo.name`. Patch row `by[i]` is merged with `configs[i]` before naming.

```yaml
# root.yaml
_ocmo:
  extend:
    mode: zip
    by: .patches
    configs: [../targets/base-a]
patches:
  - {env: dev}
```

```yaml
# targets/base-a.yaml
_ocmo:
  name: "app-{.env}.yaml"
```

→ **`app-dev.yaml`**

### `replicate`

Single target owns `_ocmo.name`. Each `by` list row is merged with the base; **no automatic `-1`/`-2` suffix** — use data-driven placeholders for distinct names.

```yaml
# final.yaml
_ocmo:
  extend:
    mode: replicate
    by: .data
    configs: [../bases/business]
data:
  - {env: dev}
  - {env: staging}
```

```yaml
# bases/business.yaml
_ocmo:
  name: "app-{.env}.yaml"
foo: bar
```

→ **`app-dev.yaml`**, **`app-staging.yaml`**

If every row resolves to the same static name, deduplication applies: `conf.yaml`, `conf-1.yaml`, …

### Nested extend

A target may run its own extend (e.g. `stack`) before the parent merges a patch. The **target** still owns `_ocmo.name`; ResolveContext is that output's fully merged data **including** the parent's patch.

---

## Render

Render runs after extend naming. **`# ocmo.name:`** on the first line of rendered output overrides the extend-resolved name.

### `broadcast`

Default name = template path leaf. Override with header:

```jinja2
# ocmo.name: nginx.conf
...
```

### `zip`

One render per template/context pair; use `# ocmo.name:` per template when names must differ.

### `replicate`

Use Jinja in the header for per-row names:

```jinja2
# ocmo.name: {{ slug }}.yaml
value: {{ value }}
```

If the header is absent and the config declared `_ocmo.name`, the extend-resolved name is used; otherwise the template path leaf applies.

### Extend + render on same config

1. Extend merge → evaluate `_ocmo.name` per output.
2. Render naming precedence per artifact:
   - `# ocmo.name:` in template body **wins** when present.
   - Else, when `_ocmo.name` was set on the config → use the **extend-resolved** name.
   - Else (render-only) → template path **leaf** (e.g. `nginx.conf.j2`).

---

## Duplicate name deduplication

When a resolve produces **more than one** output and names collide:

```text
conf.yaml, conf.yaml, conf.yaml  →  conf.yaml, conf-1.yaml, conf-2.yaml
```

The first occurrence keeps its name.

---

## Errors

| Condition | Result |
|-----------|--------|
| Missing data/metadata placeholder | `CannotResolveConfig` with `_ocmo.name on <path>: placeholder {.…} not found in resolved data.` |
| Non-scalar placeholder value | Resolve fails |
| Resolved name with `..` segment or leading/trailing `/` | Resolve fails |
| `{!param}` in `_ocmo.name` at save | Validation error |

---

## Related

- [Resolving overview](README.md)
- [Extend](extend.md)
- [Render](render.md)
- [Folder resolve](folders.md)
- [Parameters](parameters.md) — `{!param}` applies to config **body** only, not `_ocmo.name`
