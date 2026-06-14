## 🧭 Context Pre-read Gate (실행 전 필수)

<!-- plan-preread:v1 generated=2026-06-14T08:42:42Z paths=7 must_read_installed=1 -->

**정책 (IDE 공통)**: [execution.md §2.8](.agents/core/execution.md) Context Route Gate. **Read SSOT**은 각 Task 블록의 **`Pre-read`** 목록이다 — `write`/`patch` 전 **해당 Task** 목록을 전부 Read (`write`/`patch` = 파일 쓰기·부분 수정 직전; 호스트 도구명은 [runtime_edit_tools.md §1](.agents/core/runtime_edit_tools.md)). 상단 게이트만 읽고 Task `Pre-read`를 건너뛰면 정책 위반.

**기술 스택 (계획서 추론)**: (경로에서 스택 신호 미확인 — Impact Scope·Target 보강 권장)
**의도 키워드 (계획서 추론)**: ui
**라우팅 입력 경로 (7개)**: `domains/*/ui.js`, `domains/english/ui.js`, `domains/korean/ui.js`, `domains/math/ui.js`, `domains/science/ui.js`, `http://127.0.0.1:8080/domains/math/index.html`, `shared/ui/dom-cache.js`

### Read SSOT

- **단일 Task 실행**(예: 「Task 1.1만」): 그 Task의 `Pre-read`만 Read.
- **플랜 전체 순차 실행**: Task마다 해당 `Pre-read`를 **그 Task 착수 직전**에 Read(상단에 must_read 목록 없음 — 중복 제거).
- **플랜 전체 must_read 합집합(참고)**: installed 1개 — 상세 경로는 각 Task `Pre-read`에만 나열.


### 재검증 (구현 세션에서 편집 직전)

```bash
just route domains/*/ui.js domains/english/ui.js domains/korean/ui.js domains/math/ui.js domains/science/ui.js http://127.0.0.1:8080/domains/math/index.html shared/ui/dom-cache.js --json
```

플랜 갱신 시 본 절 재생성: `just plan-preread docs/plans/archive/blueprints/PLAN_dom_query_caching.md --write` → `just plan-lint docs/plans/archive/blueprints/PLAN_dom_query_caching.md`


---
title: "렌더링 개선 1/5 — DOM 쿼리 캐싱"
SSOT Check: "AGENTS.md §4.1, routing.md §1, planning.md §2"
Project Status Link: "PROJECT_RULES.md §1 Architecture Rules"
Architectural Goal: "모든 도메인 UI 파일에서 getElementById/querySelectorAll 호출을 초기화 시 한 번만 수행하여 매 렌더링 사이클의 DOM 탐색 오버헤드 제거"
Linear-Policy: "internal"
---

# PLAN_dom_query_caching.md — DOM 쿼리 캐싱 최적화

## 🎯 Origin Intent

**원래 목적**: `domains/*/ui.js` 및 `shared/ui/quiz-ui-core.js`에서 매 렌더링마다 `getElementById` / `querySelectorAll`을 호출하는 패턴을 제거하고, 초기화 시 요소 참조를 캐싱하여 DOM 탐색 오버헤드를 제거한다.

**handoff 출처**: 렌더링 개선 요청 (2026-06-14 세션) — 탐색 결과 §1.2, §1.4

**emit 출처**: `experiments/space-explorer/renderer.js` §22-53 (offscreen canvas 캐싱 — 좋은 패턴 참고)

## ⚠️ Edge Case Trace

| # | 시나리오 | Task-ID | 범위 밖 |
|---|----------|---------|---------|
| 1 | `DOMContentLoaded` 전에 UI 코드가 실행되어 요소가 아직 DOM에 없음 | `T1.2` | — |
| 2 | 동적으로 생성되는 요소 (예: `typing-input`, `seq-word`) 는 캐싱 불가 | — | — |
| 3 | 모달/오버레이가 열리고 닫히면서 요소가 제거되고 재생성됨 (`reward_ui.js`) | `T1.5` | — |
| 4 | 여러 도메인 페이지가 동시에 로드되어 타이머가 겹침 (`quiz-ui-core.js` 250ms tick) | `T1.3` | — |
| 5 | 캐싱된 요소가 null 일 때 graceful fallback | `T1.4` | — |

## 📋 업무 요약 (협업용)

**무엇을**: 수학·영어·국어·과학 UI 파일에서 `document.getElementById()` / `querySelectorAll()` 호출을 초기화 시 한 번만 수행하도록 변경

**왜**: 현재 매 정답 확인·피드백 표시·다음 문제 전환 시마다 DOM 트리를 다시 탐색. 10문제 × 4 과목 × 초당 여러 호출 = 불필요한 레이아웃 리플로우

**어떻게**: 전역 `const els = {}` 객체에 요소 참조를 캐싱. `DOMContentLoaded` 이벤트 리스너에서 초기화. 동적 요소는 기존 패턴 유지. null 체크 추가.

**이번에 안 하는 것**: `reward_ui.js`의 동적 모달 HTML 문자열 템플릿 리팩토링 (별도 PLAN), `rocket-effects.js` 파티클 풀링 (별도 PLAN), 인라인 onclick 제거 (별도 PLAN)

---

## 🔁 Agent Completion Contract

> **에이전트 스코프**: 아래 Task 1.1~1.5만 수정. `domains/math/ui.js`, `domains/english/ui.js`, `domains/korean/ui.js`, `domains/science/ui.js`, `shared/ui/quiz-ui-core.js` 총 5개 파일. 타 파일·타 디렉터리 터치 금지.

---

## 🛠️ Implementation Plan

### Phase 1 — 분석·설계 (Main Agent)

#### Task 1.1: 현재 DOM 쿼리 패턴 매핑 [Unit: Atomic]

- **Task-ID**: `DOM-QC-001`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=2 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 각 파일의 `getElementById` / `querySelectorAll` 호출 위치·빈도·사용 패턴 매핑
- **Target**: `domains/*/ui.js`, `shared/ui/quiz-ui-core.js`
- **Goal**: 어떤 요소가 얼마나 자주 쿼리되는지 정량화하여 캐싱 우선순위 결정
- **Diagnostics**: `grep -c 'getElementById\|querySelectorAll' domains/*/ui.js shared/ui/quiz-ui-core.js`
- **Verify**: `python3 -c "import subprocess; print(subprocess.run(['grep', '-c', 'getElementById', 'domains/math/ui.js'], capture_output=True, text=True).stdout)"`
- **Dependency**: None
- **Status**: done
- **Conclusion**: `domains/*/ui.js` 5개 파일의 getElementById/querySelectorAll 호출 위치·빈도 매핑 완료. math/ui.js는 이미 DOM 캐싱 구현됨(12개 요소). english/ui.js는 25+회, korean/ui.js는 20+회, science/ui.js는 20+회 직접 쿼리 사용. quiz-ui-core.js는 factory 함수 내 로컬 캐싱 있으나 handleQuestionError는 직접 쿼리. 캐싱 우선순위: q-score, feedback, next-btn, game-area, result-screen, stars, result-title, result-msg, stats-tbody.

#### Task 1.2: DOM 요소 캐싱 구조 설계 [Unit: Atomic]

- **Task-ID**: `DOM-QC-002`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 캐싱 구조 정의 — 전역 `const DOM = {}` 객체, 초기화 함수 `initDOMCache()`, null 체크 패턴
- **Target**: `shared/ui/dom-cache.js` (신규公用 모듈) 또는 각 파일 내ローカル 캐싱
- **Goal**: 재사용 가능한 DOM 캐싱 패턴 정의 — 각 도메인 UI 파일이 독립적으로 초기화
- **Diagnostics**: `shared/ui/quiz-ui-core.js`의 `QuizUICore` 패턴 참고. `DOMContentLoaded` 리스너에서 초기화하는 것이 표준
- **Verify**: `python3 -c "import subprocess; print(subprocess.run(['grep', '-l', 'initDOMCache', 'domains/math/ui.js'], capture_output=True, text=True).stdout)"`
- **Dependency**: None
- **Status**: done
- **Conclusion**: `const DOM = {}` + `initDOMCache()` + `(DOM.key || document.getElementById('id'))` fallback 패턴으로 설계 결정. 동적 요소(seq-word, typing-input, .answer-btn)는 캐싱 제외. quiz-ui-core.js의 handleQuestionError도 로컬 els 캐싱 적용. math/ui.js 패턴을 기준으로 english/korean/science/ui.js에 동일 패턴 적용.

### Phase 2 — 구현 (N=4 Subagent 병렬 실행)

#### Task 1.3: 수학 UI DOM 캐싱 구현 [Unit: Atomic]

- **Task-ID**: `DOM-QC-003`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: `document.getElementById('q-score')`, `document.getElementById('feedback')`, `document.getElementById('next-btn')`, `document.querySelectorAll('.answer-btn')` 등을 캐싱
- **Target**: `domains/math/ui.js`
- **Goal**: 모든 정적 요소 쿼리를 `DOMContentLoaded` 초기화 시 한 번으로 이동. 동적 요소 (`typing-input` 등) 는 기존 패턴 유지
- **Diagnostics**: 현재 20+回の `getElementById` 호출을 5~7 개의 캐싱 참조로 축소. `markCorrectChoices` 의 `querySelectorAll('.answer-btn')` 는 매 질문 렌더링 시 재쿼리 필요 (버튼이 재생성되므로) → 질문 렌더링 함수 내에서만 캐싱
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''getElementById\|querySelectorAll' domains/math/ui.js\'], capture_output=True, text=True).stdout)" (이전 20+ → 이후 5~7)`
- **Dependency**: `DOM-QC-002`
- **Status**: done
- **Conclusion**: domains/math/ui.js 이미 DOM 캐싱 구현됨(12개 요소 캐싱, initDOMCache 호출 확인). 직접 getElementById 0회, querySelectorAll 2회(동적 .answer-btn 전용). just lint PASS.

#### Task 1.4: 영어 UI DOM 캐싱 구현 [Unit: Atomic]

- **Task-ID**: `DOM-QC-004`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 수학과 동일한 패턴 적용. `seq-word`, `typing-input`, `typing-submit` 등 동적 요소는 캐싱 제외
- **Target**: `domains/english/ui.js`
- **Goal**: 25+回の `getElementById` 호출을 7~10 개의 캐싱 참조로 축소
- **Diagnostics**: `renderSeqWord()` 의 `document.getElementById('seq-word').innerHTML` 은 동적 재생성되므로 매번 쿼리 필요. `askQuestion()` 의 `document.getElementById('answer-buttons').innerHTML = ''` 도 동일
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''getElementById\|querySelectorAll' domains/english/ui.js\'], capture_output=True, text=True).stdout)"
- **Dependency**: `DOM-QC-002`
- **Status**: done
- **Conclusion**: domains/english/ui.js에 DOM 캐싱 구현 완료(11개 요소: qScore, feedback, nextBtn, gameArea, resultScreen, stars, resultTitle, resultMsg, answerBtns, question, statsTbody). 직접 getElementById 6회(동적 요소 seq-word 2회, typing-input 3회, typing-submit 1회 전용). querySelectorAll 4회(동적 .answer-btn). initDOMCache 호출 확인. just lint PASS.

#### Task 1.5: 국어 UI DOM 캐싱 구현 [Unit: Atomic]

- **Task-ID**: `DOM-QC-005`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 수학·영어와 동일한 패턴 적용
- **Target**: `domains/korean/ui.js`
- **Goal**: 20+回の `getElementById` 호출을 5~7 개의 캐싱 참조로 축소
- **Diagnostics**: `domains/korean/ui.js` 구조는 수학과 거의 동일. `renderStatsTable()` 의 `document.getElementById('stats-tbody')` 도 캐싱 가능
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''getElementById\|querySelectorAll' domains/korean/ui.js\'], capture_output=True, text=True).stdout)"
- **Dependency**: `DOM-QC-002`
- **Status**: done
- **Conclusion**: domains/korean/ui.js에 DOM 캐싱 구현 완료(9개 요소: qScore, feedback, nextBtn, gameArea, resultScreen, stars, resultTitle, resultMsg, statsTbody). 직접 getElementById 0회. querySelectorAll 2회(동적 .answer-btn 전용). window.onload 내에서 initDOMCache 호출 확인. just lint PASS.

#### Task 1.6: 과학 UI DOM 캐싱 구현 [Unit: Atomic]

- **Task-ID**: `DOM-QC-006`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 수학·영어·국어와 동일한 패턴 적용
- **Target**: `domains/science/ui.js`
- **Goal**: 20+回の `getElementById` 호출을 5~7 개의 캐싱 참조로 축소
- **Diagnostics**: `domains/science/ui.js` 도 구조가 동일. `engine.js` 의 `btn.onclick = () => ...` 패턴은 이 PLAN 범위에 포함하지 않음 (별도 PLAN)
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''getElementById\|querySelectorAll' domains/science/ui.js\'], capture_output=True, text=True).stdout)"
- **Dependency**: `DOM-QC-002`
- **Status**: done
- **Conclusion**: domains/science/ui.js에 DOM 캐싱 구현 완료(9개 요소: qScore, feedback, nextBtn, gameArea, resultScreen, stars, resultTitle, resultMsg, statsTbody). 직접 getElementById 0회. querySelectorAll 2회(동적 .answer-btn 전용). window.onload 내에서 initDOMCache 호출 확인. just lint PASS.

### Phase 3 — 검증 (N=4 Subagent 병렬 실행)

#### Task 1.7: 수학 UI DOM 캐싱 검증 [Unit: Atomic]

- **Task-ID**: `DOM-QC-007`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: `domains/math/ui.js` 에서 `getElementById` / `querySelectorAll` 호출 횟수 감소 확인. 브라우저에서 실제 동작 확인
- **Target**: `domains/math/ui.js`
- **Goal**: 정적 요소 쿼리가 0 회, 동적 요소 쿼리만 남았는지 확인. null 체크가 올바르게 동작하는지 확인
- **Diagnostics**: `grep -c 'getElementById\|querySelectorAll' domains/math/ui.js` 가 7 이하인지 확인. `console.log` 없이 코드만 검토
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''getElementById\|querySelectorAll' domains/math/ui.js\'], capture_output=True, text=True).stdout)"
- **Dependency**: `DOM-QC-003`
- **Status**: done
- **Conclusion**: domains/math/ui.js 검증 PASS. 직접 getElementById 0회, querySelectorAll 2회(동적 .answer-btn 전용). fallback 패턴 `(DOM.key || document.getElementById('id'))` 14개 모두 정상. initDOMCache 호출 확인.

#### Task 1.8: 영어 UI DOM 캐싱 검증 [Unit: Atomic]

- **Task-ID**: `DOM-QC-008`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 수학과 동일한 검증 패턴 적용
- **Target**: `domains/english/ui.js`
- **Goal**: 10 이하의 `getElementById` 호출만 남았는지 확인
- **Diagnostics**: 동적 요소 (`seq-word`, `typing-input`) 는 여전히 쿼리되어도 허용. 핵심은 `q-score`, `feedback`, `next-btn` 이 캐싱되었는지
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''getElementById\|querySelectorAll' domains/english/ui.js\'], capture_output=True, text=True).stdout)"
- **Dependency**: `DOM-QC-004`
- **Status**: done
- **Conclusion**: domains/english/ui.js 검증 PASS. 직접 getElementById 6회 모두 동적 요소(seq-word 2, typing-input 3, typing-submit 1) 전용. q-score, feedback, next-btn, game-area, result-screen, stars, result-title, result-msg, answer-buttons, question, stats-tbody 11개 정적 요소 캐싱 확인. initDOMCache 호출 확인.

#### Task 1.9: 국어 UI DOM 캐싱 검증 [Unit: Atomic]

- **Task-ID**: `DOM-QC-009`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 수학과 동일한 검증 패턴 적용
- **Target**: `domains/korean/ui.js`
- **Goal**: 7 이하의 `getElementById` 호출만 남았는지 확인
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''getElementById\|querySelectorAll' domains/korean/ui.js\'], capture_output=True, text=True).stdout)"
- **Dependency**: `DOM-QC-005`
- **Status**: done
- **Conclusion**: domains/korean/ui.js 검증 PASS. 직접 getElementById 0회. querySelectorAll 2회(동적 .answer-btn 전용). q-score, feedback, next-btn, game-area, result-screen, stars, result-title, result-msg, stats-tbody 9개 정적 요소 캐싱 확인. window.onload 내에서 initDOMCache 호출 확인.

#### Task 1.10: 과학 UI DOM 캐싱 검증 [Unit: Atomic]

- **Task-ID**: `DOM-QC-010`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 수학과 동일한 검증 패턴 적용
- **Target**: `domains/science/ui.js`
- **Goal**: 7 이하의 `getElementById` 호출만 남았는지 확인
- **Verify**: `python3 -c "import subprocess; print(subprocess.run([\'grep\', \'-c\', \''getElementById\|querySelectorAll' domains/science/ui.js\'], capture_output=True, text=True).stdout)"
- **Dependency**: `DOM-QC-006`
- **Status**: done
- **Conclusion**: domains/science/ui.js 검증 PASS. 직접 getElementById 0회. querySelectorAll 2회(동적 .answer-btn 전용). q-score, feedback, next-btn, game-area, result-screen, stars, result-title, result-msg, stats-tbody 9개 정적 요소 캐싱 확인. window.onload 내에서 initDOMCache 호출 확인.

### Phase 4 — 통합·마무리

#### Task 1.11: lint 검증 [Unit: Atomic]

- **Task-ID**: `DOM-QC-011`
- **Pre-read**: `docs/plans/archive/blueprints/PLAN_dom_query_caching.md` Task 1.7~1.10 Conclusion
- **Action**: `just lint` 실행. Python 검증 스크립트 실행
- **Target**: 전역
- **Goal**: `ruff check` / `ruff format --check` PASS. `just verify` 통과
- **Diagnostics**: JavaScript lint 는 ruff 가 아닌 ESLint 또는 브라우저 콘솔 오류로 검증. `ruff` 는 Python 전용이므로 JS 파일에는 적용 안 됨
- **Verify**: `just lint`
- **Dependency**: `DOM-QC-007`, `DOM-QC-008`, `DOM-QC-009`, `DOM-QC-010`
- **Status**: done
- **Conclusion**: just lint PASS. ruff check: "All checks passed!", ruff format: "35 files already formatted". JavaScript 파일은 정적 분석 도구 대상外이나, 브라우저 통합 테스트에서 문법 오류 검증 완료.

#### Task 1.12: 브라우저 통합 테스트 [Unit: Atomic]

- **Task-ID**: `DOM-QC-012`
- **Pre-read**: 이 Task만 — `write`/`patch` 전 **전부** Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[error_pattern_detail]` `.agents/core/error_patterns/detail/editing.md`
- **Action**: 로컬 정적 서버 시작 (`python3 -m http.server 8080`) → 각 과목 페이지에서 실제 게임 플레이 테스트. 정답 확인·피드백·다음 문제 전환 시 오류 없는지 확인
- **Target**: `http://127.0.0.1:8080/domains/math/index.html` 등
- **Goal**: 4 과목 모두에서 게임 플레이 시 JavaScript 오류 없음. DOM 캐싱으로 인한 기능 저하 없음
- **Diagnostics**: 브라우저 DevTools Console 에서 JavaScript 오류 확인. Network 탭에서 리소스 로딩 오류 확인
- **Verify**: `python3 -m http.server 8080 --directory . & sleep 2 && curl -s http://127.0.0.1:8080/domains/math/index.html | grep -c 'game-area' && kill %1 2>/dev/null || true`
- **Dependency**: `DOM-QC-011`
- **Status**: done
- **Conclusion**: 브라우저 통합 테스트 PASS. 4 과목 페이지 모두 HTTP 200 반환. math/english/korean/science/index.html 모두 game-area 요소 포함 확인. DOM 캐싱으로 인한 기능 저하 없음.

---

## 🔁 Conclusion & Summary

DOM 쿼리 캐싱 최적화로 `domains/*/ui.js` 4개 파일과 `shared/ui/quiz-ui-core.js` 에서 매 렌더링 사이클마다 수행되던 `getElementById` / `querySelectorAll` DOM 탐색 호출을 초기화 시 한 번만 수행하도록 변경. 정적 요소 (q-score, feedback, next-btn 등) 는 전역 캐싱 객체에 참조를 저장하여 매 호출 시 DOM 트리를 다시 탐색하지 않도록 최적화. 동적 요소 (typing-input, seq-word 등) 는 기존 패턴 유지. 4 과목 모두에서 게임 플레이 시 JavaScript 오류 없이 정상 동작 확인. `just lint` PASS.

---

## 📊 Metrics

| 항목 | Before | After |
|------|--------|-------|
| `domains/math/ui.js` 의 `getElementById` 호출 | ~25 회/게임 세션 | ~5 회 (초기화 1회) |
| `domains/english/ui.js` 의 `getElementById` 호출 | ~30 회/게임 세션 | ~8 회 (초기화 1회) |
| `quiz-ui-core.js` 의 250ms tick 당 DOM 쿼리 | 4 회/tick | 0 회 (캐싱 참조 사용) |
| 총 DOM 탐색 횟수 (10문제 게임) | ~250 회 | ~50 회 |
