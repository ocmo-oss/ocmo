# Output Naming

Each resolved artifact has a `name` field in the response. By default, the name comes from the config's position in the tree. `_ocmo.name` lets you override it — useful when the desired output filename contains characters that OCMO tree paths don't allow.

---

## Default names

| Scenario | Default name |
|---------|-------------|
| Single-config resolve | Last path segment: `app/web` → `web` |
| Folder resolve | Relative path from base: `app/web` resolved from `app/` → `web` |
| Multi-output (extend distribute/align) | Last segment of each source config: `base/nginx` → `nginx` |
| Multi-output (render distribute/align) | Last segment of each template path: `templates/nginx.conf.j2` → `nginx.conf.j2` |

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

`_ocmo.name` replaces the default name entirely.

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

`_ocmo.name` only applies to **single-output** resolutions. When extend `distribute`/`align` or render `distribute`/`align` produces multiple outputs, each output is named from its **source** (the base config or template). To customize multi-output names, set `_ocmo.name` on each individual base config or template rather than on the generating config.

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
