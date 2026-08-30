# Tutorial: install a Kubernetes application with OCMO

This tutorial starts with an empty OCMO [namespace](../../concepts/namespaces.md) named `tutorial-k8s` and ends with **cert-manager running in a Kubernetes cluster**. You install it from resolved YAML, not with `helm install`.

An OCMO namespace is a **workspace**. It is not a Kubernetes namespace and it is not “one Helm release”. Configs live under `apps/cert-manager/` so you can later add `apps/external-dns/` or `apps/metrics-server/` in the same workspace.

Two namespaces appear in this tutorial. Keep them distinct:


| Name           | Kind                 | Role                                     |
| -------------- | -------------------- | ---------------------------------------- |
| `tutorial-k8s` | OCMO namespace       | Store, versions, access policy, resolve  |
| `cert-manager` | Kubernetes namespace | Where `kubectl apply` puts the workloads |




## The problem

cert-manager issues TLS certificates. Common ways of shipping it each fail a different requirement:


| Approach                        | What goes wrong                                                                                                                                |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `helm install` in every cluster | Chart values, image tags, and HA patches live in different repos and pipeline variables. Nobody can answer “what is actually applied in prod?” |
| GitOps with a rendered dump     | Image bumps rewrite a large Deployment. HA (replicas, PDB, anti-affinity) is mixed with vendor YAML, so chart upgrades become merge conflicts. |
| Helm + extra `--set` in CI      | Secrets, who can change prod, and audit of *resolved* output sit outside the config system.                                                    |


OCMO is the store. Helm is used **once**, as a generator. After that, [extend](../../features/resolving/extend.md) layers environment changes on a frozen vendor snapshot.

## What you will have at the end

- Namespace `tutorial-k8s` with an access policy: humans author configs; CI deploys with a [resolver](../../features/resolvers.md) token.
- Vendor tree: `helm template` output for cert-manager **v1.21.1**. Each vendor config is tagged `chart-v1.21.1`.
- `envs/prod` and `envs/dev`: one `app` config per environment. Each `app` uses [distribute](../../features/resolving/extend.md#mode-distribute) so one resolve emits every Kubernetes object. Small `overrides/` files patch Deployments and ServiceAccounts.
- Dev deployment overrides and dev `app` [propagate](../../features/propagation.md) to prod when you resolve them with `--mark-stable`. You cannot set the reserved tag `stable` with `ocmo tag item`.
- Registry credentials as an OCMO [secret](../../features/secrets.md) at `apps/registry.secret`. Deployment overrides pull images from `myregistry.example.com`, not from upstream `quay.io`.
- Image tags driven by the dynamic [parameter](../../features/resolving/parameters.md) `app_version`. You can bump it in dev and propagate, or pass `--param app_version=v1.21.2` at resolve time.
- A resolver per environment (`envs/dev/deploy`, `envs/prod/deploy`) whose hooks run `kubeconform`, then `kubectl apply`, then rollout wait. The OCMO API does not run `kubectl`; the CLI does, on the machine that holds the token. Each pipeline runs `ocmo resolve app` with its own resolver token.
- Pipelines that resolve `app` (scope-relative), apply, and leave [audit](../../features/audit.md).



## Tree you will build

```
tutorial-k8s/                              # OCMO namespace (workspace)
├── _permissions
├── _webhooks
└── apps/
    ├── registry.secret                    # dockerconfigjson for myregistry.example.com
    └── cert-manager/
        ├── vendor/                        # helm template; tagged chart-v1.21.1; do not kubectl
        │   ├── deployment-cert-manager.yaml
        │   ├── deployment-cert-manager-webhook.yaml
        │   ├── customresourcedefinition-*.yaml
        │   └── …
        ├── envs/
        │   ├── dev/
        │   │   ├── app                    # distribute: all vendor + overrides → ~50 manifests
        │   │   ├── deploy                 # dev resolver (scope: envs/dev/); CI: ocmo resolve app
        │   │   └── overrides/
        │   │       ├── deployment-cert-manager-controller.yaml
        │   │       ├── deployment-cert-manager-webhook.yaml
        │   │       ├── deployment-cert-manager-cainjector.yaml
        │   │       ├── all-service-accounts.patch
        │   │       └── registry-creds
        │   └── prod/
        │       ├── app
        │       ├── deploy                 # prod resolver (scope: envs/prod/); CI: ocmo resolve app
        │       └── overrides/
        │           ├── deployment-cert-manager-controller.yaml
        │           ├── deployment-cert-manager-webhook.yaml
        │           ├── deployment-cert-manager-cainjector.yaml
        │           ├── all-service-accounts.patch
        │           └── registry-creds
```

**One resolve** of `app` (with the prod resolver token) emits every Kubernetes object (CRDs, RBAC, Deployments, Services, PDBs, pull Secret). OIDC users use the full path `apps/cert-manager/envs/prod/app`.

Deployment overrides [extend](../../features/resolving/extend.md) one vendor file each. To change only `image` on the first container, they use **numeric keys** (`containers: 0: {image: …}`). A YAML list in the override would replace the whole list. See [Updating list items by index](../../features/resolving/extend.md#updating-list-items-by-index).

Vendor ServiceAccounts are **not** listed in `app`. `all-service-accounts.patch` [distributes](../../features/resolving/extend.md#mode-distribute) `imagePullSecrets` onto the three vendor ServiceAccount configs instead.

## Prerequisites

- OCMO API reachable. You can sign in as a user who can [create a namespace](../../concepts/namespaces.md#who-can-create-a-namespace) (a [global admin](../../features/authentication.md#global-administrator) is enough).
- [CLI](../../quickstart/install-cli.md) and [SDK](../../quickstart/install-sdk.md) installed. Auth: `ocmo auth login` or the env vars in the CLI install guide.
- Helm 3, `kubectl`, and a cluster. The applying identity needs namespaced access in Kubernetes namespace `cert-manager` plus the cluster-scoped objects the chart emits (CRDs, ClusterRoles, ValidatingWebhookConfiguration).
- [kubectl-slice](https://github.com/patrickdappollonio/kubectl-slice) to split `helm template` output into one file per object (`kubectl krew install slice`).
- Optional: [kubeconform](https://github.com/yannh/kubeconform) on the runner that executes resolver hooks.

```bash
export OCMO_SERVER=https://ocmo.example.com   # or http://localhost:8080 locally
export OCMO_NAMESPACE=tutorial-k8s
```

REST examples use `$TOKEN` (OIDC Bearer). CLI and SDK pick up the same server from config / `OCMO_*`. Resolver tokens (`ocmort-…`) use a different header; see [step 5](05-resolver-and-hooks.md).

## Steps

1. [Create the namespace and access policy](01-namespace-and-access.md)
2. [Render the Helm chart and import it](02-import-helm-chart.md)
3. [Store registry credentials](03-images-and-secrets.md)
4. [Layer dev and prod environments with extend](04-layering.md)
5. [Create the deploy resolvers and hooks](05-resolver-and-hooks.md)
6. [CI/CD: resolve, apply, promote, observe](06-cicd.md)
7. [Clean up and summary](07-cleanup-and-summary.md)

