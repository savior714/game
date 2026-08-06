---
situation: 동작을 보존하면서 책임·상태·경계를 정리하는 리팩터링
level: Conditional
description: 실제 구조적 마찰과 검증 가능한 boundary가 있을 때만 수행하는 refactor workflow
version: 2.0.0
last_updated: 2026-08-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Refactor workflow

상세 절차는 [`refactor/SKILL.md`](../skills/refactor/SKILL.md)를 따른다.

## 1. 진입 조건

다음이 확인됐을 때 사용한다.

- 동일 책임이 두 개 이상의 실제 caller에서 반복됨
- 상태·event·timer·cleanup ownership이 여러 파일에 흩어짐
- public interface보다 caller가 알아야 할 내부 규칙이 지나치게 많음
- 변경할 때마다 같은 regression이 여러 경로에서 반복됨
- 현재 test seam이 실제 boundary를 검증하지 못함

버그 원인이 단순한 국소 결함이면 먼저 diagnose workflow로 수정한다.
리팩터링은 결함 수정의 이름을 바꾸는 수단이 아니다.

## 2. 현재 범위

일반 과목 안정화 중에는:

- 첫 대표 과목을 선제적으로 shared engine으로 이전하지 않는다.
- 두 번째 과목에서 동일 책임이 실제 반복된 뒤에만 공용화를 검토한다.
- Ocean Rescue와 실험 기능의 신규 ownership 이전을 자동 재개하지 않는다.
- 순수 시각 정리와 미래 확장용 abstraction을 우선하지 않는다.

## 3. 분석

1. current caller와 state flow를 확인한다.
2. 현재 public contract와 숨겨야 할 내부 규칙을 구분한다.
3. fallback·legacy·generated artifact 경계를 확인한다.
4. deletion test로 현재 abstraction의 가치가 있는지 확인한다.
5. 새로운 seam이 실제 두 번째 사용처 또는 명확한 test boundary를 갖는지 확인한다.
6. 동작 보존 criterion과 직접 regression을 정의한다.

## 4. 실행 단위

한 리팩터링 작업은 하나의 semantic boundary만 다룬다.

- 특정 per-question state reset
- 특정 event listener ownership
- 특정 timer registry
- 특정 shared UI control
- 특정 source/generated artifact boundary

여러 ownership 이전, browser proof, artifact 게시, 계획 갱신을 한 패치에 묶지 않는다.

## 5. 구현

- public behavior를 고정하는 characterization 또는 focused contract를 확인한다.
- 새로운 interface는 caller가 알아야 하는 정보를 줄여야 한다.
- adapter·callback·configuration은 실제 차이가 있을 때만 둔다.
- source와 caller를 새 seam으로 이동한다.
- 이전 implementation과 dead bridge를 안전하게 제거한다.
- cleanup과 fallback을 함께 검증한다.

무코드 논의만 요청받았다면 구현하지 않고 boundary와 criterion만 제시한다.
사용자가 실제 리팩터링을 요청했다면 별도 plan handoff를 강제하지 않고 현재 단일 작업을 수행할 수 있다.

## 6. 검증

- 동작 보존 focused test
- 새 interface의 state·error·ordering contract
- 영향을 받는 caller regression
- 필요한 실제 browser flow
- 수정 파일과 직접 영향 모듈 정적 진단
- shared 또는 artifact boundary면 영향 범위에 맞는 추가 검증

## 7. 완료

- caller가 알아야 할 규칙이 줄어듦
- 동일 책임의 source of truth가 하나가 됨
- 이전 bridge·duplicate state가 제거됨
- public behavior와 fallback이 보존됨
- 새 abstraction이 실제 use case를 가짐
- unrelated migration이나 future work가 포함되지 않음
