// 태양계 3D 탐험대 — 셰이더와 머티리얼
// 모든 커스텀 셰이더는 선형(linear) HDR 색을 출력하고,
// 마지막에 tonemapping/colorspace 청크를 붙여 컴포저 유무와 관계없이 색이 일치한다.

import * as THREE from "three";

const TONE_FOOTER = `
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
`;

export const EARTH_VERTEX = /* glsl */ `
  attribute vec4 tangent;

  varying vec2 vUv;
  varying vec3 vWorldPosition;
  varying vec3 vWorldNormal;
  varying vec3 vWorldTangent;
  varying vec3 vWorldBitangent;

  void main() {
    vUv = uv;
    vec3 worldNormal = normalize(mat3(modelMatrix) * normal);
    vec3 worldTangent = normalize(mat3(modelMatrix) * tangent.xyz);
    vWorldNormal = worldNormal;
    vWorldTangent = worldTangent;
    vWorldBitangent = normalize(cross(worldNormal, worldTangent) * tangent.w);

    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vWorldPosition = worldPosition.xyz;
    gl_Position = projectionMatrix * viewMatrix * worldPosition;
  }
`;

export const EARTH_FRAGMENT = /* glsl */ `
  uniform sampler2D dayMap;
  uniform sampler2D nightMap;
  uniform sampler2D normalMap;
  uniform sampler2D specularMap;
  uniform vec3 sunDirection;
  uniform float nightIntensity;
  uniform float specularStrength;

  varying vec2 vUv;
  varying vec3 vWorldPosition;
  varying vec3 vWorldNormal;
  varying vec3 vWorldTangent;
  varying vec3 vWorldBitangent;

  void main() {
    vec3 geometricNormal = normalize(vWorldNormal);
    vec3 tangent = normalize(vWorldTangent);
    vec3 bitangent = normalize(vWorldBitangent);

    vec3 sampledNormal = texture2D(normalMap, vUv).xyz * 2.0 - 1.0;
    sampledNormal.xy *= 0.8;
    vec3 normal = normalize(tangent * sampledNormal.x + bitangent * sampledNormal.y + geometricNormal * sampledNormal.z);

    vec3 lightDir = normalize(sunDirection);
    vec3 viewDir = normalize(cameraPosition - vWorldPosition);

    float geometricLambert = max(dot(geometricNormal, lightDir), 0.0);
    float lambert = max(dot(normal, lightDir), 0.0);
    float dayLight = smoothstep(-0.08, 0.3, geometricLambert);

    vec3 dayColor = texture2D(dayMap, vUv).rgb;
    vec3 specularMask = texture2D(specularMap, vUv).rgb;
    float ocean = smoothstep(0.18, 0.72, specularMask.r);

    vec3 halfVector = normalize(lightDir + viewDir);
    float specular = pow(max(dot(normal, halfVector), 0.0), 120.0) * ocean * specularStrength;

    vec3 color = dayColor * (0.045 + 1.22 * lambert);
    color += vec3(1.0, 0.95, 0.84) * specular * dayLight;

    // 밤 쪽 도시 불빛. 지구 대기 산란으로 살짝 번지게 한다.
    vec3 cityLights = texture2D(nightMap, vUv).rgb;
    float nightMix = 1.0 - smoothstep(-0.04, 0.22, geometricLambert);
    color += cityLights * nightIntensity * nightMix;
    color += dayColor * 0.012;

    gl_FragColor = vec4(color, 1.0);
    ${TONE_FOOTER}
  }
`;

export const ATMOSPHERE_VERTEX = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vWorldPosition;
  varying vec3 vWorldNormal;

  void main() {
    vUv = uv;
    vec3 worldNormal = normalize(mat3(modelMatrix) * normal);
    vWorldNormal = worldNormal;
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vWorldPosition = worldPosition.xyz;
    gl_Position = projectionMatrix * viewMatrix * worldPosition;
  }
`;

export const ATMOSPHERE_FRAGMENT = /* glsl */ `
  uniform vec3 glowColor;
  uniform vec3 sunDirection;
  uniform vec3 planetCenter;
  uniform float strength;
  uniform float planetRadius;

  varying vec2 vUv;
  varying vec3 vWorldPosition;
  varying vec3 vWorldNormal;

  void main() {
    vec3 normal = normalize(vWorldNormal);
    vec3 viewDir = normalize(cameraPosition - vWorldPosition);

    // 프레넬: 화면 가장자리에서만 밝아진다.
    float fresnel = pow(clamp(1.0 - dot(normal, viewDir), 0.0, 1.0), 3.0);

    // 카메라 광선이 행성 본체와 겹치면(원판 안쪽) 그 조각은 그리지 않는다.
    vec3 cameraToCenter = planetCenter - cameraPosition;
    vec3 rayDirection = normalize(vWorldPosition - cameraPosition);
    float impact = length(cross(cameraToCenter, rayDirection));
    float outsidePlanet = smoothstep(planetRadius * 0.995, planetRadius * 1.02, impact);

    // 태양을 바라보는 쪽이 밝고, 밤 쪽은 거의 사라진다.
    float sunFacing = clamp(dot(normal, normalize(sunDirection)) * 0.75 + 0.35, 0.0, 1.0);

    vec3 color = glowColor * fresnel * strength * sunFacing * outsidePlanet;
    gl_FragColor = vec4(color, 1.0);
    ${TONE_FOOTER}
  }
`;

export const CLOUD_VERTEX = ATMOSPHERE_VERTEX;

export const CLOUD_FRAGMENT = /* glsl */ `
  uniform sampler2D cloudMap;
  uniform vec3 sunDirection;
  uniform float opacity;

  varying vec2 vUv;
  varying vec3 vWorldPosition;
  varying vec3 vWorldNormal;

  void main() {
    vec4 cloud = texture2D(cloudMap, vUv);
    float alpha = cloud.a * opacity;
    if (alpha < 0.008) discard;

    vec3 normal = normalize(vWorldNormal);
    vec3 lightDir = normalize(sunDirection);
    float lambert = max(dot(normal, lightDir), 0.0);
    float terminator = smoothstep(-0.06, 0.28, dot(normal, lightDir));

    vec3 dayColor = vec3(0.94, 0.96, 1.0) * (0.05 + 0.92 * lambert);
    vec3 nightColor = vec3(0.02, 0.035, 0.06);
    vec3 color = mix(nightColor, dayColor, terminator);

    gl_FragColor = vec4(color, alpha * (0.35 + 0.65 * terminator));
    ${TONE_FOOTER}
  }
`;

export const SUN_VERTEX = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vObjectPosition;
  varying vec3 vWorldNormal;
  varying vec3 vWorldPosition;

  void main() {
    vUv = uv;
    vObjectPosition = position;
    vWorldNormal = normalize(mat3(modelMatrix) * normal);
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vWorldPosition = worldPosition.xyz;
    gl_Position = projectionMatrix * viewMatrix * worldPosition;
  }
`;

export const SUN_FRAGMENT = /* glsl */ `
  uniform sampler2D sunMap;
  uniform float uTime;
  uniform float uIntensity;

  varying vec2 vUv;
  varying vec3 vObjectPosition;
  varying vec3 vWorldNormal;
  varying vec3 vWorldPosition;

  float hash(vec3 p) {
    p = fract(p * 0.3183099 + vec3(0.1, 0.2, 0.3));
    p *= 17.0;
    return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
  }

  float valueNoise(vec3 p) {
    vec3 cell = floor(p);
    vec3 local = fract(p);
    local = local * local * (3.0 - 2.0 * local);

    float n000 = hash(cell + vec3(0.0, 0.0, 0.0));
    float n100 = hash(cell + vec3(1.0, 0.0, 0.0));
    float n010 = hash(cell + vec3(0.0, 1.0, 0.0));
    float n110 = hash(cell + vec3(1.0, 1.0, 0.0));
    float n001 = hash(cell + vec3(0.0, 0.0, 1.0));
    float n101 = hash(cell + vec3(1.0, 0.0, 1.0));
    float n011 = hash(cell + vec3(0.0, 1.0, 1.0));
    float n111 = hash(cell + vec3(1.0, 1.0, 1.0));

    float nx00 = mix(n000, n100, local.x);
    float nx10 = mix(n010, n110, local.x);
    float nx01 = mix(n001, n101, local.x);
    float nx11 = mix(n011, n111, local.x);
    float nxy0 = mix(nx00, nx10, local.y);
    float nxy1 = mix(nx01, nx11, local.y);
    return mix(nxy0, nxy1, local.z);
  }

  float fbm(vec3 p) {
    float value = 0.0;
    float amplitude = 0.55;
    for (int i = 0; i < 4; i++) {
      value += amplitude * valueNoise(p);
      p *= 2.03;
      amplitude *= 0.5;
    }
    return value;
  }

  void main() {
    vec3 p = normalize(vObjectPosition) * 2.6;
    float slow = fbm(p * 1.6 + vec3(uTime * 0.035, uTime * 0.02, -uTime * 0.03));
    float detail = fbm(p * 4.4 + vec3(-uTime * 0.06, uTime * 0.05, uTime * 0.04));
    float heat = 0.28 + 0.86 * slow + 0.34 * detail;

    // SDO 원본은 이미 채도가 높아 그대로 더하면 흰색으로 포화된다.
    // 텍스처는 대비용으로만 섞고, 실제 발광색은 플라스마 팔레트가 만든다.
    vec3 textureColor = texture2D(sunMap, vUv + vec2(uTime * 0.0022, 0.0)).rgb;
    float textureLuma = dot(textureColor, vec3(0.2126, 0.7152, 0.0722));

    float granulation = clamp(heat * (0.74 + 0.38 * textureLuma), 0.0, 1.0);
    // 대부분의 표면을 주황으로 두고, 아주 뜨거운 알갱이만 노랑으로 올린다.
    vec3 cool = vec3(0.78, 0.13, 0.015);
    vec3 warm = vec3(1.0, 0.42, 0.045);
    vec3 hot = vec3(1.0, 0.74, 0.28);
    vec3 color = mix(cool, warm, smoothstep(0.02, 0.58, granulation));
    color = mix(color, hot, smoothstep(0.86, 1.0, granulation));
    color += vec3(1.0, 0.34, 0.03) * pow(clamp(granulation - 0.45, 0.0, 1.0), 3.0) * 0.75;

    // 가장자리로 갈수록 밝아지는 림(채층) 효과. 원판 안쪽은 주황, 테두리는 노랑.
    float limb = pow(clamp(1.0 - abs(dot(normalize(vWorldNormal), normalize(cameraPosition - vWorldPosition))), 0.0, 1.0), 2.4);
    color *= 1.0 + limb * 0.85;
    color += vec3(1.0, 0.62, 0.16) * pow(limb, 3.0) * 0.6;

    gl_FragColor = vec4(color * uIntensity, 1.0);
    ${TONE_FOOTER}
  }
`;

export const RING_VERTEX = /* glsl */ `
  varying vec2 vUv;
  varying vec3 vWorldPosition;

  void main() {
    vUv = uv;
    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    vWorldPosition = worldPosition.xyz;
    gl_Position = projectionMatrix * viewMatrix * worldPosition;
  }
`;

export const RING_FRAGMENT = /* glsl */ `
  uniform sampler2D ringMap;
  uniform vec3 sunDirection;
  uniform vec3 planetWorldPosition;
  uniform float planetRadius;
  uniform float ringOpacity;

  varying vec2 vUv;
  varying vec3 vWorldPosition;

  void main() {
    vec4 ring = texture2D(ringMap, vec2(vUv.x, 0.5));
    if (ring.a < 0.01) discard;

    vec3 toSun = normalize(sunDirection);
    vec3 relative = vWorldPosition - planetWorldPosition;
    float alongSun = dot(relative, toSun);
    vec3 closest = relative - toSun * alongSun;
    float distanceToAxis = length(closest);
    float shadow = 1.0;
    if (alongSun < 0.0) {
      shadow = smoothstep(planetRadius * 0.92, planetRadius * 1.12, distanceToAxis);
    }

    float brightness = 0.42 + 0.58 * shadow;
    vec3 color = ring.rgb * brightness;
    gl_FragColor = vec4(color, ring.a * ringOpacity * (0.55 + 0.45 * shadow));
    ${TONE_FOOTER}
  }
`;

export const SKY_VERTEX = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

export const SKY_FRAGMENT = /* glsl */ `
  uniform sampler2D skyMap;
  uniform float brightness;
  varying vec2 vUv;

  void main() {
    vec3 color = texture2D(skyMap, vUv).rgb;
    color *= brightness;
    gl_FragColor = vec4(color, 1.0);
    ${TONE_FOOTER}
  }
`;

export function createEarthMaterial(maps) {
  return new THREE.ShaderMaterial({
    uniforms: {
      dayMap: { value: maps.day },
      nightMap: { value: maps.night },
      normalMap: { value: maps.normal },
      specularMap: { value: maps.specular },
      sunDirection: { value: new THREE.Vector3(1, 0, 0) },
      nightIntensity: { value: 1.35 },
      specularStrength: { value: 0.32 },
    },
    vertexShader: EARTH_VERTEX,
    fragmentShader: EARTH_FRAGMENT,
  });
}

export function createCloudMaterial(map, { opacity = 1 } = {}) {
  return new THREE.ShaderMaterial({
    uniforms: {
      cloudMap: { value: map },
      sunDirection: { value: new THREE.Vector3(1, 0, 0) },
      opacity: { value: opacity },
    },
    vertexShader: CLOUD_VERTEX,
    fragmentShader: CLOUD_FRAGMENT,
    transparent: true,
    depthWrite: false,
  });
}

export function createAtmosphereMaterial(color, { strength = 1, planetRadius = 1 } = {}) {
  return new THREE.ShaderMaterial({
    uniforms: {
      glowColor: { value: new THREE.Color(color) },
      sunDirection: { value: new THREE.Vector3(1, 0, 0) },
      planetCenter: { value: new THREE.Vector3() },
      strength: { value: strength },
      planetRadius: { value: planetRadius },
    },
    vertexShader: ATMOSPHERE_VERTEX,
    fragmentShader: ATMOSPHERE_FRAGMENT,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.FrontSide,
  });
}

export function createSunMaterial(map, { intensity = 1.12 } = {}) {
  return new THREE.ShaderMaterial({
    uniforms: {
      sunMap: { value: map },
      uTime: { value: 0 },
      uIntensity: { value: intensity },
    },
    vertexShader: SUN_VERTEX,
    fragmentShader: SUN_FRAGMENT,
  });
}

export function createRingMaterial(map, { opacity = 0.95, planetRadius = 1 } = {}) {
  return new THREE.ShaderMaterial({
    uniforms: {
      ringMap: { value: map },
      sunDirection: { value: new THREE.Vector3(1, 0, 0) },
      planetWorldPosition: { value: new THREE.Vector3() },
      planetRadius: { value: planetRadius },
      ringOpacity: { value: opacity },
    },
    vertexShader: RING_VERTEX,
    fragmentShader: RING_FRAGMENT,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
}

export function createSkyMaterial(map, { brightness = 1.15 } = {}) {
  return new THREE.ShaderMaterial({
    uniforms: {
      skyMap: { value: map },
      brightness: { value: brightness },
    },
    vertexShader: SKY_VERTEX,
    fragmentShader: SKY_FRAGMENT,
    side: THREE.BackSide,
    depthWrite: false,
  });
}

/** 원형 glow 텍스처를 캔버스로 만든다 (태양 후광, 별 반짝임 등). */
export function createGlowTexture(innerColor = "rgba(255,246,200,1)", midColor = "rgba(255,180,60,0.55)", size = 256) {
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gradient.addColorStop(0, innerColor);
  gradient.addColorStop(0.28, midColor);
  gradient.addColorStop(1, "rgba(255,120,0,0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}
