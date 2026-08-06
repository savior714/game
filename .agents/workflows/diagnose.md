---
situation: 재현 가능한 버그·성능 회귀·간헐 실패 진단
level: Recommended
description: 빠른 판정 루프를 만든 뒤 원인 하나를 증거로 닫는 진단 workflow
version: 2.0.0
last_updated: 2026-08-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Diagnose workflow

상세 절차는 [`diagnose/SKILL.md`](../skills/diagnose/SKILL.md)를 따른다.
실행·검증·보고의 상위 계약은 [`AGENTS.md`](../../AGENTS.md), [`execution.md`](../core/execution.md), [`verification.md`](../core/verification.md)다.

## 1. 사용 조건

다음 중 하나가 있을 때 사용한다.

- 사용자 흐름이 재현 가능하게 중단됨
- 특정 상태·입력·환경에서 잘못된 결과가 발생함
- 반복 실행 중 간헐적으로 실패함
- 성능이 이전 기준보다 명확히 악화됨
- page error, request failure, build failure 또는 artifact drift가 있음

단순 코드 탐색이나 수정 없는 현황 파악은 [`investigate.md`](investigate.md)를 사용한다.

## 2. 현재 제품 방향

범위가 지정되지 않은 진단은 `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`를 따른다.

- Math, English, Korean, Science 일반 문제풀이를 우선한다.
- Ocean Rescue와 `experiments/` 신규 기능·구조 이전은 자동 재개하지 않는다.
- 동결 범위는 사용자의 현재 명시적 요청 또는 치명적 운영 회귀·데이터 손상·보안 문제일 때만 예외로 다룬다.
- 과거 보고에 등장한 오류는 최신 main에서 같은 조건으로 재현되는지 먼저 확인한다.

## 3. 진단 순서

1. 사용자가 설명한 증상을 한 문장으로 고정한다.
2. 최신 `origin/main`에서 가장 작은 재현 경로를 만든다.
3. 성공·실패를 판정하는 binary criterion을 정한다.
4. source, caller, state, event, network, persistence 또는 build 경계를 추적한다.
5. 증거가 구분하지 못하는 원인에만 가설을 세운다.
6. 한 번에 변수 하나만 바꾸거나 계측한다.
7. 원인 하나가 증상 전체를 설명하는지 확인한다.
8. 수정이 요청 범위에 포함되면 최소 변경과 회귀 계약을 적용한다.
9. 원래 재현 경로와 직접 영향 회귀를 다시 실행한다.
10. 임시 로그·fixture·instrumentation을 제거한다.

가설 개수나 사용자 체크포인트를 형식적으로 강제하지 않는다.
저장소 증거로 진행할 수 있으면 중간 확인을 기다리지 않고 계속한다.

## 4. 브라우저 진단

일반 과목 브라우저 문제에서는 다음 신호를 우선한다.

- 실제 운영 entry가 열리는가
- 문제 identity가 실제로 변경되는가
- 정답·오답 후 피드백과 다음 행동이 일관적인가
- 다음 문제에서 선택·style·feedback·disabled·focus 상태가 초기화되는가
- 마지막 문제와 재시작 경계가 정상인가
- 중복 click, key repeat, pointer 재진입이 두 번 진행시키지 않는가
- `pageerror`와 `requestfailed`가 0인가

실제 browser-generated input을 사용하고 production API를 테스트 편의상 무력화하지 않는다.

## 5. 수정 경계

- 한 진단 실행에서 한 failure domain만 수정한다.
- 같은 원인을 닫는 source, caller, test, cleanup은 함께 변경할 수 있다.
- 다른 과목의 별도 결함, 선제 공용화, 순수 시각 개선을 섞지 않는다.
- 진단 결과가 문서·설정 drift라면 runtime code를 억지로 바꾸지 않는다.
- 정확한 원인을 확인하지 못하면 추측 패치를 적용하지 않는다.

## 6. 완료 조건

- 원래 증상이 동일 재현 조건에서 사라짐
- 원인을 설명하는 증거가 있음
- 회귀 test 또는 동등한 반복 가능한 판정이 있음
- 임시 계측이 제거됨
- 수정 파일과 직접 영향 모듈의 필수 정적 진단이 0임
- 실행하지 못한 criterion이 있다면 PASS가 아니라 BLOCKED로 보고함

## 7. 보고

```text
RESULT: PASS | BLOCKED
CHANGE: <확정한 원인과 수정 한 문장>
VERIFY: <재현·회귀 판정과 결과 한 문장>
```

실제 게시 시에만 `COMMIT`, 안전하게 닫지 못했을 때만 `BLOCKER`와 `NEXT`를 추가한다.
