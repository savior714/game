/*!
 * AIDEN POWER LAB — 전기 발전 실험실 물리 엔진
 *
 * 화면(DOM/canvas)과 완전히 분리된 순수 계산 모듈이다.
 * Node에서 그대로 require해 전압·전류·발전량 계산을 검증한다.
 */

(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.PowerPhysics = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const TAU = Math.PI * 2;
  const DEG = Math.PI / 180;
  const GRAVITY = 9.81;

  function clamp(value, min, max) {
    if (typeof value !== "number" || Number.isNaN(value)) return min;
    return Math.min(max, Math.max(min, value));
  }

  function round(value, digits) {
    const scale = Math.pow(10, digits === undefined ? 3 : digits);
    return Math.round(value * scale) / scale;
  }

  /* ── 1. 닫힌 회로: 전기가 도는 길 ─────────────────────────────── */

  const CIRCUIT_MATERIALS = Object.freeze({
    copper: { label: "구리 전선", conductive: true, resistance: 1, note: "전기가 아주 잘 통해요" },
    coin: { label: "동전", conductive: true, resistance: 3.4, note: "전기가 통하지만 방해를 받아요" },
    wood: { label: "나무젓가락", conductive: false, resistance: null, note: "전기가 통하지 않아요" },
    plastic: { label: "플라스틱 자", conductive: false, resistance: null, note: "전기가 통하지 않아요" },
    eraser: { label: "지우개", conductive: false, resistance: null, note: "전기가 통하지 않아요" },
  });

  const BULB_FULL_CURRENT = 1.6;

  /** 옴의 법칙(I = V / R)으로 전구 밝기를 구한다. */
  function circuitState(input) {
    const source = input || {};
    const spec = CIRCUIT_MATERIALS[source.material];
    if (!spec) {
      throw new Error("unknown circuit material: " + String(source.material));
    }
    const voltage = clamp(source.voltage, 0, 12);
    const closed = source.closed !== false;
    const flowing = Boolean(spec.conductive && closed && voltage > 0);
    const current = flowing ? voltage / spec.resistance : 0;
    const ratio = clamp(current / BULB_FULL_CURRENT, 0, 1);
    return {
      label: spec.label,
      note: spec.note,
      conductive: spec.conductive,
      closed: closed,
      voltage: round(voltage, 2),
      current: round(current, 3),
      brightness: round(Math.pow(ratio, 0.55), 4),
      lit: current >= 0.12,
    };
  }

  /** 전류가 셀수록 전자가 빠르게 움직인다(px/초). */
  function electronSpeed(current) {
    return clamp(20 + Math.abs(current) * 110, 0, 320);
  }

  /* ── 2. 마찰 전기: 비벼서 모은 전하 ───────────────────────────── */

  const STATIC_LIMITS = Object.freeze({
    maxCharge: 100,
    rubGain: 58,
    decayPerSecond: 11,
    liftCharge: 44,
    dropCharge: 22,
    reachBase: 46,
    reachPerCharge: 1.05,
  });

  /** 털에 비비는 빠르기(0~1)와 시간(초)으로 전하를 모은다. */
  function staticRub(charge, rubSpeed, dt) {
    const gain = STATIC_LIMITS.rubGain * clamp(rubSpeed, 0, 1) * Math.max(0, dt);
    return clamp(clamp(charge, 0, STATIC_LIMITS.maxCharge) + gain, 0, STATIC_LIMITS.maxCharge);
  }

  /** 공기 중으로 전하가 조금씩 사라진다. */
  function staticDecay(charge, dt) {
    return clamp(clamp(charge, 0, STATIC_LIMITS.maxCharge) - STATIC_LIMITS.decayPerSecond * Math.max(0, dt), 0, STATIC_LIMITS.maxCharge);
  }

  /** 전하가 많을수록 손이 닿는 거리가 길어진다(px). */
  function staticReach(charge) {
    return STATIC_LIMITS.reachBase + clamp(charge, 0, STATIC_LIMITS.maxCharge) * STATIC_LIMITS.reachPerCharge;
  }

  /** 종이 조각이 확 붙는지 판정한다. */
  function staticGrab(charge, distance) {
    return charge >= STATIC_LIMITS.liftCharge && distance <= staticReach(charge);
  }

  /** 멀리 있는 종이 조각이 끌려오는 세기(0~1). */
  function staticPull(charge, distance) {
    if (charge <= 0) return 0;
    const reach = staticReach(charge);
    const span = reach * 2.4;
    if (distance > span) return 0;
    return round(clamp(1 - distance / span, 0, 1) * clamp(charge / STATIC_LIMITS.maxCharge, 0, 1), 4);
  }

  /* ── 3. 과일 전지: 액체가 만드는 전기 ─────────────────────────── */

  const FRUITS = Object.freeze({
    lemon: { label: "레몬", volts: 0.9, color: "#f5d327", acid: "신 레몬즙" },
    potato: { label: "감자", volts: 0.75, color: "#c79355", acid: "감자 속 수분" },
    apple: { label: "사과", volts: 0.55, color: "#e2483f", acid: "달콤한 사과즙" },
    tomato: { label: "토마토", volts: 0.68, color: "#e8563a", acid: "토마토즙" },
    vinegar: { label: "식초 물", volts: 1.1, color: "#e8dfa8", acid: "강한 식초" },
  });

  const LED_LIMITS = Object.freeze({ forwardVolts: 1.8, fullVolts: 3.3 });

  /** 전지를 직렬로 연결하면 전압이 더해진다. */
  function fruitBattery(input) {
    const source = input || {};
    const fruit = FRUITS[source.fruit];
    if (!fruit) {
      throw new Error("unknown fruit: " + String(source.fruit));
    }
    const cells = Math.round(clamp(source.cells, 0, 8));
    const volts = fruit.volts * cells;
    let level = 0;
    if (volts >= LED_LIMITS.fullVolts) {
      level = 1;
    } else if (volts >= LED_LIMITS.forwardVolts) {
      const span = LED_LIMITS.fullVolts - LED_LIMITS.forwardVolts;
      level = 0.28 + 0.72 * ((volts - LED_LIMITS.forwardVolts) / span);
    }
    return {
      label: fruit.label,
      acid: fruit.acid,
      color: fruit.color,
      cells: cells,
      volts: round(volts, 2),
      perCell: fruit.volts,
      level: round(clamp(level, 0, 1), 4),
      lit: volts >= LED_LIMITS.forwardVolts,
      full: volts >= LED_LIMITS.fullVolts,
    };
  }

  /* ── 4. 손잡이 발전기: 자석이 코일을 지나갈 때 ────────────────── */

  const GENERATOR_LIMITS = Object.freeze({
    areaM2: 0.008,
    loadOhms: 12,
    fullWatts: 1.6,
    minTurns: 60,
    maxTurns: 600,
  });

  /** 유도 전압(EMF) = 코일 감은 수 × 자기장 × 코일 넓이 × 각속도 */
  function inducedEmf(input) {
    const source = input || {};
    const turns = clamp(source.turns, GENERATOR_LIMITS.minTurns, GENERATOR_LIMITS.maxTurns);
    const fieldTesla = clamp(source.fieldTesla, 0.02, 1.2);
    const areaM2 = clamp(source.areaM2 === undefined ? GENERATOR_LIMITS.areaM2 : source.areaM2, 0.0005, 0.5);
    const rpm = clamp(source.rpm, -3000, 3000);
    const omega = (Math.abs(rpm) * TAU) / 60;
    return round(turns * fieldTesla * areaM2 * omega, 4);
  }

  /** 발전량(W) = 전압² / 저항 */
  function generatorWatts(emf, loadOhms) {
    const load = clamp(loadOhms === undefined ? GENERATOR_LIMITS.loadOhms : loadOhms, 0.5, 200);
    return round((Math.abs(emf) * Math.abs(emf)) / load, 4);
  }

  function generatorOutput(input) {
    const source = input || {};
    const emf = inducedEmf(source);
    const watts = generatorWatts(emf, source.loadOhms);
    return {
      emf: emf,
      watts: watts,
      level: round(clamp(watts / GENERATOR_LIMITS.fullWatts, 0, 1), 4),
    };
  }

  /* ── 5. 태양광: 빛을 바로 전기로 ──────────────────────────────── */

  const SOLAR_LIMITS = Object.freeze({
    panelAreaM2: 0.05,
    efficiency: 0.19,
    irradiance: 1000,
    fullWatts: 9.5,
  });

  /** 햇빛이 패널에 똑바로 들어오면 1, 비스듬하면 작아진다. */
  function solarIncidence(sunAltitudeDeg, panelTiltDeg) {
    const altitude = clamp(sunAltitudeDeg, 0, 90);
    const tilt = clamp(panelTiltDeg, 0, 90);
    const theta = Math.abs((90 - altitude) - tilt);
    return round(clamp(Math.cos(theta * DEG), 0, 1), 4);
  }

  function solarOutput(input) {
    const source = input || {};
    const cloudiness = clamp(source.cloudiness, 0, 1);
    const clear = 1 - cloudiness * 0.85;
    const area = clamp(source.panelAreaM2 === undefined ? SOLAR_LIMITS.panelAreaM2 : source.panelAreaM2, 0.001, 5);
    const efficiency = clamp(source.efficiency === undefined ? SOLAR_LIMITS.efficiency : source.efficiency, 0.02, 0.5);
    const irradiance = clamp(source.irradiance === undefined ? SOLAR_LIMITS.irradiance : source.irradiance, 0, 1400);
    const incidence = solarIncidence(source.sunAltitudeDeg, source.panelTiltDeg);
    const watts = round(irradiance * clear * area * efficiency * incidence, 4);
    return {
      incidence: incidence,
      watts: watts,
      level: round(clamp(watts / SOLAR_LIMITS.fullWatts, 0, 1), 4),
      optimalTilt: round(90 - clamp(source.sunAltitudeDeg, 0, 90), 1),
    };
  }

  /* ── 6. 바람 발전: 바람이 2배면 전기는 8배 ───────────────────── */

  const WIND_LIMITS = Object.freeze({
    airDensity: 1.225,
    baseCp: 0.16,
    fullWatts: 20,
    tipSpeedRatio: 5.2,
  });

  const BLADE_FACTORS = Object.freeze({ 2: 0.93, 3: 1, 4: 0.86, 6: 0.6 });

  function windSweptArea(bladeLengthM) {
    const radius = clamp(bladeLengthM, 0.05, 5);
    return round(Math.PI * radius * radius, 4);
  }

  /** P = 1/2 × 공기밀도 × 날개 면적 × 풍속³ × 효율 */
  function windPower(input) {
    const source = input || {};
    const windSpeed = clamp(source.windSpeed, 0, 25);
    const bladeLength = clamp(source.bladeLength, 0.05, 5);
    const bladeCount = Math.round(clamp(source.bladeCount, 1, 8));
    const factor = BLADE_FACTORS[bladeCount] === undefined ? 0.5 : BLADE_FACTORS[bladeCount];
    const cp = WIND_LIMITS.baseCp * factor;
    const area = windSweptArea(bladeLength);
    const watts = round(0.5 * WIND_LIMITS.airDensity * area * Math.pow(windSpeed, 3) * cp, 4);
    return {
      sweptArea: area,
      cp: round(cp, 4),
      watts: watts,
      level: round(clamp(watts / WIND_LIMITS.fullWatts, 0, 1), 4),
    };
  }

  /** 날개가 도는 속도(rpm). 날개가 길면 천천히, 바람이 세면 빨리. */
  function turbineRpm(input) {
    const source = input || {};
    const windSpeed = clamp(source.windSpeed, 0, 25);
    const bladeLength = clamp(source.bladeLength, 0.05, 5);
    const drag = bladeLength > 0.45 ? 0.8 : 1;
    const omega = (WIND_LIMITS.tipSpeedRatio * windSpeed) / bladeLength;
    return round((omega * 60) / TAU * drag, 2);
  }

  /* ── 7. 물 발전: 높이와 물의 양 ───────────────────────────────── */

  const HYDRO_LIMITS = Object.freeze({
    efficiency: 0.55,
    fullWatts: 20,
    wheelDiameterM: 0.5,
  });

  /** P = 물의 밀도 × 중력가속도 × 유량(m³/s) × 낙차(m) × 효율 */
  function hydroPower(input) {
    const source = input || {};
    const headMeters = clamp(source.headMeters, 0, 30);
    const flowLitersPerSec = clamp(source.flowLitersPerSec, 0, 200);
    const efficiency = clamp(source.efficiency === undefined ? HYDRO_LIMITS.efficiency : source.efficiency, 0.05, 1);
    const flowM3PerSec = flowLitersPerSec / 1000;
    const watts = round(1000 * GRAVITY * flowM3PerSec * headMeters * efficiency, 4);
    return {
      jetSpeed: round(Math.sqrt(2 * GRAVITY * headMeters), 3),
      watts: watts,
      level: round(clamp(watts / HYDRO_LIMITS.fullWatts, 0, 1), 4),
    };
  }

  /** 물살이 바퀴를 돌리는 속도(rpm). */
  function wheelRpm(input) {
    const source = input || {};
    const jet = hydroPower(source).jetSpeed;
    const circumference = Math.PI * HYDRO_LIMITS.wheelDiameterM;
    return round(((jet * 0.45) / circumference) * 60, 2);
  }

  /* ── 공통: 발전량 표시와 모은 전기 ────────────────────────────── */

  function powerLevel(watts, fullWatts) {
    return round(clamp(watts / fullWatts, 0, 1), 4);
  }

  /** 전력(W)을 시간(초) 동안 모으면 얻는 전기 에너지(J). */
  function energyJoules(watts, seconds) {
    return round(Math.max(0, watts) * Math.max(0, seconds), 3);
  }

  return {
    TAU,
    DEG,
    GRAVITY,
    clamp,
    round,
    CIRCUIT_MATERIALS,
    BULB_FULL_CURRENT,
    circuitState,
    electronSpeed,
    STATIC_LIMITS,
    staticRub,
    staticDecay,
    staticReach,
    staticGrab,
    staticPull,
    FRUITS,
    LED_LIMITS,
    fruitBattery,
    GENERATOR_LIMITS,
    inducedEmf,
    generatorWatts,
    generatorOutput,
    SOLAR_LIMITS,
    solarIncidence,
    solarOutput,
    WIND_LIMITS,
    BLADE_FACTORS,
    windSweptArea,
    windPower,
    turbineRpm,
    HYDRO_LIMITS,
    hydroPower,
    wheelRpm,
    powerLevel,
    energyJoules,
  };
});
