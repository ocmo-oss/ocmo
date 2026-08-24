# Limits

Server-side limits and their controlling environment variables.

## Upload sizes

| Content type | Env var | Default |
|-------------|---------|---------|
| Config body | `OCMO_MAX_CONFIG_UPLOAD_BYTES` | 1,048,576 (1 MiB) |
| Template body | `OCMO_MAX_TEMPLATE_UPLOAD_BYTES` | 1,048,576 (1 MiB) |
| Secret body | `OCMO_MAX_SECRET_UPLOAD_BYTES` | 262,144 (256 KiB) |

## Resolve pipeline limits

| Limit | Env var | Default | Notes |
|-------|---------|---------|-------|
| Max dynamic parameter overrides per request | `OCMO_MAX_PARAMETERS` | 50 | `param_<name>=` query params |
| Max configs in `_ocmo.extend` list | `OCMO_MAX_EXTEND_CONFIGS` | see server | Per config |
| Max extend recursion depth | `OCMO_MAX_EXTEND_DEPTH` | see server | Transitive extends |
| Max templates in `_ocmo.render` list | `OCMO_MAX_RENDER_TEMPLATES` | see server | |
| Max propagation targets | `OCMO_MAX_PROPAGATION_TARGETS` | 5 | Per `_ocmo.propagation.targets` |

## Artifact and caching TTLs

| Setting | Env var | Default | Notes |
|---------|---------|---------|-------|
| Signed download URL TTL | `OCMO_RESOLVE_URL_TTL` | 300 seconds | Re-resolve after expiry |
| Artifact retention | `OCMO_RESOLVE_ARTIFACT_MAX_AGE` | 86,400 seconds (24h) | Filesystem / Redis |
| Resolve cache TTL | `OCMO_RESOLVE_CACHE_TTL` | 3,600 seconds (1h) | Short-circuit identical resolves |

## Artifact storage

| Setting | Env var | Values | Default |
|---------|---------|--------|---------|
| Artifact backend | `OCMO_RESOLVE_ARTIFACT_BACKEND` | `fs`, `redis` | `fs` |
| Artifact directory (fs) | `OCMO_RESOLVE_ARTIFACT_DIR` | path | `/tmp/ocmo/resolved` |
| Cache backend | `OCMO_RESOLVE_CACHE_BACKEND` | `locmem`, `redis` | `locmem` |

## Path and name constraints

| Field | Constraint |
|-------|-----------|
| Namespace name | `^[a-zA-Z0-9_-]+$`; case-insensitive uniqueness |
| Item path | `^[a-zA-Z0-9_.+\-/]+$`; no leading or trailing `/` |
| Tag name | `^[a-zA-Z0-9_.\+\-]+$` |
| Item description | Max 4,096 characters (Markdown) |
| Lock reason | 1–500 characters |
| Lock `expires_at` | Must be in the future; minimum ~30 minutes (UI enforced) |

## Pagination defaults

| Resource | Default page size |
|----------|------------------|
| Most list endpoints | 100 items |
| SDK auto-pagination threshold | 100 (fetches multiple pages if `limit > 100`) |

## Related

- [Configuration reference](../quickstart/configuration.md)
- [Errors reference](errors.md)
