#!/usr/bin/env bash
set -euo pipefail

# Bootstrap Verification Script
# This script enforces TDD and system integrity.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo -e "\033[0;36m[VERIFY] Starting verification...\033[0m"

# 1. TDD Gate Check
tdd_gate_check() {
    echo -e "\033[0;36m[TDD Gate] Checking diffs...\033[0m"
    
    # Get changed files against HEAD (including staged)
    CHANGED_FILES=$(git diff --name-only HEAD || true)
    CHANGED_FILES+=$'\n'$(git diff --name-only --cached HEAD || true)
    CHANGED_FILES=$(echo "$CHANGED_FILES" | sed '/^$/d' | sort -u)

    if [[ -z "$CHANGED_FILES" ]]; then
        echo -e "\033[0;90m[TDD Gate] No changed files detected. Skipping.\033[0m"
        return
    fi

    # Define paths (Adjust according to project structure)
    CODE_FILES=$(echo "$CHANGED_FILES" | grep -E "^(src|app|backend|frontend)/.*\.(py|ts|tsx|js|jsx)$" || true)
    TEST_FILES=$(echo "$CHANGED_FILES" | grep -E "^tests/.*\.py$" || true)

    if [[ -n "$CODE_FILES" && -z "$TEST_FILES" ]]; then
        echo -e "\033[0;31m❌ TDD Violation: Code changed but no test changes found.\033[0m"
        echo -e "Changed code files:\n$CODE_FILES"
        exit 1
    fi

    # Assertion check for new/modified tests
    if [[ -n "$TEST_FILES" ]]; then
        while IFS= read -r file; do
            [[ -z "$file" ]] || [[ ! -f "$file" ]] && continue
            if ! grep -E "assert |pytest\.raises|self\.assert" "$file" > /dev/null; then
                echo -e "\033[0;31m❌ TDD Violation: Test file without assertion: $file\033[0m"
                exit 1
            fi
        done <<< "$TEST_FILES"
    fi

    echo -e "\033[0;32m[TDD Gate] Passed.\033[0m"
}

# 2. Run Tests
run_tests() {
    echo -e "\033[0;36m[TEST] Running pytest...\033[0m"
    if command -v pytest > /dev/null; then
        # Avoid collecting template fixture tests in this bootstrap repository.
        pytest tests
    else
        echo -e "\033[0;33m[WARN] pytest not found. Skipping tests.\033[0m"
    fi
}

# Execution
tdd_gate_check
run_tests

echo -e "\n\033[0;32m✅ Verification complete.\033[0m"
