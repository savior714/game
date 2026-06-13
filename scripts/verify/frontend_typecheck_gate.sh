#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ -d "$ROOT/apps/renderer" ]]; then
  FRONTEND_DIR="$ROOT/apps/renderer"
else
  FRONTEND_DIR="$ROOT/frontend"
fi
BASELINE_FILE="$FRONTEND_DIR/.ci/typecheck-baseline.txt"
TMP_DIR="$(mktemp -d)"
RAW_OUT="$TMP_DIR/typecheck.raw.log"
CURR_ERRORS="$TMP_DIR/typecheck.current.errors.txt"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

update_baseline=0
if [[ "${1:-}" == "--update-baseline" ]]; then
  update_baseline=1
fi

mkdir -p "$FRONTEND_DIR/.ci"

set +e
cd "$FRONTEND_DIR"
pnpm run typecheck:strict >"$RAW_OUT" 2>&1
typecheck_exit=$?
cd "$ROOT"
set -e

if [[ "$typecheck_exit" -ne 0 ]]; then
  rg "^.+\\([0-9]+,[0-9]+\\): error TS[0-9]+: .+$" "$RAW_OUT" --no-line-number | sort -u >"$CURR_ERRORS" || true
else
  : >"$CURR_ERRORS"
fi

if [[ "$update_baseline" -eq 1 ]]; then
  cp "$CURR_ERRORS" "$BASELINE_FILE"
  count=$(wc -l <"$BASELINE_FILE" | tr -d ' ')
  echo "Updated frontend typecheck baseline at $BASELINE_FILE ($count entries)."
  exit 0
fi

if [[ ! -f "$BASELINE_FILE" ]]; then
  echo "Missing baseline file: $BASELINE_FILE"
  echo "Run: pnpm run typecheck:baseline:update"
  exit 1
fi

NEW_ERRORS="$TMP_DIR/typecheck.new.errors.txt"
comm -23 "$CURR_ERRORS" "$BASELINE_FILE" >"$NEW_ERRORS" || true

new_count=$(wc -l <"$NEW_ERRORS" | tr -d ' ')
current_count=$(wc -l <"$CURR_ERRORS" | tr -d ' ')
baseline_count=$(wc -l <"$BASELINE_FILE" | tr -d ' ')

# --- Changed file blocking logic ---
CHANGED_FILES_LIST="$TMP_DIR/changed_files.txt"
if git rev-parse --git-dir > /dev/null 2>&1; then
  git diff --name-only HEAD > "$CHANGED_FILES_LIST" || true
  git diff --name-only --cached >> "$CHANGED_FILES_LIST" || true
  sort -u "$CHANGED_FILES_LIST" -o "$CHANGED_FILES_LIST"
else
  touch "$CHANGED_FILES_LIST"
fi

BLOCKING_CHANGED_ERRORS="$TMP_DIR/typecheck.blocking.changed.errors.txt"
touch "$BLOCKING_CHANGED_ERRORS"

while read -r error_line; do
    # Typecheck paths are like: src/components/ui/button.tsx(10,5)
    error_path=$(echo "$error_line" | cut -d\( -f1)
    if grep -qF "$error_path" "$CHANGED_FILES_LIST"; then
        echo "$error_line" >> "$BLOCKING_CHANGED_ERRORS"
    fi
done < "$CURR_ERRORS"

blocking_changed_count=$(wc -l <"$BLOCKING_CHANGED_ERRORS" | tr -d ' ')

if [[ "$new_count" -gt 0 ]]; then
  echo "❌ New TypeScript errors detected against baseline ($new_count new)."
  echo "   Current: $current_count, Baseline: $baseline_count"
  echo
  cat "$NEW_ERRORS"
  exit 1
fi

if [[ "$blocking_changed_count" -gt 0 ]]; then
  echo "❌ TypeScript errors detected in changed files ($blocking_changed_count blocking)."
  echo "   Policy: Files modified in this session must be free of type errors."
  echo
  cat "$BLOCKING_CHANGED_ERRORS"
  exit 1
fi

echo "Typecheck baseline gate passed (current: $current_count, baseline: $baseline_count, new: 0)."

# --- Output summary for verify report ---
SUMMARY_JSON="$ROOT/artifacts/verify/verify-typecheck-summary.json"
mkdir -p "$(dirname "$SUMMARY_JSON")"
cat > "$SUMMARY_JSON" <<EOF
{
  "gate": "typecheck",
  "current": $current_count,
  "baseline": $baseline_count,
  "new": $new_count,
  "blocking": $blocking_changed_count
}
EOF

if [[ "$typecheck_exit" -ne 0 ]]; then
  echo "Note: existing baseline errors remain; no regression detected."
fi

exit 0
