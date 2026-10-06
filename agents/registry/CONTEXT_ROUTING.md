---
scope: registry
domain: core
last_verified: 2026-08-07
---
<!-- Language: ko -->

# AidenGame 컨텍스트 라우팅

이 문서는 현재 저장소에 실제로 존재하는 경로와 문서만 사용해 작업 컨텍스트를 선택한다.
정식 agent 문서 경로는 `agents/`다. `.agents/`는 이전 호출을 깨뜨리지 않기 위한 호환 링크만 제공한다.

## 1. 공통 권위

모든 작업에서 다음 우선순위를 유지한다.

`사용자의 현재 요청 → AGENTS.md → PROJECT_RULES.md와 가장 가까운 product/technical spec → 최신 code/tests/config`

현재 제품 방향은 [`ACTIVE_PRODUCT_SCOPE.md`](../../docs/specs/product/ACTIVE_PRODUCT_SCOPE.md)이고,
네 과목 Core Quiz reliability 완료 계약은
[`CORE_QUIZ_RELIABILITY_STABILIZATION.md`](../../docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md)다.

## 2. 작업 유형별 추가 문서

| 작업 | 추가로 읽을 문서 |
|---|---|
| 제품·아키텍처 경계 | `PROJECT_RULES.md`와 가장 가까운 spec |
| same hotspot·canonical runtime·generated artifact reservation | [`work-package-claim.md`](../workflows/work-package-claim.md), Issue #1 |
| Git·dirty·remote advance·publish | [`git.md`](../workflows/git.md) + [`execution.md`](../core/execution.md) |
| 상시 병렬 A/B 트랙 | [`PARALLEL_TRACKS.md`](../project/PARALLEL_TRACKS.md) |
| 로컬 프롬프트 | [`TASK_DELTA_TEMPLATE.md`](../prompts/TASK_DELTA_TEMPLATE.md) |
| 프로젝트 명령·stack | [`PROFILE.md`](../project/PROFILE.md) |
| 문서만 변경 | 참조되는 문서만 |

read-only 분석과 일반 병렬 mutation에는 reservation 문서나 board를 읽을 필요가 없다.

## 3. 경로별 라우팅

| 대상 경로 또는 요청 | 추가로 읽을 문서 | 기본 동작 |
|---|---|---|
| `domains/math/`, `domains/english/`, `domains/korean/`, `domains/science/` | 제품 방향 SSOT, 직접 관련 test | SSOT가 지정한 과목의 failure domain과 과목별 completion contract를 따른다. |
| `tests/**/*browser*`, Playwright 사용 테스트 | [`playwright.md`](../domains/testing/playwright.md) | 실제 브라우저 입력, page error, request failure, 반복 실행을 검증한다. |
| `tests/`의 기타 파일 | [`verification.md`](../core/verification.md) | 현재 failure domain을 잡는 focused assertion만 추가한다. |
| `docs/`, `README.md`, `AGENTS.md`, `PROJECT_RULES.md`, `agents/` | 가장 가까운 authority 문서 | 링크, 우선순위, 현재 제품 방향, 실제 명령 존재 여부를 함께 검증한다. |
| `domains/ocean-rescue/`, `ocean-rescue/` | 가장 가까운 Ocean Rescue technical spec | 사용자가 현재 요청에서 재개했거나 허용 예외가 성립할 때만 작업한다. |
| `experiments/` | 가장 가까운 실험 문서 | 제품 방향 SSOT가 해당 표면을 동결로 표시하면 신규 기능·구조 이전을 시작하지 않는다. |
| `Justfile`, `verify.sh`, `scripts/` | [`verification.md`](../core/verification.md)와 실제 파일 | 문서에 적힌 명령이 현재 파일에 존재하는지 먼저 확인한다. |

## 4. 범위가 없는 요청

“다음 작업”, “이어서 진행”, “로컬 프롬프트”처럼 범위가 없는 요청은 다음 순서로 해석한다.

1. [`ACTIVE_PRODUCT_SCOPE.md`](../../docs/specs/product/ACTIVE_PRODUCT_SCOPE.md)의 current development priority에서 시작 대상을 고른다.
2. 최신 `origin/main`에서 그 대상의 실제 결함을 재현한다.
3. 한 failure domain만 수정하고 독립 검증한다.

대상 과목·기능 목록과 실행 순서는 이 문서가 아니라 SSOT가 소유한다. 최근 커밋이나 과거 계획이 특정 기능을
이유로 자동 재개하지 않는다.

## 5. 컨텍스트 예산

추가 문서는 최대 세 개를 기본으로 한다.

- 직접 수정할 구현
- 직접 관련 focused test
- 현재 판단에 필요한 가장 가까운 spec

장기 계획, 과거 evidence, 이미 반영된 완료 이력은 현재 실행에 필요할 때만 읽는다.

## 6. 자동 라우팅 도구 상태

현재 저장소에는 기계식 registry catalogue이나 자동 라우팅 명령이 없다.
라우팅은 이 문서와 [`LOAD_ORDER.md`](LOAD_ORDER.md)를 기준으로 수동 수행한다.
