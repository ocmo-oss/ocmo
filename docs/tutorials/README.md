# Tutorials

End-to-end scenarios that take you from an empty [namespace](../concepts/namespaces.md) to configs running in a real environment. Each tutorial uses OCMO features to solve a concrete problem — not to demonstrate the feature in isolation.

How-to guides remain the short recipes ([CI/CD](../how-to/ci-cd.md), [deliver to a host](../how-to/deliver-config-to-a-host.md), …). Tutorials are longer, ordered walks.

## Conventions

Every mutating step is shown on all four surfaces where it makes sense:

| Surface | When to use it |
|---------|----------------|
| **CLI** (`ocmo`) | Day-to-day authoring, scripts, CI |
| **REST** | Other languages, glue, gateways |
| **Python SDK** | Services and Python automation |
| **Web UI** | Interactive browse, review, resolve preview |

Commands assume you already [installed the CLI](../quickstart/install-cli.md) and [SDK](../quickstart/install-sdk.md), and that `OCMO_SERVER` (and auth) are configured. REST examples use `https://ocmo.example.com` and `$TOKEN` (an OIDC Bearer token). Point those at your instance.

First mention of each OCMO feature links to its feature or concept page.

## Tutorials

| Tutorial | What you build |
|----------|----------------|
| [Install a Kubernetes application](install-k8s-application/README.md) | Import cert-manager as tagged vendor YAML, layer prod/dev with extend, promote with `--mark-stable`, resolve `app` from CI, `kubectl apply` |
