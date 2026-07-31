# AidenGame Ocean Rescue — Rendering MVP

- **Version:** v0.4
- **Date:** 2026-07-31
- **Status:** Renderer, asset representation, and atlas partition closed / resolution policy unresolved
- **Parent product spec:** `AIDENGAME_OCEAN_RESCUE_MVP_PRD.md`
- **Scope:** visual rendering quality only
- **Selected renderer:** PixiJS v8
- **Current implementation baseline:** PixiJS 8.19.0
- **Selected asset path:** authored source → build-time raster atlas + JSON metadata
- **Selected atlas partition:** three lifecycle-based atlases
- **Primary device:** Galaxy Tab S10-class landscape tablet
- **Build constraint:** final deployable remains a single HTML artifact

---

## 1. Purpose

This document defines the minimum rendering upgrade required to move Ocean Rescue from a functional geometric prototype to a visually legible children’s game.

It does **not** replace or redesign the gameplay, progression, input, pause, save-data, or mission contracts in the parent MVP PRD.

The rendering MVP answers one question only:

> How should the existing game be rendered so that characters, vehicles, environments, and rescue actions are immediately recognizable instead of appearing as placeholder shapes and text panels?

---

## 2. Failure domain and binary criterion

### Failure domain

`OCEAN_RESCUE_FUNCTIONAL_GAMEPLAY_IS_RENDERED_AS_PLACEHOLDER_GEOMETRY_AND_TEXT_WITHOUT_A_COHERENT_CHARACTER_ASSET_OR_SCENE_COMPOSITION_SYSTEM`

### Direct hypothesis

Migrating only the visual layer to a PixiJS v8 scene graph and replacing procedural placeholder subjects with authored 2D assets—while preserving current gameplay state and input contracts—will make the product visually understandable and emotionally readable without requiring new missions, progression, mechanics, or broader world-building.

### Binary criterion

A viewer who has not read the instructions can identify within three seconds that:

1. a sea-otter rescue leader has arrived,
2. a sea turtle needs help,
3. seaweed loops are the current obstacle,
4. the player should pull those loops away.

---

## 3. Scope boundary

The retained decisions below are visual anchors only. This rendering MVP does not expand:

- character biographies or names,
- team relationships,
- dialogue,
- mission count,
- rescue mechanics,
- progression,
- vehicle catalog,
- headquarters lore,
- collectibles or merchandising systems.

Allowed decision areas are limited to:

- PixiJS renderer architecture,
- authored asset representation,
- atlas generation and partition,
- scene layering,
- sprite and cutout animation composition,
- scaling and pixel-density policy,
- visual effects,
- performance guardrails,
- deterministic single-HTML packaging.

---

## 4. Retained visual anchors

### 4.1 Style

- Original television-animation-style 2D presentation
- Rounded, readable silhouettes
- Friendly expressions
- Strong representative colors
- Toy-like rescue equipment
- Non-threatening danger presentation
- No direct copying of an existing commercial character, costume, vehicle, badge, or composition

### 4.2 Rescue team

1. **Sea otter** — leader and pilot
2. **Puffin** — technology and scouting
3. **Sea lion** — ecology and care

Only the sea otter requires a full in-game cutout rig in the first slice. The puffin and sea lion may remain communication portraits or static support art.

### 4.3 Uniform and palette

- Fully unified retro-futuristic marine rescue suit
- Rounded helmet and equipment forms
- Large readable controls and badge
- Minimal surface detail
- Primary palette: teal, orange, cream white
- Supporting palette: deep navy, coral red, pale sky blue

### 4.4 Sea-otter impression

The lead character must appear cute, calm, intelligent, dependable, and expressive without exaggerated baby proportions.

### 4.5 Animation representation

- 2D cutout rig
- Separate head, torso, forelimbs, hind limbs, tail, eyes, and mouth where required
- Facial-expression swaps
- No full frame-by-frame requirement for this MVP

---

## 5. First rendering vertical slice

### 5.1 Target

The first and only mandatory rendering slice is the **sea-turtle rescue gameplay scene**. It becomes the reference implementation for later mission rendering.

### 5.2 Presentation

- Fixed side-view diorama
- Submarine visible as rear support
- Sea-otter leader active in the foreground
- Turtle and obstacle dominant on the right half
- Puffin and sea lion limited to portrait callouts when used

Approximate composition:

```text
┌────────────────────────────────────────────────────┐
│ Mission objective                    Support portrait│
│                                                    │
│ Submarine        Sea-otter leader      Sea turtle   │
│ rear support     active character      rescue target │
│                                                    │
│ coral foreground   seaweed interaction   sand/rocks │
└────────────────────────────────────────────────────┘
```

Recommended screen allocation:

- left 20–25%: submarine and support light,
- center 25–30%: sea-otter leader,
- right 35–40%: turtle and seaweed loops,
- remaining space: environmental framing and UI safe areas.

### 5.3 Retained interaction

- Three large seaweed loops
- One active loop at a time
- Player drags the active loop outward to release it
- Incorrect drag returns the current loop without penalty
- Repeated failure strengthens the directional hint
- Each successful release changes the turtle’s face and posture

This interaction validates rendering and animation only. It must not trigger redesign of the wider mission rules.

---

## 6. PixiJS renderer architecture

### 6.1 Renderer decision

The rendering MVP uses **PixiJS v8**, currently pinned to **8.19.0** at this decision point.

- PixiJS is bundled locally into the final HTML.
- Runtime CDN dependency is prohibited.
- One `PIXI.Application`, one renderer, one graphics context, and one controlled frame loop are used.
- Rive, Spine, React-Pixi, or a second WebGL renderer are outside this MVP.

### 6.2 Migration boundary

- Existing gameplay modules remain canonical.
- PixiJS display objects never become canonical gameplay state.
- A bounded render adapter maps read-only game snapshots into the PixiJS scene graph.
- Rendering may emit normalized pointer intents but may not redefine success, failure, or progression.
- The old Canvas paint path is removed only after the corresponding PixiJS slice independently passes visual and input acceptance.

### 6.3 Root hierarchy

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

### 6.4 Input boundary

- Browser pointer coordinates are converted once into the fixed logical 16:9 coordinate system.
- Existing domain hit-test and gesture rules remain authoritative.
- PixiJS event targets may identify the visual subject but may not silently alter hit geometry.
- Debug hit areas remain inspectable and invisible in production.

---

## 7. Authored asset pipeline

### 7.1 Selected representation

Production runtime assets are **build-time packed raster texture atlases with JSON metadata**.

The canonical pipeline is:

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

### 7.2 Authoring sources

- SVG is preferred for clean character, vehicle, UI, and simple environment source art.
- High-resolution raster source is allowed for painted or textured elements.
- Production must not depend on runtime SVG rasterization for mandatory slice assets.
- Source files remain individually reviewable and replaceable.

### 7.3 Runtime contract

- PixiJS Sprites and Textures are the primary runtime representation.
- Textures are created once from the loaded spritesheets and reused.
- No texture creation, image decode, or upload is permitted per frame.
- Frame aliases remain stable across packing runs.
- Cutout-rig pivots remain stable after trimming.
- Duplicate aliases, missing frames, invalid pivots, and out-of-bounds frame rectangles fail the build.

### 7.4 Determinism

Given identical source bytes, packer version, raster scale, trim rules, padding, and partition configuration, the build must reproduce identical atlas image bytes and JSON metadata.

The build records at minimum:

- source-file hash,
- generated-frame alias,
- source scale,
- pivot or anchor metadata,
- atlas membership,
- atlas image hash,
- spritesheet JSON hash.

---

## 8. Selected atlas partition

The first slice uses exactly three lifecycle-based atlases.

### 8.1 `characters.atlas`

Contains assets that share character-oriented revision and animation lifecycles:

- sea-otter cutout parts,
- sea-otter facial states,
- sea-turtle body states,
- sea-turtle facial states,
- puffin communication portrait,
- sea-lion communication portrait.

Rules:

- Rig pivots and frame aliases are contractually stable.
- Updating character art does not repack the environment atlas.
- Portraits may share this atlas because they change with character art direction.

### 8.2 `scene.atlas`

Contains assets tied to the sea-turtle rescue environment and stage composition:

- submarine side view,
- coral-reef background elements,
- distant silhouettes,
- midground reef and fish,
- foreground coral and sand,
- three seaweed-loop assets,
- static scene props.

Rules:

- The three interaction loops have explicit stable aliases.
- Background layers remain independently addressable even when packed together.
- Large full-screen or near-full-screen layers may use dedicated atlas pages when packer limits require it, while remaining inside the `scene` bundle identity.

### 8.3 `effects-ui.atlas`

Contains small, frequently reused presentation assets:

- bubbles,
- glow textures,
- drag arrows,
- active-target highlights,
- success particles,
- communication portrait frame,
- compact HUD icons required by the slice.

Rules:

- Effects remain reusable and independent of the mission scene atlas.
- Procedural particles may reference atlas textures but particle counts remain bounded.
- Text panels and large background art do not enter this atlas.

### 8.4 Partition invariants

- Atlas membership is declared, not inferred solely from current file size.
- A frame may not migrate between atlases without an explicit manifest change.
- No duplicate alias may exist across atlases.
- All three atlases load before the rescue scene becomes interactive.
- The runtime accesses frames by stable alias rather than pixel coordinates or atlas page number.
- `characters`, `scene`, and `effects-ui` are registered as explicit PixiJS asset bundles.
- A change confined to one partition must not change the generated bytes of the other two partitions.

### 8.5 Why not one global atlas

A single atlas would couple character, environment, and effect revisions, creating unnecessary repacks and unstable incremental evidence.

### 8.6 Why not one atlas per object

Per-object atlases would produce unnecessary texture and manifest fragmentation without a meaningful lifecycle benefit for this slice.

---

## 9. Required render layers and authored assets

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

Mandatory authored assets:

- sea-otter cutout parts,
- sea-turtle body and facial states,
- three seaweed-loop assets,
- one submarine side-view asset,
- coral-reef background layers,
- foreground coral and sand,
- communication portrait frame,
- bubble, glow, drag-arrow, and success-effect textures.

Procedural geometry is allowed only for invisible hit areas, debug overlays, temporary development guides, and simple non-disruptive particles. Primary characters, animals, vehicles, rocks, coral, and rescue obstacles must not ship as plain circles, rectangles, labels, or unstyled paths.

---

## 10. Minimum animation set

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

## 11. Readability and performance guardrails

At the target 16:9 viewport:

- sea otter, turtle, submarine, and active loop remain recognizable at 25% screenshot scale,
- the active loop has the strongest local interaction contrast,
- the turtle’s face remains readable without zooming,
- foreground decoration does not obscure interaction targets,
- inactive fish do not resemble targets,
- text panels are not the dominant visual mass.

Runtime guardrails:

- responsive pointer tracking during drag,
- stable animation cadence,
- no per-frame display-object recreation,
- no repeated image decode or texture upload,
- bounded particle counts,
- one renderer/context only,
- no filter or mask proliferation without device evidence,
- no quality fallback to placeholder primary subjects.

---

## 12. Packaging

- Final artifact remains one HTML file.
- PixiJS, atlas images, spritesheet JSON, manifest, and required runtime code are bundled at build time.
- Mandatory rendering assets make zero third-party runtime requests.
- Asset identity and deterministic bundling are testable.
- Development source remains modular.

---

## 13. Acceptance criteria

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
16. A change confined to one partition leaves the other two atlas outputs byte-identical.
17. Frame aliases and cutout pivots remain stable across deterministic rebuilds.

---

## 14. Explicit non-goals

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

---

## 15. Current technology evidence

- PixiJS `Assets` provides cached loading, aliases, manifests, bundles, background loading, and spritesheet JSON support.
- PixiJS documentation recommends manifests and bundles for structured asset management and documents AssetPack as a manifest-generation option.
- PixiJS v8.18–8.19 added renderer fallback arrays, live HTML textures, Graphics-to-SVG export, sprite mask channels, and transient WebGPU MSAA attachments.

These capabilities support the selected three-bundle atlas architecture but do not close the remaining pixel-density and memory-budget decisions.

---

## 16. Next unresolved rendering decision

Renderer, asset representation, and atlas partition are closed.

The next Grill-me question must choose only the **logical resolution and device-pixel-ratio policy** for the first slice. It must not reopen character, narrative, mission, mechanic, or world-building decisions.
