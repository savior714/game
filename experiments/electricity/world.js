/*!
 * AIDEN POWER ISLAND 3D — 인터랙티브 3D 발전소 섬 & 밤마을 디오라마 엔진
 *
 * Three.js + EffectComposer(UnrealBloomPass)로 일곱 가지 발전 장치와
 * 여섯 단계로 깨어나는 밤섬 마을·기차·등대·분수·대관람차·불꽃놀이를 렌더링한다.
 */

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

import { createIslandTextures } from "./textures.js";

const TAU = Math.PI * 2;
const DEG = Math.PI / 180;

export const CAMERA_PRESETS = Object.freeze({
  overview: {
    label: "섬 전체보기",
    position: [10.0, 40.0, 78.0],
    target: [10.5, 4.0, -6.0],
  },
  generator: {
    label: "크랭크 발전 광장",
    position: [8.5, 15.0, 34.0],
    target: [-1.0, 4.6, 14.5],
  },
  wind: {
    label: "해안 풍력 절벽",
    position: [1.0, 20.0, 27.0],
    target: [-27.0, 12.0, 4.0],
  },
  solar: {
    label: "해바라기 태양광",
    position: [-6.0, 9.5, 24.0],
    target: [-14.5, 5.0, 15.5],
  },
  hydro: {
    label: "폭포 수력 댐",
    position: [-13.5, 15.5, 6.5],
    target: [-19.5, 7.2, -15.0],
  },
  circuit: {
    label: "중앙 변전소",
    position: [9.5, 14.0, 13.5],
    target: [-0.5, 7.2, -1.0],
  },
  static: {
    label: "정전기 부두",
    position: [22.5, 11.5, 30.0],
    target: [12.0, 5.6, 18.5],
  },
  fruit: {
    label: "과일 전지 덱",
    position: [35.0, 11.5, 24.0],
    target: [24.5, 4.6, 13.5],
  },
  village: {
    label: "네온 밤마을",
    position: [39.0, 23.0, 22.0],
    target: [20.0, 8.6, -10.0],
  },
});

/** 결정론적 난수 (같은 배치가 매번 재현되도록) */
function makeRng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

const rng = makeRng(20260120);

function randRange(min, max) {
  return min + rng() * (max - min);
}

const WORLD_ANCHORS = Object.freeze({
  generator: [-1, 8.2, 14.5],
  wind: [-27.5, 17.5, 4.5],
  solar: [-14.5, 7.6, 15.5],
  hydro: [-21, 13.5, -16],
  circuit: [-0.5, 11.5, -0.5],
  static: [12.5, 7.8, 18.5],
  fruit: [24.5, 7.6, 13.5],
  village: [22, 16.5, -14],
});

function easeInOutCubic(t) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

function sculptedIslandGeometry(radiusTop, radiusBottom, height, radialSegs, lobeAmp = 0.14) {
  const geo = new THREE.CylinderGeometry(radiusTop, radiusBottom, height, radialSegs, 3, false);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i += 1) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    const angle = Math.atan2(z, x);
    const radial = Math.hypot(x, z);
    if (radial > 0.001) {
      const wave =
        1 +
        lobeAmp * Math.sin(angle * 3 + 0.6) +
        lobeAmp * 0.55 * Math.cos(angle * 5 - 1.1) +
        0.04 * Math.sin(y * 0.7 + angle * 2);
      pos.setX(i, x * wave * 1.16);
      pos.setZ(i, z * wave * 0.94);
    }
  }
  geo.computeVertexNormals();
  return geo;
}

/**
 * 섬 본체 — 잔디 상판 / 모래 해변 띠 / 암벽 절벽을 하나의 지오메트리로 만들고
 * 머티리얼 그룹으로 나눈다. 레이어를 겹쳐 쌓지 않아 z-파이팅이나 각진 이음매가 없다.
 */
function makeIslandBodyGeometry({
  rows = 108,
  topY = 2.42,
  rimY = 1.94,
  baseY = -3.6,
  seed = 1,
  radius = 34.4 * 1.16,
  withBeach = true,
} = {}) {
  const R = radius;
  const wallRepeat = Math.max(18, Math.round(radius * 2.6));
  const rimRepeat = Math.max(18, Math.round(radius * 2.4));
  const shoreline = (a) =>
    1 + 0.12 * Math.sin(a * 3 + 0.6) + 0.066 * Math.cos(a * 5 - 1.1) + 0.028 * Math.sin(a * 7 + seed);
  const inner = (a) =>
    1 + 0.05 * Math.sin(a * 2 + 1.2) + 0.032 * Math.cos(a * 4 - 0.4) + 0.016 * Math.sin(a * 6 + seed);
  const lift = (a) => Math.sin(a * 3.1 + 0.7) * 0.07 + Math.cos(a * 5.3 + 1.9) * 0.05;

  // 위에서 아래로: 잔디 상판 → (모래 해변 띠) → 암벽 절벽
  // 풍력 절벽처럼 섬 안쪽에 솟은 대지는 모래 띠 없이 잔디 상판 + 암벽만 쓴다.
  const rings = withBeach
    ? [
        { y: topY, r: 0.0, vari: inner, mat: 0, uv: "top" },
        { y: topY, r: 0.58, vari: inner, mat: 0, uv: "top" },
        { y: topY, r: 0.9, vari: inner, mat: 0, uv: "top" },
        { y: topY + 0.04, r: 1.0, vari: inner, mat: 0, uv: "top" },
        { y: rimY + 0.2, r: 1.05, vari: shoreline, mat: 1, uv: "rim" },
        { y: rimY, r: 1.075, vari: shoreline, mat: 1, uv: "rim" },
        { y: rimY - 0.12, r: 1.07, vari: shoreline, mat: 2, uv: "wall" },
        { y: rimY - 1.05, r: 1.085, vari: shoreline, mat: 2, uv: "wall" },
        { y: baseY + 1.5, r: 1.13, vari: shoreline, mat: 2, uv: "wall" },
        { y: baseY, r: 1.17, vari: shoreline, mat: 2, uv: "wall" },
      ]
    : [
        { y: topY, r: 0.0, vari: inner, mat: 0, uv: "top" },
        { y: topY, r: 0.52, vari: inner, mat: 0, uv: "top" },
        { y: topY, r: 0.86, vari: inner, mat: 0, uv: "top" },
        { y: topY + 0.03, r: 0.97, vari: inner, mat: 0, uv: "top" },
        { y: topY - 0.1, r: 1.0, vari: shoreline, mat: 2, uv: "wall" },
        { y: topY - 1.1, r: 1.03, vari: shoreline, mat: 2, uv: "wall" },
        { y: baseY + 1.2, r: 1.1, vari: shoreline, mat: 2, uv: "wall" },
        { y: baseY, r: 1.16, vari: shoreline, mat: 2, uv: "wall" },
      ];

  const ringPoint = (ringDef, angle) => {
    const radius = R * ringDef.r * ringDef.vari(angle);
    const yBase = ringDef.y;
    const y =
      ringDef.uv === "top"
        ? yBase + lift(angle) * (ringDef.r > 0.9 ? 1 : 0.55)
        : yBase + Math.sin(angle * 4.4 + 0.3) * 0.035;
    return new THREE.Vector3(Math.cos(angle) * radius, y, Math.sin(angle) * radius * 0.955);
  };

  const positions = [];
  const uvs = [];
  const colors = [];
  const indices = [];
  const groups = [];
  const rowOffset = rows + 1;

  rings.forEach((ringDef) => {
    for (let i = 0; i <= rows; i += 1) {
      const angle = (i / rows) * TAU;
      const p = ringPoint(ringDef, angle);
      positions.push(p.x, p.y, p.z);
      // 잔디 상판에만 큰 스케일의 색 얼룩을 넣는다 — 균일한 초록 판 위에
      // 소품을 얹은 느낌을 없애고, 멀리서 봐도 지형이 살아 있게 만든다.
      if (ringDef.uv === "top") {
        const patch =
          Math.sin(angle * 3.3 + 1.1) * 0.5 +
          Math.cos(angle * 6.7 - 0.4) * 0.28 +
          Math.sin(ringDef.r * 9.4 + angle * 1.7) * 0.22;
        const edge = THREE.MathUtils.smoothstep(ringDef.r, 0.86, 1.0);
        const warm = 0.5 + patch * 0.5;
        colors.push(
          0.9 + patch * 0.1 + edge * 0.06,
          0.94 + warm * 0.12 - edge * 0.05,
          0.85 + (1 - warm) * 0.12 + edge * 0.02
        );
      } else {
        colors.push(1, 1, 1);
      }
      if (ringDef.uv === "top") {
        uvs.push(p.x / 7, p.z / 7);
      } else if (ringDef.uv === "rim") {
        uvs.push((i / rows) * rimRepeat, ringDef.r > 1.06 ? 1 : 0);
      } else {
        uvs.push((i / rows) * wallRepeat, (p.y - baseY) / Math.max(1.6, (topY - baseY) / 1.6));
      }
    }
  });

  let lastMat = -1;
  for (let ring = 0; ring < rings.length - 1; ring += 1) {
    const mat = rings[ring].mat;
    const start = indices.length;
    const rowA = ring * rowOffset;
    const rowB = (ring + 1) * rowOffset;
    for (let i = 0; i < rows; i += 1) {
      const a0 = rowA + i;
      const a1 = rowA + i + 1;
      const b0 = rowB + i;
      const b1 = rowB + i + 1;
      indices.push(a0, a1, b0, b0, a1, b1);
    }
    if (mat === lastMat && groups.length) {
      groups[groups.length - 1].count += indices.length - start;
    } else {
      groups.push({ start, count: indices.length - start, mat });
      lastMat = mat;
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geo.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  geo.setIndex(indices);

  // 감기 방향 보정: 상판 노멀이 위(+Y)를 향하도록 고정한다
  const probeA = new THREE.Vector3().fromArray(positions, 0);
  const probeB = new THREE.Vector3().fromArray(positions, 3);
  const probeC = new THREE.Vector3().fromArray(positions, 3 * rowOffset);
  const normal = new THREE.Vector3()
    .subVectors(probeB, probeA)
    .cross(new THREE.Vector3().subVectors(probeC, probeA));
  if (normal.y < 0) {
    for (let i = 0; i < indices.length; i += 3) {
      const tmp = indices[i + 1];
      indices[i + 1] = indices[i + 2];
      indices[i + 2] = tmp;
    }
    geo.setIndex(indices);
  }

  groups.forEach((g) => geo.addGroup(g.start, g.count, g.mat));
  geo.computeVertexNormals();
  return geo;
}

/**
 * 지면 디테일 주입기.
 * 타일 알베도의 반복 무늬 위에 월드 좌표 기준 fBm 얼룩을 곱해, 같은 텍스처가
 * 격자처럼 반복되는 느낌을 없애고 큰 스케일의 색 변화(마른 흙·이끼·그늘)를 얹는다.
 */
function attachWorldSurface(mat, {
  noise,
  scale = 0.055,
  strength = 0.26,
  warm = 0x9c8b52,
  cool = 0x2f5c46,
  sparkle = 0,
} = {}) {
  if (!mat || !noise) return mat;
  const uniforms = {
    uSurfNoise: { value: noise },
    uSurfScale: { value: scale },
    uSurfStrength: { value: strength },
    uSurfWarm: { value: new THREE.Color(warm) },
    uSurfCool: { value: new THREE.Color(cool) },
    uSurfSparkle: { value: sparkle },
  };
  mat.userData.surfaceUniforms = uniforms;
  const prevCompile = mat.onBeforeCompile;
  mat.onBeforeCompile = (shader, renderer) => {
    if (typeof prevCompile === "function") prevCompile(shader, renderer);
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        "#include <common>\nvarying vec3 vSurfWorld;"
      )
      .replace(
        "#include <begin_vertex>",
        "#include <begin_vertex>\nvSurfWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;"
      );
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
        uniform sampler2D uSurfNoise;
        uniform float uSurfScale;
        uniform float uSurfStrength;
        uniform vec3 uSurfWarm;
        uniform vec3 uSurfCool;
        uniform float uSurfSparkle;
        varying vec3 vSurfWorld;
        float surfFbm(vec2 p) {
          float a = texture2D(uSurfNoise, p).r;
          float b = texture2D(uSurfNoise, p * 2.13 + 0.37).r;
          float c = texture2D(uSurfNoise, p * 4.41 - 0.19).r;
          return a * 0.55 + b * 0.3 + c * 0.15;
        }`
      )
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
        vec2 surfUv = vSurfWorld.xz * uSurfScale;
        float surfMacro = surfFbm(surfUv);
        float surfMacro2 = surfFbm(surfUv * 0.37 + 0.61);
        vec3 surfTint = mix(uSurfCool, uSurfWarm, smoothstep(0.34, 0.72, surfMacro2));
        diffuseColor.rgb *= mix(vec3(1.0), surfTint * 1.32, uSurfStrength * smoothstep(0.28, 0.82, surfMacro));
        diffuseColor.rgb *= 0.84 + surfMacro * 0.32;
        if (uSurfSparkle > 0.001) {
          float spark = smoothstep(0.72, 0.95, texture2D(uSurfNoise, surfUv * 9.0).r);
          diffuseColor.rgb += spark * uSurfSparkle;
        }`
      );
  };
  mat.customProgramCacheKey = () => "surf-detail-v1";
  mat.needsUpdate = true;
  return mat;
}

/**
 * 볼륨 빛기둥 재질.
 * 예전에는 반투명 원뿔 메시라 실루엣이 종이 삼각형처럼 각져 보였다.
 * 지금은 시선 방향과 표면이 이루는 각으로 밀도를 계산해 가장자리를 부드럽게
 * 날리고, 광원 쪽은 진하고 먼 쪽은 옅어지며, 느린 노이즈로 공기 입자를 흉내 낸다.
 */
function makeBeamMaterial({
  color = 0xffe9b8,
  opacity = 0.2,
  noise = null,
  fade = 1.35,
  softness = 1.9,
  speed = 0.09,
} = {}) {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
    uniforms: {
      uColor: { value: new THREE.Color(color) },
      uOpacity: { value: opacity },
      uNoise: { value: noise },
      uTime: { value: 0 },
      uFade: { value: fade },
      uSoftness: { value: softness },
      uSpeed: { value: speed },
    },
    vertexShader: /* glsl */ `
      varying vec2 vUvBeam;
      varying vec3 vViewNormal;
      varying vec3 vViewPos;
      varying vec3 vBeamWorld;
      void main() {
        vUvBeam = uv;
        vec4 worldPos = modelMatrix * vec4(position, 1.0);
        vBeamWorld = worldPos.xyz;
        vec4 mvPosition = viewMatrix * worldPos;
        vViewPos = mvPosition.xyz;
        vViewNormal = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform vec3 uColor;
      uniform float uOpacity;
      uniform sampler2D uNoise;
      uniform float uTime;
      uniform float uFade;
      uniform float uSoftness;
      uniform float uSpeed;
      varying vec2 vUvBeam;
      varying vec3 vViewNormal;
      varying vec3 vViewPos;
      varying vec3 vBeamWorld;
      void main() {
        // 원뿔 옆면은 시선이 스칠수록 두껍게 보인다 → 페레넬로 밀도 계산
        vec3 viewDir = normalize(-vViewPos);
        float facing = abs(dot(normalize(vViewNormal), viewDir));
        float density = pow(1.0 - facing, uSoftness);
        // 광원(uv.y = 1)에서 멀어질수록 옅어진다
        float lengthFade = pow(clamp(vUvBeam.y, 0.0, 1.0), uFade);
        // 아주 옅은 공기 흐름
        float grain = 0.82 + 0.18 * texture2D(uNoise, vec2(vUvBeam.x * 1.4, vUvBeam.y * 0.7 - uTime * uSpeed)).r;
        float alpha = density * lengthFade * grain * uOpacity;
        if (alpha < 0.0015) discard;
        gl_FragColor = vec4(uColor * alpha, alpha);
      }
    `,
  });
}

function makeGlowSprite(glowMap, colorHex, scale, opacity = 0.85) {
  const mat = new THREE.SpriteMaterial({
    map: glowMap,
    color: colorHex,
    transparent: true,
    opacity,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(scale, scale, 1);
  return sprite;
}

/**
 * 박공지붕 — 용마루(ridge)가 긴 축을 따라가고, 짧은 축으로 물매가 떨어진다.
 * @param {number} widthAcross 용마루에 수직인 폭 (처마 간격)
 * @param {number} lengthAlong 용마루 방향 길이
 * @param {number} height 용마루 높이
 * @param {number} overhang 처마 여유
 */
function gableRoofGeometry(widthAcross, lengthAlong, height, overhang = 0.3) {
  const w = widthAcross * 0.5 + overhang;
  const l = lengthAlong * 0.5 + overhang;
  const positions = [];
  const uvs = [];
  const push = (a, b, c, ua, ub, uc) => {
    positions.push(...a, ...b, ...c);
    uvs.push(...ua, ...ub, ...uc);
  };
  // 앞 경사면 (+z) — 두 개의 삼각형
  push([-l, 0, w], [l, 0, w], [l, height, 0], [0, 0], [1, 0], [1, 1]);
  push([-l, 0, w], [l, height, 0], [-l, height, 0], [0, 0], [1, 1], [0, 1]);
  // 뒤 경사면 (-z)
  push([l, 0, -w], [-l, 0, -w], [-l, height, 0], [0, 0], [1, 0], [1, 1]);
  push([l, 0, -w], [-l, height, 0], [l, height, 0], [0, 0], [1, 1], [0, 1]);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geo.computeVertexNormals();
  return geo;
}

/** 지붕 양 끝을 막는 삼각 벽(박공벽) — 용마루 축에 수직으로 세운다 */
function gableEndGeometry(widthAcross, height, overhang = 0.3) {
  const half = widthAcross * 0.5 + overhang * 0.5;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute(
    "position",
    new THREE.Float32BufferAttribute([-half, 0, 0, half, 0, 0, 0, height, 0], 3)
  );
  geo.setAttribute("uv", new THREE.Float32BufferAttribute([0, 0, 1, 0, 0.5, 1], 2));
  geo.computeVertexNormals();
  return geo;
}

/** 침엽수 — 4단 가지를 살짝 비틀고 아래로 처지게 만들어 실루엣을 살린다 */
function makePineTree(scale = 1, tint = 0x1e6b4b) {
  const group = new THREE.Group();
  const trunkMat = new THREE.MeshStandardMaterial({ color: 0x5a3b25, roughness: 0.94 });
  const trunk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.14 * scale, 0.3 * scale, 1.9 * scale, 8),
    trunkMat
  );
  trunk.position.y = 0.95 * scale;
  trunk.castShadow = true;
  trunk.receiveShadow = true;
  group.add(trunk);

  const foliageMat = new THREE.MeshStandardMaterial({
    color: tint,
    roughness: 0.82,
    flatShading: true,
  });
  const tiers = 4;
  for (let tier = 0; tier < tiers; tier += 1) {
    const t = tier / (tiers - 1);
    const radius = (1.34 - t * 0.82) * scale;
    const h = (1.62 - t * 0.42) * scale;
    const cone = new THREE.Mesh(new THREE.ConeGeometry(radius, h, 9, 2), foliageMat);
    cone.position.set(
      Math.cos(tier * 2.1) * 0.06 * scale,
      (1.42 + tier * 0.78) * scale,
      Math.sin(tier * 2.1) * 0.06 * scale
    );
    cone.rotation.z = Math.cos(tier * 1.7) * 0.06;
    cone.rotation.y = tier * 0.7;
    cone.castShadow = true;
    cone.receiveShadow = true;
    group.add(cone);
  }
  group.rotation.y = randRange(0, TAU);
  return group;
}

/** 활엽수 — 둥근 잎 덩어리 3~5개를 겹쳐 부피감을 준다 */
function makeBroadleafTree(scale = 1, tint = 0x2f8f5b) {
  const group = new THREE.Group();
  const trunkMat = new THREE.MeshStandardMaterial({ color: 0x6b4a2f, roughness: 0.92 });
  const trunk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.16 * scale, 0.34 * scale, 2.4 * scale, 8),
    trunkMat
  );
  trunk.position.y = 1.2 * scale;
  trunk.castShadow = true;
  group.add(trunk);

  const foliageMat = new THREE.MeshStandardMaterial({
    color: tint,
    roughness: 0.84,
    flatShading: true,
  });
  const clumps = [
    [0, 2.9, 0, 1.35],
    [-0.85, 2.45, 0.4, 0.92],
    [0.9, 2.55, -0.3, 0.86],
    [0.15, 3.55, 0.25, 0.78],
  ];
  clumps.forEach(([x, y, z, r], i) => {
    const blobGeo = new THREE.IcosahedronGeometry(r * scale, 2);
    const blobPos = blobGeo.attributes.position;
    for (let v = 0; v < blobPos.count; v += 1) {
      const nx = blobPos.getX(v);
      const ny = blobPos.getY(v);
      const nz = blobPos.getZ(v);
      const wobble =
        1 + Math.sin(nx * 3.1 + i) * 0.06 + Math.cos(nz * 2.7 - i) * 0.05 + Math.sin(ny * 4.3) * 0.03;
      blobPos.setXYZ(v, nx * wobble, ny * wobble * 0.96, nz * wobble);
    }
    blobGeo.computeVertexNormals();
    const blob = new THREE.Mesh(blobGeo, foliageMat);
    blob.position.set(x * scale, y * scale, z * scale);
    blob.rotation.set(i * 0.7, i * 1.3, i * 0.4);
    blob.castShadow = true;
    blob.receiveShadow = true;
    group.add(blob);
  });
  group.rotation.y = randRange(0, TAU);
  return group;
}

/** 야자수 — 해변 부두 옆에 어울리는 곡선 줄기 + 잎 */
function makePalmTree(scale = 1) {
  const group = new THREE.Group();
  const trunkMat = new THREE.MeshStandardMaterial({ color: 0x8a6544, roughness: 0.9 });
  const segments = 6;
  let prev = new THREE.Vector3(0, 0, 0);
  for (let i = 1; i <= segments; i += 1) {
    const t = i / segments;
    const pos = new THREE.Vector3(Math.sin(t * 1.1) * 0.95 * scale, t * 4.6 * scale, 0);
    const mid = prev.clone().lerp(pos, 0.5);
    const len = prev.distanceTo(pos) * 1.08;
    const seg = new THREE.Mesh(
      new THREE.CylinderGeometry(
        (0.24 - t * 0.1) * scale,
        (0.3 - t * 0.1) * scale,
        len,
        7
      ),
      trunkMat
    );
    seg.position.copy(mid);
    seg.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), pos.clone().sub(prev).normalize());
    seg.castShadow = true;
    group.add(seg);
    prev = pos;
  }
  const leafMat = new THREE.MeshStandardMaterial({
    color: 0x35a86a,
    roughness: 0.78,
    side: THREE.DoubleSide,
    flatShading: true,
  });
  const crown = prev.clone();
  for (let f = 0; f < 7; f += 1) {
    const angle = (f / 7) * TAU;
    const frond = new THREE.Mesh(new THREE.ConeGeometry(0.36 * scale, 2.9 * scale, 4), leafMat);
    frond.position.set(
      crown.x + Math.cos(angle) * 1.05 * scale,
      crown.y + 0.1 * scale,
      crown.z + Math.sin(angle) * 1.05 * scale
    );
    frond.rotation.z = Math.PI / 2 - 0.42;
    frond.rotation.y = -angle;
    frond.scale.set(1, 1, 0.3);
    frond.castShadow = true;
    group.add(frond);
  }
  const coconutMat = new THREE.MeshStandardMaterial({ color: 0x5c4128, roughness: 0.9 });
  for (let c = 0; c < 3; c += 1) {
    const nut = new THREE.Mesh(new THREE.SphereGeometry(0.16 * scale, 8, 8), coconutMat);
    nut.position.set(
      crown.x + Math.cos((c / 3) * TAU) * 0.35 * scale,
      crown.y - 0.18 * scale,
      crown.z + Math.sin((c / 3) * TAU) * 0.35 * scale
    );
    group.add(nut);
  }
  group.rotation.y = randRange(0, TAU);
  return group;
}

/** 바위 — 비정형으로 눌러 자연스러운 실루엣을 만든다 */
function makeRock(scale, tint, rockMap) {
  const geo = new THREE.IcosahedronGeometry(1, 2);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i += 1) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    const n =
      1 +
      Math.sin(x * 3.1 + y * 2.2 + i * 0.6) * 0.12 +
      Math.cos(z * 2.7 - y * 1.9) * 0.1 +
      Math.sin(i * 4.7) * 0.05;
    pos.setXYZ(i, x * n, y * n * 0.78, z * n);
  }
  geo.computeVertexNormals();
  const mesh = new THREE.Mesh(
    geo,
    new THREE.MeshStandardMaterial({
      color: tint,
      map: rockMap || null,
      roughness: 0.94,
      flatShading: true,
    })
  );
  const s = scale;
  mesh.scale.set(s * randRange(0.9, 1.35), s * randRange(0.6, 1), s * randRange(0.9, 1.3));
  mesh.rotation.set(randRange(-0.3, 0.3), randRange(0, TAU), randRange(-0.3, 0.3));
  mesh.receiveShadow = true;
  return mesh;
}

export function createPowerWorld({
  canvas,
  headless = false,
  reducedMotion = false,
  onZoneSelect,
  onCrankDrag,
  onBalloonDrag,
  onSunDrag,
  onPanelDrag,
  onWindGust,
  onHydroToggle,
  onSwitchToggle,
  onFruitTap,
  onTeslaFire,
} = {}) {
  const textures = createIslandTextures();
  const scene = new THREE.Scene();

  const widthInitial = Math.max(320, canvas?.clientWidth || 1280);
  const heightInitial = Math.max(240, canvas?.clientHeight || 800);

  const camera = new THREE.PerspectiveCamera(44, widthInitial / heightInitial, 0.5, 900);
  camera.position.set(...CAMERA_PRESETS.overview.position);
  camera.lookAt(...CAMERA_PRESETS.overview.target);

  let renderer = null;
  let composer = null;
  let bloomPass = null;
  let gradePass = null;
  let controls = null;
  let pmrem = null;
  let envTarget = null;

  if (!headless && canvas) {
    let glProbe = null;
    try {
      glProbe =
        canvas.getContext("webgl2", { antialias: true, powerPreference: "high-performance" }) ||
        canvas.getContext("webgl", { antialias: true, powerPreference: "high-performance" });
    } catch {
      glProbe = null;
    }
    if (glProbe) {
      try {
        renderer = new THREE.WebGLRenderer({
          canvas,
          antialias: true,
          powerPreference: "high-performance",
        });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.6));
        renderer.setSize(widthInitial, heightInitial, false);
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        // AgX는 밝은 네온과 달빛을 흰 덩어리로 태우지 않고 필름처럼 굴려 준다
        renderer.toneMapping =
          THREE.AgXToneMapping !== undefined ? THREE.AgXToneMapping : THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.02;
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        // 비스듬히 내려다보는 지면/바다가 뭉개지거나 반짝이지 않도록 이방성 필터를 최대로
        try {
          const maxAniso = renderer.capabilities.getMaxAnisotropy();
          Object.values(textures).forEach((tex) => {
            if (tex && tex.isTexture) {
              tex.anisotropy = Math.min(8, maxAniso);
              tex.needsUpdate = true;
            }
          });
        } catch {
          /* 이방성 필터 미지원 환경은 기본값 유지 */
        }
        // 금속 재질이 검게 죽지 않도록 이미지 기반 조명(IBL)을 넣는다
        try {
          pmrem = new THREE.PMREMGenerator(renderer);
          pmrem.compileEquirectangularShader();
        } catch {
          pmrem = null;
        }

        composer = new EffectComposer(renderer);
        // 병합 후처리에서도 계단이 보이지 않도록 멀티샘플 렌더 타깃 사용
        try {
          composer.renderTarget1.samples = 4;
          composer.renderTarget2.samples = 4;
        } catch {
          /* WebGL1 등 samples 미지원 환경은 그대로 진행 */
        }
        const renderPass = new RenderPass(scene, camera);
        composer.addPass(renderPass);
        bloomPass = new UnrealBloomPass(
          new THREE.Vector2(widthInitial, heightInitial),
          reducedMotion ? 0.24 : 0.38,
          0.55,
          0.92
        );
        composer.addPass(bloomPass);

        // 디오라마 그레이딩 — 미니어처 사진처럼 가장자리를 살짝 풀고,
        // 어두운 곳은 차갑게 밝은 곳은 따뜻하게 나눈 뒤 미세하게 선명도를 올린다.
        gradePass = new ShaderPass({
          uniforms: {
            tDiffuse: { value: null },
            uVignette: { value: 0.44 },
            uGrain: { value: 0.022 },
            uSaturation: { value: 1.12 },
            uTime: { value: 0 },
            uTint: { value: new THREE.Color(0.94, 0.97, 1.06) },
            uSharpen: { value: 0.42 },
            uContrast: { value: 1.16 },
            uBlur: { value: 0.00042 },
            uFocus: { value: 0.52 },
            uAberration: { value: 0.0016 },
            uTexel: { value: new THREE.Vector2(1 / widthInitial, 1 / heightInitial) },
          },
          vertexShader: /* glsl */ `
            varying vec2 vUv;
            void main() {
              vUv = uv;
              gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
          `,
          fragmentShader: /* glsl */ `
            uniform sampler2D tDiffuse;
            uniform float uVignette;
            uniform float uGrain;
            uniform float uSaturation;
            uniform float uTime;
            uniform vec3 uTint;
            uniform float uSharpen;
            uniform float uContrast;
            uniform float uBlur;
            uniform float uFocus;
            uniform float uAberration;
            uniform vec2 uTexel;
            varying vec2 vUv;

            float hash(vec2 p) {
              return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
            }
            float lumaOf(vec3 c) {
              return dot(c, vec3(0.2126, 0.7152, 0.0722));
            }

            void main() {
              vec2 uv = vUv;
              vec2 centered = uv - 0.5;
              float r2 = dot(centered, centered);
              // 가장자리로 갈수록 색이 살짝 갈라지는 렌즈 느낌
              vec2 offset = centered * uAberration * r2;
              vec3 color;
              color.r = texture2D(tDiffuse, uv + offset).r;
              color.g = texture2D(tDiffuse, uv).g;
              color.b = texture2D(tDiffuse, uv - offset).b;

              // 틸트시프트: 화면 중앙 띠는 선명하게, 위아래는 부드럽게 풀어 미니어처 느낌
              float band = smoothstep(0.3, 1.0, abs(uv.y - uFocus));
              if (band > 0.001) {
                vec2 step1 = uTexel * 2.0;
                vec2 step2 = uTexel * 4.5;
                vec2 step3 = uTexel * 8.0;
                vec3 blur = color * 0.04;
                blur += texture2D(tDiffuse, uv + vec2(step1.x, 0.0)).rgb * 0.12;
                blur += texture2D(tDiffuse, uv - vec2(step1.x, 0.0)).rgb * 0.12;
                blur += texture2D(tDiffuse, uv + vec2(0.0, step1.y)).rgb * 0.12;
                blur += texture2D(tDiffuse, uv - vec2(0.0, step1.y)).rgb * 0.12;
                blur += texture2D(tDiffuse, uv + vec2(step2.x, step2.y)).rgb * 0.08;
                blur += texture2D(tDiffuse, uv - vec2(step2.x, step2.y)).rgb * 0.08;
                blur += texture2D(tDiffuse, uv + vec2(-step2.x, step2.y)).rgb * 0.08;
                blur += texture2D(tDiffuse, uv + vec2(step2.x, -step2.y)).rgb * 0.08;
                blur += texture2D(tDiffuse, uv + vec2(step3.x, 0.0)).rgb * 0.04;
                blur += texture2D(tDiffuse, uv - vec2(step3.x, 0.0)).rgb * 0.04;
                blur += texture2D(tDiffuse, uv + vec2(0.0, step3.y)).rgb * 0.04;
                blur += texture2D(tDiffuse, uv - vec2(0.0, step3.y)).rgb * 0.04;
                color = mix(color, blur, clamp(band * uBlur * 300.0, 0.0, 0.8));
              }

              // 언샤프 마스크: 블룸으로 번진 경계를 다시 조여 준다
              vec3 sharpBase = color;
              vec3 neighbours =
                texture2D(tDiffuse, uv + vec2(uTexel.x * 1.5, 0.0)).rgb +
                texture2D(tDiffuse, uv - vec2(uTexel.x * 1.5, 0.0)).rgb +
                texture2D(tDiffuse, uv + vec2(0.0, uTexel.y * 1.5)).rgb +
                texture2D(tDiffuse, uv - vec2(0.0, uTexel.y * 1.5)).rgb;
              color = max(color + (sharpBase * 4.0 - neighbours) * uSharpen * 0.25, 0.0);

              // 대비 — 밝은 곳과 어두운 곳을 벌려 뿌옇게 뜬 느낌을 걷어낸다
              color = max((color - 0.2) * uContrast + 0.2, 0.0);

              float luma = lumaOf(color);
              // 스플릿 톤 — 그림자는 밤하늘 쪽으로, 하이라이트는 따뜻하게
              vec3 shadowTint = vec3(0.93, 0.98, 1.09);
              vec3 highTint = vec3(1.05, 1.0, 0.94);
              color *= mix(shadowTint, highTint, smoothstep(0.08, 0.85, luma));
              color = mix(vec3(lumaOf(color)), color, uSaturation);
              color *= uTint;

              float vignette = 1.0 - smoothstep(0.3, 0.92, length(centered) * 1.24);
              color *= mix(1.0, vignette, uVignette);

              float grain = hash(uv * vec2(1920.0, 1080.0) + uTime * 41.0) - 0.5;
              color += grain * uGrain * (0.12 + (1.0 - luma) * 0.5);
              gl_FragColor = vec4(max(color, 0.0), 1.0);
            }
          `,
        });
        composer.addPass(gradePass);
        composer.addPass(new OutputPass());
      } catch {
        renderer = null;
        composer = null;
        pmrem = null;
      }
    }
  }

  /* ── 0. 날씨에 반응하는 환경 조명(IBL) ──────────────────────── */

  const envUniforms = {
    uTop: { value: new THREE.Color(0x0b1d3d) },
    uHorizon: { value: new THREE.Color(0x2a5a94) },
    uGround: { value: new THREE.Color(0x081423) },
    uSunDir: { value: new THREE.Vector3(-0.4, 0.55, 0.7).normalize() },
    uSunColor: { value: new THREE.Color(0xfff0d0) },
    uSunPower: { value: 0.85 },
  };

  const envScene = new THREE.Scene();
  const envDome = new THREE.Mesh(
    new THREE.SphereGeometry(60, 20, 12),
    new THREE.ShaderMaterial({
      side: THREE.BackSide,
      depthWrite: false,
      uniforms: envUniforms,
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
        uniform vec3 uGround;
        uniform vec3 uSunDir;
        uniform vec3 uSunColor;
        uniform float uSunPower;
        varying vec3 vDir;
        void main() {
          vec3 dir = normalize(vDir);
          float h = dir.y;
          vec3 sky = mix(uHorizon, uTop, pow(clamp(h, 0.0, 1.0), 0.55));
          vec3 ground = mix(uHorizon * 0.55, uGround, clamp(-h * 2.2, 0.0, 1.0));
          vec3 color = mix(ground, sky, smoothstep(-0.08, 0.05, h));
          float sun = pow(max(dot(dir, normalize(uSunDir)), 0.0), 22.0);
          color += uSunColor * sun * uSunPower;
          float horizonGlow = exp(-abs(h) * 5.5);
          color += uHorizon * horizonGlow * 0.35;
          gl_FragColor = vec4(color, 1.0);
        }
      `,
    })
  );
  envDome.frustumCulled = false;
  envScene.add(envDome);

  let envWeatherKey = "";

  function updateEnvironmentLighting(topColor, horizonColor, groundColor, sunDir, sunColor) {
    if (!renderer || !pmrem) return;
    envUniforms.uTop.value.copy(topColor);
    envUniforms.uHorizon.value.copy(horizonColor);
    envUniforms.uGround.value.copy(groundColor);
    envUniforms.uSunDir.value.copy(sunDir).normalize();
    envUniforms.uSunColor.value.copy(sunColor);
    try {
      const next = pmrem.fromScene(envScene, 0.02, 0.1, 200);
      if (envTarget && envTarget !== next) envTarget.dispose();
      envTarget = next;
      scene.environment = next.texture;
      if ("environmentIntensity" in scene) scene.environmentIntensity = 0.72;
    } catch {
      /* IBL 생성 실패 시 기존 조명으로 계속 진행 */
    }
  }


  if (canvas && typeof window !== "undefined") {
    controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.065;
    controls.rotateSpeed = 0.68;
    controls.zoomSpeed = 0.82;
    controls.panSpeed = 0.65;
    controls.minDistance = 11;
    controls.maxDistance = 96;
    controls.maxPolarAngle = 82 * DEG;
    controls.minPolarAngle = 14 * DEG;
    controls.target.set(...CAMERA_PRESETS.overview.target);
    controls.update();
  }

  /* ── 1. 하늘 돔 · 별빛 · 달 · 구름 · 태양 ─────────────────────── */

  scene.fog = new THREE.FogExp2(0x0a1a33, 0.0042);

  // 대기 산란을 흉내 낸 그라디언트 스카이 셰이더 (지평선 발광 + 태양 헤일로)
  const skyUniforms = {
    uTop: { value: new THREE.Color(0x040b1d) },
    uHorizon: { value: new THREE.Color(0x14294c) },
    uGlow: { value: new THREE.Color(0x2b6fa8) },
    uFog: { value: new THREE.Color(0x0a1a33) },
    uSunDir: { value: new THREE.Vector3(-0.35, 0.42, 0.84).normalize() },
    uSunColor: { value: new THREE.Color(0xffe9b8) },
    uMoonDir: { value: new THREE.Vector3(50, 88, -82).normalize() },
    uMoonColor: { value: new THREE.Color(0xbcd4ff) },
    uMoon: { value: 1 },
    uSunPower: { value: 240 },
    uSunStrength: { value: 0.55 },
    uMilky: { value: 1 },
    uCloud: { value: 0.4 },
    uTime: { value: 0 },
  };

  const skyGeo = new THREE.SphereGeometry(400, 48, 32);
  const skyMat = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
    uniforms: skyUniforms,
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
      uniform vec3 uGlow;
      uniform vec3 uFog;
      uniform vec3 uSunDir;
      uniform vec3 uSunColor;
      uniform vec3 uMoonDir;
      uniform vec3 uMoonColor;
      uniform float uMoon;
      uniform float uSunPower;
      uniform float uSunStrength;
      uniform float uMilky;
      uniform float uCloud;
      uniform float uTime;
      varying vec3 vDir;

      float hash21(vec2 p) {
        p = fract(p * vec2(123.34, 456.21));
        p += dot(p, p + 45.32);
        return fract(p.x * p.y);
      }
      float valueNoise(vec2 p) {
        vec2 i = floor(p);
        vec2 f = fract(p);
        f = f * f * (3.0 - 2.0 * f);
        float a = hash21(i);
        float b = hash21(i + vec2(1.0, 0.0));
        float c = hash21(i + vec2(0.0, 1.0));
        float d = hash21(i + vec2(1.0, 1.0));
        return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
      }
      float fbm(vec2 p) {
        float value = 0.0;
        float amplitude = 0.5;
        for (int i = 0; i < 4; i += 1) {
          value += amplitude * valueNoise(p);
          p *= 2.03;
          amplitude *= 0.5;
        }
        return value;
      }

      void main() {
        vec3 dir = normalize(vDir);
        float h = dir.y;
        float up = clamp(h, 0.0, 1.0);

        // 3단 그라디언트: 지평선 헤이즈 → 중간 하늘 → 천정
        vec3 color = mix(uHorizon, uTop, pow(up, 0.55));
        color = mix(color, mix(uHorizon, uGlow, 0.35), exp(-up * 5.0) * 0.55);

        // 태양/달 주변의 큰 헤일로와 지평선 발광
        vec3 sunDir = normalize(uSunDir);
        float sunDot = max(dot(dir, sunDir), 0.0);
        color += uSunColor * pow(sunDot, max(6.0, uSunPower * 0.06)) * uSunStrength * 0.22;
        color += uSunColor * pow(sunDot, uSunPower) * uSunStrength * 2.4;

        vec3 moonDir = normalize(uMoonDir);
        float moonDot = max(dot(dir, moonDir), 0.0);
        color += uMoonColor * (pow(moonDot, 26.0) * 0.16 + pow(moonDot, 900.0) * 0.7) * uMoon;

        // 은하수 띠 — 아주 옅은 대각선 띠에 성운 결을 얹는다
        float milkyBand = exp(-pow(dot(dir, normalize(vec3(0.42, 0.36, -0.82))) * 2.6, 2.0));
        vec2 milkyUv = vec2(atan(dir.z, dir.x) * 2.2, dir.y * 6.0);
        float milkyNoise = fbm(milkyUv * 2.4 + 7.0);
        color += vec3(0.32, 0.38, 0.62) * milkyBand * smoothstep(0.35, 0.9, milkyNoise) * uMilky * 0.5;
        color += vec3(0.1, 0.12, 0.22) * milkyBand * uMilky * 0.22;

        // 높은 권운 — 구름이 많을 때만 지평선 위로 옅게 흐른다
        vec2 skyPlane = dir.xz / max(0.18, h * 1.1 + 0.28);
        float cirrus = fbm(skyPlane * vec2(0.55, 1.9) + vec2(uTime * 0.006, uTime * 0.002));
        float cirrusMask = smoothstep(0.52, 0.9, cirrus) * smoothstep(0.02, 0.3, h);
        color = mix(color, mix(uHorizon, vec3(1.0), 0.32), cirrusMask * uCloud * 0.34);

        // 지평선 아래는 바다 안개색으로 — 바다와 하늘이 한 색으로 만난다
        float below = 1.0 - smoothstep(-0.16, 0.02, h);
        color = mix(color, uFog, below * 0.92);
        color = mix(color, uFog, exp(-abs(h) * 42.0) * 0.35);

        // 밴딩 제거용 디더
        float dither = (hash21(gl_FragCoord.xy + uTime * 0.5) - 0.5) * 0.005;
        gl_FragColor = vec4(max(color + dither, 0.0), 1.0);
      }
    `,
  });
  const skyDome = new THREE.Mesh(skyGeo, skyMat);
  skyDome.frustumCulled = false;
  skyDome.renderOrder = -10;
  scene.add(skyDome);

  // 은하수 띠 + 반짝이는 별 (셰이더 포인트)
  const starCount = 900;
  const starPositions = new Float32Array(starCount * 3);
  const starColors = new Float32Array(starCount * 3);
  const starSizes = new Float32Array(starCount);
  const starPhases = new Float32Array(starCount);
  const starPalette = [
    new THREE.Color(0xffffff),
    new THREE.Color(0xc7ddff),
    new THREE.Color(0xffe7bd),
    new THREE.Color(0xb9d0ff),
    new THREE.Color(0xfff3d6),
  ];
  for (let i = 0; i < starCount; i += 1) {
    const r = 230 + (i % 9) * 12;
    const u = 0.06 + ((i * 73) % 92) / 100;
    const theta = ((i * 137.508) % 360) * DEG;
    const ring = Math.sqrt(Math.max(0, 1 - u * u));
    starPositions[i * 3] = r * ring * Math.cos(theta);
    starPositions[i * 3 + 1] = r * u;
    starPositions[i * 3 + 2] = r * ring * Math.sin(theta);
    const c = starPalette[i % starPalette.length];
    const bright = 0.55 + ((i * 37) % 45) / 100;
    starColors[i * 3] = c.r * bright;
    starColors[i * 3 + 1] = c.g * bright;
    starColors[i * 3 + 2] = c.b * bright;
    starSizes[i] = i % 17 === 0 ? 9.5 : 3.2 + (i % 5) * 1.15;
    starPhases[i] = ((i * 91) % 628) / 100;
  }
  const starGeo = new THREE.BufferGeometry();
  starGeo.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
  starGeo.setAttribute("aColor", new THREE.BufferAttribute(starColors, 3));
  starGeo.setAttribute("aSize", new THREE.BufferAttribute(starSizes, 1));
  starGeo.setAttribute("aPhase", new THREE.BufferAttribute(starPhases, 1));
  const starMat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    uniforms: {
      uMap: { value: textures.star },
      uTime: { value: 0 },
      uOpacity: { value: 0.9 },
      uPixelRatio: { value: Math.min(typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1, 2) },
    },
    vertexShader: /* glsl */ `
      attribute vec3 aColor;
      attribute float aSize;
      attribute float aPhase;
      uniform float uTime;
      uniform float uPixelRatio;
      varying vec3 vColor;
      varying float vTwinkle;
      void main() {
        vColor = aColor;
        vTwinkle = 0.62 + 0.38 * sin(uTime * 1.7 + aPhase);
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = aSize * uPixelRatio * (160.0 / max(-mv.z, 1.0));
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D uMap;
      uniform float uOpacity;
      varying vec3 vColor;
      varying float vTwinkle;
      void main() {
        vec4 tex = texture2D(uMap, gl_PointCoord);
        float alpha = tex.a * uOpacity * vTwinkle;
        if (alpha < 0.01) discard;
        gl_FragColor = vec4(vColor * tex.rgb * 1.35, alpha);
      }
    `,
  });
  const starField = new THREE.Points(starGeo, starMat);
  starField.frustumCulled = false;
  scene.add(starField);

  const moonGroup = new THREE.Group();
  const moonMesh = new THREE.Mesh(
    new THREE.SphereGeometry(4.2, 32, 32),
    new THREE.MeshBasicMaterial({ color: 0xf2f6ff, map: textures.moon, fog: false })
  );
  moonGroup.add(moonMesh);
  const moonHalo = makeGlowSprite(textures.glow, 0x9dc0ff, 13, 0.28);
  moonGroup.add(moonHalo);
  const moonHaloOuter = makeGlowSprite(textures.glow, 0x5f86d8, 24, 0.12);
  moonGroup.add(moonHaloOuter);
  moonGroup.position.set(50, 88, -82);
  scene.add(moonGroup);

  // 조명 시스템 — 달빛 키 라이트 + 하늘/지면 앰비언트 + 색조 보조광
  const hemiLight = new THREE.HemisphereLight(0x7aa6ee, 0x1b2c42, 0.95);
  scene.add(hemiLight);

  const mainLight = new THREE.DirectionalLight(0xc4dcff, 1.65);
  mainLight.position.set(-34, 52, 30);
  mainLight.castShadow = true;
  mainLight.shadow.mapSize.set(2048, 2048);
  mainLight.shadow.camera.near = 4;
  mainLight.shadow.camera.far = 150;
  mainLight.shadow.camera.left = -46;
  mainLight.shadow.camera.right = 46;
  mainLight.shadow.camera.top = 46;
  mainLight.shadow.camera.bottom = -46;
  mainLight.shadow.bias = -0.00042;
  mainLight.shadow.normalBias = 0.035;
  // r155+ PCF는 shadow.radius로 샘플을 퍼뜨린다 — 딱딱한 계단 그림자를 부드럽게
  mainLight.shadow.radius = 3.4;
  scene.add(mainLight);

  // 반대편 차가운 림 라이트 — 실루엣을 떼어 놓아 입체감을 만든다
  const rimLight = new THREE.DirectionalLight(0x63c8ff, 0.7);
  rimLight.position.set(44, 24, -40);
  scene.add(rimLight);

  // 마을 쪽 따뜻한 보조광
  const warmFill = new THREE.DirectionalLight(0xffb066, 0.32);
  warmFill.position.set(30, 12, 6);
  scene.add(warmFill);

  const villageWarmLight = new THREE.PointLight(0xffb85c, 0, 42, 1.7);
  villageWarmLight.userData.gain = 9;
  villageWarmLight.position.set(20, 9.5, -6);
  scene.add(villageWarmLight);

  const ferrisLight = new THREE.PointLight(0xd7ff00, 0, 30, 1.8);
  ferrisLight.userData.gain = 9;
  ferrisLight.position.set(22.5, 14, -19);
  scene.add(ferrisLight);

  const substationLight = new THREE.PointLight(0xd7ff00, 1.2, 26, 1.6);
  substationLight.userData.gain = 8;
  substationLight.position.set(0, 7.5, 0);
  scene.add(substationLight);

  // 항만·과일 전지 덱·수력 댐의 실내등 — 각 구역이 자기 색의 빛 웅덩이를 갖게 한다
  const pierLight = new THREE.PointLight(0xffd08a, 15, 22, 1.8);
  pierLight.position.set(12.5, 6.2, 18.5);
  pierLight.userData.baseIntensity = 15;
  scene.add(pierLight);

  const fruitDeckLight = new THREE.PointLight(0xd9ff6a, 13, 20, 1.8);
  fruitDeckLight.position.set(24.5, 6.4, 13.5);
  fruitDeckLight.userData.baseIntensity = 13;
  scene.add(fruitDeckLight);

  const damLight = new THREE.PointLight(0x8fd8ff, 15, 24, 1.8);
  damLight.position.set(-21, 9.0, -16);
  damLight.userData.baseIntensity = 15;
  scene.add(damLight);

  const solarDeckLight = new THREE.PointLight(0xffe9b0, 14, 20, 1.8);
  solarDeckLight.position.set(-14.5, 6.5, 15.5);
  solarDeckLight.userData.baseIntensity = 14;
  scene.add(solarDeckLight);

  // 정전 체험에서도 구역등이 함께 꺼지도록 전력 비율에 묶어 둔다
  const zoneLights = [pierLight, fruitDeckLight, damLight, solarDeckLight];

  const crankGlowLight = new THREE.PointLight(0xffb449, 0.4, 20, 1.6);
  crankGlowLight.userData.gain = 10;
  crankGlowLight.position.set(-1, 6.2, 14.5);
  scene.add(crankGlowLight);

  /* ── 2. 바다 · 해안 물결 · 다층 지형 디오라마 ─────────────────── */

  const interactiveTargets = [];
  const registerHit = (mesh, zoneId, kind) => {
    mesh.userData.zoneId = zoneId;
    mesh.userData.hitKind = kind || zoneId;
    interactiveTargets.push(mesh);
    return mesh;
  };

  // 일렁이는 바다 — 표면 기복·거품·수심 색을 셰이더에서 직접 만든다.
  // (물리 재질의 clearcoat 반사는 그대로 두고, 파형/거품만 주입한다)
  const seaUniforms = {
    uTime: { value: 0 },
    uSunDir: { value: new THREE.Vector3(-0.4, 0.5, 0.75).normalize() },
    uSunColor: { value: new THREE.Color(0xffe9b8) },
    uSkyColor: { value: new THREE.Color(0x2a5a94) },
    uDeepColor: { value: new THREE.Color(0x04121f) },
    uShallowColor: { value: new THREE.Color(0x0f4a5e) },
    uFoamColor: { value: new THREE.Color(0xcfe9f7) },
    uNoise: { value: textures.noise },
    uFoamAmount: { value: 1 },
  };

  const seaWaveGLSL = /* glsl */ `
    float seaWaveHeight(vec2 p, float t) {
      float h = 0.0;
      h += sin(p.x * 0.11 + t * 0.95) * 0.5;
      h += sin(p.y * 0.14 - t * 1.1) * 0.42;
      h += sin((p.x + p.y) * 0.06 + t * 0.7) * 0.3;
      h += sin(dot(p, vec2(0.42, -0.31)) + t * 1.7) * 0.12;
      h += sin(dot(p, vec2(-0.27, 0.51)) + t * 2.3) * 0.07;
      return h;
    }
    float seaShoreRadius(float a) {
      return 34.0 * (1.0 + 0.12 * sin(a * 3.0 + 0.6) + 0.066 * cos(a * 5.0 - 1.1)) * 0.955;
    }
  `;

  const seaAmount = 1680;
  const seaGeo = new THREE.PlaneGeometry(seaAmount, seaAmount, 200, 200);
  seaGeo.rotateX(-Math.PI / 2);
  const seaMat = new THREE.MeshPhysicalMaterial({
    color: 0x0a2f57,
    emissive: 0x061a30,
    emissiveIntensity: 0.34,
    roughness: 0.14,
    metalness: 0.03,
    clearcoat: 1,
    clearcoatRoughness: 0.08,
    envMapIntensity: 1.05,
    normalMap: textures.waterNormal,
    normalScale: new THREE.Vector2(0.55, 0.55),
  });
  seaMat.onBeforeCompile = (shader) => {
    shader.uniforms.uTime = seaUniforms.uTime;
    shader.uniforms.uSunDir = seaUniforms.uSunDir;
    shader.uniforms.uSunColor = seaUniforms.uSunColor;
    shader.uniforms.uSkyColor = seaUniforms.uSkyColor;
    shader.uniforms.uDeepColor = seaUniforms.uDeepColor;
    shader.uniforms.uShallowColor = seaUniforms.uShallowColor;
    shader.uniforms.uFoamColor = seaUniforms.uFoamColor;
    shader.uniforms.uNoise = seaUniforms.uNoise;
    shader.uniforms.uFoamAmount = seaUniforms.uFoamAmount;

    shader.vertexShader = shader.vertexShader
      .replace(
        "#include <common>",
        `#include <common>
        uniform float uTime;
        varying vec3 vSeaWorld;
        ${seaWaveGLSL}`
      )
      .replace(
        "#include <begin_vertex>",
        `#include <begin_vertex>
        vec3 seaOrigin = (modelMatrix * vec4(position, 1.0)).xyz;
        float seaAmp = mix(0.14, 0.5, smoothstep(80.0, 22.0, length(seaOrigin.xz)));
        transformed.y += seaWaveHeight(seaOrigin.xz, uTime) * seaAmp;
        vSeaWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;`
      );

    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
        uniform float uTime;
        uniform vec3 uSunDir;
        uniform vec3 uSunColor;
        uniform vec3 uSkyColor;
        uniform vec3 uDeepColor;
        uniform vec3 uShallowColor;
        uniform vec3 uFoamColor;
        uniform sampler2D uNoise;
        uniform float uFoamAmount;
        varying vec3 vSeaWorld;
        ${seaWaveGLSL}`
      )
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
        vec2 seaP = vSeaWorld.xz;
        float seaDist = length(seaP);
        float seaAngle = atan(seaP.y, seaP.x);
        float seaShore = seaShoreRadius(seaAngle);
        float seaDepth = smoothstep(seaShore - 0.4, seaShore + 26.0, seaDist);
        float seaBand = texture2D(uNoise, seaP * 0.035 + vec2(uTime * 0.004, -uTime * 0.003)).r;
        float seaBand2 = texture2D(uNoise, seaP * 0.11 + vec2(-uTime * 0.01, uTime * 0.008)).r;
        float seaRipple = texture2D(uNoise, seaP * 0.26 + vec2(uTime * 0.02, uTime * 0.013)).r;
        float seaCrest = smoothstep(0.74, 1.15, seaWaveHeight(seaP, uTime) + seaBand2 * 0.45);
        // 해안선을 따라 밀려오는 거품 띠 (두 겹으로 물결 끝을 만든다)
        float shoreGap = seaDist - seaShore;
        float surge = 1.5 + sin(uTime * 0.9 + seaAngle * 4.0) * 0.9;
        float seaShoreBand = 1.0 - smoothstep(0.0, 2.6 + seaBand * 3.6, abs(shoreGap - surge));
        float seaShoreBand2 = 1.0 - smoothstep(0.0, 1.3 + seaBand * 2.0, abs(shoreGap - surge * 2.4));
        float seaFoam = clamp(
          seaShoreBand * (0.55 + seaBand * 1.1) +
          seaShoreBand2 * 0.42 +
          seaCrest * (0.35 + seaRipple * 0.4),
          0.0, 1.0
        ) * uFoamAmount;
        vec3 seaColor = mix(uShallowColor, uDeepColor, seaDepth);
        seaColor += uSkyColor * smoothstep(seaShore, seaShore + 22.0, seaDist) * 0.18;
        // 수면에 비스듬히 내려앉는 빛의 길 (태양/달 글리터)
        vec3 viewDirSea = normalize(cameraPosition - vSeaWorld);
        float seaSpec = pow(max(dot(reflect(-normalize(uSunDir), vec3(0.0, 1.0, 0.0)), viewDirSea), 0.0), 14.0);
        float seaGlint = smoothstep(0.72, 1.0, seaRipple) * seaSpec * 2.6;
        seaColor += uSunColor * (seaSpec * 0.09 + seaGlint);
        diffuseColor.rgb = mix(seaColor, uFoamColor, seaFoam * 0.86);`
      )
      .replace(
        "#include <roughnessmap_fragment>",
        `#include <roughnessmap_fragment>
        roughnessFactor = clamp(0.08 + seaDepth * 0.06 + seaFoam * 0.36, 0.05, 0.85);`
      )
      .replace(
        "#include <normal_fragment_maps>",
        `#include <normal_fragment_maps>
        float seaEps = 0.55;
        float seaH0 = seaWaveHeight(seaP, uTime);
        float seaHX = seaWaveHeight(seaP + vec2(seaEps, 0.0), uTime);
        float seaHZ = seaWaveHeight(seaP + vec2(0.0, seaEps), uTime);
        vec2 seaSlope = vec2(seaHX - seaH0, seaHZ - seaH0) / seaEps;
        seaSlope += (vec2(seaBand2, seaBand) - 0.5) * 0.24;
        seaSlope += (vec2(seaRipple, seaBand2) - 0.5) * 0.12;
        vec3 seaNormalWorld = normalize(vec3(-seaSlope.x * 0.75, 1.0, -seaSlope.y * 0.75));
        normal = normalize((viewMatrix * vec4(seaNormalWorld, 0.0)).xyz);`
      );
  };
  const ocean = new THREE.Mesh(seaGeo, seaMat);
  ocean.position.y = -0.04;
  ocean.receiveShadow = true;
  scene.add(ocean);

  // 섬 둘레 얕은 바다(에메랄드 라군) + 부서지는 해안 거품 링
  // 얕은 라군은 방사형 그라디언트로 부드럽게 (링 지오메트리는 각진 띠가 보인다)
  const lagoon = new THREE.Mesh(
    new THREE.PlaneGeometry(150, 124),
    new THREE.MeshBasicMaterial({
      map: textures.glow,
      color: 0x37d8c6,
      transparent: true,
      opacity: 0.26,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    })
  );
  lagoon.rotation.x = -Math.PI / 2;
  lagoon.position.y = 0.1;
  scene.add(lagoon);

  // 해안 거품은 방사형 텍스처를 넓은 평면에 얹어 섬 윤곽을 따라 번지게 한다
  const foamRing = new THREE.Mesh(
    new THREE.PlaneGeometry(112, 92),
    new THREE.MeshBasicMaterial({
      map: textures.foam,
      color: 0xd8f4ff,
      transparent: true,
      opacity: 0.42,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
    })
  );
  foamRing.rotation.x = -Math.PI / 2;
  foamRing.position.y = 0.16;
  scene.add(foamRing);

  // 섬 지형 — 암벽 기반 / 모래 해변 / 잔디 대지 3중 레이어
  // 섬 본체: 잔디 상판 · 모래 해변 띠 · 암벽 절벽을 한 지오메트리로
  // 해변 띠는 좁고 긴 띠라 기본 반복으로는 결이 세로로 늘어난다 — 띠 비율에 맞춰 조정한다
  const beachSand = textures.sand.clone();
  beachSand.repeat.set(2.4, 1.0);
  beachSand.needsUpdate = true;
  const beachSandNormal = textures.sandNormal.clone();
  beachSandNormal.repeat.set(2.4, 1.0);
  beachSandNormal.needsUpdate = true;

  const islandGrassMat = attachWorldSurface(
    new THREE.MeshStandardMaterial({
      color: 0xf2fbf4,
      map: textures.grass,
      normalMap: textures.grassNormal,
      normalScale: new THREE.Vector2(1.15, 1.15),
      roughnessMap: textures.grassRough,
      vertexColors: true,
      roughness: 0.92,
    }),
    { noise: textures.noise, scale: 0.021, strength: 0.72, warm: 0xa8c65a, cool: 0x24583f, sparkle: 0.03 }
  );
  const islandSandMat = attachWorldSurface(
    new THREE.MeshStandardMaterial({
      color: 0xe8d3ab,
      map: beachSand,
      normalMap: beachSandNormal,
      normalScale: new THREE.Vector2(0.8, 0.8),
      roughnessMap: textures.sandRough,
      vertexColors: true,
      roughness: 0.9,
    }),
    { noise: textures.noise, scale: 0.06, strength: 0.3, warm: 0xf0e2bd, cool: 0xa8967a }
  );
  const islandCliffMat = attachWorldSurface(
    new THREE.MeshStandardMaterial({
      color: 0xe7eef8,
      map: textures.rock,
      normalMap: textures.rockNormal,
      normalScale: new THREE.Vector2(1.35, 1.35),
      roughnessMap: textures.rockRough,
      vertexColors: true,
      roughness: 0.92,
      flatShading: true,
    }),
    { noise: textures.noise, scale: 0.075, strength: 0.42, warm: 0x8a93a6, cool: 0x2c3547 }
  );
  const islandBody = new THREE.Mesh(makeIslandBodyGeometry({ rows: 116, seed: 1 }), [
    islandGrassMat,
    islandSandMat,
    islandCliffMat,
  ]);
  islandBody.castShadow = true;
  islandBody.receiveShadow = true;
  scene.add(islandBody);

  // 잔디 상판 높이 함수 — 바닥에 놓이는 소품/길이 지면에 파묻히지 않도록 맞춘다
  function terrainTopY(x, z) {
    const angle = Math.atan2(z, x);
    return 2.42 + Math.sin(angle * 3.1 + 0.7) * 0.07 + Math.cos(angle * 5.3 + 1.9) * 0.05;
  }

  // 접지 그림자 — 방향광 그림자만으로는 소품이 땅에 "떠 보인다".
  // 밑동에 부드러운 어두운 블롭을 깔아 물체를 지면에 단단히 붙인다.
  const contactShadowSpots = [];
  function addContactShadow(x, z, radius, { y = null, strength = 1 } = {}) {
    contactShadowSpots.push({
      x,
      z,
      y: (y == null ? terrainTopY(x, z) : y) + 0.045,
      radius,
      strength,
    });
  }

  // 서쪽 풍력 해안 절벽 대지 — 섬 본체와 같은 3층 문법(잔디 상판 + 화강암 벽)으로
  const windBluff = new THREE.Mesh(
    makeIslandBodyGeometry({
      rows: 64,
      radius: 12.9,
      topY: 4.78,
      rimY: 4.5,
      baseY: 0.2,
      seed: 4,
      withBeach: false,
    }),
    [
      islandBody.material[0],
      islandBody.material[1],
      islandBody.material[2],
    ]
  );
  windBluff.position.set(-27.5, 0, 4.5);
  windBluff.castShadow = true;
  windBluff.receiveShadow = true;
  scene.add(windBluff);

  // 북서쪽 수력 발전소를 감싸는 화강암 봉우리 능선 (댐을 덮지 않도록 뒤쪽으로 물러난다)
  function makeMountainGeometry(seed, detail = 2) {
    const geo = new THREE.IcosahedronGeometry(1, detail);
    const pos = geo.attributes.position;
    const localRng = makeRng(seed);
    for (let i = 0; i < pos.count; i += 1) {
      const x = pos.getX(i);
      const y = pos.getY(i);
      const z = pos.getZ(i);
      const angle = Math.atan2(z, x);
      const radial = Math.hypot(x, z);
      const ridge =
        1 +
        Math.sin(angle * 3 + seed) * 0.16 +
        Math.cos(angle * 5 - seed * 0.6) * 0.08 +
        (localRng() - 0.5) * 0.1;
      // 위로 갈수록 뾰족해지고 아래는 넓게 퍼지는 산 실루엣
      const taper = 1 - Math.max(0, y) * 0.34;
      pos.setX(i, x * radial * ridge * taper);
      pos.setZ(i, z * radial * ridge * taper);
      pos.setY(i, y + (localRng() - 0.5) * 0.08);
    }
    geo.computeVertexNormals();
    return geo;
  }

  const mountainSpecs = [
    { x: -34, z: -21.5, r: 8.6, h: 17, tint: 0x63718b, snow: 0.52, seed: 3 },
    { x: -25, z: -25, r: 7.2, h: 18, tint: 0x5a6a86, snow: 0.5, seed: 7 },
    { x: -15.5, z: -26, r: 6.2, h: 13, tint: 0x66748e, snow: 0.56, seed: 11 },
    { x: -30.5, z: -13.5, r: 4.6, h: 7.6, tint: 0x6e7c95, snow: 0.72, seed: 17 },
  ];
  const mountainMaterials = [];
  mountainSpecs.forEach((spec) => {
    const baseY = 1.1;
    const radiusY = spec.h * 0.62;
    const rockGeo = makeMountainGeometry(spec.seed);
    // 정상부를 눈색으로 물들인다 — 별도 캡 메시 없이 자연스럽게 이어진다
    const pos = rockGeo.attributes.position;
    const colors = new Float32Array(pos.count * 3);
    const rockLow = new THREE.Color(spec.tint);
    const rockHigh = new THREE.Color(0xffffff);
    const snow = new THREE.Color(0xeef5ff);
    const tmp = new THREE.Color();
    for (let i = 0; i < pos.count; i += 1) {
      const h = THREE.MathUtils.clamp((pos.getY(i) + 1) * 0.5, 0, 1);
      const rockShade = rockLow.clone().lerp(rockHigh, Math.pow(h, 2.4) * 0.5);
      const snowAmount = THREE.MathUtils.smoothstep(h, spec.snow, spec.snow + 0.16);
      tmp.copy(rockShade).lerp(snow, snowAmount);
      colors[i * 3] = tmp.r;
      colors[i * 3 + 1] = tmp.g;
      colors[i * 3 + 2] = tmp.b;
    }
    rockGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    const mountainMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      map: textures.rock,
      normalMap: textures.rockNormal,
      normalScale: new THREE.Vector2(1.25, 1.25),
      vertexColors: true,
      roughness: 0.94,
      emissive: 0x0b1a2c,
      emissiveIntensity: 0.5,
    });
    mountainMaterials.push({ mat: mountainMat, base: new THREE.Color(0x0b1a2c) });
    const rock = new THREE.Mesh(rockGeo, mountainMat);
    rock.scale.set(spec.r, radiusY, spec.r * 0.94);
    rock.position.set(spec.x, baseY + radiusY * 0.82, spec.z);
    rock.rotation.y = spec.seed;
    rock.castShadow = true;
    rock.receiveShadow = true;
    scene.add(rock);
  });

  // 댐 뒤쪽 계곡 안개 — 원경과 근경을 분리해 공간감을 준다
  const valleyMist = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: textures.smoke,
      color: 0x9fc0e8,
      transparent: true,
      opacity: 0.3,
      depthWrite: false,
    })
  );
  valleyMist.scale.set(30, 12, 1);
  valleyMist.position.set(-21, 6, -26);
  scene.add(valleyMist);

  // 동쪽 마을 석조 테라스
  const villageTerrace = new THREE.Mesh(
    sculptedIslandGeometry(16.2, 17.4, 0.9, 32, 0.08),
    new THREE.MeshStandardMaterial({
      color: 0x93a4c2,
      map: textures.stone,
      roughness: 0.9,
      flatShading: true,
    })
  );
  villageTerrace.position.set(20.5, 2.35, -7.5);
  villageTerrace.receiveShadow = true;
  scene.add(villageTerrace);

  // 마을 조약돌 산책로 (광장 ↔ 마을)
  const pathControl = [
    [-1, 14.5],
    [4.5, 9],
    [10.5, 2.5],
    [16.5, -4.5],
    [21.5, -8.5],
  ];
  const pathCurve = new THREE.CatmullRomCurve3(
    pathControl.map(([px, pz]) => new THREE.Vector3(px, terrainTopY(px, pz) + 0.12, pz))
  );

  // 지형 높이를 따라가는 평평한 조약돌 리본 (튜브 스케일 대신 정점을 직접 만든다)
  const pathPositions = [];
  const pathUvs = [];
  const pathIndices = [];
  const pathSamples = 56;
  const pathHalfWidth = 0.95;
  const pathSide = new THREE.Vector3();
  for (let i = 0; i <= pathSamples; i += 1) {
    const t = i / pathSamples;
    const point = pathCurve.getPointAt(t);
    const tangent = pathCurve.getTangentAt(t);
    pathSide.set(-tangent.z, 0, tangent.x).normalize().multiplyScalar(pathHalfWidth);
    // 좌우 정점도 각자의 지면 높이에 맞춰야 지면을 뚫지 않는다
    const leftX = point.x + pathSide.x;
    const leftZ = point.z + pathSide.z;
    const rightX = point.x - pathSide.x;
    const rightZ = point.z - pathSide.z;
    pathPositions.push(
      leftX,
      Math.max(point.y, terrainTopY(leftX, leftZ) + 0.1),
      leftZ,
      rightX,
      Math.max(point.y, terrainTopY(rightX, rightZ) + 0.1),
      rightZ
    );
    pathUvs.push(0, t * 9, 1, t * 9);
    if (i < pathSamples) {
      const a = i * 2;
      pathIndices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  }
  const pathGeo = new THREE.BufferGeometry();
  pathGeo.setAttribute("position", new THREE.Float32BufferAttribute(pathPositions, 3));
  pathGeo.setAttribute("uv", new THREE.Float32BufferAttribute(pathUvs, 2));
  pathGeo.setIndex(pathIndices);
  pathGeo.computeVertexNormals();
  const pathMesh = new THREE.Mesh(
    pathGeo,
    new THREE.MeshStandardMaterial({
      color: 0xb4c0d2,
      map: textures.cobble,
      roughness: 0.95,
      side: THREE.DoubleSide,
      polygonOffset: true,
      polygonOffsetFactor: -1,
      polygonOffsetUnits: -2,
    })
  );
  pathMesh.receiveShadow = true;
  scene.add(pathMesh);

  // 남동쪽·동쪽 나무 데크 (난간·말뚝 포함)
  const pierDeck = new THREE.Mesh(
    new THREE.BoxGeometry(11.5, 0.65, 11.5),
    new THREE.MeshStandardMaterial({ color: 0xb98b63, map: textures.wood, roughness: 0.86 })
  );
  pierDeck.position.set(12.5, 2.25, 18.5);
  pierDeck.receiveShadow = true;
  pierDeck.castShadow = true;
  scene.add(pierDeck);

  const fruitDeck = new THREE.Mesh(
    new THREE.BoxGeometry(13.5, 0.8, 10.5),
    new THREE.MeshStandardMaterial({ color: 0xa87a55, map: textures.wood, roughness: 0.86 })
  );
  fruitDeck.position.set(24.8, 2.35, 13.5);
  fruitDeck.receiveShadow = true;
  fruitDeck.castShadow = true;
  scene.add(fruitDeck);

  // 부두 말뚝 + 안전 난간 + 랜턴 (물 위로 뻗은 느낌)
  const pierPilingMat = new THREE.MeshStandardMaterial({ color: 0x6b4a30, roughness: 0.92 });
  const railingMat = new THREE.MeshStandardMaterial({
    color: 0x3d2c1e,
    roughness: 0.8,
    metalness: 0.15,
  });
  for (let i = 0; i < 5; i += 1) {
    const px = 7.4 + i * 2.55;
    [-3.5, 3.5].forEach((dz) => {
      const piling = new THREE.Mesh(
        new THREE.CylinderGeometry(0.24, 0.3, 4.6, 8),
        pierPilingMat
      );
      piling.position.set(px, 0.15, 18.5 + dz);

      scene.add(piling);
      const post = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.13, 1.25, 7), railingMat);
      post.position.set(px, 3.2, 18.5 + dz);

      scene.add(post);
    });
    const rail = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.14, 0.14), railingMat);
    rail.position.set(px - 1.27, 3.7, 18.5 + 3.5);
    scene.add(rail);
    const rail2 = rail.clone();
    rail2.position.z = 18.5 - 3.5;
    scene.add(rail2);
  }
  for (let i = 0; i < 3; i += 1) {
    const lanternPost = new THREE.Mesh(
      new THREE.CylinderGeometry(0.1, 0.13, 2.5, 7),
      railingMat
    );
    lanternPost.position.set(8.6 + i * 3.6, 3.8, 23.6);
    scene.add(lanternPost);
    const lantern = new THREE.Mesh(
      new THREE.SphereGeometry(0.26, 12, 12),
      new THREE.MeshStandardMaterial({
        color: 0xfff0c0,
        emissive: 0xffc04a,
        emissiveIntensity: 1.4,
        roughness: 0.2,
      })
    );
    lantern.position.set(8.6 + i * 3.6, 5.1, 23.6);
    scene.add(lantern);
    const halo = makeGlowSprite(textures.glow, 0xffc45c, 2.6, 0.5);
    halo.position.copy(lantern.position);
    scene.add(halo);
  }

  // 중앙 변전소 원형 석조 광장 & 남쪽 크랭크 발명가 광장
  const hubPlaza = new THREE.Mesh(
    new THREE.CylinderGeometry(8.2, 8.8, 0.85, 24),
    new THREE.MeshStandardMaterial({ color: 0x7f8ea8, map: textures.stone, roughness: 0.88 })
  );
  hubPlaza.position.set(-0.5, 2.35, -0.5);
  hubPlaza.receiveShadow = true;
  scene.add(hubPlaza);

  const crankPlaza = new THREE.Mesh(
    new THREE.CylinderGeometry(6.8, 7.4, 0.75, 24),
    new THREE.MeshStandardMaterial({ color: 0x8797b2, map: textures.cobble, roughness: 0.9 })
  );
  crankPlaza.position.set(-1, 2.3, 14.5);
  crankPlaza.receiveShadow = true;
  scene.add(crankPlaza);

  // 광장 마감 디테일 — 테두리 커브 · 방사형 황동 인레이 · 진입 계단 · 가로등 · 변압기 캐비닛
  const plazaKerbMat = new THREE.MeshStandardMaterial({ color: 0x5d6b80, roughness: 0.9, metalness: 0.12 });
  const plazaInlayMat = new THREE.MeshStandardMaterial({ color: 0xc9974a, metalness: 0.82, roughness: 0.3 });
  const hubKerb = new THREE.Mesh(new THREE.TorusGeometry(8.34, 0.22, 10, 64), plazaKerbMat);
  hubKerb.rotation.x = Math.PI / 2;
  hubKerb.position.set(-0.5, 2.78, -0.5);
  hubKerb.castShadow = true;
  hubKerb.receiveShadow = true;
  scene.add(hubKerb);
  const crankKerb = new THREE.Mesh(new THREE.TorusGeometry(6.95, 0.2, 10, 56), plazaKerbMat);
  crankKerb.rotation.x = Math.PI / 2;
  crankKerb.position.set(-1, 2.64, 14.5);
  crankKerb.castShadow = true;
  scene.add(crankKerb);
  for (let i = 0; i < 12; i += 1) {
    const angle = (i / 12) * TAU;
    const inlay = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.05, 5.2), plazaInlayMat);
    inlay.position.set(-0.5 + Math.cos(angle) * 5.6, 2.79, -0.5 + Math.sin(angle) * 5.6);
    inlay.rotation.y = -angle + Math.PI / 2;
    scene.add(inlay);
  }
  for (let i = 0; i < 8; i += 1) {
    const angle = (i / 8) * TAU + 0.2;
    const inlay = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.05, 3.6), plazaInlayMat);
    inlay.position.set(-1 + Math.cos(angle) * 4.2, 2.66, 14.5 + Math.sin(angle) * 4.2);
    inlay.rotation.y = -angle + Math.PI / 2;
    scene.add(inlay);
  }
  // 중앙 변전소 앞 진입 계단 (남쪽)
  for (let step = 0; step < 3; step += 1) {
    const stair = new THREE.Mesh(
      new THREE.BoxGeometry(5.2 - step * 0.9, 0.22, 0.72),
      new THREE.MeshStandardMaterial({ color: 0x76849a, map: textures.stone, roughness: 0.92 })
    );
    stair.position.set(-0.5, 2.72 - step * 0.2, 8.55 + step * 0.7);
    stair.receiveShadow = true;
    stair.castShadow = true;
    scene.add(stair);
  }
  // 광장 가로등 4기 — 계단 양옆과 동/서 테두리
  const plazaLampMat = new THREE.MeshStandardMaterial({
    color: 0xffe6b4,
    emissive: 0xffb347,
    emissiveIntensity: 0.85,
    roughness: 0.3,
  });
  [[-0.5 + 3.4, 8.3], [-0.5 - 3.4, 8.3], [-0.5 + 7.2, 4.0], [-0.5 - 7.2, 4.0]].forEach(([lx, lz]) => {
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.15, 3.1, 8), plazaKerbMat);
    post.position.set(lx, 4.3, lz);
    post.castShadow = true;
    scene.add(post);
    const lantern = new THREE.Mesh(new THREE.SphereGeometry(0.27, 12, 12), plazaLampMat);
    lantern.position.set(lx, 5.95, lz);
    scene.add(lantern);
    const halo = makeGlowSprite(textures.glow, 0xffc45c, 1.7, 0.36);
    halo.position.copy(lantern.position);
    scene.add(halo);
  });
  // 변압기 캐비닛 2기 — 방열핀 · 경고 스트라이프 · 부싱
  const cabinetMat = new THREE.MeshStandardMaterial({ color: 0x5f7186, metalness: 0.45, roughness: 0.52 });
  const hazardMat = new THREE.MeshStandardMaterial({
    color: 0xffd24a,
    emissive: 0x3a2a00,
    emissiveIntensity: 0.4,
    roughness: 0.5,
  });
  const bushingMat = new THREE.MeshStandardMaterial({ color: 0xe6edf7, roughness: 0.3, metalness: 0.2 });
  [-2.9, 1.1].forEach((cz) => {
    const cabinet = new THREE.Group();
    cabinet.position.set(5.5, 2.78, cz);
    const body = new THREE.Mesh(new THREE.BoxGeometry(1.7, 2.0, 2.1), cabinetMat);
    body.position.y = 1.0;
    body.castShadow = true;
    body.receiveShadow = true;
    cabinet.add(body);
    for (let fin = 0; fin < 6; fin += 1) {
      const finMesh = new THREE.Mesh(new THREE.BoxGeometry(0.14, 1.5, 1.9), cabinetMat);
      finMesh.position.set(-0.94 - fin * 0.13, 1.05, 0);
      cabinet.add(finMesh);
    }
    const stripe = new THREE.Mesh(new THREE.BoxGeometry(1.74, 0.16, 2.14), hazardMat);
    stripe.position.y = 0.55;
    cabinet.add(stripe);
    const lid = new THREE.Mesh(new THREE.BoxGeometry(1.8, 0.12, 2.2), plazaKerbMat);
    lid.position.y = 2.06;
    cabinet.add(lid);
    for (let b = -1; b <= 1; b += 1) {
      const bushing = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.12, 0.42, 8), bushingMat);
      bushing.position.set(0, 2.3, b * 0.62);
      cabinet.add(bushing);
    }
    scene.add(cabinet);
  });
  // 테슬라 코일 → 광장 밖으로 이어지는 지중 케이블 트레이
  const cableTrayMat = new THREE.MeshStandardMaterial({ color: 0x2f3b4d, metalness: 0.4, roughness: 0.62 });
  [-0.9, 0, 0.9].forEach((offset, idx) => {
    const cable = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.07, 6.0), cableTrayMat);
    cable.position.set(-2.4 + idx * 0.1, 2.8, 2.4 + offset);
    cable.rotation.y = 0.32;
    scene.add(cable);
  });

  // ── 흩뿌린 자연 디테일: 바위 · 풀포기 · 관목 · 야자수 ─────────────
  const keepOuts = [
    [-0.5, -0.5, 10.5],
    [-1, 14.5, 9],
    [-14.5, 15.5, 8],
    [12.5, 18.5, 8.5],
    [24.8, 13.5, 9],
    [20.5, -7.5, 17],
    [-27.5, 4.5, 14],
    [-21, -16, 12],
    [33.2, -4.5, 4],
  ];
  const isFreeSpot = (x, z, pad = 0) =>
    keepOuts.every(([kx, kz, kr]) => Math.hypot(x - kx, z - kz) > kr + pad);

  function islandRadiusAt(angle) {
    const wave = 1 + 0.12 * Math.sin(angle * 3 + 0.6) + 0.066 * Math.cos(angle * 5 - 1.1);
    return 34 * wave;
  }

  const rockMatPalette = [0xc2cede, 0xaebccd, 0xd2dce8];
  // 해안선을 따라 놓인 파도에 깎인 바위
  for (let i = 0; i < 34; i += 1) {
    const angle = randRange(0, TAU);
    const radius = islandRadiusAt(angle) * randRange(1.02, 1.16);
    const x = Math.cos(angle) * radius;
    const z = Math.sin(angle) * radius * 0.95;
    const rock = makeRock(randRange(0.7, 2.1), rockMatPalette[i % 3], textures.rock);
    rock.position.set(x, randRange(0.5, 1.2), z);
    scene.add(rock);
  }
  // 대지 위의 이끼 낀 바위
  for (let i = 0; i < 30; i += 1) {
    const angle = randRange(0, TAU);
    const radius = islandRadiusAt(angle) * randRange(0.42, 0.9);
    const x = Math.cos(angle) * radius;
    const z = Math.sin(angle) * radius * 0.95;
    if (!isFreeSpot(x, z, 0.5)) continue;
    const rock = makeRock(randRange(0.35, 0.95), rockMatPalette[i % 3], textures.rock);
    rock.position.set(x, terrainTopY(x, z) + 0.05, z);
    scene.add(rock);
  }

  // 풀포기 (인스턴스) — 원뿔 대신 알파 컷 잎 카드를 교차시켜 실제 풀처럼 보이게 한다
  const grassTuftGeo = (() => {
    const planes = new THREE.BufferGeometry();
    const positions = [];
    const uvs = [];
    const indices = [];
    const halfW = 0.42;
    const height = 0.72;
    for (let i = 0; i < 3; i += 1) {
      const a = (i / 3) * Math.PI;
      const dx = Math.cos(a) * halfW;
      const dz = Math.sin(a) * halfW;
      const base = i * 4;
      positions.push(-dx, 0, -dz, dx, 0, dz, dx, height, dz, -dx, height, -dz);
      uvs.push(0, 0, 1, 0, 1, 1, 0, 1);
      indices.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
    planes.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    planes.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
    planes.setIndex(indices);
    planes.computeVertexNormals();
    return planes;
  })();
  const grassTuftMat = new THREE.MeshStandardMaterial({
    color: 0xd6f2cf,
    map: textures.grassBlade,
    alphaMap: textures.grassBlade,
    transparent: true,
    alphaTest: 0.34,
    side: THREE.DoubleSide,
    roughness: 0.92,
    emissive: 0x0d2a1a,
    emissiveIntensity: 0.35,
  });
  const tuftCount = 900;
  const tuftMesh = new THREE.InstancedMesh(grassTuftGeo, grassTuftMat, tuftCount);
  const tuftDummy = new THREE.Object3D();
  let tuftIndex = 0;
  for (let i = 0; i < tuftCount * 3 && tuftIndex < tuftCount; i += 1) {
    const angle = randRange(0, TAU);
    const radius = islandRadiusAt(angle) * randRange(0.32, 0.86);
    const x = Math.cos(angle) * radius;
    const z = Math.sin(angle) * radius * 0.96;
    if (!isFreeSpot(x, z, -1.2)) continue;
    tuftDummy.position.set(x, terrainTopY(x, z) - 0.04, z);
    tuftDummy.rotation.set(0, randRange(0, TAU), randRange(-0.12, 0.12));
    const s = randRange(0.5, 1.05);
    tuftDummy.scale.set(s * 1.15, s * randRange(0.8, 1.25), s * 1.15);
    tuftDummy.updateMatrix();
    tuftMesh.setMatrixAt(tuftIndex, tuftDummy.matrix);
    tuftIndex += 1;
  }
  tuftMesh.count = tuftIndex;
  tuftMesh.instanceMatrix.needsUpdate = true;
  tuftMesh.frustumCulled = false;
  scene.add(tuftMesh);

  // 관목 (인스턴스)
  const bushGeo = new THREE.IcosahedronGeometry(0.62, 1);
  const bushMat = new THREE.MeshStandardMaterial({
    color: 0x46a878,
    roughness: 0.9,
    flatShading: true,
  });
  const bushCount = 40;
  const bushMesh = new THREE.InstancedMesh(bushGeo, bushMat, bushCount);
  let bushIndex = 0;
  for (let i = 0; i < bushCount * 4 && bushIndex < bushCount; i += 1) {
    const angle = randRange(0, TAU);
    const radius = islandRadiusAt(angle) * randRange(0.5, 0.94);
    const x = Math.cos(angle) * radius;
    const z = Math.sin(angle) * radius * 0.95;
    if (!isFreeSpot(x, z, 0.4)) continue;
    tuftDummy.position.set(x, terrainTopY(x, z) + 0.16, z);
    tuftDummy.rotation.set(0, randRange(0, TAU), 0);
    const s = randRange(0.7, 1.5);
    tuftDummy.scale.set(s, s * randRange(0.7, 1.1), s);
    tuftDummy.updateMatrix();
    bushMesh.setMatrixAt(bushIndex, tuftDummy.matrix);
    bushIndex += 1;
  }
  bushMesh.count = bushIndex;
  bushMesh.instanceMatrix.needsUpdate = true;
  bushMesh.castShadow = true;
  bushMesh.receiveShadow = true;
  bushMesh.frustumCulled = false;
  scene.add(bushMesh);

  // 자연 침엽수 · 활엽수 · 야자수 숲
  // 꽃밭 — 잔디 위 작은 색 점들이 밋밋한 면적을 깨 준다 (인스턴스)
  const flowerPalette = [0xffd166, 0xff8fb3, 0xa78bfa, 0xfef3c7, 0x7dd3fc];
  const flowerGeo = new THREE.SphereGeometry(0.13, 6, 6);
  const flowerCount = 520;
  const flowerMeshes = flowerPalette.map((hex) => {
    const mesh = new THREE.InstancedMesh(
      flowerGeo,
      new THREE.MeshStandardMaterial({
        color: hex,
        emissive: hex,
        emissiveIntensity: 0.22,
        roughness: 0.6,
      }),
      Math.ceil(flowerCount / flowerPalette.length)
    );
    mesh.frustumCulled = false;
    scene.add(mesh);
    return { mesh, used: 0 };
  });
  const flowerDummy = new THREE.Object3D();
  let flowerPlaced = 0;
  for (let i = 0; i < flowerCount * 6 && flowerPlaced < flowerCount; i += 1) {
    const angle = randRange(0, TAU);
    const radius = islandRadiusAt(angle) * randRange(0.3, 0.94);
    const x = Math.cos(angle) * radius;
    const z = Math.sin(angle) * radius * 0.95;
    if (!isFreeSpot(x, z, 0.2)) continue;
    const bucket = flowerMeshes[flowerPlaced % flowerMeshes.length];
    if (bucket.used >= bucket.mesh.count) continue;
    flowerDummy.position.set(x, terrainTopY(x, z) + 0.18, z);
    flowerDummy.rotation.set(0, randRange(0, TAU), 0);
    const sc = randRange(0.7, 1.5);
    flowerDummy.scale.set(sc, sc * 0.8, sc);
    flowerDummy.updateMatrix();
    bucket.mesh.setMatrixAt(bucket.used, flowerDummy.matrix);
    bucket.used += 1;
    flowerPlaced += 1;
  }
  flowerMeshes.forEach(({ mesh, used }) => {
    mesh.count = used;
    mesh.instanceMatrix.needsUpdate = true;
  });

  const treeCoords = [
    [-12, 2.32, -22, 1.15, "pine"],
    [-8, 2.32, -19, 0.9, "pine"],
    [-33, 2.3, -12, 1.05, "pine"],
    [-19, 4.55, 11, 0.85, "broad"],
    [-6, 2.32, 25, 0.95, "broad"],
    [6, 2.32, -23, 1.1, "pine"],
    [10, 2.32, -20, 0.88, "broad"],
    [32, 2.34, 3, 1.0, "pine"],
    [34, 2.34, -15, 0.92, "pine"],
    [8, 2.34, 8, 0.82, "broad"],
    [-16.5, 2.32, 22, 1.0, "broad"],
    [-24, 4.4, 14, 0.9, "pine"],
    [-30, 2.34, -6, 0.95, "pine"],
    [30, 2.34, 9, 0.9, "broad"],
    [-4, 2.32, -14, 0.78, "pine"],
    [16, 2.32, 14, 0.72, "broad"],
  ];
  treeCoords.forEach(([tx, ty, tz, ts, kind], idx) => {
    const tree =
      kind === "broad"
        ? makeBroadleafTree(ts, idx % 2 === 0 ? 0x4fbf85 : 0x5ed495)
        : makePineTree(ts, idx % 2 === 0 ? 0x36a877 : 0x44bf8c);
    tree.position.set(tx, ty, tz);
    scene.add(tree);
    addContactShadow(tx, tz, ts * (kind === "broad" ? 1.5 : 1.2), { y: ty, strength: 0.85 });
  });

  const palmSpots = [
    [7.6, 2.3, 25.6, 1.05],
    [18.4, 2.3, 24.6, 0.92],
    [30.5, 2.34, 18.8, 1.0],
    [-4.5, 2.32, 26.5, 0.86],
  ];
  palmSpots.forEach(([px, py, pz, ps]) => {
    const palm = makePalmTree(ps);
    palm.position.set(px, py, pz);
    scene.add(palm);
    addContactShadow(px, pz, ps * 1.1, { y: py, strength: 0.8 });
  });

  /* ── 3. 중앙 변전소 · 주 회로 스위치 · 플라스마 축전기 · 테슬라 코일 ── */

  const substationGroup = new THREE.Group();
  substationGroup.position.set(-0.5, 2.75, -0.5);
  addContactShadow(-0.5, -0.5, 5.6, { y: 2.75, strength: 0.8 });
  scene.add(substationGroup);

  const copperMat = new THREE.MeshStandardMaterial({
    color: 0xe6843a,
    metalness: 0.78,
    roughness: 0.26,
  });
  const darkMetalMat = new THREE.MeshStandardMaterial({
    color: 0x2d3b55,
    metalness: 0.55,
    roughness: 0.46,
  });
  const chromeMat = new THREE.MeshStandardMaterial({
    color: 0xdce6f7,
    metalness: 0.88,
    roughness: 0.16,
  });

  // 테슬라 코일 본체 (뒤쪽 중앙 y = 0..13.5)
  const teslaGroup = new THREE.Group();
  teslaGroup.position.set(0, 0, -3.4);
  substationGroup.add(teslaGroup);

  const teslaBase = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 2.6, 1.2, 12), darkMetalMat);
  teslaBase.position.y = 0.6;
  teslaBase.castShadow = true;
  teslaGroup.add(teslaBase);

  const teslaColumn = new THREE.Mesh(
    new THREE.CylinderGeometry(0.95, 1.15, 9.2, 20),
    new THREE.MeshStandardMaterial({
      color: 0xb9662a,
      emissive: 0xff8c2b,
      emissiveIntensity: 0.16,
      metalness: 0.72,
      roughness: 0.28,
    })
  );
  teslaColumn.position.y = 5.8;
  teslaColumn.castShadow = true;
  teslaGroup.add(teslaColumn);

  // 세로 권선 — 멀리서도 '구리 코일'로 읽히게 만든다
  const coilGeo = new THREE.TorusGeometry(1.01, 0.055, 6, 22);
  const coilMesh = new THREE.InstancedMesh(coilGeo, copperMat, 30);
  const coilDummy = new THREE.Object3D();
  for (let c = 0; c < 30; c += 1) {
    coilDummy.position.set(0, 1.55 + c * 0.24, -0.0);
    coilDummy.rotation.set(Math.PI / 2, 0, 0);
    const shrink = 1 - c * 0.004;
    coilDummy.scale.set(shrink, shrink, 1);
    coilDummy.updateMatrix();
    coilMesh.setMatrixAt(c, coilDummy.matrix);
  }
  coilMesh.instanceMatrix.needsUpdate = true;
  coilMesh.castShadow = true;
  teslaGroup.add(coilMesh);

  for (let r = 0; r < 6; r += 1) {
    const primaryRing = new THREE.Mesh(new THREE.TorusGeometry(1.55 + r * 0.12, 0.07, 8, 28), copperMat);
    primaryRing.rotation.x = Math.PI / 2;
    primaryRing.position.y = 1.45 + r * 0.22;
    teslaGroup.add(primaryRing);
  }

  const teslaToroidMat = new THREE.MeshStandardMaterial({
    color: 0x8ea6bd,
    emissive: 0x2ec2ff,
    emissiveIntensity: 0.14,
    metalness: 0.92,
    roughness: 0.28,
  });
  const teslaToroid = new THREE.Mesh(new THREE.TorusGeometry(2.15, 0.66, 18, 40), teslaToroidMat);
  teslaToroid.rotation.x = Math.PI / 2;
  teslaToroid.position.y = 10.9;
  teslaToroid.castShadow = true;
  teslaGroup.add(teslaToroid);

  // 토로이드 테두리를 감싸는 구리 밴드 — 금속 반사가 생겨 형태가 또렷해진다
  const teslaBand = new THREE.Mesh(new THREE.TorusGeometry(2.16, 0.1, 8, 44), copperMat);
  teslaBand.rotation.x = Math.PI / 2;
  teslaBand.position.y = 10.9;
  teslaGroup.add(teslaBand);
  const teslaBandTop = teslaBand.clone();
  teslaBandTop.position.y = 11.24;
  teslaGroup.add(teslaBandTop);

  const teslaCrownOrb = new THREE.Mesh(
    new THREE.SphereGeometry(0.42, 18, 18),
    new THREE.MeshStandardMaterial({
      color: 0xdff7ff,
      emissive: 0x7fe4ff,
      emissiveIntensity: 0.9,
      metalness: 0.2,
      roughness: 0.2,
    })
  );
  teslaCrownOrb.position.y = 11.62;
  teslaGroup.add(teslaCrownOrb);
  const teslaHalo = makeGlowSprite(textures.glow, 0x63e6ff, 2.2, 0.2);
  teslaHalo.position.y = 11.5;
  teslaGroup.add(teslaHalo);

  const teslaHit = new THREE.Mesh(
    new THREE.CylinderGeometry(3.2, 3.2, 13.5, 10),
    new THREE.MeshBasicMaterial({ visible: false })
  );
  teslaHit.position.y = 6.5;
  teslaGroup.add(teslaHit);
  registerHit(teslaHit, "circuit", "tesla");

  // 3개의 슈퍼 플라스마 유리 커패시터 튜브
  const capacitorCores = [];
  for (let i = -1; i <= 1; i += 1) {
    const capX = -4.6;
    const capZ = i * 2.1 - 0.8;
    const glass = new THREE.Mesh(
      new THREE.CylinderGeometry(0.68, 0.68, 4.4, 16),
      new THREE.MeshStandardMaterial({
        color: 0x9bd8ff,
        transparent: true,
        opacity: 0.34,
        roughness: 0.1,
        metalness: 0.2,
      })
    );
    glass.position.set(capX, 2.5, capZ);
    substationGroup.add(glass);

    const coreMat = new THREE.MeshStandardMaterial({
      color: 0xd7ff00,
      emissive: 0xbaff00,
      emissiveIntensity: 1.8,
      roughness: 0.2,
    });
    const core = new THREE.Mesh(new THREE.CylinderGeometry(0.46, 0.46, 3.8, 14), coreMat);
    core.position.set(capX, 0.8, capZ);
    core.scale.y = 0.15;
    substationGroup.add(core);
    capacitorCores.push(core);

    const capTop = new THREE.Mesh(new THREE.CylinderGeometry(0.76, 0.76, 0.35, 16), darkMetalMat);
    capTop.position.set(capX, 4.8, capZ);
    substationGroup.add(capTop);
  }

  // 건전지 부스터 스택 (1.5V ~ 4.5V 시각화) + 기준 전구
  const boosterCells = [];
  for (let b = 0; b < 3; b += 1) {
    const cellMat = new THREE.MeshStandardMaterial({
      color: 0x263854,
      emissive: 0xffd24a,
      emissiveIntensity: 0.2,
      roughness: 0.35,
      metalness: 0.45,
    });
    const cell = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.62, 1.55, 16), cellMat);
    cell.position.set(4.5, 0.9 + b * 1.65, -1.6);
    substationGroup.add(cell);
    boosterCells.push(cell);
  }

  const circuitBulbMat = new THREE.MeshStandardMaterial({
    color: 0xfff8d9,
    emissive: 0xffd24a,
    emissiveIntensity: 1.4,
    transparent: true,
    opacity: 0.92,
    roughness: 0.12,
  });
  const circuitBulb = new THREE.Mesh(new THREE.SphereGeometry(1.05, 24, 18), circuitBulbMat);
  circuitBulb.position.set(4.5, 6.4, -1.6);
  substationGroup.add(circuitBulb);
  const bulbStem = new THREE.Mesh(
    new THREE.CylinderGeometry(0.16, 0.16, 1.6, 10),
    new THREE.MeshStandardMaterial({ color: 0x9fb0c8, metalness: 0.85, roughness: 0.3 })
  );
  bulbStem.position.set(4.5, 5.0, -1.6);
  substationGroup.add(bulbStem);
  const bulbCollar = new THREE.Mesh(
    new THREE.CylinderGeometry(0.42, 0.5, 0.4, 12),
    new THREE.MeshStandardMaterial({ color: 0xc9974a, metalness: 0.85, roughness: 0.3 })
  );
  bulbCollar.position.set(4.5, 5.55, -1.6);
  substationGroup.add(bulbCollar);
  const bulbArm = new THREE.Mesh(
    new THREE.BoxGeometry(1.5, 0.16, 0.16),
    new THREE.MeshStandardMaterial({ color: 0x8f9db3, metalness: 0.8, roughness: 0.34 })
  );
  bulbArm.position.set(3.8, 4.3, -1.6);
  substationGroup.add(bulbArm);
  const circuitBulbHalo = makeGlowSprite(textures.glow, 0xffd85c, 4.0, 0.32);
  circuitBulbHalo.position.copy(circuitBulb.position);
  substationGroup.add(circuitBulbHalo);

  // 대형 나이프 스위치 레버 & 교체형 도체/부도체 브리지 (앞쪽 중앙!)
  const switchBase = new THREE.Mesh(new THREE.BoxGeometry(6.8, 0.65, 2.8), darkMetalMat);
  switchBase.position.set(0, 0.35, 3.1);
  switchBase.castShadow = true;
  substationGroup.add(switchBase);

  const jawLeft = new THREE.Mesh(new THREE.BoxGeometry(0.55, 1.35, 0.8), copperMat);
  jawLeft.position.set(-2.3, 1.2, 3.1);
  substationGroup.add(jawLeft);

  const jawRight = new THREE.Mesh(new THREE.BoxGeometry(0.55, 1.35, 0.8), copperMat);
  jawRight.position.set(2.3, 1.2, 3.1);
  substationGroup.add(jawRight);

  const knifePivot = new THREE.Group();
  knifePivot.position.set(-2.3, 1.65, 3.95);
  substationGroup.add(knifePivot);

  const knifeBlade = new THREE.Mesh(new THREE.BoxGeometry(4.7, 0.28, 0.36), copperMat);
  knifeBlade.position.set(2.35, 0, 0);
  knifeBlade.castShadow = true;
  knifePivot.add(knifeBlade);

  const knifeHandle = new THREE.Mesh(
    new THREE.CylinderGeometry(0.28, 0.28, 1.4, 12),
    new THREE.MeshStandardMaterial({
      color: 0xd7ff00,
      emissive: 0xa2cc00,
      emissiveIntensity: 0.7,
      roughness: 0.3,
    })
  );
  knifeHandle.rotation.z = Math.PI / 2;
  knifeHandle.position.set(5.1, 0, 0);
  knifePivot.add(knifeHandle);

  // 틈새 교체 재료 3D 블록 (구리/동전/나무/플라스틱/지우개)
  const materialMeshes = {};
  const matBridgeGroup = new THREE.Group();
  matBridgeGroup.position.set(0, 1.35, 2.55);
  substationGroup.add(matBridgeGroup);

  materialMeshes.copper = new THREE.Mesh(
    new THREE.CylinderGeometry(0.32, 0.32, 4.4, 16),
    new THREE.MeshStandardMaterial({
      color: 0xff9447,
      emissive: 0xff6a00,
      emissiveIntensity: 0.55,
      metalness: 0.85,
      roughness: 0.18,
    })
  );
  materialMeshes.copper.rotation.z = Math.PI / 2;

  materialMeshes.coin = new THREE.Mesh(
    new THREE.CylinderGeometry(1.35, 1.35, 0.42, 24),
    new THREE.MeshStandardMaterial({
      color: 0xffe074,
      emissive: 0xa87c12,
      emissiveIntensity: 0.35,
      metalness: 0.9,
      roughness: 0.2,
    })
  );
  materialMeshes.coin.rotation.x = Math.PI / 2;

  materialMeshes.wood = new THREE.Mesh(
    new THREE.CylinderGeometry(0.38, 0.44, 4.4, 10),
    new THREE.MeshStandardMaterial({ color: 0xa67442, map: textures.wood, roughness: 0.92 })
  );
  materialMeshes.wood.rotation.z = Math.PI / 2;

  materialMeshes.plastic = new THREE.Mesh(
    new THREE.BoxGeometry(4.4, 0.26, 0.95),
    new THREE.MeshStandardMaterial({
      color: 0x7fd0ff,
      transparent: true,
      opacity: 0.66,
      roughness: 0.15,
    })
  );

  materialMeshes.eraser = new THREE.Mesh(
    new THREE.BoxGeometry(3.6, 0.95, 1.3),
    new THREE.MeshStandardMaterial({ color: 0xff82a4, roughness: 0.85 })
  );

  Object.keys(materialMeshes).forEach((key) => {
    materialMeshes[key].visible = key === "copper";
    materialMeshes[key].castShadow = true;
    matBridgeGroup.add(materialMeshes[key]);
  });

  const switchHit = new THREE.Mesh(
    new THREE.BoxGeometry(7.6, 4.5, 4.4),
    new THREE.MeshBasicMaterial({ visible: false })
  );
  switchHit.position.set(0, 1.8, 3.0);
  substationGroup.add(switchHit);
  registerHit(switchHit, "circuit", "switch");

  /* ── 4. 자이언트 손잡이 크랭크 발전기 (Front-Center) ─────────── */

  const crankGroup = new THREE.Group();
  crankGroup.position.set(-1, 2.7, 14.5);
  scene.add(crankGroup);

  const dynamoBed = new THREE.Mesh(new THREE.BoxGeometry(8.6, 0.8, 5.4), darkMetalMat);
  dynamoBed.position.y = 0.4;
  dynamoBed.castShadow = true;
  dynamoBed.receiveShadow = true;
  crankGroup.add(dynamoBed);

  // 대형 구리 고정자 코일 하우징
  const coilStatorMat = new THREE.MeshStandardMaterial({
    color: 0xd97a34,
    emissive: 0xff9b28,
    emissiveIntensity: 0.2,
    metalness: 0.72,
    roughness: 0.28,
  });
  const statorRings = [];
  for (let i = 0; i < 6; i += 1) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(2.15, 0.22, 12, 28), coilStatorMat);
    ring.position.set(-1.6 + i * 0.42, 3.1, 0);
    ring.rotation.y = Math.PI / 2;
    ring.castShadow = true;
    crankGroup.add(ring);
    statorRings.push(ring);
  }

  // 회전하는 N극(빨강) / S극(파랑) 자석 로터
  const rotorPivot = new THREE.Group();
  rotorPivot.position.set(-0.5, 3.1, 0);
  crankGroup.add(rotorPivot);

  const magnetNorth = new THREE.Mesh(
    new THREE.BoxGeometry(1.1, 3.1, 1.1),
    new THREE.MeshStandardMaterial({
      color: 0xff4d6d,
      emissive: 0xb81d38,
      emissiveIntensity: 0.35,
      roughness: 0.35,
    })
  );
  magnetNorth.position.y = 0.8;
  rotorPivot.add(magnetNorth);

  const magnetSouth = new THREE.Mesh(
    new THREE.BoxGeometry(1.1, 3.1, 1.1),
    new THREE.MeshStandardMaterial({
      color: 0x3b82f6,
      emissive: 0x1d4ed8,
      emissiveIntensity: 0.35,
      roughness: 0.35,
    })
  );
  magnetSouth.position.y = -0.8;
  rotorPivot.add(magnetSouth);

  // 맞물려 도는 황동 기어 + 초대형 네온 플라이휠 크랭크 손잡이
  const crankWheelPivot = new THREE.Group();
  crankWheelPivot.position.set(2.6, 3.1, 2.2);
  crankGroup.add(crankWheelPivot);

  const flywheelRim = new THREE.Mesh(
    new THREE.TorusGeometry(2.85, 0.26, 14, 36),
    new THREE.MeshStandardMaterial({
      color: 0xc8ee44,
      emissive: 0xa8d900,
      emissiveIntensity: 0.32,
      metalness: 0.5,
      roughness: 0.28,
    })
  );
  flywheelRim.castShadow = true;
  crankWheelPivot.add(flywheelRim);

  const spokeMat = new THREE.MeshStandardMaterial({
    color: 0x6a7a93,
    metalness: 0.8,
    roughness: 0.3,
  });
  for (let s = 0; s < 6; s += 1) {
    const spoke = new THREE.Mesh(new THREE.BoxGeometry(5.4, 0.13, 0.13), spokeMat);
    spoke.rotation.z = (s * Math.PI) / 6;
    crankWheelPivot.add(spoke);
  }
  const wheelHub = new THREE.Mesh(
    new THREE.CylinderGeometry(0.42, 0.42, 0.5, 16),
    new THREE.MeshStandardMaterial({ color: 0xb7c4d6, metalness: 0.9, roughness: 0.24 })
  );
  wheelHub.rotation.x = Math.PI / 2;
  crankWheelPivot.add(wheelHub);

  const crankGrip = new THREE.Mesh(
    new THREE.CylinderGeometry(0.36, 0.36, 1.7, 16),
    new THREE.MeshStandardMaterial({
      color: 0xffbe3b,
      emissive: 0xff8c00,
      emissiveIntensity: 0.9,
      roughness: 0.22,
    })
  );
  crankGrip.rotation.x = Math.PI / 2;
  crankGrip.position.set(2.85, 0, 0.95);
  crankWheelPivot.add(crankGrip);
  const crankGripHalo = makeGlowSprite(textures.glow, 0xd7ff00, 2.6, 0.42);
  crankGripHalo.position.set(2.85, 0, 1.3);
  crankWheelPivot.add(crankGripHalo);

  // 발전기 상단 에디슨 벌브 타워
  const dynamoBulbMat = new THREE.MeshStandardMaterial({
    color: 0xfff5cc,
    emissive: 0xffae33,
    emissiveIntensity: 0.15,
    transparent: true,
    opacity: 0.9,
    roughness: 0.1,
  });
  const dynamoBulb = new THREE.Mesh(new THREE.SphereGeometry(1.15, 24, 20), dynamoBulbMat);
  dynamoBulb.position.set(-2.9, 6.2, 0);
  crankGroup.add(dynamoBulb);

  // 필라멘트 + 놋쇠 소켓
  const filamentMat = new THREE.MeshStandardMaterial({
    color: 0xfff6d0,
    emissive: 0xffc65c,
    emissiveIntensity: 1.6,
    roughness: 0.4,
  });
  for (let f = 0; f < 4; f += 1) {
    const filament = new THREE.Mesh(
      new THREE.TorusGeometry(0.34 - f * 0.05, 0.022, 5, 16, Math.PI * 1.2),
      filamentMat
    );
    filament.position.set(-2.9, 6.05 + f * 0.14, 0);
    filament.rotation.z = -Math.PI * 0.6;
    crankGroup.add(filament);
  }
  const bulbSocket = new THREE.Mesh(
    new THREE.CylinderGeometry(0.42, 0.5, 0.6, 14),
    new THREE.MeshStandardMaterial({ color: 0xd9a54b, metalness: 0.85, roughness: 0.28 })
  );
  bulbSocket.position.set(-2.9, 4.92, 0);
  crankGroup.add(bulbSocket);
  const dynamoBulbPedestal = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.65, 2.2, 12), darkMetalMat);
  dynamoBulbPedestal.position.set(-2.9, 4.4, 0);
  crankGroup.add(dynamoBulbPedestal);
  const dynamoBulbHalo = makeGlowSprite(textures.glow, 0xffbe55, 4.6, 0.0);
  dynamoBulbHalo.position.copy(dynamoBulb.position);
  crankGroup.add(dynamoBulbHalo);

  const crankHit = new THREE.Mesh(
    new THREE.SphereGeometry(4.4, 12, 12),
    new THREE.MeshBasicMaterial({ visible: false })
  );
  crankHit.position.set(1.2, 3.2, 1.2);
  crankGroup.add(crankHit);
  registerHit(crankHit, "generator", "crank");

  /* ── 5. 해안 풍력 발전 단지 (West Bluff — 3 Turbines + Wind Ribbons) ── */

  const windGroup = new THREE.Group();
  scene.add(windGroup);

  const turbineSpecs = [
    { x: -27.5, y: 4.8, z: 3.5, towerH: 13.2, scale: 1.0 },
    { x: -32.2, y: 4.5, z: -2.2, towerH: 11.4, scale: 0.86 },
    { x: -24.2, y: 4.6, z: 10.5, towerH: 11.8, scale: 0.9 },
  ];
  turbineSpecs.forEach((spec) => {
    addContactShadow(spec.x, spec.z, 2.6 * spec.scale, { y: spec.y, strength: 0.85 });
  });
  const turbines = [];
  const bladeMaterial = new THREE.MeshStandardMaterial({
    color: 0xf1f7ff,
    emissive: 0x3bf0c5,
    emissiveIntensity: 0.14,
    roughness: 0.28,
    metalness: 0.18,
  });

  /** 날개 단면을 뽑아 만든 실제 풍력 블레이드 (뿌리는 두껍고 끝은 가늘게) */
  function makeBladeGeometry(len) {
    const shape = new THREE.Shape();
    shape.moveTo(0.0, 0.0);
    shape.bezierCurveTo(0.3, len * 0.08, 0.34, len * 0.42, 0.1, len * 0.99);
    shape.lineTo(-0.02, len);
    shape.bezierCurveTo(-0.26, len * 0.55, -0.2, len * 0.2, -0.12, 0.0);
    shape.closePath();
    const geo = new THREE.ExtrudeGeometry(shape, {
      depth: 0.06,
      bevelEnabled: true,
      bevelSize: 0.02,
      bevelThickness: 0.02,
      bevelSegments: 1,
      steps: 1,
    });
    geo.translate(0, 0, -0.03);
    return geo;
  }

  function populateRotorBlades(rotor, count, bladeScale) {
    while (rotor.children.length) {
      const old = rotor.children.pop();
      if (old.geometry) old.geometry.dispose();
    }
    const len = 3.2 + bladeScale * 4.2;
    for (let i = 0; i < count; i += 1) {
      const holder = new THREE.Group();
      holder.rotation.z = (i / count) * TAU;
      const blade = new THREE.Mesh(makeBladeGeometry(len), bladeMaterial);
      blade.position.y = 0.28;
      blade.rotation.y = 0.26 + (i % 2) * 0.06;
      blade.rotation.z = 0.04;
      holder.add(blade);

      const root = new THREE.Mesh(
        new THREE.SphereGeometry(0.17, 8, 8),
        new THREE.MeshStandardMaterial({ color: 0xdfe8f5, metalness: 0.3, roughness: 0.35 })
      );
      root.position.y = 0.24;
      holder.add(root);
      rotor.add(holder);
    }
  }

  turbineSpecs.forEach((spec) => {
    const unit = new THREE.Group();
    unit.position.set(spec.x, spec.y, spec.z);
    windGroup.add(unit);

    // 타워: 살짝 도톰한 받침 + 이음매 링 + 무광 스틸 (하얀 파이프처럼 보이지 않게)
    const towerMat = new THREE.MeshStandardMaterial({
      color: 0x9aa9bd,
      roughness: 0.46,
      metalness: 0.38,
      envMapIntensity: 0.85,
    });
    const tower = new THREE.Mesh(
      new THREE.CylinderGeometry(0.4 * spec.scale, 0.9 * spec.scale, spec.towerH, 22, 1, true),
      towerMat
    );
    tower.position.y = spec.towerH * 0.5;
    tower.castShadow = true;
    tower.receiveShadow = true;
    unit.add(tower);

    const towerFoot = new THREE.Mesh(
      new THREE.CylinderGeometry(0.98 * spec.scale, 1.15 * spec.scale, 0.5, 18),
      new THREE.MeshStandardMaterial({ color: 0x6d7787, roughness: 0.72, metalness: 0.24 })
    );
    towerFoot.position.y = 0.25;
    towerFoot.castShadow = true;
    towerFoot.receiveShadow = true;
    unit.add(towerFoot);

    [0.28, 0.52, 0.76].forEach((t) => {
      const seam = new THREE.Mesh(
        new THREE.TorusGeometry((0.9 - 0.5 * t) * spec.scale, 0.035 * spec.scale, 6, 20),
        new THREE.MeshStandardMaterial({ color: 0x6f7c8e, roughness: 0.5, metalness: 0.45 })
      );
      seam.rotation.x = Math.PI / 2;
      seam.position.y = spec.towerH * t;
      unit.add(seam);
    });

    // 나셀: 뒤로 갈수록 가늘어지는 캡슐 + 꼬리 핀
    const nacelleMat = new THREE.MeshStandardMaterial({
      color: 0xa6b6cb,
      roughness: 0.32,
      metalness: 0.42,
    });
    const nacelle = new THREE.Mesh(
      new THREE.CapsuleGeometry(0.62 * spec.scale, 1.5 * spec.scale, 8, 18),
      nacelleMat
    );
    nacelle.rotation.x = Math.PI / 2;
    nacelle.position.set(0, spec.towerH, -0.15 * spec.scale);
    nacelle.castShadow = true;
    unit.add(nacelle);
    const tailFin = new THREE.Mesh(
      new THREE.BoxGeometry(0.08, 0.72 * spec.scale, 1.0 * spec.scale),
      nacelleMat
    );
    tailFin.position.set(0, spec.towerH + 0.5 * spec.scale, -1.15 * spec.scale);
    tailFin.castShadow = true;
    unit.add(tailFin);

    const beacon = new THREE.Mesh(
      new THREE.SphereGeometry(0.24, 10, 10),
      new THREE.MeshBasicMaterial({ color: 0x5cf2c2 })
    );
    beacon.position.set(0, spec.towerH + 0.85, -0.8);
    unit.add(beacon);

    const hub = new THREE.Mesh(
      new THREE.ConeGeometry(0.62 * spec.scale, 1.2 * spec.scale, 14),
      chromeMat
    );
    hub.rotation.x = Math.PI / 2;
    hub.position.set(0, spec.towerH, 1.65 * spec.scale);
    unit.add(hub);

    const rotor = new THREE.Group();
    rotor.position.set(0, spec.towerH, 1.55 * spec.scale);
    unit.add(rotor);
    populateRotorBlades(rotor, 3, 0.45 * spec.scale);

    const hit = new THREE.Mesh(
      new THREE.CylinderGeometry(4.8, 4.8, spec.towerH + 6, 8),
      new THREE.MeshBasicMaterial({ visible: false })
    );
    hit.position.y = spec.towerH * 0.6;
    unit.add(hit);
    registerHit(hit, "wind", "wind");

    turbines.push({ unit, rotor, scale: spec.scale, beacon });
  });

  // 3D 바람 리본 스트림
  const windRibbons = [];
  for (let i = 0; i < 16; i += 1) {
    const ribbon = new THREE.Mesh(
      new THREE.BoxGeometry(2.4 + (i % 4) * 0.85, 0.07, 0.13),
      new THREE.MeshBasicMaterial({
        color: 0x7ef7e1,
        transparent: true,
        opacity: 0.26,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      })
    );
    ribbon.position.set(
      -42 + (i * 4.2) % 28,
      7.5 + (i % 5) * 3.1,
      -5 + ((i * 3.7) % 21)
    );
    ribbon.rotation.y = -0.25;
    scene.add(ribbon);
    windRibbons.push(ribbon);
  }

  /* ── 6. 해바라기 태양광 테라스 + 하늘 위 황금 태양 & 구름 ─────── */

  const solarGroup = new THREE.Group();
  solarGroup.position.set(-14.5, 2.35, 15.5);
  scene.add(solarGroup);

  const solarPanels = [];
  const solarPanelMat = new THREE.MeshPhysicalMaterial({
    color: 0x5d80b8,
    map: textures.solar,
    emissive: 0x1d3f9e,
    emissiveIntensity: 0.12,
    roughness: 0.26,
    metalness: 0.25,
    clearcoat: 1,
    clearcoatRoughness: 0.08,
  });
  const solarTrimMat = new THREE.MeshStandardMaterial({
    color: 0xb9c7da,
    metalness: 0.92,
    roughness: 0.28,
  });
  const solarCellRibMat = new THREE.MeshStandardMaterial({
    color: 0x2b3a55,
    metalness: 0.6,
    roughness: 0.42,
  });

  for (let i = 0; i < 4; i += 1) {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const mount = new THREE.Group();
    mount.position.set((col - 0.5) * 5.2, 0, (row - 0.5) * 4.6);
    solarGroup.add(mount);

    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.36, 2.2, 10), darkMetalMat);
    post.position.y = 1.1;

    mount.add(post);

    const pivot = new THREE.Group();
    pivot.position.y = 2.25;
    mount.add(pivot);

    // 알루미늄 테두리(레일 4개) 위에 유리 셀 판을 얹는다 — 두께가 읽혀 종이처럼 보이지 않는다
    const frameRail = (w, d, x, z) => {
      const rail = new THREE.Mesh(new THREE.BoxGeometry(w, 0.14, d), solarTrimMat);
      rail.position.set(x, -0.03, z);
      rail.castShadow = true;
      pivot.add(rail);
    };
    frameRail(4.46, 0.12, 0, 1.6);
    frameRail(4.46, 0.12, 0, -1.6);
    frameRail(0.12, 3.32, 2.17, 0);
    frameRail(0.12, 3.32, -2.17, 0);

    const plate = new THREE.Mesh(new THREE.BoxGeometry(4.24, 0.09, 3.14), solarPanelMat);
    plate.position.y = 0.03;
    plate.castShadow = true;
    plate.receiveShadow = true;
    pivot.add(plate);

    // 셀 구획 리본 — 판 위의 격자 무늬가 가까이서도 살아난다
    for (let c = -1; c <= 1; c += 1) {
      const rib = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.012, 0.05), solarCellRibMat);
      rib.position.set(0, 0.082, c * 0.78);
      pivot.add(rib);
    }
    const midRib = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.012, 3.1), solarCellRibMat);
    midRib.position.set(0, 0.082, 0);
    pivot.add(midRib);

    // 접합 상자 & 케이블
    const junction = new THREE.Mesh(
      new THREE.BoxGeometry(0.4, 0.16, 0.28),
      new THREE.MeshStandardMaterial({ color: 0x2b3444, roughness: 0.5, metalness: 0.3 })
    );
    junction.position.set(1.2, 0.02, 1.35);
    pivot.add(junction);

    [-1.25, 1.25].forEach((offsetX) => {
      [-1.0, 1.0].forEach((offsetZ) => {
        const strut = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.055, 1.62, 6), solarTrimMat);
        strut.position.set(offsetX, -0.72, offsetZ * 0.62);
        strut.rotation.x = offsetZ * 0.42;
        strut.castShadow = true;
        pivot.add(strut);
      });
    });
    const crossBar = new THREE.Mesh(new THREE.BoxGeometry(3.0, 0.07, 0.07), solarTrimMat);
    crossBar.position.set(0, -1.02, 0.62);
    crossBar.rotation.z = 0;
    pivot.add(crossBar);

    solarPanels.push(pivot);

    const panelHit = new THREE.Mesh(
      new THREE.BoxGeometry(4.8, 3.2, 3.8),
      new THREE.MeshBasicMaterial({ visible: false })
    );
    panelHit.position.y = 2.0;
    mount.add(panelHit);
    registerHit(panelHit, "solar", "panel");
  }

  // 하늘 위 드래그 가능한 3D 황금 태양 오브 + 광선 콘
  const sunOrbGroup = new THREE.Group();
  scene.add(sunOrbGroup);

  const sunSphere = new THREE.Mesh(
    new THREE.SphereGeometry(5.4, 32, 32),
    new THREE.MeshBasicMaterial({ color: 0xfff0b8, fog: false })
  );
  sunSphere.material.color.setRGB(1.55, 1.32, 0.86);
  sunOrbGroup.add(sunSphere);

  const sunRays = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: textures.sunRays,
      color: 0xffd77a,
      transparent: true,
      opacity: 0.6,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      fog: false,
    })
  );
  sunRays.scale.set(30, 30, 1);
  sunOrbGroup.add(sunRays);

  const sunCorona = makeGlowSprite(textures.glow, 0xffbe3b, 15, 0.42);
  sunOrbGroup.add(sunCorona);

  // 태양은 멀리 떠 있어도 손으로 잡아 끌 수 있도록 보이지 않는 판정 구를 크게 둔다
  const sunHit = new THREE.Mesh(
    new THREE.SphereGeometry(24, 12, 12),
    new THREE.MeshBasicMaterial({ visible: false })
  );
  sunOrbGroup.add(sunHit);
  registerHit(sunHit, "solar", "sun");

  // 태양 → 태양광 테라스 빛 기둥
  const sunBeamMat = makeBeamMaterial({
    color: 0xffe08a,
    opacity: 0.16,
    noise: textures.noise,
    fade: 1.5,
    softness: 2.1,
    speed: 0.05,
  });
  const sunBeam = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 7.4, 42, 28, 1, true), sunBeamMat);
  scene.add(sunBeam);

  // 하늘 구름 — fBm으로 깎은 볼륨 스프라이트를 겹쳐 두께를 만들고,
  // 아래쪽 퍼프는 어둡게 깔아 스스로 음영을 갖게 한다.
  const cloudClusters = [];
  const cloudMaterials = [];
  for (let c = 0; c < 12; c += 1) {
    const cluster = new THREE.Group();
    const puffs = 4 + (c % 3);
    const shadeSeed = 0.72 + (c % 4) * 0.06;
    for (let puff = 0; puff < puffs; puff += 1) {
      const isBase = puff % 3 === 0;
      const mat = new THREE.SpriteMaterial({
        map: textures.cloudSoft,
        color: 0xffffff,
        transparent: true,
        opacity: 0,
        depthWrite: false,
        fog: true,
      });
      mat.userData.shade = isBase ? shadeSeed * 0.72 : 0.92 + (puff % 2) * 0.08;
      const sprite = new THREE.Sprite(mat);
      const width = 30 + randRange(-5, 10) + (c % 2) * 7;
      sprite.scale.set(width, width * randRange(0.46, 0.62), 1);
      sprite.position.set(
        (puff - (puffs - 1) * 0.5) * 17.5 + randRange(-3, 3),
        randRange(-2.2, 1.8) + (isBase ? -2.6 : 1.4),
        randRange(-5.5, 5.5)
      );
      cluster.add(sprite);
      cloudMaterials.push(mat);
    }
    const angle = (c / 12) * TAU + randRange(-0.14, 0.14);
    const radius = randRange(120, 200);
    cluster.position.set(
      Math.cos(angle) * radius,
      randRange(52, 96),
      Math.sin(angle) * radius * 0.92
    );
    cluster.userData = { angle, radius, baseY: cluster.position.y, phase: randRange(0, TAU) };
    scene.add(cluster);
    cloudClusters.push(cluster);
  }

  /* ── 7. 폭포 수력 발전 댐 · 저수지 · 물레바퀴 (North-West) ────── */

  const hydroGroup = new THREE.Group();
  hydroGroup.position.set(-21, 2.2, -16);
  scene.add(hydroGroup);

  const damMat = new THREE.MeshStandardMaterial({
    color: 0x9aa8bd,
    map: textures.stone,
    roughness: 0.9,
  });
  const damWall = new THREE.Mesh(new THREE.BoxGeometry(9.6, 9.0, 2.4), damMat);
  damWall.position.set(0, 4.5, -2.2);
  damWall.castShadow = true;
  damWall.receiveShadow = true;
  hydroGroup.add(damWall);

  // 댐 마루 산책로 + 난간 + 버트레스
  const damCrest = new THREE.Mesh(
    new THREE.BoxGeometry(10.2, 0.34, 2.9),
    new THREE.MeshStandardMaterial({ color: 0xc3cddd, roughness: 0.85 })
  );
  damCrest.position.set(0, 9.15, -2.2);
  damCrest.castShadow = true;
  damCrest.receiveShadow = true;
  hydroGroup.add(damCrest);

  for (let b = -1; b <= 1; b += 1) {
    const buttress = new THREE.Mesh(new THREE.BoxGeometry(1.1, 7.6, 0.9), damMat);
    buttress.position.set(b * 3.1, 3.8, -0.95);
    buttress.castShadow = true;
    buttress.receiveShadow = true;
    hydroGroup.add(buttress);
  }

  const crestRailMat = new THREE.MeshStandardMaterial({
    color: 0x515f74,
    metalness: 0.6,
    roughness: 0.45,
  });
  for (let r = 0; r < 9; r += 1) {
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.8, 5), crestRailMat);
    post.position.set(-4.4 + r * 1.1, 9.62, -0.85);
    hydroGroup.add(post);
  }
  const crestRail = new THREE.Mesh(new THREE.BoxGeometry(9.6, 0.08, 0.08), crestRailMat);
  crestRail.position.set(0, 10.0, -0.85);
  hydroGroup.add(crestRail);

  // 댐 마루 조명 3기 — 밤에도 댐 윤곽이 읽히게
  for (let l = -1; l <= 1; l += 1) {
    const crestLampMat = new THREE.MeshStandardMaterial({
      color: 0xfff3cf,
      emissive: 0xffc45c,
      emissiveIntensity: 1.8,
      roughness: 0.3,
    });
    const crestLamp = new THREE.Mesh(new THREE.SphereGeometry(0.16, 10, 10), crestLampMat);
    crestLamp.position.set(l * 4.2, 10.28, -0.85);
    hydroGroup.add(crestLamp);
    const crestLampGlow = makeGlowSprite(textures.glow, 0xffc45c, 1.9, 0.42);
    crestLampGlow.position.copy(crestLamp.position);
    hydroGroup.add(crestLampGlow);
  }

  // 콘크리트 벽면의 석조 줄눈 3단 — 밋밋한 회색 판을 쌓아 올린 벽처럼
  const courseMat = new THREE.MeshStandardMaterial({ color: 0x8494ac, roughness: 0.92 });
  for (let c = 0; c < 3; c += 1) {
    const course = new THREE.Mesh(new THREE.BoxGeometry(9.66, 0.16, 0.14), courseMat);
    course.position.set(0, 2.9 + c * 2.4, -0.97);
    hydroGroup.add(course);
  }
  // 점검 사다리 (좌측 벽면) + 배수관 2열
  const ladderMat = new THREE.MeshStandardMaterial({ color: 0x3d4a60, metalness: 0.7, roughness: 0.42 });
  [-3.9, -3.55].forEach((lx) => {
    const ladderRail = new THREE.Mesh(new THREE.BoxGeometry(0.07, 7.4, 0.07), ladderMat);
    ladderRail.position.set(lx, 5.6, -0.93);
    hydroGroup.add(ladderRail);
  });
  for (let rung = 0; rung < 11; rung += 1) {
    const step = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.05, 0.05), ladderMat);
    step.position.set(-3.72, 2.4 + rung * 0.66, -0.93);
    hydroGroup.add(step);
  }
  [-6.9, 7.3].forEach((px) => {
    const drain = new THREE.Mesh(
      new THREE.CylinderGeometry(0.11, 0.11, 8.4, 8),
      new THREE.MeshStandardMaterial({ color: 0x5a6a80, metalness: 0.55, roughness: 0.5 })
    );
    drain.position.set(px * 0.55, 4.9, -0.9);
    hydroGroup.add(drain);
  });
  // 물때 자국 — 수문 아래로 흐른 자국을 반투명 평면으로
  const damStain = new THREE.Mesh(
    new THREE.PlaneGeometry(4.2, 6.4),
    new THREE.MeshBasicMaterial({
      map: textures.foam,
      color: 0x7fd8ff,
      transparent: true,
      opacity: 0.14,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide,
    })
  );
  damStain.position.set(0.6, 5.2, -0.95);
  hydroGroup.add(damStain);

  // 낙차에 따라 수위가 오르내리는 에메랄드 저수지 수면
  const reservoirWater = new THREE.Mesh(
    new THREE.BoxGeometry(9.6, 5.5, 6.8),
    new THREE.MeshStandardMaterial({
      color: 0x2bb8ff,
      emissive: 0x0e6ba8,
      emissiveIntensity: 0.55,
      transparent: true,
      opacity: 0.84,
      roughness: 0.14,
    })
  );
  reservoirWater.position.set(0, 6.6, -6.5);
  hydroGroup.add(reservoirWater);

  // 수문 밸브 & 폭포 물줄기 리본
  const sluiceGate = new THREE.Mesh(
    new THREE.BoxGeometry(2.4, 2.2, 0.6),
    new THREE.MeshStandardMaterial({
      color: 0xffb703,
      emissive: 0x9e5800,
      emissiveIntensity: 0.35,
      roughness: 0.35,
    })
  );
  sluiceGate.position.set(1.2, 7.2, -0.8);
  hydroGroup.add(sluiceGate);

  const waterfallMat = new THREE.MeshStandardMaterial({
    color: 0x8be0ff,
    emissive: 0x3db5ff,
    emissiveIntensity: 0.75,
    transparent: true,
    opacity: 0.78,
    roughness: 0.12,
  });
  // 수문 아래 물받이 턱
  const sluiceApron = new THREE.Mesh(
    new THREE.BoxGeometry(2.8, 0.22, 1.1),
    new THREE.MeshStandardMaterial({ color: 0x8b9ab0, roughness: 0.88 })
  );
  sluiceApron.position.set(1.2, 6.95, -0.5);
  hydroGroup.add(sluiceApron);

  // 댐 벽을 따라 흐르다 아래 연못으로 떨어지는 물길 (튜브 커브)
  const fallCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(1.2, 7.9, -0.78),
    new THREE.Vector3(1.26, 6.1, -0.42),
    new THREE.Vector3(1.44, 3.6, 0.55),
    new THREE.Vector3(1.72, 1.5, 2.05),
    new THREE.Vector3(1.86, 0.62, 2.98),
  ]);
  const waterfallStream = new THREE.Mesh(
    new THREE.TubeGeometry(fallCurve, 28, 0.62, 12, false),
    waterfallMat
  );
  hydroGroup.add(waterfallStream);

  // 폭포 아래 물보라 연못 + 안개
  const splashPool = new THREE.Mesh(
    new THREE.CircleGeometry(2.5, 32),
    new THREE.MeshBasicMaterial({
      map: textures.foam,
      color: 0xbfefff,
      transparent: true,
      opacity: 0.55,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
  );
  splashPool.rotation.x = -Math.PI / 2;
  splashPool.position.set(1.9, 0.52, 3.05);
  hydroGroup.add(splashPool);

  const hydroMist = [];
  for (let m = 0; m < 3; m += 1) {
    const mist = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: textures.smoke,
        color: 0xd6f4ff,
        transparent: true,
        opacity: 0.16,
        depthWrite: false,
      })
    );
    mist.scale.set(4.2 + m, 3.2 + m, 1);
    mist.position.set(1.9 + (m - 1) * 0.8, 1.4 + m * 0.7, 2.95);
    hydroGroup.add(mist);
    hydroMist.push(mist);
  }

  // 대형 목재·황동 수차 바퀴
  const waterWheel = new THREE.Group();
  waterWheel.position.set(2.4, 3.4, 3.2);
  hydroGroup.add(waterWheel);

  const wheelWoodMat = new THREE.MeshStandardMaterial({ color: 0x8a5a34, map: textures.wood, roughness: 0.82 });
  const wheelWoodLightMat = new THREE.MeshStandardMaterial({ color: 0xb2803f, map: textures.wood, roughness: 0.78 });
  const wheelBrassMat = new THREE.MeshStandardMaterial({ color: 0xc9974a, metalness: 0.85, roughness: 0.28 });
  for (let side of [-0.75, 0.75]) {
    const rim = new THREE.Mesh(new THREE.TorusGeometry(2.9, 0.17, 10, 40), wheelWoodMat);
    rim.position.x = side;
    rim.rotation.y = Math.PI / 2;
    rim.castShadow = true;
    waterWheel.add(rim);
    // 안쪽 보강 테
    const innerRim = new THREE.Mesh(new THREE.TorusGeometry(2.15, 0.1, 8, 32), wheelWoodLightMat);
    innerRim.position.x = side;
    innerRim.rotation.y = Math.PI / 2;
    waterWheel.add(innerRim);
    // 바퀴살 8개
    for (let spoke = 0; spoke < 8; spoke += 1) {
      const spokeAngle = (spoke / 8) * TAU;
      const arm = new THREE.Mesh(new THREE.BoxGeometry(0.13, 2.85, 0.13), wheelWoodLightMat);
      arm.position.set(side, Math.cos(spokeAngle) * 1.42, Math.sin(spokeAngle) * 1.42);
      arm.rotation.x = -spokeAngle;
      waterWheel.add(arm);
    }
  }
  // 황동 중심축
  const wheelAxle = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.34, 2.2, 14), wheelBrassMat);
  wheelAxle.rotation.z = Math.PI / 2;
  waterWheel.add(wheelAxle);
  // 나무 물받이 버킷 10개 (바닥판 + 물막이판)
  for (let p = 0; p < 10; p += 1) {
    const bucketHolder = new THREE.Group();
    bucketHolder.rotation.x = (p / 10) * TAU;
    const boardMat = p % 2 === 0 ? wheelWoodLightMat : wheelWoodMat;
    const paddle = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.16, 1.0), boardMat);
    paddle.position.z = 2.82;
    paddle.castShadow = true;
    bucketHolder.add(paddle);
    const lip = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.52, 0.13), boardMat);
    lip.position.set(0, 0.26, 3.24);
    bucketHolder.add(lip);
    const brace = new THREE.Mesh(new THREE.BoxGeometry(1.36, 0.1, 0.1), wheelBrassMat);
    brace.position.set(0, -0.1, 2.36);
    bucketHolder.add(brace);
    waterWheel.add(bucketHolder);
  }

  const hydroHouse = new THREE.Group();
  hydroHouse.position.set(6.4, 0, 3.4);
  hydroGroup.add(hydroHouse);

  const houseStone = new THREE.Mesh(
    new THREE.BoxGeometry(3.9, 2.3, 3.5),
    new THREE.MeshStandardMaterial({ color: 0x93a1b8, map: textures.stone, roughness: 0.92 })
  );
  houseStone.position.y = 1.15;
  houseStone.castShadow = true;
  houseStone.receiveShadow = true;
  hydroHouse.add(houseStone);

  const houseTimber = new THREE.Mesh(
    new THREE.BoxGeometry(4.1, 1.35, 3.7),
    new THREE.MeshStandardMaterial({ color: 0x7a4f30, map: textures.wood, roughness: 0.86 })
  );
  houseTimber.position.y = 2.95;
  houseTimber.castShadow = true;
  hydroHouse.add(houseTimber);

  // 처마 + 박공지붕
  const houseRoof = new THREE.Mesh(
    new THREE.BoxGeometry(4.7, 0.24, 4.3),
    new THREE.MeshStandardMaterial({ color: 0x3f5470, roughness: 0.66 })
  );
  houseRoof.position.y = 3.72;
  houseRoof.castShadow = true;
  hydroHouse.add(houseRoof);
  for (let g = 0; g < 2; g += 1) {
    const gable = new THREE.Mesh(new THREE.BoxGeometry(4.55, 0.9, 0.2), wheelWoodMat);
    gable.position.set(0, 3.95, g === 0 ? -1.85 : 1.85);
    gable.rotation.x = (g === 0 ? 1 : -1) * 0.5;
    hydroHouse.add(gable);
  }

  // 따뜻한 창문 · 문 · 문 앞 계단
  const houseWindow = new THREE.Mesh(
    new THREE.PlaneGeometry(1.15, 0.92),
    new THREE.MeshStandardMaterial({
      map: textures.windowPane,
      color: 0xffd98a,
      emissive: 0xffb347,
      emissiveIntensity: 1.25,
      roughness: 0.3,
    })
  );
  houseWindow.position.set(-0.1, 3.0, 1.88);
  hydroHouse.add(houseWindow);
  const houseDoor = new THREE.Mesh(
    new THREE.BoxGeometry(0.95, 1.85, 0.12),
    new THREE.MeshStandardMaterial({ color: 0x4a3320, roughness: 0.8 })
  );
  houseDoor.position.set(1.05, 0.95, 1.78);
  hydroHouse.add(houseDoor);
  const houseStep = new THREE.Mesh(
    new THREE.BoxGeometry(1.5, 0.24, 0.7),
    new THREE.MeshStandardMaterial({ color: 0x8494ac, roughness: 0.9 })
  );
  houseStep.position.set(1.05, 0.12, 2.15);
  hydroHouse.add(houseStep);
  // 벽면 제어 밸브 (황동 핸들)
  const valveWheel = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.07, 8, 20), wheelBrassMat);
  valveWheel.position.set(-1.35, 2.15, 1.8);
  hydroHouse.add(valveWheel);
  for (let v = 0; v < 3; v += 1) {
    const valveSpoke = new THREE.Mesh(new THREE.BoxGeometry(0.78, 0.06, 0.06), wheelBrassMat);
    valveSpoke.position.copy(valveWheel.position);
    valveSpoke.rotation.z = (v / 3) * Math.PI;
    hydroHouse.add(valveSpoke);
  }
  // 지붕 위 굴뚝
  const houseChimney = new THREE.Mesh(
    new THREE.BoxGeometry(0.6, 1.1, 0.6),
    new THREE.MeshStandardMaterial({ color: 0x7b8698, map: textures.stone, roughness: 0.92 })
  );
  houseChimney.position.set(-1.2, 4.15, -0.8);
  houseChimney.castShadow = true;
  hydroHouse.add(houseChimney);

  const hydroBeaconMat = new THREE.MeshStandardMaterial({
    color: 0x8ce2ff,
    emissive: 0x38bdf8,
    emissiveIntensity: 0.5,
  });
  const hydroBeacon = new THREE.Mesh(new THREE.SphereGeometry(0.65, 16, 16), hydroBeaconMat);
  hydroBeacon.position.set(6.4, 4.85, 2.1);
  hydroGroup.add(hydroBeacon);
  const beaconPole = new THREE.Mesh(
    new THREE.CylinderGeometry(0.07, 0.07, 1.0, 8),
    new THREE.MeshStandardMaterial({ color: 0x3d4a60, metalness: 0.7, roughness: 0.4 })
  );
  beaconPole.position.set(6.4, 4.2, 2.1);
  hydroGroup.add(beaconPole);

  // 물방울 & 물보라 파티클 풀
  const hydroDropCount = 72;
  const hydroDropGeo = new THREE.BufferGeometry();
  const hydroDropPos = new Float32Array(hydroDropCount * 3);
  const hydroDropVel = new Float32Array(hydroDropCount * 3);
  for (let i = 0; i < hydroDropCount; i += 1) {
    hydroDropPos[i * 3] = -19.8 + ((i % 7) - 3) * 0.25;
    hydroDropPos[i * 3 + 1] = 2.5 + (i % 12) * 0.7;
    hydroDropPos[i * 3 + 2] = -15.4 + ((i % 5) - 2) * 0.25;
  }
  hydroDropGeo.setAttribute("position", new THREE.BufferAttribute(hydroDropPos, 3));
  const hydroDrops = new THREE.Points(
    hydroDropGeo,
    new THREE.PointsMaterial({
      size: 0.75,
      map: textures.glow,
      color: 0xbef0ff,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    })
  );
  scene.add(hydroDrops);

  const hydroHit = new THREE.Mesh(
    new THREE.BoxGeometry(12, 13, 10),
    new THREE.MeshBasicMaterial({ visible: false })
  );
  hydroHit.position.set(1.5, 5.5, 0);
  hydroGroup.add(hydroHit);
  registerHit(hydroHit, "hydro", "hydro");

  /* ── 8. 풍선 정전기 부두 (South-East Pier) ────────────────────── */

  const staticGroup = new THREE.Group();
  staticGroup.position.set(12.5, 2.6, 18.5);
  scene.add(staticGroup);

  // 폭신한 인디고 양모 구름 패드
  const woolPad = new THREE.Group();
  woolPad.position.set(-3.1, 0.55, -1.2);
  staticGroup.add(woolPad);
  const woolMat = new THREE.MeshStandardMaterial({
    color: 0x4f63b8,
    emissive: 0x263166,
    emissiveIntensity: 0.25,
    roughness: 0.95,
  });
  for (let w = 0; w < 6; w += 1) {
    const puff = new THREE.Mesh(new THREE.SphereGeometry(1.05, 14, 14), woolMat);
    const angle = (w / 6) * TAU;
    puff.position.set(Math.cos(angle) * 0.9, 0.2, Math.sin(angle) * 0.7);
    puff.castShadow = true;
    woolPad.add(puff);
  }
  const woolCenter = new THREE.Mesh(new THREE.SphereGeometry(1.25, 14, 14), woolMat);
  woolCenter.position.y = 0.45;
  woolPad.add(woolCenter);

  // 자이언트 광택 풍선 + 보랏빛 정전기 오라 + 드래그 히트박스
  const balloonPivot = new THREE.Group();
  balloonPivot.position.set(0.6, 3.8, 0.6);
  staticGroup.add(balloonPivot);

  const balloonMat = new THREE.MeshStandardMaterial({
    color: 0xff5c8a,
    emissive: 0x9d4edd,
    emissiveIntensity: 0.15,
    roughness: 0.14,
    metalness: 0.08,
  });
  const balloonBody = new THREE.Mesh(new THREE.SphereGeometry(1.65, 24, 24), balloonMat);
  balloonBody.scale.set(0.92, 1.14, 0.92);
  balloonBody.castShadow = true;
  balloonPivot.add(balloonBody);

  const balloonKnot = new THREE.Mesh(new THREE.ConeGeometry(0.28, 0.35, 10), balloonMat);
  balloonKnot.position.y = -1.92;
  balloonPivot.add(balloonKnot);

  // 고리 버들 바구니 + 매다는 줄 — 풍선이 공중에 떠 있는 물체로 읽히게 한다
  const basketMat = new THREE.MeshStandardMaterial({
    color: 0x8a6038,
    map: textures.wood,
    roughness: 0.86,
  });
  const basket = new THREE.Mesh(new THREE.CylinderGeometry(0.34, 0.28, 0.42, 12), basketMat);
  basket.position.y = -2.28;
  basket.castShadow = true;
  balloonPivot.add(basket);
  const basketRim = new THREE.Mesh(new THREE.TorusGeometry(0.35, 0.035, 6, 16), basketMat);
  basketRim.rotation.x = Math.PI / 2;
  basketRim.position.y = -2.06;
  balloonPivot.add(basketRim);
  const tetherMat = new THREE.LineBasicMaterial({
    color: 0xe4d6bd,
    transparent: true,
    opacity: 0.72,
  });
  for (let t = 0; t < 4; t += 1) {
    const a = (t / 4) * TAU + 0.4;
    const tetherGeo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(Math.cos(a) * 0.42, -1.62, Math.sin(a) * 0.42),
      new THREE.Vector3(Math.cos(a) * 0.3, -2.08, Math.sin(a) * 0.3),
    ]);
    balloonPivot.add(new THREE.Line(tetherGeo, tetherMat));
  }

  const balloonAura = makeGlowSprite(textures.glow, 0xc77dff, 4.4, 0.0);
  balloonPivot.add(balloonAura);

  const balloonHit = new THREE.Mesh(
    new THREE.SphereGeometry(3.2, 12, 12),
    new THREE.MeshBasicMaterial({ visible: false })
  );
  balloonPivot.add(balloonHit);
  registerHit(balloonHit, "static", "balloon");

  // 부두 위의 알록달록 3D 별·종이 조각 12개
  const confettiPalette = [0xffe066, 0x72efdd, 0xff99c8, 0xa9def9, 0xd7ff00];
  const paperBits = [];
  for (let i = 0; i < 12; i += 1) {
    const bitMesh = new THREE.Mesh(
      new THREE.OctahedronGeometry(0.34, 0),
      new THREE.MeshStandardMaterial({
        color: confettiPalette[i % confettiPalette.length],
        emissive: confettiPalette[i % confettiPalette.length],
        emissiveIntensity: 0.35,
        roughness: 0.4,
      })
    );
    bitMesh.scale.set(1.1, 0.28, 1.1);
    const homeX = 0.6 + ((i % 4) - 1.5) * 1.35;
    const homeZ = -2.2 + Math.floor(i / 4) * 2.1;
    bitMesh.position.set(homeX, 0.16, homeZ);
    staticGroup.add(bitMesh);
    paperBits.push({
      mesh: bitMesh,
      homeX,
      homeZ,
      stuck: false,
      orbitAngle: (i / 12) * TAU,
    });
  }

  // 부두 옆 나무 상자와 물통 — 빈 바닥을 채우고 생활감을 준다
  const crateMat = new THREE.MeshStandardMaterial({
    color: 0xb98b63,
    map: textures.wood,
    normalMap: textures.woodNormal,
    roughness: 0.88,
  });
  const crateSpecs = [
    [14.6, 2.9, 20.4, 0.9, 0.2],
    [15.6, 2.9, 21.2, 0.7, -0.4],
    [14.2, 3.5, 20.9, 0.6, 0.9],
  ];
  crateSpecs.forEach(([cx, cy, cz, cs, rot]) => {
    const crate = new THREE.Mesh(new THREE.BoxGeometry(cs, cs * 0.86, cs), crateMat);
    crate.position.set(cx, cy + cs * 0.43, cz);
    crate.rotation.y = rot;
    crate.castShadow = true;
    crate.receiveShadow = true;
    scene.add(crate);
  });
  const barrelMat = new THREE.MeshStandardMaterial({
    color: 0xa8764a,
    map: textures.wood,
    normalMap: textures.woodNormal,
    roughness: 0.85,
  });
  [[12.4, 2.85, 21.3], [11.6, 2.85, 20.6]].forEach(([bx, by, bz]) => {
    const barrel = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.95, 14), barrelMat);
    barrel.position.set(bx, by + 0.48, bz);
    barrel.castShadow = true;
    barrel.receiveShadow = true;
    scene.add(barrel);
    const hoop = new THREE.Mesh(
      new THREE.TorusGeometry(0.43, 0.035, 6, 16),
      new THREE.MeshStandardMaterial({ color: 0x6b7280, metalness: 0.7, roughness: 0.4 })
    );
    hoop.rotation.x = Math.PI / 2;
    hoop.position.set(bx, by + 0.72, bz);
    scene.add(hoop);
  });

  /* ── 9. 자이언트 과일 화학 전지 덱 (East Lab Deck) ────────────── */

  const fruitGroup = new THREE.Group();
  fruitGroup.position.set(24.8, 2.8, 13.5);
  scene.add(fruitGroup);

  const fruitCells3D = [];
  for (let i = 0; i < 8; i += 1) {
    const col = i % 4;
    const row = Math.floor(i / 4);
    const cellNode = new THREE.Group();
    cellNode.position.set(-4.2 + col * 2.55, 0, -2.1 + row * 3.1);
    fruitGroup.add(cellNode);

    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0xf6d828,
      roughness: 0.32,
      metalness: 0.05,
    });
    const body = new THREE.Mesh(new THREE.SphereGeometry(0.92, 18, 18), bodyMat);
    body.scale.set(1.14, 0.86, 0.92);
    body.position.y = 0.82;
    body.castShadow = true;
    cellNode.add(body);

    const znPlate = new THREE.Mesh(
      new THREE.BoxGeometry(0.14, 1.15, 0.52),
      new THREE.MeshStandardMaterial({ color: 0xcbd5e1, metalness: 0.85, roughness: 0.2 })
    );
    znPlate.position.set(-0.42, 1.45, 0);
    cellNode.add(znPlate);

    const cuPlate = new THREE.Mesh(new THREE.BoxGeometry(0.14, 1.15, 0.52), copperMat);
    cuPlate.position.set(0.42, 1.45, 0);
    cellNode.add(cuPlate);

    cellNode.visible = i === 0;
    fruitCells3D.push({ group: cellNode, body, bodyMat });
  }

  // 과일 전지로 켜지는 초대형 루비 크리스탈 LED 등대 비컨
  const fruitLedPedestal = new THREE.Mesh(
    new THREE.CylinderGeometry(1.1, 1.35, 1.2, 16),
    darkMetalMat
  );
  fruitLedPedestal.position.set(5.1, 0.6, 0);
  fruitGroup.add(fruitLedPedestal);

  const fruitLedMat = new THREE.MeshStandardMaterial({
    color: 0xff4d6d,
    emissive: 0xff2a55,
    emissiveIntensity: 0.05,
    transparent: true,
    opacity: 0.88,
    roughness: 0.12,
  });
  const fruitLedDome = new THREE.Mesh(
    new THREE.CapsuleGeometry(0.88, 1.1, 12, 20),
    fruitLedMat
  );
  fruitLedDome.position.set(5.1, 2.15, 0);
  fruitGroup.add(fruitLedDome);
  const fruitLedHalo = makeGlowSprite(textures.glow, 0xff4d6d, 4.0, 0.0);
  fruitLedHalo.position.copy(fruitLedDome.position);
  fruitGroup.add(fruitLedHalo);

  const fruitHit = new THREE.Mesh(
    new THREE.BoxGeometry(13.2, 5.2, 9.8),
    new THREE.MeshBasicMaterial({ visible: false })
  );
  fruitHit.position.set(0, 2.2, 0);
  fruitGroup.add(fruitHit);
  registerHit(fruitHit, "fruit", "fruit");

  /* ── 10. 밤섬 마을 · 가로등 · 등대 · 기차 · 분수 · 대관람차 ────── */

  const villageGroup = new THREE.Group();
  scene.add(villageGroup);

  const cottageWindows = [];
  const streetLampBulbs = [];
  const streetLampHalos = [];

  // 6채의 아기자기한 유럽풍 3D 오두막 — 박공지붕·창틀·문·굴뚝 연기
  const houseSpecs = [
    { x: 13.5, z: -3.5, w: 3.1, h: 2.6, d: 2.8, roof: 0xd9574f, wall: 0xe8e2d4, trim: 0x4a3b30, rot: 0.25 },
    { x: 16.5, z: -11.5, w: 3.4, h: 3.2, d: 3.0, roof: 0x3b7ddd, wall: 0xf0e6d3, trim: 0x3a2f28, rot: -0.35 },
    { x: 24.5, z: -3.2, w: 3.0, h: 2.5, d: 2.7, roof: 0xe4a72b, wall: 0xe4dccb, trim: 0x453a2e, rot: -0.6 },
    { x: 26.8, z: -10.8, w: 3.5, h: 3.6, d: 3.1, roof: 0xdd5f9d, wall: 0xeee2d2, trim: 0x3f3128, rot: -1.1 },
    { x: 12.2, z: -10.2, w: 2.8, h: 2.4, d: 2.6, roof: 0x25a97a, wall: 0xece3d2, trim: 0x453728, rot: 0.65 },
    { x: 20.5, z: 1.4, w: 3.6, h: 2.8, d: 2.9, roof: 0xe8783a, wall: 0xe6dcc8, trim: 0x4a3a2c, rot: 2.8 },
  ];

  const planterBloomMats = [0xff8fb3, 0xffd166, 0xc084fc].map(
    (hex) =>
      new THREE.MeshStandardMaterial({
        color: hex,
        emissive: hex,
        emissiveIntensity: 0.16,
        roughness: 0.62,
      })
  );
  const planterLeafMat = new THREE.MeshStandardMaterial({ color: 0x3f9b6c, roughness: 0.85 });

  const roofTileMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    map: textures.roof,
    roughness: 0.72,
    metalness: 0.04,
  });
  const smokePuffs = [];
  const porchLights = [];

  houseSpecs.forEach((hs, houseIndex) => {
    const house = new THREE.Group();
    house.position.set(hs.x, 2.8, hs.z);
    house.rotation.y = hs.rot;
    villageGroup.add(house);
    addContactShadow(hs.x, hs.z, Math.max(hs.w, hs.d) * 0.85, { y: 2.8, strength: 1 });

    // 석조 주춧돌
    const plinth = new THREE.Mesh(
      new THREE.BoxGeometry(hs.w + 0.42, 0.34, hs.d + 0.42),
      new THREE.MeshStandardMaterial({ color: 0x8c8f99, map: textures.stone, roughness: 0.94 })
    );
    plinth.position.y = 0.17;
    plinth.receiveShadow = true;
    plinth.castShadow = true;
    house.add(plinth);

    // 회벽 본체
    const wall = new THREE.Mesh(
      new THREE.BoxGeometry(hs.w, hs.h, hs.d),
      new THREE.MeshStandardMaterial({ color: hs.wall, roughness: 0.88 })
    );
    wall.position.y = hs.h * 0.5 + 0.3;
    wall.castShadow = true;
    wall.receiveShadow = true;
    house.add(wall);

    // 모서리 목재 기둥 — 목가적인 하프팀버 느낌
    const trimMat = new THREE.MeshStandardMaterial({ color: hs.trim, roughness: 0.82 });
    [
      [-1, -1],
      [1, -1],
      [-1, 1],
      [1, 1],
    ].forEach(([sx, sz]) => {
      const post = new THREE.Mesh(new THREE.BoxGeometry(0.16, hs.h, 0.16), trimMat);
      post.position.set((sx * hs.w) / 2, hs.h * 0.5 + 0.3, (sz * hs.d) / 2);
      house.add(post);
    });
    const band = new THREE.Mesh(new THREE.BoxGeometry(hs.w + 0.08, 0.14, hs.d + 0.08), trimMat);
    band.position.y = 0.34;
    house.add(band);

    // 박공지붕 — 용마루는 긴 축, 물매는 짧은 축
    const across = Math.min(hs.w, hs.d);
    const along = Math.max(hs.w, hs.d);
    const wallTop = hs.h + 0.3;
    const roofHeight = hs.h * 0.58;
    const roofGroup = new THREE.Group();
    roofGroup.position.y = wallTop;
    if (hs.d > hs.w) roofGroup.rotation.y = Math.PI / 2;
    house.add(roofGroup);

    const roofMat = roofTileMat.clone();
    roofMat.color.setHex(hs.roof);
    const roofMesh = new THREE.Mesh(gableRoofGeometry(across, along, roofHeight, 0.34), roofMat);
    roofMesh.castShadow = true;
    roofMesh.receiveShadow = true;
    roofGroup.add(roofMesh);

    // 박공벽 (지붕 아래 삼각 부분) — 양쪽 끝을 막아 구멍이 보이지 않게
    const gableMat = new THREE.MeshStandardMaterial({
      color: hs.wall,
      roughness: 0.9,
      side: THREE.DoubleSide,
    });
    [-1, 1].forEach((dir) => {
      const end = new THREE.Mesh(gableEndGeometry(across, roofHeight, 0.62), gableMat);
      end.position.set(dir * (along * 0.5 + 0.18), 0, 0);
      end.rotation.y = Math.PI / 2;
      roofGroup.add(end);
    });

    // 용마루 기와
    const ridge = new THREE.Mesh(
      new THREE.BoxGeometry(along + 0.5, 0.15, 0.2),
      new THREE.MeshStandardMaterial({ color: hs.trim, roughness: 0.7 })
    );
    ridge.position.y = roofHeight + 0.03;
    roofGroup.add(ridge);

    // 굴뚝 + 연기
    const chimney = new THREE.Mesh(
      new THREE.BoxGeometry(0.44, 1.1, 0.44),
      new THREE.MeshStandardMaterial({ color: 0x8a7461, roughness: 0.92 })
    );
    chimney.position.set(hs.w * 0.24, wallTop + roofHeight * 0.55, -hs.d * 0.16);
    chimney.castShadow = true;
    house.add(chimney);

    const smokeMat = new THREE.SpriteMaterial({
      map: textures.smoke,
      color: 0xc9d6e8,
      transparent: true,
      opacity: 0,
      depthWrite: false,
    });
    for (let s = 0; s < 3; s += 1) {
      const puff = new THREE.Sprite(smokeMat.clone());
      puff.scale.set(0.85, 0.85, 1);
      puff.position.set(chimney.position.x, chimney.position.y + 0.7 + s * 0.55, chimney.position.z);
      house.add(puff);
      smokePuffs.push({ sprite: puff, baseY: puff.position.y, phase: houseIndex * 1.3 + s * 0.7 });
    }

    // 창문 (앞·뒤·측면) + 창틀
    const winMat = new THREE.MeshStandardMaterial({
      color: 0x2a3448,
      map: textures.windowPane,
      emissive: 0xffbe42,
      emissiveMap: textures.windowPane,
      emissiveIntensity: 0,
      roughness: 0.22,
      metalness: 0.1,
    });
    const addWindow = (x, y, z, rotY, wdt = 0.74, hgt = 0.8) => {
      const frame = new THREE.Mesh(
        new THREE.BoxGeometry(wdt + 0.16, hgt + 0.16, 0.08),
        new THREE.MeshStandardMaterial({ color: hs.trim, roughness: 0.8 })
      );
      const pane = new THREE.Mesh(new THREE.PlaneGeometry(wdt, hgt), winMat);
      const holder = new THREE.Group();
      holder.position.set(x, y, z);
      holder.rotation.y = rotY;
      frame.position.z = 0.01;
      pane.position.z = 0.06;
      holder.add(frame);
      holder.add(pane);
      // 창가 화분 — 벽면에 작은 색 포인트를 얹어 오두막이 살아 있게 보이게 한다
      const planter = new THREE.Mesh(
        new THREE.BoxGeometry(wdt + 0.24, 0.16, 0.24),
        new THREE.MeshStandardMaterial({ color: 0x6f4b31, map: textures.wood, roughness: 0.9 })
      );
      planter.position.set(0, -hgt * 0.5 - 0.16, 0.16);
      planter.castShadow = true;
      holder.add(planter);
      for (let b = 0; b < 4; b += 1) {
        const bloom = new THREE.Mesh(
          new THREE.SphereGeometry(0.075, 6, 6),
          planterBloomMats[b % planterBloomMats.length]
        );
        bloom.position.set(
          -wdt * 0.34 + b * (wdt * 0.23),
          -hgt * 0.5 - 0.07,
          0.16 + (b % 2 === 0 ? 0.03 : -0.03)
        );
        holder.add(bloom);
        const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.09, 6, 6), planterLeafMat);
        leaf.scale.set(1.4, 0.7, 1);
        leaf.position.set(bloom.position.x + 0.05, bloom.position.y - 0.03, bloom.position.z);
        holder.add(leaf);
      }
      house.add(holder);
      return holder;
    };
    const frontZ = hs.d * 0.5 + 0.02;
    addWindow(-hs.w * 0.26, hs.h * 0.66, frontZ, 0);
    addWindow(hs.w * 0.26, hs.h * 0.66, frontZ, 0);
    addWindow(-hs.w * 0.26, hs.h * 0.66, -frontZ, Math.PI);
    addWindow(hs.w * 0.5 + 0.02, hs.h * 0.66, 0, Math.PI / 2, 0.62, 0.74);

    // 현관문 + 문 위 등불
    const doorMat = new THREE.MeshStandardMaterial({ color: 0x5a3b28, roughness: 0.72 });
    const door = new THREE.Mesh(new THREE.BoxGeometry(0.86, 1.6, 0.12), doorMat);
    door.position.set(hs.w * 0.02, 1.1, frontZ + 0.02);
    house.add(door);
    const knob = new THREE.Mesh(
      new THREE.SphereGeometry(0.06, 8, 8),
      new THREE.MeshStandardMaterial({ color: 0xffd77a, metalness: 0.9, roughness: 0.22 })
    );
    knob.position.set(hs.w * 0.02 + 0.3, 1.08, frontZ + 0.1);
    house.add(knob);
    const canopy = new THREE.Mesh(new THREE.BoxGeometry(1.15, 0.1, 0.5), trimMat);
    canopy.position.set(hs.w * 0.02, 2.0, frontZ + 0.24);
    canopy.rotation.x = 0.18;

    house.add(canopy);

    const porchMat = new THREE.MeshStandardMaterial({
      color: 0xffd7a0,
      emissive: 0xffb15c,
      emissiveIntensity: 0,
      roughness: 0.3,
    });
    const porch = new THREE.Mesh(new THREE.SphereGeometry(0.12, 10, 10), porchMat);
    porch.position.set(hs.w * 0.02, 1.86, frontZ + 0.14);
    house.add(porch);
    const porchHalo = makeGlowSprite(textures.glow, 0xffc06a, 1.7, 0);
    porchHalo.position.copy(porch.position);
    house.add(porchHalo);
    porchLights.push({ porchMat, halo: porchHalo.material });

    // 창가 꽃상자
    const flowerMat = new THREE.MeshStandardMaterial({ color: 0xe86a8d, roughness: 0.85 });
    const leafMat = new THREE.MeshStandardMaterial({ color: 0x3f9d63, roughness: 0.9 });
    [-1, 1].forEach((side) => {
      const box = new THREE.Mesh(
        new THREE.BoxGeometry(0.84, 0.2, 0.22),
        new THREE.MeshStandardMaterial({ color: 0x6b4a30, roughness: 0.9 })
      );
      box.position.set(side * hs.w * 0.26, hs.h * 0.66 - 0.5, frontZ + 0.1);
      house.add(box);
      for (let f = 0; f < 3; f += 1) {
        const bloom = new THREE.Mesh(new THREE.SphereGeometry(0.08, 6, 6), flowerMat);
        bloom.position.set(side * hs.w * 0.26 - 0.26 + f * 0.26, hs.h * 0.66 - 0.37, frontZ + 0.12);
        house.add(bloom);
        const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.09, 6, 6), leafMat);
        leaf.position.set(side * hs.w * 0.26 - 0.3 + f * 0.3, hs.h * 0.66 - 0.46, frontZ + 0.08);
        leaf.scale.set(1.2, 0.6, 0.8);
        house.add(leaf);
      }
    });

    cottageWindows.push(winMat);
  });

  // 마을 길 8개의 주철 가로등 — 받침·기둥·랜턴 케이지까지
  const lampCoords = [
    [10.2, -1.2],
    [13.8, 0.8],
    [16.8, -5.8],
    [22.2, -5.6],
    [23.2, -12.8],
    [16.4, -14.2],
    [28.5, -6.5],
    [30.5, -3.5],
  ];
  const lampIronMat = new THREE.MeshStandardMaterial({
    color: 0x1f2734,
    metalness: 0.72,
    roughness: 0.42,
  });
  lampCoords.forEach(([lx, lz]) => {
    const base = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.34, 0.32, 10), lampIronMat);
    base.position.set(lx, 2.98, lz);

    villageGroup.add(base);

    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.13, 2.7, 10), lampIronMat);
    post.position.set(lx, 4.4, lz);

    villageGroup.add(post);

    const collar = new THREE.Mesh(new THREE.TorusGeometry(0.12, 0.035, 6, 12), lampIronMat);
    collar.rotation.x = Math.PI / 2;
    collar.position.set(lx, 5.5, lz);
    villageGroup.add(collar);

    const globeMat = new THREE.MeshStandardMaterial({
      color: 0x39424f,
      emissive: 0xffd166,
      emissiveIntensity: 0,
      roughness: 0.18,
      metalness: 0.2,
    });
    const globe = new THREE.Mesh(new THREE.SphereGeometry(0.3, 16, 14), globeMat);
    globe.position.set(lx, 5.86, lz);
    villageGroup.add(globe);
    streetLampBulbs.push(globeMat);

    const cap = new THREE.Mesh(new THREE.ConeGeometry(0.34, 0.26, 10), lampIronMat);
    cap.position.set(lx, 6.13, lz);
    villageGroup.add(cap);

    const halo = makeGlowSprite(textures.glow, 0xffca58, 3.4, 0);
    halo.position.copy(globe.position);
    villageGroup.add(halo);
    streetLampHalos.push(halo);
  });

  // 곶 위의 줄무늬 회전 등대 (Tier 2: harbor)
  const lighthouseGroup = new THREE.Group();
  lighthouseGroup.position.set(33.2, 2.3, -4.5);
  addContactShadow(33.2, -4.5, 3.2, { y: 2.3, strength: 0.9 });
  villageGroup.add(lighthouseGroup);

  for (let seg = 0; seg < 5; seg += 1) {
    const rBot = 1.45 - seg * 0.14;
    const rTop = 1.31 - seg * 0.14;
    const band = new THREE.Mesh(
      new THREE.CylinderGeometry(rTop, rBot, 2.1, 16),
      new THREE.MeshStandardMaterial({
        color: seg % 2 === 0 ? 0xf8fafc : 0xef4444,
        roughness: 0.65,
      })
    );
    band.position.y = 1.05 + seg * 2.1;
    band.castShadow = true;
    lighthouseGroup.add(band);
  }

  // 석조 기단 · 등대지기 문 · 갤러리 난간
  const lighthouseBase = new THREE.Mesh(
    new THREE.CylinderGeometry(2.15, 2.4, 0.6, 18),
    new THREE.MeshStandardMaterial({ color: 0x9aa3b3, map: textures.stone, roughness: 0.92 })
  );
  lighthouseBase.position.y = 0.3;
  lighthouseBase.receiveShadow = true;
  lighthouseBase.castShadow = true;
  lighthouseGroup.add(lighthouseBase);

  const lighthouseDoor = new THREE.Mesh(
    new THREE.BoxGeometry(0.62, 1.35, 0.16),
    new THREE.MeshStandardMaterial({ color: 0x3c5a72, roughness: 0.7 })
  );
  lighthouseDoor.position.set(0, 1.3, 1.28);
  lighthouseGroup.add(lighthouseDoor);

  const gallery = new THREE.Mesh(
    new THREE.CylinderGeometry(1.55, 1.55, 0.16, 20),
    new THREE.MeshStandardMaterial({ color: 0x2b3444, metalness: 0.6, roughness: 0.45 })
  );
  gallery.position.y = 10.9;

  lighthouseGroup.add(gallery);
  for (let r = 0; r < 14; r += 1) {
    const a = (r / 14) * TAU;
    const post = new THREE.Mesh(
      new THREE.CylinderGeometry(0.03, 0.03, 0.75, 5),
      new THREE.MeshStandardMaterial({ color: 0x2b3444, metalness: 0.7, roughness: 0.4 })
    );
    post.position.set(Math.cos(a) * 1.5, 11.3, Math.sin(a) * 1.5);
    lighthouseGroup.add(post);
  }
  const railRing = new THREE.Mesh(
    new THREE.TorusGeometry(1.5, 0.035, 6, 30),
    new THREE.MeshStandardMaterial({ color: 0x2b3444, metalness: 0.7, roughness: 0.4 })
  );
  railRing.rotation.x = Math.PI / 2;
  railRing.position.y = 11.66;
  lighthouseGroup.add(railRing);

  const lanternHead = new THREE.Group();
  lanternHead.position.y = 11.4;
  lighthouseGroup.add(lanternHead);

  const lanternCoreMat = new THREE.MeshStandardMaterial({
    color: 0xfef3c7,
    emissive: 0xffe066,
    emissiveIntensity: 0,
    roughness: 0.2,
  });
  const lanternCore = new THREE.Mesh(new THREE.CylinderGeometry(0.68, 0.68, 1.3, 14), lanternCoreMat);
  lanternHead.add(lanternCore);

  const lanternGlassMat = new THREE.MeshStandardMaterial({
    color: 0xfff4cc,
    emissive: 0xffd166,
    emissiveIntensity: 0,
    transparent: true,
    opacity: 0.34,
    roughness: 0.08,
    metalness: 0.1,
    side: THREE.DoubleSide,
  });
  const lanternGlass = new THREE.Mesh(new THREE.CylinderGeometry(0.92, 0.92, 1.7, 16, 1, true), lanternGlassMat);
  lanternHead.add(lanternGlass);
  const lanternHalo = makeGlowSprite(textures.glow, 0xffe08a, 4.6, 0);
  lanternHalo.position.y = 0.1;
  lanternHead.add(lanternHalo);
  for (let b = 0; b < 8; b += 1) {
    const a = (b / 8) * TAU;
    const bar = new THREE.Mesh(
      new THREE.BoxGeometry(0.05, 1.7, 0.05),
      new THREE.MeshStandardMaterial({ color: 0x2b3444, metalness: 0.7, roughness: 0.4 })
    );
    bar.position.set(Math.cos(a) * 0.9, 0, Math.sin(a) * 0.9);
    lanternHead.add(bar);
  }

  const searchBeamMat = makeBeamMaterial({
    color: 0xfff0a8,
    opacity: 0,
    noise: textures.noise,
    fade: 1.25,
    softness: 2.4,
    speed: 0.14,
  });
  const searchBeam = new THREE.Mesh(
    new THREE.ConeGeometry(4.6, 26, 28, 1, true),
    searchBeamMat
  );
  searchBeam.rotation.x = Math.PI / 2;
  searchBeam.position.set(0, -0.3, 12.2);
  lanternHead.add(searchBeam);

  const lighthouseCap = new THREE.Mesh(
    new THREE.ConeGeometry(1.1, 1.3, 16),
    new THREE.MeshStandardMaterial({ color: 0xdc2626, roughness: 0.5 })
  );
  lighthouseCap.position.y = 12.6;
  lighthouseGroup.add(lighthouseCap);

  // 타원형 3D 철도 트랙 & 3량 꼬마 전기 기차 (Tier 3: train)
  const trackCenter = { x: 20.5, z: -7.5, rx: 12.4, rz: 10.4, y: 2.86 };
  const trackPoints = [];
  for (let i = 0; i < 48; i += 1) {
    const a = (i / 48) * TAU;
    trackPoints.push(
      new THREE.Vector3(
        trackCenter.x + Math.cos(a) * trackCenter.rx,
        trackCenter.y,
        trackCenter.z + Math.sin(a) * trackCenter.rz
      )
    );
  }
  const railCurve = new THREE.CatmullRomCurve3(trackPoints, true);
  const railTube = new THREE.Mesh(
    new THREE.TubeGeometry(railCurve, 96, 0.16, 6, true),
    chromeMat
  );
  villageGroup.add(railTube);

  const trainCars = [];
  const trainCarColors = [0xd7ff00, 0x38bdf8, 0xf472b6];
  const trainWinMat = new THREE.MeshStandardMaterial({
    color: 0x334155,
    emissive: 0xffe066,
    emissiveIntensity: 0,
  });
  for (let c = 0; c < 3; c += 1) {
    const car = new THREE.Group();
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(1.25, 1.05, 2.2),
      new THREE.MeshStandardMaterial({
        color: trainCarColors[c],
        roughness: 0.32,
        metalness: 0.25,
      })
    );
    body.position.y = 0.68;
    body.castShadow = true;
    car.add(body);

    const winBand = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.38, 1.65), trainWinMat);
    winBand.position.y = 0.78;
    car.add(winBand);

    // 지붕 · 하부 차대 · 바퀴 · 연결기
    const roofCap = new THREE.Mesh(
      new THREE.BoxGeometry(1.24, 0.14, 2.16),
      new THREE.MeshStandardMaterial({ color: 0x2b3444, metalness: 0.5, roughness: 0.45 })
    );
    roofCap.position.y = 1.25;
    car.add(roofCap);

    const chassis = new THREE.Mesh(
      new THREE.BoxGeometry(1.1, 0.22, 2.0),
      new THREE.MeshStandardMaterial({ color: 0x1b2431, metalness: 0.6, roughness: 0.5 })
    );
    chassis.position.y = 0.18;
    car.add(chassis);

    const wheelMat = new THREE.MeshStandardMaterial({ color: 0x9aa6b8, metalness: 0.8, roughness: 0.3 });
    [-0.62, 0.62].forEach((wz) => {
      [-0.58, 0.58].forEach((wx) => {
        const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.24, 0.12, 12), wheelMat);
        wheel.rotation.z = Math.PI / 2;
        wheel.position.set(wx, 0.28, wz);
        car.add(wheel);
      });
    });

    if (c === 0) {
      const stack = new THREE.Mesh(
        new THREE.CylinderGeometry(0.16, 0.22, 0.55, 10),
        new THREE.MeshStandardMaterial({ color: 0x1b2431, metalness: 0.7, roughness: 0.4 })
      );
      stack.position.set(0, 1.55, 0.75);
      car.add(stack);
      const trainSmoke = [];
      for (let p = 0; p < 3; p += 1) {
        const puff = new THREE.Sprite(
          new THREE.SpriteMaterial({
            map: textures.smoke,
            color: 0xd7e2f0,
            transparent: true,
            opacity: 0,
            depthWrite: false,
          })
        );
        puff.scale.set(0.7, 0.7, 1);
        puff.position.set(0, 1.9 + p * 0.35, 0.75 + p * 0.3);
        car.add(puff);
        trainSmoke.push(puff);
      }
      car.userData.smoke = trainSmoke;

      const lamp = new THREE.Mesh(
        new THREE.SphereGeometry(0.16, 10, 10),
        new THREE.MeshStandardMaterial({
          color: 0xfff6c8,
          emissive: 0xffe066,
          emissiveIntensity: 1.6,
        })
      );
      lamp.position.set(0, 0.62, -1.15);
      car.add(lamp);
      const lampHalo = makeGlowSprite(textures.glow, 0xffe27a, 2.2, 0);
      lampHalo.position.copy(lamp.position);
      car.add(lampHalo);
      car.userData.lampHalo = lampHalo;

      const headlight = new THREE.Mesh(
        new THREE.ConeGeometry(1.5, 6.0, 20, 1, true),
        makeBeamMaterial({
          color: 0xfff3a3,
          opacity: 0,
          noise: textures.noise,
          fade: 1.1,
          softness: 2.2,
          speed: 0.2,
        })
      );
      headlight.rotation.x = -Math.PI / 2;
      headlight.position.set(0, 0.62, 3.6);
      car.add(headlight);
      car.userData.headlight = headlight;
    }

    villageGroup.add(car);
    trainCars.push(car);
  }

  // 밤하늘 네온 대관람차 (Tier 4: ferris)
  const ferrisGroup = new THREE.Group();
  ferrisGroup.position.set(22.5, 2.8, -19.2);
  addContactShadow(22.5, -19.2, 7.4, { y: 2.8, strength: 0.7 });
  villageGroup.add(ferrisGroup);

  const ferrisHubY = 10.6;
  const ferrisRadius = 8.2;
  for (let side of [-1.4, 1.4]) {
    for (let legDir of [-1, 1]) {
      const leg = new THREE.Mesh(
        new THREE.CylinderGeometry(0.18, 0.28, 11.8, 8),
        chromeMat
      );
      leg.position.set(side, 5.4, legDir * 2.5);
      leg.rotation.x = legDir * -0.23;
      ferrisGroup.add(leg);
    }
  }

  // A자 지지대 보강 + 허브 축
  for (let side of [-1.4, 1.4]) {
    const brace = new THREE.Mesh(
      new THREE.CylinderGeometry(0.07, 0.09, 9.4, 6),
      chromeMat
    );
    brace.position.set(side, 5.2, 0);
    brace.rotation.x = Math.PI / 2;
    ferrisGroup.add(brace);
  }
  const ferrisHub = new THREE.Mesh(
    new THREE.CylinderGeometry(0.62, 0.62, 3.4, 18),
    new THREE.MeshStandardMaterial({ color: 0x8fa2bb, metalness: 0.85, roughness: 0.24 })
  );
  ferrisHub.rotation.x = Math.PI / 2;
  ferrisHub.position.y = ferrisHubY;
  ferrisHub.castShadow = true;
  ferrisGroup.add(ferrisHub);

  const ferrisWheel = new THREE.Group();
  ferrisWheel.position.y = ferrisHubY;
  ferrisGroup.add(ferrisWheel);

  // 림 네온 발광 스프라이트 (회전에 함께 따라간다)
  const ferrisBulbs = [];
  for (let b = 0; b < 16; b += 1) {
    const a = (b / 16) * TAU;
    const bulb = makeGlowSprite(textures.glow, b % 2 === 0 ? 0xd7ff00 : 0x60e8ff, 1.5, 0);
    bulb.position.set(Math.cos(a) * ferrisRadius, Math.sin(a) * ferrisRadius, 0.7);
    ferrisWheel.add(bulb);
    ferrisBulbs.push(bulb);
  }

  const ferrisNeonMat = new THREE.MeshStandardMaterial({
    color: 0x64748b,
    emissive: 0xd7ff00,
    emissiveIntensity: 0,
    roughness: 0.2,
  });
  const ferrisInnerMat = new THREE.MeshStandardMaterial({
    color: 0x64748b,
    emissive: 0x38bdf8,
    emissiveIntensity: 0,
    roughness: 0.2,
  });

  for (let zOff of [-0.65, 0.65]) {
    const outerRim = new THREE.Mesh(
      new THREE.TorusGeometry(ferrisRadius, 0.14, 10, 48),
      ferrisNeonMat
    );
    outerRim.position.z = zOff;
    ferrisWheel.add(outerRim);

    const innerRim = new THREE.Mesh(
      new THREE.TorusGeometry(ferrisRadius * 0.56, 0.09, 8, 36),
      ferrisInnerMat
    );
    innerRim.position.z = zOff;
    ferrisWheel.add(innerRim);
  }

  for (let sp = 0; sp < 12; sp += 1) {
    const spoke = new THREE.Mesh(
      new THREE.CylinderGeometry(0.06, 0.06, ferrisRadius * 2, 6),
      ferrisInnerMat
    );
    spoke.rotation.z = (sp / 12) * Math.PI;
    ferrisWheel.add(spoke);
  }

  const gondolas = [];
  const gondolaPalette = [0xff5c8a, 0x38bdf8, 0xd7ff00, 0xc084fc];
  for (let g = 0; g < 8; g += 1) {
    const angle = (g / 8) * TAU;
    const pivot = new THREE.Group();
    pivot.position.set(Math.cos(angle) * ferrisRadius, Math.sin(angle) * ferrisRadius, 0);
    const cabinMat = new THREE.MeshStandardMaterial({
      color: gondolaPalette[g % gondolaPalette.length],
      emissive: gondolaPalette[g % gondolaPalette.length],
      emissiveIntensity: 0,
      roughness: 0.25,
    });
    const cabin = new THREE.Mesh(new THREE.SphereGeometry(0.78, 14, 14), cabinMat);
    cabin.position.y = -0.68;
    pivot.add(cabin);
    ferrisWheel.add(pivot);
    gondolas.push({ pivot, cabinMat });
  }

  // 무지개 분수 광장 (Tier 5: fountain)
  const fountainGroup = new THREE.Group();
  fountainGroup.position.set(19.6, 2.8, -6.8);
  villageGroup.add(fountainGroup);

  const fountainBasin = new THREE.Mesh(
    new THREE.CylinderGeometry(2.5, 2.8, 0.7, 20),
    new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.65 })
  );
  fountainBasin.position.y = 0.35;
  fountainGroup.add(fountainBasin);

  const fountainPool = new THREE.Mesh(
    new THREE.CylinderGeometry(2.2, 2.2, 0.2, 20),
    new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      emissive: 0x22d3ee,
      emissiveIntensity: 0.2,
      roughness: 0.1,
    })
  );
  fountainPool.position.y = 0.65;
  fountainGroup.add(fountainPool);

  const fountainJets = [];
  for (let j = 0; j < 6; j += 1) {
    const jetMat = new THREE.MeshBasicMaterial({
      color: j % 2 === 0 ? 0x67e8f9 : 0xf472b6,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const jet = new THREE.Mesh(new THREE.ConeGeometry(0.32, 4.5, 10), jetMat);
    const a = (j / 6) * TAU;
    jet.position.set(Math.cos(a) * 0.9, 2.5, Math.sin(a) * 0.9);
    jet.rotation.z = -Math.cos(a) * 0.16;
    jet.rotation.x = Math.sin(a) * 0.16;
    fountainGroup.add(jet);
    fountainJets.push({ jet, jetMat });
  }

  const villageHit = new THREE.Mesh(
    new THREE.BoxGeometry(24, 18, 24),
    new THREE.MeshBasicMaterial({ visible: false })
  );
  villageHit.position.set(21, 9, -8);
  scene.add(villageHit);
  registerHit(villageHit, "village", "village");

  /* ── 11. 송전선 네트워크 & 실시간 플라스마 전류 구체 ──────────── */

  const powerLines = [
    {
      id: "generator",
      color: 0xffbe3b,
      points: [
        [-1, 5.8, 14.5],
        [-0.8, 7.6, 8.2],
        [-0.5, 6.2, 2.2],
      ],
    },
    {
      id: "wind",
      color: 0x5cf2c2,
      points: [
        [-27.5, 16.2, 3.5],
        [-15.0, 12.2, 1.5],
        [-4.2, 6.8, -0.5],
      ],
    },
    {
      id: "solar",
      color: 0xffd85c,
      points: [
        [-14.5, 4.8, 15.5],
        [-8.0, 6.8, 8.0],
        [-2.8, 5.8, 1.8],
      ],
    },
    {
      id: "hydro",
      color: 0x6bc6ff,
      points: [
        [-15.0, 5.8, -12.8],
        [-8.2, 7.4, -7.0],
        [-2.2, 6.4, -2.0],
      ],
    },
    {
      id: "fruit",
      color: 0x7ef07e,
      points: [
        [24.8, 4.6, 13.5],
        [13.5, 6.5, 7.2],
        [2.2, 5.6, 1.6],
      ],
    },
    {
      id: "townMain",
      color: 0xd7ff00,
      points: [
        [2.2, 6.2, 0.2],
        [9.8, 8.6, -2.8],
        [17.5, 7.2, -5.8],
      ],
    },
    {
      id: "townPark",
      color: 0xe879f9,
      points: [
        [17.5, 7.2, -5.8],
        [20.5, 9.6, -12.5],
        [22.5, 11.2, -18.5],
      ],
    },
  ];

  // 송전선을 받쳐 주는 가느다란 철제 전신주 (허공에 뜬 전선처럼 보이지 않도록)
  const pylonSteelMat = new THREE.MeshStandardMaterial({
    color: 0x4a566b,
    metalness: 0.7,
    roughness: 0.42,
  });
  const insulatorMat = new THREE.MeshStandardMaterial({
    color: 0xdfe8f5,
    roughness: 0.3,
    metalness: 0.2,
  });
  function addPylon(x, y, z, colorHex) {
    const groundY = 2.42;
    const height = Math.max(2.4, y - groundY);
    const pole = new THREE.Mesh(
      new THREE.CylinderGeometry(0.11, 0.2, height, 8),
      pylonSteelMat
    );
    pole.position.set(x, groundY + height / 2, z);
    pole.castShadow = true;
    scene.add(pole);

    const arm = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.1, 0.1), pylonSteelMat);
    arm.position.set(x, y - 0.18, z);
    arm.castShadow = true;
    scene.add(arm);

    [-0.62, 0.62].forEach((offset) => {
      const insulator = new THREE.Mesh(new THREE.SphereGeometry(0.1, 8, 8), insulatorMat);
      insulator.position.set(x + offset, y - 0.06, z);
      scene.add(insulator);
    });

    const beacon = new THREE.Mesh(
      new THREE.SphereGeometry(0.09, 8, 8),
      new THREE.MeshStandardMaterial({
        color: 0xffffff,
        emissive: colorHex,
        emissiveIntensity: 1.1,
      })
    );
    beacon.position.set(x, y + 0.16, z);
    scene.add(beacon);
  }

  const lineSystems = powerLines.map((spec) => {
    const curve = new THREE.CatmullRomCurve3(
      spec.points.map(([x, y, z]) => new THREE.Vector3(x, y, z))
    );
    // 각 선로의 중간 지지점에 전신주를 세운다
    const midPoint = spec.points[1];
    if (midPoint) addPylon(midPoint[0], midPoint[1], midPoint[2], spec.color);
    const wireMat = new THREE.MeshStandardMaterial({
      color: 0x334155,
      emissive: spec.color,
      emissiveIntensity: 0.08,
      roughness: 0.4,
    });
    const wireMesh = new THREE.Mesh(new THREE.TubeGeometry(curve, 48, 0.07, 6, false), wireMat);
    scene.add(wireMesh);

    const pulses = [];
    for (let p = 0; p < 5; p += 1) {
      const sprite = makeGlowSprite(textures.glow, spec.color, 1.5, 0);
      scene.add(sprite);
      pulses.push({ sprite, offset: p / 5 });
    }
    return { id: spec.id, curve, wireMat, pulses, phase: 0 };
  });

  /* ── 11-b. 바닥에 번지는 빛무리 · 밤의 반딧불 ────────────────── */

  function makeGroundGlow(colorHex, size, opacity) {
    const mesh = new THREE.Mesh(
      new THREE.PlaneGeometry(size, size),
      new THREE.MeshBasicMaterial({
        map: textures.glow,
        color: colorHex,
        transparent: true,
        opacity,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      })
    );
    mesh.rotation.x = -Math.PI / 2;
    mesh.renderOrder = 2;
    return mesh;
  }

  const substationGlow = makeGroundGlow(0xd7ff00, 22, 0.08);
  substationGlow.position.set(-0.5, 2.79, -0.5);
  scene.add(substationGlow);

  const villageGlow = makeGroundGlow(0xffb45c, 26, 0);
  villageGlow.position.set(20.5, 2.83, -7.5);
  scene.add(villageGlow);

  const ferrisGlow = makeGroundGlow(0xc8ff4a, 20, 0);
  ferrisGlow.position.set(22.5, 2.84, -19.2);
  scene.add(ferrisGlow);

  // 반딧불 — 밤에만 살랑이는 작은 빛 입자
  const fireflyCount = 64;
  const fireflyPos = new Float32Array(fireflyCount * 3);
  const fireflySeed = [];
  for (let i = 0; i < fireflyCount; i += 1) {
    const a = randRange(0, TAU);
    const r = randRange(4, 30);
    const x = Math.cos(a) * r;
    const z = Math.sin(a) * r * 0.92;
    fireflyPos[i * 3] = x;
    fireflyPos[i * 3 + 1] = randRange(3.2, 8.5);
    fireflyPos[i * 3 + 2] = z;
    fireflySeed.push({
      baseX: x,
      baseZ: z,
      baseY: fireflyPos[i * 3 + 1],
      phase: randRange(0, TAU),
      speed: randRange(0.25, 0.7),
    });
  }
  const fireflyGeo = new THREE.BufferGeometry();
  fireflyGeo.setAttribute("position", new THREE.BufferAttribute(fireflyPos, 3));
  const fireflyMat = new THREE.PointsMaterial({
    size: 0.85,
    map: textures.glow,
    color: 0xc8ff9a,
    transparent: true,
    opacity: 0.9,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    fog: false,
  });
  const fireflies = new THREE.Points(fireflyGeo, fireflyMat);
  fireflies.frustumCulled = false;
  scene.add(fireflies);

  /* ── 11-c. 원경 실루엣 · 해무 · 지면 기복 · 달빛 물길 ──────────── */

  // 수평선 너머의 먼 섬 능선 — 허공에 뜬 섬이 아니라 바다 위 섬나라처럼 보이게 한다
  const farRidgeMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.94,
    metalness: 0,
    vertexColors: true,
  });
  const farIslandSpecs = [
    { a: 2.42, r: 128, w: 42, h: 24, seed: 41 },
    { a: 2.72, r: 148, w: 54, h: 30, seed: 43 },
    { a: 3.02, r: 122, w: 36, h: 19, seed: 47 },
    { a: -0.42, r: 150, w: 48, h: 22, seed: 53 },
    { a: -0.72, r: 126, w: 34, h: 16, seed: 59 },
  ];
  farIslandSpecs.forEach((spec) => {
    const farGeo = makeMountainGeometry(spec.seed, 2);
    // 원경 산맥은 대기 원근으로 위쪽이 하늘색에 녹아들게 정점 색을 준다
    const farPos = farGeo.attributes.position;
    const farColors = new Float32Array(farPos.count * 3);
    const farLow = new THREE.Color(0x1b3350);
    const farHigh = new THREE.Color(0x5d7ea6);
    const farTmp = new THREE.Color();
    for (let i = 0; i < farPos.count; i += 1) {
      const h = THREE.MathUtils.clamp((farPos.getY(i) + 1) * 0.5, 0, 1);
      farTmp.copy(farLow).lerp(farHigh, Math.pow(h, 0.75));
      if (h > 0.72) farTmp.lerp(new THREE.Color(0xdfeaf7), (h - 0.72) * 1.6);
      farColors[i * 3] = farTmp.r;
      farColors[i * 3 + 1] = farTmp.g;
      farColors[i * 3 + 2] = farTmp.b;
    }
    farGeo.setAttribute("color", new THREE.Float32BufferAttribute(farColors, 3));
    const island = new THREE.Mesh(farGeo, farRidgeMat);
    island.scale.set(spec.w * 0.86, spec.h * 0.8, spec.w * 0.62);
    island.position.set(
      Math.cos(spec.a) * spec.r,
      spec.h * 0.16 - 3.4,
      Math.sin(spec.a) * spec.r
    );
    island.rotation.y = spec.seed * 0.7;
    scene.add(island);
  });

  // 수면 위 낮게 깔리는 해무 — 원경과 근경 사이에 공기층을 만든다
  const hazeSprites = [];
  for (let i = 0; i < 9; i += 1) {
    const angle = (i / 9) * TAU + 0.18;
    const radius = randRange(58, 88);
    const haze = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: textures.cloudSoft,
        color: 0x2f5b8c,
        transparent: true,
        opacity: randRange(0.02, 0.05),
        depthWrite: false,
        fog: false,
      })
    );
    haze.position.set(Math.cos(angle) * radius, randRange(0.8, 2.2), Math.sin(angle) * radius * 0.9);
    haze.scale.set(randRange(40, 70), randRange(4, 7), 1);
    scene.add(haze);
    hazeSprites.push({ sprite: haze, baseX: haze.position.x, baseZ: haze.position.z, phase: randRange(0, TAU) });
  }

  // ── 구역을 잇는 조약돌 산책로 ────────────────────────────────
  // 발전 광장에서 각 실험 구역으로 이어지는 길을 깔아, 섬이 "소품을 흩뿌린 판"이
  // 아니라 설계된 마을처럼 읽히게 한다. 길 위에는 언덕·바위를 놓지 않는다.
  const walkSamples = [];
  const walkwayMat = new THREE.MeshStandardMaterial({
    color: 0x8e9cb2,
    map: textures.cobble,
    normalMap: textures.cobbleNormal,
    normalScale: new THREE.Vector2(1.05, 1.05),
    roughnessMap: textures.cobbleRough,
    roughness: 0.9,
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -1,
  });

  function makeWalkway(points, width = 1.55) {
    const curve = new THREE.CatmullRomCurve3(
      points.map(([x, z]) => new THREE.Vector3(x, 0, z)),
      false,
      "catmullrom",
      0.4
    );
    const segments = 56;
    const positions = [];
    const uvs = [];
    const indices = [];
    for (let i = 0; i <= segments; i += 1) {
      const t = i / segments;
      const p = curve.getPoint(t);
      const tan = curve.getTangent(t);
      const nx = -tan.z;
      const nz = tan.x;
      const wobble = 1 + 0.1 * Math.sin(t * 21 + points.length);
      for (const side of [-1, 1]) {
        const x = p.x + nx * width * 0.5 * wobble * side;
        const z = p.z + nz * width * 0.5 * wobble * side;
        positions.push(x, terrainTopY(x, z) + 0.035, z);
        uvs.push(side > 0 ? 1 : 0, t * 16);
        walkSamples.push([x, z]);
      }
    }
    for (let i = 0; i < segments; i += 1) {
      const a = i * 2;
      indices.push(a, a + 1, a + 2, a + 2, a + 1, a + 3);
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geo.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
    geo.setIndex(indices);
    geo.computeVertexNormals();
    const mesh = new THREE.Mesh(geo, walkwayMat);
    mesh.receiveShadow = true;
    scene.add(mesh);
    return mesh;
  }

  const walkwayRoutes = [
    [[-1, 11.4], [-6, 12.6], [-11.5, 14.2], [-14.5, 16.6]],
    [[2, 12.2], [7.5, 14.4], [11.2, 16.4], [13.6, 18.4]],
    [[-1, 9.2], [-1, 4.2], [-0.6, 0.6]],
    [[-3.4, 3.6], [-9.5, 4.2], [-16.5, 4.4], [-21.5, 4.6]],
    [[2.4, -2.2], [8.5, -3.0], [13.5, -3.6]],
    [[25.5, -4.2], [26.4, 2.5], [25.2, 8.5], [24.4, 12.2]],
    [[-2.2, -3.4], [-8.5, -7.0], [-14.5, -11.5], [-18.5, -13.2]],
    [[18.6, 1.6], [19.6, 5.4], [21.4, 9.2]],
  ];
  walkwayRoutes.forEach((route) => makeWalkway(route));

  function nearWalkway(x, z, pad = 1.6) {
    return walkSamples.some(([px, pz]) => Math.hypot(px - x, pz - z) < pad);
  }

  // 섬 안쪽의 완만한 잔디 언덕 — 완전히 평평한 판 위에 소품만 얹힌 느낌을 없앤다
  const moundMat = new THREE.MeshStandardMaterial({
    color: 0xeefaf0,
    map: textures.grass,
    normalMap: textures.grassNormal,
    normalScale: new THREE.Vector2(1.05, 1.05),
    roughnessMap: textures.grassRough,
    roughness: 0.94,
  });
  const moundGeo = new THREE.SphereGeometry(1, 26, 12, 0, TAU, 0, Math.PI * 0.5);
  for (let i = 0; i < 26; i += 1) {
    const angle = randRange(0, TAU);
    const radius = islandRadiusAt(angle) * randRange(0.52, 0.92);
    const x = Math.cos(angle) * radius;
    const z = Math.sin(angle) * radius * 0.95;
    if (!isFreeSpot(x, z, 2.6) || nearWalkway(x, z, 3.4)) continue;
    const mound = new THREE.Mesh(moundGeo, moundMat);
    const spread = randRange(2.4, 5.2);
    mound.scale.set(spread, randRange(0.35, 0.95), spread * randRange(0.8, 1.2));
    mound.position.set(x, terrainTopY(x, z) - 0.12, z);
    mound.rotation.y = randRange(0, TAU);
    mound.castShadow = true;
    mound.receiveShadow = true;
    scene.add(mound);
  }

  // 달빛이 바다에 길게 내려앉는 물길 (달 방향과 정렬)
  const glitterAngle = Math.atan2(-82, 50);
  const moonGlitter = new THREE.Mesh(
    new THREE.PlaneGeometry(13, 170),
    new THREE.MeshBasicMaterial({
      map: textures.glow,
      color: 0x9dc0ff,
      transparent: true,
      opacity: 0.2,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      fog: false,
    })
  );
  moonGlitter.rotation.set(-Math.PI / 2, 0, -glitterAngle + Math.PI / 2);
  moonGlitter.position.set(
    Math.cos(glitterAngle) * 88,
    0.06,
    Math.sin(glitterAngle) * 88 * 0.86
  );
  scene.add(moonGlitter);

  // 밝은 물마루가 잔물결 따라 흔들리는 보조 광택
  const glitterSheen = moonGlitter.clone();
  glitterSheen.material = moonGlitter.material.clone();
  glitterSheen.material.opacity = 0.12;
  glitterSheen.material.color.setHex(0x5f9be8);
  glitterSheen.scale.set(1.7, 0.86, 1);
  glitterSheen.position.y = 0.08;
  scene.add(glitterSheen);

  // 해안선 바로 바깥의 얕은 물띠 — 모래와 바다의 경계를 부드럽게 만든다
  const shoreWash = new THREE.Mesh(
    new THREE.RingGeometry(38.2, 48.5, 96, 1),
    new THREE.MeshBasicMaterial({
      map: textures.foam,
      color: 0x8fe8e0,
      transparent: true,
      opacity: 0.16,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
    })
  );
  shoreWash.rotation.x = -Math.PI / 2;
  shoreWash.position.y = 0.09;
  scene.add(shoreWash);

  /* ── 12. 3D 번개 아크 & 하늘 불꽃놀이 & 스파크 파티클 ────────── */

  const lightningBolts = [];
  function spawnLightningBolt(fromVec, toVec, colorHex = 0x9ef7ff, duration = 0.34) {
    const segments = 9;
    const pts = [];
    for (let i = 0; i <= segments; i += 1) {
      const t = i / segments;
      const p = new THREE.Vector3().lerpVectors(fromVec, toVec, t);
      if (i > 0 && i < segments) {
        const jitter = (1 - Math.abs(t - 0.5) * 1.4) * 2.1;
        p.x += (Math.random() - 0.5) * jitter * 2;
        p.y += (Math.random() - 0.5) * jitter * 1.4;
        p.z += (Math.random() - 0.5) * jitter * 2;
      }
      pts.push(p);
    }
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const mat = new THREE.LineBasicMaterial({
      color: colorHex,
      transparent: true,
      opacity: 1,
      blending: THREE.AdditiveBlending,
    });
    const line = new THREE.Line(geo, mat);
    scene.add(line);
    lightningBolts.push({ line, geo, mat, life: duration, maxLife: duration });
  }

  // 불꽃놀이 & 황금 스파크 입자 풀
  const sparkPoolSize = 180;
  const sparkPositions = new Float32Array(sparkPoolSize * 3);
  const sparkColors = new Float32Array(sparkPoolSize * 3);
  const sparkState = [];
  for (let i = 0; i < sparkPoolSize; i += 1) {
    sparkPositions[i * 3 + 1] = -999;
    sparkState.push({
      life: 0,
      maxLife: 1,
      vx: 0,
      vy: 0,
      vz: 0,
      gravity: 16,
    });
  }
  const sparkGeo = new THREE.BufferGeometry();
  sparkGeo.setAttribute("position", new THREE.BufferAttribute(sparkPositions, 3));
  sparkGeo.setAttribute("color", new THREE.BufferAttribute(sparkColors, 3));
  const sparkPoints = new THREE.Points(
    sparkGeo,
    new THREE.PointsMaterial({
      size: 1.55,
      map: textures.glow,
      vertexColors: true,
      transparent: true,
      opacity: 0.95,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      fog: false,
    })
  );
  sparkPoints.frustumCulled = false;
  scene.add(sparkPoints);

  let sparkCursor = 0;
  function emitSpark(x, y, z, vx, vy, vz, colorHex, life = 0.85, gravity = 15) {
    const idx = sparkCursor % sparkPoolSize;
    sparkCursor += 1;
    const c = new THREE.Color(colorHex);
    sparkPositions[idx * 3] = x;
    sparkPositions[idx * 3 + 1] = y;
    sparkPositions[idx * 3 + 2] = z;
    sparkColors[idx * 3] = c.r;
    sparkColors[idx * 3 + 1] = c.g;
    sparkColors[idx * 3 + 2] = c.b;
    const st = sparkState[idx];
    st.life = life;
    st.maxLife = life;
    st.vx = vx;
    st.vy = vy;
    st.vz = vz;
    st.gravity = gravity;
  }

  function launchFirework(originX = 24, originZ = -15) {
    const palette = [0xd7ff00, 0x38bdf8, 0xff5c8a, 0xffbe3b, 0xc084fc];
    const color = palette[Math.floor(Math.random() * palette.length)];
    const burstY = 23 + Math.random() * 8;
    const bx = originX + (Math.random() - 0.5) * 14;
    const bz = originZ + (Math.random() - 0.5) * 12;
    const rays = reducedMotion ? 10 : 28;
    for (let i = 0; i < rays; i += 1) {
      const phi = Math.acos(1 - (2 * (i + 0.5)) / rays);
      const theta = i * 2.399963;
      const speed = 7.5 + Math.random() * 5.5;
      emitSpark(
        bx,
        burstY,
        bz,
        Math.sin(phi) * Math.cos(theta) * speed,
        Math.cos(phi) * speed,
        Math.sin(phi) * Math.sin(theta) * speed,
        color,
        1.15 + Math.random() * 0.4,
        6.2
      );
    }
  }

  function triggerTeslaSpectacle() {
    const topWorld = new THREE.Vector3(-0.5, 14.4, -3.9);
    const targets = [
      new THREE.Vector3(-14.5, 5.2, 15.5),
      new THREE.Vector3(-1, 6.2, 14.5),
      new THREE.Vector3(20.5, 9.2, -6.5),
      new THREE.Vector3(22.5, 19.5, -19.2),
      new THREE.Vector3(-19.5, 9.5, -14.5),
    ];
    targets.forEach((tv, idx) => {
      spawnLightningBolt(
        topWorld,
        tv,
        idx % 2 === 0 ? 0xa5f3fc : 0xd7ff00,
        0.42
      );
    });
    launchFirework(22, -16);
    flashBoost = 1;
  }

  /* ── 13. 카메라 프리셋 비행 & 3D 직접 드래그/터치 조작 ────────── */

  let cameraTween = null;
  let flashBoost = 0;
  let trainProgress = 0;
  let ferrisAngle = 0;
  let windSpin = 0;
  let hydroSpin = 0;
  let fireworkCooldown = 1.2;
  let stormBoltCooldown = 2.0;
  let lastBladeKey = "3:0.30";
  let lastFruitKind = "";

  function focusZone(zoneId) {
    const preset = CAMERA_PRESETS[zoneId] || CAMERA_PRESETS.overview;
    if (!controls) {
      camera.position.set(...preset.position);
      camera.lookAt(...preset.target);
      return;
    }
    cameraTween = {
      fromPos: camera.position.clone(),
      toPos: new THREE.Vector3(...preset.position),
      fromTarget: controls.target.clone(),
      toTarget: new THREE.Vector3(...preset.target),
      elapsed: 0,
      duration: reducedMotion ? 0.05 : 0.92,
    };
  }

  // 레이캐스터 직접 3D 조작
  const raycaster = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  const dragState = {
    active: null,
    pointerId: -1,
    moved: false,
    startX: 0,
    startY: 0,
    lastAngle: 0,
    lastX: 0,
    lastY: 0,
  };

  function updateNdc(event) {
    const rect = canvas.getBoundingClientRect();
    const w = rect.width || widthInitial;
    const h = rect.height || heightInitial;
    ndc.x = ((event.clientX - rect.left) / w) * 2 - 1;
    ndc.y = -((event.clientY - rect.top) / h) * 2 + 1;
  }

  function pickInteractive(event) {
    if (!canvas) return null;
    updateNdc(event);
    raycaster.setFromCamera(ndc, camera);
    const hits = raycaster.intersectObjects(interactiveTargets, false);
    return hits.length ? hits[0].object : null;
  }

  if (canvas) {
    canvas.addEventListener("pointerdown", (event) => {
      const hit = pickInteractive(event);
      if (!hit) return;
      const kind = hit.userData.hitKind;
      dragState.active = kind;
      dragState.zoneId = hit.userData.zoneId;
      dragState.pointerId = event.pointerId;
      dragState.moved = false;
      dragState.startX = event.clientX;
      dragState.startY = event.clientY;
      dragState.lastX = event.clientX;
      dragState.lastY = event.clientY;

      if (kind === "crank" || kind === "balloon" || kind === "sun" || kind === "panel") {
        if (controls) controls.enabled = false;
        if (typeof canvas.setPointerCapture === "function") {
          canvas.setPointerCapture(event.pointerId);
        }
        const rect = canvas.getBoundingClientRect();
        dragState.lastAngle = Math.atan2(
          event.clientY - (rect.top + rect.height * 0.56),
          event.clientX - (rect.left + rect.width * 0.5)
        );
      }
    });

    canvas.addEventListener("pointermove", (event) => {
      if (!dragState.active) {
        const hover = pickInteractive(event);
        if (canvas.style) {
          canvas.style.cursor = hover ? "grab" : "default";
        }
        return;
      }
      const dx = event.clientX - dragState.lastX;
      const dy = event.clientY - dragState.lastY;
      if (Math.hypot(event.clientX - dragState.startX, event.clientY - dragState.startY) > 6) {
        dragState.moved = true;
      }
      dragState.lastX = event.clientX;
      dragState.lastY = event.clientY;

      if (dragState.active === "crank" && onCrankDrag) {
        const rect = canvas.getBoundingClientRect();
        const angle = Math.atan2(
          event.clientY - (rect.top + rect.height * 0.56),
          event.clientX - (rect.left + rect.width * 0.5)
        );
        let delta = angle - dragState.lastAngle;
        while (delta > Math.PI) delta -= TAU;
        while (delta < -Math.PI) delta += TAU;
        dragState.lastAngle = angle;
        onCrankDrag(delta, Math.hypot(dx, dy));
      } else if (dragState.active === "balloon" && onBalloonDrag) {
        onBalloonDrag(dx * 0.055, -dy * 0.055, Math.hypot(dx, dy));
      } else if (dragState.active === "sun" && onSunDrag) {
        onSunDrag(-dy * 0.35);
      } else if (dragState.active === "panel" && onPanelDrag) {
        onPanelDrag(-dy * 0.35);
      }
    });

    const finishPointer = () => {
      if (!dragState.active) return;
      const kind = dragState.active;
      const zoneId = dragState.zoneId;
      const wasTap = !dragState.moved;
      dragState.active = null;
      if (controls) controls.enabled = true;

      if (wasTap) {
        if (kind === "tesla" && onTeslaFire) onTeslaFire();
        else if (kind === "switch" && onSwitchToggle) onSwitchToggle();
        else if (kind === "wind" && onWindGust) onWindGust();
        else if (kind === "hydro" && onHydroToggle) onHydroToggle();
        else if (kind === "fruit" && onFruitTap) onFruitTap();
        else if (kind === "crank" && onCrankDrag) onCrankDrag(0.65, 22);
        if (zoneId && onZoneSelect) onZoneSelect(zoneId, { fromWorld: true });
      }
    };

    canvas.addEventListener("pointerup", finishPointer);
    canvas.addEventListener("pointercancel", finishPointer);
  }

  /* ── 14. 하늘 분위기 & 매 프레임 월드 동기화 ──────────────────── */

  // ── 날씨별 대기 프리셋 ─────────────────────────────────────────
  const ATMOSPHERES = {
    night: {
      top: 0x040b1d,
      horizon: 0x152e55,
      glow: 0x2f6fa8,
      sunColor: 0xa9c8ff,
      sunStrength: 0.34,
      sunPower: 320,
      stars: 0.95,
      moon: 1,
      hemiSky: 0x7aa6ee,
      hemiGround: 0x1b2c42,
      hemi: 0.5,
      mainColor: 0xc9e0ff,
      main: 1.85,
      rim: 0.82,
      warmth: 0.3,
      fog: 0x0a1a33,
      fogDensity: 0.0034,
      seaDeep: 0x04121f,
      seaShallow: 0x0d3f52,
      seaFoam: 0xd6ecff,
      bloom: 0.28,
      exposure: 0.92,
      gradeTint: [0.94, 0.97, 1.06],
    },
    dusk: {
      top: 0x241d4f,
      horizon: 0xe07a4a,
      glow: 0xff9d5c,
      sunColor: 0xffc07a,
      sunStrength: 0.85,
      sunPower: 160,
      stars: 0.4,
      moon: 0.55,
      hemiSky: 0xffb98a,
      hemiGround: 0x2a2038,
      hemi: 0.8,
      mainColor: 0xffb377,
      main: 1.7,
      rim: 0.62,
      warmth: 0.85,
      fog: 0x3a2a44,
      fogDensity: 0.0046,
      seaDeep: 0x1a1a33,
      seaShallow: 0x4a3a58,
      seaFoam: 0xffd9c0,
      bloom: 0.36,
      exposure: 1.0,
      gradeTint: [1.07, 0.99, 0.93],
    },
    day: {
      top: 0x1f6cd6,
      horizon: 0xb4dcff,
      glow: 0xd6ecff,
      sunColor: 0xfff6da,
      sunStrength: 1.3,
      sunPower: 220,
      stars: 0.03,
      moon: 0,
      hemiSky: 0xd2e8ff,
      hemiGround: 0x3d5566,
      hemi: 0.62,
      mainColor: 0xfff4dc,
      main: 3.05,
      rim: 0.62,
      warmth: 0.18,
      fog: 0x9cc6e8,
      fogDensity: 0.0013,
      seaDeep: 0x0a4a78,
      seaShallow: 0x27a9bd,
      seaFoam: 0xf2feff,
      bloom: 0.16,
      exposure: 0.86,
      gradeTint: [1.02, 1.0, 0.99],
    },
    storm: {
      top: 0x0b1526,
      horizon: 0x2b4058,
      glow: 0x3d6185,
      sunColor: 0x9fc2ff,
      sunStrength: 0.2,
      sunPower: 340,
      stars: 0.12,
      moon: 0,
      hemiSky: 0x54708f,
      hemiGround: 0x101a26,
      hemi: 0.62,
      mainColor: 0x9fc2ff,
      main: 0.85,
      rim: 0.5,
      warmth: 0.15,
      fog: 0x0a1220,
      fogDensity: 0.0062,
      seaDeep: 0x0a1b2b,
      seaShallow: 0x224155,
      seaFoam: 0xd2e4f0,
      bloom: 0.34,
      exposure: 0.95,
      gradeTint: [0.93, 0.96, 1.05],
    },
  };

  const atmo = {
    top: new THREE.Color(ATMOSPHERES.night.top),
    horizon: new THREE.Color(ATMOSPHERES.night.horizon),
    glow: new THREE.Color(ATMOSPHERES.night.glow),
    sunColor: new THREE.Color(ATMOSPHERES.night.sunColor),
    sunStrength: ATMOSPHERES.night.sunStrength,
    sunPower: ATMOSPHERES.night.sunPower,
    stars: ATMOSPHERES.night.stars,
    moon: 1,
    hemiSky: new THREE.Color(ATMOSPHERES.night.hemiSky),
    hemiGround: new THREE.Color(ATMOSPHERES.night.hemiGround),
    hemi: ATMOSPHERES.night.hemi,
    mainColor: new THREE.Color(ATMOSPHERES.night.mainColor),
    main: ATMOSPHERES.night.main,
    rim: ATMOSPHERES.night.rim,
    warmth: ATMOSPHERES.night.warmth,
    fog: new THREE.Color(ATMOSPHERES.night.fog),
    fogDensity: ATMOSPHERES.night.fogDensity,
    seaDeep: new THREE.Color(ATMOSPHERES.night.seaDeep),
    seaShallow: new THREE.Color(ATMOSPHERES.night.seaShallow),
    seaFoam: new THREE.Color(ATMOSPHERES.night.seaFoam),
    bloom: ATMOSPHERES.night.bloom,
    exposure: ATMOSPHERES.night.exposure,
    gradeTint: new THREE.Color(...ATMOSPHERES.night.gradeTint),
  };

  const targetTmp = {
    top: new THREE.Color(),
    horizon: new THREE.Color(),
    glow: new THREE.Color(),
    sunColor: new THREE.Color(),
    hemiSky: new THREE.Color(),
    hemiGround: new THREE.Color(),
    mainColor: new THREE.Color(),
    fog: new THREE.Color(),
    gradeTint: new THREE.Color(),
    seaDeep: new THREE.Color(),
    seaShallow: new THREE.Color(),
    seaFoam: new THREE.Color(),
  };

  const sunDirWorld = new THREE.Vector3(-0.4, 0.5, 0.75);
  const TINT_HELPER = new THREE.Color();
  const CLOUD_WHITE = new THREE.Color(1, 1, 1);
  const cloudTint = new THREE.Color();
  const sunWorldPos = new THREE.Vector3();

  function applyAtmosphere(weather, sunAltitudeDeg, cloudRatio, dt = 0.016, sunLevel = 0.5) {
    const preset = ATMOSPHERES[weather] || ATMOSPHERES.night;
    const k = Math.min(1, dt * 2.6);

    Object.keys(targetTmp).forEach((key) => {
      if (Array.isArray(preset[key])) targetTmp[key].setRGB(...preset[key]);
      else targetTmp[key].setHex(preset[key]);
      atmo[key].lerp(targetTmp[key], k);
    });
    const scalarKeys = [
      "sunStrength",
      "sunPower",
      "stars",
      "moon",
      "hemi",
      "main",
      "rim",
      "warmth",
      "fogDensity",
      "bloom",
      "exposure",
    ];
    scalarKeys.forEach((key) => {
      atmo[key] += (preset[key] - atmo[key]) * k;
    });

    // 태양 궤도 위치 (고도 슬라이더와 연동) — 하늘/구름/IBL 이 모두 같은 방향을 본다
    const altRad = THREE.MathUtils.clamp(sunAltitudeDeg, 5, 90) * DEG;
    // 태양은 섬에서 150 유닛 떨어진 하늘에 뜬다 (드래그로 고도가 바뀐다)
    const sunDist = 150;
    sunOrbGroup.position.set(
      -0.42 * sunDist * Math.cos(altRad) * 0.55 - 18,
      Math.sin(altRad) * sunDist,
      0.78 * sunDist * Math.cos(altRad) * 0.55 + 12
    );
    sunDirWorld.copy(sunOrbGroup.position).sub(new THREE.Vector3(0, 3, 0)).normalize();
    sunWorldPos.copy(sunOrbGroup.position);

    // 스카이 셰이더 유니폼
    skyUniforms.uTop.value.copy(atmo.top);
    skyUniforms.uHorizon.value.copy(atmo.horizon);
    skyUniforms.uGlow.value.copy(atmo.glow);
    skyUniforms.uFog.value.copy(atmo.fog);
    skyUniforms.uSunDir.value.copy(sunDirWorld);
    skyUniforms.uSunColor.value.copy(atmo.sunColor);
    skyUniforms.uSunStrength.value = atmo.sunStrength * (1 - cloudRatio * 0.45) * (weather === "day" ? 1.5 : 1);
    skyUniforms.uSunPower.value = atmo.sunPower;
    skyUniforms.uMoonDir.value.copy(moonGroup.position).normalize();
    skyUniforms.uMoon.value = atmo.moon;
    skyUniforms.uMilky.value = atmo.stars;
    skyUniforms.uCloud.value = cloudRatio;

    // 조명
    hemiLight.color.copy(atmo.hemiSky);
    hemiLight.groundColor.copy(atmo.hemiGround);
    hemiLight.intensity = atmo.hemi + flashBoost * 0.9;
    mainLight.color.copy(atmo.mainColor);
    mainLight.intensity = atmo.main * (1 - cloudRatio * 0.35) + flashBoost * 2.4;
    rimLight.intensity = atmo.rim + flashBoost * 0.6;
    warmFill.intensity = atmo.warmth;

    starMat.uniforms.uOpacity.value = atmo.stars;
    starField.visible = atmo.stars > 0.02;
    moonGroup.visible = atmo.moon > 0.03;
    moonMesh.material.color.setRGB(0.86, 0.9, 1.0).multiplyScalar(0.92 + atmo.moon * 0.1);
    moonHalo.material.opacity = 0.3 * atmo.moon;
    moonHaloOuter.material.opacity = 0.14 * atmo.moon;

    scene.fog.color.copy(atmo.fog);
    scene.fog.density = atmo.fogDensity;

    // 원경 산맥은 대기 원근으로 하늘색을 머금는다 — 낮에는 멀리 옅어지고 밤에는 남색으로 가라앉는다
    mountainMaterials.forEach(({ mat, base }) => {
      mat.emissive.copy(base).lerp(atmo.horizon, weather === "day" ? 0.55 : weather === "dusk" ? 0.42 : 0.2);
      mat.emissiveIntensity = weather === "day" ? 0.55 : 0.42;
    });

    // 바다 — 수심 색과 거품 밝기가 하늘/날씨를 따라간다
    seaUniforms.uSunDir.value.copy(sunDirWorld);
    seaUniforms.uSunColor.value.copy(atmo.sunColor);
    seaUniforms.uSkyColor.value.copy(atmo.horizon);
    seaUniforms.uDeepColor.value.copy(atmo.seaDeep);
    seaUniforms.uShallowColor.value.copy(atmo.seaShallow);
    seaUniforms.uFoamColor.value.copy(atmo.seaFoam);
    seaUniforms.uFoamAmount.value = weather === "storm" ? 1.6 : 1;

    if (renderer) renderer.toneMappingExposure = atmo.exposure + flashBoost * 0.12;
    if (bloomPass) {
      bloomPass.strength = reducedMotion ? atmo.bloom * 0.62 : atmo.bloom;
    }
    if (gradePass) {
      gradePass.uniforms.uTint.value.copy(atmo.gradeTint);
    }

    // 태양 오브 외형
    const sunBrightness = weather === "night" ? 0.4 : 1 - cloudRatio * 0.5;
    const nightDim = weather === "night" ? 0.5 : 1;
    sunCorona.material.opacity = (0.26 + sunBrightness * 0.3) * nightDim;
    sunRays.material.opacity = (0.14 + sunBrightness * 0.32) * nightDim;
    sunRays.material.rotation += dt * 0.03;
    sunSphere.scale.setScalar(weather === "night" ? 0.62 : 1);
    sunOrbGroup.scale.setScalar(1);
    sunSphere.visible = weather !== "storm";

    // 태양광 테라스 위로 비스듬히 내리꽂히는 빛 기둥 (태양 방향과 정렬)
    const panelCenter = new THREE.Vector3(-14.5, 4.4, 15.5);
    const shaftDir = sunDirWorld.clone().normalize();
    sunBeam.position.copy(panelCenter).addScaledVector(shaftDir, 13.5);
    sunBeam.quaternion.setFromUnitVectors(
      new THREE.Vector3(0, 1, 0),
      shaftDir
    );
    const dayFactor = weather === "day" ? 1.5 : weather === "dusk" ? 1.05 : 0.5;
    sunBeam.scale.setScalar(dayFactor * (0.4 + sunLevel * 0.6));

    // 구름 밀도 — 날씨의 지평선 색을 받아 밤에는 남색, 낮에는 흰색으로 물든다
    cloudTint
      .copy(atmo.horizon)
      .lerp(atmo.top, 0.22)
      .lerp(CLOUD_WHITE, weather === "day" ? 0.72 : weather === "dusk" ? 0.5 : 0.46);
    const cloudOpacity = cloudRatio * (weather === "day" ? 0.95 : weather === "night" ? 0.42 : 0.62);
    cloudMaterials.forEach((mat) => {
      mat.opacity = cloudOpacity;
      mat.color.copy(cloudTint).multiplyScalar(mat.userData.shade);
    });
    cloudClusters.forEach((cluster, idx) => {
      cluster.visible = cloudRatio > 0.02;
      const drift = cloudRatio > 0.02 ? performanceNow * (weather === "storm" ? 0.03 : 0.008) : 0;
      const angle = cluster.userData.angle + drift + (idx % 2 ? 0.02 : -0.015);
      const radius = cluster.userData.radius;
      cluster.position.x = Math.cos(angle) * radius;
      cluster.position.z = Math.sin(angle) * radius * 0.92;
      cluster.position.y =
        cluster.userData.baseY + Math.sin(performanceNow * 0.18 + cluster.userData.phase) * 0.7;
    });

    // 환경 조명(IBL)은 날씨/태양 고도가 실제로 바뀔 때만 다시 굽는다
    const envKey = `${weather}:${Math.round(sunAltitudeDeg / 30)}:${Math.round(cloudRatio * 4)}`;
    if (envKey !== envWeatherKey) {
      envWeatherKey = envKey;
      updateEnvironmentLighting(
        atmo.top,
        atmo.horizon,
        atmo.hemiGround,
        sunDirWorld,
        atmo.sunColor
      );
    }
  }

  let performanceNow = 0;

  function step(dt, snapshot) {
    performanceNow += dt;
    flashBoost = Math.max(0, flashBoost - dt * 2.8);

    const {
      weather = "night",
      circuit,
      staticState,
      fruit,
      generator,
      solar,
      wind,
      hydro,
      grid,
    } = snapshot;

    applyAtmosphere(weather, solar.altitude, solar.cloud / 100, dt, solar.output.level);
    skyUniforms.uTime.value = performanceNow;
    if (gradePass) gradePass.uniforms.uTime.value = performanceNow;
    starMat.uniforms.uTime.value = performanceNow;

    // 1) 바다 물결 · 노멀맵 흐름 · 해안 거품
    seaUniforms.uTime.value = performanceNow * (reducedMotion ? 0.35 : 1);
    if (!reducedMotion) {
      seaMat.normalMap.offset.set(performanceNow * 0.012, performanceNow * 0.007);
    }
    const shorePulse = 0.34 + Math.sin(performanceNow * 1.15) * 0.09;
    foamRing.material.opacity = shorePulse * (weather === "storm" ? 1.6 : 1);
    foamRing.position.y = 0.16 + Math.sin(performanceNow * 0.9) * 0.035;
    lagoon.material.opacity = 0.22 + Math.sin(performanceNow * 0.7) * 0.05;
    // 달이 천천히 떠오르며 자전
    moonMesh.rotation.y += dt * 0.02;
    moonGroup.position.y = 66 + Math.sin(performanceNow * 0.12) * 0.6;

    // 2) 중앙 변전소 & 주 회로 & 테슬라 코일
    const targetKnifeAngle = circuit.closed ? 0 : 0.78;
    knifePivot.rotation.z += (targetKnifeAngle - knifePivot.rotation.z) * Math.min(1, dt * 12);

    Object.keys(materialMeshes).forEach((key) => {
      materialMeshes[key].visible = key === circuit.material;
    });

    const activeBoosterCount = Math.round(circuit.voltage / 1.5);
    boosterCells.forEach((cell, idx) => {
      cell.material.color.setHex(idx < activeBoosterCount ? 0xf59e0b : 0x263854);
      cell.material.emissiveIntensity = idx < activeBoosterCount ? 0.85 : 0.06;
    });

    circuitBulbMat.emissiveIntensity = 0.08 + circuit.output.brightness * 2.8;
    circuitBulbHalo.material.opacity = circuit.output.brightness * 0.78;

    const capRatio = Math.max(grid.gridRatio, circuit.output.brightness * 0.35);
    capacitorCores.forEach((core, idx) => {
      const pulse = 0.92 + Math.sin(performanceNow * 5 + idx * 1.4) * 0.08;
      core.scale.y = Math.max(0.08, capRatio * pulse);
      core.position.y = 0.65 + core.scale.y * 1.9;
      core.material.emissiveIntensity = 0.4 + capRatio * 2.4;
    });

    teslaToroidMat.emissiveIntensity = 0.1 + grid.gridRatio * 0.6 + flashBoost * 0.8;
    teslaHalo.material.opacity = 0.14 + grid.gridRatio * 0.36 + flashBoost * 0.3;
    substationLight.intensity =
      (0.7 + grid.gridRatio * 2.8 + flashBoost * 3.0) * substationLight.userData.gain;
    const zoneLevel = 0.18 + grid.gridRatio * 0.82;
    zoneLights.forEach((lamp) => {
      lamp.intensity = lamp.userData.baseIntensity * zoneLevel;
    });

    // 스위치 열림 상태에서 발전 중이면 단자 틈새에서 스파크!
    if ((!circuit.closed || !circuit.output.conductive) && grid.rawWatts > 2 && Math.random() < dt * 8) {
      emitSpark(
        -0.5 + (Math.random() - 0.5) * 2.2,
        4.3,
        2.5,
        (Math.random() - 0.5) * 5,
        2.5 + Math.random() * 4,
        (Math.random() - 0.5) * 5,
        0xffd85c,
        0.42,
        18
      );
    }

    // 3) 손잡이 크랭크 발전기 회전 & 불꽃
    rotorPivot.rotation.x = generator.angle;
    crankWheelPivot.rotation.z = -generator.angle;
    coilStatorMat.emissiveIntensity = 0.12 + generator.output.level * 2.2;
    const activeRings = Math.max(2, Math.round((generator.turns / 600) * statorRings.length));
    statorRings.forEach((ring, idx) => {
      ring.visible = idx < activeRings;
    });
    dynamoBulbMat.emissiveIntensity = 0.08 + generator.output.level * 3.0;
    dynamoBulbHalo.material.opacity = generator.output.level * 0.85;
    crankGlowLight.intensity =
      (0.25 + generator.output.level * 2.6) * crankGlowLight.userData.gain;

    if (!reducedMotion && generator.rpm > 35 && Math.random() < dt * (generator.rpm * 0.14)) {
      emitSpark(
        -1.2,
        5.8,
        14.5,
        (Math.random() - 0.5) * 7,
        3 + Math.random() * 6,
        (Math.random() - 0.5) * 7,
        0xffd166,
        0.5,
        18
      );
    }

    // 4) 해안 풍력 터빈 & 바람 리본
    const bladeKey = `${wind.blades}:${wind.bladeLength.toFixed(2)}`;
    if (bladeKey !== lastBladeKey) {
      lastBladeKey = bladeKey;
      const normScale = (wind.bladeLength - 0.15) / 0.35;
      turbines.forEach((tb) => {
        populateRotorBlades(tb.rotor, wind.blades, (0.3 + normScale * 0.7) * tb.scale);
      });
    }
    const visualWindRpm = Math.min(wind.rpm, 220) * (reducedMotion ? 0.35 : 1);
    windSpin += (visualWindRpm * TAU * dt) / 60;
    bladeMaterial.emissiveIntensity = 0.08 + wind.output.level * 0.85;
    turbines.forEach((tb, idx) => {
      tb.rotor.rotation.z = -windSpin * (1 - idx * 0.08) + idx * 1.1;
    });

    windRibbons.forEach((ribbon, idx) => {
      ribbon.visible = wind.windSpeed > 0.4;
      ribbon.material.opacity = Math.min(0.4, wind.windSpeed * 0.034);
      ribbon.position.x += (3 + wind.windSpeed * 2.8) * dt;
      ribbon.position.y += Math.sin(performanceNow * 2 + idx) * 0.015;
      if (ribbon.position.x > -8) {
        ribbon.position.x = -44 - (idx % 5) * 3;
      }
    });

    // 5) 태양광 패널 경사 & 광선 휘도
    const tiltRad = solar.tilt * DEG;
    solarPanels.forEach((pivot) => {
      pivot.rotation.z = -tiltRad * 0.85;
    });
    solarPanelMat.emissiveIntensity = 0.06 + solar.output.level * 0.34;
    sunBeamMat.uniforms.uOpacity.value = 0.02 + solar.output.level * 0.14;
    sunBeamMat.uniforms.uTime.value = performanceNow;

    // 6) 수력 저수지 수위 · 폭포 · 물레바퀴
    const headNorm = (hydro.head - 0.2) / 2.3;
    reservoirWater.scale.y = 0.35 + headNorm * 1.15;
    reservoirWater.position.y = 9.2 - reservoirWater.scale.y * 2.75;
    sluiceGate.position.y = 6.9 + (hydro.flow / 5) * 1.2;

    const flowNorm = hydro.flow / 5;
    waterfallStream.scale.set(0.45 + flowNorm * 0.95, 1, 0.45 + flowNorm * 0.95);
    waterfallMat.opacity = 0.35 + flowNorm * 0.55;

    const visualHydroRpm = Math.min(hydro.rpm, 240) * (reducedMotion ? 0.35 : 1);
    hydroSpin += (visualHydroRpm * TAU * dt) / 60;
    waterWheel.rotation.x = hydroSpin;
    hydroBeaconMat.emissiveIntensity = 0.15 + hydro.output.level * 2.4;
    splashPool.material.opacity = 0.2 + flowNorm * 0.5;
    splashPool.scale.setScalar(0.82 + flowNorm * 0.25 + Math.sin(performanceNow * 3.1) * 0.05);
    hydroMist.forEach((mist, idx) => {
      mist.material.opacity = (0.06 + flowNorm * 0.22) * (0.7 + Math.sin(performanceNow * 1.6 + idx) * 0.3);
      mist.position.y = 1.2 + idx * 0.65 + Math.sin(performanceNow * 1.1 + idx * 2) * 0.22;
      const sc = 3.6 + idx + flowNorm * 1.4;
      mist.scale.set(sc, sc * 0.8, 1);
    });

    if (!reducedMotion) {
      const pArr = hydroDropGeo.attributes.position.array;
      for (let i = 0; i < hydroDropCount; i += 1) {
        hydroDropVel[i] = (hydroDropVel[i] || 0) + 14 * dt;
        pArr[i * 3 + 1] -= (3.5 + flowNorm * 7 + hydroDropVel[i]) * dt;
        if (pArr[i * 3 + 1] < 1.5) {
          pArr[i * 3] = -19.9 + (Math.random() - 0.5) * (1.0 + flowNorm * 1.4);
          pArr[i * 3 + 1] = 7.1 + headNorm * 1.8;
          pArr[i * 3 + 2] = -15.5 + (Math.random() - 0.5) * 1.3;
          hydroDropVel[i] = 0;
        }
      }
      hydroDropGeo.attributes.position.needsUpdate = true;
    }

    // 7) 정전기 풍선 & 별 종이 조각 춤
    const chargeNorm = staticState.charge / 100;
    balloonPivot.position.set(
      staticState.worldX,
      staticState.worldY + Math.sin(performanceNow * 2.4) * 0.14,
      staticState.worldZ
    );
    balloonMat.emissiveIntensity = 0.12 + chargeNorm * 1.9;
    balloonAura.material.opacity = chargeNorm * 0.72;
    balloonAura.scale.setScalar(4.8 + chargeNorm * 4.2);

    paperBits.forEach((bit, idx) => {
      const stateBit = staticState.bits[idx];
      if (stateBit && stateBit.stuck) {
        const a = bit.orbitAngle + performanceNow * 1.6;
        bit.mesh.position.set(
          balloonPivot.position.x + Math.cos(a) * 1.85,
          balloonPivot.position.y - 0.4 + Math.sin(a * 2) * 0.65,
          balloonPivot.position.z + Math.sin(a) * 1.85
        );
        bit.mesh.rotation.x += dt * 4;
        bit.mesh.rotation.z += dt * 3;
      } else {
        const pull = stateBit ? stateBit.pull : 0;
        bit.mesh.position.x += (bit.homeX - bit.mesh.position.x) * Math.min(1, dt * 5);
        bit.mesh.position.z += (bit.homeZ - bit.mesh.position.z) * Math.min(1, dt * 5);
        const targetY = 0.16 + pull * 1.9;
        bit.mesh.position.y += (targetY - bit.mesh.position.y) * Math.min(1, dt * 8);
        bit.mesh.rotation.y += pull * dt * 8;
      }
    });

    if (staticState.rubbing > 0.1 && Math.random() < dt * 14) {
      emitSpark(
        12.5 + balloonPivot.position.x,
        2.6 + balloonPivot.position.y - 1.2,
        18.5 + balloonPivot.position.z,
        (Math.random() - 0.5) * 5,
        2 + Math.random() * 4,
        (Math.random() - 0.5) * 5,
        0xe0aaff,
        0.45,
        10
      );
    }

    // 8) 과일 화학 전지 덱
    if (lastFruitKind !== fruit.kind) {
      lastFruitKind = fruit.kind;
      const colorObj = new THREE.Color(fruit.output.color);
      fruitCells3D.forEach((c) => {
        c.bodyMat.color.copy(colorObj);
      });
    }
    fruitCells3D.forEach((c, idx) => {
      c.group.visible = idx < fruit.cells;
    });
    fruitLedMat.emissiveIntensity = 0.05 + fruit.output.level * 3.4;
    fruitLedHalo.material.opacity = fruit.output.level * 0.85;

    // 9) 송전선 플라스마 전류 흐름 애니메이션
    const sourceLevels = {
      generator: generator.output.level,
      wind: wind.output.level,
      solar: solar.output.level,
      hydro: hydro.output.level,
      fruit: fruit.output.level,
      townMain: grid.gridRatio,
      townPark: grid.landmarks.ferris || 0,
    };
    lineSystems.forEach((ls) => {
      const lv = sourceLevels[ls.id] || 0;
      const flowing =
        ls.id === "townMain" || ls.id === "townPark"
          ? grid.deliveredWatts > 0.3
          : lv > 0.03;
      ls.wireMat.emissiveIntensity = flowing ? 0.05 + lv * 0.42 : 0.03;
      ls.phase = (ls.phase + dt * (0.28 + lv * 1.35)) % 1;
      ls.pulses.forEach((p) => {
        if (!flowing) {
          p.sprite.material.opacity = 0;
          return;
        }
        const t = (ls.phase + p.offset) % 1;
        const pos = ls.curve.getPointAt(t);
        p.sprite.position.copy(pos);
        p.sprite.material.opacity = 0.35 + lv * 0.65;
        p.sprite.scale.setScalar(1.1 + lv * 1.25);
      });
    });

    // 10) 6단계 밤마을 랜드마크 실시간 점등 & 기구 작동!
    const lm = grid.landmarks;

    // Tier 1: 오두막 창문 & 가로등
    cottageWindows.forEach((mat) => {
      mat.emissiveIntensity += (lm.cottages * 2.5 - mat.emissiveIntensity) * Math.min(1, dt * 6);
    });
    streetLampBulbs.forEach((mat, i) => {
      mat.emissiveIntensity += (lm.cottages * 2.8 - mat.emissiveIntensity) * Math.min(1, dt * 6);
      streetLampHalos[i].material.opacity = lm.cottages * 0.65;
    });
    villageWarmLight.intensity =
      (lm.cottages * 3.0 + lm.ferris * 1.2) * villageWarmLight.userData.gain;
    porchLights.forEach(({ porchMat, halo }) => {
      porchMat.emissiveIntensity += (lm.cottages * 2.6 - porchMat.emissiveIntensity) * Math.min(1, dt * 5);
      halo.opacity = lm.cottages * 0.55;
    });
    smokePuffs.forEach(({ sprite, baseY, phase }) => {
      const t = (performanceNow * 0.42 + phase) % 1;
      sprite.material.opacity = lm.cottages > 0.05 ? 0.34 * Math.sin(Math.PI * t) : 0;
      sprite.position.y = baseY + t * 1.5;
      sprite.position.x = Math.sin(performanceNow * 0.6 + phase * 3) * 0.18;
      const scale = 0.7 + t * 1.5;
      sprite.scale.set(scale, scale, 1);
    });

    // Tier 2: 항구 회전 등대 서치라이트
    lanternCoreMat.emissiveIntensity = lm.harbor * 3.4;
    lanternGlassMat.emissiveIntensity = lm.harbor * 2.2;
    lanternGlassMat.opacity = 0.22 + lm.harbor * 0.4;
    lanternHalo.material.opacity = lm.harbor * 0.7;
    searchBeamMat.uniforms.uOpacity.value = lm.harbor * 0.34;
    searchBeamMat.uniforms.uTime.value = performanceNow;
    searchBeam.rotation.z = performanceNow * 0.22;
    searchBeam.rotation.x = Math.PI / 2 + Math.sin(performanceNow * 0.33) * 0.1;
    if (lm.harbor > 0) {
      lanternHead.rotation.y += dt * (0.9 + lm.harbor * 0.9);
    }

    // Tier 3: 꼬마 전기 기차 주행
    trainWinMat.emissiveIntensity = lm.train * 2.4;
    if (lm.train > 0) {
      trainProgress = (trainProgress + dt * (0.055 + lm.train * 0.11)) % 1;
    }
    trainCars.forEach((car, idx) => {
      const t = (trainProgress - idx * 0.052 + 1) % 1;
      const pt = railCurve.getPointAt(t);
      const ahead = railCurve.getPointAt((t + 0.01) % 1);
      car.position.copy(pt);
      car.lookAt(ahead);
      if (car.userData.headlight) {
        car.userData.headlight.material.uniforms.uOpacity.value = lm.train * 0.85;
        car.userData.headlight.material.uniforms.uTime.value = performanceNow;
      }
      if (car.userData.lampHalo) {
        car.userData.lampHalo.material.opacity = lm.train * 0.7;
      }
      if (car.userData.smoke) {
        car.userData.smoke.forEach((puff, pIdx) => {
          const t = (performanceNow * 0.9 + pIdx * 0.33) % 1;
          puff.material.opacity = lm.train > 0.05 ? 0.32 * Math.sin(Math.PI * t) : 0;
          puff.position.y = 1.75 + t * 1.05;
          puff.position.z = 0.75 + t * 0.55;
          const sc = 0.55 + t * 1.15;
          puff.scale.set(sc, sc, 1);
        });
      }
    });

    // Tier 4: 밤하늘 네온 대관람차 회전
    ferrisNeonMat.emissiveIntensity = lm.ferris * 2.6;
    ferrisInnerMat.emissiveIntensity = lm.ferris * 2.0;
    if (lm.ferris > 0) {
      ferrisAngle += dt * (0.28 + lm.ferris * 0.42);
      ferrisWheel.rotation.z = ferrisAngle;
    }
    gondolas.forEach((g) => {
      g.pivot.rotation.z = -ferrisWheel.rotation.z;
      g.cabinMat.emissiveIntensity = lm.ferris * 2.1;
    });
    ferrisBulbs.forEach((bulb, idx) => {
      const flicker = 0.65 + Math.sin(performanceNow * 2.4 + idx * 0.9) * 0.35;
      bulb.material.opacity = lm.ferris * 0.8 * flicker;
    });
    ferrisLight.intensity = lm.ferris * 2.4 * ferrisLight.userData.gain;

    // Tier 5: 무지개 분수 쇼
    fountainJets.forEach(({ jet, jetMat }, idx) => {
      const pulse = 0.78 + Math.sin(performanceNow * 5 + idx) * 0.22;
      jet.visible = lm.fountain > 0.02;
      jet.scale.y = Math.max(0.1, lm.fountain * pulse);
      jet.position.y = 0.7 + jet.scale.y * 2.1;
      jetMat.opacity = lm.fountain * 0.52;
    });

    // 바닥 빛무리 & 반딧불
    substationGlow.material.opacity = 0.03 + grid.gridRatio * 0.13 + flashBoost * 0.08;
    villageGlow.material.opacity = lm.cottages * 0.16;
    ferrisGlow.material.opacity = lm.ferris * 0.14;
    const glowPulse = 0.94 + Math.sin(performanceNow * 2.2) * 0.06;
    substationGlow.scale.setScalar(glowPulse);
    fireflyMat.opacity = weather === "day" ? 0 : weather === "storm" ? 0.15 : 0.85;
    if (!reducedMotion && weather !== "day") {
      const fPos = fireflyGeo.attributes.position;
      for (let i = 0; i < fireflyCount; i += 1) {
        const seed = fireflySeed[i];
        const t = performanceNow * seed.speed + seed.phase;
        fPos.setXYZ(
          i,
          seed.baseX + Math.sin(t) * 1.8 + Math.sin(t * 2.3) * 0.5,
          seed.baseY + Math.sin(t * 1.4) * 0.7,
          seed.baseZ + Math.cos(t * 0.9) * 1.8
        );
      }
      fPos.needsUpdate = true;
    }

    // Tier 6: 테슬라 아크 & 하늘 불꽃축제 + 폭풍 자연 낙뢰
    if (lm.festival > 0.2) {
      fireworkCooldown -= dt;
      if (fireworkCooldown <= 0) {
        fireworkCooldown = reducedMotion ? 2.6 : 1.35;
        launchFirework(21, -14);
        spawnLightningBolt(
          new THREE.Vector3(-0.5, 14.4, -3.9),
          new THREE.Vector3(
            -0.5 + (Math.random() - 0.5) * 14,
            19 + Math.random() * 6,
            -3.9 + (Math.random() - 0.5) * 14
          ),
          0xd7ff00,
          0.26
        );
      }
    }

    if (weather === "storm") {
      stormBoltCooldown -= dt;
      if (stormBoltCooldown <= 0) {
        stormBoltCooldown = 2.4 + Math.random() * 2.4;
        spawnLightningBolt(
          new THREE.Vector3(-4 + (Math.random() - 0.5) * 18, 44, -4),
          new THREE.Vector3(-0.5, 14.4, -3.9),
          0xbaf7ff,
          0.36
        );
        flashBoost = 0.9;
      }
    }

    // 번개 선분 수명 갱신
    for (let i = lightningBolts.length - 1; i >= 0; i -= 1) {
      const bolt = lightningBolts[i];
      bolt.life -= dt;
      if (bolt.life <= 0) {
        scene.remove(bolt.line);
        bolt.geo.dispose();
        bolt.mat.dispose();
        lightningBolts.splice(i, 1);
      } else {
        bolt.mat.opacity = bolt.life / bolt.maxLife;
      }
    }

    // 스파크 & 불꽃 입자 물리 갱신
    let anySparkAlive = false;
    for (let i = 0; i < sparkPoolSize; i += 1) {
      const st = sparkState[i];
      if (st.life <= 0) continue;
      anySparkAlive = true;
      st.life -= dt;
      if (st.life <= 0) {
        sparkPositions[i * 3 + 1] = -999;
        continue;
      }
      st.vy -= st.gravity * dt;
      sparkPositions[i * 3] += st.vx * dt;
      sparkPositions[i * 3 + 1] += st.vy * dt;
      sparkPositions[i * 3 + 2] += st.vz * dt;
    }
    if (anySparkAlive) {
      sparkGeo.attributes.position.needsUpdate = true;
      sparkGeo.attributes.color.needsUpdate = true;
    }

    // 해무 표류 & 달빛 물길의 잔물결
    hazeSprites.forEach((h, idx) => {
      const drift = Math.sin(performanceNow * 0.12 + h.phase) * 1.6;
      h.sprite.position.x = h.baseX + drift;
      h.sprite.position.z = h.baseZ + Math.cos(performanceNow * 0.09 + h.phase) * 1.1;
      h.sprite.material.opacity =
        (0.028 + 0.016 * Math.sin(performanceNow * 0.35 + h.phase)) * (idx % 2 ? 0.9 : 1);
      h.sprite.material.color.copy(atmo.horizon).lerp(atmo.fog, 0.5).multiplyScalar(1.15);
    });
    moonGlitter.material.opacity = 0.17 + 0.05 * Math.sin(performanceNow * 0.9);
    glitterSheen.material.opacity = 0.09 + 0.04 * Math.sin(performanceNow * 1.35 + 1.4);
    shoreWash.material.opacity = 0.13 + 0.04 * Math.sin(performanceNow * 0.7);

    // 카메라 트윈 보간
    if (cameraTween && controls) {
      cameraTween.elapsed += dt;
      const t = easeInOutCubic(Math.min(1, cameraTween.elapsed / cameraTween.duration));
      camera.position.lerpVectors(cameraTween.fromPos, cameraTween.toPos, t);
      controls.target.lerpVectors(cameraTween.fromTarget, cameraTween.toTarget, t);
      if (t >= 1) cameraTween = null;
    }

    if (controls) controls.update();
    trackFrameBudget(dt);
    if (composer) composer.render();
    else if (renderer) renderer.render(scene, camera);
  }

  const resolution = {
    max: Math.min(typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1, 1.6),
    current: 0,
    sampleTime: 0,
    sampleFrames: 0,
  };
  resolution.current = resolution.max;

  function updateGradeTexel(w, h) {
    if (!gradePass) return;
    const texel = gradePass.uniforms.uTexel;
    if (texel) texel.value.set(1 / Math.max(1, w), 1 / Math.max(1, h));
  }

  function applyPixelRatio() {
    if (!renderer) return;
    renderer.setPixelRatio(resolution.current);
    const rect = canvas.getBoundingClientRect();
    const w = Math.max(280, Math.round(rect.width || canvas.clientWidth || 1280));
    const h = Math.max(200, Math.round(rect.height || canvas.clientHeight || 800));
    renderer.setSize(w, h, false);
    if (composer) composer.setSize(w, h);
    if (bloomPass) bloomPass.setSize(w, h);
    updateGradeTexel(w, h);
  }

  // 태블릿에서 프레임이 흔들리면 해상도를 한 단계 낮춰 부드러움을 우선한다
  function trackFrameBudget(dt) {
    if (!renderer || reducedMotion) return;
    resolution.sampleTime += dt;
    resolution.sampleFrames += 1;
    if (resolution.sampleFrames < 90) return;
    const average = resolution.sampleTime / resolution.sampleFrames;
    resolution.sampleTime = 0;
    resolution.sampleFrames = 0;
    if (average > 0.028 && resolution.current > 1.0) {
      resolution.current = Math.max(1, resolution.current - 0.25);
      applyPixelRatio();
    }
  }

  function resize() {
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const w = Math.max(280, Math.round(rect.width || canvas.clientWidth || 1280));
    const h = Math.max(200, Math.round(rect.height || canvas.clientHeight || 800));
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    if (renderer) {
      renderer.setPixelRatio(resolution.current);
      renderer.setSize(w, h, false);
    }
    if (composer) composer.setSize(w, h);
    if (bloomPass) bloomPass.setSize(w, h);
    updateGradeTexel(w, h);
  }

  if (typeof window !== "undefined") {
    window.addEventListener("resize", resize);
    if (window.ResizeObserver && canvas) {
      new window.ResizeObserver(resize).observe(canvas);
    }
  }

  const projScratch = new THREE.Vector3();
  function projectAnchors(viewportWidth, viewportHeight) {
    const out = {};
    camera.updateMatrixWorld();
    Object.keys(WORLD_ANCHORS).forEach((key) => {
      projScratch.set(...WORLD_ANCHORS[key]);
      projScratch.project(camera);
      out[key] = {
        visible: projScratch.z < 1 && Math.abs(projScratch.x) < 1.05 && Math.abs(projScratch.y) < 1.05,
        x: (projScratch.x * 0.5 + 0.5) * viewportWidth,
        y: (-projScratch.y * 0.5 + 0.5) * viewportHeight,
      };
    });
    return out;
  }

  /* ── 14-b. 접지 그림자 인스턴스 ────────────────────────────── */

  if (contactShadowSpots.length) {
    const shadowGeo = new THREE.PlaneGeometry(1, 1);
    shadowGeo.rotateX(-Math.PI / 2);
    const shadowMat = new THREE.MeshBasicMaterial({
      map: textures.shadowBlob,
      transparent: true,
      opacity: 0.6,
      depthWrite: false,
      toneMapped: false,
      polygonOffset: true,
      polygonOffsetFactor: -2,
      polygonOffsetUnits: -2,
    });
    shadowMat.color.setHex(0x04060c);
    const contactShadows = new THREE.InstancedMesh(
      shadowGeo,
      shadowMat,
      contactShadowSpots.length
    );
    const shadowDummy = new THREE.Object3D();
    contactShadowSpots.forEach((spot, idx) => {
      shadowDummy.position.set(spot.x, spot.y, spot.z);
      shadowDummy.rotation.set(0, (idx % 7) * 0.42, 0);
      const r = spot.radius;
      shadowDummy.scale.set(r * 2.1, 1, r * 1.9);
      shadowDummy.updateMatrix();
      contactShadows.setMatrixAt(idx, shadowDummy.matrix);
    });
    contactShadows.name = "contact-shadows";
    contactShadows.instanceMatrix.needsUpdate = true;
    contactShadows.frustumCulled = false;
    contactShadows.renderOrder = 2;
    scene.add(contactShadows);
  }

  /* ── 15. 표면 요철 자동 배선 ─────────────────────────────────── */

  // 알베도 텍스처를 공유하는 모든 재질에 같은 결의 노멀맵을 붙인다.
  // 재질 생성 지점을 수십 군데 고치지 않아도 지면·목재·기와·석조가 조명을
  // 받을 때 실제 요철로 반응해, 평면 색종이처럼 보이던 표면이 살아난다.
  const surfaceNormalSets = [
    [textures.grass, textures.grassNormal, 0.9],
    [textures.sand, textures.sandNormal, 0.85],
    [textures.rock, textures.rockNormal, 1.15],
    [textures.roof, textures.roofNormal, 0.9],
    [textures.wood, textures.woodNormal, 0.85],
    [textures.cobble, textures.cobbleNormal, 1.0],
    [textures.stone, textures.stoneNormal, 0.9],
  ];
  const normalByAlbedo = new Map();
  surfaceNormalSets.forEach(([albedo, normal, scale]) => {
    if (albedo && normal) normalByAlbedo.set(albedo, { normal, scale });
  });
  const seenSurfaceMaterials = new Set();
  scene.traverse((obj) => {
    if (!obj.material) return;
    const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
    mats.forEach((mat) => {
      if (!mat || seenSurfaceMaterials.has(mat) || mat.normalMap || !mat.map) return;
      seenSurfaceMaterials.add(mat);
      const entry = normalByAlbedo.get(mat.map);
      if (!entry) return;
      mat.normalMap = entry.normal;
      if (!mat.normalScale) mat.normalScale = new THREE.Vector2(entry.scale, entry.scale);
      mat.needsUpdate = true;
    });
  });

  if (typeof window !== "undefined") {
    window.__islandDebug = {
      scene, camera, renderer, composer, bloomPass, gradePass, mainLight, hemiLight, rimLight,
      warmFill, ATMOSPHERES, applyAtmosphere, focusZone, controls,
    };
  }

  return {
    scene,
    camera,
    controls,
    focusZone,
    resize,
    step,
    triggerTeslaSpectacle,
    launchFirework,
    projectAnchors,
    dispose() {
      textures.dispose();
      if (controls) controls.dispose();
      if (envTarget) envTarget.dispose();
      if (pmrem) pmrem.dispose();
      if (renderer) renderer.dispose();
    },
  };
}
