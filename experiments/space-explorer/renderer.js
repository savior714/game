// 태양계 3D 탐험대 — 장면 구성과 렌더링
// 실제 텍스처, 태양 플라스마 셰이더, 지구 대기/구름/야간 조명, 고리 그림자, 블룸을 담당한다.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";

import { BELT, KUIPER_BELT, MOONS, PLANETS, SKY_TEXTURE, SUN } from "./data.js";
import { createTextureLibrary } from "./textures.js";
import {
  createAtmosphereMaterial,
  createCloudMaterial,
  createEarthMaterial,
  createGlowTexture,
  createRingMaterial,
  createSkyMaterial,
  createSunMaterial,
} from "./shaders.js";
import {
  clampAngularStep,
  orbitPathPoints,
  orbitRadiusForDistance,
  spinAngleRad,
  TAU,
  visualOrbitPosition,
} from "./simulation.js";

const DEG = Math.PI / 180;
const STAR_COUNT = 420;
const SKY_RADIUS = 2600;



function wrapAngle(angle) {
  const wrapped = angle % TAU;
  if (wrapped > Math.PI) return wrapped - TAU;
  if (wrapped < -Math.PI) return wrapped + TAU;
  return wrapped;
}

function ensureTangents(geometry) {
  if (!geometry.attributes.tangent && geometry.attributes.uv && geometry.attributes.normal) {
    geometry.computeTangents();
  }
  return geometry;
}

function createRingGeometry(inner, outer, { radialSegments = 24, angularSegments = 180 } = {}) {
  const positions = [];
  const uvs = [];
  const indices = [];

  for (let i = 0; i <= radialSegments; i += 1) {
    const t = i / radialSegments;
    const radius = inner + (outer - inner) * t;
    for (let j = 0; j <= angularSegments; j += 1) {
      const angle = (j / angularSegments) * TAU;
      positions.push(Math.cos(angle) * radius, 0, Math.sin(angle) * radius);
      uvs.push(t, j / angularSegments);
    }
  }

  for (let i = 0; i < radialSegments; i += 1) {
    for (let j = 0; j < angularSegments; j += 1) {
      const a = i * (angularSegments + 1) + j;
      const b = a + angularSegments + 1;
      indices.push(a, b, a + 1, b, b + 1, a + 1);
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function createBelt(scene, { innerAU, outerAU, count, color, size = 0.32, spread = 1.1 }) {
  const geometry = new THREE.DodecahedronGeometry(1, 0);
  const material = new THREE.MeshStandardMaterial({
    color,
    roughness: 1,
    metalness: 0,
    transparent: true,
    opacity: 0.7,
  });
  const mesh = new THREE.InstancedMesh(geometry, material, count);
  const dummy = new THREE.Object3D();
  const innerRadius = orbitRadiusForDistance(innerAU);
  const outerRadius = orbitRadiusForDistance(outerAU);

  for (let i = 0; i < count; i += 1) {
    const angle = Math.random() * TAU;
    const radius = innerRadius + Math.random() * (outerRadius - innerRadius);
    const scale = size * (0.25 + Math.random() * 0.9);
    dummy.position.set(
      Math.cos(angle) * radius,
      (Math.random() - 0.5) * spread * 1.5,
      Math.sin(angle) * radius,
    );
    dummy.rotation.set(Math.random() * TAU, Math.random() * TAU, Math.random() * TAU);
    dummy.scale.setScalar(scale);
    dummy.updateMatrix();
    mesh.setMatrixAt(i, dummy.matrix);
  }
  mesh.instanceMatrix.needsUpdate = true;
  mesh.frustumCulled = false;
  scene.add(mesh);
  return mesh;
}

function createKuiperBelt(scene, { innerAU, outerAU, count, color }) {
  const positions = new Float32Array(count * 3);
  const innerRadius = orbitRadiusForDistance(innerAU);
  const outerRadius = orbitRadiusForDistance(outerAU);

  for (let i = 0; i < count; i += 1) {
    const angle = Math.random() * TAU;
    const radius = innerRadius + Math.random() * (outerRadius - innerRadius);
    positions[i * 3] = Math.cos(angle) * radius;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 24;
    positions[i * 3 + 2] = Math.sin(angle) * radius;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const material = new THREE.PointsMaterial({
    color,
    size: 0.65,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.5,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  scene.add(points);
  return points;
}

function createStarLayer(scene) {
  const positions = new Float32Array(STAR_COUNT * 3);
  const colors = new Float32Array(STAR_COUNT * 3);
  const tints = [new THREE.Color(0xffffff), new THREE.Color(0xcfddff), new THREE.Color(0xffe4c4), new THREE.Color(0x9fc7ff)];

  for (let i = 0; i < STAR_COUNT; i += 1) {
    const radius = 700 + Math.random() * 1400;
    const u = Math.random() * 2 - 1;
    const theta = Math.random() * TAU;
    const s = Math.sqrt(1 - u * u);
    positions[i * 3] = radius * s * Math.cos(theta);
    positions[i * 3 + 1] = radius * u;
    positions[i * 3 + 2] = radius * s * Math.sin(theta);
    const tint = tints[i % tints.length];
    colors[i * 3] = tint.r;
    colors[i * 3 + 1] = tint.g;
    colors[i * 3 + 2] = tint.b;
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

  const material = new THREE.PointsMaterial({
    size: 0.72,
    sizeAttenuation: true,
    vertexColors: true,
    transparent: true,
    opacity: 0.62,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const stars = new THREE.Points(geometry, material);
  stars.frustumCulled = false;
  scene.add(stars);
  return stars;
}

function createGlowSprites(scene, sunRadius) {
  const outerTexture = createGlowTexture("rgba(255,214,130,0.9)", "rgba(255,140,40,0.35)");
  const innerTexture = createGlowTexture("rgba(255,252,230,1)", "rgba(255,190,90,0.7)");

  const outer = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: outerTexture,
      color: 0xff9d3c,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      opacity: 0.26,
    }),
  );
  outer.scale.setScalar(sunRadius * 6.4);
  scene.add(outer);

  const inner = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: innerTexture,
      color: 0xffd27a,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      opacity: 0.4,
    }),
  );
  inner.scale.setScalar(sunRadius * 1.85);
  scene.add(inner);

  return { outer, inner };
}

function materialForPlanet(planet, maps) {
  if (planet.id === "earth") {
    return createEarthMaterial({
      day: maps.get("earth_day.jpg"),
      night: maps.get("earth_night.jpg"),
      normal: maps.get("earth_normal.jpg"),
      specular: maps.get("earth_specular.jpg"),
    });
  }

  const config = {
    map: maps.get(planet.texture),
    roughness: planet.roughness ?? 0.9,
    metalness: 0,
  };
  if (planet.bumpTexture) {
    config.bumpMap = maps.get(planet.bumpTexture);
    config.bumpScale = planet.bumpScale ?? 0.02;
  }
  return new THREE.MeshStandardMaterial(config);
}

function createPlanetGroup(planet, maps, scene) {
  const group = new THREE.Group();
  const tilt = new THREE.Group();
  tilt.rotation.z = planet.axialTilt * DEG;
  group.add(tilt);

  const geometry = new THREE.SphereGeometry(planet.displayRadius, 128, 64);
  if (planet.id === "earth") ensureTangents(geometry);

  const material = materialForPlanet(planet, maps);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.userData.bodyId = planet.id;
  tilt.add(mesh);

  const record = {
    data: planet,
    kind: "planet",
    group,
    tilt,
    mesh,
    material,
    radius: planet.displayRadius,
    position: new THREE.Vector3(),
    spinCurrent: 0,
    cloudMesh: null,
    atmosphere: null,
    ring: null,
    orbitLine: null,
  };

  if (planet.id === "earth") {
    const cloudGeometry = new THREE.SphereGeometry(planet.displayRadius * 1.012, 96, 48);
    const cloudMaterial = createCloudMaterial(maps.get(planet.cloudTexture), { opacity: 0.82 });
    const clouds = new THREE.Mesh(cloudGeometry, cloudMaterial);
    clouds.userData.bodyId = planet.id;
    tilt.add(clouds);
    record.cloudMesh = clouds;
    record.cloudMaterial = cloudMaterial;
  }

  if (planet.atmosphereColor) {
    const atmosphereGeometry = new THREE.SphereGeometry(planet.displayRadius * 1.035, 96, 48);
    const atmosphereMaterial = createAtmosphereMaterial(planet.atmosphereColor, {
      strength: planet.atmosphereStrength ?? 0.9,
      planetRadius: planet.displayRadius,
    });
    const atmosphere = new THREE.Mesh(atmosphereGeometry, atmosphereMaterial);
    atmosphere.userData.bodyId = planet.id;
    tilt.add(atmosphere);
    record.atmosphere = atmosphere;
    record.atmosphereMaterial = atmosphereMaterial;
  }

  if (planet.ringTexture) {
    const inner = planet.displayRadius * (planet.ringInner ?? 1.3);
    const outer = planet.displayRadius * (planet.ringOuter ?? 2.2);
    const ringGeometry = createRingGeometry(inner, outer);
    const ringMaterial = createRingMaterial(maps.get(planet.ringTexture), {
      opacity: 0.96,
      planetRadius: planet.displayRadius,
    });
    const ring = new THREE.Mesh(ringGeometry, ringMaterial);
    ring.userData.bodyId = planet.id;
    ring.rotation.x = 0;
    tilt.add(ring);
    record.ring = ring;
    record.ringMaterial = ringMaterial;
  }

  if (planet.faintRings) {
    const faintRings = new THREE.Group();
    for (const [offset, width, opacity] of [
      [1.55, 0.03, 0.22],
      [1.78, 0.018, 0.16],
      [2.02, 0.025, 0.12],
    ]) {
      const geometry = createRingGeometry(
        planet.displayRadius * offset,
        planet.displayRadius * (offset + width),
        { radialSegments: 2, angularSegments: 128 },
      );
      const material = new THREE.MeshBasicMaterial({
        color: 0xbfe9f2,
        transparent: true,
        opacity,
        side: THREE.DoubleSide,
        depthWrite: false,
      });
      faintRings.add(new THREE.Mesh(geometry, material));
    }
    tilt.add(faintRings);
  }

  const orbitPoints = orbitPathPoints(planet.orbit, 320).map(
    (point) => new THREE.Vector3(point.x, point.y, point.z),
  );
  const orbitGeometry = new THREE.BufferGeometry().setFromPoints(orbitPoints);
  const orbitMaterial = new THREE.LineBasicMaterial({
    color: new THREE.Color(planet.color).lerp(new THREE.Color(0x9fdcff), 0.55),
    transparent: true,
    opacity: 0.32,
    depthWrite: false,
  });
  const orbitLine = new THREE.LineLoop(orbitGeometry, orbitMaterial);
  scene.add(orbitLine);
  record.orbitLine = orbitLine;
  record.orbitMaterial = orbitMaterial;

  scene.add(group);
  return record;
}

function createMoonRecord(moon, maps, scene) {
  const radius = moon.displayRadius;
  const geometry = new THREE.SphereGeometry(radius, 64, 32);
  const config = { roughness: 0.95, metalness: 0 };
  if (moon.texture) {
    config.map = maps.get(moon.texture);
  } else {
    config.color = new THREE.Color(moon.color);
  }
  if (moon.bumpTexture) {
    config.bumpMap = maps.get(moon.bumpTexture);
    config.bumpScale = moon.bumpScale ?? 0.02;
  }
  const material = new THREE.MeshStandardMaterial(config);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.userData.bodyId = moon.id;
  scene.add(mesh);

  return {
    data: moon,
    kind: "moon",
    group: mesh,
    mesh,
    material,
    radius,
    position: new THREE.Vector3(),
    spinCurrent: 0,
  };
}

function findMoonParentPosition(moon, planetRecords) {
  const parent = planetRecords.get(moon.parent);
  return parent ? parent.position : new THREE.Vector3();
}

/**
 * 3D 태양계 장면을 만든다.
 * @param {{canvas: HTMLCanvasElement, onTextureProgress?: Function}} options
 */
export async function createSolarScene({ canvas, onTextureProgress = () => {} }) {
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    powerPreference: "high-performance",
    alpha: false,
    stencil: false,
  });
  let pixelRatioCap = Math.min(window.devicePixelRatio || 1, 1.85);
  renderer.setPixelRatio(pixelRatioCap);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x01030a);

  const camera = new THREE.PerspectiveCamera(47, 1, 0.1, 8000);
  camera.position.set(0, 110, 300);

  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.075;
  controls.rotateSpeed = 0.52;
  controls.zoomSpeed = 0.85;
  controls.enablePan = false;
  controls.minDistance = 3.2;
  controls.maxDistance = 900;
  controls.maxPolarAngle = Math.PI * 0.495;
  controls.minPolarAngle = Math.PI * 0.08;
  controls.touches = {
    ONE: THREE.TOUCH.ROTATE,
    TWO: THREE.TOUCH.DOLLY_ROTATE,
  };

  const textures = createTextureLibrary(renderer, onTextureProgress);
  const maps = await textures.loadAll();

  // 은하수 배경 + 가까운 별 입자
  const skyGeometry = new THREE.SphereGeometry(SKY_RADIUS, 64, 32);
  const skyMaterial = createSkyMaterial(maps.get(SKY_TEXTURE), { brightness: 1.5 });
  const sky = new THREE.Mesh(skyGeometry, skyMaterial);
  sky.frustumCulled = false;
  scene.add(sky);
  const starLayer = createStarLayer(scene);

  scene.add(new THREE.HemisphereLight(0x2e4a72, 0x05060a, 0.42));
  const sunLight = new THREE.PointLight(0xfff3df, 2.7, 0, 0);
  scene.add(sunLight);

  // 태양
  const sunGeometry = new THREE.SphereGeometry(SUN.displayRadius, 128, 64);
  const sunMaterial = createSunMaterial(maps.get(SUN.texture), { intensity: 1.05 });
  const sunMesh = new THREE.Mesh(sunGeometry, sunMaterial);
  sunMesh.userData.bodyId = SUN.id;
  scene.add(sunMesh);
  createGlowSprites(scene, SUN.displayRadius);

  const bodies = new Map();
  const planetRecords = new Map();
  const pickables = [sunMesh];

  bodies.set(SUN.id, {
    data: SUN,
    kind: "sun",
    mesh: sunMesh,
    material: sunMaterial,
    radius: SUN.displayRadius,
    position: new THREE.Vector3(),
    spinCurrent: 0,
  });

  for (const planet of PLANETS) {
    const record = createPlanetGroup(planet, maps, scene);
    planetRecords.set(planet.id, record);
    bodies.set(planet.id, record);
    pickables.push(record.mesh);
    if (record.ring) pickables.push(record.ring);
    if (record.cloudMesh) pickables.push(record.cloudMesh);
  }

  for (const moon of MOONS) {
    const record = createMoonRecord(moon, maps, scene);
    bodies.set(moon.id, record);
    pickables.push(record.mesh);
  }

  const asteroidBelt = createBelt(scene, {
    innerAU: BELT.innerAU,
    outerAU: BELT.outerAU,
    count: BELT.count,
    color: BELT.color,
    size: 0.085,
    spread: 1.6,
  });
  const kuiperBelt = createKuiperBelt(scene, {
    innerAU: KUIPER_BELT.innerAU,
    outerAU: KUIPER_BELT.outerAU,
    count: KUIPER_BELT.count,
    color: KUIPER_BELT.color,
  });

  // 후처리 — 블룸(태양/도시 불빛)과 톤매핑
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloomPass = new UnrealBloomPass(new THREE.Vector2(1, 1), 0.52, 0.48, 0.86);
  composer.addPass(bloomPass);
  composer.addPass(new OutputPass());

  let bloomEnabled = true;
  let orbitsVisible = true;
  let width = 1;
  let height = 1;
  let viewShiftY = 0;
  let viewShiftX = 0;

  /**
   * 초점을 맞춘 천체가 정보 패널에 가리지 않도록 렌더 중심을 옮긴다.
   * viewShiftY > 0 이면 장면이 화면 위로, viewShiftX > 0 이면 화면 왼쪽으로 이동한다.
   */
  function setViewShift({ y = 0, x = 0 } = {}) {
    viewShiftY = Math.max(0, Math.min(0.3, y));
    viewShiftX = Math.max(0, Math.min(0.3, x));
    applyViewOffset();
  }

  function applyViewOffset() {
    if (viewShiftY <= 0.001 && viewShiftX <= 0.001) {
      camera.clearViewOffset();
      return;
    }
    const offsetX = Math.round(width * viewShiftX);
    const offsetY = Math.round(height * viewShiftY);
    camera.setViewOffset(width, height, offsetX, offsetY, width, height);
  }

  function resize() {
    const parent = canvas.parentElement || document.body;
    width = Math.max(1, parent.clientWidth);
    height = Math.max(1, parent.clientHeight);
    const pixelRatio = Math.min(window.devicePixelRatio || 1, pixelRatioCap);
    renderer.setPixelRatio(pixelRatio);
    renderer.setSize(width, height, false);
    composer.setPixelRatio(pixelRatio);
    composer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    applyViewOffset();
  }

  function setBloomEnabled(enabled) {
    bloomEnabled = enabled;
  }

  function setPixelRatioCap(cap) {
    pixelRatioCap = Math.max(1, cap);
    resize();
  }

  function setOrbitsVisible(visible) {
    orbitsVisible = visible;
    for (const record of planetRecords.values()) {
      record.orbitLine.visible = visible;
    }
  }

  function setOrbitHighlight(id) {
    for (const record of planetRecords.values()) {
      const active = record.data.id === id;
      record.orbitMaterial.opacity = active ? 0.85 : 0.32;
      record.orbitMaterial.color.lerpColors(
        new THREE.Color(record.data.color),
        new THREE.Color(active ? 0xffffff : 0x9fdcff),
        active ? 0.35 : 0.55,
      );
    }
  }

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  function raycastFromEvent(event) {
    const rect = canvas.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / Math.max(1, rect.width)) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / Math.max(1, rect.height)) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(pickables, false);
    for (const hit of hits) {
      const id = hit.object.userData.bodyId;
      if (id) return id;
    }
    return null;
  }

  const tempSunDirection = new THREE.Vector3();
const axisQuaternion = new THREE.Quaternion();
  let elapsed = 0;

  function updateSpin(record, days, dt) {
    if (!record.mesh) return;
    const target = spinAngleRad(record.data.rotationHours, days);
    const delta = wrapAngle(target - record.spinCurrent);
    const maxStep = Math.max(0.12, Math.min(0.4, dt * 30));
    // 일시정지(dt=0)에서는 자전도 완전히 멈춘다.
    if (dt > 0) {
      record.spinCurrent += clampAngularStep(delta, maxStep);
      record.spinCurrent = record.spinCurrent % TAU;
    }
    record.mesh.rotation.y = record.spinCurrent;
  }

  const cloudDrift = new Map();

  function update(days, dt) {
    elapsed += dt;

    // 태양 자전과 표면 플라스마 애니메이션
    const sunRecord = bodies.get(SUN.id);
    updateSpin(sunRecord, days, dt);
    sunMaterial.uniforms.uTime.value = elapsed;

    for (const planet of PLANETS) {
      const record = planetRecords.get(planet.id);
      const position = visualOrbitPosition(planet.orbit, days);
      if (record.cloudMesh && dt > 0) {
        cloudDrift.set(planet.id, (cloudDrift.get(planet.id) ?? 0) + dt * (planet.cloudDrift ?? 0.01));
      }
      record.position.set(position.x, position.y, position.z);
      record.group.position.copy(record.position);

      updateSpin(record, days, dt);
      tempSunDirection.copy(record.position).multiplyScalar(-1).normalize();

      if (record.material.uniforms?.sunDirection) {
        record.material.uniforms.sunDirection.value.copy(tempSunDirection);
      }
      if (record.cloudMaterial) {
        record.cloudMaterial.uniforms.sunDirection.value.copy(tempSunDirection);
        record.cloudMesh.rotation.y = record.spinCurrent * 1.03 + (cloudDrift.get(planet.id) ?? 0);
      }
      if (record.atmosphereMaterial) {
        record.atmosphereMaterial.uniforms.sunDirection.value.copy(tempSunDirection);
        record.atmosphereMaterial.uniforms.planetCenter.value.copy(record.position);
      }
      if (record.ringMaterial) {
        record.ringMaterial.uniforms.sunDirection.value.copy(tempSunDirection);
        record.ringMaterial.uniforms.planetWorldPosition.value.copy(record.position);
      }
    }

    // 위성: 부모 행성 위치 + 경사 궤도
    for (const moon of MOONS) {
      const record = bodies.get(moon.id);
      const parentPosition = findMoonParentPosition(moon, planetRecords);
      const parentRecord = planetRecords.get(moon.parent);
      const orbitRadius = (parentRecord?.radius ?? 1) * moon.orbitRadius;

      const angle = TAU * (days / moon.periodDays) + moon.phase;
      const inclination = (moon.inclination ?? 0) * DEG;
      const x = Math.cos(angle) * orbitRadius;
      const z = Math.sin(angle) * orbitRadius;
      record.position.set(
        parentPosition.x + x,
        parentPosition.y + Math.sin(angle) * Math.sin(inclination) * orbitRadius,
        parentPosition.z + z,
      );
      record.mesh.position.copy(record.position);
      // 조석 고정: 공전과 같은 각도로 자전한다.
      record.mesh.rotation.y = -angle + Math.PI;
    }

    asteroidBelt.rotation.y = (days / 1680) * TAU * 0.35;
    kuiperBelt.rotation.y = (days / 90000) * TAU * 0.35;
    kuiperBelt.rotation.x = 0.02;
    starLayer.rotation.y = days * 0.00002;
    sky.rotation.y = days * 0.000004;
  }

  function render() {
    if (bloomEnabled) {
      composer.render();
    } else {
      renderer.render(scene, camera);
    }
  }

  function getBodyWorldPosition(id) {
    const body = bodies.get(id);
    return body ? body.position.clone() : new THREE.Vector3();
  }

  /** 천체의 자전축(북극) 월드 방향. 궤도면 기준으로 기울어진 실제 자전축을 돌려준다. */
  function getBodyPole(id, target = new THREE.Vector3()) {
    const record = bodies.get(id);
    if (!record) return target.set(0, 1, 0);
    if (record.kind === "planet" && record.tilt) {
      target.set(0, 1, 0).applyQuaternion(record.tilt.getWorldQuaternion(axisQuaternion));
      return target.normalize();
    }
    return target.set(0, 1, 0);
  }

  function getBodyRadius(id) {
    const body = bodies.get(id);
    return body?.radius ?? 1;
  }

  function getBody(id) {
    return bodies.get(id) ?? null;
  }

  resize();
  return {
    scene,
    camera,
    renderer,
    controls,
    composer,
    bloomPass,
    bodies,
    pickables,
    textures,
    update,
    render,
    resize,
    setViewShift,
    setBloomEnabled,
    setPixelRatioCap,
    setOrbitsVisible,
    setOrbitHighlight,
    raycastFromEvent,
    getBodyWorldPosition,
    getBodyPole,
    getBodyRadius,
    getBody,
    orbitPathPoints,
    dispose() {
      controls.dispose();
      composer.dispose();
      renderer.dispose();
    },
  };
}
