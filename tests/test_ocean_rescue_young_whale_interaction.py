"""Behavioral tests for the Ocean Rescue young whale tow interaction.

Every JavaScript assertion runs the real tracked sources (``state.js``,
``missions.js``, ``gups.js``, ``launch.js``, ``travel.js``, ``terrain.js``,
``rescue.js``, ``sea-turtle.js``, ``crab.js``, ``young-whale.js``, and
``app.js``) through the installed Node runtime in a fresh VM sandbox using a
minimal fake DOM, a fake canvas 2D context, a deterministic fake timer queue,
and a deterministic fake animation-frame queue. No npm packages, no browser
automation, no real-time sleeps, and no separate JavaScript test file are
used.
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
    const YOUNG_WHALE_SOURCE = fs.readFileSync("domains/ocean-rescue/src/young-whale.js", "utf8");
    const APP_SOURCE = fs.readFileSync("domains/ocean-rescue/src/app.js", "utf8");

    function plain(value) {
      return JSON.parse(JSON.stringify(value));
    }

    function freshYoungWhale() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(YOUNG_WHALE_SOURCE, sandbox, { filename: "young-whale.js" });
      return sandbox.window.OceanRescue.YoungWhale;
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
      if (!opts.skipYoungWhale) {
        vm.runInContext(YOUNG_WHALE_SOURCE, sandbox, { filename: "young-whale.js" });
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
        YoungWhale: OceanRescue.YoungWhale,
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


def test_young_whale_constants_catalog_and_public_contract() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const YoungWhale = freshYoungWhale();

        assert.strictEqual(YoungWhale.MissionId, "young-whale");
        assert.strictEqual(Object.isFrozen(YoungWhale), true);

        assert.deepStrictEqual(plain(YoungWhale.Constants), {
          connectionStartRadius: 60,
          assistedConnectionStartRadius: 82,
          hookRadius: 60,
          assistedHookRadius: 82,
          connectionPathTolerance: 90,
          assistedConnectionPathTolerance: 130,
          minimumConnectionProgress: 0.88,
          maxBackwardProgress: 0.12,
          gupHitRadius: 72,
          assistedGupHitRadius: 94,
          safeSpotRadius: 72,
          assistedSafeSpotRadius: 104,
          towingPathTolerance: 130,
          assistedTowingPathTolerance: 180,
          wrongDirectionDistance: 80,
          pointerMovementThreshold: 10,
          successFeedbackMs: 400,
          failureFeedbackMs: 300
        });
        assert.strictEqual(Object.isFrozen(YoungWhale.Constants), true);

        assert.deepStrictEqual(plain(YoungWhale.Instructions), {
          connection: "Drag from the debris to the GUP hook!",
          towing: "Drag the GUP to the safe spot!"
        });
        assert.strictEqual(Object.isFrozen(YoungWhale.Instructions), true);

        assert.deepStrictEqual(plain(YoungWhale.GupStart), { x: 340, y: 420 });
        assert.strictEqual(Object.isFrozen(YoungWhale.GupStart), true);
        assert.deepStrictEqual(plain(YoungWhale.GupHook), { x: 275, y: 420 });
        assert.strictEqual(Object.isFrozen(YoungWhale.GupHook), true);

        assert.deepStrictEqual(plain(YoungWhale.Debris), [
          { id: "debris-1", order: 1, radius: 44, start: { x: 820, y: 260 }, connection: { x: 780, y: 260 }, safeSpot: { x: 180, y: 190 }, cleared: { x: 680, y: 30 } },
          { id: "debris-2", order: 2, radius: 52, start: { x: 880, y: 420 }, connection: { x: 830, y: 420 }, safeSpot: { x: 160, y: 420 }, cleared: { x: 700, y: 420 } },
          { id: "debris-3", order: 3, radius: 60, start: { x: 930, y: 550 }, connection: { x: 875, y: 550 }, safeSpot: { x: 180, y: 610 }, cleared: { x: 770, y: 740 } }
        ]);
        assert.strictEqual(Object.isFrozen(YoungWhale.Debris), true);
        assert.strictEqual(Object.isFrozen(YoungWhale.Debris[0]), true);
        assert.strictEqual(Object.isFrozen(YoungWhale.Debris[0].start), true);
        assert.strictEqual(Object.isFrozen(YoungWhale.Debris[0].connection), true);
        assert.strictEqual(Object.isFrozen(YoungWhale.Debris[0].safeSpot), true);
        assert.strictEqual(Object.isFrozen(YoungWhale.Debris[0].cleared), true);
        assert.strictEqual(Object.isFrozen(YoungWhale.Debris[2].start), true);

        assert.deepStrictEqual(plain(YoungWhale.Dialogues), [
          "Good work, Aiden! Two pieces left. The whale knows we\u2019re here.",
          "Just one more! The whale is moving toward the opening.",
          "The path is clear! Let\u2019s give the whale room to swim."
        ]);
        assert.strictEqual(Object.isFrozen(YoungWhale.Dialogues), true);

        assert.deepStrictEqual(
          Object.keys(YoungWhale).sort(),
          [
            "Constants",
            "Debris",
            "Dialogues",
            "GupHook",
            "GupStart",
            "Instructions",
            "MissionId",
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
          "forceSuccess",
          "connect",
          "completeTow",
          "failStage",
          "setHelpLevel",
          "setPosition",
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
          assert.strictEqual(YoungWhale[name], undefined, "exposed " + name);
        }

        YoungWhale.extra = 1;
        YoungWhale.Constants.extra = 1;
        YoungWhale.Instructions.extra = 1;
        YoungWhale.Debris[0].start.extra = 1;
        YoungWhale.GupStart.extra = 1;
        assert.strictEqual(YoungWhale.extra, undefined);
        assert.strictEqual(YoungWhale.Constants.extra, undefined);
        assert.strictEqual(YoungWhale.Instructions.extra, undefined);
        assert.strictEqual(YoungWhale.Debris[0].start.extra, undefined);
        assert.strictEqual(YoungWhale.GupStart.extra, undefined);

        const before = YoungWhale.getSnapshot();
        assert.deepStrictEqual(plain(before), {
          active: false,
          activeDebrisId: null,
          completedDebrisIds: [],
          stage: null,
          connected: false,
          failureCount: 0,
          helpLevel: 0,
          pointerActive: false,
          currentGupCenter: null,
          currentDebrisCenter: null,
          inputLocked: true,
          feedback: null,
          complete: false
        });

        assert.strictEqual(YoungWhale.start(), true);
        const after = YoungWhale.getSnapshot();
        assert.deepStrictEqual(plain(after), {
          active: true,
          activeDebrisId: "debris-1",
          completedDebrisIds: [],
          stage: "connection",
          connected: false,
          failureCount: 0,
          helpLevel: 0,
          pointerActive: false,
          currentGupCenter: null,
          currentDebrisCenter: { x: 820, y: 260 },
          inputLocked: false,
          feedback: null,
          complete: false
        });

        assert.strictEqual(YoungWhale.stop(), true);
        assert.strictEqual(YoungWhale.stop(), false);
        assert.deepStrictEqual(plain(YoungWhale.getSnapshot()), {
          active: false,
          activeDebrisId: null,
          completedDebrisIds: [],
          stage: null,
          connected: false,
          failureCount: 0,
          helpLevel: 0,
          pointerActive: false,
          currentGupCenter: null,
          currentDebrisCenter: null,
          inputLocked: true,
          feedback: null,
          complete: false
        });
        """
    )
    _assert_node_ok(_run_node(harness))


def test_fixed_order_connection_success_and_invalid_boundaries() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const YoungWhale = freshYoungWhale();
        YoungWhale.start();
        let snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.activeDebrisId, "debris-1");
        assert.strictEqual(snap.stage, "connection");
        assert.strictEqual(snap.inputLocked, false);
        assert.deepStrictEqual(plain(snap.completedDebrisIds), []);

        assert.strictEqual(YoungWhale.pointerDown(1, 800, 260), true);
        assert.strictEqual(YoungWhale.pointerMove(1, 650, 300), true);
        assert.strictEqual(YoungWhale.pointerMove(1, 500, 360), true);
        assert.strictEqual(YoungWhale.pointerMove(1, 350, 400), true);
        const result = YoungWhale.pointerUp(1, 285, 420);
        assert.deepStrictEqual(plain(result), {
          accepted: true,
          outcome: "success",
          debrisId: "debris-1"
        });
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(snap.inputLocked, true);
        assert.strictEqual(snap.connected, true);
        assert.strictEqual(snap.activeDebrisId, "debris-1");
        assert.deepStrictEqual(plain(snap.completedDebrisIds), []);
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 820, y: 260 });

        YoungWhale.finishFeedback();
        assert.strictEqual(YoungWhale.getSnapshot().stage, "towing");

        const whaleStart = YoungWhale.pointerDown(2, 1050, 400);
        assert.strictEqual(whaleStart, true);
        YoungWhale.pointerMove(2, 900, 350);
        const whaleUp = YoungWhale.pointerUp(2, 900, 350);
        assert.deepStrictEqual(plain(whaleUp), {
          accepted: true,
          outcome: "failure",
          debrisId: "debris-1"
        });
        assert.strictEqual(YoungWhale.getSnapshot().activeDebrisId, "debris-1");
        YoungWhale.finishFeedback();
        assert.strictEqual(YoungWhale.getSnapshot().stage, "towing");

        const wrongDebrisStart = YoungWhale.pointerDown(3, 850, 425);
        assert.strictEqual(wrongDebrisStart, true);
        YoungWhale.pointerMove(3, 700, 420);
        const wrongDebrisUp = YoungWhale.pointerUp(3, 700, 420);
        assert.strictEqual(wrongDebrisUp.outcome, "failure");
        YoungWhale.finishFeedback();

        const offPathStart = YoungWhale.pointerDown(4, 800, 260);
        assert.strictEqual(offPathStart, true);
        YoungWhale.pointerMove(4, 650, 300);
        YoungWhale.pointerMove(4, 500, 100);
        const offPathUp = YoungWhale.pointerUp(4, 500, 100);
        assert.strictEqual(offPathUp.outcome, "failure");
        YoungWhale.finishFeedback();

        const shortTrace = YoungWhale.pointerDown(5, 800, 260);
        assert.strictEqual(shortTrace, true);
        YoungWhale.pointerMove(5, 650, 300);
        YoungWhale.pointerMove(5, 450, 360);
        const outsideHookUp = YoungWhale.pointerUp(5, 335, 400);
        assert.strictEqual(outsideHookUp.outcome, "failure");
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.activeDebrisId, "debris-1");
        assert.strictEqual(snap.connected, true);
        assert.deepStrictEqual(plain(snap.completedDebrisIds), []);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_connection_feedback_transitions_to_towing_stage() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const YoungWhale = freshYoungWhale();
        YoungWhale.start();
        assert.strictEqual(YoungWhale.getSnapshot().stage, "connection");

        YoungWhale.pointerDown(1, 800, 260);
        YoungWhale.pointerMove(1, 650, 300);
        YoungWhale.pointerMove(1, 500, 360);
        const result = YoungWhale.pointerUp(1, 285, 420);
        assert.strictEqual(result.outcome, "success");
        let snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "connection");
        assert.strictEqual(snap.connected, true);
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(snap.inputLocked, true);

        const finish = YoungWhale.finishFeedback();
        assert.deepStrictEqual(plain(finish), {
          changed: true,
          complete: false,
          nextDebrisId: "debris-1"
        });
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.strictEqual(snap.connected, true);
        assert.strictEqual(snap.feedback, null);
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(snap.failureCount, 0);
        assert.strictEqual(snap.helpLevel, 0);
        assert.deepStrictEqual(plain(snap.currentGupCenter), { x: 340, y: 420 });
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 820, y: 260 });

        const idle = YoungWhale.finishFeedback();
        assert.deepStrictEqual(plain(idle), {
          changed: false,
          complete: false,
          nextDebrisId: null
        });
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.strictEqual(snap.connected, true);
        assert.strictEqual(snap.feedback, null);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_direct_follow_towing_success_early_release_and_wrong_direction() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const YoungWhale = freshYoungWhale();
        YoungWhale.start();
        YoungWhale.pointerDown(1, 800, 260);
        YoungWhale.pointerMove(1, 650, 300);
        YoungWhale.pointerMove(1, 500, 360);
        YoungWhale.pointerUp(1, 285, 420);
        YoungWhale.finishFeedback();
        let snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.deepStrictEqual(plain(snap.currentGupCenter), { x: 340, y: 420 });
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 820, y: 260 });

        assert.strictEqual(YoungWhale.pointerDown(2, 350, 420), true);
        assert.strictEqual(YoungWhale.pointerMove(2, 300, 390), true);
        snap = YoungWhale.getSnapshot();
        assert.deepStrictEqual(plain(snap.currentGupCenter), { x: 300, y: 390 });
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 770, y: 230 });
        assert.strictEqual(YoungWhale.pointerMove(2, 260, 330), true);
        assert.strictEqual(YoungWhale.pointerMove(2, 220, 270), true);
        snap = YoungWhale.getSnapshot();
        assert.deepStrictEqual(plain(snap.currentGupCenter), { x: 220, y: 270 });
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 690, y: 110 });

        const success = YoungWhale.pointerUp(2, 200, 220);
        assert.deepStrictEqual(plain(success), {
          accepted: true,
          outcome: "success",
          debrisId: "debris-1"
        });
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(snap.connected, true);
        assert.strictEqual(snap.activeDebrisId, "debris-1");
        assert.deepStrictEqual(plain(snap.completedDebrisIds), ["debris-1"]);
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 680, y: 30 });

        YoungWhale.finishFeedback();
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "connection");
        assert.strictEqual(snap.connected, false);
        assert.strictEqual(snap.activeDebrisId, "debris-2");
        assert.strictEqual(snap.failureCount, 0);
        assert.strictEqual(snap.helpLevel, 0);
        assert.deepStrictEqual(plain(snap.completedDebrisIds), ["debris-1"]);
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 880, y: 420 });
        assert.strictEqual(snap.currentGupCenter, null);

        YoungWhale.pointerDown(3, 850, 420);
        YoungWhale.pointerMove(3, 700, 420);
        YoungWhale.pointerMove(3, 500, 420);
        YoungWhale.pointerUp(3, 280, 420);
        YoungWhale.finishFeedback();
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.deepStrictEqual(plain(snap.currentGupCenter), { x: 340, y: 420 });
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 880, y: 420 });

        const early = YoungWhale.pointerDown(4, 350, 420);
        assert.strictEqual(early, true);
        YoungWhale.pointerMove(4, 300, 420);
        const earlyUp = YoungWhale.pointerUp(4, 300, 420);
        assert.deepStrictEqual(plain(earlyUp), {
          accepted: true,
          outcome: "failure",
          debrisId: "debris-2"
        });
        YoungWhale.finishFeedback();
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.strictEqual(snap.connected, true);
        assert.strictEqual(snap.activeDebrisId, "debris-2");
        assert.deepStrictEqual(plain(snap.completedDebrisIds), ["debris-1"]);

        const wrongDir = YoungWhale.pointerDown(5, 350, 420);
        assert.strictEqual(wrongDir, true);
        YoungWhale.pointerMove(5, 420, 500);
        const wrongDirUp = YoungWhale.pointerUp(5, 430, 520);
        assert.deepStrictEqual(plain(wrongDirUp), {
          accepted: true,
          outcome: "failure",
          debrisId: "debris-2"
        });
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.strictEqual(snap.connected, true);
        assert.strictEqual(snap.activeDebrisId, "debris-2");
        assert.deepStrictEqual(plain(snap.completedDebrisIds), ["debris-1"]);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_towing_failure_preserves_connection_and_completed_debris() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const YoungWhale = freshYoungWhale();
        YoungWhale.start();
        YoungWhale.pointerDown(1, 800, 260);
        YoungWhale.pointerMove(1, 650, 300);
        YoungWhale.pointerMove(1, 500, 360);
        YoungWhale.pointerUp(1, 285, 420);
        YoungWhale.finishFeedback();
        assert.strictEqual(YoungWhale.getSnapshot().connected, true);

        YoungWhale.pointerDown(2, 350, 420);
        YoungWhale.pointerMove(2, 300, 390);
        const failed = YoungWhale.pointerUp(2, 300, 390);
        assert.strictEqual(failed.outcome, "failure");
        let snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.strictEqual(snap.connected, true);
        assert.strictEqual(snap.activeDebrisId, "debris-1");
        assert.strictEqual(snap.feedback, "failure");
        assert.strictEqual(snap.inputLocked, true);
        assert.deepStrictEqual(plain(snap.currentGupCenter), { x: 340, y: 420 });
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 820, y: 260 });
        assert.deepStrictEqual(plain(snap.completedDebrisIds), []);

        YoungWhale.finishFeedback();
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.strictEqual(snap.connected, true);
        assert.strictEqual(snap.inputLocked, false);
        assert.deepStrictEqual(plain(snap.currentGupCenter), { x: 340, y: 420 });
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 820, y: 260 });

        YoungWhale.pointerDown(3, 350, 420);
        YoungWhale.pointerMove(3, 300, 390);
        YoungWhale.pointerMove(3, 260, 330);
        YoungWhale.pointerMove(3, 220, 270);
        const done = YoungWhale.pointerUp(3, 200, 220);
        assert.strictEqual(done.outcome, "success");
        YoungWhale.finishFeedback();
        assert.strictEqual(YoungWhale.getSnapshot().activeDebrisId, "debris-2");

        YoungWhale.pointerDown(4, 850, 420);
        YoungWhale.pointerMove(4, 700, 420);
        YoungWhale.pointerMove(4, 500, 420);
        YoungWhale.pointerUp(4, 280, 420);
        YoungWhale.finishFeedback();
        YoungWhale.pointerDown(5, 350, 420);
        YoungWhale.pointerMove(5, 300, 420);
        const failedTow = YoungWhale.pointerUp(5, 300, 420);
        assert.strictEqual(failedTow.outcome, "failure");
        YoungWhale.finishFeedback();
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.strictEqual(snap.connected, true);
        assert.strictEqual(snap.activeDebrisId, "debris-2");
        assert.deepStrictEqual(plain(snap.completedDebrisIds), ["debris-1"]);
        assert.deepStrictEqual(plain(snap.currentGupCenter), { x: 340, y: 420 });
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 880, y: 420 });

        YoungWhale.pointerDown(6, 350, 420);
        YoungWhale.pointerMove(6, 300, 420);
        YoungWhale.pointerMove(6, 250, 420);
        YoungWhale.pointerMove(6, 200, 420);
        const complete = YoungWhale.pointerUp(6, 180, 420);
        assert.strictEqual(complete.outcome, "success");
        YoungWhale.finishFeedback();
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.activeDebrisId, "debris-3");
        assert.strictEqual(snap.stage, "connection");
        assert.strictEqual(snap.connected, false);
        assert.deepStrictEqual(plain(snap.completedDebrisIds), ["debris-1", "debris-2"]);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_towing_visual_geometry_tracks_gup_and_debris_translation() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        ctx.Missions.completeMission("sea-turtle");
        ctx.Missions.completeMission("crab");
        startLaunchToTravel(dom, ctx, 0, 2);
        runToRescueActive(ctx);

        function hookArc(calls) {
          const matches = calls
            .filter((c) => c[0] === "arc" && Math.abs(c[3] - 12) < 0.5)
            .map((c) => [c[1], c[2]]);
          assert.strictEqual(matches.length >= 1, true, "missing hook dot arc");
          return matches[matches.length - 1];
        }

        function arcAt(calls, radius) {
          const matches = calls
            .filter((c) => c[0] === "arc" && Math.abs(c[3] - radius) < 0.5)
            .map((c) => [c[1], c[2]]);
          assert.strictEqual(matches.length >= 1, true, "missing arc at radius " + radius);
          return matches[matches.length - 1];
        }

        function towLine(calls) {
          let last = null;
          for (let i = 0; i < calls.length; i += 1) {
            if (calls[i][0] !== "moveTo") continue;
            for (let j = i + 1; j < calls.length; j += 1) {
              if (calls[j][0] === "moveTo") break;
              if (calls[j][0] === "lineTo") {
                last = [calls[i].slice(1), calls[j].slice(1)];
                break;
              }
            }
          }
          assert.strictEqual(last !== null, true, "missing tow line");
          return last;
        }

        dispatch(dom.canvas, "pointerdown", pointerEvent(1, 800, 260));
        dispatch(dom.canvas, "pointermove", pointerEvent(1, 650, 300));
        dispatch(dom.canvas, "pointermove", pointerEvent(1, 500, 360));
        dispatch(dom.canvas, "pointerup", pointerEvent(1, 285, 420));
        runSuccessFeedback(ctx);
        assert.strictEqual(ctx.YoungWhale.getSnapshot().stage, "towing");

        const initCalls = dom.canvas._context.calls;
        assert.deepStrictEqual(hookArc(initCalls), [275, 420]);
        assert.deepStrictEqual(towLine(initCalls), [[780, 260], [275, 420]]);

        dispatch(dom.canvas, "pointerdown", pointerEvent(11, 350, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(11, 300, 390));
        const snap = ctx.YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.deepStrictEqual(plain(snap.currentGupCenter), { x: 300, y: 390 });
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 770, y: 230 });

        const before = dom.canvas._context.calls.length;
        dispatch(dom.canvas, "pointermove", pointerEvent(11, 280, 360));
        const frameCalls = dom.canvas._context.calls.slice(before);
        const movedSnap = ctx.YoungWhale.getSnapshot();
        assert.deepStrictEqual(plain(movedSnap.currentGupCenter), { x: 280, y: 360 });
        assert.deepStrictEqual(plain(movedSnap.currentDebrisCenter), { x: 750, y: 200 });
        assert.deepStrictEqual(arcAt(frameCalls, 36), [280, 360]);
        assert.deepStrictEqual(arcAt(frameCalls, 44), [750, 200]);
        assert.deepStrictEqual(hookArc(frameCalls), [215, 360]);
        assert.deepStrictEqual(towLine(frameCalls), [[710, 200], [215, 360]]);

        const safeSpotLabel = frameCalls
          .filter((c) => c[0] === "fillText" && c[1] === "Safe spot")
          .map((c) => c.slice(1));
        assert.strictEqual(safeSpotLabel.length, 1);
        assert.deepStrictEqual(safeSpotLabel[0], ["Safe spot", 180, 280]);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_towing_failure_reset_restores_static_geometry() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        ctx.Missions.completeMission("sea-turtle");
        ctx.Missions.completeMission("crab");
        startLaunchToTravel(dom, ctx, 0, 2);
        runToRescueActive(ctx);

        function hookArc(calls) {
          const matches = calls
            .filter((c) => c[0] === "arc" && Math.abs(c[3] - 12) < 0.5)
            .map((c) => [c[1], c[2]]);
          assert.strictEqual(matches.length >= 1, true, "missing hook dot arc");
          return matches[matches.length - 1];
        }

        function arcAt(calls, radius) {
          const matches = calls
            .filter((c) => c[0] === "arc" && Math.abs(c[3] - radius) < 0.5)
            .map((c) => [c[1], c[2]]);
          assert.strictEqual(matches.length >= 1, true, "missing arc at radius " + radius);
          return matches[matches.length - 1];
        }

        function towLine(calls) {
          let last = null;
          for (let i = 0; i < calls.length; i += 1) {
            if (calls[i][0] !== "moveTo") continue;
            for (let j = i + 1; j < calls.length; j += 1) {
              if (calls[j][0] === "moveTo") break;
              if (calls[j][0] === "lineTo") {
                last = [calls[i].slice(1), calls[j].slice(1)];
                break;
              }
            }
          }
          assert.strictEqual(last !== null, true, "missing tow line");
          return last;
        }

        dispatch(dom.canvas, "pointerdown", pointerEvent(1, 800, 260));
        dispatch(dom.canvas, "pointermove", pointerEvent(1, 650, 300));
        dispatch(dom.canvas, "pointermove", pointerEvent(1, 500, 360));
        dispatch(dom.canvas, "pointerup", pointerEvent(1, 285, 420));
        runSuccessFeedback(ctx);

        const before = dom.canvas._context.calls.length;
        dispatch(dom.canvas, "pointerdown", pointerEvent(11, 350, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(11, 300, 390));
        dispatch(dom.canvas, "pointerup", pointerEvent(11, 300, 390));
        assert.strictEqual(ctx.YoungWhale.getSnapshot().feedback, "failure");
        runFailureFeedback(ctx);

        let snap = ctx.YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.strictEqual(snap.feedback, null);
        assert.deepStrictEqual(plain(snap.currentGupCenter), { x: 340, y: 420 });
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 820, y: 260 });

        const frameCalls = dom.canvas._context.calls.slice(before);
        assert.deepStrictEqual(arcAt(frameCalls, 36), [340, 420]);
        assert.deepStrictEqual(arcAt(frameCalls, 44), [820, 260]);
        assert.deepStrictEqual(hookArc(frameCalls), [275, 420]);
        assert.deepStrictEqual(towLine(frameCalls), [[780, 260], [275, 420]]);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_towing_success_completes_without_stale_translated_connector() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        ctx.Missions.completeMission("sea-turtle");
        ctx.Missions.completeMission("crab");
        startLaunchToTravel(dom, ctx, 0, 2);
        runToRescueActive(ctx);

        function hookArc(calls) {
          const matches = calls
            .filter((c) => c[0] === "arc" && Math.abs(c[3] - 12) < 0.5)
            .map((c) => [c[1], c[2]]);
          assert.strictEqual(matches.length >= 1, true, "missing hook dot arc");
          return matches[matches.length - 1];
        }

        function arcAt(calls, radius) {
          const matches = calls
            .filter((c) => c[0] === "arc" && Math.abs(c[3] - radius) < 0.5)
            .map((c) => [c[1], c[2]]);
          assert.strictEqual(matches.length >= 1, true, "missing arc at radius " + radius);
          return matches[matches.length - 1];
        }

        function towLines(calls) {
          const lines = [];
          for (let i = 0; i < calls.length; i += 1) {
            if (calls[i][0] !== "moveTo") continue;
            for (let j = i + 1; j < calls.length; j += 1) {
              if (calls[j][0] === "moveTo") break;
              if (calls[j][0] === "lineTo") {
                lines.push([calls[i].slice(1), calls[j].slice(1)]);
                break;
              }
            }
          }
          return lines;
        }

        dispatch(dom.canvas, "pointerdown", pointerEvent(1, 800, 260));
        dispatch(dom.canvas, "pointermove", pointerEvent(1, 650, 300));
        dispatch(dom.canvas, "pointermove", pointerEvent(1, 500, 360));
        dispatch(dom.canvas, "pointerup", pointerEvent(1, 285, 420));
        runSuccessFeedback(ctx);

        dispatch(dom.canvas, "pointerdown", pointerEvent(11, 350, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(11, 300, 390));
        dispatch(dom.canvas, "pointermove", pointerEvent(11, 260, 330));
        dispatch(dom.canvas, "pointermove", pointerEvent(11, 220, 270));
        dispatch(dom.canvas, "pointerup", pointerEvent(11, 200, 220));
        let snap = ctx.YoungWhale.getSnapshot();
        assert.strictEqual(snap.feedback, "success");
        assert.deepStrictEqual(plain(snap.completedDebrisIds), ["debris-1"]);
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 680, y: 30 });

        const before = dom.canvas._context.calls.length;
        runSuccessFeedback(ctx);
        snap = ctx.YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "connection");
        assert.strictEqual(snap.connected, false);
        assert.strictEqual(snap.activeDebrisId, "debris-2");
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 880, y: 420 });
        assert.strictEqual(snap.currentGupCenter, null);

        const frameCalls = dom.canvas._context.calls.slice(before);
        assert.deepStrictEqual(arcAt(frameCalls, 36), [340, 420]);
        assert.deepStrictEqual(hookArc(frameCalls), [275, 420]);
        assert.deepStrictEqual(arcAt(frameCalls, 52), [880, 420]);
        assert.deepStrictEqual(towLines(frameCalls), []);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_progressive_assistance_feedback_durations_and_immutable_snapshots() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const YoungWhale = freshYoungWhale();
        YoungWhale.start();

        function badConnection(pointerId, startX, startY) {
          YoungWhale.pointerDown(pointerId, startX, startY);
          YoungWhale.pointerMove(pointerId, startX + 60, startY + 10);
          const r = YoungWhale.pointerUp(pointerId, startX + 60, startY + 10);
          assert.strictEqual(r.outcome, "failure");
          YoungWhale.finishFeedback();
        }

        badConnection(1, 800, 260);
        let snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.failureCount, 1);
        assert.strictEqual(snap.helpLevel, 1);

        badConnection(2, 800, 260);
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.failureCount, 2);
        assert.strictEqual(snap.helpLevel, 2);

        badConnection(3, 800, 260);
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.failureCount, 3);
        assert.strictEqual(snap.helpLevel, 3);

        badConnection(4, 800, 260);
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.failureCount, 4);
        assert.strictEqual(snap.helpLevel, 3);

        const widenedStart = YoungWhale.pointerDown(5, 860, 260);
        assert.strictEqual(widenedStart, true);
        YoungWhale.pointerMove(5, 700, 300);
        YoungWhale.pointerMove(5, 450, 370);
        const widenedStartUp = YoungWhale.pointerUp(5, 280, 420);
        assert.strictEqual(widenedStartUp.outcome, "success");
        YoungWhale.finishFeedback();
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.strictEqual(snap.failureCount, 0);
        assert.strictEqual(snap.helpLevel, 0);

        function badTow(pointerId) {
          YoungWhale.pointerDown(pointerId, 350, 420);
          YoungWhale.pointerMove(pointerId, 300, 390);
          const r = YoungWhale.pointerUp(pointerId, 300, 390);
          assert.strictEqual(r.outcome, "failure");
          YoungWhale.finishFeedback();
        }

        badTow(6);
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.failureCount, 1);
        assert.strictEqual(snap.helpLevel, 1);
        badTow(7);
        assert.strictEqual(YoungWhale.getSnapshot().helpLevel, 2);
        badTow(8);
        assert.strictEqual(YoungWhale.getSnapshot().helpLevel, 3);

        YoungWhale.pointerDown(9, 350, 420);
        YoungWhale.pointerMove(9, 383, 219);
        YoungWhale.pointerMove(9, 250, 260);
        const widenedCorridor = YoungWhale.pointerUp(9, 200, 220);
        assert.strictEqual(widenedCorridor.outcome, "success");
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.failureCount, 3);
        assert.strictEqual(snap.helpLevel, 3);
        assert.deepStrictEqual(plain(snap.completedDebrisIds), ["debris-1"]);
        YoungWhale.finishFeedback();
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.failureCount, 0);
        assert.strictEqual(snap.helpLevel, 0);
        assert.strictEqual(snap.activeDebrisId, "debris-2");

        YoungWhale.pointerDown(10, 850, 420);
        YoungWhale.pointerMove(10, 700, 420);
        YoungWhale.pointerMove(10, 500, 420);
        YoungWhale.pointerUp(10, 280, 420);
        YoungWhale.finishFeedback();
        badTow(11);
        badTow(12);
        badTow(13);
        assert.strictEqual(YoungWhale.getSnapshot().helpLevel, 3);

        const widenedSafeSpot = YoungWhale.pointerDown(14, 350, 420);
        assert.strictEqual(widenedSafeSpot, true);
        YoungWhale.pointerMove(14, 300, 390);
        YoungWhale.pointerMove(14, 250, 380);
        const widenedSafeSpotUp = YoungWhale.pointerUp(14, 220, 360);
        assert.strictEqual(widenedSafeSpotUp.outcome, "success");
        snap = YoungWhale.getSnapshot();
        assert.deepStrictEqual(plain(snap.completedDebrisIds), ["debris-1", "debris-2"]);
        assert.strictEqual(snap.failureCount, 3);
        assert.strictEqual(snap.helpLevel, 3);
        YoungWhale.finishFeedback();
        snap = YoungWhale.getSnapshot();
        assert.strictEqual(snap.failureCount, 0);
        assert.strictEqual(snap.helpLevel, 0);

        const stillFails = YoungWhale.pointerDown(15, 850, 420);
        assert.strictEqual(stillFails, true);
        YoungWhale.pointerMove(15, 700, 420);
        const stillFailsUp = YoungWhale.pointerUp(15, 300, 420);
        assert.strictEqual(stillFailsUp.outcome, "failure");

        assert.strictEqual(YoungWhale.Constants.successFeedbackMs, 400);
        assert.strictEqual(YoungWhale.Constants.failureFeedbackMs, 300);

        const first = YoungWhale.getSnapshot();
        const second = YoungWhale.getSnapshot();
        assert.notStrictEqual(first, second);
        assert.strictEqual(Object.isFrozen(first), true);
        assert.strictEqual(Object.isFrozen(first.completedDebrisIds), true);
        const countBefore = first.completedDebrisIds.length;
        try {
          first.completedDebrisIds.push("debris-9");
        } catch (err) {
          // strict-mode hosts throw for frozen mutation
        }
        assert.strictEqual(first.completedDebrisIds.length, countBefore);
        try {
          first.activeDebrisId = "debris-9";
        } catch (err) {
          // strict-mode hosts throw for frozen mutation
        }
        assert.strictEqual(JSON.stringify(YoungWhale.getSnapshot()), JSON.stringify(second));
        """
    )
    _assert_node_ok(_run_node(harness))


def test_real_pointer_flow_completes_three_debris_and_enters_success() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        ctx.Missions.completeMission("sea-turtle");
        ctx.Missions.completeMission("crab");
        startLaunchToTravel(dom, ctx, 0, 2);
        runToRescueActive(ctx);

        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        let snap = ctx.YoungWhale.getSnapshot();
        assert.strictEqual(snap.active, true);
        assert.strictEqual(snap.activeDebrisId, "debris-1");
        assert.strictEqual(snap.stage, "connection");
        assert.strictEqual(snap.connected, false);
        assert.deepStrictEqual(plain(snap.completedDebrisIds), []);
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(snap.feedback, null);
        assert.strictEqual(snap.complete, false);
        assert.strictEqual(ctx.SeaTurtle.getSnapshot().active, false);
        assert.strictEqual(ctx.Crab.getSnapshot().active, false);
        assert.strictEqual(dom.rootEl.getAttribute("data-sea-turtle-active"), null);
        assert.strictEqual(dom.rootEl.getAttribute("data-crab-active"), null);

        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "active");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "enabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-active"), "true");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-debris-id"), "debris-1");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-stage"), "connection");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-completed-count"), "0");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-help-level"), "0");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-feedback"), "none");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-connected"), "false");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-complete"), "false");
        assert.strictEqual(dom.rescueProgress.textContent, "Debris 1 of 3");
        assert.strictEqual(dom.rescueInstruction.textContent, "Drag from the debris to the GUP hook!");
        assert.strictEqual(dom.statusEl.textContent, "Rescue controls ready");
        assert.strictEqual(dom.rescueAssistHand.hidden, true);
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-x"), null);
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-failure-count"), null);

        const labels = fillTextLabels(dom.canvas);
        assert.strictEqual(labels.includes("Safe spot"), false);
        const arcs = callArgs(dom.canvas, "arc");
        assert.strictEqual(
          arcs.some((a) => a[0] === 1040 && a[1] === 410 && a[2] === 66),
          true
        );
        assert.strictEqual(
          arcs.some((a) => a[0] === 820 && a[1] === 260 && a[2] === 44),
          true
        );
        assert.strictEqual(
          arcs.some((a) => a[0] === 880 && a[1] === 420 && a[2] === 52),
          true
        );
        assert.strictEqual(
          arcs.some((a) => a[0] === 930 && a[1] === 550 && a[2] === 60),
          true
        );
        assert.strictEqual(ctx.frames.pending().length, 0);
        assert.deepStrictEqual(
          Object.keys(dom.canvas.listeners).sort(),
          ["pointercancel", "pointerdown", "pointermove", "pointerup"]
        );

        dispatch(dom.canvas, "pointerdown", pointerEvent(1, 800, 260));
        dispatch(dom.canvas, "pointermove", pointerEvent(1, 650, 300));
        dispatch(dom.canvas, "pointermove", pointerEvent(1, 500, 360));
        dispatch(dom.canvas, "pointerup", pointerEvent(1, 285, 420));
        snap = ctx.YoungWhale.getSnapshot();
        assert.deepStrictEqual(plain(snap.completedDebrisIds), []);
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(snap.inputLocked, true);
        assert.strictEqual(snap.connected, true);
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-feedback"), "success");
        assert.strictEqual(
          dom.rescueOverlay.classList.contains("ocean-rescue-young-whale-success"),
          true
        );
        assert.strictEqual(dom.rescueProgress.textContent, "Debris 1 of 3");
        assert.strictEqual(
          dom.rescueInstruction.textContent,
          "Drag from the debris to the GUP hook!"
        );
        runSuccessFeedback(ctx);
        snap = ctx.YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.strictEqual(snap.connected, true);
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(snap.helpLevel, 0);
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-stage"), "towing");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-connected"), "true");
        assert.strictEqual(dom.rescueInstruction.textContent, "Drag the GUP to the safe spot!");
        assert.strictEqual(
          dom.rescueOverlay.classList.contains("ocean-rescue-young-whale-success"),
          false
        );

        dispatch(dom.canvas, "pointerdown", pointerEvent(11, 350, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(11, 300, 390));
        dispatch(dom.canvas, "pointermove", pointerEvent(11, 260, 330));
        dispatch(dom.canvas, "pointermove", pointerEvent(11, 220, 270));
        dispatch(dom.canvas, "pointerup", pointerEvent(11, 200, 220));
        snap = ctx.YoungWhale.getSnapshot();
        assert.deepStrictEqual(plain(snap.completedDebrisIds), ["debris-1"]);
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(
          dom.rescueProgress.textContent,
          "Good work, Aiden! Two pieces left. The whale knows we\u2019re here."
        );
        assert.strictEqual(
          dom.statusEl.textContent,
          "Good work, Aiden! Two pieces left. The whale knows we\u2019re here."
        );
        runSuccessFeedback(ctx);
        snap = ctx.YoungWhale.getSnapshot();
        assert.strictEqual(snap.activeDebrisId, "debris-2");
        assert.strictEqual(snap.stage, "connection");
        assert.strictEqual(snap.connected, false);
        assert.strictEqual(snap.feedback, null);
        assert.strictEqual(snap.inputLocked, false);
        assert.strictEqual(snap.helpLevel, 0);
        assert.strictEqual(dom.rescueProgress.textContent, "Debris 2 of 3");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-debris-id"), "debris-2");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-completed-count"), "1");
        assert.strictEqual(dom.rescueInstruction.textContent, "Drag from the debris to the GUP hook!");

        dispatch(dom.canvas, "pointerdown", pointerEvent(21, 850, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(21, 700, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(21, 500, 420));
        dispatch(dom.canvas, "pointerup", pointerEvent(21, 280, 420));
        runSuccessFeedback(ctx);
        assert.strictEqual(ctx.YoungWhale.getSnapshot().stage, "towing");

        dispatch(dom.canvas, "pointerdown", pointerEvent(31, 350, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(31, 300, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(31, 250, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(31, 200, 420));
        dispatch(dom.canvas, "pointerup", pointerEvent(31, 180, 420));
        snap = ctx.YoungWhale.getSnapshot();
        assert.deepStrictEqual(
          plain(snap.completedDebrisIds),
          ["debris-1", "debris-2"]
        );
        assert.strictEqual(
          dom.rescueProgress.textContent,
          "Just one more! The whale is moving toward the opening."
        );
        assert.strictEqual(
          dom.statusEl.textContent,
          "Just one more! The whale is moving toward the opening."
        );
        runSuccessFeedback(ctx);
        snap = ctx.YoungWhale.getSnapshot();
        assert.strictEqual(snap.activeDebrisId, "debris-3");
        assert.strictEqual(snap.stage, "connection");
        assert.strictEqual(dom.rescueProgress.textContent, "Debris 3 of 3");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-completed-count"), "2");

        dispatch(dom.canvas, "pointerdown", pointerEvent(41, 890, 555));
        dispatch(dom.canvas, "pointermove", pointerEvent(41, 750, 530));
        dispatch(dom.canvas, "pointermove", pointerEvent(41, 600, 500));
        dispatch(dom.canvas, "pointermove", pointerEvent(41, 450, 460));
        dispatch(dom.canvas, "pointermove", pointerEvent(41, 320, 440));
        dispatch(dom.canvas, "pointerup", pointerEvent(41, 280, 425));
        runSuccessFeedback(ctx);
        assert.strictEqual(ctx.YoungWhale.getSnapshot().stage, "towing");

        dispatch(dom.canvas, "pointerdown", pointerEvent(46, 350, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(46, 300, 470));
        dispatch(dom.canvas, "pointerup", pointerEvent(46, 300, 470));
        snap = ctx.YoungWhale.getSnapshot();
        assert.strictEqual(snap.feedback, "failure");
        assert.strictEqual(snap.helpLevel, 1);
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-help-level"), "1");
        assert.strictEqual(
          dom.rescueProgress.textContent,
          "Try towing debris 3 again"
        );
        runFailureFeedback(ctx);
        snap = ctx.YoungWhale.getSnapshot();
        assert.strictEqual(snap.stage, "towing");
        assert.strictEqual(snap.connected, true);
        assert.strictEqual(snap.inputLocked, false);
        assert.deepStrictEqual(plain(snap.currentGupCenter), { x: 340, y: 420 });
        assert.deepStrictEqual(plain(snap.currentDebrisCenter), { x: 930, y: 550 });
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-help-level"), "1");

        dispatch(dom.canvas, "pointerdown", pointerEvent(51, 350, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(51, 300, 470));
        dispatch(dom.canvas, "pointermove", pointerEvent(51, 250, 520));
        dispatch(dom.canvas, "pointermove", pointerEvent(51, 200, 570));
        dispatch(dom.canvas, "pointerup", pointerEvent(51, 190, 590));
        snap = ctx.YoungWhale.getSnapshot();
        assert.deepStrictEqual(
          plain(snap.completedDebrisIds),
          ["debris-1", "debris-2", "debris-3"]
        );
        assert.strictEqual(snap.feedback, "success");
        assert.strictEqual(
          dom.rescueProgress.textContent,
          "The path is clear! Let\u2019s give the whale room to swim."
        );
        assert.strictEqual(
          dom.statusEl.textContent,
          "The path is clear! Let\u2019s give the whale room to swim."
        );

        const beforeFinalRender = dom.canvas._context.calls.length;

        const finalTimer = timerWithDelay(ctx, 400);
        ctx.timers.run(finalTimer.id);
        snap = ctx.YoungWhale.getSnapshot();
        assert.strictEqual(snap.complete, true);
        assert.strictEqual(snap.active, false);
        assert.strictEqual(snap.activeDebrisId, null);
        assert.strictEqual(snap.stage, null);
        assert.strictEqual(snap.connected, false);
        assert.strictEqual(snap.inputLocked, true);
        assert.deepStrictEqual(
          plain(snap.completedDebrisIds),
          ["debris-1", "debris-2", "debris-3"]
        );
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");

        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "success");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "disabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-active"), "false");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-debris-id"), "");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-stage"), "");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-completed-count"), "3");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-help-level"), "0");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-feedback"), "none");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-connected"), "false");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-complete"), "true");
        assert.strictEqual(
          dom.rescueProgress.textContent,
          "The path is clear! Let\u2019s give the whale room to swim."
        );

        const afterArcs = callArgs(dom.canvas, "arc");
        assert.strictEqual(
          afterArcs.some((a) => a[0] === 680 && a[1] === 30 && a[2] === 44),
          true
        );
        assert.strictEqual(
          afterArcs.some((a) => a[0] === 700 && a[1] === 420 && a[2] === 52),
          true
        );
        assert.strictEqual(
          afterArcs.some((a) => a[0] === 770 && a[1] === 740 && a[2] === 60),
          true
        );
        const afterLabels = fillTextLabels(dom.canvas);
        const finalRenderCalls = dom.canvas._context.calls.slice(beforeFinalRender);
        const finalRenderLabels = finalRenderCalls
          .filter((call) => call[0] === "fillText")
          .map((call) => call[1]);
        assert.strictEqual(finalRenderLabels.includes("Safe spot"), false);
        assert.strictEqual(afterLabels.includes("Safe spot"), true);

        const missionSnap = ctx.Missions.getSnapshot();
        assert.deepStrictEqual(
          plain(missionSnap.completedMissionIds),
          ["sea-turtle", "crab"]
        );
        assert.deepStrictEqual(
          plain(missionSnap.unlockedMissionIds),
          ["sea-turtle", "crab", "young-whale"]
        );
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");

        finalTimer.fn();
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-completed-count"), "3");
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
        assert.strictEqual(ctx.YoungWhale.getSnapshot().active, false);
        assert.strictEqual(dom.rootEl.getAttribute("data-young-whale-active"), null);

        dispatch(dom.canvas, "pointerdown", pointerEvent(99, 800, 260));
        assert.strictEqual(ctx.YoungWhale.getSnapshot().active, false);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_ACTIVE");

        const crabDom = makeBootDom();
        const crabCtx = loadApp(crabDom.document);
        crabCtx.Missions.completeMission("sea-turtle");
        startLaunchToTravel(crabDom, crabCtx, 0, 1);
        runToRescueActive(crabCtx);
        assert.strictEqual(crabCtx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        assert.strictEqual(crabCtx.Crab.getSnapshot().active, true);
        assert.strictEqual(crabCtx.YoungWhale.getSnapshot().active, false);
        assert.strictEqual(crabDom.rootEl.getAttribute("data-young-whale-active"), null);

        const whaleDom = makeBootDom();
        const whaleCtx = loadApp(whaleDom.document);
        whaleCtx.Missions.completeMission("sea-turtle");
        whaleCtx.Missions.completeMission("crab");
        startLaunchToTravel(whaleDom, whaleCtx, 0, 2);
        runToRescueActive(whaleCtx);
        assert.strictEqual(whaleCtx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        assert.strictEqual(whaleCtx.YoungWhale.getSnapshot().active, true);
        assert.strictEqual(whaleCtx.SeaTurtle.getSnapshot().active, false);
        assert.strictEqual(whaleCtx.Crab.getSnapshot().active, false);
        assert.strictEqual(whaleDom.rootEl.getAttribute("data-young-whale-active"), "true");

        const missingYoungWhaleDom = makeBootDom();
        const missingYoungWhaleCtx = loadApp(
          missingYoungWhaleDom.document,
          {},
          { skipYoungWhale: true }
        );
        assert.strictEqual(missingYoungWhaleCtx.YoungWhale, undefined);
        missingYoungWhaleCtx.Missions.completeMission("sea-turtle");
        missingYoungWhaleCtx.Missions.completeMission("crab");
        startLaunchToTravel(missingYoungWhaleDom, missingYoungWhaleCtx, 0, 2);
        runToRescueActive(missingYoungWhaleCtx);
        assert.strictEqual(
          missingYoungWhaleCtx.State.getSnapshot().phase,
          "RESCUE_ACTIVE"
        );
        assert.strictEqual(
          missingYoungWhaleDom.rootEl.getAttribute("data-rescue-phase"),
          "active"
        );
        assert.strictEqual(
          missingYoungWhaleDom.rootEl.getAttribute("data-young-whale-active"),
          null
        );

        const staleDom = makeBootDom();
        const staleCtx = loadApp(staleDom.document);
        staleCtx.Missions.completeMission("sea-turtle");
        staleCtx.Missions.completeMission("crab");
        startLaunchToTravel(staleDom, staleCtx, 0, 2);
        runToRescueActive(staleCtx);
        dispatch(staleDom.canvas, "pointerdown", pointerEvent(1, 800, 260));
        dispatch(staleDom.canvas, "pointermove", pointerEvent(1, 650, 300));
        dispatch(staleDom.canvas, "pointermove", pointerEvent(1, 500, 360));
        dispatch(staleDom.canvas, "pointerup", pointerEvent(1, 285, 420));
        const firstTimer = timerWithDelay(staleCtx, 400);
        const before = JSON.stringify(staleCtx.YoungWhale.getSnapshot());
        firstTimer.fn();
        const after = JSON.stringify(staleCtx.YoungWhale.getSnapshot());
        assert.notStrictEqual(before, after);
        assert.strictEqual(staleCtx.YoungWhale.getSnapshot().stage, "towing");
        firstTimer.fn();
        assert.strictEqual(staleCtx.YoungWhale.getSnapshot().stage, "towing");
        assert.strictEqual(staleCtx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        """
    )
    _assert_node_ok(_run_node(harness))
