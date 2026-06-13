---
situation: 무코드 방향 합의
# trigger: /discuss  ← catalog metadata only; Read this file before executing (error_patterns §16.1)
level: Recommended
description: 코드 변경 없이 프로젝트 전체 파악 → question 도구 호출 → DISCUSS 노트 (표준 메뉴 A/B, assess 없음)
version: 1.0.3
last_updated: 2026-06-11
scope: workflow
domain: workflow
---
<!-- Language: ko -->

# Discuss (`/discuss`)

**프로토콜 SSOT**: [.agents/skills/discuss/SKILL.md](../skills/discuss/SKILL.md) — 실행 전 Read.

**코드를 건드리지 않고** 프로젝트 전체를 둘러보며 **개선 방향**을 대화로 합의한다. 막연한 방향 잡기 · 기존 계획·설계 맹점 심문 · 문제→방향+범위 정리 등 무코드 대화는 전부 여기로 모은다. 산출물은 전용 논의 노트 [docs/discussions/](../../docs/discussions/) 하위의 `DISCUSS_*.md`.

**방향·범위가 잡히면** → [/plan](plan.md). feature 정밀 분석은 [/assess](assess.md) **별도** — discuss question 메뉴에 넣지 않음.

## AidenGame 부록 (SKILL 미러)

When / When NOT / 노트 포맷 전문은 SKILL을 본다. 아래는 **어긋나기 쉬운 규칙만** 미러.

### Anti-pattern at write (요약)

- **증상**: 사용자 선택 없이 종료하거나, mermaid/긴 표로 답변이 장황해짐.
- **원인**: `/discuss`의 "한 턴 한 결정 + question 도구 호출 필수" 규칙 미준수.
- ❌ WRONG: 텍스트로 "A/B/C 중 골라 주세요"만 작성하고 도구 미사용, 또는 close 턴에 명령만 남기기.
- ✅ CORRECT: close 턴 마지막에 `question` 도구로 handoff를 수렴하고, 본문은 짧은 불릿으로 유지.
- 공통 포맷 SSOT: [`docs/agent-context/ANTI_PATTERN_FORMAT.md`](../../docs/agent-context/ANTI_PATTERN_FORMAT.md)

### 철칙 (우선)

0. **턴 판별 SSOT** — 매 `question` 도구 호출 전 SKILL §**턴 판별 결정 트리** 적용. `close` 트리거 없으면 Blueprint·메뉴 A **금지**.
1. **무코드** — 진행 중 소스(`.ts`/`.py`/`.tsx`) **절대 수정 금지**. 편집은 `DISCUSS_*.md` 노트 하나뿐.
2. **한 턴 = 한 결정** — 옵션 제공 시 `question` 도구 호출 필수 (텍스트로 흉내 금지).
3. **권장 + 이유** — 옵션마다 기대 결과 1줄, `(권장)` **2단계**(§1·[확정] 우선 → 동률 시 4요소) + 이유 1줄.
4. **비개발자 톤** — 경로·린트·Phase 등 기술 용어는 노트 갱신·핸드오프 때만.
5. **짧게** — 채팅 본문 18줄 이내. mermaid·긴 표·로드맵 금지.
6. **모호성 즉시 수렴** — `/discuss` 입력을 해석할 때 의도·범위·용어·완료기준 4축 중 하나라도 불명확하면 즉시 `question` 도구로 수렴하고, 가정으로 다음 분기를 진행하지 않는다.
7. **엣지 케이스 선제 유도** — 사용자가 예외를 **요청하지 않아도** `direction` 2~3턴마다·happy path 확정 직후 **question 1턴**으로 빈 화면·저장 실패·권한·오프라인 등을 묻는다. 뱅크: [plain-language-questions.md](../skills/discuss/references/plain-language-questions.md) §엣지 케이스 선제. converge «계획으로» **전** 엣지 question ≥1턴 또는 §3 `엣지: 해당 없음` [확정] 필수.
8. **텍스트 답 = 유효 선택** — 채팅으로 A/B/옵션 이름을 답하면 카드 스킵이어도 확정 처리. `pending_ask`·매핑 규칙은 SKILL §**채팅 텍스트 답변 수용**·§**question 스킵 시**.

### 턴 형식·예시 (SKILL SSOT)

매 `/discuss` 턴은 SKILL §턴 출력 형식의 **GOOD (첫 턴·scan / direction)** 예시 뼈대를 따른다. plan-lint PASS 직후 **산출물 요약 턴**의 필수·**금지 문구**·GOOD 예시는 SKILL §**산출물 요약 턴**만 본다(일반 턴 BAD·GOOD과 분리).

### 첫 턴 (scan)

- 사용자가 영역을 줬으면 **그 영역에 한정**한 심층 스캔. 미지정이면 [backlog](../../docs/agent-context/memory/PROJECT_REFACTORING_BACKLOG.md)·[specs](../../docs/specs/)·[plans](../../docs/plans/)·[CONTEXT](../registry/CONTEXT_ROUTING.md) 앵커부터 보고 **범위 좁히는 질문 1개**.
- **조사 게이트 → 본 질문 (두 턴)**: `scan`·`direction`은 턴1에 «외부 조사 필요?»만 `question`, 필요 시 deep-research 1회 후 턴2에 route+주제 맥락으로 본 분기·(권장). 상세는 SKILL §**question 직전 맥락·조사 게이트**.
- 스캔 요약 2~3줄 → **턴2**에서 방향 후보 질문 1개. **무한 확장 금지.**

### 방향 수렴 (converge)

방향·범위가 맞아 보이면 **`question` 수렴 메뉴** 1회 (SKILL §방향 수렴 SSOT):

| 옵션 | `(권장)` |
| :--- | :--- |
| **{새로운 심층 주제} 더 논의하기** | **기본** — `[열림]`이 0이어도 예외·UI·연동 리스크 등 **발굴** |
| **방향 확정 → 계획으로** | Ambiguity-Zero 7개 **모두 YES**일 때만 제시. 그 전 `(권장)` **금지** |
| **{§2 [열림] 문구}만 더 맞추기** | 열린 분기 1개 남았을 때 |
| **아직 더 논의** | `direction` 계속 |

- **조기 Blueprint 권장 금지**: `[열림]` 0개·방향만 잡힌 상태에서 **방향 확정 → 계획**을 `(권장)`로 두지 않는다(plain-language 뱅크 converge 표도 동일).
- 「정리」**입력 요구 문장만** 던지지 않는다.
- **방향 확정 → 계획** 선택 = `close` + **same-session plan 직행** — **메뉴 A·Blueprint 재질문 생략**(SKILL §Same-session plan 연속). 텍스트 close(정리·끝)만 **메뉴 A**.

`실행 계획(Blueprint)으로 만들기`·converge «계획으로» **허용 전** SKILL §**Blueprint 생성 허용 게이트 (Ambiguity-Zero)** 선적용. 7개 중 하나라도 NO면 converge에 «계획으로» 넣지 말고, 해당 항목만 좁히는 `question` 1개.
실무 기록: `DISCUSS_*.md` §3 **Ambiguity-Zero 체크박스 7개** — handoff·same-session plan **전** 전부 체크.

### 종료 (close)

「정리」「끝」「방향 정해졌다」**또는** 수렴 **방향 확정 → 계획** 선택 시 §3 확정.

| close 경로 | 다음 |
| :--- | :--- |
| **converge «계획으로»** | same-session plan 직행 → 산출물 **메뉴 B** (메뉴 A **생략**) |
| **텍스트만** (정리·끝) | **«계획 문서가 목표?»** → **메뉴 A** (§1·답변에 계획 의도 있을 때 Blueprint; 없으면 더 논의 `(권장)` · 마무리) |

**금지**: converge «계획» 뒤 **메뉴 A·Blueprint 재질문** · 명령형 `/plan`만 남기기 · `question` 없이 종료.

## 표준 메뉴 · Handoff (SKILL §표준 `question` 메뉴)

| 메뉴 | 언제 | `(권장)` |
| :--- | :--- | :--- |
| **A** | **텍스트** close만, PLAN 없음 (converge «계획» **금지**) | §1·계획 확인 후 Blueprint; 없으면 더 논의 |
| **B** | 산출물 요약·handed-off 재진입 | **PLAN 전체 순차 실행** (Blueprint 동결) |

Blueprint 선택 시 **같은 세션** plan SSOT → plan-lint PASS → **메뉴 B**로 이어짐.

### Same-session plan 직후 (SKILL §Same-session plan 연속)

- 산출물: DISCUSS(handed-off) + PLAN(lint PASS) — 채팅에 **둘 다 이미 있다**고 요약.
- **다음 단계**: **이 PLAN 전체 순차 실행**(Blueprint 동결) **또는** Task 1.1만 **또는** §Same-session multi-cycle(새 주제 discuss → **새** Blueprint).
- **같은 DISCUSS**에 `/plan`·「plan 시행」·「Blueprint 작성」**금지**.

### Same-session multi-cycle (SKILL §Same-session multi-cycle)

- Blueprint 1개 완료 후 **새 주제** discuss → **새** `DISCUSS_*.md` (**새 §1** «이번 discuss에서 끝까지: …» 리셋) → close → **새** `PLAN_*.md` — 세션 내 **반복 가능**.
- 이전 `handed-off` DISCUSS **재편집·재-plan 금지**. 주제마다 slug·파일·§1 **분리**.

### 의도 우선 `(권장)` (SKILL §선택지 표시 패턴 · 자가검사 5항)

- **2단계**: 1순위 §1 «이번 discuss에서 끝까지: …» + [확정] 합의 aligned → 동률 시만 안전·표준·복구·유지보수 4요소.
- **§1 인용**: `direction`·`converge` 턴마다 채팅에 «이번 discuss에서 끝까지: …» 한 줄. scan 턴2에 노트 §1 고정; multi-cycle마다 새 §1.
- **close 계획 확인**: 텍스트 close(정리·끝) 시 메뉴 A **전** «계획 문서가 목표?» `question`. converge «계획으로» = 확인 생략 → same-session plan.
- **메뉴 A 엣지**: §1·답변에 계획 의도 **없으면** 「끝」이어도 **이 주제 더 논의** `(권장)`, Blueprint `(권장)` 금지.
- **자가검사 5항**: §1 인용 / (권장) 정합 / Blueprint nudge 금지 / 4요소 역전 금지 / §1 vs [확정] 충돌 시 `question`.
- **금지**: «더 빠름·쉬움»만으로 §1 의도와 충돌하는 `(권장)` 역전.

### 이미 `handed-off` + `linked_plan`(동일 DISCUSS·재진입)

**그 노트**에 Blueprint(메뉴 A) 재안내 금지. **표준 메뉴 B**만 — **PLAN 전체 순차 실행** `(권장)` / Task 1.1만 / 새 주제 discuss / **마무리**.
