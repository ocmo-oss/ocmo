#!/usr/bin/env bash
set -euo pipefail

ocmo-api migrate --noinput
exec ocmo-api serve
