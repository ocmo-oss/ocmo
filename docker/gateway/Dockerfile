# Production image for the OCMO gateway (nginx + ngx_http_redis).
# Build context: repository root.
# Local development: use Dockerfile.dev (same image) with docker-compose.dev.yml nginx overrides.

FROM nginx:1.27-alpine AS builder

RUN apk add --no-cache --virtual .build-deps \
        gcc \
        libc-dev \
        make \
        openssl-dev \
        pcre-dev \
        zlib-dev \
        linux-headers \
        curl \
        tar \
        git \
    && git clone --depth=1 https://github.com/osokin/ngx_http_redis.git /tmp/ngx_http_redis \
    && NGINX_VERSION="$(nginx -v 2>&1 | sed 's/.*\///')" \
    && curl -fsSL "http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz" \
        | tar xz -C /tmp \
    && cd "/tmp/nginx-${NGINX_VERSION}" \
    && ./configure --with-compat \
        --add-dynamic-module="/tmp/ngx_http_redis" \
    && make modules \
    && apk del .build-deps

FROM nginx:1.27-alpine

RUN apk add --no-cache gettext wget

COPY --from=builder /tmp/nginx-*/objs/ngx_http_redis_module.so /usr/lib/nginx/modules/
COPY docker/gateway/nginx-main.conf /etc/nginx/nginx.conf
COPY docker/nginx-redis.conf.template /etc/nginx/ocmo/redis.conf.template
COPY docker/gateway/99-ocmo-redis.sh /docker-entrypoint.d/99-ocmo-redis.sh
RUN chmod +x /docker-entrypoint.d/99-ocmo-redis.sh \
    && mkdir -p /etc/nginx/conf.d/ocmo-redis

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
