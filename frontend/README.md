# ocmo-frontend

Single-page web application for OCMO operators. React 18, TypeScript, Vite, Tailwind CSS, and
TanStack Query. Authenticates humans via **OIDC (PKCE)**; resolver tokens are for automation only
(CLI/SDK).

**Package name:** `ocmo-frontend` (private, not published to npm) · **License:** Apache-2.0

---

## Features

- Namespace home and configuration tree navigation
- Config, template, secret, and resolver editing (Monaco)
- Resolve preview, diff, audit views, permissions-aware UI
- Served behind the gateway in production; Vite dev server with HMR in local Docker

UI setup and coverage: [../docs/quickstart/install-web-ui.md](../docs/quickstart/install-web-ui.md).

---

## Requirements

- **Node.js** 20 LTS (see `frontend/Dockerfile`)
- **pnpm** 10.x (`packageManager` field in `package.json`)

---

## Installation

```bash
cd frontend
corepack enable
pnpm install
```

---

## Scripts

| Command | Description |
|---------|-------------|
| `pnpm dev` | Vite dev server (default port 5173; Docker maps 3000) |
| `pnpm build` | Typecheck + production bundle to `dist/` |
| `pnpm preview` | Serve the production build locally |
| `pnpm test` | Vitest unit tests |
| `pnpm lint` | ESLint |
| `pnpm format` | Prettier |

---

## Configuration

Environment variables (Vite — baked in at **build time** for production):

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | API origin when UI and API are on different hosts; empty when served from same gateway |
| `VITE_DEV_SERVER_ORIGIN` | Public origin for HMR through the gateway (e.g. `http://localhost:8080`) |

Runtime auth settings (issuer, client ID) come from `GET /api/version` → `auth.oidc`.

---

## Local development

### Standalone (API already running)

```bash
pnpm dev
```

Point the browser at the Vite URL. Set `VITE_API_BASE_URL` if the API is not proxied.

### Docker with HMR (recommended)

From the repository root:

```bash
docker compose -f docker-compose.dev.yml -f docker-compose.hmr.yml up --build
```

UI at [http://localhost:8080](http://localhost:8080); Vite direct access on port 3000.

---

## Production build

```bash
pnpm build
```

Docker production image (`Dockerfile`):

```bash
docker build -f Dockerfile -t ocmo-frontend:local .
# optional build-time API URL:
docker build --build-arg VITE_API_BASE_URL=https://ocmo.example.com -f Dockerfile -t ocmo-frontend:local .
```

The image serves static files with nginx (`nginx.conf`).

---

## Project structure

```text
frontend/
├── src/
│   ├── api/        # HTTP client, types, auth helpers
│   ├── pages/      # Route-level views
│   ├── shell/      # Layout, top bar, sidebars
│   └── ...
├── public/
├── vite.config.ts
├── Dockerfile          # production (nginx)
└── Dockerfile.dev      # dev base image for compose
```

---

## Testing

```bash
pnpm test
```

---

## Related components

- API: [../api/README.md](../api/README.md)
- SDK: [../sdk/README.md](../sdk/README.md)
- CLI: [../cli/README.md](../cli/README.md)
- Monorepo overview: [../README.md](../README.md)
