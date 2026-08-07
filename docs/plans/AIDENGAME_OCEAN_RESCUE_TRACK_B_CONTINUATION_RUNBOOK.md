# AidenGame Ocean Rescue — Track B Closeout Runbook

- Version: v3.0
- Date: 2026-08-08
- Status: ACTIVE — closeout inventory
- Track: B — asset/content production, validation, approval, atlas, registry, manifest and package provenance

This is a **rolling working set**, not a completion log. Git history and current repository state are the completion record. Do not restore completed task transcripts, old RED/GREEN logs, historical SHAs, or retired handoff instructions here.

---

## 1. Live state

### Completed and pruned

The loop-02 and loop-03 production cycles are complete through B27, and B28 published a final seaweed-loop inventory check. The current packet/approval lineage contains all three seaweed-loop aliases as approved.

Do not reload B22–B28 execution details unless current `origin/main` proves a regression in one of those contracts.

Important closeout distinction:

- B28 directly proves the three seaweed-loop aliases are present and approved and that the current packet/approval counts agree.
- A fixed total asset count is **not** semantic proof that every Rendering MVP mandatory visible subject is authored correctly.
- B30 therefore performs the final spec-derived authored-art/placeholder inventory. Do not add another count-based proxy.

### ACTIVE

```text
B30 — mandatory MVP visible-subject authored-art / placeholder audit
```

### NEXT

```text
B31 — atlas integrity inventory
B32 — B-package provenance inventory
B33 — art-toolchain currency inventory
B34 — Track B closeout decision
```

No current external asset handoff is blocking B30.

---

## 2. Minimal read set

For B30, read only:

1. `AGENTS.md`
2. `docs/specs/product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md`
   - mandatory first-slice asset set
   - representative-final-quality / placeholder restrictions
3. this runbook
4. `domains/ocean-rescue/assets/source/art-packet.json`
5. `domains/ocean-rescue/assets/source/art-approval.json`
6. the B-owned generated manifest/registry surfaces needed to classify the same subjects

Open the manual SVG handoff spec only if B30 selects a new authored asset for a later task. Do not load either predecessor Track B runbook by default.

Current `origin/main`, current specs, canonical sources and current generated outputs override past chat reports and task labels.

---

## 3. Fixed Track B invariants

Track B owns the production side of:

```text
canonical source
→ source/security validation
→ proof/contact sheet
→ explicit human approval
→ atlas
→ registry/manifest
→ package provenance
```

Preserve these rules:

- mandatory visible acceptance subjects use authored production art where the Rendering MVP requires it;
- visible characters, creatures, vehicles, coral and rescue obstacles do not pass acceptance as procedural placeholder geometry;
- invisible hit areas, debug overlays, alignment guides and explicitly temporary development particles are not authored-art gaps;
- source hash, packet metadata, approval receipt, atlas metadata and generated provenance remain internally consistent;
- approved aliases and pivots stay stable unless a current source/spec change requires otherwise;
- generated files come from sanctioned producers, never hand edits;
- B does not change gameplay state, controller behavior, hit rules, pause/timer state or runtime scene semantics;
- a correct B producer contract followed by incorrect runtime consumption is routed to Track A.

For every task: one failure domain, one falsifiable hypothesis, one primary binary criterion. Use the minimum coherent root-cause-complete change, not minimum LOC.

---

## 4. B30 — mandatory authored-art / placeholder audit

### Failure domain

`MANDATORY_MVP_VISIBLE_SUBJECT_AUTHORING_COMPLETENESS`

### Mode

Read-only inventory first. Do not repair an asset during the audit invocation.

### Hypothesis

The current Rendering MVP mandatory visible-subject set is represented by approved canonical authored assets, with no acceptance-critical subject relying on placeholder/procedural geometry.

### Primary criterion

The spec-derived mandatory visible-subject set can be classified unambiguously as either:

```text
NO_GAP
```

or:

```text
GAP_SELECTED: exactly one highest-priority missing/unapproved/placeholder subject
```

Do **not** use `len(packet["assets"])`, `approvedAssetCount`, or another aggregate count as the deciding proof.

### Procedure

1. Refresh `origin/main`.
2. Extract the semantic mandatory subject set from the Rendering MVP, especially:
   - sea-otter minimum rig and facial states;
   - sea-turtle body/facial relief states;
   - submarine and required scene layers;
   - all three seaweed-loop obstacles;
   - required effects/UI assets.
3. Map each semantic subject to its current packet alias(es), canonical source and approval state.
4. Read the corresponding B-generated registry/manifest only as needed to distinguish a real production asset from metadata-only or stale generated state.
5. If a suspicious visible geometry fallback is found, inspect the relevant A consumer **read-only** only to decide whether it is visible acceptance art or an allowed invisible/debug surface.
6. Produce one inventory verdict.

### Stop condition

- `NO_GAP`: publish nothing and proceed to B31 in the next invocation.
- `GAP_SELECTED`: report exactly one asset/subject, authoritative expected state, observed deficiency and one binary acceptance criterion. Stop; create the handoff/fix in a later invocation.
- If the semantic mapping cannot be decided from current authoritative sources, `BLOCKED` with the exact missing authority.

Do not create a new validator, checklist, status file or test merely to record that the audit happened.

---

## 5. B31 — atlas integrity inventory

### Failure domain

`TRACK_B_ATLAS_CONTRACT_INTEGRITY`

### Mode

Read-only first.

### Primary criterion

Current atlas outputs can be evaluated against the already-established contracts with either no violation or exactly one reproduced violation selected for a later task.

Inspect only established invariants:

- atlas page/frame bounds;
- declared bundle membership;
- trim/padding metadata;
- duplicate or missing aliases;
- source/atlas provenance;
- deterministic output under the sanctioned producer.

Do not invent density, aesthetic or packing-efficiency thresholds. A reproduced defect becomes its own later failure domain; do not fix it in the inventory invocation.

---

## 6. B32 — B-package provenance inventory

### Failure domain

`TRACK_B_PACKAGE_PROVENANCE_INTEGRITY`

### Mode

Read-only first.

### Primary criterion

B-owned packaged asset data is demonstrably derived from the current approved source/packet/atlas lineage and requires no runtime network retrieval for B-owned asset payloads.

Inspect producer/package metadata and deterministic build evidence. Runtime loader/display behavior after a correct B package is Track A.

If a provenance defect is reproduced, select exactly one defect for a later task and stop.

---

## 7. B33 — art-toolchain currency inventory

### Failure domain

`TRACK_B_ART_TOOLCHAIN_CURRENCY`

### Mode

Read-only version comparison.

Current 2026-08-08 upstream stable versions:

```text
CairoSVG 2.9.0
Pillow 12.3.0
```

If repository pins still match these versions when B33 runs, report no actionable upgrade and do not mutate lock/config files.

If an upstream stable version has advanced, treat that upgrade as a separate serial integration task because raster bytes and generated provenance may change. Do not combine dependency upgrade, artifact regeneration and unrelated closeout defects into one task.

---

## 8. B34 — Track B closeout

### Failure domain

`TRACK_B_CONTINUATION_CLOSEOUT`

### Mode

Read-only decision. Do not add new closeout infrastructure.

### Primary criterion

On one refreshed `origin/main` lineage, all of the following are directly supported by current evidence:

- B30: no mandatory authored-art / placeholder gap remains;
- B31: atlas contract integrity has no unresolved B violation;
- B32: package provenance is current and network-independent for B payloads;
- current source/packet/approval validation is green;
- deterministic generated-art rebuild evidence is green;
- B33: no unreviewed actionable art-toolchain upgrade remains;
- any runtime-only consumer defects are explicitly routed to Track A.

Report only:

```text
TRACK_B_CONTINUATION: PASS | BLOCKED
MANDATORY_AUTHORED_ART: PASS | BLOCKED
ATLAS_INTEGRITY: PASS | BLOCKED
PACKAGE_PROVENANCE: PASS | BLOCKED
APPROVAL_LINEAGE: PASS | BLOCKED
DETERMINISM: PASS | BLOCKED
TOOLCHAIN_CURRENCY: PASS | BLOCKED
TRACK_A_HANDOFFS: NONE | <exact items>
REMAINING_B_GAP: NONE | <one exact gap>
```

If all fields pass, change this runbook to `Status: CLOSED` in a final documentation-only task and leave no historical task transcript behind.

---

## 9. Executor contract

Before mutation, inspect the shared owner and direct sibling surfaces that consume the same invariant. Sibling inventory expands read scope, not automatic write scope.

A bounded coherent package may include the production owner, directly coupled metadata/schema, producer/validator and focused regression when they share the same root cause, invariant and rollback boundary. Different roots stay separate.

For mutations, follow current `AGENTS.md` and `agents/workflows/git.md`: isolated locked worktree, focused V1 first, direct-impact V2 next, latest-main reapply when non-overlapping remote work advances, fast-forward publication to `origin/main`, and clean worktree cleanup only after publication is proven.

Never use PR/feature-branch flow unless explicitly requested. Never force-push, bypass hooks, use `/tmp` worktrees or hide failures with broad ignores/snapshot refreshes.

Current completion report schema is inherited from `AGENTS.md`:

```text
RESULT: PASS | BLOCKED
PRIMARY_VERIFY: PASS | FAIL | NOT_RUN
DIRECT_VERIFY: PASS | FAIL | NOT_RUN
PUBLISH: PUBLISHED | NOT_APPLICABLE | BLOCKED
DISCOVERED_FAILURE: <independent failure domain or NONE>
```

Add `COMMIT` only when published. Add `BLOCKER` and `NEXT` only when legitimately blocked.

---

## 10. Local-model context budget

For a Qwen3.6-class executor, provide only:

- §1 live state;
- §3 fixed invariants;
- the single ACTIVE Bxx section;
- the exact current source/metadata/test files needed by that hypothesis;
- only the relevant spec paragraphs.

Do not provide completed B22–B28 details, old task reports, historical SHAs, predecessor runbooks or unrelated A-runtime code.

When another failure domain is discovered, record it and stop instead of recursively expanding context.

---

## 11. Current next action

Execute **B30 only**.

Its job is to decide semantic mandatory authored-art completeness from the current Rendering MVP and current B production state. It must not reproduce B28's aggregate-count proxy, and it must not fix the first gap in the same invocation.
