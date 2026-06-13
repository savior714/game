#!/usr/bin/env bash
# Renderer App Router 스모크 — Next dev(기본 3000)가 떠 있는 상태에서만 실행한다.
# 예: ./run_dev.sh 기동 후
#   RENDERER_SMOKE_BASE=http://127.0.0.1:8080 ./scripts/verify/renderer_route_smoke.sh
set -euo pipefail

BASE="${RENDERER_SMOKE_BASE:-http://127.0.0.1:8080}"

check_status() {
  local path="$1"
  local expected_re="$2"
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' "${BASE}${path}" || echo "000")"
  if ! echo "${code}" | grep -Eq "${expected_re}"; then
    echo "FAIL ${path}: HTTP ${code} (expected ${expected_re})" >&2
    echo "Hint: start dev stack (./run_dev.sh) and ensure next.config pageExtensions uses default ['tsx','ts',...] not ['page.tsx',...]." >&2
    exit 1
  fi
  echo "OK ${path} -> ${code}"
}

check_status "/login" '^200$'
check_status "/" '^30[1278]$'

echo "OK renderer route smoke: ${BASE}"
