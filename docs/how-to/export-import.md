# Export and Import

How to back up, migrate, or duplicate OCMO configs between namespaces or instances.

---

## Export: resolve and dump all configs

The fastest way to export a subtree is folder resolve:

```bash
# Export all configs under app/ as YAML files
ocmo -n prod resolve app/ --version stable -O ./backup/

# Export as JSON
ocmo -n prod resolve app/ --version stable --cast json -O ./backup/

# With SDK — include version metadata
from ocmo import OcmoClient

with OcmoClient() as client:
    prod = client.ns("prod")
    result = prod.resolve("app/", version="stable")
    result.prefetch()
    result.save_all("./backup/")
    for name, item in result.items():
        print(name, f"v{item.version}", item.checksum)
```

---

## Export: get raw config content (with _ocmo intact)

Folder resolve strips the `_ocmo` block. To export the raw config source (including `_ocmo`):

```bash
# Individual config
ocmo -n prod get item app/web@stable --raw > app-web.yaml

# Script to export all configs preserving _ocmo
#!/bin/bash
NAMESPACE=prod
EXPORT_DIR=./raw-export

ocmo -n $NAMESPACE search tree --type config -o json | \
  python3 -c "
import sys, json, subprocess, pathlib

items = json.load(sys.stdin)['results']
for item in items:
    path = item['path']
    tag = 'stable'
    output = subprocess.check_output([
        'ocmo', '-n', '$NAMESPACE', 'get', 'item', f'{path}@{tag}', '--raw'
    ])
    dest = pathlib.Path('$EXPORT_DIR') / f'{path}.yaml'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(output)
    print(f'Exported {path}')
"
```

---

## Import: push configs from files

```bash
# Import one file
ocmo -n staging create config app/web -f backup/app/web.yaml
# or update if it already exists:
ocmo -n staging update config app/web -f backup/app/web.yaml

# Bulk import script
#!/bin/bash
NAMESPACE=staging
IMPORT_DIR=./raw-export

find "$IMPORT_DIR" -name "*.yaml" | while read -r file; do
    # Derive path from filename relative to import dir
    rel="${file#$IMPORT_DIR/}"
    path="${rel%.yaml}"

    if ocmo -n "$NAMESPACE" get item "$path" &>/dev/null; then
        ocmo -n "$NAMESPACE" update config "$path" -f "$file"
        echo "Updated $path"
    else
        ocmo -n "$NAMESPACE" create config "$path" -f "$file"
        echo "Created $path"
    fi
done
```

---

## Copy a single config to another namespace

```bash
# Export from source namespace
ocmo -n prod get item app/web@stable --raw > /tmp/app-web.yaml

# Import to destination namespace
ocmo -n staging update config app/web -f /tmp/app-web.yaml || \
  ocmo -n staging create config app/web -f /tmp/app-web.yaml
```

---

## Copy a config between paths in the same namespace

```bash
# OCMO copy (same namespace, same version)
ocmo -n prod copy item app/web app/web-backup

# Copy with REST
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~copy/app/web" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"target_path": "app/web-backup"}'
```

---

## Handling secrets in export/import

Secrets **cannot** be exported via folder resolve — they are excluded. To migrate secrets:

1. Reveal the secret content in the source namespace (requires `secret:read`).
2. Create the secret in the destination namespace.

```bash
# Export (reveals plaintext — handle carefully)
ocmo -n prod get item secrets/db@stable --reveal --raw > /tmp/db-secret.yaml

# Import
ocmo -n staging create secret secrets/db -f /tmp/db-secret.yaml

# Immediately delete the temp file
rm /tmp/db-secret.yaml
```

Or use the SDK with `reveal=True` and post directly to the destination without touching disk.

---

## Related

- [Folder resolve](../features/resolving/folders.md)
- [Configs](../features/configs.md)
- [Secrets](../features/secrets.md)
