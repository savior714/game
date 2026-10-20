/**
 * Track director: decides which obstacles, amber trails and power-ups appear
 * ahead of the runner. Pure data (no three.js, no DOM) so it can be simulated
 * headless; the presentation layer turns each descriptor into a pooled mesh.
 */

import { HAZARD, ROAD, RUN } from "./constants.js";
import { getBaseSpeed } from "./run-model.js";
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

  // A hazard the player already met in this lane needs a full reaction beat
  // before the next one arrives. Four metres was fine at 13.5 m/s and far too
  // tight at 24 m/s, so the clearance is measured in seconds.
  const SAME_LANE_SECONDS = 0.95;

  function laneClear(lane, z, seconds = SAME_LANE_SECONDS) {
    const window = Math.max(4, getBaseSpeed(z) * seconds);
    for (const entry of recent) {
      if (entry.lane === lane && Math.abs(entry.z - z) < window) {
        return false;
      }
    }
    return true;
  }

  function clearLanes(z, seconds = SAME_LANE_SECONDS) {
    const lanes = [0, 1, 2].filter((lane) => laneClear(lane, z, seconds));
    return lanes.length ? lanes : [0, 1, 2];
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

  /**
   * Generates every pattern whose trigger point is now inside the horizon.
   *
   * Spacing is expressed in *seconds*, not metres: at 24 m/s a 16 m gap is
   * 0.67 s, which is not a fair reaction window for a child on a tablet. The
   * director asks for ~1.4-1.8 s between clusters and shrinks that only as the
   * run's difficulty climbs.
   */
  function update(playerDistance, horizon = HAZARD.spawnAhead) {
    const spawns = [];
    const limit = playerDistance + horizon;
    const speed = getBaseSpeed(playerDistance);
    const secondsBetween = (difficulty) => 1.8 - difficulty * 0.45;
    const gapFor = (difficulty, multiplier = 1) =>
      speed * secondsBetween(difficulty) * multiplier * randRange(0.92, 1.12);
    let safety = 0;
    while (nextZ < limit && safety < 24) {
      safety += 1;
      const difficulty = difficultyAt(nextZ);
      const sinceFull = nextZ - lastFullWidthZ;
      // The opening stretch is a lesson, not a gauntlet: one hazard at a time
      // until the child has met the jump, then the full vocabulary.
      const early = nextZ < 140;
      // Full-width bone arches need the longest runway: never closer than
      // 200 m, and rarer than the rest of the vocabulary.
      const weightRibs = sinceFull > 200 && nextZ > 260 ? 6 + difficulty * 5 : 0;
      const weightGeyser = nextZ - lastGeyserZ > 90 && nextZ > 160 ? 9 + difficulty * 6 : 0;
      const pattern = pickWeighted([
        { id: "single", weight: early ? 46 : 34 },
        { id: "pair", weight: early ? 0 : 10 + difficulty * 10 },
        { id: "jumpLine", weight: early ? 24 : 20 },
        { id: "ribs", weight: weightRibs },
        { id: "geyser", weight: weightGeyser },
        { id: "slalom", weight: early ? 0 : 7 + difficulty * 8 },
      ]);

      let advance = gapFor(difficulty);
      let lastZ = nextZ;

      // A two-lane wall is only fair when every lane is fresh; otherwise the
      // player is asked to swerve into a lane they just left.
      let chosen = pattern;
      if (chosen.id === "pair" && clearLanes(nextZ).length < 3) {
        chosen = { id: "single" };
      }

      if (chosen.id === "single") {
        const lane = pick(clearLanes(nextZ));
        const type = pickWeighted([
          { id: "rock", weight: 38 },
          { id: "ptero", weight: 24 },
          { id: "log", weight: 38 },
        ]).id;
        const hazard = makeHazard(type, lane, nextZ);
        spawns.push(hazard);
        noteHazard(hazard);
        // A trail through the open side teaches the dodge and pays the fuel.
        const openLane = type === "ptero" ? lane : freeLane(nextZ, (lane + 1 + randInt(0, 1)) % 3);
        if (type === "ptero") {
          addAmberLine(spawns, lane, nextZ - 13, randInt(4, 5), 2.3, 0.85);
        } else {
          addAmberLine(spawns, openLane, nextZ - 14, randInt(4, 6), 2.4);
        }
        advance = gapFor(difficulty);
      } else if (chosen.id === "pair") {
        const open = pick(clearLanes(nextZ));
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
        addAmberLine(spawns, open, nextZ - 12, randInt(4, 5), 2.5);
        advance = gapFor(difficulty, 1.12);
      } else if (chosen.id === "jumpLine") {
        const lane = pick(clearLanes(nextZ));
        const hazard = makeHazard("log", lane, nextZ);
        spawns.push(hazard);
        noteHazard(hazard);
        addAmberLine(spawns, lane, nextZ - 9, 5, 4.2, 0.85, 1.05);
        // The follow-up only appears once the jump has had time to land, and
        // never in a lane the player is about to be trapped in.
        if (difficulty > 0.4 && Math.random() < 0.4) {
          const options = [0, 1, 2].filter((l) => l !== lane && laneClear(l, nextZ + speed * 1.1));
          const other = options.length ? pick(options) : (lane + 1) % 3;
          const second = makeHazard("rock", other, nextZ + speed * 1.1);
          spawns.push(second);
          noteHazard(second);
          lastZ = second.z;
        }
        advance = gapFor(difficulty, 1.05);
      } else if (chosen.id === "ribs") {
        // Nothing else may share the arch's beat: it is the one pattern that
        // owns all three lanes at once.
        nextZ = Math.max(nextZ, lastHazardZ + speed * 1.35);
        const hazard = makeHazard("ribs", 1, nextZ);
        hazard.halfWidth = ROAD.halfWidth - 0.25;
        spawns.push(hazard);
        noteHazard(hazard);
        lastFullWidthZ = nextZ;
        addAmberLine(spawns, randInt(0, 2), nextZ - 16, 4, 2.8);
        advance = gapFor(difficulty, 1.3);
      } else if (chosen.id === "geyser") {
        const lane = pick(clearLanes(nextZ));
        const hazard = makeHazard("geyser", lane, nextZ);
        spawns.push(hazard);
        noteHazard(hazard);
        lastGeyserZ = nextZ;
        const open = freeLane(nextZ, (lane + 1) % 3);
        addAmberLine(spawns, open, nextZ - 12, randInt(4, 5), 2.6);
        advance = gapFor(difficulty, 1.05);
      } else if (chosen.id === "slalom") {
        // Two hazards in alternating lanes, forcing a diagonal line. The second
        // sits a full lane-change apart in time, never in distance.
        const firstLane = pick(clearLanes(nextZ));
        const secondOptions = [0, 1, 2].filter(
          (l) => l !== firstLane && laneClear(l, nextZ + speed * 1.15),
        );
        const secondLane = secondOptions.length ? pick(secondOptions) : (firstLane + 1) % 3;
        const first = makeHazard(pick(["rock", "log"]), firstLane, nextZ);
        const second = makeHazard(pick(["rock", "log", "ptero"]), secondLane, nextZ + speed * 1.15);
        spawns.push(first, second);
        noteHazard(first);
        noteHazard(second);
        addAmberLine(spawns, (firstLane + 1) % 3, nextZ + 3, 4, 2.6);
        lastZ = second.z;
        advance = gapFor(difficulty, 1.15);
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
      nextZ += Math.max(speed * 0.9, advance);
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
