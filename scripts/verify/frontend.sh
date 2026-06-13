#!/bin/bash

# AidenGame Frontend Verification
# Included by verify.sh

run_frontend_steps() {
    if [ "$RUN_FRONTEND" -eq 1 ] && [ "$SKIP_FRONTEND_ALL" != "1" ]; then
        if ! command -v pnpm > /dev/null 2>&1; then
            echo -e "\033[0;31m[ERR] pnpm not found. Frontend verification requires pnpm (monorepo root: pnpm-lock.yaml; see README §5).\033[0m"
            exit 1
        fi

        invoke_step "Frontend: Biome (baseline gate)" "$FRONTEND" "true" 300 pnpm run lint:gate
        invoke_step "Frontend: import boundary gate" "$ROOT" "false" 120 uv run python scripts/verify/frontend_boundary_gate.py --check
        invoke_step "Frontend: function length gate" "$ROOT" "false" 120 uv run python scripts/verify/frontend_function_length_gate.py --check
        invoke_step "Frontend: complexity gate" "$ROOT" "false" 180 uv run python scripts/verify/frontend_complexity_gate.py --check
        invoke_step "Frontend: internal mock gate" "$ROOT" "false" 120 uv run python scripts/verify/test_internal_mock_gate.py --check
        invoke_step "Frontend: TypeScript (baseline gate)" "$FRONTEND" "true" 300 pnpm run typecheck
        invoke_step "Frontend: Grid Layout SSOT" "$ROOT" "false" 300 python3 scripts/verify_grid_layout.py

        if [ "$SKIP_FRONTEND_BUILD" != "1" ]; then
            echo -e "  \033[0;90mRunning frontend build (this may take ~1 minute)...\033[0m"
            invoke_step "Frontend: Production build" "$FRONTEND" "false" 300 pnpm run build
        else
            skip_frontend_step "Frontend: Production build"
        fi
    else
        if [ "$RUN_FRONTEND" -eq 0 ]; then
            skip_step "Frontend: Biome (baseline gate)" "auto-mode unaffected by changes"
            skip_step "Frontend: TypeScript (baseline gate)" "auto-mode unaffected by changes"
            skip_step "Frontend: Production build" "auto-mode unaffected by changes"
        else
            skip_frontend_step "Frontend: Biome (baseline gate)"
            skip_frontend_step "Frontend: TypeScript (baseline gate)"
            skip_frontend_step "Frontend: Production build"
            echo -e "  \033[0;33m[SKIP] Frontend: All steps (VERIFY_SKIP_FRONTEND_ALL=1)\033[0m"
        fi
    fi
}
