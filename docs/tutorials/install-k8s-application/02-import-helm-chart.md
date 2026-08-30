# 2. Render the Helm chart and import it

**Why this step:** Helm is a generator, not the store. `helm template` (Helm’s CLI — not OCMO [render](../../features/resolving/render.md)) produces Kubernetes objects for a **pinned chart version**. We import that YAML as [configs](../../features/configs.md) so environment configs can [extend](../../features/resolving/extend.md) a frozen vendor snapshot. A chart upgrade is “import again, tag `chart-vX.Y.Z`, diff” — not a merge of Helm output and HA patches.

We use **cert-manager v1.21.1** ([Helm install docs](https://cert-manager.io/docs/installation/helm/)).

## Render locally

Vendor values are chart defaults: **one replica**, PDBs on so prod can use them as-is. HA replica counts, anti-affinity, and **internal registry images** are added in [step 4](04-layering.md). Vendor Deployments keep upstream `quay.io/jetstack/…` image refs until then.

```bash
mkdir -p /tmp/tutorial-k8s-cert-manager && cd /tmp/tutorial-k8s-cert-manager

helm template cert-manager oci://quay.io/jetstack/charts/cert-manager \
  --version v1.21.1 \
  --namespace cert-manager \
  --set crds.enabled=true \
  --set replicaCount=1 \
  --set webhook.replicaCount=1 \
  --set cainjector.replicaCount=1 \
  --set podDisruptionBudget.enabled=true \
  --set webhook.podDisruptionBudget.enabled=true \
  --set cainjector.podDisruptionBudget.enabled=true \
  --set startupapicheck.enabled=false \
  > helm-rendered.yaml
```

`--namespace cert-manager` is the **Kubernetes** namespace written into the manifests. The OCMO namespace stays `tutorial-k8s`. Helm does not create the Kubernetes namespace. Create it before apply (`kubectl create namespace cert-manager`).

## Split into one config per object

Install [kubectl-slice](https://github.com/patrickdappollonio/kubectl-slice) (`kubectl krew install slice`, or the standalone binary). It writes one file per Kubernetes object. The default filename template is `{{.kind | lower}}-{{.metadata.name}}.yaml` — slugs match the Helm object name and end with `.yaml`.

Keep each document exactly as Helm emitted it. `containers` stays a **list**. Environment overrides later patch list items with [numeric keys](../../features/resolving/extend.md#updating-list-items-by-index) (`containers: 0: {image: …}`).

```bash
kubectl-slice -f helm-rendered.yaml -o vendor --skip-non-k8s
# Wrote vendor/deployment-cert-manager.yaml -- …
# Wrote vendor/deployment-cert-manager-webhook.yaml -- …
# Wrote vendor/deployment-cert-manager-cainjector.yaml -- …
# Wrote vendor/poddisruptionbudget-cert-manager.yaml -- …
# Wrote vendor/customresourcedefinition-certificates.cert-manager.io.yaml -- …
# …
# 49 files generated.
```

`--skip-non-k8s` drops documents that are not Kubernetes objects.

You can pipe `helm template` straight into `kubectl-slice` (`… | kubectl-slice -f - -o vendor --skip-non-k8s`) if you do not need `helm-rendered.yaml` on disk.

Confirm a Deployment still has a list:

```bash
grep -E '^      containers:$|name: cert-manager-controller' vendor/deployment-cert-manager.yaml
#       containers:
#         - name: cert-manager-controller
```

## Import into OCMO

The CLI [import](../../how-to/export-import.md) command walks a directory. Parseable YAML/JSON objects become configs. Filenames become the last path segment (the slug). REST has no bulk-import verb; loop as shown below.

### CLI

```bash
ocmo -n tutorial-k8s import ./vendor --to apps/cert-manager/vendor
ocmo -n tutorial-k8s ls apps/cert-manager/vendor -R
```

Use `--update` if you re-run after fixing a split. Without `--update`, a path that already exists fails. After import, `ocmo ls` is the source of truth for slugs.

**Colon → dash in slugs.** `kubectl-slice` filenames follow the Kubernetes object name. cert-manager RBAC resources use `:` in `metadata.name` (for example `cert-manager:leaderelection`), so local files look like `role-cert-manager:leaderelection.yaml`. OCMO path segments cannot contain `:`. On import, each `:` in the filename slug is replaced with `-` (`role-cert-manager-leaderelection.yaml`). The YAML body is unchanged; only the tree slug differs. In [step 4](04-layering.md), every `extend` reference and the `app` config list must use the **imported** slug from `ocmo ls`, not the on-disk `vendor/` basename.

### REST

No bulk-import verb. Loop:

```bash
for f in vendor/*; do
  path="apps/cert-manager/vendor/$(basename "$f")"
  curl -X POST "$OCMO_SERVER/api/v1/ns/tutorial-k8s/~config/~create/${path}" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/yaml" \
    --data-binary @"$f"
done
```

### SDK

```python
from pathlib import Path
from ocmo import OcmoClient

root = Path("vendor")
with OcmoClient() as client:
    ns = client.ns("tutorial-k8s")
    for path in sorted(root.iterdir()):
        rel = f"apps/cert-manager/vendor/{path.name}"
        ns.create_config(rel, content=path.read_text())
        print("created", rel)
```

### Web UI

Use CLI/SDK for CRDs and RBAC dumps. Open `apps/cert-manager/vendor/deployment-cert-manager.yaml` in the UI to confirm `containers` is still a list.

## Tag the vendor snapshot

Each write creates an immutable [version](../../concepts/versions-and-tags.md). Import created version `1`. OCMO also set the reserved tag `latest` (always the newest version; you cannot set `latest` yourself).

Tag **`chart-v1.21.1`** on **every** vendor config. Custom tags must start with a letter. Overrides pin `@chart-v1.21.1` when they extend vendor, so a later re-import does not silently change what prod extends.

Do not use the reserved tag `stable` here. `stable` on configs is only advanced by resolve `--mark-stable` (see [step 4](04-layering.md)).

### CLI

```bash
ocmo -n tutorial-k8s ls apps/cert-manager/vendor -o name | while read -r slug; do
  ocmo -n tutorial-k8s tag item "apps/cert-manager/vendor/$slug" --tag chart-v1.21.1
done
```

Use `ocmo ls` slugs (with `:` → `-`), not local `vendor/*` basenames — a loop over `vendor/*` misses or fails on the ten RBAC files whose names still contain `:`.

### REST

```bash
curl -X POST "$OCMO_SERVER/api/v1/ns/tutorial-k8s/~tag/apps/cert-manager/vendor/deployment-cert-manager.yaml" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tag": "chart-v1.21.1"}'
```

Repeat for each vendor slug (or loop like the CLI example).

### SDK

```python
for path in sorted(root.iterdir()):
    ns.set_tag(f"apps/cert-manager/vendor/{path.name}", tag="chart-v1.21.1")
```

### Web UI

Open each vendor item → **Versions** → tag `chart-v1.21.1`. For ~50 files, use the CLI loop.

## Describe the vendor folder

```bash
ocmo -n tutorial-k8s describe apps/cert-manager/vendor \
  --description "Unmodified helm template for cert-manager v1.21.1. Tagged chart-v1.21.1. Do not kubectl apply; re-import and retag on chart upgrade." \
  --yes
```

Non-interactive shells (CI, scripts) require `--yes` to confirm overwriting an existing folder description.

You will not `kubectl apply` `vendor/`. CI resolves **`app`** with the env-specific deploy resolver ([step 5](05-resolver-and-hooks.md)), which extends these configs.

Next: [registry credentials](03-images-and-secrets.md).
