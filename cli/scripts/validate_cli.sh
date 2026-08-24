#!/usr/bin/env bash
# CLI validation harness — run against a live OCMO server.
set -uo pipefail

OCMO="${OCMO_BIN:-/home/andy/ocmo/.venv/bin/ocmo}"
NS="${OCMO_NAMESPACE:-my-second-ns}"
export OCMO_SERVER="${OCMO_SERVER:-http://localhost:8080}"
export OCMO_CLIENT_ID="${OCMO_CLIENT_ID:-ocmo-sdk}"
export OCMO_CLIENT_SECRET="${OCMO_CLIENT_SECRET:-dev-only-ocmo-sdk-secret}"
export OCMO_OIDC_GRANT_TYPE="${OCMO_OIDC_GRANT_TYPE:-password}"
export OCMO_OIDC_USERNAME="${OCMO_OIDC_USERNAME:-admin@example.com}"
export OCMO_OIDC_PASSWORD="${OCMO_OIDC_PASSWORD:-password}"
export OCMO_OIDC_ISSUER="${OCMO_OIDC_ISSUER:-http://localhost:8080/dex}"
export OCMO_OIDC_TOKEN_URL="${OCMO_OIDC_TOKEN_URL:-http://localhost:8080/dex/token}"

PASS=0
FAIL=0

run() {
  local desc="$1"; shift
  local expect_code="${1:-0}"; shift
  local out
  local code
  out=$("$@" 2>&1) && code=0 || code=$?
  if [[ "$code" -eq "$expect_code" ]]; then
    echo "PASS [$code] $desc"
    ((PASS++)) || true
    return 0
  fi
  echo "FAIL [$code expected $expect_code] $desc"
  echo "  cmd: $*"
  echo "  out: ${out:0:400}"
  ((FAIL++)) || true
  return 1
}

echo "=== CLI validation (namespace=$NS) ==="

run "version" 0 "$OCMO" version
run "whoami yaml" 0 "$OCMO" whoami -o yaml
run "config view" 0 "$OCMO" config view
run "auth status" 0 "$OCMO" auth status
run "completion bash" 0 "$OCMO" completion bash
run "can-i namespace:read" 0 "$OCMO" can-i namespace:read -n "$NS"
run "api-health" 0 "$OCMO" api-health
run "get cast" 0 "$OCMO" get cast -o name
run "schema ocmo" 0 "$OCMO" schema ocmo

run "invalid global -o" 2 "$OCMO" -o blabla ls
run "ls missing ns" 2 env -u OCMO_NAMESPACE "$OCMO" ls

run "get namespace list name" 0 "$OCMO" get namespace -o name
run "get namespace show" 0 "$OCMO" get namespace "$NS" -o yaml
if "$OCMO" get namespace --help 2>&1 | grep -q -- "--output"; then
  echo "PASS [0] get namespace help has -o"
  ((PASS++)) || true
else
  echo "FAIL get namespace help missing --output"
  ((FAIL++)) || true
fi

run "ls root" 0 "$OCMO" -n "$NS" ls
run "ls name" 0 "$OCMO" -n "$NS" ls -o name
run "ls path" 0 "$OCMO" -n "$NS" ls -o path
run "ls json" 0 "$OCMO" -n "$NS" ls -o json
run "tree" 0 "$OCMO" -n "$NS" tree
run "get item builtin" 0 "$OCMO" -n "$NS" get item _permissions -o name
run "get item missing" 3 "$OCMO" -n "$NS" get item does-not-exist
run "create namespace dry-run" 0 "$OCMO" create namespace test-dry --dry-run

echo ""
echo "=== Results: PASS=$PASS FAIL=$FAIL ==="
[[ "$FAIL" -eq 0 ]]
