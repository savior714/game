# AidenGame Ocean Rescue — Rendering MVP

- **Version:** v0.3
- **Date:** 2026-07-31
- **Status:** Renderer and asset representation closed / atlas partition unresolved
- **Parent product spec:** `AIDENGAME_OCEAN_RESCUE_MVP_PRD.md`
- **Scope:** visual rendering quality only
- **Selected renderer:** PixiJS v8
- **Current implementation baseline:** PixiJS 8.19.0
- **Primary device:** Galaxy Tab S10-class landscape tablet
- **Build constraint:** final deployable remains a single HTML artifact

---

## 1. Purpose

This document defines the minimum rendering upgrade required to move Ocean Rescue from a functional geometric prototype to a visually legible children’s game.

It does **not** replace the gameplay, progression, input, pause, save-data, or mission contracts in the parent MVP PRD.

The rendering MVP answers one question only:

> How should the existing game be rendered so that characters, vehicles, environments, and rescue actions are immediately recognizable instead of appearing as placeholder shapes and text panels?

---

## 2. Current failure domain

### Failure domain

`OCEAN_RESCUE_FUNCTIONAL_GAMEPLAY_IS_RENDERED_AS_PLACEHOLDER_GEOMETRY_AND_TEXT_WITHOUT_A_COHERENT_CHARACTER_ASSET_OR_SCENE_COMPOSITION_SYSTEM`

### Direct hypothesis

Migrating only the visual layer to a PixiJS v8 scene graph and replacing procedural placeholder subjects with authored 2D assets—while preserving the current gameplay state and input contracts—will make the product visually understandable and emotionally readable without requiring new missions, progression, mechanics, or a broader world-building pass.

### Binary criterion

A viewer who has not read the instructions can identify within three seconds that:

1. a sea-otter rescue leader has arrived,
2. a sea turtle needs help,
3. seaweed loops are the current obstacle,
4. the player should pull those loops away.

---

## 3. Scope reset

The prior Grill-me sequence expanded into character lore, team structure, costume identity, and vehicle world-building. Those decisions are retained only as **visual anchors**.

From this point forward, the Grill-me process is limited to:

- PixiJS renderer architecture,
- asset representation,
- scene layering,
- sprite and animation composition,
- scaling and pixel-density policy,
- visual effects,
- performance guardrails,
- asset packaging into the single HTML build.

The following are explicitly outside the current decision scope:

- additional character biographies,
- character names,
- additional team relationships,
- new dialogue,
- new missions,
- new rescue mechanics,
- new progression,
- expanded vehicle catalog,
- base or headquarters lore,
- collectible or merchandising systems.

---

## 4. Retained visual anchors

### 4.1 Overall style

- Original television-animation-style 2D presentation
- Rounded, readable silhouettes
- Friendly expressions
- Strong representative colors
- Toy-like rescue equipment
- Dangerous situations must remain visually non-threatening
- No direct copying of an existing commercial character, costume, vehicle, badge, or composition

### 4.2 Rescue team visual anchors

Three-member animal rescue team:

1. **Sea otter** — leader and pilot
2. **Puffin** — technology and scouting
3. **Sea lion** — ecology and care

For the first rendering slice, only the sea otter requires a full in-game cutout rig. The puffin and sea lion may remain communication portraits or static support art.

### 4.3 Uniform

- Fully unified team uniform
- Retro-futuristic marine rescue suit
- Rounded helmet and equipment forms
- Large readable controls and badge
- Minimal surface detail
- Character identity comes primarily from species silhouette, face, and movement rather than costume variation

### 4.4 Palette

Primary:

- teal,
- orange,
- cream white.

Supporting:

- deep navy for outlines and depth,
- coral red for limited danger emphasis,
- pale sky blue for bubbles, scanning, and success effects.

### 4.5 Lead character impression

The sea-otter leader must appear:

- cute,
- calm,
- intelligent,
- dependable,
- expressive without exaggerated baby proportions.

### 4.6 Animation representation

- 2D cutout rig
- Separate head, torso, forelimbs, hind limbs, tail, eyes, and mouth where required
- Facial-expression swaps
- No requirement for full frame-by-frame animation in this MVP

---

## 5. First rendering vertical slice

### 5.1 Slice target

The first and only mandatory rendering slice is the **sea-turtle rescue gameplay scene**.

This slice is the reference implementation for all later mission rendering.

### 5.2 Presentation model

- Fixed side-view diorama
- Submarine approaches the site
- Sea-otter leader exits or moves into the foreground for the rescue action
- Submarine remains visible as rear support
- Puffin and sea lion may participate through portrait callouts
- Turtle and obstacle remain visually dominant in the right half of the scene

### 5.3 Approximate composition

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

### 5.4 Rescue interaction retained for the visual slice

- Three large seaweed loops
- One active loop at a time
- Player drags the loop outward to release it
- Incorrect drag returns the current loop without penalty
- Repeated failure strengthens the directional hint
- Each successful release changes the turtle’s face and posture

This interaction exists only to validate the rendering and animation system. It must not trigger redesign of the wider mission rules during this phase.

---

## 6. Selected renderer architecture

### 6.1 Renderer decision

The rendering MVP will use **PixiJS v8**.

The current implementation baseline is **PixiJS 8.19.0**, which is the stable `latest` package version at this decision point. The dependency must be pinned exactly in the repository and bundled into the single HTML artifact; the deployed game must not depend on a runtime CDN.

### 6.2 Migration boundary

The renderer migration is strictly visual.

- Existing gameplay modules remain the authoritative source of mission state.
- Existing progression, pause, save, failure-isolation, and pointer contracts remain authoritative.
- PixiJS display objects must not become the canonical gameplay state.
- A bounded render adapter maps immutable or read-only game snapshots into PixiJS scene updates.
- Rendering code may emit normalized pointer intents but must not redefine success or failure rules.
- The current Canvas paint path is removed only after the corresponding PixiJS slice independently satisfies visual and input acceptance.

### 6.3 Application and context contract

- Use exactly one `PIXI.Application` for the game.
- Use one renderer and one graphics context.
- Do not create one PixiJS application or WebGL context per scene, portrait, character, or effect.
- Use one ticker or one explicitly controlled frame loop.
- Do not mix an independent Rive, Spine, or second WebGL renderer into this MVP.
- Prefer supported GPU renderers for the production slice; Canvas fallback is resilience, not the visual-quality reference path.

### 6.4 Scene graph contract

The scene must use named containers rather than a monolithic draw function.

Minimum root hierarchy:

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

PixiJS RenderGroups may be used strategically for major scene partitions such as `gameplayWorld` and `hud`. They must not be assigned to every small layer or sprite without profile evidence.

### 6.5 Asset loading contract

- Use PixiJS `Assets` as the single runtime asset registry and cache.
- Use aliases and a manifest or equivalent deterministic generated asset table.
- Decode and upload mandatory slice assets before the rescue scene becomes interactive.
- Repeated asset requests must reuse cached textures.
- Embedded data URLs, blobs, or generated bundle entries must preserve stable asset identity.
- Runtime loading from third-party URLs is prohibited in the final single-HTML build.

### 6.6 Input boundary

- Browser pointer coordinates are converted once into the existing logical 16:9 game coordinate system.
- Existing domain hit-test and gesture rules remain authoritative where already implemented.
- PixiJS event targets may identify the visual subject, but they must not silently introduce different hit geometry from the existing contract.
- Debug hit areas remain independently inspectable and must not ship as visible geometry.

---

## 7. Selected asset representation

### 7.1 Asset representation decision

The rendering MVP will use **build-time packed raster texture atlases generated from authored source files**.

- Source art may be SVG or sufficiently high-resolution raster files.
- Source art remains editable and is not loaded directly by the production runtime.
- The build converts source art into one or more raster atlas images plus deterministic metadata.
- PixiJS consumes the generated atlas through `Assets` and exposes named textures to `Sprite` objects.
- The production scene must not rasterize SVG at runtime.
- Primary subjects must not be recreated with PixiJS Graphics.

### 7.2 Atlas build contract

The atlas pipeline must:

- use deterministic frame names,
- preserve trim, source-size, and pivot/origin metadata,
- fail on duplicate frame identities,
- fail when a declared mandatory asset is absent,
- produce stable output for identical source bytes and configuration,
- record or verify source-to-output hashes,
- avoid runtime texture discovery by filename guessing,
- emit metadata accepted by the PixiJS spritesheet loader,
- support embedding atlas image bytes and metadata into the final single HTML artifact.

### 7.3 Cutout rig contract

The sea-otter rig uses named atlas frames rather than one flattened character sprite.

Minimum frame groups:

- head base,
- torso,
- near and far forelimbs,
- near and far hind limbs where visible,
- tail,
- eye states,
- mouth states,
- optional helmet or equipment overlay.

The runtime composes these frames with PixiJS Containers and Sprites. Animation changes transforms and selected facial textures; it does not mutate or regenerate texture pixels per frame.

### 7.4 Raster quality contract

- Atlas source resolution must be selected for the target logical display size and bounded DPR policy.
- Production must not upscale tiny source frames to fill large character regions.
- Texture filtering and mipmap policy must be explicit and device-tested.
- Transparent padding or extrusion must prevent atlas edge bleeding.
- Rotation during atlas packing is prohibited initially unless the generated metadata and visual regression tests prove it safe.
- Lossy WebP may be used only where alpha-edge and line-art inspection passes; PNG remains acceptable for line art and cutout parts.

### 7.5 Runtime texture contract

- Mandatory atlas bundles are loaded before the rescue slice becomes interactive.
- Texture aliases are semantic and stable, such as `otter/head/calm` or `turtle/face/worried`.
- Display objects reuse cached textures.
- Texture creation, decode, or upload must not occur inside the per-frame render path.
- Atlas metadata is generated, not hand-maintained after packing.
- Missing production textures fail closed during build or scene initialization rather than falling back to visible placeholder rectangles.

---

## 8. Required render layers

Minimum visual layers:

1. water gradient or far background,
2. distant silhouettes and light rays,
3. midground reef and fish,
4. submarine,
5. rescue target and obstacle,
6. active sea-otter cutout rig,
7. foreground coral and sand,
8. interaction hints and effects,
9. HUD and communication portrait.

Each layer must be independently replaceable without rewriting gameplay state transitions.

---

## 9. Required authored assets

Mandatory:

- sea-otter cutout parts,
- sea-turtle body and facial states,
- three seaweed-loop assets,
- one submarine side-view asset,
- coral-reef background layers,
- foreground coral and sand,
- communication portrait frame,
- basic bubble, glow, drag-arrow, and success-effect assets.

Procedural geometry remains acceptable only for:

- invisible hit areas,
- debug overlays,
- temporary development guides,
- simple particles whose geometric nature is not visually disruptive.

Primary characters, animals, vehicles, rocks, coral, and rescue obstacles must not ship as plain circles, rectangles, labels, or unstyled paths.

---

## 10. Minimum animation set

### 10.1 Sea-otter leader

- idle breathing,
- blink,
- attention or concern,
- reach toward active loop,
- pull or lean-back motion,
- success reaction.

### 10.2 Sea turtle

- worried idle,
- partial relief after loop one,
- greater relief after loop two,
- free and happy after loop three.

### 10.3 Submarine

- arrival drift,
- idle hover,
- support light or scanner activation.

### 10.4 Environment

- slow bubbles,
- subtle seaweed sway,
- restrained fish movement,
- light-ray drift or shimmer.

Environmental motion must remain slower and lower contrast than the active rescue action.

---

## 11. Visual readability requirements

At the target 16:9 viewport:

- the sea otter, turtle, submarine, and active loop remain recognizable at 25% screenshot scale,
- the active loop has the strongest local interaction contrast,
- the turtle’s face remains readable without zooming,
- the sea otter and turtle do not overlap the HUD,
- foreground decoration does not cover interaction targets,
- inactive decorative fish do not resemble targets,
- text panels are not the dominant visual mass.

The scene should look like a paused animation frame before it looks like a debugging canvas.

---

## 12. Device and rendering guardrails

### 12.1 Resolution

- Logical game coordinates remain fixed at 16:9.
- PixiJS resolution accounts for device pixel ratio under an explicit upper bound.
- Raster assets have sufficient source resolution for Galaxy Tab-class high-density screens.
- Asset scaling avoids repeated interpolation from undersized source images.
- Pixel-density policy must be validated separately rather than guessed inside the renderer migration.

### 12.2 Performance

Rendering quality work must preserve:

- responsive pointer tracking,
- stable animation cadence during drag,
- no allocation-heavy display-object recreation per frame,
- no repeated image decoding during gameplay,
- bounded particle counts,
- one renderer/context only,
- no filter or mask proliferation without device evidence.

Performance optimization must not be pursued by reverting primary subjects to placeholder geometry.

### 12.3 Packaging

- The final artifact remains one HTML file.
- PixiJS, atlas image bytes, and atlas metadata are embedded or bundled at build time.
- Source development remains modular.
- Asset identity and deterministic bundling are testable.
- The production artifact must make zero third-party runtime requests for renderer code or mandatory slice assets.

---

## 13. Explicit non-goals for the rendering MVP

- Rendering all three missions at final quality
- Full animation rigs for all three team members
- Full headquarters or launch-bay redesign
- New character selection flow
- New mission-selection UI
- 3D rendering
- Physics-based cloth, hair, or fluid simulation
- Cinematic camera system
- Dynamic lighting system
- Procedural character generation
- Rive, Spine, skeletal physics, or another animation runtime
- React-based PixiJS scene management
- Rewriting domain gameplay state around PixiJS objects
- Runtime SVG rasterization for production subjects
- Hand-authored atlas coordinates
- Dynamic runtime atlas packing

---

## 14. Rendering MVP acceptance criteria

The rendering MVP passes only when all of the following are true.

1. The sea-turtle rescue scene uses authored assets rather than placeholder shapes for all primary subjects.
2. The scene has distinct far, middle, gameplay, foreground, effect, and UI layers.
3. The sea-otter leader has idle, pull, and success animation states with facial changes.
4. The turtle visibly progresses from worried to relieved to free.
5. The submarine remains recognizable and visually belongs to the same palette and design family.
6. The active seaweed loop is immediately distinguishable from inactive scenery.
7. A first-time viewer can explain the rescue situation within three seconds without reading the instruction text.
8. Pointer input remains aligned with the visual target across the supported 16:9 scaling path.
9. The Galaxy Tab-class target runs the scene without obvious drag latency or sustained animation collapse.
10. Existing gameplay state, failure isolation, pause, progression, and save-data contracts are not broadened or redesigned.
11. The single-HTML build remains deterministic and reproducible.
12. Debug-only geometric placeholders are absent from the production scene.
13. PixiJS is bundled locally and no mandatory renderer or slice asset is fetched from a third-party CDN at runtime.
14. The application uses one PixiJS renderer/context.
15. Production primary subjects are loaded from generated raster atlases rather than runtime SVG or procedural Graphics.
16. Identical source asset bytes and atlas configuration produce identical generated atlas metadata and image bytes.
17. Missing or duplicate mandatory atlas frames fail closed before gameplay.
18. Cutout rig pivots remain stable after atlas trimming and packing.

---

## 15. Current technology evidence

- PixiJS v8 `Assets` provides cached, Promise-based asset loading with manifest bundles and built-in spritesheet support.
- PixiJS textures represent views into a shared texture source, allowing named subtextures from one atlas image to feed multiple Sprites.
- Spritesheets combine one atlas image with JSON frame metadata and improve the opportunity for shared-texture batching.
- PixiJS v8.19.0 added official agent skills inside the npm package and an opt-in HTML-source texture path; neither is required for this rendering slice.
- PixiJS v8.16 introduced an experimental Canvas renderer fallback for environments without WebGL or WebGPU.
- PixiJS v8.18–8.19 added renderer preference arrays and optional transient WebGPU MSAA attachments that can reduce mobile memory bandwidth.

These capabilities support the selected PixiJS plus build-time atlas architecture. They do not remove the need to validate atlas partitioning, DPR ceiling, atlas dimensions, compression, filter use, and Galaxy Tab performance as separate rendering failure domains.

---

## 16. Next unresolved rendering decision

The renderer and asset representation are closed as:

- **PixiJS v8**
- **build-time generated raster texture atlases from authored source files**

The next Grill-me question must choose only how the first vertical slice is partitioned into atlas bundles:

1. one monolithic atlas for the entire slice,
2. one atlas per individual subject,
3. a small number of lifecycle-based atlases,
4. no stable atlas partition and pack whatever fits.

No character, narrative, mission, UI-flow, or gameplay decision is part of this question.
