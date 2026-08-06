---
scope: registry
domain: core
last_verified: 2026-08-06
---
<!-- Language: ko -->

# AidenGame 규칙 색인

이 색인은 현재 저장소에 실제로 존재하는 문서만 나열한다.

## 1. 최상위 권위

| 문서 | 역할 |
|---|---|
| [`AGENTS.md`](../../AGENTS.md) | 실행 우선순위, 작업 선택, Git·검증·보고 계약 |
| [`PROJECT_RULES.md`](../../PROJECT_RULES.md) | 제품·아키텍처·품질 경계 |
| [`CORE_QUIZ_RELIABILITY_STABILIZATION.md`](../../docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md) | 현재 일반 과목 안정화 제품·검증 계약 |
| [`MEMORY.md`](../../docs/agent-context/memory/MEMORY.md) | 새 세션 handoff와 다음 실행 경계 |
| [`README.md`](../../README.md) | 사용자·개발자용 저장소 진입점 |

## 2. Registry

| 문서 | 역할 |
|---|---|
| [`LOAD_ORDER.md`](LOAD_ORDER.md) | 세션과 작업 단계별 문서 로딩 순서 |
| [`CONTEXT_ROUTING.md`](CONTEXT_ROUTING.md) | AidenGame 경로별 컨텍스트 선택 |
| [`WORKFLOW_AND_SKILL_INDEX.md`](WORKFLOW_AND_SKILL_INDEX.md) | 실제 workflow와 skill 색인 |
| [`RULE_INDEX.md`](RULE_INDEX.md) | 본 문서 |

## 3. Core 참고 규칙

다음 문서는 해당 주제가 현재 작업에 직접 필요한 경우에만 읽는다.

- [`principles.md`](../core/principles.md)
- [`execution.md`](../core/execution.md)
- [`verification.md`](../core/verification.md)
- [`reporting.md`](../core/reporting.md)
- [`planning.md`](../core/planning.md)
- [`security.md`](../core/security.md)
- [`resilience.md`](../core/resilience.md)
- [`code_quality_lifecycle.md`](../core/code_quality_lifecycle.md)
- [`runtime_edit_tools.md`](../core/runtime_edit_tools.md)
- [`opencode_tools.md`](../core/opencode_tools.md)
- [`memory_hygiene.md`](../core/memory_hygiene.md)
- [`error_patterns.md`](../core/error_patterns.md)

`routing.md`는 과거 자동 route CLI 설계를 포함한 legacy reference다. 현재 실행 권위로 사용하지 않는다.

## 4. Domain 규칙

현재 존재하는 domain rule은 브라우저 테스트용
[`testing/playwright.md`](../domains/testing/playwright.md) 하나다.

현재 저장소에 없는 프레임워크·backend·규제 도메인 전용 rule은 AidenGame 작업에 적용하지 않는다.

## 5. Workflow와 Skill

실제 목록과 사용 조건은
[`WORKFLOW_AND_SKILL_INDEX.md`](WORKFLOW_AND_SKILL_INDEX.md)를 따른다.

workflow 또는 skill이 현재 제품 방향과 충돌하면 `AGENTS.md`와 현재 안정화 spec이 우선한다.
