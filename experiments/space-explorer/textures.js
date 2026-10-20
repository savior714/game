// 태양계 3D 탐험대 — 텍스처 로더
// 행성 표면/범프/야간/구름/고리 텍스처를 한 번에 불러오고 진행률을 보고한다.

import * as THREE from "three";
import { MOONS, PLANETS, SKY_TEXTURE, SUN, TEXTURE_BASE } from "./data.js";

/** 색상 텍스처(알베도)와 데이터 텍스처(범프/노멀/스페큘러)의 색 공간을 구분한다. */
const COLOR_MAPS = new Set([
  "sun.jpg",
  "mercury.jpg",
  "venus.jpg",
  "earth_day.jpg",
  "earth_night.jpg",
  "earth_clouds.png",
  "mars.jpg",
  "jupiter.jpg",
  "saturn.jpg",
  "uranus.jpg",
  "neptune.jpg",
  "moon.jpg",
  "saturn_ring_alpha.png",
  "galaxy_starfield.jpg",
]);

function collectTextureNames() {
  const names = new Set();
  for (const body of [SUN, ...PLANETS, ...MOONS]) {
    if (body.texture) names.add(body.texture);
    if (body.bumpTexture) names.add(body.bumpTexture);
    if (body.nightTexture) names.add(body.nightTexture);
    if (body.cloudTexture) names.add(body.cloudTexture);
    if (body.normalTexture) names.add(body.normalTexture);
    if (body.specularTexture) names.add(body.specularTexture);
    if (body.ringTexture) names.add(body.ringTexture);
  }
  names.add(SKY_TEXTURE);
  return [...names];
}

function createFallbackTexture(body, renderer) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 256;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = body?.color || "#8a8f98";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, "rgba(255,255,255,0.18)");
  gradient.addColorStop(0.5, "rgba(255,255,255,0)");
  gradient.addColorStop(1, "rgba(0,0,0,0.28)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  for (let i = 0; i < 140; i += 1) {
    const x = Math.random() * canvas.width;
    const y = Math.random() * canvas.height;
    const radius = 2 + Math.random() * 16;
    ctx.fillStyle = `rgba(255,255,255,${0.02 + Math.random() * 0.05})`;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = Math.min(4, renderer.capabilities.getMaxAnisotropy());
  return texture;
}

/**
 * @param {THREE.WebGLRenderer} renderer
 * @param {(loaded:number,total:number,label:string)=>void} onProgress
 */
export function createTextureLibrary(renderer, onProgress = () => {}) {
  const loader = new THREE.TextureLoader();
  const cache = new Map();
  const maxAnisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  const names = collectTextureNames();
  let loaded = 0;

  function configure(texture, name) {
    texture.colorSpace = COLOR_MAPS.has(name) ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    texture.anisotropy = maxAnisotropy;
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.generateMipmaps = true;
    texture.needsUpdate = true;
    return texture;
  }

  function loadOne(name, fallbackBody) {
    if (cache.has(name)) return cache.get(name);

    const promise = new Promise((resolve) => {
      loader.load(
        `${TEXTURE_BASE}${name}`,
        (texture) => {
          loaded += 1;
          onProgress(loaded, names.length, name);
          resolve(configure(texture, name));
        },
        undefined,
        () => {
          loaded += 1;
          onProgress(loaded, names.length, name);
          // 텍스처가 없더라도 화면이 비지 않도록 대체 텍스처를 쓴다.
          resolve(createFallbackTexture(fallbackBody, renderer));
        },
      );
    });

    cache.set(name, promise);
    return promise;
  }

  async function loadAll() {
    const entries = await Promise.all(
      names.map((name) => {
        const body = [...PLANETS, ...MOONS, SUN].find(
          (candidate) =>
            candidate.texture === name ||
            candidate.bumpTexture === name ||
            candidate.nightTexture === name ||
            candidate.cloudTexture === name ||
            candidate.normalTexture === name ||
            candidate.specularTexture === name ||
            candidate.ringTexture === name,
        );
        return loadOne(name, body).then((texture) => [name, texture]);
      }),
    );
    return new Map(entries);
  }

  return {
    names,
    loadAll,
    get: (name) => cache.get(name),
    maxAnisotropy,
  };
}
