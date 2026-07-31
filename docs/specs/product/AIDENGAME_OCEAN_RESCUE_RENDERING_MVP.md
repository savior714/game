# AidenGame Ocean Rescue — Rendering MVP

- **Version:** v0.8
- **Date:** 2026-07-31
- **Status:** Rendering architecture and authored-art workflow closed / implementation sequencing unresolved
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
- **Primary device:** Galaxy Tab S10-class landscape tablet
- **Build constraint:** final deployable remains a single HTML artifact

---

## 1. Purpose and failure domain

This document defines the minimum rendering upgrade required to move Ocean Rescue from a functional geometric prototype to a visually legible children’s game. It does not replace or redesign gameplay, progression, input, pause, save-data, or mission contracts in the parent MVP PRD.

**Failure domain**

`OCEAN_RESCUE_FUNCTIONAL_GAMEPLAY_IS_RENDERED_AS_PLACEHOLDER_GEOMETRY_AND_TEXT_WITHOUT_A_COHERENT_CHARACTER_ASSET_OR_SCENE_COMPOSITION_SYSTEM`

**Direct hypothesis**

Migrating only the visual layer to a PixiJS v8 scene graph and replacing procedural placeholder subjects with consistently authored 2D assets—while preserving current gameplay and input contracts—will make the product visually understandable and emotionally readable without adding missions, mechanics, progression, or world-building.

**Binary criterion**

A first-time viewer who has not read instructions can identify within three seconds that:

1. a sea-otter rescue leader has arrived,
2. a sea turtle needs help,
3. seaweed loops are the obstacle,
4. the player should pull those loops away.

---

## 2. Scope boundary

Allowed decisions are limited to renderer architecture, authored asset production and representation, atlas generation, scene layering, sprite/cutout animation, scaling, visual effects, performance guardrails, and deterministic single-HTML packaging.

Explicitly excluded:

- additional character biography, naming, or relationships,
- new dialogue, missions, rescue mechanics, or progression,
- expanded vehicle catalog or headquarters lore,
- collectibles or merchandising systems.

---

## 3. Retained visual anchors

- Original television-animation-style 2D presentation
- Rounded, readable silhouettes and friendly expressions
- Toy-like rescue equipment and non-threatening danger presentation
- No direct copying of an existing commercial character, costume, vehicle, badge, or composition
- Core visual team: sea otter, puffin, sea lion
- First slice requires a full sea-otter cutout rig; puffin and sea lion may remain portraits
- Unified retro-futuristic marine rescue suit
- Primary palette: teal, orange, cream white
- Supporting palette: deep navy, coral red, pale sky blue
- Sea otter reads as cute, calm, intelligent, and dependable
- Animation uses separated cutout parts and facial-state swaps; full frame-by-frame animation is not required

---

## 4. First rendering vertical slice

The first and only mandatory slice is the **sea-turtle rescue gameplay scene**.

- Fixed side-view diorama
- Submarine visible as rear support on the left
- Sea-otter leader active near the center
- Turtle and seaweed loops visually dominant on the right
- HUD and support portrait kept to safe-edge regions
- Three large seaweed loops, one active at a time
- Player drags the active loop outward to release it
- Incorrect drag returns only the current loop without penalty
- Repeated failure strengthens the directional hint
- Each successful release changes the turtle’s face and posture

This interaction validates rendering and animation only. It must not reopen wider mission design.

---

## 5. PixiJS renderer architecture

- Use PixiJS v8, pinned to `8.19.0` at this decision point.
- Bundle PixiJS locally; production may not depend on a runtime CDN.
- Use one `PIXI.Application`, one renderer/context, and one controlled frame loop.
- Existing gameplay modules remain canonical.
- PixiJS display objects never become canonical gameplay state.
- A bounded adapter maps read-only gameplay snapshots into the scene graph.
- Rendering may emit normalized pointer intents but may not redefine success, failure, progression, pause, or save behavior.
- Remove the old Canvas paint path only after the PixiJS slice independently passes visual and input acceptance.

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

RenderGroups may be used only for major partitions such as `gameplayWorld` and `hud`, not every small sprite.

---

## 6. Production renderer preference and fallback

```text
WebGL → Canvas fallback
```

- WebGL/WebGL2 is the production visual-quality reference path.
- WebGPU is excluded from this MVP.
- Canvas is an execution-resilience path, not a visual-parity target.
- Canvas must preserve startup, asset loading, input alignment, scene ordering, mandatory character visibility, loop dragging, pause, exit, and rescue completion.
- Unsupported effects may be disabled through an explicit backend capability table.
- Primary subjects may never revert to visible placeholder geometry.
- Renderer selection occurs once during startup and is exposed in diagnostics.
- If neither renderer initializes, show an explicit compatibility message rather than a blank surface.

---

## 7. Authored-art production workflow

### 7.1 Selected workflow

```text
AI concept exploration
→ select one coherent visual direction
→ manual silhouette, line, palette, anatomy, and proportion cleanup
→ redraw/vectorize into canonical source assets
→ split character parts and facial states
→ validate pivots, naming, scale, and layer ownership
→ build deterministic raster atlases
```

AI generation is used only to accelerate concept exploration. It is not the production asset generator.

### 7.2 Canonical source contract

Production source of truth is limited to:

- manually cleaned SVG for characters, vehicles, UI, props, and simple environment art,
- manually cleaned high-resolution raster source for painted or textured environment elements,
- explicit metadata for frame alias, pivot, anchor, source scale, and atlas membership.

AI concept images, prompts, seeds, chat outputs, and unedited generated rasters are **non-canonical reference material**. The build must not consume them directly.

### 7.3 Manual cleanup requirements

Before an asset becomes canonical, a human cleanup pass must normalize:

- silhouette readability,
- face and species identity,
- line weight,
- palette,
- lighting direction,
- perspective,
- costume details,
- limb count and anatomy,
- transparent edges,
- cutout overlap allowance,
- naming and layer structure.

Characters must remain visually identical across idle, concern, pull, and success states. A frame that changes facial proportions, costume geometry, fur pattern, or species-defining features is rejected rather than patched at runtime.

### 7.4 Cutout preparation

The sea-otter rig requires separately authored parts for at least:

- torso,
- head,
- near and far forelimbs,
- near and far hind limbs when visible,
- tail,
- eyes or eyelids,
- mouth states,
- optional helmet or tool layer where movement requires separation.

Parts include sufficient hidden overlap for rotation without exposing gaps. Pivots are declared in source metadata and survive trim and atlas packing.

The turtle uses stable body art plus controlled facial/posture state changes for worried, partial relief, greater relief, and free/happy states.

### 7.5 Originality boundary

Concept references may use genre-level qualities such as friendly marine rescue animation, rounded toy-like equipment, or a bright children’s television palette. They may not target or reproduce a specific protected character, costume, vehicle, badge, logo, or frame composition.

Manual cleanup must remove accidental resemblance rather than treating AI output as sufficient evidence of originality.

### 7.6 Review and provenance

Each canonical source asset records:

- asset identifier,
- source path,
- authoring method (`manual`, `AI-concept-assisted-manual-redraw`, or `manual-raster`),
- reviewer status,
- source hash,
- approved palette/version,
- declared atlas bundle,
- pivot/anchor metadata where relevant.

Concept images may be retained in a clearly non-production reference directory, but their presence is optional. Production builds read only approved canonical source directories.

---

## 8. Atlas pipeline and partition

```text
canonical authored source
→ validation
→ declared-scale rasterization
→ deterministic trim and padding
→ deterministic atlas packing
→ atlas image + spritesheet JSON
→ embedded single-HTML bundle
→ PixiJS Assets manifest/cache
```

Runtime contracts:

- PixiJS Sprite/Texture is the primary representation.
- No per-frame texture creation, decode, or upload.
- Frame aliases and cutout pivots remain stable.
- Duplicate aliases, missing frames, invalid pivots, or out-of-bounds rectangles fail the build.
- Identical source bytes and pinned generation settings reproduce identical atlas bytes and metadata.

The first slice uses exactly three bundles:

### `characters.atlas`

- sea-otter cutout parts and facial states,
- sea-turtle body and facial states,
- puffin and sea-lion communication portraits.

### `scene.atlas`

- submarine side view,
- coral-reef backgrounds and silhouettes,
- midground reef and fish,
- foreground coral and sand,
- seaweed-loop assets and static props.

### `effects-ui.atlas`

- bubbles and glow textures,
- drag arrows and active-target highlights,
- success particles,
- communication frame and compact HUD icons.

Partition/page rules:

- Membership is declared, not inferred from file size.
- Aliases are globally unique.
- Runtime accesses frames by alias, never page number or pixel rectangle.
- A partition-local change leaves the other two outputs byte-identical.
- Every page is bounded to 4096 pixels on each axis.
- Oversized bundles split deterministically inside the same bundle.
- Multi-page overflow may not change aliases or pivots.

---

## 9. Resolution and input policy

- Canonical logical viewport: `1280×720`.
- Effective renderer resolution: `Math.min(window.devicePixelRatio || 1, 2)`.
- Normal render target never exceeds `2560×1440`.
- Mandatory character, creature, vehicle, interaction, and UI art is rasterized at declared 2× source scale.
- Automatic dynamic resolution is outside this MVP.
- CSS resizing, browser zoom, letterboxing, and DPR changes may not move logical hit targets.
- Visual/hit alignment is verified at DPR 1, 1.5, and 2.

---

## 10. Minimum layers and animation

Minimum visible layers:

1. water/far background,
2. distant silhouettes and light rays,
3. midground reef and fish,
4. submarine,
5. turtle and obstacle,
6. sea-otter rig,
7. foreground coral and sand,
8. interaction hints and effects,
9. HUD and communication portrait.

Minimum animation states:

- **Sea otter:** idle breathing, blink, concern, reach, pull/lean-back, success
- **Sea turtle:** worried, partial relief, greater relief, free/happy
- **Submarine:** arrival drift, idle hover, support light/scanner
- **Environment:** slow bubbles, subtle seaweed sway, restrained fish movement, light-ray shimmer

Environmental motion remains slower and lower contrast than the rescue action.

---

## 11. Readability, performance, and packaging

- Sea otter, turtle, submarine, and active loop remain recognizable at 25% screenshot scale.
- Active loop has the strongest local interaction contrast.
- Turtle facial states remain readable without zooming.
- Decoration does not obscure interactive targets.
- Text panels are not the dominant visual mass.
- Pointer tracking remains responsive during drag.
- No per-frame display-object recreation, repeated decode, or texture upload.
- Particles are bounded.
- One renderer/context only.
- Final artifact remains one HTML file with PixiJS, atlases, JSON, manifest, and runtime code bundled locally.
- Mandatory assets make zero third-party runtime requests.

---

## 12. Acceptance criteria

The rendering MVP passes only when:

1. Primary subjects use approved canonical authored assets rather than procedural placeholders or raw AI output.
2. AI concept images are not consumed by the production build.
3. The sea otter remains visually consistent across required states and has valid cutout overlap and pivots.
4. The turtle progresses visibly from worried to relieved to free.
5. Far, middle, gameplay, foreground, effect, and UI layers are independently represented.
6. The active loop is immediately distinguishable.
7. A first-time viewer explains the rescue situation within three seconds without reading instructions.
8. Pointer input remains aligned across supported scaling and DPR paths.
9. Galaxy Tab-class hardware has no obvious drag latency or sustained animation collapse.
10. Existing gameplay, pause, progression, failure-isolation, and save-data contracts remain unchanged.
11. The single-HTML build is deterministic and reproducible.
12. PixiJS and mandatory assets are bundled locally.
13. One PixiJS renderer/context is used.
14. Assets are generated into the three declared partitions.
15. Frame aliases and cutout pivots remain stable.
16. No atlas page exceeds 4096 pixels on either axis.
17. WebGL is selected whenever it initializes successfully.
18. Canvas fallback preserves a complete playable rescue flow without visible primary-subject placeholders.
19. WebGPU is not selected.
20. Each production asset has explicit provenance and approval metadata.

---

## 13. Explicit non-goals

- Final-quality rendering of all three missions
- Full rigs for all three team members
- Headquarters, launch-bay, character-selection, or mission-selection redesign
- New dialogue, mechanics, or progression
- 3D rendering, dynamic lighting, physics-based cloth/hair/fluid, or cinematic camera
- Rive, Spine, React-Pixi, or another animation runtime
- Runtime procedural character generation
- Automatic dynamic-resolution switching
- Direct use of raw AI-generated images as production sprites

---

## 14. Next unresolved rendering decision

Renderer, fallback, asset representation, atlas policy, resolution, and authored-art workflow are closed.

The next Grill-me question must choose only the **implementation sequence for the first visual slice**: whether to prove the rendering pipeline with temporary production-shaped assets first, complete representative final art first, or integrate one representative final-quality asset pack and the pipeline together. It must not reopen character, narrative, mission, mechanic, or world-building decisions.
