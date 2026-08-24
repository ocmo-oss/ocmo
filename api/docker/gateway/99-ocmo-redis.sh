#!/bin/sh
set -e

OCMO_REDIS_CONF_DIR=/etc/nginx/conf.d/ocmo-redis
mkdir -p "${OCMO_REDIS_CONF_DIR}"

# Enable redis artifact offload only when the redis service is on the compose network.
if getent hosts redis >/dev/null 2>&1; then
    ln -sf /etc/nginx/ocmo/redis.conf "${OCMO_REDIS_CONF_DIR}/redis.conf"
fi
