/**
 * Chase-framing regression check.
 *
 * Runs the same camera director the game uses (experiments/space-explorer/
 * dino/chase.js), steps it at a fixed 60 Hz with the real staging rules, and
 * projects the T-Rex and the runner into the camera frustum. Catches the
 * classic chase-camera bugs: the predator drifting out of frame, the pair
 * overlapping, or the camera leaving the ground.
 *
 * Run: node scripts/dino/frame-check.mjs
 */

import { strict as assert } from "node:assert";
import {
  CHASE,
  createChaseDirector,
  rexStaging,
} from "../../experiments/space-explorer/dino/chase.js";

const ASPECT = 16 / 9;
const DT = 1 / 60;

/* Minimal vector / camera math (no three.js dependency). */
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const cross = (a, b) => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const norm = (a) => {
  const length = Math.hypot(a[0], a[1], a[2]) || 1;
  return [a[0] / length, a[1] / length, a[2] / length];
};

/** Projects a world point into normalised device coordinates. */
function project(pose, point) {
  const eye = [pose.x, pose.y, pose.z];
  const target = [pose.lookX, pose.lookY, pose.lookZ];
  const forward = norm(sub(target, eye));
  const right = norm(cross(forward, [0, 1, 0]));
  const up = cross(right, forward);
  const rel = sub(point, eye);
  const z = dot(rel, forward);
  const x = dot(rel, right);
  const y = dot(rel, up);
  const tanHalf = Math.tan((pose.fov * Math.PI) / 180 / 2);
  return {
    x: x / (z * tanHalf * ASPECT),
    y: y / (z * tanHalf),
    depth: z,
  };
}

/** Steps the director until its damped pose settles. */
function settle(director, input, seconds = 2.5) {
  const frames = Math.round(seconds / DT);
  let pose;
  for (let i = 0; i < frames; i += 1) {
    pose = director.update(DT, { ...input, time: i * DT });
  }
  return pose;
}

function runningInput(overrides = {}) {
  return {
    mode: "running",
    player: { x: 0, y: 0, z: 120, tilt: 0, sliding: false },
    danger: 0,
    speedRatio: 0,
    sprinting: false,
    rex: { x: -CHASE.rexLateral, z: 120 - CHASE.rexBehind },
    time: 0,
    reduceMotion: false,
    ...overrides,
  };
}

let checks = 0;
function check(name, fn) {
  fn();
  checks += 1;
  console.log(`  ok  ${name}`);
}

/* 1. While running, both the runner and the predator stay in frame. */
check("running: predator and runner stay inside the frustum", () => {
  for (const danger of [0, 0.25, 0.5, 0.75, 1]) {
    for (const laneX of [-3.6, 0, 3.6]) {
      const director = createChaseDirector();
      const stage = rexStaging(danger, "running");
      const input = runningInput({
        danger,
        speedRatio: danger,
        player: { x: laneX, y: 0, z: 120, tilt: laneX / 4.5, sliding: false },
        rex: { x: laneX - stage.lateral, z: 120 - stage.behind },
      });
      const pose = settle(director, input);
      const rexHead = project(pose, [input.rex.x, 3.35, input.rex.z]);
      const rexChest = project(pose, [input.rex.x, 2.2, input.rex.z]);
      const runner = project(pose, [input.player.x, 1.05, input.player.z]);
      for (const [label, point] of [
        ["rex head", rexHead],
        ["rex chest", rexChest],
        ["runner", runner],
      ]) {
        assert.ok(point.depth > 0.5, `${label} ended up behind the camera (danger ${danger})`);
        assert.ok(
          Math.abs(point.x) <= 1 && Math.abs(point.y) <= 1,
          `${label} fell outside the frame at danger ${danger}, lane ${laneX}: ${point.x.toFixed(2)}, ${point.y.toFixed(2)}`,
        );
      }
    }
  }
});

/* 2. The predator never stands on top of the runner. */
check("running: staging keeps the predator clear of the runner", () => {
  for (const danger of [0, 0.5, 1]) {
    const stage = rexStaging(danger, "running");
    const distance = Math.hypot(stage.lateral, stage.behind);
    assert.ok(distance > 3.2, `predator too close at danger ${danger}: ${distance.toFixed(2)} m`);
    assert.ok(stage.behind > 0.5, "predator must trail the runner, not lead");
  }
  const catchStage = rexStaging(1, "caught");
  const catchDistance = Math.hypot(catchStage.lateral, catchStage.behind);
  assert.ok(catchDistance > 2.2, `catch pose collapses the pair (${catchDistance.toFixed(2)} m)`);
});

/* 3. Camera stays behind, above and ahead-looking while running. */
check("running: camera rig stays behind and above the runner", () => {
  for (const speedRatio of [0, 0.5, 1]) {
    const director = createChaseDirector();
    const input = runningInput({ speedRatio, danger: speedRatio });
    const pose = settle(director, input);
    assert.ok(pose.y > 2.8 && pose.y < 8, `camera height out of range: ${pose.y.toFixed(2)}`);
    assert.ok(pose.z < input.player.z - 8, `camera is not trailing: ${pose.z.toFixed(2)}`);
    assert.ok(pose.lookZ > input.player.z, "camera is not looking down the track");
    assert.ok(pose.fov >= 48 && pose.fov <= 78, `fov out of range: ${pose.fov.toFixed(1)}`);
  }
});

/* 4. Landing impulses settle instead of oscillating forever. */
check("running: impact spring settles within a second", () => {
  const director = createChaseDirector();
  const input = runningInput();
  settle(director, input, 1.5);
  const rest = director.state.y;
  director.impulse(0.9);
  const bumped = director.update(DT, input).y;
  assert.ok(Math.abs(bumped - rest) < 0.2, "impulse was not applied to the rig");
  settle(director, input, 1.2);
  assert.ok(Math.abs(director.state.y - rest) < 0.02, "impact spring never settled");
});

/* 5. The menu hero shot frames both characters in the right-hand column. */
check("menu: hero shot frames the pair", () => {
  const director = createChaseDirector();
  const input = {
    mode: "menu",
    player: { x: 0, y: 0, z: 0, tilt: 0 },
    danger: 0.18,
    speedRatio: 0,
    time: 0,
  };
  const pose = settle(director, input, 3);
  const stage = rexStaging(0.18, "menu");
  const rexHead = project(pose, [-stage.lateral, 3.4, -stage.behind]);
  const runner = project(pose, [0, 1.0, 0]);
  assert.ok(Math.abs(rexHead.x) < 1.05, `menu rex off screen: ${rexHead.x.toFixed(2)}`);
  assert.ok(rexHead.depth > 4, "menu rex is behind the camera");
  assert.ok(Math.abs(runner.x) < 1.2, `menu runner off screen: ${runner.x.toFixed(2)}`);
  // The start-screen copy lives in the left column; keep the hero art clear of it.
  assert.ok(runner.x > -0.35, `menu hero drifted into the copy column: ${runner.x.toFixed(2)}`);
});

/* 6. Catch cam keeps the kill in shot. */
check("caught: hero orbit frames both characters", () => {
  const director = createChaseDirector();
  const stage = rexStaging(1, "caught");
  const input = {
    mode: "caught",
    player: { x: 0.4, y: 0, z: 80, tilt: 0 },
    danger: 1,
    speedRatio: 0.5,
    rex: { x: 0.4 - stage.lateral, z: 80 - stage.behind },
    time: 0,
  };
  const pose = settle(director, input, 3);
  const rexHead = project(pose, [input.rex.x, 3.3, input.rex.z]);
  const runner = project(pose, [input.player.x, 1.0, input.player.z]);
  assert.ok(Math.abs(rexHead.x) < 1.05 && rexHead.depth > 1, "catch cam loses the predator");
  assert.ok(Math.abs(runner.x) < 1.05 && runner.depth > 1, "catch cam loses the runner");
});

console.log(`\nframe-check: ${checks} checks passed`);
