# AidenGame 문서 권위와 상태

이 색인은 현재 개발 방향을 결정하는 문서와 안정 참고·동결·legacy 문서를 구분한다.
문서의 수정 시각이나 분량이 권위를 결정하지 않는다.

## 1. 적용 우선순위

충돌 시 다음 순서를 따른다.

1. 사용자의 현재 요청
2. [`AGENTS.md`](../AGENTS.md)
3. [`PROJECT_RULES.md`](../PROJECT_RULES.md)와 대상 기능에 가장 가까운 product/technical spec
4. 최신 `origin/main`의 코드·테스트·설정

과거 plan, evidence, 완료 보고, WP 번호는 현재 실행 순서를 정하지 않는다.

## 2. 현재 실행 권위

| 문서 | 역할 | 갱신 조건 |
|---|---|---|
| [`AGENTS.md`](../AGENTS.md) | 작업 선택, Git, 검증, 보고 계약 | 저장소 실행 규칙이 실제로 변경될 때 |
| [`PROJECT_RULES.md`](../PROJECT_RULES.md) | 제품·아키텍처·품질 경계 | 제품 정책 또는 경계가 변경될 때 |
| [`CORE_QUIZ_RELIABILITY_STABILIZATION.md`](specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md) | 현재 일반 과목 안정화 계약 | 사용자 결정이나 completion contract가 변경될 때 |
| [`MEMORY.md`](agent-context/memory/MEMORY.md) | 새 세션 handoff와 다음 실행 경계 | 제품 방향 또는 다음 실행 경계가 바뀔 때 |
| [`README.md`](../README.md) | 저장소 진입점 | 사용자·개발자 진입 정보가 변경될 때 |

현재 범위가 지정되지 않은 다음 작업은 일반 과목 공통 브라우저 진단에서 시작한다.

## 3. 동결 기술 참고

다음 문서는 구현 구조를 보존하지만 현재 작업을 지시하지 않는다.

| 문서 | 상태 | 재개 조건 |
|---|---|---|
| [`SPACE_EXPLORER_PLAN.md`](SPACE_EXPLORER_PLAN.md) | `PAUSED_REFERENCE_ONLY` | 사용자의 명시적 방향 변경 또는 일반 과목 안정화 exit 이후 재결정 |
| [`PLAN_ocean_rescue_vite_esm_typescript_migration.md`](plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md) | `PAUSED_REFERENCE_ONLY` | 사용자의 명시적 방향 변경 또는 일반 과목 안정화 exit 이후 재결정 |

동결 문서의 명령은 유지보수 참고다.
문서의 과거 phase, checklist, WP 번호를 근거로 신규 기능이나 구조 이전을 시작하지 않는다.

## 4. 안정·legacy 기술 참고

| 문서 | 상태 | 역할 |
|---|---|---|
| [`DESIGN.md`](specs/technical/DESIGN.md) | `STABLE_REFERENCE_NOT_CURRENT_PRIORITY` | 기존 시각 언어의 비회귀와 실제 runtime entry 참고 |
| [`SPEC_orchestration.md`](specs/technical/SPEC_orchestration.md) | `LEGACY_REFERENCE_ONLY` | 남아 있는 typed orchestration helper package 설명; 현재 필수 workflow 아님 |

`DESIGN.md`는 순수 시각 개선을 현재 작업으로 만들지 않는다.
`SPEC_orchestration.md`는 모든 에이전트 작업에 multi-phase dispatch를 강제하지 않는다.

## 5. 기능별 기술 문서

기능별 문서는 실제 코드와 직접 관련된 경우에만 읽는다.

- `docs/specs/product/`: 제품 동작과 수용 기준
- `docs/specs/technical/`: 기술 구조와 경계 또는 명시적으로 분류된 참고
- `docs/ops/`: 실제 운영 절차가 존재하는 경우의 운영 참고
- `docs/evidence/`: 특정 시점의 증거; 현재 상태 권위가 아님
- `docs/plans/`: 사용자가 명시적으로 요청한 Blueprint 또는 동결 기술 참고

문서와 현재 코드가 불일치하면 최신 코드·테스트·설정을 확인하고, 제품 계약 자체가 변경된 것인지 문서 drift인지 구분한다.

## 6. 계획과 상태 기록 규칙

- 일반 WP 계획과 다음 WP는 대화에서 관리한다.
- 상태 전용 plan/evidence 파일을 새로 만들지 않는다.
- 테스트에서 `다음 WP`, `현재 WP`, `WP COMPLETE` 같은 일정 상태를 검증하지 않는다.
- 완료 근거는 최신 main의 코드, focused test, 브라우저 증거, build/artifact 계약이다.
- 제품 계약이 아니라 진행률만 달라졌다면 authority 문서를 수정하지 않는다.

## 7. 문서 변경 검증

문서를 변경할 때 다음을 확인한다.

1. 링크 대상이 실제로 존재하는가
2. 적힌 명령이 `Justfile`, `verify.sh`, 스크립트에 실제로 존재하는가
3. 현재 제품 방향과 동결 범위가 충돌하지 않는가
4. 과거 상태를 현재 일정 권위처럼 표현하지 않는가
5. 제품 테스트에 일정 상태 assertion을 추가하지 않았는가
6. optional 또는 legacy package를 현재 필수 실행 경로로 승격하지 않았는가

관련 focused 검증:

```bash
uv run pytest -q tests/test_core_quiz_reliability_policy.py
uv run pytest -q tests/test_agent_registry_consistency.py
uv run pytest -q tests/test_document_authority_classification.py
uv run pytest -q tests/test_active_technical_spec_consistency.py
```

## 8. 새 문서 작성 판단

새 문서는 다음 조건을 모두 만족할 때만 추가한다.

- 기존 authority 문서에 넣으면 역할이 섞인다.
- 현재 실행이나 제품 판단에 반복적으로 필요한 안정적인 계약이다.
- 코드·테스트만으로 설명하기 어려운 관계가 있다.
- 갱신 책임과 검증 방법이 명확하다.

단순 진행 상황, 다음 작업, 이미 완료된 변경 보고만을 저장하기 위해 새 문서를 만들지 않는다.
