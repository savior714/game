# Critical Logic & Decisions

## 2026-03-26: Marble Drop Improvement
- **Problem**: Marble preview was fixed at center (`CW/2`), making users feel it only drops from there. No visual feedback for drop position.
- **Solution**: 
  - Track mouse/touch X position.
  - Render preview marble at the tracked X.
  - Add a vertical guide line for precision.
  - Use smooth lerping for preview animation.
- **Rationale**: Standard UX for Suika-like games. Improved control and precision.

## 2026-03-26: Game Difficulty Balancing
- **Problem**: The game is too easy and takes too long to end, which doesn't fit the "short break before study" goal.
- **Solution**: 
  - Reduced playable space by lowering the danger line (`DLINE`: 65 -> 100).
  - Increased marble radii by ~15% to fill the container faster.
  - Adjusted drop probabilities to favor larger marbles (Lv2/Lv3).
  - Shortened game-over timer (`OVR_MS`: 3000 -> 2200).
- **Overlap Prevention**: 
  - Hidden the preview marble and guide line during the danger state (`_mbDts` active).
  - Disabled marble drop input during the danger state.
- **Rationale**: Ensures a faster gameplay cycle (3-5 minutes) that encourages returning to study tasks, and prevents visual glitches/overlapping when the container is full.

## 2026-03-26: Physics Stability & Dynamic Difficulty
- **Problem**: Marbles overlapped when stacked/compressed. Static difficulty didn't provide enough progression.
- **Solution**:
  - **Physics Sub-stepping**: 4 iterations of collision resolution per frame.
  - **Dynamic Pick Probability**: Lv.3 frequency increases from 20% to 40% over 3 minutes.
- **Rationale**: Sub-stepping is a standard technique for multi-object collision stability. Time-based difficulty ensures a consistent progression and increasing challenge.
