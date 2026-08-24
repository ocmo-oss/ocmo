# OCMO gateway: nginx with ngx_http_redis for X-Accel-Redirect artifact offload.
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

COPY --from=builder /tmp/nginx-*/objs/ngx_http_redis_module.so /usr/lib/nginx/modules/
COPY docker/gateway/nginx-main.conf /etc/nginx/nginx.conf
COPY docker/nginx-redis.conf /etc/nginx/ocmo/redis.conf
COPY docker/gateway/99-ocmo-redis.sh /docker-entrypoint.d/99-ocmo-redis.sh
RUN chmod +x /docker-entrypoint.d/99-ocmo-redis.sh \
    && mkdir -p /etc/nginx/conf.d/ocmo-redis
