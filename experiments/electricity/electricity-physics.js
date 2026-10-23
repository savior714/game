/*!
 * AIDEN POWER ISLAND 3D — 전기 발전 실험실 & 밤섬 전력망 물리 엔진
 *
 * 화면(DOM / WebGL)과 완전히 분리된 순수 계산 모듈이다.
 * 브라우저(window.PowerPhysics)와 Node(require) 양쪽에서 동일하게 동작한다.
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

  /* ── 1. 닫힌 회로 & 중앙 변전소 버스바 ─────────────────────────── */

  const CIRCUIT_MATERIALS = Object.freeze({
    copper: {
      label: "구리 버스바",
      conductive: true,
      resistance: 1,
      transmission: 1,
      color: "#ff9248",
      note: "전기가 막힘없이 아주 잘 흘러요",
    },
    coin: {
      label: "동전 브리지",
      conductive: true,
      resistance: 3.4,
      transmission: 0.44,
      color: "#ffd968",
      note: "전기가 통하지만 저항 때문에 힘이 줄어요",
    },
    wood: {
      label: "나무 막대",
      conductive: false,
      resistance: null,
      transmission: 0,
      color: "#b98548",
      note: "부도체라 전기 길이 끊겨요",
    },
    plastic: {
      label: "플라스틱 자",
      conductive: false,
      resistance: null,
      transmission: 0,
      color: "#7cc8ff",
      note: "부도체라 전기가 멈춰요",
    },
    eraser: {
      label: "고무 지우개",
      conductive: false,
      resistance: null,
      transmission: 0,
      color: "#ff85a1",
      note: "고무는 전기를 막아 주는 절연체예요",
    },
  });

  const BULB_FULL_CURRENT = 1.6;

  /** 옴의 법칙(I = V / R)으로 주 회로 전류와 전구 밝기를 계산한다. */
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
      color: spec.color,
      conductive: spec.conductive,
      closed: closed,
      transmission: flowing ? spec.transmission : 0,
      voltage: round(voltage, 2),
      current: round(current, 3),
      brightness: round(Math.pow(ratio, 0.55), 4),
      auxWatts: flowing ? round(voltage * current * 0.35, 3) : 0,
      lit: current >= 0.12,
    };
  }

  /** 전류가 셀수록 전자가 빠르게 움직인다(단위 속도). */
  function electronSpeed(current) {
    return clamp(20 + Math.abs(current) * 110, 0, 320);
  }

  /* ── 2. 마찰 전기: 풍선과 양모 패드 ───────────────────────────── */

  const STATIC_LIMITS = Object.freeze({
    maxCharge: 100,
    rubGain: 62,
    decayPerSecond: 10.5,
    liftCharge: 42,
    dropCharge: 20,
    reachBase: 48,
    reachPerCharge: 1.08,
  });

  /** 양모 패드에 문지르는 빠르기(0~1)와 시간(초)으로 전하를 모은다. */
  function staticRub(charge, rubSpeed, dt) {
    const gain = STATIC_LIMITS.rubGain * clamp(rubSpeed, 0, 1) * Math.max(0, dt);
    return clamp(
      clamp(charge, 0, STATIC_LIMITS.maxCharge) + gain,
      0,
      STATIC_LIMITS.maxCharge
    );
  }

  /** 공기 중으로 전하가 조금씩 방전된다. */
  function staticDecay(charge, dt) {
    return clamp(
      clamp(charge, 0, STATIC_LIMITS.maxCharge) -
        STATIC_LIMITS.decayPerSecond * Math.max(0, dt),
      0,
      STATIC_LIMITS.maxCharge
    );
  }

  /** 전하가 많을수록 정전기 인력이 미치는 거리가 길어진다. */
  function staticReach(charge) {
    return (
      STATIC_LIMITS.reachBase +
      clamp(charge, 0, STATIC_LIMITS.maxCharge) * STATIC_LIMITS.reachPerCharge
    );
  }

  /** 종이 별 조각이 풍선에 달라붙는지 판정한다. */
  function staticGrab(charge, distance) {
    return charge >= STATIC_LIMITS.liftCharge && distance <= staticReach(charge);
  }

  /** 멀리 있는 종이 별 조각이 끌려 올라오는 세기(0~1). */
  function staticPull(charge, distance) {
    if (charge <= 0) return 0;
    const reach = staticReach(charge);
    const span = reach * 2.4;
    if (distance > span) return 0;
    return round(
      clamp(1 - distance / span, 0, 1) *
        clamp(charge / STATIC_LIMITS.maxCharge, 0, 1),
      4
    );
  }

  /* ── 3. 과일 화학 전지: 직렬 연결 ─────────────────────────────── */

  const FRUITS = Object.freeze({
    lemon: { label: "레몬", volts: 0.9, color: "#f6d828", acid: "새콤한 시트르산" },
    potato: { label: "감자", volts: 0.75, color: "#c99658", acid: "감자 속 인산 수분" },
    apple: { label: "사과", volts: 0.55, color: "#e8483f", acid: "달콤한 사과산" },
    tomato: { label: "토마토", volts: 0.68, color: "#ec5a3b", acid: "싱그러운 유기산" },
    vinegar: { label: "식초 비커", volts: 1.1, color: "#ece3a8", acid: "강력한 아세트산" },
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
    const clampedLevel = round(clamp(level, 0, 1), 4);
    return {
      label: fruit.label,
      acid: fruit.acid,
      color: fruit.color,
      cells: cells,
      volts: round(volts, 2),
      perCell: fruit.volts,
      level: clampedLevel,
      watts: volts >= LED_LIMITS.forwardVolts ? round(0.4 + clampedLevel * 1.8, 3) : 0,
      lit: volts >= LED_LIMITS.forwardVolts,
      full: volts >= LED_LIMITS.fullVolts,
    };
  }

  /* ── 4. 손잡이 크랭크 발전기: 패러데이 전자기 유도 ────────────── */

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
    const turns = clamp(
      source.turns,
      GENERATOR_LIMITS.minTurns,
      GENERATOR_LIMITS.maxTurns
    );
    const fieldTesla = clamp(source.fieldTesla, 0.02, 1.2);
    const areaM2 = clamp(
      source.areaM2 === undefined ? GENERATOR_LIMITS.areaM2 : source.areaM2,
      0.0005,
      0.5
    );
    const rpm = clamp(source.rpm, -3000, 3000);
    const omega = (Math.abs(rpm) * TAU) / 60;
    return round(turns * fieldTesla * areaM2 * omega, 4);
  }

  /** 발전량(W) = 전압² / 부하 저항 */
  function generatorWatts(emf, loadOhms) {
    const load = clamp(
      loadOhms === undefined ? GENERATOR_LIMITS.loadOhms : loadOhms,
      0.5,
      200
    );
    return round((Math.abs(emf) * Math.abs(emf)) / load, 4);
  }

  function generatorOutput(input) {
    const source = input || {};
    const emf = inducedEmf(source);
    const watts = generatorWatts(emf, source.loadOhms);
    return {
      emf: emf,
      watts: watts,
      gridWatts: round(watts * 4.5, 3),
      level: round(clamp(watts / GENERATOR_LIMITS.fullWatts, 0, 1), 4),
    };
  }

  /* ── 5. 해바라기 태양광 발전: 입사각과 구름 ───────────────────── */

  const SOLAR_LIMITS = Object.freeze({
    panelAreaM2: 0.05,
    efficiency: 0.19,
    irradiance: 1000,
    fullWatts: 9.5,
  });

  /** 햇빛이 패널 법선과 나란할수록 1에 가까워진다. */
  function solarIncidence(sunAltitudeDeg, panelTiltDeg) {
    const altitude = clamp(sunAltitudeDeg, 0, 90);
    const tilt = clamp(panelTiltDeg, 0, 90);
    const theta = Math.abs(90 - altitude - tilt);
    return round(clamp(Math.cos(theta * DEG), 0, 1), 4);
  }

  function solarOutput(input) {
    const source = input || {};
    const cloudiness = clamp(source.cloudiness, 0, 1);
    const clear = 1 - cloudiness * 0.85;
    const area = clamp(
      source.panelAreaM2 === undefined
        ? SOLAR_LIMITS.panelAreaM2
        : source.panelAreaM2,
      0.001,
      5
    );
    const efficiency = clamp(
      source.efficiency === undefined
        ? SOLAR_LIMITS.efficiency
        : source.efficiency,
      0.02,
      0.5
    );
    const irradiance = clamp(
      source.irradiance === undefined
        ? SOLAR_LIMITS.irradiance
        : source.irradiance,
      0,
      1400
    );
    const incidence = solarIncidence(source.sunAltitudeDeg, source.panelTiltDeg);
    const watts = round(irradiance * clear * area * efficiency * incidence, 4);
    return {
      incidence: incidence,
      watts: watts,
      level: round(clamp(watts / SOLAR_LIMITS.fullWatts, 0, 1), 4),
      optimalTilt: round(90 - clamp(source.sunAltitudeDeg, 0, 90), 1),
    };
  }

  /* ── 6. 해안 풍력 발전: 풍속 세제곱 법칙 ──────────────────────── */

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

  /** P = 1/2 × 공기밀도 × 회전면적 × 풍속³ × 효율계수 */
  function windPower(input) {
    const source = input || {};
    const windSpeed = clamp(source.windSpeed, 0, 25);
    const bladeLength = clamp(source.bladeLength, 0.05, 5);
    const bladeCount = Math.round(clamp(source.bladeCount, 1, 8));
    const factor =
      BLADE_FACTORS[bladeCount] === undefined ? 0.5 : BLADE_FACTORS[bladeCount];
    const cp = WIND_LIMITS.baseCp * factor;
    const area = windSweptArea(bladeLength);
    const watts = round(
      0.5 * WIND_LIMITS.airDensity * area * Math.pow(windSpeed, 3) * cp,
      4
    );
    return {
      sweptArea: area,
      cp: round(cp, 4),
      watts: watts,
      level: round(clamp(watts / WIND_LIMITS.fullWatts, 0, 1), 4),
    };
  }

  /** 풍속과 날개 길이에 따른 로터 회전 속도(rpm). */
  function turbineRpm(input) {
    const source = input || {};
    const windSpeed = clamp(source.windSpeed, 0, 25);
    const bladeLength = clamp(source.bladeLength, 0.05, 5);
    const drag = bladeLength > 0.45 ? 0.8 : 1;
    const omega = (WIND_LIMITS.tipSpeedRatio * windSpeed) / bladeLength;
    return round(((omega * 60) / TAU) * drag, 2);
  }

  /* ── 7. 폭포 수력 발전: 낙차와 유량 ───────────────────────────── */

  const HYDRO_LIMITS = Object.freeze({
    efficiency: 0.55,
    fullWatts: 20,
    wheelDiameterM: 0.5,
  });

  /** P = 물밀도 × 중력가속도 × 유량(m³/s) × 낙차(m) × 효율 */
  function hydroPower(input) {
    const source = input || {};
    const headMeters = clamp(source.headMeters, 0, 30);
    const flowLitersPerSec = clamp(source.flowLitersPerSec, 0, 200);
    const efficiency = clamp(
      source.efficiency === undefined
        ? HYDRO_LIMITS.efficiency
        : source.efficiency,
      0.05,
      1
    );
    const flowM3PerSec = flowLitersPerSec / 1000;
    const watts = round(
      1000 * GRAVITY * flowM3PerSec * headMeters * efficiency,
      4
    );
    return {
      jetSpeed: round(Math.sqrt(2 * GRAVITY * headMeters), 3),
      watts: watts,
      level: round(clamp(watts / HYDRO_LIMITS.fullWatts, 0, 1), 4),
    };
  }

  /** 수차 회전 속도(rpm). */
  function wheelRpm(input) {
    const source = input || {};
    const jet = hydroPower(source).jetSpeed;
    const circumference = Math.PI * HYDRO_LIMITS.wheelDiameterM;
    return round(((jet * 0.45) / circumference) * 60, 2);
  }

  /* ── 8. 밤섬 통합 전력망 & 6단계 마을 점등 계산 ───────────────── */

  const WEATHER_PRESETS = Object.freeze({
    night: {
      label: "별밤",
      sunAltitude: 28,
      cloud: 10,
      wind: 5.5,
      skyDarkness: 1,
    },
    dusk: {
      label: "노을",
      sunAltitude: 16,
      cloud: 20,
      wind: 4.5,
      skyDarkness: 0.62,
    },
    day: {
      label: "맑은 낮",
      sunAltitude: 68,
      cloud: 0,
      wind: 5,
      skyDarkness: 0.08,
    },
    storm: {
      label: "번개 폭풍",
      sunAltitude: 12,
      cloud: 85,
      wind: 9.5,
      skyDarkness: 0.92,
    },
  });

  const VILLAGE_LANDMARKS = Object.freeze([
    { id: "cottages", label: "해안 오두막과 가로등", minWatts: 1.4 },
    { id: "harbor", label: "항구 상점가와 회전 등대", minWatts: 6.5 },
    { id: "train", label: "반짝 꼬마 전기 기차", minWatts: 14 },
    { id: "ferris", label: "밤하늘 네온 대관람차", minWatts: 24 },
    { id: "fountain", label: "무지개 분수 광장", minWatts: 35 },
    { id: "festival", label: "테슬라 번개탑과 불꽃 축제", minWatts: 46 },
  ]);

  function powerLevel(watts, fullWatts) {
    return round(clamp(watts / fullWatts, 0, 1), 4);
  }

  /** 전력(W)을 시간(초) 동안 모으면 얻는 전기 에너지(J). */
  function energyJoules(watts, seconds) {
    return round(Math.max(0, watts) * Math.max(0, seconds), 3);
  }

  /** 모든 발전소 출력과 주 변전소 회로를 합산해 마을 점등 상태를 산출한다. */
  function islandGridState(input) {
    const source = input || {};
    const rawWatts =
      Math.max(0, source.generatorWatts || 0) +
      Math.max(0, source.solarWatts || 0) +
      Math.max(0, source.windWatts || 0) +
      Math.max(0, source.hydroWatts || 0) +
      Math.max(0, source.fruitWatts || 0) +
      Math.max(0, source.surgeWatts || 0);

    const circuit = source.circuit || circuitState({ material: "copper", voltage: 3, closed: true });
    const delivered = round(
      (rawWatts + (circuit.auxWatts || 0)) * (circuit.transmission || 0),
      3
    );

    const landmarks = {};
    let litCount = 0;
    for (let i = 0; i < VILLAGE_LANDMARKS.length; i += 1) {
      const spec = VILLAGE_LANDMARKS[i];
      const nextThreshold =
        i + 1 < VILLAGE_LANDMARKS.length
          ? VILLAGE_LANDMARKS[i + 1].minWatts
          : spec.minWatts + 12;
      const span = Math.max(2, nextThreshold - spec.minWatts);
      const level = delivered >= spec.minWatts
        ? clamp(0.45 + ((delivered - spec.minWatts) / span) * 0.55, 0, 1)
        : 0;
      landmarks[spec.id] = round(level, 4);
      if (level > 0) litCount += 1;
    }

    return {
      rawWatts: round(rawWatts, 3),
      deliveredWatts: delivered,
      blockedWatts: round(Math.max(0, rawWatts - delivered), 3),
      // 송전이 실제로 이뤄졌는가 — 정전(0W 공급) 판정의 단일 기준
      powered: delivered > 0,
      litCount: litCount,
      totalLandmarks: VILLAGE_LANDMARKS.length,
      gridRatio: round(clamp(delivered / 52, 0, 1), 4),
      landmarks: landmarks,
    };
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
    WEATHER_PRESETS,
    VILLAGE_LANDMARKS,
    powerLevel,
    energyJoules,
    islandGridState,
  };
});
