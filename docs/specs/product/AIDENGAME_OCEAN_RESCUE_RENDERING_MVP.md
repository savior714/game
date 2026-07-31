# AidenGame Ocean Rescue — Rendering MVP

- **Version:** v0.9
- **Date:** 2026-07-31
- **Status:** IMPLEMENTATION_READY
- **Parent product spec:** `AIDENGAME_OCEAN_RESCUE_MVP_PRD.md`
- **Scope:** visual rendering quality only
- **Selected renderer:** PixiJS v8
- **Current implementation baseline:** PixiJS 8.19.0
- **Renderer preference:** WebGL → Canvas fallback
- **Selected asset path:** authored source → build-time raster atlas + JSON metadata
- **Authored-art workflow:** AI concept exploration → manual cleanup/redraw → canonical SVG/high-resolution source → cutout preparation → atlas build
- **Selected atlas partition:** `characters` / `scene` / `effects-ui`
- **Logical resolution:** 1280×720
- **Renderer resolution:** `min(devicePixelRatio, 2)`
- **Atlas page limit:** each axis ≤ 4096, deterministic multi-page overflow
- **Implementation strategy:** representative final-quality assets and production pipeline are implemented together
- **Primary device:** Galaxy Tab S10-class landscape tablet
- **Build constraint:** final deployable remains a single HTML artifact

---

## 1. Purpose

This specification defines the minimum rendering upgrade required to move Ocean Rescue from a functional placeholder prototype to a visually legible children’s game.

It does not redesign gameplay, progression, input, pause, save-data, dialogue, or mission contracts in the parent PRD.

### Failure domain

`OCEAN_RESCUE_FUNCTIONAL_GAMEPLAY_IS_RENDERED_AS_PLACEHOLDER_GEOMETRY_AND_TEXT_WITHOUT_A_COHERENT_CHARACTER_ASSET_OR_SCENE_COMPOSITION_SYSTEM`

### Direct hypothesis

Migrating only the visual layer to a PixiJS v8 scene graph and replacing procedural placeholder subjects with authored 2D assets will make the product visually and emotionally readable while preserving the current domain gameplay contracts.

### Binary criterion

A first-time viewer who has not read instructions can identify within three seconds that:

1. a sea-otter rescue leader has arrived,
2. a sea turtle needs help,
3. seaweed loops are the obstacle,
4. the player should pull those loops away.

---

## 2. Scope boundary

Allowed work:

- PixiJS renderer integration
- authored visual assets
- texture-atlas generation
- scene layering
- cutout animation
- visual effects
- scaling and DPR handling
- performance guardrails
- deterministic single-HTML packaging

Explicitly excluded:

- new character biography, naming, or relationships
- new dialogue
- new missions
- new rescue mechanics
- progression redesign
- headquarters or vehicle-catalog expansion
- collectibles, badges, or merchandising systems
- final-quality rendering of missions 2 and 3

---

## 3. Retained visual anchors

- Original television-animation-style 2D presentation
- Rounded and immediately readable silhouettes
- Friendly expressions
- Toy-like rescue equipment
- Non-threatening danger presentation
- No direct copying of an existing commercial character, costume, badge, vehicle, or composition
- Core visual team: sea otter, puffin, sea lion
- First slice: full sea-otter rig; puffin and sea lion may remain communication portraits
- Unified retro-futuristic marine rescue suit
- Primary palette: teal, orange, cream white
- Supporting palette: deep navy, coral red, pale sky blue
- Sea otter reads as cute, calm, intelligent, and dependable
- Animation uses separated cutout parts and facial-state swaps

---

## 4. First rendering vertical slice

The only mandatory rendering slice is the **sea-turtle rescue gameplay scene**.

### Composition

- Fixed side-view diorama
- Submarine visible as rear support on the left
- Sea-otter leader active near the center
- Turtle and seaweed loops dominant on the right
- HUD and portrait callouts constrained to safe-edge areas
- Foreground coral frames the scene without covering interaction targets

Recommended allocation:

- left 20–25%: submarine and support light
- center 25–30%: sea-otter leader
- right 35–40%: turtle and seaweed loops
- remaining area: environment and UI safety margins

### Retained interaction

- Three large seaweed loops
- One active loop at a time
- Player drags the active loop outward to release it
- Incorrect drag returns only the current loop
- No penalty or mission failure
- Repeated failure strengthens the directional hint
- Each successful release changes the turtle’s expression and posture

This interaction exists only to validate rendering, animation, and visual readability. It may not reopen the wider mission design.

---

## 5. PixiJS renderer architecture

### Runtime contract

- Pin PixiJS exactly to `8.19.0` for the first implementation baseline.
- Bundle PixiJS locally into the final HTML.
- Make zero runtime requests to a renderer CDN.
- Use one `PIXI.Application`.
- Use one renderer/context.
- Use one controlled frame loop.
- Existing gameplay modules remain canonical.
- PixiJS display objects never become canonical gameplay state.
- A bounded adapter maps read-only gameplay snapshots into the scene graph.
- Rendering may emit normalized pointer intents but may not redefine success, failure, progression, pause, or save behavior.
- Remove the old Canvas paint path only after the equivalent PixiJS slice passes visual and input acceptance.

### Root hierarchy

```text
stage
├─ farBackground
├─ midground
├─ gameplayWorld
│  ├─ submarine
│  ├─ turtleAndObstacle
│  └─ seaOtterRig
├─ foreground
├─ effects
└─ hud
```

RenderGroups may be used only for major partitions such as `gameplayWorld` and `hud`.

### Input boundary

- Convert browser pointer coordinates once into logical 1280×720 coordinates.
- Existing hit geometry and gesture rules remain authoritative.
- PixiJS event targets may identify visual subjects but may not silently change hit geometry.
- Debug hit areas remain inspectable and invisible in production.

---

## 6. Renderer preference and fallback

Selected order:

```text
WebGL → Canvas fallback
```

Equivalent initialization intent:

```js
preference: ['webgl', 'canvas']
```

Contracts:

- WebGL/WebGL2 is the production visual-quality reference.
- WebGPU is excluded from this MVP.
- Canvas is an execution-resilience path, not a visual-parity target.
- Canvas must preserve startup, asset loading, scene order, input alignment, loop dragging, rescue completion, pause, and exit.
- Backend-specific effects may be disabled through an explicit capability table.
- Primary subjects may never revert to visible placeholder geometry.
- Renderer selection occurs once at startup and does not switch during an active mission.
- Diagnostics and test evidence record the selected backend.
- Failure of both backends displays an explicit compatibility message instead of a blank canvas.

---

## 7. Authored-art production workflow

Selected workflow:

```text
AI concept exploration
→ select one direction
→ manual redraw and cleanup
→ canonical SVG or high-resolution raster source
→ cutout and expression preparation
→ deterministic atlas build
→ PixiJS integration
```

### AI-use boundary

- AI images are concept references only.
- Raw AI-generated images are not production atlas inputs.
- AI-generated frames may not be shipped directly.
- Final assets must have manually controlled silhouette, anatomy, palette, outline, lighting, and part boundaries.
- The final source must be independently editable without regenerating an AI image.
- Existing commercial characters may be used only as broad genre references and may not be traced or reproduced.

### Canonical source requirements

Each production asset records:

- stable asset ID
- source path
- source hash
- source type
- declared scale
- atlas partition
- pivot or anchor metadata
- authoring method
- approval state
- revision note

Only approved canonical source directories may feed the production atlas build.

### Mandatory first-slice asset set

`characters`:

- sea-otter head
- torso
- near/far forelimbs
- near/far hind limbs as required
- tail
- eye states
- mouth states
- sea-turtle body states
- sea-turtle facial states
- optional puffin and sea-lion portraits

`scene`:

- submarine side view
- far water background
- distant reef silhouettes
- midground reef and restrained fish
- foreground coral and sand
- three seaweed-loop assets
- static scene props

`effects-ui`:

- bubbles
- glow texture
- drag arrow
- active-target highlight
- success particles
- portrait frame
- required HUD icons

---

## 8. Representative-final-quality implementation strategy

The production pipeline and representative final-quality assets are implemented together.

### Principle

There is no separate acceptance phase using crude placeholder primary subjects. The first accepted PixiJS scene must already contain representative final-quality authored art.

Temporary geometry is allowed only for:

- invisible hit areas
- debug overlays
- alignment guides
- temporary particles during development

It is not allowed for visible characters, creatures, vehicles, coral, or rescue obstacles in the acceptance scene.

### Implementation sequence

#### Phase A — Canonical art packet and contracts

Create a small but final-quality proof packet:

- sea-otter head, torso, one arm pair, tail, eyes, and mouth
- turtle worried and free states
- one production-quality seaweed loop
- submarine side-view asset
- one far background, one midground element, and one foreground element
- one drag indicator and one success effect

At the same time define:

- stable aliases
- cutout pivots
- source scale
- atlas membership
- palette and outline constants
- source validation rules

#### Phase B — Production atlas pipeline

Using the Phase A packet:

- validate sources
- rasterize at declared 2× scale
- trim and pad deterministically
- pack into declared lifecycle bundles
- emit spritesheet JSON
- emit manifest and hashes
- embed outputs in the single-HTML build
- prove deterministic rebuild behavior

This phase does not pass with dummy rectangles or generated stand-ins.

#### Phase C — PixiJS scene skeleton

Integrate the generated packet into:

- selected renderer initialization
- asset bundle loading
- named scene containers
- logical 1280×720 layout
- DPR-capped rendering
- pointer conversion
- resize and letterboxing
- WebGL diagnostics
- Canvas fallback smoke path

#### Phase D — Complete the representative slice

Complete the remaining mandatory final-quality assets and integrate:

- full sea-otter minimum rig
- all turtle relief states
- all three seaweed loops
- complete submarine presentation
- complete coral-reef layer set
- required HUD and effects

Add required motion:

- sea-otter idle, blink, concern, reach, pull, and success
- turtle worried, partial relief, greater relief, and free
- submarine arrival drift, hover, and support light
- restrained bubbles, seaweed sway, fish motion, and light shimmer

#### Phase E — Acceptance and old-renderer removal

Validate:

- three-second scene comprehension
- interaction visibility
- hit alignment at DPR 1, 1.5, and 2
- WebGL performance on Galaxy Tab-class hardware
- Canvas rescue-flow smoke test
- single-HTML deterministic build
- zero third-party runtime requests
- existing gameplay regression suite

Remove the old Canvas paint path only after the PixiJS slice passes these gates.

### Sequence invariants

- Art and renderer contracts evolve together through explicit aliases and pivots.
- A pipeline change must be exercised with real representative art.
- An art change must pass atlas and in-scene validation.
- No phase may broaden gameplay scope to obtain a visual demo.
- Work may be split into independent technical failure domains, but all converge on the same first vertical slice.

---

## 9. Atlas pipeline

Production runtime assets are build-time packed raster texture atlases with JSON metadata.

```text
canonical authored sources
→ validation
→ declared-scale rasterization
→ deterministic trim and padding
→ deterministic packing
→ atlas pages + spritesheet JSON
→ asset manifest
→ embedded single-HTML bundle
→ PixiJS Assets registry/cache
```

Contracts:

- Prefer SVG for clean characters, vehicles, UI, and simple environment art.
- High-resolution raster is allowed for painted or textured elements.
- Mandatory assets may not rely on runtime SVG rasterization.
- PixiJS Sprite and Texture are the primary runtime representation.
- No per-frame texture creation, image decode, or texture upload.
- Aliases and pivots remain stable across deterministic rebuilds.
- Duplicate aliases, missing frames, invalid pivots, or out-of-bounds rectangles fail the build.
- Identical inputs and tool versions reproduce identical atlas bytes and metadata.

The manifest records source hashes, aliases, source scale, pivots, atlas membership, page hashes, and spritesheet JSON hashes.

---

## 10. Atlas partition and page policy

Exactly three lifecycle-based bundles are used.

### `characters.atlas`

- sea-otter cutout parts and facial states
- sea-turtle body and facial states
- puffin and sea-lion portraits

### `scene.atlas`

- submarine
- backgrounds and reef layers
- fish and foreground elements
- three seaweed loops
- static props

### `effects-ui.atlas`

- bubbles and glow textures
- drag arrows and highlights
- success particles
- portrait frame and HUD icons

Invariants:

- Membership is declared rather than inferred from file size.
- Aliases are globally unique.
- A frame may not migrate between bundles without an explicit manifest change.
- All three bundles load before rescue input is enabled.
- Runtime resolves frames by alias, never page number or pixel rectangle.
- A partition-local change leaves the other two outputs byte-identical.
- Every atlas page is bounded to 4096 pixels on each axis.
- 4096×4096 is a ceiling, not a fixed output size.
- Oversized bundles split deterministically into multiple pages within the same bundle.
- Multi-page overflow may not alter aliases or pivots.

---

## 11. Resolution and pixel-density policy

- Canonical logical viewport: **1280×720**
- Effective renderer resolution: `Math.min(window.devicePixelRatio || 1, 2)`
- Maximum normal backing target: **2560×1440**
- Automatic dynamic-resolution switching is outside this MVP.
- Mandatory character, creature, vehicle, interaction, and UI art uses a declared **2× source scale**.
- CSS scaling, zoom, letterboxing, and DPR changes may not move logical hit targets.
- Visual and hit-test alignment must pass at effective DPR 1, 1.5, and 2.

---

## 12. Readability and performance guardrails

### Readability

- Sea otter, turtle, submarine, and active loop remain recognizable at 25% screenshot scale.
- The active loop has the strongest local interaction contrast.
- Turtle facial states remain readable without zooming.
- Foreground decoration does not obscure targets.
- Inactive fish do not resemble interactive targets.
- Text panels are not the dominant visual mass.
- The scene looks like a paused animation frame before it looks like a debug canvas.

### Runtime

- Responsive pointer tracking during drag
- Stable animation cadence
- No per-frame display-object recreation
- No repeated image decode or texture upload
- Bounded particle counts
- One renderer/context only
- No filter or mask proliferation without device evidence
- No quality fallback to visible placeholder primary subjects

### Packaging

- Final artifact remains one HTML file.
- PixiJS, atlas pages, spritesheet JSON, manifest, and runtime code are bundled at build time.
- Mandatory renderer and rendering assets make zero third-party runtime requests.
- Development source remains modular.
- Generated outputs remain deterministic and testable.

---

## 13. Acceptance criteria

The rendering MVP passes only when all are true:

1. Primary subjects use approved authored assets rather than placeholder geometry.
2. Far, middle, gameplay, foreground, effect, and UI layers are independently represented.
3. The sea otter has idle, pull, and success states with facial changes.
4. The turtle progresses visibly from worried to relieved to free.
5. The submarine belongs to the same palette and design family.
6. The active loop is immediately distinguishable.
7. A first-time viewer explains the rescue situation within three seconds without reading instructions.
8. Pointer input remains aligned across supported scaling and DPR paths.
9. Galaxy Tab-class hardware has no obvious drag latency or sustained animation collapse.
10. Existing gameplay, pause, progression, failure-isolation, and save-data contracts remain unchanged.
11. The single-HTML build is deterministic and reproducible.
12. Production contains no visible debug placeholders for primary subjects.
13. PixiJS and mandatory assets are bundled locally.
14. Exactly one PixiJS renderer/context is used.
15. Assets are generated into the three declared atlas partitions.
16. A partition-local change leaves the other two outputs byte-identical.
17. Frame aliases and cutout pivots remain stable.
18. Logical gameplay coordinates remain 1280×720 at every supported DPR.
19. Effective renderer DPR never exceeds 2 in normal MVP mode.
20. No atlas page exceeds 4096 pixels on either axis.
21. Multi-page overflow remains in its declared bundle and is deterministic.
22. WebGL is selected whenever it initializes successfully.
23. Canvas fallback preserves a complete playable rescue flow without visible primary-subject placeholders.
24. WebGPU is not selected.
25. Raw AI-generated images are absent from production atlas inputs.
26. Every production frame traces to an approved canonical source.
27. The first accepted slice uses representative final-quality art rather than a separate placeholder art pass.
28. The old Canvas paint path is removed only after the PixiJS slice passes acceptance.

---

## 14. Implementation readiness

All product-level decisions required to begin the rendering MVP are closed:

- rendering scope
- vertical slice
- visual anchors
- renderer
- backend fallback
- asset representation
- authored-art workflow
- atlas partition
- atlas page policy
- logical resolution
- DPR cap
- implementation sequence
- acceptance boundary

Remaining matters are implementation details and evidence gathering. They should be resolved through bounded technical tasks rather than further product Grill-me questions.

A new user decision is required only when implementation evidence exposes a genuine product trade-off that cannot be resolved within this specification.
