---
scope:
- '*'
always_apply: false
priority: 1
domain: core
last_verified: 2026-08-06
verify_with:
- uv run pytest -q tests/test_core_agent_contract_consistency.py
---
<!-- Language: ko -->

# AidenGame 검증 규칙

이 문서는 변경 위험에 맞는 검증 선택과 PASS/BLOCKED 판정을 정의한다.
실제 명령은 최신 `Justfile`, `verify.sh`, package 설정, 테스트 파일을 우선한다.

## 1. 기본 원칙

- 검증은 현재 failure domain을 판정하는 가장 작은 항목부터 시작한다.
- 파일이나 명령이 존재한다고 추측하지 않는다.
- 같은 명령으로 수정 전후를 비교할 수 있으면 동일 criterion을 유지한다.
- 실행하지 않은 검증을 PASS로 보고하지 않는다.
- 전체 suite는 공유 cutover, 광범위한 회귀 위험, 저장소 정책이 요구할 때만 실행한다.

## 2. 검증 범위

| 변경 유형 | 최소 검증 |
|---|---|
| 문서·규칙 | 링크, 경로, 실제 명령, authority·동결 정책, focused document test |
| Python 테스트·도구 | Ruff, 관련 pytest, 필요한 typecheck |
| 일반 과목 JavaScript/UI | 직접 상태 계약, 해당 과목 browser flow, 영향받는 과목 regression |
| 공용 `shared/` | 영향을 받는 모든 완료 과목의 상태·브라우저 계약 |
| 배포 entry·라우팅 | 실제 entry와 `vercel.json`, 관련 routing test |
| Ocean Rescue 유지보수 예외 | 직접 focused test, 필요한 typecheck/browser/build/artifact/rollback |
| generated artifact | clean rebuild, deterministic identity, drift, 필요한 rollback |

현재 일반 과목의 subject completion contract는
[`CORE_QUIZ_RELIABILITY_STABILIZATION.md`](../../docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md)를 따른다.

## 3. 저장소 대표 명령

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

## 4. 정적 진단 closure

- 작업 시작 시 수정 파일과 직접 영향 모듈의 baseline을 확인한다.
- 현재 변경이 만든 lint/type 오류는 반드시 제거한다.
- 수정 파일과 직접 영향 모듈에 남은 오류를 `pre-existing`이라는 이유로 PASS 처리하지 않는다.
- 서로 다른 원인의 오류는 별도 failure domain으로 순차 해결한다.
- workspace root, interpreter, dependency, stale cache, generated/vendor 오분석이면 환경을 먼저 바로잡는다.
- broad ignore, `type: ignore`, `noqa`, 검사 대상 축소, baseline·snapshot 갱신으로 녹색을 만들지 않는다.

현재 criterion을 안전하게 닫을 수 없으면 정확한 재현 명령과 원인을 포함해 `BLOCKED`로 보고한다.

## 5. 브라우저 검증

브라우저 증거가 필요한 경우 다음을 고려한다.

- 실제 지원 entry를 HTTP로 연다.
- browser-generated input을 사용한다.
- page error와 `requestfailed`를 수집한다.
- 문제 identity, 상태 초기화, disabled/focus/feedback를 사용자 흐름에서 확인한다.
- 정답과 오답 경로를 구분한다.
- 마지막 문제와 재시작 경계를 확인한다.
- flake 판정이 필요한 계약은 문서에 정의된 반복 횟수를 적용한다.

테스트 편의를 위해 production API를 무력화하거나 실제 입력 경계를 건너뛰지 않는다.

## 6. build·artifact·rollback

- authoring source와 generated artifact를 구분한다.
- source 변경이 artifact에 영향을 줄 때만 rebuild한다.
- clean rebuild와 tracked artifact의 일치를 확인한다.
- 결정성이 계약이면 반복 build의 byte identity를 확인한다.
- rollback 경계를 변경했다면 production과 rollback을 같은 기준에서 검증한다.
- proof-only artifact를 production authority로 오인하지 않는다.

## 7. 문서와 상태 결합 방지

제품 테스트는 사용자 동작, 타입, build, artifact, rollback을 검증한다.
다음은 제품 테스트의 PASS/FAIL criterion이 아니다.

- 다음 WP
- 현재 WP
- plan의 COMPLETE 문자열
- 일정 header
- 수동 진행 체크박스
- evidence 파일의 존재만으로 추정한 완료 상태

문서 drift를 막기 위한 test는 stable authority, 링크, 실제 명령, 동결 정책을 검증해야 한다.

## 8. 검증 결과 기록

`VERIFY`에는 실제 실행한 명령 또는 판정 방법과 결과를 한 문장으로 적는다.

- 실행 횟수와 통과 수
- browser error/request failure 수
- build·artifact identity
- diff scope
- remote fast-forward 확인

실행 환경 제약으로 검증하지 못한 항목이 있으면 그 한계를 명시한다.
도구 출력의 존재만으로 실행 성공을 추정하지 않는다.

## 9. 보안

검증 로그와 보고에 API key, token, cookie, password, `.env` 원문을 포함하지 않는다.
민감값은 마스킹된 식별 정보만 사용한다.
