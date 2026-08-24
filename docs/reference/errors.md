# Errors Reference

HTTP status codes, exception names, and how to resolve each.

## Error response format

```json
{
  "error": "Human-readable message",
  "audit_event_id": "uuid (if the event was recorded)",
  "lock_path": "path/to/lock (only on 423)",
  "reason": "lock reason (only on 423)"
}
```

---

## 400 Bad Request

Invalid JSON body. Check the `Content-Type` header and body syntax.

---

## 401 Unauthorized

| Condition | Fix |
|-----------|-----|
| `Unauthenticated` — no `Authorization` header on a protected route | Add `Authorization: Bearer <token>` |
| `InvalidResolverToken` — resolver token failed HMAC check | Rotate the token; confirm the namespace matches the resolver |
| `InvalidResolveToken` — signed download URL expired or tampered | Re-resolve to get a fresh URL; check `OCMO_RESOLVE_URL_TTL` |
| JWT expired or signature invalid | Re-authenticate; check clock skew; check OIDC JWKS URL |

---

## 403 Forbidden

| Condition | Fix |
|-----------|-----|
| `PermissionDenied` — identity lacks the required operation | Check `_permissions` policy; use `can-i` to probe; check `permissions_tag` is set |
| `ResolverNamespaceMismatch` — resolver token used against wrong namespace | Use the correct resolver token for this namespace |
| No Bearer on an OIDC-only endpoint | Resolver tokens are not accepted here; use a JWT |

---

## 404 Not Found

| Condition | Fix |
|-----------|-----|
| `NotFound` — item path does not exist | Check the path; use `ls` or `navigate` to browse |
| `VersionNotFound` — requested version or tag does not exist | Check available versions with `get version`; use `@latest` or `@stable` |
| `PropagationNotConfigured` — `POST /~propagate/` on a config without `_ocmo.propagation` | Add a `propagation` block to the config's `_ocmo` |

---

## 409 Conflict

| Exception | Meaning | Fix |
|-----------|---------|-----|
| `NamespaceConflict` | Namespace with that name already exists | Use a different name |
| `TreeItemConflict` | Item at that path already exists | Use update instead of create, or choose a different path |
| `WrongMoveTargetException` | Move target is invalid (child of source, etc.) | Choose a different target path |
| `WrongCopyTargetException` | Copy target is invalid | Choose a different target path |
| `ConflictPathsDetected` | Batch operation has path collisions | Resolve naming conflicts before retrying |
| `LockAlreadyExists` | Lock at that path already exists | Use `PUT /~lock/` to replace it |

---

## 413 Payload Too Large

Upload exceeds the configured limit.

| Item type | Limit env var | Default |
|-----------|--------------|---------|
| Config | `OCMO_MAX_CONFIG_UPLOAD_BYTES` | 1 MiB |
| Template | `OCMO_MAX_TEMPLATE_UPLOAD_BYTES` | 1 MiB |
| Secret | `OCMO_MAX_SECRET_UPLOAD_BYTES` | 256 KiB |

---

## 422 Unprocessable Entity

Validation failure. The `error` field contains a list of messages.

| Condition | Fix |
|-----------|-----|
| Pydantic / Ninja input validation | Check the request body against the schema |
| Config fails JSON Schema validation | Fix the YAML to match the linked schema |
| `FolderCannotBeExplicitlyCreated` | Folders are implicit; create a child item instead |
| `ReservedTagsCantBeSet` | `latest` cannot be set manually; `stable` can only be set via `mark-stable` resolve or `POST /~tag/` |
| `ActiveTagCannotBeDeleted` | The tag is referenced as the namespace's active tag; change `permissions_tag` / `webhooks_tag` first |
| `NamespaceActiveTagNotFound` | The namespace's active tag doesn't exist on the target config | Create or set the tag first |
| Cast / resolve / parameter errors | Read the error message for specifics; use `trace_only` to debug |
| Template `TemplateError` | Check Jinja2 syntax and variable names in the template |

---

## 423 Locked

A lock on the path (or an ancestor path) is blocking the write.

```json
{
  "error": "Path is locked",
  "lock_path": "app/",
  "reason": "deploy freeze",
  "audit_event_id": "..."
}
```

Fix: remove the lock (`DELETE /~lock/{lock_path}`), wait for it to expire, or coordinate with whoever created it.

See [Locks](../features/locks.md).

---

## 500 Internal Server Error

| Condition | Fix |
|-----------|-----|
| `BrokenNamespace` | Namespace is in an invalid state; contact an admin |
| Pydantic response validation error | API bug; report with the `audit_event_id` |
| Unhandled exception | Check API logs; report with the `audit_event_id` |

---

## SDK exceptions → HTTP status

| SDK exception | Status |
|---------------|--------|
| `OcmoAuthError` | 401 |
| `OcmoPermissionError` | 403 |
| `OcmoNotFoundError` | 404 |
| `OcmoConflictError` | 409 |
| `OcmoPayloadTooLargeError` | 413 |
| `OcmoValidationError` | 422 |
| `OcmoLockedError` | 423 (`.lock_path`, `.reason`) |

## Related

- [Locks](../features/locks.md)
- [Authorization](../features/authorization.md)
- [Troubleshoot resolving](../how-to/troubleshoot-resolve.md)
