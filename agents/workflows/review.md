---
situation: 변경 diff 또는 현재 파일의 정확성·회귀 위험 검토
level: Recommended
description: findings-first 방식으로 구체적인 실패 시나리오와 근거를 제시하는 review workflow
version: 2.0.0
last_updated: 2026-08-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Review workflow

상세 절차는 [`review/SKILL.md`](../skills/review/SKILL.md)를 따른다.

## 1. 검토 대상

우선순위:

1. 사용자가 지정한 commit, diff, 파일 또는 기능
2. 현재 branch가 명확하면 base 대비 diff
3. diff가 없고 특정 파일을 요청했다면 현재 파일의 정적 계약

검토 범위를 임의로 저장소 전체로 확대하지 않는다.

## 2. 리뷰 원칙

- findings를 요약보다 먼저 제시한다.
- 각 finding은 구체적인 실패 시나리오와 코드·문서 근거를 가진다.
- 정확성, 상태 오염, 회귀, 보안, cleanup, artifact authority를 style보다 우선한다.
- formatter·lint가 처리할 사소한 선호는 제외한다.
- 증거가 약한 우려는 finding으로 승격하지 않는다.
- 일정 상태와 과거 plan 문자열을 제품 동작 finding으로 취급하지 않는다.

## 3. 현재 제품 방향

범위가 지정되지 않은 review follow-up은 일반 과목 안정화 우선순위를 따른다.

- 동결된 Ocean Rescue·실험 기능의 신규 구조 개선을 자동 권장하지 않는다.
- 일반 과목에서 수정 범위가 넓어지면 첫 사용자 failure domain을 우선한다.
- 공용화는 두 번째 실제 과목에서 동일 책임이 확인된 경우에만 검토한다.

## 4. 결과 형식

심각도 순으로 작성한다.

```text
[High|Medium|Low] <제목>
- 영향: <어떻게 실패하는가>
- 근거: <파일·symbol·조건>
- 수정 경계: <최소 안전 수정>
```

실질적인 finding이 없으면 그 사실과 남은 검증 한계를 명확히 적는다.

## 5. 후속 처리

- 사용자가 수정까지 요청했다면 첫 actionable finding 하나를 단일 failure domain으로 처리한다.
- 리뷰만 요청했다면 결과를 제공하고 종료한다.
- 종료 시 사용자 선택 질문을 형식적으로 강제하지 않는다.
- review 결과를 자동으로 Blueprint 파일로 변환하지 않는다.
- 여러 finding의 장기 계획은 사용자가 저장소 Blueprint를 명시적으로 요청한 경우에만 문서화한다.

## 6. 완료 조건

- 검토 범위가 명확함
- 모든 finding이 재현 가능한 실패 시나리오와 근거를 가짐
- 중복·추측·style noise가 제거됨
- 검증하지 못한 runtime behavior를 source만으로 확정하지 않음
- 사용자 요청이 review-only면 repository mutation이 없음
