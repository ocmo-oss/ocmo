# Parameters

Parameters let you inject computed, caller-supplied, or secret values into a config at resolve time via `{!param_name}` placeholders.

---

## Quick example

```yaml
# app/web
_ocmo:
  parameters:
    env:
      type: dynamic
      value: production        # default when caller doesn't pass param_env
      description: "Target deployment environment"
    db_host:
      type: projected
      value: ".name"           # injected from the config's own name
    db_password:
      type: secret
      value: "secrets/db@stable:password"

environment: "{!env}"
database:
  host: "{!db_host}"
  password: "{!db_password}"
```

Resolve with an override:

```bash
# REST
curl "https://ocmo.example.com/api/v1/ns/prod/~resolve/app/web?param_env=staging"

# CLI
ocmo -n prod resolve app/web --param env=staging

# SDK
result = prod.resolve("app/web", params={"env": "staging"})
```

---

## Parameter types

### `dynamic`

The value comes from the **caller** at resolve time (query param `?param_<name>=`). If the caller doesn't supply it, the `value` field is used as the default.

```yaml
_ocmo:
  parameters:
    region:
      type: dynamic
      value: us-east-1          # default
      description: "AWS region"
```

> Dynamic parameters introduce implicit external dependencies. Prefer `projected` wherever you can derive the value from the config tree.

### `projected`

The value is **computed automatically** from the config's own metadata — no caller input required.

Sources:

| Source expression | What it returns |
|-------------------|----------------|
| `.name` | Last segment of the config path (`web` for `app/web`) |
| `.path` | Full config path (`app/web`) |
| `.path[-2]` | Second-to-last path segment |
| `.data.some.key` | Value of a key in the config's own data |
| `.Version.tag` | The version tag used in this resolve (e.g. `stable`, `latest`, `v1.2.0`) |
| `.Version.number` | The resolved version integer (e.g. `7`) |

```yaml
_ocmo:
  parameters:
    app_name:
      type: projected
      value: ".name"
    env:
      type: projected
      value: ".path[-2]"       # e.g. "prod" for apps/prod/api/web
```

### `secret`

The value is fetched from an encrypted **Secret** at resolve time. The reference string format:

```
<path>[@<version>][:<field.subfield>]
```

```yaml
_ocmo:
  parameters:
    db_password:
      type: secret
      value: "secrets/db@stable:password"     # path@version:field
    api_token:
      type: secret
      value: "../shared/api-key"              # relative path, latest version, whole doc
    tls_cert:
      type: secret
      value: "certs/app:tls.cert"             # nested field
```

**Rules:**
- Relative paths use `./` and `../` relative to the config's own folder.
- The extracted value must be a single-line string. Multi-line values cause resolution to fail — use `b64_encode` to embed them safely.
- Secret values appear as `***` in trace output; never in logs.
- Requires `secret:resolve` on the referenced secret path (unless `?no-creds=true`).

#### No-creds mode

When the caller passes `?no-creds=true`:
- Secret parameters receive `<secret-value-placeholder>` instead of the decrypted value.
- `secret:resolve` is not required.
- Useful for UI previews where the user can't access credentials.

```bash
curl "https://ocmo.example.com/api/v1/ns/prod/~resolve/app/web?no-creds=true"
```

---

## Placeholder syntax

Placeholders go inside **quoted YAML strings**:

```yaml
host: "{!env}.example.com"          # simple substitution
port: "{!port|int}"                 # with type transformer
url: "https://{!host}/{!path|urlencode}"  # multiple placeholders
```

> **Quoting is required.** `host: {!env}` will fail YAML parsing. Always use `"{!...}"`.

Undeclared parameters are **not** substituted — they appear literally. A declared parameter that is not used anywhere in the body is rejected at save time.

All parameter values are single-line strings. Newlines are stripped to prevent YAML corruption.

### Save-time reference validation

When a config is created or updated, extend, render, schema, and secret references in `_ocmo` are checked for existence. Placeholders in those reference paths (for example `../bases/{!env}` or `images/production@{!image_tag}`) are **substituted first** using the same rules as resolve:

- **Dynamic** parameters use their declared `value` default (no caller overrides at save time).
- **Projected** parameters are evaluated from this config's path, body, and version context (`latest` / next version number).

After substitution, the server validates that each resolved target exists (including the `@tag` or version suffix). Caller-supplied dynamic overrides (`?param_*=` / `--param`) are **not** checked on save — only at resolve time.

If a placeholder remains unresolved after substituting declared defaults, save fails with a validation error.

---

## Transformers

Append with `|`:

| Transformer | Effect | Example |
|-------------|--------|---------|
| `lower` | Lowercase | `{!env\|lower}` |
| `upper` | Uppercase | `{!env\|upper}` |
| `slug` | Lowercase; non-alphanumeric → `-` | `{!name\|slug}` |
| `snake` | Lowercase; non-alphanumeric → `_` | `{!name\|snake}` |
| `trim` | Strip whitespace | `{!value\|trim}` |
| `b64_encode` | Base64-encode | `{!secret\|b64_encode}` |
| `urlencode` | URL-percent-encode | `{!path\|urlencode}` |
| `escape_html` | Escape `<>&"'` | `{!note\|escape_html}` |
| `int` | Cast to integer YAML scalar | `{!replicas\|int}` |
| `float` | Cast to float | `{!ratio\|float}` |
| `bool` | Cast to boolean (`true`/`false`) | `{!flag\|bool}` |
| `null` | Cast to YAML null when value is empty | `{!opt\|null}` |
| `multiline` | Preserve embedded newlines | `{!cert\|b64_encode\|multiline}` |
| `omit` | Remove the key entirely when value is empty | `{!optional\|omit}` |

Chain multiple transformers left to right: `{!value|trim|lower|slug}`.

---

## Declaring parameters (`_ocmo.parameters` schema)

```yaml
_ocmo:
  parameters:
    <name>:
      type: dynamic | projected | secret
      value: <default or source>
      description: "Human-readable explanation"
      transformers:          # alternative to inline | syntax
        - lower
        - slug
```

Max 50 parameters per config (`OCMO_MAX_CONFIG_PARAMETERS`). Max 10 chained transformers per parameter (`OCMO_MAX_PARAMETER_TRANSFORMERS`).

---

## Parameter resolution at draft resolve

`POST /~resolve-draft/{path}` supports all parameter types. Supply dynamic overrides as query params:

```bash
curl -X POST \
  "https://ocmo.example.com/api/v1/ns/prod/~resolve-draft/app/web?param_env=staging" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/yaml" \
  --data-binary @draft.yaml
```

---

## Required permissions

| Parameter type | Required permissions |
|----------------|---------------------|
| `dynamic`, `projected` | `config:resolve` on the config |
| `secret` | `config:resolve` on the config **+** `secret:resolve` on each referenced secret |
| `secret` with `no-creds=true` | `config:resolve` only |

---

## Related

- [Extend](extend.md) — merge configs after parameters are applied
- [Secrets](../secrets.md) — `secret` parameter values come from here
- [Cast formats reference](../../reference/cast-formats.md)
