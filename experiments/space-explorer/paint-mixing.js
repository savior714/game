import { initializePaintLights } from "./three-backdrop.js";

const colorButtons = Array.from(document.querySelectorAll("[data-color]"));
const minusButtons = Array.from(document.querySelectorAll("[data-remove]"));
const modeTabs = Array.from(document.querySelectorAll("[data-mode]"));
const countBadges = Array.from(document.querySelectorAll("[data-count-for]"));
const threeLayer = document.getElementById("paint-mixing-three-layer");
const resultSwatch = document.getElementById("paint-result-swatch");
const statusText = document.getElementById("paint-mix-status");
const resetButton = document.getElementById("paint-reset-button");
const brightnessInput = document.getElementById("paint-brightness");
const brightnessStatus = document.getElementById("paint-brightness-status");
const brightnessGroup = document.getElementById("paint-brightness-group");
const liquidLayer = document.getElementById("paint-liquid-layer");
const dropLayer = document.getElementById("paint-drop-layer");
const bubbleLayer = document.getElementById("paint-bubble-layer");
const pipette = document.getElementById("paint-pipette");
const scoreText = document.getElementById("paint-score");
const starTotalText = document.getElementById("paint-star-total");
const streakText = document.getElementById("paint-streak");
const discoveryText = document.getElementById("paint-discovery-count");
const helpButton = document.getElementById("paint-help-button");
const soundButton = document.getElementById("paint-sound-button");
const missionPanel = document.getElementById("paint-mission-panel");
const missionChapter = document.getElementById("paint-mission-chapter");
const missionProgress = document.getElementById("paint-mission-progress");
const missionDifficulty = document.getElementById("paint-mission-difficulty");
const missionTitle = document.getElementById("paint-mission-title");
const missionStory = document.getElementById("paint-mission-story");
const targetSwatch = document.getElementById("paint-target-swatch");
const targetName = document.getElementById("paint-target-name");
const mineSwatch = document.getElementById("paint-mine-swatch");
const mineName = document.getElementById("paint-mine-name");
const similarityText = document.getElementById("paint-similarity");
const similarityFill = document.getElementById("paint-similarity-fill");
const missionToggle = document.getElementById("paint-mission-toggle");
const randomButton = document.getElementById("paint-random-button");
const missionMap = document.getElementById("paint-mission-map");
const missionGrid = document.getElementById("paint-mission-grid");
const freeNote = document.getElementById("paint-free-note");
const capacityText = document.getElementById("paint-capacity-text");
const capacityFill = document.getElementById("paint-capacity-fill");
const undoButton = document.getElementById("paint-undo-button");
const hintButton = document.getElementById("paint-hint-button");
const hintCount = document.getElementById("paint-hint-count");
const submitButton = document.getElementById("paint-submit-button");
const feedbackText = document.getElementById("paint-feedback");
const recipeBox = document.getElementById("paint-recipe");
const colorInfoText = document.getElementById("paint-color-info");
const collectionGrid = document.getElementById("paint-collection-grid");
const collectionSummary = document.getElementById("paint-collection-summary");
const successModal = document.getElementById("paint-success-modal");
const successStars = document.getElementById("paint-success-stars");
const successTitle = document.getElementById("paint-success-title");
const successScore = document.getElementById("paint-success-score");
const successRecipe = document.getElementById("paint-success-recipe");
const successClose = document.getElementById("paint-success-close");
const retryButton = document.getElementById("paint-retry-button");
const nextButton = document.getElementById("paint-next-button");
const helpModal = document.getElementById("paint-help-modal");
const helpClose = document.getElementById("paint-help-close");
const toastBox = document.getElementById("paint-toast");
const confettiLayer = document.getElementById("paint-confetti-layer");

if (
  !resultSwatch ||
  !statusText ||
  !resetButton ||
  !brightnessInput ||
  !brightnessStatus ||
  !liquidLayer ||
  !dropLayer ||
  !pipette ||
  !missionPanel ||
  !missionTitle ||
  !targetSwatch ||
  !submitButton ||
  !feedbackText ||
  !collectionGrid ||
  !successModal ||
  !helpModal ||
  colorButtons.length === 0
) {
  throw new Error("paint-mixing page is missing required elements.");
}

/* PAINT_COLOR_MATH_START */
/* 순수 색상 계산 영역: DOM에 의존하지 않아 Node 테스트에서 그대로 실행해 검증한다.
   물감은 빛(RGB 평균)이 아니라 안료 혼합(RYB 감산 혼합)으로 계산해야
   노랑+파랑=초록, 빨강+파랑=보라처럼 아이들이 배우는 색이 나온다. */
const COLOR_LIBRARY = {
  yellow: { label: "노랑", rgb: [255, 213, 0], tone: 880 },
  blue: { label: "파랑", rgb: [30, 90, 220], tone: 520 },
  red: { label: "빨강", rgb: [238, 54, 44], tone: 660 },
  white: { label: "하양", rgb: [250, 250, 250], tone: 1040 },
  black: { label: "검정", rgb: [35, 35, 40], tone: 340 },
};

// RYB 큐브 꼭짓점: 키는 (빨강, 노랑, 파랑) 축 0/1 조합, 값은 그 지점의 RGB.
const RYB_CUBE = {
  "000": [255, 255, 255],
  "100": [238, 54, 44],
  "010": [255, 213, 0],
  "001": [30, 90, 220],
  "110": [255, 128, 0],
  "101": [128, 52, 200],
  "011": [0, 176, 80],
  "111": [92, 58, 32],
};

const MAX_DROPS = 12;
const PASS_SIMILARITY = 70;
const TWO_STAR_SIMILARITY = 83;
const THREE_STAR_SIMILARITY = 93;
const DISCOVERY_SIMILARITY = 90;
const EMPTY_RGB = [243, 244, 246];

function clampChannel(value) {
  return Math.max(0, Math.min(255, Math.round(value)));
}

function toCssRgb(rgb) {
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

function applyBrightness(rgb, factor) {
  return rgb.map((channel) => clampChannel(channel * factor));
}

function offsetRgb(rgb, delta) {
  return rgb.map((channel) => clampChannel(channel + delta));
}

function rgba(rgb, alpha) {
  return `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})`;
}

function rgbToHex(rgb) {
  return `#${rgb.map((value) => value.toString(16).padStart(2, "0")).join("").toUpperCase()}`;
}

function buildPaintTexture(rgb) {
  const highlight = offsetRgb(rgb, 35);
  const shade = offsetRgb(rgb, -30);
  const deepShade = offsetRgb(rgb, -55);

  return [
    `radial-gradient(circle at 24% 22%, ${rgba(highlight, 0.9)} 0%, ${rgba(rgb, 0.76)} 36%, ${rgba(shade, 0.58)} 72%, ${rgba(deepShade, 0.64)} 100%)`,
    `radial-gradient(circle at 72% 68%, ${rgba(highlight, 0.2)} 0%, transparent 44%)`,
    `radial-gradient(circle at 40% 78%, ${rgba(shade, 0.18)} 0%, transparent 38%)`,
    `linear-gradient(145deg, ${rgba(offsetRgb(rgb, 24), 0.24)} 0%, ${rgba(offsetRgb(rgb, -24), 0.24)} 100%)`,
  ].join(", ");
}

// RYB 큐브 삼선형 보간: 비율 (r, y, b) 각 0~1을 RGB로 바꾼다.
function rybToRgb(r, y, b) {
  const channel = (key, index) => RYB_CUBE[key][index];
  const out = [0, 0, 0];
  for (let i = 0; i < 3; i += 1) {
    const x00 = channel("000", i) + (channel("100", i) - channel("000", i)) * r;
    const x10 = channel("010", i) + (channel("110", i) - channel("010", i)) * r;
    const x01 = channel("001", i) + (channel("101", i) - channel("001", i)) * r;
    const x11 = channel("011", i) + (channel("111", i) - channel("011", i)) * r;
    const y0 = x00 + (x10 - x00) * y;
    const y1 = x01 + (x11 - x01) * y;
    out[i] = clampChannel(y0 + (y1 - y0) * b);
  }
  return out;
}

function entriesToRecipe(activeEntries) {
  const recipe = {};
  for (const entry of activeEntries) {
    if (entry.intensity > 0) {
      recipe[entry.key] = entry.intensity;
    }
  }
  return recipe;
}

function recipeToEntries(recipe) {
  return Object.entries(recipe)
    .filter(([, intensity]) => intensity > 0)
    .map(([key, intensity]) => ({ key, intensity }))
    .sort((a, b) => a.key.localeCompare(b.key));
}

// 방울 비율이 색을 결정한다: 노랑2+파랑2와 노랑1+파랑1은 같은 초록이다.
function mixEntriesToRgb(activeEntries, brightnessFactor = 1) {
  const recipe = entriesToRecipe(activeEntries);
  const red = recipe.red ?? 0;
  const yellow = recipe.yellow ?? 0;
  const blue = recipe.blue ?? 0;
  const white = recipe.white ?? 0;
  const black = recipe.black ?? 0;
  const chromatic = red + yellow + blue;
  const total = chromatic + white + black;

  if (total === 0) {
    return applyBrightness([...EMPTY_RGB], brightnessFactor);
  }

  let mixed;
  if (chromatic === 0) {
    // 하양·검정만 섞으면 회색 계열이 된다.
    if (black === 0) {
      mixed = [250, 250, 250];
    } else if (white === 0) {
      mixed = [35, 35, 40];
    } else {
      const gray = clampChannel(250 + (35 - 250) * (black / (white + black)));
      mixed = [gray, gray, clampChannel(gray + 5)];
    }
  } else {
    const strongest = Math.max(red, yellow, blue);
    mixed = rybToRgb(red / strongest, yellow / strongest, blue / strongest);
    if (white > 0) {
      const tint = (white / (chromatic + white)) * 0.82;
      mixed = mixed.map((value) => clampChannel(value + (255 - value) * tint));
    }
    if (black > 0) {
      const shade = (black / (chromatic + black)) * 0.78;
      mixed = mixed.map((value) => clampChannel(value * (1 - shade) + 18 * shade));
    }
  }

  return applyBrightness(mixed, brightnessFactor);
}

function rgbToLab(rgb) {
  const linear = rgb.map((value) => {
    const srgb = value / 255;
    return srgb <= 0.04045 ? srgb / 12.92 : ((srgb + 0.055) / 1.055) ** 2.4;
  });
  const pivot = (t) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116);
  const fx = pivot((linear[0] * 0.4124 + linear[1] * 0.3576 + linear[2] * 0.1805) / 0.95047);
  const fy = pivot(linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722);
  const fz = pivot((linear[0] * 0.0193 + linear[1] * 0.1192 + linear[2] * 0.9505) / 1.08883);
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}

function computeColorDistance(rgbA, rgbB) {
  const labA = rgbToLab(rgbA);
  const labB = rgbToLab(rgbB);
  return Math.hypot(labA[0] - labB[0], labA[1] - labB[1], labA[2] - labB[2]);
}

// Lab 거리 → 아이에게 보여줄 "닮은 정도 %". 비율이 한 방울 어긋나면 70~85%대가 된다.
function computeColorSimilarity(rgbA, rgbB) {
  const similarity = Math.round(100 - computeColorDistance(rgbA, rgbB) * 0.92);
  return Math.max(0, Math.min(100, similarity));
}

function getStarCount(similarity) {
  if (similarity >= THREE_STAR_SIMILARITY) return 3;
  if (similarity >= TWO_STAR_SIMILARITY) return 2;
  if (similarity >= PASS_SIMILARITY) return 1;
  return 0;
}

// 색상 도감: 레시피로 정의해 목표 색과 판정 기준이 항상 같은 계산을 거친다.
const NAMED_COLORS = [
  { id: "red", name: "빨강", emoji: "🍎", recipe: { red: 1 } },
  { id: "yellow", name: "노랑", emoji: "🍋", recipe: { yellow: 1 } },
  { id: "blue", name: "파랑", emoji: "💧", recipe: { blue: 1 } },
  { id: "green", name: "초록", emoji: "🍃", recipe: { yellow: 1, blue: 1 } },
  { id: "orange", name: "주황", emoji: "🥕", recipe: { red: 1, yellow: 1 } },
  { id: "purple", name: "보라", emoji: "🍇", recipe: { red: 1, blue: 1 } },
  { id: "pink", name: "분홍", emoji: "🌸", recipe: { red: 1, white: 2 } },
  { id: "sky", name: "하늘", emoji: "☁️", recipe: { blue: 1, white: 2 } },
  { id: "lime", name: "연두", emoji: "🌱", recipe: { yellow: 2, blue: 1 } },
  { id: "tangerine", name: "귤색", emoji: "🍊", recipe: { yellow: 2, red: 1 } },
  { id: "scarlet", name: "다홍", emoji: "🌺", recipe: { red: 2, yellow: 1 } },
  { id: "plum", name: "자주", emoji: "💜", recipe: { red: 2, blue: 1 } },
  { id: "indigo", name: "남보라", emoji: "🔮", recipe: { red: 1, blue: 2 } },
  { id: "teal", name: "청록", emoji: "🐢", recipe: { blue: 2, yellow: 1 } },
  { id: "mint", name: "민트", emoji: "🌊", recipe: { blue: 2, yellow: 1, white: 2 } },
  { id: "peach", name: "복숭아", emoji: "🍑", recipe: { red: 1, yellow: 1, white: 2 } },
  { id: "lavender", name: "라벤더", emoji: "🪻", recipe: { red: 1, blue: 1, white: 2 } },
  { id: "forest", name: "깊은 숲", emoji: "🌲", recipe: { yellow: 1, blue: 1, black: 1 } },
  { id: "gray", name: "회색", emoji: "🪨", recipe: { black: 1, white: 2 } },
  { id: "brown", name: "갈색", emoji: "🍫", recipe: { red: 1, yellow: 1, blue: 1 } },
];

function getNamedColorRgb(named) {
  return mixEntriesToRgb(recipeToEntries(named.recipe), 1);
}

function findNearestNamedColor(rgb) {
  let nearest = null;
  for (const named of NAMED_COLORS) {
    const namedRgb = getNamedColorRgb(named);
    const similarity = computeColorSimilarity(rgb, namedRgb);
    if (!nearest || similarity > nearest.similarity) {
      nearest = { ...named, rgb: namedRgb, similarity };
    }
  }
  return nearest;
}

function formatRecipe(recipe) {
  return recipeToEntries(recipe)
    .map((entry) => `${COLOR_LIBRARY[entry.key].label} ${entry.intensity}방울`)
    .join(" + ");
}
/* PAINT_COLOR_MATH_END */

const SPECIAL_MIX_NAMES = {
  "yellow+blue": "초록",
  "blue+yellow": "초록",
  "red+yellow": "주황",
  "yellow+red": "주황",
  "red+blue": "보라",
  "blue+red": "보라",
  "red+white": "분홍",
  "blue+white": "하늘",
  "black+white": "회색",
  "red+yellow+blue": "갈색",
  "blue+red+yellow": "갈색",
  "yellow+blue+red": "갈색",
};

const MISSIONS = [
  { id: "mission-green", chapter: "1장 · 삼원색 친구들", difficulty: "쉬움", emoji: "🍃", title: "초록 나뭇잎", colorName: "초록", story: "🐰 토끼가 나뭇잎 그림을 그리고 싶대요. 초록 물감을 만들어 주세요!", recipe: { yellow: 1, blue: 1 } },
  { id: "mission-orange", chapter: "1장 · 삼원색 친구들", difficulty: "쉬움", emoji: "🥕", title: "주황 당근", colorName: "주황", story: "🐴 말이 당근 색이 필요하대요. 어떤 두 색을 섞으면 될까요?", recipe: { red: 1, yellow: 1 } },
  { id: "mission-purple", chapter: "1장 · 삼원색 친구들", difficulty: "쉬움", emoji: "🍇", title: "보라 포도", colorName: "보라", story: "🦊 여우가 포도를 그리고 있어요. 보라색을 만들어 주세요!", recipe: { red: 1, blue: 1 } },
  { id: "mission-pink", chapter: "1장 · 삼원색 친구들", difficulty: "쉬움", emoji: "🌸", title: "분홍 벚꽃", colorName: "분홍", story: "🐷 돼지가 벚꽃잎을 그리려면 연한 분홍이 필요하대요. 하양을 써 보세요!", recipe: { red: 1, white: 2 } },
  { id: "mission-sky", chapter: "2장 · 비율의 비밀", difficulty: "보통", emoji: "☁️", title: "하늘 구름", colorName: "하늘", story: "🐣 병아리가 하늘을 그리고 있어요. 연한 파랑, 하늘색을 만들어 주세요!", recipe: { blue: 1, white: 2 } },
  { id: "mission-lime", chapter: "2장 · 비율의 비밀", difficulty: "보통", emoji: "🌱", title: "연두 새싹", colorName: "연두", story: "🐸 개구리가 새싹 색을 찾고 있어요. 노랑을 파랑보다 많이 넣어 보세요!", recipe: { yellow: 2, blue: 1 } },
  { id: "mission-tangerine", chapter: "2장 · 비율의 비밀", difficulty: "보통", emoji: "🍊", title: "귤 오렌지", colorName: "귤색", story: "🐱 고양이가 귤을 그리고 싶대요. 주황보다 더 노란 귤색에 도전!", recipe: { yellow: 2, red: 1 } },
  { id: "mission-plum", chapter: "2장 · 비율의 비밀", difficulty: "보통", emoji: "💜", title: "자주 자두", colorName: "자주", story: "🦉 부엉이가 자두 색을 찾고 있어요. 빨강이 많은 보라예요!", recipe: { red: 2, blue: 1 } },
  { id: "mission-gray", chapter: "3장 · 컬러 마스터", difficulty: "어려움", emoji: "🪨", title: "구름 회색", colorName: "회색", story: "🐨 코알라가 돌멩이를 그리고 있어요. 검정과 하양만으로 회색을 만들 수 있을까요?", recipe: { black: 1, white: 2 } },
  { id: "mission-forest", chapter: "3장 · 컬러 마스터", difficulty: "어려움", emoji: "🌲", title: "깊은 숲 초록", colorName: "깊은 숲", story: "🐻 곰이 깊은 숲을 그리고 있어요. 초록을 더 진하게 만들려면 무엇이 필요할까요?", recipe: { yellow: 1, blue: 1, black: 1 } },
  { id: "mission-mint", chapter: "3장 · 컬러 마스터", difficulty: "어려움", emoji: "🌊", title: "민트 파도", colorName: "민트", story: "🐬 돌고래가 민트색 파도를 그리고 싶대요. 세 가지 물감이 필요해요!", recipe: { blue: 2, yellow: 1, white: 2 } },
  { id: "mission-brown", chapter: "3장 · 컬러 마스터", difficulty: "마스터", emoji: "🍫", title: "초콜릿 갈색", colorName: "갈색", story: "👑 마지막 미션! 세 가지 기본 물감을 모두 섞으면 어떤 색이 될까요?", recipe: { red: 1, yellow: 1, blue: 1 } },
];

const STORAGE_KEY = "aiden_paint_mixing_game_v1";
const KEYBOARD_COLORS = ["yellow", "blue", "red", "white", "black"];

const colorIntensity = new Map();
const dropHistory = [];
let brightness = Number(brightnessInput.value) / 100;
let lastDropX = 52;
let mode = "game";
let currentMission = MISSIONS[0];
let currentMissionIndex = 0;
let isRandomMission = false;
let targetRgb = getMissionRgb(currentMission);
let attempts = 0;
let hintsUsed = 0;
let roundCleared = false;
let lastSimilarity = null;
let toastTimer = 0;
let lastFocusedElement = null;
let audioContext = null;
let progress = loadProgress();

function getMissionRgb(mission) {
  return mixEntriesToRgb(recipeToEntries(mission.recipe), 1);
}

function createDefaultProgress() {
  return {
    version: 1,
    bestStars: {},
    bestScores: {},
    randomScore: 0,
    discovered: [],
    streak: 0,
    soundOn: true,
    lastMissionIndex: 0,
  };
}

// localStorage 표현은 신뢰할 수 없으므로 알려진 미션·색 id만 골라 정규화한다.
function loadProgress() {
  const fallback = createDefaultProgress();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || parsed.version !== 1) return fallback;

    const missionIds = new Set(MISSIONS.map((mission) => mission.id));
    const colorIds = new Set(NAMED_COLORS.map((named) => named.id));
    const cleanStars = {};
    const cleanScores = {};
    if (parsed.bestStars && typeof parsed.bestStars === "object") {
      for (const [id, value] of Object.entries(parsed.bestStars)) {
        if (missionIds.has(id) && Number.isInteger(value) && value >= 0 && value <= 3) {
          cleanStars[id] = value;
        }
      }
    }
    if (parsed.bestScores && typeof parsed.bestScores === "object") {
      for (const [id, value] of Object.entries(parsed.bestScores)) {
        if (missionIds.has(id) && Number.isFinite(value) && value >= 0) {
          cleanScores[id] = Math.round(value);
        }
      }
    }
    return {
      version: 1,
      bestStars: cleanStars,
      bestScores: cleanScores,
      randomScore: Number.isFinite(parsed.randomScore) && parsed.randomScore >= 0 ? Math.round(parsed.randomScore) : 0,
      discovered: Array.isArray(parsed.discovered) ? parsed.discovered.filter((id) => colorIds.has(id)) : [],
      streak: Number.isInteger(parsed.streak) && parsed.streak >= 0 ? parsed.streak : 0,
      soundOn: parsed.soundOn !== false,
      lastMissionIndex:
        Number.isInteger(parsed.lastMissionIndex) && parsed.lastMissionIndex >= 0 && parsed.lastMissionIndex < MISSIONS.length
          ? parsed.lastMissionIndex
          : 0,
    };
  } catch {
    return fallback;
  }
}

function saveProgress() {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  } catch {
    // 저장 공간이 없어도 게임 자체는 계속할 수 있다.
  }
}

function getTotalScore() {
  const missionScore = Object.values(progress.bestScores).reduce((acc, value) => acc + value, 0);
  return missionScore + progress.randomScore;
}

function getTotalStars() {
  return Object.values(progress.bestStars).reduce((acc, value) => acc + value, 0);
}

function getColorIntensity(colorKey) {
  return colorIntensity.get(colorKey) ?? 0;
}

function increaseColorIntensity(colorKey) {
  const next = getColorIntensity(colorKey) + 1;
  colorIntensity.set(colorKey, next);
  return next;
}

function decreaseColorIntensity(colorKey) {
  const next = getColorIntensity(colorKey) - 1;
  if (next <= 0) {
    colorIntensity.delete(colorKey);
    return 0;
  }
  colorIntensity.set(colorKey, next);
  return next;
}

function getActiveEntries() {
  return Array.from(colorIntensity.entries())
    .filter(([, intensity]) => intensity > 0)
    .map(([key, intensity]) => ({ key, intensity }))
    .sort((a, b) => a.key.localeCompare(b.key));
}

function getTotalDrops() {
  return getActiveEntries().reduce((acc, entry) => acc + entry.intensity, 0);
}

function mixSelectedColors(activeEntries) {
  return mixEntriesToRgb(activeEntries, brightness);
}

// 채점용 색: 조명 밝기는 자유 실험 미리보기 전용이라 채점에서 뺀다.
function getScoringRgb() {
  return mixEntriesToRgb(getActiveEntries(), 1);
}

function getMixName(colorKeys, totalDrops, rgb = null) {
  if (colorKeys.length === 0 || totalDrops === 0) {
    return "아직 색을 고르지 않았어요";
  }

  if (rgb) {
    const nearest = findNearestNamedColor(rgb);
    if (nearest && nearest.similarity >= 62) {
      return nearest.name;
    }
    return "새로운 혼합색";
  }

  if (colorKeys.length === 1) {
    return COLOR_LIBRARY[colorKeys[0]].label;
  }

  const signature = colorKeys.join("+");
  if (SPECIAL_MIX_NAMES[signature]) {
    return SPECIAL_MIX_NAMES[signature];
  }

  return "새로운 혼합색";
}

function spawnDropRipple(hexColor, xPercent) {
  const ripple = document.createElement("span");
  ripple.className = "drop-ripple";
  ripple.style.left = `${xPercent}%`;
  ripple.style.top = "74%";
  ripple.style.color = hexColor;
  dropLayer.append(ripple);
  window.setTimeout(() => ripple.remove(), 560);
}

function spawnBubbles(count = 3) {
  if (!bubbleLayer) return;
  for (let i = 0; i < count; i += 1) {
    const bubble = document.createElement("span");
    bubble.className = "paint-bubble";
    const size = 6 + Math.random() * 10;
    bubble.style.width = `${size}px`;
    bubble.style.height = `${size}px`;
    bubble.style.left = `${24 + Math.random() * 52}%`;
    bubble.style.animationDuration = `${700 + Math.random() * 500}ms`;
    bubbleLayer.append(bubble);
    window.setTimeout(() => bubble.remove(), 1300);
  }
}

function animatePipetteDrop(rgb, xPercent) {
  pipette.classList.add("is-dropping");
  pipette.style.background = `linear-gradient(180deg, ${toCssRgb(offsetRgb(rgb, 30))} 0%, ${toCssRgb(rgb)} 100%)`;

  const drop = document.createElement("span");
  drop.className = "paint-drop";
  drop.style.left = `${xPercent}%`;
  drop.style.top = "22px";
  drop.style.background = toCssRgb(rgb);
  dropLayer.append(drop);

  liquidLayer.classList.remove("is-swirling");
  // 애니메이션 재시작을 위해 리플로우를 강제한다.
  void liquidLayer.offsetWidth;
  liquidLayer.classList.add("is-swirling");

  window.setTimeout(() => {
    drop.remove();
    spawnDropRipple(toCssRgb(rgb), xPercent);
    spawnBubbles(3);
    pipette.classList.remove("is-dropping");
  }, 560);
}

/* ── 소리 (WebAudio 합성, 외부 파일 없음) ────────────────── */
function ensureAudio() {
  if (!progress.soundOn) return null;
  try {
    if (!audioContext) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (!AudioContextClass) return null;
      audioContext = new AudioContextClass();
    }
    if (audioContext.state === "suspended") {
      void audioContext.resume();
    }
    return audioContext;
  } catch {
    return null;
  }
}

function playTone(freq, { delay = 0, duration = 0.16, type = "sine", volume = 0.14 } = {}) {
  const ctx = ensureAudio();
  if (!ctx) return;
  const start = ctx.currentTime + delay;
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  oscillator.type = type;
  oscillator.frequency.setValueAtTime(freq, start);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(volume, start + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  oscillator.connect(gain).connect(ctx.destination);
  oscillator.start(start);
  oscillator.stop(start + duration + 0.05);
}

function playDropSound(colorKey) {
  const base = COLOR_LIBRARY[colorKey]?.tone ?? 620;
  playTone(base, { duration: 0.12, type: "sine" });
  playTone(base * 1.5, { delay: 0.05, duration: 0.1, volume: 0.07 });
}

function playSuccessSound(stars) {
  const notes = [523.25, 659.25, 783.99, 1046.5];
  notes.slice(0, 2 + stars).forEach((freq, index) => {
    playTone(freq, { delay: index * 0.1, duration: 0.24, type: "triangle", volume: 0.16 });
  });
}

function playEncourageSound() {
  playTone(392, { duration: 0.14, type: "triangle", volume: 0.1 });
  playTone(329.63, { delay: 0.11, duration: 0.18, type: "triangle", volume: 0.09 });
}

/* ── 화면 렌더링 ────────────────────────────────────────── */
function showToast(message) {
  if (!toastBox) return;
  toastBox.textContent = message;
  toastBox.hidden = false;
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => {
    toastBox.hidden = true;
  }, 2600);
}

function setFeedback(message) {
  feedbackText.textContent = message;
}

function repeatStars(count) {
  return "⭐".repeat(count) + "☆".repeat(3 - count);
}

function renderHud() {
  scoreText.textContent = String(getTotalScore());
  starTotalText.textContent = `⭐ ${getTotalStars()} / ${MISSIONS.length * 3}`;
  streakText.textContent = `🔥 ${progress.streak}`;
  discoveryText.textContent = `🎨 ${progress.discovered.length} / ${NAMED_COLORS.length}`;
}

function maybeDiscoverColor(rgb) {
  if (getTotalDrops() === 0) return;
  const nearest = findNearestNamedColor(rgb);
  if (!nearest || nearest.similarity < DISCOVERY_SIMILARITY) return;
  if (progress.discovered.includes(nearest.id)) return;
  progress.discovered.push(nearest.id);
  saveProgress();
  renderHud();
  renderCollection();
  showToast(`🎉 새로운 색 발견! ${nearest.emoji} ${nearest.name} (도감 ${progress.discovered.length}/${NAMED_COLORS.length})`);
  playTone(1174.66, { duration: 0.2, type: "triangle", volume: 0.12 });
}

function renderSelection() {
  const activeEntries = getActiveEntries();
  const sorted = activeEntries.map((entry) => entry.key);
  const totalDrops = activeEntries.reduce((acc, entry) => acc + entry.intensity, 0);
  const mixed = mixSelectedColors(activeEntries);
  const scoringRgb = mixEntriesToRgb(activeEntries, 1);
  const mixedName = getMixName(sorted, totalDrops, totalDrops > 0 ? scoringRgb : null);
  const chosenLabels = activeEntries
    .map((entry) => `${COLOR_LIBRARY[entry.key].label} x${entry.intensity}`)
    .join(" + ");

  resultSwatch.style.background = buildPaintTexture(mixed);
  liquidLayer.style.background = buildPaintTexture(mixed);
  liquidLayer.style.height = `${totalDrops === 0 ? 14 : 20 + (totalDrops / MAX_DROPS) * 58}%`;
  if (mineSwatch) {
    mineSwatch.style.background = buildPaintTexture(scoringRgb);
    mineName.textContent = totalDrops === 0 ? "아직 비었어요" : mixedName;
  }

  if (activeEntries.length === 0) {
    statusText.textContent = "색을 선택하면 결과가 여기에 보여요.";
  } else {
    statusText.textContent = `${chosenLabels} -> ${mixedName} (${totalDrops}방울)`;
  }
  colorInfoText.textContent =
    totalDrops === 0
      ? "색 코드가 여기에 보여요."
      : `내 색: ${mixedName} · ${rgbToHex(scoringRgb)} · RGB(${scoringRgb.join(", ")})`;

  recipeBox.replaceChildren();
  if (activeEntries.length === 0) {
    const empty = document.createElement("span");
    empty.className = "paint-recipe-empty";
    empty.textContent = "아직 넣은 물감이 없어요.";
    recipeBox.append(empty);
  } else {
    activeEntries.forEach((entry, index) => {
      if (index > 0) {
        const plus = document.createElement("span");
        plus.className = "paint-recipe-plus";
        plus.textContent = "+";
        recipeBox.append(plus);
      }
      const chip = document.createElement("span");
      chip.className = "paint-recipe-chip";
      const dot = document.createElement("span");
      dot.className = "paint-recipe-dot";
      dot.style.background = toCssRgb(COLOR_LIBRARY[entry.key].rgb);
      const label = document.createElement("span");
      label.textContent = `${COLOR_LIBRARY[entry.key].label} ${entry.intensity}방울`;
      chip.append(dot, label);
      recipeBox.append(chip);
    });
    const arrow = document.createElement("span");
    arrow.className = "paint-recipe-plus";
    arrow.textContent = "=";
    const result = document.createElement("span");
    result.className = "paint-recipe-chip paint-recipe-result";
    result.textContent = mixedName;
    recipeBox.append(arrow, result);
  }

  colorButtons.forEach((button) => {
    const key = button.dataset.color;
    button.classList.toggle("is-selected", !!key && getColorIntensity(key) > 0);
  });
  countBadges.forEach((badge) => {
    const key = badge.dataset.countFor;
    const count = key ? getColorIntensity(key) : 0;
    badge.hidden = count === 0;
    badge.textContent = `×${count}`;
  });
  minusButtons.forEach((button) => {
    const key = button.dataset.remove;
    button.disabled = !key || getColorIntensity(key) === 0 || roundCleared;
  });

  capacityText.textContent = `${totalDrops} / ${MAX_DROPS}방울`;
  capacityFill.style.width = `${(totalDrops / MAX_DROPS) * 100}%`;
  capacityFill.classList.toggle("is-full", totalDrops >= MAX_DROPS);
  undoButton.disabled = dropHistory.length === 0 || roundCleared;
  submitButton.disabled = mode !== "game" || totalDrops === 0 || roundCleared;
  colorButtons.forEach((button) => {
    button.disabled = roundCleared;
  });

  maybeDiscoverColor(scoringRgb);
}

function renderSimilarity(similarity) {
  lastSimilarity = similarity;
  if (similarity === null) {
    similarityText.textContent = "색을 섞은 뒤 확인해 보세요";
    similarityFill.style.width = "0%";
    return;
  }
  const stars = getStarCount(similarity);
  const band =
    stars === 3 ? "완벽해요!" : stars === 2 ? "아주 비슷해요!" : stars === 1 ? "비슷해요!" : "조금 더 고쳐 봐요";
  similarityText.textContent = `${similarity}% 닮았어요 · ${band}`;
  similarityFill.style.width = `${similarity}%`;
}

function isMissionUnlocked(index) {
  if (index <= 0) return true;
  if ((progress.bestStars[MISSIONS[index].id] ?? 0) >= 1) return true;
  return (progress.bestStars[MISSIONS[index - 1].id] ?? 0) >= 1;
}

function renderMissionGrid() {
  missionGrid.replaceChildren();
  MISSIONS.forEach((mission, index) => {
    const unlocked = isMissionUnlocked(index);
    const stars = progress.bestStars[mission.id] ?? 0;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "paint-mission-card";
    button.classList.toggle("is-locked", !unlocked);
    button.classList.toggle("is-current", !isRandomMission && index === currentMissionIndex);
    button.classList.toggle("is-cleared", stars >= 1);
    button.disabled = !unlocked;
    button.setAttribute("aria-label", unlocked ? `${index + 1}번 미션 ${mission.title}` : `${index + 1}번 미션 잠김`);

    const dot = document.createElement("span");
    dot.className = "paint-mission-dot";
    dot.style.background = unlocked ? buildPaintTexture(getMissionRgb(mission)) : "rgba(255,255,255,.12)";
    dot.textContent = unlocked ? "" : "🔒";
    const name = document.createElement("span");
    name.className = "paint-mission-card-title";
    name.textContent = `${index + 1}. ${mission.emoji} ${mission.title}`;
    const starLine = document.createElement("span");
    starLine.className = "paint-mission-card-stars";
    starLine.textContent = unlocked ? repeatStars(stars) : "이전 미션을 성공하면 열려요";
    button.append(dot, name, starLine);
    button.addEventListener("click", () => {
      playTone(700, { duration: 0.08, volume: 0.07 });
      startMission(index);
      toggleMissionMap(false);
    });
    missionGrid.append(button);
  });
}

function renderMission() {
  missionChapter.textContent = isRandomMission ? "랜덤 도전" : currentMission.chapter;
  missionProgress.textContent = isRandomMission ? "무한 도전" : `미션 ${currentMissionIndex + 1} / ${MISSIONS.length}`;
  missionDifficulty.textContent = currentMission.difficulty;
  missionTitle.textContent = `${currentMission.emoji} ${currentMission.title}`;
  missionStory.textContent = currentMission.story;
  targetSwatch.style.background = buildPaintTexture(targetRgb);
  targetSwatch.setAttribute("aria-label", `목표 색 ${currentMission.colorName} ${rgbToHex(targetRgb)}`);
  targetName.textContent = currentMission.colorName;
  hintCount.textContent = `${Math.max(0, 3 - hintsUsed)}개 남음`;
  hintButton.disabled = mode !== "game" || hintsUsed >= 3 || roundCleared;
  renderMissionGrid();
}

function renderCollection() {
  collectionGrid.replaceChildren();
  for (const named of NAMED_COLORS) {
    const found = progress.discovered.includes(named.id);
    const card = document.createElement("div");
    card.className = "paint-collection-item";
    card.classList.toggle("is-locked", !found);
    const swatch = document.createElement("span");
    swatch.className = "paint-collection-swatch";
    swatch.style.background = found ? buildPaintTexture(getNamedColorRgb(named)) : "rgba(255,255,255,.08)";
    swatch.textContent = found ? named.emoji : "?";
    const name = document.createElement("strong");
    name.textContent = found ? named.name : "아직 몰라요";
    const recipe = document.createElement("span");
    recipe.className = "paint-collection-recipe";
    recipe.textContent = found ? formatRecipe(named.recipe) : "섞어서 발견해 보세요";
    card.append(swatch, name, recipe);
    collectionGrid.append(card);
  }
  collectionSummary.textContent =
    progress.discovered.length >= NAMED_COLORS.length
      ? "👑 모든 색을 발견했어요! 진짜 컬러 마스터예요!"
      : `${NAMED_COLORS.length}가지 색 중 ${progress.discovered.length}가지를 발견했어요. 자유 실험실에서 마음껏 섞어 보세요.`;
}

/* ── 게임 진행 ──────────────────────────────────────────── */
function resetSelection() {
  colorIntensity.clear();
  dropHistory.length = 0;
  dropLayer.innerHTML = "";
  if (bubbleLayer) bubbleLayer.innerHTML = "";
  renderSimilarity(null);
  renderSelection();
}

function restartCurrentRound() {
  attempts = 0;
  hintsUsed = 0;
  roundCleared = false;
  resetSelection();
  renderMission();
  setFeedback(
    mode === "game"
      ? `${currentMission.colorName} 색을 만들어 보세요. 물감 튜브를 눌러 방울을 넣어요!`
      : "마음껏 섞어 보세요. 새로운 색을 만들면 도감에 모여요!",
  );
}

function startMission(index) {
  isRandomMission = false;
  currentMissionIndex = Math.max(0, Math.min(MISSIONS.length - 1, index));
  currentMission = MISSIONS[currentMissionIndex];
  targetRgb = getMissionRgb(currentMission);
  progress.lastMissionIndex = currentMissionIndex;
  saveProgress();
  restartCurrentRound();
}

function generateRandomMission() {
  const chromaticKeys = ["yellow", "blue", "red"];
  const shuffled = [...chromaticKeys].sort(() => Math.random() - 0.5);
  const recipe = {};
  const paintCount = Math.random() < 0.55 ? 2 : 1;
  for (let i = 0; i < paintCount; i += 1) {
    recipe[shuffled[i]] = Math.random() < 0.5 ? 1 : 2;
  }
  if (Math.random() < 0.45) {
    recipe.white = Math.random() < 0.5 ? 1 : 2;
  } else if (Math.random() < 0.22) {
    recipe.black = 1;
  }
  const rgb = mixEntriesToRgb(recipeToEntries(recipe), 1);
  const nearest = findNearestNamedColor(rgb);
  const colorName = nearest ? nearest.name : "비밀 색";
  return {
    id: "random",
    chapter: "랜덤 도전",
    difficulty: "랜덤",
    emoji: "🔀",
    title: `${colorName} 챌린지`,
    colorName,
    story: "🔀 랜덤 색이 나타났어요! 목표 색을 잘 보고 똑같이 만들어 보세요.",
    recipe,
  };
}

function startRandomMission() {
  isRandomMission = true;
  currentMission = generateRandomMission();
  targetRgb = getMissionRgb(currentMission);
  if (mode !== "game") {
    setMode("game", { keepMission: true });
  }
  restartCurrentRound();
  showToast("🔀 랜덤 색 도전 시작!");
}

function computeRoundScore(similarity) {
  const streakBonus = Math.min(progress.streak, 5) * 20;
  const score = similarity * 10 + streakBonus - hintsUsed * 40 - Math.max(0, attempts - 1) * 20;
  return Math.max(100, score);
}

function generateDirectionHint() {
  const current = entriesToRecipe(getActiveEntries());
  const target = currentMission.recipe;
  const currentTotal = Math.max(1, getTotalDrops());
  const targetTotal = Math.max(1, Object.values(target).reduce((acc, value) => acc + value, 0));
  let needKey = null;
  let needGap = 0.14;
  let extraKey = null;
  let extraGap = 0.14;
  for (const key of Object.keys(COLOR_LIBRARY)) {
    const diff = (target[key] ?? 0) / targetTotal - (current[key] ?? 0) / currentTotal;
    if (diff > needGap) {
      needGap = diff;
      needKey = key;
    }
    if (-diff > extraGap) {
      extraGap = -diff;
      extraKey = key;
    }
  }
  if (needKey) {
    return `${COLOR_LIBRARY[needKey].label} 물감을 조금 더 넣어 보세요!`;
  }
  if (extraKey) {
    return `${COLOR_LIBRARY[extraKey].label}이 조금 많아요. − 버튼으로 한 방울 빼 보세요!`;
  }
  return "비율이 거의 맞아요. 한 방울만 조심해서 고쳐 보세요!";
}

function getHintText(level) {
  const recipe = currentMission.recipe;
  const entries = recipeToEntries(recipe);
  if (level === 1) {
    const labels = entries.map((entry) => COLOR_LIBRARY[entry.key].label).join("와 ");
    return `💡 힌트 1: 이 색에는 ${labels} 물감이 들어가요.`;
  }
  if (level === 2) {
    const sorted = [...entries].sort((a, b) => b.intensity - a.intensity);
    const top = sorted[0];
    if (entries.length === 1) {
      return `💡 힌트 2: ${COLOR_LIBRARY[top.key].label} 물감 한 가지만 써 보세요.`;
    }
    const sameTop = sorted.filter((entry) => entry.intensity === top.intensity);
    if (sameTop.length === entries.length && entries.length > 1) {
      return "💡 힌트 2: 모든 물감을 똑같은 방울 수로 넣어 보세요.";
    }
    const others = sorted.slice(1).map((entry) => COLOR_LIBRARY[entry.key].label).join(", ");
    return `💡 힌트 2: ${COLOR_LIBRARY[top.key].label}이 가장 많아요. (${others}보다 많이!)`;
  }
  return `💡 힌트 3: 정답 레시피는 ${formatRecipe(recipe)}예요. 그대로 따라 해 보세요!`;
}

function useHint() {
  if (mode !== "game" || roundCleared || hintsUsed >= 3) return;
  hintsUsed += 1;
  setFeedback(getHintText(hintsUsed));
  playTone(987.77, { duration: 0.14, type: "triangle", volume: 0.1 });
  renderMission();
}

function spawnConfetti() {
  if (!confettiLayer) return;
  const colors = [...Object.values(COLOR_LIBRARY).map((color) => toCssRgb(color.rgb)), toCssRgb(targetRgb)];
  for (let i = 0; i < 42; i += 1) {
    const piece = document.createElement("span");
    piece.className = "paint-confetti-piece";
    piece.style.left = `${Math.random() * 100}%`;
    piece.style.background = colors[i % colors.length];
    piece.style.animationDelay = `${Math.random() * 0.35}s`;
    piece.style.animationDuration = `${1.2 + Math.random() * 0.9}s`;
    piece.style.setProperty("--confetti-drift", `${-70 + Math.random() * 140}px`);
    piece.style.setProperty("--confetti-spin", `${240 + Math.random() * 480}deg`);
    confettiLayer.append(piece);
    window.setTimeout(() => piece.remove(), 2600);
  }
}

function openModal(modal) {
  lastFocusedElement = document.activeElement;
  modal.hidden = false;
  const focusTarget = modal.querySelector("button:not([disabled])");
  if (focusTarget) focusTarget.focus();
}

function closeModal(modal) {
  modal.hidden = true;
  if (lastFocusedElement && typeof lastFocusedElement.focus === "function") {
    lastFocusedElement.focus();
  }
}

function isAllMissionsCleared() {
  return MISSIONS.every((mission) => (progress.bestStars[mission.id] ?? 0) >= 1);
}

function showSuccess(similarity, stars, score) {
  successStars.textContent = repeatStars(stars);
  successStars.setAttribute("aria-label", `별 ${stars}개 획득`);
  if (!isRandomMission && isAllMissionsCleared()) {
    successTitle.textContent = "👑 컬러 마스터 달성! 모든 미션을 끝냈어요!";
  } else {
    successTitle.textContent =
      stars === 3
        ? `완벽해요! ${currentMission.colorName} 색 완성!`
        : stars === 2
          ? `아주 잘했어요! ${currentMission.colorName} 색 완성!`
          : `해냈어요! ${currentMission.colorName} 색 완성!`;
  }
  successScore.textContent = `+${score}점 · 닮은 정도 ${similarity}% · 시도 ${attempts}번`;
  successRecipe.textContent = `정답 레시피: ${formatRecipe(currentMission.recipe)} = ${currentMission.colorName}`;
  const isLastMission = !isRandomMission && currentMissionIndex >= MISSIONS.length - 1;
  nextButton.textContent = isRandomMission || isLastMission ? "🔀 랜덤 색 도전" : "다음 색으로 →";
  spawnConfetti();
  playSuccessSound(stars);
  openModal(successModal);
  nextButton.focus();
}

function checkAnswer() {
  if (mode !== "game" || roundCleared || getTotalDrops() === 0) return;
  attempts += 1;
  const similarity = computeColorSimilarity(getScoringRgb(), targetRgb);
  const stars = getStarCount(similarity);
  renderSimilarity(similarity);

  if (stars === 0) {
    playEncourageSound();
    const cheer =
      similarity >= 55
        ? `거의 다 왔어요! ${similarity}% 닮았어요.`
        : similarity >= 35
          ? `좋은 시도예요! ${similarity}% 닮았어요.`
          : "괜찮아요, 색 섞기는 원래 여러 번 해 보는 거예요!";
    setFeedback(`${cheer} ${generateDirectionHint()} 그대로 더 섞어서 고칠 수 있어요.`);
    return;
  }

  roundCleared = true;
  const score = computeRoundScore(similarity);
  progress.streak += 1;
  if (isRandomMission) {
    progress.randomScore += score;
  } else {
    const id = currentMission.id;
    progress.bestStars[id] = Math.max(progress.bestStars[id] ?? 0, stars);
    progress.bestScores[id] = Math.max(progress.bestScores[id] ?? 0, score);
  }
  saveProgress();
  renderHud();
  renderMission();
  renderSelection();
  setFeedback(`🎉 ${similarity}% 닮았어요! 별 ${stars}개 획득!`);
  showSuccess(similarity, stars, score);
}

/* ── 조작 ───────────────────────────────────────────────── */
function addDrop(colorKey) {
  if (!COLOR_LIBRARY[colorKey]) return;
  if (mode === "game" && roundCleared) {
    showToast("🎉 이미 성공했어요. 다음 색으로 가 보세요!");
    return;
  }
  if (getTotalDrops() >= MAX_DROPS) {
    showToast("🧪 비커가 가득 찼어요! 한 방울 빼거나 비커를 비워 보세요.");
    playEncourageSound();
    return;
  }
  increaseColorIntensity(colorKey);
  dropHistory.push(colorKey);
  lastDropX = lastDropX > 62 ? 38 : lastDropX + 6;
  animatePipetteDrop(COLOR_LIBRARY[colorKey].rgb, lastDropX);
  playDropSound(colorKey);
  if (mode === "game" && lastSimilarity !== null) {
    renderSimilarity(null);
    similarityText.textContent = "색이 바뀌었어요. 다시 확인해 보세요";
  }
  renderSelection();
}

function removeOneDrop(colorKey) {
  if (getColorIntensity(colorKey) === 0 || roundCleared) return;
  decreaseColorIntensity(colorKey);
  const historyIndex = dropHistory.lastIndexOf(colorKey);
  if (historyIndex >= 0) dropHistory.splice(historyIndex, 1);
  playTone(300, { duration: 0.1, volume: 0.08 });
  if (mode === "game" && lastSimilarity !== null) {
    renderSimilarity(null);
    similarityText.textContent = "색이 바뀌었어요. 다시 확인해 보세요";
  }
  renderSelection();
}

function undoLastDrop() {
  const last = dropHistory.pop();
  if (!last || roundCleared) return;
  decreaseColorIntensity(last);
  playTone(340, { duration: 0.1, volume: 0.08 });
  renderSelection();
}

function toggleMissionMap(force) {
  const nextHidden = typeof force === "boolean" ? !force : !missionMap.hidden;
  missionMap.hidden = nextHidden;
  missionToggle.setAttribute("aria-expanded", String(!nextHidden));
  missionToggle.textContent = nextHidden ? "🗺️ 미션 목록 보기" : "🗺️ 미션 목록 닫기";
  if (!nextHidden) renderMissionGrid();
}

function setMode(nextMode, { keepMission = false } = {}) {
  mode = nextMode === "free" ? "free" : "game";
  modeTabs.forEach((tab) => {
    const active = tab.dataset.mode === mode;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  missionPanel.hidden = mode !== "game";
  freeNote.hidden = mode !== "free";
  submitButton.hidden = mode !== "game";
  hintButton.hidden = mode !== "game";
  brightnessInput.disabled = mode !== "free";
  brightnessGroup.classList.toggle("is-locked", mode !== "free");

  if (mode === "game") {
    brightness = 1;
    brightnessInput.value = "100";
    brightnessStatus.textContent = "밝기 100% (게임 중 고정)";
    if (!keepMission) {
      restartCurrentRound();
      return;
    }
  } else {
    brightnessStatus.textContent = `밝기 ${Math.round(brightness * 100)}%`;
    roundCleared = false;
    resetSelection();
    setFeedback("🧪 자유 실험실이에요. 마음껏 섞어 보고 새로운 색을 발견해 보세요!");
  }
  renderSelection();
  if (mode === "game") renderMission();
}

function findStartingMissionIndex() {
  const firstUncleared = MISSIONS.findIndex(
    (mission, index) => isMissionUnlocked(index) && (progress.bestStars[mission.id] ?? 0) === 0,
  );
  if (firstUncleared >= 0) return firstUncleared;
  return isMissionUnlocked(progress.lastMissionIndex) ? progress.lastMissionIndex : 0;
}

function updateSoundButton() {
  soundButton.textContent = progress.soundOn ? "🔊 소리 켬" : "🔇 소리 끔";
  soundButton.setAttribute("aria-pressed", String(progress.soundOn));
}

function attachHandlers() {
  colorButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const colorKey = button.dataset.color;
      if (!colorKey || !COLOR_LIBRARY[colorKey]) {
        return;
      }
      addDrop(colorKey);
    });
  });

  minusButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const colorKey = button.dataset.remove;
      if (colorKey) removeOneDrop(colorKey);
    });
  });

  modeTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      if (tab.dataset.mode) setMode(tab.dataset.mode);
    });
  });

  resetButton.addEventListener("click", () => {
    if (roundCleared) {
      // 성공한 라운드에서 비우면 시도·힌트까지 새 라운드로 시작한다.
      restartCurrentRound();
    } else {
      resetSelection();
      renderMission();
      setFeedback("🧼 비커를 깨끗이 비웠어요. 처음부터 다시 섞어 보세요!");
    }
    playTone(500, { duration: 0.1, volume: 0.07 });
  });
  undoButton.addEventListener("click", undoLastDrop);
  hintButton.addEventListener("click", useHint);
  submitButton.addEventListener("click", checkAnswer);
  missionToggle.addEventListener("click", () => toggleMissionMap());
  randomButton.addEventListener("click", startRandomMission);

  brightnessInput.addEventListener("input", () => {
    const next = Number(brightnessInput.value);
    brightness = Number.isFinite(next) ? next / 100 : 1;
    brightnessStatus.textContent = `밝기 ${Math.round(brightness * 100)}%`;
    renderSelection();
  });

  soundButton.addEventListener("click", () => {
    progress.soundOn = !progress.soundOn;
    saveProgress();
    updateSoundButton();
    if (progress.soundOn) playTone(880, { duration: 0.1, volume: 0.1 });
  });

  helpButton.addEventListener("click", () => openModal(helpModal));
  helpClose.addEventListener("click", () => closeModal(helpModal));
  successClose.addEventListener("click", () => closeModal(successModal));
  retryButton.addEventListener("click", () => {
    closeModal(successModal);
    restartCurrentRound();
  });
  nextButton.addEventListener("click", () => {
    closeModal(successModal);
    if (isRandomMission || currentMissionIndex >= MISSIONS.length - 1) {
      startRandomMission();
    } else {
      startMission(currentMissionIndex + 1);
    }
  });

  [helpModal, successModal].forEach((modal) => {
    modal.addEventListener("pointerdown", (event) => {
      if (event.target === modal) closeModal(modal);
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (!successModal.hidden) closeModal(successModal);
      else if (!helpModal.hidden) closeModal(helpModal);
      return;
    }
    if (!successModal.hidden || !helpModal.hidden) return;
    const target = event.target;
    if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) {
      return;
    }
    const index = Number(event.key) - 1;
    if (index >= 0 && index < KEYBOARD_COLORS.length) {
      addDrop(KEYBOARD_COLORS[index]);
    }
  });
}

/* ── 시작 ───────────────────────────────────────────────── */
updateSoundButton();
renderHud();
renderCollection();
startMission(findStartingMissionIndex());
setMode("game", { keepMission: true });
renderSelection();
initializePaintLights(threeLayer);
attachHandlers();
