# Vendored three.js

The lab ships three.js in-tree so every 3D page (Space Explorer, Orbit & Eclipse,
Paint Mixing, Dino Escape, Power Island) runs without a CDN and without network
access.

- Package: `three@0.185.0` (MIT)
- Source: `https://registry.npmjs.org/three/-/three-0.185.0.tgz`
- WebGL entry: `build/three.module.min.js` (+ its relative chunk
  `build/three.core.min.js`) — mapped by the `"three"` import-map key
- WebGPU entry: `build/three.webgpu.min.js` (shares the same
  `three.core.min.js` chunk, so core classes stay identity-equal across both
  renderers). It exports `WebGPURenderer`, `PostProcessing`, the node-material
  classes and the `TSL` namespace. Loaded lazily through
  `webgpu/renderer-factory.js`, never on the WebGL fallback path.
- TSL entry: `build/three.tsl.min.js` — named re-exports of the `TSL`
  namespace; resolves the bare `three/webgpu` specifier via the import map.
  Pages without an import map use the relative `webgpu/tsl.js` shim instead.
- Addons:
  - `addons/controls/`, `addons/postprocessing/` — WebGL addons
    (OrbitControls + the EffectComposer passes used by the solar-system page)
  - `addons/tsl/display/BloomNode.js` — TSL/WebGPU bloom, used by the WebGPU
    post-processing chains (imports the bare `three/webgpu` / `three/tsl`
    specifiers, so it is only loaded on pages whose import map defines them)
- License: `LICENSE/THREE_LICENSE.txt`

Upgrade by replacing `build/` and `addons/` together; do not hand-edit the
minified files. The WebGL (`three.module.min.js`) and WebGPU
(`three.webgpu.min.js`) builds must stay on the same three.js release because
they share the `three.core.min.js` chunk.
