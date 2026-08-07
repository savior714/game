# AidenGame Ocean Rescue — Track B Active Continuation Runbook

- Version: v2.0
- Date: 2026-08-08
- Status: ACTIVE
- Track: B — asset/content production, proof, approval, atlas, registry, manifest and packaging provenance
- Status refresh baseline: `b042f74c07a4f41a63fb5778534d557c61addc6b`
- Latest Track-B-specific commit at refresh: `27583817c577825b14a0e177a7d69ccf53f72bbc`

This file is intentionally **delta-only**. Completed Track B history is not repeated in executable detail. The predecessor runbooks are historical references only and should not be loaded into a local-model context unless a current contract discrepancy requires them.

---

## 1. Live state

### Closed and removed from the active queue

| Task | State | Current evidence |
| --- | --- | --- |
| B14 approval contact-sheet path contract | CLOSED | writer/validator canonical-path enforcement is on `main` (`b3c722604719c1562dc54fbc111731ad22e0cf04`) |
| B15 approved decision ↔ visual verdict coherence | CLOSED | approved receipts require exact `visualReviewVerdict: PASS` (`38acb30f69d0f64e3612c8eb1a238904a13cb370`) |
| B16 exact current proof approval | CLOSED | explicit current approval receipt published (`5320e50cb69ec780543b80c0ce32d3afc7465277`) |
| B20 mandatory visible-asset inventory | CLOSED FOR CURRENT SELECTION | Rendering MVP requires three seaweed loops; current packet has `scene.seaweed-loop.01`, so loop 02 was selected as the next single visual gap |
| B21 loop-02 handoff brief | CLOSED | `domains/ocean-rescue/assets/handoff/briefs/scene-seaweed-loop-02-01.md` published in `27583817c577825b14a0e177a7d69ccf53f72bbc` |

Do not re-run or re-explain B14–B21 unless refreshed `origin/main` proves one of those contracts regressed.

### Current active asset

```text
Asset ID: scene-seaweed-loop-02-01
Runtime alias: scene.seaweed-loop.02
Brief: domains/ocean-rescue/assets/handoff/briefs/scene-seaweed-loop-02-01.md
Expected inbox file: domains/ocean-rescue/assets/handoff/inbox/scene-seaweed-loop-02-01.svg
Canonical destination after human approval: domains/ocean-rescue/assets/source/scene/seaweed-loop-02.svg
Bundle: scene
Logical size: 120 x 200
Pivot: [0.5, 0.1]
```

At this refresh, the expected loop-02 inbox file is **absent**. The inbox contains older unrelated handoff files only. Therefore the first executable gate is B22, and B22 is `BLOCKED` until the human/frontier transfer places the exact SVG at the expected inbox path.

Do not substitute `scene.seaweed-loop.01`, generate a local-model imitation, or create placeholder geometry to bypass this gate.

### Current execution order

```text
B22 SVG intake + structure/security acceptance
→ B23 actual-size isolated + in-context proof
→ B24 explicit human visual gate + canonical registration
→ B25 generated-pipeline rebuild
→ B26 explicit approval receipt for rebuilt proof
→ B27 B → A producer-contract handoff proof
→ B28 fresh mandatory-asset inventory
→ repeat B21–B28 for at most one newly selected asset
→ B30–B34 maintenance/closeout
```

Only one task is executed per invocation.

---

## 2. Authority and minimal read set

Before each task, refresh `origin/main` and read only:

1. `AGENTS.md`
2. `docs/specs/technical/AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md`
3. `docs/specs/product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md`
4. this file
5. the selected asset brief and the exact implementation/tests required by the current task

Do **not** load the predecessor execution runbook by default.

Past chat reports and the baseline SHA in this file are orientation evidence only. Current `origin/main`, current specs, current assets and current generated outputs decide the task.

---

## 3. Execution and change-scope invariant

Every invocation has:

```text
one failure domain
one falsifiable hypothesis
one primary binary criterion
one publication decision
```

The target is not minimum LOC or minimum file count. Use the repository rule:

```text
minimum coherent, root-cause-complete change
```

Before mutation, inspect the shared owner and direct sibling surfaces that consume the same invariant. If the same root cause, invariant, ownership and rollback boundary require production metadata, a generator/validator, a direct fixture and a focused regression to move together, that bounded package may be changed together.

Do not:

- leave a shared root cause behind and add leaf workarounds;
- duplicate normalization/validation/domain rules across callers;
- widen mutation scope merely because sibling inventory found a different defect;
- add speculative abstractions, future capability or unrelated cleanup;
- mix Track A runtime behavior into a Track B producer task.

An independently rooted finding is `DISCOVERED_FAILURE` and remains a later task.

---

## 4. Track B boundary

Track B owns:

- `assets/handoff/**`, `assets/source/**`, `assets/review/**`, `assets/generated/**`;
- asset metadata/schema and hashes;
- source validation and security validation;
- proof/contact-sheet production;
- explicit approval-receipt mechanics;
- atlas generation and validation;
- registry/manifest generation and provenance;
- deterministic rebuild checks;
- B-side package provenance.

Track B does not own gameplay state, controller behavior, hit rules, timer/pause behavior or runtime scene behavior after a correct B contract has been published.

Rule:

```text
B producer contract wrong -> fix B
B producer contract correct + runtime consumption wrong -> report and route to Track A
```

---

# PART I — CURRENT LOOP-02 ASSET CYCLE

## 5. B22 — SVG intake and structure/security acceptance

### Failure domain

`SEAWEED_LOOP_02_HANDOFF_SVG_STRUCTURAL_ACCEPTANCE`

### Entry condition

The exact file exists at:

```text
domains/ocean-rescue/assets/handoff/inbox/scene-seaweed-loop-02-01.svg
```

If absent, do not mutate anything. Report:

```text
RESULT: BLOCKED
FAILURE_DOMAIN: SEAWEED_LOOP_02_HANDOFF_SVG_STRUCTURAL_ACCEPTANCE
CHANGE: NONE
PRIMARY_VERIFY: NOT_RUN
DIRECT_VERIFY: NOT_RUN
STATIC_VERIFY: NOT_RUN
PUBLISH: NOT_APPLICABLE
COMMIT: NONE
DISCOVERED_FAILURE: NONE
BLOCKER: expected loop-02 SVG has not been transferred to the handoff inbox
```

### Hypothesis

The transferred loop-02 SVG satisfies the brief and canonical incoming-SVG structure/security/build-compatibility contract without local visual modification.

### Primary criterion

The exact inbox bytes:

- map unambiguously to the loop-02 brief;
- have root `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 200">` semantics;
- contain required root semantic group `scene-seaweed-loop-02`;
- contain finite numeric geometry/transforms;
- contain unique IDs and resolved local references;
- contain no forbidden executable/external/raster constructs;
- rasterize successfully with the pinned repository toolchain.

### Read scope

- loop-02 brief
- exact inbox SVG
- `scene/seaweed-loop-01.svg` as family/style reference only
- `scripts/ocean_rescue/validate_art_packet.py` and nearest focused validator tests
- incoming-SVG and Gate A/B sections of the manual handoff spec

### Mutation rule

B22 is validation-first. Do not edit visual geometry to make the candidate pass.

Allowed only when pixel-equivalent and required by the canonical manual contract: mechanical sanitation such as editor metadata/comment/whitespace cleanup. If any path, color, transform, silhouette or visual composition must change, reject the candidate and return to frontier revision instead.

If B22 exposes a defect in the shared validator itself, stop the asset task and record that validator defect as a separate failure domain unless the current candidate cannot be judged without fixing the shared owner.

### Stop condition

Stop immediately after one of:

- `STRUCTURE_PASS` with exact incoming hash recorded; or
- `STRUCTURE_REJECTED` with the first decisive rejection reason; or
- `BLOCKED` because the SVG is absent.

Do not proceed to proof generation in the same invocation.

---

## 6. B23 — Actual-size isolated and in-context proof

### Failure domain

`SEAWEED_LOOP_02_ACTUAL_SIZE_VISUAL_PROOF`

### Entry condition

B22 is independently `PASS` for the exact same SVG hash.

### Hypothesis

The structurally accepted candidate can be rendered deterministically at its intended size and in the sea-turtle rescue context without clipping, opacity surprises or material rendering differences.

### Primary criterion

For the exact accepted candidate bytes, produce evidence sufficient for human judgment containing:

1. transparent isolated render at declared 2× scale;
2. actual-size 1× render at `120 x 200` logical pixels;
3. in-context proof in the real sea-turtle rescue composition with approved neighboring assets.

The proof must make silhouette, central opening, family similarity to loop 01, independent geometry, contrast and overlap judgeable.

### Rules

- Do not canonicalize the SVG.
- Do not update `art-packet.json` or approval state.
- Do not hand-edit raster proof output.
- Do not approve visual quality.
- Use existing repository proof/raster/runtime tooling; do not create a parallel proof framework.

### Stop condition

When proof artifacts for the exact incoming hash exist and are reproducible, stop for human review.

---

## 7. B24 — Human visual gate and canonical registration

### Failure domain

`SEAWEED_LOOP_02_HUMAN_VISUAL_ACCEPTANCE`

### Entry condition

B23 proof exists for the exact current candidate hash.

### Human gate

The user explicitly says `APPROVED` or `REJECTED` for that exact proof/candidate.

No validator, screenshot generation, hash match or local-agent report is visual approval.

### If rejected

- do not canonicalize;
- write at most one bounded revision request for the same visual failure domain when needed;
- keep gameplay/runtime unchanged;
- return to frontier authoring and stop.

### If approved

Canonicalize exactly the accepted bytes, or a separately proven pixel-equivalent sanitized copy, to:

```text
domains/ocean-rescue/assets/source/scene/seaweed-loop-02.svg
```

Update the coherent canonical metadata package required for this one asset, including its packet entry, source hash, stable alias, logical size, pivot, bundle, authoring method and approval state.

Expected packet identity:

```text
id: scene-seaweed-loop-02-01
alias: scene.seaweed-loop.02
bundle: scene
logicalSize: [120, 200]
declaredRasterScale: 2
pivot: [0.5, 0.1]
authoringMethod: frontier-svg-human-approved
approvalState: approved
```

Do not manually claim the old global approval receipt remains current after source/packet bytes change.

### Primary criterion

The exact human-approved visual bytes are the canonical source and the packet describes those exact bytes with no unrelated asset mutation.

Publish and stop.

---

## 8. B25 — Rebuild the affected generated pipeline

### Failure domain

`SEAWEED_LOOP_02_GENERATED_PIPELINE_REBUILD`

### Entry condition

B24 canonicalization is published.

### Hypothesis

Existing sanctioned producers can derive fresh proof, atlas, registry, manifest and package outputs from the new canonical loop-02 source without hand-edited generated files or unrelated bundle drift.

### Producer order

Use existing producers in this order as applicable:

1. validate art packet/source contract;
2. rebuild canonical contact sheet from current packet;
3. build atlases;
4. validate atlases;
5. rebuild render-assets registry/manifest;
6. rebuild B-side packaged/single-HTML output when required by the existing pipeline contract;
7. run generated-artifact/provenance drift checks;
8. perform a second clean rebuild and prove byte identity for deterministic surfaces.

Representative existing tools include:

```text
scripts/ocean_rescue/validate_art_packet.py
scripts/ocean_rescue/build_art_contact_sheet.py
scripts/ocean_rescue/build_atlases.py
scripts/ocean_rescue/validate_atlases.py
scripts/ocean_rescue/build_render_assets_registry.py
scripts/ocean_rescue/build_single_html.py
scripts/ocean_rescue/deterministic_html_verifier.py
```

Use their current CLI contracts from refreshed `origin/main`; do not copy stale command syntax from old runbooks.

### Primary criterion

All generated B-owned outputs are reproducible from current canonical inputs, loop-02 appears under the expected scene alias/bundle, unrelated generated surfaces do not drift without an explained shared-owner reason, and no generated file was hand-edited.

The previous approval receipt is expected to become stale after canonical source/proof change. That is not a B25 failure when all generation/provenance evidence is otherwise correct.

Publish generated outputs if the current repository pipeline tracks them, then stop.

---

## 9. B26 — Explicit approval of rebuilt packet/proof

### Failure domain

`SEAWEED_LOOP_02_REBUILT_PACKET_HUMAN_APPROVAL`

### Entry condition

B25 deterministic proof is published and the exact contact-sheet/proof hash is known.

### Human boundary

The user explicitly reviews and approves the exact rebuilt committed proof.

After explicit approval, use the official approval writer. Never patch hashes, dates, predecessor fields or verdicts manually.

Required receipt state:

- exact current packet hash;
- exact current source-set hash;
- exact current contact-sheet hash;
- valid committed predecessor lineage;
- canonical contact-sheet evidence path;
- exact `visualReviewVerdict: PASS`;
- exact current approved alias parity.

Run the canonical approval validator and focused approval regressions.

Publish the official receipt and stop.

---

## 10. B27 — B → A producer-contract handoff proof

### Failure domain

`SEAWEED_LOOP_02_B_TO_A_RENDER_HANDOFF`

### Primary criterion

On one current `origin/main` lineage, `scene.seaweed-loop.02` is:

- canonical and approved;
- present in expected scene atlas metadata;
- present in registry/manifest/package outputs;
- bound to the correct current source/proof/approval lineage;
- resolvable through the existing B producer contract;
- available without B-owned runtime network retrieval.

Do not repair Track A runtime behavior here.

If B passes and the game still consumes or displays the asset incorrectly, report:

```text
B_PRODUCER_CONTRACT: PASS
A_CONSUMER_FAILURE: <exact observation>
B_CHANGE_REQUIRED: NO
ROUTE: TRACK_A
```

Stop after the B contract is independently decided.

---

## 11. B28 — Fresh mandatory visible-asset inventory

### Failure domain

`MANDATORY_VISIBLE_ASSET_COMPLETENESS_INVENTORY`

### Mode

Read-only selection task.

### Primary criterion

Re-read the current Rendering MVP mandatory first-slice set and current packet/source/proof/approval state.

If no mandatory visual gap remains, report `NO_ACTIONABLE_VISUAL_GAP`.

If gaps remain, select **exactly one** highest-priority visible asset and report:

- asset ID/alias;
- observed deficiency;
- authoritative expected state;
- one binary visual acceptance criterion;
- next handoff brief path.

Do not preselect loop 03 merely because loop 02 just completed. The fresh inventory decides the next asset. If loop 03 is still the highest-priority missing mandatory asset, then and only then create its B21-style brief in a later invocation.

Stop after selection.

---

# PART II — REPEATING ONE-ASSET LOOP

## 12. Re-entry rule after B28

For every newly selected asset, reuse the same bounded state machine:

```text
brief
→ inbox SVG
→ structure/security acceptance
→ actual-size + in-context proof
→ explicit human visual gate
→ canonical registration
→ generated rebuild
→ exact rebuilt-proof approval
→ B → A producer proof
→ fresh inventory
```

One asset remains active until it reaches `COMPLETE`, is explicitly rejected and closed, or is blocked by a concrete external dependency.

Never batch multiple frontier-authored visual assets into one validation/canonicalization/publication task.

---

# PART III — MAINTENANCE AND CLOSEOUT

## 13. B30 — Placeholder audit

Read-only first. Confirm that mandatory MVP-visible subjects are authored where the active spec requires authored art.

If a concrete placeholder gap exists, select one and route it into the one-asset loop. Do not mass-replace assets.

---

## 14. B31 — Atlas integrity inventory

Read-only first. Check only established contracts:

- page bounds and frame bounds;
- bundle membership;
- trim/padding metadata;
- duplicate/missing aliases;
- deterministic output;
- producer provenance.

Do not invent new atlas-density or aesthetic thresholds.

A reproduced violation becomes a separate single failure domain.

---

## 15. B32 — B-package provenance inventory

Primary criterion: packaged B asset data is derived from the current approved lineage and requires no network retrieval for B-owned asset payloads.

Inspect producer/package metadata only. Runtime loader defects after a correct package are Track A.

---

## 16. B33 — Art-toolchain currency inventory

Current repository pins at this refresh:

```text
CairoSVG == 2.9.0
Pillow == 12.3.0
```

As of 2026-08-08, both match the current stable PyPI releases, so there is **no actionable Track-B toolchain upgrade at this refresh**.

Recheck authoritative upstream versions at B34 closeout or when an actual renderer/security issue makes currency relevant. Do not repeatedly spend context rechecking B33 between every asset gate.

A future upgrade is a separate serial integration task because raster bytes and generated provenance may change.

---

## 17. B34 — Track B closeout

### Failure domain

`TRACK_B_CONTINUATION_CLOSEOUT`

### Mode

Read-only.

### Primary criterion

On one current `origin/main` lineage:

- mandatory MVP visible assets have no actionable gap;
- source/packet/approval chain validates;
- atlas/registry/manifest/package provenance is current;
- deterministic rebuild proof is green;
- no unexplained B-owned generated diff remains;
- runtime-only defects are routed to Track A;
- no unreviewed actionable B toolchain/security gap remains.

Report:

```text
TRACK_B_CONTINUATION: <PASS or BLOCKED>
ORIGIN_MAIN: <sha>
MANDATORY_VISUAL_ASSETS: <PASS or BLOCKED>
APPROVAL_LINEAGE: <PASS or BLOCKED>
GENERATED_PROVENANCE: <PASS or BLOCKED>
DETERMINISM: <PASS or BLOCKED>
TOOLCHAIN_CURRENCY: <PASS or BLOCKED>
TRACK_A_HANDOFFS: <NONE or exact items>
REMAINING_B_GAP: <NONE or one exact gap>
```

Do not add a new validator/checklist solely to create closeout evidence.

---

# PART IV — EXECUTOR OPERATING CONTRACT

## 18. Git/worktree procedure

For mutation tasks follow current `AGENTS.md` and `agents/workflows/git.md`:

1. fetch current `origin/main`;
2. inspect semantic overlap since the previous task;
3. create one locked isolated task worktree under `.worktrees/game/<task-slug>`;
4. use that one CWD for editor, LSP, uv, browser, generators and tests;
5. preserve unrelated dirty state;
6. run the primary criterion before broader checks;
7. run only direct-impact verification next;
8. run required static/diff checks;
9. refresh `origin/main` before publication;
10. non-overlapping remote advance is not a blocker — reapply to latest main and rerun required focused verification;
11. publish by fast-forward to `origin/main`;
12. prove reachability;
13. unlock/remove only a clean, published, inactive worktree created by the current task.

Forbidden: PR/feature-branch workflow unless explicitly requested, force push/history rewrite, `--no-verify`, `/tmp` worktrees, `git worktree remove --force`, or full-suite reruns before the focused criterion.

---

## 19. Compact task card

Before editing:

```text
TASK_ID: Bxx
FAILURE_DOMAIN: <one domain>
HYPOTHESIS: <one falsifiable sentence>
PRIMARY_CRITERION: <one binary statement>
READ_SCOPE: <shared owner + direct siblings needed to rule out under-fixing>
WRITE_SCOPE: <bounded coherent package only>
FORBIDDEN: <adjacent roots/tracks>
BASELINE_OR_RED: <smallest decisive proof>
DIRECT_VERIFY: <directly affected checks>
STATIC_VERIFY: <required static/diff checks>
STOP_CONDITION: <exact stop point>
```

If the hypothesis or primary criterion cannot remain singular, split the task.

---

## 20. Final report schema

Allowed values:

- `RESULT`: `PASS`, `FAIL`, `BLOCKED`
- `PRIMARY_VERIFY`: `PASS`, `FAIL`, `NOT_RUN`
- `DIRECT_VERIFY`: `PASS`, `FAIL`, `NOT_RUN`
- `STATIC_VERIFY`: `PASS`, `FAIL`, `NOT_RUN`
- `PUBLISH`: `PUBLISHED`, `NOT_PUBLISHED`, `NOT_APPLICABLE`

```text
RESULT: <one allowed value>
FAILURE_DOMAIN: <exact domain>
CHANGE: <behavior/files or NONE>
PRIMARY_VERIFY: <one allowed value>
DIRECT_VERIFY: <one allowed value>
STATIC_VERIFY: <one allowed value>
PUBLISH: <one allowed value>
COMMIT: <sha or NONE>
DISCOVERED_FAILURE: <NONE or one/out-of-scope findings>
BLOCKER: <NONE or exact blocking fact>
```

`DISCOVERED_FAILURE` is not a status value and does not convert a valid current-task PASS into BLOCKED.

---

## 21. Context budget for Qwen3.6-class local models

For one invocation provide only:

- this runbook's live-state section;
- the selected Bxx section;
- the exact asset brief/candidate when applicable;
- current shared owner implementation needed by that hypothesis;
- one or two focused tests;
- only the relevant handoff/rendering spec paragraphs;
- refreshed `origin/main` SHA/status evidence.

Do not load completed B14–B21 details, the full predecessor runbooks, unrelated runtime consumers or the entire repository.

When a different failure domain appears, record it and stop instead of recursively expanding context.

---

## 22. Current next action

At the 2026-08-08 refresh, the continuation is waiting for exactly one external artifact:

```text
domains/ocean-rescue/assets/handoff/inbox/scene-seaweed-loop-02-01.svg
```

Until that file exists, B22 is `BLOCKED` and no Track B mutation is justified.

After the file is transferred, execute **B22 only**.
