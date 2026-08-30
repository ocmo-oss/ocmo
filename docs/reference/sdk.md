# Python SDK Reference

Package: `ocmo-sdk` (`from ocmo import OcmoClient, AsyncOcmoClient`)

---

## Client construction

```python
from ocmo import OcmoClient, AsyncOcmoClient, OcmoConfig

# From environment variables (recommended)
client = OcmoClient()

# Explicit config
client = OcmoClient(
    server="https://ocmo.example.com",
    namespace="prod",          # default namespace
    token="ocmort-abc123...",  # resolver token
)

# With full config object
config = OcmoConfig(
    server="https://ocmo.example.com",
    client_id="my-service",
    client_secret="...",
    timeout=30,
    retries=3,
)
client = OcmoClient(config=config)

# Context manager (recommended — ensures cleanup)
with OcmoClient() as client:
    ...

# Async
async with AsyncOcmoClient() as client:
    ...
```

---

## Top-level methods

| Method | Returns | Description |
|--------|---------|-------------|
| `client.ns(name)` | `NamespaceClient` | Get a namespace-scoped client |
| `client.whoami()` | `WhoamiResponse` | Current identity |
| `client.can_i(namespace, operations, resource)` | `CanIResponse` | Permission probe |
| `client.list_namespaces(**kwargs)` | `Page[NamespaceInfo]` | List namespaces |
| `client.create_namespace(name, description)` | `NamespaceInfo` | Create namespace |
| `client.get_namespace(name)` | `NamespaceInfo` | Get namespace |
| `client.update_namespace(name, **kwargs)` | `NamespaceInfo` | Update namespace |
| `client.delete_namespace(name)` | `None` | Delete namespace |
| `client.get_version()` | `VersionInfo` | API version and bootstrap |
| `client.get_health()` | `HealthInfo` | Health check |

---

## Namespace client (`ns`)

```python
prod = client.ns("prod")
```

### Config operations

| Method | Description |
|--------|-------------|
| `prod.get_item(path, version="latest", reveal=False)` | Get item with content |
| `prod.create_config(path, content)` | Create config from string/bytes |
| `prod.update_config(path, content)` | Update config |
| `prod.create_template(path, content)` | Create template |
| `prod.update_template(path, content)` | Update template |
| `prod.create_secret(path, content)` | Create secret |
| `prod.update_secret(path, content)` | Update secret |
| `prod.list_item_versions(path, **kwargs)` | Version history |
| `prod.delete_item(path, preview=True)` | Delete item |
| `prod.delete_version(path, version, preview=True)` | Soft-delete version |
| `prod.move_item(path, target_path, skip_reference_validation=False)` | Move |
| `prod.copy_item(path, target_path, tag_to_copy='latest', skip_reference_validation=False)` | Copy |
| `prod.set_tag(path, tag, version=None)` | Set or delete tag |
| `prod.describe_item(path, description)` | Set description |
| `prod.diff_item(path, from_version, to_version)` | Diff two versions |

### Resolve operations

| Method | Description |
|--------|-------------|
| `prod.resolve(path, **kwargs)` | Resolve config or folder |
| `prod.resolve_draft_config(path, content, **kwargs)` | Draft resolve |
| `prod.resolve_parameters(path, **kwargs)` | Inspect effective parameters |

`resolve` kwargs:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `version` | `"latest"` | Tag or version number |
| `cast` | `None` | Output format |
| `cast_options` | `{}` | Format-specific options |
| `params` | `{}` | Dynamic parameter overrides |
| `trace_only` | `False` | |
| `mark_stable` | `False` | |
| `no_creds` | `False` | |
| `ignore_configs_with_missing_tags` | `False` | Folder resolve only |

### Navigation and search

| Method | Description |
|--------|-------------|
| `prod.navigate_path(path, recursive=False)` | Navigate tree |
| `prod.search_root(q, type=None, **kwargs)` | Search |

### Resolver management

| Method | Description |
|--------|-------------|
| `prod.create_resolver(path, description=None, config=None)` | Create resolver |
| `prod.update_resolver(path, description=None, config=None, regenerate_token=None)` | Update |
| `prod.rotate_resolver_token(path, slot)` | Rotate token slot |

### Lock management

| Method | Description |
|--------|-------------|
| `prod.lock_path(path, reason, expires_at=None)` | Create lock |
| `prod.update_lock(path, reason, expires_at=None)` | Replace lock |
| `prod.unlock_path(path)` | Remove lock |
| `prod.list_locks(**kwargs)` | List active locks |

### Audit

| Method | Description |
|--------|-------------|
| `prod.list_audit_log(**kwargs)` | Query audit log |

### Propagation

| Method | Description |
|--------|-------------|
| `prod.propagate(path)` | Trigger manual propagation |

---

## Resolve result

```python
result = prod.resolve("app/web", cast="json")

result.cache_status        # "hit" | "cast" | "miss"
result.trace_only          # bool
result.items()             # dict-like iteration: name → ResolveItem
result["app/web"]          # access by path key
result.save_all("./out/")  # save all to directory
result.prefetch()          # download all in parallel

item = result["app/web"]
item.name          # artifact filename
item.version       # int
item.format        # "json", "yaml", etc.
item.checksum      # "sha256:..."
item.trace         # dependency dict
item.bytes         # raw bytes (lazy download)
item.text          # decoded string (lazy)
item.data          # parsed dict/list (JSON/YAML only; lazy)
item.get("database.host")  # dot-path into data
item.save("./app.json")    # save to file
```

---

## Error types

```python
from ocmo import (
    OcmoError,           # base
    OcmoNotFoundError,   # 404
    OcmoPermissionError, # 403
    OcmoAuthError,       # 401
    OcmoConflictError,   # 409
    OcmoLockedError,     # 423 — has .lock_path and .reason
    OcmoValidationError, # 422 — has .errors list
    OcmoServerError,     # 5xx
)
```

---

## Async

All `OcmoClient` methods have async equivalents on `AsyncOcmoClient`. The API is identical; just `await` the calls.

```python
from ocmo import AsyncOcmoClient

async with AsyncOcmoClient() as client:
    result = await client.ns("prod").resolve("app/web", cast="json")
    data = await result["app/web"].data_async()
```

---

## Environment variables

See [Configuration reference](../quickstart/configuration.md) for the full list of `OCMO_*` variables.

---

## Related

- [Install the SDK](../quickstart/install-sdk.md)
- [Resolving overview](../features/resolving/README.md)
