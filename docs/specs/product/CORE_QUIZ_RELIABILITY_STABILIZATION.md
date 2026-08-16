# Core Quiz Reliability Stabilization — Completed Reference

- **Status:** `COMPLETED_REFERENCE`
- **Completed:** 2026-08-06
- **Scope:** Math, English, Korean, Science core quiz journey
- **Current product authority:** `docs/specs/product/ACTIVE_PRODUCT_SCOPE.md`
- **Proof authority:** latest `origin/main` code, focused tests, and real-browser evidence

이 문서는 4과목 core quiz reliability stabilization 단계에서 확정한 **완료·회귀 계약**을 보존한다. 더 이상 현재 개발 우선순위나 다음 작업을 소유하지 않는다.

동일 결함이 최신 main에서 재현될 때는 이 계약으로 회귀를 판정한다. 과거 단계별 진단 순서, 다음 과목, freeze 정책은 현재 작업 선택에 사용하지 않는다.

## 1. Completed journey contract

각 과목의 핵심 흐름은 다음을 안정적으로 완료해야 한다.

```text
진입
→ 첫 문제 표시
→ 답안 선택
→ 정답/오답 처리
→ 피드백
→ 다음 문제
→ 반복
→ 마지막 문제
→ 종료/재시작
```

운영 entry:

| Subject | Runtime entry |
|---|---|
| Math | `domains/math/index.html` |
| English | `domains/english/index.html` |
| Korean | `domains/korean/index.html` |
| Science | `domains/science/index.html` |

## 2. Regression invariants

### 2.1 Question progression identity

- 다음 문제 이동 후 실제 문제 identity 또는 의미 있는 콘텐츠가 바뀌어야 한다.
- 단순 DOM rerender, 카운터 변화, animation만으로 진행을 판정하지 않는다.

### 2.2 Per-question state reset

다음 문제에 이전 문제의 transient state가 누출되지 않아야 한다.

- selected answer
- correct/wrong style
- feedback text/class
- submit/next disabled state
- duplicate-submit latch
- 문제별 임시 시도/help state
- pointer/focus/keyboard transient state

세션 전체 score, streak, progress처럼 의도적으로 지속되는 상태는 별도로 구분한다.

### 2.3 Correct and incorrect paths

- 정답과 오답 경로 모두 정의된 feedback 뒤 다음 문제로 진행 가능해야 한다.
- 한 번의 사용자 입력이 문제를 두 번 전진시키지 않아야 한다.
- 문제 유형별 retry policy가 있으면 해당 계약을 따른다.

### 2.4 Final question and restart

- 마지막 문제 뒤 정의된 종료/완료 상태가 나타나야 한다.
- 새 세션/restart가 가능해야 한다.
- 직전 세션의 answer, feedback, disabled/transient state가 새 첫 문제에 남지 않아야 한다.

### 2.5 Browser/runtime safety

실제 사용자 입력 경로에서 다음이 없어야 한다.

- unhandled page error
- 핵심 흐름을 막는 request failure
- 무한 대기
- 중복 진행
- 필수 control을 가리는 overlay/state

반복 실행 횟수는 모든 후속 작업의 고정 ritual이 아니다. 회귀 위험, 실제 flake 또는 release acceptance가 요구할 때 충분한 반복으로 확장한다.

## 3. Reliability-relevant UX

회귀 범위에 포함:

- 다음 행동이 불명확해 진행이 막힘
- 터치 control이 눌리지 않거나 오조작됨
- disabled 시각 상태와 실제 상태 불일치
- 피드백 부재로 현재 상태 판단 불가
- double tap/key repeat/pointer 재진입으로 중복 처리
- focus 손실로 핵심 진행 불가
- loading/transition 중 입력으로 상태 오염

순수 시각 취향 차이는 reliability regression으로 자동 분류하지 않는다.

## 4. Regression handling

- 과거 PASS 보고나 이 문서의 `COMPLETED_REFERENCE` 문자열만으로 현재 동작을 보증하지 않는다.
- 실제 회귀가 재현되면 한 failure domain, 한 재현 조건, 한 binary criterion으로 수리한다.
- shared owner를 수정한 경우 직접 영향받는 sibling subject를 위험에 맞게 검증한다.
- 다른 독립 결함을 같은 patch에 섞지 않는다.
- 완료된 reliability baseline을 이유 없이 다시 broad stabilization project로 열지 않는다.

## 5. Relationship to current product work

현재 제품 우선순위는 `ACTIVE_PRODUCT_SCOPE.md`의 **Math skill/mastery adaptive vertical slice**다.

새 mastery/adaptive 작업은 이 문서의 reliability invariant를 깨뜨리면 안 된다. 특히 다음은 직접 영향 계약이다.

- adaptive next-question selection 후 실제 question identity가 전진함
- mastery/persistence state와 문제별 transient UI state가 섞이지 않음
- restart/restore 경로가 invalid transient state를 복원하지 않음
- skill/mastery 변경이 correct/incorrect feedback과 중복 입력 방지를 깨뜨리지 않음

## 6. Representative existing verification

현재 실제 파일 존재와 최신 명령을 먼저 확인한 뒤 위험에 맞게 사용한다.

```bash
uv run pytest -q tests/test_math_next_question_progression.py
uv run pytest -q tests/test_nonmath_next_question_progression.py
uv run pytest -q tests/test_nonmath_browser_acceptance.py
```

이 문서는 완료 계약 자체가 바뀌거나 새 adaptive architecture가 기존 reliability invariant를 명시적으로 대체할 때만 수정한다.
