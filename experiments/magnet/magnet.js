/*!
 * AIDEN MAGNET LAB — 자석 연구소
 * 캔버스 상호작용, 미션, 철가루/자기장 렌더링, 진행 저장.
 */
(function () {
  "use strict";

  const P = window.MagnetPhysics;
  if (!P) {
    console.error("MagnetPhysics module is required.");
    return;
  }

  const STORAGE_KEY = "aiden_magnet_lab_v1";
  const MISSION_TOTAL = 6;
  const TAU = Math.PI * 2;
  const COLORS = {
    volt: "215, 255, 0",
    mint: "92, 242, 194",
    red: "255, 90, 110",
    blue: "76, 141, 255",
    gold: "255, 202, 88",
    steel: "203, 218, 240",
  };

  const ITEM_TYPES = {
    clip: { label: "종이클립", radius: 14, draw: 11, magnetic: true },
    nail: { label: "못", radius: 15, draw: 13, magnetic: true },
    key: { label: "열쇠", radius: 16, draw: 14, magnetic: true },
    ball: { label: "쇠구슬", radius: 14, draw: 12, magnetic: true },
    stick: { label: "나무젓가락", radius: 18, draw: 16, magnetic: false },
    eraser: { label: "지우개", radius: 16, draw: 14, magnetic: false },
    coin: { label: "구리 동전", radius: 14, draw: 12, magnetic: false },
    compass: { label: "나침반", radius: 22, draw: 18, magnetic: false },
  };

  function magnetSize() {
    const length = clamp(state.width * 0.19, 124, 200);
    return { length, width: Math.round(length * 0.335) };
  }

  /** 철 물건이 자석에 끌리는 거리. 좁은 화면에서는 함께 줄어든다. */
  function itemReach() {
    const magnetX = state.width * 0.16;
    const room = Math.max(150, state.width - magnetX - 56);
    return clamp(Math.min(state.width * 0.32, room / 1.3), 112, 280);
  }

  function stepOptions() {
    const reach = itemReach();
    return { reach, fadeStart: reach * 0.72 };
  }

  const $ = (id) => document.getElementById(id);
  const refs = {
    canvas: $("magnet-canvas"),
    stageShell: $("stage-shell"),
    stageHint: $("stage-hint"),
    stageMissionChip: $("stage-mission-chip"),
    stageViewChip: $("stage-view-chip"),
    selectionToolbar: $("selection-toolbar"),
    selectedName: $("selected-name"),
    fieldToggle: $("field-toggle"),
    filingsToggle: $("filings-toggle"),
    saveArtwork: $("save-artwork"),
    powerRange: $("power-range"),
    powerOutput: $("power-output"),
    soundButton: $("sound-button"),
    helpButton: $("help-button"),
    helpDialog: $("help-dialog"),
    helpClose: $("help-close"),
    helpStart: $("help-start"),
    resetScene: $("reset-scene"),
    missionView: $("mission-view"),
    freeView: $("free-view"),
    modeMission: $("mode-mission"),
    modeFree: $("mode-free"),
    missionStep: $("mission-step"),
    missionTitle: $("mission-title"),
    missionGoal: $("mission-goal"),
    missionTip: $("mission-tip"),
    missionDifficulty: $("mission-difficulty"),
    missionWhy: $("mission-why"),
    whyText: $("why-text"),
    missionReset: $("mission-reset"),
    missionNext: $("mission-next"),
    missionDots: $("mission-dots"),
    missionCount: $("mission-count"),
    statMission: $("stat-mission"),
    statFound: $("stat-found"),
    startMission: $("start-mission"),
    toast: $("reward-toast"),
    toastIcon: $("toast-icon"),
    toastTitle: $("toast-title"),
    toastText: $("toast-text"),
    confetti: $("confetti-layer"),
    live: $("live-region"),
    flipButton: $("flip-button"),
    rotateLeft: $("rotate-left"),
    rotateRight: $("rotate-right"),
    deleteMagnet: $("delete-magnet"),
  };

  if (!refs.canvas || !refs.stageShell) {
    console.error("Magnet lab canvas is missing.");
    return;
  }

  const ctx = refs.canvas.getContext("2d");
  const reduceMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

  function prefersReducedMotion() {
    return reduceMotionQuery.matches;
  }

  function clamp(value, min, max) {
    return value < min ? min : value > max ? max : value;
  }

  function distance(ax, ay, bx, by) {
    return Math.sqrt((ax - bx) * (ax - bx) + (ay - by) * (ay - by));
  }

  function randomBetween(min, max) {
    return min + Math.random() * (max - min);
  }

  const state = {
    width: 0,
    height: 0,
    dpr: 1,
    magnets: [],
    items: [],
    goal: null,
    sparks: [],
    trails: [],
    sceneMagnetIds: [],
    missionStartDistance: 0,
    materialGap: 95,
    filingsDraw: 0,
    nextId: 1,
    magnetSerial: 0,
    mode: "mission",
    missionIndex: 0,
    missionDone: false,
    completed: new Set(),
    selectedId: null,
    dragging: null,
    showField: true,
    showFilings: false,
    power: 1,
    soundOn: true,
    fieldDirty: true,
    fieldLines: [],
    lastFieldBuild: 0,
    filingsPoints: [],
    lastFrame: 0,
    lastTrail: 0,
    snapPairs: new Set(),
    toastTimer: null,
    hintDismissed: false,
    audioContext: null,
    resizeQueued: false,
  };

  let audioContext = null;

  /* ────────────────────────────────────────────────────────── progress ── */

  function loadProgress() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const data = JSON.parse(raw);
      if (!data || data.version !== 1) return null;
      const knownIds = new Set(MISSIONS.map((mission) => mission.id));
      const completed = Array.isArray(data.completed)
        ? data.completed.filter((id) => knownIds.has(id))
        : [];
      return {
        completed,
        soundOn: data.soundOn !== false,
        missionIndex:
          Number.isInteger(data.missionIndex) && data.missionIndex >= 0 && data.missionIndex < MISSIONS.length
            ? data.missionIndex
            : 0,
      };
    } catch (error) {
      return null;
    }
  }

  function saveProgress() {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          version: 1,
          completed: Array.from(state.completed),
          soundOn: state.soundOn,
          missionIndex: state.missionIndex,
        })
      );
    } catch (error) {
      /* 저장 공간이 없어도 놀이는 계속된다. */
    }
  }

  /* ─────────────────────────────────────────────────────────── missions ── */

  const MISSIONS = [
    {
      id: "clips",
      title: "클립을 모두 모아요",
      difficulty: "관찰",
      goal: "자석을 끌어서 종이클립 3개를 붙여 보세요.",
      tip: "클립은 철로 만들어져 자석에 끌려와요. 자석을 가까이 가져가 볼까요?",
      why: "자석은 철로 된 물건을 끌어당겨요. 자석과 클립이 가까워질수록 보이지 않는 자기장의 힘이 더 세게 작용해요.",
      setup: (width, height) => {
        const magnetX = width * 0.16;
        const room = Math.max(140, width - magnetX - 64);
        return {
          magnets: [{ x: magnetX, y: height * 0.5, angle: 0 }],
          items: [
            { kind: "clip", x: magnetX + room * 0.55, y: height * 0.3 },
            { kind: "clip", x: magnetX + room * 0.82, y: height * 0.54 },
            { kind: "clip", x: magnetX + room * 0.62, y: height * 0.77 },
          ],
          showField: true,
          showFilings: false,
        };
      },
      check: () => {
        const clips = state.items.filter((item) => item.kind === "clip");
        return clips.filter((item) => item.capturedBy != null).length >= 3;
      },
    },
    {
      id: "attract",
      title: "다른 극은 서로 당겨요",
      difficulty: "발견",
      goal: "N극과 S극이 마주 보게 놓인 두 자석을 가만히 지켜보세요.",
      tip: "왼쪽 자석의 N극과 오른쪽 자석의 S극이 서로를 부르고 있어요.",
      why: "서로 다른 극끼리는 끌어당겨요. N극과 S극이 가까워지면 자석이 스스로 움직여 딱 붙는답니다.",
      setup: (width, height) => {
        const size = magnetSize();
        const half = Math.max(70, size.length / 2 + 10);
        const room = width / 2 - half;
        const dx = Math.min(room, Math.max(half + 30, size.length * 0.68 + 70));
        return {
          magnets: [
            { x: width / 2 - dx, y: height * 0.5, angle: 0 },
            { x: width / 2 + dx, y: height * 0.5, angle: 0 },
          ],
          items: [],
          showField: true,
          showFilings: false,
        };
      },
      check: () => {
        const [a, b] = missionMagnets();
        if (!a || !b) return false;
        return oppositePoleGap(a, b) < 90;
      },
    },
    {
      id: "repel",
      title: "같은 극은 밀어내요",
      difficulty: "발견",
      goal: "N극끼리 마주 본 두 자석이 멀어지는 모습을 관찰하세요.",
      tip: "같은 극을 마주 보게 놓으면 자석이 서로를 밀어내요. 손을 대지 않아도 움직여요!",
      why: "같은 극끼리는 서로 밀어내요. N극과 N극, S극과 S극이 마주 보면 자석이 반대쪽으로 힘껏 달아난답니다.",
      setup: (width, height) => {
        const size = magnetSize();
        const half = Math.max(70, size.length / 2 + 10);
        const dx = clamp(size.length * 0.68, half + 4, width / 2 - half);
        return {
          magnets: [
            { x: width / 2 - dx, y: height * 0.5, angle: 0 },
            { x: width / 2 + dx, y: height * 0.5, angle: Math.PI },
          ],
          items: [],
          showField: true,
          showFilings: false,
        };
      },
      check: () => {
        const [a, b] = missionMagnets();
        if (!a || !b) return false;
        const current = distance(a.x, a.y, b.x, b.y);
        const needed = Math.max(45, Math.min(state.width * 0.09, 90));
        return current > state.missionStartDistance + needed;
      },
    },
    {
      id: "filings",
      title: "철가루로 자기장을 그려요",
      difficulty: "탐구",
      goal: "철가루를 켠 채로 자석을 천천히 움직여 곡선을 그려 보세요.",
      tip: "철가루는 자기장이 지나가는 방향으로 가지런히 늘어서요.",
      why: "철가루는 보이지 않는 자기장의 방향을 보여 줘요. 자석 주변에는 N극에서 S극으로 흐르는 곡선 모양의 자기장이 있어요.",
      setup: (width, height) => ({
        magnets: [{ x: width * 0.5, y: height * 0.5, angle: -0.25 }],
        items: [],
        showField: false,
        showFilings: true,
      }),
      check: () => state.showFilings && state.filingsDraw > 170,
    },
    {
      id: "materials",
      title: "붙는 물건, 안 붙는 물건",
      difficulty: "분류",
      goal: "자석을 나무젓가락·지우개·구리 동전 가까이 가져가 보세요.",
      tip: "자석에 붙는 물건과 그렇지 않은 물건을 하나씩 비교해 봐요.",
      why: "자석은 철로 된 물건에만 힘을 보여요. 나무, 고무, 구리로 만든 물건은 자석에 붙지 않아요.",
      setup: (width, height) => {
        const size = magnetSize();
        const magnetX = width * 0.24;
        const left = magnetX + size.length / 2 + 26;
        const right = Math.max(left + 60, width - 40);
        const span = right - left;
        return {
          magnets: [{ x: magnetX, y: height * 0.52, angle: 0 }],
          items: [
            { kind: "stick", x: left + span * 0.3, y: height * 0.3 },
            { kind: "eraser", x: left + span * 0.62, y: height * 0.62 },
            { kind: "coin", x: left + span * 0.44, y: height * 0.82 },
          ],
          showField: true,
          showFilings: false,
        };
      },
      check: () =>
        state.magnets.some((magnet) =>
          state.items.some(
            (item) =>
              !item.magnetic &&
              item.kind !== "compass" &&
              P.distanceToMagnet(magnet, item.x, item.y) < state.materialGap
          )
        ),
    },
    {
      id: "fishing",
      title: "쇠구슬을 별자리로",
      difficulty: "도전",
      goal: "자석으로 쇠구슬을 끌어 노란 별자리 안에 넣어 보세요.",
      tip: "쇠구슬은 자석 끝에 딱 붙어요. 자석을 천천히 움직여 별까지 데려가요.",
      why: "철로 만든 쇠구슬은 자석의 자기장에 이끌려 자석을 따라가요. 자석을 움직이면 쇠구슬도 함께 움직여요.",
      setup: (width, height) => ({
        magnets: [{ x: width * 0.2, y: height * 0.62, angle: 0 }],
        items: [{ kind: "ball", x: width * 0.68, y: height * 0.32 }],
        goal: { x: width * 0.77, y: height * 0.72, r: clamp(width * 0.075, 48, 70) },
        showField: true,
        showFilings: false,
      }),
      check: () => {
        if (!state.goal) return false;
        const ball = state.items.find((item) => item.kind === "ball");
        if (!ball) return false;
        if (distance(ball.x, ball.y, state.goal.x, state.goal.y) <= state.goal.r) return true;
        if (ball.capturedBy == null) return false;
        const magnet = P.findMagnet(state.magnets, ball.capturedBy);
        if (!magnet) return false;
        return distance(magnet.x, magnet.y, state.goal.x, state.goal.y) <= state.goal.r;
      },
    },
  ];

  function missionMagnets() {
    return state.sceneMagnetIds
      .map((id) => P.findMagnet(state.magnets, id))
      .filter((magnet) => magnet != null);
  }

  function oppositePoleGap(a, b) {
    let best = Infinity;
    P.poleList(a).forEach((poleA) => {
      P.poleList(b).forEach((poleB) => {
        if (poleA.sign === poleB.sign) return;
        best = Math.min(best, distance(poleA.x, poleA.y, poleB.x, poleB.y));
      });
    });
    return best;
  }

  /* ───────────────────────────────────────────────────────────── scenes ── */

  function createMagnet(spec) {
    const size = magnetSize();
    const magnet = P.createMagnet({
      id: state.nextId++,
      x: spec.x,
      y: spec.y,
      angle: spec.angle || 0,
      power: state.power,
      length: size.length,
      width: size.width,
    });
    state.magnetSerial += 1;
    magnet.name = "자석 " + state.magnetSerial;
    return magnet;
  }

  function createItem(kind, x, y) {
    const blueprint = ITEM_TYPES[kind] || ITEM_TYPES.clip;
    const item = P.createItem({
      id: state.nextId++,
      kind,
      x,
      y,
      radius: blueprint.radius,
      magnetic: blueprint.magnetic,
      angle: 0,
    });
    item.label = blueprint.label;
    item.drawRadius = blueprint.draw;
    return item;
  }

  function applyScene(scene) {
    state.magnets = [];
    state.items = [];
    state.magnetSerial = 0;
    (scene.magnets || []).forEach((spec) => {
      state.magnets.push(createMagnet(spec));
    });
    (scene.items || []).forEach((spec) => {
      state.items.push(createItem(spec.kind, spec.x, spec.y));
    });
    state.goal = scene.goal ? { x: scene.goal.x, y: scene.goal.y, r: scene.goal.r } : null;
    state.showField = scene.showField !== false;
    state.showFilings = scene.showFilings === true;
    state.sceneMagnetIds = state.magnets.map((magnet) => magnet.id);
    state.materialGap = clamp(state.width * 0.13, 58, 95);
    state.missionStartDistance =
      state.magnets.length >= 2
        ? distance(state.magnets[0].x, state.magnets[0].y, state.magnets[1].x, state.magnets[1].y)
        : 0;
    state.selectedId = null;
    state.sparks = [];
    state.trails = [];
    state.snapPairs.clear();
    state.filingsDraw = 0;
    state.fieldDirty = true;
    state.fieldLines = [];
    refs.selectionToolbar.hidden = true;
    updateViewChips();
    clampWorld();
  }

  function setupMission(resetCompletion) {
    const mission = MISSIONS[state.missionIndex];
    const scene = mission.setup(state.width, state.height);
    applyScene(scene);
    state.missionDone = resetCompletion ? false : state.completed.has(mission.id);
    updateMissionUI();
    updateStats();
    saveProgress();
    announce(`실험 ${state.missionIndex + 1}. ${mission.title}. ${mission.goal}`);
  }

  function seedFreeScene() {
    const width = state.width;
    const height = state.height;
    applyScene({
      magnets: [{ x: width * 0.3, y: height * 0.5, angle: -0.18 }],
      items: [
        { kind: "clip", x: width * 0.58, y: height * 0.3 },
        { kind: "clip", x: width * 0.66, y: height * 0.66 },
        { kind: "stick", x: width * 0.72, y: height * 0.47 },
        { kind: "compass", x: width * 0.83, y: height * 0.28 },
        { kind: "coin", x: width * 0.82, y: height * 0.7 },
      ],
      showField: true,
      showFilings: false,
    });
    state.missionDone = false;
  }

  function syncTabState(isMission) {
    refs.modeMission.setAttribute("aria-selected", String(isMission));
    refs.modeFree.setAttribute("aria-selected", String(!isMission));
    refs.modeMission.tabIndex = isMission ? 0 : -1;
    refs.modeFree.tabIndex = isMission ? -1 : 0;
  }

  function setMode(mode, options) {
    const opts = options || {};
    state.mode = mode;
    const isMission = mode === "mission";
    syncTabState(isMission);
    refs.missionView.hidden = !isMission;
    refs.freeView.hidden = isMission;

    if (isMission) {
      if (opts.keepScene !== true) setupMission(false);
      return;
    }
    if (opts.seedFree !== false && state.magnets.length === 0 && state.items.length === 0) {
      seedFreeScene();
    }
    updateMissionUI();
    updateViewChips();
  }

  function clearScene() {
    state.magnets = [];
    state.items = [];
    state.goal = null;
    state.sceneMagnetIds = [];
    state.selectedId = null;
    state.sparks = [];
    state.trails = [];
    state.filingsDraw = 0;
    state.fieldDirty = true;
    state.fieldLines = [];
    refs.selectionToolbar.hidden = true;
    setMode("free", { seedFree: false });
    announce("실험대를 비웠어요. 도구로 자석과 물건을 자유롭게 놓아 보세요.");
  }

  function clampWorld() {
    state.magnets.forEach((magnet) => {
      const half = magnet.length / 2 + 8;
      magnet.x = clamp(magnet.x, half, Math.max(half, state.width - half));
      magnet.y = clamp(magnet.y, magnet.width / 2 + 8, Math.max(magnet.width / 2 + 8, state.height - magnet.width / 2 - 8));
    });
    state.items.forEach((item) => {
      const pad = item.radius + 6;
      item.x = clamp(item.x, pad, Math.max(pad, state.width - pad));
      item.y = clamp(item.y, pad, Math.max(pad, state.height - pad));
    });
  }

  /* ───────────────────────────────────────────────────────────── canvas ── */

  function resizeCanvas(initial) {
    const rect = refs.stageShell.getBoundingClientRect();
    const width = Math.max(320, rect.width);
    const height = Math.max(320, rect.height);
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    state.width = width;
    state.height = height;
    state.dpr = dpr;
    refs.canvas.width = Math.round(width * dpr);
    refs.canvas.height = Math.round(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    buildFilingsPoints();
    rescaleMagnets();
    if (!initial) clampWorld();
    state.fieldDirty = true;
    state.fieldLines = [];
  }

  function queueResize() {
    if (state.resizeQueued) return;
    state.resizeQueued = true;
    window.requestAnimationFrame(() => {
      state.resizeQueued = false;
      resizeCanvas(false);
    });
  }

  /** 화면 크기가 바뀌면 자석도 그 비율에 맞춰 다시 그린다. */
  function rescaleMagnets() {
    const size = magnetSize();
    state.magnets.forEach((magnet) => {
      if (magnet.length === size.length && magnet.width === size.width) return;
      magnet.length = size.length;
      magnet.width = size.width;
    });
    state.items.forEach((item) => {
      if (item.capturedBy == null) return;
      const magnet = P.findMagnet(state.magnets, item.capturedBy);
      if (!magnet) {
        P.releaseItem(item);
        return;
      }
      const along = clamp(item.localX, -magnet.length * 0.46, magnet.length * 0.46);
      const side = clamp(item.localY, -magnet.width * 0.9, magnet.width * 0.9);
      const world = P.localToWorld(magnet, along, side);
      item.localX = along;
      item.localY = side;
      item.x = world.x;
      item.y = world.y;
    });
  }

  function buildFilingsPoints() {
    const random = P.seedRandom(0x51ab7e);
    const count = Math.round(clamp((state.width * state.height) / 360, 800, 2100));
    state.filingsPoints = [];
    for (let i = 0; i < count; i += 1) {
      state.filingsPoints.push({
        x: random() * state.width,
        y: random() * state.height,
        phase: random() * TAU,
        scale: 0.65 + random() * 0.75,
      });
    }
  }

  /* ───────────────────────────────────────────────────────────── physics ── */

  function stepWorld(dt) {
    if (dt <= 0) return;
    const bounds = { width: state.width, height: state.height };
    const capturedBefore = new Set(
      state.items.filter((item) => item.capturedBy != null).map((item) => item.id)
    );

    P.stepMagnets(state.magnets, dt, bounds);
    P.stepItems(state.items, state.magnets, dt, bounds, stepOptions());

    state.items.forEach((item) => {
      if (item.capturedBy != null && !capturedBefore.has(item.id)) {
        spawnSparks(item.x, item.y, COLORS.steel, 7);
        playTone(720 + Math.random() * 140, 0.07, "sine", 0.025);
      }
    });

    updateCompasses();
    detectSnaps();
    updateParticles(dt);

    if (state.magnets.some((magnet) => Math.abs(magnet.vx) + Math.abs(magnet.vy) + Math.abs(magnet.omega) > 3)) {
      state.fieldDirty = true;
    }
    if (state.mode === "mission" && !state.missionDone && missionSatisfied()) {
      completeMission();
    }
  }

  function updateCompasses() {
    state.items.forEach((item) => {
      if (item.kind !== "compass") return;
      const field = P.fieldAt(item.x, item.y, state.magnets);
      item.fieldAngle = field.magnitude > 2.6e-6 ? Math.atan2(field.y, field.x) : -Math.PI / 2;
    });
  }

  function detectSnaps() {
    for (let i = 0; i < state.magnets.length; i += 1) {
      for (let j = i + 1; j < state.magnets.length; j += 1) {
        const a = state.magnets[i];
        const b = state.magnets[j];
        const key = Math.min(a.id, b.id) + ":" + Math.max(a.id, b.id);
        const d = distance(a.x, a.y, b.x, b.y);
        if (d < 155 && !state.snapPairs.has(key)) {
          state.snapPairs.add(key);
          spawnSparks((a.x + b.x) / 2, (a.y + b.y) / 2, COLORS.volt, 10);
          playTone(170, 0.12, "triangle", 0.03);
        } else if (d > 230 && state.snapPairs.has(key)) {
          state.snapPairs.delete(key);
        }
      }
    }
  }

  function updateParticles(dt) {
    for (let i = state.sparks.length - 1; i >= 0; i -= 1) {
      const spark = state.sparks[i];
      spark.life -= dt;
      if (spark.life <= 0) {
        state.sparks.splice(i, 1);
        continue;
      }
      spark.x += spark.vx * dt;
      spark.y += spark.vy * dt;
      spark.vx *= 0.96;
      spark.vy *= 0.96;
      spark.vy += 40 * dt;
    }
    for (let i = state.trails.length - 1; i >= 0; i -= 1) {
      state.trails[i].life -= dt;
      if (state.trails[i].life <= 0) state.trails.splice(i, 1);
    }
  }

  function missionSatisfied() {
    const mission = MISSIONS[state.missionIndex];
    if (!mission) return false;
    return mission.check();
  }

  /* ─────────────────────────────────────────────────────────── particles ── */

  function spawnSparks(x, y, color, amount) {
    if (prefersReducedMotion()) return;
    const count = amount || 8;
    for (let i = 0; i < count; i += 1) {
      const angle = Math.random() * TAU;
      const speed = randomBetween(30, 170);
      state.sparks.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        life: randomBetween(0.35, 0.75),
        maxLife: 0.75,
        size: randomBetween(1.4, 3.2),
        color,
      });
    }
  }

  function spawnTrail(magnet) {
    if (prefersReducedMotion() || !state.showFilings) return;
    const now = performance.now();
    if (now - state.lastTrail < 55) return;
    state.lastTrail = now;
    for (let i = 0; i < 5; i += 1) {
      const angle = Math.random() * TAU;
      const radius = randomBetween(18, 92);
      const x = magnet.x + Math.cos(angle) * radius;
      const y = magnet.y + Math.sin(angle) * radius;
      const field = P.fieldAt(x, y, state.magnets);
      state.trails.push({
        x,
        y,
        angle: field.magnitude > 1e-7 ? Math.atan2(field.y, field.x) : angle,
        life: randomBetween(1.3, 2.1),
        maxLife: 2.1,
      });
    }
    if (state.trails.length > 650) {
      state.trails.splice(0, state.trails.length - 650);
    }
  }

  /* ────────────────────────────────────────────────────────────── drawing ── */

  function draw(now) {
    ctx.clearRect(0, 0, state.width, state.height);
    drawPoleGlows(now);
    if (state.showField) drawFieldLines(now);
    if (state.showFilings) drawTrails();
    if (state.showFilings) drawFilings(now);
    if (state.goal) drawGoal(now);
    drawFreeItems();
    state.magnets.forEach((magnet) => drawMagnet(magnet, now));
    drawCapturedItems();
    drawMaterialLabels();
    drawSparks();
    drawSelection(now);
  }

  function drawPoleGlows(now) {
    state.magnets.forEach((magnet) => {
      const poles = P.poleList(magnet);
      poles.forEach((pole) => {
        const color = pole.sign > 0 ? COLORS.red : COLORS.blue;
        const pulse = 0.9 + Math.sin(now / 620 + pole.sign) * 0.1;
        const radius = (state.showField ? 86 : 48) * pulse;
        const gradient = ctx.createRadialGradient(pole.x, pole.y, 0, pole.x, pole.y, radius);
        gradient.addColorStop(0, "rgba(" + color + ", 0.26)");
        gradient.addColorStop(0.45, "rgba(" + color + ", 0.08)");
        gradient.addColorStop(1, "rgba(" + color + ", 0)");
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(pole.x, pole.y, radius, 0, TAU);
        ctx.fill();
      });
    });
  }

  function rebuildFieldLines() {
    state.fieldLines = [];
    state.lastFieldBuild = performance.now();
    state.fieldDirty = false;
    if (!state.showField || state.magnets.length === 0) return;

    state.magnets.forEach((magnet) => {
      fieldSeeds(magnet).forEach((seed) => {
        const line = traceFieldLine(seed);
        if (line.length > 4) state.fieldLines.push(line);
      });
    });
  }

  function fieldSeeds(magnet) {
    const seeds = [];
    const cos = Math.cos(magnet.angle);
    const sin = Math.sin(magnet.angle);
    const nPole = P.poleList(magnet)[0];
    const radius = magnet.width * 0.68;
    // 자석이 많을수록 곡선 수를 줄여 태블릿에서도 부드럽게 그린다.
    const budget = state.magnets.length > 4 ? 5 : 8;
    for (let i = 0; i < budget; i += 1) {
      const angle = magnet.angle - Math.PI / 2 + (Math.PI * i) / (budget - 1);
      seeds.push({
        x: nPole.x + Math.cos(angle) * radius,
        y: nPole.y + Math.sin(angle) * radius,
      });
    }
    if (state.magnets.length <= 3) {
      [0.28, 0.62].forEach((ratio) => {
        const baseX = magnet.x + cos * magnet.length * (ratio - 0.5);
        const baseY = magnet.y + sin * magnet.length * (ratio - 0.5);
        [-1, 1].forEach((side) => {
          seeds.push({
            x: baseX - sin * side * (magnet.width / 2 + 2),
            y: baseY + cos * side * (magnet.width / 2 + 2),
          });
        });
      });
    }
    return seeds;
  }

  function insideMagnet(x, y, pad) {
    return state.magnets.some((magnet) => {
      const local = P.worldToLocal(magnet, x, y);
      return (
        Math.abs(local.x) <= magnet.length / 2 + pad &&
        Math.abs(local.y) <= magnet.width / 2 + pad
      );
    });
  }

  function traceFieldLine(seed) {
    const points = [{ x: seed.x, y: seed.y }];
    let x = seed.x;
    let y = seed.y;
    const margin = 70;
    for (let step = 0; step < 72; step += 1) {
      const field = P.fieldAt(x, y, state.magnets);
      if (field.magnitude < 1e-8) break;
      const scale = 6 / field.magnitude;
      x += field.x * scale;
      y += field.y * scale;
      if (x < -margin || x > state.width + margin || y < -margin || y > state.height + margin) break;
      if (step > 2 && insideMagnet(x, y, 1)) break;
      points.push({ x, y });
    }
    return points;
  }

  function drawFieldLines(now) {
    if (state.fieldLines.length === 0) return;
    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    ctx.strokeStyle = "rgba(" + COLORS.mint + ", 0.05)";
    ctx.lineWidth = 6;
    ctx.beginPath();
    state.fieldLines.forEach((line) => {
      ctx.moveTo(line[0].x, line[0].y);
      for (let i = 1; i < line.length; i += 1) ctx.lineTo(line[i].x, line[i].y);
    });
    ctx.stroke();

    ctx.strokeStyle = "rgba(" + COLORS.mint + ", 0.26)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    state.fieldLines.forEach((line) => {
      ctx.moveTo(line[0].x, line[0].y);
      for (let i = 1; i < line.length; i += 1) ctx.lineTo(line[i].x, line[i].y);
    });
    ctx.stroke();

    // 자기장이 흐르는 방향을 점선이 따라가듯 보여 준다.
    if (!prefersReducedMotion()) {
      ctx.strokeStyle = "rgba(215, 255, 0, 0.4)";
      ctx.lineWidth = 1.6;
      ctx.setLineDash([3, 16]);
      ctx.lineDashOffset = -((now / 26) % 19);
      ctx.beginPath();
      state.fieldLines.forEach((line) => {
        ctx.moveTo(line[0].x, line[0].y);
        for (let i = 1; i < line.length; i += 1) ctx.lineTo(line[i].x, line[i].y);
      });
      ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.restore();
  }

  function drawFilings(now) {
    if (state.magnets.length === 0) return;
    const buckets = [[], [], [], [], []];
    state.filingsPoints.forEach((point) => {
      const field = P.fieldAt(point.x, point.y, state.magnets);
      const intensity = clamp((field.magnitude - 1.05e-5) * 68000, 0, 1);
      if (intensity < 0.035) return;
      const angle = Math.atan2(field.y, field.x);
      const length = (4 + intensity * 8) * point.scale;
      const cos = Math.cos(angle);
      const sin = Math.sin(angle);
      const bucket = Math.min(4, Math.floor(intensity * 5));
      buckets[bucket].push([
        point.x - cos * length * 0.5,
        point.y - sin * length * 0.5,
        point.x + cos * length * 0.5,
        point.y + sin * length * 0.5,
      ]);
    });

    const pulse = 0.9 + Math.sin(now / 900) * 0.1;
    ctx.save();
    ctx.lineCap = "round";
    for (let bucket = 0; bucket < buckets.length; bucket += 1) {
      const segments = buckets[bucket];
      if (segments.length === 0) continue;
      const alpha = (0.12 + bucket * 0.15) * pulse;
      ctx.strokeStyle = "rgba(216, 232, 255, " + alpha.toFixed(3) + ")";
      ctx.lineWidth = 0.85 + bucket * 0.24;
      ctx.beginPath();
      segments.forEach((segment) => {
        ctx.moveTo(segment[0], segment[1]);
        ctx.lineTo(segment[2], segment[3]);
      });
      ctx.stroke();
    }
    ctx.restore();
  }

  function drawTrails() {
    if (state.trails.length === 0) return;
    ctx.save();
    ctx.lineCap = "round";
    state.trails.forEach((trail) => {
      const alpha = clamp(trail.life / trail.maxLife, 0, 1) * 0.42;
      const length = 6;
      const cos = Math.cos(trail.angle);
      const sin = Math.sin(trail.angle);
      ctx.strokeStyle = "rgba(236, 244, 255, " + alpha.toFixed(3) + ")";
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(trail.x - cos * length * 0.5, trail.y - sin * length * 0.5);
      ctx.lineTo(trail.x + cos * length * 0.5, trail.y + sin * length * 0.5);
      ctx.stroke();
    });
    ctx.restore();
  }

  function drawGoal(now) {
    const goal = state.goal;
    const pulse = 1 + Math.sin(now / 430) * 0.035;
    ctx.save();
    ctx.translate(goal.x, goal.y);
    const glow = ctx.createRadialGradient(0, 0, 4, 0, 0, goal.r * 1.45);
    glow.addColorStop(0, "rgba(" + COLORS.gold + ", 0.2)");
    glow.addColorStop(1, "rgba(" + COLORS.gold + ", 0)");
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(0, 0, goal.r * 1.45, 0, TAU);
    ctx.fill();

    ctx.save();
    ctx.scale(pulse, pulse);
    ctx.setLineDash([5, 7]);
    ctx.lineDashOffset = -now / 45;
    ctx.strokeStyle = "rgba(" + COLORS.gold + ", 0.78)";
    ctx.lineWidth = 1.8;
    ctx.beginPath();
    ctx.arc(0, 0, goal.r, 0, TAU);
    ctx.stroke();
    ctx.restore();

    ctx.setLineDash([]);
    starPath(0, 0, goal.r * 0.38, goal.r * 0.16, 5);
    ctx.fillStyle = "rgba(" + COLORS.gold + ", 0.88)";
    ctx.fill();

    ctx.fillStyle = "rgba(255, 236, 185, 0.92)";
    ctx.font = "800 11px AidenKR, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("별자리", 0, goal.r + 18);
    ctx.restore();
  }

  function drawFreeItems() {
    state.items.forEach((item) => {
      if (item.capturedBy != null) return;
      drawItem(item);
    });
  }

  function drawCapturedItems() {
    state.items.forEach((item) => {
      if (item.capturedBy == null) return;
      drawItem(item);
    });
  }

  function drawItem(item) {
    const radius = item.radius;
    const scale = radius / (item.drawRadius || radius);
    ctx.save();
    ctx.translate(item.x, item.y);
    ctx.fillStyle = "rgba(2, 6, 14, 0.4)";
    ctx.beginPath();
    ctx.ellipse(0, radius * 0.68, radius * 0.9, radius * 0.32, 0, 0, TAU);
    ctx.fill();
    ctx.scale(scale, scale);

    if (item.kind === "compass") {
      drawCompass(item);
      ctx.restore();
      return;
    }

    ctx.rotate(item.angle);
    switch (item.kind) {
      case "clip":
        drawClip();
        break;
      case "nail":
        drawNail();
        break;
      case "key":
        drawKey();
        break;
      case "ball":
        drawBall();
        break;
      case "stick":
        drawStick();
        break;
      case "eraser":
        drawEraser();
        break;
      case "coin":
        drawCoin();
        break;
      default:
        drawClip();
        break;
    }
    ctx.restore();
  }

  function drawClip() {
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    const wire = ctx.createLinearGradient(-5, -10, 5, 10);
    wire.addColorStop(0, "#f4f9ff");
    wire.addColorStop(0.55, "#cddcef");
    wire.addColorStop(1, "#8497b0");
    ctx.strokeStyle = wire;

    ctx.lineWidth = 2.1;
    ctx.beginPath();
    ctx.moveTo(-3.1, 8.6);
    ctx.lineTo(-3.1, -5.6);
    ctx.arc(0, -5.6, 3.1, Math.PI, 0, false);
    ctx.lineTo(3.1, 5.2);
    ctx.arc(0, 5.2, 3.1, 0, Math.PI, false);
    ctx.lineTo(-3.1, -1.2);
    ctx.stroke();

    ctx.lineWidth = 1.7;
    ctx.beginPath();
    ctx.moveTo(0.9, 7.9);
    ctx.lineTo(0.9, -4.2);
    ctx.arc(-0.3, -4.2, 1.2, 0, Math.PI, true);
    ctx.lineTo(-1.5, 5.4);
    ctx.stroke();

    ctx.strokeStyle = "rgba(255, 255, 255, 0.75)";
    ctx.lineWidth = 0.7;
    ctx.beginPath();
    ctx.moveTo(-3.6, -4.6);
    ctx.lineTo(-3.6, 4.2);
    ctx.stroke();
  }

  function drawNail() {
    const gradient = ctx.createLinearGradient(-3, 0, 3, 0);
    gradient.addColorStop(0, "#f7fbff");
    gradient.addColorStop(0.5, "#c3d2e5");
    gradient.addColorStop(1, "#6d8199");
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.moveTo(-1.7, -7);
    ctx.lineTo(1.7, -7);
    ctx.lineTo(1.7, 7);
    ctx.lineTo(0, 11.5);
    ctx.lineTo(-1.7, 7);
    ctx.closePath();
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(0, -8.2, 4.2, 2.2, 0, 0, TAU);
    ctx.fillStyle = "#dfe9f6";
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.45)";
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(-0.5, -5);
    ctx.lineTo(-0.5, 6);
    ctx.stroke();
  }

  function drawKey() {
    ctx.strokeStyle = "#efcf7c";
    ctx.fillStyle = "#efcf7c";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(-5, 0, 4.6, 0, TAU);
    ctx.stroke();
    ctx.fillRect(-0.8, -1.3, 11, 2.6);
    ctx.fillRect(7, 0.8, 1.8, 4.4);
    ctx.fillRect(10, 0.8, 1.8, 3);
    ctx.fillStyle = "#7a5a16";
    ctx.beginPath();
    ctx.arc(-5, 0, 1.8, 0, TAU);
    ctx.fill();
  }

  function drawBall() {
    const gradient = ctx.createRadialGradient(-3.5, -4.5, 1, 0, 0, 12);
    gradient.addColorStop(0, "#ffffff");
    gradient.addColorStop(0.28, "#e2ecfa");
    gradient.addColorStop(0.7, "#9aacc3");
    gradient.addColorStop(1, "#56657a");
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(0, 0, 10.5, 0, TAU);
    ctx.fill();
    ctx.strokeStyle = "rgba(35, 48, 66, 0.6)";
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillStyle = "rgba(255,255,255,0.75)";
    ctx.beginPath();
    ctx.arc(-3.6, -4.2, 2.1, 0, TAU);
    ctx.fill();
  }

  function drawStick() {
    const gradient = ctx.createLinearGradient(-4, 0, 4, 0);
    gradient.addColorStop(0, "#c9935e");
    gradient.addColorStop(0.5, "#e7b982");
    gradient.addColorStop(1, "#a76b3b");
    ctx.fillStyle = gradient;
    roundedRectPath(-3.2, -13, 6.4, 26, 2.6);
    ctx.fill();
    ctx.strokeStyle = "rgba(110, 68, 30, 0.45)";
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.moveTo(-0.8, -9);
    ctx.lineTo(-0.8, 8);
    ctx.moveTo(1.2, -6);
    ctx.lineTo(1.2, 11);
    ctx.stroke();
  }

  function drawEraser() {
    const gradient = ctx.createLinearGradient(0, -6, 0, 6);
    gradient.addColorStop(0, "#ffc8d8");
    gradient.addColorStop(1, "#ef7fa8");
    ctx.fillStyle = gradient;
    roundedRectPath(-9, -6, 18, 12, 3.2);
    ctx.fill();
    ctx.fillStyle = "rgba(255,255,255,0.82)";
    ctx.fillRect(-8.2, -3.9, 5.4, 7.8);
    ctx.strokeStyle = "rgba(124, 44, 74, 0.3)";
    ctx.lineWidth = 0.8;
    roundedRectPath(-9, -6, 18, 12, 3.2);
    ctx.stroke();
  }

  function drawCoin() {
    const gradient = ctx.createRadialGradient(-2.5, -3.5, 1, 0, 0, 12);
    gradient.addColorStop(0, "#ffe6b0");
    gradient.addColorStop(0.45, "#e0b464");
    gradient.addColorStop(1, "#9c6b2b");
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(0, 0, 10.5, 0, TAU);
    ctx.fill();
    ctx.strokeStyle = "rgba(120, 78, 24, 0.7)";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(0, 0, 8.4, 0, TAU);
    ctx.stroke();
    ctx.fillStyle = "rgba(92, 58, 12, 0.82)";
    ctx.font = "900 6.4px AidenKR, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("100", 0, 0.5);
  }

  function drawCompass(item) {
    ctx.save();
    const rim = ctx.createLinearGradient(0, -18, 0, 18);
    rim.addColorStop(0, "#f4db9a");
    rim.addColorStop(0.5, "#b6883e");
    rim.addColorStop(1, "#6e4c1d");
    ctx.fillStyle = rim;
    ctx.beginPath();
    ctx.arc(0, 0, 18, 0, TAU);
    ctx.fill();
    ctx.fillStyle = "#f4eedf";
    ctx.beginPath();
    ctx.arc(0, 0, 14.4, 0, TAU);
    ctx.fill();
    ctx.strokeStyle = "rgba(115, 94, 58, 0.42)";
    ctx.lineWidth = 0.8;
    for (let i = 0; i < 8; i += 1) {
      const angle = (i * TAU) / 8;
      ctx.beginPath();
      ctx.moveTo(Math.cos(angle) * 11, Math.sin(angle) * 11);
      ctx.lineTo(Math.cos(angle) * 13.2, Math.sin(angle) * 13.2);
      ctx.stroke();
    }

    ctx.save();
    ctx.rotate(item.fieldAngle == null ? -Math.PI / 2 : item.fieldAngle);
    ctx.fillStyle = "#e5484d";
    ctx.beginPath();
    ctx.moveTo(0, -12.4);
    ctx.lineTo(3.2, 0);
    ctx.lineTo(-3.2, 0);
    ctx.closePath();
    ctx.fill();
    ctx.fillStyle = "#fbfdff";
    ctx.beginPath();
    ctx.moveTo(0, 12.4);
    ctx.lineTo(3.2, 0);
    ctx.lineTo(-3.2, 0);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = "rgba(60, 74, 92, 0.45)";
    ctx.lineWidth = 0.7;
    ctx.beginPath();
    ctx.moveTo(0, -12.4);
    ctx.lineTo(0, 12.4);
    ctx.stroke();
    ctx.restore();

    ctx.fillStyle = "#3e3322";
    ctx.beginPath();
    ctx.arc(0, 0, 1.8, 0, TAU);
    ctx.fill();

    ctx.fillStyle = "rgba(72, 58, 34, 0.9)";
    ctx.font = "900 5.5px AidenKR, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("N", 0, -9.4);
    ctx.restore();
  }

  function drawMagnet(magnet, now) {
    const halfLength = magnet.length / 2;
    const halfWidth = magnet.width / 2;
    const selected = magnet.id === state.selectedId;
    ctx.save();
    ctx.translate(magnet.x, magnet.y);
    ctx.rotate(magnet.angle);

    ctx.save();
    ctx.shadowColor = "rgba(0, 0, 0, 0.62)";
    ctx.shadowBlur = 22;
    ctx.shadowOffsetY = 11;
    ctx.fillStyle = "rgba(8, 14, 27, 0.95)";
    roundedRectPath(-halfLength, -halfWidth, magnet.length, magnet.width, 11);
    ctx.fill();
    ctx.restore();

    ctx.save();
    roundedRectPath(-halfLength, -halfWidth, magnet.length, magnet.width, 11);
    ctx.clip();

    const north = ctx.createLinearGradient(0, -halfWidth, 0, halfWidth);
    north.addColorStop(0, "#ff9da8");
    north.addColorStop(0.34, "#ff5a6e");
    north.addColorStop(1, "#a7112e");
    ctx.fillStyle = north;
    ctx.fillRect(0, -halfWidth, halfLength + 1, magnet.width);

    const south = ctx.createLinearGradient(0, -halfWidth, 0, halfWidth);
    south.addColorStop(0, "#b8d3ff");
    south.addColorStop(0.34, "#4c8dff");
    south.addColorStop(1, "#0f3690");
    ctx.fillStyle = south;
    ctx.fillRect(-halfLength - 1, -halfWidth, halfLength + 1, magnet.width);

    const sheen = ctx.createLinearGradient(0, -halfWidth, 0, halfWidth);
    sheen.addColorStop(0, "rgba(255, 255, 255, 0.34)");
    sheen.addColorStop(0.26, "rgba(255, 255, 255, 0.07)");
    sheen.addColorStop(0.62, "rgba(0, 0, 0, 0)");
    sheen.addColorStop(1, "rgba(0, 0, 0, 0.22)");
    ctx.fillStyle = sheen;
    ctx.fillRect(-halfLength, -halfWidth, magnet.length, magnet.width);

    ctx.strokeStyle = "rgba(255, 255, 255, 0.22)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(0, -halfWidth + 3);
    ctx.lineTo(0, halfWidth - 3);
    ctx.stroke();
    ctx.restore();

    roundedRectPath(-halfLength, -halfWidth, magnet.length, magnet.width, 11);
    ctx.strokeStyle = "rgba(255, 255, 255, 0.3)";
    ctx.lineWidth = 1.2;
    ctx.stroke();

    ctx.save();
    roundedRectPath(-halfLength + 4, -halfWidth + 4, magnet.length - 8, 6, 3);
    ctx.fillStyle = "rgba(255, 255, 255, 0.2)";
    ctx.fill();
    ctx.restore();

    ctx.fillStyle = "rgba(255, 255, 255, 0.94)";
    ctx.font = "900 18px AidenKR, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.shadowColor = "rgba(0, 0, 0, 0.4)";
    ctx.shadowBlur = 3;
    ctx.fillText("N", halfLength * 0.47, 1);
    ctx.fillText("S", -halfLength * 0.47, 1);
    ctx.restore();

    if (selected) {
      ctx.save();
      ctx.translate(magnet.x, magnet.y);
      ctx.rotate(magnet.angle);
      const glow = 0.8 + Math.sin(now / 260) * 0.2;
      ctx.setLineDash([7, 5]);
      ctx.lineDashOffset = -now / 80;
      ctx.strokeStyle = "rgba(" + COLORS.volt + ", " + glow.toFixed(2) + ")";
      ctx.lineWidth = 2;
      roundedRectPath(
        -halfLength - 10,
        -halfWidth - 10,
        magnet.length + 20,
        magnet.width + 20,
        16
      );
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();
    }
  }

  /** 자석 가까이에 왔는데 붙지 않는 물건은 이유를 화면에 적어 준다. */
  function drawMaterialLabels() {
    if (state.magnets.length === 0) return;
    state.items.forEach((item) => {
      if (item.magnetic || item.kind === "compass") return;
      let nearest = Infinity;
      state.magnets.forEach((magnet) => {
        nearest = Math.min(nearest, P.distanceToMagnet(magnet, item.x, item.y));
      });
      if (nearest > 118) return;
      const alpha = clamp((118 - nearest) / 46, 0, 1);
      ctx.save();
      ctx.globalAlpha = alpha;
      const y = item.y - item.radius - 15;
      const text = "✕ 안 붙어요";
      ctx.font = "800 10px AidenKR, sans-serif";
      const width = ctx.measureText(text).width + 16;
      roundedRectPath(item.x - width / 2, y - 9, width, 18, 9);
      ctx.fillStyle = "rgba(9, 16, 31, 0.85)";
      ctx.fill();
      ctx.strokeStyle = "rgba(255, 202, 88, 0.5)";
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.fillStyle = "#ffd98a";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(text, item.x, y + 0.5);
      ctx.restore();
    });
  }

  function saveArtwork() {
    try {
      const link = document.createElement("a");
      link.download = "magnet-lab-" + new Date().toISOString().slice(0, 10) + ".png";
      link.href = refs.canvas.toDataURL("image/png");
      document.body.appendChild(link);
      link.click();
      link.remove();
      showToast("📷", "작품을 저장했어요!", "내가 만든 자기장 그림이 사진 파일로 저장됐어요.");
      announce("실험대 그림을 사진 파일로 저장했어요.");
    } catch (error) {
      showToast("📷", "저장을 하지 못했어요", "브라우저가 그림 저장을 막았어요. 화면을 직접 찍어 보세요.");
    }
  }

  function drawSelection() {
    const magnet = state.selectedId != null ? P.findMagnet(state.magnets, state.selectedId) : null;
    if (!magnet) return;
    const cos = Math.cos(magnet.angle);
    const sin = Math.sin(magnet.angle);
    const top = Math.min(
      magnet.y - (Math.abs(cos) * magnet.length + Math.abs(sin) * magnet.width) / 2,
      magnet.y - (Math.abs(sin) * magnet.length + Math.abs(cos) * magnet.width) / 2
    );
    ctx.save();
    ctx.font = "800 10px AidenKR, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const text = magnet.name || "자석";
    const width = ctx.measureText(text).width + 16;
    roundedRectPath(magnet.x - width / 2, top - 34, width, 18, 9);
    ctx.fillStyle = "rgba(9, 16, 31, 0.86)";
    ctx.fill();
    ctx.strokeStyle = "rgba(" + COLORS.volt + ", 0.55)";
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillStyle = "rgba(" + COLORS.volt + ", 0.95)";
    ctx.fillText(text, magnet.x, top - 24.5);
    ctx.restore();
  }

  function drawSparks() {
    if (state.sparks.length === 0) return;
    ctx.save();
    ctx.globalCompositeOperation = "lighter";
    state.sparks.forEach((spark) => {
      const alpha = clamp(spark.life / spark.maxLife, 0, 1);
      ctx.fillStyle = "rgba(" + spark.color + ", " + (alpha * 0.85).toFixed(3) + ")";
      ctx.beginPath();
      ctx.arc(spark.x, spark.y, spark.size * alpha, 0, TAU);
      ctx.fill();
    });
    ctx.restore();
  }

  function roundedRectPath(x, y, width, height, radius) {
    const r = Math.min(radius, Math.abs(width) / 2, Math.abs(height) / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + width, y, x + width, y + height, r);
    ctx.arcTo(x + width, y + height, x, y + height, r);
    ctx.arcTo(x, y + height, x, y, r);
    ctx.arcTo(x, y, x + width, y, r);
    ctx.closePath();
  }

  function starPath(cx, cy, outer, inner, points) {
    ctx.beginPath();
    for (let i = 0; i < points * 2; i += 1) {
      const radius = i % 2 === 0 ? outer : inner;
      const angle = -Math.PI / 2 + (i * Math.PI) / points;
      const x = cx + Math.cos(angle) * radius;
      const y = cy + Math.sin(angle) * radius;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
  }

  /* ────────────────────────────────────────────────────────── animation ── */

  function frame(now) {
    const dt = state.lastFrame ? clamp((now - state.lastFrame) / 1000, 0, 0.04) : 0.016;
    state.lastFrame = now;

    stepWorld(dt);

    if (state.fieldDirty && now - state.lastFieldBuild > 110) {
      rebuildFieldLines();
    }

    draw(now);
    window.requestAnimationFrame(frame);
  }

  /* ─────────────────────────────────────────────────────────── pointer ── */

  function canvasPoint(event) {
    const rect = refs.canvas.getBoundingClientRect();
    return {
      x: clamp(event.clientX - rect.left, 0, state.width),
      y: clamp(event.clientY - rect.top, 0, state.height),
    };
  }

  function hitItem(point) {
    for (let i = state.items.length - 1; i >= 0; i -= 1) {
      const item = state.items[i];
      if (distance(point.x, point.y, item.x, item.y) <= item.radius + 10) return item;
    }
    return null;
  }

  function hitMagnet(point) {
    for (let i = state.magnets.length - 1; i >= 0; i -= 1) {
      const magnet = state.magnets[i];
      const local = P.worldToLocal(magnet, point.x, point.y);
      if (
        Math.abs(local.x) <= magnet.length / 2 + 9 &&
        Math.abs(local.y) <= magnet.width / 2 + 9
      ) {
        return magnet;
      }
    }
    return null;
  }

  function onPointerDown(event) {
    if (event.button != null && event.button !== 0) return;
    initAudio();
    dismissHint();
    refs.canvas.focus({ preventScroll: true });
    const point = canvasPoint(event);
    const item = hitItem(point);

    if (item) {
      P.releaseItem(item);
      item.dragged = true;
      state.dragging = {
        type: "item",
        id: item.id,
        offsetX: item.x - point.x,
        offsetY: item.y - point.y,
      };
      selectMagnet(null);
    } else {
      const magnet = hitMagnet(point);
      if (!magnet) {
        selectMagnet(null);
        return;
      }
      selectMagnet(magnet.id);
      magnet.dragged = true;
      magnet.vx = 0;
      magnet.vy = 0;
      magnet.omega = 0;
      state.dragging = {
        type: "magnet",
        id: magnet.id,
        offsetX: magnet.x - point.x,
        offsetY: magnet.y - point.y,
      };
      playTone(430, 0.05, "sine", 0.025);
    }

    state.fieldDirty = true;
    refs.canvas.classList.add("is-dragging");
    if (refs.canvas.setPointerCapture) {
      try {
        refs.canvas.setPointerCapture(event.pointerId);
      } catch (error) {
        /* pointer capture 미지원 환경 무시 */
      }
    }
    event.preventDefault();
  }

  function onPointerMove(event) {
    if (!state.dragging) return;
    const point = canvasPoint(event);
    if (state.dragging.type === "magnet") {
      const magnet = P.findMagnet(state.magnets, state.dragging.id);
      if (!magnet) return;
      const nextX = clamp(
        point.x + state.dragging.offsetX,
        magnet.length / 2 + 8,
        Math.max(magnet.length / 2 + 8, state.width - magnet.length / 2 - 8)
      );
      const nextY = clamp(
        point.y + state.dragging.offsetY,
        magnet.width / 2 + 8,
        Math.max(magnet.width / 2 + 8, state.height - magnet.width / 2 - 8)
      );
      const moved = distance(nextX, nextY, magnet.x, magnet.y);
      magnet.x = nextX;
      magnet.y = nextY;
      magnet.vx = 0;
      magnet.vy = 0;
      magnet.omega = 0;
      if (state.showFilings) state.filingsDraw += moved;
      state.fieldDirty = true;
      spawnTrail(magnet);
    } else {
      const item = state.items.find((candidate) => candidate.id === state.dragging.id);
      if (!item) return;
      item.x = clamp(point.x + state.dragging.offsetX, item.radius + 4, state.width - item.radius - 4);
      item.y = clamp(point.y + state.dragging.offsetY, item.radius + 4, state.height - item.radius - 4);
      item.vx = 0;
      item.vy = 0;
    }
    event.preventDefault();
  }

  function endDrag() {
    if (state.dragging) {
      if (state.dragging.type === "magnet") {
        const magnet = P.findMagnet(state.magnets, state.dragging.id);
        if (magnet) magnet.dragged = false;
      } else {
        const item = state.items.find((candidate) => candidate.id === state.dragging.id);
        if (item) item.dragged = false;
      }
    }
    state.dragging = null;
    refs.canvas.classList.remove("is-dragging");
  }

  function onPointerUp(event) {
    endDrag();
    if (refs.canvas.releasePointerCapture && event.pointerId != null) {
      try {
        refs.canvas.releasePointerCapture(event.pointerId);
      } catch (error) {
        /* ignore */
      }
    }
  }

  function onKeyDown(event) {
    const key = event.key;
    if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "q", "Q", "e", "E", "f", "F", "Delete", "Backspace", "Escape"].indexOf(key) === -1) {
      return;
    }

    if (state.selectedId == null && state.magnets.length > 0 && key.indexOf("Arrow") === 0) {
      selectMagnet(state.magnets[0].id);
    }
    const magnet = state.selectedId != null ? P.findMagnet(state.magnets, state.selectedId) : null;

    if (key === "Escape") {
      selectMagnet(null);
      event.preventDefault();
      return;
    }
    if (!magnet) return;

    dismissHint();
    const step = event.shiftKey ? 3 : 9;
    const previousX = magnet.x;
    const previousY = magnet.y;
    let handled = true;
    switch (key) {
      case "ArrowLeft":
        magnet.x = Math.max(magnet.length / 2 + 8, magnet.x - step);
        break;
      case "ArrowRight":
        magnet.x = Math.min(state.width - magnet.length / 2 - 8, magnet.x + step);
        break;
      case "ArrowUp":
        magnet.y = Math.max(magnet.width / 2 + 8, magnet.y - step);
        break;
      case "ArrowDown":
        magnet.y = Math.min(state.height - magnet.width / 2 - 8, magnet.y + step);
        break;
      case "q":
      case "Q":
        magnet.angle -= Math.PI / 12;
        break;
      case "e":
      case "E":
        magnet.angle += Math.PI / 12;
        break;
      case "f":
      case "F":
        magnet.angle += Math.PI;
        announce(magnet.name + "의 극을 뒤집었어요.");
        playTone(560, 0.08, "triangle", 0.03);
        break;
      case "Delete":
      case "Backspace":
        removeMagnet(magnet.id);
        break;
      default:
        handled = false;
    }
    if (!handled) return;
    magnet.vx = 0;
    magnet.vy = 0;
    magnet.omega = 0;
    if (state.showFilings) {
      state.filingsDraw += distance(previousX, previousY, magnet.x, magnet.y);
    }
    state.fieldDirty = true;
    event.preventDefault();
  }

  /* ──────────────────────────────────────────────────────────── magnets ── */

  function addMagnet(x, y, angle) {
    if (state.magnets.length >= 8) {
      showToast("🧲", "자석은 8개까지 놓을 수 있어요", "이미 놓은 자석을 옮겨서 실험해 보세요.");
      announce("자석은 8개까지 놓을 수 있어요.");
      return;
    }
    const fallbackX = state.width * 0.36 + (state.magnets.length % 3) * 58;
    const fallbackY = state.height * 0.4 + (state.magnets.length % 2) * 72;
    const magnet = createMagnet({
      x: x == null ? fallbackX : x,
      y: y == null ? fallbackY : y,
      angle: angle == null ? 0 : angle,
    });
    magnet.x = clamp(magnet.x, magnet.length / 2 + 8, state.width - magnet.length / 2 - 8);
    magnet.y = clamp(magnet.y, magnet.width / 2 + 8, state.height - magnet.width / 2 - 8);
    state.magnets.push(magnet);
    selectMagnet(magnet.id);
    state.fieldDirty = true;
    playTone(470, 0.06, "sine", 0.025);
    announce(magnet.name + "을 놓았어요. 자석을 끌어 움직여 보세요.");
  }

  function addItem(kind) {
    const blueprint = ITEM_TYPES[kind];
    if (!blueprint) return;
    if (state.items.length >= 26) {
      showToast("🧺", "물건이 가득 찼어요", "실험대를 비우고 다시 놓아 보세요.");
      announce("물건이 가득 찼어요. 실험대를 비우고 다시 놓아 보세요.");
      return;
    }
    let x = state.width * 0.68;
    let y = state.height * 0.5;
    for (let attempt = 0; attempt < 40; attempt += 1) {
      const candidateX = randomBetween(state.width * 0.5, state.width * 0.9);
      const candidateY = randomBetween(state.height * 0.18, state.height * 0.84);
      const tooClose = state.magnets.some(
        (magnet) => P.distanceToMagnet(magnet, candidateX, candidateY) < 55
      );
      if (!tooClose) {
        x = candidateX;
        y = candidateY;
        break;
      }
    }
    state.items.push(createItem(kind, x, y));
    playTone(620, 0.06, "sine", 0.025);
    announce(blueprint.label + "을 놓았어요.");
    if (state.mode === "mission" && state.missionDone) {
      /* 완료한 실험에서도 자유롭게 더 놓아 볼 수 있다. */
    }
  }

  function removeMagnet(id) {
    const index = state.magnets.findIndex((magnet) => magnet.id === id);
    if (index === -1) return;
    const magnet = state.magnets[index];
    state.items.forEach((item) => {
      if (item.capturedBy === id) P.releaseItem(item);
    });
    state.magnets.splice(index, 1);
    if (state.selectedId === id) selectMagnet(null);
    state.fieldDirty = true;
    announce(magnet.name + "을 실험대에서 치웠어요.");
  }

  function selectMagnet(id) {
    state.selectedId = id;
    const magnet = id != null ? P.findMagnet(state.magnets, id) : null;
    if (!magnet) {
      refs.selectionToolbar.hidden = true;
      return;
    }
    refs.selectedName.textContent = magnet.name || "자석";
    refs.selectionToolbar.hidden = false;
    dismissHint();
    announce(magnet.name + " 선택. 방향키로 움직이고, Q와 E로 돌려요.");
  }

  function rotateSelected(amount) {
    const magnet = state.selectedId != null ? P.findMagnet(state.magnets, state.selectedId) : null;
    if (!magnet) return;
    magnet.angle += amount;
    magnet.omega = 0;
    state.fieldDirty = true;
    playTone(500, 0.05, "sine", 0.02);
  }

  function flipSelected() {
    const magnet = state.selectedId != null ? P.findMagnet(state.magnets, state.selectedId) : null;
    if (!magnet) return;
    magnet.angle += Math.PI;
    magnet.omega = 0;
    state.fieldDirty = true;
    playTone(560, 0.08, "triangle", 0.03);
    announce(magnet.name + "의 N극과 S극을 뒤집었어요.");
  }

  /* ──────────────────────────────────────────────────────────────── UI ── */

  function updateViewChips() {
    refs.fieldToggle.setAttribute("aria-pressed", String(state.showField));
    refs.filingsToggle.setAttribute("aria-pressed", String(state.showFilings));

    let label = "〰️ 자기장 ON";
    let off = false;
    if (state.showFilings && state.showField) label = "✨ 자기장 + 철가루";
    else if (state.showFilings) label = "✨ 철가루 관찰 중";
    else if (!state.showField) {
      label = "관찰 도구 OFF";
      off = true;
    }
    refs.stageViewChip.textContent = label;
    refs.stageViewChip.dataset.off = String(off);
  }

  function updateMissionUI() {
    const mission = MISSIONS[state.missionIndex];
    if (!mission) return;
    refs.missionStep.textContent = "실험 " + (state.missionIndex + 1) + " / " + MISSION_TOTAL;
    refs.missionTitle.textContent = mission.title;
    refs.missionGoal.textContent = mission.goal;
    refs.missionTip.textContent = mission.tip;
    refs.missionDifficulty.textContent = mission.difficulty;
    refs.missionCount.textContent = state.missionIndex + 1 + " / " + MISSION_TOTAL;

    refs.missionWhy.hidden = !state.missionDone;
    refs.whyText.textContent = state.missionDone ? mission.why : "";
    refs.missionNext.hidden = !state.missionDone;
    refs.missionNext.textContent =
      state.missionIndex < MISSIONS.length - 1 ? "다음 실험 →" : "자유 실험 →";

    refs.stageMissionChip.textContent =
      state.mode === "free"
        ? "자유 실험 · 정답은 없어요"
        : "실험 " + (state.missionIndex + 1) + " · " + mission.title;

    refs.modeMission.setAttribute("aria-selected", String(state.mode === "mission"));
    refs.modeFree.setAttribute("aria-selected", String(state.mode === "free"));
    renderMissionDots();
    updateStats();
  }

  function updateStats() {
    refs.statFound.textContent = String(state.completed.size);
    refs.statMission.textContent =
      state.mode === "free" ? "자유" : state.missionIndex + 1 + " / " + MISSION_TOTAL;
    refs.missionCount.textContent = state.missionIndex + 1 + " / " + MISSION_TOTAL;
  }

  function renderMissionDots() {
    refs.missionDots.textContent = "";
    MISSIONS.forEach((mission, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "mission-dot";
      const done = state.completed.has(mission.id);
      button.textContent = done ? "★" : String(index + 1);
      button.setAttribute(
        "aria-label",
        "실험 " + (index + 1) + ": " + mission.title + (done ? " (완료)" : "")
      );
      if (index === state.missionIndex) button.setAttribute("aria-current", "true");
      if (done) button.classList.add("is-complete");
      button.addEventListener("click", () => {
        state.missionIndex = index;
        if (state.mode === "mission") setupMission(false);
        else setMode("mission");
      });
      refs.missionDots.appendChild(button);
    });
  }

  function completeMission() {
    const mission = MISSIONS[state.missionIndex];
    state.missionDone = true;
    state.completed.add(mission.id);
    saveProgress();
    updateMissionUI();
    launchConfetti();
    playChime();
    showToast("⭐", "실험 성공! " + mission.title, mission.why);
    announce("실험 완료! " + mission.title + ". " + mission.why);
  }

  function showToast(icon, title, text) {
    refs.toastIcon.textContent = icon;
    refs.toastTitle.textContent = title;
    refs.toastText.textContent = text;
    refs.toast.classList.add("is-show");
    if (state.toastTimer) window.clearTimeout(state.toastTimer);
    state.toastTimer = window.setTimeout(() => {
      refs.toast.classList.remove("is-show");
    }, 4600);
  }

  function launchConfetti() {
    if (prefersReducedMotion()) return;
    const colors = ["#d7ff00", "#5cf2c2", "#ff5a6e", "#4c8dff", "#ffca58", "#ffffff"];
    for (let i = 0; i < 42; i += 1) {
      const piece = document.createElement("span");
      piece.className = "confetti";
      piece.style.left = Math.round(Math.random() * 100) + "%";
      piece.style.background = colors[i % colors.length];
      piece.style.width = 6 + Math.random() * 7 + "px";
      piece.style.height = 10 + Math.random() * 8 + "px";
      piece.style.setProperty("--drift", (Math.random() - 0.5) * 180 + "px");
      piece.style.setProperty("--spin", Math.random() * 760 - 380 + "deg");
      piece.style.animationDelay = Math.random() * 0.25 + "s";
      piece.style.animationDuration = 1.3 + Math.random() * 0.8 + "s";
      refs.confetti.appendChild(piece);
      window.setTimeout(() => piece.remove(), 2900);
    }
  }

  function announce(message) {
    refs.live.textContent = "";
    window.requestAnimationFrame(() => {
      refs.live.textContent = message;
    });
  }

  function dismissHint() {
    if (state.hintDismissed) return;
    state.hintDismissed = true;
    refs.stageHint.classList.add("is-hidden");
    refs.stageHint.setAttribute("aria-hidden", "true");
  }

  /* ──────────────────────────────────────────────────────────── audio ── */

  function initAudio() {
    if (!state.soundOn || audioContext) return;
    const AudioCtor = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtor) return;
    try {
      audioContext = new AudioCtor();
    } catch (error) {
      audioContext = null;
    }
  }

  function playTone(frequency, duration, type, volume) {
    if (!state.soundOn) return;
    initAudio();
    if (!audioContext) return;
    try {
      if (audioContext.state === "suspended") audioContext.resume();
      const now = audioContext.currentTime;
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      oscillator.type = type || "sine";
      oscillator.frequency.setValueAtTime(frequency, now);
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(volume || 0.04, now + 0.012);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);
      oscillator.connect(gain);
      gain.connect(audioContext.destination);
      oscillator.start(now);
      oscillator.stop(now + duration + 0.03);
    } catch (error) {
      /* 소리 재생 실패는 놀이를 막지 않는다. */
    }
  }

  function playChime() {
    if (!state.soundOn) return;
    playTone(523.25, 0.22, "triangle", 0.045);
    window.setTimeout(() => playTone(659.25, 0.22, "triangle", 0.04), 110);
    window.setTimeout(() => playTone(783.99, 0.3, "triangle", 0.045), 220);
  }

  function updateSoundButton() {
    refs.soundButton.setAttribute("aria-pressed", String(state.soundOn));
    refs.soundButton.setAttribute("aria-label", state.soundOn ? "효과음 끄기" : "효과음 켜기");
    refs.soundButton.textContent = state.soundOn ? "🔊 소리" : "🔇 소리 끔";
  }

  /* ─────────────────────────────────────────────────────────── wiring ── */

  function onTabKeyDown(event) {
    if (["ArrowLeft", "ArrowRight", "Home", "End"].indexOf(event.key) === -1) return;
    const goingRight = event.key === "ArrowRight" || event.key === "End";
    const nextMode = goingRight ? "free" : "mission";
    event.preventDefault();
    if (nextMode === "free" && state.mode !== "free") {
      setMode("free");
      announce("자유 실험실이에요. 자석과 물건을 마음껏 놓아 보세요.");
    } else if (nextMode === "mission" && state.mode !== "mission") {
      setMode("mission");
      announce("미션 랩이에요. 실험대를 새로 준비했어요.");
    }
    (nextMode === "free" ? refs.modeFree : refs.modeMission).focus();
  }

  document.querySelectorAll("[data-add-magnet]").forEach((button) => {
    button.addEventListener("click", () => {
      initAudio();
      dismissHint();
      addMagnet();
    });
  });

  document.querySelectorAll("[data-add-item]").forEach((button) => {
    button.addEventListener("click", () => {
      initAudio();
      dismissHint();
      addItem(button.getAttribute("data-add-item"));
    });
  });

  refs.resetScene.addEventListener("click", () => {
    clearScene();
  });

  refs.fieldToggle.addEventListener("click", () => {
    state.showField = !state.showField;
    state.fieldDirty = true;
    if (!state.showField) state.fieldLines = [];
    updateViewChips();
    announce(state.showField ? "자기장 보기를 켰어요." : "자기장 보기를 껐어요.");
  });

  refs.filingsToggle.addEventListener("click", () => {
    state.showFilings = !state.showFilings;
    state.fieldDirty = true;
    if (!state.showFilings) state.trails = [];
    updateViewChips();
    announce(state.showFilings ? "철가루 보기를 켰어요. 자석 주변의 곡선을 관찰해 보세요." : "철가루 보기를 껐어요.");
  });

  refs.powerRange.addEventListener("input", () => {
    state.power = Number(refs.powerRange.value) / 100;
    state.magnets.forEach((magnet) => {
      magnet.power = state.power;
    });
    refs.powerOutput.textContent =
      state.power <= 0.8 ? "약하게" : state.power >= 1.2 ? "강하게" : "보통";
    state.fieldDirty = true;
    state.fieldLines = [];
  });

  if (refs.saveArtwork) {
    refs.saveArtwork.addEventListener("click", saveArtwork);
  }

  refs.soundButton.addEventListener("click", () => {
    state.soundOn = !state.soundOn;
    updateSoundButton();
    saveProgress();
    if (state.soundOn) playTone(660, 0.09, "triangle", 0.035);
  });

  refs.flipButton.addEventListener("click", flipSelected);
  refs.rotateLeft.addEventListener("click", () => rotateSelected(-Math.PI / 12));
  refs.rotateRight.addEventListener("click", () => rotateSelected(Math.PI / 12));
  refs.deleteMagnet.addEventListener("click", () => {
    if (state.selectedId != null) removeMagnet(state.selectedId);
  });

  refs.modeMission.addEventListener("keydown", onTabKeyDown);
  refs.modeFree.addEventListener("keydown", onTabKeyDown);

  refs.modeMission.addEventListener("click", () => {
    if (state.mode === "mission") return;
    setMode("mission");
    announce("미션 랩이에요. 실험대를 새로 준비했어요.");
  });

  refs.modeFree.addEventListener("click", () => {
    if (state.mode === "free") return;
    setMode("free");
    announce("자유 실험실이에요. 자석과 물건을 마음껏 놓아 보세요.");
  });

  refs.startMission.addEventListener("click", () => {
    setMode("mission");
  });

  refs.missionReset.addEventListener("click", () => {
    setupMission(true);
    announce("실험대를 다시 준비했어요.");
  });

  refs.missionNext.addEventListener("click", () => {
    if (!state.missionDone) return;
    if (state.missionIndex < MISSIONS.length - 1) {
      state.missionIndex += 1;
      setupMission(false);
      playTone(660, 0.1, "triangle", 0.03);
    } else {
      setMode("free");
      showToast("🏅", "자석 실험을 모두 마쳤어요!", "이제 자유 실험실에서 마음껏 놀아 보세요.");
      announce("모든 실험을 마쳤어요. 자유 실험실에서 마음껏 놀아 보세요.");
    }
  });

  refs.helpButton.addEventListener("click", () => {
    if (typeof refs.helpDialog.showModal === "function") refs.helpDialog.showModal();
    else refs.helpDialog.setAttribute("open", "");
  });
  refs.helpClose.addEventListener("click", () => refs.helpDialog.close());
  refs.helpStart.addEventListener("click", () => refs.helpDialog.close());
  refs.helpDialog.addEventListener("click", (event) => {
    if (event.target === refs.helpDialog) refs.helpDialog.close();
  });

  refs.canvas.addEventListener("pointerdown", onPointerDown);
  refs.canvas.addEventListener("pointermove", onPointerMove);
  refs.canvas.addEventListener("pointerup", onPointerUp);
  refs.canvas.addEventListener("pointercancel", onPointerUp);
  refs.canvas.addEventListener("lostpointercapture", endDrag);
  refs.canvas.addEventListener("keydown", onKeyDown);

  window.addEventListener("blur", endDrag);
  window.addEventListener("resize", queueResize);
  if (typeof ResizeObserver === "function") {
    new ResizeObserver(queueResize).observe(refs.stageShell);
  }

  if (typeof reduceMotionQuery.addEventListener === "function") {
    reduceMotionQuery.addEventListener("change", () => {
      state.lastFrame = 0;
    });
  }

  /* ────────────────────────────────────────────────────────────── boot ── */

  function boot() {
    const saved = loadProgress();
    if (saved) {
      state.completed = new Set(saved.completed);
      state.soundOn = saved.soundOn;
      const firstIncomplete = MISSIONS.findIndex((mission) => !state.completed.has(mission.id));
      state.missionIndex = firstIncomplete >= 0 ? firstIncomplete : saved.missionIndex;
    }
    updateSoundButton();
    resizeCanvas(true);
    setMode("mission");
    window.requestAnimationFrame(frame);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
