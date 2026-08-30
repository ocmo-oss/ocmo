# 5. Create the deploy resolvers and hooks

**Why this step:** The deploy job must not use a human OIDC token. A [resolver](../../features/resolvers.md) is a service account. It lives at a tree path. **Its parent path is its scope.**

Create **one resolver per environment**:

| Resolver path | Scope | CI resolves |
|---------------|-------|-------------|
| `apps/cert-manager/envs/dev/deploy` | `apps/cert-manager/envs/dev/` | `app` → `apps/cert-manager/envs/dev/app` |
| `apps/cert-manager/envs/prod/deploy` | `apps/cert-manager/envs/prod/` | `app` → `apps/cert-manager/envs/prod/app` |

Both pipelines run the same command with their own resolver token:

```bash
ocmo -n tutorial-k8s resolve app
```

Paths in resolve requests are **relative to resolver scope**. `app` is not a typo — each resolver’s scope ends at `envs/{dev,prod}/`, so the deploy entry point is always `app`.

A resolver is **not** a config. You create it with `create resolver`, not `create config`.

CI resolves **one config**: `app`. That config uses `mode: distribute` and emits ~50 artifacts. Do **not** resolve `.` (scope root). That would also resolve standalone override files and duplicate work. The path `.` is only valid with a resolver token (OIDC users cannot resolve `.`).

The API only **returns** hook command text. It does not execute `kubectl` on the OCMO server. The CLI runs hooks on the machine that holds `OCMO_TOKEN`, after it has written artifacts to disk.

Resolver tokens cannot write, set tags, or read the audit log.

## Allow resolving out-of-scope paths

Resolving `app` emits `registry-creds` (from [step 4](04-layering.md)). That overlay reads the OCMO secret at `apps/registry.secret` ([step 3](03-images-and-secrets.md)) via a `secret` parameter. Each deploy resolver’s scope is `apps/cert-manager/envs/{dev,prod}/`; the shared registry secret lives at `apps/registry.secret` and vendor configs live at `apps/cert-manager/vendor/`. Implicit in-scope grants do not reach those paths — without explicit Allow rules, resolver resolve fails with `Permission denied`.

Add these policies to `_permissions` (keep the policies from [step 1](01-namespace-and-access.md)):

```yaml
  - id: deployer-registry-secret
    description: Deploy resolvers can reference the shared registry secret outside their scope
    effect: Allow
    actors:
      - kind: Resolver
        path: apps/cert-manager/envs/dev/deploy
      - kind: Resolver
        path: apps/cert-manager/envs/prod/deploy
    actions:
      - secret:resolve
    resources:
      - apps/registry.secret

  - id: deployer-vendor-extend
    description: Deploy resolvers can extend vendor configs outside their env scope
    effect: Allow
    actors:
      - kind: Resolver
        path: apps/cert-manager/envs/dev/deploy
      - kind: Resolver
        path: apps/cert-manager/envs/prod/deploy
    actions:
      - config:resolve
    resources:
      - apps/cert-manager/vendor/**
```

```bash
ocmo -n tutorial-k8s update config _permissions -f _permissions.yaml
```

See [Resolver from outside its scope](../../features/authorization.md#resolver-from-outside-its-scope-for-extend-chains) for the general pattern.

## Resolver configuration

Use the same hook document for both environments (adjust rollout wait only if your dev cluster uses different Deployment names):

```yaml
# apps/cert-manager/envs/{dev,prod}/deploy  (resolver document, not a Config)
cast:
  format: yaml
  options:
    explicit_start: true
    trailing_newline: true
validate_all: "kubeconform -strict -ignore-missing-schemas -summary {!conf}"
post_resolve_all: "kubectl apply --server-side --field-manager=ocmo -f . && kubectl -n cert-manager rollout status deployment/cert-manager --timeout=180s && kubectl -n cert-manager rollout status deployment/cert-manager-webhook --timeout=180s && kubectl -n cert-manager rollout status deployment/cert-manager-cainjector --timeout=180s"
```

| Field | Why |
|-------|-----|
| `cast` | Default [cast](../../features/resolving/cast.md) so CI can omit `--cast yaml`. |
| `validate_all` | One check over every staged file. `{!conf}` is all artifact paths. `-ignore-missing-schemas` covers cert-manager CRDs kubeconform does not ship. |
| `post_resolve_all` | Apply the staging directory (cwd) and wait until all three Deployments roll out. Failure is CLI exit **8**. |

Per-file `validate` / `post_resolve` cannot be set together with the `_all` forms. Multi-output resolve needs `_all`.

Set `OCMO_EXEC_HOOKS=always` (or pass `--exec-hooks`) on the runner, or the CLI only prints hooks and does not run them.

### CLI

Descriptions are not set at create time. Create each resolver, then set the description with `describe`:

```bash
ocmo -n tutorial-k8s create resolver apps/cert-manager/envs/dev/deploy -f deploy-resolver.yaml

ocmo -n tutorial-k8s describe apps/cert-manager/envs/dev/deploy \
  --description "Dev deploy identity. Scope: apps/cert-manager/envs/dev/. Resolves app." \
  --yes

ocmo -n tutorial-k8s create resolver apps/cert-manager/envs/prod/deploy -f deploy-resolver.yaml

ocmo -n tutorial-k8s describe apps/cert-manager/envs/prod/deploy \
  --description "Prod deploy identity. Scope: apps/cert-manager/envs/prod/. Resolves app." \
  --yes
```

The full `ocmort-…` token is printed **once** on create. Store each token in the CI secret store (`OCMO_TOKEN`). Later reads show a masked value.

### REST

```bash
curl -X POST "$OCMO_SERVER/api/v1/ns/tutorial-k8s/~resolver/~create/apps/cert-manager/envs/dev/deploy" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/yaml" \
  --data-binary @deploy-resolver.yaml

curl -X POST "$OCMO_SERVER/api/v1/ns/tutorial-k8s/~resolver/~create/apps/cert-manager/envs/prod/deploy" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/yaml" \
  --data-binary @deploy-resolver.yaml
```

### SDK

```python
for env in ("dev", "prod"):
    path = f"apps/cert-manager/envs/{env}/deploy"
    created = ns.create_resolver(
        path,
        config={
            "cast": {"format": "yaml", "options": {"explicit_start": True, "trailing_newline": True}},
            "validate_all": "kubeconform -strict -ignore-missing-schemas -summary {!conf}",
            "post_resolve_all": (
                "kubectl apply --server-side --field-manager=ocmo -f . && "
                "kubectl -n cert-manager rollout status deployment/cert-manager --timeout=180s && "
                "kubectl -n cert-manager rollout status deployment/cert-manager-webhook --timeout=180s && "
                "kubectl -n cert-manager rollout status deployment/cert-manager-cainjector --timeout=180s"
            ),
        },
    )
    print(env, created)  # store token1 immediately

    ns.describe(
        path,
        description=f"{env} deploy identity. Scope: apps/cert-manager/envs/{env}/. Resolves app.",
    )
```

### Web UI

**+** → Resolver → path `apps/cert-manager/envs/dev/deploy` → paste YAML → Save → copy `token1`.

**+** → Resolver → path `apps/cert-manager/envs/prod/deploy` → paste YAML → Save → copy `token1`.

## Inspect hooks before executing them

Resolver tokens are not OAuth Bearer tokens. REST uses `X-Ocmo-Resolver-Token`. The CLI uses `OCMO_TOKEN`.

Unset OIDC client env vars first; if `OCMO_CLIENT_ID` (or a bearer `OCMO_TOKEN`) is still set, the CLI reports ambiguous authentication.

```bash
unset OCMO_CLIENT_ID OCMO_OIDC_ISSUER
export OCMO_TOKEN=ocmort-…   # prod resolver token
ocmo -n tutorial-k8s resolve app --print-hooks
```

### REST

```bash
curl -s -H "X-Ocmo-Resolver-Token: $OCMO_TOKEN" \
  "$OCMO_SERVER/api/v1/ns/tutorial-k8s/~resolve/app?trace_only=true"
```

### SDK

```python
with OcmoClient(token="ocmort-…") as client:
    result = client.ns("tutorial-k8s").resolve("app", trace_only=True)
    print(result)
```

The SDK downloads artifacts. It does **not** run hooks. Use the CLI on the runner if you want `kubeconform` / `kubectl apply` from resolver config.

## Dry-run resolve to disk (no hooks)

Create the Kubernetes namespace first if it does not exist: `kubectl create namespace cert-manager`.

```bash
unset OCMO_CLIENT_ID OCMO_OIDC_ISSUER
export OCMO_TOKEN=ocmort-…   # prod resolver token
ocmo -n tutorial-k8s resolve app --output-dir /tmp/tutorial-k8s-manifests/
kubeconform -strict -ignore-missing-schemas /tmp/tutorial-k8s-manifests/
```

Apply from a laptop (same as CI):

```bash
ocmo -n tutorial-k8s resolve app \
  --exec-hooks \
  --hook-timeout 300 \
  --output-dir /tmp/tutorial-k8s-manifests/
```

`--trust-hooks <sha256>` is optional in CI — see [resolvers](../../features/resolvers.md).

Next: [CI/CD](06-cicd.md).
