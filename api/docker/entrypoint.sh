#!/usr/bin/env bash
# Legacy entrypoint — development only. Production uses docker/entrypoint.prod.sh.
set -ex

uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
