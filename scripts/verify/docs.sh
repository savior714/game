#!/bin/bash

# AidenGame Documentation Verification
# Included by verify.sh

run_docs_steps() {
    if [ "$RUN_DOCS" -eq 1 ]; then
        # HTML structure check
        local label="Docs: HTML structure check"
        VERIFY_STEPS+=("$label:true")
        write_step "$label"
        local start_time
        start_time=$(start_timing)
        local ok=true

        for f in $(find docs/agent-context/audit -name "*.html" 2>/dev/null); do
            for tag in "div" "table"; do
                local open close
                open=$(grep -oE "<$tag[^>]*(/)?>|<$tag>" "$f" | wc -l)
                close=$(grep -o "</$tag>" "$f" | wc -l)
                if [ "$open" -ne "$close" ]; then
                    echo -e "  - mismatch $tag: $open vs $close in $(basename "$f")"
                    ok=false
                fi
            done
        done

        if [ "$ok" = "false" ]; then
            stop_timing "$label" "$start_time"
            fail_verify 1 "$label" ""
        fi
        stop_timing "$label" "$start_time"
        serialize_state
        save_verify_result 0 "" ""

        # Korean text hallucination check (custom handling for exit codes)
        # Strict Mode: WARNING(exit 2)도 CI 실패로 처리 (PR 병합 차단)
        # NOTE: verify는 한자·일본어·모지바케 FAIL만 검사 (--no-english-detect).
        #       영문 단락()은 `just session-gate` / session_language_gate.py 가 담당.
        local korean_out="${ROOT}/artifacts/verify/verify-korean-text-output.txt"
        label="Docs: Korean text hallucination check"
        VERIFY_STEPS+=("$label:true")
        write_step "$label"
        start_time=$(start_timing)
        korean_exit=0
        python3 scripts/verify_korean_text.py --dir docs --no-english-detect --output artifacts/verify/verify-korean-text-result.json > "$korean_out" 2>&1 || korean_exit=$?
        
        # Strict Mode Configuration
        KOREAN_TEXT_STRICT_MODE=${KOREAN_TEXT_STRICT_MODE:-1}
        
        # Exit code handling: 0=PASS, 1=FAIL, 2=WARNING
        if [ "$korean_exit" -eq 0 ]; then
            echo -e "  \033[0;32m[OK]\033[0m Korean text check: PASS"
        elif [ "$korean_exit" -eq 1 ]; then
            echo -e "  \033[0;31m[FAIL]\033[0m Korean text check: FAIL (명확한 오염 발견)"
            cat "$korean_out"
            stop_timing "$label" "$start_time"
            fail_verify 1 "$label" ""
        elif [ "$korean_exit" -eq 2 ]; then
            if [ "$KOREAN_TEXT_STRICT_MODE" -eq 1 ]; then
                # Strict Mode: WARNING도 CI 실패로 처리 (PR 병합 차단)
                echo -e "  \033[0;31m[FAIL]\033[0m Korean text check: FAIL (의심 패턴 발견 - 엄격 모드)"
                cat "$korean_out"
                stop_timing "$label" "$start_time"
                fail_verify 2 "$label" ""
            else
                # Loose Mode: WARNING만 표시
                echo -e "  \033[0;33m[WARNING]\033[0m Korean text check: WARNING (의심 패턴 발견 - 사용자 확인 필요)"
                cat "$korean_out"
                echo "KOREAN_TEXT_WARNING=1" > "$ROOT/.korean-text-warning"
            fi
        else
            echo -e "  \033[0;31m[ERROR]\033[0m Korean text check: unexpected exit code $korean_exit"
            cat "$korean_out"
            stop_timing "$label" "$start_time"
            fail_verify "$korean_exit" "$label" ""
        fi
        stop_timing "$label" "$start_time"
        serialize_state
        save_verify_result 0 "" ""

        # YAML frontmatter gates for converted doc hubs (replaces H2 SSOT scan for specs)
        local yaml_label="Docs: YAML hub frontmatter (active hubs + discussions/agent-context + plans archive)"
        if [ "${CI:-}" = "true" ]; then
            invoke_step "$yaml_label" "" "false" just docs-yaml-hubs
        elif uv run python scripts/verify/docs_yaml_stamp.py check >/dev/null 2>&1; then
            skip_step "$yaml_label" "docs-yaml-stamp valid (lint-turn-end on same HEAD)"
        else
            invoke_step "$yaml_label" "" "false" just docs-yaml-hubs
        fi

        # Dual SSOT header pair must not live under docs/**/reports/** (hub paths only)
        invoke_step "Docs: SSOT path policy (dual-header hubs)" "" "false" uv run python scripts/verify_docs_ssot_path_policy.py

        # Memory index verification
        label="Docs: Memory index verification"
        VERIFY_STEPS+=("$label:true")
        write_step "$label"
        start_time=$(start_timing)
        ok=true

        if [ ! -f "docs/agent-context/memory/MEMORY.md" ]; then
            echo -e "  \033[0;31m[FAIL]\033[0m docs/agent-context/memory/MEMORY.md not found"
            ok=false
        else
            local line_count
            line_count=$(wc -l < "docs/agent-context/memory/MEMORY.md")
            if [ "$line_count" -gt 500 ]; then
                echo -e "  \033[0;31m[FAIL]\033[0m docs/agent-context/memory/MEMORY.md has $line_count lines (max 500)"
                ok=false
            else
                echo -e "  \033[0;32m[OK]\033[0m docs/agent-context/memory/MEMORY.md ($line_count lines)"
            fi
        fi

        if [ "$ok" = "false" ]; then
            stop_timing "$label" "$start_time"
            fail_verify 1 "$label" ""
        fi
        stop_timing "$label" "$start_time"
        serialize_state
        save_verify_result 0 "" ""

        # Plans index integrity check
        invoke_step "Docs: Plans index integrity check" "" "false" python3 scripts/verify_plans_index.py
    else
        skip_step "Docs: HTML structure check" "auto-mode"
        skip_step "Docs: Korean text hallucination check" "auto-mode"
        skip_step "Docs: YAML hub frontmatter (active hubs + discussions/agent-context + plans archive)" "auto-mode"
        skip_step "Docs: SSOT path policy (dual-header hubs)" "auto-mode"
        skip_step "Docs: Memory index verification" "auto-mode"
    fi
}
