# AidenGame Ocean Rescue — Rendering MVP

- **Version:** v0.1
- **Date:** 2026-07-31
- **Status:** Grill-me rendering scope partially closed
- **Parent product spec:** `AIDENGAME_OCEAN_RESCUE_MVP_PRD.md`
- **Scope:** visual rendering quality only
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

Replacing procedural placeholder shapes with authored 2D character, vehicle, creature, environment, and effect assets inside one fixed-side rescue scene—while preserving current gameplay state and input contracts—will make the product visually understandable and emotionally readable without requiring new missions, new progression, or a broader world-building pass.

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

- renderer architecture,
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

The following Grill-me decisions are accepted as art-direction constraints for the rendering MVP.

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

## 6. Required render layers

The scene must be represented as a scene graph or equivalent ordered layer model rather than one monolithic procedural paint function.

Minimum layers:

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

## 7. Required authored assets

The rendering MVP must use authored visual assets for the primary readable subjects.

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

## 8. Minimum animation set

### 8.1 Sea-otter leader

Required states:

- idle breathing,
- blink,
- attention or concern,
- reach toward active loop,
- pull or lean-back motion,
- success reaction.

### 8.2 Sea turtle

Required states:

- worried idle,
- partial relief after loop one,
- greater relief after loop two,
- free and happy after loop three.

### 8.3 Submarine

Required states:

- arrival drift,
- idle hover,
- support light or scanner activation.

### 8.4 Environment

Required motion:

- slow bubbles,
- subtle seaweed sway,
- restrained fish movement,
- light-ray drift or shimmer.

Environmental motion must remain slower and lower contrast than the active rescue action.

---

## 9. Visual readability requirements

At the target 16:9 viewport:

- the sea otter, turtle, submarine, and active loop must remain recognizable at 25% screenshot scale,
- the active loop must have the strongest local interaction contrast,
- the turtle’s face must remain readable without zooming,
- the sea otter and turtle must not overlap the HUD,
- foreground decoration must not cover interaction targets,
- inactive decorative fish must not resemble targets,
- text panels must not be the dominant visual mass.

The scene should look like a paused animation frame before it looks like a debugging canvas.

---

## 10. Device and rendering guardrails

### 10.1 Resolution

- Logical game coordinates remain fixed at 16:9.
- Drawing-surface resolution must account for device pixel ratio.
- Raster assets must have sufficient source resolution for Galaxy Tab-class high-density screens.
- Asset scaling must avoid repeated browser interpolation from very small source images.

### 10.2 Performance

Rendering quality work must preserve:

- responsive pointer tracking,
- stable animation cadence during drag,
- no allocation-heavy asset recreation per frame,
- no repeated image decoding during gameplay,
- bounded particle counts,
- no requirement for multiple independent WebGL contexts.

Performance optimization must not be pursued by reverting primary subjects to placeholder geometry.

### 10.3 Packaging

- The final artifact remains one HTML file.
- Runtime dependencies and assets may be embedded or bundled at build time.
- Source development may remain modular.
- Asset identity and deterministic bundling must be testable.

---

## 11. Explicit non-goals for the rendering MVP

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
- Mandatory adoption of PixiJS, Rive, Spine, or another engine before a renderer decision is explicitly closed

---

## 12. Rendering MVP acceptance criteria

The rendering MVP passes only when all of the following are true.

1. The sea-turtle rescue scene uses authored assets rather than placeholder shapes for all primary subjects.
2. The scene has distinct far, middle, gameplay, foreground, effect, and UI layers.
3. The sea-otter leader has idle, pull, and success animation states with facial changes.
4. The turtle visibly progresses from worried to relieved to free.
5. The submarine remains recognizable and visually belongs to the same palette and design family.
6. The active seaweed loop is immediately distinguishable from inactive scenery.
7. A first-time viewer can explain the rescue situation within three seconds without reading the instruction text.
8. Pointer input remains aligned with the visual target across the supported 16:9 scaling path.
9. The Galaxy Tab-class target can run the scene without obvious drag latency or sustained animation collapse.
10. Existing gameplay state, failure isolation, pause, progression, and save-data contracts are not broadened or redesigned by this work.
11. The single-HTML build remains deterministic and reproducible.
12. Debug-only geometric placeholders are absent from the production scene.

---

## 13. Current technology evidence

This section records current renderer facts but does not select a renderer.

- PixiJS v8.16 introduced an experimental Canvas renderer fallback for environments without WebGL or WebGPU.
- PixiJS June 2026 updates added renderer preference arrays and transient WebGPU MSAA attachments intended to reduce mobile memory bandwidth.
- Rive currently recommends its WebGL2 runtime for the highest rendering quality and performance, while also providing a smaller Canvas-based runtime for simpler graphics.
- Rive also warns that multiple visible WebGL instances can encounter browser context limits unless a shared offscreen renderer is used.

These changes make both a sprite-oriented PixiJS path and a limited Rive-character path technically viable, but neither is accepted until the renderer choice is independently decided.

---

## 14. Next unresolved rendering decision

The next Grill-me question must choose only the base renderer strategy for this single vertical slice.

Candidate strategies:

1. keep the current Canvas 2D runtime and replace procedural subjects with authored sprite assets plus a small internal scene graph,
2. preserve gameplay logic but migrate the visual layer to PixiJS v8,
3. use SVG/DOM cutout composition for the primary scene,
4. use Rive as the primary character and scene runtime.

No further character, narrative, mission, or world-building decision is required before this renderer decision is closed.
