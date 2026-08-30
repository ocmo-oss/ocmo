# 6. CI/CD: resolve, apply, promote, observe

**Why this step:** Humans should not run `--exec-hooks` against production as muscle memory. CI uses an env-specific resolver token to [resolve](../../features/resolving/README.md) **`app`**, run hooks (`kubeconform`, `kubectl apply`), and leave an [audit](../../features/audit.md) trail. A second job (OIDC, not the resolver) updates image tags in **dev** deployment overrides and dev `app`, then resolves them with `--mark-stable` so [propagation](../../features/propagation.md) updates prod. [Webhooks](../../features/webhooks.md) can notify Slack when an override changes.

This follows the generic [CI/CD guide](../../how-to/ci-cd.md), specialized for Kubernetes.

## Two identities in the pipeline

| Job | Auth | Why |
|-----|------|-----|
| `promote-image` | OIDC client `ocmo-image-bot` | Resolver tokens cannot write. This job updates `app_version` in **dev** deployment overrides and dev `app`, then resolves with `--mark-stable` to [propagate](../../features/propagation.md) to prod. |
| `deploy-dev` | `OCMO_TOKEN` (dev resolver) | Read/resolve only. Runs `ocmo resolve app --exec-hooks`. |
| `deploy-prod` | `OCMO_TOKEN` (prod resolver) | Read/resolve only. Runs `ocmo resolve app --exec-hooks --param app_version=…`. |

Never put `ocmo-image-bot` credentials on the deploy runner if that runner also has `kubectl` admin.

`--mark-stable` needs `config:write` on the resolved config. Resolvers cannot write, so they cannot mark `stable`. Use the image-bot (or a human) token for promotion.

Both deploy jobs use the same resolve path (`app`) because each resolver’s scope is its environment folder ([step 5](05-resolver-and-hooks.md)).

## Promote an image (three options)

After your mirror publishes `v1.21.2`:

### Option A — pass tag at resolve (deploy job only)

No OCMO write. The deploy job passes the tag CI already knows. The stored default on the override files and `app` does not change.

```bash
export OCMO_TOKEN=ocmort-…   # prod resolver token
ocmo -n tutorial-k8s resolve app \
  --param app_version=v1.21.2 \
  --exec-hooks \
  --hook-timeout 300 \
  --output-dir ./manifests/
```

REST: `GET .../~resolve/app?cast=yaml&param_app_version=v1.21.2` with `X-Ocmo-Resolver-Token` (prod resolver).

SDK: `ns.resolve("app", cast="yaml", params={"app_version": "v1.21.2"})` with a prod-scoped resolver client — then apply yourself; SDK does not run hooks.

### Option B — dev override + propagation (recommended)

Update the default in **dev** deployment overrides and dev `app`, then resolve with `--mark-stable` so propagation merges into prod ([step 4](04-layering.md)). You cannot set `stable` with `ocmo tag item`. Only `--mark-stable` on a successful resolve advances it, and that is what fires `trigger: tag` / `tag: stable` on the propagation block.

```bash
# OIDC env: OCMO_SERVER, OCMO_CLIENT_ID=ocmo-image-bot, …
for f in deployment-cert-manager-controller.yaml deployment-cert-manager-webhook.yaml deployment-cert-manager-cainjector.yaml; do
  ocmo -n tutorial-k8s get item "apps/cert-manager/envs/dev/overrides/$f" -o raw > "/tmp/$f"
  # edit app_version default to v1.21.2 in each file, then:
  ocmo -n tutorial-k8s update config "apps/cert-manager/envs/dev/overrides/$f" -f "/tmp/$f"
  ocmo -n tutorial-k8s resolve "apps/cert-manager/envs/dev/overrides/$f" --mark-stable
done

ocmo -n tutorial-k8s get item apps/cert-manager/envs/dev/app -o raw > /tmp/app.yaml
# edit app_version default to v1.21.2, then:
ocmo -n tutorial-k8s update config apps/cert-manager/envs/dev/app -f /tmp/app.yaml
ocmo -n tutorial-k8s resolve apps/cert-manager/envs/dev/app --mark-stable
```

Diff stored configs before the deploy job runs:

```bash
ocmo -n tutorial-k8s diff apps/cert-manager/envs/dev/overrides/deployment-cert-manager-controller.yaml \
  apps/cert-manager/envs/prod/overrides/deployment-cert-manager-controller.yaml
ocmo -n tutorial-k8s diff apps/cert-manager/envs/dev/app apps/cert-manager/envs/prod/app
```

Then run the deploy job **without** `--param app_version` if you want the stored prod default to win, or pass `--param` anyway to override at apply time.

### Option C — image bot updates prod overrides directly

Skip propagation when you need an emergency prod-only change. The image bot already has `config:write` on prod deployment overrides and prod `app` (propagation target permission).

```bash
# OIDC env: OCMO_SERVER, OCMO_CLIENT_ID=ocmo-image-bot, …
for f in deployment-cert-manager-controller.yaml deployment-cert-manager-webhook.yaml deployment-cert-manager-cainjector.yaml; do
  ocmo -n tutorial-k8s get item "apps/cert-manager/envs/prod/overrides/$f" -o raw > "/tmp/$f"
  # edit app_version default to v1.21.2 in each file, then:
  ocmo -n tutorial-k8s update config "apps/cert-manager/envs/prod/overrides/$f" -f "/tmp/$f"
done

ocmo -n tutorial-k8s get item apps/cert-manager/envs/prod/app -o raw > /tmp/app.yaml
# edit app_version default to v1.21.2, then:
ocmo -n tutorial-k8s update config apps/cert-manager/envs/prod/app -f /tmp/app.yaml
```

Tag the prod override with a **custom** tag if you gate on a release name. Do not use `stable` here — that tag is reserved:

```bash
ocmo -n tutorial-k8s tag item apps/cert-manager/envs/prod/overrides/deployment-cert-manager-controller.yaml --tag release-2026-08-29
```

## Deploy job (resolver)

Create Kubernetes namespace `cert-manager` once if it does not exist. Each resolver token must be on a runner that can reach both OCMO and the target cluster.

### GitHub Actions (prod)

```yaml
# .github/workflows/deploy-tutorial-k8s-cert-manager.yml
name: deploy-cert-manager
on:
  workflow_dispatch:
    inputs:
      app_version:
        description: cert-manager image tag
        default: v1.21.1

jobs:
  deploy:
    runs-on: [self-hosted, kubectl]
    environment: production
    env:
      OCMO_SERVER: ${{ vars.OCMO_SERVER }}
      OCMO_NAMESPACE: tutorial-k8s
      OCMO_TOKEN: ${{ secrets.OCMO_TUTORIAL_K8S_CERT_MANAGER_PROD_RESOLVER }}
      OCMO_EXEC_HOOKS: always
      KUBECONFIG: ${{ secrets.KUBECONFIG_PATH }}
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install ocmo-cli
      - name: Resolve, validate, apply
        run: |
          ocmo -n tutorial-k8s resolve app \
            --param app_version=${{ inputs.app_version }} \
            --exec-hooks \
            --hook-timeout 300 \
            --output-dir "${{ runner.temp }}/manifests/"
```

Use `OCMO_TUTORIAL_K8S_CERT_MANAGER_DEV_RESOLVER` and a dev `KUBECONFIG` for a dev deploy workflow — same `ocmo resolve app` command.

## Resolve and apply (what the deploy step does)

```bash
export OCMO_TOKEN=ocmort-…   # prod resolver token
ocmo -n tutorial-k8s resolve app \
  --param app_version=v1.21.1 \
  --exec-hooks \
  --hook-timeout 300 \
  --output-dir ./manifests/
```

Without hooks (same commands the resolver would run):

```bash
ocmo -n tutorial-k8s resolve app --param app_version=v1.21.1 --output-dir ./manifests/
kubeconform -strict -ignore-missing-schemas ./manifests
kubectl apply --server-side --field-manager=ocmo -f ./manifests/
kubectl -n cert-manager rollout status deployment/cert-manager --timeout=180s
kubectl -n cert-manager rollout status deployment/cert-manager-webhook --timeout=180s
kubectl -n cert-manager rollout status deployment/cert-manager-cainjector --timeout=180s
```

## Mark `app` stable after a good apply

Resolvers cannot set tags. After hooks exit 0, use a **user** (or image-bot) token that has `config:write` on `envs/prod/app`. Resolve with `--mark-stable`. That is the only way to advance the reserved `stable` tag on configs:

```bash
ocmo -n tutorial-k8s resolve apps/cert-manager/envs/prod/app --mark-stable
```

Once you adopt that gate, pin later deploys with `--version stable` when using the prod resolver:

```bash
export OCMO_TOKEN=ocmort-…   # prod resolver token
ocmo -n tutorial-k8s resolve app --version stable --exec-hooks
```

Note: marking prod `app` stable records the applied prod version. Dev→prod promotion of `app_version` still happens via propagation on **dev** `app` and dev deployment overrides when you resolve them with `--mark-stable`.

## Webhook: Slack when a deployment override changes

`_webhooks` is a builtin config. Updating it requires Global `write` on the namespace. Secret values are never included in webhook payloads.

```yaml
webhooks:
  - id: slack-cert-manager-deployments
    enabled: true
    url: https://hooks.slack.com/services/T000/B000/XXX
    events:
      - config.updated
    filter:
      paths:
        - apps/cert-manager/envs/**/overrides/deployment-*.yaml
    payload:
      preset: slack
```

See [Webhooks](../../features/webhooks.md) for HMAC signing (`_webhooks_secret`).

## Audit after deploy

Resolver tokens cannot read the audit log. Use a user token:

```bash
ocmo -n tutorial-k8s get audit --limit 20
ocmo -n tutorial-k8s get audit --object-id apps/cert-manager/envs/prod/app --limit 50
```

Use `--object-id` to filter by tree path (the audit field name for the config or resolver involved). Recent resolve events show `operation: Resolve` and `auth_type: resolver` when the deploy job used a resolver token.

## GitLab CI

```yaml
deploy-prod:
  script:
    - ocmo -n tutorial-k8s resolve app
        --param app_version=$APP_VERSION
        --exec-hooks --hook-timeout 300 --output-dir ./manifests/
  variables:
    OCMO_TOKEN: $OCMO_TUTORIAL_K8S_CERT_MANAGER_PROD_RESOLVER
    OCMO_EXEC_HOOKS: "always"
    APP_VERSION: v1.21.1
```

Next: [cleanup and summary](07-cleanup-and-summary.md).
