#!/usr/bin/env bash
# AidenGame local verification — bootstrap kernel (game profile)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo -e "\033[0;36m[AidenGame VERIFY] Starting at $(date)\033[0m"

export TDD_GATE_ENABLED=${TDD_GATE_ENABLED:-1}
export TDD_GATE_BASE_REF=${TDD_GATE_BASE_REF:-HEAD}

tdd_gate_check() {
    if [[ "$TDD_GATE_ENABLED" != "1" ]]; then
        echo -e "\033[0;90m[TDD Gate] skipped\033[0m"
        return
    fi

    echo -e "\n\033[0;36m=== TDD Gate ===\033[0m"
    local changed_files test_files_changed code_files_changed no_assert_files file

    changed_files="$(git diff --name-only "$TDD_GATE_BASE_REF" 2>/dev/null || true)"
    changed_files+=$'\n'"$(git diff --name-only --cached "$TDD_GATE_BASE_REF" 2>/dev/null || true)"
    changed_files="$(printf '%s\n' "$changed_files" | sed '/^$/d' | sort -u)"

    if [[ -z "$(printf '%s\n' "$changed_files" | sed '/^$/d')" ]]; then
        echo -e "\033[0;90m[TDD Gate] no changed files; skipping diff checks\033[0m"
        return
    fi

    test_files_changed="$(printf '%s\n' "$changed_files" | rg '^tests/.*\.py$' || true)"
    # Runtime code lives under the canonical project directories or root entry files.
    code_files_changed="$(printf '%s\n' "$changed_files" | rg \
        '^(domains|shared|experiments|guardian|admin|scripts)/.*\.(js|html|css)$|^[A-Za-z0-9_.-]+\.(js|html|css)$' || true)"

    if [[ -z "$code_files_changed" && -z "$test_files_changed" ]]; then
        echo -e "\033[0;90m[TDD Gate] only docs/config changed; skipping\033[0m"
        return
    fi

    if [[ -n "$code_files_changed" && -z "$test_files_changed" ]]; then
        local existing=""
        while IFS= read -r file; do
            [[ -z "$file" || ! -f "$file" ]] && continue
            existing+="${file}"$'\n'
        done <<< "$code_files_changed"
        if [[ -n "$existing" ]]; then
            echo "❌ TDD Violation: code changed without tests/"
            printf "%s" "$existing"
            exit 1
        fi
    fi

    if [[ -n "$test_files_changed" ]]; then
        no_assert_files=""
        while IFS= read -r file; do
            [[ -z "$file" || ! -f "$file" ]] && continue
            if [[ "$file" == tests/helpers/* || "$(basename "$file")" == "conftest.py" ]]; then
                continue
            fi
            if ! rg -q 'assert |pytest\.raises|self\.assert|expect\(|toBeVisible|toContainText' "$file"; then
                no_assert_files+="${file}"$'\n'
            fi
        done <<< "$test_files_changed"
        if [[ -n "$no_assert_files" ]]; then
            echo "❌ TDD Violation: test without assertion"
            printf "%s" "$no_assert_files"
            exit 1
        fi
    fi

    echo -e "\033[0;32m[TDD Gate] passed\033[0m"
}

run_lint() {
    echo -e "\n\033[0;36m=== Lint ===\033[0m"
    if command -v just >/dev/null 2>&1; then
        just lint
    elif command -v ruff >/dev/null 2>&1; then
        ruff check tests scripts/verify_korean_text.py tools/mcp_call_wrapper.py
        ruff format --check tests scripts/verify_korean_text.py tools/mcp_call_wrapper.py
    else
        echo -e "\033[0;33m[WARN] ruff/just not found; skipping lint\033[0m"
    fi
}

run_tests() {
    echo -e "\n\033[0;36m=== Tests ===\033[0m"
    if command -v just >/dev/null 2>&1; then
        just test
    elif command -v uv >/dev/null 2>&1; then
        uv run pytest tests
    elif command -v pytest >/dev/null 2>&1; then
        PYTHONPATH=. pytest tests
    else
        echo -e "\033[0;33m[WARN] pytest not found; skipping tests\033[0m"
    fi
}

run_korean_check() {
    echo -e "\n\033[0;36m=== Korean Text Check (Quantization Artifacts) ===\033[0m"
    if command -v uv >/dev/null 2>&1; then
        uv run python scripts/verify_korean_js.py --all
    elif command -v python3 >/dev/null 2>&1; then
        PYTHONPATH=. python3 scripts/verify_korean_js.py --all
    else
        echo -e "\033[0;33m[WARN] python/uv not found; skipping Korean check\033[0m"
    fi
}

tdd_gate_check

echo -e "\n\033[0;36m=== PROJECT_RULES.md Directory Sync ===\033[0m"
PROJECT_RULES="PROJECT_RULES.md"
declare -a REQUIRED_DIRS=(
    "index.html"
    "domains/math/"
    "domains/english/"
    "domains/korean/"
    "domains/science/"
    "experiments/space-explorer/"
    "experiments/marble/"
    "shared/domain/"
    "shared/ui/"
    "shared/event-bus.js"
    "domains/reward/"
    "domains/auth/"
    "domains/sync/"
    "tools/"
    "artifacts/"
    "src/"
    "styles.css"
    "verify.sh"
    "bootstrap.sh"
    "vercel.json"
)

MISSING_IN_DOCS=""
for dir in "${REQUIRED_DIRS[@]}"; do
    if [[ -e "$dir" ]]; then
        if ! rg -q "$dir" "$PROJECT_RULES"; then
            MISSING_IN_DOCS+="$dir"$'\n'
        fi
    fi
done

if [[ -n "$MISSING_IN_DOCS" ]]; then
    echo "❌ PROJECT_RULES.md 누락: 실제 존재하지만 문서에 없는 항목"
    printf "%s" "$MISSING_IN_DOCS"
    exit 1
fi

echo -e "\033[0;32m[PROJECT_RULES.md] directory sync passed\033[0m"

run_lint
run_korean_check
run_tests

echo -e "\n\033[0;32m✅ AidenGame verification complete.\033[0m"
