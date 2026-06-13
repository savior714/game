#!/bin/bash

# AidenGame Verification Report Generator
# Included by verify.sh

save_verify_result() {
    local exit_code="${1:-0}"
    local failed_step_name="${2:-}"
    local pytest_failed_tests="${3:-}"

    # Export state variables for Python heredoc
    export VERIFY_STEPS_STR
    export TIMINGS_STR
    export RESULT_JSON_PATH
    export PYTEST_FAILURES_PATH
    export exit_code
    export failed_step_name
    export pytest_failed_tests

    python3 <<'EOF'
import json
import os
from datetime import datetime, timezone

steps_raw = os.environ.get('VERIFY_STEPS_STR', '').split("|")
steps = []
for s in steps_raw:
    if not s: continue
    name, sep, ok = s.rpartition(":")
    steps.append({"name": name, "ok": ok == "true"})

timings_raw = os.environ.get('TIMINGS_STR', '').split("|")
timings = []
for t in timings_raw:
    if not t: continue
    name, sep, ms = t.rpartition(":")
    timings.append({"name": name, "ms": int(ms)})

failed_tests = os.environ.get('pytest_failed_tests', '').split() if os.environ.get('pytest_failed_tests', '') else []

exit_code = int(os.environ.get('exit_code', 0))
agent_hint = "OK: Read verify-last-result.json via Read tool" if exit_code == 0 else "FAIL: Read verify-pytest-failures.txt or pytestFailedTests array."

external_gates = {}
gate_breakdown = {}
for gate in ["biome", "typecheck", "jsx-casing"]:
    summary_path = f"artifacts/verify/verify-{gate}-summary.json"
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            gate_data = json.load(f)
            external_gates[gate] = gate_data
            gate_breakdown[gate] = {
                "current": int(gate_data.get("current", 0) or 0),
                "baseline": int(gate_data.get("baseline", 0) or 0),
                "new": int(gate_data.get("new", 0) or 0),
                "blocking": int(gate_data.get("blocking", 0) or 0),
            }

payload = {
    "generatedAtUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "exitCode": exit_code,
    "failedStep": os.environ.get('failed_step_name') if os.environ.get('failed_step_name', '') else None,
    "steps": steps,
    "pytestFailedTests": failed_tests,
    "timingsMs": timings,
    "externalGates": external_gates,
    "gateBreakdown": gate_breakdown,
    "agentHint": agent_hint
}

result_path = os.environ.get('RESULT_JSON_PATH', 'verify-last-result.json')
with open(result_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)
EOF

    # Generate Markdown report from the JSON result
    if [ -f "$ROOT/scripts/generate_verify_report.py" ]; then
        python3 "$ROOT/scripts/generate_verify_report.py" > /dev/null 2>&1 || true
    fi
}
