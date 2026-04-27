let threePromise;

function loadThree() {
  if (!threePromise) {
    threePromise = import("https://unpkg.com/three@0.165.0/build/three.module.js")
      .then((mod) => mod)
      .catch(() => null);
  }
  return threePromise;
}

function createRenderer(target, THREE, { clearAlpha = 0 } = {}) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 200);
  camera.position.set(0, 0.5, 8);
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  renderer.setClearColor(0x000000, clearAlpha);
  target.appendChild(renderer.domElement);
  return { scene, camera, renderer };
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

export async function initializeSpaceBackdrop(target, { intensity = 1 } = {}) {
  if (!target) return;
  const THREE = await loadThree();
  if (!THREE) return;

  const { scene, camera, renderer } = createRenderer(target, THREE);
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
  const starMaterial = new THREE.PointsMaterial({
    color: 0xbfe8ff,
    size: 0.08 * intensity,
    transparent: true,
    opacity: 0.85,
  });
  const points = new THREE.Points(stars, starMaterial);
  scene.add(points);
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
  target.addEventListener("pointermove", (event) => {
    const rect = target.getBoundingClientRect();
    const px = (event.clientX - rect.left) / Math.max(1, rect.width);
    const py = (event.clientY - rect.top) / Math.max(1, rect.height);
    pointerTarget.x = (px - 0.5) * 2;
    pointerTarget.y = (py - 0.5) * 2;
  }, { passive: true });
  target.addEventListener("pointerleave", () => {
    pointerTarget.set(0, 0);
  }, { passive: true });

  function animate() {
    pointerCurrent.lerp(pointerTarget, 0.045);
    points.rotation.y += (0.00045 + pointerCurrent.x * 0.0002) * intensity;
    points.rotation.x += 0.0002 + pointerCurrent.y * 0.00008;
    points.position.x = pointerCurrent.x * 0.08;
    points.position.y = -pointerCurrent.y * 0.05;
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

  const { scene, camera, renderer } = createRenderer(target, THREE, { clearAlpha: 0 });
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
