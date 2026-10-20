# Ocean Rescue — 구조 동작 시 조작 불응 Troubleshooting

## 1. 증상

구조 미션 중(canvas 위 drag/tap) 입력이 반응하지 않음.
- 드래그 중 touch move 이벤트가 drop되어 rope/rock/debris가 따라가지 않음
- pointer capture가 해제되지 않아 그 후 모든 pointer event가 무시됨
- scene failure 후 `data-rescue-input="disabled"`가 설정되어 입력 전체 정지
- replay 시 pointer listener가 바인딩 안 됨

## 2.원인·해결 (코드 수정 완료)

| # | 증상 원인|수정 위치|
|---|---------|--------|
| 1|`seaTurtleInputBound` 재바인딩 안됨 — shutdown 후 replay 시 listener 누락|`shutdownRescueInteractionState()`: `seaTurtleInputBound = false` 추가|
| 2|Crab hold timer pointer cancel 시 안 Clears — stale timer 발화|`onRescuePointerCancel`: `clearCrabHoldTimer()`를 null check **이전**으로 이동|
| 3|scene failure 시 `data-rescue-input="disabled"` 영구锁定 — recovery 불가|`onRescueStagePointerDown`: failure flag 감지 시 `exitPauseToMenu()`로 recovery|
| 4|pause → menu exit 시 pointer capture 누수|`exitPauseToMenu()`: `cancelPausePointerInteractions()` 추가|
| 5|bridge 실패 시 fallback/input path 없음 |`startSeaTurtleInteraction()`: bridge catch → legacy bind fallback + status message|
| 6|ESM pause 종료(`exitPauseToMenu`)가 rescue 시퀀스를 해제하지 않음 — 다음 구조 도착의 `handoffTravelArrival`이 stale 시퀀스에 막혀 TRAVEL 단계에 머묾|`pause-timer-resume.ts` `exitPauseToMenu()`: RESCUE_SUCCESS / SITE_TRANSITION / TUTORIAL / ACTIVE 분기에서 `cancelRescueSiteRuntime()`을 `shutdownActiveRescueForMenu()` 앞에 호출|
| 7|미션 성공 화면에서 pause → 메뉴 시 `controller`와 `host`가 같은 객체라 자기 참조 wrapper가 무한 재귀 (`Maximum call stack size exceeded`), RESCUE_SUCCESS에 머묾|`pause-timer-resume.ts`: `controller.cancelMissionSuccessPresentationForMenu` 자기 참조 wrapper 제거|

## 2-1. 검증 현황 (2026-10-19)

- 1–5: 코드 존재 확인 완료 (`app.js` `shutdownRescueInteractionState`, `onRescuePointerCancel`, `onRescueStagePointerDown`, legacy `exitPauseToMenu`, `startSeaTurtleInteraction`). ESM 경로는 pause 진입 시 `cancelPausePointerInteractions()`를 호출한다 (`pause-timer-resume.ts`).
- 6–7: 실제 Chromium 브라우저 회귀 테스트 `tests/test_ocean_rescue_pause_menu_rescue_reentry_browser.py`로 고정. 수정 전 아티팩트에서 4건 모두 실패, 수정 후 4건 모두 통과.
- 이후 검증(2026-10-20): 아래 `2-2` 절의 수정을 `tests/test_ocean_rescue_rescue_input_recovery_browser.py`(11개, 실제 Chromium)로 고정. 이 중 4개(캡처 손실, 브라우저 bridge 실패, 재생 후 진행, 게 캡처 손실)는 수정 전 아티팩트(`da57db4`)에서 실패, 수정 후 통과. 나머지 7개는 이미 동작하던 경로의 회귀 가드.
- 검증 완료: 잘못된 로프 3회 후 입력 유지, 구조 중 창 크기 변경, 멀티터치(두 번째 손가락이 제스처를 빼앗지 않음), 전환(SITE_TRANSITION) 중 탭 무시, 일시정지 중 드래그 후 재개, 게 pointer cancel 시 hold/grab 해제.

## 2-2. 2026-10-20 추가 수정

| # | 증상 원인 | 수정 위치 |
|---|-----------|-----------|
| 8 | 드래그 중 pointer capture가 pointerup 전에 풀리면(`lostpointercapture`) 컨트롤러의 `activePointerId`가 남아 다음 정상 드래그가 거부되고, 끊긴 제스처가 로프 실패로 집계됨 | `app.js` `onRescuePointerLostCapture`, `sea-turtle-lifecycle.ts` 소유권 검사 `isOwnedSeaTurtlePointer` |
| 9 | 브리지(`startSeaTurtleSession`)가 false를 반환해도 "Rescue controls ready"와 `data-rescue-input="enabled"`가 표시되어 모든 드래그가 무시됨 | `rescue-site-tutorial.ts` 튜토리얼 완료 시 시작 결과 확인 → `markRescueSceneFailure`. 레거시 폴백은 컨트롤러가 설치되어 있으면 건너뜀 |
| 10 | 장면 실패 후 탭 복구가 ACTIVE 단계에서만 동작하고 일시정지가 필요했음. 실패 마커(`data-sea-turtle-scene-failure`, `data-crab-scene-failure`, `data-rescue-scene-failure`)가 다음 구조까지 남아 첫 탭에 바로 메뉴로 나감 | `rescue-site-tutorial.ts` `handleRescueStagePointerDown`(TRANSITION/ACTIVE 복구), `abandonRescueToMenu()`, `clearSceneFailureMarkers()` |
| 11 | 재생(`#ocean-rescue-mission-complete-replay`) 시 `data-rescue-sequence="active"`가 남음. 구조 도착 판정 자체는 정상이나 DOM 마커가 실제 상태와 어긋남 | `app.js` `onMissionCompleteReplayClick`에서 마커 제거 |
| 12 | `shutdownRescueInteractionState`에 `CrabScene.exit()` 중복 블록 | `app.js` 중복 제거 (동작 변화 없음) |
| 13 | `SeaTurtle` 캔버스 리스너에 `lostpointercapture`가 추가되어 리스너 계약 테스트 3개가 갱신 필요 | 계약 테스트 갱신 (`test_ocean_rescue_sea_turtle_interaction`, `crab_interaction`, `young_whale_interaction`) |
| 14 | 타입 오류 `collisionActive` 누락 (`runtime-abi.ts`); `wp32a` 엄격 타입 검사 실패 | `runtime-abi.ts` `TerrainSnapshot.collisionActive` 추가 |

**설계 질문 (미결정, 코드 변경 없음)**: 재생 경로(레거시 여행 루프)는 도착 전에 "그물 살펴보기" 스캔(`#ocean-rescue-travel-scan`) 완료(`readyForRescue`)를 요구합니다. 첫 실행 경로(컨트롤러 여행 루프, `rescue-site-tutorial.ts` `handoffTravelArrival`)는 이 조건을 확인하지 않습니다. 같은 미션이 실행 경로에 따라 다르게 도착합니다. 스캔을 필수로 할지 결정이 필요합니다.

**테스트 계약 변경**: `test_ocean_rescue_rescue_site_tutorial.py` 3개는 상호작용 모듈을 로드하지 않은 채 튜토리얼 완료 후 "준비 완료"를 기대했습니다. 이는 시작되지 않은 장면을 준비된 것으로 보던 기대이므로, 입력 `disabled`와 장면 실패 문구를 기대하도록 갱신했습니다.

## 3.사용자 side recovery

- 구조 중 조작 불응 → **일시정지 버튼**으로 pause → **메뉴 나가기**
- scene failure 메시지 표시 시 → **canvas 탭**하면 자동으로 메뉴로 이동 (Fix 3)
- replay 시 입력 안 됨 → `seaTurtleInputBound` 초기화 적용됨 (Fix 1)
- 구조 시작 실패 메시지 → 캔버스를 한 번 탭하면 메뉴로 이동 (Fix 3, 2-2 절 10번)

## 4.디버깅 checklist

```
1. ocean-rescue-root data-rescue-input attribute 확인
   → "disabled"이면 input 차단 상태

2. ocean-rescue-root data-sea-turtle-scene-failure / data-crab-scene-failure
   → "true"이면 scene failure 상태

3. browser console: pointer event log
   → pointerdown/move/up이 fire되는지, isPrimary/false 여부

4. pointer capture 상태
   → document.hasPointerCapture(el) — true이면 capture锁定 중
```

## 5.재발 방지

- `shutdownRescueInteractionState()` 호출 시 모든 pointer ID/capture/input flag 초기화 필수
- `bindRescuePointerInput()`은 exactly-once flag(`seaTurtleInputBound`)로 중복 바인딩 방지 + shutdown 시 reset
- pointer cancel/capture lost 시 `clearCrabHoldTimer()`를 **항상** 먼저 실행
- scene failure 시 input disable 대신 phase-based blocking + recovery path 제공
- 구조 종료 경로(pause → 메뉴)는 `cancelRescueSiteRuntime()` → `shutdownActiveRescueForMenu()` 순서를 유지한다. 시퀀스와 타이머를 정리하지 않으면 다음 도착이 조용히 막힌다.
- 컨트롤러 host 브리지에 같은 객체를 자기 자신에게 다시 연결하는 wrapper를 두지 않는다 (`controller === host`인 경우 무한 재귀).
