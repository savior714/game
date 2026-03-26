# Memory SSOT

## Current Context
- **Korean Game Implementation (2026-03-26)**:
    - 6-file modular architecture (index/base/rocket/engine/rocket/ui).
    - 3 categories (spelling, antonym, honorific) with Lv 0-2 difficulty.
    - Integrated Rocket-Streak (20-streak launch) and Marble-Reward systems.
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
