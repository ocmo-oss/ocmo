# Quick Start

Get OCMO running, create a namespace, push your first config, and resolve it.

> **Prerequisites:** Docker and Docker Compose v2 installed and running.

---

## Step 1 — Start the stack

From the repo root (or wherever `docker-compose.dev.yml` lives):

```bash
docker compose -f docker-compose.dev.yml up --build
```

Wait for all services to become healthy. You should see lines like:

```
ocmo-api       | Django version 6.x, using settings 'ocmoapi.settings'
ocmo-api       | Starting development server at http://0.0.0.0:8000/
ocmo-gateway   | nginx: ready
```

**URLs:**

| Service | URL |
|---------|-----|
| Web UI + API (gateway) | <http://localhost:8080> |
| API (direct) | <http://localhost:8000> |
| OpenAPI / Swagger | <http://localhost:8080/api/docs> |

> **Dev credentials (local only — never use in production):**
>
> | Account | Email | Password |
> |---------|-------|----------|
> | Global admin | `admin@example.com` | `password` |
> | Developer | `developer@example.com` | `password` |

---

## Step 2 — Verify the API is healthy

```bash
curl http://localhost:8080/api/health
```

Expected response: `{"status": "ok", ...}`

---

## Step 3 — Get an access token

The dev stack uses [Dex](https://dexidp.io/) as the OIDC provider. Obtain a token via the SDK's password grant (for local Dex only):

```bash
export OCMO_SERVER=http://localhost:8080
export OCMO_CLIENT_ID=ocmo-sdk
export OCMO_CLIENT_SECRET=dev-only-ocmo-sdk-secret
export OCMO_OIDC_GRANT_TYPE=password
export OCMO_OIDC_USERNAME=admin@example.com
export OCMO_OIDC_PASSWORD=password

# Verify via CLI
ocmo whoami
```

Or sign in through the web UI at <http://localhost:8080>.

---

## Step 4 — Create a namespace

```bash
# CLI
ocmo create namespace myapp --description "My first namespace"

# REST
curl -X POST http://localhost:8080/api/v1/ns/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "myapp", "description": "My first namespace"}'
```

---

## Step 5 — Push your first config

```bash
cat > app.yaml <<'EOF'
environment: development
database:
  host: db.internal
  port: 5432
  pool_size: 10
EOF

# CLI
ocmo -n myapp create config app/web -f app.yaml

# REST
curl -X POST http://localhost:8080/api/v1/ns/myapp/~config/~create/app/web \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/yaml" \
  --data-binary @app.yaml
```

---

## Step 6 — Resolve it

```bash
# CLI — resolve to JSON and print
ocmo -n myapp resolve app/web --cast json

# CLI — resolve and write to file
ocmo -n myapp resolve app/web --cast json -O ./app.json

# REST — get the signed download URL, then download
RESOLVE=$(curl -s http://localhost:8080/api/v1/ns/myapp/~resolve/app/web?cast=json \
  -H "Authorization: Bearer $TOKEN")
echo $RESOLVE | python3 -m json.tool
URL=$(echo $RESOLVE | python3 -c "import sys,json; print(json.load(sys.stdin)['items'][0]['url'])")
curl "$URL" -o app.json
```

```python
# SDK
from ocmo import OcmoClient

with OcmoClient() as client:
    result = client.ns("myapp").resolve("app/web", cast="json")
    data = result["app/web"].data
    print(data["database"]["host"])
```

---

## What's next?

- [Concepts](../concepts/README.md) — understand the mental model before going further
- [Install the CLI](install-cli.md) — configure multi-context auth for teams
- [Install the SDK](install-sdk.md) — use OCMO from Python applications
- [Configs](../features/configs.md) — what you can do with configs beyond create/resolve
- [Resolving](../features/resolving/README.md) — parameters, extend, render, cast
