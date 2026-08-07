# A 트랙 런타임·플레이 — Active Execution Runbook

- **상태:** ACTIVE — Core Quiz stabilization exit gate 재확인
- **갱신:** 2026-08-08 KST
- **기준:** 실행 시점의 최신 `origin/main`
- **목적:** 완료 이력을 반복해서 읽지 않고 현재 남은 A 트랙 작업만 로컬 LLM이 순차 실행한다.

이 파일은 history/changelog가 아니라 **rolling working set**이다. 완료 상세, 과거 RED/GREEN 로그, 오래된 SHA, 해결된 blocker는 남기지 않는다. 완료 이력의 권위는 Git history와 최신 코드·테스트·브라우저 증거다.

---

## 1. 시작 시 읽기 예산

현재 카드에 필요한 것만 읽는다.

### 공통

1. `AGENTS.md`
2. `PROJECT_RULES.md`
3. 이 런북
4. 현재 카드의 가장 가까운 product/technical spec
5. production owner와 focused test

### ACTIVE가 Core Quiz일 때

- `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md` §7, §11, §13, §14
- 기존 네 과목 browser/progression/restart focused tests 중 현재 판정에 필요한 파일만

### Ocean Rescue NEXT로 이동했을 때

- `docs/specs/product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md` §4, §5, §8, §13
- `domains/ocean-rescue/src/sea-turtle-scene.js`
- sea-turtle runtime의 직접 focused/browser tests
- B 생산물은 alias/metadata/runtime handoff 확인에 필요한 부분만 read-only로 본다.

### 읽지 않는 것

- 완료된 Math / English / Korean / Science 수정 로그 전체
- 완료된 YouTube 자유시간 구현·closeout 로그
- Ocean Rescue의 art packet/generator/approval 전체 이력
- 현재 카드와 무관한 dependency/toolchain 문서

---

## 2. Current cut line

### 완료되어 ACTIVE backlog에서 제거

- Math / English / Korean / Science의 개별 next/reset/restart 보강 작업
- YouTube 15분 자유시간 세션 구현과 제품 스펙 closeout
  - 현재 제품 스펙 상태는 `APPROVED_PRODUCT_CONTRACT_IMPLEMENTED`
- Ocean Rescue B 트랙의 seaweed loop 생산
  - `scene.seaweed-loop.01/.02/.03` 모두 canonical source → approval → atlas/registry handoff 완료

위 항목은 **구체적인 회귀가 최신 main에서 다시 재현될 때만** 새 failure domain으로 연다.

### 아직 닫지 않은 것

`CORE_QUIZ_RELIABILITY_STABILIZATION.md` 자체는 여전히 ACTIVE이며 exit gate는 네 과목 모두의 completion contract와 반복 실제 브라우저 증거를 요구한다.

최근 개별 focused 보강이 많다는 사실만으로 이 exit gate를 자동 완료 처리하지 않는다. 반대로 이미 존재하는 증거를 다시 구현하거나 같은 테스트를 중복 생성하지도 않는다.

### 다음 A 런타임 공백도 이미 확인됨

B가 세 seaweed loop를 모두 게시했지만 현재 `domains/ocean-rescue/src/sea-turtle-scene.js`는:

- `REQUIRED_ALIASES`에 `scene.seaweed-loop.01`만 요구하고
- 세 loop sprite를 모두 `scene.seaweed-loop.01`로 생성한다.

따라서 Core Quiz exit가 닫힌 뒤에는 A가 B의 확정된 `.01/.02/.03` 계약을 실제 sea-turtle runtime에서 소비하는 작업이 높은 우선순위다.

---

## 3. 공통 실행 계약

- **한 작업 = 한 failure domain = 한 검증 가능한 가설 = 한 primary criterion**
- 수정 전 shared owner와 같은 invariant를 소비하는 sibling surface를 read-only로 조사한다.
- 같은 root cause + invariant + ownership/rollback boundary를 완전히 닫는 범위는 파일 수보다 coherent change를 우선한다.
- 다른 root cause는 `DISCOVERED_FAILURE`로 남기고 현재 작업에 섞지 않는다.
- production 수정 전 exact reproduction 또는 exact evidence gap을 확정한다.
- focused primary verify → 직접 영향 verify → 필요한 static verify 순서로 진행한다.
- 현재 카드 판정 전에 unrelated full suite를 우선 실행하지 않는다.
- A는 runtime/play만 수정한다. asset source/schema/generator/atlas/provenance는 B 소유다.
- 게시가 필요한 변경은 최신 `origin/main`에 fast-forward로 반영한다.

---

## 4. ACTIVE — A-QUIZ-EXIT-01

### Objective

네 과목 일반 문제풀이 stabilization exit gate가 **최신 main의 현재 증거로 실제 충족되는지 한 번만 재확인**한다.

### Mode

`VERIFY_ONLY_FIRST`

처음부터 production을 수정하지 않는다.

### Failure domain

`CORE_QUIZ_STABILIZATION_EXIT_GATE_CURRENT_EVIDENCE_UNPROVEN`

### Hypothesis

최근 Math / English / Korean / Science의 progression, wrong-answer reset, full-session restart 보강을 합치면 최신 main은 이미 제품 스펙 §13 exit gate를 충족한다.

### Primary criterion

최신 main에서 **네 과목 각각** 제품 스펙 §7의 핵심 journey를 실제 브라우저 사용자 입력으로 최초 1회 + 연속 3회, 총 4회 반복했을 때 모두 PASS하고 page error / request failure가 0이다.

### 실행 범위

1. 먼저 기존 focused/browser tests가 아래 계약을 어디까지 이미 증명하는지 inventory한다.
   - question identity가 실제로 바뀜
   - correct와 incorrect path 모두 다음 문제로 진행
   - per-question transient state reset
   - final question → result/completion
   - restart → clean first-question state
2. 같은 증거가 이미 있으면 새 테스트를 만들지 않는다.
3. 부족한 것은 **브라우저 실행 증거만** 보충한다. 범용 mega-harness나 새 policy validator를 만들지 않는다.
4. 네 과목을 한꺼번에 수정하지 않는다.
5. 한 과목이라도 재현 가능한 실패가 나오면 즉시 이 exit 판정을 `FAIL`로 끝내고, **첫 실패 과목 하나만** 다음 ACTIVE failure domain으로 승격한다.
6. 다른 과목의 실패는 현재 수정하지 않는다.

### PASS 후

A-QUIZ-EXIT-02로 이동한다.

### FAIL 후

A-QUIZ-EXIT-02로 가지 않는다. 첫 실패 과목의 단일 invariant를 새 ACTIVE 카드로 교체한다.

---

## 5. NEXT — A-QUIZ-EXIT-02

**진입 조건:** A-QUIZ-EXIT-01 `PASS`

### Mode

`DOCUMENTATION_ONLY`

### Failure domain

`CORE_QUIZ_STABILIZATION_DIRECTION_DOCS_STALE_AFTER_EXIT`

### Hypothesis

실제 exit evidence가 PASS한 뒤에도 `CORE_QUIZ_RELIABILITY_STABILIZATION.md` / `AGENTS.md`가 계속 이를 현재 미완료 기본 방향으로 가리키면 다음 세션이 이미 끝난 audit를 반복하게 된다.

### Primary criterion

제품 계약의 의미를 바꾸지 않고 **현재 방향/status 표현만 최신 exit evidence와 일치**시키며 runtime source/test에는 diff가 없다.

### 주의

- A-QUIZ-EXIT-01의 PASS 없이 문서부터 완료 처리하지 않는다.
- 과거 상세 completion history를 문서에 새로 쓰지 않는다.
- 다음 제품 로드맵을 장문으로 추가하지 않는다.

PASS 후 A-OR-SEAWEED-01로 이동한다.

---

## 6. NEXT — A-OR-SEAWEED-01

**진입 조건:** A-QUIZ-EXIT-01 및 A-QUIZ-EXIT-02 PASS/PUBLISHED

### Objective

B가 확정·게시한 세 개의 authored seaweed loop를 sea-turtle runtime이 실제 세 loop에 각각 소비한다.

### Failure domain

`SEA_TURTLE_RUNTIME_DUPLICATES_LOOP_01_TEXTURE_FOR_ALL_THREE_OBSTACLES`

### Current evidence

현재 `sea-turtle-scene.js`는 세 sprite 모두 `scene.seaweed-loop.01`을 사용한다. B 생산 계약에는 `.01/.02/.03`이 모두 존재하고 승인·atlas/registry handoff가 완료되어 있다.

### Hypothesis

runtime loop slot 1/2/3을 각각 `scene.seaweed-loop.01/.02/.03`에 매핑하면 gameplay state/hit geometry는 그대로 유지하면서 세 authored obstacle을 정확히 소비할 수 있다.

### Primary criterion

실제 sea-turtle rescue browser journey에서:

- loop slot 1/2/3이 각각 `.01/.02/.03` authored texture를 사용하고
- 기존 active-rope 순서와 3회 release 동작이 그대로 완료되며
- pointer/hit behavior와 rescue success transition이 변하지 않고
- page error / console error / failed local request가 0이다.

### Authorized write scope

우선순위:

1. `domains/ocean-rescue/src/sea-turtle-scene.js`
2. 이 invariant를 직접 검증하는 기존 focused/browser test

B 소유 경로는 수정하지 않는다.

### Read-only sibling inventory

- sea-turtle typed lifecycle/controller가 visual alias를 소유하는지 여부
- loop sprite count/active-rope mapping을 검증하는 기존 tests
- generated registry에서 `.01/.02/.03` alias 존재 여부만 확인

### Do not

- seaweed SVG/metadata/art approval/atlas generator 수정
- loop gameplay 규칙·hit geometry·rope state machine 재설계
- crab/whale mission까지 시각 변경 확장
- rendering MVP 전체 acceptance를 한 카드에 묶기

---

## 7. 그 이후 선택 규칙

A-OR-SEAWEED-01까지 닫힌 뒤 이 런북에 장기 후보를 쌓지 않는다.

최신 main에서 다음 **실제 RED 또는 증거 공백 하나**만 선택한다.

우선순위:

1. 사용자 진행을 막는 A runtime 회귀
2. 현재 vertical slice의 직접 미충족 runtime contract
3. 이미 게시된 B asset 계약의 A 소비 누락
4. 그 외 runtime/play 품질

B 생산 변경이 필요하면 A에서 억지로 닫지 않고 B 선행 작업으로 분리한다.

---

## 8. 로컬 LLM 실행 카드 형식

현재 ACTIVE 카드 하나만 수행한다.

```text
TASK_ID: <one>
MODE: VERIFY_ONLY_FIRST | MODIFY_AND_VERIFY | DOCUMENTATION_ONLY
FAILURE_DOMAIN: <one>
HYPOTHESIS: <one sentence>
PRIMARY_CRITERION: <one binary observation>

DO
- latest origin/main 기준 isolated locked worktree
- exact reproduction/evidence gap 확정
- sibling surface read-only inventory
- 필요한 경우에만 root-cause-complete coherent change
- focused primary verify
- direct-impact verify
- 필요한 static verify + git diff --check
- latest main 재확인 후 fast-forward publish

DO_NOT
- 다음 카드까지 처리
- 다른 failure domain 수정
- B 생산 체인 수정
- unrelated refactor/dependency upgrade
- 기존 증거와 같은 테스트 중복 생성
- full suite를 primary criterion 대신 사용

OUTPUT
RESULT: PASS | FAIL | BLOCKED
PRIMARY_VERIFY: PASS | FAIL | NOT_RUN
DIRECT_VERIFY: PASS | FAIL | NOT_RUN
STATIC_VERIFY: PASS | FAIL | NOT_RUN
PUBLISH: PUBLISHED | NOT_PUBLISHED | NOT_APPLICABLE
COMMIT: <sha | NONE>
CHANGE: <summary | NONE>
DISCOVERED_FAILURE: <NONE | one out-of-scope failure>
BLOCKER: <NONE | exact blocker>
```

---

## 9. 런북 유지 규칙

- 완료된 카드는 다음 갱신 때 삭제한다.
- 완료 RED/GREEN 로그, 반복 PASS 횟수, 과거 prompt, 오래된 SHA를 누적하지 않는다.
- current cut line + ACTIVE 1개 + 가까운 NEXT 2개 정도만 유지한다.
- `DISCOVERED_FAILURE`는 실제로 다음 판단에 필요한 소수만 유지한다.
- 단지 `origin/main` SHA가 바뀌었다는 이유로 이 문서를 갱신하지 않는다.
