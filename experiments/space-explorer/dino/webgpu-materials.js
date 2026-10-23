// dino-escape 전용 WebGPU/TSL 머티리얼.
//
// dino 페이지에는 import map이 없어(계약 테스트가 고정) 모든 import를 상대
// 경로로만 쓴다. world.js/models.js/particles.js의 GLSL ShaderMaterial과
// onBeforeCompile wind hook을 TSL로 대체하며, 기존 갱신 코드가 건드리는
// uniforms 키(uTime, uColor, uOpacity, uScale, uWindTime ...)를 동일하게 노출한다.

import * as TSL from "../webgpu/tsl.js";
import { createBillboardCloud } from "../webgpu/instanced-sprites.js";
import { valueNoise2DStandard } from "../webgpu/noise.js";

const {
  Fn,
  If,
  Discard,
  uniform,
  attribute,
  varyingProperty,
  positionLocal,
  positionWorld,
  normalWorld,
  cameraPosition,
  modelViewProjection,
  uv,
  float,
  vec2,
  vec3,
  vec4,
  mix,
  smoothstep,
  normalize,
  length,
  dot,
  pow,
  clamp,
  abs,
  sin,
  cos,
  atan,
  fract,
  floor,
  max,
  time,
} = TSL;

/* ------------------------------------------------------------- 하늘 */

export function createWebGpuSky(three, tsl, initial, skyRadius, sunDirection) {
  const uniforms = {
    uTop: uniform(new three.Color(initial.skyTop)),
    uHorizon: uniform(new three.Color(initial.skyHorizon)),
    uLow: uniform(new three.Color(initial.skyLow)),
    uSun: uniform(new three.Color(initial.skySun)),
    uSunDirection: uniform(sunDirection.clone()),
    uTime: uniform(0),
  };

  const fragmentNode = Fn(() => {
    const dir = normalize(positionLocal);
    const h = dir.y;
    let color = mix(uniforms.uLow, uniforms.uHorizon, smoothstep(-0.16, 0.12, h));
    color = mix(color, uniforms.uTop, smoothstep(0.03, 0.62, h));

    const sunDot = max(dot(dir, normalize(uniforms.uSunDirection)), 0);
    color = color.add(uniforms.uSun.mul(pow(sunDot, 340).mul(2.2)));
    color = color.add(uniforms.uSun.mul(pow(sunDot, 14).mul(0.34)));
    color = color.add(uniforms.uSun.mul(pow(sunDot, 2.5).mul(0.07)));

    const angle = atan(dir.z, dir.x);
    const band = h.sub(0.03).div(0.55);
    let clouds = valueNoise2DStandard(
      vec2(angle.mul(3.1).add(uniforms.uTime.mul(0.006)), band.mul(5.5)),
    );
    clouds = clouds.add(
      valueNoise2DStandard(
        vec2(angle.mul(7.4).sub(uniforms.uTime.mul(0.004)), band.mul(11)),
      ).mul(0.5),
    );
    clouds = smoothstep(0.72, 1.12, clouds)
      .mul(smoothstep(0.02, 0.2, h))
      .mul(float(1).sub(smoothstep(0.45, 0.8, h)));
    const cloudTint = mix(uniforms.uHorizon, uniforms.uSun, 0.25).mul(1.05);
    color = mix(color, cloudTint, clouds.mul(0.32));

    return vec4(color, 1.0);
  })();

  const material = new three.MeshBasicNodeMaterial({
    fragmentNode,
    side: three.BackSide,
    depthWrite: false,
    fog: false,
  });
  material.uniforms = uniforms;
  const mesh = new three.Mesh(new three.SphereGeometry(skyRadius, 32, 18), material);
  mesh.frustumCulled = false;
  mesh.renderOrder = -10;
  return { mesh, uniforms };
}

/* ----------------------------------------------------- 꽃가루(ambient) */

export function createWebGpuAmbient(three, tsl, {
  positions,
  sizes,
  phases,
  count,
  pollenColor,
  layers = null,
}) {
  const uniforms = {
    uTime: uniform(0),
    uColor: uniform(new three.Color(pollenColor)),
    uOpacity: uniform(0.55),
    // GLSL 쪽 uScale(화면 크기 기반 포인트 스케일)은 빌보드에서는 무의미하지만
    // 기존 갱신 코드 호환을 위해 키만 유지한다.
    uScale: uniform(500),
  };

  const twinkleNode = (phaseNode) => {
    const wave = float(0.5).add(float(0.5).mul(sin(uniforms.uTime.mul(1.5).add(phaseNode))));
    return float(0.45).add(float(0.55).mul(pow(wave, 2)));
  };

  const cloud = createBillboardCloud(three, {
    count,
    positions,
    sizes,
    phases,
    baseColor: 0xffffff,
    additive: true,
    twinkleNode: (phase) => twinkleNode(phase),
  });

  // createBillboardCloud는 흰색 기반을 쓰므로 최종 색을 uColor로 칠하고
  // 투명도를 uOpacity로 조절하도록 fragmentNode를 교체한다.
  const { vLocalUv } = cloud.varyings;
  cloud.material.fragmentNode = Fn(() => {
    const radial = length(vLocalUv.sub(0.5));
    const mask = smoothstep(0.5, 0.1, radial);
    const phase = attribute("aCloudPhase", "float");
    const twinkle = twinkleNode(phase);
    const alpha = uniforms.uOpacity.mul(twinkle).mul(mask);
    If(alpha.lessThan(0.003), () => {
      Discard();
    });
    return vec4(uniforms.uColor, alpha);
  })();
  cloud.mesh.renderOrder = 4;
  cloud.mesh.uniforms = uniforms;
  if (layers) cloud.mesh.layers = layers;
  return { mesh: cloud.mesh, uniforms, attributes: cloud.attributes };
}

/* ------------------------------------------------------------- 용암 기둥 */

export function createWebGpuLavaColumn(three, tsl) {
  const uniforms = {
    uTime: uniform(0),
    uOpacity: uniform(0),
    uColorHot: uniform(new three.Color(0xffd27a)),
    uColorCool: uniform(new three.Color(0xff5a1f)),
  };

  const hash1 = Fn(([n]) => fract(sin(n.mul(91.3458)).mul(47453.5453)));
  const noise1 = Fn(([x]) => {
    const i = floor(x);
    const f = smoothstep(0, 1, fract(x));
    return mix(hash1(i), hash1(i.add(1)), f);
  });

  const fragmentNode = Fn(() => {
    const rise = clamp(uv().y, 0, 1);
    const body = smoothstep(0, 0.22, rise).mul(pow(float(1).sub(rise), 0.85));
    const streak = noise1(
      uv().y.mul(7).sub(uniforms.uTime.mul(3.4)).add(uv().x.mul(4)),
    );
    const grain = noise1(
      uv().y
        .mul(21)
        .sub(uniforms.uTime.mul(6.2))
        .add(hash1(uv().x.mul(13)).mul(4)),
    );
    const fresnel = pow(
      float(1).sub(abs(normalWorld.z)),
      1.4,
    );
    const alpha = body
      .mul(float(0.42).add(streak.mul(0.42)).add(grain.mul(0.16)).add(fresnel.mul(0.25)))
      .mul(uniforms.uOpacity);
    If(alpha.lessThan(0.004), () => {
      Discard();
    });
    const heat = smoothstep(0, 0.85, float(1).sub(rise))
      .mul(float(0.55).add(streak.mul(0.45)));
    const color = mix(uniforms.uColorCool, uniforms.uColorHot, heat);
    return vec4(color, clamp(alpha, 0, 0.85));
  })();

  const material = new three.MeshBasicNodeMaterial({
    fragmentNode,
    transparent: true,
    depthWrite: false,
    blending: three.AdditiveBlending,
    side: three.DoubleSide,
  });
  material.uniforms = uniforms;
  return material;
}

/* ------------------------------------------------------------- 바람 흔들림 */

/**
 * GLSL onBeforeCompile wind 훅을 TSL positionNode로 대체한다.
 * 반환된 uniforms 객체를 windShaders 배열에 푸시하면 기존 시간 갱신 루프가
 * `shader.uniforms.uWindTime`을 그대로 갱신한다.
 */
export function applyWindNode(three, tsl, material, strength) {
  const uniforms = { uWindTime: uniform(0) };
  const instanceOrigin = attribute("instanceMatrix", "mat4").element(3).xyz;

  material.positionNode = Fn(() => {
    const bendAmount = max(float(0), positionLocal.y);
    const sway = sin(
      uniforms.uWindTime
        .mul(1.15)
        .add(instanceOrigin.x.mul(0.31))
        .add(instanceOrigin.z.mul(0.17)),
    );
    const swayB = cos(
      uniforms.uWindTime
        .mul(0.83)
        .add(instanceOrigin.z.mul(0.27))
        .add(instanceOrigin.x.mul(0.11)),
    );
    const displaced = positionLocal.add(
      vec3(
        sway.mul(bendAmount).mul(strength),
        float(0),
        swayB.mul(bendAmount).mul(strength * 0.62),
      ),
    );
    return displaced;
  })();
  material.uniforms = material.uniforms || {};
  Object.assign(material.uniforms, uniforms);
  return uniforms;
}

/* ----------------------------------------------------- 파티클 풀(먼지/불꽃) */

/**
 * WebGPU용 파티클 풀. GLSL Points 셰이더의 소프트 원형 마스크를 인스턴스
 * 빌보드로 재현하며, spawn/update가 쓰는 typed array 레이아웃은 동일하게 유지한다.
 */
export function createWebGpuParticlePool(three, tsl, scene, { max, additive = false }) {
  const positions = new Float32Array(max * 3);
  const sizes = new Float32Array(max);
  const alphas = new Float32Array(max).fill(0);
  const colors = new Float32Array(max * 3);
  // 화면에서 사라진 죽은 인스턴스는 크기 0으로 만든다(기본 알파 0).
  sizes.fill(0.0001);

  const cloud = createBillboardCloud(three, {
    count: max,
    positions,
    sizes,
    colors,
    alphas,
    additive,
    dynamic: true,
  });
  scene.add(cloud.mesh);

  const { vAlpha, vColor, vLocalUv } = cloud.varyings;
  cloud.material.fragmentNode = Fn(() => {
    const distanceToCenter = length(vLocalUv.sub(0.5));
    const mask = smoothstep(0.5, 0.08, distanceToCenter);
    const alpha = vAlpha.mul(mask);
    If(alpha.lessThan(0.003), () => {
      Discard();
    });
    return vec4(vColor, alpha);
  })();

  return {
    mesh: cloud.mesh,
    material: cloud.material,
    geometry: cloud.geometry,
    attributes: {
      position: cloud.attributes.position,
      aSize: cloud.attributes.size,
      aAlpha: cloud.attributes.alpha,
      aColor: cloud.attributes.color,
    },
  };
}

export { time, modelViewProjection };
