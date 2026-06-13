---
name: discuss
description: >
  코드 변경 없이 프로젝트 전체 상황을 파악하고, 한 턴 한 결정 AskQuestion(`question` 병용)(권장 + 이유)으로
  대화하며 "어디를 어떻게 개선할지" 방향을 합의한다. 합의 내용은 전용 논의 노트
  docs/discussions/DISCUSS_*.md에 점진 누적하고, 끝나면 plan(Blueprint)으로 핸드오프.
  같은 세션에서 주제마다 discuss→plan(multi-cycle) 반복 가능 — 주제별 DISCUSS+PLAN 1세트.
  Use when the user says discuss, /discuss, 또는 막연한 개선 욕구만 있고 아직 문제·계획이 없을 때.
license: MIT
metadata:
  version: "1.0.2"
disable-model-invocation: true
---

<!-- Language: ko -->

# Discuss

> **도구 별칭**: 본 SKILL의 `AskQuestion` 지시는 `question` 도구 호출에도 동일 적용([principles.md §1.1.1](../../core/principles.md)).

**Discuss** = 코드를 건드리지 않고 프로젝트 전체를 둘러보며 **개선 방향**을 대화로 합의한다. 막연한 방향 잡기부터 **이미 있는 계획·설계 맹점 심문**, **문제→방향+범위 정리**까지 무코드 대화는 전부 여기로 모은다. 산출물은 **전용 논의 노트**(`docs/discussions/DISCUSS_*.md`)다.

> **이웃 워크플로와의 경계** (겹치면 그쪽을 쓴다):
> - **`plan`** — 방향·범위가 잡힌 뒤 Blueprint(`PLAN_*.md`) + Task·Verify 분해 ([plan.md](../../workflows/plan.md)).
>
> 정석 흐름: `discuss`(방향 + 범위 합의) → `plan`(Task 분해). feature 정밀 아키텍처 분석은 **`/assess` 별도 워크플로** — discuss 핸드오프·AskQuestion(`question` 병용) 메뉴에 **넣지 않음**.

## When to use / NOT

| Use | NOT |
| :--- | :--- |
| "프로젝트 어디를 개선할까" **막연한 방향** 논의 | Task·구현 착수 → `/plan` **이후** |
| 이미 있는 `PLAN_*.md`·설계 **맹점 심문** | feature 정밀 아키텍처 분석 → **`/assess` 별도** (discuss 메뉴 아님) |
| 문제 프롬프트 → 방향+범위 **차근차근** 정리 | 단순 코드 리뷰·한 줄 피드백 |
| 코드 **안 건드리고** 대화·문서 폴리싱 / 여러 영역 우선순위 합의 | 방향·범위 이미 선명 → 바로 `/plan` |

**입력**: 사용자의 막연한 개선 의도(+선택: 관심 영역). **산출**: `docs/discussions/DISCUSS_<slug>.md`.

## 철칙 (우선순위 — Workflow 보다 위)

0. **Blueprint 조기 진입 금지 (Anti-rush)** — `discuss`의 기본 모드는 **선택지로 합의를 쌓는 것**이다. `converge`·`close`·same-session plan은 **사용자가 명시적으로 끝내거나** Ambiguity-Zero 7/7이 **노트 §3에 체크된 뒤**에만 허용. `[열림]` 0개·방향만 잡힌 턴에 **방향 확정 → 계획**을 `(권장)`로 두지 않는다 — 그때 `(권장)`은 **{새 심층 주제} 더 논의**. 채팅에 A/B/C 불릿만 쓰고 `AskQuestion`/`question`(병용)을 생략하는 것도 조기 종료와 동일하게 **금지**.
1. **무코드 (Meta-Only Boundary)** — `discuss` 진행 중 애플리케이션 소스(`.ts`, `.py`, `.tsx` 등)를 **절대 수정·패치하지 않는다**. 편집은 오직 `docs/discussions/DISCUSS_*.md` 노트 하나뿐.
2. **한 턴 = 한 결정** — 결정 트리 **분기 하나**만 전진. 갈래 2~4개면 **반드시 `AskQuestion`/`question` 도구를 직접 호출(병용)**(텍스트로 흉내 금지). 자유 서술이면 질문 **1문장**.
3. **권장 + 이유 필수** — 옵션마다 **기대 결과 1줄**, `(권장)` 태그는 **정말 하나만**(**2단계** 선정 — §1·[확정] 우선, 동률 시 4요소), 권장 아래 **이유 1줄(10단어 이내)**.
4. **비개발자 톤** — 사용자-facing 문장에 경로·API·Phase·린트 등 기술 용어 최소화 ([reporting.md](../../core/reporting.md) §1.6.0). 경로·`just plan-lint`는 **노트 갱신·핸드오프 때만**.
5. **짧게** — 채팅 본문 **18줄 이내**(Quick Pick·한 줄 메모 제외). mermaid·긴 표·로드맵·"다음에 물을 것" 목록 **금지**.
6. **표준 메뉴로 마무리** — 텍스트 `close`·산출물 요약·handed-off 재진입은 §**표준 AskQuestion/`question`(병용) 메뉴** A/B. converge **「방향 확정 → 계획으로」** 선택 후 close는 **메뉴 A 생략** → §Same-session plan 직행 후 **메뉴 B**만. **assess 옵션 금지**. **「여기서 마무리」**는 메뉴 A/B에 항상 포함.
7. **엣지 케이스 선제 유도 (Proactive Edge Elicitation)** — 사용자가 예외·엣지를 **요청하지 않아도**, `direction` 중 **2~3턴마다** 또는 happy path `[확정]` 직후 **AskQuestion 1턴**으로 빈 상태·저장 실패·권한·오프라인·데이터 없음 등을 묻는다. 질문 뱅크: [plain-language-questions.md](references/plain-language-questions.md) §엣지 케이스 선제. 답은 §3 **「엣지 케이스」** 불릿·§2 `[확정]`에 기록 → same-session plan 시 PLAN Edge Case Trace로 이관. **금지**: 사용자 미언급만으로 엣지 논의 생략.

## 턴 판별 결정 트리 (매 AskQuestion/`question`(병용) 전 MUST)

**Blueprint `(권장)`·메뉴 A·「실행 계획으로 만들기」**는 **텍스트 `close` 턴**에서만. `direction`·`converge`·노트 §3 갱신만으로는 **close 아님**.

| 순서 | 질문 | YES → | NO → |
| :---: | :--- | :--- | :--- |
| 1a | **close** + 직전 converge **「방향 확정 → 계획으로」** 선택 | §종료 1~2 → **§Same-session plan 직행** (메뉴 A·Blueprint **재질문 생략**) → 산출물 요약 **메뉴 B** | 1b |
| 1b | **close** + 「정리」「끝」「방향 정해졌다」**(converge «계획» **없음**) | **메뉴 A** (`linked_plan` 없을 때) | 2번 |
| 2 | **converge** 턴인가? — `[열림]` 0~1개·방향·범위가 한 덩어리로 보임 | **수렴 메뉴**. `(권장)` = **{심층 주제} 더 논의**. «계획으로»·Blueprint `(권장)` **금지** (7/7 YES여도) | 3번 |
| 3 | **scan / direction** | **Blueprint·메뉴 A·«계획으로» 전면 금지**. `status`는 **`discussing` 유지** | — |

**흔한 오판 (FAIL)**:

- §3·Ambiguity-Zero를 채웠다 → close로 착각 → 메뉴 A Blueprint `(권장)` ❌
- 「방향과 범위는 맞춰 두었습니다」문구만으로 close ❌ — **close 트리거(표 1a·1b) 없으면** `direction`/`converge` 계속
- converge **「방향 확정 → 계획으로」** 선택 후 **메뉴 A·Blueprint 재질문** ❌ — 이미 plan 의사가 확정됨
- 노트 `status: direction-set` 갱신 → **메뉴 A만** 띄우고 plan 미작성 ❌ — converge «계획» 경로면 **same-session plan**까지 이어야 함
- `linked_plan`·PLAN이 이미 있음 → 메뉴 A 재호출 ❌ — **메뉴 B**만

## 선택지 표시 패턴 (MUST)

`AskQuestion`/`question`(병용)으로 선택지를 제시할 때:

```
1. [선택지 A] (권장)
   • 이유: [10단어 이내] — 가장 안전하고 프로젝트 표준과 일치
2. [선택지 B]
   • 이유: 특정 상황에서만 유리
3. [선택지 C]
   • 이유: 실험적이지만 리스크 있음
```

`(권장)` **2단계 선정** (MUST):

| 순위 | 기준 | 적용 |
| :---: | :--- | :--- |
| **1순위** | **§1 «이번 discuss에서 끝까지: …»** + 누적 **[확정]** 합의와 **aligned**된 선택지 | `scan`·`direction`·`converge` 본 분기 |
| **2순위** | 1순위 **동률**일 때만 — 안전·프로젝트 표준·복구 용이·유지보수 친화 **4요소** | 의도-aligned 후보끼리만 비교 |

**금지**: «더 빠름·쉬움·표준» **단독**으로 §1·[확정]과 **충돌**하는 `(권장)` 역전. 모든 선택지가 동등·미검증 접근·사용자 컨텍스트만으로 갈릴 때 `(권장)` 생략. 목표 — **권장만 눌러도 성공 확률 90%+**.

**§1 vs [확정] 충돌**: 노트 §1·누적 [확정]이 어긋나면 **AskQuestion(`question` 병용) 1턴**으로 따를 쪽 확인 후 `(권장)` 선정.

## AskQuestion/`question`(병용) 직전 맥락·조사 게이트 (MUST)

본 AskQuestion(`question` 병용)(방향·분기 선택)과 `(권장)` 선정 **직전**에 프로젝트 맥락을 읽는다. 조사 없이 업계·경쟁 관행을 근거로 쓰지 않는다.
또한 `/discuss` 입력 해석에서 **의도·범위·용어·완료기준 4축 중 하나라도 불명확하면 즉시 AskQuestion(`question` 병용)**으로 수렴한다(가정·추정으로 다음 분기 진행 금지).

### 맥락 수집 (항상)

1. **`just route`** (주제가 넓으면 `just route-smart '<query>' <paths> --json`) — 관련 경로의 rules·must_read를 Read.
2. **이번 discuss 주제** — 사용자가 준 영역·경로, `DISCUSS_*.md` §1~3, scan 범위의 backlog·plans·spec **일부**.
3. **권장 선정** — §**선택지 표시 패턴** **2단계**(§1·[확정] → 동률 시 4요소). 업계·경쟁은 **조사 게이트 «예»**일 때만 [deep-research](../deep-research/SKILL.md) 요약을 보조 근거로 쓴다.

### `scan`·`direction` — 두 턴 흐름

| 턴 | 내부 | 행동 |
| :---: | :--- | :--- |
| **1** | `research-gate` | **`AskQuestion`/`question`(병용) 1개만**: «이 분기 전 **외부·업계 조사**가 필요한가요?» — 라벨 예는 [plain-language-questions.md](references/plain-language-questions.md) §외부 조사 게이트. **방향 후보·본 (권장) 없음.** |
| **2** | `scan` / `direction` | 게이트 «예» → deep-research **1회**(규제·거시·업계 벤치가 분기에 필요할 때) 후 요약 1~2줄. «아니오» → route+주제 맥락만. §턴 출력 형식대로 **본 AskQuestion(`question` 병용)** + `(권장)` 1개. |

- **`converge`·`close`·핸드오프** `AskQuestion`/`question`(병용)에는 게이트를 **쓰지 않는다**.
- 게이트 턴 채팅: 질문·옵션·권장 1줄만 — 스캔 장문·다음 분기 노출 금지.

### 채팅 텍스트 답변 수용 (Typed Answer Equiv) (MUST)

Cursor에서 사용자가 **채팅으로 답을내면** 대기 중 `AskQuestion`/`question`(병용) 카드가 `Questions skipped by the user`로 닫힐 수 있다. **타이핑은 정상 입력 채널**이며, 카드 클릭과 동등하게 처리한다.

**직전 턴 `AskQuestion`/`question`(병용) 직후** 사용자 메시지가 오면, **다음 분기로 가기 전** `pending_ask`(§논의 노트)와 대조한다.

| 매핑 신뢰도 | 판정 | 행동 |
| :--- | :--- | :--- |
| **높음** | 옵션 `id`·라벨·A/B/C·1/2/3·close 트리거(정리·끝·방향 정해졌다)·`(권장)` 옵션과 의미 일치 | 확정 1문장 → §2 `[확정]`·노트 갱신 → `pending_ask` 비움 → **다음 분기** (동일 질문 재호출 **금지**) |
| **중간** | 의도는 보이나 옵션 2개 이상에 걸침 | **2지 확인** `AskQuestion`/`question`(병용) 1회만 — 「{해석}」으로 이해했습니다. 맞나요? (예 / 아니오, 다시) |
| **낮음** | `pending_ask`와 무관·빈 메시지·새 주제만 | §**AskQuestion(`question` 병용) 스킵 시** 표로 폴백 |

**매핑 규칙** (높음 판정 예):

- `A` `B` `C` 또는 `1` `2` `3` (대소문자 무관)
- 옵션 **라벨** 전체 또는 핵심 구절 일치 (예: «접수·대기부터», «계획으로», «마무리»)
- 수렴·메뉴 A/B 표준 라벨과 일치 ([plain-language-questions.md](references/plain-language-questions.md))
- 자유 서술 1문장이 **단일 옵션** 의미와 명확히 같을 때

**금지**: 매핑 **실패**인데 route·스캔만으로 다음 분기 추진. 매핑 **성공**인데 «스킵»을 이유로 동일 질문 재호출.

### AskQuestion(`question` 병용) 스킵 시 (MUST)

도구 결과가 `Questions skipped by the user`이면 **호출 실패가 아니라 UI 스킵 이벤트**로 본다. **먼저** §**채팅 텍스트 답변 수용**으로 사용자 메시지 매핑을 시도한다. 주제별 `DISCUSS_*.md`가 아니라 **본 스킬**이 SSOT다.

| 조건 | 행동 |
| :--- | :--- |
| 스킵 + 사용자 메시지가 `pending_ask` 옵션에 **높음** 매핑 | §Typed Answer — 확정 후 다음 분기 |
| 스킵 + **중간** 매핑 | 2지 확인 `AskQuestion`/`question`(병용) 1회 |
| 스킵 + 매핑 **낮음** | 채팅 한 줄: «카드로 고르거나 **A/B/옵션 이름**으로 답해 주셔도 됩니다» → **동일 질문** `AskQuestion`/`question`(병용) 1회 재시도 (채팅 A/B/C만으로 대체 **금지**) |
| 재시도도 스킵 + 여전히 낮음 | 입력 방식 안내 후 사용자 답 대기 (연속 `AskQuestion`/`question`(병용) **금지**) |

- **한 턴 질문 1개** — 연속 `AskQuestion`/`question`(병용)으로 UI 충돌 가능성을 줄인다.

## 턴 출력 형식 (MUST)

**2턴 조사 게이트·본 AskQuestion 복붙 예시**: [references/askquestion-two-turn-examples.md](references/askquestion-two-turn-examples.md) (게이트 턴 1 + 본 턴 2 GOOD/BAD, 업계 환각 금지).

**§1 인용 (MUST)** — `direction`·`converge` 본 분기 턴마다 채팅에 **한 줄** 고정:

```text
이번 discuss에서 끝까지: {DISCUSS §1 1문장 — scan 턴2에 paraphrase로 고정}
```

`scan` 턴2(본 AskQuestion(`question` 병용))에서 노트 §1에 위 템플릿을 **첫 메시지 paraphrase**로 작성·고정한다. 이후 매 턴 대조·인용. **multi-cycle** 새 주제마다 **새 DISCUSS + 새 §1** 리셋.

순서 고정. 아래 블록만. (Quick Pick 제외 본문 18줄 이내.)

```
{한 줄: 지금 무엇을 맞추는 중인지 — 업무 말}

{선택: 이번 턴에 확정한 한 문장. 없으면 생략}

{선택: A/B/C 각각 기대 결과 1줄 — 표 대신 불릿}

{권장: X — 이유 1줄}

카드로 고르거나, A/B/옵션 이름으로 답해 주셔도 됩니다.

AskQuestion(`question` 병용) 도구 호출  ← 갈래 2~4개면 필수. 자유 답이면 텍스트 질문 1문장. 호출 직후 DISCUSS `pending_ask` 갱신.
```

**첫 턴**: 「확정」생략. 스캔 요약 **2~3줄** + 곧바로 **방향 후보 질문 1개**.

#### GOOD (첫 턴·scan) — 복붙용 (채팅 본문 아님; 실제 턴은 18줄 규칙 적용)

```text
접수·대기 화면은 요구는 있으나, 원무가 매일 쓰는 흐름은 아직 덜 맞춰진 상태로 보입니다.

이번 discuss에서 끝까지: 원무가 매일 쓰는 접수·대기 흐름을 먼저 맞춘다.

- A) 접수·대기부터 — staff가 매일 여는 화면, 손대기 쉬움
- B) 청구·수납 연동부터 — 나중 정산이 한 번에 맞춰짐
- C) 진료 화면만 — 범위는 좁지만 체감은 빠를 수 있음

권장: A — backlog와도 맞고, 일상 업무와 직결

AskQuestion(`question` 병용) (방향 후보 1개)
```

#### GOOD (direction 턴) — 복붙용

```text
이번 discuss에서 끝까지: 에이전트가 규칙을 지키는지부터 맞춘다.

이번에 확정: 우선순위 렌즈는 «에이전트가 규칙을 지키는지»

- A) 응답 형식만 통일 — 빠르고 눈에 띔
- B) 금지 문구까지 기계 검사 — 느리지만 확실
- C) 둘 다 이번에 — 범위가 커짐

권장: A — SKILL 예시만으로도 바로 효과

AskQuestion(`question` 병용) (다음 분기 1개)
```

#### BAD (한 줄) — 이렇게 쓰지 말 것

```text
「로드맵·스펙·plans를 훑어보니 reception phase2와 claim이 겹치고… (장문) … 어떻게 생각하세요?」
```

### 채팅 금지 (MUST NOT)

- 질문 2개 이상·「그리고」「또한」이은 follow-up
- 결정 트리 전체·내부 단계 번호 노출·긴 분석 나열
- mermaid·긴 표·여러 영역 동시 심문
- 옵션 없이 「어떻게 생각하세요?」만 던지기
- 「정리」「끝」**입력을 요구하는 문장만** 던지기 (수렴 `AskQuestion`/`question`(병용) 없이)
- 사용자 종료 신호 없이 Summarize·핸드오프 **실행**
- **명령형 다음 단계** — 「다음: `@DISCUSS_…` 붙이고 `/plan` 시작」등 **채팅·노트에 슬래시·@경로 지시만 던지기** (텍스트 `close`는 §메뉴 A **AskQuestion(`question` 병용)**; converge «계획» `close`는 §Same-session plan 직행)
- **assess·분석 워크플로 옵션** — discuss `AskQuestion`/`question`(병용)에 `/assess`·「더 깊게 분석」 등 **넣지 않음**
- **이중 plan 안내 (동일 DISCUSS)** — **같은** `DISCUSS_*.md`가 이미 `handed-off`·`linked_plan`이면 그 노트에 대해 「`/plan` 다시」「Blueprint 작성」을 **재안내하지 않음**. (다음은 **구현**=해당 PLAN Task 실행). **새 주제 discuss**는 §Same-session multi-cycle — 별도 DISCUSS·PLAN 1세트씩 허용.
- **AskQuestion/`question`(병용) 없이 close 종료** — 합의 요약·「핸드오프 완료」·노트 경로만 남기고 턴을 끝내기 (마지막 행동: 텍스트 `close`→**메뉴 A**; converge «계획» `close`→**same-session plan** 후 **메뉴 B**; multi-cycle은 §산출물 요약 메뉴)

### 전송 전 자가검사 (MUST)

**의도 우선 5항** (direction·converge·close 본 분기 — 게이트·close 메뉴 제외):

- [ ] **§1 인용**: `direction`·`converge` 턴에 «이번 discuss에서 끝까지: …» **한 줄**을 썼는가?
- [ ] **(권장) 정합**: `(권장)`이 §1·누적 [확정]과 **aligned**인가? (2단계 1순위)
- [ ] **Blueprint nudge 금지**: `scan`·`direction`·`converge`에서 Blueprint·메뉴 A·«계획으로» `(권장)`을 쓰지 않았는가?
- [ ] **4요소 역전 금지**: «더 빠름·쉬움»만으로 §1 의도와 **충돌**하는 `(권장)`을 붙이지 않았는가?
- [ ] **충돌 시 AskQuestion(`question` 병용)**: §1 vs [확정] 어긋남이 있으면 **1턴 확인** 후 선정했는가?

- [ ] **AskQuestion/`question` 도구를 실제로 호출(병용)**했는가? (채팅 불릿만으로 A/B/C 제시 = FAIL)
- [ ] `AskQuestion`/`question`(병용) 호출 직후 DISCUSS **`pending_ask`** 를 갱신했는가? (다음 턴 텍스트 답 매핑 SSOT)
- [ ] 직전 턴 스킵·텍스트 답이 있었는가? → §**Typed Answer** 매핑 후 재질문 없이 진행했는가?
- [ ] `scan`·`direction` **첫 본 분기 전** 조사 게이트 턴을 거쳤는가? (게이트+본 질문을 한 메시지에 합치지 않았는가?)
- [ ] §**턴 판별 결정 트리** 1번(close 트리거) 없이 Blueprint·메뉴 A·«계획으로» `(권장)`을 쓰지 않았는가?
- [ ] `converge`인가? → **방향 확정 → 계획**이 `(권장)`이 **아닌가**? (7/7 YES·사용자 종료 신호 전이면 `(권장)`은 **심층 논의 계속**)
- [ ] `scan`/`direction`인가? → `status`를 **`discussing` 유지**했는가? (`direction-set`은 close에서만)
- [ ] 이번 턴 **질문이 정확히 1개**인가?
- [ ] **다른 분기**를 미리 노출하지 않았는가?
- [ ] 본문 **18줄** 이내인가?
- [ ] 소스 코드를 건드리지 않았는가? (노트만)
- [ ] converge «계획» `close`인가? → **메뉴 A·Blueprint 재질문 없이** same-session plan 후 **메뉴 B**만 썼는가?
- [ ] 텍스트 `close`·산출물·handed-off 재진입인가? → §**표준 메뉴** A/B·**마무리**·assess 없음? (텍스트 close에 메뉴 A 없이 PLAN = FAIL)
- [ ] PLAN·plan-lint PASS **직후**(같은 DISCUSS)인가? → **그 PLAN**에 대해 `/plan` 재안내 금지. AskQuestion(`question` 병용)에 **PLAN 전체 순차 실행**·Task 1.1만·**새 주제 discuss**·마무리 중 하나는 포함했는가?
- [ ] **새 discuss 사이클** 시작인가? → 이전 `handed-off` DISCUSS를 재편집·재-plan하지 않고 **새** `DISCUSS_<slug>.md`로 scan부터 진행하는가?

하나라도 NO면 삭제 후 재작성.

## 세션 흐름 (내부 — 사용자에게 번호 노출 금지)

| 순서 | 내부 | 한 턴에 하는 일 |
| :---: | :--- | :--- |
| 1 | `scan` | **사용자가 준 영역에 한정한 심층 스캔** → 방향 후보 + 가장 먼저 정할 분기 1개 질문 |
| 2 | `direction` | 답 확정 1문장 + (선택) 그 방향의 trade-off 1~2문장 + **다음 분기** 질문 1개 |
| 3 | `polish` | 결정이 쌓일 때마다 `DISCUSS_*.md` 노트를 **점진 갱신** — §3·Ambiguity-Zero 일부 채워도 **`status: discussing` 유지** (`direction-set`은 §종료 1단계만) |
| 3.5 | `converge` | 방향·범위가 수렴한 것 같을 때 **`AskQuestion`/`question`(병용) 수렴 메뉴**(확정 / 한 항목만 / 계속) — 매 턴 필수 아님 |
| 4 | `close` | 확정 신호 → §3 확정 + (**텍스트** → 메뉴 A \| **converge «계획»** → same-session plan 직행) |

### 1. scan (첫 턴)

- 사용자가 영역을 지정했으면 **그 영역에 한정**해 깊게 본다(소스·spec·backlog·plans·CONTEXT). 영역 미지정이면 `docs/agent-context/memory/PROJECT_REFACTORING_BACKLOG.md`·`docs/specs/`·`docs/plans/`·CONTEXT 등 앵커부터 보고 **범위를 좁히는 질문 1개**부터.
- **무한 확장 금지** — "심층이되 사용자가 준 영역에 한정". 새 영역으로 번지면 한 턴만 써서 범위를 다시 묻는다.
- **진입 순서**: §AskQuestion(`question` 병용) 직전 맥락·조사 게이트 — **턴1** `research-gate` → (선택) deep-research → **턴2** route 맥락 반영 후 스캔 요약 2~3줄 + 방향 후보 **본 AskQuestion(`question` 병용)**.

## 논의 노트 (`docs/discussions/DISCUSS_<slug>.md`)

**경량 4섹션 고정.** 결정이 쌓일 때마다 in-place 갱신(전체 재작성 금지, append/update 우선).

```markdown
---
status: discussing   # discussing | direction-set | handed-off
created: <YYYY-MM-DD>
scope: <대화 대상 영역>
linked_plan:          # handed-off 시 필수 — docs/plans/PLAN_<slug>.md
pending_ask:          # AskQuestion(`question` 병용) 직후만 — 확정·다음 분기 시 null
  turn: <scan|direction|converge|close-menu-a|close-menu-b|research-gate>
  prompt: "<질문 한 줄>"
  options:
    - id: a
      label: "<옵션 A 라벨>"
    - id: b
      label: "<옵션 B 라벨>"
---
<!-- Language: ko -->

# DISCUSS: <주제>

## 1. 현황 요약
- **이번 discuss에서 끝까지:** {scan 턴2 본 AskQuestion(`question` 병용)에서 사용자 첫 메시지 paraphrase — 1문장 고정}
- (스캔으로 파악한 사실·마찰·기회 — 불릿)

## 2. 진행 중 결정 (누적)
- [확정] <결정> — 근거 1줄
- [열림] <아직 안 정한 분기>

## 3. 합의된 방향 · 범위
- 방향: (사용자가 동의한 개선 방향)
- 이번에 하는 것 / 안 하는 것 / 완료 기준: (plan 직행 전 한 줄씩 — 미정이면 "미정")
- 엣지 케이스: (§엣지 케이스 선제 AskQuestion 답 — 인범위·범위 밖 각 1줄; 없으면 `엣지: 해당 없음 — {사유}` [확정])
- Ambiguity-Zero 체크:
  - [ ] 의도 명확
  - [ ] 범위 경계 명확
  - [ ] 용어 합의 완료
  - [ ] 완료 기준 명확
  - [ ] 열린 분기 0개
  - [ ] 숨은 가정 없음
  - [ ] 엣지 케이스 확인 (§3 「엣지 케이스」 불릿 ≥1 또는 `엣지: 해당 없음` [확정])

## 4. 미해결 · 핸드오프
- 미해결 긴장: ...
- 핸드오프: pending — (사용자 `AskQuestion`/`question`(병용) 선택 전; plan | 더 논의 | 마무리)
```

**`pending_ask` 수명**: `AskQuestion`/`question`(병용) 호출 **직후** frontmatter에 기록(prompt·options·turn). 사용자 선택 확정(카드 또는 §Typed Answer) 시 **`pending_ask: null`**. multi-cycle 새 DISCUSS 생성 시 비움.

노트 §4에 **`/plan` 실행 지시·`@DISCUSS` 첨부·Task 분해 안내**를 쓰지 않는다 — 그건 **채팅 `AskQuestion`/`question`(병용)**과 사용자 선택 **후** 해당 워크플로 SSOT가 담당한다. Blueprint 선택·PLAN 준비 후 `핸드오프: plan — YYYY-MM-DD`·`status: handed-off`만 기록(마무리·더 논의만 선택 시 handed-off **금지**).

노트는 **방향과 범위**까지만 담는다. 구체 Task·Verify·인터페이스 코드는 **여기 쓰지 않는다**(plan으로 이관).
또한 Blueprint 전환(handoff·same-session plan) **전**에는 노트 §3의 Ambiguity-Zero 7개 체크박스가 **모두 체크**되어야 한다.

## 수명·보관 (handed-off 이후)

- **SSOT**: [DOC_discuss_lifecycle.md](../../../docs/discussions/DOC_discuss_lifecycle.md) — status 3값, `linked_plan`, `docs/discussions/archive/` 이관.
- **`handed-off` 기록 시**: frontmatter `linked_plan:` 에 plan repo 상대 경로를 채운다( plan 파일 생성 직후 동일 세션).
- **plan 아카이브 후**: `archive_discussions`가 연결 discuss를 `docs/discussions/archive/`로 옮긴다 — 노트를 루트에 두지 않는다.
- **검사**: `just docs-discuss-lifecycle` — 신규·수정 discuss의 `handed-off` + `linked_plan` 누락 시 FAIL.

## 방향 수렴 (converge) — pre-close

**언제**: §2 `[열림]`이 0~1개이고 방향·범위가 한 덩어리로 맞아 보일 때. `direction` 중 **수렴 직전 1턴**에만 쓴다(매 턴 필수 아님).

**조기 종료 권장 금지 (가드레일)**: `[열림]` 항목이 0개가 되었다고 해서 기계적으로 `방향 확정 → 계획으로` 옵션을 `(권장)`하지 않는다. 사용자가 명시적으로 멈추자고 하기 전까지는, 에이전트가 주도적으로 논의에서 누락된 심층 주제(예: 예외 처리, UI 세부 스펙, 연동 리스크 등)를 새 `[열림]` 질문으로 발굴하여 이를 `(권장)` 옵션으로 제시함으로써 브레인스토밍 파트너로서 논의를 계속 파고든다.

**엣지 케이스 수렴 전제 (converge 게이트)**: 수렴 메뉴에 **「방향 확정 → 계획으로」**를 넣기 **전** — (a) §엣지 케이스 선제 유도 AskQuestion **≥1턴** 완료, **또는** (b) §3에 `엣지: 해당 없음 — {사유}`가 `[확정]`으로 기록. (a)(b) 모두 없으면 첫 옵션 `(권장)`은 **반드시** `{예외·빈 화면·저장 실패} 더 논의하기`(plain-language §엣지 케이스 선제).

**행동** (본문 18줄 이내 유지):
1. 합의 요약 **2~3줄**(또는 이번 턴 확정 1문장) + **권장 1줄**. (권장은 심층 논의 계속을 기본으로 함)
2. **`AskQuestion`/`question`(병용) 수렴 메뉴** — 텍스트로 「정리」입력을 요구하지 않는다.

| 옵션 (라벨 예) | 다음 |
| :--- | :--- |
| **방향 확정 → 계획으로** | `close` 트리거 — §3·`direction-set` 후 **§Same-session plan 직행**(메뉴 A·Blueprint **재질문 생략**) |
| **{새로운 심층 주제} 더 논의하기** `(권장)` | 새 분기를 발굴하여 **질문 1개** 추가 (`direction` 유지) |
| **아직 더 논의** | `direction` 계속, 노트만 갱신 |

- **방향 확정 → 계획으로** 선택 = Blueprint 작성 의사 **확정** + `close` — **같은 세션**에서 PLAN 작성(plan-lint PASS)까지 진행. **메뉴 A로 «Blueprint 만들기」를 다시 묻지 않는다**.
- `{새로운 심층 주제}`는 에이전트가 새롭게 제안하는 다음 논의 포인트를 명시한다.

### Blueprint 생성 허용 게이트 (Ambiguity-Zero) (MUST)

`실행 계획(Blueprint)으로 만들기`를 handoff·converge «계획으로»에 넣기 **전**, 아래 7개가 **모두 YES**여야 한다. 특히 추상적인 "접근법(예: 바텀업, 점진적)"만 합의된 상태에서 범위를 명확하다고 착각하여 조기 종료(converge)하지 않도록 주의한다.

1. **의도 명확**: 이번 논의의 최종 목표를 한 문장으로 고정 가능.
2. **범위 경계 명확**: 이번에 하는 것/안 하는 것을 각 1줄로 분리 가능하며, **추상적인 방향성이나 방법론이 아닌 구체적인 실체(예: 구체적인 컴포넌트 목록, 정확한 패널 이름)가 명시**되어야 함. (예: "기초 컴포넌트 개발" ❌ -> "Button, Input 컴포넌트 2개 개발" ✅)
3. **용어 합의 완료**: 사용자와 에이전트가 같은 단어를 같은 의미로 사용.
4. **완료 기준 명확**: "무엇이 되면 끝인지"를 관찰 가능한 문장으로 작성 가능하며, 세부 방향(예: 어떤 디자인 시스템을 쓸지, 어떤 상태까지 구현할지)이 포함되어야 함.
5. **열린 분기 0개**: 노트 §2의 `[열림]` 항목이 없음.
6. **숨은 가정 없음**: "아마", "필요 시", "일단" 같은 미확정 표현이 §3/§4에 없음.
7. **엣지 케이스 확인**: §3 「엣지 케이스」 불릿 ≥1 **또는** `엣지: 해당 없음 — {사유}`가 `[확정]` — §엣지 케이스 선제 AskQuestion으로 답이 기록됨.

하나라도 NO면 Blueprint 전환 금지. 해당 항목만 좁히는 `AskQuestion`/`question`(병용) 1개를 먼저 수행한다.

## 종료 (close) — 사용자 신호 우선

**트리거** (둘 중 하나):
- 사용자가 「정리」「끝」「방향 정해졌다」라고 하거나
- **수렴 메뉴**에서 **방향 확정 → 계획으로**(또는 동등 라벨)를 선택했을 때

그 전엔 대화를 계속하고 노트만 점진 갱신한다. 방향이 잡혀 보여도 **에이전트가 먼저 `close`를 실행하지 않는다** — **`converge` 턴**으로 `AskQuestion`/`question`(병용) 수렴 메뉴를 제시한다.

**종료 시** (공통 1~2):
1. 합의 방향 + **범위 스케치**를 노트 §3에 확정, `status: direction-set`로 갱신.
2. 노트 §4 — converge «계획» 경로: `핸드오프: plan — in progress` 후 PLAN 완료 시 `handed-off` 갱신. 텍스트 close만: `핸드오프: pending`(명령형 다음 단계 금지).

**텍스트 close 전 계획 의도 확인 (MUST)** — converge «계획» **없이** 「정리」「끝」「방향 정해졌다」만 온 경우, **메뉴 A 전** `AskQuestion`/`question`(병용) **1개**:

- 「이번 discuss의 목표가 **실행 계획(Blueprint) 문서**까지인가요?」
- **예** → 메뉴 A에서 Blueprint `(권장)` 허용 (§1·답변에 계획 의도 있을 때)
- **아니오** → 메뉴 A에서 **이 주제 더 논의하기** `(권장)`, Blueprint `(권장)` **금지**

**converge «방향 확정 → 계획으로»** 선택 = plan 의사 **확인 완료** — 위 질문·메뉴 A **생략** → §Same-session plan 직행.

**경로 분기** (3):
- **A — converge «방향 확정 → 계획으로」 직후**: 채팅 합의 요약 2~3줄 → **§Same-session plan** (메뉴 A·계획 확인 **생략**) → 산출물 요약 **메뉴 B**.
- **B — 「정리」「끝」「방향 정해졌다」만**: 합의 요약 2~3줄 → **«계획 문서가 목표?»** → **표준 메뉴 A `AskQuestion`/`question`(병용)**.

**금지**: converge «계획» 선택 뒤 **메뉴 A·Blueprint 재질문**. 채팅에 `/plan`·파일 첨부 지시만 텍스트로 쓰기.

## 표준 AskQuestion/`question`(병용) 메뉴 (MUST)

주제 분기(`scan`·`direction`·`converge`)가 **아닌** discuss 마무리 턴은 **항상** 아래 메뉴로 `AskQuestion`/`question`(병용)을 끝낸다. 라벨 예는 [plain-language-questions.md](references/plain-language-questions.md) §표준 메뉴.

- 옵션 **3~4개**, `(권장)` **정확히 1개**
- **「여기서 마무리」는 항상 마지막 옵션**
- **assess·「더 깊게 분석」옵션 금지**

| 메뉴 | 언제 | `(권장)` | 구성 |
| :--- | :--- | :--- | :--- |
| **A — 설계 전** | **텍스트** `close`만 (`linked_plan` 없음). converge «계획» 경로 **금지** | §1·close 확인에 **계획 의도 있을 때만** Blueprint; **없으면** **이 주제 더 논의** | 권장 + 부가 1~2 + **마무리** |
| **B — 설계 후** | 산출물 요약, handed-off 재진입, PLAN 존재 | **이 PLAN 전체 순차 실행** | 권장 + 부가 1~2 + **마무리** |

### 메뉴 A — 설계 전 (핸드오프)

**`(권장)` 조건**: §1 «이번 discuss에서 끝까지: …»·close «계획 문서가 목표?» **답변**에 **계획·설계 넘기기 의도**가 있을 때만 **Blueprint** `(권장)`. §1에 계획 의도 **없으면** — 「끝」이어도 **이 주제 더 논의하기** `(권장)`, Blueprint `(권장)` **금지**.

| 순서 | 옵션 라벨 (예) | 선택 후 |
| :---: | :--- | :--- |
| 1 | **실행 계획(Blueprint)으로 만들기** | §Same-session plan 연속 |
| 2 | **이 주제 더 논의하기** | `direction` 계속 |
| 3 | **여기서 마무리** | 세션 종료(PLAN·handed-off 없음) |

- 부가를 2개 쓸 때: 2번에 **{§2 [열림] 한 항목}만 더 맞추기** 등 **한 가지**를 넣고, **마무리는 항상 마지막**.

### 메뉴 B — 설계 후 (산출물·재진입)

| 순서 | 옵션 라벨 (예) | 선택 후 |
| :---: | :--- | :--- |
| 1 | **이 PLAN 전체 순차 실행** `(권장)` | `plan-lint` PASS Blueprint **동결** — Dependency 순 Task 전부(Verify→`plan-task-close` 반복) — [plan.md](../../workflows/plan.md) §Blueprint 실행 동결 |
| 2 | **Task 1.1만 먼저 시작** | 해당 PLAN Task 1.1만 착수(동일 동결 규칙) |
| 3 | **새 주제로 discuss 더 하기** | §Same-session multi-cycle |
| 4 | **여기서 마무리** | 세션 종료 |

- **같은 DISCUSS**에 메뉴 A·「Blueprint 만들기」**재호출 금지**.

## Handoffs (EMR)

| `close` 경로 | 마무리 |
| :--- | :--- |
| **converge «방향 확정 → 계획으로」** | 메뉴 A **없음** → §Same-session plan 직행 |
| **텍스트** (정리·끝·방향 정해졌다) | **표준 메뉴 A `AskQuestion`/`question`(병용)** 필수 |

**메뉴 A 선택 시**:

| 선택 | 다음 |
| :--- | :--- |
| Blueprint `(권장)` | §Same-session plan |
| 이 주제 더 논의 | `direction`, §4 `pending` 유지 |
| 마무리 | 세션 종료 |

**`handed-off` 기록 시점**: `PLAN_*.md`·plan-lint PASS·`linked_plan` **후에만**. 선택 전 채팅·노트에 「@… + /plan」형 문장 금지.

## Same-session plan 연속 (MUST)

**트리거** (둘 중 하나):
- converge **「방향 확정 → 계획으로」** 선택 직후 `close`
- **텍스트** `close` 후 메뉴 A에서 **실행 계획(Blueprint)으로 만들기** 선택

**에이전트 순서** (사용자에게 `/plan`을 시키지 않음):

1. [plan.md](../../workflows/plan.md) SSOT Read.
1b. §3 「엣지 케이스」·Ambiguity-Zero 7번 **없으면** [plan.md §Edge Case Design Gate](../../workflows/plan.md) **AskQuestion 1턴** → 답을 DISCUSS §3에 먼저 기록.
2. `DISCUSS_*.md` §3·§2·엣지 불릿을 입력으로 `docs/plans/PLAN_<slug>.md` 작성(Origin Intent · Edge Case Trace 포함) → `just plan-preread` → `just plan-lint` PASS.
3. DISCUSS frontmatter `linked_plan`·`status: handed-off`·§4 한 줄 갱신.
4. **산출물 요약 턴**으로 채팅 종료(§산출물 요약 턴). **같은 DISCUSS**에 대해 「Blueprint 작성」AskQuestion(`question` 병용) **재호출 금지** — **새 주제 discuss**는 §Same-session multi-cycle.

### 산출물 요약 턴

plan-lint PASS **직후 같은 세션·같은 DISCUSS** 전용. 본문 18줄 이내. 마지막은 **표준 메뉴 B `AskQuestion`**(§표준 AskQuestion/`question`(병용) 메뉴).

**필수 포함**:

- 논의·방향: 방금 `handed-off`한 DISCUSS 노트 한 줄.
- 설계: 방금 작성한 PLAN 한 줄(Task 개수·plan-lint PASS).
- **다음 단계(필수 문장)**: **이 PLAN**에 대해 Blueprint 작성은 **이미 끝났음**을 명시. (같은 DISCUSS 재-plan 안내 금지)

**금지 문구** (이 턴에 쓰지 말 것):

- **이 DISCUSS·PLAN**에 대해 `/plan` 다시 · plan 시행 · Blueprint 작성 · 노트 붙여 /plan
- **같은 handed-off DISCUSS**에 「실행 계획(Blueprint)으로 만들기」재호출
- 「정리」「끝」만 던지고 선택 없이 종료

#### GOOD (산출물 요약 턴) — 복붙용

```text
논의: DISCUSS 접수 개선 — handed-off, 방향·범위 확정.
설계: PLAN 접수 phase2 — Task 5개, plan-lint PASS.

이 주제의 설계는 끝났습니다. 다음은 이 PLAN 전체를 순서대로 실행하거나, Task 1.1만 시작하거나, 다른 주제를 새로 논의할 수 있습니다.

AskQuestion(`question` 병용): 이 PLAN 전체 순차 실행 (권장) / Task 1.1만 / 새 주제 discuss / 마무리
```

**단계 구분 (채팅에 쓸 말)**:

| 이미 있는 것 | 사용자에게 말하는 다음 단계 | 금지 |
| :--- | :--- | :--- |
| DISCUSS만 (텍스트 close) | 표준 **메뉴 A** | PLAN 있다고 가정 |
| DISCUSS + converge «계획» close | **same-session plan** → **메뉴 B** | **메뉴 A·Blueprint 재질문** |
| DISCUSS + PLAN (방금 작성, 같은 주제) | 표준 **메뉴 B** (PLAN 전체 실행 권장 · Task 1.1만 · 새 주제 · 마무리) | **같은 DISCUSS**에 Blueprint 재안내 |
| DISCUSS handed-off + linked_plan (재진입) | 표준 **메뉴 B** | **그 DISCUSS**에 `/plan`·Blueprint 재안내 |
| 세션 내 N번째 discuss→plan 완료 | 위와 동일 — **주제마다** DISCUSS+PLAN 1세트 | 이전 handed-off DISCUSS **재편집·재-plan** |

## Same-session multi-cycle (MUST)

**목적**: 한 채팅 세션에서 discuss→plan을 **주제마다 반복** — A 주제 Blueprint 작성 후 B 주제를 새로 논의하고 **별도** Blueprint를 또 만들 수 있다.

**트리거** (둘 중 하나):

- 산출물 요약 턴 **`AskQuestion`/`question`(병용)에서 「새 주제로 discuss 더 하기」** 선택
- close **메뉴 A**에서 「이 주제 더 논의하기」— `direction` 계속 (동일 노트, §4 `pending` 유지)

**에이전트 순서**:

1. **이전 DISCUSS는 그대로** — `handed-off`·`linked_plan` 유지, 본문 **수정 금지**.
2. **새** `docs/discussions/DISCUSS_<new_slug>.md` 생성 (`status: discussing`, §1~4 뼈대) — **새 §1** «이번 discuss에서 끝까지: …» 리셋.
3. `scan`부터 재진입 — 사용자가 준 새 주제·영역에 한정. 이전 PLAN·Task·§1과 **섞지 않음**.
4. 새 주제 `close` → converge «계획» 또는 메뉴 A Blueprint 선택 시 → **새** `PLAN_<new_slug>.md` → plan-lint PASS → **새 DISCUSS**만 `handed-off`·`linked_plan` 갱신.
5. 4 완료 후 다시 **산출물 요약 턴** — 2~4를 사용자가 멈출 때까지 반복 가능.

**slug 규칙**: 주제가 다르면 DISCUSS·PLAN slug도 **다르게**. 같은 slug로 두 번째 PLAN을 덮어쓰지 않는다. slug는 **의미 단어(kebab/snake)** 만 쓰고 순서·이슈 번호(`01_`, `tem102`, `20260418`)는 넣지 않는다 — [DOC_documentation_governance.md §2](../../../docs/ops/rules/DOC_documentation_governance.md).

**금지**:

- handed-off DISCUSS를 reopen하여 두 번째 PLAN에 연결
- 「이미 Blueprint가 있으니 discuss/plan 불가」 — **세션·주제 단위**로만 금지(동일 DISCUSS)
- 새 사이클에서 이전 PLAN의 Task 번호·범위를 섞어 적기

### handed-off 이후 (동일 DISCUSS·재진입)

**대상**: 특정 `DISCUSS_*.md`가 이미 `handed-off`이고 `linked_plan` PLAN이 **디스크에 존재**할 때, 사용자가 **그 노트·그 주제**로 다시 들어온 경우.

- **그 DISCUSS에 대해** `/plan`·메뉴 A(Blueprint) **재호출 금지**.
- 마지막은 **표준 메뉴 B `AskQuestion`/`question`(병용)**만.

**「새 주제로 discuss 더 하기」** 선택 시 → §Same-session multi-cycle 1번부터.

## Principles

- 추천 없이 질문만 던지지 않는다 — **권장 1줄**은 매 턴.
- 답이 막연하면 **그 분기만** 한 번 더 좁힌다(새 분기 추가 금지).
- 소스 코드는 **절대** 건드리지 않는다 — 합의가 끝나면 핸드오프로만 구현 단계 진입.
- 노트는 **방향의 정본**이고, 회의록처럼 길게 쌓지 않는다(4섹션 cap).
