## 🧭 Context Pre-read Gate (실행 전 필수)

<!-- plan-preread:v1 generated=2026-07-26T09:50:05Z paths=0 must_read_installed=0 -->

**정책 (IDE 공통)**: [execution.md §2.8](.agents/core/execution.md) Context Route Gate. **Read SSOT**은 각 Task 블록의 **`Pre-read`** 목록이다 — `write`/`patch` 전 **해당 Task** 목록을 전부 Read (`write`/`patch` = 파일 쓰기·부분 수정 직전; 호스트 도구명은 [runtime_edit_tools.md §1](.agents/core/runtime_edit_tools.md)). 상단 게이트만 읽고 Task `Pre-read`를 건너뛰면 정책 위반.

**기술 스택 (계획서 추론)**: (경로에서 스택 신호 미확인 — Impact Scope·Target 보강 권장)
**의도 키워드 (계획서 추론)**: ui
**라우팅 입력 경로 (0개)**: (없음 — Task `Target`·Impact Scope에 경로 추가 후 재생성)

### Read SSOT

- **단일 Task 실행**(예: 「Task 1.1만」): 그 Task의 `Pre-read`만 Read.
- **플랜 전체 순차 실행**: Task마다 해당 `Pre-read`를 **그 Task 착수 직전**에 Read(상단에 must_read 목록 없음 — 중복 제거).
- **플랜 전체 must_read 합집합(참고)**: installed 0개 — 상세 경로는 각 Task `Pre-read`에만 나열.


### 재검증 (구현 세션에서 편집 직전)

```bash
just route <paths...> --json
```

플랜 갱신 시 본 절 재생성: `just plan-preread docs/plans/PLAN_epic_repository_integrity_improvements.md --write` → `just plan-lint docs/plans/PLAN_epic_repository_integrity_improvements.md`

## 🎯 Origin Intent

**원래 목적**: 현재 AidenGame 저장소에서 확인되는 개선 후보 5개 (TDD 변경 경로 분류, 검증 도구 부재 시 fail-open, 런타임 엔트리/라우팅 문서 드리프트, Ruff/검증 도구 버전 계약 드리프트, 개발 거버넌스 실효 비용) 를 하나의 ordered Epic SSOT에 기록하여, 이후 세션에서 각 후보를 독립적인 atomic child Blueprint로 구체화할 수 있는 canonical planning entrypoint를 수립한다.

**handoff 출처**: AidenGame 저장소 개선 Epic 요청 (2026-07-26 세션) — 직접 사용자 요청.

**emit 출처**: `verify.sh` §32-33 (code_files_changed 정규식), `verify.sh` §74-83/86-96/99-108 (fallback warn), `README.md` §4-10 (엔트리/라우팅 claim), `vercel.json` §1 (빈 rewrites), `.pre-commit-config.yaml` §2 (ruff v0.3.0), `pyproject.toml` §10 (ruff>=0.4.0)

## ⚠️ Edge Case Trace

| # | 시나리오 | Task-ID | 범위 밖 |
|---|----------|---------|---------|
| 1 | 기존 동등 Epic SSOT가 이미 존재하는 경우 | — | 범위 밖 (중복 생성 금지) |
| 2 | 5개 트랙 중 선행 트랙 해결로 후행 트랙 근거가 소멸하는 경우 | — | — (단기회로 규칙으로 처리) |
| 3 | `just plan-lint`가 Epic 문서 형식을 지원하지 않는 경우 | — | — (저장소 계약 우선) |
| 4 | Epic 생성 후 child Blueprint 생성 시 사용자가 요청하지 않은 경우 | — | 범위 밖 (별도 사용자 승인 필요) |
| 5 | target Epic 파일에 기존 미커밋 변경이 있는 경우 | — | 범위 밖 (BLOCKED) |

## 📋 업무 요약 (협업용)

**무엇**: 저장소 무결성 개선 후보 5개를 하나의 ordered Epic SSOT에 기록

**왜**: 현재 개선 후보가 대화·일회성 분석에만 존재하고, 저장소 내부에 canonical 문서가 없어 세션 간 분석 손실이 발생한다. 각 후보를 독립적인 child Blueprint로 분리하면 한 번에 하나씩 검증·수정할 수 있다.

**어떻게**: 현재 저장소 근거를 읽고 Epic SSOT 파일 하나를 생성. 5개 track에 future failure domain, future hypothesis, future verdict criterion, 실행 순서, 단기회로 규칙, child Blueprint 분리 계약을 기록. 제품 코드·검증 코드·설정 파일은 수정하지 않는다.

**이번에 안 하는 것**: 제품 코드 수정, 검증 코드 수정, 도구 버전 변경, 라우팅 문서 수정, 거버넌스 제거, child Blueprint 생성. 이 모든 작업은 향후 별도 child Blueprint에서만 수행한다.

---

## 🔁 Agent Completion Contract

> **에이전트 스코프**: 아래 Task 1.1만 수행. `docs/plans/PLAN_epic_repository_integrity_improvements.md` 파일 생성 또는 보완. 타 파일·타 디렉터리 터치 금지.

---

## 🛠️ Implementation Plan

#### Task 1.1: 개선 후보 상위 Registry와 분할 계약 수립 [Unit: Atomic]

- **Task-ID**: EPIC-REPO-001
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=10 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
  2. `[planning]` `.agents/core/planning.md`
  3. `[plan_workflow]` `.agents/workflows/plan.md`
  4. `[verification]` `.agents/core/verification.md`
  5. `[routing]` `.agents/core/routing.md`
  6. `verify.sh`
  7. `Justfile`
  8. `pyproject.toml`
  9. `.pre-commit-config.yaml`
  10. `README.md`
- **Action**: 현재 저장소 근거를 읽고, 5개 ordered improvement track과 future child contract를 하나의 Epic SSOT에 기록
- **Target**: `docs/plans/PLAN_epic_repository_integrity_improvements.md`
- **Goal**: 향후 개선 작업이 대화 기억에 의존하지 않고 저장소의 한 canonical entrypoint에서 시작되게 한다
- **Diagnostics**: `find docs/plans -maxdepth 1 -type f -name 'PLAN_epic_*.md' -print` (기존 Epic 검색), `just --list` (plan-lint 지원 확인)
- **Verify**: `python3 -c "
import os
path = 'docs/plans/PLAN_epic_repository_integrity_improvements.md'
assert os.path.isfile(path), 'target file missing'
content = open(path).read()
for rid in ['RID-01', 'RID-02', 'RID-03', 'RID-04', 'RID-05']:
    assert rid in content, f'{rid} missing'
assert 'short-circuit' in content.lower() or '단기회로' in content, 'short-circuit rules missing'
assert 'future child' in content.lower() or 'child Blueprint' in content, 'child contract missing'
assert 'product code changed: 0' in content or '제품 코드 변경 0건' in content, 'no-code-change scope missing'
print('PASS')
"`
- **Dependency**: None
- Status: done
- **Conclusion**: docs/plans/PLAN_epic_repository_integrity_improvements.md 생성 완료. RID-01~RID-05 5개 ordered improvement track과 future child Blueprint 계약, 실행 순서, 단기회로 규칙, Baseline Evidence (B-01~B-05) 모두 기록. just plan-lint PASS, EPIC_SSOT_CONTRACT=PASS. 제품 코드 변경 0건. [closed-by:plan-task-close]

---

## Baseline Evidence

현재 local canonical (`HEAD == origin/main == fb261505623b5ee4be5d0b3bb3614893de4f76da`) 에서 직접 읽은 근거.

### B-01: TDD 변경 경로 분류 — `verify.sh` §32-33

- **파일**: `verify.sh` lines 32-33
- **관련 코드**: `code_files_changed` 정규식: `^(math|english|korean|science|space-explorer|common|global|guardian|admin|marble|scripts)/.*\.(js|html)$|^[A-Za-z0-9_.-]+\.(js|html)$`
- **현재 관찰**: 정규식이 `domains/` prefix 없이 `math/`, `english/` 등으로 시작. 실제 제품 코드는 `domains/math/index.html`, `domains/english/index.html` 등 `domains/` prefix 하위. `domains/reward/`, `domains/auth/`, `domains/sync/` 경로가 누락될 수 있음.
- **evidence confidence**: HIGH — 정규식과 실제 디렉터리 구조 직접 비교 가능
- **아직 하지 않은 검증**: 정규식이 `domains/math/index.html` 등을 실제로 매칭하는지 `rg`로 실측하지 않음
- **향후 child track ID**: `RID-01`

### B-02: 검증 도구 부재 시 fail-open — `verify.sh` §74-83, §86-96, §99-108

- **파일**: `verify.sh` lines 74-108
- **관련 코드**: `run_lint()` §76-83 — `ruff` 없을 때 `[WARN] ruff/just not found; skipping lint` 후 계속. `run_tests()` §88-96 — `pytest` 없을 때 `[WARN] pytest not found; skipping tests` 후 계속. `run_korean_check()` §101-108 — `python3` 없을 때 `[WARN] python/uv not found; skipping Korean check` 후 계속.
- **현재 관찰**: 모든 필수 검증 도구가 없을 때 `WARN` 메시지로 스킵하고 최종 `✅ AidenGame verification complete.` 메시지를 출력. 실제 검증이 실행되지 않아도 PASS로 오인됨.
- **evidence confidence**: HIGH — 소스 코드 직접 확인
- **아직 하지 않은 검증**: 도구 제거 환경에서 실제 exit code 확인 안 함
- **향후 child track ID**: `RID-02`

### B-03: 런타임 엔트리와 라우팅 문서 SSOT 드리프트

- **파일**: `README.md` §4-10, `vercel.json` §1, `PROJECT_RULES.md` §1
- **관련 내용**:
  - `README.md`: "우주 탐험: `experiments/space-explorer.html`" — 하지만 실제 파일은 `experiments/space-explorer/index.html` (디렉터리 구조)
  - `vercel.json`: `"rewrites": []` — 라우팅 규칙 없음
  - `PROJECT_RULES.md` §1: "메인 허브: `index.html`" — 일치
- **현재 관찰**: `README.md`의 우주 탐험 경로가 실제 파일 시스템 구조와 불일치. `experiments/space-explorer.html`은 존재하지 않고 `experiments/space-explorer/index.html`이 실제 엔트리.
- **evidence confidence**: HIGH — 디렉터리 구조 직접 확인 (`ls experiments/space-explorer/`)
- **아직 하지 않은 검증**: `index.html` 내 실제 링크와 `vercel.json` rewrites 실제 동작 확인 안 함
- **향후 child track ID**: `RID-03`

### B-04: Ruff 및 검증 도구 버전 계약 드리프트

- **파일**: `.pre-commit-config.yaml` §2-3, `pyproject.toml` §10
- **관련 내용**:
  - `.pre-commit-config.yaml`: `rev: v0.3.0` (ruff pre-commit hook)
  - `pyproject.toml`: `"ruff>=0.4.0"` (dev dependency)
- **현재 관찰**: pre-commit hook의 ruff 버전 (`v0.3.0`) 과 pyproject.toml의 ruff 버전 (`>=0.4.0`) 이 불일치. 동일 코드베이스에 대해 다른 버전의 ruff가 lint 판정을 내릴 수 있음.
- **evidence confidence**: HIGH — 두 파일 직접 확인
- **아직 하지 않은 검증**: 실제 설치된 ruff 버전과 각 버전의 lint 판정 차이 확인 안 함
- **향후 child track ID**: `RID-04`

### B-05: 개발 거버넌스 실효 비용

- **파일**: `AGENTS.md` §4 (다중 에이전트 5단계 페이즈), `.agents/core/planning.md` §2.1-2.7 (Blueprint 계약), `Justfile` (17개 recipe)
- **관련 내용**:
  - AGENTS.md §4: 5단계 페이즈 (분석·계획 → 구현 → 검증 → 수정 → 최종 감사) — 각 페이즈마다 subagent 순차 호출
  - planning.md §2: Blueprint 계약 자동 검증 (`just plan-lint`), Linear sync, Conclusion 강제 게이트 등
  - Justfile: `plan-lint`, `plan-preread`, `plan-task-close`, `plan-close`, `plan-reset-gate`, `commit-gate-hard`, `commit-gate-soft`, `lint-turn-end` 등 17개 recipe
- **현재 관찰**: 거버넌스 게이트가 다수 존재. 일반 작업 (예: 단일 파일 수정) 에서도 `just route` → `just route-read` → `just route-gate-check` 절차가 필요. Blueprint 생성·close·archive 비용도 존재.
- **evidence confidence**: MEDIUM — 실제 반복 비용은 측정 안 함 (이 Epic에서는 측정만)
- **아직 하지 않은 검증**: 실제 개발 루프에서의 반복 비용 측정 안 함
- **향후 child track ID**: `RID-05`

---

## Ordered Improvement Tracks

### Track RID-01 — TDD 변경 경로 분류 무결성

```yaml
priority: P0
future_failure_domain: CURRENT_PRODUCT_CODE_PATHS_MAY_NOT_BE_CLASSIFIED_BY_TDD_CHANGE_GATE
```

**확인할 후보 근거**: B-01 (`verify.sh` §32-33 `code_files_changed` 정규식과 실제 제품 코드 경로 `domains/` 하위 불일치 가능성)

**Future direct hypothesis 의미**: 현재 제품 코드 경로를 변경 감지 계약에 포함시키면, 실제 코드 변경이 테스트 변경 여부 검사에서 누락되지 않는다.

**Future verdict criterion 예시 의미**: 대표 current code path 각각이 code change로 분류되고, docs-only 변경은 code change로 분류되지 않는다.

**이번 Epic 작업**: 정규식을 수정하거나 테스트하지 않는다.

---

### Track RID-02 — 검증 도구 부재 시 fail-open 여부

```yaml
priority: P0
future_failure_domain: REQUIRED_VERIFICATION_TOOLS_MAY_BE_SKIPPED_WITH_SUCCESS_EXIT
```

**확인할 후보 근거**: B-02 (`verify.sh` §74-108 — ruff/pytest/python3 부재 시 WARN + 계속 → 최종 PASS 메시지)

**Future direct hypothesis 의미**: 필수 검증 도구가 없으면 성공이 아니라 명시적 실패로 종료하게 하면, 검증 미실행 상태가 PASS로 오인되지 않는다.

**Future verdict criterion 예시 의미**: 필수 도구 하나를 controlled environment에서 제거했을 때 검증 명령이 non-zero로 종료되고 누락 도구를 명시한다.

**이번 Epic 작업**: fail-open 동작을 수정하지 않는다.

---

### Track RID-03 — 런타임 엔트리와 라우팅 문서 SSOT 드리프트

```yaml
priority: P1
future_failure_domain: RUNTIME_ENTRY_AND_ROUTING_DOCUMENTATION_HAVE_CONFLICTING_CANONICAL_CLAIMS
```

**확인할 후보 근거**: B-03 (`README.md` §6 — "우주 탐험: `experiments/space-explorer.html`" vs 실제 `experiments/space-explorer/index.html`)

**Future direct hypothesis 의미**: 실제 런타임 경로와 배포 설정을 기준으로 문서 claim을 하나로 정규화하면, 엔트리와 라우팅에 대한 상충하는 SSOT가 제거된다.

**Future verdict criterion 예시 의미**: 모든 canonical 문서가 동일한 실제 엔트리 경로와 동일한 Vercel rewrite 상태를 기술한다.

**이번 Epic 작업**: 문서를 직접 정정하지 않는다.

---

### Track RID-04 — Ruff 및 검증 도구 버전 계약 드리프트

```yaml
priority: P1
future_failure_domain: LOCAL_AND_PRECOMMIT_RUFF_VERSION_CONTRACTS_MAY_DIVERGE
```

**확인할 후보 근거**: B-04 (`.pre-commit-config.yaml` §2-3 — ruff `v0.3.0` vs `pyproject.toml` §10 — `ruff>=0.4.0`)

**Future direct hypothesis 의미**: Ruff 실행 경로가 하나의 버전 정책을 따르게 하면, local verification과 pre-commit의 판정 차이가 제거된다.

**Future verdict criterion 예시 의미**: 동일 fixture에 대해 local Ruff와 pre-commit Ruff가 동일 버전 계열과 동일 판정을 사용한다.

**이번 Epic 작업**: 버전 번호를 수정하지 않는다.

---

### Track RID-05 — 개발 거버넌스 실효 비용 평가

```yaml
priority: P2
future_failure_domain: GOVERNANCE_GATES_MAY_IMPOSE_UNMEASURED_RECURRING_COST
```

**확인할 후보 근거**: B-05 (AGENTS.md §4 5단계 페이즈, planning.md §2 Blueprint 계약, Justfile 17개 recipe)

이 트랙은 제거 또는 단순화를 미리 결론 내리지 않는다.

**Future direct hypothesis 의미**: 실제 개발 루프의 한 가지 반복 비용을 측정하면, 해당 게이트가 유지되어야 하는지 또는 최소화 가능한지 근거 기반으로 판정할 수 있다.

**Future verdict criterion 예시 의미**: 선택한 단일 게이트의 반복 비용과 탐지하는 구체적 failure mode가 직접 비교되어 KEEP 또는 SIMPLIFY 중 하나로 판정된다.

**이번 Epic 작업**: 거버넌스를 제거·축소·재작성하지 않는다.

---

## Execution Order

```
RID-01
→ RID-02
→ RID-03
→ RID-04
→ RID-05
```

**순서의 근거**:

1. 변경 감지 자체가 부정확하면 이후 수정의 테스트 동반 여부를 신뢰하기 어렵다 (RID-01 선행).
2. 검증 도구 부재가 성공으로 처리되면 이후 모든 PASS의 의미가 약해진다 (RID-02 선행).
3. 검증 신뢰성을 확보한 뒤 라우팅 문서 정합성을 다룬다 (RID-03).
4. 그다음 도구 버전 판정 차이를 다룬다 (RID-04).
5. 거버넌스 비용 평가는 신뢰성 문제와 분리하여 마지막에 수행한다 (RID-05).

이 순서는 구현을 한 번에 실행하라는 의미가 아니다. 각 트랙은 별도 사용자 승인과 별도 child Blueprint가 필요하다.

---

## Short-Circuit Rules

각 future child track에는 다음 규칙을 적용한다.

```
1. 최신 origin/main에서 근거를 다시 재현한다.
2. 가설 하나만 검증한다.
3. 근거가 사라졌으면 REJECTED로 닫고 코드를 수정하지 않는다.
4. 근거가 확인됐을 때만 최소 변경한다.
5. 해당 가설만 targeted verification한다.
6. 다른 오류는 별도 track으로 남긴다.
7. full-suite 결과를 여러 원인의 일괄 판정에 사용하지 않는다.
```

선행 트랙 해결로 후행 트랙의 근거가 사라질 수 있으면 후행 트랙은 자동 실행하지 않는다. 반드시 다시 재현한 뒤 진행한다.

---

## Future Child Blueprint Contract

각 트랙의 child Blueprint 이름 후보:

```
docs/plans/PLAN_verify_tdd_current_path_classification.md
docs/plans/PLAN_verify_required_tool_fail_closed.md
docs/plans/PLAN_runtime_routing_documentation_ssot.md
docs/plans/PLAN_ruff_version_contract_alignment.md
docs/plans/PLAN_governance_single_gate_cost_assessment.md
```

**이는 이번 실행에서 생성할 파일 목록이 아니다. 이번 실행에서는 위 파일을 만들지 않는다.**

각 child Blueprint는 향후 다음 계약을 지켜야 한다.

```
ONE CHILD PLAN
= ONE FAILURE DOMAIN
= ONE DIRECT HYPOTHESIS
= ONE VERDICT CRITERION
```

각 child Blueprint는 최대한 짧고 local LLM이 독립 실행 가능한 범위로 작성한다. 하나의 child plan에서 여러 트랙을 다루지 않는다.

---

## 🔁 Conclusion & Summary

[판정 — 비개발자용 요약. 검증 결과]

---

## 📊 Metrics

| 항목 | Before | After |
|------|--------|-------|
| 개선 후보 canonical 문서 | 없음 (대화·일회성 분석만) | `docs/plans/PLAN_epic_repository_integrity_improvements.md` 1건 |
| 식별된 improvement track | 0 | 5 (RID-01~RID-05) |
| 제품 코드 변경 | 0 | 0 |
| 검증 코드 변경 | 0 | 0 |
| 설정 파일 변경 | 0 | 0 |