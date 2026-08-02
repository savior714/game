"""Behavioral tests for the Ocean Rescue crab rock interaction.

Every JavaScript assertion runs the real tracked sources (``state.js``,
``missions.js``, ``gups.js``, ``launch.js``, ``travel.js``, ``terrain.js``,
``rescue.js``, ``sea-turtle.js``, ``crab.js``, and ``app.js``) through the
installed Node runtime in a fresh VM sandbox using a minimal fake DOM, a fake
canvas 2D context, a deterministic fake timer queue, and a deterministic fake
animation-frame queue. No npm packages, no browser automation, no real-time
sleeps, and no separate JavaScript test file are used.
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
    const SEA_TURTLE_SOURCE = fs.readFileSync("domains/ocean-rescue/src/sea-turtle.js", "utf8");
    const CRAB_SOURCE = fs.readFileSync("domains/ocean-rescue/src/crab.js", "utf8");
    const APP_SOURCE = fs.readFileSync("domains/ocean-rescue/src/app.js", "utf8");

    function plain(value) {
      return JSON.parse(JSON.stringify(value));
    }

    function freshCrab() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(CRAB_SOURCE, sandbox, { filename: "crab.js" });
      return sandbox.window.OceanRescue.Crab;
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
      const ctx = { calls };
      const props = {
        fillStyle: null,
        strokeStyle: null,
        lineWidth: null,
        lineCap: null,
        font: null,
        textAlign: null,
        globalAlpha: null,
      };
      for (const name of Object.keys(props)) {
        Object.defineProperty(ctx, name, {
          get() {
            return props[name];
          },
          set(value) {
            props[name] = value;
            calls.push(["set:" + name, value]);
          },
        });
      }
      ctx.save = function () {
        calls.push(["save"]);
      };
      ctx.restore = function () {
        calls.push(["restore"]);
      };
      ctx.translate = function (...args) {
        calls.push(["translate", ...args]);
      };
      ctx.rotate = function (...args) {
        calls.push(["rotate", ...args]);
      };
      ctx.clearRect = function (...args) {
        calls.push(["clearRect", ...args]);
      };
      ctx.fillRect = function (...args) {
        calls.push(["fillRect", ...args]);
      };
      ctx.beginPath = function () {
        calls.push(["beginPath"]);
      };
      ctx.arc = function (...args) {
        calls.push(["arc", ...args]);
      };
      ctx.fill = function () {
        calls.push(["fill"]);
      };
      ctx.fillText = function (...args) {
        calls.push(["fillText", ...args]);
      };
      ctx.moveTo = function (...args) {
        calls.push(["moveTo", ...args]);
      };
      ctx.lineTo = function (...args) {
        calls.push(["lineTo", ...args]);
      };
      ctx.stroke = function () {
        calls.push(["stroke"]);
      };
      ctx.setLineDash = function (...args) {
        calls.push(["setLineDash", ...args]);
      };
      return ctx;
    }

    function makeCanvasElement(canvasContext) {
      const el = makeElement("canvas");
      el.width = 1280;
      el.height = 720;
      el.rect = { left: 0, top: 0, width: 1280, height: 720 };
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
      const includeInteraction = options.includeInteraction !== false;
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
      const rescueProgress = makeElement("p");
      const rescueAssistHand = makeElement("div");
      rescueAssistHand.hidden = true;

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
        if (includeInteraction) {
          rescueOverlay.appendChild(rescueProgress);
          rescueOverlay.appendChild(rescueAssistHand);
        }
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
        if (includeInteraction) {
          elements["ocean-rescue-rescue-progress"] = rescueProgress;
          elements["ocean-rescue-rescue-assist-hand"] = rescueAssistHand;
        }
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
        rescueProgress,
        rescueAssistHand,
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
      if (!opts.skipSeaTurtle) {
        vm.runInContext(SEA_TURTLE_SOURCE, sandbox, { filename: "sea-turtle.js" });
      }
      if (!opts.skipCrab) {
        vm.runInContext(CRAB_SOURCE, sandbox, { filename: "crab.js" });
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
        SeaTurtle: OceanRescue.SeaTurtle,
        Crab: OceanRescue.Crab,
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

    function timerWithDelay(ctx, delay) {
      const matches = ctx.timers.pending().filter((t) => t.delay === delay);
      assert.strictEqual(matches.length, 1, "expected one pending timer at " + delay);
      return matches[0];
    }

    function dispatch(element, type, event) {
      const list = element.listeners[type] || [];
      for (const fn of list.slice()) {
        fn(event);
      }
    }

    function pointerEvent(pointerId, x, y) {
      return {
        pointerId,
        clientX: x,
        clientY: y,
        isPrimary: true,
        button: 0,
        preventDefault() {},
        stopPropagation() {},
      };
    }

    function fillTextLabels(canvas) {
      return (canvas._context.calls || [])
        .filter((call) => call[0] === "fillText")
        .map((call) => call[1]);
    }

    function callArgs(canvas, name) {
      return (canvas._context.calls || [])
        .filter((call) => call[0] === name)
        .map((call) => call.slice(1));
    }

    function runToRescueActive(ctx) {
      const result = runToArrival(ctx, 4000);
      assert.strictEqual(result.arrived, true);
      assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SITE_TRANSITION");
      const transitionTimer = lastPendingTimer(ctx);
      assert.strictEqual(transitionTimer.delay, 1500);
      ctx.timers.run(transitionTimer.id);
      assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_TUTORIAL");
      const tutorialTimer = lastPendingTimer(ctx);
      assert.strictEqual(tutorialTimer.delay, 3000);
      ctx.timers.run(tutorialTimer.id);
      assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_ACTIVE");
    }

    function completeRockByHoldDrag(dom, ctx, pointerId, start, target) {
      dispatch(dom.canvas, "pointerdown", pointerEvent(pointerId, start.x, start.y));
      const hold = timerWithDelay(ctx, 400);
      ctx.timers.run(hold.id);
      dispatch(dom.canvas, "pointermove", pointerEvent(pointerId, target.x, target.y));
      dispatch(dom.canvas, "pointerup", pointerEvent(pointerId, target.x, target.y));
    }

    function runSuccessFeedback(ctx) {
      const timer = timerWithDelay(ctx, 400);
      ctx.timers.run(timer.id);
    }

    function runFailureFeedback(ctx) {
      const timer = timerWithDelay(ctx, 300);
      ctx.timers.run(timer.id);
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


def test_crab_catalog_constants_and_public_contract() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Crab = freshCrab();

        assert.strictEqual(Crab.MissionId, "crab");
        assert.strictEqual(Object.isFrozen(Crab), true);

        assert.deepStrictEqual(plain(Crab.Constants), {
          holdDurationMs: 400,
          tapMovementThreshold: 10,
          baseHitRadius: 60,
          assistedHitRadius: 82,
          assistedZoneMargin: 48,
          successFeedbackMs: 400,
          failureFeedbackMs: 300
        });
        assert.strictEqual(Object.isFrozen(Crab.Constants), true);

        assert.deepStrictEqual(plain(Crab.Rocks), [
          { id: "rock-1", order: 1, radius: 46, start: { x: 870, y: 420 }, placed: { x: 240, y: 300 } },
          { id: "rock-2", order: 2, radius: 52, start: { x: 1030, y: 500 }, placed: { x: 390, y: 330 } },
          { id: "rock-3", order: 3, radius: 58, start: { x: 900, y: 560 }, placed: { x: 330, y: 215 } }
        ]);
        assert.strictEqual(Object.isFrozen(Crab.Rocks), true);
        assert.strictEqual(Object.isFrozen(Crab.Rocks[0]), true);
        assert.strictEqual(Object.isFrozen(Crab.Rocks[0].start), true);
        assert.strictEqual(Object.isFrozen(Crab.Rocks[0].placed), true);
        assert.strictEqual(Object.isFrozen(Crab.Rocks[2].start), true);

        assert.deepStrictEqual(plain(Crab.DropZone), { x: 310, y: 290, width: 300, height: 320 });
        assert.strictEqual(Object.isFrozen(Crab.DropZone), true);

        assert.deepStrictEqual(plain(Crab.Layout), {
          logicalWidth: 1280,
          logicalHeight: 720,
          crabCenter: { x: 900, y: 500 },
          crabFootprint: { width: 200, height: 180 },
          grabberBase: { x: 520, y: 520 },
          dropZone: { x: 310, y: 290, width: 300, height: 320 },
          rocks: [
            { id: "rock-1", order: 1, radius: 46, start: { x: 870, y: 420 }, placed: { x: 240, y: 300 } },
            { id: "rock-2", order: 2, radius: 52, start: { x: 1030, y: 500 }, placed: { x: 390, y: 330 } },
            { id: "rock-3", order: 3, radius: 58, start: { x: 900, y: 560 }, placed: { x: 330, y: 215 } }
          ]
        });
        assert.strictEqual(Object.isFrozen(Crab.Layout), true);
        assert.strictEqual(Object.isFrozen(Crab.Layout.crabCenter), true);
        assert.strictEqual(Object.isFrozen(Crab.Layout.grabberBase), true);
        assert.strictEqual(Crab.Layout.dropZone, Crab.DropZone);
        assert.strictEqual(Crab.Layout.rocks, Crab.Rocks);

        assert.deepStrictEqual(plain(Crab.Dialogues), [
          "Great lift! Two rocks left, and the crab can see us.",
          "One more rock! The crab is getting up.",
          "All clear! The crab is free!"
        ]);
        assert.strictEqual(Object.isFrozen(Crab.Dialogues), true);

        assert.deepStrictEqual(
          Object.keys(Crab).sort(),
          [
            "Constants",
            "Dialogues",
            "DropZone",
            "Layout",
            "MissionId",
            "Rocks",
            "finishFeedback",
            "finishHold",
            "getSnapshot",
            "pauseCancel",
            "pointerCancel",
            "pointerDown",
            "pointerMove",
            "pointerUp",
            "start",
            "stop"
          ].sort()
        );
        const hidden = [
          "reset",
          "setActiveRock",
          "completeRock",
          "failRock",
          "setHelpLevel",
          "setPointer",
          "forceSuccess",
          "skip",
          "transition",
          "subscribe",
          "dispatch",
          "serialize",
          "hydrate",
          "save",
          "load",
          "history"
        ];
        for (const name of hidden) {
          assert.strictEqual(Crab[name], undefined, "exposed " + name);
        }

        Crab.extra = 1;
        Crab.Constants.extra = 1;
        Crab.Rocks[0].start.extra = 1;
        Crab.DropZone.extra = 1;
        assert.strictEqual(Crab.extra, undefined);
        assert.strictEqual(Crab.Constants.extra, undefined);
        assert.strictEqual(Crab.Rocks[0].start.extra, undefined);
        assert.strictEqual(Crab.DropZone.extra, undefined);

        const before = Crab.getSnapshot();
        assert.deepStrictEqual(plain(before), {
          active: false,
          activeRockId: null,
          completedRockIds: [],
          failureCount: 0,
          helpLevel: 0,
          tapRockArmed: false,
          pointerActive: false,
          holding: false,
          grabbed: false,
          currentRockCenter: null,
          inputLocked: true,
          feedback: null,
          complete: false
        });

        assert.strictEqual(Crab.start(), true);
        const after = Crab.getSnapshot();
        assert.deepStrictEqual(plain(after), {
          active: true,
          activeRockId: "rock-1",
          completedRockIds: [],
          failureCount: 0,
          helpLevel: 0,
          tapRockArmed: false,
          pointerActive: false,
          holding: false,
          grabbed: false,
          currentRockCenter: { x: 870, y: 420 },
          inputLocked: false,
          feedback: null,
          complete: false
        });

        assert.strictEqual(Crab.stop(), true);
        assert.strictEqual(Crab.stop(), false);
        assert.deepStrictEqual(plain(Crab.getSnapshot()), {
          active: false,
          activeRockId: null,
          completedRockIds: [],
          failureCount: 0,
          helpLevel: 0,
          tapRockArmed: false,
          pointerActive: false,
          holding: false,
          grabbed: false,
          currentRockCenter: null,
          inputLocked: true,
          feedback: null,
          complete: false
        });
        """
    )
    _assert_node_ok(_run_node(harness))


def test_four_hundred_ms_hold_and_direct_follow_drag() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Crab = freshCrab();
        Crab.start();
        let snap = Crab.getSnapshot();
        assert.strictEqual(snap.activeRockId, "rock-1");
        assert.strictEqual(snap.inputLocked, false);
        assert.deepStrictEqual(plain(snap.completedRockIds), []);
        assert.deepStrictEqual(plain(snap.currentRockCenter), { x: 870, y: 420 });

        assert.strictEqual(Crab.pointerDown(1, 900, 440), true);
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.holding, true);
        assert.strictEqual(snap.grabbed, false);
        assert.strictEqual(snap.pointerActive, true);

        assert.strictEqual(Crab.pointerMove(1, 900, 440), true);
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.holding, true);
        assert.strictEqual(snap.grabbed, false);
        assert.deepStrictEqual(plain(snap.currentRockCenter), { x: 870, y: 420 });

        const hold = Crab.finishHold();
        assert.deepStrictEqual(plain(hold), {
          accepted: true,
          outcome: "grabbed",
          rockId: "rock-1"
        });
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.grabbed, true);
        assert.strictEqual(snap.holding, false);
        assert.deepStrictEqual(plain(snap.currentRockCenter), { x: 900, y: 440 });

        Crab.pointerMove(1, 310, 290);
        Crab.pointerMove(1, 240, 300);
        snap = Crab.getSnapshot();
        assert.deepStrictEqual(plain(snap.currentRockCenter), { x: 240, y: 300 });

        const result = Crab.pointerUp(1, 240, 300);
        assert.deepStrictEqual(plain(result), {
          accepted: true,
          outcome: "success",
          rockId: "rock-1"
        });
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(snap.inputLocked, true);
        assert.deepStrictEqual(plain(snap.completedRockIds), ["rock-1"]);

        Crab.finishFeedback();
        assert.strictEqual(Crab.getSnapshot().activeRockId, "rock-2");

        assert.strictEqual(Crab.pointerDown(2, 1060, 510), true);
        assert.strictEqual(Crab.pointerMove(2, 1080, 510), true);
        const failedHold = Crab.finishHold();
        assert.deepStrictEqual(plain(failedHold), {
          accepted: false,
          outcome: "none",
          rockId: null
        });
        const failedUp = Crab.pointerUp(2, 1080, 510);
        assert.deepStrictEqual(plain(failedUp), {
          accepted: true,
          outcome: "failure",
          rockId: "rock-2"
        });
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.feedback, "failure");
        assert.strictEqual(snap.activeRockId, "rock-2");
        assert.deepStrictEqual(plain(snap.completedRockIds), ["rock-1"]);
        assert.deepStrictEqual(plain(snap.currentRockCenter), { x: 1030, y: 500 });

        Crab.finishFeedback();
        const idleHold = Crab.finishHold();
        assert.deepStrictEqual(plain(idleHold), {
          accepted: false,
          outcome: "none",
          rockId: null
        });
        """
    )
    _assert_node_ok(_run_node(harness))


def test_center_in_zone_success_and_outside_zone_reset() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Crab = freshCrab();
        Crab.start();

        Crab.pointerDown(1, 900, 440);
        Crab.finishHold();
        Crab.pointerMove(1, 310, 290);
        Crab.pointerMove(1, 240, 300);
        const success = Crab.pointerUp(1, 240, 300);
        assert.strictEqual(success.outcome, "success");
        assert.strictEqual(success.rockId, "rock-1");
        Crab.finishFeedback();
        assert.strictEqual(Crab.getSnapshot().activeRockId, "rock-2");

        Crab.pointerDown(2, 1060, 510);
        Crab.finishHold();
        Crab.pointerMove(2, 700, 500);
        const fail = Crab.pointerUp(2, 700, 500);
        assert.strictEqual(fail.outcome, "failure");
        assert.strictEqual(fail.rockId, "rock-2");
        let snap = Crab.getSnapshot();
        assert.strictEqual(snap.feedback, "failure");
        assert.strictEqual(snap.activeRockId, "rock-2");
        assert.deepStrictEqual(plain(snap.completedRockIds), ["rock-1"]);
        assert.deepStrictEqual(plain(snap.currentRockCenter), { x: 1030, y: 500 });

        Crab.finishFeedback();
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.activeRockId, "rock-2");
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(snap.feedback, null);
        assert.deepStrictEqual(plain(snap.completedRockIds), ["rock-1"]);
        assert.deepStrictEqual(plain(Crab.Rocks[0].placed), { x: 240, y: 300 });
        assert.deepStrictEqual(plain(snap.currentRockCenter), { x: 1030, y: 500 });
        """
    )
    _assert_node_ok(_run_node(harness))


def test_two_tap_alternative_and_wrong_order_failure() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Crab = freshCrab();
        Crab.start();

        const firstTap = Crab.pointerDown(1, 900, 440);
        assert.strictEqual(firstTap, true);
        const armed = Crab.pointerUp(1, 900, 440);
        assert.deepStrictEqual(plain(armed), {
          accepted: true,
          outcome: "none",
          rockId: "rock-1"
        });
        let snap = Crab.getSnapshot();
        assert.strictEqual(snap.tapRockArmed, true);
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(snap.feedback, null);
        assert.strictEqual(snap.failureCount, 0);

        const secondTap = Crab.pointerDown(2, 310, 290);
        assert.strictEqual(secondTap, true);
        const done = Crab.pointerUp(2, 310, 290);
        assert.deepStrictEqual(plain(done), {
          accepted: true,
          outcome: "success",
          rockId: "rock-1"
        });
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.tapRockArmed, false);
        assert.strictEqual(snap.feedback, "success");
        assert.deepStrictEqual(plain(snap.completedRockIds), ["rock-1"]);
        Crab.finishFeedback();
        assert.strictEqual(Crab.getSnapshot().activeRockId, "rock-2");

        const zoneFirst = Crab.pointerDown(3, 310, 290);
        assert.strictEqual(zoneFirst, true);
        const zoneFirstUp = Crab.pointerUp(3, 310, 290);
        assert.deepStrictEqual(plain(zoneFirstUp), {
          accepted: true,
          outcome: "failure",
          rockId: "rock-2"
        });
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.feedback, "failure");
        assert.strictEqual(snap.tapRockArmed, false);
        assert.strictEqual(snap.activeRockId, "rock-2");
        assert.strictEqual(snap.failureCount, 1);
        Crab.finishFeedback();

        assert.strictEqual(Crab.pointerDown(4, 1060, 510), true);
        assert.deepStrictEqual(plain(Crab.pointerUp(4, 1060, 510)), {
          accepted: true,
          outcome: "none",
          rockId: "rock-2"
        });
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.tapRockArmed, true);

        const wrongSecond = Crab.pointerDown(5, 700, 500);
        assert.strictEqual(wrongSecond, true);
        const wrongSecondUp = Crab.pointerUp(5, 700, 500);
        assert.deepStrictEqual(plain(wrongSecondUp), {
          accepted: true,
          outcome: "failure",
          rockId: "rock-2"
        });
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.feedback, "failure");
        assert.strictEqual(snap.tapRockArmed, false);
        assert.strictEqual(snap.activeRockId, "rock-2");
        Crab.finishFeedback();

        assert.strictEqual(Crab.pointerDown(6, 1060, 510), true);
        assert.strictEqual(Crab.pointerUp(6, 1060, 510).outcome, "none");
        assert.strictEqual(Crab.getSnapshot().tapRockArmed, true);
        const tapRockAgain = Crab.pointerDown(7, 1060, 510);
        assert.strictEqual(tapRockAgain, true);
        const tapRockAgainUp = Crab.pointerUp(7, 1060, 510);
        assert.strictEqual(tapRockAgainUp.outcome, "failure");
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.feedback, "failure");
        assert.strictEqual(snap.tapRockArmed, false);
        assert.strictEqual(snap.activeRockId, "rock-2");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_fixed_order_completed_rock_preservation_and_immutable_snapshot() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Crab = freshCrab();
        Crab.start();

        Crab.pointerDown(1, 1060, 510);
        Crab.pointerUp(1, 1060, 510);
        let snap = Crab.getSnapshot();
        assert.strictEqual(snap.activeRockId, "rock-1");
        assert.strictEqual(snap.feedback, null);
        assert.strictEqual(snap.tapRockArmed, false);
        assert.deepStrictEqual(plain(snap.completedRockIds), []);

        Crab.pointerDown(2, 900, 440);
        Crab.pointerUp(2, 900, 440);
        Crab.pointerDown(3, 310, 290);
        Crab.pointerUp(3, 310, 290);
        assert.strictEqual(Crab.getSnapshot().feedback, "success");
        Crab.finishFeedback();
        assert.strictEqual(Crab.getSnapshot().activeRockId, "rock-2");

        Crab.pointerDown(4, 1060, 510);
        Crab.pointerMove(4, 700, 500);
        Crab.pointerUp(4, 700, 500);
        assert.strictEqual(Crab.getSnapshot().feedback, "failure");
        Crab.finishFeedback();
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.activeRockId, "rock-2");
        assert.deepStrictEqual(plain(snap.completedRockIds), ["rock-1"]);

        const first = Crab.getSnapshot();
        const second = Crab.getSnapshot();
        assert.notStrictEqual(first, second);
        assert.strictEqual(Object.isFrozen(first), true);
        assert.strictEqual(Object.isFrozen(first.completedRockIds), true);
        assert.strictEqual(Object.isFrozen(first.currentRockCenter), true);
        const countBefore = first.completedRockIds.length;
        try {
          first.completedRockIds.push("rock-9");
        } catch (err) {
          // strict-mode hosts throw for frozen mutation
        }
        assert.strictEqual(first.completedRockIds.length, countBefore);
        try {
          first.activeRockId = "rock-9";
        } catch (err) {
          // strict-mode hosts throw for frozen mutation
        }
        assert.strictEqual(JSON.stringify(Crab.getSnapshot()), JSON.stringify(second));
        """
    )
    _assert_node_ok(_run_node(harness))


def test_progressive_assistance_and_exact_feedback_duration() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Crab = freshCrab();
        Crab.start();

        function failRock1(pointerId) {
          Crab.pointerDown(pointerId, 900, 440);
          Crab.pointerMove(pointerId, 900, 100);
          const r = Crab.pointerUp(pointerId, 900, 100);
          assert.strictEqual(r.outcome, "failure");
          assert.strictEqual(Crab.getSnapshot().feedback, "failure");
          Crab.finishFeedback();
        }

        failRock1(1);
        let snap = Crab.getSnapshot();
        assert.strictEqual(snap.failureCount, 1);
        assert.strictEqual(snap.helpLevel, 1);
        assert.strictEqual(snap.inputLocked, false);

        failRock1(2);
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.failureCount, 2);
        assert.strictEqual(snap.helpLevel, 2);

        failRock1(3);
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.failureCount, 3);
        assert.strictEqual(snap.helpLevel, 3);

        failRock1(4);
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.failureCount, 4);
        assert.strictEqual(snap.helpLevel, 3);

        assert.strictEqual(Crab.Constants.successFeedbackMs, 400);
        assert.strictEqual(Crab.Constants.failureFeedbackMs, 300);

        Crab.pointerDown(5, 900, 440);
        Crab.finishHold();
        Crab.pointerMove(5, 310, 290);
        const done = Crab.pointerUp(5, 310, 290);
        assert.strictEqual(done.outcome, "success");
        Crab.finishFeedback();
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.activeRockId, "rock-2");
        assert.strictEqual(snap.failureCount, 0);
        assert.strictEqual(snap.helpLevel, 0);

        function failRock2(pointerId) {
          Crab.pointerDown(pointerId, 1060, 510);
          Crab.pointerMove(pointerId, 700, 500);
          const r = Crab.pointerUp(pointerId, 700, 500);
          assert.strictEqual(r.outcome, "failure");
          Crab.finishFeedback();
        }

        failRock2(6);
        failRock2(7);
        failRock2(8);
        snap = Crab.getSnapshot();
        assert.strictEqual(snap.helpLevel, 3);

        Crab.pointerDown(9, 1060, 510);
        Crab.finishHold();
        Crab.pointerMove(9, 600, 300);
        const outsideExpanded = Crab.pointerUp(9, 600, 300);
        assert.strictEqual(outsideExpanded.outcome, "failure");
        Crab.finishFeedback();
        assert.strictEqual(Crab.getSnapshot().helpLevel, 3);

        Crab.pointerDown(10, 1060, 510);
        Crab.finishHold();
        Crab.pointerMove(10, 120, 100);
        const expanded = Crab.pointerUp(10, 120, 100);
        assert.strictEqual(expanded.outcome, "success");
        snap = Crab.getSnapshot();
        assert.deepStrictEqual(plain(snap.completedRockIds), ["rock-1", "rock-2"]);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_real_pointer_flow_completes_three_rocks_and_enters_success() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        ctx.Missions.completeMission("sea-turtle");
        startLaunchToTravel(dom, ctx, 0, 1);
        runToRescueActive(ctx);

        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        let snap = ctx.Crab.getSnapshot();
        assert.strictEqual(snap.active, true);
        assert.strictEqual(snap.activeRockId, "rock-1");
        assert.deepStrictEqual(plain(snap.completedRockIds), []);
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(snap.feedback, null);
        assert.strictEqual(snap.complete, false);
        assert.strictEqual(ctx.SeaTurtle.getSnapshot().active, false);
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-active"), null);

        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "active");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "enabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-active"), "true");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-rock-id"), "rock-1");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-completed-count"), "0");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-help-level"), "0");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-feedback"), "none");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-grabbed"), "false");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-complete"), "false");
        assert.strictEqual(dom.rescueProgress.textContent, "Rock 1 of 3");
        assert.strictEqual(dom.statusEl.textContent, "Rescue controls ready");
        assert.strictEqual(dom.rescueAssistHand.hidden, true);

        const labels = fillTextLabels(dom.canvas);
        assert.strictEqual(labels.includes("Grabber arm"), true);
        assert.strictEqual(labels.includes("Drop zone"), true);
        const arcs = callArgs(dom.canvas, "arc");
        assert.strictEqual(
          arcs.some((a) => a[0] === 900 && a[1] === 500 && a[2] === 42),
          true
        );
        assert.strictEqual(
          arcs.some((a) => a[0] === 870 && a[1] === 420 && a[2] === 46),
          true
        );
        assert.strictEqual(
          arcs.some((a) => a[0] === 1030 && a[1] === 500 && a[2] === 52),
          true
        );
        assert.strictEqual(
          arcs.some((a) => a[0] === 900 && a[1] === 560 && a[2] === 58),
          true
        );
        assert.strictEqual(ctx.frames.pending().length, 0);
        assert.deepStrictEqual(
          Object.keys(dom.canvas.listeners).sort(),
          ["pointercancel", "pointerdown", "pointermove", "pointerup"]
        );

        completeRockByHoldDrag(dom, ctx, 1, { x: 900, y: 440 }, { x: 310, y: 290 });
        snap = ctx.Crab.getSnapshot();
        assert.deepStrictEqual(plain(snap.completedRockIds), ["rock-1"]);
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(snap.inputLocked, true);
        assert.strictEqual(
          dom.rescueProgress.textContent,
          "Great lift! Two rocks left, and the crab can see us."
        );
        assert.strictEqual(
          dom.statusEl.textContent,
          "Great lift! Two rocks left, and the crab can see us."
        );
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-feedback"), "success");
        assert.strictEqual(
          dom.rescueOverlay.classList.contains("ocean-rescue-crab-success"),
          true
        );
        runSuccessFeedback(ctx);
        snap = ctx.Crab.getSnapshot();
        assert.strictEqual(snap.activeRockId, "rock-2");
        assert.strictEqual(snap.feedback, null);
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(snap.helpLevel, 0);
        assert.strictEqual(dom.rescueProgress.textContent, "Rock 2 of 3");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-rock-id"), "rock-2");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-completed-count"), "1");
        assert.strictEqual(
          dom.rescueOverlay.classList.contains("ocean-rescue-crab-success"),
          false
        );

        dispatch(dom.canvas, "pointerdown", pointerEvent(11, 1060, 510));
        dispatch(dom.canvas, "pointerup", pointerEvent(11, 1060, 510));
        snap = ctx.Crab.getSnapshot();
        assert.strictEqual(snap.tapRockArmed, true);
        assert.strictEqual(snap.feedback, null);
        dispatch(dom.canvas, "pointerdown", pointerEvent(12, 310, 290));
        dispatch(dom.canvas, "pointerup", pointerEvent(12, 310, 290));
        snap = ctx.Crab.getSnapshot();
        assert.deepStrictEqual(plain(snap.completedRockIds), ["rock-1", "rock-2"]);
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(
          dom.rescueProgress.textContent,
          "One more rock! The crab is getting up."
        );
        assert.strictEqual(
          dom.statusEl.textContent,
          "One more rock! The crab is getting up."
        );
        runSuccessFeedback(ctx);
        snap = ctx.Crab.getSnapshot();
        assert.strictEqual(snap.activeRockId, "rock-3");
        assert.strictEqual(dom.rescueProgress.textContent, "Rock 3 of 3");

        dispatch(dom.canvas, "pointerdown", pointerEvent(21, 930, 575));
        const hold3 = timerWithDelay(ctx, 400);
        ctx.timers.run(hold3.id);
        dispatch(dom.canvas, "pointermove", pointerEvent(21, 880, 560));
        dispatch(dom.canvas, "pointerup", pointerEvent(21, 880, 560));
        snap = ctx.Crab.getSnapshot();
        assert.strictEqual(snap.feedback, "failure");
        assert.strictEqual(snap.failureCount, 1);
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-feedback"), "failure");
        assert.strictEqual(dom.rescueProgress.textContent, "Try rock 3 again");
        assert.strictEqual(
          dom.rescueOverlay.classList.contains("ocean-rescue-crab-failure"),
          true
        );
        runFailureFeedback(ctx);
        snap = ctx.Crab.getSnapshot();
        assert.strictEqual(snap.activeRockId, "rock-3");
        assert.strictEqual(snap.feedback, null);
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(snap.helpLevel, 1);
        assert.strictEqual(dom.rescueAssistHand.hidden, false);
        assert.strictEqual(
          dom.rescueAssistHand.classList.contains("ocean-rescue-assist-hand-visible"),
          true
        );
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-help-level"), "1");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-feedback"), "none");
        assert.strictEqual(dom.rescueProgress.textContent, "Rock 3 of 3");

        completeRockByHoldDrag(dom, ctx, 22, { x: 930, y: 575 }, { x: 330, y: 215 });
        snap = ctx.Crab.getSnapshot();
        assert.deepStrictEqual(
          plain(snap.completedRockIds),
          ["rock-1", "rock-2", "rock-3"]
        );
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(snap.activeRockId, "rock-3");
        assert.strictEqual(
          dom.rescueProgress.textContent,
          "All clear! The crab is free!"
        );
        assert.strictEqual(
          dom.statusEl.textContent,
          "All clear! The crab is free!"
        );

        const finalTimer = timerWithDelay(ctx, 400);
        ctx.timers.run(finalTimer.id);
        snap = ctx.Crab.getSnapshot();
        assert.strictEqual(snap.complete, true);
        assert.strictEqual(snap.active, false);
        assert.strictEqual(snap.activeRockId, null);
        assert.strictEqual(snap.inputLocked, true);
        assert.deepStrictEqual(
          plain(snap.completedRockIds),
          ["rock-1", "rock-2", "rock-3"]
        );
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");

        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "success");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "disabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-active"), "false");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-rock-id"), "");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-completed-count"), "3");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-feedback"), "none");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-grabbed"), "false");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-complete"), "true");
        assert.strictEqual(
          dom.rescueProgress.textContent,
          "All clear! The crab is free!"
        );

        const afterArcs = callArgs(dom.canvas, "arc");
        assert.strictEqual(
          afterArcs.some((a) => a[0] === 240 && a[1] === 300 && a[2] === 46),
          true
        );
        assert.strictEqual(
          afterArcs.some((a) => a[0] === 390 && a[1] === 330 && a[2] === 52),
          true
        );
        assert.strictEqual(
          afterArcs.some((a) => a[0] === 330 && a[1] === 215 && a[2] === 58),
          true
        );
        const afterLabels = fillTextLabels(dom.canvas);
        assert.strictEqual(afterLabels.includes("Free!"), true);

        const missionSnap = ctx.Missions.getSnapshot();
        assert.deepStrictEqual(plain(missionSnap.completedMissionIds), ["sea-turtle"]);
        assert.deepStrictEqual(plain(missionSnap.unlockedMissionIds), ["sea-turtle", "crab"]);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");

        finalTimer.fn();
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-completed-count"), "3");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_mission_gating_stale_timers_and_missing_runtime_safety() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToTravel(dom, ctx, 0);
        runToRescueActive(ctx);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        assert.strictEqual(ctx.SeaTurtle.getSnapshot().active, true);
        assert.strictEqual(ctx.Crab.getSnapshot().active, false);
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-active"), null);

        dispatch(dom.canvas, "pointerdown", pointerEvent(99, 800, 545));
        assert.strictEqual(ctx.Crab.getSnapshot().active, false);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_ACTIVE");

        const crabDom = makeBootDom();
        const crabCtx = loadApp(crabDom.document);
        crabCtx.Missions.completeMission("sea-turtle");
        startLaunchToTravel(crabDom, crabCtx, 0, 1);
        runToRescueActive(crabCtx);
        assert.strictEqual(crabCtx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        assert.strictEqual(crabCtx.Crab.getSnapshot().active, true);
        assert.strictEqual(crabCtx.SeaTurtle.getSnapshot().active, false);
        assert.strictEqual(crabDom.rootEl.getAttribute("data-sea-turtle-active"), null);
        assert.strictEqual(crabDom.rootEl.getAttribute("data-crab-active"), "true");

        const whaleDom = makeBootDom();
        const whaleCtx = loadApp(whaleDom.document);
        whaleCtx.Missions.completeMission("sea-turtle");
        whaleCtx.Missions.completeMission("crab");
        startLaunchToTravel(whaleDom, whaleCtx, 0, 2);
        runToRescueActive(whaleCtx);
        assert.strictEqual(whaleCtx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        assert.strictEqual(whaleCtx.Crab.getSnapshot().active, false);
        assert.strictEqual(whaleCtx.SeaTurtle.getSnapshot().active, false);
        assert.strictEqual(whaleDom.rootEl.getAttribute("data-crab-active"), null);
        assert.strictEqual(whaleDom.rootEl.getAttribute("data-sea-turtle-active"), null);

        const missingCrabDom = makeBootDom();
        const missingCrabCtx = loadApp(
          missingCrabDom.document,
          {},
          { skipCrab: true }
        );
        assert.strictEqual(missingCrabCtx.Crab, undefined);
        missingCrabCtx.Missions.completeMission("sea-turtle");
        startLaunchToTravel(missingCrabDom, missingCrabCtx, 0, 1);
        runToRescueActive(missingCrabCtx);
        assert.strictEqual(
          missingCrabCtx.State.getSnapshot().phase,
          "RESCUE_ACTIVE"
        );
        assert.strictEqual(
          missingCrabDom.rootEl.getAttribute("data-rescue-phase"),
          "active"
        );
        assert.strictEqual(
          missingCrabDom.rootEl.getAttribute("data-crab-active"),
          null
        );
        """
    )
    _assert_node_ok(_run_node(harness))


def test_crab_interaction_geometry_contract() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const Crab = freshCrab();

        const Layout = Crab.Layout || null;
        const logicalWidth = Layout ? Layout.logicalWidth : 1280;
        const logicalHeight = Layout ? Layout.logicalHeight : 720;

        const dz = Crab.DropZone;
        const dzRect = {
          x1: dz.x - dz.width / 2,
          x2: dz.x + dz.width / 2,
          y1: dz.y - dz.height / 2,
          y2: dz.y + dz.height / 2
        };
        assert.strictEqual(
          Object.prototype.hasOwnProperty.call(dz, "x") &&
            Object.prototype.hasOwnProperty.call(dz, "y") &&
            Object.prototype.hasOwnProperty.call(dz, "width") &&
            Object.prototype.hasOwnProperty.call(dz, "height"),
          true
        );
        assert.strictEqual(dz.width > 0 && dz.height > 0, true);

        const crabFootprint = Layout
          ? {
              x1: Layout.crabCenter.x - Layout.crabFootprint.width / 2,
              x2: Layout.crabCenter.x + Layout.crabFootprint.width / 2,
              y1: Layout.crabCenter.y - Layout.crabFootprint.height / 2,
              y2: Layout.crabCenter.y + Layout.crabFootprint.height / 2
            }
          : { x1: 800, x2: 1000, y1: 410, y2: 590 };

        function circleIntersectsRect(cx, cy, r, rect) {
          const nx = Math.max(rect.x1, Math.min(cx, rect.x2));
          const ny = Math.max(rect.y1, Math.min(cy, rect.y2));
          return Math.hypot(cx - nx, cy - ny) <= r;
        }

        function circleInsideRect(cx, cy, r, rect) {
          return (
            cx - r >= rect.x1 &&
            cx + r <= rect.x2 &&
            cy - r >= rect.y1 &&
            cy + r <= rect.y2
          );
        }

        assert.strictEqual(Crab.Rocks.length, 3);
        const ids = Crab.Rocks.map((rock) => rock.id);
        assert.strictEqual(new Set(ids).size, 3);
        const orders = Crab.Rocks.map((rock) => rock.order);
        assert.deepStrictEqual(plain(orders), [1, 2, 3]);

        for (const rock of Crab.Rocks) {
          assert.strictEqual(
            Number.isFinite(rock.radius) && rock.radius > 0,
            true,
            rock.id + " radius"
          );
          assert.strictEqual(
            Number.isFinite(rock.start.x) && Number.isFinite(rock.start.y),
            true,
            rock.id + " start finite"
          );
          assert.strictEqual(
            Number.isFinite(rock.placed.x) && Number.isFinite(rock.placed.y),
            true,
            rock.id + " placed finite"
          );
          assert.strictEqual(
            rock.start.x >= 0 && rock.start.x <= logicalWidth &&
              rock.start.y >= 0 && rock.start.y <= logicalHeight,
            true,
            rock.id + " start in viewport"
          );
          assert.strictEqual(
            rock.placed.x >= 0 && rock.placed.x <= logicalWidth &&
              rock.placed.y >= 0 && rock.placed.y <= logicalHeight,
            true,
            rock.id + " placed in viewport"
          );
          assert.strictEqual(
            circleIntersectsRect(rock.start.x, rock.start.y, rock.radius, dzRect),
            false,
            rock.id + " start rock must not intersect the drop zone"
          );
          assert.strictEqual(
            circleInsideRect(rock.placed.x, rock.placed.y, rock.radius, dzRect),
            true,
            rock.id + " placed rock must sit fully inside the drop zone"
          );
          assert.strictEqual(
            circleIntersectsRect(rock.start.x, rock.start.y, rock.radius, crabFootprint),
            true,
            rock.id + " start rock must press on the crab footprint"
          );
          assert.strictEqual(
            circleIntersectsRect(rock.placed.x, rock.placed.y, rock.radius, crabFootprint),
            false,
            rock.id + " placed rock must be clear of the crab footprint"
          );
        }

        assert.strictEqual(
          dz.x - dz.width / 2 >= 0 &&
            dz.x + dz.width / 2 <= logicalWidth &&
            dz.y - dz.height / 2 >= 0 &&
            dz.y + dz.height / 2 <= logicalHeight,
          true,
          "drop zone must be fully inside the logical viewport"
        );
        assert.strictEqual(
          circleIntersectsRect(
            crabFootprint.x1 + (crabFootprint.x2 - crabFootprint.x1) / 2,
            crabFootprint.y1 + (crabFootprint.y2 - crabFootprint.y1) / 2,
            0,
            dzRect
          ) === false ||
            dz.x + dz.width / 2 < crabFootprint.x1 ||
            dz.x - dz.width / 2 > crabFootprint.x2 ||
            dz.y + dz.height / 2 < crabFootprint.y1 ||
            dz.y - dz.height / 2 > crabFootprint.y2,
          true,
          "drop zone must be visually separate from the crab footprint"
        );
        """
    )
    _assert_node_ok(_run_node(harness))
