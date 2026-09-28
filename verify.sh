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
    local changed_files unstaged_files staged_files test_files_changed code_files_changed no_assert_files file

    if ! unstaged_files="$(git diff --name-only "$TDD_GATE_BASE_REF" 2>&1)"; then
        echo "[ERROR] TDD Gate could not read unstaged changes for base: $TDD_GATE_BASE_REF" >&2
        printf '%s\n' "$unstaged_files" >&2
        return 1
    fi

    if ! staged_files="$(git diff --name-only --cached "$TDD_GATE_BASE_REF" 2>&1)"; then
        echo "[ERROR] TDD Gate could not read staged changes for base: $TDD_GATE_BASE_REF" >&2
        printf '%s\n' "$staged_files" >&2
        return 1
    fi

    changed_files="$(printf '%s\n%s\n' "$unstaged_files" "$staged_files" | sed '/^$/d' | sort -u)"

    if [[ -z "$(printf '%s\n' "$changed_files" | sed '/^$/d')" ]]; then
        echo -e "\033[0;90m[TDD Gate] no changed files; skipping diff checks\033[0m"
        return
    fi

    test_files_changed="$(printf '%s\n' "$changed_files" | rg '^tests/.*\.py$' || true)"
    # Runtime files and executable Python tooling require accompanying test changes.
    code_files_changed="$(printf '%s\n' "$changed_files" | rg \
        '^(domains|shared|experiments|guardian|admin)/.*\.(js|html|css)$|^(scripts|tools)/.*\.py$|^[A-Za-z0-9_.-]+\.(js|html|css)$' || true)"

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
    elif command -v uv >/dev/null 2>&1; then
        uv run ruff check tests scripts/verify_korean_text.py tools/mcp_call_wrapper.py
        uv run ruff format --check tests scripts/verify_korean_text.py tools/mcp_call_wrapper.py
    elif command -v ruff >/dev/null 2>&1; then
        ruff check tests scripts/verify_korean_text.py tools/mcp_call_wrapper.py
        ruff format --check tests scripts/verify_korean_text.py tools/mcp_call_wrapper.py
    else
        echo -e "\033[0;31m[ERROR] required lint tool unavailable: install just, uv, or ruff\033[0m" >&2
        return 1
    fi
}

CORE_POLICY_TESTS=(
    "tests/test_active_product_scope_policy.py"
    "tests/test_core_agent_contract_consistency.py"
    "tests/test_auxiliary_core_contract_consistency.py"
    "tests/test_document_authority_classification.py"
    "tests/test_git_workflow_guardrails.py"
    "tests/test_readme_identity.py"
    "tests/test_verification_pipeline_guardrails.py"
)

run_tests() {
    echo -e "\n\033[0;36m=== Tests ===\033[0m"

    if [[ "${VERIFY_ALL_TESTS:-0}" == "1" || "${1:-}" == "--all" ]]; then
        echo -e "\033[0;33m[Running full test suite (all tests, timeout=60s)]\033[0m"
        if command -v uv >/dev/null 2>&1; then
            uv run pytest -m "" -o "addopts=-q --timeout=60" tests
        elif command -v pytest >/dev/null 2>&1; then
            PYTHONPATH=. pytest -m "" -o "addopts=-q --timeout=60" tests
        else
            echo -e "\033[0;31m[ERROR] required test tool unavailable: install uv or pytest\033[0m" >&2
            return 1
        fi
        return
    fi

    local target_tests=()
    for test_file in "${CORE_POLICY_TESTS[@]}"; do
        if [[ -f "$test_file" ]]; then
            target_tests+=("$test_file")
        fi
    done

    # Collect changed test files if TDD gate was skipped or did not set CHANGED_TEST_FILES
    local changed_tests="${CHANGED_TEST_FILES:-}"
    if [[ -z "$changed_tests" && "$TDD_GATE_ENABLED" != "1" ]]; then
        changed_tests="$(git diff --name-only "$TDD_GATE_BASE_REF" 2>/dev/null | rg '^tests/.*\.py$' || true)"
    fi

    if [[ -n "$changed_tests" ]]; then
        while IFS= read -r file; do
            [[ -z "$file" || ! -f "$file" ]] && continue
            local duplicate=0
            for existing in "${target_tests[@]}"; do
                if [[ "$existing" == "$file" ]]; then
                    duplicate=1
                    break
                fi
            done
            if [[ "$duplicate" -eq 0 ]]; then
                target_tests+=("$file")
            fi
        done <<< "$changed_tests"
    fi

    echo -e "\033[0;32m[Running essential tests: ${#target_tests[@]} file(s)]\033[0m"
    for t in "${target_tests[@]}"; do
        echo -e "  - \033[0;90m$t\033[0m"
    done

    if command -v uv >/dev/null 2>&1; then
        uv run pytest -o "addopts=-q --timeout=30" "${target_tests[@]}"
    elif command -v pytest >/dev/null 2>&1; then
        PYTHONPATH=. pytest -o "addopts=-q --timeout=30" "${target_tests[@]}"
    else
        echo -e "\033[0;31m[ERROR] required test tool unavailable: install uv or pytest\033[0m" >&2
        return 1
    fi
}

run_korean_check() {
    echo -e "\n\033[0;36m=== Korean Text Check (Quantization Artifacts) ===\033[0m"
    if command -v uv >/dev/null 2>&1; then
        uv run python scripts/verify_korean_js.py --all
    elif command -v python3 >/dev/null 2>&1; then
        PYTHONPATH=. python3 scripts/verify_korean_js.py --all
    else
        echo -e "\033[0;31m[ERROR] required Python runtime unavailable: install uv or python3\033[0m" >&2
        return 1
    fi
}

tdd_gate_check
run_lint
run_korean_check
run_tests "${@:-}"

echo -e "\n\033[0;32m✅ AidenGame verification complete.\033[0m"
