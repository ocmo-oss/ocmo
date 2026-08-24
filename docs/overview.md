# What is OCMO?

OCMO is a configuration management platform. It stores YAML configs in versioned, hierarchical trees, transforms them through a composable pipeline (merge → render → format), and delivers the results to your services as signed download URLs — with full audit trails, encrypted secrets, and fine-grained access control.

## The problem OCMO solves

Config files scatter across repos, environment variables, Helm values, and wiki pages. By the time a service reads its config, no one knows which version is running, who changed it, or why. Secrets travel as plain text. Rolling back means grepping git history.

OCMO gives every config a home:

- **Versioned** — every write creates an immutable snapshot; any version can be fetched, diffed, or restored at any time.
- **Composable** — configs inherit from shared base configs, rendered through Jinja2 templates, and cast to any output format (YAML, JSON, env vars, HCL, raw text).
- **Secure** — secrets are encrypted at rest with AES-256-GCM; values are never returned without explicit authorization and are never written to artifacts unless the caller has permission.
- **Audited** — every read, write, and resolve is recorded with identity, time, and outcome.
- **Access-controlled** — OIDC-native; no internal user database; two-tier ABAC keeps namespace policies independent.

## How it works

A **config** lives at a path inside a **namespace** (e.g. `apps/api/web` in namespace `prod`). When a service needs its config, it calls the **resolve** endpoint. OCMO:

1. Loads the config and strips the `_ocmo` metadata block.
2. Applies **parameters** (projecting values from the path, accepting dynamic overrides, or decrypting secrets).
3. **Extends** the config by deep-merging referenced base configs.
4. **Renders** any Jinja2 templates with the merged data.
5. **Casts** to the requested output format.
6. Stores the artifact and returns a short-lived signed download URL.

The service downloads the artifact — no credentials needed for the download step.

## Component map

| Component | Install | Role |
|-----------|---------|------|
| **API** (`ocmo-api`) | PyPI / Docker | REST service; source of truth |
| **Web UI** | Docker / static build | Browser tree browser, editor, resolve panel |
| **CLI** (`ocmo-cli`) | PyPI / `uv tool` | `ocmo` command for scripting and local workflows |
| **SDK** (`ocmo-sdk`) | PyPI | Python client library for applications |

```
Browser / CLI / SDK
       │
       ▼
   Gateway (nginx :8080)
   ├── /api/*  → API (:8000)
   │              └── Postgres
   ├── /dex/*  → OIDC provider (Dex)
   └── /*      → Frontend (static SPA)
```

All four surfaces talk to the same REST API. The gateway is optional in production — you can point clients directly at the API.

## When to use each surface

| Task | Surface |
|------|---------|
| Browse and edit configs interactively | Web UI |
| Scripting, CI/CD pipelines | CLI |
| Application startup: pull config at runtime | SDK or CLI |
| Automation against OCMO from Python code | SDK |
| Raw API access, other languages | REST directly |

## Next steps

- [Quick Start](quickstart/README.md) — running the full stack in 10 minutes
- [Concepts](concepts/README.md) — namespaces, trees, versions, and the resolve pipeline
- [Features](features/README.md) — deep dives on each capability
