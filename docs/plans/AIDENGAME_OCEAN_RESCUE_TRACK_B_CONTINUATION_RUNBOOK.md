# AidenGame Ocean Rescue — Track B Active Continuation Runbook

- Version: v1.1
- Date: 2026-08-07
- Status: ACTIVE
- Track: B — asset/content production, proof, approval, atlas, registry, manifest and packaging provenance
- Predecessor: `docs/plans/AIDENGAME_OCEAN_RESCUE_TRACK_B_EXECUTION_RUNBOOK.md`
- Status refresh baseline: `25887c30a8359a25b1df7ca5b7a70d5bc473ce25`

---

## 1. Current state at the status refresh baseline

The predecessor Track B execution runbook has already exercised the initial asset-pipeline integrity inventory and published its fixes. The continuation phase is not complete.

The current executable order is:

1. **B14 — OPEN / confirmed**: approval writer ↔ validator contact-sheet path round trip.
2. **B15 — OPEN / confirmed**: approved decision ↔ `visualReviewVerdict` coherence.
3. **B16 — PENDING HUMAN GATE**: explicit visual approval of the exact current committed contact sheet through the official approval writer.
4. **B20 — NOT YET ELIGIBLE**: mandatory visible-asset completeness inventory. Run only after B14–B16 are closed.
5. **B21–B28 — CONDITIONAL**: one-asset visual completion loop, only when B20 selects one concrete asset gap.
6. **B30–B33 — MAINTENANCE INVENTORIES**: placeholder audit, atlas integrity, package provenance, toolchain currency.
7. **B34 — FINAL CLOSEOUT**.

### Why B14 is confirmed open

Current `scripts/ocean_rescue/approve_art.py` still builds a missing `evidence` object with:

```text
contactSheet = ../review/proof-art-contact-sheet.html
```

Current `scripts/ocean_rescue/validate_art_approval.py` rejects evidence paths that escape above their root. The tracked `art-approval.json` is manually aligned to the canonical repository-relative path, but the official producer can still recreate a receipt that is inconsistent with the validator contract.

### Why B15 is confirmed open

The approval writer still uses `receipt.setdefault("evidence", ...)`, so an existing contradictory `visualReviewVerdict` can survive a new explicit approval action. The approval validator currently requires the field to exist but does not require the approved receipt's verdict to be exactly `PASS`.

### B16 current mechanical state

The tracked receipt currently reports 53 approved aliases and binds the packet, source set, and contact sheet hashes. Its `requiredPredecessor` is `311236d6ad872b787920610a2e52c7748901c99f`, while `approvalDate` remains `2026-08-02`.

Mechanical consistency is not equivalent to explicit human review of the exact current proof. B16 therefore remains a human gate after B14 and B15 are fixed.

### Changes after the continuation runbook was first added

The later Ocean Rescue commits at the refresh baseline modify Track A runtime code only (`travel.js` and `travel-scene.js`). They do not close B14 or B15 and do not authorize Track B to edit runtime behavior.

---

## 2. Authority and read order

Before every task, refresh and read the current `origin/main` versions of:

1. `AGENTS.md`
2. `PROJECT_RULES.md` when relevant to the touched surface
3. `docs/specs/technical/AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md`
4. `docs/specs/product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md`
5. `docs/plans/AIDENGAME_OCEAN_RESCUE_TRACK_B_EXECUTION_RUNBOOK.md`
6. this file
7. the exact implementation and focused tests named by the selected B task

Past completion reports and this file's baseline SHA are orientation evidence only. Current code/specs on refreshed `origin/main` decide the task.

---

## 3. Execution invariant

Every invocation executes exactly one independently decidable unit:

```text
one task
= one failure domain
= one falsifiable hypothesis
= one primary binary criterion
= one publication decision
```

Do not combine B14 and B15 because they touch the same files. They have different hypotheses and different decision criteria.

Do not continue automatically to the next B task after a PASS. Publish the current task, report evidence, clean up the worktree when allowed, and stop.

If an out-of-scope defect is found, record it under `DISCOVERED_FAILURE`; do not widen the current write scope.

---

## 4. Track B boundary

Track B owns the production chain from authored source through deterministic generated output:

- source/review/handoff SVG assets;
- art packet metadata, hashes and schema;
- structural/security validation of incoming authored assets;
- proof/contact-sheet generation;
- explicit human approval receipt mechanics;
- atlas generation and atlas metadata;
- render-asset registry/manifest generation;
- provenance and deterministic rebuild checks;
- B-side packaging provenance at the B → A boundary.

Track B does **not** own:

- gameplay FSM;
- mission controller behavior;
- pointer/input state machines;
- timers and pause/resume runtime behavior;
- runtime loader/renderer behavior after B's published contract is proven correct;
- gameplay tuning such as movement speed or screen effects.

A/B contract rule:

```text
B producer contract wrong  -> fix B only
B producer contract correct + runtime consumption wrong -> report and route to Track A
```

Never modify A runtime files merely to make a B test pass.

---

## 5. Git/worktree procedure

Use the current `AGENTS.md` contract.

For a mutation task:

1. `git fetch origin`
2. inspect the current `origin/main` SHA and relevant diff since the previous task
3. create a dedicated worktree under `/Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>`
4. create it locked with `git worktree add --lock --reason ...`
5. use the same worktree/CWD for editor, LSP, Python, browser, generators and tests
6. keep unrelated dirty state untouched
7. run the task's focused primary criterion first
8. run only direct-impact verification next
9. run required static/diff checks
10. check `origin/main` again immediately before publication
11. if remote advanced without semantic overlap, reapply to latest main and rerun the task's V1 plus required direct-impact checks; do not treat ordinary non-overlapping advance as a blocker
12. publish by fast-forward to `origin/main`
13. prove the commit is reachable from current `origin/main`
14. only if the worktree is clean, published, no longer active, and was created by this task: unlock it and remove it with plain `git worktree remove`

Forbidden:

- `/tmp`, `/private/tmp`, `$TMPDIR`, or `mktemp` worktrees;
- PR/feature-branch workflow unless the user explicitly requests it;
- force push/history rewrite;
- `git worktree remove --force`;
- deleting dirty/unpublished/active worktrees;
- full-suite reruns before the focused criterion unless an existing project command is itself the direct criterion.

---

## 6. Required task card

Before editing, write a compact task card:

```text
TASK_ID: Bxx
FAILURE_DOMAIN: <one domain>
HYPOTHESIS: <one falsifiable sentence>
PRIMARY_CRITERION: <one binary statement>
READ_SCOPE:
  - <minimum files/spec sections>
WRITE_SCOPE:
  - <minimum files allowed to change>
FORBIDDEN:
  - <adjacent surfaces explicitly excluded>
RED_OR_BASELINE: <smallest reproduction or proof of current state>
DIRECT_VERIFY: <smallest directly affected regression set>
STATIC_VERIFY: <required lint/type/diff checks>
STOP_CONDITION: <exact point to stop>
```

If the hypothesis cannot be stated in one sentence, split the task before coding.

---

# PART I — APPROVAL CONTRACT CARRY-OVER

## 7. B14 — Approval writer ↔ validator contact-sheet path round trip

### Failure domain

`APPROVAL_WRITER_VALIDATOR_EVIDENCE_PATH_ROUNDTRIP`

### Current hypothesis

When the official approval writer creates an `evidence` object from an empty/legacy receipt, it can emit a contact-sheet path that the official validator rejects or that is not the canonical proof path.

### Primary criterion

A receipt produced by the official writer uses exactly:

```text
domains/ocean-rescue/assets/review/proof-art-contact-sheet.html
```

and that writer-produced fixture passes the approval validator, while unsafe/noncanonical contact-sheet paths required by the contract remain rejected.

### Read scope

- `scripts/ocean_rescue/approve_art.py`
- `scripts/ocean_rescue/validate_art_approval.py`
- `tests/test_ocean_rescue_art_approval.py`
- `tests/test_ocean_rescue_approval_evidence_path_escape.py`
- the approval/proof section of the manual SVG handoff spec

### Write scope

Only the minimum needed from:

- `scripts/ocean_rescue/approve_art.py`
- `scripts/ocean_rescue/validate_art_approval.py` only if validator-side exact canonical-path enforcement is needed
- one focused approval regression test file

Do **not** modify canonical `art-approval.json` in B14.

### RED reproduction

Use isolated fixture data. Do not invoke live approval.

Preferred reproduction:

1. import/call the official writer's `build_receipt()` using the canonical packet plus an empty or legacy receipt;
2. assert the produced `evidence.contactSheet` value;
3. demonstrate the pre-fix value is `../review/proof-art-contact-sheet.html` or otherwise fails the canonical-path criterion.

A second focused case should prove the writer-produced fixture can be fed to the validator contract without rewriting canonical approval state.

### Correction rules

- Prefer one small canonical path constant or equivalent single owner.
- Do not introduce a schema framework, generic path abstraction, or broad receipt refactor.
- Do not fix B15 in the same task even if the nearby `setdefault` behavior is visible.

### Direct verification

Minimum evidence:

- writer-produced fixture contains the canonical contact-sheet path;
- writer-produced fixture satisfies the validator contract;
- `../review/...` remains rejected;
- absolute path remains rejected;
- escaping traversal remains rejected;
- current canonical approval validation remains green without changing the tracked receipt.

Suggested focused commands, adjusted to exact test names after implementation:

```bash
uv run pytest -q tests/test_ocean_rescue_approval_evidence_path_escape.py
uv run pytest -q tests/test_ocean_rescue_art_approval.py
uv run python scripts/ocean_rescue/validate_art_approval.py domains/ocean-rescue/assets/source
```

Do not run unrelated gameplay/browser suites for B14.

### B14 PASS condition

All required focused cases are green, the diff contains only the allowed approval-contract files/tests, static checks pass, and the task commit is published to `origin/main`.

Then stop. Do not start B15 in the same invocation.

---

## 8. B15 — Approved decision ↔ visual verdict coherence

### Failure domain

`APPROVAL_DECISION_VISUAL_VERDICT_INCONSISTENCY`

### Current hypothesis

An approved receipt can retain or validate a non-`PASS` `visualReviewVerdict` because the writer preserves an existing evidence object and the validator only checks field presence.

### Primary criterion

For `decision == "approved"`:

1. the official writer always emits `evidence.visualReviewVerdict == "PASS"` for the explicit approval action; and
2. the official validator rejects approved receipts whose verdict is missing, blank, `FAIL`, `REJECTED`, or any value other than exact `PASS`.

### Read scope

- current post-B14 `approve_art.py`
- current post-B14 `validate_art_approval.py`
- focused approval tests
- human-approval contract in the handoff spec

### Write scope

Only:

- approval writer and/or validator required for this criterion;
- one focused test file.

Do not modify the canonical approval receipt in B15.

### RED reproduction

Create isolated fixtures with an otherwise valid approved receipt and vary only `evidence.visualReviewVerdict`.

At least one pre-fix case must demonstrate acceptance/preservation of a contradictory verdict.

Writer-side reproduction should also begin from an existing evidence object containing a stale contradictory verdict and prove that the explicit approval operation currently preserves it.

### Correction rules

- Preserve unrelated evidence fields only when the contract requires them.
- Explicit approval must own the resulting approval verdict; stale contradictory state cannot override that action.
- Do not use B15 to redesign approval date semantics, predecessor semantics, or packet hashes.

### Direct verification

Required cases:

- exact `PASS` accepted;
- missing verdict rejected;
- empty/whitespace verdict rejected;
- `FAIL` rejected;
- `REJECTED` rejected;
- writer from stale contradictory evidence emits exact `PASS`;
- unrelated required evidence fields remain intact;
- canonical receipt validator remains green without rewriting it.

Run focused approval tests first, then the direct canonical validator command.

### B15 PASS condition

Only decision/verdict coherence is changed and independently verified/published.

Then stop. Do not execute B16 automatically.

---

## 9. B16 — Exact current contact-sheet human approval provenance

### Failure domain

`CURRENT_CONTACT_SHEET_HUMAN_APPROVAL_PROVENANCE`

### Mode

Human gate. This is not an autonomous code-fix task.

### Precheck

After B14 and B15 are published, refresh `origin/main` and report read-only:

- current `origin/main` SHA;
- current packet SHA-256;
- current source-set SHA-256;
- current contact-sheet SHA-256;
- current `art-approval.json` values;
- commit that contains the exact current proof/contact sheet.

Do not change files during the precheck.

### Human gate

The user must explicitly state that the exact identified committed contact sheet has been visually reviewed and accepted.

Do not infer approval from:

- a validator PASS;
- deterministic generation;
- a previous approval message referring to an older sheet;
- a local agent report;
- matching hashes alone.

If explicit approval is absent, report `RESULT: BLOCKED` for B16 with `CHANGE: NONE`, `PRIMARY_VERIFY: NOT_RUN`, and `PUBLISH: NOT_APPLICABLE`.

### After explicit human approval

Use the official approval writer. Do not manually edit `art-approval.json`.

Verify that the generated receipt has:

- exact current packet hash;
- exact current source-set hash;
- exact current contact-sheet hash;
- `requiredPredecessor` pointing to the committed reviewed lineage required by the tool/spec;
- canonical contact-sheet evidence path;
- exact `visualReviewVerdict: PASS`;
- tool-generated approval date;
- all 53 current aliases or the current packet's exact alias count/parity if the packet legitimately changed before the gate.

Then run the canonical approval validator and direct approval regression tests.

### B16 PASS condition

The tool-generated receipt for the explicitly reviewed exact proof is published and validates. Then stop.

---

# PART II — VISUAL COMPLETION LOOP

## 10. B20 — Mandatory visible-asset completeness inventory

Run only after B14, B15 and B16 are independently closed.

### Failure domain

`MANDATORY_VISIBLE_ASSET_COMPLETENESS_INVENTORY`

### Mode

Read-only selection task.

### Primary criterion

Every mandatory visible asset in the current Rendering MVP maps to exactly one current packet entry with:

- canonical source bytes present;
- valid source hash;
- approved asset state;
- expected bundle membership;
- stable alias;
- proof/contact-sheet representation sufficient for current MVP review.

If all are complete, report no actionable gap.

If not, select exactly one highest-priority asset gap and report:

- asset ID/alias;
- exact observed deficiency;
- exact authoritative expected state;
- one binary visual acceptance criterion;
- whether the next action is B21.

Do not alter SVGs, packet, atlas, registry, approval receipt or runtime in B20.

---

## 11. B21 — One-asset handoff brief

Run only when B20 selected one concrete asset gap.

### Failure domain

`<ASSET_ALIAS>_VISUAL_HANDOFF_CONTRACT`

Produce one bounded brief containing:

- asset ID and stable alias;
- canonical destination path;
- target atlas bundle;
- intended display/proof scale;
- current source reference when revising an asset;
- one visual deficiency only;
- one binary acceptance criterion;
- silhouette/readability requirement;
- palette/style continuity constraints;
- forbidden external SVG features/references;
- structural SVG constraints from the current handoff contract;
- exact inbox filename/path;
- focused structural/proof commands;
- explicit note that human visual approval is still required.

Local coding LLMs must not invent/redraw frontier-quality final geometry merely to close B21.

Publish the brief if repository documentation is the authorized handoff mechanism, then stop.

---

## 12. B22 — One-asset inbox structural acceptance

Run after the exact candidate exists in the handoff inbox.

### Failure domain

`<ASSET_ALIAS>_HANDOFF_SVG_STRUCTURAL_ACCEPTANCE`

### Primary criterion

The exact candidate passes the sanctioned SVG structure/security/renderability contract.

Validate only the candidate and its declared contract. Do not canonicalize it.

If invalid, report the first decisive structural failure domain and stop. Do not redraw the asset locally.

---

## 13. B23 — One-asset actual-size proof

### Failure domain

`<ASSET_ALIAS>_ACTUAL_SIZE_VISUAL_PROOF`

### Primary criterion

A deterministic proof derived from the exact candidate bytes exists at the intended viewing size/context for human judgment.

Do not approve, canonicalize or hand-edit a substitute raster.

Stop for human review.

---

## 14. B24 — One-asset human visual gate and canonicalization

### Failure domain

`<ASSET_ALIAS>_HUMAN_VISUAL_ACCEPTANCE`

The user must explicitly accept or reject the exact B23 proof/candidate.

If rejected, do not canonicalize. Return to a new single-asset revision cycle.

If explicitly accepted:

- promote exactly the accepted bytes to the canonical source path;
- update only the packet fields required for that asset's actual bytes/metadata;
- do not claim the old global approval receipt remains current.

### Primary criterion

The exact human-accepted candidate is canonical and the packet records its exact current bytes without unrelated asset changes.

Publish and stop.

---

## 15. B25 — Rebuild affected generated pipeline

### Failure domain

`<ASSET_ALIAS>_GENERATED_PIPELINE_REBUILD`

Rebuild through existing producers only. Never hand-edit generated outputs.

As applicable, prove in producer order:

1. packet validation;
2. contact-sheet clean rebuild;
3. atlas generation;
4. atlas validation;
5. registry/manifest generation and provenance;
6. generated-artifact drift checks;
7. second clean rebuild byte identity for affected generated surfaces;
8. B-side package provenance.

The old human approval receipt is expected to become stale after source/proof change. Do not manually repair it in B25.

Stop when generation is correct and fresh human reapproval is the only expected remaining approval consequence.

---

## 16. B26 — Reapprove rebuilt visual packet

### Failure domain

`REBUILT_PACKET_HUMAN_APPROVAL`

Repeat the B16 human boundary for the new exact committed proof.

No automatic approval. No manual hash patching. No reuse of an old approval date/verdict as evidence for new bytes.

Publish only the official writer's new receipt and stop.

---

## 17. B27 — B → A handoff evidence for changed asset

### Failure domain

`<ASSET_ALIAS>_B_TO_A_RENDER_HANDOFF`

### Primary criterion

The changed approved asset is present under the expected alias/bundle/registry/package with the correct B-side source lineage and can be resolved through the existing producer contract.

If that passes but the actual runtime still renders/behaves incorrectly, report:

```text
B_PRODUCER_CONTRACT: PASS
A_CONSUMER_FAILURE: <exact runtime observation>
B_CHANGE_REQUIRED: NO
ROUTE: TRACK_A
```

Do not patch A runtime in B27.

---

## 18. B28 — Select next visual gap

Read-only. Re-run B20 inventory on fresh `origin/main` and choose at most one next gap.

If none exists, the visual completion loop is complete.

Do not begin the next B21 in the same invocation.

---

# PART III — MAINTENANCE INVENTORIES

## 19. B30 — Authored-versus-placeholder audit

### Failure domain

`PRIMARY_VISIBLE_ASSET_PLACEHOLDER_AUDIT`

Read-only first.

Determine whether any mandatory current-MVP visible asset still uses a procedural/placeholder representation where the active contract requires authored art.

If one exists, report exactly one and route it into B21. Do not mass-replace assets.

---

## 20. B31 — Atlas resource/integrity inventory

### Failure domain

`ATLAS_RESOURCE_BUDGET_INVENTORY`

Inspect only already-authorized constraints such as:

- page dimensions;
- bundle membership;
- frame bounds;
- trim/padding metadata integrity;
- duplicate/missing aliases;
- toolchain provenance;
- deterministic output.

Do not invent new density, waste, page-count or aesthetic thresholds.

If a concrete contract violation is reproduced, stop and open one serial task for that violation only.

---

## 21. B32 — Offline/package provenance inventory

### Failure domain

`B_PACKAGE_PROVENANCE_INVENTORY`

### Primary criterion

The packaged B asset payload is derived from the current approved source lineage and does not require network retrieval for B-owned asset data.

Inspect B build/package metadata only. Runtime network/loader behavior belongs to Track A after the B package contract is proven correct.

---

## 22. B33 — Toolchain currency inventory

### Failure domain

`OCEAN_RESCUE_ART_TOOLCHAIN_CURRENCY`

Read-only by default.

At this v1.1 refresh, repository pins are:

- CairoSVG `2.9.0`
- Pillow `12.3.0`

For each execution:

1. read current repo pins;
2. check authoritative upstream stable versions;
3. inspect security/reliability relevance;
4. report `NO_ACTIONABLE_GAP` if current;
5. if an upgrade exists, do not upgrade inside the inventory task;
6. create a separate serial toolchain-upgrade task because output pixels, manifests and root dependency metadata may change.

Any real renderer/toolchain upgrade must use isolated candidate rebuilds, output/pixel diff classification and deterministic rebuild proof before publication.

---

## 23. B34 — Track B continuation closeout

### Failure domain

`TRACK_B_CONTINUATION_CLOSEOUT`

Read-only.

### Primary criterion

All of these must be true on one current `origin/main` lineage:

- B14 writer/validator path round trip closed;
- B15 approved/verdict coherence closed;
- B16 explicit human approval provenance current;
- mandatory MVP visible-asset inventory has no actionable gap;
- source/packet/approval chain validates;
- atlas/registry/manifest/package provenance current;
- deterministic rebuild evidence green;
- no unexplained B-owned generated diff remains;
- runtime-only defects are routed to Track A rather than patched from B;
- B33 has no unreviewed actionable toolchain/security gap.

Closeout report:

```text
TRACK_B_CONTINUATION: <PASS or BLOCKED>
ORIGIN_MAIN: <sha>
APPROVAL_LINEAGE: <PASS or BLOCKED>
MANDATORY_VISUAL_ASSETS: <PASS or BLOCKED>
GENERATED_PROVENANCE: <PASS or BLOCKED>
DETERMINISM: <PASS or BLOCKED>
TOOLCHAIN_CURRENCY: <PASS or BLOCKED>
TRACK_A_HANDOFFS: <NONE or exact items>
REMAINING_B_GAP: <NONE or one exact gap>
```

Do not add a new validator/checklist solely to manufacture a closeout artifact.

---

# PART IV — LOCAL LLM EXECUTION GUIDE

## 24. Task selection without a separate prompt

If a local executor receives only this runbook:

1. refresh `origin/main`;
2. read §2 authority documents;
3. inspect whether B14 is already independently closed by newer code;
4. if B14 is open, execute B14 only;
5. else inspect B15 and execute B15 only if open;
6. else perform the B16 precheck only;
7. if B16 needs human approval, stop `BLOCKED` without mutation;
8. after B16 is proven closed, select the earliest eligible B20+ task;
9. execute exactly one task;
10. publish only if the task's own criterion passes;
11. report using §25;
12. stop.

Never infer that a numbered task is complete merely because a previous chat said PASS. Use current code, tests, artifacts and `origin/main` reachability.

---

## 25. Final report schema

Allowed values:

- `RESULT`: exactly one of `PASS`, `FAIL`, `BLOCKED`
- `PRIMARY_VERIFY`: exactly one of `PASS`, `FAIL`, `NOT_RUN`
- `DIRECT_VERIFY`: exactly one of `PASS`, `FAIL`, `NOT_RUN`
- `STATIC_VERIFY`: exactly one of `PASS`, `FAIL`, `NOT_RUN`
- `PUBLISH`: exactly one of `PUBLISHED`, `NOT_PUBLISHED`, `NOT_APPLICABLE`

Report:

```text
RESULT: <one allowed value>
FAILURE_DOMAIN: <exact domain>
CHANGE: <concise behavior/files or NONE>
PRIMARY_VERIFY: <one allowed value>
DIRECT_VERIFY: <one allowed value>
STATIC_VERIFY: <one allowed value>
PUBLISH: <one allowed value>
COMMIT: <sha or NONE>
DISCOVERED_FAILURE: <NONE or out-of-scope observations>
BLOCKER: <NONE or blocking fact>
```

`DISCOVERED_FAILURE` does not convert a valid current-task PASS into BLOCKED. `BLOCKER` is required when `RESULT: BLOCKED`.

---

## 26. Context budget for Qwen3.6-class local models

Do not load the entire repository.

For one B task, provide only:

- the selected task section from this runbook;
- current implementation file(s) named by that task;
- one or two focused tests;
- only the relevant spec paragraphs;
- current `origin/main` SHA/status evidence.

Read adjacent surfaces only to decide the same hypothesis. Do not recursively load runtime consumers just because they mention the same asset alias.

When a new failure domain appears, record it and stop rather than expanding context and write scope indefinitely.

---

## 27. Final invariant

Track B is complete only when its producer, proof, explicit human approval boundary, generated lineage and package handoff all agree on the same authoritative bytes.

For every concrete defect:

```text
isolate one failure domain
→ reproduce or prove current state
→ change only that domain
→ verify the one primary criterion
→ verify direct impact
→ publish
→ stop
```

That sequence is the default for the remainder of Track B.
