# A 트랙 런타임·플레이 — Active Execution Runbook

- **상태:** ACTIVE — YouTube 자유시간 실제 브라우저 수용 단계
- **갱신:** 2026-08-08 KST
- **재구성 기준:** `origin/main` reviewed through `eae29f3b6de716f1312194b1669f8ad39dcafe63`
- **목적:** 완료된 작업 이력을 반복해서 읽지 않고, 현재 남은 A 트랙 작업만 로컬 LLM이 독립 실행한다.

이 문서는 **continuation-only 런북**이다. 과거 4과목 audit matrix, 완료된 failure domain, 장문의 공통 Git/테스트 규칙은 의도적으로 제거했다. 일반 운영 규칙은 `AGENTS.md`와 `agents/workflows/git.md`를 따른다.

---

## 1. 권위와 읽기 예산

작업 시작 시 다음만 읽는다.

1. `AGENTS.md`
2. `PROJECT_RULES.md`
3. 이 런북
4. `docs/specs/product/AIDENGAME_YOUTUBE_FREE_TIME_SESSION.md` 중 현재 작업과 직접 관련된 절
5. 현재 failure domain의 production owner와 focused test

과거 대화, 과거 PASS 보고, 이전 SHA를 현재 상태의 권위로 사용하지 않는다. 항상 최신 `origin/main`을 다시 확인한다.

### 읽지 않는 것

- 완료된 Math / English / Korean / Science audit 전체
- 이미 green인 테스트를 설명하는 과거 실행 로그
- Ocean Rescue B 트랙 asset packet / generator / atlas 내부
- 현재 failure domain과 무관한 의존성·도구 업데이트 문서

필요한 경우에만 특정 완료 테스트를 직접 영향 회귀로 다시 연다.

---

## 2. 현재 cut line

### 활성 backlog에서 제거

일반 4과목 문제풀이 신뢰성 보강은 현재 런북의 실행 backlog에서 제거한다.

최근 main에는 다음과 같은 실제 브라우저/상태 계약 보강이 이미 들어가 있다.

- Math: reinforcement A→B→A 결정성, full-session clean restart
- English: wrong-answer/typing reset, 10-question completion → clean restart
- Korean: wrong-answer reset, mixed 10-question → clean restart
- Science: restart binding, wrong-answer reset, mixed full-session restart

**재개 조건은 하나뿐이다:** 최신 main에서 구체적인 회귀가 다시 재현될 때. 그때만 새 failure domain으로 연다. "혹시 빠졌을 수 있음"을 이유로 4과목 전체 감사를 반복하지 않는다.

### 현재 활성 영역

`docs/specs/product/AIDENGAME_YOUTUBE_FREE_TIME_SESSION.md` §14의 구현 경계 중 다음은 이미 production/test에 존재한다.

1. 세션 상태와 deadline 기반 시간 계산
2. 외부 탭 + 15분 차감 시작 트랜잭션
3. 고정 타이머 + Document PiP fallback
4. 경고/만료/acknowledge 수명주기

최근 main에는 추가로 다음 보강이 들어갔다.

- expired session bootstrap 복원
- acknowledged session restore 보존
- 시작 클릭에서 `AudioContext`를 준비하고 만료 경고에서 재사용

따라서 **현재 남은 단계는 §14.5 실제 브라우저 수용(closeout)** 이다.

스펙 상단의 `APPROVED_PRODUCT_CONTRACT_NOT_IMPLEMENTED` 상태 문자열은 구현 현실보다 오래된 문서 상태다. 현재 작업자는 이 문자열을 근거로 기능을 처음부터 재구현하지 않는다. 런타임 closeout 후 별도 문서 정합성 작업에서 갱신한다.

---

## 3. 공통 실행 계약

모든 카드는 다음을 지킨다.

- **한 작업 = 한 failure domain = 한 검증 가능한 가설 = 한 primary criterion**
- 수정 전 shared owner와 같은 invariant를 소비하는 sibling surface를 읽기 전용으로 확인한다.
- 같은 root cause + invariant + ownership/rollback boundary를 완전히 닫는 범위는 파일 수보다 coherent change를 우선한다.
- 다른 root cause는 `DISCOVERED_FAILURE`로 남기고 현재 작업에 섞지 않는다.
- production 수정 전에 exact reproduction 또는 exact evidence gap을 확정한다.
- focused 검증 → 직접 영향 검증 → 필요한 static 검증 순서로 진행한다.
- 현재 카드 판정 전에 full suite를 우선 실행하지 않는다.
- `origin/main` fast-forward 게시 후 clean worktree만 회수한다.

A 트랙은 runtime/play만 수정한다. asset source/schema/generator/atlas/provenance가 원인이면 B 트랙으로 넘긴다.

---

## 4. Active Queue

큐는 **위에서부터 하나씩** 처리한다. 앞 카드가 PASS/PUBLISHED 되기 전에는 다음 카드를 시작하지 않는다.

### A-RWD-05A — 실제 시작 클릭 → 외부 YouTube 탭

**Failure domain**

`YOUTUBE_FREE_TIME_REAL_BROWSER_START_ACCEPTANCE_UNPROVEN`

**가설**

지원 브라우저의 실제 사용자 클릭 한 번은 공식 YouTube 탭 생성 시도를 정확히 한 번 만들고, 성공 시에만 15분을 정확히 한 번 차감하며 활성 세션/타이머를 하나 만든다.

**Primary criterion**

실제 브라우저 smoke 1회에서 다음이 동시에 성립한다.

- 보호자 승인 전: 새 탭 0, 차감 0, 활성 세션 0
- 시작 클릭 1회: 외부 탭 생성 시도 1회
- 성공 후: `youtube_minutes` 정확히 -15
- 활성 session 정확히 1개
- 게임 탭 timer 표시
- 같은 클릭에서 pageerror / console.error / failed local request 0

**먼저 읽기**

- product spec §4.2, §4.3, §5, §12, §13.2
- `domains/reward/reward.js`
- `domains/reward/reward_ui.js`
- `domains/reward/free-time-session-start-transaction.js`
- `shared/browser/external-tab-launcher.js` 또는 현재 실제 launcher owner
- `tests/test_youtube_atomic_start_browser.py`
- `tests/test_external_tab_launcher_browser.py`

**실행 원칙**

1. 최신 main에서 기존 browser test가 이미 primary criterion을 정확히 증명하는지 확인한다.
2. 증명되면 새 테스트를 만들지 않고 실제 YouTube manual smoke만 수행한다.
3. 실제 회귀가 재현될 때만 production을 수정한다.
4. popup/network/YouTube 자체 콘텐츠 상태는 AidenGame 로컬 계약과 분리한다.
5. 실패가 다른 invariant라면 즉시 종료하고 별도 카드로 남긴다.

**종료**

`PASS`이면 A-RWD-05B로 이동한다.

---

### A-RWD-05B — background / reload / deadline 보정

**Failure domain**

`YOUTUBE_FREE_TIME_REAL_BROWSER_BACKGROUND_DEADLINE_RECOVERY_UNPROVEN`

**가설**

타이머는 tick 누적이 아니라 persisted deadline을 권위로 사용하므로 background/reload/시간 점프 후에도 현재 시각에 맞춰 남은 시간을 즉시 보정하고, 마감이 지났으면 정확히 한 번 expired로 전환한다.

**Primary criterion**

실제 브라우저에서 running session을 만든 뒤 background/reload 경계를 통과시켰을 때:

- 추가 15분 차감 없음
- 새 session 생성 없음
- 남은 시간 = persisted deadline과 현재 시각의 차이
- deadline 경과 시 status = `expired`
- expiry UI가 1회 활성화
- pageerror / console.error / failed local request 0

**먼저 읽기**

- product spec §6, §8, §11, §13
- `shared/domain/free-time-session.js`
- `domains/reward/reward_ui.js`
- `tests/test_free_time_session_pure_state.mjs`
- `tests/test_youtube_expired_restore_bootstrap.py`
- `tests/test_youtube_warning_expiry_lifecycle.py`

**실행 원칙**

15분을 실제로 기다리는 것을 primary test로 만들지 않는다. production 의미를 바꾸지 않는 기존 clock/storage 경계로 deadline을 가까운 미래에 배치하고 실제 browser background/reload를 검증한다.

**종료**

`PASS`이면 A-RWD-05C로 이동한다.

---

### A-RWD-05C — keyboard / PiP fallback / 경고 접근성

**Failure domain**

`YOUTUBE_FREE_TIME_ACCESSIBLE_BROWSER_CLOSEOUT_UNPROVEN`

**가설**

키보드만으로 시작·만료 확인 흐름을 완료할 수 있고, Document PiP가 없거나 거부되어도 fixed timer/expiry UI로 동일한 세션 상태를 계속 사용할 수 있다.

**Primary criterion**

실제 브라우저 한 journey에서:

- keyboard로 보호자 승인 이후 start control 도달/실행 가능
- PiP unsupported 또는 rejected 경로에서 세션은 유지되고 fixed timer가 표시
- 만료 UI의 acknowledge control을 keyboard로 실행 가능
- acknowledge 후 경고 UI/오디오 lifecycle이 종료
- `prefers-reduced-motion`에서 빠른 섬광/필수 정보 손실 없음
- pageerror / console.error / failed local request 0

**먼저 읽기**

- product spec §7, §8, §12.8-12.12
- `domains/reward/reward_ui.js`
- `tests/test_youtube_pip_timer_ui.py`
- `tests/test_youtube_warning_expiry_lifecycle.py`
- 관련 focus/a11y test가 있으면 그것만 추가로 읽는다.

**주의**

Document Picture-in-Picture 자체 지원 여부를 제품이 강제하지 않는다. API 미지원/거부는 정상 fallback 경로다.

**종료**

`PASS`이면 A-RWD-06로 이동한다.

---

### A-RWD-06 — 제품 스펙 closeout 정합성

**Mode:** documentation-only

**Failure domain**

`YOUTUBE_FREE_TIME_SPEC_IMPLEMENTATION_STATUS_STALE`

**가설**

A-RWD-05A/B/C가 최신 main에서 모두 PASS이면 제품 스펙의 `APPROVED_PRODUCT_CONTRACT_NOT_IMPLEMENTED` 상태만 현실과 불일치한다.

**Primary criterion**

제품 계약의 의미를 바꾸지 않고 status/구현 완료 표현만 현재 증거와 일치시키며, runtime source/test에는 diff가 없다.

이 카드에서는 새 기능을 만들지 않는다. 문서 상태만 정합화한다.

---

## 5. 이후 A 트랙 선택

A-RWD-06까지 닫힌 뒤에는 이 런북에 오래된 후보 목록을 쌓지 않는다.

최신 `origin/main`과 `AGENTS.md`의 A 트랙 정의를 다시 읽고 다음 **실제 RED 또는 증거 공백 하나**를 선택한다.

후보 탐색 순서:

1. 현재 배포에서 사용자 진행을 막는 runtime 회귀
2. reward/runtime의 실제 남은 계약 공백
3. 사용자가 명시적으로 재개한 Ocean Rescue runtime
4. 그 외 A 트랙 runtime/play 영역

Ocean Rescue를 선택하면 asset 생산 문제는 B로 넘기고 runtime loader/renderer/controller/play state만 A에서 다룬다.

---

## 6. 로컬 LLM 카드 형식

프론티어 모델의 별도 프롬프트 없이 런북을 직접 수행해야 할 때는 현재 Active Queue 카드 하나만 읽고 아래 필드를 채운다.

```text
TASK_ID: <A-RWD-...>
MODE: ANALYZE_ONLY_FIRST | MODIFY_AND_VERIFY
FAILURE_DOMAIN: <one>
HYPOTHESIS: <one sentence>
PRIMARY_CRITERION: <one binary observation>

DO
- 최신 origin/main 기준 locked isolated worktree 생성
- 정확한 reproduction/evidence gap 확정
- sibling surface read-only inventory
- 필요할 때만 coherent root-cause-complete 수정
- focused primary verify
- 직접 영향 verify
- 필요한 static verify + git diff --check
- 최신 main 재확인 후 fast-forward publish
- published/clean worktree 회수

DO_NOT
- 다음 Active Queue 카드까지 처리
- 다른 failure domain 수정
- B 트랙 asset production chain 수정
- unrelated refactor/dependency upgrade
- 기존 증거와 같은 테스트를 중복 생성
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

모든 상태 필드는 서로 배타적인 단일 값만 사용한다.

---

## 7. 프론티어 리뷰용 최소 패킷

중간 리뷰 시 전체 로그를 붙이지 않는다.

```text
TASK_ID:
BASE:
HEAD:
RESULT:
FAILURE_DOMAIN:
HYPOTHESIS:
PRIMARY_CRITERION:
CHANGED_FILES:
PRIMARY_VERIFY: <command + result>
DIRECT_VERIFY: <command + result>
STATIC_VERIFY: <command + result>
DISCOVERED_FAILURE:
BLOCKER:
```

리뷰에서 구멍이 확인되면 전체 작업을 다시 시키지 않고 **그 구멍 하나만 delta prompt**로 보완한다.

---

## 8. 런북 유지 규칙

이 파일은 history log가 아니다.

- 완료된 카드는 다음 갱신 때 삭제한다.
- 오래된 commit 목록, PASS 횟수, 실행 로그를 누적하지 않는다.
- 다음 세션이 필요한 current cut line과 active queue만 유지한다.
- 새 failure domain이 생기지 않았으면 단지 최신 SHA를 기록하려고 문서를 수정하지 않는다.
