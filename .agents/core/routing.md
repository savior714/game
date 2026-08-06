---
scope:
- '*'
always_apply: false
priority: 2
domain: core
last_verified: 2026-08-06
verify_with:
- uv run pytest -q tests/test_agent_registry_consistency.py
---
<!-- Language: ko -->

# AidenGame 도구·컨텍스트 라우팅

이 문서는 현재 세션에 실제로 제공된 도구와 AidenGame 저장소의 실제 경로를 기준으로 읽기·수정·검증 컨텍스트를 선택하는 보조 규칙이다.
실행 우선순위는 [`AGENTS.md`](../../AGENTS.md)를 따르며 이 문서가 이를 재정의하지 않는다.

## 1. 권위 순서

충돌 시 다음 순서를 적용한다.

1. 사용자의 현재 요청
2. `AGENTS.md`
3. `PROJECT_RULES.md`와 대상 기능에 가장 가까운 product/technical spec
4. 최신 `origin/main`의 코드·테스트·설정

현재 범위가 지정되지 않은 작업 선택은
[`CORE_QUIZ_RELIABILITY_STABILIZATION.md`](../../docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md)를 따른다.

## 2. 도구 선택

- 현재 세션에 노출된 읽기·검색·편집·실행 도구만 사용한다.
- 특정 IDE, 로컬 모델, 외부 에이전트의 도구 이름이나 인자 스키마를 현재 세션에 강제하지 않는다.
- 저장소 내용과 연결 데이터는 사용 가능한 repository connector를 우선한다.
- connector가 제공하지 않는 로컬 실행·정적 진단·브라우저 검증만 실제 checkout 도구로 보완한다.
- 파일이나 명령의 존재를 추측하지 않고 현재 디스크 또는 최신 repository state에서 확인한다.

## 3. 수정 전 조건

기존 파일을 수정하기 전에 다음을 확인한다.

1. 최신 `origin/main`과 대상 파일의 현재 내용을 읽는다.
2. 변경하려는 failure domain과 binary criterion을 고정한다.
3. 수정 범위가 현재 제품 방향에 포함되는지 확인한다.
4. 부분 수정이면 대상 블록이 정확히 식별되는지 확인한다.
5. 전체 덮어쓰기이면 원본 동작·테스트·문서 계약이 유실되지 않는지 diff로 확인한다.
6. 게시 직전 `origin/main` 이동 여부를 다시 확인한다.

대상 문자열이 이미 목표 상태라면 변경을 만들지 않는다.
패턴 불일치가 발생하면 대상 파일을 다시 읽고 원인을 확인한 뒤 더 작은 경계로 재시도한다.

## 4. 경로별 컨텍스트

| 대상 | 우선 컨텍스트 |
|---|---|
| `domains/math/`, `domains/english/`, `domains/korean/`, `domains/science/` | 현재 안정화 spec, 직접 관련 구현, focused test |
| 브라우저 테스트 | 직접 관련 entry, [`playwright.md`](../domains/testing/playwright.md), 실제 browser evidence |
| `docs/`, `.agents/`, README, 최상위 규칙 | authority 문서, 링크 대상, 실제 명령, drift guard |
| `domains/ocean-rescue/`, `ocean-rescue/` | 사용자의 명시적 재개 또는 허용 예외 확인 후 가장 가까운 technical spec |
| `experiments/` | 일반 과목 안정화 동결 정책과 가장 가까운 기술 참고 |
| `Justfile`, `verify.sh`, `scripts/` | 실제 recipe·script와 직접 영향 테스트 |

추가 문서는 기본적으로 다음 세 종류만 읽는다.

- 직접 수정할 구현 또는 문서
- 직접 관련 focused test
- 판단에 필요한 가장 가까운 spec

과거 plan, evidence, 완료 보고를 관성적으로 로드하지 않는다.

## 5. 편집 규율

- 한 작업에는 하나의 failure domain만 둔다.
- 같은 원인을 닫는 source, caller, test, config는 함께 수정할 수 있다.
- unrelated cleanup, 일정 상태 갱신, 새 coordination 체계를 섞지 않는다.
- 대형 파일을 전체 교체할 때는 게시 전에 원본과 후보 diff를 확인한다.
- 생성 artifact는 source와 build pipeline을 통해서만 갱신한다.
- 강제 push, 필수 검증 우회, broad ignore로 녹색 상태를 만들지 않는다.

## 6. 검증과 게시

검증은 위험에 직접 대응하는 가장 작은 항목부터 확장한다.

1. 현재 binary criterion의 focused test 또는 정적 assertion
2. 수정 파일과 직접 영향 모듈의 lint/typecheck
3. 실제 브라우저 또는 build가 필요한 경우 해당 검증
4. 공유 경계 변경 시 영향받는 regression
5. repository-wide gate는 실제 위험이나 정책상 요구될 때

게시 전 최신 `origin/main`을 확인한다.
원격이 이동했으면 최신 main에 재적용하고 직접 영향 검증을 반복한다.
fast-forward가 아니면 게시하지 않는다.

## 7. 현재 자동 라우팅 상태

현재 저장소에는 별도의 자동 route CLI, route manifest, context budget 생성 명령이 없다.
라우팅은 이 문서와
[`CONTEXT_ROUTING.md`](../registry/CONTEXT_ROUTING.md),
[`LOAD_ORDER.md`](../registry/LOAD_ORDER.md)를 기준으로 수동 수행한다.

존재하지 않는 명령이나 catalogue 생성을 작업 완료 조건으로 삼지 않는다.
