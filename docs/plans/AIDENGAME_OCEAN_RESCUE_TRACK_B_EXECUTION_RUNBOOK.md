# AidenGame Ocean Rescue — Track B Execution Runbook

- **Date:** 2026-08-07
- **Status:** ACTIVE EXECUTION RUNBOOK
- **Track:** B — asset/content authoring, generation, validation, provenance, deterministic publication
- **Audience:** local coding agents (including Qwen3.6 35B-class or smaller), frontier-model reviewer, human operator
- **Repository:** `savior714/game`
- **Integration branch:** `origin/main`

---

## 1. Purpose

This document turns the existing Ocean Rescue asset-pipeline contracts into a step-by-step execution queue that a local LLM can follow without reconstructing the whole architecture on every task.

It is **not** a new source of truth for product or asset contracts. Its job is to answer four operational questions:

1. What is the next bounded Track B task?
2. What may the local agent read and modify?
3. What single hypothesis and pass criterion decide that task?
4. What compact evidence should be returned for frontier-model review?

The expected operating loop is:

```text
run one bounded B task
→ return its evidence packet
→ frontier reviewer checks only that task and current main
→ reviewer supplies a delta-only corrective prompt if a gap exists
→ local agent closes that gap
→ publish to origin/main
→ advance to the next independent B task
```

Do not repeatedly restate the whole runbook in follow-up prompts.

---

## 2. Authority and precedence

When instructions differ, use this order:

1. the user's current request,
2. `AGENTS.md`,
3. `PROJECT_RULES.md` and the nearest product/technical specification,
4. current `origin/main` code/tests/configuration,
5. this runbook.

Primary Ocean Rescue B-track references:

- `docs/specs/technical/AIDENGAME_OCEAN_RESCUE_MANUAL_SVG_ASSET_HANDOFF.md`
- `docs/specs/technical/AIDENGAME_OCEAN_RESCUE_DEVELOPMENT_ARCHITECTURE.md`
- the current validators/builders under `scripts/ocean_rescue/`

If this runbook disagrees with a higher-authority source, **do not repair the conflict by guessing**. Stop the current task and report the exact disagreement.

---

## 3. Track B ownership boundary

### Track B owns

- `domains/ocean-rescue/assets/source/**`
- `domains/ocean-rescue/assets/review/**`
- `domains/ocean-rescue/assets/handoff/**`
- `domains/ocean-rescue/assets/generated/**`
- asset metadata and schema
- SVG intake and structural/security validation
- proof/contact-sheet generation
- approval receipt integrity
- atlas generation and validation
- registry/manifest generation
- provenance and hashes
- deterministic regeneration
- B-side tests and pipeline tooling

### Track B may read but must not modify

Track A runtime/gameplay surfaces, including runtime loader/renderer/controller/FSM/input/timer/gameplay code, may be inspected only to understand the consumer contract or collect evidence.

### Serial/shared area

Root dependency/toolchain changes, shared lockfiles, and repository-wide CI/verification configuration are not routine A/B parallel work. If a B task appears to require one of these, stop and classify it as a separate serial integration task.

### B → A handoff rule

If B artifacts satisfy their producer contract but the runtime consumer still fails, do **not** modify Track A from a B task. Record the exact producer evidence and open a separate A-track failure domain.

---

## 4. Core execution rule

For this runbook:

> **One task = one failure domain = one independently decidable criterion.**

Each task must have all of the following before any modification:

- one reproducible or directly inspectable failure/uncertainty,
- one hypothesis,
- one bounded write scope,
- one primary verifier,
- one binary pass criterion.

Do not combine multiple unrelated validator gaps, multiple unrelated assets, source repair plus runtime repair, or dependency upgrade plus pipeline repair into one task.

A newly discovered independent problem is recorded under `DISCOVERED_FAILURE`; it is not silently folded into the current change.

---

## 5. Standard workspace procedure

### 5.1 Refresh canonical state

```bash
git fetch origin
git status --short
git rev-parse origin/main
```

Do not treat a harmless remote advance as a blocker.

### 5.2 Create an isolated locked worktree

Use the repository workflow in `agents/workflows/git.md`. The normal location is:

```text
/Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>
```

The worktree must start from the current `origin/main` and be locked with a short operational reason.

### 5.3 Preserve unrelated state

Never clean, reset, stash, delete, or overwrite another task's dirty files merely to make the current task easier.

### 5.4 Before publication

Re-fetch `origin/main`. If another non-overlapping task advanced it, reapply onto the latest main and rerun this task's primary verifier plus its required direct-impact verification.

### 5.5 After successful publication

Only when all are true:

- the task is published to `origin/main`,
- the worktree is clean,
- its HEAD is contained in current `origin/main`,
- it is the worktree created by this task,

unlock it and remove it with normal `git worktree remove`. Never use `--force` or `rm -rf`.

---

## 6. Local-LLM context discipline

A local task prompt should contain only:

1. task identity,
2. one hypothesis,
3. relevant contract excerpts or exact reference paths,
4. allowed read paths,
5. allowed write paths,
6. forbidden scope,
7. reproduction command,
8. primary verifier,
9. required direct-impact checks,
10. output format.

Do not paste the whole repository history, all prior completed tasks, or this entire runbook into every follow-up prompt.

For Qwen3.6-class local agents, prefer a prompt that can be understood without reconstructing cross-track architecture. If understanding requires more than a few directly relevant files, split the investigation first.

---

## 7. Standard task card

Use this shape for every executable B task:

```text
TASK: Bxx — <short name>
FAILURE_DOMAIN: <one precise failure domain>
MODE: ANALYZE_ONLY_FIRST or MODIFY_AND_VERIFY

GOAL
- <one observable outcome>

HYPOTHESIS
- <one falsifiable statement>

READ FIRST
- <contract/spec path>
- <implementation path>
- <focused test path>

ALLOWED READ
- <paths>

ALLOWED WRITE
- <smallest paths that can close this failure>

DO NOT
- do not modify Track A runtime/gameplay code
- do not fix independent discovered failures
- do not change root dependencies/lockfiles unless this is an explicitly authorized serial task
- do not regenerate unrelated artifacts
- do not approve visual quality on behalf of the human operator

REPRODUCTION / BASELINE
- <exact command or direct inspection>

PRIMARY VERIFIER
- <exact command>

PASS IFF
- <one binary criterion>

DIRECT IMPACT
- <small bounded checks only>

STOP IF
- the hypothesis is false
- the required fix crosses A/B ownership
- a higher-authority contract is ambiguous or contradictory
- the baseline failure belongs to another failure domain

REPORT
RESULT: PASS | FAIL | BLOCKED
FAILURE_DOMAIN: <same task domain>
CHANGE: <short exact summary or NONE>
PRIMARY_VERIFY: PASS | FAIL | NOT_RUN
DIRECT_VERIFY: PASS | FAIL | NOT_RUN
STATIC_VERIFY: PASS | FAIL | NOT_RUN
PUBLISH: PUBLISHED | NOT_PUBLISHED | NOT_APPLICABLE
COMMIT: <sha or NONE>
DISCOVERED_FAILURE: NONE | <one-line independent finding>
BLOCKER: NONE | <why current task cannot continue>
```

Each status field must contain exactly one allowed value. Do not emit compound states such as `PASS | BLOCKED` or `PASS (with caveat)`.

---

## 8. Frontier-review evidence packet

When asking the frontier reviewer to inspect a local-agent result, provide this compact packet plus the local agent's report:

```text
TRACK: B
TASK: Bxx
BASE_ORIGIN_MAIN: <sha used when task began>
PUBLISHED_COMMIT: <sha or NONE>
FAILURE_DOMAIN: <one domain>
HYPOTHESIS: <one sentence>
CHANGED_FILES:
- ...
PRIMARY_COMMAND: <command>
PRIMARY_RESULT: <result>
DIRECT_COMMANDS:
- ...
DIRECT_RESULTS:
- ...
FAILURE_EXCERPT: <only when failed>
DISCOVERED_FAILURE: <NONE or independent finding>
```

Do not ask the local model to prepare a long retrospective.

The frontier reviewer should independently compare the actual commit/diff and current `origin/main` against this evidence rather than trusting the report text alone.

---

## 9. Delta-only corrective prompt protocol

If review finds a gap, the next prompt should **not** repeat the original task. It should preserve everything already proven and describe only the missing correction.

Template:

```text
TASK: Bxx-Dn — <specific review gap>

PRESERVE
- the already-passing Bxx behavior and tests

CORRECT ONLY
- <one missing condition>

ALLOWED WRITE
- <minimal paths>

DO NOT
- broaden into adjacent defects
- rewrite already-passing implementation without need
- modify Track A

VERIFY
- <one focused command>

PASS IFF
- <one binary criterion>

REPORT
- use the standard mutually-exclusive status fields
```

Once the delta passes, return to the original queue. Do not recursively grow the prompt with prior history.

---

# PART II — EXECUTION QUEUE

## 10. B00 — Reconstruct current B baseline

**Purpose:** establish the current source/approval/generated state before selecting a new defect.

This is read-only unless the user explicitly asks for documentation refresh.

### Read

- `AGENTS.md`
- both Ocean Rescue technical specs named in §2
- `domains/ocean-rescue/assets/source/art-packet.json`
- `domains/ocean-rescue/assets/source/art-approval.json`
- `domains/ocean-rescue/assets/generated/atlas-manifest.json`
- current `scripts/ocean_rescue/`
- recent B-related commits on current main

### Run

```bash
uv run python scripts/ocean_rescue/validate_art_packet.py \
  domains/ocean-rescue/assets/source

uv run python scripts/ocean_rescue/validate_art_approval.py \
  domains/ocean-rescue/assets/source

uv run python scripts/ocean_rescue/validate_atlases.py \
  --packet domains/ocean-rescue/assets/source/art-packet.json \
  --approval domains/ocean-rescue/assets/source/art-approval.json \
  --generated-dir domains/ocean-rescue/assets/generated
```

### Pass criterion

All three canonical validators pass on unchanged current `origin/main`.

### If one fails

Do not fix all three. Choose the earliest producer-side failing gate as the next single failure domain.

---

## 11. B01 — Incoming SVG structural/security contract

**Purpose:** ensure untrusted SVG cannot enter the canonical source set with a structural, reference, or security violation that the current contract says must be rejected.

### Primary implementation

- `scripts/ocean_rescue/validate_art_packet.py`
- focused validator tests under `tests/`

### Known classes to inventory before choosing a task

- XML parse validity
- SVG root/namespace contract
- `viewBox` arity, finiteness, and positive dimensions
- duplicate IDs
- local `url(#id)` target existence
- path traversal
- forbidden elements such as script-capable/embedded/animation content
- event-handler attributes (`on*`)
- external or executable URI forms
- drawable-content existence
- declared source SHA-256 parity

### Task-selection rule

Inventory the validator and focused tests read-only. Pick **one actual unguarded contract**. Add one RED reproduction proving the gap, then modify only the validator logic needed for that gap.

### Primary verifier

The focused test for that exact invalid SVG form must be RED before the fix and GREEN after it.

### Direct impact

Run the canonical source packet validator once after the focused test passes.

### Do not

- refactor the whole validator while closing one missing rejection,
- change canonical SVG files merely to make a new validation rule pass unless the task is explicitly a source-correction task,
- fix a second validator gap found during inventory.

---

## 12. B02 — Art-packet metadata and source provenance

**Purpose:** keep metadata, aliases, bundle placement, dimensions, pivots, source paths, and source hashes consistent with canonical SVG inputs.

### Focus areas

Choose only one per task:

- alias uniqueness/stability,
- source path containment,
- bundle membership,
- logical dimensions,
- pivot bounds,
- `sourceSha256` parity,
- packet schema shape,
- ordering/deterministic serialization where contractually required.

### Primary verifier

```bash
uv run python scripts/ocean_rescue/validate_art_packet.py \
  domains/ocean-rescue/assets/source
```

For a validator defect, add a focused synthetic fixture/reproduction first. For a stale canonical metadata value, directly prove the mismatch before changing the packet.

### Pass criterion

The selected metadata/provenance mismatch is eliminated and the canonical packet validator passes.

---

## 13. B03 — Proof/contact-sheet determinism

**Purpose:** ensure visual-review evidence is derived from the current canonical packet and can be reproduced byte-for-byte when inputs are unchanged.

### Generator

```bash
uv run python scripts/ocean_rescue/build_art_contact_sheet.py \
  domains/ocean-rescue/assets/source \
  --output domains/ocean-rescue/assets/review/proof-art-contact-sheet.html
```

### Procedure

1. Build to a disposable comparison path or record the current tracked hash.
2. Rebuild from unchanged inputs.
3. Compare bytes/hash.
4. If the tracked proof sheet is stale, update only that generated evidence file in this task.
5. Rebuild again and prove no second diff.

### Pass criterion

Two clean builds from identical inputs are byte-identical and the tracked proof evidence matches a clean rebuild.

### Do not

Treat a generated contact sheet as human approval. It is evidence only.

---

## 14. B04 — Human visual review/revision loop

**Purpose:** move one visually deficient asset through bounded human/frontier-model revision without letting the local agent redesign art.

### One task = one visual failure domain

Examples:

- silhouette unreadable at intended size,
- incorrect facing direction,
- contrast failure against the real background,
- anatomy/perspective defect,
- inconsistent line weight,
- visual overlap obscuring the interaction target.

### Local agent may

- inspect the current asset and scene,
- prepare a bounded revision brief,
- validate the returned SVG structurally,
- generate isolated and contextual proof,
- prepare evidence for the human operator.

### Local agent may not

- redraw path geometry,
- change silhouette/anatomy/palette/composition itself,
- record `APPROVED` by inference,
- replace a rejected asset with procedural placeholder geometry.

### Human gate

Only the human operator may decide `APPROVED` or `REJECTED` after viewing the actual-size contextual proof.

If rejected, create/update only the bounded revision request for that asset and return to the frontier SVG revision loop.

---

## 15. B05 — Approval receipt integrity

**Purpose:** ensure the approval receipt describes exactly the committed source packet and review evidence that the human actually approved.

### Validation

```bash
uv run python scripts/ocean_rescue/validate_art_approval.py \
  domains/ocean-rescue/assets/source
```

The validator checks the current packet/approved alias set, source-set provenance, evidence paths, contact-sheet linkage, predecessor/commit expectations, and deterministic fields.

### Recording approval

`scripts/ocean_rescue/approve_art.py --approve` is an **explicit human-authorized action**. A local LLM must not invoke it merely because technical validation passed.

After the user explicitly approves the reviewed current committed contact sheet, the agent may use the repository approval tool as directed by the current script/spec.

### Pass criterion

The approval validator passes against the exact current packet and evidence the user approved.

---

## 16. B06 — Deterministic atlas generation

**Purpose:** produce generated atlas artifacts only from the approved canonical packet.

### Canonical build command

```bash
uv run python scripts/ocean_rescue/build_atlases.py \
  --packet domains/ocean-rescue/assets/source/art-packet.json \
  --approval domains/ocean-rescue/assets/source/art-approval.json \
  --output-dir domains/ocean-rescue/assets/generated
```

### Current generated contract

Expected top-level products include:

- `atlas-manifest.json`
- `pixi-assets-manifest.json`
- bundle directories for `characters`, `scene`, and `effects-ui`

The current atlas validator also requires exact recorded toolchain pins, including CairoSVG `2.9.0` and Pillow `12.3.0`. Do not upgrade them inside an ordinary B task.

### Pass criterion

A clean build completes from the current approved source set without altering unrelated source or runtime files.

---

## 17. B07 — Atlas output integrity

**Purpose:** prove the generated atlas satisfies the producer contract independently of Track A runtime behavior.

### Canonical validator

```bash
uv run python scripts/ocean_rescue/validate_atlases.py \
  --packet domains/ocean-rescue/assets/source/art-packet.json \
  --approval domains/ocean-rescue/assets/source/art-approval.json \
  --generated-dir domains/ocean-rescue/assets/generated
```

### Validator-owned areas include

- exact bundle count,
- manifest file hashes,
- PNG dimensions,
- spritesheet schema,
- alias membership,
- frame bounds,
- overlap/padding,
- trim metadata,
- pivot metadata,
- page ceiling,
- multi-pack linkage,
- undeclared generated files,
- timestamps/UUIDs or other forbidden nondeterministic content,
- exact toolchain pins.

### Task-selection rule

If this validator itself has a missing guarantee, close only one guarantee per task with a focused RED fixture. If canonical output is stale, regenerate the producer outputs rather than weakening the validator.

---

## 18. B08 — Registry generation/provenance

**Purpose:** ensure the runtime-facing registry is a deterministic projection of the validated generated atlas, not an independently drifting data source.

### Generator interface

```bash
uv run python scripts/ocean_rescue/build_render_assets_registry.py \
  --atlas-dir domains/ocean-rescue/assets/generated \
  --output <current canonical registry path>
```

Before running, determine the canonical output path from current `origin/main`; do not invent a new registry destination.

### Verify

- registry embeds/reflects the current atlas-manifest and Pixi-manifest provenance,
- bundle order and embedded files match the current generated outputs,
- a second rebuild from unchanged inputs is byte-identical,
- no Track A source is manually edited to compensate for registry drift.

### Pass criterion

The canonical registry exactly matches a clean deterministic rebuild from current validated generated artifacts.

---

## 19. B09 — Generated manifest/provenance closure

**Purpose:** prove there is one coherent provenance chain:

```text
canonical SVG bytes
→ art-packet sourceSha256
→ art-approval packet/source-set evidence
→ atlas-manifest provenance + generated file hashes
→ Pixi manifest / registry provenance
```

### One task may close only one broken link

Examples:

- packet hash mismatch,
- approval hash mismatch,
- stale atlas source provenance,
- stale generated file hash,
- stale registry manifest hash.

### Pass criterion

The selected broken link is mathematically consistent with the actual bytes on disk and its direct producer/consumer checks pass.

Do not regenerate every downstream artifact blindly before identifying which link first diverges.

---

## 20. B10 — Whole-pipeline determinism proof

Run this only after focused source/approval/atlas/registry defects are closed.

### Goal

Rebuild the B-owned generated chain twice from identical committed inputs and prove stable bytes/hashes.

### Procedure

1. Start from a clean worktree at current `origin/main`.
2. Record hashes of B-owned generated outputs.
3. Rebuild the applicable B pipeline.
4. Confirm expected diff scope only.
5. Rebuild a second time.
6. Confirm the second rebuild produces no diff.

### Pass criterion

The second clean rebuild is byte-identical and no undeclared/unrelated file changes remain.

### If nondeterminism appears

Stop this aggregate proof. Convert the first proven nondeterministic producer into a separate focused failure domain.

---

## 21. B11 — B-side publication artifact consistency

Some B-generated data may feed a single-HTML packaging step. This task is limited to **generated asset publication integrity**, not gameplay/runtime behavior.

Inspect current `scripts/ocean_rescue/build_single_html.py` and the nearest packaging tests before selecting a failure domain.

Allowed B concerns include:

- current generated asset bytes included exactly once/as declared,
- provenance recorded consistently,
- deterministic packaging inputs,
- no missing or undeclared generated asset files.

If the issue is event handling, mission flow, renderer behavior, pause/resume, game state, or browser gameplay semantics, route it to Track A.

---

## 22. B12 — B → A contract handoff gate

This is a read/verify gate, not a cross-track repair task.

### B must be able to state

- canonical source packet validator: PASS,
- approval validator: PASS,
- atlas build: PASS,
- atlas validator: PASS,
- registry/manifest deterministic rebuild: PASS,
- relevant generated artifact hashes/provenance: current,
- no unexplained B-owned diff remains.

### If all pass but runtime fails

Report:

```text
B_PRODUCER_CONTRACT: PASS
A_CONSUMER_FAILURE: <exact observed failure>
B_CHANGE_REQUIRED: NO
ROUTE: TRACK_A
```

Do not patch the runtime consumer from this task.

---

## 23. B13 — Maintenance inventory: one gap at a time

After the current pipeline passes end-to-end, continue B work by read-only inventory of one surface at a time:

1. SVG validator security/structure coverage,
2. art-packet schema/provenance coverage,
3. approval receipt coverage,
4. contact-sheet determinism,
5. atlas builder/validator symmetry,
6. registry provenance and determinism,
7. generated artifact undeclared/stale-file detection,
8. packaging provenance at the B boundary.

For each inventory:

- compare implementation against the current authoritative contract,
- compare tests against implementation branches and failure modes,
- identify only a concrete, reproducible uncovered guarantee,
- execute it as a new Bxx task,
- otherwise record `NO_ACTIONABLE_GAP` and move to the next surface.

Do not create speculative validators or governance layers when no real failure/contract gap is found.

---

# PART III — FAILURE ROUTING

## 24. Routing table

| Observation | Current owner | Next action |
|---|---|---|
| invalid SVG accepted | B | one validator gap task |
| valid SVG rejected | B | one validator false-positive task |
| source SHA mismatch | B | packet/source provenance task |
| contact sheet stale/nondeterministic | B | proof-generation task |
| human dislikes visual quality | B + human/frontier art loop | one asset revision |
| approval receipt mismatches packet/evidence | B | approval integrity task |
| atlas build fails on approved canonical source | B | one build failure domain |
| atlas validator finds malformed output | B | one generator/validator contract task |
| repeated builds differ | B | isolate first nondeterministic producer |
| registry hash/provenance stale | B | registry generation task |
| B outputs pass but runtime alias loading fails | A | hand off exact B evidence |
| controller/FSM/input/timer/gameplay fails | A | do not modify from B |
| root dependency/lockfile upgrade needed | serial integration | leave A/B parallel lane |

---

## 25. Visual asset correction policy

When a visual asset itself must change:

- choose one asset or one truly shared visual root cause,
- define one binary visual criterion,
- preserve unrelated assets,
- use the frontier SVG author/revision loop for geometry changes,
- use local tools only for allowed mechanical/pixel-equivalent cleanup,
- re-enter packet → proof → human approval → build → validation in order.

Never declare a technically valid but visually rejected asset complete.

---

## 26. Generated artifact repair policy

Do not hand-edit generated atlas PNG/JSON, generated manifest, or generated registry to make tests pass unless the authoritative workflow explicitly defines that file as hand-maintained.

Prefer:

```text
find first stale/incorrect producer input or generator
→ fix that one failure domain
→ regenerate affected partition
→ prove direct provenance/determinism
```

If a rebuild touches unrelated partitions, treat that as evidence to investigate rather than automatically committing the noise.

---

## 27. Test selection policy

During a focused task:

1. run the smallest test/reproduction that decides the hypothesis,
2. run the direct producer/consumer regression needed for that change,
3. run static/diff checks appropriate to the changed files,
4. avoid broad full-suite reruns while the focused task is still failing.

Use broader milestone verification only after a focused task passes or at a defined B pipeline gate.

Never weaken or delete a failing test merely to obtain green status without proving the asserted contract is obsolete.

---

# PART IV — MILESTONES

## 28. M0 — Canonical source trustworthy

Pass when:

- art-packet validation passes,
- no known unhandled structural/security gap remains in the selected inventory surface,
- metadata/source hashes are current.

## 29. M1 — Human-approved source trustworthy

Pass when:

- review evidence is reproducible,
- explicit human approval exists for the current committed source set,
- approval validation passes.

## 30. M2 — Generated outputs trustworthy

Pass when:

- atlas build passes,
- atlas validation passes,
- manifests and registry match the current approved source set,
- generated outputs are deterministic.

## 31. M3 — Producer handoff ready

Pass when:

- M0–M2 pass on the same current source lineage,
- no unexplained B-owned diff remains,
- the B → A handoff packet records current provenance and any consumer-side failure separately.

---

# PART V — CURRENT BASELINE NOTES

## 32. 2026-08-07 recent B hardening already present on main

Do not reopen these as new tasks unless a distinct uncovered variant is proven.

Recent B-track commits include, among others:

- rejection of SVG `javascript:` URIs,
- rejection of missing local `url(#id)` reference targets,
- SVG root namespace enforcement,
- finite/positive root `viewBox` validation,
- rejection of all `on*` event-handler attributes,
- duplicate SVG ID rejection/coverage,
- approval evidence path escape rejection,
- forbidden SVG animation/`foreignObject` hardening,
- deterministic proof contact-sheet refresh,
- generated provenance coverage.

These commits are evidence of the current direction: continue closing **specific producer-side contract gaps one at a time**, rather than replacing the pipeline with a large new abstraction.

---

## 33. Toolchain pin rule

The current atlas validator requires exact manifest toolchain versions:

- CairoSVG `2.9.0`
- Pillow `12.3.0`

An upstream release existing does not authorize a B-track upgrade. Dependency/toolchain upgrades must be investigated as a separate serial task because they may touch root dependency metadata/lockfiles and can change rendered pixels.

For an upgrade task, require at minimum:

1. current pinned baseline render hashes,
2. candidate-version isolated rebuild,
3. pixel/output diff classification,
4. validator/build compatibility,
5. deterministic rebuild proof,
6. explicit dependency/lockfile scope,
7. separate publication decision.

---

# PART VI — COMPLETION AND REVIEW

## 34. Definition of a completed B task

A task is complete only when:

- its hypothesis was actually tested,
- its single pass criterion passed,
- direct-impact checks passed,
- unrelated failures were kept separate,
- the actual diff matches the allowed scope,
- publication status is unambiguous,
- if published, the commit is reachable from current `origin/main`,
- the disposable worktree is safely reclaimed when eligible.

`DISCOVERED_FAILURE` does not invalidate an otherwise completed task unless it is genuinely a prerequisite/blocker for the current criterion.

---

## 35. What to send the frontier reviewer mid-run

When the user asks for review during this runbook, send the compact evidence packet from §8 and the local agent's report. The reviewer should:

1. refresh current `origin/main`,
2. inspect the actual commit/diff,
3. reproduce the claimed primary evidence when feasible,
4. determine whether the original B task is genuinely closed,
5. directly fix what can safely be fixed with connected tools when appropriate,
6. otherwise return **one delta-only prompt** for the exact remaining gap.

The reviewer should not restart the entire B plan or reissue completed work.

---

## 36. Final operating instruction for a local agent

When this runbook is handed to a local LLM without another task-specific prompt:

1. refresh and read current `origin/main`,
2. read `AGENTS.md` and the two B-track technical specs,
3. execute B00 read-only baseline,
4. identify the earliest concrete B-owned failing gate or one concrete unguarded guarantee from B13,
5. formulate exactly one task card using §7,
6. execute that task to its binary criterion,
7. publish only if all required verification passes,
8. report using the standard mutually-exclusive fields,
9. stop after that single task.

Do **not** autonomously continue through multiple independent failure domains in one invocation.
