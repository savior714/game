# A 트랙 런타임·플레이 — Rolling Runbook

- **상태:** READY — 확인된 A backlog 없음; 실제 RED/증거 공백이 생길 때만 ACTIVE를 연다.
- **갱신:** 2026-08-08 KST
- **기준:** 실행 시점의 최신 `origin/main`
- **범위:** player-facing runtime/play. Asset source/schema/generator/atlas/provenance는 B 소유다.

이 문서는 history/changelog가 아니라 **rolling working set**이다. 완료 이력의 SSOT는 Git history와 최신 코드·테스트·브라우저 증거다.

## 1. Current cut line

최신 main에서 닫혀 있으므로 backlog에서 제거한다.

- Core Quiz stabilization exit gate
- YouTube 15분 자유시간 세션 제품 계약
- Ocean Rescue Sea Turtle의 `scene.seaweed-loop.01/.02/.03` 런타임 소비

Ocean Rescue의 기존 browser baseline은 진입 smoke가 아니라 profile → mission select → GUP → launch → travel → pause/resume → Sea Turtle rescue를 관통한다. 동일 의미의 새 smoke/evidence test를 만들지 않는다.

위 항목은 **최신 main에서 구체적 회귀가 재현될 때만** 새 failure domain으로 다시 연다.

## 2. 시작 시 읽기 예산

1. `AGENTS.md`
2. 이 런북
3. 현재 failure domain의 가장 가까운 spec 1개
4. production owner + 직접 caller + 가장 가까운 focused/browser test
5. 같은 invariant를 소비하는 sibling surface만 read-only inventory

필요할 때만 `docs/specs/OCEAN_RESCUE_FREEZE_NOTICE.md`를 읽는다. 완료된 quiz/YouTube/Ocean Rescue 생산 이력, B art pipeline 전체, unrelated dependency/toolchain 문서는 읽지 않는다.

## 3. ACTIVE 개방 조건

현재 ACTIVE 카드: **NONE**.

다음 중 하나가 최신 main에서 확인될 때만 카드 하나를 연다.

1. 사용자의 진행을 막는 runtime 회귀가 exact reproduction으로 확인됨
2. 현재 vertical slice의 명시적 runtime contract가 실제 코드/테스트와 불일치함
3. B에서 승인·게시된 asset 계약을 A runtime이 소비하지 못함
4. 기존 증거가 현재 contract를 판정하지 못하는 **구체적인 evidence gap**이 있음

단순히 오래된 WP/TODO가 보이거나, broad suite가 다른 failure를 발견했거나, 최신 SHA가 이동했다는 이유로 backlog를 만들지 않는다.

## 4. 한 카드의 실행 계약

- **한 작업 = 한 failure domain = 한 검증 가능한 가설 = 한 primary criterion**
- 수정 전 exact reproduction 또는 exact evidence gap을 확정한다.
- shared owner/sibling surface를 read-only로 확인해 under-fix를 막는다.
- 같은 root cause + invariant + ownership/rollback boundary는 minimum coherent change로 함께 닫는다.
- 다른 root cause는 `DISCOVERED_FAILURE`로 분리한다.
- A에서는 B 생산 체인을 수정하지 않는다.

### Risk-Directed Verification

- **V0 BASELINE:** 현재 실패/증거 공백을 정확히 고정
- **V1 PRIMARY:** 단일 primary criterion 판정
- **V2 DIRECT:** 변경 owner와 직접 영향 surface만 회귀 확인
- **V3 SYSTEM_SMOKE:** 독립 failure discovery. 여기서 unrelated failure가 나와도 V1/V2 PASS를 뒤집지 않는다.
- **V4 RELEASE:** 명시적 release candidate일 때만 수행

visual/game-feel 탐색은 implementation-first + browser verify가 가능하다. Progress/state/input exactly-once, 저장/복구, 보안·무결성 성격은 test-first 또는 동시 회귀 테스트를 우선한다. Broad/full suite를 primary criterion으로 쓰지 않는다.

## 5. 다음 카드 선택 순서

ACTIVE가 비어 있을 때만 아래 순서로 **실제 RED/증거 공백 하나**를 고른다.

1. 사용자 진행 차단 runtime 회귀
2. 현재 vertical slice의 직접 contract 위반
3. 승인된 B asset의 A 소비 누락
4. 그 외 runtime/play 품질

Ocean Rescue가 pause 상태여도 사용자가 A 트랙 작업을 명시적으로 재개한 범위에서는 최신 runtime/config를 먼저 대조한다. 새로운 mission/mechanic/asset 생산을 과거 WP에서 자동 부활시키지 않는다.

## 6. 로컬 LLM 카드 템플릿

```text
TASK_ID: <one>
MODE: VERIFY_ONLY_FIRST | MODIFY_AND_VERIFY
FAILURE_DOMAIN: <one>
HYPOTHESIS: <one sentence>
PRIMARY_CRITERION: <one binary observation>

DO
- exact reproduction/evidence gap 확정
- shared owner + sibling surface read-only inventory
- 필요한 경우에만 root-cause-complete coherent change
- V1 primary → V2 direct → 필요한 static verify
- git diff --check
- latest main 재확인 후 fast-forward publish

DO_NOT
- 다음 카드까지 처리
- 다른 failure domain 수정
- B 생산 체인 수정
- unrelated refactor/dependency upgrade
- 이미 충분한 기존 증거를 중복 생성
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

## 7. 유지 규칙

- 완료 카드는 다음 갱신 때 삭제한다.
- 완료 RED/GREEN 로그, 반복 PASS 횟수, 과거 prompt, 오래된 SHA, 해결된 blocker를 누적하지 않는다.
- 평상시에는 **cut line + ACTIVE 최대 1개 + NEXT 최대 2개**만 유지한다.
- 실제 backlog가 없으면 ACTIVE/NEXT를 억지로 채우지 않는다.