#!/bin/bash

# AidenGame Verification Common Utilities
# Included by verify.sh and modules

set -euo pipefail

# --- Paths ---
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
ROOT="${ROOT:-$(pwd)}"
export ROOT
FRONTEND="$ROOT/apps/renderer"
RESULT_JSON_PATH="$ROOT/artifacts/verify/verify-last-result.json"
PYTEST_LOG_PATH="$ROOT/artifacts/verify/.verify-pytest-last.log"
PYTEST_FAILURES_PATH="$ROOT/artifacts/verify/verify-pytest-failures.txt"
STEP_LOG_PATH="$ROOT/artifacts/verify/.verify-step-last.log"
mkdir -p "$ROOT/artifacts/verify"
export VERIFY_TMP_DIR=""

# Merge ``DATABASE_URL`` from repo ``.env`` only (never ``source`` full .env: would break Settings e.g. ALLOWED_ORIGINS JSON).
verify_merge_database_url_from_dotenv() {
    if [ -n "${DATABASE_URL:-}" ]; then
        return 0
    fi
    if [ -f "$ROOT/.env" ]; then
        local from_file
        from_file="$(python3 "$ROOT/scripts/verify/read_dotenv_key.py" "$ROOT/.env" DATABASE_URL)"
        if [ -n "${from_file:-}" ]; then
            export DATABASE_URL="$from_file"
        fi
    fi
}

# --- Timeout wrapper (timeout → gtimeout on macOS) ---
verify_timeout_cmd() {
    local secs="$1"
    shift
    if command -v timeout >/dev/null 2>&1; then
        timeout "$secs" "$@"
    elif command -v gtimeout >/dev/null 2>&1; then
        gtimeout "$secs" "$@"
    else
        echo -e "\033[0;31m[FAIL] timeout/gtimeout not found\033[0m" >&2
        return 127
    fi
}

# --- DB Isolation Setup (PostgreSQL: DATABASE_URL / .env.example SSOT) ---
setup_db_isolation() {
    echo -e "\033[0;90m[Isolation] Setting up verify-only PostgreSQL database...\033[0m"
    verify_merge_database_url_from_dotenv
    VERIFY_TMP_DIR=$(mktemp -d -t emr-verify-XXXXXX)
    VERIFY_PG_DATABASE="emr_verify_${RANDOM}_$$"
    export VERIFY_PG_DATABASE

    if ! command -v createdb >/dev/null 2>&1; then
        echo -e "\033[0;31m[FAIL] createdb not found. Install PostgreSQL client tools.\033[0m"
        rm -rf "$VERIFY_TMP_DIR"
        exit 1
    fi

    # shellcheck disable=SC1090
    eval "$(python3 "$ROOT/scripts/verify/resolve_verify_database_env.py" "$VERIFY_PG_DATABASE")"

    if [ -n "${VERIFY_PG_PASSWORD:-}" ]; then
        export PGPASSWORD="$VERIFY_PG_PASSWORD"
    else
        unset PGPASSWORD || true
    fi

    if ! verify_timeout_cmd 30 createdb -h "$VERIFY_PG_HOST" -p "$VERIFY_PG_PORT" -U "$VERIFY_PG_USER" "$VERIFY_PG_DATABASE" 2>/dev/null; then
        echo -e "\033[0;31m[FAIL] createdb failed for ${VERIFY_PG_DATABASE} (PostgreSQL 가동·CREATEDB·DATABASE_URL·.env 확인).\033[0m"
        rm -rf "$VERIFY_TMP_DIR"
        exit 1
    fi

    echo -e "  DATABASE_URL: \033[0;32m$DATABASE_URL\033[0m"

    trap cleanup_db_isolation EXIT INT TERM
}

cleanup_db_isolation() {
    if [ -n "${VERIFY_PG_DATABASE:-}" ] && command -v dropdb >/dev/null 2>&1; then
        echo -e "\n\033[0;90m[Isolation] Dropping verify database ${VERIFY_PG_DATABASE}...\033[0m"
        if [ -n "${VERIFY_PG_PASSWORD:-}" ]; then
            export PGPASSWORD="$VERIFY_PG_PASSWORD"
        else
            unset PGPASSWORD || true
        fi
        dropdb -h "${VERIFY_PG_HOST:-127.0.0.1}" -p "${VERIFY_PG_PORT:-5432}" -U "${VERIFY_PG_USER:-postgres}" "$VERIFY_PG_DATABASE" 2>/dev/null || true
    fi
    if [ -n "${VERIFY_TMP_DIR:-}" ] && [ -d "$VERIFY_TMP_DIR" ]; then
        rm -rf "$VERIFY_TMP_DIR"
    fi
}

# --- State Variables ---
VERIFY_STEPS=()
TIMINGS=()

# --- Helper Functions ---

write_step() {
    echo -e "\n\033[0;36m=== $1 ===\033[0m"
}

start_timing() {
    python3 -c "import time; print(int(time.time() * 1000))"
}

stop_timing() {
    local step_name="$1"
    local start_time="$2"
    local end_time
    end_time=$(start_timing)
    local diff=$((end_time - start_time))
    TIMINGS+=("$step_name:$diff")
    echo -e "  \033[0;90m[${diff}ms] $step_name\033[0m"
}

get_step_log_path() {
    local label="$1"
    local safe_name="${label//[^a-zA-Z0-9]/_}"
    echo "$ROOT/artifacts/verify/.verify-step-${safe_name}.log"
}

run_command() {
    "$@"
}

skip_frontend_step() {
    local step_name="$1"
    VERIFY_STEPS+=("$step_name (skipped):true")
    echo -e "  \033[0;33m[SKIP] $step_name (VERIFY_SKIP_FRONTEND_ALL=1)\033[0m"
}

skip_step() {
    local step_name="$1"
    local reason="$2"
    VERIFY_STEPS+=("$step_name (skipped):true")
    echo -e "  \033[0;33m[SKIP] $step_name ($reason)\033[0m"
}

serialize_state() {
    VERIFY_STEPS_STR=$(printf "%s|" "${VERIFY_STEPS[@]}")
    TIMINGS_STR=$(printf "%s|" "${TIMINGS[@]}")
}

fail_verify() {
    local exit_code="$1"
    local step_name="$2"
    # shellcheck disable=SC2124
    local pytest_failed_tests="${3:-}"

    # Mark last step as failed in internal state
    local last_idx=$((${#VERIFY_STEPS[@]} - 1))
    if [ "$last_idx" -ge 0 ]; then
        VERIFY_STEPS["$last_idx"]="${step_name}:false"
    fi

    serialize_state
    if command -v save_verify_result >/dev/null; then
        save_verify_result "$exit_code" "$step_name" "$pytest_failed_tests"
    fi
    exit "$exit_code"
}
