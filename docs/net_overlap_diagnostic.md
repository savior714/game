# 그물 중첩 현상 점검 실행서

## 1) 전 과목 상태 전이표 (map-state-flow)

대상 파일
- `korean/engine.js`
- `math/engine.js`
- `english/engine.js`
- `science/engine.js`
- `common/rocket-core.js`

공통 상태
- `netStreak`: 연속 정답 카운트
- `hasNet`: 그물 보유 여부(불리언)
- `streak`: 로켓 연속 정답 카운트

상태 전이
1. 정답 처리 (`recordResult(true, elapsed)`)
   - `netStreak++`
   - `netStreak >= NET_STREAK(5)` and `!hasNet`이면:
     - `hasNet = true`
     - `netStreak = 0`
     - `showNetBanner()`
2. 오답 처리 (`recordResult(false, elapsed)`)
   - `netStreak = 0`
   - 이후 `updateStreak(false)` 경로에서 `crashRocket()` 호출
3. 그물 발동 (`crashRocket()`)
   - `hasNet`이 `true`이면 즉시:
     - `hasNet = false`
     - `netStreak = 0`
     - `netBounceRocket()` 실행

판정
- 논리 상태 기준으로는 동시 2개 그물 보유가 불가능합니다.
- 현재 기준에서 체크 대상은 DOM 이펙트(`.net-element`) 단일성입니다.

## 2) 수동 재현 매트릭스 (reproduce-matrix)

시나리오 정의
- A: 5연속 정답 -> 1회 오답으로 그물 발동 -> 즉시 추가 입력 반복
- B: 그물 발동 애니메이션(복귀 전후) 중 추가 입력 시도
- C: 과목 전환 후 동일 절차 반복

체크 항목
- 상태: `hasNet`, `netStreak`, `streak`
- DOM: `.net-element` 동시 개수
- 체감: 그물이 2개처럼 보이는 시점(발동 직후/복귀 직전/복귀 직후)

기록 템플릿

| 과목 | 시나리오 | 재현 여부 | 상태 이상 | DOM 중첩 | 비고 |
|---|---|---|---|---|---|
| korean | A/B/C | Y/N | Y/N | Y/N | |
| math | A/B/C | Y/N | Y/N | Y/N | |
| english | A/B/C | Y/N | Y/N | Y/N | |
| science | A/B/C | Y/N | Y/N | Y/N | |

## 3) DOM/타이밍 점검 포인트 (dom-timing-check)

핵심 타이밍
- `netBounceRocket()` 내부:
  - 약 `950ms` 후 `spawnNetEffect(track, netBottomPx)` 호출
  - 이후 `350ms` 후 복귀 애니메이션 시작
  - 복귀 시작 `900ms` 후 `showNetActivatedBanner()`
- `spawnNetEffect()` 내부:
  - `.net-element` 생성 후 `1800ms` 뒤 제거

중첩 가능 구간
- 기존 `.net-element` 제거 전 새 발동이 트리거되는 경우가 핵심 관찰 포인트입니다.

브라우저 콘솔 관찰 스니펫
```js
(() => {
  const track = document.getElementById("rp-track");
  if (!track) return console.warn("rp-track not found");
  const sample = () => {
    const nets = track.querySelectorAll(".net-element").length;
    console.log("[net-snapshot]", {
      t: Date.now(),
      nets,
    });
  };
  window.__netWatch = setInterval(sample, 120);
  console.log("net watch started: clearInterval(window.__netWatch)");
})();
```

## 4) 원인 분류별 수정 우선순위와 회귀 기준 (define-fix-criteria)

우선순위
1. 상태 불일치(치명)
   - `hasNet`이 false인데 그물 발동 연출이 실행되거나, 반대로 true인데 미실행
2. DOM 정리 지연(중간)
   - `.net-element` 동시 2개 이상 생성/잔존
3. 체감 중첩(경미)
   - 논리 정상이나 `.net-element` 시각 연출 타이밍이 겹쳐 오해 유발

수정 기준
- 상태 불일치: 즉시 수정, 공용 코어 우선
- DOM 정리 지연: 이펙트 생성 시 기존 `.net-element` 선제 제거 또는 싱글톤화
- 체감 중첩: `.net-element` 생명주기/선제 제거 타이밍 조정

회귀 테스트 기준(전 과목 공통)
- 5연속 획득 후 오답 발동 시 상태 전이 동일
- `.net-element` 최대 동시 개수 <= 1
- A/B/C 시나리오에서 과목별 동작 편차 없음
