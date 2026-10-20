/*!
 * AIDEN POWER ISLAND 3D — 프로시저럴 PBR 텍스처 & 발광 스프라이트 생성기
 * 외부 이미지나 네트워크 없이 선명한 2D 캔버스/데이터 텍스처를 즉석에서 합성한다.
 */

import * as THREE from "three";

function makeCanvas(size, height = size) {
  if (typeof document === "undefined" || typeof document.createElement !== "function") return null;
  try {
    const el = document.createElement("canvas");
    if (!el) return null;
    el.width = size;
    el.height = height;
    if (typeof el.getContext !== "function") return null;
    const ctx = el.getContext("2d");
    // 실제 2D 컨텍스트인지 확인한다 (헤드리스 스텁/DOM shim 은 canvas 역참조가 없다)
    if (
      ctx &&
      ctx.canvas === el &&
      typeof ctx.fillRect === "function" &&
      typeof ctx.createImageData === "function"
    ) {
      return { el, ctx };
    }
  } catch {
    return null;
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

/** 캔버스가 없을 때(헤드리스/구형 브라우저) 쓰는 단색 폴백 */
function canvasTexture(size, height, draw, fallbackRGB, { repeat = null, srgb = true } = {}) {
  const surface = makeCanvas(size, height);
  if (!surface) return { texture: solidDataTexture(...fallbackRGB), usedCanvas: false, canvas: null };
  const { el, ctx } = surface;
  try {
    draw(ctx, size, height);
  } catch {
    return { texture: solidDataTexture(...fallbackRGB), usedCanvas: false, canvas: null };
  }
  const tex = new THREE.CanvasTexture(el);
  if (srgb) tex.colorSpace = THREE.SRGBColorSpace;
  if (repeat) {
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(repeat[0], repeat[1]);
  }
  return { texture: tex, usedCanvas: true, canvas: el };
}

/**
 * 알베도 캔버스의 휘도에서 탄젠트 스페이스 노멀맵을 만든다.
 * 지면·암벽·기와·판자 같은 표면이 조명을 받을 때 실제 요철처럼 반응해
 * "색칠한 종이" 느낌을 없앤다. 알베도와 정확히 같은 결을 쓰므로 얼룩이 어긋나지 않는다.
 */
function normalFromCanvas(source, strength = 2.2, repeat = null) {
  if (!source || typeof source.getContext !== "function") {
    const tex = new THREE.DataTexture(
      new Uint8Array([128, 128, 255, 255]),
      1,
      1,
      THREE.RGBAFormat
    );
    tex.needsUpdate = true;
    return tex;
  }
  const size = source.width;
  const height = source.height || size;
  const sourceCtx = source.getContext("2d");
  let src;
  try {
    src = sourceCtx.getImageData(0, 0, size, height);
  } catch {
    const tex = new THREE.DataTexture(
      new Uint8Array([128, 128, 255, 255]),
      1,
      1,
      THREE.RGBAFormat
    );
    tex.needsUpdate = true;
    return tex;
  }
  const lum = new Float32Array(size * height);
  for (let i = 0; i < size * height; i += 1) {
    lum[i] =
      (src.data[i * 4] * 0.299 + src.data[i * 4 + 1] * 0.587 + src.data[i * 4 + 2] * 0.114) /
      255;
  }
  const surface = makeCanvas(size, height);
  if (!surface) {
    const tex = new THREE.DataTexture(
      new Uint8Array([128, 128, 255, 255]),
      1,
      1,
      THREE.RGBAFormat
    );
    tex.needsUpdate = true;
    return tex;
  }
  const { el, ctx } = surface;
  const out = ctx.createImageData(size, height);
  const wrapX = (x) => (x + size) % size;
  const wrapY = (y) => (y + height) % height;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const left = lum[wrapY(y) * size + wrapX(x - 1)];
      const right = lum[wrapY(y) * size + wrapX(x + 1)];
      const up = lum[wrapY(y - 1) * size + wrapX(x)];
      const down = lum[wrapY(y + 1) * size + wrapX(x)];
      // uv 공간 기울기 (flipY 로 v축이 뒤집히므로 세로 성분은 부호를 맞춘다)
      let nx = -(right - left) * strength;
      let ny = (down - up) * strength;
      const len = Math.hypot(nx, ny, 1);
      nx /= len;
      ny /= len;
      const nz = 1 / len;
      const i = (y * size + x) * 4;
      out.data[i] = Math.round((nx * 0.5 + 0.5) * 255);
      out.data[i + 1] = Math.round((ny * 0.5 + 0.5) * 255);
      out.data[i + 2] = Math.round((nz * 0.5 + 0.5) * 255);
      out.data[i + 3] = 255;
    }
  }
  ctx.putImageData(out, 0, 0);
  const tex = new THREE.CanvasTexture(el);
  tex.colorSpace = THREE.NoColorSpace;
  if (repeat) {
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.RepeatWrapping;
    tex.repeat.set(repeat[0], repeat[1]);
  }
  return tex;
}

function seededRandom(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

export function createIslandTextures() {
  const created = [];
  const track = (tex) => {
    created.push(tex);
    return tex;
  };

  // 1. 부드러운 방사형 발광 할로 스프라이트
  let glow;
  const glowTex = canvasTexture(
    128,
    128,
    (ctx) => {
      const grad = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
      grad.addColorStop(0, "rgba(255, 255, 255, 1)");
      grad.addColorStop(0.16, "rgba(255, 255, 255, 0.82)");
      grad.addColorStop(0.42, "rgba(255, 255, 255, 0.26)");
      grad.addColorStop(0.72, "rgba(255, 255, 255, 0.07)");
      grad.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, 128, 128);
    },
    [255, 255, 255, 255]
  );
  glow = glowTex.texture;
  track(glow);

  // 2. 반짝이는 별 스프라이트 (중심 코어 + 4방향 광채)
  const starTex = canvasTexture(
    64,
    64,
    (ctx) => {
      const core = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
      core.addColorStop(0, "rgba(255, 255, 255, 1)");
      core.addColorStop(0.14, "rgba(255, 255, 255, 0.72)");
      core.addColorStop(0.4, "rgba(255, 255, 255, 0.14)");
      core.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = core;
      ctx.fillRect(0, 0, 64, 64);
      ctx.translate(32, 32);
      for (let arm = 0; arm < 4; arm += 1) {
        ctx.save();
        ctx.rotate((arm * Math.PI) / 2);
        const ray = ctx.createLinearGradient(0, 0, 30, 0);
        ray.addColorStop(0, "rgba(255, 255, 255, 0.55)");
        ray.addColorStop(0.45, "rgba(255, 255, 255, 0.12)");
        ray.addColorStop(1, "rgba(255, 255, 255, 0)");
        ctx.fillStyle = ray;
        ctx.beginPath();
        ctx.moveTo(0, -1.35);
        ctx.lineTo(30, 0);
        ctx.lineTo(0, 1.35);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
      }
    },
    [255, 255, 255, 255]
  );
  track(starTex.texture);

  // 3. 뭉게구름 스프라이트 (여러 겹의 부드러운 방울)
  const cloudTex = canvasTexture(
    256,
    128,
    (ctx) => {
      const rand = seededRandom(90210);
      const puffs = [
        [128, 82, 66],
        [86, 88, 48],
        [172, 90, 46],
        [112, 62, 44],
        [150, 58, 46],
        [64, 96, 30],
        [196, 98, 30],
      ];
      ctx.clearRect(0, 0, 256, 128);
      puffs.forEach(([cx, cy, r]) => {
        const g = ctx.createRadialGradient(cx, cy, r * 0.12, cx, cy, r);
        g.addColorStop(0, "rgba(255, 255, 255, 0.95)");
        g.addColorStop(0.5, "rgba(255, 255, 255, 0.6)");
        g.addColorStop(0.82, "rgba(255, 255, 255, 0.16)");
        g.addColorStop(1, "rgba(255, 255, 255, 0)");
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.fill();
      });
      // 아래쪽을 살짝 눌러 평평한 구름 밑동을 만든다
      const base = ctx.createLinearGradient(0, 104, 0, 128);
      base.addColorStop(0, "rgba(255, 255, 255, 0)");
      base.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = base;
      ctx.fillRect(0, 100, 256, 28);
    },
    [235, 243, 255, 255]
  );
  track(cloudTex.texture);

  // 4. 연기/수증기 퍼프
  const smokeTex = canvasTexture(
    96,
    96,
    (ctx) => {
      const g = ctx.createRadialGradient(48, 48, 4, 48, 48, 46);
      g.addColorStop(0, "rgba(255, 255, 255, 0.62)");
      g.addColorStop(0.45, "rgba(255, 255, 255, 0.3)");
      g.addColorStop(0.8, "rgba(255, 255, 255, 0.07)");
      g.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, 96, 96);
    },
    [220, 232, 245, 255]
  );
  track(smokeTex.texture);

  // 5. 태양 광선 스프라이트 (코어 + 방사형 빛살)
  const sunRaysTex = canvasTexture(
    256,
    256,
    (ctx) => {
      const rand = seededRandom(4242);
      ctx.translate(128, 128);
      for (let i = 0; i < 34; i += 1) {
        const angle = (i / 34) * Math.PI * 2 + rand() * 0.06;
        const len = 78 + rand() * 46;
        const spread = 0.012 + rand() * 0.03;
        const ray = ctx.createLinearGradient(0, 0, Math.cos(angle) * len, Math.sin(angle) * len);
        ray.addColorStop(0, "rgba(255, 238, 180, 0.5)");
        ray.addColorStop(0.45, "rgba(255, 214, 120, 0.16)");
        ray.addColorStop(1, "rgba(255, 190, 80, 0)");
        ctx.fillStyle = ray;
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(Math.cos(angle - spread) * len, Math.sin(angle - spread) * len);
        ctx.lineTo(Math.cos(angle + spread) * len, Math.sin(angle + spread) * len);
        ctx.closePath();
        ctx.fill();
      }
      const core = ctx.createRadialGradient(0, 0, 0, 0, 0, 74);
      core.addColorStop(0, "rgba(255, 255, 238, 0.96)");
      core.addColorStop(0.34, "rgba(255, 231, 158, 0.5)");
      core.addColorStop(0.68, "rgba(255, 198, 92, 0.14)");
      core.addColorStop(1, "rgba(255, 170, 60, 0)");
      ctx.fillStyle = core;
      ctx.beginPath();
      ctx.arc(0, 0, 76, 0, Math.PI * 2);
      ctx.fill();
    },
    [255, 230, 160, 255]
  );
  track(sunRaysTex.texture);

  // 6. 단결정 태양광 셀 그리드 텍스처
  const solarTex = canvasTexture(
    256,
    256,
    (ctx) => {
      const bg = ctx.createLinearGradient(0, 0, 256, 256);
      bg.addColorStop(0, "#0a2a6b");
      bg.addColorStop(0.5, "#164a9e");
      bg.addColorStop(1, "#071c47");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, 256, 256);

      const cols = 4;
      const rows = 6;
      const cw = 256 / cols;
      const ch = 256 / rows;
      for (let r = 0; r < rows; r += 1) {
        for (let c = 0; c < cols; c += 1) {
          const cellGrad = ctx.createLinearGradient(c * cw, r * ch, c * cw + cw, r * ch + ch);
          cellGrad.addColorStop(0, "rgba(48, 124, 238, 0.5)");
          cellGrad.addColorStop(1, "rgba(16, 60, 150, 0.42)");
          ctx.fillStyle = cellGrad;
          ctx.fillRect(c * cw + 3, r * ch + 3, cw - 6, ch - 6);
          ctx.strokeStyle = "rgba(170, 214, 255, 0.5)";
          ctx.lineWidth = 1.4;
          ctx.strokeRect(c * cw + 3, r * ch + 3, cw - 6, ch - 6);
          ctx.strokeStyle = "rgba(214, 238, 255, 0.22)";
          ctx.lineWidth = 1;
          for (let bus = 1; bus < 4; bus += 1) {
            ctx.beginPath();
            ctx.moveTo(c * cw + (cw * bus) / 4, r * ch + 3);
            ctx.lineTo(c * cw + (cw * bus) / 4, r * ch + ch - 3);
            ctx.stroke();
          }
          ctx.beginPath();
          ctx.moveTo(c * cw + cw * 0.5, r * ch + 3);
          ctx.lineTo(c * cw + cw * 0.5, r * ch + ch - 3);
          ctx.strokeStyle = "rgba(226, 245, 255, 0.34)";
          ctx.lineWidth = 1.6;
          ctx.stroke();
        }
      }
      ctx.strokeStyle = "#d7e6fb";
      ctx.lineWidth = 6;
      ctx.strokeRect(3, 3, 250, 250);
    },
    [24, 82, 180, 255]
  );
  track(solarTex.texture);

  // 7. 나무 데크 판자 텍스처 (결 + 못 자국)
  const woodTex = canvasTexture(
    256,
    256,
    (ctx) => {
      const rand = seededRandom(1337);
      ctx.fillStyle = "#7a5333";
      ctx.fillRect(0, 0, 256, 256);
      const planks = 8;
      const ph = 256 / planks;
      for (let i = 0; i < planks; i += 1) {
        const shade = i % 2 === 0 ? 0x8a5e3b : 0x744d2e;
        const r = (shade >> 16) & 255;
        const g = (shade >> 8) & 255;
        const b = shade & 255;
        ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
        ctx.fillRect(0, i * ph + 2, 256, ph - 3);
        // 나뭇결
        for (let line = 0; line < 7; line += 1) {
          ctx.strokeStyle = `rgba(${Math.max(0, r - 34)}, ${Math.max(0, g - 26)}, ${Math.max(0, b - 18)}, ${0.1 + rand() * 0.18})`;
          ctx.lineWidth = 0.8 + rand();
          ctx.beginPath();
          const y = i * ph + 5 + rand() * (ph - 10);
          ctx.moveTo(0, y);
          for (let x = 0; x <= 256; x += 32) {
            ctx.lineTo(x, y + Math.sin((x + i * 40) * 0.05) * 1.6 + (rand() - 0.5) * 1.2);
          }
          ctx.stroke();
        }
        ctx.fillStyle = "rgba(34, 18, 8, 0.5)";
        ctx.fillRect(0, i * ph, 256, 2);
        ctx.fillStyle = "rgba(226, 206, 168, 0.14)";
        ctx.fillRect(0, i * ph + 2, 256, 1);
        // 못 머리
        ctx.fillStyle = "rgba(28, 22, 18, 0.55)";
        [14, 128, 242].forEach((nx) => {
          ctx.beginPath();
          ctx.arc(nx, i * ph + ph * 0.5, 1.6, 0, Math.PI * 2);
          ctx.fill();
        });
      }
    },
    [132, 90, 56, 255],
    { repeat: [3, 3] }
  );
  track(woodTex.texture);

  // 8. 아늑한 오두막 창문 격자 텍스처
  const windowTex = canvasTexture(
    128,
    128,
    (ctx) => {
      const g = ctx.createLinearGradient(0, 0, 0, 128);
      g.addColorStop(0, "#fff8da");
      g.addColorStop(0.55, "#ffcf74");
      g.addColorStop(1, "#ffab3d");
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
      ctx.strokeStyle = "rgba(255, 255, 255, 0.35)";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(14, 118);
      ctx.lineTo(52, 12);
      ctx.stroke();
    },
    [255, 224, 140, 255]
  );
  track(windowTex.texture);

  // 9. 화강암 석조 타일 텍스처
  const stoneTex = canvasTexture(
    256,
    256,
    (ctx) => {
      const rand = seededRandom(777);
      ctx.fillStyle = "#4d586c";
      ctx.fillRect(0, 0, 256, 256);
      const rows = 8;
      const bh = 256 / rows;
      const bw = 64;
      for (let r = 0; r < rows; r += 1) {
        const offset = (r % 2) * (bw * 0.5);
        for (let c = -1; c <= 4; c += 1) {
          const shade = 92 + Math.floor(rand() * 26);
          const tint = rand() * 12;
          ctx.fillStyle = `rgb(${shade}, ${shade + 6}, ${shade + 18 + tint})`;
          ctx.fillRect(c * bw + offset + 2, r * bh + 2, bw - 4, bh - 4);
          ctx.fillStyle = "rgba(255, 255, 255, 0.06)";
          ctx.fillRect(c * bw + offset + 2, r * bh + 2, bw - 4, 2);
          ctx.fillStyle = "rgba(6, 12, 22, 0.16)";
          ctx.fillRect(c * bw + offset + 2, r * bh + bh - 6, bw - 4, 4);
        }
      }
      // 미세 균열
      for (let i = 0; i < 26; i += 1) {
        ctx.strokeStyle = `rgba(18, 24, 34, ${0.08 + rand() * 0.12})`;
        ctx.lineWidth = 0.7 + rand();
        ctx.beginPath();
        let x = rand() * 256;
        let y = rand() * 256;
        ctx.moveTo(x, y);
        for (let s = 0; s < 4; s += 1) {
          x += (rand() - 0.5) * 26;
          y += (rand() - 0.5) * 26;
          ctx.lineTo(x, y);
        }
        ctx.stroke();
      }
    },
    [96, 108, 130, 255],
    { repeat: [3, 2] }
  );
  track(stoneTex.texture);

  // 10. 잔디 지면 텍스처 (풀 포기 + 흙 얼룩)
  const grassTex = canvasTexture(
    256,
    256,
    (ctx) => {
      const rand = seededRandom(2024);
      const bg = ctx.createLinearGradient(0, 0, 256, 256);
      bg.addColorStop(0, "#2a7448");
      bg.addColorStop(0.5, "#1f6540");
      bg.addColorStop(1, "#245f3d");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, 256, 256);
      for (let i = 0; i < 260; i += 1) {
        const x = rand() * 256;
        const y = rand() * 256;
        const r = 6 + rand() * 22;
        const dark = rand() > 0.5;
        const g = ctx.createRadialGradient(x, y, 0, x, y, r);
        g.addColorStop(0, dark ? "rgba(11, 52, 33, 0.3)" : "rgba(78, 160, 96, 0.26)");
        g.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
      // 풀잎 결
      for (let i = 0; i < 900; i += 1) {
        const x = rand() * 256;
        const y = rand() * 256;
        const len = 2 + rand() * 5;
        const lean = (rand() - 0.5) * 2;
        ctx.strokeStyle = rand() > 0.55
          ? `rgba(126, 196, 118, ${0.1 + rand() * 0.24})`
          : `rgba(12, 48, 30, ${0.1 + rand() * 0.24})`;
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(x + lean, y - len);
        ctx.stroke();
      }
    },
    [29, 95, 70, 255],
    { repeat: [10, 10] }
  );
  track(grassTex.texture);

  // 10-b. 젖은 모래 해변 텍스처 (조개 부스러기 + 물결 자국)
  const sandTex = canvasTexture(
    256,
    256,
    (ctx) => {
      const rand = seededRandom(7717);
      const bg = ctx.createLinearGradient(0, 0, 256, 256);
      bg.addColorStop(0, "#e8d3a6");
      bg.addColorStop(0.55, "#dcc79a");
      bg.addColorStop(1, "#cbb487");
      ctx.fillStyle = bg;
      ctx.fillRect(0, 0, 256, 256);
      // 물이 지나간 잔물결 자국
      for (let band = 0; band < 14; band += 1) {
        ctx.strokeStyle = `rgba(168, 148, 112, ${0.1 + rand() * 0.14})`;
        ctx.lineWidth = 1.4 + rand() * 2.2;
        ctx.beginPath();
        const baseY = (band / 14) * 256 + rand() * 6;
        ctx.moveTo(0, baseY);
        for (let x = 0; x <= 256; x += 16) {
          ctx.lineTo(x, baseY + Math.sin(x * 0.045 + band * 1.3) * 4 + (rand() - 0.5) * 2);
        }
        ctx.stroke();
      }
      // 모래알
      for (let i = 0; i < 2600; i += 1) {
        const x = rand() * 256;
        const y = rand() * 256;
        const light = rand() > 0.5;
        ctx.fillStyle = light
          ? `rgba(255, 245, 220, ${0.14 + rand() * 0.3})`
          : `rgba(150, 128, 96, ${0.1 + rand() * 0.24})`;
        ctx.fillRect(x, y, 1 + rand() * 1.6, 1 + rand() * 1.6);
      }
      // 조개 부스러기
      for (let i = 0; i < 90; i += 1) {
        const x = rand() * 256;
        const y = rand() * 256;
        ctx.fillStyle = `rgba(255, 252, 246, ${0.25 + rand() * 0.4})`;
        ctx.beginPath();
        ctx.ellipse(x, y, 1 + rand() * 2.2, 0.8 + rand() * 1.4, rand() * 3, 0, Math.PI * 2);
        ctx.fill();
      }
    },
    [222, 200, 158, 255],
    { repeat: [9, 9] }
  );
  track(sandTex.texture);

  // 11. 암벽 텍스처 (거친 화강암 + 층리)
  const rockTex = canvasTexture(
    256,
    256,
    (ctx) => {
      const rand = seededRandom(31415);
      ctx.fillStyle = "#42506a";
      ctx.fillRect(0, 0, 256, 256);
      for (let i = 0; i < 460; i += 1) {
        const x = rand() * 256;
        const y = rand() * 256;
        const r = 3 + rand() * 18;
        const light = rand() > 0.48;
        const g = ctx.createRadialGradient(x, y, 0, x, y, r);
        g.addColorStop(0, light ? "rgba(150, 168, 196, 0.24)" : "rgba(24, 32, 48, 0.28)");
        g.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
      for (let layer = 0; layer < 9; layer += 1) {
        ctx.strokeStyle = `rgba(16, 22, 34, ${0.12 + rand() * 0.16})`;
        ctx.lineWidth = 1 + rand() * 2.4;
        ctx.beginPath();
        const baseY = (layer / 9) * 256 + rand() * 8;
        ctx.moveTo(0, baseY);
        for (let x = 0; x <= 256; x += 24) {
          ctx.lineTo(x, baseY + Math.sin(x * 0.05 + layer) * 3.4 + (rand() - 0.5) * 3);
        }
        ctx.stroke();
      }
    },
    [66, 80, 106, 255],
    { repeat: [4, 3] }
  );
  track(rockTex.texture);

  // 12. 기와 지붕 텍스처 (겹친 기와 줄)
  const roofTex = canvasTexture(
    256,
    256,
    (ctx) => {
      const rand = seededRandom(5150);
      ctx.fillStyle = "#f2f4f8";
      ctx.fillRect(0, 0, 256, 256);
      const rows = 10;
      const rh = 256 / rows;
      for (let r = 0; r < rows; r += 1) {
        for (let c = 0; c < 10; c += 1) {
          const cw = 256 / 10;
          const x = c * cw + (r % 2) * (cw * 0.5);
          const shade = 208 + Math.floor(rand() * 40);
          const g = ctx.createLinearGradient(0, r * rh, 0, r * rh + rh);
          g.addColorStop(0, `rgba(${shade}, ${shade}, ${shade + 6}, 1)`);
          g.addColorStop(0.7, `rgba(${shade - 44}, ${shade - 44}, ${shade - 38}, 1)`);
          g.addColorStop(1, `rgba(${shade - 84}, ${shade - 84}, ${shade - 76}, 1)`);
          ctx.fillStyle = g;
          ctx.beginPath();
          ctx.roundRect
            ? ctx.roundRect(x + 1, r * rh + 1, cw - 2, rh - 2, 3)
            : ctx.rect(x + 1, r * rh + 1, cw - 2, rh - 2);
          ctx.fill();
        }
      }
    },
    [240, 240, 244, 255],
    { repeat: [3, 2] }
  );
  track(roofTex.texture);

  // 13. 조약돌 길 텍스처
  const cobbleTex = canvasTexture(
    256,
    256,
    (ctx) => {
      const rand = seededRandom(8080);
      ctx.fillStyle = "#3a4254";
      ctx.fillRect(0, 0, 256, 256);
      for (let r = 0; r < 9; r += 1) {
        for (let c = 0; c < 9; c += 1) {
          const x = c * 30 + (r % 2) * 14 + 6 + rand() * 3;
          const y = r * 30 + 6 + rand() * 3;
          const rx = 10 + rand() * 3;
          const shade = 112 + Math.floor(rand() * 46);
          const g = ctx.createRadialGradient(x - rx * 0.3, y - rx * 0.35, 1, x, y, rx);
          g.addColorStop(0, `rgb(${shade + 32}, ${shade + 36}, ${shade + 46})`);
          g.addColorStop(0.75, `rgb(${shade}, ${shade + 4}, ${shade + 12})`);
          g.addColorStop(1, `rgb(${shade - 34}, ${shade - 32}, ${shade - 24})`);
          ctx.fillStyle = g;
          ctx.beginPath();
          ctx.ellipse(x, y, rx, rx * 0.86, rand() * 0.6, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    },
    [92, 102, 122, 255],
    { repeat: [4, 4] }
  );
  track(cobbleTex.texture);

  // 14. 바다 표면 노멀맵 (원활한 파동 법선, 타일링)
  let waterNormal;
  const waterSurface = makeCanvas(128, 128);
  if (waterSurface) {
    const { el, ctx } = waterSurface;
    try {
      const img = ctx.createImageData(128, 128);
      const heightAt = (x, y) => {
        const u = (x / 128) * Math.PI * 2;
        const v = (y / 128) * Math.PI * 2;
        return (
          Math.sin(u * 3 + v * 2) * 0.5 +
          Math.sin(u * 5 - v * 4 + 1.3) * 0.3 +
          Math.cos(u * 8 + v * 7 + 2.1) * 0.16 +
          Math.sin(u * 13 - v * 9) * 0.08
        );
      };
      for (let y = 0; y < 128; y += 1) {
        for (let x = 0; x < 128; x += 1) {
          const dx = heightAt((x + 1) % 128, y) - heightAt((x + 127) % 128, y);
          const dy = heightAt(x, (y + 1) % 128) - heightAt(x, (y + 127) % 128);
          const strength = 1.65;
          let nx = -dx * strength;
          let ny = -dy * strength;
          const nz = 1;
          const len = Math.hypot(nx, ny, nz);
          nx /= len;
          ny /= len;
          const i = (y * 128 + x) * 4;
          img.data[i] = Math.round((nx * 0.5 + 0.5) * 255);
          img.data[i + 1] = Math.round((ny * 0.5 + 0.5) * 255);
          img.data[i + 2] = Math.round((nz / len * 0.5 + 0.5) * 255);
          img.data[i + 3] = 255;
        }
      }
      ctx.putImageData(img, 0, 0);
      waterNormal = new THREE.CanvasTexture(el);
      waterNormal.wrapS = THREE.RepeatWrapping;
      waterNormal.wrapT = THREE.RepeatWrapping;
      waterNormal.repeat.set(26, 26);
    } catch {
      waterNormal = solidDataTexture(128, 128, 255);
    }
  } else {
    waterNormal = solidDataTexture(128, 128, 255);
  }
  track(waterNormal);

  // 15. 달 표면 (크레이터가 있는 옅은 마리아)
  const moonTex = canvasTexture(
    256,
    128,
    (ctx) => {
      const rand = seededRandom(6060);
      const base = ctx.createLinearGradient(0, 0, 256, 128);
      base.addColorStop(0, "#f6f8ff");
      base.addColorStop(0.55, "#e8eeff");
      base.addColorStop(1, "#cfdcf7");
      ctx.fillStyle = base;
      ctx.fillRect(0, 0, 256, 128);
      for (let i = 0; i < 44; i += 1) {
        const x = rand() * 256;
        const y = 10 + rand() * 108;
        const r = 2 + rand() * 12;
        const g = ctx.createRadialGradient(x - r * 0.2, y - r * 0.24, r * 0.15, x, y, r);
        g.addColorStop(0, "rgba(150, 166, 200, 0.55)");
        g.addColorStop(0.72, "rgba(176, 190, 218, 0.26)");
        g.addColorStop(1, "rgba(176, 190, 218, 0)");
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }
    },
    [238, 244, 255, 255]
  );
  track(moonTex.texture);

  // 16. 해안 거품 링 (방사형 그라디언트 밴드)
  const foamTex = canvasTexture(
    256,
    256,
    (ctx) => {
      const rand = seededRandom(1122);
      const grad = ctx.createRadialGradient(128, 128, 0, 128, 128, 128);
      grad.addColorStop(0, "rgba(255, 255, 255, 0)");
      grad.addColorStop(0.6, "rgba(255, 255, 255, 0)");
      grad.addColorStop(0.72, "rgba(214, 240, 255, 0.16)");
      grad.addColorStop(0.8, "rgba(255, 255, 255, 0.5)");
      grad.addColorStop(0.87, "rgba(236, 250, 255, 0.28)");
      grad.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, 256, 256);
      // 부서지는 거품 얼룩
      for (let i = 0; i < 180; i += 1) {
        const a = rand() * Math.PI * 2;
        const r = 95 + rand() * 32;
        const x = 128 + Math.cos(a) * r;
        const y = 128 + Math.sin(a) * r;
        const size = 1 + rand() * 6;
        ctx.fillStyle = `rgba(255, 255, 255, ${0.06 + rand() * 0.32})`;
        ctx.beginPath();
        ctx.arc(x, y, size, 0, Math.PI * 2);
        ctx.fill();
      }
    },
    [255, 255, 255, 255]
  );
  track(foamTex.texture);

  // 17. 알베도에서 뽑아낸 노멀맵 — 조명을 받을 때 표면에 실제 요철이 생긴다
  const grassNormal = normalFromCanvas(grassTex.canvas, 1.5, [10, 10]);
  const sandNormal = normalFromCanvas(sandTex.canvas, 1.9, [9, 9]);
  const rockNormal = normalFromCanvas(rockTex.canvas, 2.6, [4, 3]);
  const roofNormal = normalFromCanvas(roofTex.canvas, 1.7, [3, 2]);
  const woodNormal = normalFromCanvas(woodTex.canvas, 1.8, [2, 2]);
  const cobbleNormal = normalFromCanvas(cobbleTex.canvas, 2.4, [4, 4]);
  const stoneNormal = normalFromCanvas(stoneTex.canvas, 2.0, [2, 2]);
  [grassNormal, sandNormal, rockNormal, roofNormal, woodNormal, cobbleNormal, stoneNormal].forEach(
    track
  );

  return {
    glow,
    star: starTex.texture,
    cloud: cloudTex.texture,
    smoke: smokeTex.texture,
    sunRays: sunRaysTex.texture,
    solar: solarTex.texture,
    wood: woodTex.texture,
    windowPane: windowTex.texture,
    stone: stoneTex.texture,
    grass: grassTex.texture,
    rock: rockTex.texture,
    roof: roofTex.texture,
    cobble: cobbleTex.texture,
    sand: sandTex.texture,
    waterNormal,
    moon: moonTex.texture,
    foam: foamTex.texture,
    grassNormal,
    sandNormal,
    rockNormal,
    roofNormal,
    woodNormal,
    cobbleNormal,
    stoneNormal,
    dispose() {
      created.forEach((tex) => tex.dispose());
    },
  };
}
