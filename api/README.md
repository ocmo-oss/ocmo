# ocmo-api

REST API for the OCMO configuration service. HTTP surface is implemented with
[django-ninja](https://django-ninja.dev/); routes live under `/api/` (application routes under
`/api/v1/`).

**Distribution:** PyPI name `ocmo-api` · **Python:** 3.13+ · **License:** Apache-2.0

---

## Features

- Versioned config, template, secret, and resolver trees per namespace
- Resolve pipeline (extend, render, cast) with artifact download URLs and optional Redis offload
- OIDC JWT validation and resolver-token authentication
- Namespace policies, global permissions, audit log
- OpenAPI / Swagger UI at `/api/docs`

Product behavior is documented in [../docs/](../docs/). This README covers running and developing
the service.

---

## Requirements

- Python **3.13+**
- PostgreSQL **15+** (required)
- Redis **7+** (optional — RQ workers, resolve cache/artifact backends)
- OIDC provider (any; Dex is bundled in the dev Docker stack)

---

## Installation

From this directory:

```bash
uv sync              # runtime + dev dependencies
uv sync --no-dev     # production install (containers use this)
```

The install provides:

- Django project package `ocmoapi`
- Application package `core`
- Console script **`ocmo-api`** (management CLI)

---

## Management CLI

```bash
ocmo-api migrate              # interactive migrations
ocmo-api migrate --noinput    # non-interactive (containers, CI)
ocmo-api serve                # gunicorn WSGI server
```

`serve` options and environment variables:

| Option / variable | Default | Description |
|-------------------|---------|-------------|
| `--bind` / `GUNICORN_BIND` | `0.0.0.0:8000` | Listen address |
| `--workers` / `GUNICORN_WORKERS` | `4` | Worker processes |
| `--timeout` / `GUNICORN_TIMEOUT` | `120` | Worker timeout (seconds) |

Equivalent: `python -m ocmoapi`.

Legacy Django entry point remains available:

```bash
uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000   # development only
```

---

## Configuration

Settings are read from environment variables in `ocmoapi/settings.py`. Copy [`.env.example`](.env.example)
for local development; see [../.env.example](../.env.example) for production Docker Compose.

Common variables:

| Variable | Description |
|----------|-------------|
| `DJANGO_SECRET_KEY` | Django secret (required in production) |
| `DJANGO_DEBUG` | `True` / `False` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated host names |
| `POSTGRES_*` | Database connection (`HOST`, `PORT`, `DB`, `USER`, `PASSWORD`) |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` | Redis when using worker or Redis-backed resolve |
| `OIDC_*` | Discovery, JWKS, issuer, client ID, audiences, Swagger redirect |
| `OCMO_MASTER_KEY` | Base64 master key for secret encryption |
| `OCMO_PUBLIC_URL` | Public gateway URL for absolute download links |
| `OCMO_RESOLVE_ARTIFACT_*` | Artifact storage backend (`fs` / `redis`) and paths |
| `OCMO_RESOLVE_CACHE_BACKEND` | Short-circuit cache (`locmem` / `redis`) |
| `ADMIN_EMAIL` | Bootstrap admin identity hint for dev stacks |

See the dev compose file for a full local example:
[../docker-compose.dev.yml](../docker-compose.dev.yml).

### Production security

Before exposing the API to a network:

- Set unique `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, and `OCMO_MASTER_KEY` (required for secrets).
- Set `DJANGO_DEBUG=False` and restrict `DJANGO_ALLOWED_HOSTS`.
- Use your organization's OIDC provider — do not use the Dex stack from `docker-compose.dev.yml`.
- Set `OCMO_PUBLIC_URL` when running behind a reverse proxy.

See [../SECURITY.md](../SECURITY.md) and [../docs/quickstart/configuration.md](../docs/quickstart/configuration.md).

---

## Local development

### Without Docker

```bash
uv sync
export DJANGO_SETTINGS_MODULE=ocmoapi.settings
# configure POSTGRES_* and OIDC_* to point at your database and IdP
ocmo-api migrate
uv run python manage.py runserver 0.0.0.0:8000
```

### With Docker (recommended)

From the repository root:

```bash
docker compose -f docker-compose.dev.yml -f docker-compose.hmr.yml up --build
```

The API container bind-mounts `./api` and uses `Dockerfile.dev` with Django `runserver`.

### OpenAPI export

```bash
uv run python manage.py dump_openapi --output /tmp/openapi.json
```

Used by the SDK code generation pipeline (`sdk/Makefile`).

---

## Testing

```bash
uv run python manage.py test --keepdb
```

Focused example:

```bash
uv run python manage.py test core.tests.test_system --keepdb -v2
```

### Linting and type checking

```bash
uv run ruff check .
uv run mypy core ocmoapi
```

---

## Docker

| File | Purpose |
|------|---------|
| `Dockerfile` | Production image (`ocmo-api serve`) |
| `Dockerfile.dev` | Dev image with full `uv sync` |
| `docker/entrypoint.prod.sh` | `migrate --noinput` + `exec ocmo-api serve` |

Build production image:

```bash
docker build -f Dockerfile -t ocmo-api:local .
```

---

## Project structure

```text
api/
├── core/           # Models, managers, Ninja routes, schemas, tests
├── ocmoapi/        # Django settings, URLs, WSGI, management CLI
├── manage.py       # Django manage.py (development)
├── pyproject.toml
└── uv.lock
```

Business logic belongs in **managers** (`core/managers/`). Ninja handlers in `core/api/` should stay
thin.

---

## API documentation

When the service is running:

- Swagger UI: `/api/docs`
- Health: `/api/health`
- Version + public OIDC bootstrap: `/api/version`

---

## Related components

- Python SDK: [../sdk/README.md](../sdk/README.md)
- CLI: [../cli/README.md](../cli/README.md)
- Web UI: [../frontend/README.md](../frontend/README.md)
- Monorepo overview: [../README.md](../README.md)
