---
situation: 명시적으로 요청된 모듈 경계·interface·ownership 구조 검토
level: Conditional
description: 실제 caller와 반복 책임을 기준으로 architecture deepening 후보를 검토하는 workflow
version: 2.0.0
last_updated: 2026-08-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Improve codebase architecture workflow

상세 절차는 [`improve-codebase-architecture/SKILL.md`](../skills/improve-codebase-architecture/SKILL.md)를 따른다.

## 1. 사용 조건

- 사용자가 architecture 또는 module/interface 개선을 명시적으로 요청함
- 반복 defect가 module boundary와 직접 연결됨
- 여러 caller가 같은 invariants·ordering·cleanup을 알아야 함
- 기존 abstraction이 pass-through라 locality와 leverage를 만들지 못함

현재 runtime defect를 국소 수정할 수 있으면 architecture redesign보다 diagnose를 우선한다.

## 2. 현재 제품 경계

- 일반 과목 첫 안정화 과목에서는 선제 architecture 통합을 하지 않는다.
- 두 번째 과목에서 동일 책임이 확인된 뒤 shared seam을 검토한다.
- Ocean Rescue와 실험 기능의 신규 architecture 이전은 현재 동결한다.
- file length나 AI 탐색 편의만으로 production boundary를 바꾸지 않는다.

## 3. 검토 순서

1. 현재 entry, caller, state owner, test seam을 확인한다.
2. module 삭제 시 복잡성이 caller로 퍼지는지 deletion test를 적용한다.
3. interface가 숨기지 못하는 invariants와 lifecycle을 식별한다.
4. 실제 두 번째 adapter·caller가 있는지 확인한다.
5. deepening이 현재 defect 또는 반복 변경 비용을 줄이는지 확인한다.
6. 최소 interface와 migration boundary를 제안한다.
7. public behavior와 rollback criterion을 정의한다.

## 4. 결과

후보마다 다음을 제시한다.

- 현재 module과 caller
- shallow interface 또는 ownership 문제
- deepened module이 숨길 규칙
- 실제 seam과 adapter
- locality·leverage 효과
- migration non-goal
- 검증 criterion

후보 목록은 actionable한 항목만 최대 3개로 제한한다.

## 5. 후속 처리

- 분석만 요청받았다면 코드를 수정하지 않는다.
- 구현까지 요청받았다면 첫 architecture boundary 하나만 처리한다.
- 여러 interface안을 형식적으로 생성하거나 사용자 선택을 강제하지 않는다.
- 저장소 Blueprint는 명시적 요청이 있을 때만 작성한다.
