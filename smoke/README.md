# OCMO resolve smoke tests

HTTP smoke tests for the resolve API. Each scenario lives under `cases/<name>/`:

```
cases/<name>/
  case.yaml           # resolve path, query params, expectations
  configs/            # YAML configs → POST ~config/~create/{path}
  templates/          # Jinja2 templates → POST ~template/~create/{path}
  secrets/            # YAML secrets → POST ~secret/~create/{path}
  expected/           # golden resolved artifact(s) to compare
```

Tree paths mirror the API: `configs/scenario2/prod.yaml` creates config `scenario2/prod`.
Template paths keep their extension, e.g. `templates/scenario4/nginx.conf.j2`.

## Prerequisites

- OCMO API running (default `http://localhost:8000`)
- Auth disabled or reachable without credentials (dev setup)
- `OCMO_MASTER_KEY` set if cases use secrets

## Run

```bash
cd smoke
uv sync
uv run pytest -v
```

Resolver token visibility and rotation:

```bash
uv run pytest test_resolver_tokens.py -v
```

Document upload content-types (config, template, secret, resolver create/update):

```bash
uv run pytest test_document_content_types.py -v
```

`mark-stable` tag promotion on resolve:

```bash
uv run pytest test_mark_stable.py -v
```

Tree locking (`~lock/` API and write enforcement):

```bash
uv run pytest test_locks.py -v
```

Change propagation (`~propagate/`, tag triggers, stable promotion):

```bash
uv run pytest test_propagation.py -v
```

Propagation cases use `kind: propagation` in `case.yaml` (see `cases/propagation_manual/`).
Actions: `propagate` (POST `~propagate/`), `tag` (set tag on source), or `resolve` with `?mark-stable=true`.
Targets may use `path/to/config@version_or_tag` in `_ocmo.propagation.targets`.

Each test sends the same logical document via every `supported_types` media type declared on the request schema (plus `application/octet-stream` from OpenAPI) and compares stored content.

### Options

| Flag / env | Purpose |
|---|---|
| `--base-url URL` | API base URL (default `OCMO_SMOKE_BASE_URL` or `http://localhost:8000`) |
| `--keep-namespace` | Do not delete namespace after test (`OCMO_SMOKE_KEEP_NAMESPACE=1`) |

On failure, pytest shows a unified diff between `expected/<file>` and the downloaded artifact.

## Refresh expected artifacts

After intentional resolver changes, re-record golden files from a running API:

```bash
cd smoke
uv run python scripts/record_expected.py cases/simple_yaml
uv run python scripts/record_expected.py --all
```

## `case.yaml` reference

```yaml
id: my_case
description: Human-readable summary
resolve_path: path/to/config-or-folder
query:                      # optional GET query params
  version: latest
  cast: json
  param_replicas: "7"
  trace_only: "true"
  mark-stable: "true"
expect:
  status: 200               # or 422 for error cases
  error_substring: "..."    # for status != 200
  trace_only: true          # compare expected/trace.json
  match: ordered            # ordered (default) | multiset
  sort_by_name: true        # pair items by name when ordered
  items:
    - name: output-name     # optional API item name check
      file: output.yaml     # file under expected/
```

Use `match: multiset` when folder resolve returns duplicate `name` values with different content.
