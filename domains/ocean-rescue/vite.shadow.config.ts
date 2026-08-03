import { createBundleLaneConfig } from "./vite.bundle";

// WP-20 historical shadow lane: deterministic IIFE bundle beside the legacy
// production path, emitted to dist/ocean-rescue-app.shadow.js. The manifest
// parsing, boundary validation, and bundling logic live in vite.bundle.ts and
// are shared with the WP-21 production lane.
export default createBundleLaneConfig({
  lane: "shadow",
  outFile: "ocean-rescue-app.shadow.js",
  htmlFile: "index.shadow.html",
  metadataFile: "shadow-bundle-metadata.json",
  globalName: "OceanRescueShadowBundle",
  metadataState: "SHADOW_BUNDLE",
  target: "baseline-widely-available",
});