# Configs

A **Config** is a YAML document stored at a path in a namespace. It is the primary item type in OCMO — the thing you resolve, inherit, compare, and version.

---

## Config vs Template

| | Config | Template |
|-|--------|----------|
| Format | YAML | Jinja2 (any output format) |
| Resolved directly? | Yes | No — rendered by a Config via `_ocmo.render` |
| Has `_ocmo` block? | Yes | No |
| Versioned? | Yes | Yes |
| `stable` tag? | Yes | No (use custom tags) |

---

## Create

Send the YAML body as the raw request body (not a JSON envelope).

```bash
# REST
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~config/~create/app/web" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/yaml" \
  --data-binary @app.yaml

# CLI
ocmo -n prod create config app/web -f app.yaml
ocmo -n prod create config app/web <<'EOF'
environment: production
replicas: 3
database:
  host: db.prod.internal
  port: 5432
EOF

# SDK
prod.create_config("app/web", content=open("app.yaml").read())
```

- Parent folders are created automatically.
- Returns HTTP 409 if a config already exists at the path.
- Returns HTTP 422 if the body is not valid YAML.
- First version (1) created; `latest` tag points to it.

## Read

```bash
# REST — latest version
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~get/app/web"

# REST — specific version or tag
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~get/app/web?version=stable"

# CLI
ocmo -n prod get item app/web
ocmo -n prod get item app/web@stable

# SDK
item = prod.get_item("app/web")
item = prod.get_item("app/web", version="stable")
print(item.data)          # parsed dict
print(item.raw_content)   # raw YAML string
```

## Update

```bash
# REST
curl -X PUT "https://ocmo.example.com/api/v1/ns/prod/~config/~update/app/web" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/yaml" \
  --data-binary @updated.yaml

# CLI
ocmo -n prod update config app/web -f updated.yaml

# SDK
prod.update_config("app/web", content=updated_yaml)
```

- Creates a new version only if the content changed.
- Identical content → no new version, no error.
- `latest` advances to the new version.

## Version history

```bash
# REST
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~versions/app/web"

# CLI
ocmo -n prod get version app/web
ocmo -n prod get version app/web --tagged-only

# SDK
history = prod.list_item_versions("app/web")
```

## Tags

```bash
# Set a custom tag
ocmo -n prod tag item app/web --tag v1.0.0
ocmo -n prod tag item app/web --tag v1.0.0 --version 3   # explicit version

# Delete a custom tag
ocmo -n prod untag item app/web --tag v1.0.0

# REST — set
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~tag/app/web" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"tag": "v1.0.0", "version": 3}'

# REST — delete (omit version)
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~tag/app/web" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"tag": "v1.0.0"}'
```

Reserved tags: `latest` (auto-managed), `stable` (advance via `mark-stable=true` on resolve).

## Delete

```bash
# Preview what would be deleted (default)
ocmo -n prod delete item app/web --preview

# Execute
ocmo -n prod delete item app/web -y

# Delete a single version
ocmo -n prod delete version app/web --version 3 -y

# REST — delete whole item
curl -X DELETE "https://ocmo.example.com/api/v1/ns/prod/~delete/app/web?preview=false" \
  -H "Authorization: Bearer $TOKEN"

# REST — soft-delete one version
curl -X DELETE "https://ocmo.example.com/api/v1/ns/prod/~delete/app/web?version=3&preview=false" \
  -H "Authorization: Bearer $TOKEN"
```

Deleting a whole item removes all versions and any now-empty parent folders. Soft-deleting a version clears its content but preserves the version number in history.

## Move and copy

```bash
# Move
ocmo -n prod move item app/web app/api-web

# Copy (copies current latest version)
ocmo -n prod copy item app/web app/web-backup

# REST — move
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~move/app/web" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"target_path": "app/api-web"}'

# REST — copy
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~copy/app/web" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"target_path": "app/web-backup"}'
```

## Diff

```bash
# Diff two versions of the same config
ocmo -n prod diff app/web --from-version 2 --to-version 3

# Diff current against stable
ocmo -n prod diff app/web --from stable --to latest

# REST
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~diff/app/web?from=2&to=3"
```

The UI shows a structured inline diff in the **Versions** panel.

## Description (Markdown)

```bash
# CLI
ocmo -n prod describe app/web --description "# Web config\n\nPrimary web API config."

# REST
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~describe/app/web" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"description": "# Web config\n\nPrimary web API config."}'
```

Descriptions don't create a new content version.

## Search

```bash
# REST
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~search/?q=database&type=config"

# CLI
ocmo -n prod search tree --q "database" --type config
```

---

## Upload size limit

Default: 1 MiB (`OCMO_MAX_CONFIG_UPLOAD_BYTES`). Returns HTTP 413 if exceeded.

---

## Required permissions

| Operation | Permission |
|-----------|-----------|
| Read / get | `config:read` |
| Create / update | `config:write` |
| Delete | `config:delete` |
| Tag | `config:tag` |
| Resolve | `config:resolve` |
| Set description | `config:describe` |
| Move (source) | `config:write` |
| Copy (source) | `config:read` |

---

## Related

- [Templates](templates.md)
- [Resolving](resolving/README.md)
- [Versions and tags](../concepts/versions-and-tags.md)
- [Validation](validation.md)
- [Propagation](propagation.md)
