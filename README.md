# OCMO

<p align="center">
  <img src="img/logo-large.png" alt="OCMO logo" width="100">
</p>

> **Note:** A proper brand logo is wanted — the image above is a placeholder.

> **OCMO** stands for **O**pen **C**onfiguration **M**anager **O**CMO.

OCMO is a configuration management platform for structured YAML data: versioned config trees,
Jinja2 template rendering, policy-based access control, and integration surfaces for applications,
operators, and automation.

Use it to store hierarchical configuration, resolve configs into deployable artifacts (JSON, env
files, HCL, custom templates), manage secrets alongside configs, and audit every change.

**License:** [Apache License 2.0](LICENSE) (see also [NOTICE](NOTICE) and component `LICENSE` files).

<details>
  <summary>Motivation</summary>
  
  What do your TFvars, .env files, Helm chart values.yaml, Dockerfiles, Nginx server configurations, Kubernetes manifests, docker-compose.yaml, and similar files have in common? They are all configuration files that require proper handling (versioning, audit, access management, propagation, resolving, and validation). Yet they are often treated differently, and there is no single solution that lets you achieve this for free.

  OCMO is designed to cover these gaps and provide a single platform to manage all your configuration files.
  It is free and built so it can be easily integrated into any workflow.

  Made by DevOps engineers for all kinds of IT professionals who face such requirements daily.

</details>


---

## What OCMO provides

| Capability | Summary |
|------------|---------|
| **Namespacing** | Separate your configuration files per project, team, department, or whatever you need |
| **Config tree structure** | Store configuration in path-oriented tree storage with automatic versioning, tags, and an easy-to-understand folder structure |
| **Versioning and tags** | Automatic creation of immutable versions on update, with the ability to set automatic and manual tags for better discovery |
| **Resolving** | Merge, extend, and render templates; cast outputs to the exact format you need; parameters and secret injection |
| **Secrets** | Keep secrets for your configuration files securely and inject them where they are needed during resolving |
| **Auth & policy** | Manage users via OIDC (no separate user database) and define flexible permissions on specific elements using ABAC/RBAC |
| **Resolvers** | Special built-in service accounts that grant resolve access to specific configs in one click |
| **Integrations** | REST API, Python SDK, CLI, webhooks, Git sync export |
| **Web UI** | SPA for operators and managers with better observability; full API coverage for day-to-day tasks |

Deep feature documentation: [docs/](docs/).

Read the main [concepts](docs/concepts/README.md) before you start.

---

## Repository layout

| Path | Component | Description |
|------|-----------|-------------|
| [api/](api/) | [**API**](https://hub.docker.com/r/ocmooss/ocmo-api) (`ocmo-api`) | Django + django-ninja REST service |
| [sdk/](sdk/) | [**SDK**](https://pypi.org/project/ocmo-sdk/) (`ocmo-sdk`) | Python client library (`import ocmo`) |
| [cli/](cli/) | [**CLI**](https://pypi.org/project/ocmo-cli/) (`ocmo-cli`) | `ocmo` command-line tool |
| [frontend/](frontend/) | [**Web UI**](https://hub.docker.com/r/ocmooss/ocmo-frontend) | React + Vite SPA served via nginx or Vite dev server |
| [docker/](docker/) | [**Gateway**](https://hub.docker.com/r/ocmooss/ocmo-gateway) | nginx gateway image (API proxy, static UI, artifact offload) preconfigured to properly handle requests to OCMO components |
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

---

## FAQ

**Q:** **Is it production ready?**
**A:** Not yet. The product is still in the stabilization phase, and its API may change. More real-world usage feedback and a security audit are also needed. It is expected to be production-ready at version 1.0.0. For now, you can use it in development environments if you do not mind that some features and API endpoints may change between releases.

**Q:** **Can I store secrets and other sensitive information in the system? (SSL private keys, passwords, tokens, etc.)**
**A:** Yes. The system lets you create special Secret items that can be referenced in configs. This provides a baseline level of security: all secrets are stored encrypted with AES-256-GCM. They are decrypted and injected into configurations during resolving and are never cached. Each namespace has its own encryption key, which is also encrypted with a global (per-instance) key defined in the `OCMO_MASTER_KEY` variable that must be set during API setup. That said, storing credentials in configuration systems is generally not recommended (although some software leaves no alternative). For cases that need a higher level of security, consider using [HashiCorp Vault](https://www.hashicorp.com/en/products/vault).

**Q:** **How do I back up or dump all my configs?**
**A:** The easiest way is the OCMO CLI command `ocmo export`.

**Q:** **Can I store a large amount of data in the system?**
**A:** No. OCMO is not designed for that. The API uses per-instance limits on how large configs, templates, secrets, and other items can be. It is intended only for configuration files, which are usually less than a couple of MB.

**Q:** **Can I store my application's source code in the system?**
**A:** No. Use Git for that.

**Q:** **Where is it designed to be used?**
**A:** In CI/CD (e.g. `ocmo resolve path/to/config` returns the build configuration you need); in your application (e.g. the OCMO SDK can fetch configuration at startup); on a server (e.g. resolve hundreds of Nginx configs from a single YAML config and template); in Kubernetes (e.g. run the OCMO CLI as an init container to resolve and bootstrap configuration as environment variables); and many more cases. Ocmo designed to be not a end-to-end solution, but be the framework that can easily integrate in any flow you need.

**Q:** **How is it better than solution X?**
**A:** See [Comparison with other products](docs/comparison_with_other_products.md).

**Q:** **Does OCMO have any AI-based features?**
**A:** No. They may be added in the future if a compelling use case is identified.

**Q:** **What are the future plans for solution development?**
**A:** A lot of things:
  * Make it production ready: security review, more tests, more real user feedback, improved docs
  * Implement automatic Git sync of configs to a repository per namespace for backup and integration
  * Implement an async worker for tasks such as webhook delivery, Git sync, and similar background work
  * Implement change requests: config approval flows and the ability to extend or fix configuration for people who do not have direct write access
  * Extend config propagation to automatically set a tag on the target config after successful propagation, including cascade propagation
  * Implement post-resolve schema validation to verify that a config resolved correctly before casting it to the target syntax
  * Implement the ability to enable or disable specific resolvers
  * Implement white labeling
  * Implement config collections to group sets of configs under common versioning
  * Implement email notifications for configuration changes
  * Implement API rate limiting
  * Expose monitoring metrics via the API
  * Implement tag history (for easier rollback)
  * Ensure the OCMO API scales well for HA setups
  * Implement a dependency graph to visualize which configs depend on others
  * Implement an OCMO CLI monitor feature to continuously watch specific config files on the filesystem and remediate direct changes
  * Better installation options. Installer, Helm chart, etc
  * Better integrations: Terraform/Pulumi providers
  * Make cast formats extendable as plugins
  * Bug fixes and minor improvements


**Q:** **How many people currently work on this project?**
**A:** For now, only one DevOps engineer with more than 10 years of experience. Contributions and collaborators are welcome.