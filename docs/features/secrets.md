# Secrets

Secrets store sensitive structured data (passwords, API tokens, SSH keys, certificates) alongside Configs in the same namespace tree. They follow the same versioning and path model as Configs but their content is encrypted at rest.

---

## What makes secrets different

| | Config | Secret |
|-|--------|--------|
| Format | YAML (plaintext) | YAML (AES-256-GCM encrypted at rest) |
| Content returned without `reveal=true`? | Yes | No — metadata only |
| Resolved directly? | Yes | No |
| Injected at resolve | No (it is the data) | Yes — via `_ocmo.parameters` |
| `stable` / `latest` tags | Yes | Yes |
| Change propagation | Yes | **No** |
| Folder resolve inclusion | Yes | **No** |

---

## Encryption

Every secret version is encrypted with AES-256-GCM:
- A **per-namespace DEK** (Data Encryption Key) is generated at namespace creation.
- The DEK is wrapped (encrypted) with the deployment-level **`OCMO_MASTER_KEY`**.
- A database dump without the master key yields only ciphertext.

**`OCMO_MASTER_KEY` must not be lost** — losing it makes all encrypted secrets unrecoverable. Back it up in a separate secrets store (vault, HSM).

---

## Create

Send the YAML body as the raw request body.

```bash
# REST
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~secret/~create/secrets/db" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/yaml" \
  --data-binary @db-secret.yaml

# CLI
ocmo -n prod create secret secrets/db -f db-secret.yaml

# Inline
cat <<'EOF' | ocmo -n prod create secret secrets/db
host: db.prod.internal
port: 5432
username: myapp
password: S3cur3P@ssw0rd!
EOF

# SDK
prod.create_secret("secrets/db", content=open("db-secret.yaml").read())
```

- Returns HTTP 409 if the path already exists.
- Returns HTTP 422 if the body is not valid YAML.

## Read (metadata only)

Without `reveal=true`, the response contains metadata but no decrypted content:

```bash
# REST — metadata only
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~get/secrets/db"

# REST — with content (reveal)
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~get/secrets/db?reveal=true"

# CLI
ocmo -n prod get item secrets/db             # metadata only
ocmo -n prod get item secrets/db --reveal    # decrypted content

# SDK
item = prod.get_item("secrets/db")           # metadata
item = prod.get_item("secrets/db", reveal=True)  # decrypted
```

Revealing a secret requires `secret:read` permission.

## Update

```bash
# REST
curl -X PUT "https://ocmo.example.com/api/v1/ns/prod/~secret/~update/secrets/db" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/yaml" \
  --data-binary @updated.yaml

# CLI
ocmo -n prod update secret secrets/db -f updated.yaml
```

## Tags

Secrets support `latest` (auto-managed) and custom tags. No `stable` promotion flow.

```bash
ocmo -n prod tag item secrets/db --tag v2
ocmo -n prod untag item secrets/db --tag v2
```

## Delete

```bash
# Preview
ocmo -n prod delete item secrets/db --preview

# Execute
ocmo -n prod delete item secrets/db -y

# Soft-delete one version
ocmo -n prod delete version secrets/db --version 2 -y
```

---

## Using secrets in configs via parameters

Reference a secret from a config's `_ocmo.parameters` block:

```yaml
# app/web
_ocmo:
  parameters:
    db_password:
      type: secret
      value: "secrets/db@stable:password"    # path@version:field
    api_token:
      type: secret
      value: "secrets/api-key"              # whole document (must be scalar)
    tls_cert:
      type: secret
      value: "secrets/tls:certificate"
      transformers:
        - b64_encode                        # safely embed multi-line cert

database:
  password: "{!db_password}"
api:
  token: "{!api_token}"
tls:
  cert: "{!tls_cert}"
```

Secret reference format:

```
<path>[@<version>][:<field.subfield>]
```

- `secrets/db@stable:password` — `password` field from the `stable` version
- `secrets/db:tls.cert` — nested `tls.cert` field, latest version
- `../shared/api-key` — relative path, latest version, whole document

**Rules:**
- Extracted value must be a single-line string; multi-line values fail resolution (use `b64_encode`)
- Values appear as `***` in trace output
- Requires `secret:resolve` permission (or use `?no-creds=true` to skip)

---

## Sensitive transformers

Use these on secret parameters to safely embed values in output documents:

| Transformer | Use case |
|-------------|---------|
| `b64_encode` | Embed PEM certificates, SSH keys, or any multi-line secret |
| `urlencode` | Embed passwords in connection URLs |
| `escape_html` | Embed in HTML/XML output |

---

## Upload size limit

Default: 256 KiB (`OCMO_MAX_SECRET_UPLOAD_BYTES`). Returns HTTP 413 if exceeded.

---

## Companion secrets (namespace builtins)

`_webhooks_secret` and `_git_sync_secret` are auto-created at namespace creation. They follow special rules:
- Cannot be deleted, moved, copied, or renamed.
- Only accessible to identities with Global `write` on the namespace.
- Not governed by namespace `secret:*` policies.
- Only referenceable from their parent builtin config (`_webhooks` or `_git_sync`).

---

## Required permissions

| Operation | Permission |
|-----------|-----------|
| Read metadata | `secret:read` |
| Read content (`reveal=true`) | `secret:read` |
| Create / update | `secret:write` |
| Delete | `secret:delete` |
| Tag | `secret:tag` |
| Resolve via parameter | `secret:resolve` |
| Set description | `secret:describe` |

---

## Related

- [Parameters](resolving/parameters.md) — how secrets are injected at resolve time
- [Authorization](authorization.md) — `secret:*` permission group
- [Configuration reference](../quickstart/configuration.md) — `OCMO_MASTER_KEY`
