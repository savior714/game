/*!
 * AIDEN POWER ISLAND 3D — 프로시저럴 PBR 텍스처 & 발광 스프라이트 생성기
 * 외부 이미지나 네트워크 없이 선명한 2D 캔버스/데이터 텍스처를 즉석에서 합성한다.
 */

import * as THREE from "three";

function makeCanvas(size) {
  if (typeof document !== "undefined" && typeof document.createElement === "function") {
    const el = document.createElement("canvas");
    el.width = size;
    el.height = size;
    const ctx = el.getContext("2d");
    if (ctx && typeof ctx.fillRect === "function" && "canvas" in ctx) {
      return { el, ctx };
    }
  }
  return null;
}

function solidDataTexture(r, g, b, a = 255) {
  const data = new Uint8Array([r, g, b, a]);
  const tex = new THREE.DataTexture(data, 1, 1, THREE.RGBAFormat);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.needsUpdate = true;
  return tex;
}

export function createIslandTextures() {
  const created = [];
  const track = (tex) => {
    created.push(tex);
    return tex;
  };

  // 1. 부드러운 방사형 발광 할로 스프라이트
  let glow;
  const glowCanvas = makeCanvas(128);
  if (glowCanvas) {
    const { el, ctx } = glowCanvas;
    const grad = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    grad.addColorStop(0, "rgba(255, 255, 255, 1)");
    grad.addColorStop(0.18, "rgba(255, 255, 255, 0.78)");
    grad.addColorStop(0.48, "rgba(255, 255, 255, 0.24)");
    grad.addColorStop(1, "rgba(255, 255, 255, 0)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 128, 128);
    glow = new THREE.CanvasTexture(el);
    glow.colorSpace = THREE.SRGBColorSpace;
  } else {
    glow = solidDataTexture(255, 255, 255, 255);
  }
  track(glow);

  // 2. 단결정 태양광 셀 그리드 텍스처
  let solar;
  const solarCanvas = makeCanvas(256);
  if (solarCanvas) {
    const { el, ctx } = solarCanvas;
    const bg = ctx.createLinearGradient(0, 0, 256, 256);
    bg.addColorStop(0, "#0b2a66");
    bg.addColorStop(0.5, "#124296");
    bg.addColorStop(1, "#092152");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, 256, 256);

    const cols = 4;
    const rows = 6;
    const cw = 256 / cols;
    const ch = 256 / rows;
    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c < cols; c += 1) {
        ctx.fillStyle = (r + c) % 2 === 0 ? "rgba(38, 108, 224, 0.36)" : "rgba(20, 74, 175, 0.32)";
        ctx.fillRect(c * cw + 3, r * ch + 3, cw - 6, ch - 6);
        ctx.strokeStyle = "rgba(155, 208, 255, 0.42)";
        ctx.lineWidth = 1.5;
        ctx.strokeRect(c * cw + 3, r * ch + 3, cw - 6, ch - 6);
        ctx.strokeStyle = "rgba(214, 238, 255, 0.25)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(c * cw + cw * 0.5, r * ch + 3);
        ctx.lineTo(c * cw + cw * 0.5, r * ch + ch - 3);
        ctx.stroke();
      }
    }
    ctx.strokeStyle = "#cbdcf7";
    ctx.lineWidth = 6;
    ctx.strokeRect(3, 3, 250, 250);
    solar = new THREE.CanvasTexture(el);
    solar.colorSpace = THREE.SRGBColorSpace;
  } else {
    solar = solidDataTexture(24, 82, 180);
  }
  track(solar);

  // 3. 나무 데크 판자 텍스처
  let wood;
  const woodCanvas = makeCanvas(256);
  if (woodCanvas) {
    const { el, ctx } = woodCanvas;
    ctx.fillStyle = "#7a5333";
    ctx.fillRect(0, 0, 256, 256);
    const planks = 8;
    const ph = 256 / planks;
    for (let i = 0; i < planks; i += 1) {
      ctx.fillStyle = i % 2 === 0 ? "#8a5e3b" : "#754e2f";
      ctx.fillRect(0, i * ph + 2, 256, ph - 3);
      ctx.fillStyle = "rgba(40, 22, 10, 0.45)";
      ctx.fillRect(0, i * ph, 256, 2);
    }
    wood = new THREE.CanvasTexture(el);
    wood.wrapS = THREE.RepeatWrapping;
    wood.wrapT = THREE.RepeatWrapping;
    wood.repeat.set(3, 3);
    wood.colorSpace = THREE.SRGBColorSpace;
  } else {
    wood = solidDataTexture(132, 90, 56);
  }
  track(wood);

  // 4. 아늑한 오두막 창문 격자 텍스처
  let windowPane;
  const winCanvas = makeCanvas(128);
  if (winCanvas) {
    const { el, ctx } = winCanvas;
    const g = ctx.createLinearGradient(0, 0, 0, 128);
    g.addColorStop(0, "#fff6cc");
    g.addColorStop(1, "#ffbe55");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, 128, 128);
    ctx.strokeStyle = "#3b281c";
    ctx.lineWidth = 10;
    ctx.strokeRect(5, 5, 118, 118);
    ctx.beginPath();
    ctx.moveTo(64, 0);
    ctx.lineTo(64, 128);
    ctx.moveTo(0, 64);
    ctx.lineTo(128, 64);
    ctx.stroke();
    windowPane = new THREE.CanvasTexture(el);
    windowPane.colorSpace = THREE.SRGBColorSpace;
  } else {
    windowPane = solidDataTexture(255, 224, 140);
  }
  track(windowPane);

  // 5. 화강암 댐 & 석조 광장 타일 텍스처
  let stone;
  const stoneCanvas = makeCanvas(256);
  if (stoneCanvas) {
    const { el, ctx } = stoneCanvas;
    ctx.fillStyle = "#5c687d";
    ctx.fillRect(0, 0, 256, 256);
    const rows = 8;
    const bh = 256 / rows;
    const bw = 64;
    for (let r = 0; r < rows; r += 1) {
      const offset = (r % 2) * (bw * 0.5);
      for (let c = -1; c <= 4; c += 1) {
        const shade = 84 + ((r * 17 + c * 29) % 24);
        ctx.fillStyle = `rgb(${shade}, ${shade + 9}, ${shade + 24})`;
        ctx.fillRect(c * bw + offset + 2, r * bh + 2, bw - 4, bh - 4);
      }
    }
    stone = new THREE.CanvasTexture(el);
    stone.wrapS = THREE.RepeatWrapping;
    stone.wrapT = THREE.RepeatWrapping;
    stone.repeat.set(3, 2);
    stone.colorSpace = THREE.SRGBColorSpace;
  } else {
    stone = solidDataTexture(96, 108, 130);
  }
  track(stone);

  return {
    glow,
    solar,
    wood,
    windowPane,
    stone,
    dispose() {
      created.forEach((tex) => tex.dispose());
    },
  };
}
