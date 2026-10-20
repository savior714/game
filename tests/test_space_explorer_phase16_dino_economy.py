"""Phase 16 regressions: the amber survival economy and fair obstacle spacing.

Two player complaints drove this phase:

* obstacles arrived too fast to dodge, because clusters were spaced in metres
  (a 16 m gap is 1.7 s at 13.5 m/s but only 0.67 s at 24 m/s), and
* amber was purely decorative — running without collecting cost nothing.

The contract pinned here:

* amber is the survival currency: each pickup hands distance back to the
  runner and the HUD bar is scaled to the real cap,
* hazard clusters are spaced in *seconds*, never block all three lanes and
  never repeat in the same lane faster than a child can react,
* a player who never steers at amber is caught, while a player who collects
  keeps the rex at distance for a full five-minute run.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments" / "space-explorer"
DINO = EXPERIMENTS / "dino"
SCRIPT = EXPERIMENTS / "dino-escape.js"
HUD = DINO / "hud.js"
CONSTANTS = DINO / "constants.js"


def _run_node(source: str) -> dict:
    node = shutil.which("node")
    if not node:
        return {}
    result = subprocess.run(
        [node, "--input-type=module", "-e", source],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


_COLLECTOR = """
import { HAZARD } from "./experiments/space-explorer/dino/constants.js";
import { createRunState, stepRun, collectAmber } from "./experiments/space-explorer/dino/run-model.js";
import { createSpawner } from "./experiments/space-explorer/dino/spawner.js";
import { createPlayerState, resetPlayer, stepPlayer } from "./experiments/space-explorer/dino/player.js";

// ``skill`` is how often the runner actually steers at the nearest amber; the
// runner itself uses the real player physics and the real run model.
function simulate({ skill, seconds = 300, seed = 7 }) {
  let rnd = seed;
  const next = () => (rnd = (rnd * 1664525 + 1013904223) % 4294967296) / 4294967296;
  const run = createRunState();
  const spawner = createSpawner();
  const player = createPlayerState();
  resetPlayer(player, 0);
  const ambers = [];
  let caughtAt = null;
  let collected = 0;
  const dt = 1 / 60;
  for (let frame = 0; frame < seconds * 60; frame += 1) {
    for (const descriptor of spawner.update(run.distance, HAZARD.spawnAhead)) {
      if (descriptor.kind === "amber") ambers.push(descriptor);
    }
    player.z = run.distance;
    let target = null;
    for (const amber of ambers) {
      const dz = amber.z - player.z;
      if (dz > 1 && dz < 26 && (!target || dz < target.z - player.z)) target = amber;
    }
    let axis = 0;
    if (target && next() < skill) {
      const delta = target.x - player.x;
      if (Math.abs(delta) > 0.06) axis = -Math.sign(delta);
    }
    stepPlayer(player, dt, { axis });
    stepRun(run, dt, {});
    for (let i = ambers.length - 1; i >= 0; i -= 1) {
      const amber = ambers[i];
      const dz = Math.abs(amber.z - player.z);
      const dx = Math.abs(amber.x - player.x);
      if (dz <= 1.5 && dx <= 1.15) {
        collectAmber(run);
        collected += 1;
        ambers.splice(i, 1);
      } else if (amber.z < player.z - 6) {
        ambers.splice(i, 1);
      }
    }
    if (run.caught) { caughtAt = frame / 60; break; }
  }
  return {
    caughtAt,
    distance: Math.round(run.distance),
    gap: +run.gap.toFixed(2),
    density: +(collected / Math.max(1, run.distance)).toFixed(4),
  };
}

const idle = [1, 2, 3].map((seed) => simulate({ skill: 0, seed }));
const skilled = [1, 2, 3].map((seed) => simulate({ skill: 0.6, seed }));
console.log(JSON.stringify({ idle, skilled }));
"""


def test_amber_is_wired_as_the_survival_currency() -> None:
    """The pickup must hand distance back, and the HUD must show that gain."""
    constants = CONSTANTS.read_text()
    for key in ("amberGapGain", "amberStreak", "amberStreakBonus", "maxGap"):
        assert re.search(rf"^\s+{key}: [\d.]+,", constants, re.MULTILINE), key

    run_model = (DINO / "run-model.js").read_text()
    collect = run_model.split("export function collectAmber", 1)[1]
    assert "state.gap = Math.min(RUN.maxGap" in collect
    assert "RUN.amberGapGain" in collect
    assert "streak" in collect.split("return", 1)[1]

    # The bar used to divide by a hard-coded 15.5 m while the real gap drifted
    # to 26 m, so a comfortable chase read as "full".
    assert "RUN.maxGap" in HUD.read_text()

    page = SCRIPT.read_text()
    assert "hud.pulseGap(" in page
    assert "result.gapGain" in page


def test_one_amber_pushes_the_rex_back_by_the_configured_gain() -> None:
    data = _run_node(
        """
        import { RUN } from "./experiments/space-explorer/dino/constants.js";
        import { createRunState, collectAmber } from "./experiments/space-explorer/dino/run-model.js";
        const run = createRunState();
        run.gap = 10;
        const first = collectAmber(run);
        let tenth = null;
        for (let i = 1; i < 10; i += 1) tenth = collectAmber(run);
        // The cap must hold even when the trail is dense.
        for (let i = 0; i < 400; i += 1) collectAmber(run);
        console.log(JSON.stringify({
          gain: RUN.amberGapGain,
          afterOne: first.gapGain,
          streak: tenth.streak,
          tenthGain: tenth.gapGain,
          capped: run.gap,
          cap: RUN.maxGap,
        }));
        """
    )
    if not data:
        return
    assert data["afterOne"] == data["gain"]
    assert data["streak"] is True
    assert data["tenthGain"] > data["gain"], "every tenth pickup must pay a bonus"
    assert data["capped"] <= data["cap"] + 1e-9


def test_hazard_clusters_are_spaced_in_seconds() -> None:
    """Reaction time must not shrink as the runner speeds up.

    The same lane also needs a beat between hazards: at 24 m/s a 12 m repeat is
    0.5 s, which no child can answer.
    """
    data = _run_node(
        """
        import { HAZARD } from "./experiments/space-explorer/dino/constants.js";
        import { createSpawner } from "./experiments/space-explorer/dino/spawner.js";
        import { getBaseSpeed } from "./experiments/space-explorer/dino/run-model.js";
        const spawner = createSpawner();
        const list = [];
        const seen = new Set();
        for (let d = 0; d <= 6000; d += 2) {
          for (const item of spawner.update(d, HAZARD.spawnAhead)) {
            if (item.kind !== "hazard") continue;
            const key = `${item.z.toFixed(1)}:${item.type}:${item.lane}`;
            if (seen.has(key)) continue;
            seen.add(key);
            list.push(item);
          }
        }
        list.sort((a, b) => a.z - b.z);
        const seconds = (a, b) => (b.z - a.z) / getBaseSpeed((a.z + b.z) / 2);
        const buckets = { early: [], late: [] };
        for (let i = 1; i < list.length; i += 1) {
          const mid = (list[i].z + list[i - 1].z) / 2;
          if (mid < 700) buckets.early.push(seconds(list[i - 1], list[i]));
          else if (mid > 1800) buckets.late.push(seconds(list[i - 1], list[i]));
        }
        const median = (xs) => {
          const sorted = [...xs].sort((a, b) => a - b);
          return sorted[Math.floor(sorted.length / 2)];
        };
        // Same-lane follow-ups and three-lane walls.
        const byLane = new Map();
        let walls = 0;
        let ribsClashes = 0;
        for (const hazard of list) {
          if (hazard.type !== "ribs") {
            if (!byLane.has(hazard.lane)) byLane.set(hazard.lane, []);
            byLane.get(hazard.lane).push(hazard);
            continue;
          }
          if (list.some((other) => other !== hazard && Math.abs(other.z - hazard.z) < 6)) ribsClashes += 1;
        }
        const sameLane = [];
        for (const lane of byLane.values()) {
          for (let i = 1; i < lane.length; i += 1) sameLane.push(seconds(lane[i - 1], lane[i]));
        }
        for (const hazard of list) {
          if (hazard.type === "ribs") continue;
          const blocked = new Set([hazard.lane]);
          for (const other of list) {
            if (other !== hazard && other.type !== "ribs" && Math.abs(other.z - hazard.z) < 3.4) blocked.add(other.lane);
          }
          if (blocked.size >= 3) walls += 1;
        }
        console.log(JSON.stringify({
          count: list.length,
          early: median(buckets.early),
          late: median(buckets.late),
          sameLaneMin: Math.min(...sameLane),
          walls,
          ribsClashes,
        }));
        """
    )
    if not data:
        return
    assert data["count"] > 200, "the sample must cover 6 km of track"
    assert data["early"] >= 1.45, f"early clusters are too tight: {data['early']:.2f}s"
    assert data["late"] >= 1.05, f"late game collapses to {data['late']:.2f}s"
    assert data["sameLaneMin"] >= 0.9, f"same-lane repeat after {data['sameLaneMin']:.2f}s"
    assert data["walls"] == 0, "a three-lane wall is unavoidable"
    assert data["ribsClashes"] == 0, "the full-width arch must own its beat"


def test_running_without_amber_gets_the_player_caught() -> None:
    data = _run_node(_COLLECTOR)
    if not data:
        return
    for run in data["idle"]:
        assert run["caughtAt"] is not None, "a runner who ignores amber must be eaten"
        assert run["caughtAt"] < 180, f"caught after {run['caughtAt']:.0f}s is too generous"
        assert run["distance"] > 150, "the chase must still start with real running room"


def test_collecting_amber_holds_the_rex_off() -> None:
    data = _run_node(_COLLECTOR)
    if not data:
        return
    for run in data["skilled"]:
        assert run["caughtAt"] is None, f"a collecting player was caught at {run['caughtAt']:.0f}s"
        assert run["gap"] >= 12, "the rex must stay visibly behind a collecting player"
        assert run["density"] >= 0.1, "the collector must actually be picking up amber"
