# OCMO

<p align="center">
  <img src="img/logo-large.png" alt="OCMO logo" width="200">
</p>

> **Note:** A proper brand logo is wanted — the image above is a placeholder.

OCMO is a configuration management platform for structured YAML data: versioned config trees,
Jinja2 template rendering, policy-based access control, and integration surfaces for applications,
operators, and automation.

Use it to store hierarchical configuration, resolve configs into deployable artifacts (JSON, env
files, HCL, custom templates), manage secrets alongside configs, and audit every change.

**License:** [Apache License 2.0](LICENSE) (see also [NOTICE](NOTICE) and component `LICENSE` files).

---

## What OCMO provides

| Capability | Summary |
|------------|---------|
| **Config trees** | Namespaced, path-oriented storage with automatic versioning, tags, and folder structure |
| **Resolving** | Merge, extend, and render templates; cast outputs; parameters and secret injection |
| **Secrets** | Encrypted tree items integrated with resolve parameters and namespace settings |
| **Auth & policy** | OIDC users, resolver tokens, namespace ABAC/RBAC, global permissions |
| **Integrations** | REST API, Python SDK, CLI, webhooks, Git sync export |
| **Web UI** | SPA for operators (OIDC); full API coverage for day-to-day tasks |

Deep feature documentation: [docs/](docs/).

---

## Repository layout

| Path | Component | Description |
|------|-----------|-------------|
| [api/](api/) | **API** (`ocmo-api`) | Django + django-ninja REST service |
| [sdk/](sdk/) | **SDK** (`ocmo-sdk`) | Python client library (`import ocmo`) |
| [cli/](cli/) | **CLI** (`ocmo-cli`) | `ocmo` command-line tool |
| [frontend/](frontend/) | **Web UI** | React + Vite SPA served via nginx or Vite dev server |
| [docker/](docker/) | **Gateway** | nginx gateway image (API proxy, static UI, artifact offload) |
| [smoke/](smoke/) | **Smoke tests** | HTTP golden tests against a running API |
| [docs/](docs/) | **Documentation** | Product and feature specifications (not runtime code) |

Python packages are managed with **[uv](https://docs.astral.sh/uv/)** (`pyproject.toml` + lockfiles).
The frontend uses **pnpm**.

---

## Architecture (local stack)

```text
Browser ──► gateway (:8080) ──► frontend (static or Vite :3000)
                │
                ├── /api/* ──► api (:8000) ──► PostgreSQL
                └── /dex/* ──► Dex OIDC (dev only)
```

Production deployments run the application containers (`api`, `frontend`, `gateway`) separately
from Postgres, Redis, and your IdP. See [docker-compose.yml](docker-compose.yml) and
[docker-compose.dev.yml](docker-compose.dev.yml). Copy [`.env.example`](.env.example) for production
variables.

---

## Quick start (local development)

**Prerequisites:** Docker, Docker Compose.

Full stack with Postgres, Dex, API, frontend (HMR), and gateway:

```bash
docker compose -f docker-compose.dev.yml -f docker-compose.hmr.yml up --build
```

Open [http://localhost:8080](http://localhost:8080). API health:
[http://localhost:8080/api/health](http://localhost:8080/api/health). Interactive OpenAPI:
[http://localhost:8080/api/docs](http://localhost:8080/api/docs).

Without Vite HMR (static frontend build):

```bash
docker compose -f docker-compose.dev.yml up --build
```

> **Security:** The dev compose stack uses known default credentials and a bundled Dex IdP. Use only
> on trusted local machines. See [SECURITY.md](SECURITY.md) before any production deployment.

---

## Component guides

| Component | README | Install / run (summary) |
|-----------|--------|-------------------------|
| API | [api/README.md](api/README.md) | `cd api && uv sync` · `ocmo-api serve` |
| SDK | [sdk/README.md](sdk/README.md) | `pip install ocmo-sdk` · `from ocmo import OcmoClient` |
| CLI | [cli/README.md](cli/README.md) | `pipx install ocmo-cli` · `ocmo auth login` |
| Frontend | [frontend/README.md](frontend/README.md) | `cd frontend && pnpm install && pnpm dev` |
| Smoke tests | [smoke/README.md](smoke/README.md) | `cd smoke && uv sync && uv run pytest -v` |

---

## Development

| Component | Setup | Test / lint |
|-----------|-------|-------------|
| API | `cd api && uv sync` | `uv run python manage.py test --keepdb` |
| SDK | `uv sync --package ocmo-sdk` | `cd sdk && make test` |
| CLI | `uv sync --package ocmo-cli` | `uv run --package ocmo-cli pytest cli/tests` |
| Frontend | `cd frontend && pnpm install` | `pnpm test && pnpm lint` |
| Smoke | `cd smoke && uv sync` | `uv run pytest -v` (API must be running) |

Full details: [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Documentation index

| Document | Contents |
|----------|----------|
| [docs/README.md](docs/README.md) | Documentation hub and navigation by audience |
| [docs/overview.md](docs/overview.md) | Product overview |
| [docs/features/README.md](docs/features/README.md) | Feature guides (configs, resolving, secrets, auth, …) |
| [docs/concepts/identities-and-access.md](docs/concepts/identities-and-access.md) | Namespaces, OIDC, policies, resolver tokens |
| [docs/features/configs.md](docs/features/configs.md) | Config tree, versioning, templates |
| [docs/features/resolving/README.md](docs/features/resolving/README.md) | Resolve pipeline |
| [docs/how-to/README.md](docs/how-to/README.md) | Integration and operational how-to guides |
| [docs/quickstart/install-web-ui.md](docs/quickstart/install-web-ui.md) | Web UI setup and coverage |
| [docs/quickstart/configuration.md](docs/quickstart/configuration.md) | Environment variable reference |

---

## Versioning

All application components share the same version number. Backward compatibility and API stability
are not guaranteed until version `1.0.0`. See [CHANGELOG.md](CHANGELOG.md).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security issues: [SECURITY.md](SECURITY.md). Community
standards: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
