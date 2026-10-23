// WebGPU용 인스턴스 빌보드 스프라이트.
//
// 배경: WebGPU의 point 프리미티브는 1픽셀 고정 크기라 gl_PointSize 기반의
// 별/꽃가루/불꽃 놀이를 그릴 수 없다(three.js PointUVNode 문서 참고).
// 대신 1x1 PlaneGeometry를 InstancedMesh로 복제하고, TSL billboarding()으로
// 항상 카메라를 향하게 만들어 감쇠(sizeAttenuation) 효과를 월드 크기로 재현한다.
// 인스턴스 속성은 InstancedBufferAttribute라서 WebGPU 쪽에서 인스턴스 스텝으로
// 샘플링되고, WebGL 빌드에서도 동일한 지오메트리를 그대로 쓸 수 있다.

import * as TSL from "./tsl.js";

const {
  Fn,
  attribute,
  varyingProperty,
  positionLocal,
  uv,
  billboarding,
  texture,
  vec4,
  vec3,
  float,
  mix,
  smoothstep,
  length,
  saturate,
} = TSL;

/**
 * @param {object} three WebGPU 번들 네임스페이스
 * @param {object} options
 * @param {number} options.count 최대 인스턴스 수
 * @param {Float32Array} options.positions [x,y,z] * count
 * @param {Float32Array} options.sizes 월드 단위 크기(지름) * count
 * @param {Float32Array} [options.colors] [r,g,b] * count
 * @param {Float32Array} [options.alphas] alpha * count
 * @param {Float32Array} [options.phases] 트윙클 위상 * count
 * @param {object} [options.map] THREE.Texture(없으면 원형 마스크)
 * @param {number} [options.baseColor] colors가 없을 때 기본 색
 * @param {boolean} [options.additive]
 * @param {boolean} [options.dynamic] 매 프레임 갱신 여부
 * @param {Function} [options.twinkleNode] (phaseNode, timeNode) => alpha multiplier node
 * @param {Function} [options.timeNode] 시간 노드(기본 TSL time)
 * @param {Function} [options.transformPosition] (instancePositionNode) => world position node.
 *   billboarding은 메시 회전을 무효화하므로 구름 전체 회전이 필요하면 여기서 직접 돌린다.
 */
export function createBillboardCloud(three, options) {
  const {
    count,
    positions,
    sizes,
    colors = null,
    alphas = null,
    phases = null,
    map = null,
    baseColor = 0xffffff,
    additive = false,
    dynamic = false,
    twinkleNode = null,
    timeNode = TSL.time,
    transformPosition = null,
  } = options;

  const geometry = new three.PlaneGeometry(1, 1);
  const usage = dynamic ? three.DynamicDrawUsage : three.StaticDrawUsage;

  const positionAttr = new three.InstancedBufferAttribute(positions, 3);
  const sizeAttr = new three.InstancedBufferAttribute(sizes, 1);
  positionAttr.usage = usage;
  sizeAttr.usage = usage;
  geometry.setAttribute("aCloudPosition", positionAttr);
  geometry.setAttribute("aCloudSize", sizeAttr);

  if (colors) {
    const colorAttr = new three.InstancedBufferAttribute(colors, 3);
    colorAttr.usage = usage;
    geometry.setAttribute("aCloudColor", colorAttr);
  }
  if (alphas) {
    const alphaAttr = new three.InstancedBufferAttribute(alphas, 1);
    alphaAttr.usage = usage;
    geometry.setAttribute("aCloudAlpha", alphaAttr);
  }
  if (phases) {
    geometry.setAttribute(
      "aCloudPhase",
      new three.InstancedBufferAttribute(phases, 1),
    );
  }

  const instancePosition = attribute("aCloudPosition", "vec3");
  const instanceSize = attribute("aCloudSize", "float");

  // 커스텀 fragmentNode를 끼우는 호출자가 같은 varying 인스턴스를 재사용하도록 노출한다.
  const vColor = varyingProperty("vec3", "vCloudColor");
  const vAlpha = varyingProperty("float", "vCloudAlpha");
  const vLocalUv = varyingProperty("vec2", "vCloudUv");
  const varyings = { vColor, vAlpha, vLocalUv };

  const vertexNode = Fn(() => {
    if (colors) {
      vColor.assign(attribute("aCloudColor", "vec3"));
    } else {
      vColor.assign(new three.Color(baseColor));
    }
    let alpha = alphas ? attribute("aCloudAlpha", "float") : float(1.0);
    if (phases && twinkleNode) {
      alpha = alpha.mul(twinkleNode(attribute("aCloudPhase", "float"), timeNode));
    }
    vAlpha.assign(alpha);
    vLocalUv.assign(uv());
    // positionLocal은 1x1 평면의 [-0.5, 0.5] 로컬 좌표. 크기만큼 곱해 인스턴스
    // 중심으로 옮긴 월드 좌표를 billboarding에 넘겨 회전을 제거한다.
    const worldCenter = transformPosition
      ? transformPosition(instancePosition)
      : instancePosition;
    const corner = positionLocal.mul(instanceSize);
    return billboarding({ position: worldCenter.add(corner) });
  })();

  const fragmentNode = Fn(() => {
    const localUv = vLocalUv;
    let mask;
    if (map) {
      const sampled = texture(map, localUv);
      mask = sampled.a;
      const tinted = colors ? vColor : vColor;
      return vec4(tinted.mul(sampled.rgb), vAlpha.mul(mask));
    }
    const radial = length(localUv.sub(float(0.5)));
    mask = smoothstep(float(0.5), float(0.08), radial);
    let rgb = vColor;
    if (additive) {
      // 가산 블렌딩에서는 검은 배경이 더해지지 않도록 색에 마스크를 미리 태운다.
      rgb = rgb.mul(mask);
      return vec4(rgb, vAlpha);
    }
    return vec4(rgb, vAlpha.mul(mask));
  })();

  const material = new three.MeshBasicNodeMaterial({
    vertexNode,
    fragmentNode,
    transparent: true,
    depthWrite: false,
    side: three.DoubleSide,
    blending: additive ? three.AdditiveBlending : three.NormalBlending,
  });

  const mesh = new three.InstancedMesh(geometry, material, count);
  mesh.frustumCulled = false;
  // 인스턴스 행렬은 사용하지 않고 인스턴스 속성만 사용하므로 단위행렬로 고정.
  const dummy = new three.Object3D();
  for (let i = 0; i < count; i += 1) {
    dummy.updateMatrix();
    mesh.setMatrixAt(i, dummy.matrix);
  }
  mesh.instanceMatrix.needsUpdate = true;

  return {
    mesh,
    geometry,
    material,
    varyings,
    attributes: {
      position: positionAttr,
      size: sizeAttr,
      color: geometry.getAttribute("aCloudColor") ?? null,
      alpha: geometry.getAttribute("aCloudAlpha") ?? null,
      phase: geometry.getAttribute("aCloudPhase") ?? null,
    },
  };
}

/** 부드러운 원형 알파 마스크를 별도 색 변화 없이 만들 때 쓴다. */
export function softCircleAlpha(uvNode) {
  const radial = length(uvNode.sub(float(0.5)));
  return smoothstep(float(0.5), float(0.1), radial);
}

export { saturate, mix };
