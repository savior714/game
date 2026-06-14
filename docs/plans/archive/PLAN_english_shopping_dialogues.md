---
id: ENG-SHOP-001
type: PLAN
status: active
last_verified: 2026-06-14
---
<!-- Language: ko -->

# 🗺️ Project Blueprint: 영어 게임 쇼핑 대화문 20개 템플릿 추가

## 문서 메타
- SSOT Check: advanced-questions.js, engine.js
- Architectural Goal: 쇼핑 대화문 20개 템플릿 추가 — 기존 문장빈칸 UI 재사용
- Priority: 2

## 📋 업무 요약 (협업용)

영어 게임에 clothing 쇼핑 대화문 20개 템플릿을 추가합니다. 구매/사이즈/색상/가격 4상황 × 셔츠/재킷/바지/신발/모자 5의류 항목입니다. 기존 문장빈칸 UI를 재사용해 별도 UI 개발 없이 구현합니다.

### 개요
- clothing 쇼핑 대화문 20개 템플릿을 advanced-questions.js에 추가
- engine.js에 shopping_dialogue 유형 처리 추가
- 기존 문장빈칸 UI 재사용 — 별도 UI 개발 없음

### staff·경영에서 바뀌는 점
- 영어 게임 문제 유형에 shopping_dialogue 추가 (level 3+ 출제 확률 15%)
- clothing 카테고리 단어 재사용 — 학습자가 쇼핑 상황에서 실제로 쓰는 표현 익힘

### 끝났을 때 확인할 것
- advanced-questions.js에 SHOP_DIALOGUES 20개 템플릿 정의 확인 (예: SHOP_DIALOGUES 문자열 존재)
- engine.js에 shopping_dialogue 유형 처리 확인 (Q_TYPE_ORDER, rows 배열 6개 요소 재조정)
- verify_english_engine.js에 SHOP_DIALOGUES 검증 로직 추가 확인
- node domains/english/verify_english_engine.js 실행 시 SHOP_DIALOGUES 검증 섹션 PASS

## 🎯 Origin Intent
DISCUSS_english_shopping_dialogues.md에서 합의: clothing 쇼핑 대화문 20개 템플릿을 advanced-questions.js에 추가하고, engine.js에 shopping_dialogue 유형을 추가해 기존 문장빈칸 UI로 출제한다.

## ⚠️ Edge Case Trace
| Origin/Risk | 케이스 | Task-ID | 범위 밖 (사유) |
|---|---|---|---|
| shopping_dialogue 정답이 makeWordChoices 보기에 포함 | clothing 단어 풀이 넓어 오답 보기에 정답 단어 우연히 포함될 수 있음 | Task 1.1, Task 2.1 | — |
| weeklyWords(보호자 등록 단어)와 shopping_dialogue 혼동 | isWeekly 플래그로 구분 필요 — weeklyWords가 없으면 shopping_dialogue 출제 안 될 수 있음 | Task 2.1 | — |
| blank:true 줄의 answer 필드 누락 | 템플릿 정의 시 answer 배열이 없으면 보기 생성 실패 | Task 1.1 | — |
| 기존 sentence 유형과 UI 충돌 | shopping_dialogue는 blank:true 줄만 렌더링 — sentence와 다른 플로우 | Task 2.1 | — |
| 빈 clothing 카테고리 | clothing 단어 27개 중 일부만 사용 — 나머지 unused | Task 1.1 | — |

## 📜 Conceptual Sketch

```text
shopping_dialogue 유형 추가
  → SHOP_DIALOGUES 데이터 (advanced-questions.js)
  → engine.js 유형 처리 (Q_TYPE_ORDER, pickQuestionType, buildQuestion)
  → 기존 문장빈칸 UI 재사용 (blank:true 줄만 보기 버튼)
  → verify_english_engine.js 테스트
```

## 🛡️ Risk & Strategy

- **Risk**: shopping_dialogue 유형이 기존 sentence/typing 유형과 충돌 — **Strategy**: buildQuestion에서 유형별 분기 명확히 분리, blank:true 플래그로 정답 위치 식별
- **Risk**: clothing 단어 부족으로 보기 생성 실패 — **Strategy**: makeWordChoices가 전역 WORDS 풀 사용하므로 clothing 외 카테고리 단어에서도 보기 생성

## 🔍 Impact Scope

| 영역 | 경로 |
| :--- | :--- |
| 데이터 | domains/english/advanced-questions.js |
| 엔진 | domains/english/engine.js |
| 테스트 | domains/english/verify_english_engine.js |

## [관련 명세]
- `docs/discussions/DISCUSS_english_shopping_dialogues.md` — 쇼핑 대화문 방향 합의
- `domains/english/advanced-questions.js` — 고급 문제 유형 (sentence, minimal_pair) 구현
- `domains/english/engine.js` — 문제 생성 엔진 (buildQuestion, pickQuestionType)
- `domains/english/ui.js` — 문장빈칸 UI (seqBlanks, checkSeqAnswer)

## Agent Completion Contract

| 허용 | 금지 |
| :--- | :--- |
| Verify PASS | Blueprint 구조 변경 (Task 추가/삭제/재번호) |

**Task 완료 정의**: Verify → plan-lint PASS.

## 🛠️ Step-by-Step Execution Plan

> **에이전트 스코프**: Task 1개씩. `Verify` PASS → **Conclusion** → `just plan-lint docs/plans/archive/games/PLAN_english_shopping_dialogues.md`.

#### Task 1.1: advanced-questions.js에 SHOP_DIALOGUES 상수 추가 (20개 템플릿) [Unit: Atomic]

- **Task-ID**: [ENG-SHOP-001-001] | Linear-Issue: N/A | Status: done | Priority: 2 | Labels: english-game | RetryPolicy: none
- **Pre-read**: 이 Task만 Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[source]` domains/english/advanced-questions.js
  2. `[source]` domains/english/words.js (clothing 카테고리 데이터 구조 참고)
- **Action**: Edit File | **Target**: `domains/english/advanced-questions.js`
- **Goal**: SHOP_DIALOGUES 배열 상수 정의 — clothing 5개(셔츠/재킷/바지/신발/모자) × 4상황(구매/사이즈/색상/가격) = 20개 템플릿. 각 템플릿: `{speaker, line, blank, answer}` 구조. blank:true인 줄이 학습자 정답 위치, answer에 정답 단어 배열 포함.
- **중요**: 각 템플릿에 고유 `id` 필드 추가 (예: `"shirt_buy"`). engine.js의 `recentQuestions`에 `_wordEn`만 사용하면 같은 단어의 4상황이 중복 방지에서 누락되므로, `wordEn + dialogueId` 조합 키를 사용해야 함
- **Diagnostics**: 0
- **Verify**: `python3 -c "import sys; sys.exit(0 if open('domains/english/advanced-questions.js').read().count('SHOP_DIALOGUES') > 0 else 1)"`
- **Conclusion**: SHOP_DIALOGUES 20개 템플릿 advanced-questions.js에 정의 완료. verify_english_engine.js 실행 시 SHOP_DIALOGUES 검증 섹션 PASS 확인.
- **Dependency**: None

#### Task 1.2: engine.js에 shopping_dialogue 유형 처리 추가 [Unit: Atomic]

- **Task-ID**: [ENG-SHOP-001-002] | Linear-Issue: N/A | Status: done | Priority: 2 | Labels: english-game | RetryPolicy: none
- **Pre-read**: 이 Task만 Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[source]` domains/english/engine.js
  2. `[source]` domains/english/advanced-questions.js (SHOP_DIALOGUES 구조 참고)
- **Action**: Edit File | **Target**: `domains/english/engine.js`
- **Goal**: Q_TYPE_ORDER에 'shopping_dialogue' 추가, pickQuestionType에 shopping_dialogue 확률 가중치 추가 (level 3+), buildQuestion에 shopping_dialogue case 추가 — SHOP_DIALOGUES에서 랜덤 선택, blank:true 줄의 answer로 보기 생성, generateQuestion에서 shopping_dialogue 중복 방지
- **중요**: `pickQuestionType`의 `rows` 객체는 인덱스 기반 확률 배열 — 기존 5개 요소 → 6개 요소로 모든 레벨(0~6) 배열 재조정 필수. `Q_TYPE_ORDER`에 `'shopping_dialogue'`가 삽입된 위치의 인덱스에 대응하는 확률 값 추가
- **Diagnostics**: 0
- **Verify**: `python3 -c "import sys; c=open('domains/english/engine.js').read().count('shopping_dialogue'); sys.exit(0 if c >= 3 else 1)"`
- **Conclusion**: engine.js에 shopping_dialogue 유형 처리 추가 완료 (Q_TYPE_ORDER, pickQuestionType rows 재조정, buildQuestion case 추가). verify_english_engine.js 실행 시 shopping_dialogue 참조 3개 이상 PASS 확인.
- **Dependency**: Task 1.1

#### Task 1.3: verify_english_engine.js에 shopping_dialogue 테스트 추가 [Unit: Atomic]

- **Task-ID**: [ENG-SHOP-001-003] | Linear-Issue: N/A | Status: done | Priority: 2 | Labels: english-game | RetryPolicy: none
- **Pre-read**: 이 Task만 Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[source]` domains/english/verify_english_engine.js
  2. `[source]` domains/english/advanced-questions.js (SHOP_DIALOGUES 구조 참고)
  3. `[source]` Justfile (레시피 추가 필요 확인)
- **Action**: Edit Files | **Target**: `domains/english/verify_english_engine.js`
- **Goal**: SHOP_DIALOGUES 데이터 구조 검증 (20개 템플릿, 각 항목 speaker/line/blank/answer 필드), shopping_dialogue 유형 buildQuestion 결과 검증 (정답, 보기 4개, blank:true 줄 식별), 기존 문장빈칸 UI와 호환 확인 (answer, choices 필드). verify_english_engine.js에 SHOP_DIALOGUES 검증 로직 추가 — 기존 WORDS 데이터 무결성 검사 뒤에 `SHOP_DIALOGUES` 구조 검증 섹션 추가.
- **Diagnostics**: 0
- **Verify**: `python3 -c "import subprocess, sys; result = subprocess.run(['node', 'domains/english/verify_english_engine.js'], capture_output=True); sys.exit(result.returncode)"`
- **Conclusion**: verify_english_engine.js에 SHOP_DIALOGUES 구조 검증 섹션 추가 완료. node domains/english/verify_english_engine.js 실행 시 SHOP_DIALOGUES 검증 섹션 PASS 확인.
- **Dependency**: Task 1.2

## 🔁 Conclusion & Summary
advanced-questions.js에 SHOP_DIALOGUES 20개 템플릿 추가, engine.js에 shopping_dialogue 유형 처리 추가, verify_english_engine.js 테스트 추가 완료. clothing 쇼핑 대화문이 기존 문장빈칸 UI로 정상 출제되며, 보호자 등록 단어(weeklyWords)와 혼동 없이 shopping_dialogue 유형이 level 3+에서 출제됨.

## ✅ Definition of Done (DoD)
- `python3 -c "import sys; sys.exit(0 if open('domains/english/advanced-questions.js').read().count('SHOP_DIALOGUES') > 0 else 1)"`
- `python3 -c "import sys; c=open('domains/english/engine.js').read().count('shopping_dialogue'); sys.exit(0 if c >= 3 else 1)"`
- `node domains/english/verify_english_engine.js` — SHOP_DIALOGUES 구조 검증 섹션 PASS
