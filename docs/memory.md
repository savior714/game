# Memory SSOT

## Current Context
- Completed Marble Game improvements:
    - Smooth tracking/guide line mechanics.
    - Difficulty balancing (faster game cycle, time-based probability).
    - Physics refinement (Sub-stepping x4 for overlap prevention).
    - Symmetry breaker for vertical stacking.
    - Strict overlap prevention (auto-hide preview).

## Design Decisions
- **Preview Hiding**: Hidden when ANY marble is in the top zone to avoid overlapping graphics.
- **Physics Bias**: Added `±0.06` horizontal nudge to nearly vertically-stacked colliding marbles to encourage rolling.
- **Damping/Gravity**: Adjusted for "heavier" feel (G:0.45, D:0.97).
