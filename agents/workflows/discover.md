---
situation: 현재 범위 안의 기술 부채·검증 공백·반복 결함 후보 탐색
level: Conditional
description: 저장소 증거에서 실행 가능한 후보를 찾되 자동 plan·queue를 만들지 않는 discover workflow
version: 2.0.0
last_updated: 2026-08-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Discover workflow

상세 절차는 [`discover/SKILL.md`](../skills/discover/SKILL.md)를 따른다.

## 1. 사용 조건

- 사용자가 개선 후보나 기술 부채 탐색을 명시적으로 요청함
- 현재 기능 안정화 중 다음 failure domain을 증거로 선택해야 함
- 테스트·문서·도구의 반복 drift를 감사해야 함
- 특정 영역의 구조적 마찰을 우선순위화해야 함

범위가 없는 “다음 작업”은 discover 메뉴가 아니라 현재 [`CORE_QUIZ_RELIABILITY_STABILIZATION.md`](../../docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md) 공통 진단으로 해석한다.

## 2. 기본 원칙

- 기본적으로 read-only다.
- 사용자 선택 메뉴를 형식적으로 강제하지 않는다.
- queue JSON, timestamp Blueprint, backlog를 자동 생성하지 않는다.
- 파일 길이·복잡도 숫자만으로 후보를 만들지 않는다.
- 실제 사용자 실패, 반복 변경 비용, 검증 공백, ownership 혼란을 근거로 후보를 만든다.
- 동결된 Ocean Rescue·실험 기능의 구조 개선 후보를 현재 실행 대상으로 추천하지 않는다.

## 3. 탐색 순서

1. 사용자가 지정한 제품·경로·문제 범위를 확인한다.
2. 현재 authority와 직접 관련 code/test를 읽는다.
3. 사용자 흐름, state ownership, duplication, cleanup, test gap을 조사한다.
4. 후보마다 구체적인 실패 또는 반복 비용을 확인한다.
5. 이미 해결됐거나 현재 main에서 재현되지 않는 후보를 제거한다.
6. 현재 제품 방향 안에서 첫 actionable candidate 하나를 권장한다.
7. 후보의 재현 조건, binary criterion, non-goal을 정리한다.

## 4. 후보 유형

- 사용자 진행을 막는 runtime defect
- 문제별 state reset 또는 final/restart 공백
- 중복 input·listener·timer lifecycle
- 두 과목에서 실제로 반복된 동일 책임 (동일 책임의 두 번째 실제 사용처)
- browser evidence 또는 static contract 공백
- stale authority·broken link·가짜 command
- generated artifact와 source ownership drift
- 수정 파일의 정적 진단 오류

단순 naming 선호, 미래 확장 가능성, 한 번만 나타난 코드 유사성은 우선 후보가 아니다.

## 5. 결과

```text
CANDIDATE: <실행 가능한 첫 후보>
EVIDENCE: <현재 code/test/runtime 근거>
IMPACT: <사용자 또는 유지보수 영향>
BOUNDARY: <한 failure domain과 non-goal>
CRITERION: <PASS/FAIL 판정>
```

여러 후보를 나열해야 하면 최대 3개로 제한하고 우선순위 근거를 명시한다.

## 6. 후속 처리

- 사용자가 구현을 요청하면 첫 candidate 하나만 실행한다.
- 사용자가 저장소 Blueprint를 명시적으로 요청한 경우에만 plan workflow로 전환한다.
- discovery 결과를 자동으로 `docs/plans/`, artifact queue, backlog에 쓰지 않는다.
- 후보가 없으면 확인한 범위와 “material candidate 없음”을 보고한다.
