# 4. Layer dev and prod environments with extend

**Why this step:** Chart defaults (`replicaCount: 1`, stock `quay.io` images) are not how you run cert-manager in production. Those defaults stay in `vendor/` (tagged `chart-v1.21.1`). Environment intent lives under `envs/{dev,prod}/`.

Three pieces work together:

1. `overrides/` — small configs that [extend](../../features/resolving/extend.md) one vendor manifest each (Deployments, ServiceAccounts).
2. `app` — one config with `mode: distribute`. It lists every vendor slug plus the override configs. The shared `metadata.labels` patch is merged into **each** output. One resolve → ~50 Kubernetes files.
3. `_ocmo.propagation` **on dev overrides** — when you resolve a dev config with `[--mark-stable](../../features/resolving/README.md#mark-stable)`, OCMO advances the reserved `stable` tag and [pushes](../../features/propagation.md) a merge into the matching prod config. Prod keeps HA fields that dev does not define (`replicas`, `affinity`, `resources`).

The `_ocmo` block is stripped from the artifact. It never appears in the YAML you apply.

Kubernetes `containers` is a **list**. [Extend](../../features/resolving/extend.md#deep-merge-behaviour) **replaces** a whole list if you assign a new YAML list. To change only `image` on `containers[0]`, use **numeric-key dict syntax** ([Updating list items by index](../../features/resolving/extend.md#updating-list-items-by-index)): `containers: 0: {image: …}` deep-merges into that item and keeps `args`, `name`, and probes.

## Creation order

1. **Dev** — create dev overrides and `envs/dev/app` first (no propagation blocks yet).
2. **Prod** — create prod overrides and `envs/prod/app`. Prod configs are propagation targets; they must exist before step 3.
3. **Propagation** — update dev deployment overrides and dev `app` to add `_ocmo.propagation` pointing at the prod paths.

`registry-creds` and `all-service-accounts.patch` are identical in dev and prod in this tutorial. In real life scenarion it often might reference different registires. Copy them from dev to prod with `ocmo copy item`; they do not need propagation.

Extend references are checked at save time: vendor files from [step 2](02-import-helm-chart.md) must already be imported.

## Layout

| Path                                             | Role                                                                                                                  |
| ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `envs/dev/overrides/deployment-*.yaml`           | Lighter overrides; [propagate](../../features/propagation.md) to prod when resolved with `--mark-stable` (step 3)     |
| `envs/dev/overrides/all-service-accounts.patch`  | [Distribute](../../features/resolving/extend.md#mode-distribute) `imagePullSecrets` onto three vendor ServiceAccounts |
| `envs/dev/overrides/registry-creds`              | Kubernetes pull Secret (reads `apps/registry.secret`)                                                                 |
| `envs/dev/app`                                   | Lists every vendor + override; `distribute` adds env labels to all outputs                                            |
| `envs/prod/overrides/deployment-*.yaml`          | Extend one vendor Deployment; HA, images, resources                                                                   |
| `envs/prod/overrides/all-service-accounts.patch` | Same distribute patch as dev (copy with `ocmo copy item`)                                                            |
| `envs/prod/overrides/registry-creds`             | Same pull Secret overlay as dev (copy with `ocmo copy item`)                                                          |
| `envs/prod/app`                                  | Same `app` body as dev; `env` comes from the path (`prod`)                                                            |

## Dev environment

Create dev first. Each override extends the vendor Deployment at `@chart-v1.21.1` (the tag from [step 2](02-import-helm-chart.md)). Dynamic `app_version` is the image tag. Projected `app_name` comes from the path (`cert-manager`). Images use the internal registry: `myregistry.example.com/{!app_name}-<component>:{!app_version}`.

Every entry under `_ocmo.parameters` must include a `description` string (API validation rejects saves without it).

### Dev: controller Deployment override

```yaml
# apps/cert-manager/envs/dev/overrides/deployment-cert-manager-controller.yaml
_ocmo:
  extend:
    configs:
      - ../../../vendor/deployment-cert-manager.yaml@chart-v1.21.1
  parameters:
    app_name:
      type: projected
      value: ".Path[1]"
      description: Application name (cert-manager)
      transformers:
        - lower
    app_version:
      type: dynamic
      value: v1.21.1
      description: Image tag for all cert-manager images
      transformers:
        - lower

spec:
  template:
    metadata:
      labels:
        app.kubernetes.io/version: "{!app_version}"
        helm.sh/chart: "{!omit}"
        app.kubernetes.io/managed-by: ocmo
    spec:
      containers:
        0:
          image: "myregistry.example.com/{!app_name}-controller:{!app_version}"
          args:
            3: "{!omit}"
            99: "--acme-http01-solver-image=myregistry.example.com/{!app_name}-acmesolver:{!app_version}"
            100: "--v=4"
```

What the numeric keys do:

- `containers: 0:` patches only the first container.
- `args: 3: "{!omit}"` **removes** the chart’s default ACME solver flag at index 3. `{!omit}` is reserved; you cannot declare a parameter named `omit`.
- `args: 99:` and `100:` **append** (index ≥ list length → append).
- `{!omit}` on `helm.sh/chart` **deletes** that label from pod metadata.

### Dev: webhook Deployment override

```yaml
# apps/cert-manager/envs/dev/overrides/deployment-cert-manager-webhook.yaml
_ocmo:
  extend:
    configs:
      - ../../../vendor/deployment-cert-manager-webhook.yaml@chart-v1.21.1
  parameters:
    app_name:
      type: projected
      value: ".Path[1]"
      description: Application name (cert-manager)
      transformers:
        - lower
    app_version:
      type: dynamic
      value: v1.21.1
      description: Image tag for all cert-manager images
      transformers:
        - lower

spec:
  template:
    metadata:
      labels:
        app.kubernetes.io/version: "{!app_version}"
        helm.sh/chart: "{!omit}"
        app.kubernetes.io/managed-by: ocmo
    spec:
      containers:
        0:
          image: "myregistry.example.com/{!app_name}-webhook:{!app_version}"
```

### Dev: cainjector Deployment override

```yaml
# apps/cert-manager/envs/dev/overrides/deployment-cert-manager-cainjector.yaml
_ocmo:
  extend:
    configs:
      - ../../../vendor/deployment-cert-manager-cainjector.yaml@chart-v1.21.1
  parameters:
    app_name:
      type: projected
      value: ".Path[1]"
      description: Application name (cert-manager)
      transformers:
        - lower
    app_version:
      type: dynamic
      value: v1.21.1
      description: Image tag for all cert-manager images
      transformers:
        - lower

spec:
  template:
    metadata:
      labels:
        app.kubernetes.io/version: "{!app_version}"
        helm.sh/chart: "{!omit}"
        app.kubernetes.io/managed-by: ocmo
    spec:
      containers:
        0:
          image: "myregistry.example.com/{!app_name}-cainjector:{!app_version}"
```

Draft-resolve checks a file **before** you save it. It does not create a version. `--trace-only` returns the dependency map without writing artifacts.

```bash
ocmo -n tutorial-k8s resolve draft apps/cert-manager/envs/dev/overrides/deployment-cert-manager-controller.yaml \
  -f deployment-cert-manager-controller.yaml --trace-only -o json
```

### Dev: ServiceAccounts (extend vendor, do not recreate)

Vendor ServiceAccounts are **not** listed in `app`. This patch [distributes](../../features/resolving/extend.md#mode-distribute) the same `imagePullSecrets` fragment onto each vendor ServiceAccount. One resolve of this config emits **three** outputs (one per listed vendor file).

```yaml
# apps/cert-manager/envs/dev/overrides/all-service-accounts.patch
_ocmo:
  name: serviceaccount-cert-manager.yaml
  extend:
    mode: distribute
    configs:
      - ../../../vendor/serviceaccount-cert-manager.yaml@chart-v1.21.1
      - ../../../vendor/serviceaccount-cert-manager-webhook.yaml@chart-v1.21.1
      - ../../../vendor/serviceaccount-cert-manager-cainjector.yaml@chart-v1.21.1
  cast:
    format: yaml
    options:
      explicit_start: true

imagePullSecrets:
  - name: registry-creds
```

For [distribute](../../features/resolving/output-naming.md#multi-output-naming), each output is named from the **source** vendor slug (`serviceaccount-cert-manager.yaml`, and so on). `_ocmo.name` on this generating config does not rename those outputs.

### Dev: registry pull Secret

This config is ordinary Kubernetes YAML plus a secret parameter. `apps/registry.secret@latest:dockerconfigjson` means: secret path, tag `latest`, field `dockerconfigjson`. `b64_encode` is required because Kubernetes Secret `data` values are base64. Resolving this config needs `secret:resolve` on `apps/registry.secret`. Each deploy resolver needs an explicit `_permissions` grant for that path ([step 5](05-resolver-and-hooks.md#allow-resolving-out-of-scope-paths)).

```yaml
# apps/cert-manager/envs/dev/overrides/registry-creds
_ocmo:
  name: registry-creds.yaml
  parameters:
    registry_creds:
      type: secret
      value: apps/registry.secret@latest:dockerconfigjson
      description: Credentials to internal registry
      transformers:
        - b64_encode

apiVersion: v1
kind: Secret
metadata:
  name: registry-creds
  namespace: cert-manager
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: "{!registry_creds}"
```

### Dev: `app` — one config, every manifest

`app` is the deploy entry point. It lists every vendor config **except**:

- the three ServiceAccounts (the patch emits those)
- the three vendor Deployments (the override files replace them)

`mode: distribute` with no `by` uses the whole document (minus `_ocmo`) as the patch. Here that is `metadata.labels`. Each listed config gets those labels merged in. You get **one output per list entry**. Nested distribute (the ServiceAccount patch) expands in place, so you still get one file per ServiceAccount.

After [importing the chart](02-import-helm-chart.md), confirm slugs with `ocmo -n tutorial-k8s ls apps/cert-manager/vendor -o name`. Imported slugs use `-` where `kubectl-slice` used `:` (see [step 2](02-import-helm-chart.md#import-into-ocmo)). If your split matches step 2, use this file as-is:

```yaml
# apps/cert-manager/envs/dev/app
_ocmo:
  parameters:
    app_version:
      type: dynamic
      value: v1.21.1
      description: Version of application
      transformers:
        - lower
    env:
      type: projected
      value: ".Path[-2]"
      description: Target environment (prod / dev)
  extend:
    mode: distribute
    configs:
      - ../../vendor/clusterrolebinding-cert-manager-cainjector.yaml@chart-v1.21.1
      - ../../vendor/clusterrolebinding-cert-manager-controller-approve-cert-manager-io.yaml@chart-v1.21.1
      - ../../vendor/clusterrolebinding-cert-manager-controller-certificatesigningrequests.yaml@chart-v1.21.1
      - ../../vendor/clusterrolebinding-cert-manager-controller-certificates.yaml@chart-v1.21.1
      - ../../vendor/clusterrolebinding-cert-manager-controller-challenges.yaml@chart-v1.21.1
      - ../../vendor/clusterrolebinding-cert-manager-controller-clusterissuers.yaml@chart-v1.21.1
      - ../../vendor/clusterrolebinding-cert-manager-controller-ingress-shim.yaml@chart-v1.21.1
      - ../../vendor/clusterrolebinding-cert-manager-controller-issuers.yaml@chart-v1.21.1
      - ../../vendor/clusterrolebinding-cert-manager-controller-orders.yaml@chart-v1.21.1
      - ../../vendor/clusterrolebinding-cert-manager-webhook-subjectaccessreviews.yaml@chart-v1.21.1
      - ../../vendor/clusterrole-cert-manager-cainjector.yaml@chart-v1.21.1
      - ../../vendor/clusterrole-cert-manager-cluster-view.yaml@chart-v1.21.1
      - ../../vendor/clusterrole-cert-manager-controller-approve-cert-manager-io.yaml@chart-v1.21.1
      - ../../vendor/clusterrole-cert-manager-controller-certificatesigningrequests.yaml@chart-v1.21.1
      - ../../vendor/clusterrole-cert-manager-controller-certificates.yaml@chart-v1.21.1
      - ../../vendor/clusterrole-cert-manager-controller-challenges.yaml@chart-v1.21.1
      - ../../vendor/clusterrole-cert-manager-controller-clusterissuers.yaml@chart-v1.21.1
      - ../../vendor/clusterrole-cert-manager-controller-ingress-shim.yaml@chart-v1.21.1
      - ../../vendor/clusterrole-cert-manager-controller-issuers.yaml@chart-v1.21.1
      - ../../vendor/clusterrole-cert-manager-controller-orders.yaml@chart-v1.21.1
      - ../../vendor/clusterrole-cert-manager-edit.yaml@chart-v1.21.1
      - ../../vendor/clusterrole-cert-manager-view.yaml@chart-v1.21.1
      - ../../vendor/clusterrole-cert-manager-webhook-subjectaccessreviews.yaml@chart-v1.21.1
      - ../../vendor/customresourcedefinition-certificaterequests.cert-manager.io.yaml@chart-v1.21.1
      - ../../vendor/customresourcedefinition-certificates.cert-manager.io.yaml@chart-v1.21.1
      - ../../vendor/customresourcedefinition-challenges.acme.cert-manager.io.yaml@chart-v1.21.1
      - ../../vendor/customresourcedefinition-clusterissuers.cert-manager.io.yaml@chart-v1.21.1
      - ../../vendor/customresourcedefinition-issuers.cert-manager.io.yaml@chart-v1.21.1
      - ../../vendor/customresourcedefinition-orders.acme.cert-manager.io.yaml@chart-v1.21.1
      - ../../vendor/rolebinding-cert-manager-cainjector-leaderelection.yaml@chart-v1.21.1
      - ../../vendor/rolebinding-cert-manager-leaderelection.yaml@chart-v1.21.1
      - ../../vendor/rolebinding-cert-manager-webhook-dynamic-serving.yaml@chart-v1.21.1
      - ../../vendor/role-cert-manager-cainjector-leaderelection.yaml@chart-v1.21.1
      - ../../vendor/role-cert-manager-leaderelection.yaml@chart-v1.21.1
      - ../../vendor/role-cert-manager-webhook-dynamic-serving.yaml@chart-v1.21.1
      - ../../vendor/service-cert-manager-cainjector.yaml@chart-v1.21.1
      - ../../vendor/service-cert-manager-webhook.yaml@chart-v1.21.1
      - ../../vendor/service-cert-manager.yaml@chart-v1.21.1
      - ./overrides/deployment-cert-manager-cainjector.yaml
      - ./overrides/deployment-cert-manager-webhook.yaml
      - ./overrides/deployment-cert-manager-controller.yaml
      - ../../vendor/mutatingwebhookconfiguration-cert-manager-webhook.yaml@chart-v1.21.1
      - ../../vendor/poddisruptionbudget-cert-manager-cainjector.yaml@chart-v1.21.1
      - ../../vendor/poddisruptionbudget-cert-manager-webhook.yaml@chart-v1.21.1
      - ../../vendor/poddisruptionbudget-cert-manager.yaml@chart-v1.21.1
      - ./overrides/registry-creds
      - ./overrides/all-service-accounts.patch
      - ../../vendor/validatingwebhookconfiguration-cert-manager-webhook.yaml@chart-v1.21.1

metadata:
  labels:
    app.kubernetes.io/managed-by: ocmo
    app.kubernetes.io/version: "{!app_version}"
    app.kubernetes.io/env: "{!env}"
    helm.sh/chart: "{!omit}"
```

`.Path[-2]` for `apps/cert-manager/envs/dev/app` is `dev`. The same file stored at `envs/prod/app` yields `prod`.

Create the override configs **before** `app` (save-time reference checks):

```bash
ocmo -n tutorial-k8s create config apps/cert-manager/envs/dev/overrides/deployment-cert-manager-controller.yaml -f deployment-cert-manager-controller.yaml
ocmo -n tutorial-k8s create config apps/cert-manager/envs/dev/overrides/deployment-cert-manager-webhook.yaml -f deployment-cert-manager-webhook.yaml
ocmo -n tutorial-k8s create config apps/cert-manager/envs/dev/overrides/deployment-cert-manager-cainjector.yaml -f deployment-cert-manager-cainjector.yaml
ocmo -n tutorial-k8s create config apps/cert-manager/envs/dev/overrides/all-service-accounts.patch -f all-service-accounts.patch.yaml
ocmo -n tutorial-k8s create config apps/cert-manager/envs/dev/overrides/registry-creds -f registry-creds.yaml
ocmo -n tutorial-k8s create config apps/cert-manager/envs/dev/app -f envs/dev/app.yaml
```

## Prod environment

Prod deployment overrides add HA (`replicas`, anti-affinity, resource limits) on top of the same registry images and `app_version` parameter. Create prod **after** dev so propagation targets exist when you add `_ocmo.propagation` in the next section.

### Prod: controller Deployment override

```yaml
# apps/cert-manager/envs/prod/overrides/deployment-cert-manager-controller.yaml
_ocmo:
  extend:
    configs:
      - ../../../vendor/deployment-cert-manager.yaml@chart-v1.21.1
  parameters:
    app_name:
      type: projected
      value: ".Path[1]"
      description: Application name (cert-manager)
      transformers:
        - lower
    app_version:
      type: dynamic
      value: v1.21.1
      description: Image tag for all cert-manager images
      transformers:
        - lower

spec:
  replicas: 2
  template:
    metadata:
      labels:
        app.kubernetes.io/version: "{!app_version}"
        helm.sh/chart: "{!omit}"
        app.kubernetes.io/managed-by: ocmo
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                topologyKey: kubernetes.io/hostname
                labelSelector:
                  matchLabels:
                    app.kubernetes.io/name: cert-manager
                    app.kubernetes.io/instance: cert-manager
                    app.kubernetes.io/component: controller
      containers:
        0:
          image: "myregistry.example.com/{!app_name}-controller:{!app_version}"
          args:
            3: "{!omit}"
            99: "--acme-http01-solver-image=myregistry.example.com/{!app_name}-acmesolver:{!app_version}"
          resources:
            requests:
              cpu: 50m
              memory: 128Mi
            limits:
              memory: 512Mi
```

### Prod: webhook Deployment override

```yaml
# apps/cert-manager/envs/prod/overrides/deployment-cert-manager-webhook.yaml
_ocmo:
  extend:
    configs:
      - ../../../vendor/deployment-cert-manager-webhook.yaml@chart-v1.21.1
  parameters:
    app_name:
      type: projected
      value: ".Path[1]"
      description: Application name (cert-manager)
      transformers:
        - lower
    app_version:
      type: dynamic
      value: v1.21.1
      description: Image tag for all cert-manager images
      transformers:
        - lower

spec:
  replicas: 3
  template:
    metadata:
      labels:
        app.kubernetes.io/version: "{!app_version}"
        helm.sh/chart: "{!omit}"
        app.kubernetes.io/managed-by: ocmo
    spec:
      containers:
        0:
          image: "myregistry.example.com/{!app_name}-webhook:{!app_version}"
```

### Prod: cainjector Deployment override

```yaml
# apps/cert-manager/envs/prod/overrides/deployment-cert-manager-cainjector.yaml
_ocmo:
  extend:
    configs:
      - ../../../vendor/deployment-cert-manager-cainjector.yaml@chart-v1.21.1
  parameters:
    app_name:
      type: projected
      value: ".Path[1]"
      description: Application name (cert-manager)
      transformers:
        - lower
    app_version:
      type: dynamic
      value: v1.21.1
      description: Image tag for all cert-manager images
      transformers:
        - lower

spec:
  replicas: 2
  template:
    metadata:
      labels:
        app.kubernetes.io/version: "{!app_version}"
        helm.sh/chart: "{!omit}"
        app.kubernetes.io/managed-by: ocmo
    spec:
      containers:
        0:
          image: "myregistry.example.com/{!app_name}-cainjector:{!app_version}"
```

### Prod: registry pull Secret and ServiceAccount patch

Copy the dev configs (identical content when both environments use the same cluster and registry):

```bash
ocmo -n tutorial-k8s copy item apps/cert-manager/envs/dev/overrides/registry-creds \
  apps/cert-manager/envs/prod/overrides/ --yes
ocmo -n tutorial-k8s copy item apps/cert-manager/envs/dev/overrides/all-service-accounts.patch \
  apps/cert-manager/envs/prod/overrides/ --yes
```

A trailing `/` on the target path places the source under that folder and keeps its leaf name (`registry-creds`, `all-service-accounts.patch`). Non-interactive shells (CI, scripts) require `--yes` to confirm each copy.

### Prod: `app`

Use the same body as dev. `env` is projected from the path, so `envs/prod/app` yields `app.kubernetes.io/env: prod`.

```bash
ocmo -n tutorial-k8s create config apps/cert-manager/envs/prod/overrides/deployment-cert-manager-controller.yaml -f deployment-cert-manager-controller.yaml
ocmo -n tutorial-k8s create config apps/cert-manager/envs/prod/overrides/deployment-cert-manager-webhook.yaml -f deployment-cert-manager-webhook.yaml
ocmo -n tutorial-k8s create config apps/cert-manager/envs/prod/overrides/deployment-cert-manager-cainjector.yaml -f deployment-cert-manager-cainjector.yaml
ocmo -n tutorial-k8s create config apps/cert-manager/envs/prod/app -f envs/dev/app.yaml
```

## Configure propagation

After prod configs exist, update each dev config that should promote to prod. Add [propagation](../../features/propagation.md) with `trigger: tag` and `tag: stable`. A successful resolve with `--mark-stable` then updates the prod counterpart.

`stable` is a [reserved tag](../../concepts/versions-and-tags.md#reserved-tags). You cannot run `ocmo tag item … --tag stable`. That call returns `ReservedTagsCantBeSet`. Only a successful resolve with `--mark-stable` advances `stable` (and then fires tag-triggered propagation). `--trace-only` skips promotion.

Use `mode: whole` on deployment overrides so `_ocmo.parameters.app_version` (the image tag default) is copied with the body. Prod-only `spec` keys (`replicas`, `affinity`, `resources`) live only in prod. Deep-merge **keeps** them when the source omits them. `exclude` strips fields from the **source** before the merge, so prod keeps its own values.

### Dev: controller Deployment override (with propagation)

```yaml
# apps/cert-manager/envs/dev/overrides/deployment-cert-manager-controller.yaml
_ocmo:
  extend:
    configs:
      - ../../../vendor/deployment-cert-manager.yaml@chart-v1.21.1
  parameters:
    app_name:
      type: projected
      value: ".Path[1]"
      description: Application name taken from config path
      transformers:
        - lower
    app_version:
      type: dynamic
      value: v1.21.1
      description: Image tag for all cert-manager images
      transformers:
        - lower
  propagation:
    enabled: true
    trigger: tag
    tag: stable
    mode: whole
    targets:
      - apps/cert-manager/envs/prod/overrides/deployment-cert-manager-controller.yaml
    exclude:
      - spec.template.spec.containers.0.args

spec:
  template:
    metadata:
      labels:
        app.kubernetes.io/version: "{!app_version}"
        helm.sh/chart: "{!omit}"
        app.kubernetes.io/managed-by: ocmo
    spec:
      containers:
        0:
          image: "myregistry.example.com/{!app_name}-controller:{!app_version}"
          args:
            3: "{!omit}"
            99: "--acme-http01-solver-image=myregistry.example.com/{!app_name}-acmesolver:{!app_version}"
            100: "--v=4"
```

Here `exclude` drops the whole `args` mapping from the source. Prod keeps its own `args` (solver image, no `--v=4`). The image still propagates.

### Dev: webhook Deployment override (with propagation)

```yaml
# apps/cert-manager/envs/dev/overrides/deployment-cert-manager-webhook.yaml
_ocmo:
  extend:
    configs:
      - ../../../vendor/deployment-cert-manager-webhook.yaml@chart-v1.21.1
  parameters:
    app_name:
      type: projected
      value: ".Path[1]"
      description: Application name (cert-manager)
      transformers:
        - lower
    app_version:
      type: dynamic
      value: v1.21.1
      description: Image tag for all cert-manager images
      transformers:
        - lower
  propagation:
    enabled: true
    trigger: tag
    tag: stable
    mode: whole
    targets:
      - apps/cert-manager/envs/prod/overrides/deployment-cert-manager-webhook.yaml

spec:
  template:
    metadata:
      labels:
        app.kubernetes.io/version: "{!app_version}"
        helm.sh/chart: "{!omit}"
        app.kubernetes.io/managed-by: ocmo
    spec:
      containers:
        0:
          image: "myregistry.example.com/{!app_name}-webhook:{!app_version}"
```

### Dev: cainjector Deployment override (with propagation)

```yaml
# apps/cert-manager/envs/dev/overrides/deployment-cert-manager-cainjector.yaml
_ocmo:
  extend:
    configs:
      - ../../../vendor/deployment-cert-manager-cainjector.yaml@chart-v1.21.1
  parameters:
    app_name:
      type: projected
      value: ".Path[1]"
      description: Application name (cert-manager)
      transformers:
        - lower
    app_version:
      type: dynamic
      value: v1.21.1
      description: Image tag for all cert-manager images
      transformers:
        - lower
  propagation:
    enabled: true
    trigger: tag
    tag: stable
    mode: whole
    targets:
      - apps/cert-manager/envs/prod/overrides/deployment-cert-manager-cainjector.yaml

spec:
  template:
    metadata:
      labels:
        app.kubernetes.io/version: "{!app_version}"
        helm.sh/chart: "{!omit}"
        app.kubernetes.io/managed-by: ocmo
    spec:
      containers:
        0:
          image: "myregistry.example.com/{!app_name}-cainjector:{!app_version}"
```

### Dev: `app` (with propagation)

Propagate the `app_version` default (used in `metadata.labels`) to prod. `env` stays per-environment because it is a projected parameter resolved from the path at read time.

Take the full `envs/dev/app` YAML from the [Dev: `app`](#dev-app--one-config-every-manifest) section above and add this block under `_ocmo` (after `parameters`, before `extend`):

```yaml
  propagation:
    enabled: true
    trigger: tag
    tag: stable
    mode: whole
    targets:
      - apps/cert-manager/envs/prod/app
```

Update all four dev configs:

```bash
ocmo -n tutorial-k8s update config apps/cert-manager/envs/dev/overrides/deployment-cert-manager-controller.yaml -f deployment-cert-manager-controller.yaml
ocmo -n tutorial-k8s update config apps/cert-manager/envs/dev/overrides/deployment-cert-manager-webhook.yaml -f deployment-cert-manager-webhook.yaml
ocmo -n tutorial-k8s update config apps/cert-manager/envs/dev/overrides/deployment-cert-manager-cainjector.yaml -f deployment-cert-manager-cainjector.yaml
ocmo -n tutorial-k8s update config apps/cert-manager/envs/dev/app -f envs/dev/app.yaml
```

`registry-creds` and `all-service-accounts.patch` do not need propagation — copy them to prod when you create prod, as shown above.

## Promote dev → prod

After QA on the dev cluster, resolve dev configs with `--mark-stable`. That requires `config:write` on the source (for promotion) and `config:write` on each target ([step 1](01-namespace-and-access.md)). Do not pass `--trace-only`.

```bash
# diff stored configs before promoting
ocmo -n tutorial-k8s diff apps/cert-manager/envs/dev/overrides/deployment-cert-manager-controller.yaml \
  apps/cert-manager/envs/prod/overrides/deployment-cert-manager-controller.yaml
ocmo -n tutorial-k8s diff apps/cert-manager/envs/dev/app apps/cert-manager/envs/prod/app

# resolve dev deployment overrides and app: advances stable and propagates to prod
ocmo -n tutorial-k8s resolve apps/cert-manager/envs/dev/overrides/deployment-cert-manager-controller.yaml --mark-stable
ocmo -n tutorial-k8s resolve apps/cert-manager/envs/dev/overrides/deployment-cert-manager-webhook.yaml --mark-stable
ocmo -n tutorial-k8s resolve apps/cert-manager/envs/dev/overrides/deployment-cert-manager-cainjector.yaml --mark-stable
ocmo -n tutorial-k8s resolve apps/cert-manager/envs/dev/app --mark-stable

# or resolve the whole overrides folder (skips configs without propagation, such as registry-creds):
ocmo -n tutorial-k8s resolve apps/cert-manager/envs/dev/overrides --mark-stable
ocmo -n tutorial-k8s resolve apps/cert-manager/envs/dev/app --mark-stable
```

Deployment overrides and `app` use `trigger: tag` / `tag: stable`, so propagation runs when you resolve with `--mark-stable` above. Manual `ocmo propagate config …` is only for sources with `trigger: manual` ([propagation](../../features/propagation.md#trigger-manual)).

REST:

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "$OCMO_SERVER/api/v1/ns/tutorial-k8s/~resolve/apps/cert-manager/envs/dev/app?mark-stable=true"
```

After propagation, prod still has `replicas: 2`, anti-affinity, and resource limits on the controller. It picks up the new `app_version` default and any shared image changes from dev.

## Preview prod output

Resolve the **single** `app` config (multi-output). Do **not** resolve the `overrides/` folder for deploy — that would emit standalone override files as extra artifacts.

### CLI

```bash
ocmo -n tutorial-k8s resolve apps/cert-manager/envs/prod/app --trace-only -o json
ocmo -n tutorial-k8s resolve apps/cert-manager/envs/prod/app --cast yaml --output-dir /tmp/tutorial-k8s-manifests/
ls /tmp/tutorial-k8s-manifests/ | wc -l    # expect ~50
```

`envs/prod/app` is a multi-output [distribute](../../features/resolving/extend.md#mode-distribute) resolve (~50 files). Use `--output-dir` to write one file per artifact; `-O` / `--output-file` is only for single-item resolves.

### REST

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "$OCMO_SERVER/api/v1/ns/tutorial-k8s/~resolve/apps/cert-manager/envs/prod/app?cast=yaml"
```

The JSON response lists items with signed download URLs. Fetch each `url` for the YAML. CLI and SDK do that for you.

### SDK

```python
result = ns.resolve("apps/cert-manager/envs/prod/app", cast="yaml")
result.save_all("/tmp/tutorial-k8s-manifests/")
```

### Web UI

Open `apps/cert-manager/envs/prod/app` → **Resolve** → download items.

Next: [resolver and kubectl hooks](05-resolver-and-hooks.md).
