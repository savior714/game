# AidenGame 문서 권위와 상태

이 색인은 현재 개발 방향을 결정하는 문서와 feature reference, 완료 계약, 동결·legacy 문서를 구분한다. 문서의 수정 시각, 분량, `ACTIVE`/WP 같은 내부 문자열이 권위를 결정하지 않는다.

## 1. 적용 우선순위

충돌 시 다음 순서를 따른다.

1. 사용자의 현재 요청
2. [`AGENTS.md`](../AGENTS.md) — 실행·Git·검증 규칙
3. [`ACTIVE_PRODUCT_SCOPE.md`](specs/product/ACTIVE_PRODUCT_SCOPE.md) — **현재 제품 방향 단일 SSOT**
4. [`PROJECT_RULES.md`](../PROJECT_RULES.md) — 아키텍처·품질 경계
5. 대상 기능에 가장 가까운 product/technical spec
6. 최신 `origin/main`의 코드·테스트·설정

과거 plan, evidence, 완료 보고, WP 번호, runbook의 `ACTIVE` 문구는 현재 제품 우선순위를 정하지 않는다.

## 2. 현재 권위 문서

| 문서 | 역할 | 갱신 조건 |
|---|---|---|
| [`AGENTS.md`](../AGENTS.md) | 작업 실행, Git, 검증, 보고 계약 | 저장소 실행 규칙이 실제로 변경될 때 |
| [`ACTIVE_PRODUCT_SCOPE.md`](specs/product/ACTIVE_PRODUCT_SCOPE.md) | **제품 목표, 현재 priority, 학습↔게임 관계, active/frozen surface, 큰 개발 sequence의 단일 SSOT** | 제품 방향이 실제로 변경될 때 |
| [`PROJECT_RULES.md`](../PROJECT_RULES.md) | 아키텍처·품질·보안 경계 | 제품 결정의 결과로 해당 경계가 실제 변경될 때 |
| [`MEMORY.md`](agent-context/memory/MEMORY.md) | 새 세션 handoff와 바로 다음 실행 경계 | 현재 방향/다음 실행 경계가 바뀔 때 |
| [`README.md`](../README.md) | 저장소 진입점과 제품 요약 | 사용자·개발자 진입 정보가 변경될 때 |

범위가 지정되지 않은 “다음 작업”은 `ACTIVE_PRODUCT_SCOPE.md`의 current development priority에서 시작한다. 현재는 Math skill/mastery adaptive vertical slice가 기본이다.

## 3. 완료된 제품 계약

| 문서 | 상태 | 역할 |
|---|---|---|
| [`CORE_QUIZ_RELIABILITY_STABILIZATION.md`](specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md) | `COMPLETED_REFERENCE` | Math/English/Korean/Science 핵심 quiz reliability baseline과 회귀 계약 |

이 문서의 과거 “현재 최우선”, freeze 조건, implementation sequence는 **2026-08-06 안정화 단계의 계약**이다. 현재 작업 선택은 `ACTIVE_PRODUCT_SCOPE.md`를 따른다. 동일 신뢰성 결함이 재현되면 회귀 계약으로 재사용한다.

## 4. Active feature reference

### Ocean Rescue

Ocean Rescue는 더 이상 제품 차원에서 동결된 feature가 아니다. **학습 목표 완료 후 이용하는 active reward-game product**다. 다만 현재 기본 개발 priority는 Math mastery/adaptive loop이므로 Ocean Rescue 내부의 과거 WP/runbook이 자동으로 다음 작업이 되지는 않는다.

| 문서 | 역할 | 분류 |
|---|---|---|
| [`AIDENGAME_OCEAN_RESCUE_MVP_PRD.md`](specs/product/AIDENGAME_OCEAN_RESCUE_MVP_PRD.md) | 게임 내부 사용자 흐름·mission·상호작용 제품 계약 | `ACTIVE_FEATURE_REFERENCE` |
| [`AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md`](specs/product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md) | rendering acceptance | `ACTIVE_FEATURE_REFERENCE` |
| [`AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md`](specs/technical/AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md) | source/build/runtime/artifact architecture | `ACTIVE_FEATURE_REFERENCE` |
| [`AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md`](specs/technical/AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md) | manual asset handoff와 provenance | `ACTIVE_FEATURE_REFERENCE` |
| [`PLAN_ocean_rescue_vite_esm_typescript_migration.md`](plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md) | 현재 Vite/ESM/TypeScript/rollback 구조의 기술 참고 | `STABLE_TECHNICAL_REFERENCE_NOT_CURRENT_PRIORITY` |

`IMPLEMENTATION_READY`, `CANONICAL`, `ACTIVE` 같은 문서 내부 성숙도/작업 문자열은 `ACTIVE_PRODUCT_SCOPE.md`의 현재 priority를 덮어쓰지 않는다.

A/B track runbook은 사용자가 **A트랙/B트랙을 명시적으로 요청한 경우에만** 실행 범위 참고로 사용한다. 범위 미지정 다음 작업의 authority가 아니다.

## 5. 동결 기술 참고

| 문서 | 상태 | 재개 조건 |
|---|---|---|
| [`SPACE_EXPLORER_PLAN.md`](SPACE_EXPLORER_PLAN.md) | `PAUSED_REFERENCE_ONLY` | 사용자가 제품 방향에서 Space Explorer 재개를 명시적으로 결정할 때 |

Space Explorer의 존재나 과거 plan만으로 신규 기능을 시작하지 않는다.

## 6. 안정·legacy 기술 참고

| 문서 | 상태 | 역할 |
|---|---|---|
| [`DESIGN.md`](specs/technical/DESIGN.md) | `STABLE_REFERENCE_NOT_CURRENT_PRIORITY` | 기존 시각 언어의 비회귀와 실제 runtime entry 참고 |
| [`SPEC_orchestration.md`](specs/technical/SPEC_orchestration.md) | `LEGACY_REFERENCE_ONLY` | 남아 있는 typed orchestration helper package 설명; 현재 필수 workflow 아님 |

`DESIGN.md`의 과거 단계 표현은 현재 UI redesign priority를 만들지 않는다. `SPEC_orchestration.md`는 모든 에이전트 작업에 multi-phase dispatch를 강제하지 않는다.

## 7. 기타 feature contract

| 문서 | 상태 | 역할 |
|---|---|---|
| [`AIDENGAME_YOUTUBE_FREE_TIME_SESSION.md`](specs/product/AIDENGAME_YOUTUBE_FREE_TIME_SESSION.md) | `APPROVED_PRODUCT_CONTRACT_NOT_CURRENT_PRIORITY` | 외부 YouTube 자유시간 feature 계약; active product priority를 자동 변경하지 않음 |

- `docs/specs/product/`: 제품 동작과 수용 기준
- `docs/specs/technical/`: 기술 구조와 경계
- `docs/evidence/`: 특정 시점의 증거; 현재 상태 권위가 아님
- `docs/plans/`: 명시적 runbook 또는 안정 기술 참고; 제품 priority authority가 아님

문서와 현재 코드가 불일치하면 최신 코드·테스트·설정을 확인하고, 제품 계약 변경인지 문서 drift인지 구분한다.

## 8. 계획과 상태 기록 규칙

- 제품의 큰 방향과 dependency sequence만 `ACTIVE_PRODUCT_SCOPE.md`가 소유한다.
- atomic 다음 작업, 진행률, 완료 이력은 제품 SSOT에 누적하지 않는다.
- 상태 전용 plan/evidence 파일을 새로 만들지 않는다.
- runbook은 해당 범위가 명시적으로 선택된 경우만 읽는다.
- 테스트에서 `다음 WP`, `현재 WP`, `WP COMPLETE` 같은 일정 상태를 검증하지 않는다.
- 완료 근거는 최신 main의 코드, focused test, 브라우저 증거, build/artifact 계약이다.

## 9. 문서 변경 검증

문서를 변경할 때 다음을 확인한다.

1. 링크 대상이 실제로 존재하는가
2. 적힌 명령이 실제 스크립트/Justfile에 존재하는가
3. `ACTIVE_PRODUCT_SCOPE.md`와 제품 방향이 충돌하지 않는가
4. 완료된 reliability 계약을 다시 current priority처럼 표현하지 않는가
5. Ocean Rescue를 product-level frozen feature처럼 표현하지 않는가
6. Space Explorer를 명시적 결정 없이 active로 승격하지 않았는가
7. 과거 runbook/WP/internal maturity label을 현재 실행 우선순위로 오인하지 않았는가
8. 제품 테스트에 일정 상태 assertion을 추가하지 않았는가

관련 focused 검증:

```bash
uv run pytest -q tests/test_active_product_scope_policy.py
uv run pytest -q tests/test_document_authority_classification.py
uv run pytest -q tests/test_ocean_rescue_product_classification.py
uv run pytest -q tests/test_active_technical_spec_consistency.py
```

## 10. 새 문서 작성 판단

새 문서는 다음 조건을 모두 만족할 때만 추가한다.

- 기존 authority 문서에 넣으면 역할이 섞인다.
- 현재 실행이나 제품 판단에 반복적으로 필요한 안정적인 계약이다.
- 코드·테스트만으로 설명하기 어려운 관계가 있다.
- 갱신 책임과 검증 방법이 명확하다.

`ACTIVE_PRODUCT_SCOPE.md`와 같은 내용을 다른 문서에 복제하기 위한 새 문서는 만들지 않는다.
