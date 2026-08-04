"""Behavioral tests for Ocean Rescue terrain collision recovery.

Every JavaScript assertion runs the real tracked sources (``state.js``,
``missions.js``, ``gups.js``, ``launch.js``, ``travel.js``, ``terrain.js``,
and ``app.js``) through the installed Node runtime in a fresh VM sandbox
using a minimal fake DOM, a fake canvas 2D context, a deterministic fake
timer queue, and a deterministic fake animation-frame queue. No npm packages,
no browser automation, no real-time sleeps, and no separate JavaScript test
file are used.
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_BIN: str = shutil.which("node") or ""
if not NODE_BIN:
    raise RuntimeError("Node executable not found on PATH")


_BOOTSTRAP = textwrap.dedent(
    """\
    const fs = require("fs");
    const vm = require("vm");
    const assert = require("assert");

    const STATE_SOURCE = fs.readFileSync("domains/ocean-rescue/src/state.js", "utf8");
    const MISSIONS_SOURCE = fs.readFileSync("domains/ocean-rescue/src/missions.js", "utf8");
    const GUPS_SOURCE = fs.readFileSync("domains/ocean-rescue/src/gups.js", "utf8");
    const LAUNCH_SOURCE = fs.readFileSync("domains/ocean-rescue/src/launch.js", "utf8");
    const TRAVEL_SOURCE = fs.readFileSync("domains/ocean-rescue/src/travel.js", "utf8");
    const TERRAIN_SOURCE = fs.readFileSync("domains/ocean-rescue/src/terrain.js", "utf8");
    const POINTER_INPUT_SOURCE = fs.readFileSync("domains/ocean-rescue/src/pointer-input.js", "utf8");
    const APP_SOURCE = fs.readFileSync("domains/ocean-rescue/src/app.js", "utf8");

    function plain(value) {
      return JSON.parse(JSON.stringify(value));
    }

    function freshTerrain() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(TERRAIN_SOURCE, sandbox, { filename: "terrain.js" });
      return sandbox.window.OceanRescue.Terrain;
    }

    function freshTravel() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(TRAVEL_SOURCE, sandbox, { filename: "travel.js" });
      return sandbox.window.OceanRescue.Travel;
    }

    function freshTerrainAndTravel() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(TRAVEL_SOURCE, sandbox, { filename: "travel.js" });
      vm.runInContext(TERRAIN_SOURCE, sandbox, { filename: "terrain.js" });
      return {
        Travel: sandbox.window.OceanRescue.Travel,
        Terrain: sandbox.window.OceanRescue.Terrain,
      };
    }

    const EXPECTED_GEOMETRY = [
      { worldX: 1200, y: 220, width: 180, height: 150 },
      { worldX: 2200, y: 500, width: 200, height: 160 },
      { worldX: 3200, y: 300, width: 160, height: 180 },
      { worldX: 4200, y: 470, width: 190, height: 150 },
      { worldX: 5200, y: 250, width: 200, height: 170 },
    ];

    const EXPECTED_LAYOUTS = {
      "sea-turtle": {
        missionId: "sea-turtle",
        environment: "coral-reef",
        ids: ["coral-column-1", "reef-arch-2", "coral-rock-3", "kelp-rock-4", "reef-spire-5"],
        kinds: ["coral-column", "reef-arch", "coral-rock", "kelp-rock", "reef-spire"],
      },
      "crab": {
        missionId: "crab",
        environment: "sandy-reef",
        ids: ["sand-rock-1", "shell-ledge-2", "low-reef-3", "rock-stack-4", "sand-pillar-5"],
        kinds: ["sand-rock", "shell-ledge", "low-reef", "rock-stack", "sand-pillar"],
      },
      "young-whale": {
        missionId: "young-whale",
        environment: "rocky-canyon",
        ids: ["canyon-wall-1", "rock-spire-2", "canyon-ledge-3", "boulder-stack-4", "canyon-pillar-5"],
        kinds: ["canyon-wall", "rock-spire", "canyon-ledge", "boulder-stack", "canyon-pillar"],
      },
    };

    function makeClassList() {
      const names = [];
      return {
        add(token) {
          if (names.indexOf(token) === -1) {
            names.push(token);
          }
        },
        remove(token) {
          const index = names.indexOf(token);
          if (index !== -1) {
            names.splice(index, 1);
          }
        },
        contains(token) {
          return names.indexOf(token) !== -1;
        },
      };
    }

    function makeElement(tagName) {
      const el = {
        tagName,
        children: [],
        attributes: {},
        style: {},
        textContent: null,
        className: "",
        disabled: false,
        hidden: false,
        parent: null,
        listeners: {},
        classList: makeClassList(),
        scrollIntoViewCalls: 0,
        appendChild(child) {
          child.parent = this;
          this.children.push(child);
        },
        setAttribute(name, value) {
          this.attributes[name] = String(value);
        },
        getAttribute(name) {
          return Object.prototype.hasOwnProperty.call(this.attributes, name)
            ? this.attributes[name]
            : null;
        },
        removeAttribute(name) {
          delete this.attributes[name];
        },
        addEventListener(type, fn) {
          if (!this.listeners[type]) {
            this.listeners[type] = [];
          }
          this.listeners[type].push(fn);
        },
        click() {
          const list = this.listeners["click"] || [];
          for (const fn of list.slice()) {
            fn({ stopPropagation() {} });
          }
          if (this.parent) {
            this.parent.click();
          }
        },
        querySelectorAll(selector) {
          if (selector === "button") {
            return this.children.filter((child) => child.tagName === "button");
          }
          return [];
        },
        scrollIntoView() {
          this.scrollIntoViewCalls += 1;
        },
      };
      Object.defineProperty(el, "innerHTML", {
        enumerable: false,
        get() {
          return this._innerHTML || "";
        },
        set(value) {
          this._innerHTML = value;
          this.children = [];
        },
      });
      return el;
    }

    function makeContext() {
      const calls = [];
      const ctx = {
        calls,
        fillStyle: null,
        font: null,
        textAlign: null,
        clearRect(...args) {
          calls.push(["clearRect", ...args]);
        },
        fillRect(...args) {
          calls.push(["fillRect", ...args]);
        },
        beginPath() {
          calls.push(["beginPath"]);
        },
        arc(...args) {
          calls.push(["arc", ...args]);
        },
        fill() {
          calls.push(["fill"]);
        },
        fillText(...args) {
          calls.push(["fillText", ...args]);
        },
      };
      return ctx;
    }

    function makeCanvasElement() {
      const el = makeElement("canvas");
      el.width = 1280;
      el.height = 720;
      el.rect = { top: 0, height: 480 };
      el._context = makeContext();
      el.getContext = function (type) {
        if (type === "2d") {
          return el._context;
        }
        return null;
      };
      el.getBoundingClientRect = function () {
        return el.rect;
      };
      return el;
    }

    function makeDocument(elements) {
      return {
        domListenerCount: 0,
        domLoadedHandler: null,
        getElementById(id) {
          return Object.prototype.hasOwnProperty.call(elements, id)
            ? elements[id]
            : null;
        },
        createElement(tagName) {
          return makeElement(tagName);
        },
        addEventListener(type, fn) {
          if (type === "DOMContentLoaded") {
            this.domListenerCount += 1;
            this.domLoadedHandler = fn;
          }
        },
      };
    }

    function makeBootDom() {
      const rootEl = makeElement("main");
      const statusEl = makeElement("p");
      const missionSection = makeElement("section");
      const missionList = makeElement("div");
      const gupSection = makeElement("section");
      gupSection.hidden = true;
      const gupMission = makeElement("p");
      const gupList = makeElement("div");
      const actions = makeElement("div");
      const gupBack = makeElement("button");
      const gupLaunch = makeElement("button");
      const launchSection = makeElement("section");
      launchSection.hidden = true;
      const launchTitle = makeElement("h2");
      const launchVisual = makeElement("div");
      const launchDoorLeft = makeElement("div");
      const launchDoorRight = makeElement("div");
      const launchGup = makeElement("div");
      const launchGupName = makeElement("span");
      const launchCompanion = makeElement("p");
      const launchBriefing = makeElement("p");
      const launchTapHint = makeElement("p");
      const launchSkip = makeElement("button");
      const goalBanner = makeElement("div");
      goalBanner.hidden = true;
      const stage = makeElement("section");
      stage.hidden = true;
      const canvas = makeCanvasElement();

      missionSection.appendChild(missionList);
      actions.appendChild(gupBack);
      actions.appendChild(gupLaunch);
      gupSection.appendChild(gupMission);
      gupSection.appendChild(gupList);
      gupSection.appendChild(actions);
      launchSection.appendChild(launchTitle);
      launchVisual.appendChild(launchDoorLeft);
      launchVisual.appendChild(launchDoorRight);
      launchVisual.appendChild(launchGup);
      launchGup.appendChild(launchGupName);
      launchSection.appendChild(launchVisual);
      launchSection.appendChild(launchCompanion);
      launchSection.appendChild(launchBriefing);
      launchSection.appendChild(launchTapHint);
      launchSection.appendChild(launchSkip);
      stage.appendChild(canvas);
      rootEl.appendChild(missionSection);
      rootEl.appendChild(gupSection);
      rootEl.appendChild(launchSection);
      rootEl.appendChild(goalBanner);
      rootEl.appendChild(stage);

      const elements = {
        "ocean-rescue-root": rootEl,
        "ocean-rescue-status": statusEl,
        "ocean-rescue-mission-select": missionSection,
        "ocean-rescue-mission-list": missionList,
        "ocean-rescue-gup-select": gupSection,
        "ocean-rescue-gup-mission": gupMission,
        "ocean-rescue-gup-list": gupList,
        "ocean-rescue-gup-actions": actions,
        "ocean-rescue-gup-back": gupBack,
        "ocean-rescue-gup-launch": gupLaunch,
        "ocean-rescue-launch": launchSection,
        "ocean-rescue-launch-title": launchTitle,
        "ocean-rescue-launch-visual": launchVisual,
        "ocean-rescue-launch-gup-name": launchGupName,
        "ocean-rescue-launch-companion": launchCompanion,
        "ocean-rescue-launch-briefing": launchBriefing,
        "ocean-rescue-launch-skip": launchSkip,
        "ocean-rescue-goal-banner": goalBanner,
        "ocean-rescue-stage": stage,
        "ocean-rescue-canvas": canvas,
      };
      return {
        document: makeDocument(elements),
        rootEl,
        statusEl,
        missionSection,
        missionList,
        gupSection,
        gupMission,
        gupList,
        actions,
        gupBack,
        gupLaunch,
        launchSection,
        launchTitle,
        launchVisual,
        launchDoorLeft,
        launchDoorRight,
        launchGup,
        launchGupName,
        launchCompanion,
        launchBriefing,
        launchTapHint,
        skipButton: launchSkip,
        goalBanner,
        stage,
        canvas,
      };
    }

    function makeTimerQueue() {
      let nextId = 1;
      const timers = [];
      return {
        timers,
        setTimeout(fn, delay) {
          const id = nextId;
          nextId += 1;
          timers.push({ id, fn, delay, cancelled: false });
          return id;
        },
        clearTimeout(id) {
          const entry = timers.find((entry) => entry.id === id);
          if (entry) {
            entry.cancelled = true;
          }
        },
        pending() {
          return timers.filter((entry) => !entry.cancelled);
        },
        run(id) {
          const entry = timers.find((entry) => entry.id === id);
          if (!entry) {
            throw new Error("no such timer " + id);
          }
          if (entry.cancelled) {
            throw new Error("timer already cancelled " + id);
          }
          entry.cancelled = true;
          entry.fn();
        },
      };
    }

    function makeFrameQueue() {
      let nextId = 1;
      const frames = [];
      return {
        frames,
        requestAnimationFrame(fn) {
          const id = nextId;
          nextId += 1;
          frames.push({ id, fn, ran: false, cancelled: false });
          return id;
        },
        cancelAnimationFrame(id) {
          const entry = frames.find((entry) => entry.id === id);
          if (entry) {
            entry.cancelled = true;
          }
        },
        pending() {
          return frames.filter((entry) => !entry.cancelled && !entry.ran);
        },
        run(id, timestamp) {
          const entry = frames.find((entry) => entry.id === id);
          if (!entry) {
            throw new Error("no such frame " + id);
          }
          if (entry.cancelled) {
            throw new Error("frame already cancelled " + id);
          }
          entry.ran = true;
          entry.fn(timestamp);
        },
      };
    }

    function loadApp(document, windowExtras) {
      const timers = makeTimerQueue();
      const frames = makeFrameQueue();
      const extras = Object.assign({}, windowExtras, {
        setTimeout: timers.setTimeout,
        clearTimeout: timers.clearTimeout,
        requestAnimationFrame: frames.requestAnimationFrame,
        cancelAnimationFrame: frames.cancelAnimationFrame,
      });
      const sandbox = { window: extras, document };
      vm.createContext(sandbox);
      vm.runInContext(STATE_SOURCE, sandbox, { filename: "state.js" });
      vm.runInContext(MISSIONS_SOURCE, sandbox, { filename: "missions.js" });
      vm.runInContext(GUPS_SOURCE, sandbox, { filename: "gups.js" });
      vm.runInContext(LAUNCH_SOURCE, sandbox, { filename: "launch.js" });
      vm.runInContext(TRAVEL_SOURCE, sandbox, { filename: "travel.js" });
      vm.runInContext(TERRAIN_SOURCE, sandbox, { filename: "terrain.js" });
      vm.runInContext(POINTER_INPUT_SOURCE, sandbox, { filename: "pointer-input.js" });
      vm.runInContext(APP_SOURCE, sandbox, { filename: "app.js" });
      return {
        sandbox,
        timers,
        frames,
        State: sandbox.window.OceanRescue.State,
        Missions: sandbox.window.OceanRescue.Missions,
        Gups: sandbox.window.OceanRescue.Gups,
        Launch: sandbox.window.OceanRescue.Launch,
        Travel: sandbox.window.OceanRescue.Travel,
        Terrain: sandbox.window.OceanRescue.Terrain,
        App: sandbox.window.OceanRescue.App,
      };
    }

    function startLaunchToLaunch(dom, ctx, gupIndex) {
      dom.document.domLoadedHandler();
      assert.strictEqual(ctx.App.boot(), true);
      dom.missionList.children[0].click();
      if (gupIndex !== undefined) {
        dom.gupList.children[gupIndex].click();
      }
      dom.gupLaunch.click();
      assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
    }

    function dispatch(canvas, type, event) {
      const list = canvas.listeners[type] || [];
      for (const fn of list.slice()) {
        fn(event);
      }
    }

    function runToCollision(ctx, dom, maxFrames) {
      const canvas = dom.canvas;
      dispatch(canvas, "pointerdown", {
        pointerId: 1,
        clientY: 240,
        isPrimary: true,
        button: 0,
        preventDefault() {},
      });
      dispatch(canvas, "pointermove", {
        pointerId: 1,
        clientY: 160,
        isPrimary: true,
        button: 0,
        preventDefault() {},
      });
      dispatch(canvas, "pointerup", {
        pointerId: 1,
        clientY: 160,
        isPrimary: true,
        button: 0,
        preventDefault() {},
      });
      let frameTime = 1000;
      let frames = 0;
      for (;;) {
        const pending = ctx.frames.pending();
        if (pending.length === 0) {
          return { collided: false, frames, nextTime: frameTime };
        }
        frames += 1;
        if (frames > maxFrames) {
          return { collided: false, frames, nextTime: frameTime };
        }
        ctx.frames.run(pending[0].id, frameTime);
        frameTime += 1000;
        if (ctx.Terrain.getSnapshot().collisionCount > 0) {
          return { collided: true, frames, nextTime: frameTime };
        }
      }
    }
    """
)


def _run_node(script: str) -> subprocess.CompletedProcess[str]:
    """Run a Node harness from the repository root with explicit result handling."""
    return subprocess.run(
        [NODE_BIN, "-e", script],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _assert_node_ok(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, (
        f"Node harness failed (exit {result.returncode}):\n{result.stderr}"
    )


def test_terrain_catalog_geometry_and_public_contract() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Terrain = freshTerrain();

        assert.deepStrictEqual(plain(Terrain.Constants), {
          gupScreenX: 320,
          gupHalfWidth: 70,
          gupHalfHeight: 36,
          obstacleSpacing: 1000,
          slowdownDurationMs: 1000,
          slowdownMultiplier: 0.5,
          sameObstacleCooldownMs: 700,
          shakeDurationMs: 350,
          knockbackDistance: 36,
        });
        assert.strictEqual(Object.isFrozen(Terrain.Constants), true);
        assert.strictEqual(Object.isFrozen(Terrain), true);

        assert.deepStrictEqual(
          Object.keys(Terrain.Layouts).sort(),
          ["crab", "sea-turtle", "young-whale"]
        );

        for (const missionId of ["sea-turtle", "crab", "young-whale"]) {
          const layout = Terrain.Layouts[missionId];
          assert.deepStrictEqual(Object.keys(layout).sort(), ["environment", "missionId", "obstacles"]);
          assert.strictEqual(layout.missionId, missionId);
          assert.strictEqual(layout.environment, EXPECTED_LAYOUTS[missionId].environment);
          assert.strictEqual(layout.obstacles.length, 5);
          for (let i = 0; i < 5; i += 1) {
            const obs = layout.obstacles[i];
            assert.strictEqual(obs.id, EXPECTED_LAYOUTS[missionId].ids[i]);
            assert.strictEqual(obs.kind, EXPECTED_LAYOUTS[missionId].kinds[i]);
            assert.strictEqual(obs.worldX, EXPECTED_GEOMETRY[i].worldX);
            assert.strictEqual(obs.y, EXPECTED_GEOMETRY[i].y);
            assert.strictEqual(obs.width, EXPECTED_GEOMETRY[i].width);
            assert.strictEqual(obs.height, EXPECTED_GEOMETRY[i].height);
            assert.deepStrictEqual(
              Object.keys(obs).sort(),
              ["height", "id", "kind", "width", "worldX", "y"]
            );
          }
          for (let i = 1; i < 5; i += 1) {
            assert.strictEqual(
              layout.obstacles[i].worldX - layout.obstacles[i - 1].worldX,
              1000
            );
          }
          assert.strictEqual(Object.isFrozen(layout), true);
          assert.strictEqual(Object.isFrozen(layout.obstacles), true);
          assert.strictEqual(Object.isFrozen(layout.obstacles[0]), true);
        }

        for (let i = 0; i < 5; i += 1) {
          const a = Terrain.Layouts["sea-turtle"].obstacles[i];
          const b = Terrain.Layouts["crab"].obstacles[i];
          const c = Terrain.Layouts["young-whale"].obstacles[i];
          assert.deepStrictEqual([a.worldX, a.y, a.width, a.height], [b.worldX, b.y, b.width, b.height]);
          assert.deepStrictEqual([b.worldX, b.y, b.width, b.height], [c.worldX, c.y, c.width, c.height]);
        }

        assert.deepStrictEqual(
          Object.keys(Terrain).sort(),
          ["Constants", "Layouts", "getLayout", "getSnapshot", "start", "step", "stop"].sort()
        );
        const hidden = [
          "collide",
          "triggerCollision",
          "setSlowdown",
          "setCooldown",
          "setMission",
          "reset",
          "damage",
          "fail",
          "complete",
          "subscribe",
          "dispatch",
          "serialize",
          "hydrate",
          "load",
          "save",
          "history",
        ];
        for (const name of hidden) {
          assert.strictEqual(Terrain[name], undefined, "exposed " + name);
        }

        Terrain.extra = 1;
        Terrain.Constants.extra = 1;
        Terrain.Layouts.extra = 1;
        Terrain.Layouts["sea-turtle"].extra = 1;
        Terrain.Layouts["sea-turtle"].obstacles.extra = 1;
        Terrain.Layouts["sea-turtle"].obstacles[0].extra = 1;
        assert.strictEqual(Terrain.extra, undefined);
        assert.strictEqual(Terrain.Constants.extra, undefined);
        assert.strictEqual(Terrain.Layouts.extra, undefined);
        assert.strictEqual(Terrain.Layouts["sea-turtle"].extra, undefined);
        assert.strictEqual(Terrain.Layouts["sea-turtle"].obstacles.extra, undefined);
        assert.strictEqual(Terrain.Layouts["sea-turtle"].obstacles[0].extra, undefined);

        assert.strictEqual(Terrain.getLayout("sea-turtle"), Terrain.Layouts["sea-turtle"]);
        assert.strictEqual(Terrain.getLayout("crab"), Terrain.Layouts["crab"]);
        assert.strictEqual(Terrain.getLayout("young-whale"), Terrain.Layouts["young-whale"]);
        assert.strictEqual(Terrain.getLayout("unknown"), null);
        assert.strictEqual(Terrain.getLayout(""), null);
        assert.strictEqual(Terrain.getLayout(null), null);
        assert.strictEqual(Terrain.getLayout(undefined), null);
        assert.strictEqual(Terrain.getLayout(123), null);
        assert.strictEqual(Terrain.getLayout({}), null);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_terrain_start_and_initial_snapshot() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Terrain = freshTerrain();

        const initial = {
          active: false,
          missionId: null,
          collisionCount: 0,
          lastCollisionObstacleId: null,
          slowdownRemainingMs: 0,
          forwardSpeedMultiplier: 1,
          shakeRemainingMs: 0,
          knockbackOffsetX: 0,
          shakeOffsetY: 0,
          collisionActive: false,
        };
        assert.deepStrictEqual(plain(Terrain.getSnapshot()), initial);
        assert.strictEqual(Object.isFrozen(Terrain.getSnapshot()), true);
        assert.notStrictEqual(Terrain.getSnapshot(), Terrain.getSnapshot());

        assert.strictEqual(Terrain.start("unknown"), false);
        assert.strictEqual(Terrain.start(""), false);
        assert.strictEqual(Terrain.start(null), false);
        assert.strictEqual(Terrain.start(123), false);
        assert.strictEqual(Terrain.start(undefined), false);
        assert.deepStrictEqual(plain(Terrain.getSnapshot()), initial);

        assert.strictEqual(Terrain.start("sea-turtle"), true);
        assert.deepStrictEqual(plain(Terrain.getSnapshot()), {
          active: true,
          missionId: "sea-turtle",
          collisionCount: 0,
          lastCollisionObstacleId: null,
          slowdownRemainingMs: 0,
          forwardSpeedMultiplier: 1,
          shakeRemainingMs: 0,
          knockbackOffsetX: 0,
          shakeOffsetY: 0,
          collisionActive: false,
        });

        assert.strictEqual(
          Terrain.step(50, { active: true, distance: 720, y: 220 }),
          true
        );
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 1);

        assert.strictEqual(Terrain.stop(), true);
        const stopped = plain(Terrain.getSnapshot());
        assert.strictEqual(stopped.active, false);
        assert.strictEqual(stopped.missionId, "sea-turtle");
        assert.strictEqual(stopped.collisionCount, 1);
        assert.strictEqual(stopped.lastCollisionObstacleId, "coral-column-1");
        assert.strictEqual(stopped.slowdownRemainingMs, 0);
        assert.strictEqual(stopped.shakeRemainingMs, 0);
        assert.strictEqual(Terrain.stop(), false);
        assert.deepStrictEqual(plain(Terrain.getSnapshot()), stopped);

        assert.strictEqual(Terrain.start("crab"), true);
        assert.deepStrictEqual(plain(Terrain.getSnapshot()), {
          active: true,
          missionId: "crab",
          collisionCount: 0,
          lastCollisionObstacleId: null,
          slowdownRemainingMs: 0,
          forwardSpeedMultiplier: 1,
          shakeRemainingMs: 0,
          knockbackOffsetX: 0,
          shakeOffsetY: 0,
          collisionActive: false,
        });
        """
    )
    _assert_node_ok(_run_node(harness))


def test_first_contact_triggers_bounded_recovery() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const { Terrain, Travel } = freshTerrainAndTravel();
        Travel.start();
        assert.strictEqual(Terrain.start("sea-turtle"), true);
        const beforeTravel = plain(Travel.getSnapshot());

        assert.strictEqual(
          Terrain.step(16, { active: true, distance: 720, y: 220 }),
          true
        );
        const ts = Terrain.getSnapshot();
        assert.strictEqual(ts.collisionCount, 1);
        assert.strictEqual(ts.lastCollisionObstacleId, "coral-column-1");
        assert.strictEqual(ts.forwardSpeedMultiplier, 0.5);
        assert.strictEqual(ts.slowdownRemainingMs, 1000);
        assert.strictEqual(ts.shakeRemainingMs, 350);
        assert.strictEqual(ts.knockbackOffsetX, 36);
        assert.strictEqual(ts.shakeOffsetY, -6);
        assert.strictEqual(ts.collisionActive, true);
        assert.strictEqual(ts.active, true);

        assert.deepStrictEqual(plain(Travel.getSnapshot()), beforeTravel);

        Terrain.stop();
        Terrain.start("sea-turtle");
        assert.strictEqual(
          Terrain.step(16, { active: true, distance: 719, y: 220 }),
          true
        );
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 0);
        assert.strictEqual(
          Terrain.step(16, { active: true, distance: 720, y: 220 }),
          true
        );
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 1);

        Terrain.stop();
        Terrain.start("sea-turtle");
        assert.strictEqual(
          Terrain.step(16, { active: true, distance: 720, y: 331 }),
          true
        );
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 1);

        Terrain.stop();
        Terrain.start("sea-turtle");
        assert.strictEqual(
          Terrain.step(16, { active: true, distance: 720, y: 332 }),
          true
        );
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 0);

        Terrain.stop();
        Terrain.start("sea-turtle");
        assert.strictEqual(Terrain.step(0, { active: true, distance: 720, y: 220 }), false);
        assert.strictEqual(Terrain.step(-1, { active: true, distance: 720, y: 220 }), false);
        assert.strictEqual(Terrain.step(NaN, { active: true, distance: 720, y: 220 }), false);
        assert.strictEqual(Terrain.step(50, null), false);
        assert.strictEqual(Terrain.step(50, { active: false, distance: 720, y: 220 }), false);
        assert.strictEqual(Terrain.step(50, { active: true, distance: NaN, y: 220 }), false);
        assert.strictEqual(Terrain.step(50, { active: true, distance: 720, y: NaN }), false);
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 0);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_continuous_contact_and_cooldown_prevent_repeat() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Terrain = freshTerrain();
        Terrain.start("sea-turtle");

        assert.strictEqual(Terrain.step(50, { active: true, distance: 720, y: 220 }), true);
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 1);

        for (let i = 0; i < 10; i += 1) {
          assert.strictEqual(Terrain.step(50, { active: true, distance: 740, y: 220 }), true);
        }
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 1);

        assert.strictEqual(Terrain.step(50, { active: true, distance: 690, y: 220 }), true);
        assert.strictEqual(Terrain.step(50, { active: true, distance: 720, y: 220 }), true);
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 1);

        for (let i = 0; i < 20; i += 1) {
          assert.strictEqual(Terrain.step(50, { active: true, distance: 725, y: 220 }), true);
        }
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 1);

        Terrain.stop();
        Terrain.start("sea-turtle");
        assert.strictEqual(Terrain.step(50, { active: true, distance: 720, y: 220 }), true);
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 1);
        Terrain.step(50, { active: true, distance: 690, y: 220 });
        for (let i = 0; i < 16; i += 1) {
          Terrain.step(50, { active: true, distance: 690, y: 220 });
        }
        assert.strictEqual(Terrain.step(50, { active: true, distance: 720, y: 220 }), true);
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 2);

        Terrain.stop();
        Terrain.start("sea-turtle");
        assert.strictEqual(Terrain.step(50, { active: true, distance: 720, y: 220 }), true);
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 1);
        Terrain.step(50, { active: true, distance: 690, y: 220 });
        Terrain.step(50, { active: true, distance: 720, y: 220 });
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 1);
        Terrain.step(50, { active: true, distance: 690, y: 220 });
        for (let i = 0; i < 12; i += 1) {
          Terrain.step(50, { active: true, distance: 690, y: 220 });
        }
        assert.strictEqual(Terrain.step(50, { active: true, distance: 720, y: 220 }), true);
        assert.strictEqual(Terrain.getSnapshot().collisionCount, 2);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_slowdown_affects_only_horizontal_progress() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Travel = freshTravel();
        Travel.start();

        assert.strictEqual(Travel.step(1000), true);
        assert.strictEqual(Travel.getSnapshot().distance, 6);

        assert.strictEqual(Travel.step(1000, 0.5), true);
        assert.strictEqual(Travel.getSnapshot().distance, 9);

        assert.strictEqual(Travel.tapTo(500), true);
        assert.strictEqual(Travel.step(50, 0.5), true);
        let snap = Travel.getSnapshot();
        assert.strictEqual(snap.distance, 12);
        assert.strictEqual(snap.y, 378);

        assert.strictEqual(Travel.beginDrag(5, 400), true);
        assert.strictEqual(Travel.moveDrag(5, 480), true);
        assert.strictEqual(Travel.step(50, 0.5), true);
        snap = Travel.getSnapshot();
        assert.strictEqual(snap.distance, 15);
        assert.strictEqual(snap.y, 458);
        assert.strictEqual(Travel.endDrag(5), true);

        assert.strictEqual(Travel.step(50, 0), true);
        assert.strictEqual(Travel.getSnapshot().distance, 15);
        assert.strictEqual(Travel.step(50, 1), true);
        assert.strictEqual(Travel.getSnapshot().distance, 21);

        assert.strictEqual(Travel.step(50, 2), false);
        assert.strictEqual(Travel.step(50, -0.1), false);
        assert.strictEqual(Travel.step(50, NaN), false);
        assert.strictEqual(Travel.step(50, Infinity), false);
        assert.strictEqual(Travel.step(50, "0.5"), false);
        assert.strictEqual(Travel.step(50, null), false);
        assert.strictEqual(Travel.step(50, {}), false);
        snap = Travel.getSnapshot();
        assert.strictEqual(snap.distance, 21);
        assert.strictEqual(snap.y, 458);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_recovery_timers_restore_normal_speed() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Terrain = freshTerrain();
        Terrain.start("sea-turtle");

        assert.strictEqual(Terrain.step(50, { active: true, distance: 720, y: 220 }), true);
        assert.strictEqual(Terrain.getSnapshot().slowdownRemainingMs, 1000);
        assert.strictEqual(Terrain.getSnapshot().shakeRemainingMs, 350);

        for (let i = 0; i < 6; i += 1) {
          Terrain.step(50, { active: true, distance: 725, y: 220 });
        }
        let ts = Terrain.getSnapshot();
        assert.strictEqual(ts.shakeRemainingMs, 50);
        assert.strictEqual(ts.slowdownRemainingMs, 700);

        Terrain.step(50, { active: true, distance: 725, y: 220 });
        ts = Terrain.getSnapshot();
        assert.strictEqual(ts.shakeRemainingMs, 0);
        assert.strictEqual(ts.collisionActive, false);
        assert.strictEqual(ts.knockbackOffsetX, 0);
        assert.strictEqual(ts.shakeOffsetY, 0);
        assert.strictEqual(ts.slowdownRemainingMs, 650);
        assert.strictEqual(ts.forwardSpeedMultiplier, 0.5);
        assert.strictEqual(ts.active, true);

        Terrain.stop();
        Terrain.start("sea-turtle");
        Terrain.step(50, { active: true, distance: 720, y: 220 });
        assert.strictEqual(Terrain.getSnapshot().knockbackOffsetX, 36);
        Terrain.step(50, { active: true, distance: 725, y: 220 });
        ts = Terrain.getSnapshot();
        assert.strictEqual(ts.knockbackOffsetX > 0, true);
        assert.strictEqual(ts.knockbackOffsetX < 36, true);

        Terrain.stop();
        Terrain.start("sea-turtle");
        Terrain.step(50, { active: true, distance: 720, y: 220 });
        for (let i = 0; i < 19; i += 1) {
          Terrain.step(50, { active: true, distance: 725, y: 220 });
        }
        ts = Terrain.getSnapshot();
        assert.strictEqual(ts.slowdownRemainingMs, 50);
        assert.strictEqual(ts.forwardSpeedMultiplier, 0.5);
        Terrain.step(50, { active: true, distance: 725, y: 220 });
        ts = Terrain.getSnapshot();
        assert.strictEqual(ts.slowdownRemainingMs, 0);
        assert.strictEqual(ts.forwardSpeedMultiplier, 1);
        assert.strictEqual(ts.collisionActive, false);
        assert.strictEqual(ts.active, true);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_runtime_renders_five_obstacles_and_collision_feedback() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToLaunch(dom, ctx, 2);
        ctx.timers.run(ctx.timers.pending()[0].id);
        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");

        assert.strictEqual(ctx.Terrain.getSnapshot().active, true);
        assert.strictEqual(ctx.Terrain.getSnapshot().missionId, "sea-turtle");

        const result = runToCollision(ctx, dom, 200);
        assert.strictEqual(result.collided, true);

        const distance = ctx.Travel.getSnapshot().distance;
        assert.strictEqual(ctx.Travel.getSnapshot().y, 240);

        assert.strictEqual(ctx.Terrain.getSnapshot().collisionCount, 1);
        assert.strictEqual(
          ctx.Terrain.getSnapshot().lastCollisionObstacleId,
          "coral-column-1"
        );
        assert.strictEqual(ctx.Terrain.getSnapshot().slowdownRemainingMs, 1000);
        assert.strictEqual(ctx.Terrain.getSnapshot().shakeRemainingMs, 350);
        assert.strictEqual(ctx.Terrain.getSnapshot().collisionActive, true);
        assert.strictEqual(ctx.Terrain.getSnapshot().forwardSpeedMultiplier, 0.5);

        assert.strictEqual(dom.rootEl.getAttribute("data-travel-mission-id"), "sea-turtle");
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-gup-id"), "gup-x");
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-ready"), "true");
        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_collision_never_causes_failure_or_stops_input() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToLaunch(dom, ctx, 2);
        ctx.timers.run(ctx.timers.pending()[0].id);

        const result = runToCollision(ctx, dom, 200);
        assert.strictEqual(result.collided, true);

        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        assert.strictEqual(ctx.Travel.getSnapshot().active, true);

        let frameTime = result.nextTime;
        function runFrame() {
          const pending = ctx.frames.pending();
          assert.strictEqual(pending.length, 1);
          ctx.frames.run(pending[0].id, frameTime);
          frameTime += 1000;
        }

        const slowStart = ctx.Travel.getSnapshot().distance;
        for (let i = 0; i < 4; i += 1) {
          runFrame();
        }
        const slowEnd = ctx.Travel.getSnapshot().distance;
        assert.strictEqual(slowEnd - slowStart, 12);
        assert.strictEqual(ctx.Terrain.getSnapshot().forwardSpeedMultiplier, 0.5);

        const canvas = dom.canvas;
        const yBeforeDrag = ctx.Travel.getSnapshot().y;
        dispatch(canvas, "pointerdown", {
          pointerId: 2,
          clientY: 160,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        dispatch(canvas, "pointermove", {
          pointerId: 2,
          clientY: 240,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        dispatch(canvas, "pointerup", {
          pointerId: 2,
          clientY: 240,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        assert.strictEqual(ctx.Travel.getSnapshot().y, yBeforeDrag + 120);
        assert.strictEqual(ctx.Travel.getSnapshot().dragging, false);

        dispatch(canvas, "pointerdown", {
          pointerId: 3,
          clientY: 120,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        dispatch(canvas, "pointerup", {
          pointerId: 3,
          clientY: 120,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        assert.strictEqual(ctx.Travel.getSnapshot().tapTargetY, 180);
        runFrame();
        assert.strictEqual(ctx.Travel.getSnapshot().y, 342);
        assert.strictEqual(ctx.Terrain.getSnapshot().forwardSpeedMultiplier, 0.5);

        const forbiddenKeys = ["health", "damage", "score", "failure", "restart"];
        const travelSnap = plain(ctx.Travel.getSnapshot());
        const terrainSnap = plain(ctx.Terrain.getSnapshot());
        const stateSnap = plain(ctx.State.getSnapshot());
        for (const key of forbiddenKeys) {
          assert.strictEqual(Object.prototype.hasOwnProperty.call(travelSnap, key), false);
          assert.strictEqual(Object.prototype.hasOwnProperty.call(terrainSnap, key), false);
          assert.strictEqual(Object.prototype.hasOwnProperty.call(stateSnap, key), false);
        }

        let guard = 0;
        while (ctx.Terrain.getSnapshot().forwardSpeedMultiplier !== 1 && guard < 100) {
          runFrame();
          guard += 1;
        }
        assert.strictEqual(ctx.Terrain.getSnapshot().forwardSpeedMultiplier, 1);
        const beforeFull = ctx.Travel.getSnapshot().distance;
        runFrame();
        assert.strictEqual(ctx.Travel.getSnapshot().distance - beforeFull, 6);
        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        assert.strictEqual(ctx.Travel.getSnapshot().active, true);
        """
    )
    _assert_node_ok(_run_node(harness))
