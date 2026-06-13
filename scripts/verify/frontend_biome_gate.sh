#!/usr/bin/env bash

set -euo pipefail

show_help() {
  cat <<EOF
Usage: $(basename "$0") [OPTION]

Frontend Biome lint gate - validates Biome errors against baseline.

Options:
  --auto-fix           Run Biome auto-fix (--write --unsafe) and exit
  --auto-fix --update-baseline  Auto-fix and update baseline in one command
  --update-baseline    Update the baseline file with current errors
  --help               Show this help message

Examples:
  # Run gate check (default)
  $(basename "$0")

  # Auto-fix lint issues and verify gate
  $(basename "$0") --auto-fix

  # Auto-fix, verify, and update baseline (one-command workflow)
  $(basename "$0") --auto-fix --update-baseline

  # Update baseline after reviewing fixes
  $(basename "$0") --update-baseline

EOF
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -d "$ROOT/apps/renderer" ]]; then
  FRONTEND_DIR="$ROOT/apps/renderer"
else
  FRONTEND_DIR="$ROOT/frontend"
fi
BASELINE_FILE="$FRONTEND_DIR/.ci/biome-baseline.txt"
REPORTS_DIR="$ROOT/docs/reports/biome"
TMP_DIR="$(mktemp -d)"
RAW_OUT="$TMP_DIR/biome.raw.log"
DIAG_JSON="$TMP_DIR/biome.diagnostics.json"
CURR_ERRORS="$TMP_DIR/biome.current.errors.txt"
FIXED_FILES="$TMP_DIR/biome.fixed_files.txt"
GIT_DIFF_FILES="$TMP_DIR/biome.git_diff.txt"
FIX_REPORT="$TMP_DIR/biome.fix_report.md"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

update_baseline=0
auto_fix=0

# Parse all arguments (support multiple flags)
for arg in "$@"; do
  case "$arg" in
    --update-baseline)
      update_baseline=1
      ;;
    --auto-fix)
      auto_fix=1
      ;;
    --help|-h)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $arg"
      show_help
      exit 1
      ;;
  esac
done

mkdir -p "$FRONTEND_DIR/.ci"

# --- Auto-fix mode: run biome --write --unsafe to auto-correct issues ---
if [[ "$auto_fix" -eq 1 ]]; then
  echo "=== Biome Auto-Fix Mode ==="
  echo "Running: pnpm run lint:write (biome check --write --unsafe ./src)"
  echo

  set +e
  cd "$FRONTEND_DIR"
  pnpm run lint:write 2>&1 | tee "$TMP_DIR/biome.fix_output.log"
  fix_exit=$?
  cd "$ROOT"
  set -e

  # Extract modified files using git diff (more accurate than grep)
  if command -v git &>/dev/null && git rev-parse --git-dir &>/dev/null 2>&1; then
    cd "$FRONTEND_DIR"
    git diff --name-only HEAD 2>/dev/null | sort > "$GIT_DIFF_FILES" || true
    cd "$ROOT"
  else
    # Fallback: extract from biome output
    grep -oE 'apps/[^ ]+|frontend/[^ ]+|src/[^ ]+' "$TMP_DIR/biome.fix_output.log" 2>/dev/null | sort -u > "$GIT_DIFF_FILES" || true
  fi

  # Also capture files that biome reports as fixed
  grep -oE '✓ [^ ]+' "$TMP_DIR/biome.fix_output.log" 2>/dev/null | sed 's/✓ //' >> "$GIT_DIFF_FILES" || true
  sort -u "$GIT_DIFF_FILES" -o "$FIXED_FILES"

  if [[ -s "$FIXED_FILES" ]]; then
    fixed_count=$(wc -l < "$FIXED_FILES" | tr -d ' ')
    echo
    echo "✅ Auto-fix completed. $fixed_count file(s) processed."
    echo
    echo "Modified files:"
    cat "$FIXED_FILES"
  else
    echo
    echo "ℹ️  No files were modified by auto-fix."
  fi

  # Generate fix report in standardized location
  mkdir -p "$REPORTS_DIR"
  TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
  FIX_REPORT="$REPORTS_DIR/auto-fix-${TIMESTAMP}.md"

  cat > "$FIX_REPORT" <<EOF
---
id: REPORT-biome-auto-fix-${TIMESTAMP}
type: REPORT
status: archived
last_verified: $(date -u +"%Y-%m-%d")
---
# Biome Auto-Fix Report

**Date:** $(date -u +"%Y-%m-%dT%H:%M:%SZ")
**Exit Code:** $fix_exit
**Mode:** $(if [[ "$update_baseline" -eq 1 ]]; then echo "auto-fix + update-baseline"; else echo "auto-fix"; fi)

## Summary
- Auto-fix was executed via \`pnpm run lint:write\` (Biome \`--write --unsafe\` on \`./src\`)
- Exit code: $fix_exit

## Modified Files ($fixed_count)
$(if [[ -s "$FIXED_FILES" ]]; then cat "$FIXED_FILES" | sed 's/^/ - /'; else echo "No files were modified."; fi)

## Next Steps
1. Review the changes made by auto-fix
2. Run \`pnpm run lint:gate\` to verify the gate passes
3. If changes are intentional, update baseline: \`pnpm run lint:baseline:update\`
4. Commit the changes

EOF

  echo
  echo "📄 Report saved to: $FIX_REPORT"
  echo

  # Auto-run gate verification after fix
  echo "=== Running Gate Verification ==="
  cd "$FRONTEND_DIR"
  set +e
  pnpm run lint:ci --reporter=json >"$RAW_OUT" 2>&1
  post_fix_exit=$?
  set -e
  cd "$ROOT"

  # Parse diagnostics
  python3 - "$RAW_OUT" "$DIAG_JSON" <<'PY'
import json
import sys
from pathlib import Path

raw_path = Path(sys.argv[1])
json_path = Path(sys.argv[2])

json_line = None
for line in raw_path.read_text(encoding="utf-8", errors="replace").splitlines():
    candidate = line.strip()
    if candidate.startswith("{") and '"summary"' in candidate and '"diagnostics"' in candidate:
        json_line = candidate
        break

if json_line is None:
    json_path.write_text("{}", encoding="utf-8")
    sys.exit(0)

report = json.loads(json_line)
json_path.write_text(json.dumps(report), encoding="utf-8")
PY

  python3 - "$DIAG_JSON" "$CURR_ERRORS" <<'PY'
import json
import sys
from pathlib import Path

diag_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])

if not diag_path.exists():
    out_path.write_text("", encoding="utf-8")
    sys.exit(0)

content = diag_path.read_text(encoding="utf-8", errors="replace").strip()
if not content:
    out_path.write_text("", encoding="utf-8")
    sys.exit(0)

report = json.loads(content)
diagnostics = report.get("diagnostics", [])

entries = set()
for item in diagnostics:
    if item.get("severity") != "error":
        continue
    location = item.get("location", {})
    start = location.get("start", {})
    line = start.get("line", 0)
    column = start.get("column", 0)
    path = location.get("path", "<unknown>")
    category = item.get("category", "<unknown>")
    message = item.get("message", "").replace("\n", " ").strip()
    entries.add(f"{path}:{line}:{column} {category} {message}")

out_path.write_text("\n".join(sorted(entries)) + ("\n" if entries else ""), encoding="utf-8")
PY

  current_count=$(wc -l < "$CURR_ERRORS" | tr -d ' ')

  if [[ "$post_fix_exit" -eq 0 ]]; then
    echo "✅ Gate passed after auto-fix (current errors: $current_count)."
  else
    echo "⚠️  Gate still has errors after auto-fix (current errors: $current_count)."
    echo "   Some issues require manual intervention."
  fi

  # Update baseline if requested
  if [[ "$update_baseline" -eq 1 ]]; then
    cp "$CURR_ERRORS" "$BASELINE_FILE"
    count=$(wc -l <"$BASELINE_FILE" | tr -d ' ')
    echo
    echo "✅ Baseline updated at $BASELINE_FILE ($count entries)."
  fi

  exit $fix_exit
fi

# --- Normal gate mode ---

set +e
pnpm run lint:ci --reporter=json >"$RAW_OUT" 2>&1
biome_exit=$?
set -e

python3 - "$RAW_OUT" "$DIAG_JSON" <<'PY'
import json
import sys
from pathlib import Path

raw_path = Path(sys.argv[1])
json_path = Path(sys.argv[2])

json_line = None
for line in raw_path.read_text(encoding="utf-8", errors="replace").splitlines():
    candidate = line.strip()
    if candidate.startswith("{") and '"summary"' in candidate and '"diagnostics"' in candidate:
        json_line = candidate
        break

if json_line is None:
    json_path.write_text("{}", encoding="utf-8")
    sys.exit(0)

report = json.loads(json_line)
json_path.write_text(json.dumps(report), encoding="utf-8")
PY

python3 - "$DIAG_JSON" "$CURR_ERRORS" <<'PY'
import json
import sys
from pathlib import Path

diag_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])

if not diag_path.exists():
    out_path.write_text("", encoding="utf-8")
    sys.exit(0)

content = diag_path.read_text(encoding="utf-8", errors="replace").strip()
if not content:
    out_path.write_text("", encoding="utf-8")
    sys.exit(0)

report = json.loads(content)
diagnostics = report.get("diagnostics", [])

entries = set()
for item in diagnostics:
    if item.get("severity") != "error":
        continue
    location = item.get("location", {})
    start = location.get("start", {})
    line = start.get("line", 0)
    column = start.get("column", 0)
    path = location.get("path", "<unknown>")
    category = item.get("category", "<unknown>")
    message = item.get("message", "").replace("\n", " ").strip()
    entries.add(f"{path}:{line}:{column} {category} {message}")

out_path.write_text("\n".join(sorted(entries)) + ("\n" if entries else ""), encoding="utf-8")
PY

if [[ "$update_baseline" -eq 1 ]]; then
  cp "$CURR_ERRORS" "$BASELINE_FILE"
  count=$(wc -l <"$BASELINE_FILE" | tr -d ' ')
  echo "Updated frontend Biome baseline at $BASELINE_FILE ($count entries)."
  exit 0
fi

if [[ ! -f "$BASELINE_FILE" ]]; then
  echo "Missing baseline file: $BASELINE_FILE"
  echo "Run: pnpm run lint:baseline:update"
  exit 1
fi

NEW_ERRORS="$TMP_DIR/biome.new.errors.txt"
comm -23 "$CURR_ERRORS" "$BASELINE_FILE" >"$NEW_ERRORS" || true

new_count=$(wc -l <"$NEW_ERRORS" | tr -d ' ')
current_count=$(wc -l <"$CURR_ERRORS" | tr -d ' ')
baseline_count=$(wc -l <"$BASELINE_FILE" | tr -d ' ')

# --- Changed file blocking logic ---
CHANGED_FILES_LIST="$TMP_DIR/changed_files.txt"
if git rev-parse --git-dir > /dev/null 2>&1; then
  git diff --name-only HEAD > "$CHANGED_FILES_LIST" || true
  # staged changes도 포함
  git diff --name-only --cached >> "$CHANGED_FILES_LIST" || true
  sort -u "$CHANGED_FILES_LIST" -o "$CHANGED_FILES_LIST"
else
  touch "$CHANGED_FILES_LIST"
fi

BLOCKING_CHANGED_ERRORS="$TMP_DIR/biome.blocking.changed.errors.txt"
touch "$BLOCKING_CHANGED_ERRORS"

# Biome paths in CURR_ERRORS are relative to the project root or frontend dir.
# Normalize paths to match git diff output.
while read -r error_line; do
    error_path=$(echo "$error_line" | cut -d: -f1)
    # Check if error_path is in CHANGED_FILES_LIST
    # We use grep with word boundaries or exact match to avoid partial matches
    if grep -qF "$error_path" "$CHANGED_FILES_LIST"; then
        echo "$error_line" >> "$BLOCKING_CHANGED_ERRORS"
    fi
done < "$CURR_ERRORS"

blocking_changed_count=$(wc -l <"$BLOCKING_CHANGED_ERRORS" | tr -d ' ')

if [[ "$new_count" -gt 0 ]]; then
  echo "❌ New Biome errors detected against baseline ($new_count new)."
  echo "   Current: $current_count, Baseline: $baseline_count"
  echo
  echo "New errors:"
  cat "$NEW_ERRORS"
  echo
  # Task 3.1 (JUST-BIOME-01): 고유 파일 경로 요약 (≤10줄)
  echo "Affected files (unique paths):"
  cut -d: -f1 "$NEW_ERRORS" | sort -u | head -n 10
  echo
  exit 1
fi

if [[ "$blocking_changed_count" -gt 0 ]]; then
  echo "❌ Biome errors detected in changed files ($blocking_changed_count blocking)."
  echo "   Policy: Files modified in this session must be free of lint errors (SSOT: AGENTS.md 검증 매트릭스, .agents/core/verification.md)."
  echo
  echo "Blocking errors in changed files:"
  cat "$BLOCKING_CHANGED_ERRORS"
  echo
  exit 1
fi

echo "✅ Biome baseline gate passed (current: $current_count, baseline: $baseline_count, new: 0, blocking: 0)."

# --- Output summary for verify report ---
SUMMARY_JSON="$ROOT/artifacts/verify/verify-biome-summary.json"
mkdir -p "$(dirname "$SUMMARY_JSON")"
cat > "$SUMMARY_JSON" <<EOF
{
  "gate": "biome",
  "current": $current_count,
  "baseline": $baseline_count,
  "new": $new_count,
  "blocking": $blocking_changed_count
}
EOF

if [[ "$biome_exit" -ne 0 ]]; then
  echo "⚠️  Note: existing baseline Biome errors remain in untouched files."
fi

exit 0
