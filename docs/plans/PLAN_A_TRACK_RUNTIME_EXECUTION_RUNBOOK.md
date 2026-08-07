# A 트랙 런타임·플레이 — Rolling Runbook

- **상태:** ACTIVE — DPR input alignment runtime evidence
- **갱신:** 2026-08-08 KST
- **기준:** 실행 시점의 최신 `origin/main`
- **범위:** player-facing runtime/play. Asset source/schema/generator/atlas/provenance는 B 소유다.

이 문서는 history/changelog가 아니라 **rolling working set**이다. 완료 이력은 Git history와 현재 코드·테스트가 소유한다.

## 1. Cut line

재개하지 않는다. 구체적 회귀가 최신 main에서 재현될 때만 새 카드로 연다.

- Quiz launcher / YouTube fallback 안정화
- Ocean Rescue authored Kid / Sea Turtle / Seaweed 런타임 소비와 현재 macOS app 조립

기존 Ocean Rescue browser baseline은 profile → mission select → GUP → launch → travel → pause/resume → Sea Turtle rescue를 이미 관통한다. 같은 의미의 smoke/evidence test를 추가하지 않는다.

## 2. ACTIVE — DPR input alignment runtime evidence

**Failure domain**  
Ocean Rescue의 실제 runtime pointer mapping이 DPR `1`, `1.5`, `2`에서 정렬된다는 acceptance evidence가 production path에 연결되어 있지 않다.

**Current evidence**
- Rendering MVP Phase E는 DPR `1`, `1.5`, `2` hit alignment를 요구한다.
- Acceptance criteria는 supported scaling/DPR에서 pointer alignment와 1280×720 logical coordinates 유지를 요구한다.
- `tests/ocean-rescue/rendering-acceptance/coordinates/test_coordinates.py`는 production code를 import하지 않고 `mapRescueCoordinates` 수식을 Python으로 다시 구현해 fixture와 비교한다.

**Hypothesis**  
현재 fixture/formula test는 수학 계약은 검증하지만, 최신 Ocean Rescue runtime의 실제 pointer-mapping owner가 같은 계약을 소비하는지는 판정하지 못한다.

**Primary criterion**  
고정된 representative browser-pointer samples가 **실제 최신 runtime mapping path**를 통과했을 때 DPR `1`, `1.5`, `2` 각각에서 기존 fixture의 expected logical coordinates를 기존 tolerance 안에서 모두 만족하면 PASS.

**Do first — read only**
1. 최신 runtime에서 pointer/client coordinates → 1280×720 logical coordinates를 소유하는 production owner와 직접 caller를 찾는다.
2. resize/letterbox/DPR 값을 같은 mapping에 공급하는 sibling surface만 inventory한다.
3. 기존 browser/runtime harness 중 해당 owner를 실제 실행할 수 있는 가장 가까운 것을 찾는다.

**Authorized change boundary**
- 우선: 기존 coordinate acceptance test/fixture 또는 가장 가까운 runtime/browser acceptance harness.
- production mapping은 runtime reproducer가 실제 결함을 증명할 때만 같은 카드에서 수정한다.
- scene asset, animation, fallback renderer, packaging, quiz, B 생산 체인은 수정하지 않는다.

**Verification**
- V0: 현재 pure-formula test가 production path를 실행하지 않는 증거를 고정한다.
- V1 PRIMARY: DPR `1`, `1.5`, `2` runtime mapping acceptance 하나만 판정한다.
- V2 DIRECT: 수정한 harness/owner의 직접 영향 surface만 확인한다.
- `git diff --check` 및 수정 파일 static diagnostics를 통과한다.
- shipped assembly를 건드렸을 때만 build/exact-app probe를 추가한다.

**Stop condition**  
첫 runtime mismatch가 나오면 evidence-gap 작업을 계속 넓히지 말고, 그 mismatch의 mapping defect 하나로 hypothesis를 다시 좁힌다.

## 3. NEXT — ACTIVE 종료 후에만

1. **Game-state presentation evidence audit** — sea-otter/turtle의 required state transitions와 success/failure visual distinction 중 실제 runtime evidence가 없는 항목 하나만 승격한다.
2. **Fallback acceptance evidence audit** — Canvas fallback의 complete playable rescue flow와 visible-placeholder 금지 계약 중 실제 증거 공백 하나만 승격한다.

NEXT는 backlog 구현 지시가 아니다. 최신 main에 이미 충분한 evidence가 있으면 삭제한다.

## 4. 실행 계약

- **한 작업 = 한 failure domain = 한 검증 가능한 가설 = 한 primary criterion**
- 수정 전 exact reproduction 또는 exact evidence gap을 확정한다.
- shared owner/sibling surface는 read-only inventory로 under-fix만 방지한다.
- 같은 root cause + invariant + ownership/rollback boundary만 minimum coherent change로 함께 닫는다.
- 다른 root cause는 `DISCOVERED_FAILURE`로 분리한다.
- Broad/full suite는 primary criterion으로 쓰지 않는다.
- verification은 `AGENTS.md`의 Risk-Directed Verification을 따른다.

## 5. 로컬 LLM 출력 계약

```text
RESULT: PASS | FAIL | BLOCKED
FAILURE_DOMAIN: <one>
HYPOTHESIS: <one sentence>
PRIMARY_VERIFY: PASS | FAIL | NOT_RUN
DIRECT_VERIFY: PASS | FAIL | NOT_RUN
STATIC_VERIFY: PASS | FAIL | NOT_RUN
CHANGE: <summary | NONE>
DISCOVERED_FAILURE: <NONE | one out-of-scope failure>
PUBLISH: PUBLISHED | NOT_PUBLISHED | NOT_APPLICABLE
COMMIT: <sha | NONE>
BLOCKER: <NONE | exact blocker>
```

## 6. 유지 규칙

- 완료된 ACTIVE 상세는 다음 갱신 때 삭제한다.
- 완료 RED/GREEN 로그, 반복 PASS 횟수, 과거 prompt, 오래된 SHA, 해결된 blocker를 누적하지 않는다.
- 평상시에는 **cut line + ACTIVE 최대 1개 + NEXT 최대 2개**만 유지한다.
- 실제 backlog/evidence gap이 없으면 ACTIVE/NEXT를 억지로 채우지 않는다.
