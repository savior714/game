---
scope: registry
domain: core
last_verified: 2026-08-06
---
<!-- Language: ko -->

# AidenGame Workflow · Skill 색인

현재 저장소에 실제로 존재하는 workflow와 skill만 나열한다.
workflow는 작업 방식을 보조하며 현재 제품 우선순위를 바꾸지 않는다.

## 1. 현재 방향 gate

- 범위가 없는 다음 작업은 일반 과목 공통 브라우저 진단으로 시작한다.
- Ocean Rescue와 `experiments/`는 사용자가 현재 요청에서 재개하거나 허용 예외가 성립할 때만 다룬다.
- `/plan` 또는 계획 관련 표현만으로 저장소에 plan 문서를 만들지 않는다. 사용자가 저장소 Blueprint를 명시적으로 요청한 경우만 허용한다.
- workflow가 요구하는 명령이나 파일이 실제 저장소에 없으면 추측으로 대체하지 않는다.

## 2. Workflow

| 요청 | Workflow | 동행 Skill |
|---|---|---|
| 재현 가능한 실패 진단 | [`diagnose.md`](../workflows/diagnose.md) | [`diagnose/SKILL.md`](../skills/diagnose/SKILL.md) |
| 경량 원인 조사 | [`investigate.md`](../workflows/investigate.md) | [`investigate/SKILL.md`](../skills/investigate/SKILL.md) |
| 코드·변경 검토 | [`review.md`](../workflows/review.md) | [`review/SKILL.md`](../skills/review/SKILL.md) |
| 무코드 방향 합의 | [`discuss.md`](../workflows/discuss.md) | [`discuss/SKILL.md`](../skills/discuss/SKILL.md) |
| 스펙과 구현 정합성 확인 | [`sync.md`](../workflows/sync.md) | [`sync/SKILL.md`](../skills/sync/SKILL.md) |
| 기술 부채 탐색 | [`discover.md`](../workflows/discover.md) | [`discover/SKILL.md`](../skills/discover/SKILL.md) |
| 제한된 리팩터링 검토 | [`refactor.md`](../workflows/refactor.md) | [`refactor/SKILL.md`](../skills/refactor/SKILL.md) |
| 모듈 구조 심화 검토 | [`improve-codebase-architecture.md`](../workflows/improve-codebase-architecture.md) | [`improve-codebase-architecture/SKILL.md`](../skills/improve-codebase-architecture/SKILL.md) |
| 실제 브라우저 검증 | [`playwright.md`](../workflows/playwright.md) | [`testing/playwright.md`](../domains/testing/playwright.md) |
| 사용자가 명시한 Blueprint 계획 | [`plan.md`](../workflows/plan.md) | — |
| 커밋·게시 절차 | [`git.md`](../workflows/git.md) | — |
| 세션 handoff | [`go.md`](../workflows/go.md) | — |
| 사용자가 명시한 과거 plan 정리 | [`archive.md`](../workflows/archive.md) | — |

## 3. 선택 규칙

1. 현재 objective와 직접 일치하는 workflow 하나만 고른다.
2. 동행 skill이 있으면 workflow와 skill을 함께 읽는다.
3. 현재 작업에 소비되지 않는 workflow를 연쇄적으로 읽지 않는다.
4. workflow 본문이 `AGENTS.md`, `PROJECT_RULES.md`, 현재 product spec과 충돌하면 상위 문서를 따른다.
5. workflow에 오래된 명령·경로가 있으면 현재 디스크에서 존재 여부를 확인하고, 없으면 실행 조건으로 사용하지 않는다.
