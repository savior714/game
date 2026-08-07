# Asset identity

- Asset ID: `scene-seaweed-loop-02-01`
- Runtime alias: `scene.seaweed-loop.02`
- Target canonical path: `domains/ocean-rescue/assets/source/scene/seaweed-loop-02.svg`
- Atlas bundle: `scene`
- Source type: `svg`
- Palette version: `ocean-rescue-v1`
- Declared raster scale: `2`
- Pivot: `[0.5, 0.1]`
- Approval state: `planned`
- Authoring method: `frontier-svg-human-approved` (planned)
- Workflow state: `BRIEF_READY`

---

# Purpose

This asset is the second of three authored seaweed obstacles in the sea-turtle rescue slice of Ocean Rescue.
It must read instantly as a green seaweed loop that forms a closed obstacle around or interfering with the turtle rescue area.
The player must immediately recognize it as a member of the same draggable/releasable seaweed obstacle family as `scene.seaweed-loop.01` and sharing the exact same art direction, but as an independently authored second obstacle rather than repeated background scenery.
This asset defines visual geometry only and does not redesign the rescue mechanic or gameplay interaction rules.

---

# Actual display context

- Logical viewport: `1280 x 720`
- Intended logical asset size: `120 x 200`
- Source logical frame: `120 x 200` (exact viewBox `0 0 120 200`)
- Declared raster scale: `2`
- Root viewBox: `0 0 120 200`
- Atlas bundle: `scene`
- Expected pivot metadata after canonical registration: `[0.5, 0.1]`
- Camera / view: fixed side-view underwater diorama
- Placement: `turtleAndObstacle` container on the gameplay plane
  - Positioned and rotated dynamically by runtime according to canonical rope geometry (Rope 2 start `(750, 420)` to end `(1050, 440)`)
- Background context: midground reef, far deep water, foreground framing coral, and the sea turtle rescue subject
- Interaction: draggable obstacle ring; external motion, scaling, tinting, and rotation are applied externally by PixiJS runtime
- Static vector source: the SVG file itself must contain no runtime animation, SMIL, or script elements

---

# Visual-family reference

`scene.seaweed-loop.01` is an APPROVED STYLE/FAMILY REFERENCE ONLY.

DO preserve:
- Recognizable green seaweed material family consistent with palette `ocean-rescue-v1`
- Soft, rounded, child-friendly silhouette
- Clear open central opening for visual legibility
- Strong readability at actual gameplay size (`120 x 200` logical pixels)
- Simple vector construction suitable for deterministic build-time rasterization
- Sufficient contrast against the underwater scene background

DO NOT copy:
- Path geometry of `scene.seaweed-loop.01`
- Exact outer contour or node positions
- Exact internal strand layout or stem branching
- Mirrored geometry of loop 01
- Rotation-only or scale-only variants of loop 01

Loop 02 must not be loop 01 with different rotation, different scale, mirroring, path translation, recoloring, or superficial leaf/node relocation.

---

# Silhouette requirements

- Must feature a genuinely different outer silhouette while remaining strictly within the same obstacle family.
- Visibly different outer contour rhythm from loop 01 (e.g., distinct wave, bulb, or bulge distribution).
- Noticeable organic asymmetry.
- Different curvature and strand/node placement along the loop.
- Clear central opening so the enclosed area remains distinct.
- No visual ambiguity with coral props, rope lines, UI rings, or sea turtle anatomy.
- Do NOT prescribe individual SVG path coordinates; the frontier model owns visual geometry.

---

# Visual style

- Palette version: `ocean-rescue-v1`
- Transparent background (no opaque canvas fill)
- Friendly, non-threatening organic seaweed aesthetic suitable for a children's game
- Fills using approved green tones (e.g., `#2D8B46`, `#3AA85A`, `#4AB86A`, `#1A6B3A`)
- No photorealism or photo-bashed textures
- No text, letters, numbers, badges, logos, or watermarks
- No commercial franchise resemblance
- Restrained detail so the obstacle remains clean and readable at intended size

---

# Required structure

- Root element: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 200">`
- Root viewBox: `0 0 120 200`
- Transparent background
- Root semantic group ID: `scene-seaweed-loop-02`
- Deterministic local IDs prefixed with asset ID if `<defs>` or gradients are used
- Finite numeric coordinates and transforms
- Independently editable vector geometry
- Required movable parts: NONE (runtime motion and rotation are applied externally by PixiJS)

---

# Pivot expectations

- Planned canonical metadata pivot: `[0.5, 0.1]`
- Do not encode gameplay state or rotation offsets into SVG geometry.
- The SVG composition must remain compatible with this top-center loop placement contract.
- Runtime hit geometry and interaction thresholds are owned by gameplay modules and must not be altered by SVG geometry.

---

# Preserve

- Visual language and material family of approved `scene.seaweed-loop.01`
- Scene palette compatibility (`ocean-rescue-v1`)
- Closed-loop obstacle readability and clear central opening
- Clean, transparent vector source
- `120 x 200` composition contract and `0 0 120 200` viewBox
- Child-friendly rounded appearance

---

# Exclude

- Copying or tracing `scene.seaweed-loop.01` geometry
- Mirror, rotate, scale, or recolor variants of `scene.seaweed-loop.01`
- Procedural placeholder geometry or crude shapes
- SVG `<script>` elements or JavaScript code
- `<foreignObject>` elements
- External URLs or network resource references
- External `href` or `xlink:href` attributes
- Embedded raster images, PNGs, JPEGs, or base64 data URIs
- External fonts or external stylesheets
- Event handler attributes (`onload`, `onclick`, etc.)
- SMIL or runtime SVG animation elements
- Unsupported executable CSS
- Unresolved local `url(#id)` references
- Duplicate element IDs
- Invisible tracking or click layers
- Unbounded filter regions or heavy blur effects
- Commercial character, logo, or franchise imitation

---

# Binary acceptance criterion

At the intended in-game size, loop 02 is immediately recognizable as the same seaweed-obstacle family as loop 01 while having independently authored outer contour and internal strand/node geometry that cannot reasonably be described as a mirrored, rotated, scaled, recolored, or trivially edited copy of loop 01.

---

# Frontier-model delivery instruction

Create exactly one complete production SVG according to this asset brief.

The SVG file itself is the deliverable. Do not return a tutorial, poster, character sheet, contact sheet, or raster-only image.
One optional preview image may accompany the SVG file.

Preserve the required viewBox (`0 0 120 200`), root group ID (`scene-seaweed-loop-02`), and transparent background.
Do not use scripts, foreignObject, external URLs, external images, external fonts, embedded raster images, or runtime animation.

Optimize visual readability for the actual intended gameplay display size of `120 x 200` logical pixels in a 1280x720 side-view underwater scene.
