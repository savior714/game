---
scope: detail
domain: core
parent: .agents/core/error_patterns.md
lazy_load: true
---
<!-- Language: ko -->

## 5. 계획서 (Blueprint) 실수

### 5.1 plan-lint 통과 전 구현 착수

**증상**: plan-lint 미통과 Blueprint 로 바로 구현 → 실패 재수정.

**원인**: 메타 금지 5 위반 (구조적 오류 포함 가능 Blueprint).

**사례**: `Write('PLAN.md', content)` → 구현 → plan-lint 실패.

**해결**: `just plan-lint PLAN.md` PASS 후 구현.

### 5.2 Task 상태 역방향 리셋 (done → todo)

**증상**: 완료된 Task를 다시 todo로 바꾸면 plan-lint가 실패하거나, 의존성 문제가 생김.

**원인**: Task 완료는 원칙적으로 되돌릴 수 없음.

```
❌ WRONG: 완료된 Task를 todo로 리셋
StrReplace(path, old_string='Status: done', new_string='Status: todo')

✅ CORRECT: plan-reset-gate 사용
just plan-reset-gate PLAN_*.md  # → 승인 및 검증
```

### 5.3 Verify에 grep/echo 단독 사용

**증상**: `just plan-lint`에서 Verify runner 인식 실패로 Task가 FAIL됨.

**원인**: Verify를 "검색/출력 명령"으로만 작성하고 실행 runner(`just`, `pytest`, `uv run`, `pnpm run`, `python3`)를 쓰지 않음.

```
❌ WRONG: runner 없는 Verify
- **Verify**: `grep "class Foo" src/api/router.py`
- **Verify**: `echo "done"`

✅ CORRECT: runner 1개로 검증
- **Verify**: `just lint-be`
- **Verify**: `uv run pytest tests/unit/test_foo.py::test_bar`
```

### 5.4 plan-preread 누락으로 Task-level Pre-read FAIL

**증상**: 신규 Task들이 `Task-level Pre-read missing`으로 연쇄 FAIL.

**원인**: Blueprint 저장 후 `just plan-preread docs/plans/<file>.md --write`를 실행하지 않음.

```
❌ WRONG: 파일 작성 직후 plan-lint만 실행
just plan-lint docs/plans/PLAN_xxx.md

✅ CORRECT: plan-preread → plan-lint 순서 고정
just plan-preread docs/plans/PLAN_xxx.md --write
just plan-lint docs/plans/PLAN_xxx.md
```

### 5.5 todo/running Conclusion에 임의 문구 사용

**증상**: `Status=todo/running` Task에서 Conclusion 포맷 오류로 FAIL.

**원인**: CSF 슬롯 대신 내러티브 결과 문장 또는 `[PASS]` 같은 완료형 문구를 미리 작성함.

```
❌ WRONG: 미완료 Task에 완료형/임의 문구
- **Status**: todo
- **Conclusion**: 구현 완료, 테스트 통과

✅ CORRECT: CSF 슬롯 유지
- **Status**: todo
- **Conclusion**: [판정 — 비개발자용 요약. 검증 결과]
```

### 5.6 plan-lint WARN을 통과로 오인하고 Blueprint 미수정

**증상**: plan-lint가 exit 0을 반환했음에도, 린트 오류나 warnings가 남아있어 실제 PR 게이트나 CI 단계에서 실패함.

**원인**: `plan-lint`는 atomicity 위반, Conclusion 25자 미만, 또는 허용되지 않는 접속사("및", "와", "그리고" 등) 사용 시 WARN을 발생시킵니다. 이를 무시하고 넘어감.

```
❌ WRONG: warnings를 무시하고 그대로 구현 진행
- **Verify**: pnpm exec vitest (비인식 runner 경고 발생)
- **Conclusion**: 완료 (25자 미만 경고 발생)

✅ CORRECT: WARN 메시지 확인 후 Blueprint 수정
- **Verify**: just renderer-vitest-consultation-store (인식된 runner로 교체)
- **Conclusion**: ConsultationPage.tsx 탭 프리셋 mock 수정 완료. tests/unit/pages/ConsultationPage.test.tsx 1개 성공. (25자 이상 구체적 서술)
```

### 5.7 Task Status/Conclusion 에디터 직접 수정

**증상**: `just plan-task-close` 대신 에디터(StrReplace/`edit`)로 Task의 `Status`·`Conclusion`을 직접 수정 → 스크립트가 필드 갱신을 감지하지 못해 실패하거나, 인접 Task Conclusion이 덮어씌워짐.

**원인**: `plan_task_close.py`는 `_patch_task_block`에서 `Status: todo/running/blocked/failed` → `done`과 `- **Conclusion**: ...` 패턴을 정규식으로 매칭한다. 에디터로 수정할 때 공백·인덴트·마커 형식이 다르면 갱신이 안 된다. 또한 `[완료 시 기입]` 같은 placeholder가 그대로 남거나 Conclusion이 25자 미만으로 작성될 위험이 큽니다.

```
❌ WRONG: 에디터로 직접 수정 및 플레이스홀더 잔존
StrReplace(path, old_string='Status: pending', new_string='Status: done')
StrReplace(path, old_string='- **Conclusion**: [완료 시 기입]', new_string='- **Conclusion**: [PASS] 완료함.') // 25자 미만 및 플레이스홀더 오류

✅ CORRECT: plan-task-close CLI만 사용
just plan-task-close plan=docs/plans/PLAN_xxx.md task=XXX-001 conclusion="[PASS] SPEC_ui_billing.md에 청구 준비 점검 패널 요구사항 추가 완료. just docs-ssot-headers PASS." // 25자 이상 상세 검증 명시
```

**규칙**: Blueprint Task의 `Status`·`Conclusion` 수정은 **`just plan-task-close` CLI만 허용**. 에디터 직접 수정 및 `[완료 시 기입]` 등의 placeholder 사용은 절대 금지됩니다.

### 5.8 DoD에 `just plan-close` 포함 (재귀 타임아웃)

**증상**: `just plan-close` 또는 `plan_close_gate.py`가 타임아웃(120초 초과) 또는 재귀 호출로 중단됨.

**원인**: DoD(Definition of Done) 섹션에 `just plan-close`를 백틱 명령어로 포함하면, `plan_close_gate.py`의 `extract_dod_verify_specs()`가 이를 verify 명령어로 추출해 실행한다. 즉 **plan-close가 자기 자신을 호출**하는 재귀가 발생한다.

```
❌ WRONG: DoD에 plan-close 포함
## ✅ Definition of Done (DoD)
- `just plan-close plan=docs/plans/PLAN_xxx.md`

✅ CORRECT: DoD에서 plan-close 제거 또는 주석 처리
## ✅ Definition of Done (DoD)
- `just plan-lint docs/plans/PLAN_xxx.md` → PASS
- (plan-close는 Task 9.9 Verify에서 별도 실행)
```

**규칙**: DoD 섹션에 `just plan-close`를 verify 명령어로 포함하지 않는다. plan-close는 Closeout Task의 Verify에서 별도 실행한다.

### 5.9 Verify에 pytest 전체 파일 실행 (구체성 부족)

**증상**: `just plan-lint`에서 `Task#N Verify must prove one automated outcome (use pytest -k <one> or path::test_name) — split tasks` 오류.

**원인**: Verify에 `pytest tests/.../test_file.py -q`처럼 전체 파일을 실행하는 명령어를 사용하면, plan-lint가 단일 테스트 결과를 증명하지 못한다고 판단한다. Atomic Task는 **단일 테스트**로 검증해야 한다.

```
❌ WRONG: 전체 파일 실행 Verify
- **Verify**: `uv run pytest tests/unit/scripts/linear_sync/test_backlog_triage_review.py -q`

✅ CORRECT: 단일 테스트 검증 (pytest -k 또는 ::test_name)
- **Verify**: `uv run pytest tests/unit/scripts/linear_sync/test_backlog_triage_review.py::test_review_yes_archives_no_plan_issue -q`
- **Verify**: `uv run pytest tests/unit/scripts/linear_sync/test_backlog_triage_review.py -k test_review_process -q`
```

**규칙**: Blueprint Task의 Verify는 **단일 테스트**를 검증해야 한다. `pytest -k <selector>` 또는 `::test_name`을 반드시 포함한다. 여러 테스트를 검증해야 하면 Task를 분할한다.

### 5.10 just plan-close 실행 전 linear-sync 누락

**증상**: `just plan-close` 혹은 Closeout Task 검증 도중 `[FAIL] Linear synchronization required` 발생하며 실패함.

**원인**: 로컬 Blueprint와 원격 Linear 상태 간의 동기화가 이루어지지 않은 상태에서 플랜 종료 게이트를 닫으려 했기 때문입니다.

```
❌ WRONG: linear-sync 없이 plan-close 바로 실행
just plan-close plan=docs/plans/PLAN_xxx.md

✅ CORRECT: linear-sync 선행 후 plan-close 실행
just linear-sync plan=docs/plans/PLAN_xxx.md
just plan-close plan=docs/plans/PLAN_xxx.md
```

**규칙**: 플랜을 종료(close)하기 전에는 반드시 `just linear-sync`를 통해 상태를 동기화해야 합니다.

---
