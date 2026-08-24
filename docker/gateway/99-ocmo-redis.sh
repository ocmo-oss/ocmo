#!/bin/sh
set -e

OCMO_REDIS_CONF_DIR=/etc/nginx/conf.d/ocmo-redis
mkdir -p "${OCMO_REDIS_CONF_DIR}"

REDIS_HOST="${REDIS_HOST:-redis}"
REDIS_PORT="${REDIS_PORT:-6379}"

# Enable redis artifact offload when the configured Redis host resolves on the container network.
if getent hosts "${REDIS_HOST}" >/dev/null 2>&1; then
    export REDIS_HOST REDIS_PORT
    envsubst < /etc/nginx/ocmo/redis.conf.template > "${OCMO_REDIS_CONF_DIR}/redis.conf"
fi
