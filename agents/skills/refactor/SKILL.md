---
name: refactor
description: AidenGame의 동작을 보존하며 실제 반복 책임과 ownership을 검증 가능한 seam으로 정리하는 skill
metadata:
  version: "2.0.0"
---
<!-- Language: ko -->

# Refactor skill

workflow 진입점은 [`refactor.md`](../../workflows/refactor.md)다.

## 1. 리팩터링 자격

다음 질문에 답한다.

- 현재 사용자 동작은 무엇인가
- 구조가 어떤 반복 결함 또는 변경 비용을 만들었는가
- 동일 책임이 어디에서 반복되는가
- 어떤 caller가 내부 구현 세부사항을 과도하게 아는가
- 새 seam을 검증할 실제 use case가 있는가

명확한 구조적 마찰이 없으면 리팩터링하지 않는다.

## 2. 현재 구조 지도

최소한 다음을 그린다.

- entry와 caller
- state owner
- event·timer·pointer lifecycle owner
- render 또는 persistence boundary
- fallback·legacy path
- focused test seam

문서의 과거 architecture 설명보다 현재 import와 runtime call을 우선한다.

## 3. deep module 판단

좋은 module은 작은 interface 뒤에 많은 유효한 동작과 불변조건을 숨긴다.

- caller가 전달해야 할 state가 줄어드는가
- ordering과 error mode가 module 안으로 들어가는가
- cleanup이 한 소유자에게 모이는가
- 두 caller가 같은 규칙을 재구현하지 않는가
- test가 실제 interface를 통해 동작을 검증할 수 있는가

단순 pass-through wrapper는 제거하거나 만들지 않는다.

## 4. interface 설계

interface에는 signature뿐 아니라 다음을 포함한다.

- 입력과 출력
- 허용 state와 transition
- ordering
- idempotency
- error 또는 no-op 조건
- lifecycle 시작·종료
- cleanup 책임

옵션을 여러 개 제시해야 할 때만 사용자 결정축을 하나로 좁힌다.
모든 리팩터링에서 3개 interface안을 형식적으로 만들지 않는다.

## 5. 테스트 순서

1. 현재 public behavior와 failure mode를 고정한다.
2. 새 seam을 통해 같은 동작을 증명할 contract를 만든다.
3. implementation과 caller를 이동한다.
4. duplicate state와 old bridge를 제거한다.
5. 직접 caller와 fallback regression을 실행한다.
6. 필요한 browser 또는 artifact 검증으로 확장한다.

테스트만 위해 production interface를 부풀리지 않는다.

## 6. 일반 과목 공용화

첫 과목에서는 현재 구조 안에서 안정화한다.
두 번째 과목에서 같은 책임이 확인되면 다음을 비교한다.

- DOM contract
- state transition
- correct/incorrect policy
- next/final/restart lifecycle
- persistence와 transient state 경계
- subject-specific data 차이

계약이 같지 않으면 shared abstraction보다 과목별 구현을 유지한다.

## 7. 동결 기능

Ocean Rescue와 `experiments/`의 architecture 개선은 현재 방향에서 제외된다.
사용자의 명시적 재개 또는 허용 예외가 없으면 후보 분석을 구현으로 전환하지 않는다.

## 8. 완료 점검

- public behavior 보존
- 새 seam에 실제 caller 둘 또는 명확한 lifecycle owner가 있음
- interface가 implementation보다 단순함
- duplicate source와 state 제거
- cleanup과 idempotency 검증
- 직접 회귀와 정적 진단 통과
- plan·evidence 상태 변경 없음

리팩터링 완료 후 다음 구조 개선을 관성적으로 이어가지 않는다.
