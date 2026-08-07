# AidenGame Ocean Rescue — Track B Continuation Runbook

- Version: v1.0
- Date: 2026-08-07
- Status: ACTIVE
- Track: B — asset/content production, proof, approval, atlas, registry and packaging provenance
- Predecessor: `docs/plans/AIDENGAME_OCEAN_RESCUE_TRACK_B_EXECUTION_RUNBOOK.md`
- Review baseline: `8c28208ddaacde5490a4eea0741416de5231e90f`

---

## 1. Purpose

This runbook starts after the first Track B execution runbook and its eight maintenance-inventory surfaces have been exercised.

It has two jobs, in this order:

1. close concrete approval-provenance gaps discovered by frontier review of the completed runbook;
2. continue Ocean Rescue Track B through one-asset-at-a-time visual completion and deterministic publication.

Do not skip the approval-provenance carry-over tasks just because the current tracked `art-approval.json` passes validation.

A tracked artifact being green is not sufficient if the official producer can recreate an invalid or semantically inconsistent artifact.

---

## 2. Authoritative documents to read before work

Read the current `origin/main` versions of:

1. `AGENTS.md`
2. `docs/plans/AIDENGAME_OCEAN_RESCUE_TRACK_B_EXECUTION_RUNBOOK.md`
3. `docs/specs/technical/AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md`
4. `docs/specs/product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md`
5. this continuation runbook

If these disagree, follow the higher-authority/current project contract and report the exact disagreement before editing.

Do not use the baseline SHA above as a frozen implementation target. Always refresh `origin/main` first.

---

## 3. Non-negotiable execution model

Every invocation performs exactly one task.

```text
one task
= one failure domain
= one testable hypothesis
= one binary primary criterion
= one publication decision
```

Never combine independent defects because they are nearby.

Never continue automatically into the next Bxx task after the current Bxx task is complete.

After each task:

1. publish if and only if that task passed all required checks;
2. report the exact evidence;
3. stop.

A later invocation refreshes `origin/main` and chooses the next eligible task.

---

## 4. Track boundary

Track B owns:

- SVG handoff and source assets;
- art-packet metadata and source hashes;
- proof/contact-sheet generation;
- explicit human approval receipt mechanics;
- atlas generation and validation;
- generated render-asset registry provenance;
- deterministic generated-artifact rebuilds;
- packaging provenance at the B → A boundary.

Track B does not own:

- gameplay FSM;
- mission controller behavior;
- pointer/input state machines;
- timers;
- runtime interaction logic;
- runtime alias-consumer bugs when B output is proven correct.

If B outputs pass their producer contract but the runtime fails, report the exact consumer failure and route it to Track A without patching runtime code.

---

## 5. Human visual approval boundary

Human approval is not inferable from:

- a file existing;
- a hash matching;
- a validator passing;
- a generated contact sheet being deterministic;
- a local agent saying `PASS`;
- a previous approval receipt whose fields were later rewritten.

Only an explicit human review of the exact current committed proof/contact sheet authorizes approval of that visual state.

Local agents must never fabricate or infer that approval.

The official approval command may be invoked only after the user explicitly confirms that the exact current committed contact sheet has been reviewed and accepted.

---

## 6. Git/worktree discipline

Follow current `AGENTS.md` exactly.

Default operating pattern:

1. `git fetch origin`
2. inspect current `origin/main`
3. create/use an isolated disposable worktree from that current commit
4. keep the task diff limited to its allowed scope
5. verify the single hypothesis
6. commit intentionally
7. publish fast-forward to `origin/main`
8. confirm the commit is reachable from `origin/main`
9. remove the disposable worktree when it is clean, published and no longer active

Do not create a PR or long-lived feature branch for this runbook.

Do not delete dirty, unpublished or active worktrees.

---

## 7. Required task card

Before editing, write this compact task card locally:

```text
TASK_ID: Bxx
FAILURE_DOMAIN: <one domain>
HYPOTHESIS: <one falsifiable sentence>
PRIMARY_CRITERION: <one binary pass/fail statement>
READ_SCOPE:
  - <files/specs needed to understand the domain>
WRITE_SCOPE:
  - <minimum files allowed to change>
FORBIDDEN:
  - <explicit adjacent surfaces not to modify>
RED_REPRODUCTION: <smallest command/fixture proving the gap>
DIRECT_VERIFY: <smallest direct regression set>
STATIC_VERIFY: <diff/static checks>
STOP_CONDITION: <exact point to stop>
```

If the hypothesis cannot be stated in one sentence, the task is too broad.

---

## 8. Standard final report

Every local execution must end with exactly these fields:

```text
RESULT: PASS | FAIL | BLOCKED
FAILURE_DOMAIN: <exact domain>
CHANGE: <concise changed behavior/files or NONE>
PRIMARY_VERIFY: PASS | FAIL | NOT_RUN
DIRECT_VERIFY: PASS | FAIL | NOT_RUN
STATIC_VERIFY: PASS | FAIL | NOT_RUN
PUBLISH: PUBLISHED | NOT_PUBLISHED | NOT_APPLICABLE
COMMIT: <sha or NONE>
DISCOVERED_FAILURE: NONE | <one or more out-of-scope observations>
BLOCKER: NONE | <blocking fact; required when RESULT=BLOCKED>
```

Each status field must contain one mutually exclusive value only.

`DISCOVERED_FAILURE` is not itself a reason to change an otherwise valid `PASS` into `BLOCKED`.

---

# PART I — REVIEW CARRY-OVER

## 9. B14 — Approval writer ↔ validator contact-sheet path round trip

### Failure domain

`APPROVAL_WRITER_VALIDATOR_EVIDENCE_PATH_ROUNDTRIP`

### Confirmed review observation

The official approval writer currently has a default evidence path:

```text
../review/proof-art-contact-sheet.html
```

The approval validator rejects root-level `..` path traversal.

The tracked receipt may currently be manually aligned to the canonical repository-relative path, but that does not close the producer contract if the official writer can recreate the rejected value.

### Hypothesis

A receipt produced by the official approval writer from an empty or legacy evidence object can contain a contact-sheet evidence path that the official approval validator rejects or that is not the canonical contact-sheet path.

### Primary criterion

The official writer must produce the canonical repository-relative contact-sheet evidence path, and the validator must accept that writer-produced receipt while rejecting noncanonical/unsafe contact-sheet paths required by the contract.

### Read scope

- `scripts/ocean_rescue/approve_art.py`
- `scripts/ocean_rescue/validate_art_approval.py`
- `tests/test_ocean_rescue_art_approval.py`
- `tests/test_ocean_rescue_approval_evidence_path_escape.py`
- canonical handoff spec

### Write scope

Only the minimum of:

- `scripts/ocean_rescue/approve_art.py`
- `scripts/ocean_rescue/validate_art_approval.py` if exact canonical-path validation is actually needed to make writer/validator symmetric
- one focused approval test file

Do not change the live `art-approval.json` in this task.

### RED reproduction

Use a temporary/isolated fixture. Do not invoke live human approval.

Prove at least one of these on the pre-fix implementation:

1. `build_receipt()` with no pre-existing `evidence` writes `../review/proof-art-contact-sheet.html`; or
2. an official-writer-produced fixture fails `validate_art_approval.py`; or
3. a safe but wrong contact-sheet evidence path is accepted even though the receipt claims canonical proof evidence.

The reproduction must not rewrite canonical approval state.

### Expected correction

Prefer one canonical path constant or equivalent single source inside the approval producer/validator contract rather than two drifting literals.

The canonical evidence value is:

```text
domains/ocean-rescue/assets/review/proof-art-contact-sheet.html
```

Do not introduce a new framework, schema layer or generic path library for this one gap.

### Direct verification

Run only focused approval tests first.

Minimum proof:

- writer-produced fixture contains canonical path;
- writer-produced fixture passes validator;
- `../review/...` is rejected;
- absolute/traversal evidence remains rejected;
- canonical live approval validation remains green without rewriting it.

### Stop condition

Stop after this round-trip contract is independently green and published.

Do not proceed to B15 in the same invocation.

---

## 10. B15 — Approved decision ↔ visual review verdict coherence

### Failure domain

`APPROVAL_DECISION_VISUAL_VERDICT_INCONSISTENCY`

### Confirmed review observation

The approval validator currently requires the `visualReviewVerdict` field to exist but does not prove that an approved receipt's verdict is exactly `PASS`.

The approval writer also preserves an existing `evidence` object wholesale via `setdefault`, so a stale verdict can survive a new `--approve` invocation.

### Hypothesis

A receipt with:

```text
decision = approved
visualReviewVerdict != PASS
```

can remain accepted or can be reproduced by the official approval path.

### Primary criterion

For an approved receipt:

- the validator rejects every non-`PASS` visual verdict;
- a genuine explicit `--approve` operation writes `visualReviewVerdict: PASS` rather than preserving a stale contradictory value.

### Read scope

- approval writer
- approval validator
- focused approval tests
- manual SVG handoff spec human-approval section

### Write scope

Only the approval writer/validator and one focused test as required by this failure domain.

Do not update canonical `art-approval.json` here.

### RED reproduction

Create a fixture based on current canonical receipt with only:

```json
"visualReviewVerdict": "REJECTED"
```

or another non-`PASS` value.

Run the approval validator.

The task is confirmed only if the contradictory approved receipt is accepted, or if writer behavior demonstrably preserves that contradictory verdict on explicit approval.

If the current code has already moved and both paths are safe, make no change and report `PASS` with the direct evidence.

### Direct verification

Required focused cases:

- `PASS` verdict accepted;
- missing verdict rejected;
- `REJECTED`/`FAIL`/blank verdict rejected;
- explicit writer receipt produces `PASS`;
- unrelated evidence fields required by the contract remain intact.

### Stop condition

Stop after decision/verdict coherence alone is green and published.

---

## 11. B16 — Current contact sheet human-approval provenance

### Failure domain

`CURRENT_CONTACT_SHEET_HUMAN_APPROVAL_PROVENANCE`

### Current review baseline fact

At review baseline `8c28208`, the tracked receipt binds:

- `requiredPredecessor` to the current regenerated contact-sheet lineage;
- `contactSheetSha256` to the current tracked sheet;
- `approvalDate` to `2026-08-02`.

Repository evidence alone cannot prove that a human re-reviewed the exact regenerated sheet before those fields were realigned.

### Hypothesis

The current receipt's mechanical integrity may be green while explicit human approval of the exact current contact sheet is not independently evidenced by the current official approval action.

### Primary criterion

The exact current committed contact sheet is explicitly reviewed by the user and, only after that explicit approval, the official approval writer regenerates the receipt; then the approval validator passes against that exact lineage.

### Mode

This is a human gate, not an autonomous code-fix task.

### Read-only precheck

Refresh `origin/main` and show:

- current contact-sheet blob/hash;
- current packet hash;
- current source-set hash;
- current receipt values;
- commit containing the exact reviewed contact sheet.

Do not modify anything during the precheck.

### Human gate

If the user has not explicitly said that the exact current sheet was visually reviewed and accepted:

```text
RESULT: BLOCKED
CHANGE: NONE
PRIMARY_VERIFY: NOT_RUN
PUBLISH: NOT_APPLICABLE
BLOCKER: explicit human visual approval of current committed contact sheet is required
```

Do not infer approval from previous messages saying the pipeline is technically complete.

### After explicit human approval

Invoke the official approval writer, not a manual JSON edit.

Then verify:

- receipt date is generated by the tool;
- predecessor is the commit containing the reviewed source/packet/sheet state;
- packet, source-set and contact-sheet hashes match;
- canonical evidence path is present;
- visual verdict is `PASS`;
- approval validator passes.

### Stop condition

Stop once the human-approved current lineage is recorded and published.

---

# PART II — VISUAL COMPLETION LOOP

## 12. B20 — Mandatory visible-asset completeness inventory

### Failure domain

`MANDATORY_VISIBLE_ASSET_COMPLETENESS_INVENTORY`

### Purpose

After B14–B16 are closed, identify whether the Rendering MVP still contains any mandatory primary visible asset that is missing, placeholder-grade, unapproved, incorrectly aliased, or materially below the current intended proof standard.

This task is read-only.

### Primary criterion

Every mandatory first-slice visible asset required by the current Rendering MVP is mapped to one canonical packet entry with a valid source, expected bundle, stable alias and approved state; otherwise identify exactly one highest-priority concrete gap.

### Read scope

- Rendering MVP mandatory asset list
- art-packet
- canonical source directories
- current contact sheet
- handoff briefs
- atlas manifest/registry aliases as needed for parity

### Forbidden

- no SVG changes;
- no packet edits;
- no atlas rebuild;
- no runtime changes;
- no speculative expansion into missions explicitly excluded from current rendering MVP.

### Output

If complete:

```text
RESULT: PASS
CHANGE: NONE
PRIMARY_VERIFY: PASS
DISCOVERED_FAILURE: NONE
```

If one concrete visual gap exists, report it as `DISCOVERED_FAILURE` with:

- asset alias/id;
- exact observed deficiency;
- authoritative expected state;
- smallest visual criterion that would close it.

Do not fix it in B20.

### Stop condition

Stop after inventory and one-gap selection.

---

## 13. B21 — One-asset handoff brief

Run only when B20 identified one concrete visual-asset gap.

### Failure domain

`<ASSET_ALIAS>_VISUAL_HANDOFF_CONTRACT`

### Hypothesis

A precise one-asset brief can state the visual deficiency and acceptance criterion without requiring the local coding agent to invent final geometry.

### Primary criterion

One handoff brief exists for exactly one asset/revision and contains enough bounded information for the frontier visual author to produce a candidate without touching unrelated assets.

### Brief must contain

- asset ID and stable alias;
- canonical destination path;
- target atlas bundle;
- intended display size / proof scale;
- current source reference if revising an existing asset;
- exactly one visual failure domain;
- one binary visual acceptance criterion;
- silhouette/readability requirements;
- palette/style continuity constraints;
- forbidden external references/features;
- required SVG structural constraints;
- expected handoff inbox filename;
- focused validation/proof commands;
- explicit statement that human visual approval is still required.

### Forbidden

The local LLM must not author or redraw frontier-level final SVG geometry in this task.

### Stop condition

Publish the brief and stop for frontier/human asset production.

---

## 14. B22 — One-asset inbox structural acceptance

Run only after the user/frontier visual author has placed the exact candidate SVG in the handoff inbox.

### Failure domain

`<ASSET_ALIAS>_HANDOFF_SVG_STRUCTURAL_ACCEPTANCE`

### Primary criterion

The one candidate satisfies the current handoff SVG structural/security contract and is renderable by the sanctioned toolchain.

### Procedure

1. validate only the candidate and its expected contract;
2. prove expected root namespace/viewBox/IDs/references/security constraints;
3. render a mechanical proof if required by the existing handoff workflow;
4. do not canonicalize yet.

If invalid, produce one revision request describing the first decisive failure domain and stop.

Do not redraw the asset locally to make it pass.

---

## 15. B23 — One-asset actual-size proof

### Failure domain

`<ASSET_ALIAS>_ACTUAL_SIZE_VISUAL_PROOF`

### Primary criterion

A deterministic proof of the candidate exists at the intended viewing size/context needed for human visual judgment.

### Rules

- proof generation is allowed;
- proof content must come from the candidate bytes, not a hand-edited raster substitute;
- do not mark the candidate approved;
- do not canonicalize the candidate;
- do not rebuild global approval state.

### Stop condition

Publish only proof artifacts that are authoritative outputs of the existing workflow, then stop for human review.

---

## 16. B24 — One-asset human visual gate and canonicalization

### Failure domain

`<ASSET_ALIAS>_HUMAN_VISUAL_ACCEPTANCE`

### Human gate

The user must explicitly accept or reject the exact candidate/proof.

If rejected:

- do not canonicalize;
- do not modify packet approval metadata;
- return to a new one-asset revision brief/task.

If explicitly accepted:

- copy/promote only the accepted bytes to the canonical source path according to the handoff spec;
- update only the packet fields required for that one asset's new bytes/metadata;
- do not claim global approval receipt remains current after source or proof changes.

### Primary criterion

The exact human-accepted candidate is the canonical asset and the packet records its actual bytes/hash without unrelated asset changes.

### Stop condition

Stop after canonical source + packet state for that one asset is correct and published.

---

## 17. B25 — Rebuild affected generated asset pipeline

### Failure domain

`<ASSET_ALIAS>_GENERATED_PIPELINE_REBUILD`

### Hypothesis

The accepted canonical source can pass through the existing producer chain deterministically without hand-editing generated outputs.

### Primary criterion

The affected atlas/manifest/registry/contact-sheet outputs are regenerated from authoritative inputs, validate successfully, and a second clean rebuild is byte-identical for the affected generated surfaces.

### Required order

Use the existing producer order from the predecessor runbook. Do not invent a new generator.

At minimum prove as applicable:

1. art-packet validation;
2. contact-sheet clean rebuild;
3. atlas generation;
4. atlas validation;
5. registry generation/provenance;
6. generated-artifact drift/determinism;
7. packaging provenance at the B boundary.

### Important

A source/contact-sheet change intentionally makes the previous human approval receipt stale.

Do not manually patch the receipt in B25.

The stale approval receipt is expected until B26.

### Stop condition

Stop when generated outputs are correct and the only expected approval-state consequence is the need for fresh explicit human review.

---

## 18. B26 — Reapprove the rebuilt visual packet

### Failure domain

`REBUILT_PACKET_HUMAN_APPROVAL`

### Primary criterion

The user explicitly reviews the exact current committed contact sheet after the asset change, then the official approval writer records that approval and the validator passes.

### Forbidden

- no automatic approval;
- no manual hash editing;
- no carrying forward an old approval date/verdict as proof of the new visual state.

### Stop condition

Publish the tool-generated approval receipt and stop.

---

## 19. B27 — B → A actual runtime handoff evidence for the changed asset

### Failure domain

`<ASSET_ALIAS>_B_TO_A_RENDER_HANDOFF`

### Purpose

Prove that B's published output is discoverable and packaged under the expected alias/provenance at the runtime boundary.

This is not a gameplay-fix task.

### Primary criterion

The changed asset is present in the expected generated bundle/registry/package with the approved source lineage and can be resolved by the existing B-side handoff contract.

### If runtime behavior fails

If B evidence is correct but runtime rendering/interaction is wrong:

```text
B_PRODUCER_CONTRACT: PASS
A_CONSUMER_FAILURE: <exact observation>
B_CHANGE_REQUIRED: NO
ROUTE: TRACK_A
```

Do not cross the track boundary.

---

## 20. B28 — Select next visual asset, if any

This is a read-only selection task.

Re-run the mandatory visible-asset completeness inventory against the new `origin/main`.

Choose at most one next gap.

If none exists, visual completion loop is done.

Do not start B21 for the next asset in the same invocation.

---

# PART III — MAINTENANCE AFTER VISUAL COMPLETION

## 21. B30 — Authored-versus-placeholder audit

### Failure domain

`PRIMARY_VISIBLE_ASSET_PLACEHOLDER_AUDIT`

### Primary criterion

No mandatory primary visible asset in the current Rendering MVP relies on procedural/placeholder representation where the active product contract requires authored art.

Read-only first.

If one real placeholder gap is found, report exactly one candidate and route it back to the B21 one-asset loop.

Do not mass-replace assets.

---

## 22. B31 — Atlas budget/integrity inventory

### Failure domain

`ATLAS_RESOURCE_BUDGET_INVENTORY`

Read-only unless a concrete contract violation is reproduced.

Check only limits already authorized by current specs/validators, such as:

- atlas page dimensions;
- declared bundle membership;
- frame bounds;
- trim/padding metadata integrity;
- duplicate/missing aliases;
- current toolchain provenance;
- deterministic output.

Do not invent new density, waste-percentage or page-count thresholds merely because they seem desirable.

If a concrete violation exists, open one new task for that single violation.

---

## 23. B32 — Offline/package provenance inventory

### Failure domain

`B_PACKAGE_PROVENANCE_INVENTORY`

### Primary criterion

The packaged B asset payload is derived from the current approved source lineage and does not require runtime network retrieval for its asset data.

This task may inspect packaging outputs and B-owned build metadata.

Do not edit runtime behavior.

If an offline/network failure originates from runtime application code rather than B packaging, route it to Track A.

---

## 24. B33 — Toolchain currency check

### Failure domain

`OCEAN_RESCUE_ART_TOOLCHAIN_CURRENCY`

This is read-only by default.

Current sanctioned exact pins at the time this runbook was written:

- CairoSVG `2.9.0`
- Pillow `12.3.0`

An upstream release does not authorize an automatic upgrade.

For every currency check:

1. determine current sanctioned repo pins;
2. determine current upstream stable releases from authoritative sources;
3. inspect security/reliability relevance;
4. if pins are current, report `NO_ACTIONABLE_GAP`;
5. if a candidate upgrade exists, do not perform it in the inventory task;
6. create a separate serial upgrade task because renderer/toolchain changes may alter pixel output and root dependency metadata.

A real upgrade task must preserve the predecessor runbook's requirements for isolated candidate rebuild, pixel/output diff classification and deterministic proof.

---

## 25. B34 — Continuation closeout

### Failure domain

`TRACK_B_CONTINUATION_CLOSEOUT`

This task is read-only.

### Primary criterion

All of the following are true on the same current `origin/main` lineage:

- B14 writer/validator round trip is closed;
- B15 decision/verdict coherence is closed;
- B16 current human approval provenance is explicit;
- mandatory visual-asset inventory has no actionable gap within current MVP scope;
- current canonical source/packet/approval chain validates;
- generated atlas/registry/package provenance is current;
- deterministic rebuild evidence is green;
- no unexplained B-owned diff remains;
- any runtime-only failure is explicitly routed to Track A;
- toolchain inventory has no unreviewed actionable security/currency gap.

### Output

Produce a concise closeout packet:

```text
TRACK_B_CONTINUATION: PASS | BLOCKED
ORIGIN_MAIN: <sha>
APPROVAL_LINEAGE: PASS | BLOCKED
MANDATORY_VISUAL_ASSETS: PASS | BLOCKED
GENERATED_PROVENANCE: PASS | BLOCKED
DETERMINISM: PASS | BLOCKED
TOOLCHAIN_CURRENCY: PASS | BLOCKED
TRACK_A_HANDOFFS: NONE | <exact items>
REMAINING_B_GAP: NONE | <one exact gap>
```

Do not add new validators/checklists solely to manufacture a closeout artifact.

---

# PART IV — LOCAL LLM INVOCATION GUIDE

## 26. If handed this runbook without a task-specific prompt

The local LLM must:

1. refresh `origin/main`;
2. read the authoritative documents in §2;
3. inspect whether B14 is already independently closed on the refreshed code;
4. if not, execute B14 only;
5. if B14 is closed, inspect B15;
6. if B15 is closed, inspect B16;
7. after B16 is closed, choose the earliest eligible B20+ task;
8. execute exactly one task;
9. publish only if that task passes;
10. report using §8;
11. stop.

Do not execute multiple Bxx tasks in one invocation.

---

## 27. Context budget for local models

Do not dump the whole repository into context.

For each Bxx task, provide only:

- this task's section;
- exact current implementation file(s);
- one or two focused test files;
- only the relevant paragraphs from the authoritative spec;
- current git status/SHA evidence.

If another subsystem becomes relevant, inspect it read-only first and add it only if it is necessary to decide the same hypothesis.

Do not recursively load adjacent runtime files merely because they reference an asset alias.

---

## 28. Final invariant

A Track B task is not complete because generated files are green.

It is complete only when the authoritative producer, proof, human-approval boundary, generated lineage and its single task-specific criterion agree.

When a new defect is discovered:

```text
isolate it
→ prove it
→ fix only it
→ verify only it plus direct impact
→ publish
→ stop
```

That sequence is the default for every continuation task.
