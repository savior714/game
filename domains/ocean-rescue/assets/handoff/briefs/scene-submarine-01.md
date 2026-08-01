# Asset identity

- Asset ID: `scene-submarine-01`
- Runtime alias: `scene.submarine`
- Target canonical path: `domains/ocean-rescue/assets/source/scene/submarine.svg`
- Atlas bundle: `scene`
- Source type: `svg`
- Palette version: `ocean-rescue-v1`
- Declared raster scale: `2`
- Pivot: `[0.5, 0.55]`
- Approval state: `approved` (per art-approval.json scope: ocean-rescue-rendering-mvp-proof-packet)
- Authoring method: `manual-vector`
- Workflow state: `BRIEF_READY`

---

# Purpose

This asset is the player's primary vehicle during the Travel phase of Ocean Rescue.
It must read instantly as a small, friendly, toy-like rescue submarine heading to the right.
A child player should understand without any text that this is a safe, cheerful ocean rescue vehicle
with a visible cockpit for the crew, a propulsion system at the rear, and rescue equipment on the hull.
The design belongs to the Ocean Rescue teal/orange/cream visual family and must feel consistent
with the sea otter rescue team's aesthetic.

---

# Actual display context

- Logical viewport: `1280 x 720`
- Source logical frame: `320 x 200` (exact viewBox)
- Runtime scale: `1.1 x 1.1`
- Approximate display footprint: `352 x 220` logical pixels (320 x 1.1 = 352 width, 200 x 1.1 = 220 height)
- Camera / view: fixed side-view, no camera movement or zoom
- Facing direction: right (nose cone and forward visual weight point toward positive X)
- Placement: left-side player vehicle during TravelScene; container `submarine` under `gameplayWorld`
  - Static base position: `(260, travelY)` where `travelY` is the vertical travel coordinate
  - Hover animation: `Math.sin(activeTime / 900) * 4` pixels vertical offset
  - Rotation: `Math.sin(activeTime / 1400) * 0.02` radians (negligible, near-vertical only)
- Background context: deep navy/teal water with pale caustic light bands, midground reef silhouettes,
  sand/rock corridor at the bottom, foreground coral framing the edges, and obstacle sprites
  (terrain props) scrolling past on the gameplay plane
- Occlusion: foreground coral and effects may partially overlap the rear/top of the submarine,
  but the nose, cockpit canopy, and propulsion silhouette must remain identifiable at all times
- Interaction: visual sprite only; gameplay hit geometry, collision detection, and state management
  are owned by TravelScene and Terrain modules, not by this asset's visual representation
- Collision feedback: a separate `fx.bubbles` flash sprite is positioned near `(260, gupY)` for
  collision visual feedback; this asset itself is not modified during collisions

---

# Silhouette requirements

- Rightward facing direction must be readable within 3 seconds at actual display size.
- A rounded main hull body must be clearly distinguishable from the forward nose cone.
- A transparent or lighter-colored cockpit canopy must visually separate from the hull body.
- The rear propulsion element must read as a functional propeller/thruster, not mere decoration.
- At least one rescue equipment indicator or support light must be visible as a non-interactive visual cue.
- The submarine must remain identifiable as a submarine when viewed at 25% screenshot scale.
- Avoid extremely thin protrusions or micro-details that disappear at the actual rendered size of approximately 352 x 220 logical pixels.
- The overall silhouette must feel friendly, approachable, and non-threatening for a child audience.

---

# Visual style

- Original television-animation-style 2D presentation
- Rounded, toy-like rescue vehicle aesthetic
- Clean vector fills with controlled outline hierarchy
- Primary palette: teal, orange, cream white
- Supporting palette: deep navy, coral red, pale sky blue
- Consistent lighting from upper-left or upper-front direction
- 2 to 3 simple material/depth layers (e.g., hull base, highlight band, canopy glass)
- No excessive gradients, no blur filters, no texture noise
- No imitation of any existing commercial character, vehicle, logo, or protected design

---

# Required structure

- Root element: `<svg xmlns="http://www.w3.org/2000/svg">`
- Root viewBox: `0 0 320 200` (exact, must not change)
- Transparent background (no full-canvas opaque fill)
- Deterministic local IDs with asset-specific prefixing
- Required root group: `scene-submarine`

Recommended semantic groups (required if the build pipeline supports group-level IDs;
if the current atlas toolchain cannot preserve group IDs through rasterization,
document this constraint in the revision request and treat geometry-level IDs as sufficient):

- `submarine-hull` — main hull body and nose cone
- `submarine-cockpit` — canopy/glass area with portholes
- `submarine-propulsion` — rear propeller/thruster assembly
- `submarine-rescue-gear` — rescue equipment, support lights, deck details
- `submarine-lights` — navigation lights and illumination elements

Required movable parts: none.
This asset is a single atlas frame. Group separation serves editability and validation only;
no runtime cutout animation contract is created by this brief.

Pivot expectations:

- The art-packet pivot `[0.5, 0.55]` must be preserved exactly.
- The visible silhouette must not appear to jump or shift unexpectedly when the runtime hover animation applies vertical offset relative to this pivot.
- Pivot adjustment is outside this task scope.

---

# Preserve

- Stable asset ID: `scene-submarine-01`
- Stable runtime alias: `scene.submarine`
- Canonical source path: `domains/ocean-rescue/assets/source/scene/submarine.svg`
- Atlas bundle membership: `scene`
- Exact viewBox and logical size: `0 0 320 200`, `320 x 200`
- Declared raster scale: `2`
- Current pivot: `[0.5, 0.55]`
- Right-facing direction
- Single-sprite runtime contract (one PIXI.Sprite instance, no cutout parts)
- TravelScene placement: container `submarine` under `gameplayWorld`, base position `(260, travelY)`, scale `1.1 x 1.1`
- TravelScene motion: small vertical hover and subtle rotation only
- Existing gameplay and collision geometry (unchanged)
- Transparent background
- Zero runtime external requests

---

# Exclude

- Text, letters, numbers, badges, logos, or watermarks
- Protected franchise resemblance (including but not limited to Octonauts, GUP vehicles, or similar children's rescue vehicle IP)
- Military weapons, aggressive spikes, gun-like silhouettes, or combat aesthetics
- Scary teeth, menacing eyes, creature-face vehicle designs, or threatening expressions
- Photorealism or photo-bashed textures
- Complex painted backgrounds (this is a vehicle, not an environment piece)
- External images, fonts, stylesheets, or network URLs
- Embedded raster data or base64 payloads
- SVG script elements, event handler attributes, foreignObject elements
- SMIL animation, CSS animation, or runtime-triggered animation
- Filter-heavy glow effects or unbounded filter regions
- Full-canvas opaque background
- Multiple vehicle variants in a single file (character sheets, pose sheets, mock-ups)
- Gameplay UI elements or environment/terrain assets
- Implementation code or build pipeline artifacts

---

# Binary acceptance criterion

When rendered in the 1280x720 TravelScene at approximately 352x220 logical pixels as a single sprite on the left side of the screen,
an observer who has not read this brief must identify the forward direction, cockpit canopy, rear propulsion system,
and rescue function within 3 seconds and describe the asset as a friendly ocean rescue submarine.

---

# Frontier-model delivery request

Create or revise exactly one production SVG according to the attached asset brief.

Return a complete `.svg` file, not a tutorial, mock-up, poster, character sheet,
or raster image.

Preserve the required viewBox (`0 0 320 200`), root group ID (`scene-submarine`),
transparent background, and right-facing direction.

Do not use scripts, foreignObject, external URLs, external images,
external fonts, embedded raster images, or runtime animation.

Optimize visual readability for the stated in-game logical size of approximately
352x220 pixels at 1.1x scale within a 1280x720 side-view underwater scene.
Do not imitate an existing protected character, vehicle, logo, badge, or frame composition.

Also provide one preview image, but treat the SVG file as the deliverable.
