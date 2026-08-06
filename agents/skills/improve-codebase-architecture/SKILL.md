---
name: improve-codebase-architecture
description: 실제 caller·invariant·cleanup을 기준으로 AidenGame module depth와 seam을 검토하는 architecture skill
metadata:
  version: "2.0.0"
---
<!-- Language: ko -->

# Improve codebase architecture skill

workflow 진입점은 [`improve-codebase-architecture.md`](../../workflows/improve-codebase-architecture.md)다.

## 1. 용어

- **Module:** interface와 implementation을 가진 책임 단위
- **Interface:** caller가 알아야 하는 입력, 출력, invariant, ordering, error, lifecycle
- **Depth:** 작은 interface 뒤에 숨겨진 유효 동작과 규칙의 양
- **Seam:** 동작을 교체하거나 검증할 수 있는 interface 위치
- **Adapter:** seam의 구체 구현
- **Locality:** 변경과 지식이 한 책임에 모이는 정도
- **Leverage:** caller가 적은 지식으로 얻는 동작

용어보다 현재 AidenGame code와 product vocabulary를 우선한다.

## 2. explore

- import와 runtime call을 따라 실제 module 경계를 확인한다.
- 한 개념을 이해하기 위해 여러 파일을 왕복해야 하는 이유를 찾는다.
- caller가 반복하는 validation, ordering, state reset, cleanup을 찾는다.
- pure helper로 분리됐지만 실제 bug가 orchestration에 남는지 확인한다.
- interface와 implementation의 복잡도가 거의 같은 pass-through wrapper를 찾는다.

## 3. deletion test

module을 제거한다고 가정한다.

- 복잡성이 사라지면 불필요한 wrapper일 수 있다.
- 동일 복잡성이 여러 caller에 재등장하면 module이 depth를 제공할 수 있다.
- caller 하나뿐이고 교체 가능성도 없으면 hypothetical seam을 만들지 않는다.
- 두 adapter 또는 동일 lifecycle을 공유하는 여러 caller가 있을 때 seam의 실재성을 검토한다.

## 4. interface 최소화

새 interface는 다음을 숨겨야 한다.

- per-question transient state reset
- duplicate input guard
- event·pointer·timer ownership
- ordering과 idempotency
- fallback 선택
- persistence와 session state 구분
- error·no-op 조건

method 수가 적다는 이유만으로 deep module은 아니다. caller가 내부 순서와 invariants를 계속 알아야 하면 shallow하다.

## 5. 후보 비교

여러 interface가 실제로 다른 trade-off를 만들 때만 비교한다.

- minimal common contract
- subject-specific configuration
- lifecycle owner
- ports/adapters가 필요한 외부 dependency

각 후보에서 caller code, hidden rules, failure modes, migration cost, test seam을 설명한다.
권장안은 현재 use case와 검증 가능성을 기준으로 하나만 고른다.

## 6. AidenGame 적용

### 일반 과목

- 첫 과목은 기존 구조 안에서 안정화한다.
- 두 번째 과목에서 answer/feedback/next/final/restart 책임이 반복될 때 shared module을 검토한다.
- 과목별 question data와 pedagogy 차이를 억지로 하나의 interface에 넣지 않는다.

### Ocean Rescue와 experiments

현재 신규 architecture migration은 동결 상태다.
명시적 재개나 치명적 유지보수 예외가 없으면 분석 결과를 implementation으로 전환하지 않는다.

## 7. migration

- characterization 또는 interface contract를 먼저 확인한다.
- source와 caller를 한 boundary씩 이동한다.
- old state와 bridge를 제거한다.
- fallback과 cleanup을 검증한다.
- shared boundary 변경이면 모든 실제 caller regression을 실행한다.
- artifact 영향은 별도 판정 경계로 다룬다.

## 8. 완료

architecture 개선은 다음이 모두 참일 때만 완료다.

- caller 지식이 줄었음
- invariants와 cleanup이 한 owner에 모임
- interface가 실제 use case를 가짐
- duplicate state와 orchestration이 제거됨
- public behavior가 보존됨
- test가 interface를 통해 실패를 잡음
- 현재 동결·제품 우선순위를 위반하지 않음
