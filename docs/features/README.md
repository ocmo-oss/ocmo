# Features

Each page describes one OCMO feature: what it is, how it behaves, and how to use it across all four surfaces (REST API, web UI, CLI, SDK).

## Item management

| Feature | Summary |
|---------|---------|
| [Configs](configs.md) | Versioned YAML documents with a resolve pipeline |
| [Templates](templates.md) | Jinja2 sources referenced during config rendering |
| [Secrets](secrets.md) | Encrypted YAML; values injected at resolve time |
| [Resolvers](resolvers.md) | API tokens + config for consumer services |

## Resolve pipeline

| Feature | Summary |
|---------|---------|
| [Resolving overview](resolving/README.md) | Full pipeline: extend → render → parameters → cast → artifact |
| [Parameters](resolving/parameters.md) | `{!name}` placeholders: projected, dynamic, secret |
| [Extend](resolving/extend.md) | Deep-merge other configs into this one |
| [Render](resolving/render.md) | Apply Jinja2 templates to config data |
| [Cast](resolving/cast.md) | Output format: yaml, json, env, hcl, raw |
| [Output naming](resolving/output-naming.md) | Override the artifact filename via `_ocmo.name` |
| [Folder resolve](resolving/folders.md) | Resolve multiple configs in one call |

## Governance

| Feature | Summary |
|---------|---------|
| [Validation](validation.md) | JSON Schema validation on config save |
| [Propagation](propagation.md) | Push config data to downstream targets on tag/manual |
| [Locks](locks.md) | Freeze a path tree against writes |
| [Audit](audit.md) | Immutable event log for all operations |
| [Webhooks](webhooks.md) | HTTP notifications on tree mutations |

## Access control

| Feature | Summary |
|---------|---------|
| [Authentication](authentication.md) | OIDC login, resolver tokens, whoami, can-i |
| [Authorization](authorization.md) | Global permission rules + namespace ABAC policies |
