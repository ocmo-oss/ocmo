#!/usr/bin/env bash
set -ex

uv run python manage.py migrate
uv run python manage.py runserver 0.0.0.0:8000
