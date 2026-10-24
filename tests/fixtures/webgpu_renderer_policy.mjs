import assert from "node:assert/strict";
import {
  BACKEND_WEBGL,
  createBestRenderer,
  webgpuPolicyState,
} from "../../experiments/space-explorer/webgpu/renderer-factory.js";

assert.deepEqual(webgpuPolicyState({}), {
  disabled: true,
  reason: "opt-in-required",
});
assert.deepEqual(webgpuPolicyState({ location: { search: "?webgpu=on" } }), {
  disabled: false,
  reason: null,
});
assert.deepEqual(webgpuPolicyState({ location: { search: "?webgpu=off" } }), {
  disabled: true,
  reason: "url-flag",
});
assert.deepEqual(webgpuPolicyState({
  location: { search: "?webgpu=on" },
  localStorage: { getItem: (key) => key === "aiden.webgpu.disabled" ? "1" : null },
}), {
  disabled: true,
  reason: "local-storage-flag",
});
assert.deepEqual(webgpuPolicyState({
  localStorage: { getItem: (key) => key === "aiden.webgpu.enabled" ? "1" : null },
}), {
  disabled: false,
  reason: null,
});

let webglRendererCreated = false;
const selected = await createBestRenderer({
  WebGLRenderer: class {
    constructor() {
      webglRendererCreated = true;
    }
  },
}, { globalRef: {} });
assert.equal(webglRendererCreated, true);
assert.equal(selected.backend, BACKEND_WEBGL);
assert.equal(selected.fallbackReason, "opt-in-required");

console.log("WebGPU renderer policy smoke test passed");
