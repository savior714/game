# Risk-Directed Verification — AidenGame

이 문서는 AidenGame의 개발·디버깅 검증 방식을 구체화한다. 현재 사용자 지시, 루트 `AGENTS.md`, `PROJECT_RULES.md`가 우선하며, 이 문서는 기존 `위험 기반 개발·테스트 선택` 원칙의 실행 규칙이다.

## 1. 핵심 원칙

**Criterion first; test-first only when it is the cheapest sufficiently faithful proof.**

- TDD는 품질 목표가 아니라 선택 가능한 verification strategy다.
- RED/GREEN, test count, coverage, `test-first` 준수 자체는 완료 근거가 아니다.
- 한 작업은 하나의 failure domain 또는 가설, 하나의 `PRIMARY_CRITERION`, 하나의 주 verification strategy를 유지한다.
- 검증은 가장 작은 test가 아니라 primary criterion을 실제로 falsify할 수 있는 가장 싸고 충분히 충실한 층에서 시작한다.
- primary criterion, 직접 영향 contract/sibling closure, 필수 static check가 통과하면 해당 failure domain은 종료한다.

## 2. Verification strategy

### REPRODUCTION_FIRST

이미 발생한 bug가 싸고 deterministic하게 재현되면 수정 전에 실제 실패를 고정한다. 수정 후 같은 재현을 GREEN으로 만들고 재발 가능성과 유지비가 합리적이면 regression으로 남긴다.

실제 browser/rendering/timing/device 조건에서만 재현되거나 pre-fix harness가 비싸고 flaky하면 failing unit test를 억지로 만들지 않는다. 실제 runtime에서 먼저 재현하고 수정 후 올바른 경계의 가장 싼 안정적 regression을 남긴다.

### CONTRACT_OR_EXAMPLE_FIRST

다음에는 focused test-first 또는 구현과 동시에 contract test를 우선한다.

- score/progress/save contract
- 입력 한 번당 직접 효과 한 번
- duplicate handler/listener 방지
- parser/validator/asset-manifest contract
- deterministic FSM과 restart/recovery
- unlock/progression invariant
- shared controller/state owner
- 데이터 손실·중복 반영 위험
- deterministic concurrency/timer invariant

테스트는 내부 함수 호출 순서보다 게임 사용자에게 보이는 상태 전이와 데이터 불변식을 고정한다.

### CHARACTERIZATION_FIRST

기존 게임 로직을 보존하는 refactor에서 외부 행동이 불명확하거나 회귀 위험이 큰 경우 사용한다. 현재 의도한 사용자 행동만 특성화하고 accidental implementation detail을 동결하지 않는다.

### IMPLEMENT_OR_RUNTIME_FIRST

다음에는 unit-test-first를 강제하지 않는다.

- 레이아웃, 스타일, 애니메이션
- 터치 감각, game feel, timing feel
- Pixi/WebGL/Canvas rendering
- responsive/visual behavior
- 탐색적 기능과 콘텐츠 표시
- browser/device/runtime wiring
- 단순 dependency/toolchain 승격

먼저 가장 작은 구현을 만들고 실제 browser/render/input 흐름에서 criterion을 판정한다. 안정된 사용자 계약이나 실제 regression 가치가 생긴 부분만 자동화한다.

## 3. Fidelity ladder

- **F0 STRUCTURAL** — diff, type/static check, asset/config/path inspection
- **F1 FOCUSED** — pure/domain/unit/contract test
- **F2 INTEGRATION** — shared controller, asset pipeline, persistence, build integration
- **F3 RUNTIME** — real browser, WebGL/Canvas, touch/input, responsive/game flow
- **F4 SYSTEM/RELEASE** — broad suite, device/release smoke, cutover artifact verification

규칙:

- visual/render/input failure를 F1 DOM mock만으로 닫지 않는다.
- F1이 실제 animation frame, Pixi renderer, browser event ordering 또는 persistence boundary를 관찰하지 못하면 F1 GREEN은 충분한 증거가 아니다.
- F4는 confirmed broad impact, generated-artifact cutover 또는 release 판단일 때만 확대한다.

## 4. AidenGame 위험 프로파일

**자동화 test-first 가치가 높은 영역**

- deterministic state machine
- save/progress/unlock
- duplicate input/effect
- scoring and completion
- shared event/controller ownership
- validator/build artifact integrity

**runtime-first 가치가 높은 영역**

- animation, visual composition, game feel
- Pixi/WebGL/Canvas behavior
- touch target, focus, responsive layout
- 실제 브라우저의 pointer/keyboard interaction
- performance/frame pacing

같은 작업에서 visual correctness와 독립적인 state bug를 억지로 하나의 criterion으로 묶지 않는다.

## 5. Regression automation gate

새 테스트는 다음을 만족할 때 추가하거나 유지한다.

- 구체적인 failure mode 또는 중요한 invariant가 있다.
- stable contract/boundary를 관찰한다.
- 반복 가능하고 flaky하지 않다.
- 실제 regression 탐지 가치가 유지 비용보다 높다.
- 수동 증거를 반복하는 것보다 싸다.

코드가 바뀌었다는 이유, coverage 확보, 형식적 RED, internal call count를 고정하기 위해 테스트를 만들지 않는다.

## 6. False GREEN 방지

- mock/fake/snapshot/baseline으로 실제 browser/rendering/persistence failure를 숨기지 않는다.
- production implementation을 그대로 재작성한 test는 독립적인 증거가 아니다.
- test와 production이 같은 잘못된 가정을 공유한 RED→GREEN은 사용자 계약 증거가 아니다.
- lower-fidelity GREEN과 actual runtime failure가 충돌하면 runtime evidence를 우선한다.

## 7. Local LLM prompt contract

로컬 prompt/runbook에는 generic `write tests first`를 넣지 않고 다음을 명시한다.

```text
PRIMARY_CRITERION: <단일 관찰 기준>
VERIFICATION_STRATEGY: REPRODUCTION_FIRST | CONTRACT_OR_EXAMPLE_FIRST | CHARACTERIZATION_FIRST | IMPLEMENT_OR_RUNTIME_FIRST
PRIMARY_FIDELITY: F0 | F1 | F2 | F3 | F4
WHY_THIS_STRATEGY: <현재 failure mode에 맞는 이유>
ESCALATE_IF: <현재 층으로 criterion을 판정할 수 없는 조건>
STOP_WHEN: <primary + direct closure + required static checks>
```

- 새 harness/seam/abstraction은 현재 criterion 관찰에 필요한 경우에만 추가한다.
- local executor가 test count나 coverage 목표를 새로 만들지 않는다.
- unrelated full-suite failure는 별도 failure domain으로 남긴다.

## 8. 종료 기준

다음이 모두 참이면 현재 failure domain은 종료한다.

1. `PRIMARY_CRITERION`이 충분한 fidelity에서 PASS한다.
2. 같은 invariant의 직접 영향 sibling/caller가 중복 workaround 없이 closure된다.
3. 변경 및 직접 영향 범위의 required static diagnostics가 clean하다.
4. 현재 변경으로 생긴 regression이 없다.
5. 더 높은 fidelity나 broad suite가 필요하다는 구체적 위험 근거가 없다.

추가 RED/GREEN 반복, coverage 채우기, unrelated full-suite 실행은 기본 완료 조건이 아니다.
