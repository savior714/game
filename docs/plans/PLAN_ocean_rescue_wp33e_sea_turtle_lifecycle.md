# Ocean Rescue WP-33E — Sea-Turtle Lifecycle Replan

- **Status:** ACTIVE
- **Parent plan:** `docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md`
- **Parent phase:** Phase 8 — Application orchestration decomposition
- **Replanned:** 2026-08-05
- **Baseline:** `origin/main` at `d55acd2d47556bb2244512640cee37dbb4006166`
- **Current implementation:** PARTIAL SCAFFOLD; WP-33E is not complete
- **Next executable package:** WP-33E-0
- **Execution model:** sequential packages with one ownership boundary and one focused acceptance decision per package

---

## 1. Why WP-33E is being replanned

The original Phase 8 table names WP-33E as one package: “Sea-turtle mission
lifecycle.” That label is too broad for the current runtime.

The sea-turtle flow currently crosses all of these independent reasoning and
rollback boundaries:

1. rescue-session identity and phase eligibility;
2. read-only snapshot projection and root diagnostics;
3. authored-scene activation and synchronization;
4. DOM pointer routing, coordinate mapping, pointer ownership, and capture;
5. success/failure feedback timing integrated with WP-33D pause/rearm behavior;
6. assist/progress/status UI projection;
7. stale callback and stale rescue-sequence rejection;
8. transition to `RESCUE_SUCCESS` and handoff to mission-success presentation;
9. canonical ESM ownership while retaining the ordered-script rollback lane.

Attempting all of these in one controller change creates a failure domain large
enough that a type error, pointer-capture bug, timer bug, or stale-sequence bug
can invalidate the whole package.

The current `sea-turtle-lifecycle.ts` is therefore treated as a scaffold, not as
WP-33E closure. It currently exposes only snapshot/start helpers while pointer
handling, capture, feedback timers, success/failure visuals, completion routing,
and most rendering orchestration remain in `src/app.js`.

### Current scaffold defects that must not be normalized as the target design

- `getSeaTurtleSnapshot()` returns `unknown | null` instead of the concrete
  `SeaTurtleSnapshot | null` contract.
- The installer casts through `unknown` and mutates the host object, obscuring
  whether the host actually satisfies the controller API.
- `startSeaTurtleInteraction()` has no rescue-sequence argument, so the
  controller cannot reject stale work by sequence identity.
- `SeaTurtleApi` does not yet type every value used by orchestration, including
  `Constants` and `Dialogues`.
- `SeaTurtleSceneApi.sync` does not currently express the pointer-intent argument
  used by the runtime.
- Static tests prove file presence and installer order but do not prove
  lifecycle ownership or browser behavior.
- The shared rescue pointer dispatcher still branches across sea turtle, crab,
  and young whale. Moving that shared dispatcher during WP-33E would expand the
  package into WP-33F/WP-33G territory.

---

## 2. Replanning decision

WP-33E is replaced by six sequential packages:

| Package | Ownership moved | Runtime behavior allowed to change |
|---|---|---|
| WP-33E-0 | Characterization, ABI correction, and exact boundary contract | None |
| WP-33E-1 | Read-only sea-turtle projection and scene synchronization | None |
| WP-33E-2 | Sea-turtle session activation and shutdown | None |
| WP-33E-3 | Sea-turtle pointer session and capture lifecycle | None |
| WP-33E-4 | Sea-turtle feedback timer and feedback UI lifecycle | None |
| WP-33E-5 | Completion handoff, canonical authority proof, and closeout | None |

A package may start only after the previous package has passed its focused
acceptance decision on the latest `origin/main`.

No package may silently absorb crab, young-whale, mission-success, render-runtime,
or scene-module migration work.

---

## 3. Final ownership model

### 3.1 `sea-turtle.js` remains the gameplay state machine

It continues to own:

- rope catalog and ordering;
- gesture validity and trace rules;
- help-level progression;
- interaction lock state;
- success/failure result generation;
- feedback completion and next-rope state;
- immutable snapshots.

WP-33E does not rewrite those gameplay rules.

### 3.2 `sea-turtle-lifecycle.ts` becomes canonical ESM orchestration

At WP-33E closeout it owns:

- one active sea-turtle rescue-session reference;
- start and stop of the sea-turtle state machine;
- authored-scene activation and snapshot synchronization;
- legacy paint fallback invocation through a narrow host bridge;
- sea-turtle root diagnostic markers;
- sea-turtle pointer ID and capture target;
- pointer down/move/up/cancel routing after shared mission dispatch;
- feedback timer scheduling through WP-33D;
- success/failure visual classes;
- progress, dialogue, status, and assist-hand projection;
- stale feedback callback rejection;
- completion detection;
- a single typed completion handoff to the host.

### 3.3 `app.js` retains shared rescue routing

During WP-33E, `app.js` continues to own:

- binding the shared rescue canvas listeners exactly once;
- deciding which mission controller receives each rescue event;
- shared rescue coordinate mapping through `PointerInput`;
- `activeRescueSequence` storage until a later dedicated extraction;
- crab and young-whale branches;
- the actual `RESCUE_SUCCESS` transition and mission-success presentation until
  WP-33H.

The canonical ESM lane must delegate sea-turtle branches to WP-33E methods.
The ordered-script lane keeps the existing inline fallback behavior for rollback.

### 3.4 WP-33D remains timer authority

WP-33E must call only the typed pauseable-timer boundary:

- `schedulePauseableTimer("sea-turtle-feedback", duration, callback)`;
- `cancelPauseableTimer("sea-turtle-feedback")`;
- related registration methods only when required by the existing WP-33D
  contract.

WP-33E must not call `window.setTimeout()` for feedback.

### 3.5 WP-33H remains mission-success authority

WP-33E detects that the third rope has completed and invokes one typed host
callback. It does not own:

- mission completion persistence;
- new mission unlocks;
- mission-success stage timers;
- replay, continue, or return actions;
- mission-success screen rendering.

---

## 4. Target controller contracts

Exact names may change during WP-33E-0 if the current code proves a smaller
contract, but responsibilities must remain equivalent.

```ts
interface SeaTurtleSessionRef {
  readonly rescueSequenceId: number;
  readonly missionId: "sea-turtle";
}

interface SeaTurtlePointerInput {
  readonly pointerId: number;
  readonly point: Readonly<{ x: number; y: number }>;
  readonly captureTarget: HTMLCanvasElement;
}

interface SeaTurtleLifecycleHostApi extends PauseTimerResumeAppApi {
  getActiveRescueSequence(): RescueSiteSequence | null;
  renderLegacySeaTurtleFrame(intent?: PointerIntent): void;
  onSeaTurtleInteractionComplete(session: SeaTurtleSessionRef): void;
}

interface SeaTurtleLifecycleAppApi extends SeaTurtleLifecycleHostApi {
  startSeaTurtleSession(sequence: RescueSiteSequence): boolean;
  stopSeaTurtleSession(): boolean;
  isSeaTurtleSessionActive(): boolean;
  getSeaTurtleSnapshot(): SeaTurtleSnapshot | null;
  syncSeaTurtleProjection(intent?: PointerIntent): boolean;
  handleSeaTurtlePointerDown(input: SeaTurtlePointerInput): boolean;
  handleSeaTurtlePointerMove(input: SeaTurtlePointerInput): boolean;
  handleSeaTurtlePointerUp(input: SeaTurtlePointerInput): boolean;
  handleSeaTurtlePointerCancel(pointerId: number): boolean;
  cancelSeaTurtlePointerForPause(): void;
}
```

Contract rules:

- no `any`;
- no `unknown` return type where a runtime ABI type exists;
- no optional callback used to hide an unimplemented mandatory responsibility;
- no controller method may infer a rescue sequence only from mutable global
  state when a session reference can be captured at start;
- no direct dependency on Crab or YoungWhale;
- no direct registration of shared DOM listeners;
- no direct mission-success presentation call;
- no direct feedback `setTimeout()`;
- pointer capture is released only by the controller that acquired it;
- release is guarded so an already-released or implicitly released pointer does
  not create a second failure.

---

## 5. WP-33E-0 — Characterization and ABI lock

- **Status:** NOT_STARTED
- **Objective:** Make the existing behavior and the intended typed boundary
  explicit before moving runtime ownership.
- **Runtime ownership moved:** none
- **Allowed files:** runtime ABI types, sea-turtle controller contract, focused
  tests, Justfile recipe, this plan, and narrowly necessary type-only imports
- **Forbidden files:** gameplay state-machine implementation, authored scene
  implementation, generated standalone HTML

### Included work

1. Correct `SeaTurtleApi` typing for values already consumed by orchestration:
   `MissionId`, `Constants`, `Ropes`, `Dialogues`, snapshots, pointer results,
   and feedback completion.
2. Correct `SeaTurtleSceneApi.sync` to include the actual pointer-intent contract.
3. Replace `unknown` snapshot return types in the controller scaffold.
4. Define a rescue-sequence-bound session reference.
5. Define a focused characterization matrix for:
   - start eligibility;
   - first render and markers;
   - pointer down/move/up/cancel;
   - pointer capture and release;
   - success and failure feedback;
   - pause during an active pointer;
   - pause during feedback timing;
   - stale feedback callback rejection;
   - menu shutdown;
   - third-rope completion handoff.
6. Add a dedicated `just` recipe that runs only the WP-33E characterization
   and direct WP-33C/WP-33D regressions.
7. Retain the current runtime behavior unchanged.

### Acceptance decision

**PASS only when:** strict typecheck passes, the characterization suite passes
against the existing behavior, and no runtime source ownership has moved.

### Stop conditions

- Any required ABI cannot be expressed without changing gameplay semantics.
- Current browser behavior cannot be reproduced deterministically enough to
  become the migration baseline.
- The observed problem belongs to the shared rescue dispatcher rather than the
  sea-turtle branch; record it separately instead of widening WP-33E-0.

### Rollback boundary

Revert type/test/document changes only.

---

## 6. WP-33E-1 — Read-only projection ownership

- **Status:** BLOCKED_BY_WP-33E-0
- **Objective:** Move only snapshot-to-view projection into the typed controller.
- **Runtime ownership moved:** render/sync/markers only

### Included work

- controller-owned `syncSeaTurtleProjection(intent?)`;
- authored-scene sync when mounted;
- narrow legacy paint fallback bridge when the authored scene is unavailable;
- root markers for active rope, completed count, help level, feedback, and
  complete state;
- typed rope lookup/order helpers only when required for projection;
- canonical `app.js` delegation to the controller;
- ordered-script fallback remains behaviorally unchanged.

### Explicit exclusions

- start/stop;
- pointer ownership or capture;
- feedback timers;
- success/failure class changes;
- assist hand;
- phase transitions;
- mission-success handoff.

### Acceptance decision

**PASS only when:** every canonical sea-turtle render/marker call uses the typed
controller, the characterization matrix remains identical, and the legacy
ordered-script rollback path still passes.

### Rollback boundary

Restore canonical render/marker calls to the existing `app.js` functions.

---

## 7. WP-33E-2 — Session activation and shutdown

- **Status:** BLOCKED_BY_WP-33E-1
- **Objective:** Give the typed controller one explicit sea-turtle session
  lifecycle without moving pointer or feedback behavior.
- **Runtime ownership moved:** session identity, start, stop, scene activation,
  initial projection, and shutdown cleanup

### Included work

- `startSeaTurtleSession(sequence)` with exact mission and
  `RESCUE_ACTIVE` validation;
- capture of `rescueSequenceId` at session start;
- idempotent duplicate-start behavior matching the baseline;
- `SeaTurtle.start()` and scene activation;
- initial “Rope 1 of 3” projection and marker synchronization;
- `stopSeaTurtleSession()` for menu exit, rescue cancellation, and replacement;
- scene exit and state-machine stop where the current behavior requires them;
- canonical delegation from `startRescueInteraction()`;
- no change to crab or young-whale startup.

### Acceptance decision

**PASS only when:** canonical startup/shutdown is controller-owned, stale or
wrong-mission sequences are rejected, and pointer/feedback behavior still uses
the unchanged legacy branch.

### Rollback boundary

Restore sea-turtle start/stop to the existing host implementation while keeping
WP-33E-1 projection ownership.

---

## 8. WP-33E-3 — Pointer session and capture ownership

- **Status:** BLOCKED_BY_WP-33E-2
- **Objective:** Move the complete sea-turtle pointer session into the typed
  controller without moving the shared rescue listener/router.
- **Runtime ownership moved:** sea-turtle pointer ID, capture target, and
  down/move/up/cancel operations

### Included work

- typed pointer input accepted only for the current captured rescue sequence;
- one primary left-button pointer at a time;
- pointer-down state-machine call and capture acquisition;
- pointer-move state-machine call and active pointer-intent projection;
- pointer-up result production, capture release, inactive projection, and result
  return to the existing feedback router;
- pointer-cancel and pause-cancel cleanup;
- capture release guarded by active capture state;
- canonical sea-turtle branches in the shared router delegate to the controller;
- crab and young-whale branches remain byte-for-byte or semantically unchanged.

### Explicit exclusions

- moving `bindRescuePointerInput()`;
- moving the shared rescue mission router;
- converting input to PixiJS scene-object events;
- feedback timer ownership;
- completion transition.

### Acceptance decision

**PASS only when:** browser-generated trusted pointer input proves down → move →
up and cancel flows, native capture is acquired and released, pause cancels the
active pointer, no pointer remains stuck, and crab/young-whale focused tests are
unchanged.

### Rollback boundary

Restore only sea-turtle pointer branches to the host fallback.

---

## 9. WP-33E-4 — Feedback timer and feedback UI ownership

- **Status:** BLOCKED_BY_WP-33E-3
- **Objective:** Move success/failure feedback from pointer result through
  `finishFeedback()` into the typed controller.
- **Runtime ownership moved:** feedback sequence, pauseable timer, feedback UI,
  assist UI, next-rope projection, and stale callback rejection

### Included work

- typed feedback sequence containing rescue sequence ID, rope ID, and kind;
- success and failure class application/removal;
- dialogue and progress text;
- assist-hand show/hide based on help level;
- scheduling and cancellation through WP-33D only;
- pause freeze and resume rearm proof for both success and failure durations;
- exact stale-sequence rejection after menu exit, restart, or newer rescue;
- `SeaTurtle.finishFeedback()` and next-rope rendering;
- completion detection followed by one host callback, not direct mission-success
  presentation.

### Acceptance decision

**PASS only when:** success and failure feedback complete once, pause preserves
remaining time, stale callbacks are inert, direct feedback `setTimeout()` is
absent from the canonical controller, and all three ropes still advance in
order.

### Rollback boundary

Restore feedback routing/timing to the host while retaining WP-33E-1 through
WP-33E-3 ownership.

---

## 10. WP-33E-5 — Completion handoff and closeout

- **Status:** BLOCKED_BY_WP-33E-4
- **Objective:** Prove the typed controller is the canonical ESM owner of the
  complete sea-turtle interaction and close WP-33E without taking WP-33H work.

### Included work

- exact `onSeaTurtleInteractionComplete(session)` host bridge;
- host verifies the session is still the active rescue sequence;
- host retains `RESCUE_SUCCESS` transition and
  `startMissionSuccessPresentation()` until WP-33H;
- remove canonical sea-turtle fallback branches that are no longer reachable;
- retain ordered-script rollback implementation and prove it remains operational;
- update Phase 8 status and ownership documentation;
- create WP-33E evidence under
  `docs/evidence/ocean-rescue/migration/phase-8/`;
- set the next executable package to WP-33F only after all closeout checks pass.

### Closeout verification bundle

1. strict `tsc --noEmit`;
2. WP-33E-0 characterization suite;
3. controller-focused unit tests;
4. real Chromium sea-turtle mission:
   - startup;
   - rope 1, rope 2, rope 3;
   - failure and assist escalation;
   - pointer cancel;
   - pause during pointer;
   - pause during feedback;
   - completion handoff;
   - zero page errors;
   - zero unexpected console errors;
   - zero failed or external runtime requests;
5. WP-33C rescue-site/tutorial regression;
6. WP-33D pause/timer/resume regression;
7. crab and young-whale input regressions;
8. deterministic production bundle in two clean builds;
9. deterministic standalone HTML in two clean builds;
10. tracked artifact drift check;
11. operational ordered-script rollback proof;
12. diff scope and generated-artifact provenance check.

### Final acceptance decision

**WP-33E is COMPLETE only when:** the canonical ESM lane uses the typed
controller for sea-turtle start, projection, pointer session, feedback timing,
completion detection, and cleanup; the host owns only shared routing and the
WP-33H handoff; the legacy rollback lane remains operational; and the complete
verification bundle passes.

### Rollback boundary

Restore the canonical ESM installer to the last passing WP-33E-4 state. Do not
alter the ordered-script rollback source to manufacture a rollback.

---

## 11. Package-wide forbidden actions

- Do not migrate crab or young-whale behavior.
- Do not move the shared rescue listener/router.
- Do not redesign rope rules, tolerances, durations, dialogue, or visuals.
- Do not convert input to PixiJS scene-object interaction during WP-33E.
- Do not migrate `SeaTurtleScene` to TypeScript; that remains WP-41B.
- Do not import PixiJS as a package; that remains WP-40.
- Do not implement mission-success progression; that remains WP-33H.
- Do not delete the ordered-script rollback implementation.
- Do not edit generated standalone HTML directly.
- Do not accept static source-presence tests as browser-behavior proof.
- Do not use direct `setTimeout()` for sea-turtle feedback.
- Do not suppress type errors with `any`, broad index signatures, or
  `as unknown as` when a concrete boundary can be expressed.
- Do not run unrelated full-suite fixes inside a WP-33E package.

---

## 12. Publication and conflict handling

Each package is published independently to `origin/main` after its focused
acceptance decision passes.

Before publication:

1. fetch latest `origin/main`;
2. rebase or replay the isolated worktree on the latest published state;
3. inspect same-file changes in `app.js`, runtime ABI types, controller files,
   and WP-33 tests;
4. rerun only the package verification bundle plus directly affected
   regressions;
5. fast-forward push to `origin/main`;
6. verify local and remote commit IDs match.

A moved `origin/main` is not itself a blocker. A semantic conflict in the same
ownership boundary is a blocker until the package is re-evaluated on the new
state.

---

## 13. Required completion report

On PASS:

```text
RESULT: PASS
CHANGE: <one sentence describing the ownership boundary moved>
VERIFY: <focused acceptance decision and direct regressions>
COMMIT: <published commit SHA>
```

On BLOCKED:

```text
RESULT: BLOCKED
BLOCKER: <specific unmet precondition or semantic conflict>
VERIFY: <what was reproduced and what remains unproven>
```

Do not report WP-33E complete from an intermediate package.
