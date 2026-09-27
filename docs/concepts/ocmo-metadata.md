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
    configs:
      - base/database@stable
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

Merge other configs into this one before the artifact is produced. Sources are deep-merged in order; the current config's data is merged last and always wins on conflict.

```yaml
_ocmo:
  extend:
    configs:
      - base/database@stable
      - path: shared/all@stable
        key: .database               # extract a subtree before merging
        as: .persistence              # place it at a different key
    mode: stack                        # stack | broadcast | zip | replicate
    by: .some.key                      # required for zip and replicate; optional for broadcast
```

| Sub-field | Required | Description |
|-----------|----------|-------------|
| `configs` | Yes | List of config references to merge, in order |
| `mode` | No | Merge strategy. Default: `stack` |
| `by` | No | Selector into this config's data. Required for `zip` and `replicate`; optional for `broadcast` |

Each entry in `configs` is either a **path string** or an **object**:

| Entry field | Required | Description |
|-------------|----------|-------------|
| *(string)* | — | Whole document at the given path. Pin with `@stable`, `@3`, etc. Append `?` to skip if path or version is absent |
| `path` | Yes (object form) | Config path with optional `@version` suffix. Supports `{!param}` substitution |
| `key` | No | Selector into the resolved source to extract a subset (e.g. `.database`). Append `?` to skip if key is missing |
| `as` | No | Selector describing where to place the extracted value in the merge target |
| `skip_missing` | No | When `true`, skip this source if the config path or version/tag is absent (default `false`) |

`key` selects *what* to take; `as` selects *where* to put it.

See [Extend](../features/resolving/extend.md) for modes, merge semantics, and examples.

---

### `render`

Apply Jinja2 templates to this config's data. The template output becomes the artifact.

```yaml
_ocmo:
  render:
    templates:
      - templates/nginx-vhost@latest
    mode: broadcast                    # broadcast | zip | replicate
```

**Mutually exclusive with `cast`** — use one or the other.

`mode` (`broadcast`, `zip`, `replicate`) controls multi-template output. `by` is required for `zip` and `replicate`.

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

Override the output artifact filename. Does not affect the item's path in the tree. Evaluated **after extend merge** using `{.selector}` placeholders (not `{!param}`).

```yaml
_ocmo:
  name: "nginx.conf"
  # merged data + name-owner metadata:
  name: "{._ocmo.Name}-{.database.env}.yaml"
```

See [Output naming](../features/resolving/output-naming.md) for full syntax, examples per extend/render mode, and name ownership rules.

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
