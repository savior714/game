import * as THREE from "../vendor/three/three.module.min.js";
import { BIOMES, PARTICLE_LIMITS, REX_LAYER, SCENERY } from "./constants.js";
import { clamp, damp, randRange, randInt, pick } from "./util.js";
import { buildMergedGeometry, createHazardModel } from "./models.js";

export const SUN_DIRECTION = new THREE.Vector3(-0.78, 0.27, 0.56).normalize();

const SKY_RADIUS = 320;
const GROUND_LENGTH = 340;
const ROAD_LENGTH = 260;

const BIOME_TINT = {
  jungle: new THREE.Color(0xe3ffd6),
  desert: new THREE.Color(0xffe6c2),
  volcano: new THREE.Color(0xffab8a),
};

const AMBIENT_DRIFT = {
  jungle: { x: 0.08, y: 0.13, z: -0.22, opacity: 0.55 },
  desert: { x: 0.42, y: 0.02, z: -0.34, opacity: 0.34 },
  volcano: { x: 0.05, y: 0.46, z: 0.12, opacity: 0.5 },
};

const BIOME_TARGETS = BIOMES.map((biome) => ({
  id: biome.id,
  skyTop: new THREE.Color(biome.skyTop),
  skyHorizon: new THREE.Color(biome.skyHorizon),
  skyLow: new THREE.Color(biome.skyLow),
  skySun: new THREE.Color(biome.skySun),
  fog: new THREE.Color(biome.fog),
  ground: new THREE.Color(biome.ground),
  road: new THREE.Color(biome.road),
  roadEdge: new THREE.Color(biome.roadEdge),
  rock: new THREE.Color(biome.rock),
  cliff: new THREE.Color(biome.cliff),
  light: new THREE.Color(biome.light),
  hemiSky: new THREE.Color(biome.hemiSky),
  hemiGround: new THREE.Color(biome.hemiGround),
  fill: new THREE.Color(biome.fill),
  ambient: new THREE.Color(biome.ambient),
  pollen: new THREE.Color(biome.pollen),
  fogNear: biome.fogNear,
  fogFar: biome.fogFar,
  lightIntensity: biome.lightIntensity,
  hemiIntensity: biome.hemiIntensity,
  fillIntensity: biome.fillIntensity,
  ambientIntensity: biome.ambientIntensity,
  exposure: biome.exposure,
  tint: BIOME_TINT[biome.id].clone(),
}));

/* ------------------------------------------------------------------ */
/* Procedural textures                                                 */
/* ------------------------------------------------------------------ */

function makeCanvas(width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

function addNoise(ctx, width, height, amount) {
  const image = ctx.getImageData(0, 0, width, height);
  const data = image.data;
  for (let i = 0; i < data.length; i += 4) {
    const noise = (Math.random() * 2 - 1) * amount;
    data[i] = clamp(data[i] + noise, 0, 255);
    data[i + 1] = clamp(data[i + 1] + noise, 0, 255);
    data[i + 2] = clamp(data[i + 2] + noise, 0, 255);
  }
  ctx.putImageData(image, 0, 0);
}

function makeRoadTexture(renderer) {
  const width = 512;
  const height = 1024;
  const canvas = makeCanvas(width, height);
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#cfc7b9";
  ctx.fillRect(0, 0, width, height);
  addNoise(ctx, width, height, 26);

  // Wheel ruts running down the track.
  for (const x of [0.2, 0.34, 0.66, 0.8]) {
    const gradient = ctx.createLinearGradient(width * x - 20, 0, width * x + 20, 0);
    gradient.addColorStop(0, "rgba(70,55,38,0)");
    gradient.addColorStop(0.5, "rgba(70,55,38,0.22)");
    gradient.addColorStop(1, "rgba(70,55,38,0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(width * x - 22, 0, 44, height);
  }

  // Pebbles and dry patches.
  for (let i = 0; i < 900; i += 1) {
    const x = Math.random() * width;
    const y = Math.random() * height;
    const radius = randRange(0.6, 3.4);
    ctx.fillStyle = Math.random() > 0.45 ? "rgba(88,71,52,0.22)" : "rgba(245,232,205,0.18)";
    ctx.beginPath();
    ctx.ellipse(x, y, radius, radius * randRange(0.5, 1.2), Math.random() * Math.PI, 0, Math.PI * 2);
    ctx.fill();
  }

  // Cracks.
  ctx.strokeStyle = "rgba(60,46,34,0.25)";
  for (let i = 0; i < 26; i += 1) {
    ctx.lineWidth = randRange(0.6, 1.8);
    let x = Math.random() * width;
    let y = Math.random() * height;
    ctx.beginPath();
    ctx.moveTo(x, y);
    const steps = randInt(3, 8);
    for (let s = 0; s < steps; s += 1) {
      x += randRange(-28, 28);
      y += randRange(14, 46);
      ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  // Sparse glowing amber flecks baked into the dirt.
  for (let i = 0; i < 70; i += 1) {
    const x = Math.random() * width;
    const y = Math.random() * height;
    ctx.fillStyle = `rgba(255,183,64,${randRange(0.05, 0.16)})`;
    ctx.beginPath();
    ctx.arc(x, y, randRange(1, 3), 0, Math.PI * 2);
    ctx.fill();
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(1, 12);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  return texture;
}

function makeGroundTexture(renderer) {
  const size = 512;
  const canvas = makeCanvas(size, size);
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#c9c7b6";
  ctx.fillRect(0, 0, size, size);
  addNoise(ctx, size, size, 34);

  for (let i = 0; i < 460; i += 1) {
    const x = Math.random() * size;
    const y = Math.random() * size;
    const radius = randRange(3, 26);
    ctx.fillStyle =
      Math.random() > 0.5 ? `rgba(76,86,54,${randRange(0.06, 0.18)})` : `rgba(236,224,190,${randRange(0.05, 0.13)})`;
    ctx.beginPath();
    ctx.ellipse(x, y, radius, radius * randRange(0.45, 1), Math.random() * Math.PI, 0, Math.PI * 2);
    ctx.fill();
  }
  for (let i = 0; i < 450; i += 1) {
    ctx.strokeStyle = `rgba(60,72,38,${randRange(0.1, 0.3)})`;
    ctx.lineWidth = randRange(0.6, 1.6);
    const x = Math.random() * size;
    const y = Math.random() * size;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + randRange(-4, 4), y - randRange(3, 10));
    ctx.stroke();
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(34, 34);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  return texture;
}

function makeCrackTexture() {
  const width = 256;
  const height = 128;
  const canvas = makeCanvas(width, height);
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, width, height);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  const drawBranch = (points) => {
    ctx.beginPath();
    ctx.moveTo(points[0][0], points[0][1]);
    for (let i = 1; i < points.length; i += 1) {
      ctx.lineTo(points[i][0], points[i][1]);
    }
    ctx.stroke();
  };
  ctx.shadowColor = "rgba(255,80,10,0.95)";
  ctx.shadowBlur = 16;
  ctx.strokeStyle = "rgba(255,90,20,0.75)";
  ctx.lineWidth = 9;
  const main = [];
  for (let x = 0; x <= width; x += 20) {
    main.push([x, 64 + Math.sin(x * 0.12) * 12 + randRange(-10, 10)]);
  }
  drawBranch(main);
  for (let i = 0; i < 5; i += 1) {
    const start = pick(main);
    const branch = [start];
    let bx = start[0];
    let by = start[1];
    for (let s = 0; s < 4; s += 1) {
      bx += randRange(-24, 24);
      by += randRange(-22, 22);
      branch.push([bx, by]);
    }
    drawBranch(branch);
  }
  ctx.shadowBlur = 0;
  ctx.strokeStyle = "rgba(255,214,120,0.95)";
  ctx.lineWidth = 2.4;
  drawBranch(main);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

/* ------------------------------------------------------------------ */
/* Scenery geometry                                                    */
/* ------------------------------------------------------------------ */

function palmGeometry() {
  const parts = [];
  const trunkColors = [0x5b4630, 0x6a5138, 0x4c3b28];
  for (let i = 0; i < 4; i += 1) {
    parts.push({
      geometry: new THREE.CylinderGeometry(0.28 - i * 0.045, 0.32 - i * 0.04, 1.55, 7),
      color: trunkColors[i % 3],
      position: [Math.sin(i * 0.5) * 0.35, 0.78 + i * 1.45, 0],
      rotation: [0, 0, Math.sin(i * 0.7) * 0.07],
    });
  }
  const topX = Math.sin(1.5) * 0.35;
  for (let i = 0; i < 7; i += 1) {
    const angle = (i / 7) * Math.PI * 2;
    parts.push({
      geometry: new THREE.ConeGeometry(0.42, 3.2, 4),
      color: i % 2 === 0 ? 0x3e7c36 : 0x4d8f3d,
      position: [topX + Math.cos(angle) * 0.8, 6.15, Math.sin(angle) * 0.8],
      rotation: [0.9, angle, Math.cos(angle) * 0.35],
      scale: [1, 1, 0.35],
    });
  }
  parts.push({ geometry: new THREE.SphereGeometry(0.3, 7, 5), color: 0x6d7c35, position: [topX, 6.0, 0] });
  for (let i = 0; i < 3; i += 1) {
    parts.push({
      geometry: new THREE.SphereGeometry(0.17, 6, 4),
      color: 0x9b7836,
      position: [topX + Math.cos(i * 2.1) * 0.32, 5.78, Math.sin(i * 2.1) * 0.32],
    });
  }
  return buildMergedGeometry(parts);
}

function fernGeometry() {
  const parts = [];
  parts.push({ geometry: new THREE.CylinderGeometry(0.09, 0.16, 0.8, 5), color: 0x3f6b2f, position: [0, 0.4, 0] });
  for (let i = 0; i < 9; i += 1) {
    const angle = (i / 9) * Math.PI * 2;
    const length = 1.2 + (i % 3) * 0.35;
    parts.push({
      geometry: new THREE.ConeGeometry(0.26, length, 4),
      color: i % 2 === 0 ? 0x4e8e3c : 0x3a7332,
      position: [Math.cos(angle) * (0.5 + i * 0.035), 0.82 + (i % 3) * 0.09, Math.sin(angle) * (0.5 + i * 0.035)],
      rotation: [Math.sin(angle) * 0.9, 0, -Math.cos(angle) * 0.9],
      scale: [1, 1, 0.28],
    });
  }
  return buildMergedGeometry(parts);
}

function boulderGeometry() {
  return buildMergedGeometry([
    { geometry: new THREE.IcosahedronGeometry(1, 0), color: 0x7d8272, position: [0, 0.55, 0], rotation: [0.3, 0.2, 0.1], scale: [1.1, 0.8, 0.95] },
    { geometry: new THREE.IcosahedronGeometry(1, 0), color: 0x69705f, position: [0.9, 0.35, 0.4], rotation: [0.8, 0.4, 0.2], scale: [0.6, 0.5, 0.7] },
    { geometry: new THREE.IcosahedronGeometry(1, 0), color: 0x8d907c, position: [-0.8, 0.3, -0.3], rotation: [0.1, 0.9, 0.5], scale: [0.55, 0.45, 0.6] },
    { geometry: new THREE.IcosahedronGeometry(1, 0), color: 0x5e7050, position: [0.1, 1.0, -0.1], rotation: [0.6, 0.3, 0.2], scale: [0.4, 0.12, 0.34] },
  ]);
}

function spireGeometry() {
  return buildMergedGeometry([
    { geometry: new THREE.CylinderGeometry(0.25, 0.85, 4.8, 6), color: 0x9a7a5d, position: [0, 2.4, 0], rotation: [0.03, 0.2, 0.02] },
    { geometry: new THREE.CylinderGeometry(0.18, 0.55, 3.2, 5), color: 0x87705a, position: [-0.8, 1.7, 0.4], rotation: [0.1, 0.8, -0.14] },
    { geometry: new THREE.CylinderGeometry(0.12, 0.4, 2.4, 5), color: 0x6f5d4c, position: [0.8, 1.3, -0.3], rotation: [-0.08, 0.2, 0.18] },
    { geometry: new THREE.IcosahedronGeometry(0.7, 0), color: 0x7e6954, position: [0.1, 0.3, 0.3], scale: [1, 0.45, 1] },
  ]);
}

function boneGeometry() {
  const parts = [];
  const curve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-1.4, 0.15, -0.6),
    new THREE.Vector3(-0.9, 0.8, 0),
    new THREE.Vector3(0, 1.4, 0.25),
    new THREE.Vector3(0.9, 0.8, 0.1),
    new THREE.Vector3(1.3, 0.1, -0.4),
  ]);
  parts.push({ geometry: new THREE.TubeGeometry(curve, 14, 0.18, 6, false), color: 0xd8cbaa });
  for (let i = 0; i < 5; i += 1) {
    parts.push({
      geometry: new THREE.SphereGeometry(0.26 - i * 0.02, 7, 5),
      color: 0xc7b895,
      position: [-1 + i * 0.5, 0.3 + Math.sin((i / 4) * Math.PI) * 0.85, 0.12],
    });
  }
  parts.push({ geometry: new THREE.CylinderGeometry(0.16, 0.26, 1.2, 6), color: 0xd6c9a8, position: [1.25, 0.5, -0.35], rotation: [0.1, 0, 0.35] });
  return buildMergedGeometry(parts);
}

function crystalGeometry() {
  return buildMergedGeometry([
    { geometry: new THREE.OctahedronGeometry(0.65, 0), color: 0xffc247, position: [0, 0.95, 0], rotation: [0.1, 0.4, 0.15], scale: [0.7, 1.5, 0.7] },
    { geometry: new THREE.OctahedronGeometry(0.4, 0), color: 0xff9c2e, position: [0.5, 0.55, 0.2], rotation: [0.2, 0.2, -0.4], scale: [0.6, 1.2, 0.6] },
    { geometry: new THREE.OctahedronGeometry(0.32, 0), color: 0xffe08a, position: [-0.4, 0.45, -0.25], rotation: [0.4, 0.7, 0.2], scale: [0.55, 1.1, 0.55] },
    { geometry: new THREE.IcosahedronGeometry(0.8, 0), color: 0x5e5b4e, position: [0, 0.15, 0], scale: [1, 0.35, 1] },
  ]);
}

function cliffGeometry() {
  const parts = [];
  const colors = [0x777d70, 0x666d62, 0x848878];
  for (let i = 0; i < 4; i += 1) {
    const height = 9 + (i % 2) * 5;
    parts.push({
      geometry: new THREE.CylinderGeometry(1.3 + i * 0.2, 2.4 + i * 0.3, height, 6),
      color: colors[i % 3],
      position: [i * 1.7 - 2.2, height * 0.5 - 0.5, (i % 2) * 1.4 - 0.7],
      rotation: [0.02, i * 0.7, (i % 2 === 0 ? 1 : -1) * 0.035],
      scale: [1, 1, 0.8 + (i % 3) * 0.15],
    });
  }
  parts.push({ geometry: new THREE.IcosahedronGeometry(2, 0), color: 0x5c6358, position: [1.2, 0.5, 0], scale: [1.4, 0.6, 1.2] });
  parts.push({ geometry: new THREE.IcosahedronGeometry(1.4, 0), color: 0x6f7568, position: [-2.1, 0.35, 0.9], scale: [1, 0.5, 0.8] });
  return buildMergedGeometry(parts);
}

function mesaGeometry(variant) {
  const parts = [];
  const height = 35 + variant * 10;
  parts.push({
    geometry: new THREE.CylinderGeometry(12 + variant * 4, 22 + variant * 6, height, 7),
    color: [0x6b6252, 0x5d584c, 0x776c59][variant % 3],
    position: [0, height * 0.5, 0],
    rotation: [0, variant * 0.7, 0.02],
  });
  parts.push({
    geometry: new THREE.CylinderGeometry(9 + variant * 2, 12 + variant * 4, 5, 7),
    color: 0x837866,
    position: [0, height + 2, 0],
    rotation: [0, variant * 0.4, 0],
  });
  parts.push({
    geometry: new THREE.IcosahedronGeometry(8, 0),
    color: 0x565247,
    position: [18, 4, 6],
    scale: [1.4, 0.55, 1],
  });
  return buildMergedGeometry(parts);
}

function volcanoGeometry() {
  return buildMergedGeometry([
    { geometry: new THREE.CylinderGeometry(7, 38, 54, 9), color: 0x3a2a26, position: [0, 27, 0] },
    { geometry: new THREE.CylinderGeometry(9, 11, 5, 9), color: 0x2a1d1b, position: [0, 56, 0] },
    { geometry: new THREE.CylinderGeometry(5.4, 6.6, 2, 9), color: 0xff6428, position: [0, 57.5, 0] },
  ]);
}

/* ------------------------------------------------------------------ */
/* Wind shader hook                                                     */
/* ------------------------------------------------------------------ */

function applyWind(material, strength, windShaders) {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uWindTime = { value: 0 };
    shader.vertexShader = `uniform float uWindTime;\n${shader.vertexShader}`;
    shader.vertexShader = shader.vertexShader.replace(
      "#include <begin_vertex>",
      `#include <begin_vertex>
      #ifdef USE_INSTANCING
        vec3 instanceOrigin = instanceMatrix[3].xyz;
      #else
        vec3 instanceOrigin = vec3(0.0);
      #endif
      float bendAmount = max(0.0, position.y);
      float sway = sin(uWindTime * 1.15 + instanceOrigin.x * 0.31 + instanceOrigin.z * 0.17);
      float swayB = cos(uWindTime * 0.83 + instanceOrigin.z * 0.27 + instanceOrigin.x * 0.11);
      transformed.x += sway * bendAmount * ${strength.toFixed(4)};
      transformed.z += swayB * bendAmount * ${(strength * 0.62).toFixed(4)};`,
    );
    windShaders.push(shader);
  };
  material.customProgramCacheKey = () => `dino-wind-${strength.toFixed(4)}`;
  material.needsUpdate = true;
}

/* ------------------------------------------------------------------ */
/* World                                                               */
/* ------------------------------------------------------------------ */

export function createWorld(scene, renderer, options = {}) {
  const quality = options.quality === "low" ? "low" : "high";
  const windShaders = [];
  let targetBiome = BIOME_TARGETS[0];
  const scratchObject = new THREE.Object3D();
  const scratchColor = new THREE.Color();

  scene.fog = new THREE.Fog(BIOMES[0].fog, BIOMES[0].fogNear, BIOMES[0].fogFar);

  /* Sky ------------------------------------------------------------ */
  const skyUniforms = {
    uTop: { value: new THREE.Color(BIOMES[0].skyTop) },
    uHorizon: { value: new THREE.Color(BIOMES[0].skyHorizon) },
    uLow: { value: new THREE.Color(BIOMES[0].skyLow) },
    uSun: { value: new THREE.Color(BIOMES[0].skySun) },
    uSunDirection: { value: SUN_DIRECTION.clone() },
    uTime: { value: 0 },
  };
  const skyMaterial = new THREE.ShaderMaterial({
    uniforms: skyUniforms,
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    vertexShader: /* glsl */ `
      varying vec3 vDir;
      void main() {
        vDir = normalize(position);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uTop;
      uniform vec3 uHorizon;
      uniform vec3 uLow;
      uniform vec3 uSun;
      uniform vec3 uSunDirection;
      uniform float uTime;
      varying vec3 vDir;

      float hash(vec2 p) {
        return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
      }
      float noise(vec2 p) {
        vec2 i = floor(p);
        vec2 f = fract(p);
        vec2 u = f * f * (3.0 - 2.0 * f);
        return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
                   mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
      }

      void main() {
        vec3 dir = normalize(vDir);
        float h = dir.y;
        vec3 color = mix(uLow, uHorizon, smoothstep(-0.16, 0.12, h));
        color = mix(color, uTop, smoothstep(0.03, 0.62, h));

        float sunDot = max(dot(dir, normalize(uSunDirection)), 0.0);
        color += uSun * pow(sunDot, 340.0) * 2.2;
        color += uSun * pow(sunDot, 14.0) * 0.34;
        color += uSun * pow(sunDot, 2.5) * 0.07;

        float angle = atan(dir.z, dir.x);
        float band = (h - 0.03) / 0.55;
        float clouds = noise(vec2(angle * 3.1 + uTime * 0.006, band * 5.5));
        clouds += noise(vec2(angle * 7.4 - uTime * 0.004, band * 11.0)) * 0.5;
        clouds = smoothstep(0.72, 1.12, clouds) * smoothstep(0.02, 0.2, h) * (1.0 - smoothstep(0.45, 0.8, h));
        vec3 cloudTint = mix(uHorizon, uSun, 0.25) * 1.05;
        color = mix(color, cloudTint, clouds * 0.32);

        gl_FragColor = vec4(color, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  });
  const sky = new THREE.Mesh(new THREE.SphereGeometry(SKY_RADIUS, 32, 18), skyMaterial);
  sky.frustumCulled = false;
  sky.renderOrder = -10;
  sky.layers.enable(REX_LAYER);
  scene.add(sky);

  /* Lights --------------------------------------------------------- */
  const initial = BIOMES[0];
  const ambientLight = new THREE.AmbientLight(initial.ambient, initial.ambientIntensity);
  ambientLight.layers.enable(REX_LAYER);
  scene.add(ambientLight);

  const hemiLight = new THREE.HemisphereLight(initial.hemiSky, initial.hemiGround, initial.hemiIntensity);
  hemiLight.layers.enable(REX_LAYER);
  scene.add(hemiLight);

  const sun = new THREE.DirectionalLight(initial.light, initial.lightIntensity);
  sun.castShadow = true;
  sun.shadow.mapSize.set(quality === "low" ? 1024 : 2048, quality === "low" ? 1024 : 2048);
  sun.shadow.camera.left = -38;
  sun.shadow.camera.right = 38;
  sun.shadow.camera.top = 42;
  sun.shadow.camera.bottom = -38;
  sun.shadow.camera.near = 8;
  sun.shadow.camera.far = 170;
  sun.shadow.bias = -0.0006;
  sun.shadow.normalBias = 0.05;
  sun.layers.enable(REX_LAYER);
  scene.add(sun);
  scene.add(sun.target);

  const fill = new THREE.DirectionalLight(initial.fill, initial.fillIntensity);
  fill.layers.enable(REX_LAYER);
  scene.add(fill);
  scene.add(fill.target);

  const lavaLight = new THREE.PointLight(0xff5c24, 0, 42, 2);
  lavaLight.position.set(8, 1.6, 10);
  lavaLight.layers.enable(REX_LAYER);
  scene.add(lavaLight);

  /* Ground + road -------------------------------------------------- */
  const groundTexture = makeGroundTexture(renderer);
  const roadTexture = makeRoadTexture(renderer);
  const crackTexture = makeCrackTexture();

  const groundMaterial = new THREE.MeshStandardMaterial({
    color: initial.ground,
    map: groundTexture,
    roughness: 0.98,
    metalness: 0,
  });
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(340, GROUND_LENGTH), groundMaterial);
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  ground.position.set(0, 0, 70);
  ground.layers.enable(REX_LAYER);
  scene.add(ground);

  const roadMaterial = new THREE.MeshStandardMaterial({
    color: initial.road,
    map: roadTexture,
    roughness: 0.95,
    metalness: 0,
  });
  const road = new THREE.Mesh(new THREE.PlaneGeometry(9.4, ROAD_LENGTH), roadMaterial);
  road.rotation.x = -Math.PI / 2;
  road.receiveShadow = true;
  road.position.set(0, 0.025, 55);
  road.layers.enable(REX_LAYER);
  scene.add(road);

  const edgeMaterial = new THREE.MeshStandardMaterial({ color: initial.roadEdge, roughness: 1 });
  const edgeGeometry = new THREE.PlaneGeometry(0.42, ROAD_LENGTH);
  const edgeLeft = new THREE.Mesh(edgeGeometry, edgeMaterial);
  edgeLeft.rotation.x = -Math.PI / 2;
  edgeLeft.position.set(-4.68, 0.03, 55);
  edgeLeft.receiveShadow = true;
  edgeLeft.layers.enable(REX_LAYER);
  const edgeRight = edgeLeft.clone();
  edgeRight.position.x = 4.68;
  scene.add(edgeLeft, edgeRight);

  /* Scenery -------------------------------------------------------- */
  const sceneryMaterial = new THREE.MeshStandardMaterial({
    vertexColors: true,
    roughness: 0.93,
    metalness: 0,
    flatShading: true,
  });
  const foliageMaterial = new THREE.MeshStandardMaterial({
    vertexColors: true,
    roughness: 0.9,
    metalness: 0,
    flatShading: true,
  });
  applyWind(foliageMaterial, 0.05, windShaders);
  const trunkMaterial = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95, flatShading: true });
  applyWind(trunkMaterial, 0.028, windShaders);

  const crystalMaterial = new THREE.MeshStandardMaterial({
    vertexColors: true,
    color: 0xffffff,
    emissive: 0xff8a00,
    emissiveIntensity: 0.75,
    roughness: 0.32,
    metalness: 0.15,
    flatShading: true,
  });

  function createPropPool({ geometry, material, count, minX, maxX, minScale, maxScale, y = -0.08 }) {
    const mesh = new THREE.InstancedMesh(geometry, material, count);
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.frustumCulled = false;
    scene.add(mesh);
    const items = [];
    for (let i = 0; i < count; i += 1) {
      const side = Math.random() > 0.5 ? 1 : -1;
      const item = {
        x: side * randRange(minX, maxX),
        z: randRange(-30, 185),
        scale: randRange(minScale, maxScale),
        rotY: Math.random() * Math.PI * 2,
        y: y + randRange(-0.04, 0.04),
      };
      items.push(item);
      applyPropTransform(mesh, i, item, true);
    }
    mesh.instanceColor.needsUpdate = true;
    mesh.instanceMatrix.needsUpdate = true;
    return { mesh, items, count, minX, maxX, minScale, maxScale, y };
  }

  function applyPropTransform(mesh, index, item, initial = false) {
    scratchObject.position.set(item.x, item.y, item.z);
    scratchObject.rotation.set(0, item.rotY, 0);
    scratchObject.scale.set(item.scale, item.scale, item.scale);
    scratchObject.updateMatrix();
    mesh.setMatrixAt(index, scratchObject.matrix);
    if (initial) {
      scratchColor.copy(targetBiome.tint).offsetHSL(randRange(-0.03, 0.03), randRange(-0.1, 0.08), randRange(-0.09, 0.09));
      mesh.setColorAt(index, scratchColor);
    }
  }

  const palms = createPropPool({
    geometry: palmGeometry(),
    material: trunkMaterial,
    count: 28,
    minX: 7.5,
    maxX: 27,
    minScale: 0.72,
    maxScale: 1.45,
  });
  const ferns = createPropPool({
    geometry: fernGeometry(),
    material: foliageMaterial,
    count: 52,
    minX: 5.7,
    maxX: 19,
    minScale: 0.55,
    maxScale: 1.5,
  });
  const rocks = createPropPool({
    geometry: boulderGeometry(),
    material: sceneryMaterial,
    count: 34,
    minX: 5.6,
    maxX: 30,
    minScale: 0.55,
    maxScale: 2.1,
  });
  const spires = createPropPool({
    geometry: spireGeometry(),
    material: sceneryMaterial,
    count: 18,
    minX: 15,
    maxX: 46,
    minScale: 0.8,
    maxScale: 1.9,
    y: -0.3,
  });
  const bones = createPropPool({
    geometry: boneGeometry(),
    material: sceneryMaterial,
    count: 14,
    minX: 6.2,
    maxX: 21,
    minScale: 0.7,
    maxScale: 1.7,
  });
  const crystals = createPropPool({
    geometry: crystalGeometry(),
    material: crystalMaterial,
    count: 10,
    minX: 6.4,
    maxX: 16,
    minScale: 0.65,
    maxScale: 1.4,
  });
  const propPools = [palms, ferns, rocks, spires, bones, crystals];
  for (const pool of propPools) {
    pool.mesh.layers.enable(REX_LAYER);
  }

  const cliffs = (() => {
    const mesh = new THREE.InstancedMesh(cliffGeometry(), sceneryMaterial, SCENERY.cliffSegments);
    mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.frustumCulled = false;
    scene.add(mesh);
    const items = [];
    for (let i = 0; i < SCENERY.cliffSegments; i += 1) {
      const side = i % 2 === 0 ? 1 : -1;
      const item = {
        x: side * randRange(17, 38),
        z: randRange(-40, 200),
        scale: randRange(0.9, 2.1),
        rotY: Math.random() * Math.PI * 2,
        y: -Number(randRange(1.5, 4.5)),
      };
      items.push(item);
      scratchObject.position.set(item.x, item.y, item.z);
      scratchObject.rotation.set(0, item.rotY, 0);
      scratchObject.scale.set(item.scale * randRange(0.85, 1.25), item.scale, item.scale * randRange(0.8, 1.2));
      scratchObject.updateMatrix();
      mesh.setMatrixAt(i, scratchObject.matrix);
      scratchColor.copy(targetBiome.tint).multiplyScalar(randRange(0.72, 0.95));
      mesh.setColorAt(i, scratchColor);
    }
    mesh.instanceColor.needsUpdate = true;
    mesh.instanceMatrix.needsUpdate = true;
    mesh.layers.enable(REX_LAYER);
    return { mesh, items };
  })();

  /* Mountains + volcano + landmark ribs ---------------------------- */
  const mountainGroup = new THREE.Group();
  scene.add(mountainGroup);
  mountainGroup.traverse((object) => object.layers.enable(REX_LAYER));

  const mountainMaterial = new THREE.MeshStandardMaterial({
    vertexColors: true,
    color: 0x8b8577,
    roughness: 1,
    metalness: 0,
    flatShading: true,
  });
  const mesaGeometries = [mesaGeometry(0), mesaGeometry(1), mesaGeometry(2)];
  const mountainSlots = [
    [-58, 42, 1.1, 0],
    [48, 60, 1.3, 1],
    [-92, 78, 1.6, 2],
    [86, 95, 1.7, 0],
    [-26, 84, 1.2, 1],
    [110, 74, 1.5, 2],
    [-118, 55, 1.8, 0],
    [24, 105, 1.3, 2],
    [-72, 110, 1.9, 1],
  ];
  for (const [x, z, scale, variant] of mountainSlots) {
    const mountain = new THREE.Mesh(mesaGeometries[variant], mountainMaterial);
    mountain.position.set(x, -4, z);
    mountain.scale.set(scale, scale * randRange(0.8, 1.25), scale);
    mountain.rotation.y = Math.random() * Math.PI;
    mountain.castShadow = false;
    mountain.receiveShadow = false;
    mountainGroup.add(mountain);
  }

  const volcanoGroup = new THREE.Group();
  const volcanoMaterial = new THREE.MeshStandardMaterial({
    vertexColors: true,
    color: 0xffffff,
    roughness: 0.95,
    flatShading: true,
    transparent: true,
    opacity: 0,
  });
  const volcanoGeometryShared = volcanoGeometry();
  const volcanoLights = [];
  const craterMaterial = new THREE.MeshBasicMaterial({ color: 0xff8a3c, transparent: true, opacity: 0 });
  for (const [x, z, scale] of [
    [-58, 46, 1.1],
    [64, 66, 1.35],
  ]) {
    const cone = new THREE.Mesh(volcanoGeometryShared, volcanoMaterial);
    cone.position.set(x, -3, z);
    cone.scale.setScalar(scale);
    cone.rotation.y = Math.random() * Math.PI;
    volcanoGroup.add(cone);
    const crater = new THREE.Mesh(new THREE.CircleGeometry(5.2, 14), craterMaterial);
    crater.rotation.x = -Math.PI / 2;
    crater.position.set(x, 57.7 * scale - 3, z);
    volcanoGroup.add(crater);
    const glow = new THREE.PointLight(0xff5a24, 0, 130, 2);
    glow.position.set(x, 58 * scale, z);
    glow.layers.enable(REX_LAYER);
    volcanoGroup.add(glow);
    volcanoLights.push(glow);
  }
  volcanoGroup.traverse((object) => object.layers.enable(REX_LAYER));
  scene.add(volcanoGroup);

  const landmarkGroup = new THREE.Group();
  for (const [x, z, scale, rotation] of [
    [-27, 98, 2.7, 0.18],
    [31, 152, 2.2, -0.4],
  ]) {
    const rib = createHazardModel("ribs").root;
    rib.position.set(x, -0.2, z);
    rib.scale.setScalar(scale);
    rib.rotation.y = rotation;
    rib.traverse((child) => {
      if (child.isMesh) {
        child.castShadow = false;
        child.receiveShadow = false;
      }
    });
    landmarkGroup.add(rib);
  }
  scene.add(landmarkGroup);
  landmarkGroup.traverse((object) => object.layers.enable(REX_LAYER));

  // Distant wildlife silhouettes. They are deliberately smaller, higher and
  // tinted like the fog so they never read as a slide-under ptero hazard.
  const birds = [];
  const birdGroup = new THREE.Group();
  const birdMaterial = new THREE.MeshBasicMaterial({ color: 0x2c3a34, fog: true });
  for (let i = 0; i < 5; i += 1) {
    const bird = createHazardModel("ptero");
    bird.root.scale.setScalar(0.95 + (i % 2) * 0.18);
    bird.root.rotation.y = Math.PI;
    bird.root.traverse((child) => {
      if (child.isMesh) {
        child.castShadow = false;
        child.receiveShadow = false;
        child.material = birdMaterial;
        child.layers.enable(REX_LAYER);
      }
    });
    const holder = new THREE.Group();
    holder.add(bird.root);
    holder.position.set(-46 + i * 23, 31 + (i % 3) * 4, 130 + i * 12);
    birdGroup.add(holder);
    birds.push({
      bird,
      holder,
      phase: Math.random() * Math.PI * 2,
      radius: 16 + i * 6,
      speed: 0.08 + i * 0.022,
      baseY: 31 + (i % 3) * 4,
    });
  }
  scene.add(birdGroup);

  /* Lava cracks ---------------------------------------------------- */
  const lavaMaterial = new THREE.MeshBasicMaterial({
    map: crackTexture,
    transparent: true,
    opacity: 0,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  const lavaMesh = new THREE.InstancedMesh(new THREE.PlaneGeometry(5.2, 1.7), lavaMaterial, 16);
  lavaMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  lavaMesh.frustumCulled = false;
  lavaMesh.visible = false;
  lavaMesh.layers.enable(REX_LAYER);
  scene.add(lavaMesh);
  const lavaItems = [];
  for (let i = 0; i < 16; i += 1) {
    const item = {
      x: (Math.random() > 0.5 ? 1 : -1) * randRange(5.5, 18),
      z: randRange(-20, 170),
      scale: randRange(0.7, 1.9),
      rot: Math.random() * Math.PI * 2,
    };
    lavaItems.push(item);
    scratchObject.position.set(item.x, 0.04, item.z);
    scratchObject.rotation.set(-Math.PI / 2, 0, item.rot);
    scratchObject.scale.set(item.scale, item.scale, 1);
    scratchObject.updateMatrix();
    lavaMesh.setMatrixAt(i, scratchObject.matrix);
  }
  lavaMesh.instanceMatrix.needsUpdate = true;

  /* Ambient motes --------------------------------------------------- */
  const ambientCount = PARTICLE_LIMITS.ambient;
  const ambientPositions = new Float32Array(ambientCount * 3);
  const ambientSizes = new Float32Array(ambientCount);
  const ambientPhases = new Float32Array(ambientCount);
  const ambientParticles = [];
  for (let i = 0; i < ambientCount; i += 1) {
    const p = {
      x: randRange(-34, 34),
      y: randRange(0.3, 15),
      z: randRange(-35, 70),
      size: randRange(0.035, 0.13),
      phase: Math.random() * Math.PI * 2,
    };
    ambientParticles.push(p);
    ambientPositions[i * 3] = p.x;
    ambientPositions[i * 3 + 1] = p.y;
    ambientPositions[i * 3 + 2] = p.z;
    ambientSizes[i] = p.size;
    ambientPhases[i] = p.phase;
  }
  const ambientGeometry = new THREE.BufferGeometry();
  ambientGeometry.setAttribute("position", new THREE.BufferAttribute(ambientPositions, 3).setUsage(THREE.DynamicDrawUsage));
  ambientGeometry.setAttribute("aSize", new THREE.BufferAttribute(ambientSizes, 1));
  ambientGeometry.setAttribute("aPhase", new THREE.BufferAttribute(ambientPhases, 1));
  ambientGeometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1000000);
  const ambientUniforms = {
    uTime: { value: 0 },
    uColor: { value: new THREE.Color(BIOMES[0].pollen) },
    uOpacity: { value: 0.55 },
    uScale: { value: 500 },
  };
  const ambientMaterial = new THREE.ShaderMaterial({
    uniforms: ambientUniforms,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    vertexShader: /* glsl */ `
      attribute float aSize;
      attribute float aPhase;
      uniform float uScale;
      uniform float uTime;
      varying float vTwinkle;
      void main() {
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = clamp(aSize * uScale / max(1.0, -mv.z), 1.0, 26.0);
        gl_Position = projectionMatrix * mv;
        vTwinkle = 0.45 + 0.55 * pow(0.5 + 0.5 * sin(uTime * 1.5 + aPhase), 2.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uOpacity;
      varying float vTwinkle;
      void main() {
        vec2 p = gl_PointCoord - vec2(0.5);
        float d = length(p);
        if (d > 0.5) discard;
        float mask = smoothstep(0.5, 0.1, d);
        gl_FragColor = vec4(uColor, uOpacity * vTwinkle * mask);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
  });
  const ambientPoints = new THREE.Points(ambientGeometry, ambientMaterial);
  ambientPoints.frustumCulled = false;
  ambientPoints.renderOrder = 4;
  ambientPoints.layers.enable(REX_LAYER);
  scene.add(ambientPoints);

  /* Biome blending -------------------------------------------------- */
  let volcanoBlend = 0;
  const current = {
    skyTop: new THREE.Color(BIOMES[0].skyTop),
    skyHorizon: new THREE.Color(BIOMES[0].skyHorizon),
    skyLow: new THREE.Color(BIOMES[0].skyLow),
    skySun: new THREE.Color(BIOMES[0].skySun),
    fog: new THREE.Color(BIOMES[0].fog),
    ground: new THREE.Color(BIOMES[0].ground),
    road: new THREE.Color(BIOMES[0].road),
    roadEdge: new THREE.Color(BIOMES[0].roadEdge),
    rock: new THREE.Color(BIOMES[0].rock),
    cliff: new THREE.Color(BIOMES[0].cliff),
    light: new THREE.Color(BIOMES[0].light),
    hemiSky: new THREE.Color(BIOMES[0].hemiSky),
    hemiGround: new THREE.Color(BIOMES[0].hemiGround),
    fill: new THREE.Color(BIOMES[0].fill),
    ambient: new THREE.Color(BIOMES[0].ambient),
    pollen: new THREE.Color(BIOMES[0].pollen),
    fogNear: BIOMES[0].fogNear,
    fogFar: BIOMES[0].fogFar,
    lightIntensity: BIOMES[0].lightIntensity,
    hemiIntensity: BIOMES[0].hemiIntensity,
    fillIntensity: BIOMES[0].fillIntensity,
    ambientIntensity: BIOMES[0].ambientIntensity,
    exposure: BIOMES[0].exposure,
  };
  const pollenTarget = new THREE.Color(BIOMES[0].pollen);

  function snapBiome(index) {
    const target = BIOME_TARGETS[clamp(index, 0, BIOME_TARGETS.length - 1)];
    targetBiome = target;
    for (const key of Object.keys(current)) {
      if (current[key] instanceof THREE.Color) {
        current[key].copy(target[key]);
      } else {
        current[key] = target[key];
      }
    }
    ambientUniforms.uColor.value.copy(target.pollen);
    pollenTarget.copy(target.pollen);
    volcanoBlend = target.id === "volcano" ? 1 : 0;
    applyBiomeToScene();
  }

  function setBiome(index) {
    const clamped = clamp(index, 0, BIOME_TARGETS.length - 1);
    if (BIOME_TARGETS[clamped] === targetBiome) {
      return;
    }
    targetBiome = BIOME_TARGETS[clamped];
    pollenTarget.copy(targetBiome.pollen);
  }

  function dampColor(color, target, lambda, dt) {
    color.lerp(target, 1 - Math.exp(-lambda * dt));
  }

  function applyBiomeToScene() {
    scene.fog.color.copy(current.fog);
    scene.fog.near = current.fogNear;
    scene.fog.far = current.fogFar;
    skyUniforms.uTop.value.copy(current.skyTop);
    skyUniforms.uHorizon.value.copy(current.skyHorizon);
    skyUniforms.uLow.value.copy(current.skyLow);
    skyUniforms.uSun.value.copy(current.skySun);
    groundMaterial.color.copy(current.ground);
    roadMaterial.color.copy(current.road);
    edgeMaterial.color.copy(current.roadEdge);
    mountainMaterial.color.copy(current.cliff).lerp(current.fog, 0.38);
    ambientLight.color.copy(current.ambient);
    ambientLight.intensity = current.ambientIntensity;
    hemiLight.color.copy(current.hemiSky);
    hemiLight.groundColor.copy(current.hemiGround);
    hemiLight.intensity = current.hemiIntensity;
    sun.color.copy(current.light);
    sun.intensity = current.lightIntensity;
    fill.color.copy(current.fill);
    fill.intensity = current.fillIntensity;
    renderer.toneMappingExposure = current.exposure;
  }

  snapBiome(0);

  /* Rain of updates -------------------------------------------------- */
  let ambientDrift = { ...AMBIENT_DRIFT.jungle };

  function recycleProp(pool, index, playerZ) {
    const item = pool.items[index];
    const side = Math.random() > 0.5 ? 1 : -1;
    item.x = side * randRange(pool.minX, pool.maxX);
    item.z = playerZ + randRange(150, 196);
    item.scale = randRange(pool.minScale, pool.maxScale);
    item.rotY = Math.random() * Math.PI * 2;
    item.y = pool.y + randRange(-0.04, 0.04);
    applyPropTransform(pool.mesh, index, item);
    scratchColor
      .copy(targetBiome.tint)
      .offsetHSL(randRange(-0.03, 0.03), randRange(-0.1, 0.08), randRange(-0.09, 0.09));
    pool.mesh.setColorAt(index, scratchColor);
    pool.mesh.instanceColor.needsUpdate = true;
    pool.mesh.instanceMatrix.needsUpdate = true;
  }

  function recycleCliff(index, playerZ) {
    const item = cliffs.items[index];
    item.x = (Math.random() > 0.5 ? 1 : -1) * randRange(18, 42);
    item.z = playerZ + randRange(180, 230);
    item.scale = randRange(0.9, 2.2);
    item.rotY = Math.random() * Math.PI * 2;
    item.y = -Number(randRange(1.5, 5));
    scratchObject.position.set(item.x, item.y, item.z);
    scratchObject.rotation.set(0, item.rotY, 0);
    scratchObject.scale.set(item.scale * randRange(0.85, 1.25), item.scale, item.scale * randRange(0.8, 1.2));
    scratchObject.updateMatrix();
    cliffs.mesh.setMatrixAt(index, scratchObject.matrix);
    scratchColor.copy(targetBiome.tint).multiplyScalar(randRange(0.72, 0.95));
    cliffs.mesh.setColorAt(index, scratchColor);
    cliffs.mesh.instanceColor.needsUpdate = true;
    cliffs.mesh.instanceMatrix.needsUpdate = true;
  }

  function updateAmbient(dt, playerX, playerZ, time) {
    const drift = ambientDrift;
    for (let i = 0; i < ambientCount; i += 1) {
      const p = ambientParticles[i];
      p.x += (drift.x + Math.sin(time * 0.4 + p.phase) * 0.15) * dt;
      p.y += (drift.y + Math.sin(time * 0.9 + p.phase * 1.7) * 0.06) * dt;
      p.z += drift.z * dt;
      if (p.z < playerZ - 45) {
        p.z += 120;
      } else if (p.z > playerZ + 75) {
        p.z -= 120;
      }
      if (p.x < playerX - 36) {
        p.x += 72;
      } else if (p.x > playerX + 36) {
        p.x -= 72;
      }
      if (p.y > 17) {
        p.y = 0.25;
      } else if (p.y < 0.1) {
        p.y = 1.2;
      }
      ambientPositions[i * 3] = p.x;
      ambientPositions[i * 3 + 1] = p.y;
      ambientPositions[i * 3 + 2] = p.z;
    }
    ambientGeometry.attributes.position.needsUpdate = true;
    ambientUniforms.uTime.value = time;
  }

  /**
   * @param {number} dt
   * @param {{playerX:number, playerZ:number, time:number, camera:THREE.Camera, speed:number}} view
   */
  function update(dt, view) {
    if (!(dt > 0)) {
      return;
    }
    const step = Math.min(dt, 0.05);
    const { playerX, playerZ, time, camera } = view;

    // Biome blends.
    for (const key of Object.keys(current)) {
      if (current[key] instanceof THREE.Color) {
        dampColor(current[key], targetBiome[key], 0.9, step);
      } else {
        current[key] = damp(current[key], targetBiome[key], 0.8, step);
      }
    }
    volcanoBlend = damp(volcanoBlend, targetBiome.id === "volcano" ? 1 : 0, 1.1, step);
    dampColor(ambientUniforms.uColor.value, pollenTarget, 0.9, step);
    const driftTarget = AMBIENT_DRIFT[targetBiome.id];
    ambientDrift.x = damp(ambientDrift.x, driftTarget.x, 0.6, step);
    ambientDrift.y = damp(ambientDrift.y, driftTarget.y, 0.6, step);
    ambientDrift.z = damp(ambientDrift.z, driftTarget.z, 0.6, step);
    ambientUniforms.uOpacity.value = damp(
      ambientUniforms.uOpacity.value,
      driftTarget.opacity,
      0.6,
      step,
    );
    applyBiomeToScene();

    // Camera-following sky, world-following road.
    sky.position.set(camera.position.x, 0, camera.position.z);
    skyUniforms.uTime.value = time;
    skyUniforms.uSun.value.copy(current.skySun);

    ground.position.z = playerZ + 70;
    road.position.z = playerZ + 55;
    edgeLeft.position.z = playerZ + 55;
    edgeRight.position.z = playerZ + 55;
    roadTexture.offset.y = -((playerZ / (ROAD_LENGTH / 12)) % 1);
    groundTexture.offset.y = -((playerZ / (GROUND_LENGTH / 34)) % 1);

    // Lights and shadow frustum follow the runner.
    const targetX = Math.round(playerX / 2) * 2;
    const targetZ = Math.round((playerZ + 10) / 2) * 2;
    sun.target.position.set(targetX, 0, targetZ);
    sun.position.set(targetX + SUN_DIRECTION.x * 82, SUN_DIRECTION.y * 82, targetZ + SUN_DIRECTION.z * 82);
    fill.target.position.set(playerX, 1.6, playerZ - 4);
    fill.position.set(playerX + 26, 18, playerZ - 34);
    lavaLight.position.set(playerX + 8, 1.7, playerZ + 14);
    lavaLight.intensity = volcanoBlend * 9;

    // Recycle scenery that slipped behind the camera.
    for (const pool of propPools) {
      for (let i = 0; i < pool.count; i += 1) {
        if (pool.items[i].z < playerZ - 36) {
          recycleProp(pool, i, playerZ);
        }
      }
    }
    for (let i = 0; i < cliffs.items.length; i += 1) {
      if (cliffs.items[i].z < playerZ - 45) {
        recycleCliff(i, playerZ);
      }
    }

    // Landmarks remain in the distance.
    landmarkGroup.position.z = playerZ;
    mountainGroup.position.z = playerZ + 95;
    mountainGroup.rotation.y = 0;
    volcanoGroup.position.z = playerZ + 85;
    volcanoGroup.visible = volcanoBlend > 0.02;
    volcanoMaterial.opacity = volcanoBlend * 0.95;
    craterMaterial.opacity = volcanoBlend * 0.9;
    for (const light of volcanoLights) {
      light.intensity = volcanoBlend * 22;
    }

    // Lava cracks.
    lavaMesh.visible = volcanoBlend > 0.02;
    lavaMaterial.opacity = volcanoBlend * 0.9;
    for (let i = 0; i < lavaItems.length; i += 1) {
      if (lavaItems[i].z < playerZ - 30) {
        const item = lavaItems[i];
        item.x = (Math.random() > 0.5 ? 1 : -1) * randRange(5.5, 18);
        item.z = playerZ + randRange(130, 185);
        item.scale = randRange(0.7, 1.9);
        item.rot = Math.random() * Math.PI * 2;
        scratchObject.position.set(item.x, 0.04, item.z);
        scratchObject.rotation.set(-Math.PI / 2, 0, item.rot);
        scratchObject.scale.set(item.scale, item.scale, 1);
        scratchObject.updateMatrix();
        lavaMesh.setMatrixAt(i, scratchObject.matrix);
        lavaMesh.instanceMatrix.needsUpdate = true;
      }
    }

    // Birds circle far ahead.
    for (const entry of birds) {
      entry.phase += step * entry.speed;
      entry.holder.position.set(
        playerX + Math.cos(entry.phase) * entry.radius - 18,
        entry.baseY + Math.sin(entry.phase * 1.7) * 2.6,
        playerZ + 132 + Math.sin(entry.phase) * entry.radius,
      );
      entry.holder.rotation.y = entry.phase + Math.PI / 2;
      entry.bird.update(step, time, { speed: 12 });
    }

    // Foliage sway.
    for (const shader of windShaders) {
      if (shader.uniforms.uWindTime) {
        shader.uniforms.uWindTime.value = time;
      }
    }

    updateAmbient(step, playerX, playerZ, time);

    ambientUniforms.uTime.value = time;
    ambientUniforms.uScale.value = renderer.domElement.height * 0.5;
  }

  function setQuality(level) {
    const low = level === "low";
    sun.castShadow = !low;
    renderer.shadowMap.enabled = !low;
    for (const pool of [...propPools, cliffs]) {
      pool.mesh.castShadow = !low;
    }
    for (const pool of propPools) {
      pool.mesh.receiveShadow = !low;
    }
  }

  function setViewportSize(width, height, pixelRatio) {
    ambientUniforms.uScale.value = Math.max(200, height * 0.5 * Math.min(pixelRatio, 2));
  }

  function dispose() {
    scene.traverse((object) => {
      if (object.isMesh || object.isPoints) {
        object.geometry?.dispose?.();
        if (Array.isArray(object.material)) {
          object.material.forEach((material) => material.dispose?.());
        } else {
          object.material?.dispose?.();
        }
      }
    });
    [groundTexture, roadTexture, crackTexture].forEach((texture) => texture.dispose());
  }

  return {
    update,
    setBiome,
    setQuality,
    setViewportSize,
    dispose,
    sun,
    ambientPoints,
    getBiomeId: () => targetBiome.id,
  };
}
