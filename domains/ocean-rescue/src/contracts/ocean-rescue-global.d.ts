/**
 * Single global `window.OceanRescue` declaration for Ocean Rescue (WP-32A).
 *
 * The typed canonical modules register the temporary compatibility ABI slots
 * (`Profile`, `Launch`, `State`, `Travel`) and the ESM controller adapters
 * replace the legacy controller ABI slots (`Missions`, `Gups`). `src/app.js`
 * still consumes this temporary global. The property is optional because the
 * root object is created lazily by whichever module runs first.
 */
import type { OceanRescueNamespace } from "./runtime-abi";

declare global {
  interface Window {
    OceanRescue?: OceanRescueNamespace;
  }
}

export {};
