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
- 미검증: 3번 실패 경로(잘못된 로프 3회 → `data-rescue-input="disabled"` 복구), 5번 bridge 실패 경로, 구조 중 창 크기 변경, 멀티터치.

## 3.사용자 side recovery

- 구조 중 조작 불응 → **일시정지 버튼**으로 pause → **메뉴 나가기**
- scene failure 메시지 표시 시 → **canvas 탭**하면 자동으로 메뉴로 이동 (Fix 3)
- replay 시 입력 안 됨 → `seaTurtleInputBound` 초기화 적용됨 (Fix 1)

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
