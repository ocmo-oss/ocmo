# Install the CLI

## Install

```bash
# Recommended: isolated tool install (upgradeable)
uv tool install ocmo-cli

# Alternative
pipx install ocmo-cli

# Verify
ocmo --version
```

Requires Python 3.11+. The `uv tool` method puts `ocmo` on your `PATH` in an isolated virtualenv.

---

## Configure

### Minimal (single server)

```bash
ocmo config set server https://ocmo.example.com
ocmo config set namespace prod      # optional default namespace
```

This writes to `~/.config/ocmo/config.yaml` (or `$OCMO_CONFIG`). The file is created with `0600` permissions.

### Multiple environments (contexts)

```bash
# Create a context for each environment
ocmo config set-context prod \
  --server https://ocmo.example.com \
  --namespace prod \
  --auth company-oidc

ocmo config set-context staging \
  --server https://staging.ocmo.example.com \
  --namespace staging \
  --auth company-oidc

# Define the auth profile
ocmo config set-auth company-oidc \
  --mode oidc \
  --issuer https://sso.example.com \
  --client-id ocmo-cli \
  --client-secret-file /run/secrets/ocmo-cli

# Switch contexts
ocmo config use-context prod

# See what's active
ocmo config current-context
ocmo config view
```

Config file format:

```yaml
current-context: prod
contexts:
  prod:
    server: https://ocmo.example.com
    namespace: prod
    auth: company-oidc
  staging:
    server: https://staging.ocmo.example.com
    namespace: staging
    auth: company-oidc
auths:
  company-oidc:
    mode: oidc
    issuer: https://sso.example.com
    client_id: ocmo-cli
    client_secret_file: /run/secrets/ocmo-cli
```

---

## Authenticate

### Interactive login (OIDC device code — no browser required)

```bash
ocmo auth login
```

Follow the printed URL and code to complete login in a browser. The access token is cached in `~/.cache/ocmo/` and refreshed automatically.

### Browser-based login (PKCE)

```bash
ocmo auth login --browser
```

Opens your default browser; completes authorization automatically.

### Check your session

```bash
ocmo auth status        # shows config source, auth mode, token expiry
ocmo whoami             # shows identity the server sees
```

### Logout

```bash
ocmo auth logout        # clears cached OIDC token
ocmo auth logout --all  # clears the entire cache directory
```

### CI/CD (no interactive login)

For pipelines, use environment variables. The CLI inherits all `OCMO_*` SDK env vars:

```bash
# OIDC client credentials (recommended for services)
export OCMO_SERVER=https://ocmo.example.com
export OCMO_CLIENT_ID=ci-pipeline
export OCMO_CLIENT_SECRET="$(cat /run/secrets/ocmo)"
export OCMO_NAMESPACE=prod
ocmo whoami    # token acquired automatically
```

Or a resolver token (read-only):

```bash
export OCMO_TOKEN=ocmort-...
export OCMO_SERVER=https://ocmo.example.com
ocmo -n prod resolve app/web --cast json
```

### Local dev against Dex (password grant)

```bash
export OCMO_SERVER=http://localhost:8080
export OCMO_CLIENT_ID=ocmo-sdk
export OCMO_CLIENT_SECRET=dev-only-ocmo-sdk-secret
export OCMO_OIDC_GRANT_TYPE=password
export OCMO_OIDC_USERNAME=admin@example.com
export OCMO_OIDC_PASSWORD=password
ocmo whoami
```

---

## First commands

```bash
ocmo version                        # check CLI and server versions match
ocmo whoami                         # confirm your identity
ocmo get namespace                  # list namespaces you have access to
ocmo -n prod ls                     # list items at the root of namespace "prod"
ocmo -n prod ls app/ -R             # list recursively under app/
ocmo -n prod tree app/ --depth 3    # ASCII tree view
ocmo -n prod get item app/web       # show item metadata
ocmo -n prod resolve app/web        # resolve and print (raw format by default)
```

---

## Shell completion

```bash
ocmo completion bash >> ~/.bashrc
ocmo completion zsh >> ~/.zshrc
ocmo completion fish > ~/.config/fish/completions/ocmo.fish
```

---

## Related

- [CLI reference](../reference/cli.md)
- [CI/CD guide](../how-to/ci-cd.md)
- [Authentication](../features/authentication.md)
