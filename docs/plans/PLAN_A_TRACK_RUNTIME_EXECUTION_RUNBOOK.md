# A 트랙 런타임·플레이 — Rolling Runbook

- **상태:** ACTIVE — Game-state presentation evidence audit
- **갱신:** 2026-08-08 KST
- **기본 기준:** 실행 시점의 최신 `origin/main` (실행 환경이 workspace/ref를 지정하면 해당 경계 우선)
- **범위:** player-facing runtime/play. Asset source/schema/generator/atlas/provenance는 B 소유다.

이 문서는 history/changelog가 아니라 **rolling working set**이다. 완료 이력은 Git history와 현재 코드·테스트가 소유한다.

## 1. Cut line

아래 cut-line 항목은 이 runbook에서 자동으로 다시 열지 않는다. 이는 Ocean Rescue feature 전체의 동결 선언이 아니다. 명시적 사용자 요청은 별도 bounded task를 선택할 수 있으며, 요청이 없는 경우에만 같은 결함이 할당된 workspace/ref (별도 지정이 없으면 최신 main)에서 재현될 때 재개한다.

- Quiz launcher / YouTube fallback 안정화
- Ocean Rescue authored Kid / Sea Turtle / Seaweed 런타임 소비와 현재 macOS app 조립
- DPR 1, 1.5, 2 production pointer-input.js mapping acceptance evidence (2c2ca83)

기존 Ocean Rescue browser baseline은 profile → mission select → GUP → launch → travel → pause/resume → Sea Turtle rescue를 이미 관통한다. 같은 의미의 smoke/evidence test를 추가하지 않는다.

## 2. ACTIVE — Game-state presentation evidence audit

**Failure domain**  
Sea Turtle rescue 미션에서 required state transitions (IDLE → APPROACH → RECOVERY / SUCCESS / FAILURE) 및 visual state distinction에 관한 실제 runtime presentation evidence가 부족하거나 누락된 지점을 확정하고 닫는다.

**Current evidence**
- `sea-turtle-scene.js` 및 `sea-turtle.js`는 상태 전이와 연출(feedback / success / failure) 인터페이스를 소유한다.
- unit level / controller scaffold 테스트는 구조 계약을 확인하지만, 실제 runtime presentation 및 state transition visual distinction이 통과하는지 검증하는 focused acceptance harness 증거를 확장할 필요가 있다.

**Hypothesis**  
Sea Turtle rescue 미션의 상태 전이 및 visual feedback distinction을 단일 focused runtime acceptance test로 고정함으로써 런타임 플레이 딜리버리 신뢰성을 확증할 수 있다.

**Primary criterion**  
Sea Turtle 미션의 주요 state transition(상태 전이 및 feedback presentation)이 production runtime 코드 경로를 통과하여 올바른 visual state distinction 상태를 반환하면 PASS.

**Do first — read only**
1. `sea-turtle-scene.js` 및 `sea-turtle.js`의 상태 전이 메서드와 visual feedback presentation 소유자를 읽는다.
2. 현재 `tests/` 아래에서 Sea Turtle state presentation 관련 테스트의 커버리지 공백을 확인한다.

**Authorized change boundary**
- 우선: 기존 sea turtle test / harness 또는 신규 focused runtime acceptance test.
- production state presentation logic은 실제 결함 증명 시에만 수정한다.

**Verification**
- V0: state presentation evidence gap 고정
- V1 PRIMARY: Sea Turtle state transition 및 visual distinction acceptance 하나만 판정
- V2 DIRECT: 수정한 harness/owner의 직접 영향 surface 확인

**Stop condition**  
첫 presentation mismatch 발견 시 그 defect 하나로 가설을 축소한다.

## 3. NEXT — ACTIVE 종료 후에만

1. **Fallback acceptance evidence audit** — Canvas fallback의 complete playable rescue flow와 visible-placeholder 금지 계약 중 실제 증거 공백 하나만 승격한다.


NEXT는 backlog 구현 지시가 아니다. 할당된 workspace/ref (별도 지정이 없으면 최신 main)에 이미 충분한 evidence가 있으면 삭제한다.

## 4. 실행 계약

- **한 작업 = 한 failure domain = 한 검증 가능한 가설 = 한 primary criterion**
- 수정 전 exact reproduction 또는 exact evidence gap을 확정한다.
- shared owner/sibling surface는 read-only inventory로 under-fix만 방지한다.
- 같은 root cause + invariant + ownership/rollback boundary만 minimum coherent change로 함께 닫는다.
- 다른 root cause는 `DISCOVERED_FAILURE`로 분리한다.
- Broad/full suite는 primary criterion으로 쓰지 않는다.
- 필수 검증 범위와 판정은 `agents/core/verification.md`, 위험 기반 전략과 fidelity는 `agents/RISK_DIRECTED_VERIFICATION.md`를 따른다.

## 5. 로컬 LLM 출력 계약

```text
RESULT: PASS | BLOCKED
CHANGE: <short summary or 변경 없음>
PRIMARY_VERIFY: PASS | FAIL | NOT_RUN
DIRECT_VERIFY: PASS | FAIL | NOT_RUN
PUBLISH: PUBLISHED | NOT_APPLICABLE | BLOCKED
DISCOVERED_FAILURE: <independent failure domain or NONE>
COMMIT: <only when published>
BLOCKER: <only when blocked>
NEXT: <only when blocked>
```

최종 상태와 게시 의미는 `agents/core/reporting.md`가 소유한다. 검증이 실패했지만 안전하게 계속 수정할 수
있다면 완료/중단 보고를 내기 전에 task를 계속 닫고, 필수 기준을 안전하게 충족할 수 없을 때만 `BLOCKED`로 보고한다.

## 6. 유지 규칙

- 완료된 ACTIVE 상세는 다음 갱신 때 삭제한다.
- 완료 RED/GREEN 로그, 반복 PASS 횟수, 과거 prompt, 오래된 SHA, 해결된 blocker를 누적하지 않는다.
- 평상시에는 **cut line + ACTIVE 최대 1개 + NEXT 최대 2개**만 유지한다.
- 실제 backlog/evidence gap이 없으면 ACTIVE/NEXT를 억지로 채우지 않는다.
