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

## 2026-03-26: Korean Game Implementation (SDD)
- **Problem**: Need to implement a Korean language game for early elementary students within the shared platform architecture.
- **Solution**:
  - **Categorization**: Split into `spelling` (orthography), `antonym` (vocabulary), and `honorific` (grammar).
  - **Adaptive DB**: Integrated a 28-item question database directly into `engine.js` to minimize file count while maintaining category-specific difficulty tiers (Lv 0-2).
  - **Standardization**: Reused the Rocket-Streak (20 answers) and Marble-Reward systems from the English/Math games.
- **Rationale**: Adheres to the "6-file modularity" and "500-line limit" rules. Provides a cohesive learning experience across subjects.

## 2026-03-26: Agent Safety Instruction
- **Problem**: Agent may get stuck or make wrong assumptions if a target local file cannot be opened.
- **Solution**: Added a fatal constraint to stop work and ask the user for manual verification if file access fails repeatedly.
- **Rationale**: Prevents hallucinations and potential file corruption or logic errors based on missing context.

## 2026-03-26: Core Maintenance Standards
- **Rule**: Single file limit is set to **500 lines**.
- **Rule**: Documentation SSOT limits (`SDD.md` 100 lines, `docs/memory.md` 200 lines).
- **Rationale**: Ensures the project remains manageable for AI models and humans alike, preventing context overflow and maintainability issues.
## 2026-03-26: Statistics UI - Difficulty to Proficiency (Mastery)
- **Problem**: Users performing well (Accuracy >= 75%, Time <= 7s) were labeled as "Difficulty: Hard" (어려움), which was confusing or demotivating as they felt the game was easy.
- **Solution**: 
  - Renamed "Difficulty" (난이도) header to **"Proficiency" (숙련도)** in the stats table.
  - Replaced labels `['쉬움', '보통', '어려움']` with **`['기초', '중급', '마스터']`** (Basic, Intermediate, Master).
  - Updated badge colors: Level 1 (Intermediate) to **Blue (`#42a5f5`)**, Level 2 (Master) to **Gold (`#ffca28`)**.
- **Rationale**: Rewards high achievement with positive reinforcement ("Master") rather than describing the content's technical difficulty. Adheres to child-centric UX standards.

## 2026-03-26: Global Time Limit & Typo Maintenance
- **Problem**: 
  - Current 20s time limit is too short for some learners. 
  - "허륭해요!" typo in math game (Hallucination/Typo).
  - Korean question data is too sparse (prevents repetition).
- **Solution**: 
  - Increased global `TIME_LIMIT` to **60s** across all games.
  - Fixed typo in `math/ui.js` from **"허륭해요!"** to **"훌륭해요!"**.
  - Expanded `korean/engine.js` DB with additional Level 0-2 questions.
- **Rationale**: Relaxing time limits encourages more thoughtful learning before speed-up phases. Data expansion prevents boredom and improves learning coverage.

## 2026-03-26: Production Activation - Korean Game
- **Problem**: Korean game was implemented and tested but main portal (`index.html`) still displayed it as "Soon" (locked).
- **Solution**: Removed "Soon" badge, converted `div` to `a` tag in `index.html`, and added "Start" (시작하기) interactive element.
- **Rationale**: Formally launching the feature to the end user.

## 2026-03-26: Korean Cloze Blank Rule (Honorific Particle Bug)
- **Problem**: Some honorific questions were authored as `'( )께서'`, which can produce ungrammatical duplication (e.g. `께서께서`) when the correct choice is `께서`.
- **Solution**: Standardized cloze text to use only `'( )'` with **no fixed post-blank particle**; choices contain the full particle string (e.g. `께서`).
- **Rationale**: The UI renders `qText` verbatim (no morphological composition). Data-level standard prevents duplication and keeps sentences grammatically valid.

## 2026-03-26: Streak Reward Roulette (20 Correct Answers)
- **Problem**: On 20 consecutive correct answers, the Korean game always granted only one fixed reward (Marble game). This reduced novelty and motivational variety.
- **Solution**: Replace the fixed reward with a **roulette-style reward chooser** containing three options: **Marble game (1 round)**, **YouTube (15 minutes)**, **Snack (pick one)**.
- **Rationale**: A small, varied reward pool increases engagement while preserving the existing Rocket-Streak trigger and keeping implementation lightweight (overlay UI + simple random choice).

## 2026-03-26: Reward Roulette Manual Start
- **Problem**: Auto-opening the roulette immediately after the 20-streak could feel like the app is taking control away from the child.
- **Solution**: On 20-streak, only **reveal** the top `🎁 보상 룰렛` button; roulette opens **only when the user clicks**.
- **Rationale**: Improves agency and avoids interrupting the learning flow while keeping the reward accessible.

## 2026-03-26: Center Rocket → Explosion → Roulette Entrance
- **Problem**: Reward appearance felt detached from the rocket streak climax (boost banner), and lacked a strong celebratory cue.
- **Solution**: After 20-streak boost, spawn a transient rocket that **flies to the screen center**, triggers a **"boom" particle effect**, then opens the roulette overlay in the center (roulette remains idle until spin).
- **Rationale**: Makes the reward feel earned and visually connected to the streak moment while preserving user agency (no auto-spin).
