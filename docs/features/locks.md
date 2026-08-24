# Locks

Locks prevent write operations on a path and all its descendants. Use them to enforce change freezes before deployments, during release windows, or for compliance-required freeze periods.

Reads and resolves are never blocked by locks. Tags with `mark-stable=true` are blocked (they modify a tag, which is a write).

---

## Creating a lock

```bash
# REST — lock with expiry
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~lock/myapp/prod" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Production freeze — release 2026-Q3",
    "expires_at": "2026-09-01T06:00:00Z"
  }'

# REST — lock without expiry (manual removal required)
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~lock/myapp/prod" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Compliance freeze — pending audit"}'

# CLI
ocmo -n prod lock myapp/prod \
  --reason "Production freeze — release 2026-Q3" \
  --expires-at 2026-09-01T06:00:00Z

# SDK
prod.lock_path(
    "myapp/prod",
    reason="Production freeze — release 2026-Q3",
    expires_at="2026-09-01T06:00:00Z",
)
```

The path must already exist as a tree item. Attempting to lock a non-existent path returns HTTP 404.

Each path can hold at most one lock. Creating a lock on an already-locked path returns HTTP 409.

---

## Lock scope

A lock on `myapp/prod` blocks writes on:
- `myapp/prod` itself
- `myapp/prod/web`
- `myapp/prod/api/config`
- Any other item under `myapp/prod/**`

It does **not** block:
- `myapp/staging` (different branch)
- Reads or resolves on any locked path

---

## What is blocked

When any write operation hits a locked path, the API returns HTTP **423 Locked**:

```json
{
  "error": "Path is locked",
  "lock_path": "myapp/prod",
  "reason": "Production freeze — release 2026-Q3",
  "expires_at": "2026-09-01T06:00:00Z"
}
```

Blocked operations include: create, update, delete (item or version), move (as source or target), copy (as target), tag, describe.

---

## Listing locks

```bash
# REST — list all active locks
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~lock/"

# CLI
ocmo -n prod get lock
ocmo -n prod get lock -o wide   # with expiry and creator

# SDK
locks = prod.list_locks()
```

Only active (non-expired) locks are returned.

## Get a specific lock

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~lock/myapp/prod"

ocmo -n prod get lock myapp/prod
```

## Update a lock (extend expiry or change reason)

```bash
# REST — PUT replaces the lock
curl -X PUT "https://ocmo.example.com/api/v1/ns/prod/~lock/myapp/prod" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Extended freeze — pending rollback review",
    "expires_at": "2026-09-02T06:00:00Z"
  }'

# CLI
ocmo -n prod update lock myapp/prod \
  --reason "Extended freeze" \
  --expires-at 2026-09-02T06:00:00Z
```

## Remove a lock

```bash
# REST
curl -X DELETE "https://ocmo.example.com/api/v1/ns/prod/~lock/myapp/prod" \
  -H "Authorization: Bearer $TOKEN"

# CLI
ocmo -n prod delete lock myapp/prod

# SDK
prod.unlock_path("myapp/prod")
```

---

## Lock expiry

Locks with an `expires_at` timestamp expire automatically — no action required. Expired locks are filtered from list responses and no longer block writes. Removing them explicitly before expiry is optional.

---

## Required permissions

| Operation | Permission |
|-----------|-----------|
| List locks | `lock:read` |
| Get lock details | `lock:read` on the locked path |
| Create lock | `lock:write` on the path |
| Update lock | `lock:write` on the locked path |
| Remove lock | `lock:delete` on the locked path |

---

## Related

- [Authorization](authorization.md)
- [CI/CD guide](../how-to/ci-cd.md) — enforcing change freezes in pipelines
