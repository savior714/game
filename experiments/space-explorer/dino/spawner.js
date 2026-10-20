/**
 * Track director: decides which obstacles, amber trails and power-ups appear
 * ahead of the runner. Pure data (no three.js, no DOM) so it can be simulated
 * headless; the presentation layer turns each descriptor into a pooled mesh.
 */

import { HAZARD, ROAD, RUN } from "./constants.js";
import { clamp, clamp01, pick, pickWeighted, randInt, randRange } from "./util.js";

export const HAZARD_TYPES = Object.freeze({
  rock: Object.freeze({
    type: "rock",
    halfWidth: HAZARD.rockHalfWidth,
    bottom: 0,
    top: 1.45,
    depth: 1.0,
    avoid: "jump",
    hint: "바위는 옆으로 피해요",
  }),
  log: Object.freeze({
    type: "log",
    halfWidth: HAZARD.logHalfWidth,
    bottom: 0,
    top: 0.9,
    depth: 0.95,
    avoid: "jump",
    hint: "통나무는 점프!",
  }),
  ribs: Object.freeze({
    type: "ribs",
    halfWidth: ROAD.halfWidth - 0.3,
    bottom: 1.06,
    top: 3.8,
    depth: 1.25,
    avoid: "slide",
    hint: "뼈 아치는 슬라이드!",
  }),
  ptero: Object.freeze({
    type: "ptero",
    halfWidth: HAZARD.pteroHalfWidth,
    bottom: 1.03,
    top: 3.7,
    depth: 1.15,
    avoid: "slide",
    hint: "익룡 아래로 미끄러져요",
  }),
  geyser: Object.freeze({
    type: "geyser",
    halfWidth: HAZARD.geyserHalfWidth,
    bottom: 0,
    top: 5.4,
    depth: 1.15,
    avoid: "dodge",
    hint: "간헐천은 솟기 전에 피해요",
  }),
});

const LANES = ROAD.lanes;

function laneX(lane) {
  return LANES[clamp(lane, 0, 2)];
}

function laneOf(x) {
  let best = 0;
  let bestDelta = Infinity;
  for (let i = 0; i < LANES.length; i += 1) {
    const delta = Math.abs(LANES[i] - x);
    if (delta < bestDelta) {
      bestDelta = delta;
      best = i;
    }
  }
  return best;
}

function makeHazard(type, lane, z) {
  const def = HAZARD_TYPES[type];
  return {
    kind: "hazard",
    type: def.type,
    x: laneX(lane),
    lane,
    z,
    halfWidth: def.halfWidth,
    bottom: def.bottom,
    top: def.top,
    depth: def.depth,
    avoid: def.avoid,
    hint: def.hint,
    erupting: def.type !== "geyser",
    warning: false,
    phase: Math.random(),
    collected: false,
    disabled: false,
  };
}

function makeAmber(x, y, z) {
  return { kind: "amber", x, y, z, collected: false };
}

function makePickup(kind, lane, z) {
  return { kind, x: laneX(lane), y: 1.15, z, collected: false, lane };
}

export function createSpawner() {
  let nextZ = 0;
  let lastFullWidthZ = -999;
  let lastHazardZ = -999;
  let lastPowerupZ = -120;
  let lastGeyserZ = -999;
  let spawned = 0;
  const recent = [];

  function reset(atDistance = 0) {
    const start = Math.max(0, atDistance);
    nextZ = start + RUN.firstHazardDistance;
    lastFullWidthZ = start - 240;
    lastHazardZ = start;
    lastPowerupZ = start - 140;
    lastGeyserZ = start - 140;
    spawned = 0;
    recent.length = 0;
  }
  reset();

  function difficultyAt(z) {
    return clamp01((z - RUN.firstHazardDistance) / 1700);
  }

  function noteHazard(hazard) {
    recent.push({ lane: hazard.lane, z: hazard.z });
    if (recent.length > 10) {
      recent.shift();
    }
    lastHazardZ = Math.max(lastHazardZ, hazard.z);
  }

  function laneFree(lane, z, tolerance = 4) {
    for (const entry of recent) {
      if (entry.lane === lane && Math.abs(entry.z - z) < tolerance) {
        return false;
      }
    }
    return true;
  }

  function freeLane(z, preferred = null) {
    if (preferred !== null && laneFree(preferred, z)) {
      return preferred;
    }
    const order = [0, 1, 2].sort(() => Math.random() - 0.5);
    for (const lane of order) {
      if (laneFree(lane, z)) {
        return lane;
      }
    }
    return randInt(0, 2);
  }

  function addAmberLine(spawns, lane, z, count, spacing, baseY = 1.0, arc = 0) {
    const x = laneX(lane);
    for (let i = 0; i < count; i += 1) {
      const t = count > 1 ? i / (count - 1) : 0.5;
      const y = baseY + Math.sin(t * Math.PI) * arc;
      spawns.push(makeAmber(x, y, z + i * spacing));
    }
  }

  /** Generates every pattern whose trigger point is now inside the horizon. */
  function update(playerDistance, horizon = HAZARD.spawnAhead) {
    const spawns = [];
    const limit = playerDistance + horizon;
    let safety = 0;
    while (nextZ < limit && safety < 24) {
      safety += 1;
      const difficulty = difficultyAt(nextZ);
      const sinceFull = nextZ - lastFullWidthZ;
      const weightRibs = sinceFull > 120 ? 9 + difficulty * 8 : 0;
      const weightGeyser = nextZ - lastGeyserZ > 70 ? 10 + difficulty * 8 : 0;
      const pattern = pickWeighted([
        { id: "single", weight: 34 },
        { id: "pair", weight: 12 + difficulty * 12 },
        { id: "jumpLine", weight: 18 },
        { id: "ribs", weight: weightRibs },
        { id: "geyser", weight: weightGeyser },
        { id: "slalom", weight: 8 + difficulty * 10 },
      ]);

      let advance = randRange(16, 25) - difficulty * 4;
      let lastZ = nextZ;

      if (pattern.id === "single") {
        const lane = randInt(0, 2);
        const type = pickWeighted([
          { id: "rock", weight: 38 },
          { id: "ptero", weight: 24 },
          { id: "log", weight: 38 },
        ]).id;
        const hazard = makeHazard(type, lane, nextZ);
        spawns.push(hazard);
        noteHazard(hazard);
        if (Math.random() < 0.55) {
          const trailLane = freeLane(nextZ - 14);
          addAmberLine(spawns, trailLane, nextZ - 15, randInt(3, 5), 2.4);
        }
        advance = randRange(18, 27) - difficulty * 5;
      } else if (pattern.id === "pair") {
        const open = randInt(0, 2);
        const type = pickWeighted([
          { id: "rock", weight: 46 },
          { id: "ptero", weight: 28 },
          { id: "log", weight: 26 },
        ]).id;
        for (let lane = 0; lane < 3; lane += 1) {
          if (lane === open) {
            continue;
          }
          const hazard = makeHazard(type, lane, nextZ + (lane === 1 ? 2.5 : 0));
          spawns.push(hazard);
          noteHazard(hazard);
        }
        if (Math.random() < 0.7) {
          addAmberLine(spawns, open, nextZ - 12, 4, 2.6);
        }
        advance = randRange(22, 30) - difficulty * 4;
      } else if (pattern.id === "jumpLine") {
        const lane = randInt(0, 2);
        const hazard = makeHazard("log", lane, nextZ);
        spawns.push(hazard);
        noteHazard(hazard);
        addAmberLine(spawns, lane, nextZ - 9, 5, 4.5, 0.85, 1.1);
        if (difficulty > 0.35 && Math.random() < 0.5) {
          const other = (lane + 1 + randInt(0, 1)) % 3;
          const second = makeHazard("rock", other, nextZ + 16);
          spawns.push(second);
          noteHazard(second);
          lastZ = second.z;
        }
        advance = randRange(24, 32) - difficulty * 4;
      } else if (pattern.id === "ribs") {
        const hazard = makeHazard("ribs", 1, nextZ);
        hazard.halfWidth = ROAD.halfWidth - 0.25;
        spawns.push(hazard);
        noteHazard(hazard);
        lastFullWidthZ = nextZ;
        addAmberLine(spawns, randInt(0, 2), nextZ - 16, 4, 2.8);
        advance = randRange(34, 44);
      } else if (pattern.id === "geyser") {
        const lane = randInt(0, 2);
        const hazard = makeHazard("geyser", lane, nextZ);
        spawns.push(hazard);
        noteHazard(hazard);
        lastGeyserZ = nextZ;
        const free = freeLane(nextZ, (lane + 1) % 3);
        addAmberLine(spawns, free, nextZ - 10, 4, 2.8);
        advance = randRange(26, 36);
      } else if (pattern.id === "slalom") {
        // Two hazards in alternating lanes, forcing a diagonal line.
        const firstLane = randInt(0, 2);
        const secondLane = (firstLane + (Math.random() < 0.5 ? 1 : 2)) % 3;
        const first = makeHazard(pick(["rock", "log"]), firstLane, nextZ);
        const second = makeHazard(pick(["rock", "log", "ptero"]), secondLane, nextZ + 17);
        spawns.push(first, second);
        noteHazard(first);
        noteHazard(second);
        addAmberLine(spawns, (firstLane + 1) % 3, nextZ + 3, 3, 3);
        lastZ = second.z;
        advance = randRange(30, 38);
      }

      // Power-ups live between hazard clusters.
      const afterCluster = Math.max(lastZ, nextZ + advance * 0.45);
      if (afterCluster - lastPowerupZ > 140) {
        if (Math.random() < 0.28) {
          const lane = freeLane(afterCluster, laneOf(0));
          spawns.push(makePickup("shield", lane, afterCluster));
        } else {
          const lane = freeLane(afterCluster, laneOf(0));
          spawns.push(makePickup("bait", lane, afterCluster));
        }
        lastPowerupZ = afterCluster;
      }

      spawned += 1;
      nextZ += Math.max(15, advance);
      lastHazardZ = Math.max(lastHazardZ, lastZ);
    }
    return spawns;
  }

  return {
    update,
    reset,
    get nextSpawnZ() {
      return nextZ;
    },
    get count() {
      return spawned;
    },
  };
}
