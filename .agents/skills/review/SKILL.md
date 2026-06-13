---
name: review
description: "Review code changes with focus on correctness and risk"
---

# Review Skill

## Purpose

Review code changes with focus on:

* correctness
* regression risk
* side effects
* security
* maintainability

Avoid style nitpicks and trivial lint comments.

---

# Core Rules

## Anti-pattern at write

**Symptom**: 리뷰 결과가 추측성 코멘트 위주가 되거나, 후속 경로가 불명확해서 작업이 멈춤.

**Cause**: evidence 기반 점검 대신 인상평을 남기고 close 수렴(AskQuestion/`question` 병용)을 생략함.

❌ WRONG:

* "probably safe", "looks okay" 같은 추측성 표현
* close 턴에서 사용자 선택 없이 "/plan 하세요"만 남기고 종료

✅ CORRECT:

* 모든 이슈에 실패 시나리오 + 코드 근거를 포함
* close 턴 마지막에 `AskQuestion`/`question`(병용)으로 다음 행동(plan/discuss/fix-first/close)을 수렴

Reference SSOT: [`docs/agent-context/ANTI_PATTERN_FORMAT.md`](../../../docs/agent-context/ANTI_PATTERN_FORMAT.md)

## Diff-first

Always review based on:

```bash
git diff <base>...HEAD
```

Focus on:

* what changed
* what could break
* unintended side effects

Do not review unrelated repository areas.

### No-diff fallback (정적 리뷰 허용)

`git diff` 기준 변경점이 0건이어도 리뷰를 중단하지 않는다. 사용자가 특정 파일 리뷰를 요청했다면, 해당 파일 본문을 기준으로 **정적 리뷰**(내부 일관성, 참조 무결성, 실행/운영 절차 충돌, 모순 규칙)를 수행한다.

정적 리뷰 시에도 Evidence 규칙은 동일하게 적용한다:

1. 왜 중요한지
2. 어떤 실패/혼선을 만들 수 있는지
3. 코드/문서의 구체 근거

단, 정적 리뷰 결과는 "변경 회귀 리스크"가 아니라 "현재 상태의 잠재 리스크"임을 명확히 구분해 보고한다.

---

## Evidence Required

Never speculate.

Bad:

* "probably safe"
* "might break"
* "looks okay"

Good:

* exact execution path
* concrete failure scenario
* specific line/condition reference

Every concern must include:

1. why it matters
2. how it can fail
3. evidence from code

---

## Focus Areas

Prioritize:

* auth / permission issues
* null / undefined edge cases
* async bugs
* stale state
* race conditions
* transaction safety
* silent failures
* hidden regressions
* input validation
* API contract mismatch
* prompt injection surface
* missing error handling

**구조·결합 체크리스트** (R-1~R-5): [code_quality_lifecycle.md](../../core/code_quality_lifecycle.md) §3 — 중복·죽은 코드, 무음 에러, 숨은 결합, re-export, fan-in/out 집중.

---

## Ignore

Do NOT focus on:

* formatting
* naming preferences
* lint-level comments
* subjective style opinions

Assume formatter/linter already exists.

---

## Review Process

1. Read diff
2. Identify risk areas
3. Trace execution flow
4. Validate assumptions
5. Check downstream impact
6. Produce concise findings

---

## Finding Format

### High Risk

* issue
* impact
* evidence
* suggested fix

### Medium Risk

* issue
* edge case
* evidence

### Low Risk

Only include if meaningful.

---

## Fix-first Principle

If issue is:

* obvious
* low-risk
* localized

prefer fixing directly instead of only reporting.

Ask before:

* architectural changes
* schema changes
* behavior changes
* destructive operations

---

## Final Check

Before concluding:

* verify assumptions
* ensure finding is actionable
* remove weak/speculative comments
* reduce noise
* if Cursor 환경이면 close 턴에서 `AskQuestion`/`question`(병용) **tool call이 실제로 실행되었는지** 확인 (텍스트 안내만 출력하면 실패)

Prefer deterministic inspection tools over assumptions.

---

## Close turn (세션 종료)

리뷰 본문(발견·권장 수정)을 **한 턴에 제시한 뒤**, 같은 턴 **마지막**에 `AskQuestion`/`question`(병용)으로 다음 행동을 수렴한다. ([principles.md](../../core/principles.md) §1.1.1, [error_patterns.md](../../core/error_patterns.md) 메타 금지 6)

### Close 조건

* High/Medium 발견·권장 수정 요약을 채팅에 낸 직후
* 사용자가 「끝」「충분」「리뷰 마무리」 등으로 종료를 요청한 경우(이미 본문이 있으면 handoff만)

리뷰 본문 없이 close·handoff만 하지 않는다.

### Handoff `AskQuestion`/`question`(병용) (close 턴 필수)

**권장 수정·후속 작업이 1건 이상** 있을 때(High/Medium의 suggested fix·후속 검증 포함):

| 옵션 (비개발자 라벨 예) | 내부 |
| :--- | :--- |
| 권장 수정을 실행 계획(Blueprint)으로 정리하기 `(권장)` | same-session `/plan` — 리뷰 권장안을 Task로 쪼갬 |
| 리뷰·수정 범위 더 discuss하기 | `/discuss` 또는 동일 세션에서 항목별 질의 계속 |
| 지금 바로 소규모만 고치기 | Fix-first — [Fix-first Principle](#fix-first-principle) 범위 내 즉시 패치 |
| 여기서 마무리 | 세션 종료 |

`(권장)`은 **Blueprint로 묶는 편이 안전할 때**(복수 파일·동작 변경·아키텍처 터치)에만 단다. 단일 1~2줄·명확한 버그 1건이면 「지금 바로 소규모만 고치기」에 `(권장)`을 둘 수 있다.

**실질 이슈 없음**(Low만 또는 발견 0):

| 옵션 | 내부 |
| :--- | :--- |
| 마무리 `(권장)` | 종료 |
| 다른 변경 범위 리뷰 | 새 diff 범위로 `/review` 재개 |

### Fast-path

사용자가 이미 「계획으로」「Blueprint로」를 선택했거나, 직전 턴 수렴 메뉴에서 plan을 골랐다면 handoff `AskQuestion`/`question`(병용)을 **생략**하고 same-session `/plan`으로 이어간다. ([workflows/review.md](../../workflows/review.md) §Same-session plan)

### Same-session plan 연속

* 사용자가 **plan**을 고르면 **같은 세션**에서 [plan.md](../../workflows/plan.md) SSOT로 `docs/plans/PLAN_*.md` 작성·`just plan-lint` PASS까지 진행한다. `/plan` 재입력을 요구하지 않는다.
* Blueprint §1.9.1·Task는 리뷰 **권장 수정·High/Medium**을 근거로 쓴다. 리뷰 채팅 요약 2~3줄을 §1.9 맥락에 반영한다.
* plan 직후 **AskQuestion/`question`(병용)**: Task 1.1 구현 `(권장)` / 리뷰 항목 더 discuss / 마무리 — discuss·plan 워크플로와 동일 톤.

### Handoff 선택지 출력 방법 (IDE-agnostic)

IDE마다 사용 가능한 도구가 다르므로 **우선순위**에 따라 선택한다.

1. **Cursor** — `AskQuestion`/`question` 도구(tool call, 병용)가 사용 가능하면 그것으로 호출
2. **그 외 IDE / CLI** — 도구가 없으면 아래 마크다운 포맷으로 텍스트 출력

#### Cursor 강제 규칙 (재발 방지)

- Cursor에서 close 턴은 **반드시 `AskQuestion`/`question` 도구(병용) 호출**로 끝낸다.
- 단순 문장(예: "선택지를 골라주세요")이나 체크리스트 텍스트만 출력하고 종료하는 것은 정책 위반이다.
- close 응답 직전에 self-check: `AskQuestion`/`question`(병용) 호출 여부를 확인하고, 누락 시 응답 전 즉시 호출한다.

```markdown
**리뷰 결과를 어떻게 처리할까요?**

A) 권장 수정을 실행 계획(Blueprint)으로 정리하기 (권장)
B) 리뷰 항목 더 discuss하기
C) 지금 바로 소규모만 고치기
D) 여기서 마무리
```

어느 쪽이든 `<ask_followup_question>` XML 태그나 `<tool_call>` 텍스트를 **직접 출력하지 않는다** — 이는 렌더링되지 않고 노이즈만 된다.

### 금지

* close 턴 마지막에 「`/plan`으로 Blueprint 작성하세요」처럼 **명령만** 남기기 — 선택은 항상 사용자가 고를 수 있는 형태로.
* 선택지 없이 「리뷰 완료」만 던지고 끝내기.
* 선택지 텍스트에 literal `\n` 문자열 포함 ([refactor.md](../../workflows/refactor.md) §AskQuestion(`question` 병용) 문자열 가드).
