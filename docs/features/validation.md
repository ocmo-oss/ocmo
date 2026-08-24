# Validation

OCMO validates config bodies against **JSON Schema** — either automatically for namespace builtin configs (`_permissions`, `_webhooks`, `_git_sync`) or explicitly when a config declares `_ocmo.validation.schema`.

---

## JSON Schema configs

A JSON Schema document is stored as a regular Config with `_ocmo.is_json_schema: true`. Once marked, it cannot have any other `_ocmo` fields and it becomes available as a validation target.

```yaml
# schemas/app-config
_ocmo:
  is_json_schema: true

type: object
required:
  - environment
  - database
properties:
  environment:
    type: string
    enum: [development, staging, production]
  database:
    type: object
    required: [host, port]
    properties:
      host: { type: string }
      port: { type: integer, minimum: 1, maximum: 65535 }
      pool_size: { type: integer, minimum: 1, default: 5 }
```

## Declaring validation on a config

```yaml
# app/web
_ocmo:
  validation:
    schema: schemas/app-config   # path to a config with is_json_schema: true

environment: production
database:
  host: db.prod.internal
  port: 5432
```

From this point on, every write to `app/web` is validated against `schemas/app-config`. A body that fails validation is rejected with HTTP 422 and a list of schema errors.

## Walkthrough

### Creating the schema config

```bash
# REST
cat > schema.yaml <<'EOF'
_ocmo:
  is_json_schema: true

type: object
required: [environment, database]
properties:
  environment:
    type: string
    enum: [development, staging, production]
  database:
    type: object
    required: [host, port]
    properties:
      host: { type: string }
      port: { type: integer }
EOF

curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~config/~create/schemas/app-config" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/yaml" \
  --data-binary @schema.yaml

# CLI
ocmo -n prod create config schemas/app-config -f schema.yaml
```

### Linking a config to the schema

```bash
cat > app.yaml <<'EOF'
_ocmo:
  validation:
    schema: schemas/app-config

environment: production
database:
  host: db.prod.internal
  port: 5432
EOF

ocmo -n prod create config app/web -f app.yaml
```

### Attempting an invalid update

```bash
cat > bad.yaml <<'EOF'
_ocmo:
  validation:
    schema: schemas/app-config

environment: unknown   # not in enum!
database:
  host: db.prod.internal
  port: -1              # < 1
EOF

ocmo -n prod update config app/web -f bad.yaml
# → Error 422: environment must be one of: development, staging, production
#              database.port must be >= 1
```

### Fetching the schema

```bash
# REST
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~config-schema/schemas/app-config"

# Global _ocmo metadata schema
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/~config-metadata-schema"

# CLI
ocmo schema item schemas/app-config -n prod
ocmo schema ocmo
```

---

## Builtin schema validation

The namespace builtin configs `_permissions`, `_webhooks`, and `_git_sync` are always validated against OCMO's built-in schemas before each write. You cannot disable this. This prevents invalid policy documents from breaking access control.

If a policy is accidentally locked (e.g., you push a `_permissions` doc that denies everyone), the global admin can always recover by pushing a corrected version — global admin access to builtin configs is unconditional.

---

## Schema config rules

- A schema config cannot have any `_ocmo` fields other than `is_json_schema: true`.
- Schema configs are read-only from the perspective of validation — they are never themselves validated against another schema.
- Deleting a schema config does not automatically remove validation declarations from configs that reference it (those configs will start failing validation on next write — fix by removing `_ocmo.validation.schema` from them).

---

## Related

- [Configs](configs.md)
- [`_ocmo` metadata block](../concepts/ocmo-metadata.md)
- [Authorization](authorization.md) — `_permissions` validation
