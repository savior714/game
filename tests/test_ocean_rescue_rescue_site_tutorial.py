"""Behavioral tests for the Ocean Rescue site-transition and tutorial handoff.

Every JavaScript assertion runs the real tracked sources (``state.js``,
``missions.js``, ``gups.js``, ``launch.js``, ``travel.js``, ``terrain.js``,
``rescue.js``, and ``app.js``) through the installed Node runtime in a fresh
VM sandbox using a minimal fake DOM, a fake canvas 2D context, a deterministic
fake timer queue, and a deterministic fake animation-frame queue. No npm
packages, no browser automation, no real-time sleeps, and no separate
JavaScript test file are used.
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
    const RESCUE_SOURCE = fs.readFileSync("domains/ocean-rescue/src/rescue.js", "utf8");
    const APP_SOURCE = fs.readFileSync("domains/ocean-rescue/src/app.js", "utf8");

    function plain(value) {
      return JSON.parse(JSON.stringify(value));
    }

    function freshRescue() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(RESCUE_SOURCE, sandbox, { filename: "rescue.js" });
      return sandbox.window.OceanRescue.Rescue;
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

    function makeCanvasElement(canvasContext) {
      const el = makeElement("canvas");
      el.width = 1280;
      el.height = 720;
      el.rect = { top: 0, height: 480 };
      if (canvasContext === null) {
        el._context = null;
        el.getContext = function () {
          return null;
        };
      } else {
        el._context = canvasContext || makeContext();
        el.getContext = function (type) {
          if (type === "2d") {
            return el._context;
          }
          return null;
        };
      }
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

    function makeBootDom(opts) {
      const options = opts || {};
      const includeRescue = options.includeRescue !== false;
      const canvasContext = options.canvasContext;
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
      const canvas = makeCanvasElement(canvasContext);

      const rescueOverlay = makeElement("section");
      rescueOverlay.hidden = true;
      const rescueTitle = makeElement("h2");
      const rescueCompanion = makeElement("p");
      const rescueSituation = makeElement("p");
      const rescueReady = makeElement("div");
      rescueReady.hidden = true;
      const rescueTutorial = makeElement("div");
      rescueTutorial.hidden = true;
      const rescueInstruction = makeElement("p");
      const rescueHand = makeElement("div");

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
      if (includeRescue) {
        rescueOverlay.appendChild(rescueTitle);
        rescueOverlay.appendChild(rescueCompanion);
        rescueOverlay.appendChild(rescueSituation);
        rescueOverlay.appendChild(rescueReady);
        rescueOverlay.appendChild(rescueTutorial);
        rescueTutorial.appendChild(rescueInstruction);
        rescueTutorial.appendChild(rescueHand);
        stage.appendChild(rescueOverlay);
      }
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
      if (includeRescue) {
        elements["ocean-rescue-rescue-overlay"] = rescueOverlay;
        elements["ocean-rescue-rescue-companion"] = rescueCompanion;
        elements["ocean-rescue-rescue-situation"] = rescueSituation;
        elements["ocean-rescue-rescue-ready"] = rescueReady;
        elements["ocean-rescue-rescue-tutorial"] = rescueTutorial;
        elements["ocean-rescue-rescue-instruction"] = rescueInstruction;
        elements["ocean-rescue-rescue-hand"] = rescueHand;
      }
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
        rescueOverlay,
        rescueCompanion,
        rescueSituation,
        rescueReady,
        rescueTutorial,
        rescueInstruction,
        rescueHand,
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

    function loadApp(document, windowExtras, options) {
      const opts = options || {};
      const timers = makeTimerQueue();
      const frames = makeFrameQueue();
      const extras = Object.assign({}, windowExtras, {
        setTimeout: opts.omitSetTimeout ? undefined : timers.setTimeout,
        clearTimeout: opts.omitClearTimeout ? undefined : timers.clearTimeout,
        requestAnimationFrame: opts.omitRequestAnimationFrame
          ? undefined
          : frames.requestAnimationFrame,
        cancelAnimationFrame: opts.omitCancelAnimationFrame
          ? undefined
          : frames.cancelAnimationFrame,
      });
      const sandbox = { window: extras, document };
      vm.createContext(sandbox);
      vm.runInContext(STATE_SOURCE, sandbox, { filename: "state.js" });
      vm.runInContext(MISSIONS_SOURCE, sandbox, { filename: "missions.js" });
      vm.runInContext(GUPS_SOURCE, sandbox, { filename: "gups.js" });
      vm.runInContext(LAUNCH_SOURCE, sandbox, { filename: "launch.js" });
      vm.runInContext(TRAVEL_SOURCE, sandbox, { filename: "travel.js" });
      vm.runInContext(TERRAIN_SOURCE, sandbox, { filename: "terrain.js" });
      if (!opts.skipRescue) {
        vm.runInContext(RESCUE_SOURCE, sandbox, { filename: "rescue.js" });
      }
      vm.runInContext(APP_SOURCE, sandbox, { filename: "app.js" });
      const OceanRescue = sandbox.window.OceanRescue;
      return {
        sandbox,
        timers,
        frames,
        State: OceanRescue.State,
        Missions: OceanRescue.Missions,
        Gups: OceanRescue.Gups,
        Launch: OceanRescue.Launch,
        Travel: OceanRescue.Travel,
        Terrain: OceanRescue.Terrain,
        Rescue: OceanRescue.Rescue,
        App: OceanRescue.App,
      };
    }

    function startLaunchToTravel(dom, ctx, gupIndex, missionIndex) {
      const mIndex = missionIndex === undefined ? 0 : missionIndex;
      dom.document.domLoadedHandler();
      assert.strictEqual(ctx.App.boot(), true);
      dom.missionList.children[mIndex].click();
      dom.gupList.children[gupIndex].click();
      dom.gupLaunch.click();
      assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
      const pending = ctx.timers.pending();
      assert.strictEqual(pending.length >= 1, true);
      ctx.timers.run(pending[0].id);
      assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
    }

    function runToArrival(ctx, maxFrames) {
      let frameTime = 1000;
      let frames = 0;
      for (;;) {
        const pending = ctx.frames.pending();
        if (pending.length === 0) {
          return { arrived: false, frames, phase: ctx.State.getSnapshot().phase };
        }
        frames += 1;
        if (frames > maxFrames) {
          return { arrived: false, frames, phase: ctx.State.getSnapshot().phase };
        }
        ctx.frames.run(pending[0].id, frameTime);
        frameTime += 1000;
        if (ctx.State.getSnapshot().phase !== "TRAVEL") {
          return { arrived: true, frames, phase: ctx.State.getSnapshot().phase };
        }
      }
    }

    function lastPendingTimer(ctx) {
      const pending = ctx.timers.pending();
      assert.strictEqual(pending.length >= 1, true);
      return pending[pending.length - 1];
    }

    function dispatch(element, type, event) {
      const list = element.listeners[type] || [];
      for (const fn of list.slice()) {
        fn(event);
      }
    }

    function fillTextLabels(canvas) {
      return (canvas._context.calls || [])
        .filter((call) => call[0] === "fillText")
        .map((call) => call[1]);
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


def test_rescue_catalog_timing_and_public_contract() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Rescue = freshRescue();

        assert.strictEqual(Rescue.ArrivalDistance, 6000);
        assert.strictEqual(Rescue.SiteTransitionMs, 1500);
        assert.strictEqual(Rescue.TutorialDurationMs, 3000);
        assert.strictEqual(Object.isFrozen(Rescue), true);

        assert.deepStrictEqual(
          plain(Rescue.Catalog).map((entry) => entry.missionId),
          ["sea-turtle", "crab", "young-whale"]
        );
        assert.strictEqual(Object.isFrozen(Rescue.Catalog), true);
        assert.strictEqual(Object.isFrozen(Rescue.Catalog[0]), true);
        assert.strictEqual(Object.isFrozen(Rescue.Catalog[1]), true);
        assert.strictEqual(Object.isFrozen(Rescue.Catalog[2]), true);

        const expected = [
          {
            missionId: "sea-turtle",
            targetLabel: "Sea turtle",
            toolLabel: "Cutter",
            situation: "The sea turtle is tangled in three ropes.",
            tutorial: "Start here. Follow the rope to the end!"
          },
          {
            missionId: "crab",
            targetLabel: "Crab",
            toolLabel: "Grabber arm",
            situation: "The crab is trapped under three rocks.",
            tutorial: "Hold the rock. Move it. Release it in the zone!"
          },
          {
            missionId: "young-whale",
            targetLabel: "Young whale",
            toolLabel: "GUP hook",
            situation: "Debris is blocking the young whale\u2019s path.",
            tutorial: "Drag from the debris to the GUP hook!"
          }
        ];
        assert.deepStrictEqual(plain(Rescue.Catalog), expected);

        assert.deepStrictEqual(
          Object.keys(Rescue).sort(),
          [
            "ArrivalDistance",
            "Catalog",
            "SiteTransitionMs",
            "TutorialDurationMs",
            "getMissionContent",
            "hasArrived"
          ].sort()
        );
        const hidden = [
          "start",
          "stop",
          "complete",
          "skip",
          "activate",
          "setPhase",
          "transition",
          "timer",
          "reset",
          "subscribe",
          "dispatch",
          "serialize",
          "hydrate",
          "save",
          "load",
          "history"
        ];
        for (const name of hidden) {
          assert.strictEqual(Rescue[name], undefined, "exposed " + name);
        }

        Rescue.extra = 1;
        Rescue.Catalog.extra = 1;
        Rescue.Catalog[0].extra = 1;
        assert.strictEqual(Rescue.extra, undefined);
        assert.strictEqual(Rescue.Catalog.extra, undefined);
        assert.strictEqual(Rescue.Catalog[0].extra, undefined);

        assert.strictEqual(Rescue.getMissionContent("sea-turtle"), Rescue.Catalog[0]);
        assert.strictEqual(Rescue.getMissionContent("crab"), Rescue.Catalog[1]);
        assert.strictEqual(Rescue.getMissionContent("young-whale"), Rescue.Catalog[2]);
        assert.strictEqual(Rescue.getMissionContent("sea-turtle"), Rescue.Catalog[0]);
        assert.strictEqual(Rescue.getMissionContent("unknown"), null);
        assert.strictEqual(Rescue.getMissionContent(""), null);
        assert.strictEqual(Rescue.getMissionContent(null), null);
        assert.strictEqual(Rescue.getMissionContent(undefined), null);
        assert.strictEqual(Rescue.getMissionContent(123), null);
        assert.strictEqual(Rescue.getMissionContent({}), null);
        const before = JSON.stringify(Rescue.Catalog);
        Rescue.getMissionContent("sea-turtle");
        Rescue.getMissionContent("crab");
        assert.strictEqual(JSON.stringify(Rescue.Catalog), before);

        assert.strictEqual(Rescue.hasArrived({ active: true, distance: 5999.999 }), false);
        assert.strictEqual(Rescue.hasArrived({ active: true, distance: 6000 }), true);
        assert.strictEqual(Rescue.hasArrived({ active: true, distance: 6000.001 }), true);
        assert.strictEqual(Rescue.hasArrived({ active: false, distance: 9000 }), false);
        assert.strictEqual(Rescue.hasArrived({ active: true, distance: -1 }), false);
        assert.strictEqual(Rescue.hasArrived({ active: true, distance: NaN }), false);
        assert.strictEqual(Rescue.hasArrived({ active: true, distance: Infinity }), false);
        assert.strictEqual(Rescue.hasArrived({ active: true }), false);
        assert.strictEqual(Rescue.hasArrived(null), false);
        assert.strictEqual(Rescue.hasArrived(undefined), false);
        assert.strictEqual(Rescue.hasArrived(42), false);
        assert.strictEqual(Rescue.hasArrived({ active: true, distance: "6000" }), false);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_arrival_threshold_is_distance_based_and_exact() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Rescue = freshRescue();
        const Travel = freshTravel();

        assert.strictEqual(Rescue.ArrivalDistance, 6000);
        assert.strictEqual(Travel.AutoForwardSpeed, 120);
        assert.strictEqual(Rescue.ArrivalDistance / Travel.AutoForwardSpeed, 50);

        assert.strictEqual(Rescue.hasArrived({ active: true, distance: 5999.999 }), false);
        assert.strictEqual(Rescue.hasArrived({ active: true, distance: 6000 }), true);
        assert.strictEqual(Rescue.hasArrived({ active: true, distance: 6000.001 }), true);
        assert.strictEqual(Rescue.hasArrived({ active: false, distance: 6000 }), false);

        assert.strictEqual(Travel.start(), true);
        let elapsed = 0;
        for (let i = 0; i < 1000; i += 1) {
          assert.strictEqual(Travel.step(50), true);
          elapsed += 50;
        }
        assert.strictEqual(Travel.getSnapshot().distance, 6000);
        assert.strictEqual(elapsed, 50000);
        assert.strictEqual(Rescue.hasArrived(Travel.getSnapshot()), true);

        const travelKeys = Object.keys(Travel).sort();
        for (const name of ["start", "stop", "step", "getSnapshot"]) {
          assert.strictEqual(travelKeys.includes(name), true);
        }
        assert.strictEqual(travelKeys.includes("complete"), false);
        assert.strictEqual(travelKeys.includes("timer"), false);
        assert.strictEqual(typeof Travel.complete, "undefined");
        assert.strictEqual(typeof Travel.timer, "undefined");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_runtime_arrival_stops_travel_terrain_and_input() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToTravel(dom, ctx, 0);

        dispatch(dom.canvas, "pointerdown", {
          pointerId: 1,
          clientY: 240,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        dispatch(dom.canvas, "pointermove", {
          pointerId: 1,
          clientY: 160,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        assert.strictEqual(ctx.Travel.getSnapshot().dragging, true);

        const result = runToArrival(ctx, 4000);
        assert.strictEqual(result.arrived, true);
        assert.strictEqual(result.phase, "RESCUE_SITE_TRANSITION");
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SITE_TRANSITION");

        assert.strictEqual(ctx.Travel.getSnapshot().active, false);
        assert.strictEqual(ctx.Terrain.getSnapshot().active, false);
        assert.strictEqual(ctx.Travel.getSnapshot().dragging, false);
        assert.strictEqual(ctx.Travel.getSnapshot().pointerId, null);
        assert.strictEqual(ctx.Travel.getSnapshot().tapTargetY, null);
        assert.strictEqual(ctx.Travel.getSnapshot().distance >= 6000, true);

        assert.strictEqual(ctx.frames.pending().length, 0);

        assert.strictEqual(dom.rootEl.getAttribute("data-travel-runtime"), "stopped");
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-input"), "disabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-sequence"), "active");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "site-transition");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "disabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-mission-id"), "sea-turtle");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-gup-id"), "gup-c");

        const travelSnapBefore = JSON.stringify(ctx.Travel.getSnapshot());
        dispatch(dom.canvas, "pointerdown", {
          pointerId: 2,
          clientY: 100,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        dispatch(dom.canvas, "pointermove", {
          pointerId: 2,
          clientY: 300,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        dispatch(dom.canvas, "pointerup", {
          pointerId: 2,
          clientY: 300,
          isPrimary: true,
          button: 0,
          preventDefault() {},
        });
        assert.strictEqual(JSON.stringify(ctx.Travel.getSnapshot()), travelSnapBefore);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_site_transition_presentation_and_input_consumption() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToTravel(dom, ctx, 0);

        const result = runToArrival(ctx, 4000);
        assert.strictEqual(result.arrived, true);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SITE_TRANSITION");

        assert.strictEqual(dom.stage.hidden, false);
        assert.strictEqual(dom.rescueOverlay.hidden, false);
        assert.strictEqual(dom.rescueCompanion.textContent, "Peso:");
        assert.strictEqual(
          dom.rescueSituation.textContent,
          "The sea turtle is tangled in three ropes."
        );
        assert.strictEqual(dom.rescueReady.hidden, false);
        assert.strictEqual(dom.rescueTutorial.hidden, true);
        assert.strictEqual(
          dom.statusEl.textContent,
          "Rescue site: The sea turtle is tangled in three ropes."
        );
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "site-transition");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "disabled");

        const labels = fillTextLabels(dom.canvas);
        assert.strictEqual(labels.includes("Sea turtle"), true);
        assert.strictEqual(labels.includes("Cutter"), true);
        assert.strictEqual(labels.includes("GUP-C"), true);

        const transitionTimers = ctx.timers.pending().filter((t) => t.delay === 1500);
        assert.strictEqual(transitionTimers.length, 1);
        const beforeCount = ctx.timers.pending().length;

        const events = [];
        dispatch(dom.stage, "pointerdown", {
          pointerId: 9,
          clientY: 100,
          isPrimary: true,
          button: 0,
          preventDefault() {
            events.push("preventDefault");
          },
          stopPropagation() {
            events.push("stopPropagation");
          },
        });
        assert.strictEqual(events.includes("preventDefault"), true);
        assert.strictEqual(events.includes("stopPropagation"), true);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SITE_TRANSITION");
        assert.strictEqual(dom.rescueTutorial.hidden, true);
        assert.strictEqual(dom.rescueReady.hidden, false);
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "disabled");
        assert.strictEqual(ctx.timers.pending().length, beforeCount);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_site_transition_enters_exact_tutorial() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToTravel(dom, ctx, 0);

        const result = runToArrival(ctx, 4000);
        assert.strictEqual(result.arrived, true);
        const transitionTimer = lastPendingTimer(ctx);
        assert.strictEqual(transitionTimer.delay, 1500);
        ctx.timers.run(transitionTimer.id);

        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_TUTORIAL");
        assert.strictEqual(dom.rescueReady.hidden, true);
        assert.strictEqual(dom.rescueTutorial.hidden, false);
        assert.strictEqual(
          dom.rescueInstruction.textContent,
          "Start here. Follow the rope to the end!"
        );
        assert.strictEqual(
          dom.rescueTutorial.classList.contains("ocean-rescue-tutorial-active"),
          true
        );
        assert.strictEqual(
          dom.rescueTutorial.classList.contains("ocean-rescue-tutorial-hold"),
          false
        );
        assert.strictEqual(
          dom.statusEl.textContent,
          "Start here. Follow the rope to the end!"
        );
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "tutorial");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "disabled");

        const tutorialTimer = lastPendingTimer(ctx);
        assert.strictEqual(tutorialTimer.delay, 3000);

        assert.strictEqual(ctx.Travel.getSnapshot().active, false);
        assert.deepStrictEqual(
          Object.keys(dom.canvas.listeners).sort(),
          ["pointercancel", "pointerdown", "pointermove", "pointerup"]
        );
        """
    )
    _assert_node_ok(_run_node(harness))


def test_tutorial_auto_completion_enters_rescue_active() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToTravel(dom, ctx, 0);

        const result = runToArrival(ctx, 4000);
        assert.strictEqual(result.arrived, true);
        const transitionTimer = lastPendingTimer(ctx);
        ctx.timers.run(transitionTimer.id);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_TUTORIAL");

        const tutorialTimer = lastPendingTimer(ctx);
        assert.strictEqual(tutorialTimer.delay, 3000);
        ctx.timers.run(tutorialTimer.id);

        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "active");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "enabled");
        assert.strictEqual(
          dom.rootEl.getAttribute("data-rescue-tutorial-skipped"),
          "false"
        );
        assert.strictEqual(
          dom.rescueTutorial.classList.contains("ocean-rescue-tutorial-active"),
          false
        );
        assert.strictEqual(dom.rescueHand.hidden, true);
        assert.strictEqual(dom.rescueOverlay.hidden, false);
        assert.strictEqual(dom.rescueTutorial.hidden, false);
        assert.strictEqual(
          dom.rescueInstruction.textContent,
          "Start here. Follow the rope to the end!"
        );
        assert.strictEqual(dom.statusEl.textContent, "Rescue controls ready");

        const pendingAfter = ctx.timers.pending().length;
        const markersBefore =
          dom.rootEl.getAttribute("data-rescue-phase") +
          "|" +
          dom.rootEl.getAttribute("data-rescue-input") +
          "|" +
          dom.rootEl.getAttribute("data-rescue-tutorial-skipped");
        const stateBefore = JSON.stringify(ctx.State.getSnapshot());

        tutorialTimer.fn();
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        assert.strictEqual(JSON.stringify(ctx.State.getSnapshot()), stateBefore);
        assert.strictEqual(ctx.timers.pending().length, pendingAfter);
        assert.strictEqual(
          dom.rootEl.getAttribute("data-rescue-phase") +
            "|" +
            dom.rootEl.getAttribute("data-rescue-input") +
            "|" +
            dom.rootEl.getAttribute("data-rescue-tutorial-skipped"),
          markersBefore
        );
        """
    )
    _assert_node_ok(_run_node(harness))


def test_tutorial_tap_skips_once_and_stale_timer_is_ignored() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToTravel(dom, ctx, 0);

        const result = runToArrival(ctx, 4000);
        assert.strictEqual(result.arrived, true);
        const transitionTimer = lastPendingTimer(ctx);
        ctx.timers.run(transitionTimer.id);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_TUTORIAL");

        const tutorialTimer = lastPendingTimer(ctx);
        assert.strictEqual(tutorialTimer.delay, 3000);

        const events = [];
        dispatch(dom.stage, "pointerdown", {
          pointerId: 9,
          clientY: 120,
          isPrimary: true,
          button: 0,
          preventDefault() {
            events.push("preventDefault");
          },
          stopPropagation() {
            events.push("stopPropagation");
          },
        });

        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "active");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "enabled");
        assert.strictEqual(
          dom.rootEl.getAttribute("data-rescue-tutorial-skipped"),
          "true"
        );
        assert.strictEqual(
          dom.rescueTutorial.classList.contains("ocean-rescue-tutorial-active"),
          false
        );
        assert.strictEqual(dom.rescueHand.hidden, true);
        assert.strictEqual(dom.statusEl.textContent, "Rescue controls ready");

        const tutorialEntry = ctx.timers.timers.find((t) => t.id === tutorialTimer.id);
        assert.strictEqual(tutorialEntry.cancelled, true);

        const stateBefore = JSON.stringify(ctx.State.getSnapshot());
        const pendingBefore = ctx.timers.pending().length;
        const markersBefore =
          dom.rootEl.getAttribute("data-rescue-phase") +
          "|" +
          dom.rootEl.getAttribute("data-rescue-input") +
          "|" +
          dom.rootEl.getAttribute("data-rescue-tutorial-skipped");

        tutorialTimer.fn();
        assert.strictEqual(JSON.stringify(ctx.State.getSnapshot()), stateBefore);
        assert.strictEqual(ctx.timers.pending().length, pendingBefore);
        assert.strictEqual(
          dom.rootEl.getAttribute("data-rescue-phase") +
            "|" +
            dom.rootEl.getAttribute("data-rescue-input") +
            "|" +
            dom.rootEl.getAttribute("data-rescue-tutorial-skipped"),
          markersBefore
        );

        dispatch(dom.stage, "pointerdown", {
          pointerId: 10,
          clientY: 200,
          isPrimary: true,
          button: 0,
          preventDefault() {},
          stopPropagation() {},
        });
        assert.strictEqual(JSON.stringify(ctx.State.getSnapshot()), stateBefore);
        assert.strictEqual(ctx.timers.pending().length, pendingBefore);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_all_mission_site_content_and_missing_optional_runtime_are_safe() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const cases = [
          {
            missionIndex: 0,
            companion: "Peso:",
            target: "Sea turtle",
            tool: "Cutter",
            situation: "The sea turtle is tangled in three ropes.",
            tutorial: "Start here. Follow the rope to the end!"
          },
          {
            missionIndex: 1,
            companion: "Tweak:",
            target: "Crab",
            tool: "Grabber arm",
            situation: "The crab is trapped under three rocks.",
            tutorial: "Hold the rock. Move it. Release it in the zone!"
          },
          {
            missionIndex: 2,
            companion: "Captain Barnacles:",
            target: "Young whale",
            tool: "GUP hook",
            situation: "Debris is blocking the young whale\\u2019s path.",
            tutorial: "Drag from the debris to the GUP hook!"
          }
        ];
        for (const c of cases) {
          const dom = makeBootDom();
          const ctx = loadApp(dom.document);
          ctx.Missions.completeMission("sea-turtle");
          ctx.Missions.completeMission("crab");
          startLaunchToTravel(dom, ctx, 0, c.missionIndex);

          const result = runToArrival(ctx, 4000);
          assert.strictEqual(result.arrived, true);
          assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SITE_TRANSITION");
          assert.strictEqual(dom.rescueCompanion.textContent, c.companion);
          assert.strictEqual(dom.rescueSituation.textContent, c.situation);
          assert.strictEqual(dom.rescueReady.hidden, false);

          const labels = fillTextLabels(dom.canvas);
          assert.strictEqual(labels.includes(c.target), true);
          assert.strictEqual(labels.includes(c.tool), true);

          const transitionTimer = lastPendingTimer(ctx);
          assert.strictEqual(transitionTimer.delay, 1500);
          ctx.timers.run(transitionTimer.id);
          assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_TUTORIAL");
          assert.strictEqual(dom.rescueInstruction.textContent, c.tutorial);
          assert.strictEqual(dom.statusEl.textContent, c.tutorial);
          assert.strictEqual(
            dom.rescueTutorial.classList.contains("ocean-rescue-tutorial-active"),
            true
          );

          const tutorialTimer = lastPendingTimer(ctx);
          assert.strictEqual(tutorialTimer.delay, 3000);
          ctx.timers.run(tutorialTimer.id);
          assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_ACTIVE");
          assert.strictEqual(
            dom.rescueTutorial.classList.contains("ocean-rescue-tutorial-active"),
            false
          );
          assert.strictEqual(dom.statusEl.textContent, "Rescue controls ready");
        }

        const missingRescueDom = makeBootDom();
        const missingRescueCtx = loadApp(missingRescueDom.document, {}, { skipRescue: true });
        assert.strictEqual(missingRescueCtx.Rescue, undefined);
        startLaunchToTravel(missingRescueDom, missingRescueCtx, 0);
        let frameTime = 1000;
        for (let i = 0; i < 60; i += 1) {
          const pending = missingRescueCtx.frames.pending();
          if (pending.length === 0) {
            break;
          }
          missingRescueCtx.frames.run(pending[0].id, frameTime);
          frameTime += 1000;
        }
        assert.strictEqual(missingRescueCtx.State.getSnapshot().phase, "TRAVEL");
        assert.strictEqual(missingRescueCtx.Travel.getSnapshot().active, true);

        const noOverlayDom = makeBootDom({ includeRescue: false });
        const noOverlayCtx = loadApp(noOverlayDom.document);
        startLaunchToTravel(noOverlayDom, noOverlayCtx, 0);
        frameTime = 1000;
        let crossed = false;
        for (let i = 0; i < 4000 && !crossed; i += 1) {
          const pending = noOverlayCtx.frames.pending();
          if (pending.length === 0) {
            break;
          }
          noOverlayCtx.frames.run(pending[0].id, frameTime);
          frameTime += 1000;
          if (noOverlayCtx.Travel.getSnapshot().distance >= 6000) {
            crossed = true;
          }
        }
        assert.strictEqual(crossed, true);
        assert.strictEqual(noOverlayCtx.State.getSnapshot().phase, "TRAVEL");
        assert.strictEqual(noOverlayCtx.Travel.getSnapshot().active, true);

        const noCanvasCtxDom = makeBootDom({ canvasContext: null });
        const noCanvasCtx = loadApp(noCanvasCtxDom.document);
        startLaunchToTravel(noCanvasCtxDom, noCanvasCtx, 0);
        const noCanvasResult = runToArrival(noCanvasCtx, 4000);
        assert.strictEqual(noCanvasResult.arrived, true);
        assert.strictEqual(noCanvasCtx.State.getSnapshot().phase, "RESCUE_SITE_TRANSITION");
        assert.strictEqual(noCanvasCtx.Travel.getSnapshot().active, false);

        const noTimersDom = makeBootDom();
        const noTimersCtx = loadApp(noTimersDom.document);
        startLaunchToTravel(noTimersDom, noTimersCtx, 0);
        delete noTimersCtx.sandbox.window.setTimeout;
        delete noTimersCtx.sandbox.window.clearTimeout;
        delete noTimersCtx.sandbox.window.cancelAnimationFrame;
        const noTimersResult = runToArrival(noTimersCtx, 4000);
        assert.strictEqual(noTimersResult.arrived, true);
        assert.strictEqual(noTimersCtx.State.getSnapshot().phase, "RESCUE_SITE_TRANSITION");
        assert.strictEqual(noTimersCtx.Travel.getSnapshot().active, false);
        const timersPending = noTimersCtx.timers.pending();
        assert.strictEqual(timersPending.length, 1);
        assert.strictEqual(timersPending[0].delay, 3000);
        """
    )
    _assert_node_ok(_run_node(harness))
