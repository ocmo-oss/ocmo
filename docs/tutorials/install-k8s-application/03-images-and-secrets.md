# 3. Store registry credentials

**Why this step:** Vendor YAML from `helm template` still points at `quay.io/jetstack/…`. In this tutorial, cluster nodes pull mirrored images from an internal registry (`myregistry.example.com`). Nodes need a dockerconfigjson. Store it as an OCMO [secret](../../features/secrets.md). The deploy overlay later injects it with a [secret parameter](../../features/resolving/parameters.md) and `b64_encode`.

Secrets are encrypted at rest (AES-256-GCM, per-namespace key). A get without `--reveal` returns metadata only. Secrets are **not** resolved as artifacts. They appear in Kubernetes YAML only when a config parameter references them.

Mirror the cert-manager images into your registry **before** deploy. Use names that match the Deployment overrides in [step 4](04-layering.md):

| Upstream (vendor) | Mirrored image |
|-------------------|----------------|
| `quay.io/jetstack/cert-manager-controller:v1.21.1` | `myregistry.example.com/cert-manager-controller:v1.21.1` |
| `quay.io/jetstack/cert-manager-webhook:v1.21.1` | `myregistry.example.com/cert-manager-webhook:v1.21.1` |
| `quay.io/jetstack/cert-manager-cainjector:v1.21.1` | `myregistry.example.com/cert-manager-cainjector:v1.21.1` |
| `quay.io/jetstack/cert-manager-acmesolver:v1.21.1` | `myregistry.example.com/cert-manager-acmesolver:v1.21.1` |

Image **tags** are not a separate config tree. Each Deployment override declares a dynamic `app_version` parameter (default `v1.21.1`) and builds the image as `myregistry.example.com/{!app_name}-<component>:{!app_version}`. `app_name` is a [projected](../../features/resolving/parameters.md#projected) parameter from the path (`apps/cert-manager/…` → `cert-manager`). CI can pass a newer tag at resolve time (`--param app_version=v1.21.2`) or the image bot can update the default in the override files ([step 6](06-cicd.md)).

Placeholders must be quoted YAML strings: `"{!app_version}"`, not `{!app_version}`.

## Registry secret

The secret body is ordinary YAML. The value of `dockerconfigjson` is a JSON string (one line). Replace the password.

```yaml
# apps/registry.secret
dockerconfigjson: '{"auths":{"myregistry.example.com":{"username":"robot$cert-manager","password":"replace-me"}}}'
```

### CLI

```bash
ocmo -n tutorial-k8s create secret apps/registry.secret -f registry.secret.yaml
```

Reads without `--reveal` return metadata only.

### REST

```bash
curl -X POST "$OCMO_SERVER/api/v1/ns/tutorial-k8s/~secret/~create/apps/registry.secret" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/yaml" \
  --data-binary @registry.secret.yaml
```

### SDK

```python
ns.create_secret("apps/registry.secret", content=open("registry.secret.yaml").read())
```

### Web UI

**+** → Secret → `apps/registry.secret` → paste → Save.

The Kubernetes `Secret` object is **not** this OCMO secret. It is emitted later by `envs/{prod,dev}/overrides/registry-creds` at resolve time (see [step 4](04-layering.md)). Each environment needs its own `registry-creds` config when using the shared `app` body. ServiceAccounts get `imagePullSecrets` from `all-service-accounts.patch` in the same `overrides/` folder, which [extends](../../features/resolving/extend.md) the three vendor ServiceAccount configs.

Next: [prod and dev environments](04-layering.md).
