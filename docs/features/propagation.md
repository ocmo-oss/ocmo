# Propagation

Propagation automatically pushes a config's data into one or more target configs when a trigger fires. It enables "promote to downstream environments" workflows without manual copy-paste.

---

## How it works

1. You declare `_ocmo.propagation` on a source config listing targets and a trigger.
2. When the trigger fires (a matching tag is set, or you call the manual endpoint), OCMO deep-merges the source config's data into each target.
3. Each target gets a new version with the merged content.

**Secrets and templates are never propagated.**

---

## Configuration

```yaml
# proj/dev/app/config
_ocmo:
  propagation:
    enabled: true
    trigger: tag             # tag | manual
    tag: stable              # glob matched against tag name; required for trigger=tag
    mode: data               # data | whole
    targets:
      - proj/qa/app/config
      - proj/stage/app/config
    exclude:
      - logging.log_level    # keep target's own value for this field
      - database.host        # each env has its own host

environment: dev
database:
  host: db.dev.internal
  port: 5432
  pool_size: 5
logging:
  log_level: debug
```

### Fields

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `true` | Toggle propagation without removing the config |
| `trigger` | `tag` | `tag` — fires when a matching tag is set; `manual` — fires only via API call |
| `tag` | — | Glob matched against the tag name. Required when `trigger=tag`. Example: `stable`, `release-*` |
| `mode` | `data` | `data` — propagate data body only; target keeps its own `_ocmo`. `whole` — propagate data + `_ocmo` (except target keeps `_ocmo.propagation`) |
| `targets` | — | List of config paths (absolute). Optionally with `@version`: `proj/qa/app/config@stable`. Glob patterns in targets are not supported. |
| `exclude` | `[]` | List of dot-path field paths to exclude from propagation (e.g. `logging.log_level`). Target keeps its own values for these fields. |

Max 5 targets per source config (`OCMO_MAX_PROPAGATION_TARGETS`).

---

## Trigger: `tag`

When `trigger: tag`, propagation fires each time a tag is set on the source config whose name matches the `tag` glob.

```bash
# This sets "stable" on the dev config, which triggers propagation to QA and stage
ocmo -n prod tag item proj/dev/app/config --tag stable

# REST
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~tag/proj/dev/app/config" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"tag": "stable"}'
```

Propagation requires `config:tag` on the source **and** `config:write` on each target. If the caller lacks write permission on any target, propagation is rejected.

---

## Trigger: `manual`

```bash
# REST
curl -X POST "https://ocmo.example.com/api/v1/ns/prod/~propagate/proj/dev/app/config" \
  -H "Authorization: Bearer $TOKEN"

# CLI
ocmo -n prod propagate proj/dev/app/config
```

Requires `config:read` on source + `config:write` on each target.

---

## Merge semantics

Propagation uses **deep-merge** — source data is merged into the current target content. The source wins on conflicts. **Lists are replaced** (not appended).

Given source data:

```yaml
database:
  host: db.dev.internal
  port: 5432
replicas: 2
tags:
  - dev
  - latest
```

And target (QA):

```yaml
database:
  host: db.qa.internal   # own host — will be overwritten unless excluded
  port: 5432
  name: myapp            # not in source — kept
replicas: 1
tags:
  - qa
```

With `exclude: [database.host]`:

Result in QA:

```yaml
database:
  host: db.qa.internal   # kept (excluded)
  port: 5432
  name: myapp            # kept (not in source)
replicas: 2              # from source
tags:
  - dev                  # list replaced by source value
  - latest
```

---

## Using `exclude` to protect environment-specific values

Move environment-specific values into `_ocmo.parameters` on the target configs instead of using `exclude`. This is cleaner — parameters are resolved at read time from the path, while `exclude` requires remembering to keep the list updated.

```yaml
# proj/qa/app/config
_ocmo:
  parameters:
    db_host:
      type: dynamic
      value: db.qa.internal

database:
  host: "{!db_host}"   # stays per-env regardless of propagation
  port: 5432
```

---

## Related

- [Configs](configs.md)
- [Tags and versions](../concepts/versions-and-tags.md)
- [Parameters](resolving/parameters.md)
