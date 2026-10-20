/*!
 * AIDEN POWER ISLAND 3D — 3D 그래픽 품질 계약 프로브
 *
 * 브라우저 없이 `world.js` / `textures.js` 모듈 그래프를 적재해
 * 실제 씬 구성을 수치로 보고한다. 픽셀 비교 대신 "장면이 어떤 재질·지오메트리·
 * 후처리로 구성되었는가"를 검증해 시각 품질 회귀를 잡는다.
 */

import { register } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..");
const pageDir = path.join(root, "experiments", "electricity");
const vendorDir = path.join(root, "experiments", "space-explorer", "vendor", "three");

const loaderSource = `
export async function resolve(specifier, context, nextResolve) {
  if (specifier === "three") {
    return { shortCircuit: true, url: ${JSON.stringify(
      pathToFileURL(path.join(vendorDir, "build", "three.module.min.js")).href
    )} };
  }
  if (specifier.startsWith("three/addons/")) {
    const sub = specifier.slice("three/addons/".length);
    return { shortCircuit: true, url: ${JSON.stringify(
      pathToFileURL(path.join(vendorDir, "addons")).href + "/"
    )} + sub };
  }
  return nextResolve(specifier, context);
}
`;
register("data:text/javascript;charset=utf-8," + encodeURIComponent(loaderSource));

const { createPowerWorld, CAMERA_PRESETS } = await import(
  pathToFileURL(path.join(pageDir, "world.js")).href
);
const { createIslandTextures } = await import(
  pathToFileURL(path.join(pageDir, "textures.js")).href
);

/* ── 1. 텍스처 세트 ────────────────────────────────────────────── */

const textures = createIslandTextures();
const textureKeys = Object.keys(textures).filter((key) => key !== "dispose");
const textureReport = textureKeys.map((key) => {
  const tex = textures[key];
  return {
    key,
    isTexture: Boolean(tex && tex.isTexture),
    width: tex && tex.image ? tex.image.width : 0,
    hasDispose: Boolean(tex && typeof tex.dispose === "function"),
  };
});

/* ── 2. 씬 구성 ───────────────────────────────────────────────── */

const world = createPowerWorld({ headless: true });
const { scene, camera } = world;

const report = {
  textures: textureReport,
  meshes: 0,
  shaderMaterials: 0,
  physicalMaterials: 0,
  standardMaterials: 0,
  instancedMeshes: 0,
  sprites: 0,
  castShadowMeshes: 0,
  receiveShadowMeshes: 0,
  triangles: 0,
  multiMaterialMeshes: 0,
  normalMappedMaterials: 0,
  vertexColorMeshes: 0,
  walkwayMeshes: 0,
  multiMaterialGroups: [],
  islandTopY: null,
  fogType: scene.fog ? scene.fog.constructor.name : "",
  lights: { hemisphere: 0, directional: 0, point: 0 },
  cameras: CAMERA_PRESETS,
  cameraFar: camera.far,
  cameraFov: camera.fov,
};

const seenMaterials = new Set();
scene.traverse((obj) => {
  if (obj.isLight) {
    if (obj.isHemisphereLight) report.lights.hemisphere += 1;
    else if (obj.isDirectionalLight) report.lights.directional += 1;
    else if (obj.isPointLight) report.lights.point += 1;
  }
  if (obj.isSprite) report.sprites += 1;
  if (obj.isInstancedMesh) report.instancedMeshes += 1;
  if (!obj.isMesh || !obj.geometry) return;

  report.meshes += 1;
  if (obj.castShadow) report.castShadowMeshes += 1;
  if (obj.geometry.attributes.color) report.vertexColorMeshes += 1;
  if (obj.material && obj.material.polygonOffset && obj.material.map) report.walkwayMeshes += 1;
  if (obj.receiveShadow) report.receiveShadowMeshes += 1;

  const pos = obj.geometry.attributes.position;
  if (pos) {
    report.triangles += Math.round((obj.geometry.index ? obj.geometry.index.count : pos.count) / 3);
  }

  const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
  materials.forEach((mat) => {
    if (!mat || seenMaterials.has(mat.uuid)) return;
    seenMaterials.add(mat.uuid);
    if (mat.normalMap) report.normalMappedMaterials += 1;
    if (mat.isShaderMaterial) report.shaderMaterials += 1;
    else if (mat.isMeshPhysicalMaterial) report.physicalMaterials += 1;
    else if (mat.isMeshStandardMaterial) report.standardMaterials += 1;
  });

  if (Array.isArray(obj.material) && obj.geometry.groups.length >= 2) {
    report.multiMaterialMeshes += 1;
    if (!report.islandTopY) {
      obj.geometry.computeBoundingBox();
      report.islandTopY = Number(obj.geometry.boundingBox.max.y.toFixed(2));
      report.multiMaterialGroups = obj.geometry.groups.map((group) => group.materialIndex);
    }
  }
});

/* ── 3. 렌더 상태(날씨/전력) 없이도 스텝이 안전한지 ──────────────── */

const errors = [];
let stepped = 0;
try {
  const snapshot = {
    weather: "night",
    circuit: {
      closed: true,
      material: "copper",
      voltage: 4.5,
      output: { brightness: 1, conductive: true, transmission: 1 },
    },
    staticState: { charge: 50, worldX: 0.6, worldY: 3.8, worldZ: 0.6, bits: [], rubbing: 0 },
    fruit: { kind: "lemon", cells: 4, output: { level: 0.8, color: 0xffd24a } },
    generator: { angle: 1.1, rpm: 120, turns: 480, output: { level: 0.7, watts: 20 } },
    solar: { altitude: 55, tilt: 45, cloud: 15, output: { level: 0.8 } },
    wind: { blades: 3, bladeLength: 0.3, rpm: 110, windSpeed: 6, output: { level: 0.7, watts: 40 } },
    hydro: { head: 1.8, flow: 4.2, rpm: 90, output: { level: 0.8 } },
    grid: {
      gridRatio: 0.9,
      deliveredWatts: 130,
      rawWatts: 150,
      landmarks: { cottages: 1, harbor: 1, train: 1, ferris: 1, fountain: 1, festival: 1 },
    },
  };
  for (const weather of ["night", "dusk", "day", "storm"]) {
    for (let i = 0; i < 12; i += 1) {
      world.step(1 / 60, { ...snapshot, weather });
      stepped += 1;
    }
  }
} catch (error) {
  errors.push(`step: ${error.message}`);
}

textures.dispose();

console.log(
  JSON.stringify({
    errors,
    stepped,
    ...report,
  })
);
