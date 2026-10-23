/**
 * electricity_lab WebGPU TSL 빌더 모음.
 *
 * world.js의 GLSL ShaderMaterial / onBeforeCompile / EffectComposer 경로를
 * WebGPURenderer에서 재생산한다. 모든 빌더는 기존 코드가 건드리는 uniform 키를
 * `material.uniforms.<key>.value` 형태로 그대로 노출해 갱신 루프를 공유한다.
 *
 * importmap에 three/webgpu · three/tsl · three/addons/tsl/ 이 있는 페이지 전용.
 */
import { Fn, If, Discard, Loop, float, vec2, vec3, vec4, uniform, uv, positionLocal,
  positionWorld, normalLocal, positionView, normalView, modelViewMatrix, color,
  texture, screenUV, pass, viewportResolution, attribute, varyingProperty, sin, cos,
  atan, asin, tan, pow, exp, abs, max, min, dot, normalize, mix, smoothstep, step,
  fract, reflect, clamp, length, floor, cameraPosition } from "three/tsl";
import { bloom } from "three/addons/tsl/display/BloomNode.js";
import { RenderPipeline } from "three/webgpu";
import { fbm2, fbm3, hash21Alt } from "../space-explorer/webgpu/noise.js";
import { createBillboardCloud } from "../space-explorer/webgpu/instanced-sprites.js";

/* ------------------------------------------------------------- 유틸 */

function attachUniforms(material, uniforms) {
  material.uniforms = uniforms;
  return material;
}

const saturate = (v) => v.clamp(0, 1);

/* ------------------------------------------------------------- 광선 빔 */

/**
 * makeBeamMaterial의 TSL 이식. 시점 facing 볼륨 라이트 + 노이즈 그레인.
 */
export function createWebGpuBeamMaterial(three, tsl, {
  color: colorHex = 0xffd88a,
  opacity = 0.32,
  noise = null,
  fade = 0.18,
  softness = 1.25,
  speed = 1,
} = {}) {
  const uniforms = {
    uColor: uniform(new three.Color(colorHex)),
    uOpacity: uniform(opacity),
    uNoise: uniform(noise),
    uTime: uniform(0),
    uFade: uniform(fade),
    uSoftness: uniform(softness),
    uSpeed: uniform(speed),
  };
  const material = new three.MeshBasicNodeMaterial({
    transparent: true,
    depthWrite: false,
    side: three.DoubleSide,
    blending: three.AdditiveBlending,
  });
  const uvBeam = uv();
  const facing = abs(dot(normalize(normalView), positionView.negate().normalize()));
  const density = pow(float(1).sub(facing), uniforms.uSoftness);
  const lengthFade = pow(clamp(uvBeam.y, 0, 1), uniforms.uFade);
  const noiseUv = uvBeam
    .mul(vec2(2.5, 1.0))
    .add(vec2(0.0, uniforms.uTime.mul(uniforms.uSpeed).negate()));
  const grain = clamp(texture(uniforms.uNoise, noiseUv).r.mul(1.18), 0.0, 1.25);
  material.opacityNode = density.mul(lengthFade).mul(grain).mul(uniforms.uOpacity);
  material.colorNode = vec4(uniforms.uColor, 1.0);
  material.alphaTest = 0.0015;
  return attachUniforms(material, uniforms);
}

/* ------------------------------------------------------------- 대기 스카이 */

/**
 * world.js skyMat의 1:1 TSL 이식. uniforms는 GLSL 버전과 동일한 키 집합을 가진다.
 * @returns {{mesh:object, uniforms:object, material:object}}
 */
/* ------------------------------------------------------------- 대기 스카이 */

// skyMat GLSL과 동일한 해시/벨류 노이즈/4옥타브 fbm(노이즈 모듈과 해시 규칙이 다르다).
const skyHash21 = Fn(([p]) => {
  const q = fract(p.mul(vec2(123.34, 456.21))).toVar();
  q.addAssign(q.dot(q.add(45.32)));
  return fract(q.x.mul(q.y));
});
const skyValueNoise = Fn(([p]) => {
  const i = floor(p).toVar();
  const f = fract(p).toVar();
  const ff = f.mul(f).mul(float(3.0).sub(f.mul(2.0)));
  const a = skyHash21(i);
  const b = skyHash21(i.add(vec2(1.0, 0.0)));
  const c = skyHash21(i.add(vec2(0.0, 1.0)));
  const d = skyHash21(i.add(vec2(1.0, 1.0)));
  return mix(mix(a, b, ff.x), mix(c, d, ff.x), ff.y);
});
const skyFbm = Fn(([p]) => {
  const q = p.toVar();
  const value = float(0.0).toVar();
  const amplitude = float(0.5).toVar();
  Loop(4, () => {
    value.addAssign(skyValueNoise(q).mul(amplitude));
    q.mulAssign(2.03);
    amplitude.mulAssign(0.5);
  });
  return value;
});

/**
 * world.js skyMat의 1:1 TSL 이식. uniforms는 GLSL 버전과 동일한 키 집합을 가진다.
 * @returns {{mesh:object, uniforms:object, material:object}}
 */
export function createWebGpuSky(three, tsl, skyUniforms, radius = 400) {
  const skyFragment = Fn(() => {
    const u = skyUniforms;
    const dir = normalize(positionWorld).toVar();
    const h = dir.y;
    const up = clamp(h, 0.0, 1.0);

    // 3단 그라디언트: 지평선 헤이즈 → 중간 하늘 → 천정
    let col = mix(u.uHorizon, u.uTop, pow(up, 0.55));
    col = mix(col, mix(u.uHorizon, u.uGlow, 0.35), exp(up.negate().mul(5.0)).mul(0.55));

    // 태양 헤일로 2단
    const sunDot = max(dot(dir, normalize(u.uSunDir)), 0.0);
    col = col.add(
      u.uSunColor.mul(pow(sunDot, max(6.0, u.uSunPower.mul(0.06)))).mul(u.uSunStrength).mul(0.22)
    );
    col = col.add(
      u.uSunColor.mul(pow(sunDot, u.uSunPower)).mul(u.uSunStrength).mul(2.4)
    );

    // 달 헤일로
    const moonDot = max(dot(dir, normalize(u.uMoonDir)), 0.0);
    col = col.add(
      u.uMoonColor
        .mul(pow(moonDot, 26.0).mul(0.16).add(pow(moonDot, 900.0).mul(0.7)))
        .mul(u.uMoon)
    );

    // 은하수 띠
    const bandDir = normalize(vec3(0.42, 0.36, -0.82));
    const milkyBand = exp(pow(dot(dir, bandDir).mul(2.6), 2.0).negate());
    const milkyUv = vec2(atan(dir.z, dir.x).mul(2.2), dir.y.mul(6.0));
    const milkyNoise = skyFbm(milkyUv.mul(2.4).add(7.0));
    col = col.add(
      vec3(0.32, 0.38, 0.62)
        .mul(milkyBand).mul(smoothstep(0.35, 0.9, milkyNoise)).mul(u.uMilky).mul(0.5)
    );
    col = col.add(vec3(0.1, 0.12, 0.22).mul(milkyBand).mul(u.uMilky).mul(0.22));

    // 권운
    const skyPlane = dir.xz.div(max(0.18, h.mul(1.1).add(0.28)));
    const cirrus = skyFbm(
      skyPlane.mul(vec2(0.55, 1.9)).add(vec2(u.uTime.mul(0.006), u.uTime.mul(0.002)))
    );
    const cirrusMask = smoothstep(0.52, 0.9, cirrus).mul(smoothstep(0.02, 0.3, h));
    col = mix(col, mix(u.uHorizon, vec3(1.0), 0.32), cirrusMask.mul(u.uCloud).mul(0.34));

    // 지평선 아래 안개 합성
    const below = float(1.0).sub(smoothstep(-0.16, 0.02, h));
    col = mix(col, u.uFog, below.mul(0.92));
    col = mix(col, u.uFog, exp(abs(h).mul(-42.0)).mul(0.35));

    // 밴딩 제거 디더
    const fragCoord = screenUV.mul(viewportResolution);
    const dither = skyHash21(fragCoord.add(u.uTime.mul(0.5))).sub(0.5).mul(0.005);
    return vec4(col.add(dither).max(0.0), 1.0);
  })();

  const material = new three.MeshBasicNodeMaterial({
    side: three.BackSide,
    depthWrite: false,
    fog: false,
  });
  material.fragmentNode = skyFragment;
  const mesh = new three.Mesh(new three.SphereGeometry(radius, 48, 32), material);
  mesh.frustumCulled = false;
  mesh.renderOrder = -10;
  return { mesh, material, uniforms: skyUniforms };
}

/* ------------------------------------------------------------- 별 빌보드 */

/**
 * starMat Points를 대체하는 인스턴스 빌보드. gl_PointSize 감쇠 공식
 * (aSize * uPixelRatio * 160 / 거리)을 셰이더 안에서 월드 크기로 재현한다.
 */
export function createWebGpuStarField(three, tsl, {
  positions, sizes, phases, colors, count, map, fovDeg = 44,
  pixelRatio = 1, viewportHeight = 800,
} = {}) {
  const { varyingProperty, Discard, tan } = tsl;
  const uniforms = {
    uMap: tsl.uniform(map),
    uTime: tsl.uniform(0),
    uOpacity: tsl.uniform(0.9),
    uPixelRatio: tsl.uniform(pixelRatio),
    uViewportHeight: tsl.uniform(viewportHeight),
    uFov: tsl.uniform(fovDeg * (Math.PI / 180)),
  };
  const geo = new three.PlaneGeometry(1, 1);
  geo.setAttribute("aCloudPosition", new three.InstancedBufferAttribute(positions, 3));
  geo.setAttribute("aCloudSize", new three.InstancedBufferAttribute(sizes, 1));
  geo.setAttribute("aCloudPhase", new three.InstancedBufferAttribute(phases, 1));
  geo.setAttribute("aCloudColor", new three.InstancedBufferAttribute(colors, 3));
  geo.boundingSphere = new three.Sphere(new three.Vector3(), 100000);

  const vColor = varyingProperty("vec3", "vStarColor");
  const vTwinkle = varyingProperty("float", "vStarTwinkle");

  const vertexNode = Fn(() => {
    const instancePos = attribute("aCloudPosition", "vec3");
    const aSize = attribute("aCloudSize", "float");
    const phase = attribute("aCloudPhase", "float");
    const mv = modelViewMatrix.mul(vec4(instancePos, 1.0));
    const dist = max(mv.z.negate(), 1.0);
    const pointPx = aSize.mul(uniforms.uPixelRatio).mul(160.0).div(dist);
    // 픽셀 크기를 해당 깊이의 월드 크기로 환산(투영 높이 = 2*tan(fov/2)*dist)
    const worldHalf = pointPx
      .mul(tan(uniforms.uFov.mul(0.5)))
      .mul(dist).mul(2.0)
      .div(uniforms.uViewportHeight);
    vColor.assign(attribute("aCloudColor", "vec3"));
    vTwinkle.assign(
      sin(uniforms.uTime.mul(1.7).add(phase)).mul(0.38).add(0.62)
    );
    const corner = positionLocal.mul(worldHalf);
    return tsl.billboarding({ position: instancePos.add(corner) });
  })();

  const fragmentNode = Fn(() => {
    const sampled = texture(uniforms.uMap, uv());
    const alpha = sampled.a.mul(uniforms.uOpacity).mul(vTwinkle);
    If(alpha.lessThan(0.01), () => {
      Discard();
    });
    return vec4(vColor.mul(sampled.rgb).mul(1.35), alpha);
  })();

  const material = new three.MeshBasicNodeMaterial({
    vertexNode,
    fragmentNode,
    transparent: true,
    depthWrite: false,
    side: three.DoubleSide,
    blending: three.AdditiveBlending,
  });
  const mesh = new three.InstancedMesh(geo, material, count);
  mesh.frustumCulled = false;
  return {
    mesh,
    material,
    geometry: geo,
    uniforms,
    setViewport(heightPx, pixelRatioValue) {
      uniforms.uViewportHeight.value = heightPx;
      uniforms.uPixelRatio.value = pixelRatioValue;
    },
  };
}

export function createWebGpuEnvDome(three, tsl, envUniforms) {
  const material = new three.MeshBasicNodeMaterial({
    side: three.BackSide,
    depthWrite: false,
  });
  material.fragmentNode = Fn(() => {
    const u = envUniforms;
    const dir = normalize(positionWorld).toVar();
    const h = dir.y;
    const sky = mix(u.uHorizon, u.uTop, pow(saturate(h), 0.55));
    const ground = mix(u.uHorizon.mul(0.55), u.uGround, saturate(h.negate().mul(2.2)));
    let col = mix(ground, sky, smoothstep(-0.08, 0.05, h));
    const sun = pow(max(dot(dir, normalize(u.uSunDir)), 0.0), 22.0);
    col = col.add(u.uSunColor.mul(sun).mul(u.uSunPower));
    const horizonGlow = exp(abs(h).mul(-5.5));
    col = col.add(u.uHorizon.mul(horizonGlow).mul(0.35));
    return vec4(col, 1.0);
  })();
  const mesh = new three.Mesh(new three.SphereGeometry(60, 20, 12), material);
  mesh.frustumCulled = false;
  return mesh;
}

/* ------------------------------------------------------------- 지면 디테일 */

/**
 * attachWorldSurface의 TSL 이식. MeshStandardNodeMaterial의 colorNode에
 * 노이즈 기반 온기/서리/스파클을 주입한다(조명 파이프라인은 PBR 그대로 유지).
 */
export function attachWorldSurfaceNode(three, tsl, material, {
  noise, scale = 0.05, strength = 0.5, warm = 0x8a9a6b, cool = 0x4a6a7a, sparkle = 0,
} = {}) {
  const warmColor = vec3(new three.Color(warm));
  const coolColor = vec3(new three.Color(cool));
  const baseColor = new three.Color(material.color?.getHex?.() ?? 0xffffff);
  const useVertexColors = Boolean(material.vertexColors);

  material.colorNode = Fn(() => {
    const worldPos = positionWorld;
    const detailUv = worldPos.xz.mul(scale);
    const detail = texture(noise, detailUv);
    let tint = texture(material.map, uv()).rgb.mul(vec3(baseColor));
    if (useVertexColors) {
      tint = tint.mul(color);
    }
    const grassNoise = smoothstep(0.28, 0.72, detail.r);
    const patchMask = smoothstep(0.55, 0.82, detail.g);
    const warmth = float(strength).mul(0.4).mul(grassNoise).mul(patchMask);
    tint = mix(tint, warmColor, warmth);
    const coolness = float(strength).mul(0.32).mul(smoothstep(0.62, 0.9, detail.b));
    tint = mix(tint, coolColor, coolness);
    if (sparkle > 0) {
      const sp = pow(detail.a, 14.0).mul(float(sparkle));
      tint = tint.add(vec3(1.0, 0.95, 0.82).mul(sp));
    }
    return vec4(tint, 1.0);
  })();
  return material;
}

/* ------------------------------------------------------------- 바다 */

const seaWaveHeight = Fn(([p, t]) => {
  return sin(p.x.mul(0.11).add(t.mul(0.95))).mul(0.5)
    .add(sin(p.y.mul(0.14).sub(t.mul(1.1))).mul(0.42))
    .add(sin(p.x.add(p.y).mul(0.06).add(t.mul(0.7))).mul(0.3))
    .add(sin(dot(p, vec2(0.42, -0.31)).add(t.mul(1.7))).mul(0.12))
    .add(sin(dot(p, vec2(-0.27, 0.51)).add(t.mul(2.3))).mul(0.07));
});

const seaShoreRadius = Fn(([a]) =>
  float(34.0).mul(
    float(1.0)
      .add(sin(a.mul(3.0).add(0.6)).mul(0.12))
      .add(cos(a.mul(5.0).sub(1.1)).mul(0.066))
  ).mul(0.955)
);

/**
 * seaMat(onBeforeCompile) 이식. 물리 PBR(clearcoat/normalMap)은 유지하고
 * 파고 변위(positionNode)와 거품/수심/글리터 색(colorNode)을 TSL로 주입한다.
 */
export function createWebGpuSeaMaterial(three, tsl, {
  config = {},
  uniforms,
} = {}) {
  const material = new three.MeshPhysicalNodeMaterial({
    ...config,
    side: three.DoubleSide,
  });

  // 정점 변위 — GLSL begin_vertex 주입과 동일하게 해안 가까이에서 진폭을 키운다
  material.positionNode = Fn(() => {
    const local = positionLocal.toVar();
    const origin = positionWorld;
    const seaAmp = mix(float(0.14), float(0.5), smoothstep(80.0, 22.0, length(origin.xz)));
    const height = seaWaveHeight(origin.xz, uniforms.uTime).mul(seaAmp);
    local.y.addAssign(height);
    return local;
  })();

  material.colorNode = Fn(() => {
    const u = uniforms;
    const seaWorld = positionWorld.toVar();
    const seaP = seaWorld.xz;
    const seaDist = length(seaP);
    const seaAngle = atan(seaP.y, seaP.x);
    const seaShore = seaShoreRadius(seaAngle);
    const seaDepth = smoothstep(seaShore.sub(0.4), seaShore.add(26.0), seaDist);

    const seaBand = texture(
      u.uNoise, seaP.mul(0.035).add(vec2(u.uTime.mul(0.004), u.uTime.mul(-0.003)))
    ).r;
    const seaBand2 = texture(
      u.uNoise, seaP.mul(0.11).add(vec2(u.uTime.mul(-0.01), u.uTime.mul(0.008)))
    ).r;
    const seaRipple = texture(
      u.uNoise, seaP.mul(0.26).add(vec2(u.uTime.mul(0.02), u.uTime.mul(0.013)))
    ).r;
    const seaCrest = smoothstep(
      0.74, 1.15, seaWaveHeight(seaP, u.uTime).add(seaBand2.mul(0.45))
    );

    // 밀려오는 해안 거품 두 겹
    const shoreGap = seaDist.sub(seaShore);
    const surge = float(1.5).add(sin(u.uTime.mul(0.9).add(seaAngle.mul(4.0))).mul(0.9));
    const shoreBand = float(1.0).sub(
      smoothstep(0.0, float(2.6).add(seaBand.mul(3.6)), abs(shoreGap.sub(surge)))
    );
    const shoreBand2 = float(1.0).sub(
      smoothstep(0.0, float(1.3).add(seaBand.mul(2.0)), abs(shoreGap.sub(surge.mul(2.4))))
    );
    const seaFoam = clamp(
      shoreBand.mul(float(0.55).add(seaBand.mul(1.1)))
        .add(shoreBand2.mul(0.42))
        .add(seaCrest.mul(float(0.35).add(seaRipple.mul(0.4)))),
      0.0, 1.0
    ).mul(u.uFoamAmount);

    let seaColor = mix(u.uShallowColor, u.uDeepColor, seaDepth);
    seaColor = seaColor.add(
      u.uSkyColor.mul(smoothstep(seaShore, seaShore.add(22.0), seaDist)).mul(0.18)
    );

    // 태양/달 글리터 길
    const viewDirSea = normalize(cameraPosition.sub(seaWorld));
    const reflected = reflect(u.uSunDir.negate().normalize(), vec3(0.0, 1.0, 0.0));
    const seaSpec = pow(max(dot(reflected, viewDirSea), 0.0), 14.0);
    const seaGlint = smoothstep(0.72, 1.0, seaRipple).mul(seaSpec).mul(2.6);
    seaColor = seaColor.add(u.uSunColor.mul(seaSpec.mul(0.09).add(seaGlint)));

    return vec4(mix(seaColor, u.uFoamColor, seaFoam.mul(0.86)), 1.0);
  })();

  material.uniforms = uniforms;
  return material;
}

export function createWebGpuPointCloud(three, tsl, {
  positions,
  colors = null,
  count,
  size = 1,
  map = null,
  color: colorHex = 0xffffff,
  opacity = 1,
  additive = false,
  dynamic = false,
  fog = false,
} = {}) {
  const sizes = new Float32Array(count).fill(size);
  // 빌보드 fragmentNode가 인스턴스 alpha(vAlpha)를 곱하므로 전역 투명도를 배열로 주입한다.
  const alphas = new Float32Array(count).fill(opacity);
  const cloud = createBillboardCloud(three, {
    count,
    positions,
    sizes,
    colors,
    alphas,
    map,
    baseColor: colorHex,
    additive,
    dynamic,
  });
  // 갱신 코드 호환용 별칭(같은 속성 객체를 두 이름으로 노출)
  cloud.geometry.attributes.position = cloud.attributes.position;
  if (colors) {
    cloud.geometry.attributes.color = cloud.attributes.color;
  }
  cloud.mesh.frustumCulled = false;
  if (fog) cloud.material.fog = true;
  cloud.material.opacity = opacity;
  return {
    mesh: cloud.mesh,
    material: cloud.material,
    geometry: cloud.geometry,
    attributes: cloud.attributes,
    uniforms: { uColor: null, uOpacity: null, uSize: cloud.attributes.size },
  };
}

/* ------------------------------------------------------------- 후처리 */

/**
 * EffectComposer(UnrealBloomPass + grade ShaderPass)를 TSL PostProcessing으로 대체.
 * grade 셰이더의 색수차·비네트·그레인·채도·틴트·대비를 그대로 이식한다.
 */
export function createWebGpuPost(renderer, scene, camera, tsl, {
  gradeUniforms,
  bloomUniforms,
} = {}) {
  const post = new RenderPipeline(renderer);
  const scenePass = pass(scene, camera);
  const sceneColor = scenePass.getTextureNode("output");

  // world.js grade ShaderPass 프래그먼트의 1:1 이식
  const grade = Fn(() => {
    const g = gradeUniforms;
    const uvNode = screenUV.toVar();
    const centered = uvNode.sub(0.5);
    const offset = centered.mul(g.uAberration).mul(dot(centered, centered));
    const r = texture(sceneColor, uvNode.add(offset)).r;
    const b = texture(sceneColor, uvNode.sub(offset)).b;
    const base = texture(sceneColor, uvNode);
    let col = vec3(r, base.g, b);
    // 대비(하단 0.2 클리프)
    col = col.sub(0.2).mul(g.uContrast).add(0.2).max(0.0);

    const luma = dot(col, vec3(0.2126, 0.7152, 0.0722));
    const shadowTint = vec3(0.93, 0.98, 1.09);
    const highTint = vec3(1.05, 1.0, 0.94);
    col = col.mul(mix(shadowTint, highTint, smoothstep(0.08, 0.85, luma)));
    col = mix(vec3(luma), col, g.uSaturation).mul(g.uTint);

    const vignette = float(1.0).sub(smoothstep(0.3, 0.92, length(centered).mul(1.24)));
    col = col.mul(mix(float(1.0), vignette, g.uVignette));

    const grainUv = uvNode.mul(vec2(1920.0, 1080.0)).add(g.uTime.mul(41.0));
    const grain = fract(sin(dot(grainUv, vec2(12.9898, 78.233))).mul(43758.5453));
    col = col.add(float(grain.sub(0.5)).mul(g.uGrain).mul(float(0.12).add(float(1.0).sub(luma).mul(0.5))));
    return col.max(0.0);
  })();

  const bloomNode = bloom(sceneColor, bloomUniforms.uBloomStrength,
    bloomUniforms.uBloomRadius, bloomUniforms.uBloomThreshold);
  // RenderPipeline이 톤매핑/색공간 변환을 자동 적용한다(outputColorTransform 기본값).
  post.outputNode = grade.add(bloomNode);

  return {
    post,
    render() {
      post.render();
    },
    setSize(width, height) {
      post.setSize(width, height);
    },
    dispose() {
      post.dispose();
    },
  };
}
