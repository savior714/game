# Vendored three.js

The lab ships three.js in-tree so every 3D page (Space Explorer, Orbit & Eclipse,
Paint Mixing, Dino Escape) runs without a CDN and without network access.

- Package: `three@0.185.0` (MIT)
- Source: `https://registry.npmjs.org/three/-/three-0.185.0.tgz`
- Entry: `build/three.module.min.js` (+ its relative chunk `build/three.core.min.js`)
- Addons: `addons/` (OrbitControls + the post-processing passes used by the
  solar-system page)
- License: `LICENSE/THREE_LICENSE.txt`

Upgrade by replacing `build/` and `addons/` together; do not hand-edit the
minified files.
