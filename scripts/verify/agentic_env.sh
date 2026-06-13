#!/bin/bash

# Agentic workflow: EditorConfig + 비정상 공백/스마트 따옴표 검사 (verify.sh)
# Included by verify.sh

run_agentic_env_steps() {
    if [ "${VERIFY_SKIP_AGENTIC_ENV:-0}" = "1" ]; then
        skip_step "Agentic env: EditorConfig & text hygiene" "VERIFY_SKIP_AGENTIC_ENV=1"
        return
    fi

    invoke_step "Agentic env: EditorConfig & text hygiene" "" "false" uv run python scripts/verify_agentic_env.py
}
