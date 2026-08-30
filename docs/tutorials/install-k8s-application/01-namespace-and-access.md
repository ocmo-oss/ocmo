# 1. Create the namespace and access policy

**Why this step:** cert-manager should not sit in a catch-all tree next to unrelated apps. It also should not consume a whole OCMO namespace by itself. A [namespace](../../concepts/namespaces.md) is the isolation boundary: its own encryption key for secrets, its own `_permissions` policy, and no cross-namespace `extend`. We create `tutorial-k8s` as a **platform workspace**. The app is a path prefix (`apps/cert-manager/`).

A new namespace already contains builtin configs (`_permissions`, `_webhooks`, and others). You do not create `_permissions`; you update it.

## Create the namespace

### CLI

```bash
ocmo create namespace tutorial-k8s \
  --description "Kubernetes platform configs (cert-manager, and later other cluster apps)"
```

### REST

```bash
curl -X POST "$OCMO_SERVER/api/v1/ns/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "tutorial-k8s",
    "description": "Kubernetes platform configs (cert-manager, and later other cluster apps)"
  }'
```

### SDK

```python
from ocmo import OcmoClient

with OcmoClient() as client:
    ns = client.create_namespace(
        name="tutorial-k8s",
        description="Kubernetes platform configs (cert-manager, and later other cluster apps)",
    )
    print(ns.name, ns.permissions_tag)
```

### Web UI

1. Open OCMO → **Namespaces**.
2. Click **+**.
3. Name: `tutorial-k8s`. Description: as above.
4. **Create**, then open the namespace.

```bash
ocmo get namespace tutorial-k8s
ocmo whoami
```

A new namespace starts with `policies: []` on `_permissions`. **Default deny** applies to everyone except the [global admin](../../features/authentication.md#global-administrator).

`permissions_tag` on the namespace object selects which version of `_permissions` is enforced (default `latest`).

## Who may do what

| Actor | Job | Must not do |
|-------|------|-------------|
| Platform engineers (OIDC group `platform`) | Import charts, edit `envs/`, manage resolvers, resolve dev configs with `--mark-stable` to [propagate](../../features/propagation.md) to prod | — |
| Image bot (OIDC client `ocmo-image-bot`) | Update `app_version` in **dev** deployment overrides and dev `app`; resolve with `--mark-stable` so prod receives the merge | Touch `vendor/` |
| Deploy pipeline (dev or prod) | [Resolve](../../features/resolving/README.md) `app` with the env-specific resolver token and apply | Write any config ([resolvers cannot write](../../features/resolvers.md#scope-and-access)) |

[Authorization](../../features/authorization.md) has two tiers:

1. **Global permissions** — who can see, create, update, or delete the **namespace object**. This does not grant access to configs inside the tree.
2. **`_permissions`** — who can read, write, resolve, and tag items **in the tree**.

Writing `_permissions` itself requires Global `write` on the namespace (builtin path). The policies inside `_permissions` then apply to ordinary paths such as `apps/cert-manager/`.

If this instance already lets your user list namespaces, skip the global rule. Otherwise the global admin adds:

### CLI

```bash
cat > /tmp/gp-tutorial-k8s.yaml <<'EOF'
id: tutorial-k8s-platform
description: Platform group can see and administer the tutorial-k8s namespace object
namespace: tutorial-k8s
read:
  actors:
    - kind: User
      claims:
        groups: platform
write:
  actors:
    - kind: User
      claims:
        groups: platform
delete:
  actors:
    - kind: User
      claims:
        groups: platform
EOF

ocmo create globalpermission tutorial-k8s-platform -f /tmp/gp-tutorial-k8s.yaml
```

### REST / SDK / Web UI

Same pattern as [global permissions](../../features/authorization.md#global-permissions-tier-1).

## Namespace tree policy

Write `_permissions` now. Deploy resolvers live at `apps/cert-manager/envs/dev/deploy` and `apps/cert-manager/envs/prod/deploy`. **Parent path is scope** (`apps/cert-manager/envs/dev/` and `apps/cert-manager/envs/prod/`). Inside each scope the resolver has implicit `config:resolve` and `secret:resolve`. Vendor configs and the shared registry secret are outside those scopes; explicit Allow rules for both resolvers are added in [step 5](05-resolver-and-hooks.md).

Adjust `groups` / `client_id` to what `ocmo whoami` shows.

`--mark-stable` on resolve requires `config:write` on the config being resolved (not `config:tag`). Propagation then needs `config:write` on each target.

```yaml
# _permissions
policies:
  - id: platform-full
    description: Platform engineers own the tutorial-k8s tree
    effect: Allow
    actors:
      - kind: User
        claims:
          groups: platform
    actions:
      - "*:*"
    resources:
      - "**"

  - id: image-bot-dev-overrides
    description: CI client updates dev deployment overrides, dev app, and resolves with mark-stable to propagate
    effect: Allow
    actors:
      - kind: User
        claims:
          client_id: ocmo-image-bot
    actions:
      - config:read
      - config:write
      - config:resolve
    resources:
      - apps/cert-manager/envs/dev/overrides/deployment-*.yaml
      - apps/cert-manager/envs/dev/app

  - id: image-bot-propagate-prod
    description: Propagation target writes when dev configs are promoted via mark-stable
    effect: Allow
    actors:
      - kind: User
        claims:
          client_id: ocmo-image-bot
    actions:
      - config:write
    resources:
      - apps/cert-manager/envs/prod/overrides/deployment-*.yaml
      - apps/cert-manager/envs/prod/app
```

Do not grant the image bot `config:write` on prod `app` except as a propagation target (the policy above). The bot writes **dev** deployment overrides and dev `app`, then `--mark-stable` pushes a merge into **prod** counterparts only.

### CLI

```bash
ocmo -n tutorial-k8s update config _permissions -f _permissions.yaml
```

### REST

```bash
curl -X PUT "$OCMO_SERVER/api/v1/ns/tutorial-k8s/~config/~update/_permissions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/yaml" \
  --data-binary @_permissions.yaml
```

### SDK

```python
client.ns("tutorial-k8s").update_config(
    "_permissions",
    content=open("_permissions.yaml").read(),
)
```

### Web UI

Configs tree → `_permissions` → paste → **Save**.

## Check access

### CLI

```bash
ocmo can-i config:write --resource apps/cert-manager/vendor/deployment-cert-manager.yaml -n tutorial-k8s
ocmo can-i config:write --resource apps/cert-manager/envs/prod/overrides/deployment-cert-manager-controller.yaml -n tutorial-k8s
```

Next: [import the Helm chart](02-import-helm-chart.md).
