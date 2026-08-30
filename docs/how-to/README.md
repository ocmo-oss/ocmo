# How-to Guides

Goal-oriented recipes. Each guide solves one concrete task end-to-end.

| Guide | When to use it |
|-------|---------------|
| [Deliver a config to a host](deliver-config-to-a-host.md) | Set up a service to pull its config on start-up or on a schedule |
| [CI/CD integration](ci-cd.md) | Use OCMO in pipelines: write configs, validate, promote to stable |
| [Promote configs across environments](promote-across-environments.md) | Diff, tag, and mark-stable across dev → staging → production |
| [Export and import](export-import.md) | Backup a namespace to disk; bulk-load configs from a directory |
| [Troubleshoot resolving](troubleshoot-resolve.md) | Diagnose why a resolve fails or returns unexpected output |

Longer, ordered scenarios (Helm chart to `kubectl apply`, …) live under [Tutorials](../tutorials/README.md).
