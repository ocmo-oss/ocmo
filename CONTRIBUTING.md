# Contributing to OCMO

Thank you for your interest in contributing. This repository is a monorepo; change the component
that owns the behavior you are modifying and run its tests before opening a pull request.

## Getting started

1. Fork the repository and create a branch from `main`.
2. Install dependencies for the component you are working on (see [Development](#development)).
3. Make focused changes; match existing style and conventions.
4. Run linters and tests for that component.
5. Open a pull request with a clear description of the problem and solution.

## Development

| Component | Setup | Tests / lint |
|-----------|-------|--------------|
| **API** (`api/`) | `cd api && uv sync` | `uv run python manage.py test --keepdb` · `uv run ruff check .` · `uv run mypy core ocmoapi` |
| **SDK** (`sdk/`) | `uv sync --package ocmo-sdk` | `cd sdk && make test` · `make lint` |
| **CLI** (`cli/`) | `uv sync --package ocmo-cli` | `uv run --package ocmo-cli pytest cli/tests` · `uv run ruff check cli` |
| **Frontend** (`frontend/`) | `cd frontend && pnpm install` | `pnpm test` · `pnpm lint` |
| **Smoke** (`smoke/`) | `cd smoke && uv sync` | `uv run pytest -v` (requires running API) |

Full stack locally:

```bash
docker compose -f docker-compose.dev.yml -f docker-compose.hmr.yml up --build
```

See [docs/quickstart/README.md](docs/quickstart/README.md) for first-time setup.

## Code guidelines

- **API:** Business logic in `core/managers/`; thin Ninja handlers in `core/api/`; schemas in
  `core/schemas/`. Create Django migrations when models change.
- **SDK:** Regenerate client code when the OpenAPI spec changes (`cd sdk && make generate`).
- **CLI:** Command map is generated from `sdk/operations.yaml`; run the SDK/CLI codegen checks in CI
  when you touch API routes or CLI commands.
- **Docs:** Product docs live in `docs/`; keep README links in sync when moving pages.

## Use of AI tools

AI assistants (Cursor, Copilot, ChatGPT, and similar) are allowed when contributing. Treat them as
tools, not as a substitute for your own judgment.

If you use AI to help write or edit a contribution, you remain fully responsible for the result. You
should:

- Read and understand every line you submit — do not paste output you have not reviewed.
- Be able to explain and defend the design, behavior, and trade-offs in review.
- Verify that tests pass, edge cases are handled, and the change fits project conventions.
- Catch incorrect assumptions, hallucinated APIs, and subtle security or logic bugs before opening a
  PR.

Maintainers may ask you to rework or justify AI-assisted changes that look copy-pasted, untested, or
misaligned with the codebase.

## Pull requests

- One logical change per PR when possible.
- Include tests for bug fixes and new behavior where practical.
- Update documentation when user-visible behavior or configuration changes.
- Do not commit secrets, `.env` files, or local scratch data.

## Versioning

All application components share the same version number (currently `0.8.x`). API stability is not
guaranteed before `1.0.0`.

## Questions

- **Bugs and features:** [GitHub Issues](https://github.com/ocmo-oss/ocmo/issues)
- **Security:** see [SECURITY.md](SECURITY.md) — do not open public issues for vulnerabilities

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
