# Memory SSOT

## Current Context
- **Korean Game Implementation (2026-03-26)**:
    - 6-file modular architecture (index/base/rocket/engine/rocket/ui).
    - 3 categories (spelling, antonym, honorific) with Lv 0-2 difficulty.
    - Integrated Rocket-Streak (20-streak launch) and Marble-Reward systems.
- **Game Difficulty Expansion (2026-03-26)**:
    - Expanded max difficulty from Master (Lv 2) to Transcendence (초월, Lv 3) and Divine (신, Lv 4) across `math`, `korean`, `english`.
    - `math`: Increased number ranges and multiplication factors up to 19x.
    - `korean`: Added strict spacing, typos, exact honorific exceptions, and abstract antonyms for Lv 3-4.
    - `english`: Provided longer terminology (e.g., rhinoceros, esophagus) and increased spelling problem ratios.
- Completed Marble Game improvements.
- **Statistics Labeling Redesign (2026-03-26)**:
    - Renamed 'Difficulty' (난이도) to 'Proficiency' (숙련도) in the stats table.
    - Rebranded 'Hard' (어려움) to 'Master' (마스터) for achievement-oriented UX.
    - Updated colors (Intermediate: Blue, Master: Gold).
    - Synced changes across `math`, `english`, `korean` games and `platform.md`.

## Design Decisions
- **Preview Hiding**: Hidden when ANY marble is in the top zone to avoid overlapping graphics.
- **Physics Bias**: Added `±0.06` horizontal nudge to nearly vertically-stacked colliding marbles to encourage rolling.
- **Damping/Gravity**: Adjusted for "heavier" feel (G:0.45, D:0.97).
- **Agent Safety**: Implemented a "Stop & Ask" rule for inaccessible local files to ensure data integrity.

- **Maintenance & Relaxation (2026-03-26)**:
    - Increased all games' `TIME_LIMIT` to 60s for lower cognitive pressure.
    - Expanded Korean game dataset (Lv 0-2) for variety and domain coverage.
    - Fixed specific typo ("허륭해요" -> "훌륭해요") in math feedback logic.
    - SDD Alignment: Updated `CRITICAL_LOGIC.md` and `specs/korean.md` before execution.
    - **Portal Update**: Activated "Korean Play" (국어 놀이) link in `index.html` by removing 'Soon' label.

- **Net Shield System (2026-03-26)**:
    - 5연속 정답 시 그물망(hasNet) 획득 → 오답 1회 추락 차단 후 튕겨 재상승.
    - 누적 불가(boolean), 소실 후 netStreak 리셋 → 다음 5연속부터 재발동.
    - `engine.js`: `netStreak`, `hasNet`, `NET_STREAK=5` 상태 추가; `recordResult()`에 갱신 로직.
    - `rocket.js`: `crashRocket()`에 hasNet 분기; `netBounceRocket()` 추락→그물→재상승 시퀀스.
    - `rocket.css`: `.net-element`, `.net-falling`, `.net-bounce`, `.net-indicator`, `.net-banner` 스타일.

- **Browser Verification Infrastructure (2026-03-26)**:
    - `serve_game.py`: Python HTTP 서버 (port 3000), 서브페이지 경로 인수 지원.
    - `global_workflows/verify.md`: `/verify` 워크플로우 — file:// 차단 우회 표준 프로토콜.
    - `CLAUDE.md` 정책 갱신: browser subagent 사용 금지 명시.
