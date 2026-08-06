---
situation: 사용자가 저장소 Blueprint를 명시적으로 요청함
level: Conditional
description: 명시적으로 선택된 저장소 Blueprint의 작성·검증·실행 경계
version: 2.0.0
last_updated: 2026-08-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# 명시적 Blueprint 워크플로우

이 워크플로우는 사용자가 **저장소에 Blueprint 또는 plan 문서를 만들라고 명시적으로 요청한 경우에만** 적용한다.
일반적인 “계획해줘”, “다음 작업 정리”, “이어서 진행”, 로컬 프롬프트 요청은 채팅에서 처리하며 plan 파일을 만들지 않는다.

현재 일반 과목 안정화 방향과 실행 우선순위는
[`AGENTS.md`](../../AGENTS.md),
[`PROJECT_RULES.md`](../../PROJECT_RULES.md),
[`CORE_QUIZ_RELIABILITY_STABILIZATION.md`](../../docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md)를 따른다.

## 1. 진입 조건

다음 조건 중 하나가 분명할 때만 저장소 Blueprint를 작성한다.

- 사용자가 “저장소에 Blueprint를 만들어라”라고 요청함
- 사용자가 구체적인 `docs/plans/...` 파일의 생성·수정을 요청함
- 사용자가 기존 Blueprint 전체 실행을 요청함

다음 표현만으로는 Blueprint를 만들지 않는다.

- 계획해줘
- 다음 단계 알려줘
- 이어서 진행해줘
- 작업을 나눠줘
- 로컬 모델용 프롬프트를 줘

의도가 불명확하지만 파일 생성 여부가 제품 범위나 작업 방식에 실질 영향을 주면 질문 하나로 확인한다. 그 외에는 채팅 계획을 기본값으로 사용한다.

## 2. 작성 전 확인

1. 최신 `origin/main`을 확인한다.
2. `AGENTS.md`와 현재 product spec을 읽는다.
3. 기존 Blueprint 또는 더 가까운 기술 문서가 있는지 확인한다.
4. 계획 파일이 현재 동결 범위를 재개하지 않는지 확인한다.
5. 목표, 포함 범위, 제외 범위, 완료 기준을 한 경로로 정리한다.
6. 저장소에 실제로 존재하는 구현·테스트·명령만 참조한다.

Ocean Rescue WP 계획, 다음 WP, 진행 상태를 저장하기 위해 `docs/plans/PLAN_ocean_rescue_wp*.md`를 만들지 않는다.
상태 전용 evidence도 만들지 않는다.

## 3. Blueprint 내용

Blueprint는 최소한 다음을 포함한다.

- 목적과 사용자 가시 결과
- 현재 검증된 baseline
- 포함 범위와 명시적 제외 범위
- 작업 간 dependency
- 각 작업의 재현 조건 또는 입력 계약
- 각 작업의 단일 판정 기준
- 실제 존재하는 검증 명령
- rollback 또는 중단 경계
- 최종 완료 조건

작업 수를 줄이기 위해 서로 다른 failure domain을 묶지 않는다.
반대로 같은 원인을 닫는 source, caller, test, config는 하나의 작업으로 함께 다룰 수 있다.

## 4. 검증 도구

저장소에 현재 존재하는 plan tooling을 사용해야 할 때는 최신 `Justfile`과 스크립트의 실제 계약을 먼저 확인한다.
명령 이름을 과거 문서에서 복사해 추측하지 않는다.

대표적으로 다음 명령이 존재할 수 있다.

```bash
just plan-preread docs/plans/<file>.md --write
just plan-lint docs/plans/<file>.md
just plan-task-close plan=docs/plans/<file>.md task=<ID> conclusion="..."
just plan-close plan=docs/plans/<file>.md verify="..."
```

실제 작업에서 필요한 명령만 사용한다.
명령이 존재하지 않거나 현재 파일 형식과 맞지 않으면 Blueprint를 억지로 변경하지 말고 정확한 불일치를 보고한다.

## 5. 실행 규율

기존 Blueprint 실행 요청에서는 다음을 따른다.

1. 현재 파일과 최신 코드·테스트의 drift를 확인한다.
2. 이미 완료된 항목을 문자열 상태만 보고 다시 실행하지 않는다.
3. dependency 순서에서 아직 닫히지 않은 작업 하나를 선택한다.
4. 한 failure domain만 수정하고 독립 검증한다.
5. 상태 갱신이 실제 Blueprint 계약에 포함된 경우 제공된 안전한 도구를 사용한다.
6. 제품 테스트에 계획 진행률이나 다음 작업 assertion을 추가하지 않는다.
7. 계획이 현재 제품 방향과 충돌하면 실행하지 않고 충돌을 먼저 해소한다.

Blueprint 전체 실행 중 저장소 현실과 계획이 달라지면 과거 계획을 권위로 삼지 않는다. 최신 코드·테스트·제품 계약을 확인하고 필요한 재설계 범위를 사용자에게 명확히 보고한다.

## 6. 완료와 보고

Blueprint 완료는 문서의 완료 문자열만으로 선언하지 않는다.
최신 main의 코드, focused test, 브라우저·build·artifact 증거가 해당 완료 조건을 만족해야 한다.

보고 형식은 `AGENTS.md`를 따른다.

```text
RESULT: PASS | BLOCKED
CHANGE: <한 문장>
VERIFY: <한 문장>
```

실제 게시 시에만 `COMMIT`, 중단 시에만 `BLOCKER`와 `NEXT`를 추가한다.

## 7. 금지

- 명시적 요청 없이 plan 파일 생성
- 일반 WP 일정과 다음 작업을 저장소에서 관리
- 과거 plan 상태를 제품 동작 테스트로 검증
- 존재하지 않는 외부 서비스·issue tracker를 필수 전제화
- 한 Blueprint에 여러 대안 실행 경로를 동시에 유지
- 장문 계획을 이전 계획에 계속 누적
- 완료된 작업 이력을 다음 실행 프롬프트에 재귀적으로 복사
