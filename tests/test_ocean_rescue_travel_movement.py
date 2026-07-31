"""Behavioral tests for Ocean Rescue travel movement and input.

Every JavaScript assertion runs the real tracked sources (``state.js``,
``missions.js``, ``gups.js``, ``launch.js``, ``travel.js``, and ``app.js``)
through the installed Node runtime in a fresh VM sandbox using a minimal fake
DOM, a fake canvas 2D context, a deterministic fake timer queue, and a
deterministic fake animation-frame queue. No npm packages, no browser
automation, no real-time sleeps, and no separate JavaScript test file are used.
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_BIN = shutil.which("node")
if NODE_BIN is None:
    raise RuntimeError("Node executable not found on PATH")


_TRAVEL_BOOTSTRAP = textwrap.dedent(
    """\
    const fs = require("fs");
    const vm = require("vm");
    const assert = require("assert");

    const STATE_SOURCE = fs.readFileSync("domains/ocean-rescue/src/state.js", "utf8");
    const MISSIONS_SOURCE = fs.readFileSync("domains/ocean-rescue/src/missions.js", "utf8");
    const GUPS_SOURCE = fs.readFileSync("domains/ocean-rescue/src/gups.js", "utf8");
    const LAUNCH_SOURCE = fs.readFileSync("domains/ocean-rescue/src/launch.js", "utf8");
    const TRAVEL_SOURCE = fs.readFileSync("domains/ocean-rescue/src/travel.js", "utf8");
    const APP_SOURCE = fs.readFileSync("domains/ocean-rescue/src/app.js", "utf8");

    function plain(value) {
      return JSON.parse(JSON.stringify(value));
    }

    function assertThrows(fn) {
      let threw = false;
      try {
        fn();
      } catch (err) {
        threw = true;
      }
      assert.strictEqual(threw, true);
    }

    function freshTravel() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(TRAVEL_SOURCE, sandbox, { filename: "travel.js" });
      return sandbox.window.OceanRescue.Travel;
    }

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

    function enterTravel(dom, ctx, gupIndex) {
      startLaunchToLaunch(dom, ctx, gupIndex);
      ctx.timers.run(ctx.timers.pending()[0].id);
      assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
    }

    function dispatch(canvas, type, event) {
      const list = canvas.listeners[type] || [];
      for (const fn of list.slice()) {
        fn(event);
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


def test_travel_public_contract_and_initial_state() -> None:
    harness = _TRAVEL_BOOTSTRAP + textwrap.dedent(
        """\
        const Travel = freshTravel();

        assert.deepStrictEqual(plain(Travel.Bounds), {
          minY: 120,
          maxY: 600,
          startY: 360,
        });
        assert.strictEqual(Travel.AutoForwardSpeed, 120);
        assert.strictEqual(Travel.TapSpeed, 360);
        assert.strictEqual(Object.isFrozen(Travel.Bounds), true);
        assert.strictEqual(Object.isFrozen(Travel), true);

        const expectedMembers = [
          "AutoForwardSpeed",
          "Bounds",
          "TapSpeed",
          "beginDrag",
          "endDrag",
          "getSnapshot",
          "moveDrag",
          "start",
          "step",
          "stop",
          "tapTo",
        ];
        assert.deepStrictEqual(Object.keys(Travel).sort(), expectedMembers.slice().sort());

        const hidden = [
          "reset",
          "setY",
          "setDistance",
          "complete",
          "collide",
          "addObstacle",
          "removeObstacle",
          "subscribe",
          "dispatch",
          "serialize",
          "hydrate",
          "load",
          "save",
          "history",
        ];
        for (const name of hidden) {
          assert.strictEqual(Travel[name], undefined, "exposed " + name);
        }

        assert.deepStrictEqual(plain(Travel.getSnapshot()), {
          active: false,
          distance: 0,
          y: 360,
          tapTargetY: null,
          dragging: false,
          pointerId: null,
        });

        assert.strictEqual(Object.isFrozen(Travel.getSnapshot()), true);
        assert.notStrictEqual(Travel.getSnapshot(), Travel.getSnapshot());
        const before = JSON.stringify(plain(Travel.getSnapshot()));
        const snap = Travel.getSnapshot();
        snap.y = 999;
        snap.distance = 999;
        snap.active = true;
        snap.tapTargetY = 111;
        assert.strictEqual(JSON.stringify(plain(Travel.getSnapshot())), before);

        Travel.extra = 1;
        Travel.Bounds.extra = 1;
        assert.strictEqual(Travel.extra, undefined);
        assert.strictEqual(Travel.Bounds.extra, undefined);
        Travel.AutoForwardSpeed = 999;
        Travel.Bounds.minY = 0;
        Travel.Bounds.maxY = 0;
        Travel.step = "no";
        assert.strictEqual(Travel.AutoForwardSpeed, 120);
        assert.strictEqual(Travel.Bounds.minY, 120);
        assert.strictEqual(Travel.Bounds.maxY, 600);
        assert.strictEqual(typeof Travel.step, "function");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_start_stop_and_auto_forward_step() -> None:
    harness = _TRAVEL_BOOTSTRAP + textwrap.dedent(
        """\
        const Travel = freshTravel();

        assert.strictEqual(Travel.start(), true);
        assert.deepStrictEqual(plain(Travel.getSnapshot()), {
          active: true,
          distance: 0,
          y: 360,
          tapTargetY: null,
          dragging: false,
          pointerId: null,
        });

        assert.strictEqual(Travel.step(1000), true);
        assert.strictEqual(Travel.getSnapshot().distance, 6);
        assert.strictEqual(Travel.getSnapshot().y, 360);

        assert.strictEqual(Travel.step(50), true);
        assert.strictEqual(Travel.getSnapshot().distance, 12);
        assert.strictEqual(Travel.getSnapshot().y, 360);

        assert.strictEqual(Travel.step(25), true);
        assert.strictEqual(Travel.getSnapshot().distance, 15);
        assert.strictEqual(Travel.getSnapshot().y, 360);

        assert.strictEqual(Travel.stop(), true);
        assert.strictEqual(Travel.getSnapshot().active, false);
        const stopped = plain(Travel.getSnapshot());
        assert.strictEqual(stopped.distance, 15);
        assert.strictEqual(stopped.y, 360);

        assert.strictEqual(Travel.step(50), false);
        assert.deepStrictEqual(plain(Travel.getSnapshot()), stopped);
        assert.strictEqual(Travel.stop(), false);

        assert.strictEqual(Travel.start(), true);
        assert.deepStrictEqual(plain(Travel.getSnapshot()), {
          active: true,
          distance: 0,
          y: 360,
          tapTargetY: null,
          dragging: false,
          pointerId: null,
        });

        const beforeInvalid = plain(Travel.getSnapshot());
        assert.strictEqual(Travel.step(0), false);
        assert.strictEqual(Travel.step(-1), false);
        assert.strictEqual(Travel.step(NaN), false);
        assert.strictEqual(Travel.step(Infinity), false);
        assert.strictEqual(Travel.step("50"), false);
        assert.strictEqual(Travel.step(null), false);
        assert.strictEqual(Travel.step(undefined), false);
        assert.strictEqual(Travel.step({}), false);
        assert.deepStrictEqual(plain(Travel.getSnapshot()), beforeInvalid);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_tap_assist_clamps_moves_smoothly_and_holds() -> None:
    harness = _TRAVEL_BOOTSTRAP + textwrap.dedent(
        """\
        const Travel = freshTravel();
        Travel.start();

        assert.strictEqual(Travel.tapTo(700), true);
        assert.strictEqual(Travel.getSnapshot().tapTargetY, 600);
        assert.strictEqual(Travel.tapTo(-50), true);
        assert.strictEqual(Travel.getSnapshot().tapTargetY, 120);
        assert.strictEqual(Travel.tapTo(NaN), false);
        assert.strictEqual(Travel.tapTo("360"), false);
        assert.strictEqual(Travel.tapTo(null), false);

        Travel.tapTo(600);
        let snap = Travel.getSnapshot();
        assert.strictEqual(snap.y, 360);
        assert.strictEqual(snap.tapTargetY, 600);
        let overshot = false;
        for (let i = 0; i < 20; i += 1) {
          assert.strictEqual(Travel.step(50), true);
          snap = Travel.getSnapshot();
          if (snap.y > 600) {
            overshot = true;
          }
          assert.strictEqual(snap.y >= 120, true);
        }
        assert.strictEqual(overshot, false);
        assert.strictEqual(snap.y, 600);
        assert.strictEqual(snap.tapTargetY, null);
        assert.strictEqual(snap.distance, 20 * 6);

        assert.strictEqual(Travel.tapTo(600), true);
        snap = Travel.getSnapshot();
        assert.strictEqual(snap.tapTargetY, null);
        assert.strictEqual(snap.y, 600);

        Travel.tapTo(120);
        overshot = false;
        for (let i = 0; i < 30; i += 1) {
          Travel.step(50);
          snap = Travel.getSnapshot();
          if (snap.y < 120) {
            overshot = true;
          }
        }
        assert.strictEqual(overshot, false);
        assert.strictEqual(snap.y, 120);
        assert.strictEqual(snap.tapTargetY, null);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_relative_drag_cancels_tap_and_holds_height() -> None:
    harness = _TRAVEL_BOOTSTRAP + textwrap.dedent(
        """\
        const Travel = freshTravel();
        Travel.start();

        Travel.tapTo(500);
        assert.strictEqual(Travel.getSnapshot().tapTargetY, 500);
        assert.strictEqual(Travel.beginDrag(7, 400), true);
        let snap = Travel.getSnapshot();
        assert.strictEqual(snap.tapTargetY, null);
        assert.strictEqual(snap.dragging, true);
        assert.strictEqual(snap.pointerId, 7);
        assert.strictEqual(snap.y, 360);

        assert.strictEqual(Travel.moveDrag(7, 420), true);
        assert.strictEqual(Travel.getSnapshot().y, 380);
        assert.strictEqual(Travel.moveDrag(7, 400), true);
        assert.strictEqual(Travel.getSnapshot().y, 360);
        assert.strictEqual(Travel.moveDrag(7, 500), true);
        assert.strictEqual(Travel.getSnapshot().y, 460);

        assert.strictEqual(Travel.moveDrag(7, 800), true);
        assert.strictEqual(Travel.getSnapshot().y, 600);
        assert.strictEqual(Travel.moveDrag(7, 780), true);
        assert.strictEqual(Travel.getSnapshot().y, 580);
        assert.strictEqual(Travel.moveDrag(7, -100), true);
        assert.strictEqual(Travel.getSnapshot().y, 120);
        assert.strictEqual(Travel.moveDrag(7, -80), true);
        assert.strictEqual(Travel.getSnapshot().y, 140);

        assert.strictEqual(Travel.step(50), true);
        snap = Travel.getSnapshot();
        assert.strictEqual(snap.distance, 6);
        assert.strictEqual(snap.y, 140);

        assert.strictEqual(Travel.endDrag(7), true);
        snap = Travel.getSnapshot();
        assert.strictEqual(snap.dragging, false);
        assert.strictEqual(snap.pointerId, null);
        assert.strictEqual(snap.y, 140);
        assert.strictEqual(snap.tapTargetY, null);

        assert.strictEqual(Travel.moveDrag(7, 400), false);
        assert.strictEqual(Travel.endDrag(7), false);
        assert.strictEqual(Travel.endDrag(99), false);
        assert.strictEqual(Travel.moveDrag(99, 400), false);
        snap = Travel.getSnapshot();
        assert.strictEqual(snap.y, 140);
        assert.strictEqual(snap.distance, 6);

        assert.strictEqual(Travel.beginDrag(1, 300), true);
        assert.strictEqual(Travel.beginDrag(2, 400), false);
        assert.strictEqual(Travel.moveDrag(2, 400), false);
        assert.strictEqual(Travel.endDrag(1), true);

        const beforeInvalid = plain(Travel.getSnapshot());
        assert.strictEqual(Travel.beginDrag(NaN, 300), false);
        assert.strictEqual(Travel.beginDrag(3, NaN), false);
        assert.strictEqual(Travel.beginDrag("3", 300), false);
        assert.strictEqual(Travel.beginDrag(null, 300), false);
        assert.strictEqual(Travel.moveDrag(3, NaN), false);
        assert.strictEqual(Travel.endDrag(3), false);
        assert.deepStrictEqual(plain(Travel.getSnapshot()), beforeInvalid);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_travel_handoff_starts_one_runtime_and_renders_gup() -> None:
    harness = _TRAVEL_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToLaunch(dom, ctx, 2);
        ctx.timers.run(ctx.timers.pending()[0].id);

        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        assert.strictEqual(ctx.Travel.getSnapshot().active, true);
        assert.strictEqual(ctx.Travel.getSnapshot().y, 360);
        assert.strictEqual(ctx.Travel.getSnapshot().distance, 0);

        assert.strictEqual(dom.rootEl.getAttribute("data-travel-runtime"), "active");
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-input"), "enabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-mission-id"), "sea-turtle");
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-gup-id"), "gup-x");
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-ready"), "true");
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-skipped"), "false");

        assert.strictEqual(ctx.frames.pending().length, 1);

        const calls = dom.canvas._context.calls;
        const clearCalls = calls.filter((call) => call[0] === "clearRect");
        assert.strictEqual(clearCalls.length, 1);
        assert.deepStrictEqual(clearCalls[0].slice(1), [0, 0, 1280, 720]);
        const fillTextCalls = calls.filter((call) => call[0] === "fillText");
        assert.strictEqual(fillTextCalls.length, 1);
        assert.strictEqual(fillTextCalls[0][1], "GUP-X");
        assert.strictEqual(fillTextCalls[0][2], 320);
        assert.strictEqual(fillTextCalls[0][3], 360);

        assert.strictEqual(dom.stage.hidden, false);
        assert.strictEqual(dom.stage.getAttribute("aria-hidden"), "false");
        assert.strictEqual(dom.goalBanner.hidden, false);
        assert.strictEqual(dom.goalBanner.textContent, "Rescue the sea turtle!");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_animation_frames_advance_world_without_duplicate_loop() -> None:
    harness = _TRAVEL_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToLaunch(dom, ctx, 2);
        ctx.timers.run(ctx.timers.pending()[0].id);
        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        assert.strictEqual(ctx.frames.pending().length, 1);

        const firstFrame = ctx.frames.pending()[0];
        ctx.frames.run(firstFrame.id, 1000);
        assert.strictEqual(ctx.Travel.getSnapshot().distance, 0);
        assert.strictEqual(ctx.Travel.getSnapshot().y, 360);
        assert.strictEqual(ctx.frames.pending().length, 1);

        const secondFrame = ctx.frames.pending()[0];
        ctx.frames.run(secondFrame.id, 2000);
        assert.strictEqual(ctx.Travel.getSnapshot().distance, 6);
        assert.strictEqual(ctx.Travel.getSnapshot().y, 360);
        assert.strictEqual(ctx.frames.pending().length, 1);

        const thirdFrame = ctx.frames.pending()[0];
        ctx.frames.run(thirdFrame.id, 3000);
        assert.strictEqual(ctx.Travel.getSnapshot().distance, 12);
        assert.strictEqual(ctx.Travel.getSnapshot().y, 360);
        assert.strictEqual(ctx.frames.pending().length, 1);

        const oldFrame = ctx.frames.pending()[0];

        function step(to) {
          const token = ctx.State.beginTransition(to);
          assert.notStrictEqual(token, null, "begin -> " + to);
          assert.strictEqual(ctx.State.completeTransition(token), true);
        }
        step("RESCUE_SITE_TRANSITION");
        step("RESCUE_TUTORIAL");
        step("RESCUE_ACTIVE");
        step("RESCUE_SUCCESS");
        step("MISSION_COMPLETE");
        step("MISSION_SELECT");
        step("GUP_SELECT");
        assert.strictEqual(ctx.App.launchSelectedGup(), true);
        assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
        ctx.timers.run(ctx.timers.pending()[0].id);
        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        assert.strictEqual(ctx.Travel.getSnapshot().distance, 0);

        const oldEntry = ctx.frames.frames.find((entry) => entry.id === oldFrame.id);
        assert.strictEqual(oldEntry.cancelled, true);
        assert.strictEqual(ctx.frames.pending().length, 1);

        const distanceBeforeStale = ctx.Travel.getSnapshot().distance;
        const yBeforeStale = ctx.Travel.getSnapshot().y;
        oldFrame.fn(4000);
        assert.strictEqual(ctx.Travel.getSnapshot().distance, distanceBeforeStale);
        assert.strictEqual(ctx.Travel.getSnapshot().y, yBeforeStale);
        assert.strictEqual(ctx.frames.pending().length, 1);
        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");

        const freshFrame = ctx.frames.pending()[0];
        ctx.frames.run(freshFrame.id, 5000);
        assert.strictEqual(ctx.Travel.getSnapshot().distance, 0);
        const nextFrame = ctx.frames.pending()[0];
        ctx.frames.run(nextFrame.id, 6000);
        assert.strictEqual(ctx.Travel.getSnapshot().distance, 6);
        assert.strictEqual(ctx.frames.pending().length, 1);
        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_pointer_tap_maps_to_canvas_and_drives_tap_assist() -> None:
    harness = _TRAVEL_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        enterTravel(dom, ctx, 2);
        const canvas = dom.canvas;
        assert.strictEqual(canvas.height, 720);
        assert.strictEqual(canvas.rect.height, 480);

        dispatch(canvas, "pointerdown", {
          pointerId: 1,
          clientY: 200,
          isPrimary: true,
          preventDefault() {},
        });
        dispatch(canvas, "pointerup", {
          pointerId: 1,
          clientY: 200,
          isPrimary: true,
          preventDefault() {},
        });
        assert.strictEqual(ctx.Travel.getSnapshot().tapTargetY, 300);
        assert.strictEqual(ctx.Travel.getSnapshot().y, 360);

        const first = ctx.frames.pending()[0];
        ctx.frames.run(first.id, 1000);
        const second = ctx.frames.pending()[0];
        ctx.frames.run(second.id, 2000);
        let snap = ctx.Travel.getSnapshot();
        assert.strictEqual(snap.tapTargetY, 300);
        assert.strictEqual(snap.y, 342);
        assert.strictEqual(snap.distance, 6);

        let overshot = false;
        let ran = 0;
        while (ran < 12) {
          const pending = ctx.frames.pending();
          if (pending.length === 0) {
            break;
          }
          ctx.frames.run(pending[0].id, 3000 + (ran + 1) * 1000);
          snap = ctx.Travel.getSnapshot();
          if (snap.y < 300) {
            overshot = true;
          }
          ran += 1;
        }
        assert.strictEqual(overshot, false);
        assert.strictEqual(snap.y, 300);
        assert.strictEqual(snap.tapTargetY, null);

        const beforeSecondary = plain(ctx.Travel.getSnapshot());
        dispatch(canvas, "pointerdown", {
          pointerId: 99,
          clientY: 300,
          isPrimary: false,
          preventDefault() {},
        });
        dispatch(canvas, "pointermove", {
          pointerId: 99,
          clientY: 350,
          isPrimary: false,
          button: 0,
          preventDefault() {},
        });
        dispatch(canvas, "pointerup", {
          pointerId: 99,
          clientY: 350,
          isPrimary: false,
          button: 0,
          preventDefault() {},
        });
        assert.deepStrictEqual(plain(ctx.Travel.getSnapshot()), beforeSecondary);

        dispatch(canvas, "pointerdown", {
          pointerId: 2,
          clientY: NaN,
          isPrimary: true,
        });
        dispatch(canvas, "pointerup", {
          pointerId: 2,
          clientY: 300,
          isPrimary: true,
          preventDefault() {},
        });
        assert.deepStrictEqual(plain(ctx.Travel.getSnapshot()), beforeSecondary);
        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_pointer_drag_is_relative_and_cancel_safe() -> None:
    harness = _TRAVEL_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        enterTravel(dom, ctx, 2);
        const canvas = dom.canvas;

        dispatch(canvas, "pointerdown", {
          pointerId: 1,
          clientY: 200,
          isPrimary: true,
          preventDefault() {},
        });
        dispatch(canvas, "pointermove", {
          pointerId: 1,
          clientY: 205,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        let snap = ctx.Travel.getSnapshot();
        assert.strictEqual(snap.dragging, false);
        assert.strictEqual(snap.y, 360);

        dispatch(canvas, "pointermove", {
          pointerId: 1,
          clientY: 210,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        snap = ctx.Travel.getSnapshot();
        assert.strictEqual(snap.dragging, true);
        assert.strictEqual(snap.y, 375);

        dispatch(canvas, "pointermove", {
          pointerId: 1,
          clientY: 230,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        snap = ctx.Travel.getSnapshot();
        assert.strictEqual(snap.y, 405);

        dispatch(canvas, "pointerup", {
          pointerId: 1,
          clientY: 230,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        snap = ctx.Travel.getSnapshot();
        assert.strictEqual(snap.dragging, false);
        assert.strictEqual(snap.y, 405);
        assert.strictEqual(snap.tapTargetY, null);

        dispatch(canvas, "pointerdown", {
          pointerId: 1,
          clientY: 230,
          isPrimary: true,
          preventDefault() {},
        });
        dispatch(canvas, "pointerup", {
          pointerId: 1,
          clientY: 230,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        assert.strictEqual(ctx.Travel.getSnapshot().tapTargetY, 345);

        dispatch(canvas, "pointerdown", {
          pointerId: 1,
          clientY: 230,
          isPrimary: true,
          preventDefault() {},
        });
        dispatch(canvas, "pointermove", {
          pointerId: 1,
          clientY: 250,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        snap = ctx.Travel.getSnapshot();
        assert.strictEqual(snap.tapTargetY, null);
        assert.strictEqual(snap.dragging, true);
        assert.strictEqual(snap.y, 435);

        dispatch(canvas, "pointerup", {
          pointerId: 1,
          clientY: 250,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        snap = ctx.Travel.getSnapshot();
        assert.strictEqual(snap.dragging, false);
        assert.strictEqual(snap.y, 435);
        assert.strictEqual(snap.tapTargetY, null);

        dispatch(canvas, "pointerdown", {
          pointerId: 1,
          clientY: 200,
          isPrimary: true,
          preventDefault() {},
        });
        dispatch(canvas, "pointermove", {
          pointerId: 1,
          clientY: 220,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        snap = ctx.Travel.getSnapshot();
        assert.strictEqual(snap.dragging, true);
        dispatch(canvas, "pointercancel", {
          pointerId: 1,
          isPrimary: true,
        });
        snap = ctx.Travel.getSnapshot();
        assert.strictEqual(snap.dragging, false);
        assert.strictEqual(snap.tapTargetY, null);

        const beforeStale = plain(ctx.Travel.getSnapshot());
        dispatch(canvas, "pointermove", {
          pointerId: 1,
          clientY: 300,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        dispatch(canvas, "pointerup", {
          pointerId: 1,
          clientY: 300,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        dispatch(canvas, "pointercancel", {
          pointerId: 1,
          isPrimary: true,
        });
        dispatch(canvas, "pointerdown", {
          pointerId: 1,
          clientY: 300,
          isPrimary: true,
          button: 2,
          preventDefault() {},
        });
        dispatch(canvas, "pointermove", {
          pointerId: 1,
          clientY: 350,
          isPrimary: true,
          button: 2,
          preventDefault() {},
        });
        dispatch(canvas, "pointerup", {
          pointerId: 1,
          clientY: 350,
          isPrimary: true,
          button: 2,
          preventDefault() {},
        });
        dispatch(canvas, "pointerdown", {
          pointerId: 1,
          clientY: 300,
          isPrimary: true,
          preventDefault() {},
        });
        dispatch(canvas, "pointerdown", {
          pointerId: 2,
          clientY: 320,
          isPrimary: true,
          preventDefault() {},
        });
        dispatch(canvas, "pointerup", {
          pointerId: 2,
          clientY: 320,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        assert.deepStrictEqual(plain(ctx.Travel.getSnapshot()), beforeStale);
        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        """
    )
    _assert_node_ok(_run_node(harness))
