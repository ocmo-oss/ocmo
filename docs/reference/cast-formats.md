# Cast Formats

Output formats available in the resolve pipeline.

## `yaml` (default)

Standard YAML output. No options.

**Example input:**
```yaml
database:
  host: db.internal
  port: 5432
```

**Output:**
```yaml
database:
  host: db.internal
  port: 5432
```

---

## `json`

JSON output.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `indent` | `"2"` \| `"4"` \| `""` | `""` (compact) | JSON indentation |
| `sort_keys` | `"true"` \| `"false"` | `"false"` | Sort object keys |

**Example (indent=2):**
```json
{
  "database": {
    "host": "db.internal",
    "port": 5432
  }
}
```

---

## `env`

Environment variable format.

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `type` | `unix` \| `dotenv` \| `windows` | `unix` | Line ending and quote style |
| `export` | `"true"` \| `"false"` | `"false"` | Prefix keys with `export ` |
| `prefix` | string | `""` | Prepend to all key names |
| `lowercase` | `"true"` \| `"false"` | `"false"` | Lowercase key names |
| `nested_separator` | string | `__` | Separator for nested keys |

**Notes:**
- Nested YAML dicts are flattened: `database.host` → `DATABASE__HOST`
- Lists cannot be represented in env format
- `type=dotenv`: keys are quoted; useful for Docker `--env-file`

**Example (type=unix, nested_separator=__):**
```
DATABASE__HOST=db.internal
DATABASE__PORT=5432
```

**Example (type=unix, export=true):**
```
export DATABASE__HOST=db.internal
export DATABASE__PORT=5432
```

---

## `hcl`

HashiCorp Configuration Language (Terraform `.tfvars`-compatible).

No options.

**Example:**
```hcl
database = {
  host = "db.internal"
  port = 5432
}
```

---

## `raw`

Returns the config YAML document bytes unchanged. No serialization.

Use when the config body is already in its final format (shell script, certificate PEM, nginx config written as `render` output, etc.).

**Not compatible** with `_ocmo.extend` or `_ocmo.render` — those stages require structured YAML input.

---

## `python` (SDK only)

SDK-local pseudo-format. Sends `json` on the wire, then parses to Python `dict`/`list`.

- `wire_cast` in the `ResolveResult` reports `"json"`
- Use `result[name].data` to access the parsed object

---

## Format precedence

```
?cast= query param (or --cast / cast= in CLI/SDK)
  → resolver's default cast.format
    → _ocmo.cast.format in the config
      → yaml (default)
```

## Related

- [Cast feature](../features/resolving/cast.md)
- [Resolving overview](../features/resolving/README.md)
