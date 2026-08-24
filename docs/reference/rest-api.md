# REST API Reference

Base URL: `https://<ocmo-host>/api/v1/`

Interactive docs (Swagger): `https://<ocmo-host>/api/docs`

---

## URL conventions

- `~` prefix — all action verbs and object-type prefixes start with `~` (e.g. `~resolve`, `~config`). This guarantees they never collide with user-defined path segments (which cannot contain `~`).
- Generic actions work on any item type: `~get`, `~delete`, `~move`, `~copy`, `~tag`, `~describe`, `~diff`, `~versions`, `~navigate`, `~search`.
- Type-specific actions use a prefix: `~config/~create`, `~template/~update`, `~secret/~create`, `~resolver/~create`.

---

## Unauthenticated endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health probe. Returns 200 when all dependencies are up. |
| `GET` | `/api/version` | Version and OIDC bootstrap config for clients. |

---

## Auth endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/auth/whoami/` | Current identity details |
| `POST` | `/api/v1/auth/can-i/` | Batch permission probe |

---

## Namespace endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/ns/` | List namespaces (`?name_filter=`, `?limit=`, `?offset=`) |
| `POST` | `/api/v1/ns/` | Create namespace |
| `GET` | `/api/v1/ns/{ns}` | Get namespace details |
| `PATCH` | `/api/v1/ns/{ns}` | Update namespace metadata or active tags |
| `DELETE` | `/api/v1/ns/{ns}` | Delete namespace and all contents |

---

## Global permissions (admin only)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/global-permissions/` | Get ordered rules list |
| `POST` | `/api/v1/global-permissions/` | Append a rule |
| `GET` | `/api/v1/global-permissions/{rule_id}` | Get a rule |
| `PUT` | `/api/v1/global-permissions/{rule_id}` | Replace a rule |
| `DELETE` | `/api/v1/global-permissions/{rule_id}` | Delete a rule |
| `POST` | `/api/v1/global-permissions/{rule_id}/~move/` | Reorder |

---

## Generic tree actions (any item type)

All paths below are relative to `/api/v1/ns/{ns}/`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `~get/{path}` | Read item at version (`?version=latest`) |
| `GET` | `~versions/{path}` | Version history |
| `GET` | `~navigate/{path}` | Tree navigation (`?recursive=false`) |
| `GET` | `~search/` | Search (`?q=`, `?type=`, `?limit=`, `?offset=`) |
| `POST` | `~move/{path}` | Move item to new path — body: `{target_path}` |
| `POST` | `~copy/{path}` | Copy item — body: `{target_path}` |
| `DELETE` | `~delete/{path}` | Delete item or version (`?version=`, `?preview=true`) |
| `POST` | `~tag/{path}` | Set or delete a tag — body: `{tag, version?}` |
| `POST` | `~describe/{path}` | Set Markdown description — body: `{description}` |
| `GET` | `~diff/{path}` | Diff versions (`?from=`, `?to=`) |

---

## Config create/update

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `~config/~create/{path}` | Body: raw YAML. Content-Type: `application/yaml` |
| `PUT` | `~config/~update/{path}` | Body: raw YAML |

---

## Template create/update

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `~template/~create/{path}` | Body: Jinja2 source. Content-Type: `text/plain` |
| `PUT` | `~template/~update/{path}` | Body: Jinja2 source |

---

## Secret create/update

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `~secret/~create/{path}` | Body: raw YAML |
| `PUT` | `~secret/~update/{path}` | Body: raw YAML |
| `GET` | `~get/{path}?reveal=true` | Decrypted content (requires `secret:read`) |

---

## Resolver create/update

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `~resolver/~create/{path}` | Body: JSON `{description?, config?}` |
| `PATCH` | `~resolver/~update/{path}` | Body: JSON `{description?, config?, regenerate_token?}` |

---

## Resolve

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `~resolve/{path}` | Resolve a config or folder |
| `POST` | `~resolve-draft/{path}` | Draft resolve (body: raw YAML) |
| `GET` | `~resolve/{path}/~download/{token}` | Download artifact (no auth) |
| `GET` | `~resolve-parameters/{path}` | Inspect effective parameters |

Query params for `~resolve`: `version`, `cast`, `trace_only`, `mark-stable`, `no-creds`, `ignore-configs-with-missing-tags`, `param_<name>`, `cast_option_<key>`.

---

## Validation

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/~config-metadata-schema` | JSON Schema for the `_ocmo` block |
| `GET` | `~config-schema/{path}` | JSON Schema stored at path |

---

## Locks

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `~lock/` | List active locks |
| `GET` | `~lock/{path}` | Get lock details |
| `POST` | `~lock/{path}` | Create lock — body: `{reason, expires_at?}` |
| `PUT` | `~lock/{path}` | Replace lock |
| `DELETE` | `~lock/{path}` | Remove lock |

---

## Propagation

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `~propagate/{path}` | Trigger manual propagation |

---

## Audit

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `~audit/` | Namespace audit log (`?path=`, `?actor=`, `?action=`, `?from=`, `?to=`, `?limit=`, `?offset=`) |
| `GET` | `/api/v1/~audit/` | Global audit log (admin only) |

---

## Common HTTP status codes

| Code | Meaning |
|------|---------|
| `200` | OK |
| `201` | Created |
| `204` | No-op (tag already set, etc.) |
| `400` | Bad request |
| `401` | Missing or invalid token |
| `403` | Permission denied |
| `404` | Not found (or path hidden by permissions) |
| `409` | Conflict (duplicate path, already locked, etc.) |
| `413` | Upload too large |
| `422` | Validation error |
| `423` | Path is locked |
| `503` | Service dependency unhealthy |

---

## Request body notes

Create and update endpoints for Config, Template, and Secret accept only the **raw document** as the request body — no JSON envelope. Supported Content-Types:
- Config: `application/yaml`, `application/json`, `application/octet-stream`
- Template: `text/plain`, `text/x-jinja2`, `application/octet-stream`
- Secret: `application/yaml`, `application/octet-stream`

`multipart/form-data` is not supported.

---

## Related

- [Errors reference](errors.md)
- [Permissions reference](permissions.md)
- [Cast formats reference](cast-formats.md)
