// WebGPU/TSL 번들 shim.
//
// three.js 0.185의 WebGPU 빌드는 TSL 함수를 `TSL` 네임스페이스로 export하고,
// `three.tsl.min.js`는 bare specifier "three/webgpu"를 import한다. dino-escape
// 페이지에는 import map이 없고(계약 테스트가 금지) 상대 경로 import만 허용되므로,
// 모든 페이지가 import map 없이 동일한 상대 경로로 TSL을 쓸 수 있게 이 shim을 둔다.
// 벤더의 minified 파일은 수정하지 않고 이 모듈에서 named member로만 다시 내보낸다.

import * as webgpuBundle from "../vendor/three/build/three.webgpu.min.js";

export default webgpuBundle;

// WebGPURenderer, PostProcessing, *NodeMaterial 클래스 등 최상위 export 전체.
export * from "../vendor/three/build/three.webgpu.min.js";

const { TSL } = webgpuBundle;

// 아래 이름들은 빌드 버전에 실제로 존재하는 멤버만 구조 분해한다.
// three.js 업그렝드 후 이름이 바뀌면 이 모듈을 로드하는 순간 즉시 에러가 난다.
export const {
  // 셰이더 작성
  Fn,
  nodeObject,
  uniform,
  attribute,
  varyingProperty,
  // 기하 입력
  positionLocal,
  positionWorld,
  normalLocal,
  normalWorld,
  normalView,
  positionView,
  positionViewDirection,
  cameraPosition,
  cameraWorldMatrix,
  cameraViewMatrix,
  cameraProjectionMatrix,
  modelViewMatrix,
  modelViewProjection,
  modelWorldMatrix,
  uv,
  pointUV,
  pointWidth,
  screenUV,
  faceDirection,
  vertexIndex,
  instanceIndex,
  // 텍스처
  texture,
  textureLoad,
  textureSize,
  maxMipLevel,
  // 스칼라/벡터 생성
  float,
  int,
  uint,
  bool,
  vec2,
  vec3,
  vec4,
  mat3,
  mat4,
  // 산술
  add,
  sub,
  mul,
  div,
  negate,
  oneMinus,
  abs,
  sign,
  floor,
  ceil,
  round,
  trunc,
  fract,
  mod,
  min,
  max,
  clamp,
  saturate,
  mix,
  select,
  equal,
  notEqual,
  smoothstep,
  step,
  sqrt,
  inversesqrt,
  pow,
  pow2,
  exp,
  exp2,
  log,
  log2,
  sin,
  cos,
  tan,
  atan,
  radians,
  degrees,
  cross,
  dot,
  length,
  distance,
  normalize,
  reflect,
  refract,
  // 분기/반복
  If,
  Loop,
  Continue,
  Break,
  Return,
  Discard,
  Const,
  Var,
  // 색/색공간
  color,
  luminance,
  convertColorSpace,
  workingToColorSpace,
  colorSpaceToWorking,
  // 후처리
  pass,
  passTexture,
  output,
  mrt,
  blur,
  // 노이즈
  mx_noise_float,
  mx_noise_vec3,
  mx_fractal_noise_float,
  mx_fractal_noise_vec3,
  mx_cell_noise_float,
  mx_worley_noise_float,
  triNoise3D,
  hash,
  interleavedGradientNoise,
  // 시간/빌보드
  time,
  billboarding,
  instancedMesh,
  element,
  storage,
} = TSL;
