// three.js 렌더러 선택 팩토리.
//
// 원칙:
// - WebGPU를 지원하는 브라우저/기기에서만 WebGPURenderer를 쓰고, 어댑터 요청이나
//   초기화가 실패하면 동일 canvas로 WebGLRenderer에 자동 폴백한다.
// - WebGPU 어댑터 조회는 canvas에 webgpu context를 만들기 전에 일어나므로
//   (three 0.185 WebGPUBackend.init 순서: requestAdapter → requestDevice →
//   canvas.getContext("webgpu")), 초기 단계 실패는 canvas context를 오염시키지
//   않는다. 늦은 단계 실패로 canvas가 오염된 경우에만 canvas를 복제해 교체한다.
// - 정책/긴급 차단: `?webgpu=off` 쿼리 또는 localStorage
//   `aiden.webgpu.disabled = "1"`으로 WebGPU를 강제로 끌 수 있다.
// - 이 모듈은 최상위에서 DOM에 접근하지 않아 Node 하니스에서도 그대로 적재된다.

const WEBGPU_BUILD_URL = new URL(
  "../vendor/three/build/three.webgpu.min.js",
  import.meta.url,
);

export const BACKEND_WEBGL = "webgl";
export const BACKEND_WEBGPU = "webgpu";

let bundlePromise = null;

/** @returns {Promise<typeof import("../vendor/three/build/three.webgpu.min.js")>} */
export function loadWebGPUBundle() {
  if (!bundlePromise) {
    bundlePromise = import(WEBGPU_BUILD_URL);
  }
  return bundlePromise;
}

/**
 * 운영/정책 차단 스위치. 테스트나 긴급 대응으로 WebGPU를 강제 비활성화한다.
 * @returns {{disabled: boolean, reason: string|null}}
 */
export function webgpuPolicyState(globalRef = globalThis) {
  try {
    const loc = globalRef.location;
    if (loc && typeof loc.search === "string") {
      const params = new URLSearchParams(loc.search);
      const flag = params.get("webgpu");
      if (flag === "off" || flag === "0" || flag === "false") {
        return { disabled: true, reason: "url-flag" };
      }
    }
  } catch {
    /* location 없음(Node 등) — 계속 진행 */
  }
  try {
    const storage = globalRef.localStorage;
    if (storage && storage.getItem("aiden.webgpu.disabled") === "1") {
      return { disabled: true, reason: "local-storage-flag" };
    }
  } catch {
    /* 샌드박스 등에서 localStorage 접근 실패 — 무시 */
  }
  return { disabled: false, reason: null };
}

/**
 * @returns {Promise<boolean>} navigator.gpu 어댑터를 실제로 받아올 수 있는지
 */
export async function probeWebGPU(globalRef = globalThis) {
  const gpu = globalRef.navigator?.gpu;
  if (!gpu || typeof gpu.requestAdapter !== "function") return false;
  try {
    const adapter = await gpu.requestAdapter();
    return adapter !== null && adapter !== undefined;
  } catch {
    return false;
  }
}

function cloneCanvas(canvas) {
  const replacement = canvas.cloneNode(false);
  if (canvas.parentNode) {
    canvas.parentNode.insertBefore(replacement, canvas.nextSibling);
    canvas.remove();
  }
  return replacement;
}

/**
 * @param {object} webglThree — 기존 "three" 모듈 네임스페이스(WebGL 빌드)
 * @param {object} options
 * @param {HTMLCanvasElement} [options.canvas] 대상 canvas(없으면 렌더러가 생성)
 * @param {object} [options.parameters] 양쪽 렌더러에 전달할 공통 파라미터
 * @param {boolean} [options.preferWebGPU=true]
 * @param {typeof globalThis} [options.globalRef]
 * @returns {Promise<{renderer: object, backend: string, canvas: HTMLCanvasElement,
 *   three: object, tsl: object|null, fallbackReason: string|null}>}
 */
export async function createBestRenderer(
  webglThree,
  { canvas, parameters = {}, preferWebGPU = true, globalRef = globalThis } = {},
) {
  if (preferWebGPU) {
    const policy = webgpuPolicyState(globalRef);
    if (!policy.disabled && (await probeWebGPU(globalRef))) {
      try {
        const bundle = await loadWebGPUBundle();
        const renderer = new bundle.WebGPURenderer({ canvas, ...parameters });
        if (typeof renderer.init === "function") {
          await renderer.init();
        }
        return {
          renderer,
          backend: BACKEND_WEBGPU,
          canvas,
          three: bundle,
          tsl: bundle.TSL,
          fallbackReason: null,
        };
      } catch (error) {
        // 폴백 경로로 진행. canvas가 이미 webgpu context를 점유한 경우 복제한다.
        let nextCanvas = canvas;
        try {
          const stillUsable =
            canvas.getContext("webgl2") || canvas.getContext("webgl");
          if (!stillUsable) nextCanvas = cloneCanvas(canvas);
        } catch {
          nextCanvas = cloneCanvas(canvas);
        }
        const renderer = new webglThree.WebGLRenderer({
          canvas: nextCanvas,
          ...parameters,
        });
        return {
          renderer,
          backend: BACKEND_WEBGL,
          canvas: nextCanvas,
          three: webglThree,
          tsl: null,
          fallbackReason: `webgpu-init-failed: ${error?.message ?? "unknown"}`,
        };
      }
    }
  }

  const renderer = new webglThree.WebGLRenderer({ canvas, ...parameters });
  return {
    renderer,
    backend: BACKEND_WEBGL,
    canvas,
    three: webglThree,
    tsl: null,
    fallbackReason: preferWebGPU ? "webgpu-unavailable" : null,
  };
}
