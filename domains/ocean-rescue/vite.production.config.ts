import { createBundleLaneConfig } from "./vite.bundle";

export default createBundleLaneConfig({
  lane: "production",
  outFile: "ocean-rescue-app.js",
  htmlFile: null,
  metadataFile: "production-bundle-metadata.json",
  globalName: "OceanRescueProductionBundle",
  entryName: "ocean-rescue-production-entry.mjs",
  metadataState: "PRODUCTION_BUNDLE",
  target: "baseline-widely-available",
});