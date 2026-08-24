# Install the SDK

## Install

```bash
# pip
pip install ocmo-sdk

# uv (recommended for projects)
uv add ocmo-sdk
```

Requires Python 3.11+.

---

## Configure

The SDK reads configuration from environment variables. The only required variable is `OCMO_SERVER`.

```bash
export OCMO_SERVER=https://ocmo.example.com
export OCMO_NAMESPACE=prod          # optional default namespace
```

Auth is inferred automatically from which credentials you set (see [Authentication modes](#authentication-modes) below).

You can also pass config directly:

```python
from ocmo import OcmoClient, OcmoConfig

client = OcmoClient(
    server="https://ocmo.example.com",
    namespace="prod",
)
```

---

## Minimal example

```python
from ocmo import OcmoClient

with OcmoClient() as client:
    # Resolve a config and read its data
    result = client.ns("prod").resolve("app/web", cast="json")
    data = result["app/web"].data
    print(data["database"]["host"])

    # Access a nested value with dot notation
    host = result["app/web"].get("database.host")

    # Save all resolved artifacts to disk
    result.save_all("./configs/")
```

---

## Async

```python
import asyncio
from ocmo import AsyncOcmoClient

async def main():
    async with AsyncOcmoClient() as client:
        prod = client.ns("prod")
        result = await prod.resolve("app/web", cast="json")
        data = await result["app/web"].data_async()
        print(data["database"]["host"])

asyncio.run(main())
```

---

## Authentication modes

The SDK auto-detects auth mode from the environment variables that are set. Only one mode should be active at a time.

### OIDC client credentials (recommended for services)

```bash
export OCMO_CLIENT_ID=my-service
export OCMO_CLIENT_SECRET=...
# OCMO_OIDC_GRANT_TYPE defaults to client_credentials
```

The SDK obtains and caches OIDC tokens automatically; tokens are refreshed before expiry.

### Password grant (local Dex only)

```bash
export OCMO_CLIENT_ID=ocmo-sdk
export OCMO_CLIENT_SECRET=dev-only-ocmo-sdk-secret
export OCMO_OIDC_GRANT_TYPE=password
export OCMO_OIDC_USERNAME=admin@example.com
export OCMO_OIDC_PASSWORD=password
```

### Resolver token (read-only, for services pulling config)

```bash
export OCMO_TOKEN=ocmort-abc123...
```

The `ocmort-` prefix tells the SDK to use `X-Ocmo-Resolver-Token` header instead of Bearer.

### Bearer token (existing token)

```bash
export OCMO_TOKEN=eyJhbGci...    # any token not starting with ocmort-
```

Token is re-read from `OCMO_TOKEN_FILE` on 401 (useful for token rotation in containers).

---

## Working with resolved artifacts

```python
from ocmo import OcmoClient

with OcmoClient() as client:
    prod = client.ns("prod")
    result = prod.resolve(
        "app/web",
        version="stable",           # tag or version number; default "latest"
        cast="json",                # yaml | json | env | hcl | raw | python
        params={"env": "staging"},  # dynamic parameter overrides
        cast_options={"indent": "2"},
        mark_stable=True,           # advance "stable" tag after resolve
    )

    # Cache status
    print(result.cache_status)      # "hit" | "cast" | "miss"

    # Access individual items (lazy download on first access)
    item = result["app/web"]
    print(item.bytes)               # raw bytes
    print(item.text)                # decoded string
    print(item.data)                # parsed dict (JSON/YAML only)
    print(item.get("database.host"))  # dot-path into data

    # Save to disk
    item.save("./app.json")

    # Prefetch all items concurrently
    result.prefetch()
    result.save_all("./configs/")   # writes each item by its name
```

---

## Error handling

```python
from ocmo import (
    OcmoClient,
    OcmoNotFoundError,
    OcmoLockedError,
    OcmoPermissionError,
    OcmoAuthError,
    OcmoValidationError,
)

with OcmoClient() as client:
    try:
        result = client.ns("prod").resolve("app/web")
    except OcmoNotFoundError:
        print("Config not found or tag doesn't exist")
    except OcmoLockedError as e:
        print(f"Path locked at {e.lock_path}: {e.reason}")
    except OcmoPermissionError:
        print("Access denied — check _permissions policy")
    except OcmoAuthError:
        print("Authentication failed — check OCMO_TOKEN or client credentials")
    except OcmoValidationError as e:
        print("Validation error:", e.errors)
```

---

## TLS and proxy settings

```bash
# Custom CA bundle
export OCMO_CA_BUNDLE=/etc/ssl/certs/my-ca.pem

# Disable TLS verification (not recommended; prints a warning)
export OCMO_INSECURE_SKIP_TLS_VERIFY=true

# Timeout and retries
export OCMO_TIMEOUT=30          # per-request timeout in seconds
export OCMO_CONNECT_TIMEOUT=10
export OCMO_RETRIES=3
```

---

## Related

- [SDK reference](../reference/sdk.md)
- [Authentication](../features/authentication.md)
- [Resolving overview](../features/resolving/README.md)
