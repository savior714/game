// 태양계 장면의 WebGPU/TSL 머티리얼.
//
// shaders.js의 GLSL ShaderMaterial 6종을 TSL로 동일 수식 포팅했다.
// 모든 머티리얼은 기존 갱신 코드가 그대로 동작하도록 GLSL 쪽과 같은 키의
// `uniforms` 맵을 인스턴스에 붙여 돌려준다(TSL uniform 노드도 .value를 갖는다).
// 렌더러 출력 색공간/톤매핑은 RenderPipeline의 기본 outputColorTransform이 적용한다.

import { bloom } from "three/addons/tsl/display/BloomNode.js";

import * as WebGPU from "../vendor/three/build/three.webgpu.min.js";
import * as TSL from "./tsl.js";
import { fbm3 } from "./noise.js";

// r183부터 PostProcessing은 RenderPipeline으로 이름이 바뀌었다(구 이름은 경고만 남김).
const RenderPipeline = WebGPU.RenderPipeline;

const {
  Fn,
  If,
  Discard,
  uniform,
  attribute,
  uv,
  positionLocal,
  positionWorld,
  normalWorld,
  cameraPosition,
  modelWorldMatrix,
  texture,
  float,
  vec3,
  vec4,
  mix,
  smoothstep,
  normalize,
  length,
  cross,
  dot,
  pow,
  clamp,
  abs,
  sin,
  pass,
} = TSL;

function attachUniforms(material, uniforms) {
  material.uniforms = uniforms;
  return { material, uniforms };
}

/* ------------------------------------------------------------- 하늘 */

export function createSkyMaterial(three, map, { brightness = 1.15 } = {}) {
  const uBrightness = uniform(brightness);
  const material = new three.MeshBasicNodeMaterial({
    side: three.BackSide,
    depthWrite: false,
    colorNode: texture(map, uv()).rgb.mul(uBrightness),
  });
  return attachUniforms(material, { brightness: uBrightness });
}

/* ------------------------------------------------------------- 태양 */

export function createSunMaterial(three, map, { intensity = 1.12 } = {}) {
  const uTime = uniform(0);
  const uIntensity = uniform(intensity);

  const fragmentNode = Fn(() => {
    const p = positionLocal.normalize().mul(2.6);
    const slow = fbm3(
      p
        .mul(1.6)
        .add(vec3(uTime.mul(0.035), uTime.mul(0.02), uTime.mul(-0.03))),
    );
    const detail = fbm3(
      p
        .mul(4.4)
        .add(vec3(uTime.mul(-0.06), uTime.mul(0.05), uTime.mul(0.04))),
    );
    const heat = float(0.28).add(float(0.86).mul(slow)).add(float(0.34).mul(detail));

    // SDO 텍스처는 대비용으로만 섞고 발광색은 플라스마 팔레트가 만든다.
    const textureColor = texture(map, uv().add(vec2(uTime.mul(0.0022), 0))).rgb;
    const textureLuma = dot(textureColor, vec3(0.2126, 0.7152, 0.0722));
    const granulation = clamp(heat.mul(float(0.74).add(float(0.38).mul(textureLuma))), 0, 1);

    const cool = vec3(0.78, 0.13, 0.015);
    const warm = vec3(1.0, 0.42, 0.045);
    const hot = vec3(1.0, 0.74, 0.28);
    let color = mix(cool, warm, smoothstep(0.02, 0.58, granulation));
    color = mix(color, hot, smoothstep(0.86, 1.0, granulation));
    const hotBoost = pow(clamp(granulation.sub(0.45), 0, 1), 3.0).mul(0.75);
    color = color.add(vec3(1.0, 0.34, 0.03).mul(hotBoost));

    // 림(채층) 효과
    const viewDir = normalize(cameraPosition.sub(positionWorld));
    const limb = pow(clamp(float(1).sub(abs(dot(normalWorld, viewDir))), 0, 1), 2.4);
    color = color.mul(float(1).add(limb.mul(0.85)));
    color = color.add(vec3(1.0, 0.62, 0.16).mul(pow(limb, 3.0)).mul(0.6));

    return vec4(color.mul(uIntensity), 1.0);
  })();

  const material = new three.MeshBasicNodeMaterial({ fragmentNode });
  return attachUniforms(material, { uTime, uIntensity });
}

/* ------------------------------------------------------------- 지구 */

export function createEarthMaterial(three, maps) {
  const sunDirection = uniform(new three.Vector3(1, 0, 0));
  const nightIntensity = uniform(1.35);
  const specularStrength = uniform(0.32);

  const fragmentNode = Fn(() => {
    const geometricNormal = normalWorld;
    const tangent = modelWorldMatrix
      .mul(vec4(attribute("tangent", "vec4").xyz, 0))
      .xyz.normalize();
    const bitangent = cross(geometricNormal, tangent)
      .mul(attribute("tangent", "vec4").w)
      .normalize();

    const sampledNormal = texture(maps.normal, uv()).xyz.mul(2).sub(1);
    const mappedNormal = vec3(
      sampledNormal.x.mul(0.8),
      sampledNormal.y.mul(0.8),
      sampledNormal.z,
    );
    const normal = normalize(
      tangent
        .mul(mappedNormal.x)
        .add(bitangent.mul(mappedNormal.y))
        .add(geometricNormal.mul(mappedNormal.z)),
    );

    const lightDir = normalize(sunDirection);
    const viewDir = normalize(cameraPosition.sub(positionWorld));

    const geometricLambert = clamp(dot(geometricNormal, lightDir), 0, 1);
    const lambert = clamp(dot(normal, lightDir), 0, 1);
    const dayLight = smoothstep(-0.08, 0.3, geometricLambert);

    const dayColor = texture(maps.day, uv()).rgb;
    const specularMask = texture(maps.specular, uv()).rgb;
    const ocean = smoothstep(0.18, 0.72, specularMask.r);

    const halfVector = normalize(lightDir.add(viewDir));
    const specular = pow(clamp(dot(normal, halfVector), 0, 1), 120)
      .mul(ocean)
      .mul(specularStrength);

    let color = dayColor.mul(float(0.045).add(float(1.22).mul(lambert)));
    color = color.add(vec3(1.0, 0.95, 0.84).mul(specular).mul(dayLight));

    const cityLights = texture(maps.night, uv()).rgb;
    const nightMix = float(1).sub(smoothstep(-0.04, 0.22, geometricLambert));
    color = color.add(cityLights.mul(nightIntensity).mul(nightMix));
    color = color.add(dayColor.mul(0.012));

    return vec4(color, 1.0);
  })();

  const material = new three.MeshBasicNodeMaterial({ fragmentNode });
  return attachUniforms(material, { sunDirection, nightIntensity, specularStrength });
}

/* ------------------------------------------------------------- 구름 */

export function createCloudMaterial(three, map, { opacity = 1 } = {}) {
  const cloudMap = map;
  const sunDirection = uniform(new three.Vector3(1, 0, 0));
  const uOpacity = uniform(opacity);

  const fragmentNode = Fn(() => {
    const cloud = texture(cloudMap, uv());
    const alpha = cloud.a.mul(uOpacity);
    If(alpha.lessThan(0.008), () => {
      Discard();
    });

    const lightDir = normalize(sunDirection);
    const lambert = clamp(dot(normalWorld, lightDir), 0, 1);
    const terminator = smoothstep(-0.06, 0.28, dot(normalWorld, lightDir));

    const dayColor = vec3(0.94, 0.96, 1.0).mul(float(0.05).add(float(0.92).mul(lambert)));
    const nightColor = vec3(0.02, 0.035, 0.06);
    const color = mix(nightColor, dayColor, terminator);

    return vec4(color, alpha.mul(float(0.35).add(float(0.65).mul(terminator))));
  })();

  const material = new three.MeshBasicNodeMaterial({
    fragmentNode,
    transparent: true,
    depthWrite: false,
  });
  return attachUniforms(material, { sunDirection, opacity: uOpacity });
}

/* ------------------------------------------------------------- 대기 */

export function createAtmosphereMaterial(three, color, {
  strength = 1,
  planetRadius = 1,
} = {}) {
  const glowColor = uniform(new three.Color(color));
  const sunDirection = uniform(new three.Vector3(1, 0, 0));
  const planetCenter = uniform(new three.Vector3());
  const uStrength = uniform(strength);
  const uPlanetRadius = uniform(planetRadius);

  const fragmentNode = Fn(() => {
    const viewDir = normalize(cameraPosition.sub(positionWorld));
    const fresnel = pow(clamp(float(1).sub(dot(normalWorld, viewDir)), 0, 1), 3.0);

    const cameraToCenter = planetCenter.sub(cameraPosition);
    const rayDirection = normalize(positionWorld.sub(cameraPosition));
    const impact = length(cross(cameraToCenter, rayDirection));
    const outsidePlanet = smoothstep(
      uPlanetRadius.mul(0.995),
      uPlanetRadius.mul(1.02),
      impact,
    );

    const sunFacing = clamp(
      dot(normalWorld, normalize(sunDirection)).mul(0.75).add(0.35),
      0,
      1,
    );

    const color = glowColor
      .mul(fresnel)
      .mul(uStrength)
      .mul(sunFacing)
      .mul(outsidePlanet);
    return vec4(color, 1.0);
  })();

  const material = new three.MeshBasicNodeMaterial({
    fragmentNode,
    transparent: true,
    depthWrite: false,
    blending: three.AdditiveBlending,
    side: three.FrontSide,
  });
  return attachUniforms(material, {
    glowColor,
    sunDirection,
    planetCenter,
    strength: uStrength,
    planetRadius: uPlanetRadius,
  });
}

/* ------------------------------------------------------------- 고리 */

export function createRingMaterial(three, map, { opacity = 0.95, planetRadius = 1 } = {}) {
  const sunDirection = uniform(new three.Vector3(1, 0, 0));
  const planetWorldPosition = uniform(new three.Vector3());
  const uPlanetRadius = uniform(planetRadius);
  const ringOpacity = uniform(opacity);

  const fragmentNode = Fn(() => {
    const ring = texture(map, vec2(uv().x, 0.5));
    If(ring.a.lessThan(0.01), () => {
      Discard();
    });

    const toSun = normalize(sunDirection);
    const relative = positionWorld.sub(planetWorldPosition);
    const alongSun = dot(relative, toSun);
    const closest = relative.sub(toSun.mul(alongSun));
    const distanceToAxis = length(closest);
    const shadowValue = TSL.select(
      alongSun.lessThan(0),
      smoothstep(uPlanetRadius.mul(0.92), uPlanetRadius.mul(1.12), distanceToAxis),
      float(1),
    );

    const brightness = float(0.42).add(float(0.58).mul(shadowValue));
    const color = ring.rgb.mul(brightness);
    return vec4(
      color,
      ring.a
        .mul(ringOpacity)
        .mul(float(0.55).add(float(0.45).mul(shadowValue))),
    );
  })();

  const material = new three.MeshBasicNodeMaterial({
    fragmentNode,
    transparent: true,
    depthWrite: false,
    side: three.DoubleSide,
  });
  return attachUniforms(material, {
    sunDirection,
    planetWorldPosition,
    planetRadius: uPlanetRadius,
    ringOpacity,
  });
}

/* ------------------------------------------------------------- 후처리 */

/**
 * WebGPU용 블룸 후처리. UnrealBloomPass(0.52, 0.48, 0.86)를 TSL BloomNode로 대체한다.
 */
export function createSolarPostProcessing(renderer, scene, camera, {
  strength = 0.52,
  radius = 0.4,
  threshold = 0.86,
} = {}) {
  const post = new RenderPipeline(renderer);
  const scenePass = pass(scene, camera);
  const sceneColor = scenePass.getTextureNode("output");
  const bloomNode = bloom(sceneColor, strength, radius, threshold);

  let bloomEnabled = true;
  // RenderPipeline이 톤매핑/색공간 변환을 자동 적용한다(outputColorTransform 기본값).
  post.outputNode = sceneColor.add(bloomNode);

  return {
    post,
    render() {
      post.render();
    },
    setBloomEnabled(enabled) {
      bloomEnabled = enabled;
      post.outputNode = enabled
        ? sceneColor.add(bloomNode)
        : sceneColor;
    },
    isBloomEnabled: () => bloomEnabled,
    setSize(width, height) {
      post.setSize(width, height);
    },
    dispose() {
      post.dispose();
    },
  };
}
