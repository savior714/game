---
name: review
description: AidenGame 변경의 정확성·회귀·상태·보안 위험을 findings-first로 검토하는 skill
metadata:
  version: "2.0.0"
---
<!-- Language: ko -->

# Review skill

workflow 진입점은 [`review.md`](../../workflows/review.md)다.

## 1. 범위 설정

- 명시된 commit 또는 diff가 있으면 그것을 기준으로 한다.
- 현재 branch review라면 base와 head를 확인한다.
- 특정 파일 정적 review라면 변경 회귀가 아니라 현재 상태 위험임을 구분한다.
- unrelated repository area를 탐색하지 않는다.

## 2. 검토 순서

1. changed files와 semantic boundary를 확인한다.
2. 사용자 가시 흐름 또는 runtime caller를 추적한다.
3. state, event, timer, pointer, persistence, build boundary를 확인한다.
4. 기존 focused test가 실제 위험을 잡는지 확인한다.
5. fallback, rollback, generated artifact 영향이 있는지 확인한다.
6. concrete failure scenario가 있는 항목만 finding으로 남긴다.

## 3. 우선 위험

### 일반 과목

- question identity가 바뀌지 않음
- answer/feedback/disabled state가 다음 문제에 누출됨
- 정답 또는 오답 한 경로만 진행 가능
- 중복 click·key·pointer로 두 번 진행
- final/restart 실패
- localStorage 통계와 transient state 혼합
- touch target·focus·overlay 때문에 진행 불가

### 공통 runtime

- listener·timer·pointer capture cleanup 누락
- duplicate binding
- stale closure 또는 shared mutable state
- silent failure와 fail-open fallback
- source와 generated artifact authority 혼동
- production과 rollback 경계 파괴
- credential 또는 외부 입력 검증 누락

## 4. 근거 기준

finding에는 다음이 모두 있어야 한다.

1. 어느 입력·상태에서 실패하는가
2. 사용자 또는 운영 영향은 무엇인가
3. 어느 코드·문서 조건이 원인인가
4. 어떤 최소 변경으로 닫을 수 있는가
5. 어떤 검증이 재발을 잡는가

“아마”, “보통”, “깔끔하지 않음”만으로 finding을 만들지 않는다.
source inspection만으로 browser runtime을 확정할 수 없으면 추가 검증 필요로 표시한다.

## 5. 심각도

- **High:** 사용 흐름 중단, 데이터 손상, 보안, production/rollback 파괴
- **Medium:** 특정 입력에서 잘못된 상태, 회귀 가능성이 높은 계약 공백
- **Low:** 실제 실패가 있으나 영향이 제한적이고 우회가 명확함

style, naming, formatter 대상은 원칙적으로 제외한다.

## 6. 수정 요청이 포함된 경우

- 가장 높은 actionable finding 하나를 선택한다.
- 한 failure domain과 binary criterion을 고정한다.
- 같은 원인의 source, caller, test, cleanup만 수정한다.
- 나머지 finding은 현재 patch에 섞지 않는다.
- 수정 후 원래 finding의 실패 시나리오와 직접 회귀를 확인한다.

사용자가 review-only를 요청했다면 코드를 변경하지 않는다.

## 7. 종료

- 필수 질문이나 handoff menu를 자동으로 붙이지 않는다.
- 리뷰 결과를 자동 plan 파일로 만들지 않는다.
- actionable finding이 없으면 “발견 없음”과 확인한 범위·남은 검증 한계를 보고한다.
- 사용자가 후속 수정을 요청하면 그때 첫 failure domain으로 진행한다.

## 8. 출력

findings가 있으면 심각도 순으로 먼저 제시한다.
그 뒤에 범위와 검증 한계를 짧게 정리한다.
요약부터 시작해 중요한 finding을 묻히지 않는다.
