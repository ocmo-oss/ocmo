# Promote Configs Across Environments

Patterns for moving configs from development through staging to production.

---

## Recommended tree layout

```
app/
  base/
    database        # shared defaults
    logging
  dev/
    database        # extends ../base/database, dev overrides
    logging
  staging/
    database        # extends ../base/database, staging overrides
    logging
  prod/
    database        # extends ../base/database, prod overrides
    logging
```

Each environment config extends the base and applies environment-specific values.

---

## Pattern 1: Tags as promotion gates

Each environment's `_permissions` grants CI the `config:tag` action. Promotion means tagging a config as `stable` in the target environment.

```bash
# After QA passes, tag staging stable
ocmo -n myapp tag item app/staging/database --tag stable

# After staging sign-off, copy to prod and tag
ocmo -n myapp get item app/staging/database@stable --raw > /tmp/db.yaml
ocmo -n myapp update config app/prod/database -f /tmp/db.yaml
ocmo -n myapp tag item app/prod/database --tag stable
```

Consumers in each environment resolve with `?version=stable` — they always get the last approved version.

---

## Pattern 2: Propagation (automatic push)

Set up propagation on the dev config so tagging `stable` in dev automatically updates downstream:

```yaml
# app/dev/database
_ocmo:
  extend:
    configs:
      - ../base/database@stable
  propagation:
    enabled: true
    trigger: tag
    tag: stable
    mode: data
    targets:
      - app/staging/database
      - app/prod/database
    exclude:
      - database.host      # each env has its own host
      - database.password  # managed per-env via secrets

environment: dev
database:
  host: db.dev.internal
  pool_size: 5
```

When you run:

```bash
ocmo -n myapp tag item app/dev/database --tag stable
```

OCMO automatically pushes the dev data to staging and prod (excluding `database.host` and `database.password`).

Staging and prod configs keep their own values for excluded fields.

---

## Pattern 3: `mark-stable` on resolve (CD trigger)

Instead of tagging manually, have your CD pipeline resolve with `mark-stable=true` after a successful deployment:

```bash
# After prod deployment succeeds
ocmo -n myapp resolve app/prod/ --version latest --mark-stable
```

This advances `stable` on all resolved configs, and if propagation is configured with `trigger: tag` and `tag: stable`, it cascades.

---

## Protecting production from accidental writes

Use `_permissions` to require two actors for prod writes:

```json
{
  "id": "prod-write-devops-only",
  "effect": "Allow",
  "actors": [
    {"kind": "User", "claims": {"groups": "devops-admins@example.com"}}
  ],
  "actions": ["config:write", "config:tag"],
  "resources": ["app/prod/**"]
}
```

And a deny for everyone else:

```json
{
  "id": "deny-prod-writes-others",
  "effect": "Deny",
  "actors": [
    {"kind": "User", "claims": {"groups": "*"}}
  ],
  "actions": ["config:write", "config:tag"],
  "resources": ["app/prod/**"]
}
```

---

## Checking diff before promoting

Before promoting, diff the two environments:

```bash
# Compare staging and prod configs
ocmo -n myapp diff app/staging/database ..app/prod/database

# Or compare resolved outputs
ocmo -n myapp resolve app/staging/database --cast json -O /tmp/staging.json
ocmo -n myapp resolve app/prod/database --cast json -O /tmp/prod.json
diff /tmp/staging.json /tmp/prod.json
```

---

## Related

- [Propagation](../features/propagation.md)
- [Tags and versions](../concepts/versions-and-tags.md)
- [CI/CD guide](ci-cd.md)
- [Locks](../features/locks.md)
