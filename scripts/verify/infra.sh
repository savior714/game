#!/bin/bash

# AidenGame Verification Infrastructure & Dependency Checks
# Included by verify.sh

should_run_env_check() {
    if [ "${VERIFY_ENV_CHECK:-auto}" = "1" ]; then return 0; fi
    if [ "${VERIFY_ENV_CHECK:-auto}" = "0" ]; then return 1; fi
    if [ "${CI:-}" = "true" ] || [ "${VERIFY_MODE:-auto}" = "full" ]; then return 0; fi
    if [ "${VERIFY_AGENT_LOOP:-1}" = "1" ]; then return 1; fi
    return 0
}

check_version() {
    local cmd="$1"
    local min_ver_major="$2"
    local min_ver_minor="$3"
    local tool_name="$4"
    
    local version_output
    version_output=$($cmd --version 2>&1 | head -n 1) || true
    local current_ver
    current_ver=$(echo "$version_output" | grep -oE "[0-9]+\.[0-9]+(\.[0-9]+)?" || echo "unknown")
    
    if [ "$current_ver" = "unknown" ]; then
        echo -e "\033[0;31m[FAIL]\033[0m $tool_name not found or version detection failed."
        return 1
    fi
    
    local current_major
    current_major=$(echo "$current_ver" | cut -d. -f1)
    local current_minor
    current_minor=$(echo "$current_ver" | cut -d. -f2)
    current_minor=${current_minor:-0}
    
    if [ "$current_major" -lt "$min_ver_major" ]; then
        echo -e "\033[0;31m[FAIL]\033[0m $tool_name version: $current_ver (Required: ${min_ver_major}.${min_ver_minor}+)"
        return 1
    elif [ "$current_major" -eq "$min_ver_major" ] && [ "$current_minor" -lt "$min_ver_minor" ]; then
        echo -e "\033[0;31m[FAIL]\033[0m $tool_name version: $current_ver (Required: ${min_ver_major}.${min_ver_minor}+)"
        return 1
    fi
    
    echo -e "\033[0;32m[OK]\033[0m $tool_name: $current_ver"
    return 0
}

_valkey_reachable() {
    if command -v valkey-cli >/dev/null 2>&1; then
        valkey-cli -h 127.0.0.1 -p 6379 ping >/dev/null 2>&1 && return 0
    elif command -v redis-cli >/dev/null 2>&1; then
        redis-cli -h 127.0.0.1 -p 6379 ping >/dev/null 2>&1 && return 0
    elif python3 -c "import socket; s = socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', 6379))" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

_vault_reachable() {
    curl -sf "http://127.0.0.1:8200/v1/sys/health" >/dev/null 2>&1
}

verify_dependencies() {
    local errors=0
    echo -e "\n\033[0;36m=== Dependency Version Check ===\033[0m"
    
    check_version "python3.14" "3" "14" "Python" || errors=$((errors + 1))
    check_version "node" "20" "0" "Node.js" || errors=$((errors + 1))
    check_version "pnpm" "9" "0" "pnpm" || errors=$((errors + 1))
    
    local valkey_cmd=""
    if command -v valkey-server >/dev/null 2>&1; then valkey_cmd=$(command -v valkey-server)
    elif [ -x "/opt/homebrew/bin/valkey-server" ]; then valkey_cmd="/opt/homebrew/bin/valkey-server"; fi
    
    if [ -n "$valkey_cmd" ]; then
        check_version "$valkey_cmd" "8" "0" "Valkey" || errors=$((errors + 1))
    elif [ "${CI:-}" = "true" ] && _valkey_reachable; then
        echo -e "\033[0;32m[OK]\033[0m Valkey: reachable on localhost:6379 (Docker service)"
    else
        echo -e "\033[0;31m[FAIL]\033[0m Valkey (valkey-server) not found. Install: brew install valkey"
        errors=$((errors + 1))
    fi
    
    if command -v bao >/dev/null 2>&1; then
        check_version "bao" "2" "0" "OpenBao" || errors=$((errors + 1))
    elif [ "${CI:-}" = "true" ] && _vault_reachable; then
        echo -e "\033[0;32m[OK]\033[0m Vault: reachable on localhost:8200 (Docker service)"
    else
        check_version "bao" "2" "0" "OpenBao" || errors=$((errors + 1))
    fi

    # Pyx Registry Check (Task 2)
    if ! check_pyx_registry; then
        errors=$((errors + 1))
    fi
    
    if [ $errors -gt 0 ]; then
        echo -e "\n\033[0;31m[ERROR]\033[0m Dependency version check failed."
        return 1
    fi
    return 0
}

check_pyx_registry() {
    echo -e "\033[0;90m[Registry] Checking Pyx status...\033[0m"
    # Try reaching Pyx registry with timeout
    if curl -I -s --connect-timeout 2 https://pyx.dev/index > /dev/null 2>&1; then
        echo -e "  \033[0;32m[OK]\033[0m Pyx Registry (https://pyx.dev) is available"
        return 0
    else
        echo -e "  \033[0;31m[FAIL]\033[0m Pyx Registry is unreachable. Package installation may fail."
        return 1
    fi
}

check_infrastructure_health() {
    local errors=0
    echo -e "\n\033[0;36m=== Infrastructure Health Check ===\033[0m"

    # PostgreSQL (verify 격리 DB·pytest 공통; 호스트는 DATABASE_URL에서 해석된 VERIFY_PG_* 우선)
    local pg_host="${VERIFY_PG_HOST:-localhost}"
    local pg_port="${VERIFY_PG_PORT:-5432}"
    local pg_up=0
    if command -v pg_isready >/dev/null 2>&1; then
        if pg_isready -h "$pg_host" -p "$pg_port" >/dev/null 2>&1; then pg_up=1; fi
    elif PG_SOCK_HOST="$pg_host" PG_SOCK_PORT="$pg_port" python3 -c "import os, socket; h=os.environ['PG_SOCK_HOST']; p=int(os.environ['PG_SOCK_PORT']); s=socket.socket(); s.settimeout(2); s.connect((h, p))" >/dev/null 2>&1; then
        pg_up=1
    fi
    if [ $pg_up -eq 1 ]; then
        echo -e "  \033[0;32m[OK]\033[0m PostgreSQL is reachable on ${pg_host}:${pg_port}"
    else
        echo -e "  \033[0;31m[FAIL]\033[0m PostgreSQL is not reachable on ${pg_host}:${pg_port} (pg_isready 또는 소켓 확인 실패)"
        errors=$((errors + 1))
    fi

    local kv_up=0
    if command -v valkey-cli >/dev/null 2>&1; then
        if valkey-cli -h localhost -p 6379 ping >/dev/null 2>&1; then kv_up=1; fi
    elif command -v redis-cli >/dev/null 2>&1; then
        if redis-cli -h localhost -p 6379 ping >/dev/null 2>&1; then kv_up=1; fi
    else
        if python3 -c "import socket; s = socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', 6379))" >/dev/null 2>&1; then kv_up=1; fi
    fi

    if [ $kv_up -eq 1 ]; then
        echo -e "  \033[0;32m[OK]\033[0m Valkey (KV-Store) is up on localhost:6379"
    else
        echo -e "  \033[0;31m[FAIL]\033[0m Valkey (KV-Store) is not responding on localhost:6379"
        echo -e "  \033[0;90m[HINT] Start valkey-server (e.g. brew services start valkey). run_dev.sh no longer falls back to redis-server.\033[0m"
        errors=$((errors + 1))
    fi

    if [ $errors -gt 0 ]; then
        echo -e "\n\033[0;31m[ABORT]\033[0m Infrastructure services are down."
        return 1
    fi
    return 0
}
