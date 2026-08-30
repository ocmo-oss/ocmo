# 7. Clean up and summary

## What you should see in the cluster

```bash
kubectl -n cert-manager get deploy,pdb,svc,sa
kubectl -n cert-manager get deploy cert-manager -o jsonpath='{.spec.replicas}{"\n"}{.spec.template.spec.containers[0].image}{"\n"}'
kubectl -n cert-manager get deploy cert-manager-webhook -o jsonpath='{.spec.replicas}{"\n"}'
kubectl -n cert-manager get deploy cert-manager-cainjector -o jsonpath='{.spec.replicas}{"\n"}'
```

Expect **2 / 3 / 2** replicas (controller, webhook, cainjector), images `myregistry.example.com/cert-manager-*:v1.21.1` (or whatever you passed as `app_version`), and vendor PDBs. Every object should carry `app.kubernetes.io/env=prod` and `app.kubernetes.io/managed-by=ocmo` from the `app` distribute patch.

ServiceAccounts should list `imagePullSecrets: [{name: registry-creds}]`.

## Revert OCMO and the cluster

### 1. Cluster objects

Cluster-scoped objects (CRDs, ClusterRoles, webhook configurations) are **not** deleted by deleting Kubernetes namespace `cert-manager` alone. Delete them explicitly, or delete the applied files:

```bash
kubectl delete -f ./manifests/ --wait=false
# or:
kubectl delete namespace cert-manager
kubectl delete clusterrole,clusterrolebinding,mutatingwebhookconfiguration,validatingwebhookconfiguration,customresourcedefinition \
  -l app.kubernetes.io/instance=cert-manager
```

### 2. Disable webhooks (optional)

```bash
ocmo -n tutorial-k8s update config _webhooks -f webhooks.yaml   # enabled: false
```

Updating `_webhooks` requires Global `write` on the namespace.

### 3. Delete the OCMO namespace — only if nothing else lives there

This deletes the workspace, including secrets, the resolver, and its tokens. You cannot recover encrypted secrets after the namespace (and its DEK) is gone.

```bash
ocmo delete namespace tutorial-k8s --dry-run
ocmo delete namespace tutorial-k8s -y
```

If you created the optional [global permission](01-namespace-and-access.md#global-permission-for-the-namespace-object) in step 1, remove it too:

```bash
ocmo delete globalpermission tutorial-k8s-platform -y
```

### 4. Keep the namespace, delete only cert-manager

`delete item` supports `--preview`; `delete namespace` uses `--dry-run` (see section 3). Builtin configs (`_permissions`, `_webhooks`) cannot be deleted.

```bash
ocmo -n tutorial-k8s delete item apps/cert-manager --preview
ocmo -n tutorial-k8s delete item apps/cert-manager -y
ocmo -n tutorial-k8s delete item apps/registry.secret -y
```

### 5. Local working files

The tutorial writes temporary files outside OCMO. Remove them when you are done:

```bash
rm -rf /tmp/tutorial-k8s-cert-manager /tmp/tutorial-k8s-manifests
rm -f /tmp/gp-tutorial-k8s.yaml
rm -f /tmp/deployment-cert-manager-*.yaml /tmp/all-service-accounts.patch.yaml /tmp/registry-creds.yaml
```

If you saved a resolver token to disk for testing, delete that file as well. Revoke access by deleting the resolver (section 4) or the whole namespace (section 3).

---

## Summary

| What we did | Problem it solved |
|-------------|-------------------|
| Namespace `tutorial-k8s` + `_permissions` | Workspace for multiple cluster apps; platform vs image-bot vs deploy resolver |
| `helm template` + import + tag **`chart-v1.21.1` on every vendor file** | Helm is a generator; overlays pin a chart snapshot |
| `envs/{prod,dev}/app` with `distribute` | One resolve emits the full manifest set (~50 files) |
| Deployment overrides with `containers: 0:` numeric keys | Patch image/resources without rewriting the whole Pod spec |
| `all-service-accounts.patch` extends vendor SAs | `imagePullSecrets` without duplicating ServiceAccount YAML |
| `_ocmo.propagation` on dev deployment overrides and dev `app` | Promote image/config changes to prod when dev is resolved with `--mark-stable` |
| `app_version` dynamic parameter | CI bumps tags in dev, propagates to prod, or passes `--param` at resolve |
| `apps/registry.secret` + `registry-creds` overlay | Pull credentials for `myregistry.example.com`, rendered as a Kubernetes Secret |
| Resolvers at `envs/dev/deploy` and `envs/prod/deploy` | Each env’s CI runs `ocmo resolve app`; CLI hooks validate and apply |

Related: [Resolving](../../features/resolving/README.md) · [Extend](../../features/resolving/extend.md) · [Propagation](../../features/propagation.md) · [Deliver a config to a host](../../how-to/deliver-config-to-a-host.md) · [Troubleshoot resolving](../../how-to/troubleshoot-resolve.md)
