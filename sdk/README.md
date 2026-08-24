# ocmo-sdk

Python client SDK for the OCMO REST API.

- **Import package:** `ocmo`
- **Distribution name:** `ocmo-sdk`
- **Python:** 3.11+
- **License:** Apache-2.0

**Pre-1.0.0 notice:** Version `0.8.x` makes no compatibility guarantees until `1.0.0`. Use the SDK
release that matches your API server version.

---

## Installation

```bash
pip install ocmo-sdk
# or
uv add ocmo-sdk
```

Monorepo development (from repository root):

```bash
uv sync --package ocmo-sdk
```

---

## Quick start

```python
from ocmo import OcmoClient

with OcmoClient() as client:          # reads OCMO_SERVER, OCMO_TOKEN, etc.
    result = client.ns("prod").resolve("app/web", cast="json")
    config = result["app.json"].data  # lazy fetch + parse; no download until here
    host   = result["app.json"].get("database.host")
```

---

## Configuration

Every setting is available as an `OCMO_*` environment variable **and** as a constructor argument
(explicit argument wins).

| Variable | Default | Description |
|----------|---------|-------------|
| `OCMO_SERVER` | *(required)* | Base URL, e.g. `https://ocmo.example.com` |
| `OCMO_NAMESPACE` | — | Default namespace |
| `OCMO_TIMEOUT` | `30` | Per-request timeout (s) |
| `OCMO_CONNECT_TIMEOUT` | `10` | Connection timeout (s) |
| `OCMO_RETRIES` | `3` | Retry attempts |
| `OCMO_MAX_CONCURRENCY` | `8` | Parallel artifact downloads |
| `OCMO_CA_BUNDLE` | system store | PEM bundle path |
| `OCMO_INSECURE_SKIP_TLS_VERIFY` | `false` | Disables TLS verification (warns) |
| `OCMO_AUTH_MODE` | inferred | `oidc` \| `resolver-token` \| `bearer` \| `none` |
| `OCMO_CLIENT_ID` | — | OAuth2 client ID (OIDC) |
| `OCMO_CLIENT_SECRET` | — | Client secret (prefer `OCMO_CLIENT_SECRET_FILE`) |
| `OCMO_CLIENT_SECRET_FILE` | — | File containing the secret |
| `OCMO_OIDC_ISSUER` | from API | OIDC issuer URL |
| `OCMO_OIDC_SCOPE` | `openid` | OAuth2 scopes |
| `OCMO_OIDC_AUDIENCE` | from API | `aud` claim required by provider |
| `OCMO_OIDC_GRANT_TYPE` | `client_credentials` | `client_credentials` or `password` (local Dex) |
| `OCMO_OIDC_USERNAME` | — | Resource-owner username for `password` grant |
| `OCMO_OIDC_PASSWORD` | — | Password for `password` grant (prefer `OCMO_OIDC_PASSWORD_FILE`) |
| `OCMO_OIDC_PASSWORD_FILE` | — | File containing the password |
| `OCMO_TOKEN` | — | Resolver token (`ocmort-…`) or bearer token |
| `OCMO_TOKEN_FILE` | — | File containing the token |
| `OCMO_CACHE_DIR` | `~/.cache/ocmo` | Token cache location |
| `OCMO_LOG_LEVEL` | `WARNING` | Logger level |
| `OCMO_SKIP_VERSION_CHECK` | `false` | Disable version compatibility check |

Auth mode is inferred when unset: `ocmort-…` token → `resolver-token`; other token → `bearer`;
`OCMO_CLIENT_ID` → `oidc`. Ambiguous combinations raise `OcmoConfigError`.

---

## Authentication

### OIDC (machine-to-machine)

```bash
export OCMO_SERVER=https://ocmo.example.com
export OCMO_CLIENT_ID=my-service
export OCMO_CLIENT_SECRET_FILE=/run/secrets/ocmo-secret
```

The SDK performs `client_credentials` against the OIDC token endpoint (discovered from
`OCMO_OIDC_ISSUER` or the API's `/api/version` response), caches the token on disk (`~/.cache/ocmo`,
mode `0600`), and refreshes proactively at 80% of `expires_in`.

**Local stack (Dex ≤ v2.45):** Dex does not yet expose `client_credentials`. Use the
`ocmo-sdk` confidential client with the password grant:

```bash
export OCMO_SERVER=http://localhost:8080
export OCMO_SKIP_VERSION_CHECK=true
export OCMO_CLIENT_ID=ocmo-sdk
export OCMO_CLIENT_SECRET=dev-only-ocmo-sdk-secret
export OCMO_OIDC_ISSUER=http://localhost:8080/dex/
export OCMO_OIDC_GRANT_TYPE=password
export OCMO_OIDC_USERNAME=admin@example.com
export OCMO_OIDC_PASSWORD=password
export OCMO_OIDC_SCOPE="openid profile email groups"
```

### Resolver token

```bash
export OCMO_TOKEN=ocmort-…
```

Sent as `X-Ocmo-Resolver-Token`. Scoped to resolve, parameters, `whoami`, and `can-i`.

### Pre-obtained bearer

```bash
export OCMO_TOKEN=eyJhbGci…
```

No refresh. On `401`, re-reads `OCMO_TOKEN_FILE` once if set.

---

## Resolving configs

```python
result = client.ns("prod").resolve(
    "app/web",
    version="stable",
    cast="json",
    params={"env": "eu"},
    cast_options={"indent": "2"},
)

result.cache_status          # "hit" | "cast" | "miss"
data = result["app.json"].data
result.prefetch()
result.save_all("./configs/")
```

`cast="python"` is SDK-local: the wire format is JSON; `result.wire_cast` reports `"json"`.

---

## Error handling

```python
from ocmo import (
    OcmoConfigError,
    OcmoAuthError,
    OcmoPermissionError,
    OcmoNotFoundError,
    OcmoConflictError,
    OcmoLockedError,
    OcmoValidationError,
    OcmoTransportError,
    ArtifactExpiredError,
    ChecksumMismatchError,
    NoArtifactError,
    UnstructuredFormatError,
    PropertyNotFoundError,
)
```

---

## Generated client code

REST operations are generated from OpenAPI into `ocmo/_generated/` using
`openapi-python-client`, then wrapped in `ocmo/_facade_impl.py`. Do not edit generated files by
hand. Stable operation IDs live in `operations.yaml` (mirrored in `api/core/operation_ids.py`).

```python
client.whoami()
client.list_namespaces()
client.ns("prod").list_locks()
```

Do not import `ocmo._generated` directly.

---

## Development

```bash
cd sdk/
uv sync
make test               # pytest, ≥90% coverage on hand-written code
make lint               # ruff
make typecheck          # mypy --strict
make spec               # export openapi.json from api/
make generate           # regenerate ocmo/_generated/
make generate-facade    # regenerate ocmo/_facade_impl.py
make build              # wheel + sdist in dist/
```

CI gates:

1. `make generate` diff must be empty.
2. `make lint` and `make typecheck` pass.
3. `make test` meets coverage threshold.

From monorepo root: `uv sync --package ocmo-sdk` and `uv run --package ocmo-sdk pytest sdk/tests`.

---

## Related components

- CLI: [../cli/README.md](../cli/README.md)
- API: [../api/README.md](../api/README.md)
- Integration guides: [../docs/how-to/README.md](../docs/how-to/README.md) · [../docs/reference/sdk.md](../docs/reference/sdk.md)
- Monorepo overview: [../README.md](../README.md)
