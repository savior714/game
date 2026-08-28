import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const EPOCH = new Date("2026-08-28T00:00:00Z");
const TAU = Math.PI * 2;
const DEG = Math.PI / 180;

const BODY_DATA = [
  {
    id: "mercury", name: "수성", en: "Mercury", icon: "🪨", category: "암석형 행성",
    radius: 3.2, distance: 42, period: 87.97, rotationHours: 1407.6, eccentricity: 0.2056, inclination: 7.0, tilt: 0.034,
    color: "#9b9b9b", accent: "#d7d7d7", initial: 45,
    highlight: "달처럼 운석 구덩이가 가득한 태양계의 가장 빠른 행성!",
    overview: "태양과 가장 가까운 행성입니다. 대기가 거의 없어 낮과 밤의 온도 차이가 매우 커요.",
    stats: [["태양에서", "1번째"], ["공전", "약 88일"], ["하루", "약 59일"], ["온도", "낮 430°C / 밤 -180°C"]],
    facts: ["태양 주위를 약 88일 만에 한 바퀴 돌아요.", "대기가 거의 없어 낮과 밤의 온도 차이가 매우 커요.", "표면에는 오래된 충돌 분화구가 아주 많아요."]
  },
  {
    id: "venus", name: "금성", en: "Venus", icon: "🟡", category: "암석형 행성",
    radius: 5.6, distance: 64, period: 224.7, rotationHours: -5832.5, eccentricity: 0.0067, inclination: 3.39, tilt: 177.36,
    color: "#d8a968", accent: "#f6dfae", initial: 130, atmosphere: "#f5c978",
    highlight: "두꺼운 대기의 온실효과로 태양계에서 가장 뜨거운 행성!",
    overview: "지구와 크기는 비슷하지만 두꺼운 이산화탄소 대기 때문에 표면은 매우 뜨겁습니다.",
    stats: [["태양에서", "2번째"], ["공전", "약 225일"], ["하루", "약 243일"], ["온도", "약 465°C"]],
    facts: ["수성보다 태양에서 멀지만 평균 표면 온도는 더 높아요.", "대부분의 행성과 반대 방향으로 천천히 자전해요.", "밤하늘에서 달 다음으로 밝게 보이는 천체 중 하나예요."]
  },
  {
    id: "earth", name: "지구", en: "Earth", icon: "🌍", category: "암석형 행성 · 우리의 집",
    radius: 6.0, distance: 92, period: 365.25, rotationHours: 23.934, eccentricity: 0.0167, inclination: 0, tilt: 23.44,
    color: "#1f66d8", accent: "#58c56f", initial: 210, atmosphere: "#62b5ff",
    highlight: "액체 물과 생명체가 있는, 지금까지 확인된 우리의 유일한 집!",
    overview: "표면의 약 71%가 바다로 덮여 있고 하나의 큰 위성인 달이 지구 주위를 돕니다.",
    stats: [["태양에서", "3번째"], ["공전", "365.25일"], ["하루", "약 24시간"], ["위성", "달 1개"]],
    facts: ["지구의 자전축이 약 23.4° 기울어져 있어 계절 변화가 생겨요.", "달은 지구에 거의 같은 면을 보여 주며 공전해요.", "대기와 자기장이 지표의 생명 환경을 보호하는 데 중요한 역할을 해요."]
  },
  {
    id: "mars", name: "화성", en: "Mars", icon: "🔴", category: "암석형 행성 · 붉은 사막",
    radius: 4.0, distance: 122, period: 686.98, rotationHours: 24.62, eccentricity: 0.0934, inclination: 1.85, tilt: 25.19,
    color: "#b7482f", accent: "#e77f55", initial: 320,
    highlight: "산화철 먼지 때문에 붉게 보이는 미래 탐사의 핵심 행성!",
    overview: "태양계에서 가장 큰 화산인 올림푸스 몬스와 거대한 협곡 지형을 볼 수 있습니다.",
    stats: [["태양에서", "4번째"], ["공전", "약 687일"], ["하루", "24시간 37분"], ["위성", "2개"]],
    facts: ["지구와 하루 길이가 꽤 비슷해요.", "극지방에는 물얼음과 이산화탄소 얼음이 있어요.", "표면의 산화철 성분 때문에 붉은빛을 띠어요."]
  },
  {
    id: "jupiter", name: "목성", en: "Jupiter", icon: "🟠", category: "가스형 거대행성",
    radius: 13.5, distance: 175, period: 4332.59, rotationHours: 9.925, eccentricity: 0.0484, inclination: 1.30, tilt: 3.13,
    color: "#c6915d", accent: "#f0d0a2", initial: 85, bands: true,
    highlight: "지구 1,300개 정도가 들어갈 만큼 거대한 태양계 최대 행성!",
    overview: "빠른 자전으로 줄무늬 구름이 발달했고, 수백 년 동안 지속된 거대한 폭풍인 대적점이 유명합니다.",
    stats: [["태양에서", "5번째"], ["공전", "약 11.86년"], ["하루", "약 9시간 55분"], ["크기", "지구 지름의 11.2배"]],
    facts: ["태양계에서 가장 큰 행성이에요.", "빠른 자전 때문에 적도가 약간 불룩해요.", "가니메데·유로파 등 많은 위성을 거느리고 있어요."]
  },
  {
    id: "saturn", name: "토성", en: "Saturn", icon: "🪐", category: "가스형 거대행성 · 고리",
    radius: 11.2, distance: 232, period: 10759.22, rotationHours: 10.656, eccentricity: 0.0541, inclination: 2.48, tilt: 26.73,
    color: "#d7b875", accent: "#f2dfae", initial: 190, rings: true, bands: true,
    highlight: "얼음과 암석 조각 수없이 모여 만든 눈부신 고리를 가진 행성!",
    overview: "토성의 고리는 넓지만 매우 얇으며, 수많은 얼음 입자와 암석 조각으로 이루어져 있습니다.",
    stats: [["태양에서", "6번째"], ["공전", "약 29.5년"], ["하루", "약 10시간 40분"], ["특징", "거대한 고리"]],
    facts: ["토성의 평균 밀도는 물보다 낮아요.", "고리는 하나의 판이 아니라 수많은 입자들의 집합이에요.", "타이탄을 포함해 다양한 위성이 토성 주위를 돌아요."]
  },
  {
    id: "uranus", name: "천왕성", en: "Uranus", icon: "🔵", category: "얼음형 거대행성",
    radius: 8.2, distance: 285, period: 30688.5, rotationHours: -17.24, eccentricity: 0.0472, inclination: 0.77, tilt: 97.77,
    color: "#7ed7de", accent: "#c4f5f4", initial: 290, atmosphere: "#8de5ed",
    highlight: "자전축이 거의 옆으로 누운 채 태양 주위를 도는 독특한 행성!",
    overview: "메탄이 붉은빛을 흡수해 청록색으로 보이며, 자전축이 약 98° 기울어져 있습니다.",
    stats: [["태양에서", "7번째"], ["공전", "약 84년"], ["하루", "약 17시간"], ["자전축", "약 98°"]],
    facts: ["거의 옆으로 누운 채 자전해요.", "대기의 메탄 때문에 푸른빛을 띠어요.", "희미한 고리도 가지고 있어요."]
  },
  {
    id: "neptune", name: "해왕성", en: "Neptune", icon: "🔷", category: "얼음형 거대행성",
    radius: 7.8, distance: 335, period: 60182, rotationHours: 16.11, eccentricity: 0.0086, inclination: 1.77, tilt: 28.32,
    color: "#315bd8", accent: "#5f8fff", initial: 15, atmosphere: "#4774ff",
    highlight: "태양계 바깥쪽에서 매우 빠른 바람이 부는 짙푸른 거대행성!",
    overview: "태양에서 매우 멀리 떨어져 있으며, 상층 대기에서는 초속 수백 미터의 강풍이 관측됩니다.",
    stats: [["태양에서", "8번째"], ["공전", "약 164.8년"], ["하루", "약 16시간"], ["특징", "초고속 바람"]],
    facts: ["태양을 한 바퀴 도는 데 약 165년이 걸려요.", "태양계에서 매우 빠른 바람이 관측되는 곳이에요.", "가장 큰 위성 트리톤은 해왕성의 자전 방향과 반대로 공전해요."]
  }
];

const SUN = {
  id: "sun", name: "태양", en: "Sun", icon: "☀️", category: "항성 · 태양계의 중심",
  radius: 18, color: "#ffad22", accent: "#fff2a8",
  highlight: "태양계 전체 질량의 대부분을 차지하며 모든 행성을 중력으로 붙잡는 중심별!",
  overview: "태양은 스스로 빛과 열을 내는 항성입니다. 중심에서 일어나는 핵융합이 태양계의 에너지원이 됩니다.",
  stats: [["종류", "항성"], ["표면", "약 5,500°C"], ["빛→지구", "약 8분 20초"], ["크기", "지구 지름의 약 109배"]],
  facts: ["태양의 중력이 행성들의 공전을 유지해요.", "태양 중심부의 핵융합에서 막대한 에너지가 만들어져요.", "태양은 은하 중심도 매우 긴 주기로 공전하고 있어요."]
};

const canvas = document.getElementById("space-canvas");
const labelsLayer = document.getElementById("labels-layer");
const dateDisplay = document.getElementById("date-display");
const speedBadge = document.getElementById("speed-badge");
const detailCard = document.getElementById("detail-card");
const detailClose = document.getElementById("detail-close");
const overviewBtn = document.getElementById("overview-btn");
const planetRibbon = document.getElementById("planet-ribbon");
const orbitsBtn = document.getElementById("orbits-btn");
const pauseBtn = document.getElementById("pause-btn");
const helpModal = document.getElementById("help-modal");

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x030814);
scene.fog = new THREE.FogExp2(0x030814, 0.00095);

const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 1600);
camera.position.set(0, 205, 430);

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.12;

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.07;
controls.minDistance = 24;
controls.maxDistance = 760;
controls.target.set(0, 0, 0);
controls.maxPolarAngle = Math.PI * 0.88;
controls.minPolarAngle = Math.PI * 0.08;

scene.add(new THREE.HemisphereLight(0x5577aa, 0x05050a, 0.28));
const sunLight = new THREE.PointLight(0xffffff, 3.3, 1000, 1.2);
sunLight.position.set(0, 0, 0);
scene.add(sunLight);

function makeStars() {
  const count = 5200;
  const positions = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  for (let i = 0; i < count; i += 1) {
    const radius = 520 + Math.random() * 700;
    const u = Math.random() * 2 - 1;
    const theta = Math.random() * TAU;
    const s = Math.sqrt(1 - u * u);
    positions[i * 3] = radius * s * Math.cos(theta);
    positions[i * 3 + 1] = radius * u;
    positions[i * 3 + 2] = radius * s * Math.sin(theta);
    sizes[i] = 0.7 + Math.random() * 1.4;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("size", new THREE.BufferAttribute(sizes, 1));
  const material = new THREE.PointsMaterial({ color: 0xcfe8ff, size: 1.25, sizeAttenuation: true, transparent: true, opacity: 0.88, depthWrite: false });
  scene.add(new THREE.Points(geometry, material));
}

function hexToRgb(hex) {
  const c = new THREE.Color(hex);
  return { r: Math.round(c.r * 255), g: Math.round(c.g * 255), b: Math.round(c.b * 255) };
}

function makePlanetTexture(body) {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 256;
  const ctx = c.getContext("2d");
  const base = hexToRgb(body.color);
  const accent = hexToRgb(body.accent || body.color);

  const gradient = ctx.createLinearGradient(0, 0, 0, c.height);
  gradient.addColorStop(0, `rgb(${Math.min(255, base.r + 24)},${Math.min(255, base.g + 24)},${Math.min(255, base.b + 24)})`);
  gradient.addColorStop(0.5, `rgb(${base.r},${base.g},${base.b})`);
  gradient.addColorStop(1, `rgb(${Math.max(0, base.r - 34)},${Math.max(0, base.g - 34)},${Math.max(0, base.b - 34)})`);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, c.width, c.height);

  if (body.id === "earth") {
    ctx.fillStyle = `rgb(${accent.r},${accent.g},${accent.b})`;
    const continents = [[75,80,64,40],[175,120,52,70],[300,70,86,44],[390,135,70,48],[255,170,42,34]];
    for (const [x,y,w,h] of continents) {
      ctx.beginPath();
      ctx.ellipse(x, y, w, h, -0.3 + Math.random() * 0.6, 0, TAU);
      ctx.fill();
    }
    ctx.globalAlpha = 0.42;
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 8;
    for (let y = 38; y < 220; y += 55) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.bezierCurveTo(120, y - 18, 250, y + 18, 512, y - 5);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  } else if (body.bands) {
    for (let y = 18; y < c.height; y += 18) {
      const alpha = 0.12 + (y % 36 === 0 ? 0.18 : 0.08);
      ctx.fillStyle = `rgba(${accent.r},${accent.g},${accent.b},${alpha})`;
      ctx.fillRect(0, y, c.width, 8 + (y % 4));
    }
    if (body.id === "jupiter") {
      ctx.fillStyle = "rgba(166,55,31,.72)";
      ctx.beginPath();
      ctx.ellipse(355, 158, 35, 16, -0.12, 0, TAU);
      ctx.fill();
    }
  } else {
    for (let i = 0; i < 70; i += 1) {
      const x = Math.random() * c.width;
      const y = Math.random() * c.height;
      const r = 1 + Math.random() * 10;
      ctx.fillStyle = `rgba(${accent.r},${accent.g},${accent.b},${0.06 + Math.random() * 0.13})`;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, TAU);
      ctx.fill();
    }
  }

  const texture = new THREE.CanvasTexture(c);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
  return texture;
}

function makeSunGlow() {
  const c = document.createElement("canvas");
  c.width = 256;
  c.height = 256;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(128, 128, 12, 128, 128, 128);
  g.addColorStop(0, "rgba(255,245,170,1)");
  g.addColorStop(0.18, "rgba(255,178,35,.92)");
  g.addColorStop(0.48, "rgba(255,111,0,.28)");
  g.addColorStop(1, "rgba(255,80,0,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 256, 256);
  const material = new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(86, 86, 1);
  return sprite;
}

makeStars();

const bodies = new Map();
const orbitLines = [];
const pickables = [];

const sunMesh = new THREE.Mesh(
  new THREE.SphereGeometry(SUN.radius, 64, 32),
  new THREE.MeshBasicMaterial({ color: SUN.color })
);
sunMesh.userData.bodyId = "sun";
scene.add(sunMesh);
scene.add(makeSunGlow());
bodies.set("sun", { data: SUN, mesh: sunMesh, position: new THREE.Vector3() });
pickables.push(sunMesh);

function makeOrbit(body) {
  const points = [];
  const inc = body.inclination * DEG;
  for (let i = 0; i <= 256; i += 1) {
    const theta = (i / 256) * TAU;
    const r = body.distance * (1 - body.eccentricity * Math.cos(theta));
    points.push(new THREE.Vector3(
      Math.cos(theta) * r,
      Math.sin(theta) * r * Math.sin(inc),
      Math.sin(theta) * r
    ));
  }
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({ color: 0x3d648d, transparent: true, opacity: 0.34 });
  const line = new THREE.LineLoop(geometry, material);
  scene.add(line);
  orbitLines.push(line);
}

function makeRings(body, tiltGroup) {
  if (!body.rings) return null;
  const geometry = new THREE.RingGeometry(body.radius * 1.35, body.radius * 2.55, 128);
  const material = new THREE.MeshStandardMaterial({
    color: 0xe6d4a4, roughness: 0.86, metalness: 0.03, side: THREE.DoubleSide,
    transparent: true, opacity: 0.78, depthWrite: false
  });
  const ring = new THREE.Mesh(geometry, material);
  ring.rotation.x = Math.PI / 2;
  ring.userData.bodyId = body.id;
  tiltGroup.add(ring);
  pickables.push(ring);
  return ring;
}

for (const data of BODY_DATA) {
  makeOrbit(data);
  const root = new THREE.Group();
  const tiltGroup = new THREE.Group();
  tiltGroup.rotation.z = data.tilt * DEG;
  root.add(tiltGroup);

  const mesh = new THREE.Mesh(
    new THREE.SphereGeometry(data.radius, 48, 28),
    new THREE.MeshStandardMaterial({ map: makePlanetTexture(data), roughness: 0.76, metalness: 0.02 })
  );
  mesh.userData.bodyId = data.id;
  tiltGroup.add(mesh);
  pickables.push(mesh);

  if (data.atmosphere) {
    const atmosphere = new THREE.Mesh(
      new THREE.SphereGeometry(data.radius * 1.055, 40, 24),
      new THREE.MeshBasicMaterial({ color: data.atmosphere, transparent: true, opacity: 0.11, side: THREE.BackSide, blending: THREE.AdditiveBlending, depthWrite: false })
    );
    tiltGroup.add(atmosphere);
  }
  makeRings(data, tiltGroup);
  scene.add(root);
  bodies.set(data.id, { data, root, tiltGroup, mesh, position: new THREE.Vector3() });
}

const moonMesh = new THREE.Mesh(
  new THREE.SphereGeometry(1.7, 32, 20),
  new THREE.MeshStandardMaterial({ color: 0xb9bec5, roughness: 0.9 })
);
moonMesh.userData.bodyId = "moon";
scene.add(moonMesh);
pickables.push(moonMesh);
bodies.set("moon", {
  data: {
    id: "moon", name: "달", en: "Moon", icon: "🌕", category: "지구의 자연위성", radius: 1.7,
    highlight: "지구의 가장 가까운 우주 이웃이며 조석과 밤하늘의 모습을 크게 바꾸는 위성!",
    overview: "달은 약 27.3일에 한 번 지구 주위를 공전하며, 지구에는 거의 같은 면을 보여 줍니다.",
    stats: [["공전", "약 27.3일"], ["지구 거리", "평균 38.4만 km"], ["중력", "지구의 약 1/6"], ["대기", "거의 없음"]],
    facts: ["지구와의 조석 고정 때문에 거의 같은 면을 바라봐요.", "달의 중력은 지구의 조석 현상에 큰 영향을 줘요.", "달 표면의 어두운 평원은 과거 용암이 굳은 지역이에요."]
  },
  mesh: moonMesh,
  position: new THREE.Vector3()
});

let simulationDays = 0;
let speedDaysPerSecond = 7;
let previousSpeed = 7;
let paused = false;
let showOrbits = true;
let focusedId = null;
let focusDistance = 90;
let focusDirection = new THREE.Vector3(0.7, 0.45, 1).normalize();
let transitionFrames = 0;

const labels = new Map();
function createLabel(data) {
  const el = document.createElement("button");
  el.type = "button";
  el.className = "space-label";
  el.innerHTML = `<span>${data.icon}</span><strong>${data.name}</strong>`;
  el.addEventListener("click", () => focusBody(data.id));
  labelsLayer.appendChild(el);
  labels.set(data.id, el);
}
createLabel(SUN);
for (const data of BODY_DATA) createLabel(data);
createLabel(bodies.get("moon").data);

function bodyPosition(id) {
  return bodies.get(id)?.position || new THREE.Vector3();
}

function updateSimulation(dt) {
  if (!paused) simulationDays += dt * speedDaysPerSecond;

  for (const data of BODY_DATA) {
    const body = bodies.get(data.id);
    const mean = data.initial * DEG + (simulationDays / data.period) * TAU;
    const r = data.distance * (1 - data.eccentricity * Math.cos(mean));
    const inc = data.inclination * DEG;
    body.position.set(
      Math.cos(mean) * r,
      Math.sin(mean) * r * Math.sin(inc),
      Math.sin(mean) * r
    );
    body.root.position.copy(body.position);

    if (!paused) {
      const retro = data.rotationHours < 0 ? -1 : 1;
      const relative = Math.min(2.5, 24 / Math.max(8, Math.abs(data.rotationHours)));
      const factor = speedDaysPerSecond <= 0 ? 0 : Math.min(2.2, 0.6 + Math.pow(Math.max(speedDaysPerSecond, 0.001), 0.3) * 0.45);
      body.mesh.rotation.y += retro * relative * 0.22 * factor * dt;
    }
  }

  const earth = bodies.get("earth");
  const moon = bodies.get("moon");
  const moonAngle = (simulationDays / 27.321661) * TAU;
  moon.position.set(
    earth.position.x + Math.cos(moonAngle) * 11,
    earth.position.y + Math.sin(moonAngle * 2) * 1.25,
    earth.position.z + Math.sin(moonAngle) * 11
  );
  moon.mesh.position.copy(moon.position);
  moon.mesh.rotation.y = moonAngle;
  sunMesh.rotation.y += dt * 0.035;
}

function updateDateUI() {
  const d = new Date(EPOCH.getTime() + simulationDays * 86400000);
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  dateDisplay.textContent = `📅 ${y}년 ${m}월 ${day}일`;
}

function speedText(speed) {
  if (speed < 0.001) return "실시간";
  if (speed === 365) return "1년 / 초";
  return `${speed}일 / 초`;
}

function updateSpeedUI() {
  speedBadge.textContent = paused ? "일시정지" : speedText(speedDaysPerSecond);
  pauseBtn.textContent = paused ? "▶ 계속" : "⏸ 일시정지";
  pauseBtn.setAttribute("aria-pressed", String(paused));
  document.querySelectorAll(".speed-btn").forEach((btn) => {
    const value = Number(btn.dataset.speed);
    btn.classList.toggle("active", !paused && Math.abs(value - speedDaysPerSecond) < 1e-8);
  });
}

function renderRibbon() {
  const items = [SUN, ...BODY_DATA];
  planetRibbon.innerHTML = items.map((d) => `<button type="button" data-body="${d.id}"><span>${d.icon}</span>${d.name}</button>`).join("");
  planetRibbon.addEventListener("click", (event) => {
    const btn = event.target.closest("button[data-body]");
    if (btn) focusBody(btn.dataset.body);
  });
}

function fillDetail(data) {
  document.getElementById("detail-icon").textContent = data.icon;
  document.getElementById("detail-name").textContent = `${data.name} · ${data.en}`;
  document.getElementById("detail-category").textContent = data.category;
  document.getElementById("detail-highlight").textContent = `🌟 ${data.highlight}`;
  document.getElementById("detail-overview").textContent = data.overview;
  document.getElementById("detail-stats").innerHTML = data.stats.map(([k, v]) => `<div><span>${k}</span><strong>${v}</strong></div>`).join("");
  document.getElementById("detail-facts").innerHTML = data.facts.map((f) => `<li>${f}</li>`).join("");
}

function focusBody(id) {
  const body = bodies.get(id);
  if (!body) return;
  focusedId = id;
  const pos = body.position.clone();
  const radius = Math.max(body.data.radius || 5, 2);
  focusDistance = id === "sun" ? 72 : Math.max(28, radius * 6.8);
  focusDirection.copy(camera.position).sub(controls.target).normalize();
  if (!Number.isFinite(focusDirection.x) || focusDirection.lengthSq() < 0.1) focusDirection.set(0.7, 0.45, 1).normalize();
  transitionFrames = 90;
  fillDetail(body.data);
  detailCard.classList.remove("hidden");
  overviewBtn.classList.remove("hidden");
  document.querySelectorAll("#planet-ribbon button").forEach((btn) => btn.classList.toggle("selected", btn.dataset.body === id));
  if (id === "moon") {
    controls.target.copy(pos);
  }
}

function returnOverview() {
  focusedId = null;
  transitionFrames = 110;
  focusDistance = 0;
  detailCard.classList.add("hidden");
  overviewBtn.classList.add("hidden");
  document.querySelectorAll("#planet-ribbon button").forEach((btn) => btn.classList.remove("selected"));
}

function updateCamera() {
  if (focusedId) {
    const target = bodyPosition(focusedId);
    controls.target.lerp(target, transitionFrames > 0 ? 0.1 : 0.2);
    if (transitionFrames > 0) {
      const desired = target.clone().addScaledVector(focusDirection, focusDistance);
      camera.position.lerp(desired, 0.08);
      transitionFrames -= 1;
    }
  } else if (transitionFrames > 0) {
    controls.target.lerp(new THREE.Vector3(), 0.08);
    camera.position.lerp(new THREE.Vector3(0, 205, 430), 0.07);
    transitionFrames -= 1;
  }
}

function updateLabels() {
  const width = renderer.domElement.clientWidth;
  const height = renderer.domElement.clientHeight;
  for (const [id, el] of labels) {
    const body = bodies.get(id);
    if (!body) continue;
    const p = body.position.clone();
    const projected = p.clone().project(camera);
    const visible = projected.z > -1 && projected.z < 1 && Math.abs(projected.x) < 1.15 && Math.abs(projected.y) < 1.15;
    if (!visible) {
      el.style.opacity = "0";
      el.style.pointerEvents = "none";
      continue;
    }
    const x = (projected.x * 0.5 + 0.5) * width;
    const y = (-projected.y * 0.5 + 0.5) * height;
    const distance = camera.position.distanceTo(p);
    const scale = THREE.MathUtils.clamp(1.32 - distance / 700, 0.68, 1.05);
    el.style.transform = `translate(-50%, -50%) translate(${x}px, ${y}px) scale(${scale})`;
    el.style.opacity = focusedId && focusedId !== id ? "0.32" : "1";
    el.style.pointerEvents = "auto";
    el.classList.toggle("selected", focusedId === id);
  }
}

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
function setPointer(event) {
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
}

canvas.addEventListener("click", (event) => {
  setPointer(event);
  raycaster.setFromCamera(pointer, camera);
  const hits = raycaster.intersectObjects(pickables, false);
  const id = hits.find((hit) => hit.object.userData.bodyId)?.object.userData.bodyId;
  if (id) focusBody(id);
});

canvas.addEventListener("pointermove", (event) => {
  setPointer(event);
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObjects(pickables, false).some((h) => h.object.userData.bodyId);
  canvas.style.cursor = hit ? "pointer" : "grab";
});
canvas.addEventListener("pointerdown", () => { canvas.style.cursor = "grabbing"; });
canvas.addEventListener("pointerup", () => { canvas.style.cursor = "grab"; });

orbitsBtn.addEventListener("click", () => {
  showOrbits = !showOrbits;
  for (const line of orbitLines) line.visible = showOrbits;
  orbitsBtn.textContent = `🪐 궤도선 ${showOrbits ? "켜짐" : "꺼짐"}`;
  orbitsBtn.setAttribute("aria-pressed", String(showOrbits));
});

pauseBtn.addEventListener("click", () => {
  paused = !paused;
  if (!paused && speedDaysPerSecond === 0) speedDaysPerSecond = previousSpeed || 7;
  updateSpeedUI();
});

document.querySelectorAll(".speed-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const value = Number(btn.dataset.speed);
    if (!Number.isFinite(value)) return;
    speedDaysPerSecond = value;
    if (value > 0.001) previousSpeed = value;
    paused = false;
    updateSpeedUI();
  });
});

document.getElementById("prev10-btn").addEventListener("click", () => { simulationDays -= 10; updateDateUI(); });
document.getElementById("next10-btn").addEventListener("click", () => { simulationDays += 10; updateDateUI(); });
overviewBtn.addEventListener("click", returnOverview);
detailClose.addEventListener("click", returnOverview);

document.getElementById("help-btn").addEventListener("click", () => helpModal.classList.remove("hidden"));
document.getElementById("help-close").addEventListener("click", () => helpModal.classList.add("hidden"));
helpModal.addEventListener("click", (event) => { if (event.target === helpModal) helpModal.classList.add("hidden"); });
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    if (!helpModal.classList.contains("hidden")) helpModal.classList.add("hidden");
    else if (focusedId) returnOverview();
  }
});

function resize() {
  const width = Math.max(1, window.innerWidth);
  const height = Math.max(1, window.innerHeight);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize, { passive: true });

let last = performance.now();
let uiAccumulator = 0;
function animate(now) {
  const dt = Math.min(0.05, Math.max(0, (now - last) / 1000));
  last = now;
  if (!document.hidden) updateSimulation(dt);
  updateCamera();
  controls.update();
  renderer.render(scene, camera);
  updateLabels();
  uiAccumulator += dt;
  if (uiAccumulator > 0.16) {
    updateDateUI();
    uiAccumulator = 0;
  }
  requestAnimationFrame(animate);
}

document.addEventListener("visibilitychange", () => { last = performance.now(); });

renderRibbon();
resize();
updateSimulation(0);
updateDateUI();
updateSpeedUI();
requestAnimationFrame(animate);
