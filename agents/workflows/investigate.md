---
situation: 수정 전 원인·영향 범위 조사
level: Recommended
description: 코드를 바꾸지 않고 증거·재현 가능성·유력 원인을 정리하는 조사 workflow
version: 2.0.0
last_updated: 2026-08-06
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Investigate workflow

상세 절차는 [`investigate/SKILL.md`](../skills/investigate/SKILL.md)를 따른다.

## 1. 사용 조건

- 사용자가 원인 분석이나 현황 파악을 요청함
- 수정 범위를 정하기 전에 영향을 조사해야 함
- 여러 문서·테스트·구현의 정합성을 감사함
- 현재 증상이 runtime failure인지 test gap인지 구분해야 함
- 즉시 수정하지 않고 근거와 권장 경계를 보고해야 함

실제 수정과 회귀 closure까지 요청받았다면 조사 후 [`diagnose.md`](diagnose.md) 또는 해당 구현 workflow로 이어간다.

## 2. 기본 원칙

- 기본적으로 read-only다.
- 사용자 요청이 분석만이면 production code를 수정하지 않는다.
- 파일·명령·상태는 최신 `origin/main`에서 확인한다.
- 과거 계획과 완료 보고를 현재 증거로 사용하지 않는다.
- 사실, 추정, 미확인 항목을 구분한다.
- 검색 결과의 존재 자체를 결함으로 판정하지 않는다.

## 3. 조사 순서

1. 질문 또는 증상을 정확히 정의한다.
2. 가장 가까운 authority 문서와 current code/test를 읽는다.
3. 실행 경로, state ownership, caller, fallback, generated artifact를 추적한다.
4. 필요하면 가장 작은 재현 또는 source-level 판정을 만든다.
5. 확인된 사실과 모순을 정리한다.
6. 원인을 하나로 확정할 수 있으면 근거를 제시한다.
7. 확정할 수 없으면 유력 원인과 각각의 검증 방법을 제시한다.
8. 수정이 필요한 경우 첫 failure domain 하나와 binary criterion을 권장한다.

## 4. 현재 제품 방향 적용

범위가 지정되지 않은 조사는 일반 과목 안정화 계약을 기준으로 한다.

- 네 과목의 실제 runtime failure와 test coverage gap을 구분한다.
- 이미 해결된 next progression과 touch target을 재현 없이 다시 결함으로 선언하지 않는다.
- Ocean Rescue·실험 기능은 동결 정책 위반 여부만 조사할 수 있으며, 자동 구현 재개로 이어가지 않는다.

## 5. 결과 형식

```text
FINDING: <확인된 핵심 사실>
EVIDENCE: <코드·테스트·실행 또는 문서 근거>
IMPACT: <사용자·검증·운영 영향>
RECOMMENDED BOUNDARY: <첫 수정 failure domain 또는 변경 없음>
```

수정하지 않았다면 `CHANGE: 변경 없음`을 명확히 한다.
사용자가 수정까지 요청했다면 조사 결과를 현재 단일 작업의 입력으로 사용한다.
