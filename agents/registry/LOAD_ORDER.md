---
scope: registry
domain: core
last_verified: 2026-08-06
---
<!-- Language: ko -->

# AidenGame 문서 로딩 순서

이 문서는 AidenGame 에이전트가 어떤 문서를 언제 읽어야 하는지 정의한다. 로딩 순서는 우선순위를 바꾸지 않는다.

## 1. 우선순위

충돌 시 다음 순서를 적용한다.

1. 사용자의 현재 요청
2. [`AGENTS.md`](../../AGENTS.md)
3. [`PROJECT_RULES.md`](../../PROJECT_RULES.md)와 대상 기능에 가장 가까운 product/technical spec
4. 최신 `origin/main`의 코드·테스트·설정

`.agents/`의 registry, core, workflow, skill 문서는 위 순서를 보조할 뿐 이를 재정의하지 않는다.

## 2. 세션 시작

다음 문서를 읽는다.

1. [`AGENTS.md`](../../AGENTS.md)
2. [`PROJECT_RULES.md`](../../PROJECT_RULES.md)
3. [`MEMORY.md`](../../docs/agent-context/memory/MEMORY.md)

현재 기본 개발 방향은 일반 과목 문제풀이 안정화이므로, 범위가 지정되지 않은 다음 작업이나 로컬 프롬프트 요청에서는
[`CORE_QUIZ_RELIABILITY_STABILIZATION.md`](../../docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md)를 추가로 읽는다.

## 3. 작업 착수

`.agent-harness.yml`의 `max_additional_documents: 3`을 기준으로 다음 세 종류만 우선한다.

1. 대상 구현 파일
2. 직접 관련 focused test
3. 대상 기능에 가장 가까운 spec 또는 운영 계약

과거 계획, 완료 보고, evidence는 현재 코드·테스트보다 높은 권위를 갖지 않는다.

## 4. 선택적 워크플로와 스킬

사용자가 명시적으로 요청했거나 현재 작업에 직접 필요한 경우에만
[`WORKFLOW_AND_SKILL_INDEX.md`](WORKFLOW_AND_SKILL_INDEX.md)에서 실제 존재하는 workflow 또는 skill 하나를 선택한다.

현재 저장소에는 자동 컨텍스트 라우팅 CLI가 없다.
존재하지 않는 명령을 전제하거나 route manifest 생성을 완료 조건으로 삼지 않는다.

## 5. 세션 종료

- 변경 위험에 대응하는 가장 작은 검증을 실행한다.
- `RESULT / CHANGE / VERIFY` 중심으로 보고한다.
- 제품 방향 또는 다음 실행 경계가 바뀐 경우에만 `MEMORY.md`를 교체한다.
- 과목별 진행률, 다음 WP, 완료 문자열을 문서에 누적하지 않는다.
