// GLSL 셰이더들의 커스텀 노이즈를 TSL로 1:1 포팅한 공용 모듈.
// three.js 내장 mx_* 노이즈와 출력이 다르기 때문에(화면 룩이 바뀌므로)
// 기존 ShaderMaterial의 hash/valueNoise/fbm 수식을 그대로 옮겨 왔다.

import {
  Fn,
  float,
  vec2,
  vec3,
  fract,
  floor,
  sin,
  cos,
  dot,
  mix,
  Var,
  Loop,
  abs,
} from "./tsl.js";

// GLSL: fract(sin(dot(p, vec2(127.1,311.7))) * 43758.5453)
export const hash21 = Fn(([p]) => fract(sin(dot(p, vec2(127.1, 311.7))).mul(43758.5453123)));

// electricity sky가 쓰는 변형 해시: p = fract(p*vec2(123.34,456.21)); p += dot(p,p+45.32); fract(p.x*p.y)
export const hash21Alt = Fn(([p]) => {
  const q = Var(fract(p.mul(vec2(123.34, 456.21))));
  q.addAssign(dot(q, q.add(45.32)));
  return fract(q.x.mul(q.y));
});

// sun 셰이더의 3D 해시
export const hash3 = Fn(([p]) => {
  const q = Var(fract(p.mul(0.3183099).add(vec3(0.1, 0.2, 0.3))));
  q.assign(q.mul(17.0));
  return fract(q.x.mul(q.y).mul(q.z).mul(q.x.add(q.y).add(q.z)));
});

function smooth(t) {
  return t.mul(t).mul(float(3).sub(t.mul(2)));
}

// dino sky GLSL의 noise()와 동일: hash21 기반 표식 value noise
export const valueNoise2DStandard = Fn(([p]) => {
  const i = Var(floor(p));
  const f = Var(fract(p));
  f.assign(smooth(f));

  const a = hash21(i);
  const b = hash21(i.add(vec2(1.0, 0.0)));
  const c = hash21(i.add(vec2(0.0, 1.0)));
  const d = hash21(i.add(vec2(1.0, 1.0)));

  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
});

// 2D value noise (electricity sky — 변형 해시 버전)
export const valueNoise2D = Fn(([p]) => {
  const i = Var(floor(p));
  const f = Var(fract(p));
  f.assign(smooth(f));

  const a = hash21Alt(i);
  const b = hash21Alt(i.add(vec2(1.0, 0.0)));
  const c = hash21Alt(i.add(vec2(0.0, 1.0)));
  const d = hash21Alt(i.add(vec2(1.0, 1.0)));

  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
});

// 3D value noise (sun plasma)
export const valueNoise3D = Fn(([p]) => {
  const cell = Var(floor(p));
  const local = Var(smooth(fract(p)));

  const n000 = hash3(cell);
  const n100 = hash3(cell.add(vec3(1.0, 0.0, 0.0)));
  const n010 = hash3(cell.add(vec3(0.0, 1.0, 0.0)));
  const n110 = hash3(cell.add(vec3(1.0, 1.0, 0.0)));
  const n001 = hash3(cell.add(vec3(0.0, 0.0, 1.0)));
  const n101 = hash3(cell.add(vec3(1.0, 0.0, 1.0)));
  const n011 = hash3(cell.add(vec3(0.0, 1.0, 1.0)));
  const n111 = hash3(cell.add(vec3(1.0, 1.0, 1.0)));

  const nx00 = mix(n000, n100, local.x);
  const nx10 = mix(n010, n110, local.x);
  const nx01 = mix(n001, n101, local.x);
  const nx11 = mix(n011, n111, local.x);
  const nxy0 = mix(nx00, nx10, local.y);
  const nxy1 = mix(nx01, nx11, local.y);
  return mix(nxy0, nxy1, local.z);
});

export const fbm2 = Fn(([input]) => {
  const p = Var(input);
  const value = Var(float(0.0));
  const amplitude = Var(float(0.5));
  Loop(4, () => {
    value.addAssign(amplitude.mul(valueNoise2D(p)));
    p.assign(p.mul(2.03));
    amplitude.mulAssign(0.5);
  });
  return value;
});

export const fbm3 = Fn(([input]) => {
  const p = Var(input);
  const value = Var(float(0.0));
  const amplitude = Var(float(0.55));
  Loop(4, () => {
    value.addAssign(amplitude.mul(valueNoise3D(p)));
    p.assign(p.mul(2.03));
    amplitude.mulAssign(0.5);
  });
  return value;
});

export { abs };
