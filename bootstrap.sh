#!/usr/bin/env bash
# Deprecated local wrapper — SSOT installer is ../bootstrap/bootstrap.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/../bootstrap/bootstrap.sh" "${1:-${SCRIPT_DIR}}"
