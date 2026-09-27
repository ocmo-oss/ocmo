#!/bin/sh
set -e

: "${OCMO_FRONTEND_UPSTREAM:=http://frontend:80}"
export OCMO_FRONTEND_UPSTREAM

envsubst '$OCMO_FRONTEND_UPSTREAM' \
  < /etc/nginx/ocmo/default.conf.template \
  > /etc/nginx/conf.d/default.conf
