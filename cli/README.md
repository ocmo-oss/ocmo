# ocmo-cli

Command-line interface for the OCMO configuration service. A thin shell over
[`ocmo-sdk`](https://pypi.org/project/ocmo-sdk/) with a `kubectl`-shaped verb/noun grammar. The CLI
contains no API protocol logic of its own.

**Distribution:** PyPI name `ocmo-cli` · **Python:** 3.11+ · **License:** Apache-2.0

**Pre-1.0.0:** Pin `ocmo-cli` and `ocmo-sdk` to the same release as your OCMO API server.

---

## Installation

Published package:

```bash
uv tool install ocmo-cli
# or
pipx install ocmo-cli
```

Monorepo development (from repository root):

```bash
uv sync --all-packages
uv run ocmo --help
```

---

## Quick start

```bash
# Point at your server (saved to ~/.config/ocmo/config.yaml)
ocmo config set server https://ocmo.example.com
ocmo config set namespace prod

# Authenticate
ocmo auth login

# Use it
ocmo -n prod get config app/web
ocmo -n prod resolve app/web --cast json
ocmo -n prod ls tree app/
```

---

## Configuration

Precedence (same model as `kubectl`):

```text
command flag > OCMO_* env var > current context in ~/.config/ocmo/config.yaml > built-in default
```

Manage contexts:

```bash
ocmo config get-contexts
ocmo config use-context prod
ocmo config set server https://ocmo.example.com
ocmo config view
```

---

## Output formats

`-o, --output` accepts: `table` (default on TTY), `wide`, `json`, `yaml`, `name`, `raw`,
`jsonpath=<expr>`.

---

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Generic runtime failure |
| 2 | Usage error |
| 3 | Not found (404) |
| 4 | Auth / permission failure (401, 403) |
| 5 | Conflict (409) |
| 6 | Path locked (423) |
| 7 | Validation failure (422, 413) |
| 8 | Hook execution failure |
| 9 | Import/export verification failure |
| 130 | Interrupted |

---

## Development

From repository root (workspace includes CLI and SDK):

```bash
uv sync --all-packages
uv run pytest cli/tests -q
uv run ruff check cli/
uv run mypy cli/ocmo_cli
```

Regenerate the command tree from the SDK operation map:

```bash
cd cli
uv run python scripts/generate_commands.py --write
```

Integration smoke tests (live API):

```bash
OCMO_RUN_INTEGRATION=1 uv run pytest cli/tests/test_smoke_integration.py -v
```

---

## Architecture notes

### Command surface

Generated operations are registered at import time from committed `commands.yaml` (produced from
`sdk/operations.yaml`). CI fails if the file drifts from the spec. Hand-written commands live in
`ocmo_cli/commands/`.

### Framework

Built on **click** (not typer) for fast cold start, dynamic command registration, and programmatic
`ocmo api` escape hatch.

---

## Related components

- SDK: [../sdk/README.md](../sdk/README.md)
- API: [../api/README.md](../api/README.md)
- Integration guides: [../docs/how-to/README.md](../docs/how-to/README.md) · [../docs/reference/cli.md](../docs/reference/cli.md)
- Monorepo overview: [../README.md](../README.md)
