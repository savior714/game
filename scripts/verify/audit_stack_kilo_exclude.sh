#!/usr/bin/env bash
# Regression: .kilo/package-lock.json must not fail just audit-stack.
# Kilo plugin sandbox is outside monorepo pnpm SSOT (see scripts/audit_stack.sh exclude_tokens).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

cleanup() {
  rm -f .kilo/package-lock.json
}
trap cleanup EXIT

mkdir -p .kilo
touch .kilo/package-lock.json

output="$(bash scripts/audit_stack.sh 2>&1 || true)"

if echo "$output" | grep -qE '\.kilo/package-lock\.json'; then
  echo "❌ audit_stack.sh flagged .kilo/package-lock.json (exclude_tokens regression)" >&2
  exit 1
fi

echo "✅ audit_stack.sh ignores .kilo/package-lock.json"
