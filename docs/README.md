# OCMO Documentation

OCMO is a YAML configuration management platform. Configs are stored in versioned trees, resolved through a pipeline (extend → render → cast → artifact), and consumed by services via the REST API, Python SDK, CLI, or web UI.

## Start here

| Goal | Where to go |
|------|-------------|
| Run the full stack locally for the first time | [Quick Start](quickstart/README.md) |
| Understand OCMO concepts (namespaces, trees, tags) | [Concepts](concepts/README.md) |
| Learn about a specific feature | [Features](features/README.md) |
| Accomplish a specific task | [How-to guides](how-to/README.md) |
| Look up an API route, CLI flag, or error code | [Reference](reference/README.md) |

## By audience

**Platform operator / first-time install**
→ [Install the server](quickstart/install-server.md) · [Configuration reference](quickstart/configuration.md)

**Developer integrating OCMO into a service**
→ [Deliver a config to a host](how-to/deliver-config-to-a-host.md) · [SDK reference](reference/sdk.md) · [CI/CD guide](how-to/ci-cd.md)

**Config author (writing and managing configs)**
→ [Configs](features/configs.md) · [Templates](features/templates.md) · [Secrets](features/secrets.md) · [Resolving](features/resolving/README.md)

**Security / access control**
→ [Authentication](features/authentication.md) · [Authorization](features/authorization.md) · [Secrets](features/secrets.md)

**Troubleshooting**
→ [Troubleshoot resolving](how-to/troubleshoot-resolve.md) · [Errors reference](reference/errors.md)

## Product overview

→ [What is OCMO?](overview.md)

## Contents

- [Overview](overview.md)
- [Quick Start](quickstart/README.md)
  - [Install the server](quickstart/install-server.md)
  - [Install the web UI](quickstart/install-web-ui.md)
  - [Install the CLI](quickstart/install-cli.md)
  - [Install the SDK](quickstart/install-sdk.md)
  - [Configuration reference](quickstart/configuration.md)
- [Concepts](concepts/README.md)
  - [Namespaces](concepts/namespaces.md)
  - [Tree and items](concepts/tree-and-items.md)
  - [Versions and tags](concepts/versions-and-tags.md)
  - [The `_ocmo` metadata block](concepts/ocmo-metadata.md)
  - [Identities and access](concepts/identities-and-access.md)
- [Features](features/README.md)
  - [Configs](features/configs.md)
  - [Templates](features/templates.md)
  - [Secrets](features/secrets.md)
  - [Resolvers](features/resolvers.md)
  - [Resolving](features/resolving/README.md)
    - [Parameters](features/resolving/parameters.md)
    - [Extend](features/resolving/extend.md)
    - [Render (templates)](features/resolving/render.md)
    - [Cast (output formats)](features/resolving/cast.md)
    - [Output naming](features/resolving/output-naming.md)
    - [Folder resolve](features/resolving/folders.md)
  - [Validation](features/validation.md)
  - [Propagation](features/propagation.md)
  - [Locks](features/locks.md)
  - [Audit](features/audit.md)
  - [Webhooks](features/webhooks.md)
  - [Authentication](features/authentication.md)
  - [Authorization](features/authorization.md)
- [How-to guides](how-to/README.md)
  - [Deliver a config to a host](how-to/deliver-config-to-a-host.md)
  - [CI/CD integration](how-to/ci-cd.md)
  - [Promote configs across environments](how-to/promote-across-environments.md)
  - [Export and import](how-to/export-import.md)
  - [Troubleshoot resolving](how-to/troubleshoot-resolve.md)
- [Reference](reference/README.md)
  - [REST API](reference/rest-api.md)
  - [CLI](reference/cli.md)
  - [Python SDK](reference/sdk.md)
  - [Permission operations](reference/permissions.md)
  - [Cast formats](reference/cast-formats.md)
  - [Errors](reference/errors.md)
  - [Limits](reference/limits.md)
