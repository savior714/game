#!/usr/bin/env bash
# 대시보드 REST 스모크 — 백엔드 HTTP 서버가 떠 있는 상태에서만 실행한다.
# 예: ./run_dev.sh 기동 후
#   DASHBOARD_SMOKE_BASE=http://127.0.0.1:8000 ./scripts/verify/smoke_dashboard_rest.sh
set -euo pipefail

BASE="${DASHBOARD_SMOKE_BASE:-http://127.0.0.1:8000}"

curl -sf "${BASE}/api/v1/dashboard/stats/today" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for k in ('waiting', 'in_progress', 'waiting_payment', 'completed', 'unsigned_charts'):
    assert k in d, k
"
curl -sf "${BASE}/api/v1/dashboard/stats/system-health" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for k in ('audit_integrity', 'backup_status', 'vault_status', 'nims_reporting', 'last_check'):
    assert k in d, k
"
echo "OK dashboard REST smoke: ${BASE}"
