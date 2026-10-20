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
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

import { createIslandTextures } from "./textures.js";

const TAU = Math.PI * 2;
const DEG = Math.PI / 180;

export const CAMERA_PRESETS = Object.freeze({
  overview: {
    label: "섬 전체보기",
    position: [9.5, 37.5, 63],
    target: [8.0, 6.2, -3.5],
  },
  generator: {
    label: "크랭크 발전 광장",
    position: [3.5, 9.8, 29.5],
    target: [-1, 4.8, 14.5],
  },
  wind: {
    label: "해안 풍력 절벽",
    position: [-14.5, 16.5, 22],
    target: [-27.5, 11.5, 4.5],
  },
  solar: {
    label: "해바라기 태양광",
    position: [-8.5, 12.2, 31],
    target: [-14.5, 5.2, 15.5],
  },
  hydro: {
    label: "폭포 수력 댐",
    position: [-9.5, 15.5, -1.5],
    target: [-21, 8.2, -16],
  },
  circuit: {
    label: "중앙 변전소",
    position: [5.5, 12.8, 14.5],
    target: [-0.5, 5.8, -0.5],
  },
  static: {
    label: "정전기 부두",
    position: [16.5, 9.5, 31.5],
    target: [12.5, 4.4, 18.5],
  },
  fruit: {
    label: "과일 전지 덱",
    position: [31, 11.2, 26.5],
    target: [24.5, 4.5, 13.5],
  },
  village: {
    label: "네온 밤마을",
    position: [33, 21.5, 16],
    target: [21, 8.8, -10.5],
  },
});

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

function makePineTree(scale = 1, tint = 0x1e6b4b) {
  const group = new THREE.Group();
  const trunk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.18 * scale, 0.28 * scale, 1.3 * scale, 7),
    new THREE.MeshStandardMaterial({ color: 0x5d3d26, roughness: 0.9 })
  );
  trunk.position.y = 0.65 * scale;
  trunk.castShadow = true;
  group.add(trunk);

  const foliageMat = new THREE.MeshStandardMaterial({
    color: tint,
    roughness: 0.78,
    flatShading: true,
  });
  for (let tier = 0; tier < 3; tier += 1) {
    const cone = new THREE.Mesh(
      new THREE.ConeGeometry((1.35 - tier * 0.28) * scale, (1.7 - tier * 0.2) * scale, 7),
      foliageMat
    );
    cone.position.y = (1.6 + tier * 0.92) * scale;
    cone.castShadow = true;
    cone.receiveShadow = true;
    group.add(cone);
  }
  return group;
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
  let controls = null;

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
        renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        renderer.setSize(widthInitial, heightInitial, false);
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.06;
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;

        composer = new EffectComposer(renderer);
        const renderPass = new RenderPass(scene, camera);
        composer.addPass(renderPass);
        bloomPass = new UnrealBloomPass(
          new THREE.Vector2(widthInitial, heightInitial),
          reducedMotion ? 0.45 : 0.68,
          0.48,
          0.78
        );
        composer.addPass(bloomPass);
        composer.addPass(new OutputPass());
      } catch {
        renderer = null;
        composer = null;
      }
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

  scene.fog = new THREE.FogExp2(0x09162e, 0.0052);

  const skyGeo = new THREE.SphereGeometry(320, 32, 20);
  const skyPos = skyGeo.attributes.position;
  const skyColors = new Float32Array(skyPos.count * 3);
  skyGeo.setAttribute("color", new THREE.BufferAttribute(skyColors, 3));
  const skyMat = new THREE.MeshBasicMaterial({
    vertexColors: true,
    side: THREE.BackSide,
    depthWrite: false,
    fog: false,
  });
  const skyDome = new THREE.Mesh(skyGeo, skyMat);
  skyDome.frustumCulled = false;
  scene.add(skyDome);

  const starCount = 520;
  const starPositions = new Float32Array(starCount * 3);
  const starColors = new Float32Array(starCount * 3);
  const starPalette = [
    new THREE.Color(0xffffff),
    new THREE.Color(0xbcd8ff),
    new THREE.Color(0xffe6b3),
    new THREE.Color(0xd7ff7a),
  ];
  for (let i = 0; i < starCount; i += 1) {
    const r = 185 + (i % 7) * 14;
    const u = 0.12 + ((i * 73) % 88) / 100;
    const theta = ((i * 137.508) % 360) * DEG;
    const ring = Math.sqrt(Math.max(0, 1 - u * u));
    starPositions[i * 3] = r * ring * Math.cos(theta);
    starPositions[i * 3 + 1] = r * u;
    starPositions[i * 3 + 2] = r * ring * Math.sin(theta);
    const c = starPalette[i % starPalette.length];
    starColors[i * 3] = c.r;
    starColors[i * 3 + 1] = c.g;
    starColors[i * 3 + 2] = c.b;
  }
  const starGeo = new THREE.BufferGeometry();
  starGeo.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
  starGeo.setAttribute("color", new THREE.BufferAttribute(starColors, 3));
  const starMat = new THREE.PointsMaterial({
    size: 2.3,
    map: textures.glow,
    vertexColors: true,
    transparent: true,
    opacity: 0.9,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    fog: false,
  });
  const starField = new THREE.Points(starGeo, starMat);
  starField.frustumCulled = false;
  scene.add(starField);

  const moonGroup = new THREE.Group();
  const moonMesh = new THREE.Mesh(
    new THREE.SphereGeometry(3.4, 24, 24),
    new THREE.MeshBasicMaterial({ color: 0xf4f7ff, fog: false })
  );
  moonGroup.add(moonMesh);
  const moonHalo = makeGlowSprite(textures.glow, 0xa8c8ff, 18, 0.42);
  moonGroup.add(moonHalo);
  moonGroup.position.set(54, 58, -74);
  scene.add(moonGroup);

  // 조명 시스템
  const hemiLight = new THREE.HemisphereLight(0x5d88d6, 0x18263a, 0.85);
  scene.add(hemiLight);

  const mainLight = new THREE.DirectionalLight(0xaad0ff, 1.35);
  mainLight.position.set(-28, 42, 26);
  mainLight.castShadow = true;
  mainLight.shadow.mapSize.set(2048, 2048);
  mainLight.shadow.camera.near = 6;
  mainLight.shadow.camera.far = 140;
  mainLight.shadow.camera.left = -48;
  mainLight.shadow.camera.right = 48;
  mainLight.shadow.camera.top = 42;
  mainLight.shadow.camera.bottom = -42;
  mainLight.shadow.bias = -0.0006;
  scene.add(mainLight);

  const rimLight = new THREE.DirectionalLight(0x52c4ff, 0.42);
  rimLight.position.set(36, 20, -34);
  scene.add(rimLight);

  const villageWarmLight = new THREE.PointLight(0xffb85c, 0, 38, 1.6);
  villageWarmLight.position.set(20, 9.5, -6);
  scene.add(villageWarmLight);

  const substationLight = new THREE.PointLight(0xd7ff00, 1.2, 26, 1.6);
  substationLight.position.set(0, 7.5, 0);
  scene.add(substationLight);

  const crankGlowLight = new THREE.PointLight(0xffb449, 0.4, 20, 1.6);
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

  // 잔잔히 일렁이는 바다 평면
  const seaGeo = new THREE.PlaneGeometry(420, 420, 48, 48);
  seaGeo.rotateX(-Math.PI / 2);
  const seaBaseY = new Float32Array(seaGeo.attributes.position.count);
  for (let i = 0; i < seaBaseY.length; i += 1) {
    seaBaseY[i] = seaGeo.attributes.position.getY(i);
  }
  const seaMat = new THREE.MeshStandardMaterial({
    color: 0x0b3a66,
    emissive: 0x06203c,
    emissiveIntensity: 0.45,
    roughness: 0.22,
    metalness: 0.55,
    flatShading: true,
  });
  const ocean = new THREE.Mesh(seaGeo, seaMat);
  ocean.position.y = 0;
  ocean.receiveShadow = true;
  scene.add(ocean);

  // 섬 둘레 에메랄드 얕은 산호초 링
  const reefRing = new THREE.Mesh(
    sculptedIslandGeometry(41.5, 44.5, 0.5, 42, 0.12),
    new THREE.MeshStandardMaterial({
      color: 0x1985a1,
      emissive: 0x0b4f6c,
      emissiveIntensity: 0.45,
      transparent: true,
      opacity: 0.55,
      roughness: 0.25,
    })
  );
  reefRing.position.y = -0.08;
  scene.add(reefRing);

  // 섬 모래 해변 층 + 암벽 기반 + 잔디 대지
  const sandBase = new THREE.Mesh(
    sculptedIslandGeometry(37.2, 40.2, 1.5, 40, 0.13),
    new THREE.MeshStandardMaterial({ color: 0xc9ab76, roughness: 0.92, flatShading: true })
  );
  sandBase.position.y = 0.55;
  sandBase.receiveShadow = true;
  scene.add(sandBase);

  const grassPlateau = new THREE.Mesh(
    sculptedIslandGeometry(34.5, 36.6, 2.2, 40, 0.12),
    new THREE.MeshStandardMaterial({ color: 0x1d5f46, roughness: 0.86, flatShading: true })
  );
  grassPlateau.position.y = 1.18;
  grassPlateau.castShadow = true;
  grassPlateau.receiveShadow = true;
  scene.add(grassPlateau);

  // 서쪽 풍력 해안 절벽 대지
  const windBluff = new THREE.Mesh(
    sculptedIslandGeometry(11.5, 13.8, 3.2, 20, 0.1),
    new THREE.MeshStandardMaterial({ color: 0x267353, roughness: 0.84, flatShading: true })
  );
  windBluff.position.set(-27.5, 3.2, 4.5);
  windBluff.castShadow = true;
  windBluff.receiveShadow = true;
  scene.add(windBluff);

  // 북서쪽 수력 화강암 산악 지형
  const hydroMountain = new THREE.Mesh(
    new THREE.DodecahedronGeometry(11.5, 1),
    new THREE.MeshStandardMaterial({
      color: 0x45536b,
      map: textures.stone,
      roughness: 0.88,
      flatShading: true,
    })
  );
  hydroMountain.position.set(-25.5, 7.2, -21.5);
  hydroMountain.scale.set(1.25, 1.18, 1.05);
  hydroMountain.castShadow = true;
  hydroMountain.receiveShadow = true;
  scene.add(hydroMountain);

  const snowCap = new THREE.Mesh(
    new THREE.ConeGeometry(5.6, 4.4, 8),
    new THREE.MeshStandardMaterial({ color: 0xdce8f8, roughness: 0.72, flatShading: true })
  );
  snowCap.position.set(-26.5, 16.4, -22.5);
  snowCap.castShadow = true;
  scene.add(snowCap);

  // 동쪽 마을 석조 테라스
  const villageTerrace = new THREE.Mesh(
    sculptedIslandGeometry(16.2, 17.4, 0.9, 28, 0.08),
    new THREE.MeshStandardMaterial({
      color: 0x3b4861,
      map: textures.stone,
      roughness: 0.82,
      flatShading: true,
    })
  );
  villageTerrace.position.set(20.5, 2.35, -7.5);
  villageTerrace.receiveShadow = true;
  scene.add(villageTerrace);

  // 남동쪽 정전기 나무 부두 & 동쪽 과일 전지 나무 덱
  const pierDeck = new THREE.Mesh(
    new THREE.BoxGeometry(11.5, 0.65, 11.5),
    new THREE.MeshStandardMaterial({ color: 0x8b5e3c, map: textures.wood, roughness: 0.8 })
  );
  pierDeck.position.set(12.5, 2.25, 18.5);
  pierDeck.receiveShadow = true;
  pierDeck.castShadow = true;
  scene.add(pierDeck);

  const fruitDeck = new THREE.Mesh(
    new THREE.BoxGeometry(13.5, 0.8, 10.5),
    new THREE.MeshStandardMaterial({ color: 0x7c5436, map: textures.wood, roughness: 0.8 })
  );
  fruitDeck.position.set(24.8, 2.35, 13.5);
  fruitDeck.receiveShadow = true;
  fruitDeck.castShadow = true;
  scene.add(fruitDeck);

  // 중앙 변전소 원형 석조 광장 & 남쪽 크랭크 발명가 광장
  const hubPlaza = new THREE.Mesh(
    new THREE.CylinderGeometry(8.2, 8.8, 0.85, 8),
    new THREE.MeshStandardMaterial({ color: 0x2b3952, map: textures.stone, roughness: 0.75 })
  );
  hubPlaza.position.set(-0.5, 2.35, -0.5);
  hubPlaza.receiveShadow = true;
  scene.add(hubPlaza);

  const crankPlaza = new THREE.Mesh(
    new THREE.CylinderGeometry(6.8, 7.4, 0.75, 16),
    new THREE.MeshStandardMaterial({ color: 0x32425e, map: textures.stone, roughness: 0.75 })
  );
  crankPlaza.position.set(-1, 2.3, 14.5);
  crankPlaza.receiveShadow = true;
  scene.add(crankPlaza);

  // 자연 침엽수 숲 배치 (발전소와 마을을 감싸는 미니어처 디테일)
  const treeCoords = [
    [-12, 2.2, -22, 1.15],
    [-8, 2.2, -19, 0.9],
    [-33, 2.2, -12, 1.05],
    [-19, 4.6, 11, 0.85],
    [-6, 2.2, 25, 0.95],
    [6, 2.2, -23, 1.1],
    [10, 2.2, -20, 0.88],
    [32, 2.2, 3, 1.0],
    [34, 2.2, -15, 0.92],
    [8, 2.2, 8, 0.82],
  ];
  treeCoords.forEach(([tx, ty, tz, ts], idx) => {
    const tree = makePineTree(ts, idx % 2 === 0 ? 0x1e7450 : 0x25845c);
    tree.position.set(tx, ty, tz);
    scene.add(tree);
  });

  /* ── 3. 중앙 변전소 · 주 회로 스위치 · 플라스마 축전기 · 테슬라 코일 ── */

  const substationGroup = new THREE.Group();
  substationGroup.position.set(-0.5, 2.75, -0.5);
  scene.add(substationGroup);

  const copperMat = new THREE.MeshStandardMaterial({
    color: 0xe6843a,
    metalness: 0.78,
    roughness: 0.26,
  });
  const darkMetalMat = new THREE.MeshStandardMaterial({
    color: 0x1b263b,
    metalness: 0.62,
    roughness: 0.38,
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
      color: 0xc96f2d,
      emissive: 0xff8c2b,
      emissiveIntensity: 0.3,
      metalness: 0.72,
      roughness: 0.28,
    })
  );
  teslaColumn.position.y = 5.8;
  teslaColumn.castShadow = true;
  teslaGroup.add(teslaColumn);

  for (let r = 0; r < 6; r += 1) {
    const primaryRing = new THREE.Mesh(new THREE.TorusGeometry(1.55 + r * 0.12, 0.07, 8, 28), copperMat);
    primaryRing.rotation.x = Math.PI / 2;
    primaryRing.position.y = 1.45 + r * 0.22;
    teslaGroup.add(primaryRing);
  }

  const teslaToroidMat = new THREE.MeshStandardMaterial({
    color: 0xeaf4ff,
    emissive: 0x6ce5ff,
    emissiveIntensity: 0.85,
    metalness: 0.9,
    roughness: 0.12,
  });
  const teslaToroid = new THREE.Mesh(new THREE.TorusGeometry(2.15, 0.68, 16, 36), teslaToroidMat);
  teslaToroid.rotation.x = Math.PI / 2;
  teslaToroid.position.y = 10.9;
  teslaToroid.castShadow = true;
  teslaGroup.add(teslaToroid);

  const teslaCrownOrb = new THREE.Mesh(
    new THREE.SphereGeometry(0.85, 20, 20),
    new THREE.MeshBasicMaterial({ color: 0xe6ffff })
  );
  teslaCrownOrb.position.y = 11.7;
  teslaGroup.add(teslaCrownOrb);
  const teslaHalo = makeGlowSprite(textures.glow, 0x72f5ff, 11, 0.6);
  teslaHalo.position.y = 11.4;
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
  const circuitBulb = new THREE.Mesh(new THREE.SphereGeometry(1.05, 20, 20), circuitBulbMat);
  circuitBulb.position.set(4.5, 6.4, -1.6);
  substationGroup.add(circuitBulb);
  const circuitBulbHalo = makeGlowSprite(textures.glow, 0xffd85c, 6.5, 0.55);
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
      color: 0xd7ff00,
      emissive: 0xa8d900,
      emissiveIntensity: 0.85,
      metalness: 0.45,
      roughness: 0.25,
    })
  );
  flywheelRim.castShadow = true;
  crankWheelPivot.add(flywheelRim);

  const spokeMat = new THREE.MeshStandardMaterial({
    color: 0x334155,
    metalness: 0.78,
    roughness: 0.34,
  });
  for (let s = 0; s < 4; s += 1) {
    const spoke = new THREE.Mesh(new THREE.BoxGeometry(5.5, 0.24, 0.2), spokeMat);
    spoke.rotation.z = (s * Math.PI) / 4;
    crankWheelPivot.add(spoke);
  }

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
  const crankGripHalo = makeGlowSprite(textures.glow, 0xd7ff00, 3.4, 0.65);
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
  const dynamoBulb = new THREE.Mesh(new THREE.SphereGeometry(1.15, 20, 20), dynamoBulbMat);
  dynamoBulb.position.set(-2.9, 6.2, 0);
  crankGroup.add(dynamoBulb);
  const dynamoBulbPedestal = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.65, 2.2, 12), darkMetalMat);
  dynamoBulbPedestal.position.set(-2.9, 4.4, 0);
  crankGroup.add(dynamoBulbPedestal);
  const dynamoBulbHalo = makeGlowSprite(textures.glow, 0xffbe55, 7.2, 0.0);
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
  const turbines = [];
  const bladeMaterial = new THREE.MeshStandardMaterial({
    color: 0xf1f7ff,
    emissive: 0x3bf0c5,
    emissiveIntensity: 0.14,
    roughness: 0.28,
    metalness: 0.18,
  });

  function populateRotorBlades(rotor, count, bladeScale) {
    while (rotor.children.length) {
      const old = rotor.children.pop();
      if (old.geometry) old.geometry.dispose();
    }
    const len = 3.2 + bladeScale * 4.2;
    for (let i = 0; i < count; i += 1) {
      const holder = new THREE.Group();
      holder.rotation.z = (i / count) * TAU;
      const bladeGeo = new THREE.ConeGeometry(0.46, len, 6);
      bladeGeo.scale(1, 1, 0.24);
      const blade = new THREE.Mesh(bladeGeo, bladeMaterial);
      blade.position.y = len * 0.5 + 0.35;
      blade.rotation.y = 0.22;
      blade.castShadow = true;
      holder.add(blade);
      rotor.add(holder);
    }
  }

  turbineSpecs.forEach((spec) => {
    const unit = new THREE.Group();
    unit.position.set(spec.x, spec.y, spec.z);
    windGroup.add(unit);

    const tower = new THREE.Mesh(
      new THREE.CylinderGeometry(0.42 * spec.scale, 0.92 * spec.scale, spec.towerH, 16),
      new THREE.MeshStandardMaterial({ color: 0xe6eefc, roughness: 0.35, metalness: 0.25 })
    );
    tower.position.y = spec.towerH * 0.5;
    tower.castShadow = true;
    unit.add(tower);

    const nacelle = new THREE.Mesh(
      new THREE.BoxGeometry(1.4 * spec.scale, 1.3 * spec.scale, 2.7 * spec.scale),
      new THREE.MeshStandardMaterial({ color: 0xd6e4ff, roughness: 0.3, metalness: 0.3 })
    );
    nacelle.position.y = spec.towerH;
    nacelle.castShadow = true;
    unit.add(nacelle);

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
      new THREE.BoxGeometry(5.5 + (i % 4) * 1.8, 0.12, 0.18),
      new THREE.MeshBasicMaterial({
        color: 0x7ef7e1,
        transparent: true,
        opacity: 0.32,
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
  const solarPanelMat = new THREE.MeshStandardMaterial({
    color: 0x102a63,
    map: textures.solar,
    emissive: 0x1d4ed8,
    emissiveIntensity: 0.2,
    roughness: 0.22,
    metalness: 0.72,
  });

  for (let i = 0; i < 4; i += 1) {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const mount = new THREE.Group();
    mount.position.set((col - 0.5) * 5.2, 0, (row - 0.5) * 4.6);
    solarGroup.add(mount);

    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.36, 2.2, 10), darkMetalMat);
    post.position.y = 1.1;
    post.castShadow = true;
    mount.add(post);

    const pivot = new THREE.Group();
    pivot.position.y = 2.25;
    mount.add(pivot);

    const frame = new THREE.Mesh(new THREE.BoxGeometry(4.42, 0.14, 3.32), chromeMat);
    pivot.add(frame);

    const plate = new THREE.Mesh(new THREE.BoxGeometry(4.16, 0.19, 3.06), solarPanelMat);
    plate.castShadow = true;
    plate.receiveShadow = true;
    pivot.add(plate);
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
    new THREE.SphereGeometry(3.2, 24, 24),
    new THREE.MeshBasicMaterial({ color: 0xffe066, fog: false })
  );
  sunOrbGroup.add(sunSphere);

  const sunCorona = makeGlowSprite(textures.glow, 0xffbe3b, 20, 0.85);
  sunOrbGroup.add(sunCorona);

  const sunHit = new THREE.Mesh(
    new THREE.SphereGeometry(7.2, 10, 10),
    new THREE.MeshBasicMaterial({ visible: false })
  );
  sunOrbGroup.add(sunHit);
  registerHit(sunHit, "solar", "sun");

  // 태양 → 태양광 테라스 빛 기둥
  const sunBeamMat = new THREE.MeshBasicMaterial({
    color: 0xffe484,
    transparent: true,
    opacity: 0.12,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  const sunBeam = new THREE.Mesh(new THREE.CylinderGeometry(1.8, 6.2, 42, 14, 1, true), sunBeamMat);
  scene.add(sunBeam);

  // 하늘 구름 클러스터
  const cloudGroups = [];
  const cloudMat = new THREE.MeshStandardMaterial({
    color: 0xd8e4f8,
    roughness: 0.92,
    transparent: true,
    opacity: 0.0,
    flatShading: true,
  });
  for (let c = 0; c < 5; c += 1) {
    const cg = new THREE.Group();
    for (let puff = 0; puff < 4; puff += 1) {
      const pMesh = new THREE.Mesh(
        new THREE.DodecahedronGeometry(2.6 + (puff % 2) * 1.1, 1),
        cloudMat
      );
      pMesh.position.set((puff - 1.5) * 2.5, (puff % 2) * 0.7, (puff % 3 - 1) * 1.1);
      cg.add(pMesh);
    }
    cg.position.set(-30 + c * 15, 29 + (c % 2) * 3.5, 4 + (c % 3) * 6);
    scene.add(cg);
    cloudGroups.push(cg);
  }

  /* ── 7. 폭포 수력 발전 댐 · 저수지 · 물레바퀴 (North-West) ────── */

  const hydroGroup = new THREE.Group();
  hydroGroup.position.set(-21, 2.2, -16);
  scene.add(hydroGroup);

  const damWall = new THREE.Mesh(
    new THREE.BoxGeometry(10.5, 11.2, 2.6),
    new THREE.MeshStandardMaterial({ color: 0x67758c, map: textures.stone, roughness: 0.82 })
  );
  damWall.position.set(0, 5.6, -2.2);
  damWall.castShadow = true;
  damWall.receiveShadow = true;
  hydroGroup.add(damWall);

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
  reservoirWater.position.set(0, 6.2, -6.5);
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
  sluiceGate.position.set(1.2, 6.8, -0.7);
  hydroGroup.add(sluiceGate);

  const waterfallMat = new THREE.MeshStandardMaterial({
    color: 0x8be0ff,
    emissive: 0x3db5ff,
    emissiveIntensity: 0.75,
    transparent: true,
    opacity: 0.78,
    roughness: 0.12,
  });
  const waterfallStream = new THREE.Mesh(new THREE.CylinderGeometry(0.85, 1.35, 8.6, 12), waterfallMat);
  waterfallStream.position.set(1.2, 3.8, 1.2);
  waterfallStream.rotation.x = 0.28;
  hydroGroup.add(waterfallStream);

  // 대형 목재·황동 수차 바퀴
  const waterWheel = new THREE.Group();
  waterWheel.position.set(2.4, 3.4, 3.2);
  hydroGroup.add(waterWheel);

  for (let side of [-0.75, 0.75]) {
    const rim = new THREE.Mesh(
      new THREE.TorusGeometry(2.9, 0.2, 10, 28),
      new THREE.MeshStandardMaterial({ color: 0x9b6b43, roughness: 0.7 })
    );
    rim.position.x = side;
    rim.rotation.y = Math.PI / 2;
    waterWheel.add(rim);
  }
  for (let p = 0; p < 10; p += 1) {
    const bucketHolder = new THREE.Group();
    bucketHolder.rotation.x = (p / 10) * TAU;
    const paddle = new THREE.Mesh(
      new THREE.BoxGeometry(1.55, 0.18, 0.95),
      new THREE.MeshStandardMaterial({
        color: p % 2 === 0 ? 0xd9ecff : 0x7aaee8,
        roughness: 0.4,
      })
    );
    paddle.position.z = 2.85;
    bucketHolder.add(paddle);
    waterWheel.add(bucketHolder);
  }

  const hydroHouse = new THREE.Mesh(new THREE.BoxGeometry(3.8, 3.2, 3.4), darkMetalMat);
  hydroHouse.position.set(6.0, 1.6, 3.2);
  hydroHouse.castShadow = true;
  hydroGroup.add(hydroHouse);

  const hydroBeaconMat = new THREE.MeshStandardMaterial({
    color: 0x8ce2ff,
    emissive: 0x38bdf8,
    emissiveIntensity: 0.5,
  });
  const hydroBeacon = new THREE.Mesh(new THREE.SphereGeometry(0.65, 16, 16), hydroBeaconMat);
  hydroBeacon.position.set(6.0, 3.65, 3.2);
  hydroGroup.add(hydroBeacon);

  // 물방울 & 물보라 파티클 풀
  const hydroDropCount = 72;
  const hydroDropGeo = new THREE.BufferGeometry();
  const hydroDropPos = new Float32Array(hydroDropCount * 3);
  const hydroDropVel = new Float32Array(hydroDropCount * 3);
  for (let i = 0; i < hydroDropCount; i += 1) {
    hydroDropPos[i * 3] = -19.8 + ((i % 7) - 3) * 0.25;
    hydroDropPos[i * 3 + 1] = 2.5 + (i % 12) * 0.7;
    hydroDropPos[i * 3 + 2] = -14.8 + ((i % 5) - 2) * 0.25;
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

  const balloonAura = makeGlowSprite(textures.glow, 0xc77dff, 6.8, 0.0);
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
  const fruitLedHalo = makeGlowSprite(textures.glow, 0xff4d6d, 6.2, 0.0);
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

  // 6채의 아기자기한 유럽풍 3D 오두막과 상점
  const houseSpecs = [
    { x: 13.5, z: -3.5, w: 3.1, h: 2.6, d: 2.8, roof: 0xe05652, wall: 0x2b3a55, rot: 0.25 },
    { x: 16.5, z: -11.5, w: 3.4, h: 3.2, d: 3.0, roof: 0x3b82f6, wall: 0x33415c, rot: -0.35 },
    { x: 24.5, z: -3.2, w: 3.0, h: 2.5, d: 2.7, roof: 0xeab308, wall: 0x3d3b63, rot: -0.6 },
    { x: 26.8, z: -10.8, w: 3.5, h: 3.6, d: 3.1, roof: 0xec4899, wall: 0x46344e, rot: -1.1 },
    { x: 12.2, z: -10.2, w: 2.8, h: 2.4, d: 2.6, roof: 0x10b981, wall: 0x284b63, rot: 0.65 },
    { x: 20.5, z: 1.4, w: 3.6, h: 2.8, d: 2.9, roof: 0xf97316, wall: 0x4a3e38, rot: 2.8 },
  ];

  houseSpecs.forEach((hs) => {
    const house = new THREE.Group();
    house.position.set(hs.x, 2.8, hs.z);
    house.rotation.y = hs.rot;
    villageGroup.add(house);

    const wall = new THREE.Mesh(
      new THREE.BoxGeometry(hs.w, hs.h, hs.d),
      new THREE.MeshStandardMaterial({ color: hs.wall, roughness: 0.82 })
    );
    wall.position.y = hs.h * 0.5;
    wall.castShadow = true;
    wall.receiveShadow = true;
    house.add(wall);

    const roof = new THREE.Mesh(
      new THREE.ConeGeometry(Math.hypot(hs.w, hs.d) * 0.62, hs.h * 0.68, 4),
      new THREE.MeshStandardMaterial({ color: hs.roof, roughness: 0.72, flatShading: true })
    );
    roof.position.y = hs.h + hs.h * 0.34;
    roof.rotation.y = Math.PI / 4;
    roof.castShadow = true;
    house.add(roof);

    const chimney = new THREE.Mesh(
      new THREE.BoxGeometry(0.45, 1.05, 0.45),
      new THREE.MeshStandardMaterial({ color: 0x6c584c, roughness: 0.88 })
    );
    chimney.position.set(hs.w * 0.26, hs.h + hs.h * 0.38, -hs.d * 0.18);
    house.add(chimney);

    const winMat = new THREE.MeshStandardMaterial({
      color: 0x38465e,
      map: textures.windowPane,
      emissive: 0xffbe42,
      emissiveMap: textures.windowPane,
      emissiveIntensity: 0,
      roughness: 0.25,
    });
    for (let side of [-1, 1]) {
      const win = new THREE.Mesh(new THREE.PlaneGeometry(0.72, 0.78), winMat);
      win.position.set(side * hs.w * 0.24, hs.h * 0.56, hs.d * 0.5 + 0.03);
      house.add(win);
      const backWin = win.clone();
      backWin.position.z = -hs.d * 0.5 - 0.03;
      backWin.rotation.y = Math.PI;
      house.add(backWin);
    }
    cottageWindows.push(winMat);
  });

  // 마을 길 8개의 주철 가로등
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
  lampCoords.forEach(([lx, lz]) => {
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.14, 2.9, 8), darkMetalMat);
    post.position.set(lx, 4.25, lz);
    villageGroup.add(post);

    const globeMat = new THREE.MeshStandardMaterial({
      color: 0x4b5563,
      emissive: 0xffd166,
      emissiveIntensity: 0,
      roughness: 0.2,
    });
    const globe = new THREE.Mesh(new THREE.SphereGeometry(0.32, 12, 12), globeMat);
    globe.position.set(lx, 5.8, lz);
    villageGroup.add(globe);
    streetLampBulbs.push(globeMat);

    const halo = makeGlowSprite(textures.glow, 0xffca58, 2.8, 0);
    halo.position.copy(globe.position);
    villageGroup.add(halo);
    streetLampHalos.push(halo);
  });

  // 곶 위의 줄무늬 회전 등대 (Tier 2: harbor)
  const lighthouseGroup = new THREE.Group();
  lighthouseGroup.position.set(33.2, 2.3, -4.5);
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

  const lanternHead = new THREE.Group();
  lanternHead.position.y = 11.4;
  lighthouseGroup.add(lanternHead);

  const lanternCoreMat = new THREE.MeshStandardMaterial({
    color: 0xfef3c7,
    emissive: 0xffe066,
    emissiveIntensity: 0,
  });
  const lanternCore = new THREE.Mesh(new THREE.CylinderGeometry(0.68, 0.68, 1.3, 14), lanternCoreMat);
  lanternHead.add(lanternCore);

  const searchBeamMat = new THREE.MeshBasicMaterial({
    color: 0xfff099,
    transparent: true,
    opacity: 0,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  const searchBeam = new THREE.Mesh(
    new THREE.ConeGeometry(4.2, 24, 16, 1, true),
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

    if (c === 0) {
      const headlight = new THREE.Mesh(
        new THREE.ConeGeometry(1.4, 5.5, 12, 1, true),
        new THREE.MeshBasicMaterial({
          color: 0xfff3a3,
          transparent: true,
          opacity: 0,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
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

  const ferrisWheel = new THREE.Group();
  ferrisWheel.position.y = ferrisHubY;
  ferrisGroup.add(ferrisWheel);

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

  const lineSystems = powerLines.map((spec) => {
    const curve = new THREE.CatmullRomCurve3(
      spec.points.map(([x, y, z]) => new THREE.Vector3(x, y, z))
    );
    const wireMat = new THREE.MeshStandardMaterial({
      color: 0x334155,
      emissive: spec.color,
      emissiveIntensity: 0.08,
      roughness: 0.4,
    });
    const wireMesh = new THREE.Mesh(new THREE.TubeGeometry(curve, 36, 0.09, 6, false), wireMat);
    scene.add(wireMesh);

    const pulses = [];
    for (let p = 0; p < 5; p += 1) {
      const sprite = makeGlowSprite(textures.glow, spec.color, 1.5, 0);
      scene.add(sprite);
      pulses.push({ sprite, offset: p / 5 });
    }
    return { id: spec.id, curve, wireMat, pulses, phase: 0 };
  });

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

  const skyTopNight = new THREE.Color(0x040b1d);
  const skyBotNight = new THREE.Color(0x0f2547);
  const skyTopDay = new THREE.Color(0x1f6feb);
  const skyBotDay = new THREE.Color(0x8fd3ff);
  const skyTopDusk = new THREE.Color(0x1d1a4a);
  const skyBotDusk = new THREE.Color(0xd96b43);
  const skyTopStorm = new THREE.Color(0x080d1a);
  const skyBotStorm = new THREE.Color(0x1c2b42);
  const tmpTop = new THREE.Color();
  const tmpBot = new THREE.Color();
  const tmpMix = new THREE.Color();

  function applyAtmosphere(weather, sunAltitudeDeg, cloudRatio) {
    if (weather === "day") {
      tmpTop.copy(skyTopDay);
      tmpBot.copy(skyBotDay);
      hemiLight.intensity = 1.35;
      mainLight.color.setHex(0xfff1cc);
      mainLight.intensity = 2.15 * (1 - cloudRatio * 0.45);
      starMat.opacity = 0.04;
      moonGroup.visible = false;
    } else if (weather === "dusk") {
      tmpTop.copy(skyTopDusk);
      tmpBot.copy(skyBotDusk);
      hemiLight.intensity = 0.98;
      mainLight.color.setHex(0xffa96b);
      mainLight.intensity = 1.55;
      starMat.opacity = 0.48;
      moonGroup.visible = true;
    } else if (weather === "storm") {
      tmpTop.copy(skyTopStorm);
      tmpBot.copy(skyBotStorm);
      hemiLight.intensity = 0.65 + flashBoost * 1.4;
      mainLight.color.setHex(0x9fc2ff);
      mainLight.intensity = 0.9 + flashBoost * 2.6;
      starMat.opacity = 0.15;
      moonGroup.visible = false;
    } else {
      tmpTop.copy(skyTopNight);
      tmpBot.copy(skyBotNight);
      hemiLight.intensity = 0.78 + flashBoost * 0.9;
      mainLight.color.setHex(0x9ec5ff);
      mainLight.intensity = 1.25 + flashBoost * 1.6;
      starMat.opacity = 0.92;
      moonGroup.visible = true;
    }

    scene.fog.color.copy(tmpBot).multiplyScalar(0.55);

    const pos = skyGeo.attributes.position;
    const col = skyGeo.attributes.color;
    for (let i = 0; i < pos.count; i += 1) {
      const h = THREE.MathUtils.clamp((pos.getY(i) + 40) / 300, 0, 1);
      tmpMix.copy(tmpBot).lerp(tmpTop, Math.pow(h, 0.72));
      col.setXYZ(i, tmpMix.r, tmpMix.g, tmpMix.b);
    }
    col.needsUpdate = true;

    // 태양 궤도 위치 갱신
    const altRad = THREE.MathUtils.clamp(sunAltitudeDeg, 5, 90) * DEG;
    const sunDist = 66;
    sunOrbGroup.position.set(
      -26 + Math.cos(altRad) * 14,
      Math.max(7, Math.sin(altRad) * sunDist * 0.78),
      15.5 - Math.cos(altRad) * 8
    );
    const sunBrightness = weather === "night" ? 0.42 : 1 - cloudRatio * 0.55;
    sunCorona.material.opacity = 0.35 + sunBrightness * 0.55;
    sunSphere.scale.setScalar(weather === "night" ? 0.72 : 1);

    // 태양 → 태양광 패널 빔 연결
    const panelCenter = new THREE.Vector3(-14.5, 4.4, 15.5);
    const mid = new THREE.Vector3().addVectors(sunOrbGroup.position, panelCenter).multiplyScalar(0.5);
    sunBeam.position.copy(mid);
    sunBeam.lookAt(sunOrbGroup.position);
    sunBeam.rotateX(Math.PI / 2);
    const beamLen = sunOrbGroup.position.distanceTo(panelCenter);
    sunBeam.scale.set(1, beamLen / 42, 1);

    cloudMat.opacity = cloudRatio * 0.82;
    cloudGroups.forEach((cg, idx) => {
      cg.visible = cloudRatio > 0.03;
      cg.position.x = -36 + ((idx * 17 + performanceNow * 0.8) % 72);
    });
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

    applyAtmosphere(weather, solar.altitude, solar.cloud / 100);

    // 1) 바다 물결 애니메이션
    const seaPos = seaGeo.attributes.position;
    if (!reducedMotion) {
      for (let i = 0; i < seaPos.count; i += 1) {
        const sx = seaPos.getX(i);
        const sz = seaPos.getZ(i);
        seaPos.setY(
          i,
          seaBaseY[i] +
            Math.sin(sx * 0.14 + performanceNow * 1.5) * 0.22 +
            Math.cos(sz * 0.16 + performanceNow * 1.2) * 0.18
        );
      }
      seaPos.needsUpdate = true;
    }

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

    teslaToroidMat.emissiveIntensity = 0.45 + grid.gridRatio * 2.5 + flashBoost * 2.0;
    teslaHalo.material.opacity = 0.25 + grid.gridRatio * 0.65 + flashBoost * 0.4;
    substationLight.intensity = 0.7 + grid.gridRatio * 2.8 + flashBoost * 3.0;

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
    crankGlowLight.intensity = 0.25 + generator.output.level * 2.6;

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
      ribbon.material.opacity = Math.min(0.55, wind.windSpeed * 0.045);
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
    solarPanelMat.emissiveIntensity = 0.14 + solar.output.level * 1.15;
    sunBeamMat.opacity = 0.014 + solar.output.level * 0.038;

    // 6) 수력 저수지 수위 · 폭포 · 물레바퀴
    const headNorm = (hydro.head - 0.2) / 2.3;
    reservoirWater.scale.y = 0.35 + headNorm * 1.15;
    reservoirWater.position.y = 3.2 + reservoirWater.scale.y * 2.75;
    sluiceGate.position.y = 6.4 + (hydro.flow / 5) * 1.4;

    const flowNorm = hydro.flow / 5;
    waterfallStream.scale.set(0.45 + flowNorm * 0.95, 1, 0.45 + flowNorm * 0.95);
    waterfallMat.opacity = 0.35 + flowNorm * 0.55;

    const visualHydroRpm = Math.min(hydro.rpm, 240) * (reducedMotion ? 0.35 : 1);
    hydroSpin += (visualHydroRpm * TAU * dt) / 60;
    waterWheel.rotation.x = hydroSpin;
    hydroBeaconMat.emissiveIntensity = 0.15 + hydro.output.level * 2.4;

    if (!reducedMotion) {
      const pArr = hydroDropGeo.attributes.position.array;
      for (let i = 0; i < hydroDropCount; i += 1) {
        hydroDropVel[i] = (hydroDropVel[i] || 0) + 14 * dt;
        pArr[i * 3 + 1] -= (3.5 + flowNorm * 7 + hydroDropVel[i]) * dt;
        if (pArr[i * 3 + 1] < 2.2) {
          pArr[i * 3] = -19.8 + (Math.random() - 0.5) * (1.2 + flowNorm * 1.8);
          pArr[i * 3 + 1] = 8.4 + headNorm * 2.2;
          pArr[i * 3 + 2] = -14.8 + (Math.random() - 0.5) * 1.4;
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
      ls.wireMat.emissiveIntensity = flowing ? 0.12 + lv * 1.4 : 0.04;
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
    villageWarmLight.intensity = lm.cottages * 2.6 + lm.ferris * 1.2;

    // Tier 2: 항구 회전 등대 서치라이트
    lanternCoreMat.emissiveIntensity = lm.harbor * 3.0;
    searchBeamMat.opacity = lm.harbor * 0.085;
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
        car.userData.headlight.material.opacity = lm.train * 0.34;
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

    // Tier 5: 무지개 분수 쇼
    fountainJets.forEach(({ jet, jetMat }, idx) => {
      const pulse = 0.78 + Math.sin(performanceNow * 5 + idx) * 0.22;
      jet.visible = lm.fountain > 0.02;
      jet.scale.y = Math.max(0.1, lm.fountain * pulse);
      jet.position.y = 0.7 + jet.scale.y * 2.1;
      jetMat.opacity = lm.fountain * 0.52;
    });

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

    // 카메라 트윈 보간
    if (cameraTween && controls) {
      cameraTween.elapsed += dt;
      const t = easeInOutCubic(Math.min(1, cameraTween.elapsed / cameraTween.duration));
      camera.position.lerpVectors(cameraTween.fromPos, cameraTween.toPos, t);
      controls.target.lerpVectors(cameraTween.fromTarget, cameraTween.toTarget, t);
      if (t >= 1) cameraTween = null;
    }

    if (controls) controls.update();
    if (composer) composer.render();
    else if (renderer) renderer.render(scene, camera);
  }

  function resize() {
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const w = Math.max(280, Math.round(rect.width || canvas.clientWidth || 1280));
    const h = Math.max(200, Math.round(rect.height || canvas.clientHeight || 800));
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    if (renderer) {
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(w, h, false);
    }
    if (composer) composer.setSize(w, h);
    if (bloomPass) bloomPass.setSize(w, h);
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
      if (renderer) renderer.dispose();
    },
  };
}
