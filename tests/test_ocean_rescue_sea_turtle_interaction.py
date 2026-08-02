"""Behavioral tests for the Ocean Rescue sea-turtle rope interaction.

Every JavaScript assertion runs the real tracked sources (``state.js``,
``missions.js``, ``gups.js``, ``launch.js``, ``travel.js``, ``terrain.js``,
``rescue.js``, ``sea-turtle.js``, and ``app.js``) through the installed Node
runtime in a fresh VM sandbox using a minimal fake DOM, a fake canvas 2D
context, a deterministic fake timer queue, and a deterministic fake
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
    const APP_SOURCE = fs.readFileSync("domains/ocean-rescue/src/app.js", "utf8");

    function plain(value) {
      return JSON.parse(JSON.stringify(value));
    }

    function freshSeaTurtle() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(SEA_TURTLE_SOURCE, sandbox, { filename: "sea-turtle.js" });
      return sandbox.window.OceanRescue.SeaTurtle;
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

    function completeRopeByTrace(dom, ctx, pointerId, start, moves, end) {
      dispatch(dom.canvas, "pointerdown", pointerEvent(pointerId, start.x, start.y));
      for (const point of moves) {
        dispatch(dom.canvas, "pointermove", pointerEvent(pointerId, point.x, point.y));
      }
      dispatch(dom.canvas, "pointerup", pointerEvent(pointerId, end.x, end.y));
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


def test_sea_turtle_catalog_constants_and_public_contract() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const SeaTurtle = freshSeaTurtle();

        assert.strictEqual(SeaTurtle.MissionId, "sea-turtle");
        assert.strictEqual(Object.isFrozen(SeaTurtle), true);

        assert.deepStrictEqual(plain(SeaTurtle.Constants), {
          baseEndpointRadius: 54,
          assistedEndpointRadius: 74,
          basePathTolerance: 70,
          assistedPathTolerance: 100,
          tapMovementThreshold: 10,
          minimumTraceProgress: 0.85,
          maxBackwardProgress: 0.12,
          successFeedbackMs: 400,
          failureFeedbackMs: 300
        });
        assert.strictEqual(Object.isFrozen(SeaTurtle.Constants), true);

        assert.deepStrictEqual(plain(SeaTurtle.Ropes), [
          { id: "rope-1", order: 1, start: { x: 760, y: 300 }, end: { x: 1040, y: 330 } },
          { id: "rope-2", order: 2, start: { x: 750, y: 420 }, end: { x: 1050, y: 440 } },
          { id: "rope-3", order: 3, start: { x: 770, y: 540 }, end: { x: 1030, y: 570 } }
        ]);
        assert.strictEqual(Object.isFrozen(SeaTurtle.Ropes), true);
        assert.strictEqual(Object.isFrozen(SeaTurtle.Ropes[0]), true);
        assert.strictEqual(Object.isFrozen(SeaTurtle.Ropes[0].start), true);
        assert.strictEqual(Object.isFrozen(SeaTurtle.Ropes[0].end), true);
        assert.strictEqual(Object.isFrozen(SeaTurtle.Ropes[2].start), true);

        assert.deepStrictEqual(plain(SeaTurtle.Dialogues), [
          "Good start, Aiden! Two ropes left.",
          "Well done! One rope left.",
          "Great work, Aiden! The turtle is free!"
        ]);
        assert.strictEqual(Object.isFrozen(SeaTurtle.Dialogues), true);

        assert.deepStrictEqual(
          Object.keys(SeaTurtle).sort(),
          [
            "Constants",
            "Dialogues",
            "MissionId",
            "Ropes",
            "finishFeedback",
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
          "setActiveRope",
          "completeRope",
          "failRope",
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
          assert.strictEqual(SeaTurtle[name], undefined, "exposed " + name);
        }

        SeaTurtle.extra = 1;
        SeaTurtle.Constants.extra = 1;
        SeaTurtle.Ropes[0].start.extra = 1;
        assert.strictEqual(SeaTurtle.extra, undefined);
        assert.strictEqual(SeaTurtle.Constants.extra, undefined);
        assert.strictEqual(SeaTurtle.Ropes[0].start.extra, undefined);

        const before = SeaTurtle.getSnapshot();
        assert.deepStrictEqual(plain(before), {
          active: false,
          activeRopeId: null,
          completedRopeIds: [],
          failureCount: 0,
          helpLevel: 0,
          tapStartArmed: false,
          pointerActive: false,
          inputLocked: true,
          feedback: null,
          complete: false
        });

        assert.strictEqual(SeaTurtle.start(), true);
        const after = SeaTurtle.getSnapshot();
        assert.deepStrictEqual(plain(after), {
          active: true,
          activeRopeId: "rope-1",
          completedRopeIds: [],
          failureCount: 0,
          helpLevel: 0,
          tapStartArmed: false,
          pointerActive: false,
          inputLocked: false,
          feedback: null,
          complete: false
        });

        assert.strictEqual(SeaTurtle.stop(), true);
        assert.strictEqual(SeaTurtle.stop(), false);
        assert.deepStrictEqual(plain(SeaTurtle.getSnapshot()), {
          active: false,
          activeRopeId: null,
          completedRopeIds: [],
          failureCount: 0,
          helpLevel: 0,
          tapStartArmed: false,
          pointerActive: false,
          inputLocked: true,
          feedback: null,
          complete: false
        });
        """
    )
    _assert_node_ok(_run_node(harness))


def test_fixed_order_trace_success_and_feedback_advance() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const SeaTurtle = freshSeaTurtle();
        SeaTurtle.start();
        let snap = SeaTurtle.getSnapshot();
        assert.strictEqual(snap.activeRopeId, "rope-1");
        assert.strictEqual(snap.inputLocked, false);
        assert.deepStrictEqual(plain(snap.completedRopeIds), []);

        assert.strictEqual(SeaTurtle.pointerDown(1, 800, 305), true);
        assert.strictEqual(SeaTurtle.pointerMove(1, 900, 315), true);
        assert.strictEqual(SeaTurtle.pointerMove(1, 1000, 322), true);
        const result = SeaTurtle.pointerUp(1, 1035, 328);
        assert.deepStrictEqual(plain(result), {
          accepted: true,
          outcome: "success",
          ropeId: "rope-1"
        });

        snap = SeaTurtle.getSnapshot();
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(snap.inputLocked, true);
        assert.strictEqual(snap.activeRopeId, "rope-1");
        assert.deepStrictEqual(plain(snap.completedRopeIds), ["rope-1"]);

        const finish = SeaTurtle.finishFeedback();
        assert.deepStrictEqual(plain(finish), {
          changed: true,
          complete: false,
          nextRopeId: "rope-2"
        });
        const idle = SeaTurtle.finishFeedback();
        assert.deepStrictEqual(plain(idle), {
          changed: false,
          complete: false,
          nextRopeId: null
        });
        snap = SeaTurtle.getSnapshot();
        assert.strictEqual(snap.activeRopeId, "rope-2");
        assert.strictEqual(snap.feedback, null);
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(snap.failureCount, 0);
        assert.strictEqual(snap.helpLevel, 0);
        assert.deepStrictEqual(plain(snap.completedRopeIds), ["rope-1"]);

        const wrong = SeaTurtle.pointerDown(2, 790, 425);
        assert.strictEqual(wrong, true);
        SeaTurtle.pointerMove(2, 900, 428);
        const wrongUp = SeaTurtle.pointerUp(2, 1000, 432);
        assert.strictEqual(wrongUp.outcome, "failure");
        assert.strictEqual(wrongUp.ropeId, "rope-2");
        assert.strictEqual(SeaTurtle.getSnapshot().activeRopeId, "rope-2");
        assert.deepStrictEqual(plain(SeaTurtle.getSnapshot().completedRopeIds), ["rope-1"]);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_two_tap_alternative_completes_current_rope() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const SeaTurtle = freshSeaTurtle();
        SeaTurtle.start();

        const firstTap = SeaTurtle.pointerDown(1, 790, 305);
        assert.strictEqual(firstTap, true);
        const armed = SeaTurtle.pointerUp(1, 790, 305);
        assert.deepStrictEqual(plain(armed), {
          accepted: true,
          outcome: "none",
          ropeId: "rope-1"
        });
        let snap = SeaTurtle.getSnapshot();
        assert.strictEqual(snap.tapStartArmed, true);
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(snap.feedback, null);
        assert.strictEqual(snap.failureCount, 0);

        const secondTap = SeaTurtle.pointerDown(2, 1030, 328);
        assert.strictEqual(secondTap, true);
        const done = SeaTurtle.pointerUp(2, 1030, 328);
        assert.deepStrictEqual(plain(done), {
          accepted: true,
          outcome: "success",
          ropeId: "rope-1"
        });
        snap = SeaTurtle.getSnapshot();
        assert.strictEqual(snap.tapStartArmed, false);
        assert.strictEqual(snap.feedback, "success");
        assert.deepStrictEqual(plain(snap.completedRopeIds), ["rope-1"]);
        SeaTurtle.finishFeedback();

        assert.strictEqual(SeaTurtle.getSnapshot().activeRopeId, "rope-2");

        const badEnd = SeaTurtle.pointerDown(3, 1030, 435);
        assert.strictEqual(badEnd, true);
        const badUp = SeaTurtle.pointerUp(3, 1030, 435);
        assert.deepStrictEqual(plain(badUp), {
          accepted: true,
          outcome: "failure",
          ropeId: "rope-2"
        });
        assert.strictEqual(SeaTurtle.getSnapshot().tapStartArmed, false);
        SeaTurtle.finishFeedback();

        const firstTapAgain = SeaTurtle.pointerDown(4, 790, 425);
        SeaTurtle.pointerUp(4, 790, 425);
        assert.strictEqual(SeaTurtle.getSnapshot().tapStartArmed, true);
        const wrongSecond = SeaTurtle.pointerDown(5, 640, 430);
        SeaTurtle.pointerUp(5, 640, 430);
        let s = SeaTurtle.getSnapshot();
        assert.strictEqual(s.feedback, "failure");
        assert.strictEqual(s.tapStartArmed, false);
        assert.strictEqual(s.activeRopeId, "rope-2");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_failures_preserve_progress_and_raise_assistance() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const SeaTurtle = freshSeaTurtle();
        SeaTurtle.start();

        function farTrace(pointerId) {
          SeaTurtle.pointerDown(pointerId, 800, 305);
          SeaTurtle.pointerMove(pointerId, 900, 100);
          const result = SeaTurtle.pointerUp(pointerId, 900, 100);
          assert.strictEqual(result.outcome, "failure");
        }

        farTrace(1);
        let snap = SeaTurtle.getSnapshot();
        assert.strictEqual(snap.activeRopeId, "rope-1");
        assert.strictEqual(snap.failureCount, 1);
        assert.strictEqual(snap.helpLevel, 1);
        assert.strictEqual(snap.feedback, "failure");
        assert.strictEqual(snap.inputLocked, true);
        assert.deepStrictEqual(plain(snap.completedRopeIds), []);
        let finish = SeaTurtle.finishFeedback();
        assert.deepStrictEqual(plain(finish), {
          changed: true,
          complete: false,
          nextRopeId: "rope-1"
        });

        farTrace(2);
        snap = SeaTurtle.getSnapshot();
        assert.strictEqual(snap.failureCount, 2);
        assert.strictEqual(snap.helpLevel, 2);
        SeaTurtle.finishFeedback();

        farTrace(3);
        snap = SeaTurtle.getSnapshot();
        assert.strictEqual(snap.failureCount, 3);
        assert.strictEqual(snap.helpLevel, 3);
        SeaTurtle.finishFeedback();

        farTrace(4);
        snap = SeaTurtle.getSnapshot();
        assert.strictEqual(snap.failureCount, 4);
        assert.strictEqual(snap.helpLevel, 3);
        SeaTurtle.finishFeedback();

        const offCorridor = SeaTurtle.pointerDown(5, 790, 300);
        assert.strictEqual(offCorridor, true);
        SeaTurtle.pointerMove(5, 900, 405);
        SeaTurtle.pointerMove(5, 1000, 420);
        const wideUp = SeaTurtle.pointerUp(5, 1020, 370);
        assert.strictEqual(wideUp.outcome, "success");
        snap = SeaTurtle.getSnapshot();
        assert.strictEqual(snap.activeRopeId, "rope-1");
        assert.deepStrictEqual(plain(snap.completedRopeIds), ["rope-1"]);
        SeaTurtle.finishFeedback();
        assert.strictEqual(SeaTurtle.getSnapshot().activeRopeId, "rope-2");

        farTrace(6);
        SeaTurtle.finishFeedback();
        snap = SeaTurtle.getSnapshot();
        assert.strictEqual(snap.activeRopeId, "rope-2");
        assert.deepStrictEqual(plain(snap.completedRopeIds), ["rope-1"]);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_pointer_boundaries_cancel_and_snapshot_immutability() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const SeaTurtle = freshSeaTurtle();
        assert.strictEqual(SeaTurtle.pointerDown(1, 100, 100), false);
        assert.strictEqual(SeaTurtle.pointerUp(1, 100, 100), false);
        assert.strictEqual(SeaTurtle.pointerCancel(1), false);

        SeaTurtle.start();
        const baseline = JSON.stringify(SeaTurtle.getSnapshot());

        assert.strictEqual(SeaTurtle.pointerUp(1, 100, 100), false);
        assert.strictEqual(SeaTurtle.pointerMove(1, 100, 100), false);
        assert.strictEqual(SeaTurtle.pointerUp(NaN, 100, 100), false);
        assert.strictEqual(SeaTurtle.pointerCancel(2), false);
        assert.strictEqual(JSON.stringify(SeaTurtle.getSnapshot()), baseline);

        assert.strictEqual(SeaTurtle.pointerDown(1, NaN, 100), false);
        assert.strictEqual(SeaTurtle.pointerDown(1, 100, "x"), false);
        assert.strictEqual(SeaTurtle.pointerDown(NaN, 100, 100), false);
        assert.strictEqual(SeaTurtle.pointerDown(1, Infinity, 100), false);
        assert.strictEqual(JSON.stringify(SeaTurtle.getSnapshot()), baseline);

        assert.strictEqual(SeaTurtle.pointerDown(1, 800, 305), true);
        assert.strictEqual(SeaTurtle.pointerDown(1, 820, 310), false);
        assert.strictEqual(SeaTurtle.pointerDown(7, 830, 312), false);
        assert.strictEqual(SeaTurtle.pointerMove(2, 900, 315), false);
        assert.strictEqual(SeaTurtle.pointerMove(1, NaN, 315), false);
        assert.strictEqual(SeaTurtle.pointerCancel(2), false);
        assert.strictEqual(SeaTurtle.pointerCancel(1), true);
        let snap = SeaTurtle.getSnapshot();
        assert.strictEqual(snap.pointerActive, false);
        assert.strictEqual(snap.feedback, null);
        assert.deepStrictEqual(plain(snap.completedRopeIds), []);
        assert.strictEqual(snap.failureCount, 0);

        const badTrace = SeaTurtle.pointerDown(1, 600, 300);
        assert.strictEqual(badTrace, true);
        SeaTurtle.pointerMove(1, 700, 305);
        const badUp = SeaTurtle.pointerUp(1, 700, 305);
        assert.strictEqual(badUp.outcome, "failure");
        snap = SeaTurtle.getSnapshot();
        assert.strictEqual(snap.feedback, "failure");
        assert.strictEqual(snap.inputLocked, true);

        const locked = SeaTurtle.pointerDown(9, 800, 305);
        assert.strictEqual(locked, false);
        assert.strictEqual(SeaTurtle.getSnapshot().pointerActive, false);

        const progress = SeaTurtle.pointerDown(10, 800, 305);
        assert.strictEqual(progress, false);
        SeaTurtle.finishFeedback();

        assert.strictEqual(SeaTurtle.pointerDown(1, 800, 305), true);
        SeaTurtle.pointerMove(1, 950, 318);
        SeaTurtle.pointerMove(1, 820, 307);
        const backward = SeaTurtle.pointerUp(1, 820, 307);
        assert.strictEqual(backward.outcome, "failure");

        SeaTurtle.finishFeedback();

        const first = SeaTurtle.getSnapshot();
        const second = SeaTurtle.getSnapshot();
        assert.notStrictEqual(first, second);
        assert.strictEqual(Object.isFrozen(first), true);
        assert.strictEqual(Object.isFrozen(first.completedRopeIds), true);
        const countBefore = first.completedRopeIds.length;
        try {
          first.completedRopeIds.push("rope-9");
        } catch (err) {
          // strict-mode hosts throw for frozen mutation
        }
        assert.strictEqual(first.completedRopeIds.length, countBefore);
        assert.strictEqual(SeaTurtle.getSnapshot().completedRopeIds.length, countBefore);
        try {
          first.active = true;
        } catch (err) {
          // strict-mode hosts throw for frozen mutation
        }
        assert.strictEqual(JSON.stringify(SeaTurtle.getSnapshot()), JSON.stringify(second));
        """
    )
    _assert_node_ok(_run_node(harness))


def test_app_rescue_active_starts_and_renders_sea_turtle() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToTravel(dom, ctx, 0);
        runToRescueActive(ctx);

        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        const snap = ctx.SeaTurtle.getSnapshot();
        assert.strictEqual(snap.active, true);
        assert.strictEqual(snap.activeRopeId, "rope-1");
        assert.deepStrictEqual(plain(snap.completedRopeIds), []);
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(snap.feedback, null);
        assert.strictEqual(snap.complete, false);

        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "active");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "enabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-active"), "true");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-rope-id"), "rope-1");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-completed-count"), "0");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-help-level"), "0");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-feedback"), "none");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-complete"), "false");
        assert.strictEqual(dom.rescueProgress.textContent, "Rope 1 of 3");
        assert.strictEqual(dom.statusEl.textContent, "Rescue controls ready");
        assert.strictEqual(dom.rescueAssistHand.hidden, true);

        const labels = fillTextLabels(dom.canvas);
        assert.strictEqual(labels.includes("Cutter"), true);
        assert.strictEqual(labels.includes("GUP-C"), true);

        const arcs = callArgs(dom.canvas, "arc");
        const ropeOneStart = arcs.some(
          (a) => a[0] === 760 && a[1] === 300 && a[2] === 22
        );
        const ropeOneEnd = arcs.some(
          (a) => a[0] === 1040 && a[1] === 330 && a[2] === 15
        );
        assert.strictEqual(ropeOneStart, true);
        assert.strictEqual(ropeOneEnd, true);

        const moves = callArgs(dom.canvas, "moveTo");
        const lineTos = callArgs(dom.canvas, "lineTo");
        const ropeStarts = [
          [760, 300],
          [750, 420],
          [770, 540]
        ];
        for (const [x, y] of ropeStarts) {
          assert.strictEqual(
            moves.some((m) => m[0] === x && m[1] === y),
            true,
            "missing rope start " + x + "," + y
          );
        }
        const ropeEnds = [
          [1040, 330],
          [1050, 440],
          [1030, 570]
        ];
        for (const [x, y] of ropeEnds) {
          assert.strictEqual(
            lineTos.some((m) => m[0] === x && m[1] === y),
            true,
            "missing rope end " + x + "," + y
          );
        }
        assert.strictEqual(
          arcs.some((a) => a[0] === 930 && a[1] === 420 && a[2] === 60),
          true
        );

        assert.strictEqual(ctx.frames.pending().length, 0);
        assert.deepStrictEqual(
          Object.keys(dom.canvas.listeners).sort(),
          ["pointercancel", "pointerdown", "pointermove", "pointerup"]
        );
        """
    )
    _assert_node_ok(_run_node(harness))


def test_real_pointer_flow_frees_three_ropes_and_enters_success() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToTravel(dom, ctx, 0);
        runToRescueActive(ctx);

        completeRopeByTrace(dom, ctx, 1, { x: 800, y: 305 }, [
          { x: 900, y: 315 },
          { x: 1000, y: 322 }
        ], { x: 1035, y: 328 });
        let snap = ctx.SeaTurtle.getSnapshot();
        assert.deepStrictEqual(plain(snap.completedRopeIds), ["rope-1"]);
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(snap.inputLocked, true);
        assert.strictEqual(dom.rescueProgress.textContent, "Good start, Aiden! Two ropes left.");
        assert.strictEqual(dom.statusEl.textContent, "Good start, Aiden! Two ropes left.");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-feedback"), "success");
        assert.strictEqual(
          dom.rescueOverlay.classList.contains("ocean-rescue-sea-turtle-success"),
          true
        );
        runSuccessFeedback(ctx);
        snap = ctx.SeaTurtle.getSnapshot();
        assert.strictEqual(snap.activeRopeId, "rope-2");
        assert.strictEqual(snap.feedback, null);
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(snap.helpLevel, 0);
        assert.strictEqual(dom.rescueProgress.textContent, "Rope 2 of 3");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-rope-id"), "rope-2");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-completed-count"), "1");
        assert.strictEqual(
          dom.rescueOverlay.classList.contains("ocean-rescue-sea-turtle-success"),
          false
        );

        dispatch(dom.canvas, "pointerdown", pointerEvent(11, 780, 425));
        dispatch(dom.canvas, "pointerup", pointerEvent(11, 780, 425));
        snap = ctx.SeaTurtle.getSnapshot();
        assert.strictEqual(snap.tapStartArmed, true);
        assert.strictEqual(snap.feedback, null);
        dispatch(dom.canvas, "pointerdown", pointerEvent(12, 1040, 438));
        dispatch(dom.canvas, "pointerup", pointerEvent(12, 1040, 438));
        snap = ctx.SeaTurtle.getSnapshot();
        assert.deepStrictEqual(plain(snap.completedRopeIds), ["rope-1", "rope-2"]);
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(dom.rescueProgress.textContent, "Well done! One rope left.");
        assert.strictEqual(dom.statusEl.textContent, "Well done! One rope left.");
        runSuccessFeedback(ctx);
        snap = ctx.SeaTurtle.getSnapshot();
        assert.strictEqual(snap.activeRopeId, "rope-3");
        assert.strictEqual(dom.rescueProgress.textContent, "Rope 3 of 3");

        completeRopeByTrace(dom, ctx, 21, { x: 810, y: 545 }, [
          { x: 900, y: 550 },
          { x: 1000, y: 560 }
        ], { x: 1025, y: 568 });
        snap = ctx.SeaTurtle.getSnapshot();
        assert.deepStrictEqual(
          plain(snap.completedRopeIds),
          ["rope-1", "rope-2", "rope-3"]
        );
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(snap.activeRopeId, "rope-3");
        assert.strictEqual(
          dom.rescueProgress.textContent,
          "Great work, Aiden! The turtle is free!"
        );
        assert.strictEqual(
          dom.statusEl.textContent,
          "Great work, Aiden! The turtle is free!"
        );

        const finalTimer = timerWithDelay(ctx, 400);
        ctx.timers.run(finalTimer.id);
        snap = ctx.SeaTurtle.getSnapshot();
        assert.strictEqual(snap.complete, true);
        assert.strictEqual(snap.active, false);
        assert.strictEqual(snap.activeRopeId, null);
        assert.strictEqual(snap.inputLocked, true);
        assert.deepStrictEqual(
          plain(snap.completedRopeIds),
          ["rope-1", "rope-2", "rope-3"]
        );
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");

        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "success");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "disabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-active"), "false");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-rope-id"), "");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-completed-count"), "3");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-feedback"), "none");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-complete"), "true");
        assert.strictEqual(
          dom.rescueProgress.textContent,
          "Great work, Aiden! The turtle is free!"
        );

        const missionSnap = ctx.Missions.getSnapshot();
        assert.deepStrictEqual(plain(missionSnap.completedMissionIds), []);
        assert.deepStrictEqual(plain(missionSnap.unlockedMissionIds), ["sea-turtle"]);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");

        finalTimer.fn();
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "success");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-completed-count"), "3");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_failure_feedback_help_ui_mission_gating_and_missing_runtime_are_safe() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToTravel(dom, ctx, 0);
        runToRescueActive(ctx);

        dispatch(dom.canvas, "pointerdown", pointerEvent(1, 800, 305));
        dispatch(dom.canvas, "pointermove", pointerEvent(1, 900, 100));
        dispatch(dom.canvas, "pointerup", pointerEvent(1, 900, 100));
        let snap = ctx.SeaTurtle.getSnapshot();
        assert.strictEqual(snap.feedback, "failure");
        assert.strictEqual(snap.helpLevel, 1);
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-feedback"), "failure");
        assert.strictEqual(dom.rescueProgress.textContent, "Try rope 1 again");
        assert.strictEqual(
          dom.rescueOverlay.classList.contains("ocean-rescue-sea-turtle-failure"),
          true
        );

        runFailureFeedback(ctx);
        snap = ctx.SeaTurtle.getSnapshot();
        assert.strictEqual(snap.activeRopeId, "rope-1");
        assert.strictEqual(snap.helpLevel, 1);
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(dom.rescueAssistHand.hidden, false);
        assert.strictEqual(
          dom.rescueAssistHand.classList.contains("ocean-rescue-assist-hand-visible"),
          true
        );
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-help-level"), "1");
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-feedback"), "none");

        dispatch(dom.canvas, "pointerdown", pointerEvent(2, 800, 305));
        dispatch(dom.canvas, "pointermove", pointerEvent(2, 900, 100));
        dispatch(dom.canvas, "pointerup", pointerEvent(2, 900, 100));
        assert.strictEqual(dom.rescueAssistHand.hidden, true);
        runFailureFeedback(ctx);
        snap = ctx.SeaTurtle.getSnapshot();
        assert.strictEqual(snap.helpLevel, 2);
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-help-level"), "2");
        const arcsAfterSecond = callArgs(dom.canvas, "arc");
        assert.strictEqual(
          arcsAfterSecond.some((a) => a[0] === 760 && a[1] === 300 && a[2] === 30),
          true
        );

        dispatch(dom.canvas, "pointerdown", pointerEvent(3, 800, 305));
        dispatch(dom.canvas, "pointermove", pointerEvent(3, 900, 100));
        dispatch(dom.canvas, "pointerup", pointerEvent(3, 900, 100));
        runFailureFeedback(ctx);
        snap = ctx.SeaTurtle.getSnapshot();
        assert.strictEqual(snap.helpLevel, 3);
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-help-level"), "3");
        const dashCalls = callArgs(dom.canvas, "setLineDash");
        assert.strictEqual(
          dashCalls.some((d) => d.length === 1 && d[0][0] === 14 && d[0][1] === 12),
          true
        );
        const lineWidthSets = dom.canvas._context.calls
          .filter((call) => call[0] === "set:lineWidth")
          .map((call) => call[1]);
        assert.strictEqual(lineWidthSets.includes(200), true);

        const noForward = ctx.SeaTurtle.getSnapshot();
        dispatch(dom.stage, "pointerdown", pointerEvent(99, 400, 300));
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        assert.strictEqual(
          JSON.stringify(ctx.SeaTurtle.getSnapshot()),
          JSON.stringify(noForward)
        );

        const crabDom = makeBootDom();
        const crabCtx = loadApp(crabDom.document);
        crabCtx.Missions.completeMission("sea-turtle");
        crabCtx.Missions.completeMission("crab");
        startLaunchToTravel(crabDom, crabCtx, 0, 1);
        runToRescueActive(crabCtx);
        assert.strictEqual(crabCtx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        assert.strictEqual(crabCtx.SeaTurtle.getSnapshot().active, false);
        assert.strictEqual(crabDom.rootEl.getAttribute("data-sea-turtle-active"), null);

        const whaleDom = makeBootDom();
        const whaleCtx = loadApp(whaleDom.document);
        whaleCtx.Missions.completeMission("sea-turtle");
        whaleCtx.Missions.completeMission("crab");
        startLaunchToTravel(whaleDom, whaleCtx, 0, 2);
        runToRescueActive(whaleCtx);
        assert.strictEqual(whaleCtx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        assert.strictEqual(whaleCtx.SeaTurtle.getSnapshot().active, false);
        assert.strictEqual(whaleDom.rootEl.getAttribute("data-sea-turtle-active"), null);

        const missingSeaTurtleDom = makeBootDom();
        const missingSeaTurtleCtx = loadApp(
          missingSeaTurtleDom.document,
          {},
          { skipSeaTurtle: true }
        );
        assert.strictEqual(missingSeaTurtleCtx.SeaTurtle, undefined);
        startLaunchToTravel(missingSeaTurtleDom, missingSeaTurtleCtx, 0);
        runToRescueActive(missingSeaTurtleCtx);
        assert.strictEqual(
          missingSeaTurtleCtx.State.getSnapshot().phase,
          "RESCUE_ACTIVE"
        );
        assert.strictEqual(
          missingSeaTurtleDom.rootEl.getAttribute("data-rescue-phase"),
          "active"
        );
        assert.strictEqual(
          missingSeaTurtleDom.rootEl.getAttribute("data-sea-turtle-active"),
          null
        );

        const noInteractionDom = makeBootDom({ includeInteraction: false });
        const noInteractionCtx = loadApp(noInteractionDom.document);
        startLaunchToTravel(noInteractionDom, noInteractionCtx, 0);
        runToRescueActive(noInteractionCtx);
        assert.strictEqual(
          noInteractionCtx.State.getSnapshot().phase,
          "RESCUE_ACTIVE"
        );
        assert.strictEqual(noInteractionCtx.SeaTurtle.getSnapshot().active, true);
        assert.strictEqual(
          noInteractionDom.rootEl.getAttribute("data-sea-turtle-rope-id"),
          "rope-1"
        );
        """
    )
    _assert_node_ok(_run_node(harness))
