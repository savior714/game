#!/bin/bash

# AidenGame Verification Mode Configuration
# Included by verify.sh

configure_verify_mode() {
    # 1. Detect Tier automatically if VERIFY_TIER is not set
    if [ -z "${VERIFY_TIER:-}" ]; then
        export VERIFY_TIER=$(python3 scripts/detect_tier.py)
    fi
    
    # RISK-06: Consultation 경로 변경 시 L2 강제 (의료 기록 SSOT — 단순 린트(L1) 불충분)
    if [ "$VERIFY_TIER" != "L2" ] && [ "$VERIFY_TIER" != "L3" ]; then
        local changed
        changed="$(git status --porcelain 2>/dev/null || true)"
        if echo "$changed" | grep -qE "apps/renderer/src/components/consultation/"; then
            echo -e "  \\033[1;33m[RISK-06]\\033[0m Consultation path changed — forcing L2 verification."
            export VERIFY_TIER="L2"
        fi
    fi
    
    echo -e "  Tier: \033[0;32m$VERIFY_TIER\033[0m"

    # 2. Set default VERIFY_MODE based on Tier
    if [ -z "${VERIFY_MODE:-}" ]; then
        case "$VERIFY_TIER" in
            L1) export VERIFY_MODE="quick" ;;
            L2) export VERIFY_MODE="auto" ;;
            L3) export VERIFY_MODE="full" ;;
            *)  export VERIFY_MODE="agent" ;;
        esac
    fi
    
    case "$VERIFY_MODE" in
        agent|auto|quick|full)
            ;;
        *)
            echo -e "\033[0;31m[ERROR] Invalid VERIFY_MODE: $VERIFY_MODE\033[0m"
            exit 1
            ;;
    esac

    # agent mode: optimized defaults for end-of-task loop
    if [ "$VERIFY_MODE" = "agent" ]; then
        export VERIFY_SKIP_FRONTEND_BUILD=1
        export VERIFY_TEST_STRATEGY=${VERIFY_TEST_STRATEGY:-fast}
        VERIFY_MODE="auto"
    fi

    # quick mode: prioritize fast feedback loop
    if [ "$VERIFY_MODE" = "quick" ]; then
        export VERIFY_SKIP_FRONTEND_BUILD=1
        export VERIFY_TEST_STRATEGY=${VERIFY_TEST_STRATEGY:-fast}
    fi

    # Prepare execution flags (honour CI/workflow overrides set before configure_verify_mode)
    RUN_FRONTEND=${RUN_FRONTEND:-1}
    RUN_BACKEND=${RUN_BACKEND:-1}
    RUN_DOCS=${RUN_DOCS:-1}
    RUN_PYTEST=${RUN_PYTEST:-1}
    SKIP_FRONTEND_BUILD=${VERIFY_SKIP_FRONTEND_BUILD:-0}
    SKIP_FRONTEND_ALL=${VERIFY_SKIP_FRONTEND_ALL:-0}

    # Tier-based overrides
    if [ "$VERIFY_TIER" = "L1" ]; then
        RUN_PYTEST=0
        RUN_DOCS=0
        SKIP_FRONTEND_BUILD=1
    elif [ "$VERIFY_TIER" = "L2" ]; then
        export VERIFY_TEST_STRATEGY=${VERIFY_TEST_STRATEGY:-fast}
        RUN_DOCS=0
    fi

    # full mode: force all stages
    if [ "$VERIFY_MODE" = "full" ]; then
        return
    fi

    # auto mode: detect changed files
    if [ "$VERIFY_MODE" = "auto" ]; then
        local changed
        changed="$(git status --porcelain 2>/dev/null || true)"

        if [ -z "$changed" ]; then
            echo -e "  \033[0;93m[AUTO]\033[0m No changes detected; running full verification."
            return
        fi

        local has_frontend=0
        local has_backend=0
        local has_docs=0
        local has_shared=0

        while IFS= read -r line; do
            [ -z "$line" ] && continue
            local path="${line:3}"
            if [[ "$path" == apps/renderer/* ]]; then has_frontend=1
            elif [[ "$path" == src/* ]] || [[ "$path" == tests/* ]]; then has_backend=1
            elif [[ "$path" == docs/* ]]; then has_docs=1
            elif [[ "$path" == "verify.sh" ]] || [[ "$path" == "pyproject.toml" ]] || [[ "$path" == "uv.lock" ]] || [[ "$path" == "package.json" ]] || [[ "$path" == ".mcp.json" ]] || [[ "$path" == scripts/verify/* ]]; then
                has_shared=1
            elif [[ "$path" == *.md ]]; then has_docs=1
            else has_shared=1; fi
        done <<< "$changed"

        if [ "$has_shared" -eq 1 ]; then return; fi

        RUN_FRONTEND=$has_frontend
        RUN_BACKEND=$has_backend
        RUN_DOCS=$has_docs
        RUN_PYTEST=$has_backend

        if [ "$RUN_FRONTEND" -eq 0 ]; then SKIP_FRONTEND_ALL=1; fi
        if [ "$RUN_BACKEND" -eq 0 ]; then RUN_PYTEST=0; fi
    fi
}
