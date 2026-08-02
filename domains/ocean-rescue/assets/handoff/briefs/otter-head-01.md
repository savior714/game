# Asset identity

- Task ID: `AIDENGAME-OCEAN-RESCUE-OTTER-HEAD-HANDOFF-STRUCTURE-GATE-01`
- Asset ID: `otter-head-01`
- Runtime alias: `otter.head`
- Target canonical path: `domains/ocean-rescue/assets/source/characters/otter-head.svg`
- Atlas bundle: `characters`
- Source type: `svg`
- Palette version: `ocean-rescue-v1`
- Declared raster scale: `2`
- Pivot: `[0.5, 0.55]`
- Approval state: `approved` (per art-approval.json scope: ocean-rescue-rendering-mvp-proof-packet)
- Authoring method: `manual-vector`
- Workflow state: `BRIEF_READY`

---

# Purpose

This asset is the **face base** of the sea otter rescue-team member in the Sea Turtle scene.
It must read instantly as the warm, round head of a friendly sea otter in the Ocean Rescue
teal/orange/cream visual family, with perky ears, a light muzzle, and a dark nose.
The face base carries no eyes and no mouth: the eyes and mouth are separate overlay sprites
assembled by the rig so the otter can blink and change expression without a second head asset.

---

# Actual display context

- Logical viewport: `1280 x 720`
- Source logical frame: `200 x 200` (exact viewBox)
- Runtime scale: `0.62 x 0.62`
- Approximate display footprint: `124 x 124` logical pixels (200 x 0.62 = 124 width and height)
- Camera / view: fixed side-view, no camera movement or zoom
- Facing direction: friendly forward-facing head; the rig orients the whole otter to the right
- Placement: container `seaOtterRig` under the authored scene graph
  - Rig base position: `(590, 420)`
  - Head sprite rig offset: `(0, -42)` on top of the torso (`(0, 22)`)
- Face overlay sprites (all scale `0.62 x 0.62`):
  - Eyes open / eyes closed overlay: rig offset `(0, -55)` (above the head base)
  - Mouth neutral / concern / smile overlay: rig offset `(0, -15)` (below the head base)
- Background context: deep navy/teal water, midground reef silhouettes, sand/rock corridor,
  foreground coral framing, and the rescue-submarine and turtle scene props nearby
- Occlusion: foreground coral and effects may slightly overlap the rig, but the head silhouette,
  ears, muzzle, and nose must remain identifiable at all times
- Interaction: visual sprite only; rig rotation/expression state is owned by the scene,
  not by this asset's visual representation

---

# Silhouette requirements

- Round otter head silhouette must read within 3 seconds at the actual display size of about 124 x 124 logical pixels.
- Two perky ear shells must be clearly visible on the top corners.
- A lighter muzzle and a dark nose must be visible and instantly readable as an otter's face.
- The head must remain identifiable as a sea otter head when viewed at 25% screenshot scale.
- Avoid extremely thin protrusions or micro-details that disappear at the actual rendered size.
- The silhouette must feel friendly, approachable, and non-threatening for a child audience.

---

# Visual style

- Original television-animation-style 2D presentation
- Rounded, toy-like friendly character aesthetic
- Clean vector fills with controlled outline hierarchy
- Primary palette: warm otter brown/tan fur, cream muzzle
- Supporting palette: teal scene accents, deep navy outlines, soft coral/pink blush
- Consistent lighting from upper-left or upper-front direction
- 2 to 3 simple material/depth layers (fur base, muzzle, subtle shading)
- No excessive gradients, no blur filters, no texture noise
- No imitation of any existing commercial character or protected design

---

# Facial base contract

This head sprite is the **face base only**. The eyes and mouth are separate overlay sprites
assembled by the rig; this asset must never bake them in.

- Fixed eyes: `none`
- Fixed mouth: `none`
- Fixed brows: `none`

Allowed fixed features on this asset: ears, head silhouette, cheeks, muzzle, nose, and whiskers.

---

# Required structure

- Root element: `<svg xmlns="http://www.w3.org/2000/svg">`
- Root viewBox: `0 0 200 200` (exact, must not change)
- Transparent background (no full-canvas opaque fill)
- Deterministic local IDs with asset-specific prefixing
- Required root group: `otter-head`

Required semantic groups:

- `otter-head-ears` — left/right ear shells and inner ears
- `otter-head-silhouette` — head silhouette, forehead shading, cheek shading
- `otter-head-muzzle` — muzzle cheeks, chin, nose, nose highlight
- `otter-head-details` — whiskers, cheek blush, forehead highlight

Required movable parts: none.
This asset is a single atlas frame. Group separation serves editability and validation only;
no runtime cutout animation contract is created by this brief.

Pivot expectations:

- The art-packet pivot `[0.5, 0.55]` must be preserved exactly.
- The visible head must not appear to jump or shift when the rig applies its head rotation
  (concern `0.035`, success `-0.025`) relative to this pivot.
- Pivot adjustment is outside this task scope.

---

# Preserve

- Stable asset ID: `otter-head-01`
- Stable runtime alias: `otter.head`
- Canonical source path: `domains/ocean-rescue/assets/source/characters/otter-head.svg`
- Atlas bundle membership: `characters`
- Exact viewBox and logical size: `0 0 200 200`, `200 x 200`
- Declared raster scale: `2`
- Current pivot: `[0.5, 0.55]`
- Face-base-only contract: no fixed eyes or mouth in the head SVG
- Face overlay aliases owned elsewhere: `otter.eyes.open`, `otter.eyes.closed`,
  `otter.mouth.neutral`, `otter.mouth.concern`, `otter.mouth.smile`
- Sea Turtle rig placement: `seaOtterRig` at `(590, 420)`, head offset `(0, -42)`, scale `0.62 x 0.62`
- Transparent background
- Zero runtime external requests

---

# Exclude

- Fixed eyes, eye whites, pupils, eyelids, or eyebrows baked into the head SVG
- Fixed mouth, lips, smile, concern, or frown geometry baked into the head SVG
- Text, letters, numbers, badges, logos, or watermarks
- Protected franchise resemblance (including but not limited to Octonauts or similar children's character IP)
- Scary teeth, menacing expressions, or threatening features
- Photorealism or photo-bashed textures
- External images, fonts, stylesheets, or network URLs
- Embedded raster data or base64 payloads
- SVG script elements, event handler attributes, foreignObject elements
- SMIL animation, CSS animation, or runtime-triggered animation
- Filter-heavy glow effects or unbounded filter regions
- Full-canvas opaque background
- Multiple head variants in a single file (pose sheets, mock-ups)
- Gameplay UI elements or environment/terrain assets
- Implementation code or build pipeline artifacts

---

# Binary acceptance criterion

When the head base is assembled in the Sea Turtle scene with the eye and mouth overlay sprites
at their rig offsets and the whole rig at approximately 124 x 124 logical pixels,
an observer who has not read this brief must identify the friendly sea otter head (ears, muzzle,
nose) and confirm that the blinking eyes and changing mouth read as separate live expressions,
never as a duplicate or smeared face.

---

# Frontier-model delivery request

Create or revise exactly one production SVG according to the attached asset brief.

Return a complete `.svg` file, not a tutorial, mock-up, poster, character sheet,
or raster image.

Preserve the required viewBox (`0 0 200 200`), root group ID (`otter-head`),
transparent background, and the face-base-only contract (no fixed eyes or mouth).

Do not use scripts, foreignObject, external URLs, external images,
external fonts, embedded raster images, or runtime animation.

Optimize visual readability for the stated in-game logical size of approximately
124 x 124 pixels at 0.62x scale within a 1280x720 side-view underwater scene.
Do not imitate an existing protected character or frame composition.

Also provide one preview image, but treat the SVG file as the deliverable.
