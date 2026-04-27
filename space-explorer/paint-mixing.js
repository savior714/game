import { initializePaintLights } from "./three-backdrop.js";

const colorButtons = Array.from(document.querySelectorAll("[data-color]"));
const threeLayer = document.getElementById("paint-mixing-three-layer");
const resultSwatch = document.getElementById("paint-result-swatch");
const statusText = document.getElementById("paint-mix-status");
const resetButton = document.getElementById("paint-reset-button");
const brightnessInput = document.getElementById("paint-brightness");
const brightnessStatus = document.getElementById("paint-brightness-status");

if (!resultSwatch || !statusText || !resetButton || !brightnessInput || !brightnessStatus || colorButtons.length === 0) {
  throw new Error("paint-mixing page is missing required elements.");
}

const COLOR_LIBRARY = {
  yellow: { label: "노랑", rgb: [244, 208, 63] },
  blue: { label: "파랑", rgb: [59, 130, 246] },
  red: { label: "빨강", rgb: [239, 68, 68] },
  white: { label: "하양", rgb: [250, 250, 250] },
  black: { label: "검정", rgb: [31, 41, 55] },
};

const SPECIAL_MIX_NAMES = {
  "yellow+blue": "초록",
  "blue+yellow": "초록",
  "red+yellow": "주황",
  "yellow+red": "주황",
  "red+blue": "보라",
  "blue+red": "보라",
  "red+yellow+blue": "갈색",
  "blue+red+yellow": "갈색",
  "yellow+blue+red": "갈색",
};

const selectedColors = new Set();
let brightness = Number(brightnessInput.value) / 100;

function toCssRgb(rgb) {
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

function clampChannel(value) {
  return Math.max(0, Math.min(255, Math.round(value)));
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

function mixSelectedColors(colorKeys) {
  if (colorKeys.length === 0) {
    return [243, 244, 246];
  }

  const linearRgb = colorKeys.map((key) => {
    const color = COLOR_LIBRARY[key];
    return color.rgb.map((channel) => channel / 255);
  });

  const subtracted = [0, 1, 2].map((index) => {
    const keepLight = linearRgb.reduce((acc, rgb) => acc * rgb[index], 1);
    return clampChannel(keepLight * 255);
  });

  return applyBrightness(subtracted, brightness);
}

function getMixName(colorKeys) {
  if (colorKeys.length === 0) {
    return "아직 색을 고르지 않았어요";
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

function renderSelection() {
  const sorted = Array.from(selectedColors).sort();
  const mixed = mixSelectedColors(sorted);
  const mixedName = getMixName(sorted);
  const chosenLabels = sorted.map((key) => COLOR_LIBRARY[key].label).join(" + ");

  resultSwatch.style.background = buildPaintTexture(mixed);

  if (sorted.length === 0) {
    statusText.textContent = "색을 선택하면 결과가 여기에 보여요.";
  } else {
    statusText.textContent = `${chosenLabels} -> ${mixedName}`;
  }

  colorButtons.forEach((button) => {
    const key = button.dataset.color;
    button.classList.toggle("is-selected", !!key && selectedColors.has(key));
  });
}

function resetSelection() {
  selectedColors.clear();
  brightness = 1;
  brightnessInput.value = "100";
  brightnessStatus.textContent = "밝기 100%";
  renderSelection();
}

function attachHandlers() {
  colorButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const colorKey = button.dataset.color;
      if (!colorKey || !COLOR_LIBRARY[colorKey]) {
        return;
      }

      if (selectedColors.has(colorKey)) {
        selectedColors.delete(colorKey);
      } else {
        selectedColors.add(colorKey);
      }

      renderSelection();
    });
  });

  resetButton.addEventListener("click", resetSelection);

  brightnessInput.addEventListener("input", () => {
    const next = Number(brightnessInput.value);
    brightness = Number.isFinite(next) ? next / 100 : 1;
    brightnessStatus.textContent = `밝기 ${Math.round(brightness * 100)}%`;
    renderSelection();
  });
}

renderSelection();
initializePaintLights(threeLayer);
attachHandlers();
