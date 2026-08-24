# Permission Operations

Every operation string used in `_permissions` policies, global permission rules, and the `can-i` endpoint.

## Global operations

| Operation | Description |
|-----------|-------------|
| `global:admin` | Full admin access: manage global rules, access global audit |
| `namespace:create` | Create a new namespace |
| `namespace:read` | List and view a namespace |
| `namespace:write` | Update namespace metadata and builtin configs |
| `namespace:delete` | Delete a namespace (cascades entire tree) |
| `namespace:audit` | View namespace audit log |

## Config operations

| Operation | Description |
|-----------|-------------|
| `config:read` | Read config content and metadata |
| `config:write` | Create or update a config |
| `config:delete` | Delete a config or version |
| `config:resolve` | Resolve a config (run the pipeline, produce artifact) |
| `config:tag` | Set or delete tags on a config |
| `config:describe` | Set the description of a config |
| `config:audit` | View audit timeline for a config |

## Template operations

| Operation | Description |
|-----------|-------------|
| `template:read` | Read template content |
| `template:write` | Create or update a template |
| `template:delete` | Delete a template |
| `template:tag` | Tag a template version |
| `template:describe` | Set description |
| `template:audit` | View audit timeline |

## Secret operations

| Operation | Description |
|-----------|-------------|
| `secret:read` | Read secret content (encrypted) |
| `secret:write` | Create or update a secret |
| `secret:delete` | Delete a secret |
| `secret:resolve` | Decrypt secret values for use in parameter substitution |
| `secret:tag` | Tag a secret version |
| `secret:describe` | Set description |
| `secret:audit` | View audit timeline |

## Resolver operations

| Operation | Description |
|-----------|-------------|
| `resolver:read` | View resolver config (not token values) |
| `resolver:write` | Create or update a resolver; rotate tokens |
| `resolver:delete` | Delete a resolver |
| `resolver:describe` | Set description |
| `resolver:audit` | View audit timeline |

## Folder operations

| Operation | Description |
|-----------|-------------|
| `folder:describe` | Set folder description |
| `folder:audit` | View folder audit timeline |

## Lock operations

| Operation | Description |
|-----------|-------------|
| `lock:read` | View locks |
| `lock:write` | Create or update a lock |
| `lock:delete` | Remove a lock |

## Notes

- Resolvers have **implicit** `config:resolve` and `secret:resolve` within their `access_scope`. No `_permissions` entry needed.
- Builtin paths (`_permissions`, `_webhooks`, `_git_sync`, `*.schema`) require `namespace:write` (enforced server-side regardless of policy).
- `"*"` in an operation list matches all operations in a policy.

## Related

- [Authorization](../features/authorization.md)
- [Identities and access](../concepts/identities-and-access.md)
