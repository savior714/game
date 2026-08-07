# Core Quiz Reliability Stabilization

- **Status:** COMPLETED — 4과목 핵심 journey 브라우저 반복 PASS 검증 완료
- **Effective date:** 2026-08-06
- **Scope:** AidenGame 일반 과목 문제풀이
- **Subjects:** Math, English, Korean, Science
- **Product authority:** `PROJECT_RULES.md`
- **Execution authority:** `AGENTS.md`
- **Proof authority:** current code, focused tests, and real-browser evidence on the latest `origin/main`

## 1. Purpose

현재 개발의 최우선 목표는 새로운 기능을 늘리는 것이 아니라 이미 제공 중인 일반 과목 문제풀이를 믿고 사용할 수 있는 상태로 만드는 것이다.

이번 단계는 다음 문제를 해소한다.

- 과목마다 핵심 흐름의 구현과 검증 수준이 다르다.
- 특정 결함이 수정되어도 다른 과목의 동등한 흐름이 함께 증명되지 않는다.
- 기능 수정, 구조 이전, 실험 기능 개발이 같은 우선순위로 병행되어 현재 방향이 흐려진다.
- 브라우저에서 한 번 동작한 사실과 상태 계약이 안정적으로 유지된다는 증명이 구분되지 않는다.
- 공용화가 실제 중복 확인보다 먼저 진행될 경우 안정화와 리팩터링의 실패 원인이 섞인다.

이번 문서는 일정 상태를 관리하는 plan이 아니다. 안정화 단계에서 작업을 선택하고 완료를 판정하는 제품·검증 계약이다.

## 2. Governing decisions

| # | Decision axis | Adopted rule |
|---|---|---|
| 1 | 최우선 목표 | 신규 기능·콘텐츠·게임성보다 기존 학습 기능의 신뢰성을 우선한다. |
| 2 | 진행 방식 | 대표 과목 하나를 현재 구조 안에서 안정화한 뒤 다른 과목으로 확장한다. |
| 3 | 대표 과목 기준 | 과거 중요도나 사용량이 아니라 현재 오류가 가장 명확하게 재현되는 과목을 우선한다. |
| 4 | 단계 종료 조건 | 네 기존 과목의 핵심 흐름이 모두 안정화되기 전에는 신규 기능 개발을 재개하지 않는다. |
| 5 | 제품 범위 | 일반 과목 문제풀이만 포함한다. Ocean Rescue와 실험 기능 개발은 중단한다. |
| 6 | 완료 증명 | 상태·동작 계약과 실제 브라우저 흐름을 함께 증명한다. |
| 7 | 첫 과목 선정 | 네 과목에 동일 진단을 실행하고 첫 실패 과목을 선택한다. 모두 통과하면 검증 공백이 가장 큰 과목을 선택한다. |
| 8 | 공용화 시점 | 첫 과목에서는 공용화하지 않는다. 두 번째 과목에서 같은 중복이 확인된 뒤에만 `shared/` 추출을 검토한다. |
| 9 | UI/UX 범위 | 진행 중단·오조작을 유발하는 사용성 결함은 포함하고 순수 시각 개선은 제외한다. |
| 10 | 게시 단위 | 과목 하나가 완료될 때마다 직접 영향 회귀를 확인하고 `origin/main`에 게시한다. |

## 3. Included product surface

운영 대상은 다음 네 경로다.

| Subject | Runtime entry |
|---|---|
| Math | `domains/math/index.html` |
| English | `domains/english/index.html` |
| Korean | `domains/korean/index.html` |
| Science | `domains/science/index.html` |

각 과목의 핵심 학습 흐름은 다음과 같다.

```text
메인 허브 또는 직접 진입
→ 첫 문제 표시
→ 답안 선택
→ 정답 또는 오답 처리
→ 피드백 확인
→ 다음 문제 이동
→ 반복
→ 마지막 문제 이후 종료 또는 재시작
```

과목별 문제 유형, 문구, 난이도 데이터, 보상 표현은 달라도 이 흐름의 진행 가능성과 상태 격리는 동일한 신뢰성 계약을 만족해야 한다.

## 4. Explicit exclusions and freeze policy

안정화 단계가 종료될 때까지 다음 작업은 시작하지 않는다.

- 신규 과목, 신규 문제 유형 또는 신규 콘텐츠 생산 파이프라인
- 적응형 난이도 알고리즘 확장
- 보상·성장·게임화 신규 기능
- Ocean Rescue 신규 기능, typed-controller 이전, 렌더링 개선 또는 추가 구조 이전
- Space Explorer 등 `experiments/` 신규 기능
- 순수 시각 리디자인, 장식, 애니메이션 또는 테마 개선
- 검증된 중복 근거가 없는 공용 엔진 통합
- 이번 흐름과 직접 관련 없는 dependency 또는 toolchain upgrade
- 상태를 표시하기 위한 별도 plan/evidence 문서와 그 상태를 검사하는 테스트

예외는 현재 배포 사용을 막는 치명적 회귀, 데이터 손상, 보안 문제다. 예외 수정은 안정화 작업과 별도 failure domain으로 수행하고 직접 영향만 검증한다.

## 5. Baseline interpretation

기존 테스트와 최근 수정은 출발점이지 네 과목 완료의 자동 증명이 아니다.

현재 저장소에는 다음과 같은 관련 검증이 존재한다.

- `tests/test_math_next_question_progression.py`
- `tests/test_nonmath_next_question_progression.py`
- `tests/test_nonmath_browser_acceptance.py`

이 테스트들은 재사용하거나 확장할 수 있지만, 파일 이름이나 과거 PASS 보고만으로 과목을 완료 처리하지 않는다. 최신 `origin/main`에서 아래 공통 진단과 과목별 완료 계약을 다시 적용한다.

이미 수정된 다음 문제 진행이나 터치 타깃 문제를 새로운 개발 목표로 반복하지 않는다. 동일 증상이 재현될 때만 회귀로 취급한다.

## 6. Phase 0 — Four-subject diagnostic matrix

첫 구현 변경 전에 네 과목에 같은 진단을 실행한다. 이 단계의 목적은 수정이 아니라 현재 실패 지점을 비교 가능한 형식으로 측정하는 것이다.

### 6.1 Common diagnostic scenario

각 과목에서 다음 순서를 동일하게 수행한다.

1. 운영 entry를 실제 브라우저로 연다.
2. 첫 문제의 식별 가능한 값 또는 화면 내용을 기록한다.
3. 답안 선택 전 제출·다음 문제 컨트롤의 초기 상태를 확인한다.
4. 정답 경로를 완료하고 피드백을 확인한다.
5. 다음 문제로 이동한다.
6. 문제 식별 값 또는 의미 있는 화면 내용이 바뀌었는지 확인한다.
7. 이전 답안 선택, 정오답 스타일, 피드백, disabled 상태가 남지 않았는지 확인한다.
8. 오답 경로를 완료하고 피드백을 확인한다.
9. 다시 다음 문제로 이동해 동일한 상태 초기화를 확인한다.
10. 마지막 문제 또는 세션 종료 경계까지 진행한다.
11. 종료 화면, 새 세션 시작 또는 재시작 동작을 확인한다.
12. 페이지 오류, unhandled exception, failed request, 무한 대기, 중복 진행이 없는지 확인한다.

### 6.2 Diagnostic result

과목별 결과는 다음 중 하나로만 분류한다.

- `FAIL`: 공통 시나리오에서 재현 가능한 실패가 있다.
- `PASS_WITH_GAP`: 시나리오는 통과하지만 필수 상태 계약 또는 반복 브라우저 증거가 부족하다.
- `PASS`: 이 문서의 과목별 완료 계약까지 이미 충족한다.

### 6.3 Representative subject selection

1. `FAIL` 과목이 있으면 첫 재현 실패가 명확한 과목을 대표 과목으로 선택한다.
2. 여러 과목이 같은 실패를 보이면 가장 작은 재현 조건으로 원인을 격리할 수 있는 과목을 선택한다.
3. 모든 과목이 시나리오를 통과하면 `PASS_WITH_GAP` 중 상태 계약과 브라우저 증거의 공백이 가장 큰 과목을 선택한다.
4. 과거에 중요했던 과목, 파일 수가 많은 과목, 수학이라는 이유만으로 자동 선택하지 않는다.

## 7. Subject completion contract

한 과목은 다음 여섯 계약을 모두 만족해야 완료된다.

### 7.1 Question progression identity

- 다음 문제 동작 후 현재 문제의 안정적인 식별 값 또는 의미 있는 콘텐츠가 이전 문제와 달라야 한다.
- 단순 DOM 재렌더, 카운터 변화 또는 애니메이션만으로 진행을 판정하지 않는다.
- 문제 풀이 대상이 실제로 바뀌지 않으면 FAIL이다.

### 7.2 Per-question state reset

다음 문제 진입 시 이전 문제에서 생성된 다음 상태가 남지 않아야 한다.

- 선택된 답안
- 정답·오답 스타일
- 피드백 텍스트와 보조 설명
- 제출 또는 다음 문제 버튼의 disabled/enabled 상태
- 중복 제출 방지 latch
- 문제별 임시 점수·시도·도움말 상태
- pointer, focus 또는 keyboard interaction 상태

의도적으로 세션 전체에 유지되는 점수·연속 정답·진도는 문제별 상태와 구분해 검증한다.

### 7.3 Correct and incorrect paths

- 정답 경로와 오답 경로 모두 피드백 후 다음 문제로 진행할 수 있어야 한다.
- 한 경로만 검증한 과목은 완료가 아니다.
- 오답 후 재시도 정책이 있는 경우 그 정책을 따른 뒤 진행 가능해야 한다.
- 피드백 노출 중 중복 클릭이나 연속 입력이 상태를 두 번 전진시키면 FAIL이다.

### 7.4 Final-question and restart boundary

- 마지막 문제 이후 정의된 종료 화면 또는 완료 상태가 나타나야 한다.
- 종료 후 새 세션 시작 또는 재시작이 가능해야 한다.
- 재시작한 첫 문제에 직전 세션의 답안·피드백·disabled 상태가 남지 않아야 한다.
- 영속화된 통계가 있더라도 새 문제의 transient state와 섞이지 않아야 한다.

### 7.5 Repeated real-browser proof

- 실제 지원 브라우저에서 전체 핵심 흐름을 반복 실행한다.
- 최소 기준은 최초 1회와 연속 3회 반복, 총 4회 모두 PASS다.
- 브라우저가 생성한 사용자 입력을 사용한다.
- unhandled page error와 request failure를 수집하고 허용 목록 없이 0건을 요구한다. 저장소 자체 로컬 정적 서버가 불필요한 외부 요청을 만들지 않는다는 전제다.
- 반복 중 한 번이라도 실패하면 flake로 분류해 원인을 해결하기 전에는 완료 처리하지 않는다.

### 7.6 Previously stabilized subject regression

- 새 과목을 수정할 때 이미 완료한 과목의 직접 영향 회귀를 확인한다.
- 공유 파일을 수정하지 않았다면 완료 과목의 focused contract와 최소 브라우저 smoke를 실행한다.
- `shared/` 또는 공용 UI를 수정했다면 영향을 받는 완료 과목 모두의 상태 계약과 브라우저 핵심 흐름을 다시 검증한다.
- 다른 과목의 실패를 발견하면 현재 원인과 한 번에 수정하지 않고 별도 failure domain으로 남긴다.

## 8. Reliability-relevant UI/UX

다음은 신뢰성 범위에 포함한다.

- 다음 행동이 불명확해 사용자가 진행하지 못함
- 실제 터치 환경에서 컨트롤이 눌리지 않거나 잘못 눌림
- disabled 상태와 시각 상태가 불일치함
- 정오답 피드백이 없어 현재 상태를 판단할 수 없음
- 중복 클릭, double tap, key repeat 또는 pointer 재진입이 문제를 두 번 진행시킴
- focus가 사라져 키보드 진행이 막힘
- overlay, toast 또는 animation이 필수 컨트롤을 가림
- 로딩 또는 전환 중 입력이 허용되어 상태가 오염됨

다음은 안정화 단계에서 제외한다.

- 색상·그림자·배경·장식 변경
- 새 애니메이션
- 캐릭터와 보상 연출 개선
- 기능과 무관한 레이아웃 재설계
- 브랜드 또는 테마 통일

구분 기준은 “예쁜가”가 아니라 “사용자가 의도한 학습 흐름을 정확히 완료할 수 있는가”다.

## 9. Implementation sequence

### Step 1 — Diagnose all four subjects

- 소스 수정 없이 공통 진단을 네 과목에 실행한다.
- 실패 재현 조건, 관찰 결과, 단일 판정 기준을 기록한다.
- 첫 대표 과목을 선택한다.

### Step 2 — Stabilize the representative subject

- 첫 failure domain 하나만 선택한다.
- 해당 과목의 현재 구조와 소유권을 유지한다.
- 수정 전 재현 조건과 binary criterion을 고정한다.
- 수정 후 같은 진단으로 해당 원인만 독립 검증한다.
- 다른 실패는 별도 항목으로 남기고 다음 failure domain으로 이동한다.
- 모든 subject completion contract가 충족될 때까지 반복한다.
- 완료 전 선제적 `shared/` 추출을 하지 않는다.

### Step 3 — Publish the completed subject

- 과목의 상태 계약과 반복 브라우저 증거를 모두 확인한다.
- 수정 파일과 직접 영향 모듈의 정적 진단을 0으로 만든다.
- 최신 `origin/main` 이동 여부를 확인한다.
- 최신 main에 재적용한 뒤 focused verification을 다시 실행한다.
- 과목 하나의 완료를 하나의 게시 경계로 삼아 main에 fast-forward push한다.

### Step 4 — Apply the contract to the second subject

- 최신 main에서 공통 진단을 다시 실행한다.
- 두 번째 과목의 실제 실패 또는 검증 공백을 해결한다.
- 첫 과목과 같은 코드·상태·UI 패턴이 반복되는지 비교한다.

### Step 5 — Consider shared extraction

다음 조건이 모두 충족될 때만 공용화를 허용한다.

1. 두 과목에서 실제로 동일한 책임이 반복된다.
2. 입력·출력·상태 전이 계약이 동일하다.
3. 과목별 차이를 callback, configuration 또는 data로 표현할 수 있다.
4. 추출 후 두 과목의 상태 계약과 브라우저 흐름을 함께 검증할 수 있다.
5. 공용화가 현재 재현 실패를 해결하거나 재발 방지 계약을 명확히 한다.

단순히 코드가 비슷해 보이거나 장기 구조가 깔끔해진다는 이유로 추출하지 않는다.

### Step 6 — Complete the remaining subjects

- 최신 main에서 미완료 과목을 다시 진단한다.
- 한 과목씩 같은 완료 계약을 적용한다.
- 과목 완료마다 게시한다.
- 네 과목 모두 완료된 후에만 안정화 종료를 판정한다.

## 10. Work-package discipline

과목은 게시 단위지만, 구현 중 여러 실패 원인을 한 작업으로 섞지 않는다.

각 실행 작업은 다음 형식을 따른다.

```text
한 작업
= 한 failure domain
= 한 재현 조건
= 한 binary criterion
= 한 독립 검증
```

예:

- 답안 상태 초기화 실패
- 다음 문제 identity 미변경
- 중복 클릭으로 index 2회 증가
- 마지막 문제 이후 restart 실패
- 브라우저 request failure
- 직접 영향 파일의 lint/type 오류

위 원인들은 같은 과목에서 발견되어도 순차적으로 해결한다. 한 원인을 검증한 뒤 다음 원인을 선택하며, unrelated full-suite 재실행으로 원인을 섞지 않는다.

## 11. Verification strategy

검증 순서는 가장 작은 위험 대응 검사부터 확장한다.

1. 재현 스크립트 또는 focused state contract
2. 해당 과목의 focused unit/static test
3. 해당 과목의 실제 브라우저 flow
4. 이미 완료한 과목의 직접 영향 regression
5. 공용 파일 변경 시 영향받는 과목 matrix
6. repository-wide gate는 실제 공용 cutover 또는 저장소 정책상 필수인 경우

기존 관련 테스트는 유지하되 새 완료 계약을 대신한다고 가정하지 않는다.

권장 출발점:

```bash
uv run pytest -q tests/test_math_next_question_progression.py
uv run pytest -q tests/test_nonmath_next_question_progression.py
uv run pytest -q tests/test_nonmath_browser_acceptance.py
```

실제 다음 작업에서는 현재 Justfile과 테스트 구조를 확인해 네 과목 공통 진단을 하나의 명시적 recipe로 만들 수 있다. recipe 추가 자체가 목적이 되어서는 안 되며 네 과목의 동일 시나리오를 재현 가능하게 실행하는 데 필요할 때만 추가한다.

## 12. Publication and reporting

### 12.1 Publication boundary

- 과목 하나의 완료 계약이 모두 충족된 뒤 게시한다.
- 미완료 과목의 부분 수정은 publish하지 않는다는 뜻이 아니라, 현재 repository 정책상 안전과 충돌 회피를 위해 중간 게시가 필요한 경우에도 “과목 완료”로 보고하지 않는다.
- 완료 보고의 `CHANGE`는 어떤 과목의 어떤 계약이 닫혔는지 명시한다.
- `VERIFY`는 상태 계약, 브라우저 반복 횟수, 직접 영향 회귀를 포함한다.

### 12.2 Status truth

- 수동 체크박스나 문서의 `COMPLETE` 문자열은 완료의 근거가 아니다.
- 완료의 근거는 최신 main의 코드, 테스트, 브라우저 증거와 해당 게시 커밋이다.
- 이 문서에 과목별 진행 상태를 계속 갱신하지 않는다.
- 일정과 다음 작업은 대화에서 관리하고, 제품 계약이 바뀔 때만 이 문서를 수정한다.

## 13. Stabilization exit gate

안정화 단계는 다음 조건을 모두 만족할 때만 종료한다.

- Math가 subject completion contract를 모두 만족한다.
- English가 subject completion contract를 모두 만족한다.
- Korean이 subject completion contract를 모두 만족한다.
- Science가 subject completion contract를 모두 만족한다.
- 네 과목의 정답·오답·다음 문제·종료·재시작 핵심 흐름이 실제 브라우저에서 반복 PASS한다.
- 네 과목의 문제별 상태가 다음 문제와 새 세션에 누출되지 않는다.
- 완료한 과목 간 직접 영향 회귀가 없다.
- 수정 파일과 직접 영향 모듈의 필수 정적 진단이 0이다.
- unresolved P0/P1 일반 문제풀이 결함이 없다.

종료 후 다음 우선순위는 자동으로 정하지 않는다. 최신 제품 상태를 다시 평가한 뒤 콘텐츠 확장, 학습 효과, Ocean Rescue 또는 다른 기능 중 다음 방향을 별도로 결정한다.

## 14. Immediate next action

네 과목(Math, English, Korean, Science)의 exit gate 브라우저 검증이 완료되었으므로 후속 작업은 `docs/plans/PLAN_A_TRACK_RUNTIME_EXECUTION_RUNBOOK.md`에 따라 진행한다.
