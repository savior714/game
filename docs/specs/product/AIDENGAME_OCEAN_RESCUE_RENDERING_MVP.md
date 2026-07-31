# AidenGame Ocean Rescue — Rendering MVP

- **Version:** v0.7
- **Date:** 2026-07-31
- **Status:** Renderer architecture and runtime fallback closed / authored-art production workflow unresolved
- **Parent product spec:** `AIDENGAME_OCEAN_RESCUE_MVP_PRD.md`
- **Scope:** visual rendering quality only
- **Selected renderer:** PixiJS v8
- **Current implementation baseline:** PixiJS 8.19.0
- **Renderer preference:** WebGL → Canvas fallback
- **Selected asset path:** authored source → build-time raster atlas + JSON metadata
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

Migrating only the visual layer to a PixiJS v8 scene graph and replacing procedural placeholder subjects with authored 2D assets—while preserving current gameplay state and input contracts—will make the product visually understandable and emotionally readable without new missions, progression, mechanics, or broader world-building.

**Binary criterion**

A first-time viewer who has not read instructions can identify within three seconds that:

1. a sea-otter rescue leader has arrived,
2. a sea turtle needs help,
3. seaweed loops are the obstacle,
4. the player should pull those loops away.

---

## 2. Scope boundary

Allowed decisions are limited to PixiJS renderer architecture, authored asset production and representation, atlas generation, scene layering, sprite/cutout animation, scaling, visual effects, performance guardrails, and deterministic single-HTML packaging.

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
- Sea otter should read as cute, calm, intelligent, and dependable
- Animation representation: separated cutout parts plus facial-state swaps; full frame-by-frame animation is not required

---

## 4. First rendering vertical slice

The first and only mandatory slice is the **sea-turtle rescue gameplay scene**.

Presentation:

- Fixed side-view diorama
- Submarine visible as rear support on the left
- Sea-otter leader active near the center
- Turtle and seaweed loops visually dominant on the right
- HUD and support portrait kept to safe-edge regions

Retained interaction:

- Three large seaweed loops
- One active loop at a time
- Player drags the active loop outward to release it
- Incorrect drag returns only the current loop without penalty
- Repeated failure strengthens the directional hint
- Each successful release changes the turtle’s face and posture

This interaction validates rendering and animation only. It must not reopen wider mission design.

---

## 5. PixiJS renderer architecture

- Use PixiJS v8, currently pinned to `8.19.0` at this decision point.
- Bundle PixiJS locally; production may not depend on a runtime CDN.
- Use one `PIXI.Application`, one renderer/context, and one controlled frame loop.
- Existing gameplay modules remain canonical.
- PixiJS display objects never become canonical gameplay state.
- A bounded adapter maps read-only gameplay snapshots into the scene graph.
- Rendering may emit normalized pointer intents but may not redefine success, failure, progression, pause, or save behavior.
- Remove the old Canvas paint path only after the PixiJS slice independently passes visual and input acceptance.

Root hierarchy:

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

Input remains in the fixed logical 1280×720 coordinate system. PixiJS event targets may identify a visual subject but may not silently change the existing hit geometry.

---

## 6. Production renderer preference and fallback

### Selected order

```text
WebGL → Canvas fallback
```

Equivalent initialization intent:

```js
preference: ['webgl', 'canvas']
```

Contracts:

- WebGL/WebGL2 is the production visual-quality reference path.
- WebGPU is excluded from this rendering MVP and must not be selected automatically.
- Canvas fallback is an execution-resilience path, not the visual-parity acceptance reference.
- Canvas fallback must preserve mission progression, input alignment, scene ordering, mandatory character visibility, and rescue completion.
- Effects unsupported or materially different in Canvas may be disabled through an explicit backend capability table; primary subjects may not revert to visible placeholder geometry.
- Renderer selection occurs once during application startup and must not switch during an active mission.
- The selected backend is exposed in diagnostics and automated test evidence.
- If neither WebGL nor Canvas initializes, the game shows an explicit blocking compatibility message rather than a blank surface.

Validation boundaries:

- Full visual acceptance and Galaxy Tab performance acceptance run on WebGL.
- Canvas receives a bounded smoke test for startup, asset loading, input alignment, loop dragging, completion, pause, and exit.
- Both backends use the same logical coordinates, stable frame aliases, asset manifest, and canonical gameplay state.

---

## 7. Authored asset pipeline

Production assets are **build-time packed raster texture atlases with JSON metadata**.

```text
authored source files
  → validation
  → declared-scale rasterization
  → deterministic trim and padding
  → deterministic atlas packing
  → atlas image + spritesheet JSON
  → embedded single-HTML bundle
  → PixiJS Assets manifest/cache
```

Contracts:

- Prefer SVG source for clean character, vehicle, UI, and simple environment art.
- High-resolution raster source is allowed for painted or textured elements.
- Mandatory assets must not rely on runtime SVG rasterization.
- PixiJS Sprite/Texture is the primary runtime representation.
- No per-frame texture creation, decode, or upload.
- Frame aliases and cutout pivots remain stable across deterministic rebuilds.
- Duplicate aliases, missing frames, invalid pivots, or out-of-bounds rectangles fail the build.
- Identical source bytes, tool versions, scale, trim, padding, partition, and compression settings reproduce identical atlas bytes and metadata.

The generated manifest records source hashes, aliases, source scale, pivot/anchor metadata, atlas membership, page hashes, and spritesheet JSON hashes.

---

## 8. Atlas partition and page policy

The first slice uses exactly three lifecycle-based bundles.

### `characters.atlas`

- Sea-otter cutout parts and facial states
- Sea-turtle body and facial states
- Puffin and sea-lion communication portraits

### `scene.atlas`

- Submarine side view
- Coral-reef background and distant silhouettes
- Midground reef, fish, foreground coral, and sand
- Three seaweed-loop assets and static scene props

### `effects-ui.atlas`

- Bubbles and glow textures
- Drag arrows and active-target highlights
- Success particles
- Communication frame and compact HUD icons

Partition and page invariants:

- Membership is declared rather than inferred from file size.
- Frames do not migrate between bundles without an explicit manifest change.
- Aliases are globally unique.
- All three bundles load before the rescue scene becomes interactive.
- Runtime accesses frames by alias, never by pixel coordinates or page number.
- A partition-local change leaves the other two outputs byte-identical.
- Every atlas page is bounded to 4096 pixels on each axis.
- 4096×4096 is a ceiling, not a fixed output size.
- Oversized bundles split into deterministic multiple pages inside the same bundle.
- Multi-page overflow may not change aliases or cutout pivots.

---

## 9. Resolution and pixel-density policy

- Canonical logical viewport: **1280×720**.
- Gameplay state, hit geometry, layout anchors, camera bounds, and pointer conversion use this coordinate system.
- Effective renderer resolution is `Math.min(window.devicePixelRatio || 1, 2)`.
- Normal MVP render targets never exceed **2560×1440**.
- Automatic dynamic-resolution switching is outside this MVP.
- Mandatory character, creature, vehicle, interaction, and UI art is rasterized at a declared **2× source scale** relative to logical display size.
- CSS resizing, browser zoom, letterboxing, or DPR changes may resize the backing surface but may not move logical hit targets.
- Visual/hit alignment is verified at effective DPR 1, 1.5, and 2.

---

## 10. Minimum layers and animation

Minimum visible layers:

1. water gradient/far background,
2. distant silhouettes and light rays,
3. midground reef and fish,
4. submarine,
5. rescue target and obstacle,
6. active sea-otter rig,
7. foreground coral and sand,
8. interaction hints and effects,
9. HUD and communication portrait.

Minimum animation states:

- **Sea otter:** idle breathing, blink, concern, reach, pull/lean-back, success
- **Sea turtle:** worried, partial relief, greater relief, free/happy
- **Submarine:** arrival drift, idle hover, support light/scanner
- **Environment:** slow bubbles, subtle seaweed sway, restrained fish, light-ray shimmer

Environmental motion remains slower and lower contrast than the active rescue action.

---

## 11. Readability, performance, and packaging

Readability:

- Sea otter, turtle, submarine, and active loop remain recognizable at 25% screenshot scale.
- The active loop has the strongest local interaction contrast.
- Turtle facial states remain readable without zooming.
- Foreground decoration does not obscure interaction targets.
- Inactive fish do not resemble interactive targets.
- Text panels are not the dominant visual mass.

Runtime guardrails:

- Responsive pointer tracking during drag
- Stable animation cadence
- No per-frame display-object recreation
- No repeated image decode or texture upload
- Bounded particles
- One renderer/context only
- No filter or mask proliferation without device evidence
- No fallback to visible placeholder geometry for primary subjects

Packaging:

- Final artifact remains one HTML file.
- PixiJS, atlas images, spritesheet JSON, manifest, and runtime code are bundled at build time.
- Mandatory rendering assets make zero third-party runtime requests.
- Development source remains modular and deterministic outputs remain testable.

---

## 12. Rendering MVP acceptance criteria

The MVP passes only when:

1. Primary subjects use authored assets rather than placeholder geometry.
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
14. One PixiJS renderer/context is used.
15. Assets are generated into the three declared partitions.
16. A partition-local change leaves the other two outputs byte-identical.
17. Frame aliases and cutout pivots remain stable.
18. Logical gameplay coordinates remain 1280×720 at every supported DPR.
19. Effective renderer DPR never exceeds 2 in normal MVP mode.
20. No atlas page exceeds 4096 pixels on either axis.
21. Multi-page overflow remains inside its declared bundle and is deterministic.
22. WebGL is selected whenever it initializes successfully.
23. Canvas fallback preserves a complete playable rescue flow without visible primary-subject placeholders.
24. WebGPU is not selected in this MVP.

---

## 13. Explicit non-goals

- Final-quality rendering of all three missions
- Full rigs for all three team members
- Headquarters, launch-bay, character-selection, or mission-selection redesign
- New dialogue, mechanics, or progression
- 3D rendering, dynamic lighting, physics-based cloth/hair/fluid, or cinematic camera
- Rive, Spine, skeletal physics, React-Pixi, or another animation/runtime layer
- Runtime procedural character generation
- Automatic dynamic-resolution switching
- Visual parity between WebGL and the Canvas resilience path

---

## 14. Next unresolved rendering decision

Renderer architecture, renderer fallback, atlas representation, atlas partition, resolution, and page policy are closed.

The next Grill-me question must choose only the **authored-art production workflow** for the first slice. It must not reopen character, narrative, mission, mechanic, or world-building decisions.
