# Cast Formats

After the resolve pipeline (parameters → extend), OCMO serializes the result to the requested output format. This is the "cast" step.

> **Mutually exclusive with `render`** — a config with `_ocmo.render` produces arbitrary text and is always returned as format `raw`. No explicit cast applies.

---

## Format priority (highest to lowest)

1. `?cast=` query parameter on the resolve call
2. Resolver's configured default cast (set on the resolver item)
3. `_ocmo.cast.format` embedded in the config
4. Default: `yaml`

---

## Setting cast in the config

```yaml
_ocmo:
  cast:
    format: json
    options:
      indent: 2
      sort_keys: true
```

---

## Overriding at resolve time

```bash
# REST
curl "https://ocmo.example.com/api/v1/ns/prod/~resolve/app/web?cast=json&cast_option_indent=2"

# CLI
ocmo -n prod resolve app/web --cast json --cast-option indent=2

# SDK
result = prod.resolve("app/web", cast="json", cast_options={"indent": "2"})
```

---

## Supported formats

### `yaml` (default)

Returns the resolved data as YAML. Preserves comments where possible.

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `indent` | `2` | Block indentation width (1–9) |
| `width` | `80` | Soft line-wrap width; `0` = no wrap |
| `sort_keys` | `false` | Sort keys alphabetically |
| `flow_style` | `block` | `block`, `flow`, or `auto` |
| `explicit_start` | `false` | Emit leading `---` |
| `explicit_end` | `false` | Emit trailing `...` |
| `trailing_newline` | `true` | Append newline at end |

---

### `json`

Converts YAML data to JSON.

```json
{
  "database": {
    "host": "db.prod.example.com",
    "port": 5432
  }
}
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `indent` | `null` | Pretty-print with N spaces; `null` = compact |
| `sort_keys` | `false` | Sort object keys |
| `ensure_ascii` | `false` | Escape non-ASCII as `\uXXXX` |
| `trailing_newline` | `false` | Append trailing newline |

---

### `env` — shell environment variables

Flattens YAML into shell-assignable key=value pairs. Nested keys joined with `_`.

Three dialects via `options.type`:

**Unix/bash (`type: unix` — default):**

```sh
export database_host='db.prod.example.com'
export database_port=5432
```

**Windows batch (`type: windows`):**

```bat
SET "database_host=db.prod.example.com"
SET "database_port=5432"
```

**PowerShell (`type: powershell`):**

```powershell
$env:database_host = 'db.prod.example.com'
$env:database_port = '5432'
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `type` | `unix` | `unix`, `windows`, `powershell` |
| `export` | `true` | Prefix unix lines with `export` |
| `uppercase` | `false` | UPPERCASE variable names |
| `prefix` | `""` | Prepend to every variable name (e.g. `APP_`) |
| `separator` | `_` | Separator between nested keys |
| `list_format` | `indexed` | `indexed` (`key_0`, `key_1`), `joined` (CSV), `json`, `space` |
| `null_handling` | `skip` | `skip` (omit), `empty` (`KEY=`), `literal` (`KEY=null`) |
| `bool_format` | `lower` | `lower` (`true`/`false`), `numeric` (`1`/`0`), `yesno`, `onoff` |
| `sort_keys` | `false` | Sort alphabetically |
| `strict` | `true` | Fail on names not matching `[A-Za-z_][A-Za-z0-9_]*` |
| `comment_header` | `false` | Emit a comment header with source config path/version |

**Flattening example:**

```yaml
app:
  name: myservice
  ports:
    - 8080
    - 8443
```

→

```sh
export app_name='myservice'
export app_ports_0=8080
export app_ports_1=8443
```

> The root must be a mapping (dict). A bare scalar at root raises an error.

---

### `hcl` — HashiCorp Configuration Language

Suitable for Terraform variable files.

```hcl
database = {
  host = "db.prod.example.com"
  port = 5432
}
```

With `tfvars: true`:

```hcl
database_host = "db.prod.example.com"
database_port = 5432
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `version` | `"2"` | HCL version: `"1"` or `"2"` |
| `indent` | `2` | Indentation width |
| `block_style` | `attribute` | `attribute` (`x = { ... }`) or `block` (`x { ... }`) |
| `sort_keys` | `false` | Sort attribute keys |
| `tfvars` | `false` | Emit `terraform.tfvars` style (flat top-level assignments) |
| `trailing_newline` | `true` | Append trailing newline |

---

### `raw`

Returns the root value as a raw text string. Requires the root to be a scalar string (not a mapping or list).

Use case: a config whose data is just a text file content (script, certificate, etc.).

```yaml
# app/entrypoint-script
_ocmo:
  cast:
    format: raw
    options:
      trailing_newline: true

value: |
  #!/bin/bash
  exec /opt/app/bin/server "$@"
```

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `strict` | `true` | Require root scalar; raise error if dict/list |
| `stringify` | `false` | When `strict=false`, YAML-dump non-scalar values instead of failing |
| `trailing_newline` | `false` | Append trailing newline |
| `strip` | `false` | Strip leading/trailing whitespace |

---

### `python`

Returns the resolved data as a native Python dict/list. **Only meaningful via the Python SDK** — the REST API always returns JSON.

```python
result = prod.resolve("app/web", cast="python")
data = result["app/web"].data   # already a dict, no JSON parsing step
print(type(data))               # <class 'dict'>
```

---

## Using env vars sourced from OCMO in a shell script

```bash
# Resolve and source into the current shell
source <(ocmo -n prod resolve app/web --cast env)

# Or save to a file first
ocmo -n prod resolve app/web --cast env -O .env
source .env
```

---

## Full reference

See [Cast formats reference](../../reference/cast-formats.md) for a single-page lookup table covering all formats, all options, and all defaults.

---

## Related

- [Resolving overview](README.md)
- [Extend](extend.md)
- [Render](render.md)
- [Output naming](output-naming.md)
