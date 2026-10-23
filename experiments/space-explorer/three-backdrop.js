import { createBestRenderer, BACKEND_WEBGPU } from "./webgpu/renderer-factory.js";
import { createBillboardCloud } from "./webgpu/instanced-sprites.js";

let threePromise;

// 번들된 three.js를 쓴다. 미니게임 페이지에도 같은 import map이 선언되어 있다.
function loadThree() {
  if (!threePromise) {
    threePromise = import("three")
      .then((mod) => mod)
      .catch(() => null);
  }
  return threePromise;
}

async function createRenderer(target, THREE, { clearAlpha = 0 } = {}) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 200);
  camera.position.set(0, 0.5, 8);
  // WebGPU를 먼저 시도하고 실패하면 동일 옵션으로 WebGLRenderer에 폴백한다.
  const selected = await createBestRenderer(THREE, {
    parameters: { alpha: true, antialias: true },
  });
  const renderer = selected.renderer;
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  renderer.setClearColor(0x000000, clearAlpha);
  target.appendChild(renderer.domElement);
  return {
    scene,
    camera,
    renderer,
    backend: selected.backend,
    bundle: selected.three,
    tsl: selected.tsl,
  };
}

function bindResize(target, camera, renderer) {
  const onResize = () => {
    const width = Math.max(1, target.clientWidth);
    const height = Math.max(1, target.clientHeight);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  onResize();
  window.addEventListener("resize", onResize, { passive: true });
}

// WebGPU는 point 프리미티브가 1픽셀 고정이라 인스턴스 빌보드로 별을 그린다.
// 구름 전체의 회원전/이동은 빌보드가 메시 회전을 무시하므로 TSL 유니폼으로 직접 돌린다.
function createWebGpuStars(bundle, tsl, starCount, vertices, intensity) {
  const sizes = new Float32Array(starCount);
  sizes.fill(0.08 * intensity);
  const uRotY = tsl.uniform(0);
  const uRotX = tsl.uniform(0);
  const uShiftX = tsl.uniform(0);
  const uShiftY = tsl.uniform(0);

  const transformPosition = (instancePosition) => {
    const p = instancePosition;
    const cy = tsl.cos(uRotY);
    const sy = tsl.sin(uRotY);
    const cx = tsl.cos(uRotX);
    const sx = tsl.sin(uRotX);
    // three.js Y축 회전 → X축 회전 순서(rotation.y, rotation.x 적재 순서와 동일)
    const x1 = p.x.mul(cy).add(p.z.mul(sy));
    const z1 = p.x.mul(sy).negate().add(p.z.mul(cy));
    const y1 = p.y.mul(cx).sub(z1.mul(sx));
    const z2 = p.y.mul(sx).add(z1.mul(cx));
    return tsl.vec3(
      x1.add(uShiftX),
      y1.add(uShiftY),
      z2,
    );
  };

  const cloud = createBillboardCloud(bundle, {
    count: starCount,
    positions: vertices,
    sizes,
    baseColor: 0xbfe8ff,
    alphas: new Float32Array(starCount).fill(0.85),
    additive: true,
    transformPosition,
  });

  return {
    object: cloud.mesh,
    setMotion({ rotY, rotX, shiftX, shiftY }) {
      uRotY.value = rotY;
      uRotX.value = rotX;
      uShiftX.value = shiftX;
      uShiftY.value = shiftY;
    },
  };
}

export async function initializeSpaceBackdrop(target, { intensity = 1 } = {}) {
  if (!target) return;
  const THREE = await loadThree();
  if (!THREE) return;

  const { scene, camera, renderer, backend, bundle, tsl } = await createRenderer(target, THREE);
  bindResize(target, camera, renderer);

  const stars = new THREE.BufferGeometry();
  const starCount = 700;
  const vertices = new Float32Array(starCount * 3);
  for (let i = 0; i < starCount; i += 1) {
    const spread = 28;
    vertices[i * 3 + 0] = (Math.random() - 0.5) * spread;
    vertices[i * 3 + 1] = (Math.random() - 0.5) * spread * 0.65;
    vertices[i * 3 + 2] = (Math.random() - 0.5) * spread - 8;
  }
  stars.setAttribute("position", new THREE.BufferAttribute(vertices, 3));

  let starObject;
  let webGpuStarMotion = null;
  if (backend === BACKEND_WEBGPU) {
    const webGpuStars = createWebGpuStars(bundle, tsl, starCount, vertices, intensity);
    starObject = webGpuStars.object;
    webGpuStarMotion = webGpuStars.setMotion;
    scene.add(starObject);
  } else {
    const starMaterial = new THREE.PointsMaterial({
      color: 0xbfe8ff,
      size: 0.08 * intensity,
      transparent: true,
      opacity: 0.85,
    });
    starObject = new THREE.Points(stars, starMaterial);
    scene.add(starObject);
  }

  const nebulaGeo = new THREE.PlaneGeometry(26, 16, 1, 1);
  const nebulaMat = new THREE.MeshBasicMaterial({
    color: 0x6ea8ff,
    transparent: true,
    opacity: 0.12,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const nebula = new THREE.Mesh(nebulaGeo, nebulaMat);
  nebula.position.z = -9;
  scene.add(nebula);

  const pointerTarget = new THREE.Vector2(0, 0);
  const pointerCurrent = new THREE.Vector2(0, 0);
  // The three-layer overlay is pointer-events: none, so track the pointer from
  // the scene wrapper that hosts it.
  const pointerSurface = target.parentElement || target;
  pointerSurface.addEventListener("pointermove", (event) => {
    const rect = target.getBoundingClientRect();
    const px = (event.clientX - rect.left) / Math.max(1, rect.width);
    const py = (event.clientY - rect.top) / Math.max(1, rect.height);
    pointerTarget.x = (px - 0.5) * 2;
    pointerTarget.y = (py - 0.5) * 2;
  }, { passive: true });
  pointerSurface.addEventListener("pointerleave", () => {
    pointerTarget.set(0, 0);
  }, { passive: true });

  let rotY = 0;
  let rotX = 0;
  function animate() {
    pointerCurrent.lerp(pointerTarget, 0.045);
    rotY += (0.00045 + pointerCurrent.x * 0.0002) * intensity;
    rotX += 0.0002 + pointerCurrent.y * 0.00008;
    const shiftX = pointerCurrent.x * 0.08;
    const shiftY = -pointerCurrent.y * 0.05;
    if (webGpuStarMotion) {
      webGpuStarMotion({ rotY, rotX, shiftX, shiftY });
    } else {
      starObject.rotation.y = rotY;
      starObject.rotation.x = rotX;
      starObject.position.x = shiftX;
      starObject.position.y = shiftY;
    }
    nebula.rotation.z = pointerCurrent.x * 0.12;
    nebula.position.x = pointerCurrent.x * 0.55;
    nebula.position.y = -pointerCurrent.y * 0.3;
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }
  animate();
}

export async function initializePaintLights(target) {
  if (!target) return;
  const THREE = await loadThree();
  if (!THREE) return;

  const { scene, camera, renderer } = await createRenderer(target, THREE, { clearAlpha: 0 });
  bindResize(target, camera, renderer);

  const orbGeo = new THREE.SphereGeometry(1.4, 32, 32);
  const orbMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.5,
    metalness: 0.15,
  });
  const orb = new THREE.Mesh(orbGeo, orbMat);
  orb.scale.set(1.15, 0.7, 1.0);
  scene.add(orb);

  const key = new THREE.PointLight(0xf87171, 2.4, 24);
  key.position.set(-3.8, 1.8, 4.8);
  scene.add(key);
  const fill = new THREE.PointLight(0x60a5fa, 2.4, 24);
  fill.position.set(3.8, -1.4, 4.8);
  scene.add(fill);
  scene.add(new THREE.AmbientLight(0xffffff, 0.42));

  function animate() {
    const t = performance.now() * 0.001;
    orb.rotation.y = t * 0.35;
    orb.rotation.x = Math.sin(t * 0.5) * 0.18;
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }
  animate();
}
