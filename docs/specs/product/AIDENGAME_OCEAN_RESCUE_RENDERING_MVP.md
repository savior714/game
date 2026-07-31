# AidenGame Ocean Rescue — Rendering MVP

- **Version:** v0.5
- **Date:** 2026-07-31
- **Status:** Renderer, asset pipeline, atlas partition, and resolution policy closed / atlas page limit unresolved
- **Parent product spec:** `AIDENGAME_OCEAN_RESCUE_MVP_PRD.md`
- **Scope:** visual rendering quality only
- **Selected renderer:** PixiJS v8
- **Current implementation baseline:** PixiJS 8.19.0
- **Selected asset path:** authored source → build-time raster atlas + JSON metadata
- **Selected atlas partition:** three lifecycle-based atlas bundles
- **Logical resolution:** 1280×720
- **Renderer resolution:** `min(devicePixelRatio, 2)`
- **Primary device:** Galaxy Tab S10-class landscape tablet
- **Build constraint:** final deployable remains a single HTML artifact

---

## 1. Purpose

This document defines the minimum rendering upgrade required to move Ocean Rescue from a functional geometric prototype to a visually legible children’s game.

It does **not** replace or redesign gameplay, progression, input, pause, save-data, or mission contracts in the parent MVP PRD.

The rendering MVP answers one question only:

> How should the existing game be rendered so that characters, vehicles, environments, and rescue actions are immediately recognizable instead of appearing as placeholder shapes and text panels?

### Failure domain

`OCEAN_RESCUE_FUNCTIONAL_GAMEPLAY_IS_RENDERED_AS_PLACEHOLDER_GEOMETRY_AND_TEXT_WITHOUT_A_COHERENT_CHARACTER_ASSET_OR_SCENE_COMPOSITION_SYSTEM`

### Direct hypothesis

Migrating only the visual layer to a PixiJS v8 scene graph and replacing procedural placeholder subjects with authored 2D assets—while preserving current gameplay state and input contracts—will make the product visually understandable and emotionally readable without new missions, progression, mechanics, or broader world-building.

### Binary criterion

A first-time viewer who has not read instructions can identify within three seconds that:

1. a sea-otter rescue leader has arrived,
2. a sea turtle needs help,
3. seaweed loops are the obstacle,
4. the player should pull those loops away.

---

## 2. Scope boundary

Allowed decisions are limited to:

- PixiJS renderer architecture,
- authored asset representation,
- atlas generation and partition,
- scene layering,
- sprite and cutout animation composition,
- logical resolution and pixel-density policy,
- visual effects,
- performance guardrails,
- deterministic single-HTML packaging.

Explicitly excluded:

- additional character biography, naming, or relationships,
- new dialogue,
- new missions or rescue mechanics,
- progression redesign,
- expanded vehicle catalog,
- headquarters lore,
- collectibles or merchandising systems.

---

## 3. Retained visual anchors

### Style

- Original television-animation-style 2D presentation
- Rounded, readable silhouettes
- Friendly expressions
- Strong representative colors
- Toy-like rescue equipment
- Non-threatening danger presentation
- No direct copying of an existing commercial character, costume, vehicle, badge, or composition

### Rescue team

1. **Sea otter** — leader and pilot
2. **Puffin** — technology and scouting
3. **Sea lion** — ecology and care

Only the sea otter requires a complete in-game cutout rig in the first slice. The puffin and sea lion may remain communication portraits or static support art.

### Uniform and palette

- Fully unified retro-futuristic marine rescue suit
- Rounded helmet and equipment forms
- Minimal surface detail
- Primary palette: teal, orange, cream white
- Supporting palette: deep navy, coral red, pale sky blue

### Sea-otter impression

The lead character must appear cute, calm, intelligent, dependable, and expressive without exaggerated baby proportions.

### Animation representation

- 2D cutout rig
- Separate head, torso, forelimbs, hind limbs, tail, eyes, and mouth where required
- Facial-expression swaps
- No full frame-by-frame animation requirement for this MVP

---

## 4. First rendering vertical slice

The first and only mandatory rendering slice is the **sea-turtle rescue gameplay scene**.

### Presentation

- Fixed side-view diorama
- Submarine visible as rear support
- Sea-otter leader active in the foreground
- Turtle and obstacle dominant on the right half
- Puffin and sea lion limited to portrait callouts when used

Approximate composition:

```text
┌────────────────────────────────────────────────────┐
│ Mission objective                   Support portrait│
│                                                    │
│ Submarine       Sea-otter leader       Sea turtle  │
│ rear support    active character       rescue target│
│                                                    │
│ coral foreground  seaweed interaction   sand/rocks │
└────────────────────────────────────────────────────┘
```

Recommended allocation:

- left 20–25%: submarine and support light,
- center 25–30%: sea-otter leader,
- right 35–40%: turtle and seaweed loops,
- remaining space: environmental framing and UI safe areas.

### Retained interaction

- Three large seaweed loops
- One active loop at a time
- Player drags the active loop outward to release it
- Incorrect drag returns the current loop without penalty
- Repeated failure strengthens the directional hint
- Each successful release changes the turtle’s face and posture

This interaction validates rendering and animation only. It must not reopen wider mission design.

---

## 5. PixiJS renderer architecture

### Renderer contract

- Use PixiJS v8, currently pinned to `8.19.0` at this decision point.
- Bundle PixiJS locally into the final HTML.
- Runtime CDN dependency is prohibited.
- Use one `PIXI.Application`, one renderer, one graphics context, and one controlled frame loop.
- Rive, Spine, React-Pixi, or a second WebGL renderer are outside this MVP.

### Migration boundary

- Existing gameplay modules remain canonical.
- PixiJS display objects never become canonical gameplay state.
- A bounded render adapter maps read-only game snapshots into the scene graph.
- Rendering may emit normalized pointer intents but may not redefine success, failure, or progression.
- Remove the old Canvas paint path only after the PixiJS slice independently passes visual and input acceptance.

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

RenderGroups may be used only for major partitions such as `gameplayWorld` and `hud`; they must not be assigned to every small container without profile evidence.

### Input boundary

- Convert browser pointer coordinates once into the fixed logical 1280×720 coordinate system.
- Existing domain hit-test and gesture rules remain authoritative.
- PixiJS event targets may identify a visual subject but may not silently alter hit geometry.
- Debug hit areas remain inspectable and invisible in production.

---

## 6. Authored asset pipeline

Production runtime assets are **build-time packed raster texture atlases with JSON metadata**.

```text
authored source files
  → validation
  → rasterization at declared source scale
  → deterministic trim and padding
  → deterministic atlas packing
  → atlas image + spritesheet JSON
  → embedded single-HTML bundle
  → PixiJS Assets manifest and cache
```

### Authoring sources

- SVG is preferred for clean character, vehicle, UI, and simple environment source art.
- High-resolution raster source is allowed for painted or textured elements.
- Mandatory production assets must not depend on runtime SVG rasterization.
- Source files remain individually reviewable and replaceable.

### Runtime contract

- PixiJS Sprites and Textures are the primary runtime representation.
- Textures are created once from loaded spritesheets and reused.
- No texture creation, image decode, or upload is permitted per frame.
- Frame aliases remain stable across packing runs.
- Cutout-rig pivots remain stable after trimming.
- Duplicate aliases, missing frames, invalid pivots, and out-of-bounds rectangles fail the build.

### Determinism

Given identical source bytes, packer version, raster scale, trim rules, padding, partition configuration, and compression settings, the build must reproduce identical atlas image bytes and JSON metadata.

Record at minimum:

- source-file hash,
- frame alias,
- source scale,
- pivot or anchor metadata,
- atlas membership,
- atlas image hash,
- spritesheet JSON hash.

---

## 7. Atlas partition

The first slice uses exactly three lifecycle-based atlas bundles.

### `characters.atlas`

- sea-otter cutout parts and facial states,
- sea-turtle body and facial states,
- puffin communication portrait,
- sea-lion communication portrait.

Character art updates must not repack the environment atlas. Rig pivots and aliases are stable contracts.

### `scene.atlas`

- submarine side view,
- coral-reef background elements,
- distant silhouettes,
- midground reef and fish,
- foreground coral and sand,
- three seaweed-loop assets,
- static scene props.

Large full-screen or near-full-screen layers may use dedicated pages while remaining inside the `scene` bundle identity.

### `effects-ui.atlas`

- bubbles,
- glow textures,
- drag arrows,
- active-target highlights,
- success particles,
- communication portrait frame,
- compact HUD icons required by the slice.

### Partition invariants

- Atlas membership is declared, not inferred solely from file size.
- A frame may not migrate between atlases without an explicit manifest change.
- No duplicate alias may exist across atlases.
- All three bundles load before the rescue scene becomes interactive.
- Runtime access uses stable aliases, never pixel coordinates or page numbers.
- A change confined to one partition must leave the other two outputs byte-identical.

---

## 8. Resolution and pixel-density policy

### Logical coordinate system

- Canonical logical viewport: **1280×720**.
- All gameplay state, hit geometry, layout anchors, camera bounds, and pointer conversion use this coordinate system.
- CSS scaling and device pixel ratio must not change gameplay coordinates or acceptance geometry.

### Renderer resolution

Initialize the PixiJS renderer with an effective resolution equivalent to:

```js
Math.min(window.devicePixelRatio || 1, 2)
```

Rules:

- DPR values below 1 are normalized to 1 unless a separately validated degraded mode is introduced.
- DPR values above 2 do not increase the renderer resolution.
- Maximum normal render target: **2560×1440**.
- The DPR cap is a rendering-quality and memory guardrail, not a gameplay setting.
- No automatic runtime DPR switching is part of this MVP.

### Asset source scale

- Mandatory character, creature, vehicle, interaction, and UI assets are rasterized for a declared **2× source scale** relative to logical display size.
- Assets expected to occupy a stable screen region must not be enlarged from undersized source frames.
- Lower-DPR devices downsample the 2× atlas through the renderer’s declared scale mode.
- Atlas metadata must retain source scale so runtime code does not infer it from filenames.

### Resize and input invariants

- Resizing recalculates CSS fit and letterboxing without mutating logical object coordinates.
- Pointer conversion uses the actual canvas bounds and renderer resolution only once before producing logical coordinates.
- A DPR or browser zoom change may resize the backing surface but may not move the logical hit target.
- Visual and hit-test alignment must be verified at effective DPR 1, 1.5, and 2.

### Resolution acceptance

The policy passes only when:

1. the 1280×720 scene remains visually sharp at DPR 2,
2. character outlines and turtle facial states remain readable,
3. drag targets remain aligned after CSS resizing and letterboxing,
4. no code path creates a render target above 2560×1440 in the normal MVP mode,
5. the Galaxy Tab-class target shows no obvious drag latency or sustained animation collapse from the selected resolution.

---

## 9. Required visual layers and animation

Minimum visible layers:

1. water gradient or far background,
2. distant silhouettes and light rays,
3. midground reef and fish,
4. submarine,
5. rescue target and obstacle,
6. active sea-otter cutout rig,
7. foreground coral and sand,
8. interaction hints and effects,
9. HUD and communication portrait.

Minimum animation states:

### Sea otter

- idle breathing,
- blink,
- attention or concern,
- reach toward active loop,
- pull or lean-back motion,
- success reaction.

### Sea turtle

- worried idle,
- partial relief after loop one,
- greater relief after loop two,
- free and happy after loop three.

### Submarine

- arrival drift,
- idle hover,
- support light or scanner activation.

### Environment

- slow bubbles,
- subtle seaweed sway,
- restrained fish movement,
- light-ray drift or shimmer.

Environmental motion remains slower and lower contrast than the active rescue action.

---

## 10. Readability, performance, and packaging

### Readability

- Sea otter, turtle, submarine, and active loop remain recognizable at 25% screenshot scale.
- The active loop has the strongest local interaction contrast.
- The turtle’s face remains readable without zooming.
- Foreground decoration does not obscure interaction targets.
- Inactive fish do not resemble targets.
- Text panels are not the dominant visual mass.

### Runtime guardrails

- Responsive pointer tracking during drag
- Stable animation cadence
- No per-frame display-object recreation
- No repeated image decode or texture upload
- Bounded particle counts
- One renderer/context only
- No filter or mask proliferation without device evidence
- No quality fallback to placeholder primary subjects

### Packaging

- Final artifact remains one HTML file.
- PixiJS, atlas images, spritesheet JSON, manifest, and required runtime code are bundled at build time.
- Mandatory rendering assets make zero third-party runtime requests.
- Asset identity and deterministic bundling are testable.
- Development source remains modular.

---

## 11. Rendering MVP acceptance criteria

The rendering MVP passes only when all are true:

1. Primary subjects use authored assets rather than placeholder geometry.
2. The scene has distinct far, middle, gameplay, foreground, effect, and UI layers.
3. The sea otter has idle, pull, and success states with facial changes.
4. The turtle progresses visibly from worried to relieved to free.
5. The submarine belongs to the same palette and design family.
6. The active seaweed loop is immediately distinguishable.
7. A first-time viewer explains the rescue situation within three seconds without reading instructions.
8. Pointer input remains aligned across the supported 16:9 scaling path.
9. Galaxy Tab-class hardware runs the scene without obvious drag latency or sustained animation collapse.
10. Existing gameplay, pause, progression, failure-isolation, and save-data contracts remain unchanged.
11. The single-HTML build is deterministic and reproducible.
12. Production contains no visible debug placeholders for primary subjects.
13. PixiJS and mandatory assets are bundled locally.
14. The application uses one PixiJS renderer/context.
15. Assets are generated into the three declared atlas partitions.
16. A change confined to one partition leaves the other two outputs byte-identical.
17. Frame aliases and cutout pivots remain stable across deterministic rebuilds.
18. Logical gameplay coordinates remain 1280×720 at every supported DPR.
19. Effective renderer DPR never exceeds 2 in normal MVP mode.
20. Visual and hit-test alignment passes at effective DPR 1, 1.5, and 2.

---

## 12. Explicit non-goals

- Final-quality rendering of all three missions
- Full rigs for all three team members
- Headquarters or launch-bay redesign
- Character-selection or mission-selection redesign
- New dialogue, mechanics, or progression
- 3D rendering
- Dynamic lighting system
- Physics-based cloth, hair, or fluid simulation
- Cinematic camera system
- Rive, Spine, skeletal physics, or another animation runtime
- React-based PixiJS scene management
- Runtime procedural character generation
- Automatic dynamic-resolution switching

---

## 13. Next unresolved rendering decision

Renderer, asset representation, atlas partition, and resolution policy are closed.

The next Grill-me question must choose only the **maximum atlas page dimension and multi-page policy**. It must not reopen character, narrative, mission, mechanic, or world-building decisions.
