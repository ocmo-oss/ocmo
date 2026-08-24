# Webhooks

Webhooks deliver HTTP push notifications to external systems when config events happen. They're configured through the `_webhooks` builtin config in each namespace.

---

## Supported events

| Event | When it fires |
|-------|--------------|
| `config.created` | Config created (new path) |
| `config.updated` | Config updated (new version) |
| `config.deleted` | Config or version deleted |
| `config.tagged` | Tag set or removed on a config |
| `config.resolved` | Config resolved via `~resolve` |
| `template.created` | Template created |
| `template.updated` | Template updated |
| `template.deleted` | Template or version deleted |
| `template.tagged` | Tag set or removed on a template |
| `resolver.created` | Resolver created |
| `resolver.updated` | Resolver updated |
| `secret.created` | Secret created (value never included) |
| `secret.updated` | New secret version saved (value never included) |
| `secret.deleted` | Secret or version deleted |
| `secret.tagged` | Tag set or removed on a secret |
| `namespace.updated` | Namespace metadata or tag pointers changed |
| `lock.created` | Tree lock created |
| `lock.updated` | Existing lock replaced |
| `lock.deleted` | Lock removed |
| `propagation.triggered` | Manual propagation triggered |

---

## Default payload

```json
{
  "event": "config.updated",
  "namespace": "prod",
  "path": "app/web",
  "version": 8,
  "tag": null,
  "actor": {
    "type": "user",
    "email": "alice@example.com"
  },
  "timestamp": "2026-08-24T18:42:11Z"
}
```

Payloads are signed with HMAC-SHA256. The signature is sent in the `X-OCMO-Signature` header (configurable per webhook entry).

---

## Configuring webhooks

Update the `_webhooks` config in your namespace. Only users with Global `write` on the namespace can access this path.

```bash
# Read current config
ocmo -n prod get item _webhooks --reveal     # (requires global:write)

# Update
ocmo -n prod update config _webhooks -f webhooks.yaml
```

### Example `_webhooks` config

```yaml
_ocmo:
  parameters:
    hmac_signing_key:
      type: secret
      value: _webhooks_secret@latest    # auto-created companion secret
      description: HMAC signing key for webhook payloads

webhooks:
  - id: ci-pipeline
    enabled: true
    url: https://ci.example.com/hooks/ocmo
    events:
      - config.updated
      - config.tagged
    filter:
      paths:
        - app/**           # only events on paths under app/
    signature_key: "{!hmac_signing_key}"
    payload:
      preset: ocmo         # built-in format

  - id: slack-alerts
    enabled: true
    url: https://hooks.slack.com/services/T.../B.../...
    events:
      - config.updated
    filter:
      paths:
        - app/prod/**
    signature_key: "{!hmac_signing_key}"
    payload:
      preset: slack        # Slack message format
```

### Webhook entry fields

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Stable identifier for logs and error messages |
| `enabled` | No | Default `true`. Set `false` to disable without removing. |
| `url` | Yes | HTTPS endpoint to deliver to |
| `events` | Yes | List of event types to subscribe to |
| `filter.paths` | No | Glob list — only deliver when event path matches at least one glob |
| `signature_key` | Yes | HMAC signing key — literal string or `{!param}` reference |
| `signature_header` | No | Header name for the signature. Default: `X-OCMO-Signature` |
| `payload` | No | Format configuration (see below) |

---

## Payload formats

### Built-in presets

| Preset | Description |
|--------|-------------|
| `ocmo` | Default OCMO JSON format (shown above) |
| `slack` | Slack Incoming Webhook message with formatted attachment |
| `teams` | Microsoft Teams Adaptive Card |
| `discord` | Discord embed |
| `generic_json` | Flat JSON with all event fields at the top level |

```yaml
payload:
  preset: slack
```

### Custom Jinja2 template

Full control over the payload body:

```yaml
payload:
  template: |
    {
      "text": "{{ event }}: {{ namespace }}/{{ path }}@v{{ version }} by {{ actor.email }}"
    }
  headers:
    Content-Type: application/json
    Authorization: Bearer my-secret-token
```

Template variables: `event`, `namespace`, `path`, `version`, `tag`, `actor.type`, `actor.email`, `actor.name`, `timestamp`.

`payload.headers` adds extra HTTP headers alongside the HMAC signature header.

---

## The HMAC signing key

The signing key is stored in `_webhooks_secret` (a companion Secret auto-created with the namespace). Reference it with a `secret` parameter:

```yaml
_ocmo:
  parameters:
    hmac_signing_key:
      type: secret
      value: _webhooks_secret@latest
```

Then use `"{!hmac_signing_key}"` as `signature_key` for each webhook entry.

To rotate the signing key, update `_webhooks_secret`:

```bash
cat <<'EOF' | ocmo -n prod update secret _webhooks_secret
new_hmac_key: "$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
EOF
```

The resolved `_webhooks` config is cached in-process and refreshed when `_webhooks` is updated, `webhooks_tag` changes, or any referenced secret is updated.

---

## Active tag and validation

OCMO evaluates the version of `_webhooks` pointed to by `webhooks_tag` (default `latest`). Switch to a specific version before it goes to `latest`:

```bash
ocmo update namespace prod --webhooks-tag tested
```

Every write to `_webhooks` is validated against `_webhooks.schema` before saving. Invalid configs are rejected.

---

## Delivery

- Timeout: `OCMO_WEBHOOK_TIMEOUT_SECONDS` (default 5 s)
- Delivery is best-effort — OCMO does not retry on failure (implement retries on the receiver side)
- Secret values are never included in webhook payloads
- Builtin configs (`_permissions`, `_webhooks`, `_git_sync`) and companion secrets emit events normally; opt in via `filter.paths`

---

## Related

- [Namespaces](../concepts/namespaces.md) — `webhooks_tag`
- [Secrets](secrets.md) — `_webhooks_secret`
- [Authorization](authorization.md) — Global `write` required to access `_webhooks`
