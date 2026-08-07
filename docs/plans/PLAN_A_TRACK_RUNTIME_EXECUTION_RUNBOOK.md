# A 트랙 런타임·플레이 — Active Execution Runbook

- **상태:** ACTIVE — Ocean Rescue 런타임 수용 완료 / 다음 A failure domain 대기
- **갱신:** 2026-08-08 KST
- **기준:** 실행 시점의 최신 `origin/main`
- **목적:** 완료 이력을 반복해서 읽지 않고 현재 남은 A 트랙 작업만 순차 실행한다.

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

### Ocean Rescue A 트랙 선택 시

- `docs/specs/product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md`
- `domains/ocean-rescue/src/sea-turtle-scene.js`
- sea-turtle / travel runtime의 직접 focused/browser tests
- B 생산물은 alias/metadata/runtime handoff 확인에 필요한 부분만 read-only로 본다.

### 읽지 않는 것

- 완료된 Math / English / Korean / Science exit gate 검증 로그
- 완료된 YouTube 자유시간 구현·closeout 로그
- Ocean Rescue의 art packet/generator/approval 전체 이력
- 현재 카드와 무관한 dependency/toolchain 문서

---

## 2. Current cut line

### 완료되어 ACTIVE backlog에서 제거

- Math / English / Korean / Science의 개별 next/reset/restart 보강 작업
- Core Quiz stabilization exit gate (`A-QUIZ-EXIT-01`, `A-QUIZ-EXIT-02`) 브라우저 반복 PASS 확인 및 스펙 완료 처리
- YouTube 15분 자유시간 세션 구현과 제품 스펙 closeout (`APPROVED_PRODUCT_CONTRACT_IMPLEMENTED`)
- Ocean Rescue B 트랙의 seaweed loop 01, 02, 03 생산 및 A 트랙 런타임 소비 (`A-OR-SEAWEED-01`)
  - `sea-turtle-scene.js`가 `scene.seaweed-loop.01/.02/.03`을 세 loop slot에 각각 소비하며 브라우저 acceptance PASS

위 항목은 **구체적인 회귀가 최신 main에서 다시 재현될 때만** 새 failure domain으로 연다.

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

## 4. 이후 A 트랙 선택 규칙

현재 ACTIVE 큐의 모든 작업이 최신 `origin/main`에 완료·게시되었다.

다음 세션에서는 최신 `origin/main`과 `AGENTS.md`의 A 트랙 정의를 읽고 아래 우선순위에 따라 다음 **실제 RED 또는 증거 공백 하나**만 선택하여 ACTIVE 카드로 추가한다.

우선순위:

1. 사용자 진행을 막는 A runtime 회귀
2. 현재 vertical slice의 직접 미충족 runtime contract
3. 이미 게시된 B asset 계약의 A 소비 누락
4. 그 외 runtime/play 품질

B 생산 변경이 필요하면 A에서 억지로 닫지 않고 B 선행 작업으로 분리한다.

---

## 5. 로컬 LLM 실행 카드 형식

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

## 6. 런북 유지 규칙

- 완료된 카드는 다음 갱신 때 삭제한다.
- 완료 RED/GREEN 로그, 반복 PASS 횟수, 과거 prompt, 오래된 SHA를 누적하지 않는다.
- current cut line + ACTIVE 1개 + 가까운 NEXT 2개 정도만 유지한다.
- `DISCOVERED_FAILURE`는 실제로 다음 판단에 필요한 소수만 유지한다.
- 단지 `origin/main` SHA가 바뀌었다는 이유로 이 문서를 갱신하지 않는다.
