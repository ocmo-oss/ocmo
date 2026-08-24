# The `_ocmo` Metadata Block

The `_ocmo` block is an optional top-level key in any config YAML document. It controls how the config behaves in the resolve pipeline. The block is **stripped from the artifact output** — it never appears in the final resolved document that your service receives.

> **Configuration:** The metadata key name defaults to `_ocmo`. It is configurable per deployment via `OCMO_CONFIG_METADATA_KEY`.

---

## Quick example

```yaml
# This config's resolved output will have "environment", "replicas", and "database" —
# but NOT the "_ocmo" key.
_ocmo:
  parameters:
    env:
      type: dynamic
      value: production
      description: "Deployment environment"
    db_password:
      type: secret
      value: "secrets/db@stable:password"
  extend:
    - path: base/database
      version: stable
  cast:
    format: json
    options:
      indent: "2"
  validation:
    schema: schemas/app-config

environment: "{!env}"
replicas: 3
database:
  host: "db.{!env|lower}.internal"
  password: "{!db_password}"
```

---

## Fields

### `parameters`

Declare named values substituted via `{!param_name}` placeholders anywhere in the config body (YAML string values).

```yaml
_ocmo:
  parameters:
    env:
      type: dynamic          # dynamic | projected | secret
      value: production      # default (for dynamic); source (for projected/secret)
      description: "Env name"
```

Placeholders must be in quoted strings: `host: "{!env}.example.com"`.

Undeclared parameters are not substituted — they appear literally in the output. Declared parameters that are not used in the config body cause a validation error on save.

See [Parameters](../features/resolving/parameters.md) for the full reference.

---

### `extend`

Merge other configs into this one before the artifact is produced. Configs in the list are deep-merged into the current config's data; the current config's values always win on conflict.

```yaml
_ocmo:
  extend:
    - path: base/database
      version: stable
    - path: base/logging
      selector: logging   # take only the "logging" key from this config
```

| Sub-field | Required | Description |
|-----------|----------|-------------|
| `path` | Yes | Path to another config in the same namespace |
| `version` | No | Tag or version number. Default: `latest` |
| `selector` | No | Dot-path or list of dot-paths to extract a subset |
| `remap` | No | `{old_key: new_key}` — rename keys before merging |

Mode (`accumulate`, `distribute`, `align`) applies to the whole `extend` list. Default: `accumulate`.

See [Extend](../features/resolving/extend.md) for modes and merge semantics.

---

### `render`

Apply Jinja2 templates to this config's data. The template output becomes the artifact.

```yaml
_ocmo:
  render:
    - path: templates/nginx-vhost
      version: latest
```

**Mutually exclusive with `cast`** — use one or the other.

Mode (`distribute`, `align`) controls multi-template output.

See [Render](../features/resolving/render.md).

---

### `cast`

Set a default output format. Can be overridden at resolve time with `?cast=`.

```yaml
_ocmo:
  cast:
    format: json      # yaml | json | env | hcl | raw
    options:
      indent: "2"
      sort_keys: "true"
```

**Mutually exclusive with `render`**.

Format priority: `?cast=` query param → resolver default → `_ocmo.cast.format` → `yaml`.

See [Cast](../features/resolving/cast.md) and [Cast formats reference](../reference/cast-formats.md).

---

### `parameters` — `{!placeholder}` syntax

Placeholders go in YAML string values:

```yaml
host: "{!env}.example.com"            # simple
port: "{!port|int}"                   # with type transformer
url: "https://{!host}/{!path|urlencode}"  # multiple in one value
```

**Transformers** are appended with `|`:

| Transformer | Effect |
|-------------|--------|
| `lower` / `upper` | Case conversion |
| `slug` | Lowercase, non-alphanumeric → `-` |
| `snake` | Lowercase, non-alphanumeric → `_` |
| `trim` | Strip leading/trailing whitespace |
| `b64_encode` | Base64-encode the value |
| `urlencode` | URL-percent-encode |
| `escape_html` | HTML-escape `<>&"'` |
| `int` / `float` / `bool` / `null` | Type coercion (produces typed YAML scalar) |
| `multiline` | Preserve newlines |
| `omit` | Remove the key entirely if value is empty |

Multiple transformers chain left to right: `{!value|trim|lower|slug}`.

---

### `name`

Override the output artifact filename. Does not affect the item's path in the tree.

```yaml
_ocmo:
  name: "nginx.conf"
  # or with parameter substitution:
  name: "configs/{!env}/web.yaml"
```

See [Output naming](../features/resolving/output-naming.md).

---

### `validation`

Link this config to a JSON Schema config in the same namespace. The config body is validated against the schema on every save (create/update). Validation failures return HTTP 422.

```yaml
_ocmo:
  validation:
    schema: schemas/app-config   # path to a config with is_json_schema: true
```

See [Validation](../features/validation.md).

---

### `propagation`

When a trigger fires, copy this config's data into one or more target configs.

```yaml
_ocmo:
  propagation:
    trigger: tag      # tag | manual
    targets:
      - path: services/api
        mode: data    # data | whole
        exclude:
          - internal.debug
```

See [Propagation](../features/propagation.md).

---

### `is_json_schema`

Marks this config as a JSON Schema document. When set, no other `_ocmo` fields are allowed. The config becomes available via `GET /~config-schema/{path}`.

```yaml
_ocmo:
  is_json_schema: true

type: object
required: [port, host]
properties:
  port: { type: integer }
  host: { type: string }
```

See [Validation](../features/validation.md).

---

## Fetch the `_ocmo` JSON Schema

To see the full schema for the `_ocmo` block itself:

```bash
# REST
curl -H "Authorization: Bearer $TOKEN" \
  https://ocmo.example.com/api/v1/~config-metadata-schema

# CLI
ocmo schema ocmo
```

---

## Related

- [Resolving overview](../features/resolving/README.md)
- [Parameters](../features/resolving/parameters.md)
- [Extend](../features/resolving/extend.md)
- [Render](../features/resolving/render.md)
- [Cast](../features/resolving/cast.md)
