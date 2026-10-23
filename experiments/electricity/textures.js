import * as THREE from "three";

const TAU = Math.PI * 2;
const IS_HEADLESS = typeof document === "undefined";

function makeRng(seed) {
  let s = seed >>> 0;
  return function next() {
    s += 0x6d2b79f5;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const SURF_SIZE = 128;
const SURF_MASK = SURF_SIZE - 1;

/**
 * 옥타브 피라미드를 미리 생성한 뒤 정수 비트 시프트 쌍선형 보간만으로
 * SURF_SIZE x SURF_SIZE 완전 타일링 fBm 필드를 합성한다.
 */
function buildSeamlessFbm(seed, baseFreq = 4, octaves = 5) {
  const size = SURF_SIZE;
  const total = size * size;
  const accum = new Float32Array(total);
  const rand = makeRng(seed);
  let amp = 0.5;
  let norm = 0;

  for (let o = 0; o < octaves; o += 1) {
    const g = baseFreq << o;
    if (g > 64) break;
    const gMask = g - 1;
    const lattice = new Float32Array(g * g);
    for (let i = 0; i < g * g; i += 1) lattice[i] = rand();

    const step = g / size;
    for (let y = 0; y < size; y += 1) {
      const fy = y * step;
      const iy0 = fy | 0;
      const ty = fy - iy0;
      const sy = ty * ty * (3 - 2 * ty);
      const r0 = (iy0 & gMask) * g;
      const r1 = ((iy0 + 1) & gMask) * g;
      const rowOff = y * size;

      for (let x = 0; x < size; x += 1) {
        const fx = x * step;
        const ix0 = fx | 0;
        const tx = fx - ix0;
        const sx = tx * tx * (3 - 2 * tx);
        const c0 = ix0 & gMask;
        const c1 = (ix0 + 1) & gMask;
        const a = lattice[r0 + c0];
        const b = lattice[r0 + c1];
        const c = lattice[r1 + c0];
        const d = lattice[r1 + c1];
        accum[rowOff + x] += amp * (a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy);
      }
    }
    norm += amp;
    amp *= 0.5;
  }

  const invNorm = 1 / (norm || 1);
  for (let i = 0; i < total; i += 1) accum[i] *= invNorm;
  return accum;
}

function finishDataTexture(
  data,
  size,
  { repeatX = 1, repeatY = 1, srgb = false, generateMipmaps = true } = {}
) {
  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(repeatX, repeatY);
  tex.generateMipmaps = generateMipmaps;
  tex.minFilter = generateMipmaps ? THREE.LinearMipmapLinearFilter : THREE.LinearFilter;
  tex.magFilter = THREE.LinearFilter;
  if (srgb) {
    tex.colorSpace = THREE.SRGBColorSpace;
  }
  tex.needsUpdate = true;
  return tex;
}

/**
 * getImageData GPU 역읽기를 완전히 제거하고, 순수 메모리 버퍼(albedo RGBA + height Float32)에서
 * 알베도·노멀·거칠기 3종 이음매 없는(Seamless) PBR DataTexture 세트를 한 번에 생성한다.
 */
function finalizeSurfacePbr(
  albedoData,
  heightField,
  size,
  { strength = 2.0, lo = 0.65, hi = 0.98, repeatX = 1, repeatY = 1 } = {}
) {
  if (IS_HEADLESS) {
    const mk = () => {
      const t = new THREE.DataTexture(new Uint8Array([200, 200, 200, 255]), 1, 1);
      t.needsUpdate = true;
      return t;
    };
    return { albedo: mk(), normal: mk(), rough: mk() };
  }
  const mask = size - 1;
  const count = size * size;
  const normalData = new Uint8Array(count * 4);
  const roughData = new Uint8Array(count * 4);
  const span = hi - lo;

  for (let y = 0; y < size; y += 1) {
    const ym = ((y - 1) & mask) * size;
    const y0 = y * size;
    const yp = ((y + 1) & mask) * size;
    for (let x = 0; x < size; x += 1) {
      const xm = (x - 1) & mask;
      const xp = (x + 1) & mask;
      const idx = y0 + x;
      const p4 = idx * 4;

      const hVal = heightField[idx];
      const rv = Math.min(255, Math.max(0, ((hi - hVal * span) * 255) | 0));
      roughData[p4] = rv;
      roughData[p4 + 1] = rv;
      roughData[p4 + 2] = rv;
      roughData[p4 + 3] = 255;

      const tl = heightField[ym + xm];
      const t = heightField[ym + x];
      const tr = heightField[ym + xp];
      const l = heightField[y0 + xm];
      const r = heightField[y0 + xp];
      const bl = heightField[yp + xm];
      const b = heightField[yp + x];
      const br = heightField[yp + xp];
      const dx = (tr + 2 * r + br - (tl + 2 * l + bl)) * strength;
      const dy = (bl + 2 * b + br - (tl + 2 * t + tr)) * strength;
      const invLen = 127.5 / Math.sqrt(dx * dx + dy * dy + 1);
      normalData[p4] = (-dx * invLen + 127.5) | 0;
      normalData[p4 + 1] = (-dy * invLen + 127.5) | 0;
      normalData[p4 + 2] = (invLen + 127.5) | 0;
      normalData[p4 + 3] = 255;
    }
  }

  return {
    albedo: finishDataTexture(albedoData, size, { repeatX, repeatY, srgb: true }),
    normal: finishDataTexture(normalData, size, { repeatX, repeatY }),
    rough: finishDataTexture(roughData, size, { repeatX, repeatY }),
  };
}

function buildGlowTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([255, 255, 255, 255]), 1, { srgb: true });
  const size = 64;
  const half = (size - 1) * 0.5;
  const invR = 1 / half;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const dy = (y - half) * invR;
    for (let x = 0; x < size; x += 1) {
      const dx = (x - half) * invR;
      const d = Math.sqrt(dx * dx + dy * dy);
      const t = d >= 1 ? 0 : 1 - d;
      const a = t * t * (0.35 + 0.65 * t);
      const i = (y * size + x) * 4;
      data[i] = 255;
      data[i + 1] = 255;
      data[i + 2] = 255;
      data[i + 3] = (a * 255) | 0;
    }
  }
  const tex = finishDataTexture(data, size, { srgb: true });
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  return tex;
}

function buildStarTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([255, 255, 255, 255]), 1, { srgb: true });
  const size = 64;
  const half = (size - 1) * 0.5;
  const invR = 1 / 30;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const ady = Math.abs(y - half);
    for (let x = 0; x < size; x += 1) {
      const adx = Math.abs(x - half);
      const d = Math.sqrt(adx * adx + ady * ady) * invR;
      const core = d >= 1 ? 0 : (1 - d) * (1 - d);
      const crossX = ady < 1.35 && adx < 26 ? (1 - adx / 26) * 0.85 : 0;
      const crossY = adx < 1.35 && ady < 26 ? (1 - ady / 26) * 0.85 : 0;
      const a = Math.min(1, core + Math.max(crossX, crossY));
      const i = (y * size + x) * 4;
      data[i] = 242;
      data[i + 1] = 248;
      data[i + 2] = 255;
      data[i + 3] = (a * 255) | 0;
    }
  }
  const tex = finishDataTexture(data, size, { srgb: true });
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  return tex;
}

function buildCloudTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([255, 255, 255, 160]), 1, { srgb: true });
  const { fbm4 } = getSharedFields();
  const size = 64;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const dy = (y / size - 0.5) * 2.3;
    const row = (y * 2) * SURF_SIZE;
    for (let x = 0; x < size; x += 1) {
      const dx = (x / size - 0.5) * 1.9;
      const r = Math.sqrt(dx * dx + dy * dy);
      const n = fbm4[row + x * 2];
      const a = Math.max(0, Math.min(0.45, (1 - r + (n - 0.5) * 0.5) * 0.55));
      const i = (y * size + x) * 4;
      data[i] = 245;
      data[i + 1] = 250;
      data[i + 2] = 255;
      data[i + 3] = (a * 255) | 0;
    }
  }
  const tex = finishDataTexture(data, size, { srgb: true });
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  return tex;
}

function buildSmokeTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([240, 246, 255, 160]), 1, { srgb: true });
  const { fbm8 } = getSharedFields();
  const size = 64;
  const half = (size - 1) * 0.5;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const dy = (y - half) / 30;
    const row = (y * 2) * SURF_SIZE;
    for (let x = 0; x < size; x += 1) {
      const dx = (x - half) / 30;
      const r = Math.sqrt(dx * dx + dy * dy);
      const n = fbm8[row + x * 2];
      const t = r >= 1 ? 0 : 1 - r;
      const a = t * t * (0.46 + n * 0.28);
      const i = (y * size + x) * 4;
      data[i] = 236;
      data[i + 1] = 243;
      data[i + 2] = 255;
      data[i + 3] = Math.min(255, (a * 255) | 0);
    }
  }
  const tex = finishDataTexture(data, size, { srgb: true });
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  return tex;
}

function buildSunRaysTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([255, 240, 190, 255]), 1, { srgb: true });
  const size = 128;
  const half = (size - 1) * 0.5;
  const invR = 1 / 63;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const dy = (y - half) * invR;
    for (let x = 0; x < size; x += 1) {
      const dx = (x - half) * invR;
      const d = Math.sqrt(dx * dx + dy * dy);
      const i = (y * size + x) * 4;
      if (d >= 1) {
        data[i + 3] = 0;
        continue;
      }
      const core = (1 - d) * (1 - d);
      const rayWave = Math.cos(Math.atan2(dy, dx) * 16);
      const ray = d > 0.18 && rayWave > 0.72 ? (rayWave - 0.72) * 3.5 * (1 - d) * 0.34 : 0;
      const a = Math.min(1, core * 1.05 + ray);
      data[i] = 255;
      data[i + 1] = (212 + core * 40) | 0;
      data[i + 2] = (110 + core * 122) | 0;
      data[i + 3] = (a * 255) | 0;
    }
  }
  const tex = finishDataTexture(data, size, { srgb: true });
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  return tex;
}

function buildSolarTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([24, 58, 130, 255]), 1, { srgb: true });
  const size = 128;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const cy = y % 16;
    const isRowGap = cy < 2;
    const isFinger = cy === 5 || cy === 9 || cy === 13;
    for (let x = 0; x < size; x += 1) {
      const cx = x % 32;
      const isColGap = cx < 2;
      const isBusbar = cx === 11 || cx === 21;
      const i = (y * size + x) * 4;
      if (isRowGap || isColGap) {
        data[i] = 16;
        data[i + 1] = 37;
        data[i + 2] = 68;
      } else if (isBusbar) {
        data[i] = 191;
        data[i + 1] = 219;
        data[i + 2] = 254;
      } else if (isFinger) {
        data[i] = 58;
        data[i + 1] = 104;
        data[i + 2] = 178;
      } else {
        const sheen = 1 - (cx / 32 + cy / 16) * 0.42;
        data[i] = (15 + sheen * 16) | 0;
        data[i + 1] = (41 + sheen * 38) | 0;
        data[i + 2] = (92 + sheen * 124) | 0;
      }
      data[i + 3] = 255;
    }
  }
  return finishDataTexture(data, size, { srgb: true });
}

function buildWindowPaneTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([255, 220, 120, 255]), 1, { srgb: true });
  const size = 64;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const mullionY = y < 3 || y > 60 || (y >= 29 && y <= 34);
    const dy = (y - 34) / 40;
    for (let x = 0; x < size; x += 1) {
      const mullionX = x < 3 || x > 60 || (x >= 29 && x <= 34);
      const i = (y * size + x) * 4;
      if (mullionX || mullionY) {
        data[i] = 54;
        data[i + 1] = 41;
        data[i + 2] = 32;
      } else {
        const dx = (x - 32) / 40;
        const d = Math.min(1, Math.sqrt(dx * dx + dy * dy));
        data[i] = (255 - d * 38) | 0;
        data[i + 1] = (246 - d * 118) | 0;
        data[i + 2] = (214 - d * 172) | 0;
      }
      data[i + 3] = 255;
    }
  }
  return finishDataTexture(data, size, { srgb: true });
}

function buildMoonTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([232, 238, 248, 255]), 1, { srgb: true });
  const { fbm4, fbm16 } = getSharedFields();
  const size = 128;
  const data = new Uint8Array(size * size * 4);
  for (let i = 0; i < size * size; i += 1) {
    const maria = fbm4[i];
    const crater = fbm16[i];
    const shade = 236 - Math.max(0, maria - 0.45) * 145 - (crater > 0.72 ? (crater - 0.72) * 120 : 0);
    const p4 = i * 4;
    data[p4] = Math.max(120, shade | 0);
    data[p4 + 1] = Math.max(130, (shade + 6) | 0);
    data[p4 + 2] = Math.min(255, Math.max(148, (shade + 16) | 0));
    data[p4 + 3] = 255;
  }
  return finishDataTexture(data, size, { srgb: true });
}

function buildFoamTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([236, 250, 255, 180]), 1, { srgb: true });
  const { fbm8, fbm16 } = getSharedFields();
  const size = 128;
  const half = (size - 1) * 0.5;
  const invR = 1 / half;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const dy = (y - half) * invR;
    for (let x = 0; x < size; x += 1) {
      const idx = y * size + x;
      const dx = (x - half) * invR;
      const r = Math.sqrt(dx * dx + dy * dy);
      const b1 = Math.max(0, 1 - Math.abs(r - 0.84) / 0.14) * 0.62;
      const b2 = Math.max(0, 1 - Math.abs(r - 0.7) / 0.1) * 0.28;
      const bubbles = fbm16[idx] * 0.5 + fbm8[idx] * 0.5;
      const a = Math.min(1, (b1 + b2) * (0.55 + bubbles * 0.9));
      const p4 = idx * 4;
      data[p4] = 228;
      data[p4 + 1] = 248;
      data[p4 + 2] = 255;
      data[p4 + 3] = (a * 255) | 0;
    }
  }
  const tex = finishDataTexture(data, size, { srgb: true });
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  return tex;
}

function buildGrassBladeTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([92, 188, 112, 255]), 1, { srgb: true });
  const rand = makeRng(20262020);
  const size = 64;
  const data = new Uint8Array(size * size * 4);
  const blades = Array.from({ length: 9 }, (_, i) => ({
    bx: size * (0.1 + (i / 8) * 0.8) + (rand() - 0.5) * 4.5,
    h: size * (0.52 + rand() * 0.44),
    w: 2.4 + rand() * 2.4,
    bend: (rand() - 0.5) * 13,
    tint: rand(),
  }));

  for (let b = 0; b < blades.length; b += 1) {
    const bl = blades[b];
    const yStart = Math.max(0, Math.ceil(size - bl.h));
    for (let y = yStart; y < size; y += 1) {
      const t = (size - 1 - y) / bl.h;
      const cx = bl.bx + bl.bend * t * t;
      const hw = bl.w * 0.5 * (1 - t * 0.85);
      const x0 = Math.max(0, Math.floor(cx - hw));
      const x1 = Math.min(size - 1, Math.ceil(cx + hw));
      const r = (26 + t * (108 + bl.tint * 42)) | 0;
      const g = (78 + t * (134 + bl.tint * 28)) | 0;
      const blCol = (52 + t * (80 + bl.tint * 26)) | 0;
      for (let x = x0; x <= x1; x += 1) {
        const p4 = (y * size + x) * 4;
        data[p4] = r;
        data[p4 + 1] = g;
        data[p4 + 2] = blCol;
        data[p4 + 3] = 255;
      }
    }
  }
  const tex = finishDataTexture(data, size, { srgb: true });
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  return tex;
}

function buildShadowBlobTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([0, 0, 0, 160]), 1);
  const size = 64;
  const half = (size - 1) * 0.5;
  const invR = 1 / half;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const dy = (y - half) * invR;
    for (let x = 0; x < size; x += 1) {
      const dx = (x - half) * invR;
      const d = Math.sqrt(dx * dx + dy * dy);
      const t = d >= 1 ? 0 : 1 - d;
      const a = t * t * 0.62;
      data[(y * size + x) * 4 + 3] = (a * 255) | 0;
    }
  }
  const tex = finishDataTexture(data, size);
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  return tex;
}

/* ── 이음매 없는(Seamless) 고속 DataTexture PBR 표면 생성기 7종 ── */

const SHARED_FIELDS = { fbm4: null, fbm8: null, fbm16: null, fine: null };

function getSharedFields() {
  if (!SHARED_FIELDS.fbm4 || !SHARED_FIELDS.fbm8 || !SHARED_FIELDS.fbm16 || !SHARED_FIELDS.fine) {
    throw new Error("Island surface fields must be prepared before creating surface textures.");
  }
  return SHARED_FIELDS;
}

function createFineNoiseField() {
  const fine = new Float32Array(SURF_SIZE * SURF_SIZE);
  const rand = makeRng(20260807);
  for (let i = 0; i < fine.length; i += 1) fine[i] = rand();
  return fine;
}

function buildWoodBundle() {
  if (IS_HEADLESS) return finalizeSurfacePbr(null, null, 1);
  const { fbm8 } = getSharedFields();
  const size = SURF_SIZE;
  const albedo = new Uint8Array(size * size * 4);
  const height = new Float32Array(size * size);
  const rand = makeRng(20260901);
  const plankShades = Float32Array.from({ length: 6 }, () => (rand() - 0.5) * 26);

  for (let y = 0; y < size; y += 1) {
    const buttSeam = y === 63;
    const gRow = ((y >> 1) & SURF_MASK) * size;
    for (let x = 0; x < size; x += 1) {
      const idx = y * size + x;
      const p4 = idx * 4;
      const pFloat = (x / size) * 6;
      const pIdx = pFloat < 5 ? pFloat | 0 : 5;
      const pLocal = pFloat - pIdx;
      const groove = pLocal < 0.045 || pLocal > 0.965;
      const grain = fbm8[gRow + ((x * 4) & SURF_MASK)];
      const ring = Math.sin(pLocal * 22 + grain * 7.5) * 0.5 + 0.5;
      const shade = plankShades[pIdx] + (grain - 0.5) * 30 + (ring - 0.5) * 16;

      let r = 138 + shade;
      let g = 92 + shade * 0.7;
      let b = 54 + shade * 0.5;
      let h = 0.72 + (grain - 0.5) * 0.24 + (ring - 0.5) * 0.14;

      if (groove || buttSeam) {
        r *= 0.42;
        g *= 0.4;
        b *= 0.38;
        h = 0.12;
      } else if (pLocal < 0.09) {
        r += 18;
        g += 14;
        b += 10;
        h += 0.08;
      }

      albedo[p4] = r < 0 ? 0 : r > 255 ? 255 : r | 0;
      albedo[p4 + 1] = g < 0 ? 0 : g > 255 ? 255 : g | 0;
      albedo[p4 + 2] = b < 0 ? 0 : b > 255 ? 255 : b | 0;
      albedo[p4 + 3] = 255;
      height[idx] = h < 0 ? 0 : h > 1 ? 1 : h;
    }
  }
  return finalizeSurfacePbr(albedo, height, size, { strength: 1.5, lo: 0.66, hi: 0.96, repeatX: 2, repeatY: 2 });
}

function buildStoneBundle() {
  if (IS_HEADLESS) return finalizeSurfacePbr(null, null, 1);
  const { fbm16, fine } = getSharedFields();
  const size = SURF_SIZE;
  const albedo = new Uint8Array(size * size * 4);
  const height = new Float32Array(size * size);
  const rand = makeRng(20261010);
  const blockTone = Float32Array.from({ length: 64 }, () => 92 + rand() * 36);

  for (let y = 0; y < size; y += 1) {
    const rowF = (y / size) * 8;
    const row = rowF | 0;
    const ry = rowF - row;
    const rowShift = (row & 1) * 0.5;
    for (let x = 0; x < size; x += 1) {
      const idx = y * size + x;
      const p4 = idx * 4;
      const colF = (x / size + rowShift) * 4;
      const colInt = colF | 0;
      const cx = colF - colInt;

      const mortar = ry < 0.07 || ry > 0.94 || cx < 0.035 || cx > 0.965;
      const grain = fbm16[idx];
      const speck = fine[idx];
      const base = blockTone[(row & 7) * 4 + (colInt & 3)] + (grain - 0.5) * 28 + (speck - 0.5) * 18;

      let r = base;
      let g = base + 8;
      let b = base + 20;
      let h = 0.74 + (grain - 0.5) * 0.3;

      if (mortar) {
        r = 68 + grain * 18;
        g = 75 + grain * 18;
        b = 88 + grain * 18;
        h = 0.14;
      } else if (ry < 0.14) {
        r += 22;
        g += 22;
        b += 24;
        h += 0.1;
      }

      albedo[p4] = r < 0 ? 0 : r > 255 ? 255 : r | 0;
      albedo[p4 + 1] = g < 0 ? 0 : g > 255 ? 255 : g | 0;
      albedo[p4 + 2] = b < 0 ? 0 : b > 255 ? 255 : b | 0;
      albedo[p4 + 3] = 255;
      height[idx] = h < 0 ? 0 : h > 1 ? 1 : h;
    }
  }
  return finalizeSurfacePbr(albedo, height, size, { strength: 2.0, lo: 0.72, hi: 0.99, repeatX: 3, repeatY: 3 });
}

function buildGrassBundle() {
  if (IS_HEADLESS) return finalizeSurfacePbr(null, null, 1);
  const { fbm4, fbm16, fine } = getSharedFields();
  const size = SURF_SIZE;
  const albedo = new Uint8Array(size * size * 4);
  const height = new Float32Array(size * size);

  for (let y = 0; y < size; y += 1) {
    const bladeRow = ((y * 2) & SURF_MASK) * size;
    for (let x = 0; x < size; x += 1) {
      const idx = y * size + x;
      const p4 = idx * 4;
      const patch = fbm4[idx];
      const blades = fbm16[bladeRow + ((x * 6 + ((patch * 16) | 0)) & SURF_MASK)];
      const grain = fine[idx];
      const lush = blades * 0.65 + grain * 0.35;
      const soil = patch < 0.36 ? (0.36 - patch) * 2.1 : 0;

      let r = 34 + patch * 52 + lush * 48 + soil * 62;
      let g = 96 + patch * 72 + lush * 68 - soil * 14;
      let b = 64 + patch * 36 + lush * 42 - soil * 8;
      let h = 0.35 + lush * 0.55 + patch * 0.14;

      if (grain > 0.994) {
        r = 252;
        g = grain > 0.997 ? 232 : 186;
        b = grain > 0.997 ? 148 : 212;
        h = 0.95;
      }

      albedo[p4] = r < 0 ? 0 : r > 255 ? 255 : r | 0;
      albedo[p4 + 1] = g < 0 ? 0 : g > 255 ? 255 : g | 0;
      albedo[p4 + 2] = b < 0 ? 0 : b > 255 ? 255 : b | 0;
      albedo[p4 + 3] = 255;
      height[idx] = h < 0 ? 0 : h > 1 ? 1 : h;
    }
  }
  return finalizeSurfacePbr(albedo, height, size, { strength: 1.7, lo: 0.72, hi: 0.99, repeatX: 9, repeatY: 9 });
}

function buildSandBundle() {
  if (IS_HEADLESS) return finalizeSurfacePbr(null, null, 1);
  const { fbm4, fine } = getSharedFields();
  const size = SURF_SIZE;
  const albedo = new Uint8Array(size * size * 4);
  const height = new Float32Array(size * size);
  const uWave = new Float32Array(size);
  for (let x = 0; x < size; x += 1) uWave[x] = Math.sin((x / size) * TAU * 2) * 0.28;

  for (let y = 0; y < size; y += 1) {
    const vBase = (y / size) * 18;
    for (let x = 0; x < size; x += 1) {
      const idx = y * size + x;
      const p4 = idx * 4;
      const warp = fbm4[((y + 32) & SURF_MASK) * size + ((x + 48) & SURF_MASK)];
      const ripple = Math.sin((vBase + uWave[x] + warp * 1.4) * TAU) * 0.5 + 0.5;
      const grain = fine[idx];
      const shade = (ripple - 0.5) * 28 + (warp - 0.5) * 24 + (grain - 0.5) * 26;

      const r = 202 + shade;
      const g = 178 + shade * 0.92;
      const b = 134 + shade * 0.82;
      const h = 0.45 + ripple * 0.35 + grain * 0.2;

      albedo[p4] = r < 0 ? 0 : r > 255 ? 255 : r | 0;
      albedo[p4 + 1] = g < 0 ? 0 : g > 255 ? 255 : g | 0;
      albedo[p4 + 2] = b < 0 ? 0 : b > 255 ? 255 : b | 0;
      albedo[p4 + 3] = 255;
      height[idx] = h < 0 ? 0 : h > 1 ? 1 : h;
    }
  }
  return finalizeSurfacePbr(albedo, height, size, { strength: 1.4, lo: 0.74, hi: 0.99, repeatX: 7, repeatY: 7 });
}

function buildRockBundle() {
  if (IS_HEADLESS) return finalizeSurfacePbr(null, null, 1);
  const { fbm8, fbm16 } = getSharedFields();
  const size = SURF_SIZE;
  const albedo = new Uint8Array(size * size * 4);
  const height = new Float32Array(size * size);

  for (let y = 0; y < size; y += 1) {
    const sRow = ((y * 2) & SURF_MASK) * size;
    for (let x = 0; x < size; x += 1) {
      const idx = y * size + x;
      const p4 = idx * 4;
      const strata = fbm8[sRow + (x >> 1)];
      const detail = fbm16[((y + 57) & SURF_MASK) * size + ((x + 29) & SURF_MASK)];
      const crackField = Math.abs(fbm8[((y + ((strata * 24) | 0)) & SURF_MASK) * size + x] - 0.5);
      const crack = crackField < 0.04 ? 1 - crackField / 0.04 : 0;

      const base = 76 + strata * 56 + (detail - 0.5) * 34 - crack * 52;
      const h = 0.42 + strata * 0.38 + detail * 0.24 - crack * 0.42;

      albedo[p4] = base < 0 ? 0 : base > 255 ? 255 : base | 0;
      albedo[p4 + 1] = base + 8 < 0 ? 0 : base + 8 > 255 ? 255 : (base + 8) | 0;
      albedo[p4 + 2] = base + 20 < 0 ? 0 : base + 20 > 255 ? 255 : (base + 20) | 0;
      albedo[p4 + 3] = 255;
      height[idx] = h < 0 ? 0 : h > 1 ? 1 : h;
    }
  }
  return finalizeSurfacePbr(albedo, height, size, { strength: 2.6, lo: 0.7, hi: 0.99, repeatX: 5, repeatY: 3 });
}

function buildRoofBundle() {
  if (IS_HEADLESS) return finalizeSurfacePbr(null, null, 1);
  const { fbm16 } = getSharedFields();
  const size = SURF_SIZE;
  const albedo = new Uint8Array(size * size * 4);
  const height = new Float32Array(size * size);
  const rand = makeRng(20261414);
  const tileVar = Float32Array.from({ length: 128 }, () => (rand() - 0.5) * 40);

  for (let y = 0; y < size; y += 1) {
    const rowF = (y / size) * 9;
    const row = rowF < 8 ? rowF | 0 : 8;
    const ry = rowF - row;
    const rowShift = (row & 1) * 0.5;
    for (let x = 0; x < size; x += 1) {
      const idx = y * size + x;
      const p4 = idx * 4;
      const colF = (x / size + rowShift) * 7;
      const col = colF | 0;
      const cx = colF - col;
      const arch = 4 * cx * (1 - cx);
      const overlap = ry > 0.72 + arch * 0.2;
      const seam = cx < 0.045 || cx > 0.955;
      const moss = fbm16[idx];
      const base = 178 + tileVar[(row * 11 + col) & 127] + arch * 26 - ry * 42;

      let r = base;
      let g = base - 2 + (moss > 0.68 ? 14 : 0);
      let b = base - 6;
      let h = 0.42 + arch * 0.42 + (1 - ry) * 0.16;

      if (overlap || seam) {
        r *= 0.66;
        g *= 0.66;
        b *= 0.66;
        h = 0.12;
      }

      albedo[p4] = r < 0 ? 0 : r > 255 ? 255 : r | 0;
      albedo[p4 + 1] = g < 0 ? 0 : g > 255 ? 255 : g | 0;
      albedo[p4 + 2] = b < 0 ? 0 : b > 255 ? 255 : b | 0;
      albedo[p4 + 3] = 255;
      height[idx] = h < 0 ? 0 : h > 1 ? 1 : h;
    }
  }
  return finalizeSurfacePbr(albedo, height, size, { strength: 2.0, lo: 0.55, hi: 0.92, repeatX: 2.2, repeatY: 2.2 });
}

function buildCobbleBundle() {
  if (IS_HEADLESS) return finalizeSurfacePbr(null, null, 1);
  const { fbm16 } = getSharedFields();
  const size = SURF_SIZE;
  const cells = 12;
  const albedo = new Uint8Array(size * size * 4);
  const height = new Float32Array(size * size);
  const rand = makeRng(20261515);
  const ptsX = new Float32Array(cells * cells);
  const ptsY = new Float32Array(cells * cells);
  const ptsTone = new Float32Array(cells * cells);
  for (let i = 0; i < cells * cells; i += 1) {
    ptsX[i] = 0.16 + rand() * 0.68;
    ptsY[i] = 0.16 + rand() * 0.68;
    ptsTone[i] = 108 + rand() * 58;
  }

  const scale = cells / size;
  for (let y = 0; y < size; y += 1) {
    const gy = y * scale;
    const cy = gy | 0;
    for (let x = 0; x < size; x += 1) {
      const idx = y * size + x;
      const p4 = idx * 4;
      const gx = x * scale;
      const cx = gx | 0;

      let d1Sq = 9;
      let d2Sq = 9;
      let winTone = 130;
      for (let oy = -1; oy <= 1; oy += 1) {
        const ny = (cy + oy + cells) % cells;
        const rowBase = ny * cells;
        for (let ox = -1; ox <= 1; ox += 1) {
          const nx = (cx + ox + cells) % cells;
          const cIdx = rowBase + nx;
          const dx = cx + ox + ptsX[cIdx] - gx;
          const dy = cy + oy + ptsY[cIdx] - gy;
          const dSq = dx * dx + dy * dy;
          if (dSq < d1Sq) {
            d2Sq = d1Sq;
            d1Sq = dSq;
            winTone = ptsTone[cIdx];
          } else if (dSq < d2Sq) {
            d2Sq = dSq;
          }
        }
      }

      const edge = Math.sqrt(d2Sq) - Math.sqrt(d1Sq);
      const dome = edge * 3.4 < 1 ? edge * 3.4 : 1;
      const fine = fbm16[idx];
      const mortar = edge < 0.095;
      let base = winTone * (0.72 + dome * 0.36) + (fine - 0.5) * 20;
      let h = dome * 0.85 + fine * 0.15;

      if (mortar) {
        base = 56 + fine * 20;
        h = 0.08;
      }

      albedo[p4] = base < 0 ? 0 : base > 255 ? 255 : base | 0;
      albedo[p4 + 1] = base + 8 < 0 ? 0 : base + 8 > 255 ? 255 : (base + 8) | 0;
      albedo[p4 + 2] = base + 20 < 0 ? 0 : base + 20 > 255 ? 255 : (base + 20) | 0;
      albedo[p4 + 3] = 255;
      height[idx] = h < 0 ? 0 : h > 1 ? 1 : h;
    }
  }
  return finalizeSurfacePbr(albedo, height, size, { strength: 2.3, lo: 0.66, hi: 0.98, repeatX: 1, repeatY: 1 });
}

function buildWaterNormalTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([128, 128, 255, 255]), 1);
  const size = SURF_SIZE;
  const waves = [
    [3, 1, 1.0, 0.4],
    [2, -4, 0.85, 1.7],
    [-5, 3, 0.55, 2.6],
    [7, 6, 0.35, 0.9],
    [-9, -5, 0.26, 4.1],
    [12, -11, 0.18, 3.0],
  ];
  const cosX = waves.map(([kx, , , phase]) => {
    const arr = new Float32Array(size);
    for (let x = 0; x < size; x += 1) arr[x] = Math.cos((kx * x * TAU) / size + phase);
    return arr;
  });
  const sinX = waves.map(([kx, , , phase]) => {
    const arr = new Float32Array(size);
    for (let x = 0; x < size; x += 1) arr[x] = Math.sin((kx * x * TAU) / size + phase);
    return arr;
  });

  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const v = (y * TAU) / size;
    const cosY = new Float32Array(6);
    const sinY = new Float32Array(6);
    for (let w = 0; w < 6; w += 1) {
      const kyv = waves[w][1] * v;
      cosY[w] = Math.cos(kyv);
      sinY[w] = Math.sin(kyv);
    }
    for (let x = 0; x < size; x += 1) {
      let dhdu = 0;
      let dhdv = 0;
      for (let w = 0; w < 6; w += 1) {
        const d = (cosX[w][x] * cosY[w] - sinX[w][x] * sinY[w]) * waves[w][2];
        dhdu += d * waves[w][0];
        dhdv += d * waves[w][1];
      }
      const nx = -dhdu * 0.055;
      const ny = -dhdv * 0.055;
      const invLen = 127.5 / Math.sqrt(nx * nx + ny * ny + 1);
      const i = (y * size + x) * 4;
      data[i] = (nx * invLen + 127.5) | 0;
      data[i + 1] = (ny * invLen + 127.5) | 0;
      data[i + 2] = (invLen + 127.5) | 0;
      data[i + 3] = 255;
    }
  }
  return finishDataTexture(data, size, { repeatX: 26, repeatY: 26 });
}

function buildNoiseTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([128, 128, 128, 255]), 1);
  const { fbm4, fbm8, fbm16 } = getSharedFields();
  const size = SURF_SIZE;
  const data = new Uint8Array(size * size * 4);
  for (let i = 0; i < size * size; i += 1) {
    const p4 = i * 4;
    data[p4] = (fbm4[i] * 255) | 0;
    data[p4 + 1] = (fbm8[i] * 255) | 0;
    data[p4 + 2] = (fbm16[i] * 255) | 0;
    data[p4 + 3] = 255;
  }
  return finishDataTexture(data, size);
}

function buildCloudSoftTexture() {
  if (IS_HEADLESS) return finishDataTexture(new Uint8Array([255, 255, 255, 180]), 1, { srgb: true });
  const { fbm4, fbm8 } = getSharedFields();
  const size = SURF_SIZE;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const v = y / size;
    const dy = (v - 0.56) / 0.42;
    const tLit = v > 0.72 ? 0 : v < 0.18 ? 1 : (0.72 - v) / 0.54;
    const sLit = tLit * tLit * (3 - 2 * tLit);
    const nRow = ((y + 37) & SURF_MASK) * size;
    const fRow = ((y + 9) & SURF_MASK) * size;
    for (let x = 0; x < size; x += 1) {
      const u = x / size;
      const dx = (u - 0.5) / 0.49;
      const radial = Math.sqrt(dx * dx + dy * dy);
      const n = fbm4[nRow + ((x + 17) & SURF_MASK)];
      const nFine = fbm8[fRow + ((x + 78) & SURF_MASK)];
      const edge = 1 - radial + (n - 0.5) * 0.85 + (nFine - 0.5) * 0.26;
      const tEdge = edge < 0.02 ? 0 : edge > 0.5 ? 1 : (edge - 0.02) / 0.48;
      const tRad = radial > 1.06 ? 0 : radial < 0.86 ? 1 : (1.06 - radial) / 0.2;
      const alpha = tEdge * tEdge * (3 - 2 * tEdge) * (tRad * tRad * (3 - 2 * tRad));
      const lit = 0.72 + 0.28 * sLit + (n - 0.5) * 0.12;
      const shade = lit <= 0 ? 0 : lit >= 1 ? 255 : (lit * 255) | 0;
      const i = (y * size + x) * 4;
      data[i] = (shade * 0.96) | 0;
      data[i + 1] = (shade * 0.985) | 0;
      data[i + 2] = shade;
      data[i + 3] = (alpha * 255) | 0;
    }
  }
  const tex = finishDataTexture(data, size, { srgb: true });
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  return tex;
}

function createTextureStepList(bag) {
  return [
    () => { SHARED_FIELDS.fine = createFineNoiseField(); },
    () => { SHARED_FIELDS.fbm4 = buildSeamlessFbm(10101, 4, 4); },
    () => { SHARED_FIELDS.fbm8 = buildSeamlessFbm(20202, 8, 4); },
    () => { SHARED_FIELDS.fbm16 = buildSeamlessFbm(30303, 16, 3); },
    () => { bag.glow = buildGlowTexture(); },
    () => { bag.star = buildStarTexture(); },
    () => { bag.smoke = buildSmokeTexture(); },
    () => { bag.windowPane = buildWindowPaneTexture(); },
    () => { bag.shadowBlob = buildShadowBlobTexture(); },
    () => { bag.cloud = buildCloudTexture(); },
    () => { bag.sunRays = buildSunRaysTexture(); },
    () => { bag.solar = buildSolarTexture(); },
    () => { bag.grassBlade = buildGrassBladeTexture(); },
    () => { bag.moon = buildMoonTexture(); },
    () => { bag.foam = buildFoamTexture(); },
    () => {
      const wood = buildWoodBundle();
      bag.wood = wood.albedo;
      bag.woodNormal = wood.normal;
      bag.woodRough = wood.rough;
    },
    () => {
      const stone = buildStoneBundle();
      bag.stone = stone.albedo;
      bag.stoneNormal = stone.normal;
      bag.stoneRough = stone.rough;
    },
    () => {
      const grass = buildGrassBundle();
      bag.grass = grass.albedo;
      bag.grassNormal = grass.normal;
      bag.grassRough = grass.rough;
    },
    () => {
      const sand = buildSandBundle();
      bag.sand = sand.albedo;
      bag.sandNormal = sand.normal;
      bag.sandRough = sand.rough;
    },
    () => {
      const rock = buildRockBundle();
      bag.rock = rock.albedo;
      bag.rockNormal = rock.normal;
      bag.rockRough = rock.rough;
    },
    () => {
      const roof = buildRoofBundle();
      bag.roof = roof.albedo;
      bag.roofNormal = roof.normal;
      bag.roofRough = roof.rough;
    },
    () => {
      const cobble = buildCobbleBundle();
      bag.cobble = cobble.albedo;
      bag.cobbleNormal = cobble.normal;
      bag.cobbleRough = cobble.rough;
    },
    () => { bag.waterNormal = buildWaterNormalTexture(); },
    () => { bag.noise = buildNoiseTexture(); },
    () => { bag.cloudSoft = buildCloudSoftTexture(); },
  ];
}

function finalizeTextureBag(bag) {
  const list = Object.values(bag).filter((v) => v && v.isTexture);
  bag.dispose = () => {
    list.forEach((t) => t.dispose());
  };
  return bag;
}

/**
 * 발전섬 디오라마가 사용하는 35종 프로시저럴 PBR 텍스처 세트 (동기 생성).
 */
export function createIslandTextures() {
  const bag = {};
  const steps = createTextureStepList(bag);
  for (let i = 0; i < steps.length; i += 1) {
    steps[i]();
  }
  return finalizeTextureBag(bag);
}

const nextFrame = () =>
  new Promise((resolve) => {
    // A task yield gives the browser a paint opportunity and also works in headless
    // harnesses whose requestAnimationFrame queue is deliberately test-controlled.
    const timer = typeof window !== "undefined" && typeof window.setTimeout === "function"
      ? window.setTimeout.bind(window)
      : setTimeout;
    timer(resolve, 0);
  });

/**
 * 메인 스레드 프레임 예산(기본 9ms)을 넘기면 브라우저 페인트에 양보하며
 * 프로시저럴 텍스처를 비동기로 생성한다.
 */
export async function createIslandTexturesAsync({ onProgress, budgetMs = 9 } = {}) {
  const bag = {};
  const steps = createTextureStepList(bag);
  let sliceStart = performance.now();
  for (let i = 0; i < steps.length; i += 1) {
    steps[i]();
    if (onProgress) onProgress((i + 1) / steps.length);
    if (i < steps.length - 1 && performance.now() - sliceStart >= budgetMs) {
      await nextFrame();
      sliceStart = performance.now();
    }
  }
  return finalizeTextureBag(bag);
}
