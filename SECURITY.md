# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.8.x   | Yes       |
| < 0.8   | No        |

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Send details to the maintainers via [GitHub Security Advisories](https://github.com/ocmo-oss/ocmo/security/advisories/new)
(private report) or email the repository owners listed on the [ocmo-oss](https://github.com/ocmo-oss) organization.

Include:

- Description of the issue and potential impact
- Steps to reproduce
- Affected component (`api`, `sdk`, `cli`, `frontend`, `gateway`)
- Version or commit hash, if known

We aim to acknowledge reports within a few business days and will coordinate disclosure and a fix
before any public announcement when possible.

## Production deployment checklist

Before exposing OCMO to a network:

1. Set strong, unique values for `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, and `OCMO_MASTER_KEY`.
2. Set `DJANGO_DEBUG=False` and restrict `DJANGO_ALLOWED_HOSTS`.
3. Use a production-grade OIDC provider; do not rely on the bundled Dex stack outside local dev.
4. Set `OCMO_PUBLIC_URL` to your public gateway URL when behind a reverse proxy.
5. Prefer Redis-backed resolve cache and artifact storage when running multiple API workers.
6. Never commit `.env` files or real credentials to the repository.

The dev Docker stack (`docker-compose.dev.yml`) ships insecure defaults on purpose. See
[`.env.example`](.env.example) and [`api/.env.example`](api/.env.example) for production-oriented
templates.

## Dependency updates

Report issues in third-party dependencies through the channels above if they affect OCMO's security
posture. Routine dependency bumps are handled via pull requests.
