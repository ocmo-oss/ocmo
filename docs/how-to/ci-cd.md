# CI/CD Integration

How to use OCMO in CI/CD pipelines for promoting configs, validating changes, and triggering downstream deployments.

---

## Authenticating in CI

For pipelines, use OIDC client credentials (preferred) or a resolver token:

```yaml
# GitHub Actions — OIDC client credentials
env:
  OCMO_SERVER: ${{ vars.OCMO_SERVER }}
  OCMO_CLIENT_ID: ${{ vars.OCMO_CLIENT_ID }}
  OCMO_CLIENT_SECRET: ${{ secrets.OCMO_CLIENT_SECRET }}
  OCMO_NAMESPACE: prod
```

```yaml
# GitHub Actions — resolver token (read-only, simpler)
env:
  OCMO_SERVER: ${{ vars.OCMO_SERVER }}
  OCMO_TOKEN: ${{ secrets.OCMO_RESOLVER_TOKEN }}
  OCMO_NAMESPACE: prod
```

---

## Common CI tasks

### Validate config (draft resolve before merge)

Before merging a config change, verify the new version resolves without errors:

```yaml
# GitHub Actions
- name: Validate config
  run: |
    ocmo -n prod resolve draft app/web -f config.yaml --cast json --trace-only
```

Or use the SDK in a Python test:

```python
import os
from pathlib import Path
from ocmo import OcmoClient

def test_config_resolves():
    with OcmoClient() as client:
        result = client.ns("prod").resolve_draft_config(
            "app/web",
            content=Path("config.yaml").read_text(),
            cast="json",
            trace_only=True,
        )
        assert result.trace_only
```

### Push updated config

```yaml
- name: Update config
  run: |
    ocmo -n prod update config app/web -f config.yaml
```

### Tag after successful test

```yaml
- name: Tag as stable
  run: |
    ocmo -n prod tag item app/web --tag stable
  # or mark-stable via resolve:
  # ocmo -n prod resolve app/web --mark-stable
```

### Resolve and download for deployment artifact

```yaml
- name: Fetch configs
  run: |
    mkdir -p ./deploy-config
    ocmo -n prod resolve app/ --version stable --cast json -O ./deploy-config/
    ls ./deploy-config/
```

---

## Change freeze (lock before deploy)

```yaml
- name: Lock production configs
  run: |
    ocmo -n prod lock app/prod \
      --reason "Deploying v${{ github.run_number }}" \
      --expires-at $(date -u -d '+2 hours' +%Y-%m-%dT%H:%M:%SZ)

- name: Deploy
  run: ./deploy.sh

- name: Unlock
  if: always()    # unlock even if deploy fails
  run: ocmo -n prod delete lock app/prod
```

---

## Promote across environments (manual approval gate)

```yaml
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    steps:
      - name: Tag staging as stable
        run: ocmo -n staging tag item app/web --tag stable

  promote-to-prod:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production      # GitHub environment with required reviewers
    steps:
      - name: Copy stable config from staging to prod
        run: |
          # Read staging content
          ocmo -n staging get item app/web@stable --raw > /tmp/staging-config.yaml
          # Update prod
          ocmo -n prod update config app/web -f /tmp/staging-config.yaml
          ocmo -n prod tag item app/web --tag stable
```

---

## GitLab CI example

```yaml
variables:
  OCMO_SERVER: https://ocmo.example.com
  OCMO_NAMESPACE: prod

stages:
  - validate
  - deploy

validate-config:
  stage: validate
  image: python:3.13-slim
  before_script:
    - pip install ocmo-cli
  script:
    - ocmo -n $OCMO_NAMESPACE resolve draft app/web -f config.yaml --trace-only
  only:
    - merge_requests

deploy:
  stage: deploy
  image: python:3.13-slim
  before_script:
    - pip install ocmo-cli
  script:
    - ocmo -n $OCMO_NAMESPACE update config app/web -f config.yaml
    - ocmo -n $OCMO_NAMESPACE tag item app/web --tag stable
  variables:
    OCMO_CLIENT_ID: $OCMO_CLIENT_ID
    OCMO_CLIENT_SECRET: $OCMO_CLIENT_SECRET
  only:
    - main
```

---

## Webhook-triggered pipeline

Configure OCMO to push events to your CI system:

```yaml
# _webhooks config
webhooks:
  - id: ci-trigger
    enabled: true
    url: https://ci.example.com/api/webhook/ocmo
    events:
      - config.tagged
    filter:
      paths:
        - app/**
    signature_key: "{!hmac_signing_key}"
    payload:
      preset: ocmo
```

Then in your CI system, verify the HMAC signature and trigger a pipeline when `event: config.tagged` with a matching tag.

---

## Related

- [Locks](../features/locks.md)
- [Propagation](../features/propagation.md)
- [Webhooks](../features/webhooks.md)
- [Promote across environments](promote-across-environments.md)
