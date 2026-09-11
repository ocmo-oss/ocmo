# Output Naming

Each resolved artifact has a `name` field in the response. By default, the name comes from the config's position in the tree. `_ocmo.name` lets you override it — useful when the desired output filename contains characters that OCMO tree paths don't allow.

---

## Default names

| Scenario | Default name |
|---------|-------------|
| Single-config resolve (`stack`) | Generating config `_ocmo.name` or last path segment |
| Folder resolve | Relative path from base: `app/web` resolved from `app/` → `web` |
| Multi-output extend `broadcast` / `zip` | Target config `_ocmo.name` or path leaf |
| Multi-output extend `replicate` | Target config name + `-1`, `-2`, … before extension |
| Multi-output render `broadcast` / `zip` | Template path leaf or `# ocmo.name:` header |
| Multi-output render `replicate` | `# ocmo.name:` in template (Jinja + context); no auto suffix |

---

## Overriding with `_ocmo.name`

```yaml
_ocmo:
  name: "nginx.conf"
```

or with parameter substitution:

```yaml
_ocmo:
  name: "configs/{!env}/web.yaml"
```

**What can `_ocmo.name` contain?** Any string, including characters not allowed in OCMO paths: `@`, `&`, `#`, spaces, Unicode. The path separator `/` is allowed and has special meaning in folder resolution (see below).

---

## Single-config resolve

`_ocmo.name` on the generating config replaces the default name entirely.

```yaml
# Config at: k8s/prod/nginx-deployment
_ocmo:
  name: "nginx-deployment@prod.yaml"
```

Resolve response `items[0].name` = `"nginx-deployment@prod.yaml"`.

CLI writes the file as `nginx-deployment@prod.yaml`:

```bash
ocmo -n prod resolve k8s/prod/nginx-deployment -O ./output/
# → ./output/nginx-deployment@prod.yaml
```

---

## Folder resolve

When `_ocmo.name` **contains a `/`**, it is treated as a full override path (relative to the folder resolve root). Only the **last segment** is replaced when there is no `/`.

| `_ocmo.name` value | Effect in folder resolve |
|--------------------|--------------------------|
| `"web"` | Replaces only the last segment; base path from the folder root is preserved |
| `"configs/web.json"` | Full path override (with `/`); replaces relative path entirely |
| _(not set)_ | Default relative path from resolve base |

**Example — preserve folder structure:**

```
Namespace tree:
  apps/api/web          (_ocmo.name: "web-api.json")
  apps/api/worker       (_ocmo.name: "worker.json")

Folder resolve: GET /~resolve/apps/api/
Response items:
  name: "web-api.json"    (last segment replaced)
  name: "worker.json"     (last segment replaced)
```

**Example — full path override:**

```
apps/api/web  (_ocmo.name: "output/web-api@v2.json")

Folder resolve: GET /~resolve/apps/api/
Response items:
  name: "output/web-api@v2.json"   (full override, replaces relative path)
```

CLI respects the full path when writing to the target directory:

```bash
ocmo -n prod resolve apps/api/ -O ./output/
# → ./output/output/web-api@v2.json
```

---

## Multi-output naming

`_ocmo.name` on the **generating** config applies only to **single-output** (`stack`) resolutions.

| Extend mode | Name source |
|-------------|-------------|
| `broadcast`, `zip` | Each **target config** (`_ocmo.name` or path leaf) |
| `replicate` | Target config name + numeric suffix on every output (`myconf-1.yaml`, `myconf-2.yaml`, …) |

| Render mode | Name source |
|-------------|-------------|
| `broadcast`, `zip` | Template path leaf, or `# ocmo.name:` first line in rendered body |
| `replicate` | `# ocmo.name:` in template (use context variables); no automatic suffix |

Set `_ocmo.name` on each **target config** (extend) or use `# ocmo.name:` in templates (render) to customize names.

---

## Duplicate name deduplication

When a resolve produces **more than one** output and two or more items share the same name, OCMO assigns numeric suffixes before the extension to duplicates:

```
conf.yaml, conf.yaml, conf.yaml  →  conf.yaml, conf-1.yaml, conf-2.yaml
```

The **first** occurrence keeps the original name; later duplicates get `-1`, `-2`, and so on. This applies across all multi-output modes after mode-specific naming runs.

---

## Parameters in names

```yaml
_ocmo:
  name: "configs/{!env}-web.yaml"
  parameters:
    env:
      type: dynamic
      value: prod
```

Resolve with `?param_env=staging` → artifact name: `configs/staging-web.yaml`.

---

## Related

- [Resolving overview](README.md)
- [Folder resolve](folders.md)
- [Parameters](parameters.md)
- [Extend](extend.md)
- [Render](render.md)
