# AidenGame Ocean Rescue — Manual Frontier SVG Asset Handoff

- **Version:** v1.0
- **Date:** 2026-08-01
- **Status:** CANONICAL
- **Owner:** Ocean Rescue visual asset pipeline
- **Parent product spec:** `../product/AIDENGAME_OCEAN_RESCUE_RENDERING_MVP.md`
- **Applies to:** manually transferred SVG assets created or visually revised by a frontier model
- **Automation policy:** no model API, no MCP asset generator, no automated remote generation
- **Runtime policy:** canonical SVG source → deterministic build-time raster atlas → PixiJS texture

---

## 1. Purpose

This specification defines the single source of truth for producing higher-quality Ocean Rescue SVG assets with a frontier model while keeping implementation, validation, and runtime integration in the local repository workflow.

The human operator is the transfer boundary:

```text
local coding agent
→ asset brief
→ human copy/paste
→ frontier model SVG creation or visual revision
→ human file transfer
→ repository inbox
→ local validation
→ human visual approval
→ canonical source registration
→ deterministic atlas build
→ PixiJS integration
```

The process intentionally avoids API credentials, usage metering, model routing code, MCP services, webhooks, and background automation.

---

## 2. Authority and precedence

The parent Rendering MVP remains authoritative for:

- PixiJS architecture,
- WebGL and Canvas fallback policy,
- logical 1280×720 coordinates,
- atlas partitioning,
- deterministic build requirements,
- runtime asset representation,
- performance and acceptance requirements.

This document is authoritative for:

- who may create or visually revise SVG artwork,
- how asset requirements are handed to a frontier model,
- how returned files enter the repository,
- what local agents may and may not change,
- structural, security, visual, and canonicalization gates,
- approval and rejection states.

For SVG assets only, this specification supersedes the parent document's statement that AI output is limited to concept exploration. A frontier-generated SVG may become canonical production source **only after** it passes every gate in this document and receives explicit human visual approval.

This exception does not permit raw generated raster images, unreviewed SVG, or chat output to enter the production atlas.

---

## 3. Decision

### Selected operating model

```text
frontier model authors visual SVG
local agent authors the brief and integration
human performs transfer and visual approval
```

### Direct hypothesis

Separating visual authorship from local implementation will improve asset quality while preventing a smaller local model from degrading SVG geometry, style, or composition during integration.

### Binary criterion

The workflow passes when one asset can move from a repository-authored brief to an approved canonical SVG and then to an in-game atlas texture while all of the following remain true:

1. no generation API is used,
2. the local agent does not redraw the asset,
3. unsafe or unsupported SVG content is rejected,
4. human approval is based on an actual-size in-game proof,
5. deterministic atlas and runtime validation pass,
6. the original gameplay contract is unchanged.

---

## 4. Scope

### Included

- player vehicles,
- characters and character parts,
- animal states,
- HUD icons,
- interaction indicators,
- rescue tools,
- simple terrain and environment props,
- simple foreground and midground elements,
- SVG revisions of existing canonical assets.

### Excluded

- API integration,
- automatic remote model invocation,
- automatic prompt submission,
- automatic downloading from chat services,
- runtime SVG parsing as the production rendering path,
- gameplay logic changes,
- hit-geometry redesign unless separately specified,
- mission, progression, dialogue, or save-data changes,
- complex painted backgrounds better represented as raster source,
- bulk replacement of multiple visual systems in one task.

---

## 5. Core invariants

1. **One asset task equals one visual failure domain.**
2. The local agent may describe, validate, register, rasterize, and integrate an asset; it may not redesign it.
3. The frontier model may change visual geometry; it may not change repository code or gameplay contracts.
4. The human operator is the only authority that moves an asset from visual review to approved canonical source.
5. An inbox SVG is untrusted and non-canonical.
6. Only assets registered in `art-packet.json` and included in the current approval record may feed a production atlas.
7. Runtime code consumes stable aliases, never handoff file names or chat-generated names.
8. A visual correction must return to the frontier-model revision loop unless it is a proven pixel-equivalent mechanical cleanup.
9. Existing unrelated repository failures are not bundled into an asset task.
10. A failed gate remains visible; it is not converted into an approval by fallback geometry.

---

## 6. Roles and permissions

### 6.1 Local coding agent

The local coding agent may:

- inspect the current scene and asset contracts,
- choose one asset candidate,
- define one measurable visual failure,
- write the asset brief,
- define required IDs, aliases, dimensions, pivots, and bundle membership,
- inspect an incoming SVG,
- run structural and security validation,
- produce a raster preview and in-game proof,
- prepare a revision request,
- copy an approved file into the canonical source directory,
- update `art-packet.json`, hashes, and approval evidence,
- rebuild atlases and the single-HTML artifact,
- run focused regression tests.

The local coding agent may not:

- invent replacement path geometry,
- redraw a character or prop,
- alter anatomy, silhouette, facial expression, costume, palette, or composition,
- silently simplify the SVG to make validation pass,
- replace a rejected asset with procedural geometry,
- approve visual quality,
- process multiple unrelated asset failures in one task.

### 6.2 Frontier model

The frontier model is responsible for:

- original SVG geometry,
- silhouette and shape language,
- line weight,
- palette application,
- expression and visual readability,
- layer and group structure requested by the brief,
- visual revisions requested after proof review.

The frontier model receives only the bounded asset brief, optional approved references, the current SVG when revising, and a precise revision request.

### 6.3 Human operator

The human operator:

- copies the brief into the frontier-model conversation,
- obtains the resulting `.svg` file,
- transfers the file into the repository inbox,
- reviews the rendered proof at intended game size,
- explicitly approves or rejects the visual result,
- returns rejected assets to the frontier model with the generated revision request.

Human approval cannot be inferred from file presence, a successful build, or an agent report.

---

## 7. Repository layout

### Handoff workspace

```text
domains/ocean-rescue/assets/handoff/
├─ briefs/
│  └─ <asset-id>.md
├─ inbox/
│  └─ <asset-id>.svg
└─ revisions/
   └─ <asset-id>-rNN.md
```

Handoff files are workflow inputs and are not production source.

### Existing canonical and generated locations

```text
domains/ocean-rescue/assets/source/
├─ characters/
├─ scene/
├─ effects-ui/
├─ art-packet.json
└─ art-approval.json

domains/ocean-rescue/assets/review/
└─ visual proof artifacts

domains/ocean-rescue/assets/generated/
└─ deterministic atlas outputs and manifests
```

### Location rules

- `handoff/inbox/` never feeds the production build.
- Approval does not occur inside `handoff/inbox/`.
- After approval, the exact accepted SVG or a proven pixel-equivalent sanitized copy is moved or copied to the appropriate `source/<bundle>/` directory.
- The canonical file name follows repository naming conventions, not the download name supplied by the chat service.
- Handoff artifacts may be retained for audit or removed after canonicalization according to repository hygiene rules.

---

## 8. Asset state machine

Every manual SVG asset follows this state model:

```text
PLANNED
→ BRIEF_READY
→ SVG_RECEIVED
→ STRUCTURE_PASS
→ RENDER_PROOF_READY
→ HUMAN_VISUAL_PASS
→ CANONICALIZED
→ ATLAS_PASS
→ IN_GAME_PASS
→ COMPLETE
```

Rejection transitions:

```text
SVG_RECEIVED       → STRUCTURE_REJECTED
STRUCTURE_PASS      → RENDER_REJECTED
RENDER_PROOF_READY  → HUMAN_VISUAL_REJECTED
CANONICALIZED       → ATLAS_REJECTED
ATLAS_PASS          → IN_GAME_REJECTED
```

A rejected asset returns to `BRIEF_READY` through a bounded revision request. It does not skip directly to canonicalization.

---

## 9. Task selection contract

Before writing a brief, the local agent must define:

- **Asset ID**
- **Stable runtime alias**
- **One visual failure domain**
- **One direct hypothesis**
- **One binary visual criterion**
- **Intended logical display size**
- **Target scene and state**
- **Allowed repository paths**
- **Focused validation commands**

Example:

```text
Asset: scene.submarine
Failure: the submarine silhouette is unreadable at its actual travel-scene size
Hypothesis: a frontier-authored side-view SVG with a distinct cockpit, nose,
propeller, and rescue arm will remain identifiable at 220×125 logical pixels
Criterion: an unbriefed viewer identifies direction, cockpit, propulsion,
and rescue function within three seconds
```

Do not begin a second asset until the first reaches `COMPLETE`, is explicitly rejected and closed, or is blocked by a documented external dependency.

---

## 10. Asset brief contract

Each brief is stored at:

```text
domains/ocean-rescue/assets/handoff/briefs/<asset-id>.md
```

Required fields:

```markdown
# Asset identity

- Asset ID:
- Runtime alias:
- Target canonical path:
- Atlas bundle:

# Purpose

One paragraph describing what the player must understand from this asset.

# Actual display context

- Logical viewport: 1280×720
- Intended logical size:
- Camera/view:
- Facing direction:
- Background context:
- Occlusion constraints:

# Silhouette requirements

A short list of features that must remain readable at intended size.

# Visual style

- Palette version:
- Fill treatment:
- Outline treatment:
- Lighting direction:
- Depth treatment:

# Required structure

- Root viewBox:
- Required group IDs:
- Required movable parts:
- Pivot expectations:
- Transparent background: yes

# Preserve

Existing details that a revision must not change.

# Exclude

Specific unwanted motifs, unsafe content, external dependencies, text,
franchise resemblance, or excess detail.

# Binary acceptance criterion

One observable pass/fail sentence.
```

A brief must specify outcomes, not micromanage every SVG path. It must be short enough for a frontier model to follow without losing the primary visual objective.

---

## 11. Frontier-model request contract

The human operator may use the following request wrapper with the brief:

```text
Create or revise exactly one production SVG according to the attached asset brief.

Return a complete .svg file, not a tutorial, mock-up, poster, character sheet,
or raster image.

Preserve the required viewBox, group IDs, transparent background, and facing
direction. Do not use scripts, foreignObject, external URLs, external images,
external fonts, embedded raster images, or runtime animation.

Optimize visual readability for the stated in-game logical size. Do not imitate
an existing protected character, vehicle, logo, badge, or frame composition.

Also provide one preview image, but treat the SVG file as the deliverable.
```

For revisions, attach:

1. the exact current SVG,
2. the original brief,
3. the latest bounded revision request.

Do not ask the frontier model to redesign multiple assets in the same request.

---

## 12. Incoming SVG contract

An incoming SVG must satisfy all of the following before visual review.

### Required

- one root `<svg>` element,
- explicit `xmlns`,
- finite numeric `viewBox`,
- transparent background,
- deterministic local IDs,
- required group IDs from the brief,
- finite coordinates and transforms,
- no missing referenced local definitions,
- no embedded raster payload,
- no external resource dependency,
- no runtime animation requirement.

### Forbidden

- `<script>`,
- `<foreignObject>`,
- event handler attributes such as `onload` or `onclick`,
- `javascript:` URLs,
- network URLs,
- external `href` or `xlink:href`,
- embedded base64 raster images,
- external fonts or stylesheets,
- executable CSS,
- SMIL animation elements,
- unbounded filter regions,
- duplicate IDs,
- non-finite numeric values,
- invisible full-canvas click or tracking layers.

### Build compatibility

The SVG must rasterize successfully through the repository's pinned build toolchain. Visual effects unsupported or rendered inconsistently by that toolchain are rejected or returned for revision rather than approximated by the local agent.

The production runtime continues to consume atlas textures. Direct runtime SVG loading is outside this workflow.

---

## 13. Local modification boundary

### Allowed mechanical changes

A local agent may create a sanitized copy only when the operation is proven not to change rendered pixels at the acceptance dimensions. Examples include:

- removal of editor metadata,
- removal of comments,
- normalization of XML declaration,
- deterministic whitespace formatting,
- safe filename normalization,
- deterministic ID prefixing when all references are updated,
- attribute ordering that does not alter rendering.

### Forbidden local visual changes

The local agent may not alter:

- path data,
- shape coordinates,
- viewBox composition,
- group order,
- transforms,
- fill colors,
- stroke colors or widths,
- opacity,
- gradients,
- clipping or masks,
- facial features,
- anatomy,
- silhouette,
- costume details,
- perspective,
- lighting direction.

When any forbidden change appears necessary, the asset returns to the frontier-model revision loop.

### Pixel-equivalence rule

If a sanitized copy is created, render both original and sanitized files using the same pinned toolchain and acceptance dimensions. Canonicalization is allowed only when the comparison satisfies the repository's exact or declared pixel-equivalence threshold.

---

## 14. Validation gates

### Gate A — Intake identity

Pass when:

- the file maps to exactly one active brief,
- the intended asset ID and alias are unambiguous,
- the target bundle and canonical path are known,
- no unrelated asset files are bundled into the task.

### Gate B — Structure and security

Pass when:

- XML parses,
- required IDs exist,
- forbidden constructs are absent,
- all references resolve locally,
- IDs are unique,
- coordinates and transforms are finite,
- the file satisfies size and complexity limits,
- the pinned rasterizer completes without warning or fallback substitution.

### Gate C — Isolated render proof

Generate a transparent-background preview at:

- declared logical size,
- declared 2× raster scale,
- at least one actual-size 1× preview.

Reject blank, clipped, unexpectedly opaque, cropped, or materially different output.

### Gate D — In-context proof

Render the asset in the actual target scene at the intended logical size. The proof must include enough surrounding scene context to assess:

- silhouette,
- scale,
- contrast,
- direction,
- overlap,
- focal hierarchy,
- interaction readability,
- consistency with approved neighboring assets.

A large standalone SVG preview is not sufficient for approval.

### Gate E — Human visual approval

The human operator explicitly records one of:

```text
APPROVED
REJECTED
```

Silence, file transfer, or a passing test is not approval.

### Gate F — Canonical registration

After approval:

- place the accepted source under `assets/source/<bundle>/`,
- assign the canonical filename,
- update `art-packet.json`,
- record alias, source, bundle, logical size, scale, pivot, authoring method, approval state, revision note, and source hash,
- update the approval record and proof evidence through the repository's existing process.

Recommended authoring method value:

```text
frontier-svg-human-approved
```

### Gate G — Atlas and determinism

Pass when:

- focused art-packet validation passes,
- atlas generation passes,
- aliases remain stable,
- pivots remain valid,
- generated manifests are consistent,
- a repeated build from identical inputs is deterministic according to the existing contract,
- unrelated atlas bundles remain unchanged when the change is partition-local.

### Gate H — In-game acceptance

Pass when:

- the target scene loads through the normal runtime path,
- WebGL/WebGL2 displays the intended asset,
- Canvas fallback preserves the required flow,
- no placeholder geometry appears,
- no external-origin request is made,
- no console, page, CSP, or asset-loading error occurs,
- the task's single binary visual criterion passes.

---

## 15. Human visual review checklist

The human reviewer evaluates the actual-size in-context proof.

```text
[ ] The asset's purpose is understandable without reading the brief.
[ ] The silhouette remains readable at intended size.
[ ] Facing direction and action are unambiguous.
[ ] Major parts do not merge into one indistinct shape.
[ ] Contrast is sufficient against the real background.
[ ] The palette matches the approved Ocean Rescue direction.
[ ] Outline weight is consistent with neighboring assets.
[ ] No accidental franchise resemblance is apparent.
[ ] No anatomy, limb-count, or perspective defect is visible.
[ ] The asset does not obscure interaction targets or HUD.
[ ] The asset feels authored rather than like placeholder geometry.
```

Approval should fail when the asset is technically valid but visually weak.

---

## 16. Revision request contract

Rejected assets receive a bounded revision document:

```text
domains/ocean-rescue/assets/handoff/revisions/<asset-id>-rNN.md
```

Template:

```markdown
# Revision identity

- Asset ID:
- Revision:
- Previous proof:

# Preserve unchanged

List the aspects already approved.

# Observed defects

1. One visible defect.
2. Another visible defect only when it belongs to the same visual failure domain.

# Required changes

Use measurable visual instructions tied to actual display size.

# Do not change

List viewBox, IDs, direction, palette, proportions, or details that must remain stable.

# Binary re-review criterion

One observable pass/fail sentence.
```

Revision requests must describe visible evidence, not rewrite SVG path commands for the frontier model.

---

## 17. Naming and metadata

### Asset IDs

Use stable kebab-case identifiers with a revision-independent semantic identity.

Examples:

```text
submarine-player-side
sea-turtle-worried
sea-turtle-free
rescue-arm-front
terrain-reef-arch
hud-loop-icon
```

### Runtime aliases

Use the existing dotted namespace convention:

```text
scene.submarine
otter.head
turtle.worried
terrain.reef-arch
hud.loop-icon
```

Aliases may not encode page number, generated filename, revision number, or model name.

### SVG IDs

Prefix internal IDs with the asset identity to prevent collisions after processing.

Model provider names, chat identifiers, and conversation URLs are not runtime metadata.

---

## 18. Proof and audit evidence

The task report must retain or reference:

- active brief path,
- incoming SVG hash,
- structural validation result,
- isolated render proof,
- in-context proof,
- explicit human approval or rejection,
- canonical source hash,
- art-packet entry,
- approval record update,
- atlas build result,
- focused in-game acceptance result,
- final commit SHA when published.

The report must distinguish:

- the SVG returned by the frontier model,
- any sanitized pixel-equivalent copy,
- the final canonical source,
- generated atlas outputs.

---

## 19. Completion definition

An asset task is `COMPLETE` only when all are true:

```text
brief exists
AND incoming SVG is traceable
AND structure/security validation passes
AND actual-size in-context proof exists
AND human explicitly approves
AND canonical source is registered
AND approval evidence is updated
AND deterministic atlas build passes
AND focused in-game acceptance passes
AND the change is published according to repository policy
```

A visually rejected, structurally rejected, or unapproved file is not partial production progress. It remains a handoff artifact.

---

## 20. Failure and blocker policy

Use `BLOCKED` only when the single active asset cannot proceed because of a concrete external dependency, such as:

- the frontier model did not return a usable SVG file,
- the human has not yet transferred the file,
- explicit visual approval is pending,
- the pinned rasterizer cannot represent a required effect and the brief must be revised,
- a prerequisite canonical alias or pivot contract is unresolved.

Do not block because:

- unrelated repository tests fail,
- `origin/main` advanced without overlapping the target paths,
- another asset remains visually weak,
- a larger visual redesign is desirable.

Those remain separate tasks.

---

## 21. Compatibility notes as of 2026-08-01

- The project remains pinned to PixiJS `8.19.0`. Current PixiJS documentation supports loading SVG assets and the June 2026 release added SVG-related capabilities, but this workflow deliberately preserves the existing build-time raster-atlas contract. Runtime SVG loading is not introduced by this specification.
- SVGO `4.0.1` is the current upstream release. If SVGO is adopted for mechanical cleanup, the repository must pin its exact version and configuration. A floating `npx svgo` invocation is not canonical, and optimization may not remove required IDs, viewBox data, pivots, or layer structure.

These notes do not authorize dependency upgrades. Toolchain changes require their own bounded task and determinism proof.

---

## 22. Initial adoption sequence

Adopt this workflow with exactly one representative asset.

Recommended sequence:

1. select the highest-impact currently weak asset,
2. write one brief,
3. obtain one frontier-authored SVG manually,
4. validate without local visual edits,
5. produce an actual-size in-context proof,
6. obtain explicit human approval,
7. canonicalize and rebuild the affected atlas bundle,
8. verify the normal runtime path,
9. close the task before selecting the next asset.

Do not begin with a bulk character pack or environment replacement.

---

## 23. Change control

Changes to this specification must preserve:

- no-API operation,
- human-controlled transfer,
- explicit human visual approval,
- local-agent non-redraw boundary,
- untrusted inbox separation,
- canonical art-packet and approval registration,
- deterministic atlas generation,
- one-asset failure-domain isolation.

A future automated generation pipeline, direct model API integration, or runtime SVG architecture requires a separate superseding specification. It may not be introduced as an incidental implementation detail of an asset task.
