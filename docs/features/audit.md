# Audit Log

OCMO records every operation — reads, writes, resolves, and failed attempts — in an append-only audit log. Audit entries cannot be deleted or modified.

---

## What is recorded

| Event type | Captured when |
|------------|--------------|
| Config / template / secret / resolver / folder write | Created, updated, deleted, moved, copied, tagged, described |
| Resolve | Config or folder resolved; includes which version and format |
| Read | Config / secret read (configurable verbosity) |
| Authentication | Login, logout, token use |
| Namespace operations | Created, updated, deleted |
| Permission checks | Access denied events (always audited) |

Each entry contains:
- **Who** — identity (OIDC user email/sub or resolver path)
- **What** — action type
- **Resource** — namespace + path + version
- **When** — UTC timestamp
- **Outcome** — success or failure code
- **Details** — action-specific metadata (e.g. from/to paths for move, cast format for resolve)

---

## Audit verbosity

Controlled by `OCMO_AUDIT_MODE` (defaults to `all` in debug mode, `resolve` in production):

| Mode | What is recorded |
|------|-----------------|
| `resolve` | Resolve calls only (reads of configs via `~resolve` and `~resolve-parameters`) |
| `modifications-and-resolve` | All writes/deletes/tags + resolves |
| `all` | Everything including reads (`~get`, `~navigate`, `~search`, `~versions`) |

Audit cannot be fully disabled.

---

## Query the audit log

```bash
# REST — paginated list
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~audit/?limit=50&offset=0"

# REST — filter by path
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~audit/?path=app/web&limit=100"

# REST — filter by actor
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~audit/?actor=alice@example.com"

# REST — filter by action type
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~audit/?action=config.resolve"

# REST — time range
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~audit/?from=2026-08-01T00:00:00Z&to=2026-08-24T23:59:59Z"

# CLI
ocmo -n prod get audit --limit 50
ocmo -n prod get audit --path app/web --action resolve
ocmo -n prod get audit --actor alice@example.com --from 2026-08-01 --to 2026-08-24

# SDK
entries = prod.list_audit_log(limit=50, path="app/web")
```

## Example audit entry

```json
{
  "id": "01j...uuid",
  "timestamp": "2026-08-24T18:42:11.341Z",
  "actor": {
    "type": "user",
    "identifier": "alice@example.com",
    "display_name": "Alice"
  },
  "action": "config.resolve",
  "namespace": "prod",
  "resource": {
    "path": "app/web",
    "version": 7,
    "type": "config"
  },
  "outcome": "success",
  "details": {
    "cast": "json",
    "cache_status": "hit",
    "mark_stable": false,
    "trace_participants": ["base/database@3", "base/logging@12"]
  }
}
```

---

## Global audit (across namespaces)

The global admin can query the global audit log (all namespaces):

```bash
# REST
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/~audit/?limit=50"

# CLI
ocmo get audit --all-namespaces --limit 50
```

---

## Required permissions

| Operation | Permission |
|-----------|-----------|
| Read namespace audit log | `audit:read` in namespace policy or Global `audit` |
| Read global audit log | Global admin or Global `audit` rule |

---

## Related

- [Authorization](authorization.md) — `audit:read` permission
- [Configuration reference](../quickstart/configuration.md) — `OCMO_AUDIT_MODE`
