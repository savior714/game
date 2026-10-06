---
scope:
- '*'
always_apply: false
priority: 1
domain: core
last_verified: 2026-10-06
verify_with:
- uv run pytest -q tests/test_core_agent_contract_consistency.py
---
<!-- Language: ko -->

# AidenGame 검증 규칙

이 문서는 변경 위험에 맞는 검증 선택, 검증 계층, PASS/BLOCKED 판정을 정의한다.
변경 범위 경계는 [`principles.md`](principles.md), 실행 순서는
[`execution.md`](execution.md), 보고 형식은 [`reporting.md`](reporting.md)를 따른다.
실제 명령은 최신 `Justfile`, `verify.sh`, package 설정, 테스트 파일을 우선한다.

## 1. 기본 원칙

- 검증은 현재 failure domain을 판정하는 가장 작은 항목부터 시작한다.
- 파일이나 명령이 존재한다고 추측하지 않는다.
- 같은 명령으로 수정 전후를 비교할 수 있으면 동일 criterion을 유지한다.
- 실행하지 않은 검증을 PASS로 보고하지 않는다.
- 전체 suite는 공유 cutover, 광범위한 회귀 위험, 저장소 정책이 요구할 때만 실행한다.
- workaround, fail-open fallback, broad ignore, 검사 대상 축소, baseline·snapshot 갱신으로 실패를
  숨기지 않는다.

## 2. 위험 기반 개발·테스트 선택

정통 TDD를 모든 변경에 일률적으로 강제하지 않는다. TDD를 생략하는 것은 무검증 개발을 허용한다는
뜻이 아니다.

- 화면 구성, 스타일, 애니메이션, 조작감, 게임 감각, 콘텐츠 표현, 탐색적 신규 기능과 단순
  dependency/toolchain 승격은 먼저 구현하고 실제 브라우저·입력·렌더링으로 직접 확인한 뒤 안정된
  계약만 회귀 테스트로 고정할 수 있다.
- 입력 한 번에 효과 한 번, 이벤트 중복 연결, 점수·진행·저장 데이터, 복잡한 상태 전이, 재시작·복구,
  공유 controller, 사용자 데이터 손상 가능성과 이미 발생한 회귀 버그는 테스트 우선 또는 구현과 동시에
  테스트한다.
- 시각적 품질과 재미를 단위 테스트로 대신하지 않는다. 반대로 자동 검증 가능한 핵심 계약을 수동
  확인만으로 남기지 않는다.
- 테스트는 구현 구조를 복제하지 않고 사용자에게 중요한 동작과 재발 방지에 집중한다.
- 모든 변경은 수정 전 재현 조건 또는 기대 동작과 단일 판정 기준을 정하고, 수정 후 해당 failure
  domain을 가장 짧은 독립 검증으로 판정한다.
- 형식적인 RED 증명, 고정 횟수 반복, 전 과목·전체 suite 실행을 모든 작업의 기본 절차로 삼지 않는다.
  현재 위험이나 실제 불안정성이 요구할 때만 넓힌다.

## 3. 형제 화면·공용 소유자 사전 점검

과목별 화면이나 공용 UI·controller의 동작을 수정하기 전에는 같은 사용자 계약을 제공하는 형제 범위를
읽기 전용으로 점검한다.

- 기본 형제 범위는 `domains/math/`, `domains/korean/`, `domains/english/`, `domains/science/`의 대응
  control·flow와 이를 소유하는 `shared/` 구현이다.
- 재시작, 통계, 점수, 진행, 저장, 입력 이벤트처럼 같은 기능을 제공하는 위치와 동일 button/event
  binding을 먼저 검색한다.
- 이 점검은 누락·중복 소유자를 찾기 위한 조사 범위이며 authorized write scope를 자동으로 넓히지
  않는다.
- 같은 shared owner의 한 수정으로 같은 root cause와 rollback boundary를 함께 닫을 수 있을 때만 하나의
  failure domain에 포함한다.
- 과목별 독립 wiring이나 다른 root cause가 확인되면 현재 대상만 수정·검증하고 나머지는
  `DISCOVERED_FAILURE` 또는 별도 objective로 분리한다.
- 현재 대상은 실제 사용자 입력 경로로 검증하며, 입력 한 번에 handler·render·request 같은 직접 효과가
  정확히 한 번만 발생해야 한다.

## 4. 판정 기준과 검증 계층

현재 작업 결과는 다음 두 항목으로만 판정한다.

- `PRIMARY_CRITERION`: 현재 단일 가설을 직접 판정하는 기준
- `DIRECT_IMPACT_CLOSURE`: 수정 파일과 직접 영향 범위의 lint·type·focused regression

검증 계층:

- V0 `BASELINE`: 수정 전 결함 재현
- V1 `PRIMARY`: 단일 가설 판정
- V2 `DIRECT`: 수정 파일과 직접 영향 closure
- V3 `SYSTEM_SMOKE`: 독립 결함 탐색; 현재 작업 PASS를 취소하지 않음
- V4 `RELEASE`: 명시적인 release candidate에서만 수행

현재 변경이 정상이어도 실패할 수 있는 broad smoke, full suite 또는 다른 과목·실험 영역의 실패는
primary criterion이 될 수 없다. V3에서 발견된 독립 실패는 현재 작업의 PASS를 취소하지 않고
`DISCOVERED_FAILURE`로 분리한다.

변경 위험에 직접 대응하는 가장 작은 검증부터 시작하며 모든 명령을 일괄 실행하지 않는다.

수정 파일과 직접 영향 모듈의 LSP·typecheck·lint 오류는 0이어야 한다. 환경·workspace·SDK·cache·
generated/vendor 오분석을 production code 변경으로 우회하지 않는다.

실행하지 못한 V1·필수 V2 criterion은 PASS로 보고하지 않는다.

## 5. 검증 범위

| 변경 유형 | 최소 검증 |
|---|---|
| 문서·규칙 | 링크, 경로, 실제 명령, authority·동결 정책, focused document test |
| Python 테스트·도구 | Ruff, 관련 pytest, 필요한 typecheck |
| 일반 과목 JavaScript/UI | 직접 상태 계약, 해당 과목 browser flow, 영향받는 과목 regression |
| 공용 `shared/` | 영향을 받는 모든 완료 과목의 상태·브라우저 계약 |
| 배포 entry·라우팅 | 실제 entry와 `vercel.json`, 관련 routing test |
| Ocean Rescue 유지보수 예외 | 직접 focused test, 필요한 typecheck/browser/build/artifact/rollback |
| generated artifact | clean rebuild, deterministic identity, drift, 필요한 rollback |

현재 제품 방향 문서 정합성:

```bash
uv run pytest -q tests/test_active_product_scope_policy.py
```

현재 제품 방향과 개발 우선순위는
[`ACTIVE_PRODUCT_SCOPE.md`](../../docs/specs/product/ACTIVE_PRODUCT_SCOPE.md)의 current development priority가
소유한다. 이 문서는 그 방향을 다시 서술하지 않는다. 일반 과목 reliability 완료 계약이 필요할 때만
[`CORE_QUIZ_RELIABILITY_STABILIZATION.md`](../../docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md)를
함께 읽는다.

## 6. 저장소 대표 명령

다음은 현재 저장소의 대표 entry다. 작업에 필요한 항목만 선택한다.

```bash
just verify
just lint
just typecheck
just test
just ci
bash ./verify.sh
```

문서 정책 focused test:

```bash
uv run pytest -q tests/test_core_quiz_reliability_policy.py
uv run pytest -q tests/test_agent_registry_consistency.py
uv run pytest -q tests/test_planning_workflow_consistency.py
uv run pytest -q tests/test_core_agent_contract_consistency.py
```

일반 과목 관련 기존 출발점:

```bash
uv run pytest -q tests/test_math_next_question_progression.py
uv run pytest -q tests/test_nonmath_next_question_progression.py
uv run pytest -q tests/test_nonmath_browser_acceptance.py
```

기존 테스트가 과목 완료 계약 전체를 자동 충족한다고 가정하지 않는다.

## 7. 정적 진단 closure

- 작업 시작 시 수정 파일과 직접 영향 모듈의 baseline을 확인한다.
- 현재 변경이 만든 lint/type 오류는 반드시 제거한다.
- 수정 파일과 직접 영향 모듈에 남은 오류를 `pre-existing`이라는 이유로 PASS 처리하지 않는다.
- 서로 다른 원인의 오류는 별도 failure domain으로 순차 해결한다.
- workspace root, interpreter, dependency, stale cache, generated/vendor 오분석이면 환경을 먼저 바로잡는다.
- broad ignore, `type: ignore`, `noqa`, 검사 대상 축소, baseline·snapshot 갱신으로 녹색을 만들지 않는다.

현재 criterion을 안전하게 닫을 수 없으면 정확한 재현 명령과 원인을 포함해 `BLOCKED`로 보고한다.

## 8. 브라우저 검증

브라우저 증거가 필요한 경우 다음을 고려한다.

- 실제 지원 entry를 HTTP로 연다.
- browser-generated input을 사용한다.
- page error와 `requestfailed`를 수집한다.
- 문제 identity, 상태 초기화, disabled/focus/feedback를 사용자 흐름에서 확인한다.
- 정답과 오답 경로를 구분한다.
- 마지막 문제와 재시작 경계를 확인한다.
- flake 판정이 필요한 계약은 문서에 정의된 반복 횟수를 적용한다.

테스트 편의를 위해 production API를 무력화하거나 실제 입력 경계를 건너뛰지 않는다.

## 9. build·artifact·rollback

- authoring source와 generated artifact를 구분한다.
- source 변경이 artifact에 영향을 줄 때만 rebuild한다.
- clean rebuild와 tracked artifact의 일치를 확인한다.
- 결정성이 계약이면 반복 build의 byte identity를 확인한다.
- rollback 경계를 변경했다면 production과 rollback을 같은 기준에서 검증한다.
- proof-only artifact를 production authority로 오인하지 않는다.

## 10. BLOCKED 사유와 blocker가 아닌 것

`BLOCKED`는 다음 사유에만 사용한다.

- `DECISION_REQUIRED`: 필수 정보가 없어 실행 자체가 불가능하거나, 서로 양립할 수 없는 해석이 결과를
  크게 바꾸거나, 사용자 가시 동작·제품 방향·수정 범위·acceptance criterion·사용자 데이터 무결성 또는
  안전 경계를 바꿔야만 완료할 수 있을 때
- `PRIMARY_UNEVALUABLE`: 필수 criterion을 실행하지 못해 PASS로 보고할 수 없을 때
- `SEMANTIC_OVERLAP`: 현재 변경이 선언된 경계 안에서 다른 owner의 계약을 덮어써야만 닫힐 때
- `SAFETY_BOUNDARY`: 현재 failure domain 안에서 안전하게 닫을 수 없는 정적 오류나 보호 상태 전이가
  남을 때
- V1 또는 필수 V2 검증 실패를 현재 failure domain 안에서 안전하게 닫을 수 없을 때

다음은 면책 사유가 아니라 blocker도 아니다.

- remote advance와 non-fast-forward
- unrelated dirty state
- V3 시스템 smoke 실패
- 새로 발견한 독립 결함
- 다른 세션의 선행 게시

## 11. 문서와 상태 결합 방지

제품 테스트는 사용자 동작, 타입, build, artifact, rollback을 검증한다.
다음은 제품 테스트의 PASS/FAIL criterion이 아니다.

- 다음 WP
- 현재 WP
- plan의 COMPLETE 문자열
- 일정 header
- 수동 진행 체크박스
- evidence 파일의 존재만으로 추정한 완료 상태

문서 drift를 막기 위한 test는 stable authority, 링크, 실제 명령, 동결 정책을 검증해야 한다.

## 12. 검증 결과 기록

`PRIMARY_VERIFY`와 `DIRECT_VERIFY`에는 실제 실행한 명령 또는 판정 방법과 결과를 적는다.

- 실행 횟수와 통과 수
- browser error/request failure 수
- build·artifact identity
- diff scope
- remote fast-forward 확인

실행 환경 제약으로 검증하지 못한 항목이 있으면 그 한계를 명시한다.
도구 출력의 존재만으로 실행 성공을 추정하지 않는다.

## 13. 보안

검증 로그와 보고에 API key, token, cookie, password, `.env` 원문을 포함하지 않는다.
민감값은 마스킹된 식별 정보만 사용한다.