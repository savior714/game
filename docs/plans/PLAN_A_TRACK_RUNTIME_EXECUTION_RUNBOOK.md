# A 트랙 런타임 실행 런북

- 상태: `ACTIVE_EXECUTION_RUNBOOK`
- 기준일: 2026-08-07
- 적용 트랙: A 트랙 — 게임 런타임·플레이 경험
- 현재 실행 우선순위: 국어·수학·영어·과학 일반 문제풀이 신뢰성 안정화
- 통합 기준: `origin/main`
- 대상 실행자: Qwen3.6 35B급 이하 로컬 LLM을 포함한 순차 실행 에이전트
- 갱신 조건: A 트랙 우선순위, 트랙 경계, 공통 완료 계약, 로컬 실행/리뷰 방식이 바뀔 때

이 문서는 진행률을 기록하는 체크리스트가 아니다. **최신 `origin/main`에서 무엇을 어떻게 판정하고, 한 번에 어느 범위까지 실행할지**를 정하는 실행 런북이다. 완료 여부의 최종 권위는 항상 최신 코드·테스트·설정이다.

---

## 1. 이 문서를 사용하는 방법

로컬 LLM은 한 세션에서 이 문서 전체를 구현하려고 하지 않는다.

항상 다음 순서로 사용한다.

1. `AGENTS.md`, `PROJECT_RULES.md`, 이 문서의 §1~§5를 읽는다.
2. 현재 작업에 해당하는 **작업 카드 하나만** §8 규칙으로 만든다.
3. 해당 카드에 필요한 코드·테스트·스펙만 추가로 읽는다.
4. 한 작업은 하나의 실패 영역, 하나의 검증 가능한 가설, 하나의 단일 판정 기준으로 끝낸다.
5. 결과를 `origin/main`에 게시하거나, 정확한 이유로 `FAIL`/`BLOCKED`를 보고하고 멈춘다.
6. 다음 카드까지 같은 실행에서 이어서 처리하지 않는다.
7. 사용자가 중간에 프론티어 모델에게 리뷰를 요청하면 §11의 리뷰 패킷만 전달한다.
8. 리뷰 결과가 보완 필요라면 **전체 작업을 다시 설명하지 않고 delta 프롬프트 하나만** 실행한다.

### 로컬 LLM의 기본 컨텍스트 상한

한 작업 시작 시 읽는 범위를 다음 정도로 제한한다.

- 공통 규칙: `AGENTS.md`, `PROJECT_RULES.md`, 이 문서의 필요한 절
- 제품 계약: 현재 기능에 가장 가까운 스펙 1개
- production owner: 우선 1~3개 파일
- 직접 영향 test: 우선 1~3개 파일
- sibling inventory: 같은 계약을 가진 형제 과목/경로의 owner 이름과 핵심 부분만 읽기

문제를 찾는다는 이유로 저장소 전체를 먼저 읽거나 전체 테스트 출력을 컨텍스트에 넣지 않는다.

---

## 2. 권위와 충돌 해결

충돌 시 다음 순서를 따른다.

1. 사용자의 현재 요청
2. `AGENTS.md`
3. `PROJECT_RULES.md`
4. 대상 기능에 가장 가까운 product/technical spec
5. 이 실행 런북
6. 최신 `origin/main`의 실제 코드·테스트·설정
7. 과거 plan/evidence/대화 보고

이 런북의 특정 파일명, 테스트명, 증거 후보가 최신 `main`과 달라졌다면 **실제 최신 코드가 우선**이다. 단, 트랙 경계나 현재 P0 우선순위를 임의로 뒤집어서는 안 된다.

---

## 3. A 트랙 경계

### 3.1 A 트랙이 소유하는 것

A 트랙은 실제 사용자가 게임을 실행하면서 경험하는 동작을 소유한다.

- `domains/math/`, `domains/english/`, `domains/korean/`, `domains/science/`의 문제풀이 런타임
- 문제 진행, 점수, 정답/오답, 피드백, 결과 화면, 재시작
- 키보드·터치 입력과 실제 상호작용
- disabled/focus/feedback 상태
- 중복 입력 방지와 한 번의 입력이 한 번만 효과를 내는 계약
- 보상 런타임과 보호자 승인 이후의 사용자 흐름
- Ocean Rescue의 **런타임 소비 측** 플레이 동작: 상태기계, 입력, 상호작용, HUD, pause/resume, runtime rendering

### 3.2 B 트랙이 소유하므로 A 트랙에서 수정하지 않는 것

다음은 기본적으로 B 트랙이다.

- SVG/PNG 등 원천 에셋 제작·수정
- art packet / approval / atlas 생성
- exporter, validator, deterministic generator
- asset metadata/schema의 생산 측 계약
- render asset registry 생성 파이프라인
- Ocean Rescue의 생성 산출물과 에셋 검증 스크립트

특히 다음 경로는 A 트랙 일반 작업에서 건드리지 않는다.

- `scripts/ocean_rescue/`의 에셋·생성 파이프라인
- `domains/ocean-rescue/assets/source/`
- `domains/ocean-rescue/assets/generated/`
- proof/contact-sheet 계열 산출물

B가 생산하고 A가 소비하는 계약을 바꿔야 한다면:

1. A 작업을 멈춘다.
2. 필요한 계약 변경을 `DISCOVERED_FAILURE`로 적는다.
3. B 트랙이 생산 측 계약을 먼저 확정·검증·게시한다.
4. 이후 최신 `origin/main`에서 A 트랙이 소비 측 변경을 별도 작업으로 수행한다.

### 3.3 현재 잠금

일반 문제풀이 안정화 exit 전에는 다음을 자동으로 시작하지 않는다.

- Ocean Rescue 신규 플레이 기능
- Ocean Rescue 구조 이전
- Space Explorer 신규 기능
- 순수 시각 리디자인
- 새 콘텐츠 대량 추가
- dependency/toolchain 업그레이드

치명적 운영 회귀, 데이터 손상, 보안 문제는 예외가 될 수 있지만 반드시 별도 실패 영역으로 다룬다.

---

## 4. 모든 A 트랙 작업의 불변 실행 프로토콜

### 4.1 시작: 최신 main과 격리 worktree

canonical checkout은 확인·통합 기준으로 두고, 수정은 안정적인 별도 worktree에서 한다.

예시:

```bash
git fetch origin
BASE="$(git rev-parse origin/main)"
TASK_ID="A-QUIZ-EXAMPLE"
WT="/Users/seungjulee/Desktop/Dev/.worktrees/game/a-quiz-example"

git worktree add --detach "$WT" origin/main
git worktree lock --reason "$TASK_ID active task" "$WT"
cd "$WT"
git status --short
```

판정:

- 시작 worktree는 clean이어야 한다.
- `/tmp`, `/private/tmp`, `${TMPDIR}`, `mktemp` 아래 source checkout을 사용하지 않는다.
- VS Code/OpenCode/LSP/브라우저/테스트는 모두 같은 worktree root를 사용한다.
- feature branch나 PR을 만들지 않는다.

### 4.2 수정 전에 반드시 한 문장씩 고정

코드를 바꾸기 전에 아래 세 줄을 실제 작업 메모에 적는다.

```text
FAILURE_DOMAIN: <하나의 실패 영역>
HYPOTHESIS: <왜 이 동작이 실패한다고 보는지 한 문장>
BINARY_CRITERION: <수정 후 PASS/FAIL을 가를 하나의 관찰 가능한 기준>
```

좋은 예:

```text
FAILURE_DOMAIN: SCIENCE_WRONG_ANSWER_FEEDBACK_LEAKS_INTO_NEXT_QUESTION
HYPOTHESIS: 다음 문제 렌더가 이전 feedback class를 제거하지 않는다.
BINARY_CRITERION: 오답 후 next 1회 클릭 시 새 문제에서 correct/wrong/feedback-wrong 상태가 0개다.
```

나쁜 예:

```text
과학 퀴즈를 전반적으로 개선한다.
```

### 4.3 sibling-surface inventory는 읽기 전용

같은 사용자 계약을 가진 형제 과목이나 형제 경로가 있으면 수정 전에 짧게 비교한다.

예: Science next-question 문제를 고칠 때 Math/English/Korean의 같은 handler 이름 또는 같은 DOM contract를 확인한다.

목적은 다음뿐이다.

- 같은 누락이 공통 owner에 있는지 확인
- 현재 대상만의 결함인지 확인
- 이미 검증된 구현 패턴이 있는지 확인

**inventory가 write scope를 넓히지는 않는다.**

공통 owner 한 곳의 동일 root cause로 형제 표면이 함께 해결되는 경우만 같은 작업에 포함한다. 과목별 독립 구현이면 현재 과목만 수정하고 나머지는 `DISCOVERED_FAILURE`로 분리한다.

### 4.4 기존 증거를 먼저 찾는다

새 테스트를 쓰기 전에 다음 순서로 확인한다.

1. 정확히 같은 사용자 계약을 검증하는 기존 focused test가 있는가?
2. 있다면 최신 `origin/main`에서 그 test가 green인가?
3. green이면 현재 카드는 `ALREADY_PROVEN`으로 종료하고 production/test를 수정하지 않는다.
4. test는 있지만 실제 계약의 핵심 관찰을 하지 않으면 그 **한 증거 공백**만 현재 작업 후보가 된다.
5. 정확한 증거가 없을 때만 최소 RED를 추가한다.

테스트 개수 증가 자체는 목표가 아니다.

### 4.5 RED는 가장 작은 재현만 만든다

RED는 다음을 만족해야 한다.

- 실제 사용자 입력 또는 production owner를 통과한다.
- 한 failure mode만 잡는다.
- 구현 세부사항보다 사용자/호출자 계약을 검증한다.
- 수정 전 의도한 이유로 실패한다.
- unrelated full suite 실패를 RED 근거로 사용하지 않는다.

브라우저 상호작용에서는 가능하면 다음도 기록한다.

- `pageerror`
- `console.error`
- `requestfailed`

JS를 브라우저에서 비동기 계측할 때는 `AGENTS.md`의 bounded-evaluation 규칙을 따른다. 무한 대기 가능한 `page.evaluate()`를 만들지 않는다.

### 4.6 production 수정

수정은 root cause의 가장 가까운 owner에서 최소화한다.

허용:

- 같은 failure domain을 완결하는 production + focused test
- 같은 owner의 필요한 caller/adapter 조정

금지:

- 주변 코드 정리
- 이름 일괄 변경
- 무관한 lint 정리
- 여러 과목의 독립 결함 동시 수정
- `shared/` 추출을 위한 선제적 리팩터링
- dependency upgrade
- snapshot/baseline 갱신으로 실패 숨기기
- broad ignore / `noqa` / 검사 대상 축소

### 4.7 focused GREEN

먼저 RED를 만든 정확한 test만 다시 실행한다.

예:

```bash
uv run pytest -q tests/test_science_wrong_answer_state_reset.py
```

단일 판정 기준이 green이 되지 않으면 다른 실패를 고치러 가지 않는다.

### 4.8 직접 영향 회귀

focused GREEN 다음에만 직접 영향 회귀를 실행한다.

예:

- next-question 수정 → 같은 과목 restart + wrong-answer reset
- restart 수정 → 같은 과목 full-session + state reset
- 공통 focus 수정 → 네 과목 focus 계약

직접 영향 범위를 넘는 full suite를 기본으로 실행하지 않는다.

### 4.9 정적 진단 closure

현재 수정 파일과 직접 영향 범위에 대해 저장소가 요구하는 정적 진단을 닫는다.

대표 명령:

```bash
just lint
just typecheck
git diff --check
```

모든 작업에서 무조건 `just lint`/`just typecheck` 전체를 돌리라는 뜻은 아니다. 현재 파일이 해당 검사 대상에 포함되고 직접 영향 판단에 필요한 최소 게이트를 선택한다.

판정:

- 이번 변경이 만든 정적 오류는 현재 작업에서 반드시 제거한다.
- 기존이더라도 수정 파일/직접 영향 범위의 정적 오류가 현재 작업의 안전한 검증을 막으면 PASS하지 않는다.
- 별개의 원인이라면 현재 production 수정을 섞지 말고 `BLOCKED` 후 별도 실패 영역으로 분리한다.

### 4.10 게시

작업 worktree에서 commit을 만든 뒤 최신 `origin/main`과 다시 맞춘다.

```bash
git diff --check
git status --short
git add <current-task-files-only>
git commit -m "<focused commit message>"

git fetch origin
```

`origin/main`이 시작 SHA 이후 이동했으면:

```bash
git rebase origin/main
```

그 뒤 **현재 작업의 focused test와 필요한 직접 영향/정적 검증만 다시 실행**한다.

게시:

```bash
git push origin HEAD:main
git fetch origin
```

최종 확인:

```bash
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
```

push가 non-fast-forward로 실패하면 force push하지 않는다. 최신 `origin/main`으로 다시 맞추고 현재 작업만 재검증한다.

### 4.11 종료와 worktree 회수

게시 완료 후 worktree가 clean이고 더 이상 활성 작업이 아니면 회수한다.

canonical checkout 등 worktree 밖에서:

```bash
git worktree unlock "$WT"
git worktree remove "$WT"
git worktree prune
```

다음 경우에는 자동 삭제하지 않는다.

- dirty worktree
- 미게시 commit/변경 존재
- 현재 리뷰 중인 활성 작업

---

## 5. 한 작업에서 즉시 멈춰야 하는 조건

다음 중 하나면 다음 실패 영역으로 넘어가지 않는다.

### 5.1 `ALREADY_PROVEN`

최신 main의 기존 focused test가 현재 계약을 정확히 검증하고 green이다.

- source 변경 없음
- test 추가 없음
- `RESULT: PASS`
- `PUBLISH: NOT_APPLICABLE`

### 5.2 `HYPOTHESIS_INVALID`

RED가 예상한 이유로 실패하지 않거나 production이 이미 가설과 반대로 동작한다.

- 억지로 test를 실패시키지 않는다.
- production 변경 없음
- 관찰 사실을 보고하고 멈춘다.
- 다음 가설은 별도 카드에서 세운다.

### 5.3 새로운 별도 실패 발견

현재 기준은 green/독립 판정 가능하지만 주변에서 다른 실패를 발견했다면:

- 현재 작업은 정상 종료 가능
- 새 실패를 `DISCOVERED_FAILURE`에만 기록
- 같은 patch에 섞지 않음

### 5.4 검증 기반 자체가 깨짐

예:

- Playwright 브라우저 설치 누락
- 현재 worktree가 아닌 경로를 LSP가 보고 있음
- 필수 fixture가 시작 전부터 무관한 이유로 실패

환경을 현재 카드 안에서 안전하게 복원할 수 있으면 환경만 고치고 같은 판정을 다시 실행한다. 그렇지 않으면 `BLOCKED`로 멈춘다. production 코드를 억지로 바꾸지 않는다.

### 5.5 게시 충돌

최신 main과 현재 변경의 동일 owner가 충돌하면 자동으로 의미를 합치지 않는다.

- 최신 owner를 다시 읽는다.
- 현재 failure domain이 여전히 남는지 재확인한다.
- 이미 해결됐다면 `ALREADY_PROVEN` 취급
- 의미 충돌이면 `BLOCKED` 또는 새 카드

---

## 6. 현재 P0: 4과목 문제풀이 안정화 완료 계약

대상:

- `domains/math/`
- `domains/english/`
- `domains/korean/`
- `domains/science/`

과목 하나가 완료되려면 최소한 다음 계약이 실제 브라우저 흐름에서 증명되어야 한다.

| 계약 ID | 계약 |
|---|---|
| `ENTRY` | 페이지 진입 후 첫 문제가 보이고 비어 있지 않으며 런타임 오류가 없다. |
| `CONTENT` | 현재 문제의 prompt/choice/correct-answer 관계가 유효하다. |
| `CORRECT` | 정답 1회 입력이 정확히 1회 채점되고 점수/피드백이 맞다. |
| `WRONG` | 오답 1회 입력이 점수를 올리지 않고 오답/정답 안내가 맞다. |
| `NEXT_RESET` | next 1회가 정확히 다음 문제 하나로 이동하고 이전 상태가 새 문제로 누수되지 않는다. |
| `INPUT_GUARD` | 이미 답한 문제의 중복 입력·오조작이 중복 점수/진행/handler 효과를 만들지 않는다. |
| `TERMINAL` | 마지막 문제 처리 후 결과 화면으로 정확히 한 번 전환되고 최종 점수/문구가 맞다. |
| `RESTART` | 재시작 1회가 새 세션을 정확히 한 번 시작하고 진행/점수/피드백/타이머/입력 상태를 초기화한다. |
| `FOCUS` | 키보드 사용 시 현재 조작 대상과 visible focus가 일관되고 modal/화면 전환 뒤 focus가 갇히거나 사라지지 않는다. |
| `RUNTIME_ERRORS` | 대표 full-session 동안 pageerror/console.error/requestfailed가 없다. |

English에 별도 typing/sequential-blank 모드가 존재하면 해당 모드는 `CORRECT`, `WRONG`, `NEXT_RESET`, `INPUT_GUARD`, `TERMINAL`, `RESTART`를 별도 표면으로 취급한다. 단, 동일 owner와 동일 root cause가 명확할 때만 한 작업에 묶는다.

---

## 7. 최신 main에서 먼저 확인할 기존 증거 후보

아래는 **완료 상태표가 아니라 탐색 시작점**이다. 파일이 존재한다는 이유만으로 계약이 증명됐다고 간주하지 않는다. 현재 테스트 본문과 최신 실행 결과를 확인한다.

### 공통/비수학 브라우저

- `tests/test_nonmath_browser_acceptance.py`
  - Korean/English/Science: load, first question, answer button, feedback, next button
  - Math: 일부 control smoke
- `tests/test_nonmath_next_question_progression.py`
  - Korean/English/Science: correct answer 후 next가 정확히 +1 진행
- `tests/test_quiz_focus_visible.py`
- `tests/test_quiz_stats_modal_dialog_semantics.py`
- `tests/test_quiz_stats_modal_escape.py`
- `tests/test_quiz_stats_modal_focus.py`
- `tests/test_quiz_stats_modal_focus_containment.py`
- `tests/test_quiz_stats_modal_inertness.py`
- `tests/test_quiz_stats_modal_initial_focus.py`
- `tests/test_quiz_stats_modal_open_control.py`

### Math

먼저 다음을 확인한다.

- `tests/test_math_next_question_progression.py`
- `tests/test_math_wrong_answer_reinforcement_boundary.py`
- `tests/test_math_reinforcement_fallback_guarantee.mjs`
- `tests/test_math_restart_progression.py`

최근 main에는 full-session clean restart와 mixed/correct progression을 강화한 이력이 있으므로, 같은 계약을 새 테스트로 다시 만들지 않는다.

### English

먼저 다음을 확인한다.

- `tests/test_english_engine_bootstrap.py`
- `tests/test_english_restart_progression.py`
- `tests/test_english_typing_restart_progression.py`
- `tests/test_english_typing_state_reset.py`
- `tests/test_english_wrong_answer_state_reset.py`

일반 선택형과 typing/sequential-blank 계약을 혼동하지 않는다.

### Korean

먼저 다음을 확인한다.

- `tests/test_korean_batchim_content.py`
- `tests/test_korean_restart_progression.py`
- `tests/test_korean_wrong_answer_state_reset.py`

최근 main에는 10문제 mixed session → result → clean restart 증거가 있으므로 같은 journey를 단순 반복하지 않는다.

### Science

먼저 다음을 확인한다.

- `tests/test_science_restart_progression.py`
- `tests/test_science_wrong_answer_state_reset.py`

현재 restart test에는 mixed 10-question journey, terminal result, clean restart, runtime error 수집이 포함될 수 있으므로 먼저 본문을 읽고 겹치는 새 테스트를 만들지 않는다.

---

## 8. P0 실행 순서

고정 과목 순서로 무작정 구현하지 않는다. 먼저 동일한 방식으로 네 과목의 현재 실패/증거 공백을 재구성한다.

### 단계 A-Q0 — 과목별 읽기 전용 계약 감사

한 번의 로컬 실행은 과목 하나만 감사한다.

작업 ID:

- `A-Q0-MATH-AUDIT`
- `A-Q0-ENGLISH-AUDIT`
- `A-Q0-KOREAN-AUDIT`
- `A-Q0-SCIENCE-AUDIT`

각 audit의 해야 할 일:

1. 해당 과목 `index.html`과 직접 로드되는 runtime JS owner를 식별한다.
2. §6의 계약별로 정확한 기존 test를 매핑한다.
3. 매핑한 test를 필요한 최소 명령으로 실행한다.
4. 각 계약을 다음 셋 중 하나로 분류한다.
   - `PROVEN`: 정확한 관찰 + green
   - `GAP`: 테스트가 없거나 핵심 관찰이 빠짐
   - `RED`: 정확한 기존 test가 현재 실패
5. production/test를 수정하지 않는다.
6. 첫 번째 `RED`가 있더라도 이 audit 안에서 수정하지 않는다.

audit 출력 예:

```text
SUBJECT: SCIENCE
ENTRY: PROVEN — tests/...
CONTENT: GAP — 정확한 answer-key consistency 증거 없음
CORRECT: PROVEN — tests/...
WRONG: PROVEN — tests/...
NEXT_RESET: PROVEN — tests/...
INPUT_GUARD: GAP — answered=true 이후 두 번째 실제 입력 효과 미검증
TERMINAL: PROVEN — tests/...
RESTART: PROVEN — tests/...
FOCUS: PROVEN — tests/...
RUNTIME_ERRORS: PROVEN — tests/...
FIRST_RED: NONE
```

#### audit 판정 기준

한 audit의 binary criterion은 다음 하나다.

> 해당 과목의 §6 모든 계약이 `PROVEN/GAP/RED` 중 정확히 하나로 근거와 함께 분류되었는가?

### 단계 A-Q1 — 첫 실제 failure domain 선택

네 audit 결과를 모은 뒤 다음 순서로 하나만 선택한다.

1. 현재 재현되는 `RED`가 있는 과목/계약
2. `RED`가 여러 개면 사용자 흐름을 더 앞에서 막는 계약
   - `ENTRY` → `CONTENT` → `CORRECT/WRONG` → `NEXT_RESET/INPUT_GUARD` → `TERMINAL` → `RESTART/FOCUS`
3. `RED`가 없으면 `GAP`이 가장 많은 과목
4. 같은 과목의 여러 `GAP` 중에서는 위 사용자 흐름 순서의 첫 계약
5. 완전 동률이면 `Math → English → Korean → Science` 순으로만 결정한다.

선택 자체는 source 변경이 아니다.

### 단계 A-Q2 — 계약 하나를 증명 또는 수정

작업 ID 형식:

```text
A-Q2-<SUBJECT>-<CONTRACT>
```

예:

```text
A-Q2-SCIENCE-INPUT_GUARD
A-Q2-ENGLISH-TYPING-TERMINAL
```

실행:

1. 최신 `origin/main`에서 새 worktree를 만든다.
2. 선택된 계약의 기존 증거를 다시 확인한다.
3. 이미 증명됐으면 `ALREADY_PROVEN`으로 끝낸다.
4. `RED`이면 그 정확한 실패를 재현한다.
5. `GAP`이면 계약을 증명하는 최소 테스트를 만들고, production 결함이 실제 있으면 RED를 확보한다.
6. production이 이미 올바르면 테스트만 추가할 수 있다. 단, 테스트는 실제로 계약의 핵심 관찰을 검증해야 한다.
7. production 결함이면 가장 가까운 owner만 수정한다.
8. focused GREEN → 직접 영향 회귀 → 정적 closure 순으로 검증한다.
9. 현재 작업만 commit/publish한다.
10. 종료한다. 다음 `GAP/RED`까지 처리하지 않는다.

### 단계 A-Q3 — 같은 과목의 다음 계약

A-Q2가 게시된 뒤에는 **최신 main에서 해당 과목 audit를 다시 계산**한다.

- 다음 `RED/GAP`이 있으면 새 A-Q2 카드 하나
- 모두 `PROVEN`이면 해당 과목을 완료 후보로 두고 다른 과목 audit로 이동

과거 audit 결과를 그대로 신뢰하지 않는다.

### 단계 A-Q4 — 과목 완료 직접 영향 묶음

한 과목의 모든 계약이 `PROVEN`이 된 시점에만 그 과목의 직접 영향 회귀 묶음을 실행한다.

목적:

- 개별 focused test는 모두 green이지만 서로 조합했을 때 상태가 충돌하는지 확인
- 한 session의 시작부터 result/restart까지 대표 journey가 실제 브라우저에서 성립하는지 확인

이 단계에서 새 실패가 생기면 전체를 한꺼번에 고치지 않는다. 첫 실패를 새 failure domain으로 분리하고 다시 A-Q2로 돌아간다.

### 단계 A-Q5 — P0 exit gate

네 과목이 모두 완료 후보가 된 뒤에만 P0 종료 검증을 한다.

최소 조건:

1. 네 과목의 §6 계약이 최신 main의 실제 증거로 모두 `PROVEN`
2. 대표 full-session에서 결과 화면까지 도달
3. restart가 clean state를 만든다.
4. 대표 journey 중 browser `pageerror`, `console.error`, `requestfailed`가 없다.
5. 현재 변경 범위의 정적 진단이 닫혀 있다.
6. `tests/test_core_quiz_reliability_policy.py`가 정책 drift 없이 통과한다.

필요할 때만 이 시점에서 넓은 회귀를 사용한다.

예:

```bash
uv run pytest -q \
  tests/test_nonmath_browser_acceptance.py \
  tests/test_nonmath_next_question_progression.py \
  tests/test_math_next_question_progression.py \
  tests/test_math_restart_progression.py \
  tests/test_english_restart_progression.py \
  tests/test_english_typing_restart_progression.py \
  tests/test_korean_restart_progression.py \
  tests/test_science_restart_progression.py \
  tests/test_core_quiz_reliability_policy.py
```

이 명령은 예시다. 최신 main에서 중복 journey가 정리되거나 파일명이 바뀌면 실제 직접 증거 집합으로 조정한다.

P0 exit가 확인되면 **자동으로 다음 기능을 구현하지 않는다.** §9 후보를 최신 main과 대조하고 사용자/프론티어 모델이 다음 A 트랙 묶음을 선택한다.

---

## 9. P0 이후 A 트랙 후보 — 자동 실행 금지

이 절은 우선순위 후보를 잃지 않기 위한 지도다. P0 exit 또는 사용자의 명시적 재개 전에는 실행하지 않는다.

### 9.1 Reward / YouTube 자유시간 세션

제품 계약:

- `docs/specs/product/AIDENGAME_YOUTUBE_FREE_TIME_SESSION.md`

현재 저장소에는 외부 탭 launcher와 session-start 관련 구현 이력이 이미 있을 수 있다. 따라서 `NOT_IMPLEMENTED`라는 과거 문구만 보고 처음부터 다시 만들지 않는다.

재개 시 첫 카드는 반드시 읽기 전용 inventory다.

```text
A-RWD-YT-00-CURRENT-STATE-INVENTORY
```

inventory에서 스펙 각 계약을 최신 production/test에 매핑하고 `PROVEN/GAP/RED`로 분류한다.

그 뒤에만 다음과 같은 독립 failure domain 후보를 하나씩 선택한다.

- 허용 YouTube URL 검증
- 한 번의 실제 클릭 = 한 번의 새 탭 생성
- 새 탭 생성 실패 시 시간 미차감
- session 시작과 15분 차감의 원자성
- 활성 session 중 중복 시작 방지
- `deadline - Date.now()` 기반 시간 권위
- reload/sleep 이후 session 복원
- fixed timer fallback
- Document Picture-in-Picture 지원/실패 fallback
- 1분/10초 경고 exactly-once
- expiry 경고와 acknowledge 상태
- 브라우저 종료/재진입 시 expired 복원

각 항목은 서로 다른 원인이면 반드시 별도 카드다.

### 9.2 Ocean Rescue 런타임

현재 일반 과목 P0가 끝나고 사용자가 Ocean Rescue A 트랙을 재개한 뒤에만 시작한다.

재개 첫 작업:

```text
A-OR-00-RUNTIME-INVENTORY
```

읽기 범위:

- 가장 가까운 Ocean Rescue product/technical spec
- `domains/ocean-rescue/src/` runtime owner
- 실제 runtime tests
- 최신 `origin/main`의 A/B boundary

다음 영역을 inventory하되 **고정 WP 번호를 현재 일정으로 사용하지 않는다.**

- mission/state-machine runtime
- travel/movement/input
- turtle/crab/whale interaction
- pause/resume lifecycle
- renderer adapter와 runtime asset consumption
- HUD/feedback
- touch/tablet interaction
- runtime performance/long task
- fallback rendering

inventory가 `RED/GAP`을 확인한 뒤 한 failure domain만 카드로 만든다.

에셋 packet/atlas/validator/generator 문제면 B 트랙으로 넘긴다.

### 9.3 Space Explorer

`experiments/space-explorer/`는 현재 개발 동결이다. 사용자가 명시적으로 재개하기 전에는 A 트랙 런북에서 실행하지 않는다.

---

## 10. 로컬 LLM용 작업 카드 템플릿

새 로컬 작업을 시작할 때 프론티어 모델이 별도 프롬프트를 주지 않아도 아래 템플릿으로 카드 하나를 만들 수 있다.

```text
TASK_ID: <A-...>
MODE: MODIFY_AND_VERIFY | ANALYZE_ONLY_FIRST

GOAL
- <이번 한 작업에서 닫을 사용자/런타임 계약 하나>

FAILURE_DOMAIN
- <하나>

HYPOTHESIS
- <한 문장>

BINARY_CRITERION
- <PASS/FAIL 하나로 판정 가능한 관찰>

READ_SCOPE
- AGENTS.md
- PROJECT_RULES.md
- docs/plans/PLAN_A_TRACK_RUNTIME_EXECUTION_RUNBOOK.md의 필요한 절
- <가장 가까운 spec 1개>
- <production owner 후보 1~3개>
- <focused test 후보 1~3개>

WRITE_SCOPE
- <허용 production 파일>
- <허용 test 파일>

DO
1. git fetch 후 최신 origin/main 기준 locked detached worktree를 만든다.
2. exact existing evidence를 먼저 확인한다.
3. 수정 전 RED 또는 증거 공백을 단일 기준으로 확정한다.
4. 가장 가까운 owner만 최소 수정한다.
5. focused GREEN을 실행한다.
6. 직접 영향 회귀만 실행한다.
7. 필요한 정적 진단과 git diff --check를 닫는다.
8. 최신 origin/main 이동 시 rebase 후 같은 focused 검증을 재실행한다.
9. origin/main에 fast-forward push한다.
10. clean published worktree를 회수한다.

DO_NOT
- 다음 failure domain을 같이 수정하지 않는다.
- Ocean Rescue B 트랙 에셋/생성 파일을 건드리지 않는다.
- shared 추출을 선제적으로 하지 않는다.
- dependency/toolchain을 업그레이드하지 않는다.
- full suite를 RED나 초기 GREEN 대신 사용하지 않는다.
- broad ignore/noqa/snapshot 갱신으로 녹색을 만들지 않는다.
- feature branch/PR/force push를 만들지 않는다.

STOP
- 정확한 기존 증거가 이미 green이면 ALREADY_PROVEN으로 종료한다.
- 가설이 틀리면 production 변경 없이 종료한다.
- 별도 실패를 발견하면 DISCOVERED_FAILURE에만 기록한다.
- 검증 기반이 깨져 현재 판정이 불가능하면 BLOCKED로 종료한다.

OUTPUT
RESULT: PASS | FAIL | BLOCKED
FAILURE_DOMAIN: <single value>
HYPOTHESIS: CONFIRMED | REJECTED | NOT_TESTED
PRIMARY_VERIFY: PASS | FAIL | NOT_RUN
DIRECT_VERIFY: PASS | FAIL | NOT_RUN
STATIC_VERIFY: PASS | FAIL | NOT_RUN
PUBLISH: PUBLISHED | NOT_PUBLISHED | NOT_APPLICABLE
COMMIT: <sha | NONE>
CHANGE: <짧은 변경 요약 | NONE>
DISCOVERED_FAILURE: <NONE | 범위 밖 새 실패 1줄>
BLOCKER: <NONE | RESULT=BLOCKED인 정확한 이유>
```

`RESULT`와 각 검증 상태는 반드시 서로 배타적인 단일 값만 사용한다.

---

## 11. 프론티어 모델 리뷰 패킷과 delta 보완 규칙

사용자가 중간에 ChatGPT에게 리뷰를 맡길 때 로컬 LLM은 전체 세션 로그를 붙이지 않는다.

다음 패킷만 준비한다.

```text
REVIEW_TASK: <TASK_ID>
BASE: <작업 시작 origin/main sha>
HEAD: <현재 commit sha 또는 working tree>
RESULT: <PASS|FAIL|BLOCKED>
FAILURE_DOMAIN: <...>
HYPOTHESIS: <...>
BINARY_CRITERION: <...>
CHANGED_FILES:
- ...
PRIMARY_VERIFY:
- command: ...
- result: ...
DIRECT_VERIFY:
- command: ...
- result: ...
STATIC_VERIFY:
- command: ...
- result: ...
DISCOVERED_FAILURE: ...
```

필요하면 추가로 다음만 첨부한다.

```bash
git status --short
git diff --stat "$BASE"..HEAD
git diff "$BASE"..HEAD -- <changed-files>
```

### 프론티어 리뷰가 반환해야 하는 결과

#### `REVIEW_PASS`

- 현재 failure domain이 충분히 닫힘
- 추가 로컬 프롬프트 없음
- 다음 작업은 최신 main에서 새로 선택

#### `DELTA_REQUIRED`

프론티어 모델은 **기존 작업 설명을 반복하지 않고 발견한 구멍 하나만** 보완 프롬프트로 준다.

Delta 형식:

```text
DELTA_ID: <TASK_ID>-D1
PARENT_TASK: <TASK_ID>
GAP: <리뷰에서 확인한 정확한 구멍 하나>

DO
- <추가/수정할 한 가지>

WRITE_SCOPE
- <필요 파일만>

VERIFY
- <이 구멍만 판정하는 명령/관찰>

DO_NOT
- 이미 통과한 부분을 재구현하지 않는다.
- 다른 failure domain을 추가하지 않는다.
- 전체 런북을 다시 수행하지 않는다.

OUTPUT
- §10 상태 필드 형식을 유지하고 DELTA_ID를 추가한다.
```

#### `HYPOTHESIS_INVALID`

리뷰 결과 원래 가설이 성립하지 않으면 현재 patch를 더 키우지 않는다. 사실을 보존하고 새 카드에서 원인을 다시 고른다.

#### `REVIEW_BLOCKED`

필수 증거가 없거나 현재 diff만으로 안전 판정이 불가능할 때만 사용한다. 다음 입력으로 무엇이 필요한지 하나만 명시한다.

---

## 12. 테스트 설계 세부 규칙

### 12.1 상태를 DOM만으로 추정하지 않는다

가능하면 사용자-visible 결과와 내부 상태를 함께 본다.

예:

- `#q-count`와 `currentQ`
- `#q-score`와 `score`
- button class와 `answered`
- result screen visibility와 terminal state

둘이 어긋나면 실제 failure domain이 된다.

### 12.2 exactly-once를 우선 검증할 동작

다음은 중복 handler가 사용자 결과를 망가뜨리기 쉬우므로 실제 입력 1회에 효과가 정확히 1회인지 확인한다.

- 정답/오답 선택
- next
- restart
- modal open/close
- reward consume/start
- 외부 탭 launch

단순 dataset marker 존재만으로 exactly-once를 증명하지 않는다. 가능하면 최종 상태 변화나 제한된 계측으로 직접 확인한다.

### 12.3 타이머

재시작/세션 복원에서 타이머를 검증할 때는 다음을 구분한다.

- 활성 timer가 존재하는가
- 중복 timer가 존재하지 않는가
- 시간 권위가 wall clock인지 단순 tick 누적인가

과목 퀴즈의 기존 timer 구현을 YouTube 자유시간 세션의 시간 권위 계약과 임의로 통합하지 않는다.

### 12.4 randomized content

무작위 문제 때문에 test가 flaky해지면 production randomization을 제거하지 않는다.

우선순위:

1. 현재 runtime이 노출하는 정답/상태를 읽어 정확한 사용자 입력을 선택
2. seed/test seam이 이미 있으면 사용
3. 새 seam이 정말 필요하면 production 의미를 바꾸지 않는 최소 seam만 별도 판단

문제 텍스트 자체를 고정값으로 과도하게 snapshot하지 않는다.

### 12.5 browser error 수집

대표 journey에서는 가능한 경우 다음 세 가지를 각각 0건으로 판정한다.

```text
pageerror == 0
console.error == 0
requestfailed == 0
```

외부 네트워크를 의도적으로 사용하지 않는 정적 과목 페이지에서 request failure가 있으면 무시하지 않는다.

---

## 13. 의존성·도구 경계

A 트랙 런타임 안정화 작업에서는 도구 버전 업데이트를 함께 하지 않는다.

- Python 검증은 repository의 `uv.lock`/현재 환경을 따른다.
- `uv lock --upgrade`, 광범위한 `uv sync --upgrade`를 A 트랙 bugfix에 섞지 않는다.
- Ruff/Pytest/Playwright 업데이트는 별도 maintenance failure domain이다.
- Ocean Rescue Node/pnpm toolchain은 일반 4과목 런타임 검증에 끌어오지 않는다.

도구 업데이트 때문에 새 진단이나 포맷 변화가 생겼다면 현재 런타임 결함과 분리한다.

---

## 14. 이 런북 자체의 완료 기준

이 문서가 제 역할을 하는지는 다음으로 판단한다.

1. 새 로컬 LLM 세션이 과거 대화 없이도 현재 A 트랙 경계를 알 수 있다.
2. 한 세션이 다음 세션의 failure domain을 임의로 같이 처리하지 않는다.
3. 기존 증거가 있으면 중복 테스트를 만들지 않는다.
4. 네 과목 P0의 완료 계약과 종료 gate가 명시돼 있다.
5. P0 이후 후보는 보존되지만 자동 실행되지 않는다.
6. 중간 리뷰 후 전체 프롬프트 재서술 없이 delta 하나만 넘길 수 있다.
7. Git 작업이 PR/feature branch 없이 `origin/main` fast-forward 흐름으로 끝난다.
8. A/B 경계면에서 asset 생산 측을 A 트랙이 임의로 수정하지 않는다.

이 기준이 바뀌지 않는 한 개별 작업의 진행 상황만으로 이 문서를 계속 수정하지 않는다.
