// 태양계 3D 탐험대 — 궤도/자전 계산 (three.js 비의존 순수 모듈)
// Node 테스트에서 그대로 import 해 검증할 수 있도록 DOM/THREE를 사용하지 않습니다.

export const TAU = Math.PI * 2;

/** 표준 J2000.0 원기 (2000-01-01 12:00 UTC). 궤도 요소의 기준 시각. */
export const J2000_ISO = "2000-01-01T12:00:00Z";
export const J2000_MS = Date.parse(J2000_ISO);
export const MS_PER_DAY = 86400000;

/** 화면에서 행성 궤도 반지름을 압축하는 기준값. */
export const ORBIT_RADIUS_BASE = 40;
export const ORBIT_RADIUS_EXPONENT = 0.42;

const DEG = Math.PI / 180;

export function degToRad(degrees) {
  return degrees * DEG;
}

export function normalizeAngle(radians) {
  const wrapped = radians % TAU;
  return wrapped < 0 ? wrapped + TAU : wrapped;
}

/**
 * 케플러 방정식 M = E - e·sin(E) 를 뉴턴 반복으로 푼다.
 * 행성 궤도는 이심률이 작아 6~8회면 충분히 수렴한다.
 */
export function solveKepler(meanAnomalyRad, eccentricity) {
  const m = normalizeAngle(meanAnomalyRad);
  let eccentricAnomaly = eccentricity < 0.8 ? m : Math.PI;

  for (let i = 0; i < 8; i += 1) {
    const f = eccentricAnomaly - eccentricity * Math.sin(eccentricAnomaly) - m;
    const derivative = 1 - eccentricity * Math.cos(eccentricAnomaly);
    const step = f / derivative;
    eccentricAnomaly -= step;
    if (Math.abs(step) < 1e-10) break;
  }

  return eccentricAnomaly;
}

/**
 * J2000 기준 경과일로 태양 중심 황도 좌표(AU)를 구한다.
 * 반환 좌표는 (x, y, z)이며 z가 황도면의 수직 방향이다.
 */
export function eclipticPositionAU(orbit, daysSinceJ2000) {
  const meanMotion = TAU / orbit.periodDays;
  const meanAnomaly = degToRad(orbit.m0) + meanMotion * daysSinceJ2000;
  const eccentricAnomaly = solveKepler(meanAnomaly, orbit.e);

  return eclipticFromEccentric(orbit, eccentricAnomaly);
}

/**
 * 이심 근점각 E를 황도 좌표로 변환한다.
 * ω(근일점 인수) = ϖ(근일점 경도) − Ω(승교점 경도).
 */
export function eclipticFromEccentric(orbit, eccentricAnomaly) {
  const xOrbital = orbit.a * (Math.cos(eccentricAnomaly) - orbit.e);
  const yOrbital = orbit.a * Math.sqrt(1 - orbit.e * orbit.e) * Math.sin(eccentricAnomaly);

  const node = degToRad(orbit.node);
  const argumentOfPerihelion = degToRad(orbit.perihelion - orbit.node);
  const inclination = degToRad(orbit.inclination);

  const cosNode = Math.cos(node);
  const sinNode = Math.sin(node);
  const cosPeri = Math.cos(argumentOfPerihelion);
  const sinPeri = Math.sin(argumentOfPerihelion);
  const cosInc = Math.cos(inclination);
  const sinInc = Math.sin(inclination);

  const x =
    (cosNode * cosPeri - sinNode * sinPeri * cosInc) * xOrbital +
    (-cosNode * sinPeri - sinNode * cosPeri * cosInc) * yOrbital;
  const y =
    (sinNode * cosPeri + cosNode * sinPeri * cosInc) * xOrbital +
    (-sinNode * sinPeri + cosNode * cosPeri * cosInc) * yOrbital;
  const z = sinPeri * sinInc * xOrbital + cosPeri * sinInc * yOrbital;

  return { x, y, z };
}

/**
 * AU 거리 → 장면 단위 거리.
 * 실제 비율(해왕성 30AU)을 그대로 쓰면 수성이 화면에서 사라지므로 거듭제곱으로 압축한다.
 * 값 자체는 실제 순서와 상대적 간격을 유지한다.
 */
export function orbitRadiusForDistance(distanceAU) {
  return ORBIT_RADIUS_BASE * Math.pow(Math.max(distanceAU, 1e-6), ORBIT_RADIUS_EXPONENT);
}

/**
 * 황도 좌표를 three.js 좌표계로 옮긴다.
 * three.js는 Y가 위쪽이므로 황도면의 y를 -Z로 보낸다.
 */
export function toWorldUnits(positionAU) {
  const distance = Math.hypot(positionAU.x, positionAU.y, positionAU.z);
  const scale = distance > 0 ? orbitRadiusForDistance(distance) / distance : 0;
  return {
    x: positionAU.x * scale,
    y: positionAU.z * scale,
    z: -positionAU.y * scale,
  };
}

/** 태양 중심 장면 좌표. */
export function visualOrbitPosition(orbit, daysSinceJ2000) {
  return toWorldUnits(eclipticPositionAU(orbit, daysSinceJ2000));
}

/** 궤도선을 그리기 위한 장면 좌표 목록. */
export function orbitPathPoints(orbit, segments = 256) {
  const points = [];
  for (let i = 0; i < segments; i += 1) {
    const eccentricAnomaly = (i / segments) * TAU;
    points.push(toWorldUnits(eclipticFromEccentric(orbit, eccentricAnomaly)));
  }
  return points;
}

/** 자전 각도(rad). rotationHours가 음수면 역방향 자전이다. */
export function spinAngleRad(rotationHours, daysSinceJ2000) {
  if (!Number.isFinite(rotationHours) || rotationHours === 0) return 0;
  return TAU * ((daysSinceJ2000 * 24) / rotationHours);
}

/**
 * 한 프레임에서 자전이 튀지 않도록 각도 변화량에 상한을 둔다.
 * 빠른 배속에서 행성이 깜빡이듯 보이는 현상을 막는다.
 */
export function clampAngularStep(angleDelta, maxRadiansPerFrame = 0.22) {
  if (!Number.isFinite(angleDelta)) return 0;
  return Math.max(-maxRadiansPerFrame, Math.min(maxRadiansPerFrame, angleDelta));
}

/** J2000 경과일 → UTC 날짜. */
export function dateFromSimulationDays(daysSinceJ2000) {
  return new Date(J2000_MS + daysSinceJ2000 * MS_PER_DAY);
}

export function formatSimDate(daysSinceJ2000) {
  const date = dateFromSimulationDays(daysSinceJ2000);
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  const day = String(date.getUTCDate()).padStart(2, "0");
  return `${year}년 ${month}월 ${day}일`;
}

/** ISO 날짜 문자열 → J2000 경과일. */
export function daysSinceJ2000(isoDate) {
  const parsed = Date.parse(isoDate);
  if (!Number.isFinite(parsed)) return 0;
  return (parsed - J2000_MS) / MS_PER_DAY;
}

export function speedLabel(daysPerSecond, paused = false) {
  if (paused) return "일시정지";
  if (daysPerSecond <= 0) return "정지";
  if (daysPerSecond < 1 / 24) return "실시간";
  if (daysPerSecond < 1) return `${Math.round(daysPerSecond * 24)}시간 / 초`;
  if (daysPerSecond < 30) return `${Math.round(daysPerSecond)}일 / 초`;
  if (daysPerSecond < 300) return `${Math.round(daysPerSecond)}일 / 초`;
  return "1년 / 초";
}
