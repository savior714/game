# 그물망 DOM·타이밍 점검 실행서

**최초 작성**: 2026-03-27 · **최종 수정**: 2026-03-29  

구현 SSOT: `common/rocket-core.js` (`netBounceRocket`, `spawnNetEffect`). 상태 규칙 SSOT: `docs/CRITICAL_LOGIC.md` §7.  
플래시·연기 등은 `common/rocket-effects.js`에서 호출된다.

---

## 1) 전 과목 상태 전이 (요약)

대상: `korean/math/english/science/engine.js`의 `recordResult` 및 `common/rocket-core.js`의 `updateStreak` → `crashRocket` 경로.

공통 상태:

- `netStreak`: 그물 **획득**용 연속 정답 카운트
- `hasNet`: 그물 보유(불리언)
- `streak`: 로켓 **발사**용 연속 정답 카운트

상태 전이(요지):

1. 정답 `recordResult(true, elapsed)` → `netStreak++` → `netStreak >= NET_STREAK(5)` 이고 `!hasNet`이면 `hasNet = true`, `netStreak = 0`, `showNetBanner()`.
2. 오답 `recordResult(false, …)` → `netStreak = 0` → 이후 `crashRocket()`에서 그물 소모 또는 일반 추락.
3. `crashRocket()`에서 `hasNet === true`이면 `hasNet = false`, `netBounceRocket()` (그물 발동).

판정: 논리적으로 **동시에 그물 2중 보유는 없음**. 점검 초점은 **DOM `.net-element`가 한 번에 하나만 보이는지**와 애니메이션 타이밍이다.

---

## 2) 수동 재현 매트릭스 (reproduce-matrix)

시나리오:

- **A**: 5연속 정답 → 오답 1회로 그물 발동 → 즉시 추가 입력
- **B**: 그물 발동 애니메이션 중 추가 입력
- **C**: 과목 전환 후 동일 절차

체크 항목:

- 상태: `hasNet`, `netStreak`, `streak`
- DOM: `#rp-track` 안 `.net-element` 동시 개수
- 체감: 그물이 겹쳐 보이는지(발동 직후·복귀 전후)

기록 템플릿:

| 과목 | 시나리오 | 재현 여부 | 상태 이상 | DOM 중첩 | 비고 |
|------|----------|-----------|-----------|----------|------|
| korean | A/B/C | Y/N | Y/N | Y/N | |
| math | A/B/C | Y/N | Y/N | Y/N | |
| english | A/B/C | Y/N | Y/N | Y/N | |
| science | A/B/C | Y/N | Y/N | Y/N | |

---

## 3) DOM/타이밍 (현행 구현 기준)

`netBounceRocket()` (`common/rocket-core.js`):

- 약 **950ms** 후 `spawnNetEffect(track, netBottomPx)` 및 로켓 복귀 준비.
- 그 안의 `setTimeout` 체인으로 복귀 애니메이션 후 약 **900ms** 뒤 `showNetActivatedBanner()`.

`spawnNetEffect()`:

- **선제 정리**: 새 그물을 붙이기 전에 `track.querySelectorAll(".net-element").forEach(el => el.remove())`로 기존 노드를 제거한다 → **동시에 2개 `.net-element`가 남는 경우를 구조적으로 억제**.
- 생성된 요소는 약 **1800ms** 후 `remove()`.

중첩 관찰이 필요한 구간: 위 선제 제거 이전에 예외 경로로 `spawnNetEffect`가 두 번 호출되는지(과거 이슈 후보). 회귀 시 DevTools에서 `.net-element` 개수를 본다.

---

## 4) 브라우저 콘솔 관찰 스니펫

```js
(() => {
  const track = document.getElementById("rp-track");
  if (!track) return console.warn("rp-track not found");
  const sample = () => {
    const nets = track.querySelectorAll(".net-element").length;
    console.log("[net-snapshot]", { t: Date.now(), nets });
  };
  window.__netWatch = setInterval(sample, 120);
  console.log("net watch started: clearInterval(window.__netWatch)");
})();
```

---

## 5) 원인 분류·수정 우선순위·회귀 기준

우선순위:

1. **상태 불일치(치명)**: `hasNet`과 연출 불일치.
2. **DOM 정리 지연**: `.net-element` 동시 2개 이상(현재는 `spawnNetEffect` 선제 제거로 완화됨).
3. **체감 중첩**: 논리는 정상이나 애니메이션·배너 타이밍이 겹쳐 보이는 경우.

회귀 기준:

- 5연속 획득 후 오답 시 상태 전이가 전 과목 동일.
- `.net-element` 최대 동시 개수 ≤ 1(정상 경로).
- A/B/C 시나리오에서 과목별 편차 없음.

자동 검증: `node verify_net_logic.js`, `node verify_all.js`.
