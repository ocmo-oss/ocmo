# Production image for the OCMO API (Django + django-ninja).
# Build context: api/
# Local development: use Dockerfile.dev and docker-compose.dev.yml.

FROM python:3.13-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 ocmo \
    && useradd --uid 1000 --gid ocmo --create-home --shell /usr/sbin/nologin ocmo

WORKDIR /app

COPY --from=builder --chown=ocmo:ocmo /app /app

RUN mkdir -p /tmp/ocmo/resolved /var/log/ocmo-api/sync /tmp/git-sync \
    && chown -R ocmo:ocmo /tmp/ocmo /var/log/ocmo-api /tmp/git-sync

USER ocmo

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

CMD ["bash", "/app/docker/entrypoint.prod.sh"]
