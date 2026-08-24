# Deliver Config to a Host

The standard pattern for getting OCMO config onto a machine or into a container at startup, using a resolver token.

---

## Prerequisites

- An OCMO namespace with your configs
- A resolver created at the path your host should pull from
- The resolver token (from `ocmo -n prod create resolver`)

## Pattern 1: CLI in an entrypoint / init script

Install the CLI in your image and resolve at startup:

```dockerfile
FROM python:3.13-slim
RUN pip install ocmo-cli
...
```

`entrypoint.sh`:

```bash
#!/bin/bash
set -euo pipefail

# Resolve all configs in scope and write to /etc/myapp/
ocmo -n prod resolve . \
  --cast env \
  --target /etc/myapp/ \
  --version stable

# Source env file if that's what you need
source /etc/myapp/web

exec "$@"
```

Environment:

```bash
OCMO_SERVER=https://ocmo.example.com
OCMO_TOKEN=ocmort-abc123...   # from resolver creation
```

The `.` path resolves the resolver's entire scope (all configs under the resolver's parent path).

## Pattern 2: SDK at application startup

```python
import os
from ocmo import OcmoClient

def load_config():
    with OcmoClient() as client:
        result = client.ns(os.environ["OCMO_NAMESPACE"]).resolve(
            ".",                # resolve all in scope
            version="stable",
            cast="python",
        )
        return result["app/web"].data

config = load_config()
DATABASE_HOST = config["database"]["host"]
```

Environment:

```bash
OCMO_SERVER=https://ocmo.example.com
OCMO_NAMESPACE=prod
OCMO_TOKEN=ocmort-abc123...
```

## Pattern 3: sidecar (Kubernetes)

Run the CLI as an init container to populate a shared volume:

```yaml
initContainers:
  - name: config-fetch
    image: ghcr.io/yourorg/ocmo-cli:latest
    command:
      - /bin/sh
      - -c
      - |
        ocmo -n prod resolve . \
          --version stable \
          --cast env \
          --target /etc/config/
    env:
      - name: OCMO_SERVER
        value: https://ocmo.example.com
      - name: OCMO_TOKEN
        valueFrom:
          secretKeyRef:
            name: ocmo-resolver-token
            key: token
    volumeMounts:
      - name: config-vol
        mountPath: /etc/config

containers:
  - name: myapp
    volumeMounts:
      - name: config-vol
        mountPath: /etc/config
        readOnly: true
```

## Pattern 4: curl (no CLI, minimal image)

```bash
#!/bin/bash
# Two-step: resolve → get URL → download
RESPONSE=$(curl -sf \
  -H "X-Ocmo-Resolver-Token: $OCMO_TOKEN" \
  "https://ocmo.example.com/api/v1/ns/prod/~resolve/.?cast=json&version=stable")

# Download each artifact (URLs require no auth)
echo "$RESPONSE" | python3 -c "
import sys, json, urllib.request, os, pathlib
for item in json.load(sys.stdin)['items']:
    dest = pathlib.Path('/etc/myapp') / item['name']
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(urllib.request.urlopen(item['url']).read())
    print(f'Written {dest}', file=sys.stderr)
"
```

---

## Handling resolve failures

Fail fast rather than starting with stale config:

```bash
if ! ocmo -n prod resolve . --version stable --target /etc/myapp/; then
  echo "FATAL: failed to fetch config from OCMO" >&2
  exit 1
fi
```

---

## Token rotation (zero-downtime)

See [Resolvers — zero-downtime rotation](../features/resolvers.md#zero-downtime-rotation).

---

## Related

- [Resolvers](../features/resolvers.md)
- [Folder resolve](../features/resolving/folders.md)
- [Cast formats](../features/resolving/cast.md)
