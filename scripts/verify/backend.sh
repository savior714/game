#!/bin/bash

# AidenGame Backend Verification
# Included by verify.sh
#
# 대시보드 REST 스모크(Phase 1, `docs/plans/archive/20260419_dashboard_network_followup_blueprint.md` Task 2.1):
# - `tests/test_dashboard_stats_smoke.py`는 `slow`·`integration` 마커가 없어 `VERIFY_TEST_STRATEGY=fast`(기본)의
#   `pytest -m "not slow and not integration"`에 포함된다.
# - 통합 검증(`./verify.sh`)에 별도 셸 스텝을 추가하지 않는다(동일 시나리오의 중복 실행 방지).
#   백엔드 프로세스 기동 후 수동 확인은 `scripts/verify/smoke_dashboard_rest.sh` 또는 `just smoke-dashboard-rest`.
# - 실행되지 않는 경우: `RUN_PYTEST=0`(예: auto 모드에서 백엔드·tests·공유 변경 없음), 또는 `PYTEST_TARGET`이
#   해당 파일을 범위에 두지 않을 때.
# - CI(`CI=true`)에서도 별도 스킵 없음 — Postgres·Valkey 전제는 기존 pytest 단계와 동일.

run_backend_steps() {
    # Repo-root src/ layout: packages are src.api, src.domain, src.infrastructure
    export PYTHONPATH="$ROOT"
    
    if [ "$RUN_BACKEND" -eq 1 ]; then
        local target_python="python3"
        [ -f "$VENV_BIN/python3" ] && target_python="$VENV_BIN/python3"
        
        invoke_step "Backend: compileall" "" "false" 120 "$target_python" -m compileall src
        
        if [ -f "$VENV_BIN/lint-imports" ]; then
            invoke_step "Backend: lint-imports" "" "false" 120 "$VENV_BIN/lint-imports" --config "$ROOT/.importlinter"
        else
            invoke_step "Backend: lint-imports" "" "false" 120 "$target_python" -m importlinter lint --config "$ROOT/.importlinter"
        fi

        local ruff_cmd=("uv" "run" "ruff" "check" "src/")
        if [ "${VERIFY_FIX:-0}" = "1" ]; then
            ruff_cmd+=("--fix" "--unsafe-fixes")
            echo -e "  \033[0;32m[Auto-Fix] Enabling ruff --fix --unsafe-fixes\033[0m"
        fi
        invoke_step "Backend: ruff lint" "" "false" 120 "${ruff_cmd[@]}"
        invoke_step "Backend: import boundary gate" "$ROOT" "false" 120 uv run python scripts/verify/backend_boundary_gate.py --check
        invoke_step "Backend: function length gate" "$ROOT" "false" 120 uv run python scripts/verify/backend_function_length_gate.py --check
        invoke_step "Backend: vulture dead code" "" "false" 120 uv run vulture src
        invoke_step "Backend: Ty static check" "" "false" 120 uv run ty check src/
        invoke_step "Backend: type-imports" "" "false" 120 python3 scripts/verify_type_imports.py --dir src/domain/dtos
        # 격리 DB(setup_db_isolation)는 빈 DB이므로, pytest conftest의 init_db보다 먼저 도는 Schema Doctor 전에 스키마를 부트스트랩한다.
        invoke_step "Backend: init_db (verify isolation)" "" "false" 120 uv run python -c "from src.infrastructure.persistence.core.database import init_db; init_db()"
        invoke_step "Backend: DB Schema Doctor" "" "false" 120 uv run python scripts/verify/db_schema_doctor.py --exit-on-error
        invoke_step "Backend: F011 backup evidence check" "" "false" 120 uv run python scripts/verify_f011_evidence.py
        invoke_step "Backend: runtime coupling gate" "$ROOT" "false" 120 uv run python scripts/verify/runtime_coupling_gate.py --check
        invoke_step "Backend: test coupling gate" "$ROOT" "false" 120 uv run python scripts/verify/test_coupling_scan.py --check
    else
        skip_step "Backend: compileall" "auto-mode"
        skip_step "Backend: lint-imports" "auto-mode"
        skip_step "Backend: ruff lint" "auto-mode"
        skip_step "Backend: import boundary gate" "auto-mode"
        skip_step "Backend: function length gate" "auto-mode"
        skip_step "Backend: vulture dead code" "auto-mode"
        skip_step "Backend: Ty static check" "auto-mode"
        skip_step "Backend: type-imports" "auto-mode"
        skip_step "Backend: init_db (verify isolation)" "auto-mode"
        skip_step "Backend: DB Schema Doctor" "auto-mode"
        skip_step "Backend: F011 backup evidence check" "auto-mode"
        skip_step "Backend: runtime coupling gate" "auto-mode"
        skip_step "Backend: test coupling gate" "auto-mode"
    fi
}

run_pytest_steps() {
    if [ "$RUN_PYTEST" -eq 1 ]; then
        local strategy=${VERIFY_TEST_STRATEGY:-fast}
        local pytest_args=()

        if [ -n "$PYTEST_TARGET" ]; then
            echo -e "  \033[0;32m[Targeted Testing] Target: $PYTEST_TARGET\033[0m"
            pytest_args=($PYTEST_TARGET)
        elif [ "${VERIFY_INCLUDE_INTEGRATION:-0}" = "1" ]; then
            # RISK-03 L2 통합 테스트 포함 (FHIR roundtrip 등)
            echo -e "  \033[0;90m[INTEGRATION] Including L2 integration tests\033[0m"
            pytest_args=(-n 0 --timeout=180 -m "not slow")
        else
            case "$strategy" in
                # asyncpg 글로벌 엔진·TestClient·세션 루프 조합에서 xdist 병렬 시 풀·락 플레이크가 있어 -n 0 고정
                # ComplianceService·Vault 경로 등 async 통합이 30s를 넘길 수 있어 fast 모드도 상한 여유 확보
                fast) pytest_args=(-n 0 -m "not slow and not integration" --maxfail=3 --timeout=120) ;;
                full) pytest_args=(-n 0 --timeout=300) ;;
                parallel) pytest_args=(-n auto --dist=loadscope --timeout=60) ;;
                unit) pytest_args=(-m "unit and not integration and not slow") ;;
                last-failed) pytest_args=(--lf --maxfail=1) ;;
                *) echo -e "  \033[0;31m[ERROR] Invalid strategy: $strategy\033[0m"; exit 1 ;;
            esac
        fi

        local label="Backend: pytest"
        VERIFY_STEPS+=("$label:true")
        write_step "$label"
        echo -e "  \033[0;90mRunning pytest with strategy: $strategy...\033[0m"
        local start_time
        start_time=$(start_timing)
        local status=0

        (set +e; uv run pytest "${pytest_args[@]}" 2>&1 | tee "$PYTEST_LOG_PATH"; exit $?) || status=$?

        if [ $status -ne 0 ]; then
            local failed_lines
            failed_lines=$(grep -E "FAILED|ERROR" "$PYTEST_LOG_PATH" | awk '{print $NF}' | tr '\n' ' ')
            echo "FAILED TESTS: $failed_lines" > "$PYTEST_FAILURES_PATH"
            echo "" >> "$PYTEST_FAILURES_PATH"
            echo "--- tail ---" >> "$PYTEST_FAILURES_PATH"
            tail -n 30 "$PYTEST_LOG_PATH" >> "$PYTEST_FAILURES_PATH"

            echo -e "\033[0;31mFAILED: $label (exit $status)\033[0m"
            stop_timing "$label" "$start_time"
            fail_verify "$status" "$label" "$failed_lines"
        fi
        stop_timing "$label" "$start_time"
        serialize_state
        save_verify_result 0 "" ""
    else
        skip_step "Backend: pytest" "auto-mode"
    fi
}
