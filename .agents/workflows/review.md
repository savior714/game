---
situation: "코드 리뷰 및 PR 전 검토"
# trigger: /review  ← catalog metadata only; Read this file before executing (error_patterns §16.1)
level: Recommended
description: "Review code changes with focus on correctness and risk"
version: 1.1.0
last_updated: 2026-06-02
scope: workflow
domain: workflow
---

<!-- Language: ko -->

# Review (`/review`)

**프로토콜 SSOT**: [.agents/skills/review/SKILL.md](../skills/review/SKILL.md) — 실행 전 Read 후 리뷰 절차를 따른다.

## 흐름 요약

| 단계 | 내용 |
| :--- | :--- |
| 1 | diff·리스크·**구조 체크list(R-1~R5)** 분석 (SKILL §Review Process · [code_quality_lifecycle.md §3](../core/code_quality_lifecycle.md)) |
| 2 | 발견 정리 (High / Medium / Low) |
| 3 | Final Check |
| 4 | **close** — 본문 제시 후 handoff `AskQuestion`/`question`(병용) |

## Close turn

리뷰 결과를 채팅에 낸 **같은 턴 마지막**에 SKILL §**Handoff `AskQuestion`/`question`(병용)**을 호출한다.

### Handoff (`AskQuestion`/`question`(병용) — close 턴 필수)

**권장 수정·후속 작업이 있을 때** (SKILL 표와 동일):

| 옵션 (비개발자 라벨 예) | 내부 |
| :--- | :--- |
| 권장 수정을 실행 계획(Blueprint)으로 정리하기 `(권장)` | `/plan` same-session |
| 리뷰·수정 범위 더 discuss하기 | `/discuss` 또는 동일 세션 질의 계속 |
| 지금 바로 소규모만 고치기 | Fix-first 범위 내 즉시 패치 |
| 여기서 마무리 | 종료 |

**실질 이슈 없을 때**: 마무리 `(권장)` / 다른 변경 범위 리뷰.

**Fast-path**: 사용자가 이미 plan·Blueprint 연속을 선택했으면 handoff `AskQuestion`/`question`(병용) **생략** → same-session plan.

**금지**: close 마지막에 `/plan`·`/discuss` **명령만** 안내. **AskQuestion/`question`(병용) 없이** 종료 선언만 하기. (discuss.md §종료 금지와 동일)

## Same-session plan

사용자가 **Blueprint로 정리**를 고르면:

1. 같은 세션에서 [plan.md](plan.md) SSOT — `PLAN_<slug>.md`·`just plan-lint` PASS.
2. Task·범위는 리뷰 권장 수정(High/Medium)에서 가져온다.
3. plan-lint PASS 후 **AskQuestion(`question` 병용)**: Task 1.1 구현 `(권장)` / 리뷰·범위 더 discuss / 마무리.

사용자에게 `/plan` 재입력을 요구하지 않는다.

## Same-session discuss

**더 discuss** 선택 시: 코드 변경 없이 범위·우선순위·트레이드오프를 [discuss.md](discuss.md)로 이어가거나, 동일 `/review` 세션에서 항목별로 질의한다. discuss close 시 plan handoff는 discuss SSOT를 따른다.
