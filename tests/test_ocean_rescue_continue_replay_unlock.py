"""Behavioral tests for the Ocean Rescue completion actions and unlock flow.

Every JavaScript assertion runs the real tracked sources (``state.js``,
``missions.js``, ``gups.js``, ``launch.js``, ``travel.js``, ``terrain.js``,
``rescue.js``, ``sea-turtle.js``, ``crab.js``, ``young-whale.js``,
``mission-success.js``, and ``app.js``) through the installed Node runtime in a
fresh VM sandbox using a minimal fake DOM, a fake canvas 2D context, a
deterministic fake timer queue, and a deterministic fake animation-frame queue.
No npm packages, no browser automation, no real-time sleeps, and no separate
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
    const SEA_TURTLE_SOURCE = fs.readFileSync("domains/ocean-rescue/src/sea-turtle.js", "utf8");
    const CRAB_SOURCE = fs.readFileSync("domains/ocean-rescue/src/crab.js", "utf8");
    const YOUNG_WHALE_SOURCE = fs.readFileSync("domains/ocean-rescue/src/young-whale.js", "utf8");
    const MISSION_SUCCESS_SOURCE = fs.readFileSync("domains/ocean-rescue/src/mission-success.js", "utf8");
    const POINTER_INPUT_SOURCE = fs.readFileSync("domains/ocean-rescue/src/pointer-input.js", "utf8");
    const APP_SOURCE = fs.readFileSync("domains/ocean-rescue/src/app.js", "utf8");

    function plain(value) {
      return JSON.parse(JSON.stringify(value));
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

    function makeElement(tagName, options) {
      const opts = options || {};
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
      };
      if (!opts.noScroll) {
        el.scrollIntoView = function () {
          this.scrollIntoViewCalls += 1;
        };
      }
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

    function makeDocument(elements, options) {
      const opts = options || {};
      return {
        elements,
        domListenerCount: 0,
        domLoadedHandler: null,
        getElementById(id) {
          return Object.prototype.hasOwnProperty.call(elements, id)
            ? elements[id]
            : null;
        },
        createElement(tagName) {
          return makeElement(tagName, { noScroll: opts.noElementScroll });
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
      const includeMissionSuccess = options.includeMissionSuccess === true;
      const includeCompleteActions = options.includeCompleteActions !== false;
      const noElementScroll = options.noElementScroll === true;
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
      const canvas = makeCanvasElement(undefined);

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

      const dom = {
        elements,
        document: makeDocument(elements, { noElementScroll }),
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

      if (includeMissionSuccess) {
        const successSection = makeElement("section");
        successSection.hidden = true;
        const successTitle = makeElement("h2");
        const successVisual = makeElement("div");
        const successAnimal = makeElement("div");
        const successSecondaryAnimal = makeElement("div");
        const successDestination = makeElement("div");
        const successEcology = makeElement("p");
        successEcology.hidden = true;
        const successNarration = makeElement("div");
        successNarration.hidden = true;
        const successSpeaker = makeElement("p");
        const successLine = makeElement("p");
        const successTapHelp = makeElement("p");
        successTapHelp.hidden = true;
        const completeCard = makeElement("div");
        completeCard.hidden = true;
        const completeName = makeElement("p");
        const completeEcology = makeElement("p");

        successSection.appendChild(successTitle);
        successVisual.appendChild(successAnimal);
        successVisual.appendChild(successSecondaryAnimal);
        successVisual.appendChild(successDestination);
        successSection.appendChild(successVisual);
        successSection.appendChild(successEcology);
        successNarration.appendChild(successSpeaker);
        successNarration.appendChild(successLine);
        successSection.appendChild(successNarration);
        successSection.appendChild(successTapHelp);
        completeCard.appendChild(completeName);
        completeCard.appendChild(completeEcology);
        successSection.appendChild(completeCard);
        rootEl.appendChild(successSection);

        elements["ocean-rescue-mission-success"] = successSection;
        elements["ocean-rescue-mission-success-title"] = successTitle;
        elements["ocean-rescue-mission-success-visual"] = successVisual;
        elements["ocean-rescue-mission-success-animal"] = successAnimal;
        elements["ocean-rescue-mission-success-secondary-animal"] = successSecondaryAnimal;
        elements["ocean-rescue-mission-success-destination"] = successDestination;
        elements["ocean-rescue-mission-success-ecology"] = successEcology;
        elements["ocean-rescue-mission-success-narration"] = successNarration;
        elements["ocean-rescue-mission-success-speaker"] = successSpeaker;
        elements["ocean-rescue-mission-success-line"] = successLine;
        elements["ocean-rescue-mission-success-tap-help"] = successTapHelp;
        elements["ocean-rescue-mission-complete-card"] = completeCard;
        elements["ocean-rescue-mission-complete-name"] = completeName;
        elements["ocean-rescue-mission-complete-ecology"] = completeEcology;

        dom.missionSuccessSection = successSection;
        dom.missionSuccessTitle = successTitle;
        dom.missionSuccessVisual = successVisual;
        dom.missionSuccessAnimal = successAnimal;
        dom.missionSuccessSecondaryAnimal = successSecondaryAnimal;
        dom.missionSuccessDestination = successDestination;
        dom.missionSuccessEcology = successEcology;
        dom.missionSuccessNarration = successNarration;
        dom.missionSuccessSpeaker = successSpeaker;
        dom.missionSuccessLine = successLine;
        dom.missionSuccessTapHelp = successTapHelp;
        dom.completeCard = completeCard;
        dom.completeName = completeName;
        dom.completeEcology = completeEcology;

        if (includeCompleteActions) {
          const completeUnlock = makeElement("div");
          completeUnlock.hidden = true;
          completeUnlock.textContent = "Next Mission Unlocked!";
          const completeUnlockName = makeElement("p");
          const completeActions = makeElement("div");
          const completeContinue = makeElement("button");
          completeContinue.textContent = "Continue";
          const completeReplay = makeElement("button");
          completeReplay.textContent = "Replay";

          completeUnlock.appendChild(completeUnlockName);
          completeCard.appendChild(completeUnlock);
          completeCard.appendChild(completeActions);
          completeActions.appendChild(completeContinue);
          completeActions.appendChild(completeReplay);

          elements["ocean-rescue-mission-complete-unlock"] = completeUnlock;
          elements["ocean-rescue-mission-complete-unlock-name"] = completeUnlockName;
          elements["ocean-rescue-mission-complete-actions"] = completeActions;
          elements["ocean-rescue-mission-complete-continue"] = completeContinue;
          elements["ocean-rescue-mission-complete-replay"] = completeReplay;

          dom.completeUnlock = completeUnlock;
          dom.completeUnlockName = completeUnlockName;
          dom.completeActions = completeActions;
          dom.completeContinue = completeContinue;
          dom.completeReplay = completeReplay;
        }
      }

      return dom;
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
      vm.runInContext(RESCUE_SOURCE, sandbox, { filename: "rescue.js" });
      vm.runInContext(SEA_TURTLE_SOURCE, sandbox, { filename: "sea-turtle.js" });
      vm.runInContext(CRAB_SOURCE, sandbox, { filename: "crab.js" });
      vm.runInContext(YOUNG_WHALE_SOURCE, sandbox, { filename: "young-whale.js" });
      vm.runInContext(MISSION_SUCCESS_SOURCE, sandbox, {
        filename: "mission-success.js",
      });
      vm.runInContext(POINTER_INPUT_SOURCE, sandbox, { filename: "pointer-input.js" });
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
        MissionSuccess: OceanRescue.MissionSuccess,
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

    function runToRescueActiveClean(ctx) {
      runToRescueActive(ctx);
      const goal = timerWithDelay(ctx, 3000);
      ctx.timers.run(goal.id);
    }

    function completeRopeByTrace(dom, ctx, pointerId, start, moves, end) {
      dispatch(dom.canvas, "pointerdown", pointerEvent(pointerId, start.x, start.y));
      for (const point of moves) {
        dispatch(dom.canvas, "pointermove", pointerEvent(pointerId, point.x, point.y));
      }
      dispatch(dom.canvas, "pointerup", pointerEvent(pointerId, end.x, end.y));
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

    function completeMissionInteraction(dom, ctx, missionId) {
      if (missionId === "sea-turtle") {
        completeRopeByTrace(dom, ctx, 1, { x: 800, y: 305 }, [
          { x: 900, y: 315 },
          { x: 1000, y: 322 }
        ], { x: 1035, y: 328 });
        runSuccessFeedback(ctx);
        dispatch(dom.canvas, "pointerdown", pointerEvent(11, 780, 425));
        dispatch(dom.canvas, "pointerup", pointerEvent(11, 780, 425));
        dispatch(dom.canvas, "pointerdown", pointerEvent(12, 1040, 438));
        dispatch(dom.canvas, "pointerup", pointerEvent(12, 1040, 438));
        runSuccessFeedback(ctx);
        completeRopeByTrace(dom, ctx, 21, { x: 810, y: 545 }, [
          { x: 900, y: 550 },
          { x: 1000, y: 560 }
        ], { x: 1025, y: 568 });
        runSuccessFeedback(ctx);
        return;
      }
      if (missionId === "crab") {
        completeRockByHoldDrag(dom, ctx, 1, { x: 900, y: 440 }, { x: 310, y: 290 });
        runSuccessFeedback(ctx);
        dispatch(dom.canvas, "pointerdown", pointerEvent(11, 1060, 510));
        dispatch(dom.canvas, "pointerup", pointerEvent(11, 1060, 510));
        dispatch(dom.canvas, "pointerdown", pointerEvent(12, 310, 290));
        dispatch(dom.canvas, "pointerup", pointerEvent(12, 310, 290));
        runSuccessFeedback(ctx);
        completeRockByHoldDrag(dom, ctx, 22, { x: 930, y: 575 }, { x: 330, y: 215 });
        runSuccessFeedback(ctx);
        return;
      }
      if (missionId === "young-whale") {
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
        runSuccessFeedback(ctx);
        dispatch(dom.canvas, "pointerdown", pointerEvent(21, 850, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(21, 700, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(21, 500, 420));
        dispatch(dom.canvas, "pointerup", pointerEvent(21, 280, 420));
        runSuccessFeedback(ctx);
        dispatch(dom.canvas, "pointerdown", pointerEvent(31, 350, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(31, 300, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(31, 250, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(31, 200, 420));
        dispatch(dom.canvas, "pointerup", pointerEvent(31, 180, 420));
        runSuccessFeedback(ctx);
        dispatch(dom.canvas, "pointerdown", pointerEvent(41, 890, 555));
        dispatch(dom.canvas, "pointermove", pointerEvent(41, 750, 530));
        dispatch(dom.canvas, "pointermove", pointerEvent(41, 600, 500));
        dispatch(dom.canvas, "pointermove", pointerEvent(41, 450, 460));
        dispatch(dom.canvas, "pointermove", pointerEvent(41, 320, 440));
        dispatch(dom.canvas, "pointerup", pointerEvent(41, 280, 425));
        runSuccessFeedback(ctx);
        dispatch(dom.canvas, "pointerdown", pointerEvent(51, 350, 420));
        dispatch(dom.canvas, "pointermove", pointerEvent(51, 300, 470));
        dispatch(dom.canvas, "pointermove", pointerEvent(51, 250, 520));
        dispatch(dom.canvas, "pointermove", pointerEvent(51, 200, 570));
        dispatch(dom.canvas, "pointerup", pointerEvent(51, 190, 590));
        runSuccessFeedback(ctx);
        return;
      }
      throw new Error("unknown mission " + missionId);
    }

    function runSeaTurtleToRescueSuccess(dom, ctx) {
      startLaunchToTravel(dom, ctx, 0, 0);
      runToRescueActiveClean(ctx);
      completeMissionInteraction(dom, ctx, "sea-turtle");
      assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
    }

    function runCrabToRescueSuccess(dom, ctx) {
      ctx.Missions.completeMission("sea-turtle");
      startLaunchToTravel(dom, ctx, 0, 1);
      runToRescueActiveClean(ctx);
      completeMissionInteraction(dom, ctx, "crab");
      assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
    }

    function runYoungWhaleToRescueSuccess(dom, ctx) {
      ctx.Missions.completeMission("sea-turtle");
      ctx.Missions.completeMission("crab");
      startLaunchToTravel(dom, ctx, 0, 2);
      runToRescueActiveClean(ctx);
      completeMissionInteraction(dom, ctx, "young-whale");
      assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
    }

    function runReplayFromLaunchToRescueSuccess(dom, ctx, missionId) {
      const launchTimer = timerWithDelay(ctx, 6000);
      ctx.timers.run(launchTimer.id);
      assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
      runToRescueActiveClean(ctx);
      completeMissionInteraction(dom, ctx, missionId);
      assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
    }

    function advanceToNarration1(ctx) {
      const anim = timerWithDelay(ctx, 4000);
      ctx.timers.run(anim.id);
      const eco = timerWithDelay(ctx, 3000);
      ctx.timers.run(eco.id);
    }

    function advanceToNarration2(dom, ctx) {
      advanceToNarration1(ctx);
      const n1 = timerWithDelay(ctx, 3000);
      ctx.timers.run(n1.id);
      assert.strictEqual(
        dom.rootEl.getAttribute("data-mission-success-stage"),
        "narration-2"
      );
      return timerWithDelay(ctx, 3000);
    }

    function advanceFromRescueSuccessToComplete(dom, ctx) {
      const n2 = advanceToNarration2(dom, ctx);
      ctx.timers.run(n2.id);
      assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_COMPLETE");
    }

    function collectVisibleText(el) {
      if (el.hidden) {
        return [];
      }
      let parts = [];
      if (typeof el.textContent === "string" && el.textContent.length > 0) {
        parts.push(el.textContent);
      }
      for (const child of el.children) {
        parts = parts.concat(collectVisibleText(child));
      }
      return parts;
    }

    function hasNewBadge(card) {
      return card.children.some(
        (child) => child.className === "ocean-rescue-mission-new"
      );
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


def test_first_sea_turtle_completion_unlocks_crab_once() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom({ includeMissionSuccess: true });
        const ctx = loadApp(dom.document);
        runSeaTurtleToRescueSuccess(dom, ctx);
        const n2 = advanceToNarration2(dom, ctx);
        ctx.timers.run(n2.id);
        assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_COMPLETE");

        assert.deepStrictEqual(
          plain(ctx.Missions.getSnapshot().completedMissionIds),
          ["sea-turtle"]
        );
        assert.deepStrictEqual(
          plain(ctx.Missions.getSnapshot().unlockedMissionIds),
          ["sea-turtle", "crab"]
        );
        assert.deepStrictEqual(
          plain(ctx.Missions.getSnapshot().newMissionIds),
          ["crab"]
        );

        assert.strictEqual(dom.completeUnlock.hidden, false);
        assert.strictEqual(dom.completeUnlockName.textContent, "Crab Rescue");
        const visibleText = collectVisibleText(dom.missionSuccessSection).join(" ");
        assert.strictEqual(/next mission unlocked/i.test(visibleText), true);

        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-completion-recorded"),
          "true"
        );
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-first-completion"),
          "true"
        );
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-newly-unlocked-id"),
          "crab"
        );
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-continue-focus-id"),
          "crab"
        );
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-complete-action"),
          "ready"
        );
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-complete-ready"),
          "true"
        );
        assert.strictEqual(dom.completeContinue.disabled, false);
        assert.strictEqual(dom.completeReplay.disabled, false);
        assert.strictEqual(dom.completeContinue.textContent, "Continue");
        assert.strictEqual(dom.completeReplay.textContent, "Replay");

        n2.fn();
        assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_COMPLETE");
        assert.deepStrictEqual(
          plain(ctx.Missions.getSnapshot().completedMissionIds),
          ["sea-turtle"]
        );
        assert.deepStrictEqual(
          plain(ctx.Missions.getSnapshot().unlockedMissionIds),
          ["sea-turtle", "crab"]
        );
        assert.deepStrictEqual(
          plain(ctx.Missions.getSnapshot().newMissionIds),
          ["crab"]
        );
        """
    )
    _assert_node_ok(_run_node(harness))


def test_continue_returns_to_mission_select_and_focuses_new_card() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom({ includeMissionSuccess: true });
        const ctx = loadApp(dom.document);
        runSeaTurtleToRescueSuccess(dom, ctx);
        advanceFromRescueSuccessToComplete(dom, ctx);

        dom.completeContinue.click();
        assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_SELECT");
        assert.strictEqual(dom.statusEl.textContent, "Choose a mission");
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-complete-action"),
          "continue"
        );
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "inactive");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "disabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-complete-ready"), null);
        assert.strictEqual(dom.missionSuccessSection.hidden, true);
        assert.strictEqual(dom.completeCard.hidden, true);
        assert.strictEqual(dom.gupSection.hidden, true);

        const seaCard = dom.missionList.children[0];
        const seaStatus = seaCard.children[3];
        assert.strictEqual(seaStatus.textContent, "Completed");
        assert.strictEqual(seaCard.scrollIntoViewCalls, 0);

        const crabCard = dom.missionList.children[1];
        assert.strictEqual(crabCard.scrollIntoViewCalls, 1);
        assert.strictEqual(crabCard.children[3].textContent, "Available");
        assert.strictEqual(hasNewBadge(crabCard), true);
        assert.strictEqual(crabCard.children[4].textContent, "New!");

        const whaleCard = dom.missionList.children[2];
        assert.strictEqual(whaleCard.scrollIntoViewCalls, 0);
        assert.strictEqual(whaleCard.children[3].textContent, "Locked");

        assert.deepStrictEqual(
          plain(ctx.Missions.getSnapshot().newMissionIds),
          ["crab"]
        );
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-complete-ready"),
          null
        );
        """
    )
    _assert_node_ok(_run_node(harness))


def test_new_marker_is_consumed_only_when_card_is_selected() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom({ includeMissionSuccess: true });
        const ctx = loadApp(dom.document);
        runSeaTurtleToRescueSuccess(dom, ctx);
        advanceFromRescueSuccessToComplete(dom, ctx);

        dom.completeContinue.click();
        assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_SELECT");
        assert.deepStrictEqual(
          plain(ctx.Missions.getSnapshot().newMissionIds),
          ["crab"]
        );
        assert.strictEqual(hasNewBadge(dom.missionList.children[1]), true);

        dom.missionList.children[1].click();
        assert.strictEqual(ctx.State.getSnapshot().phase, "GUP_SELECT");
        assert.strictEqual(dom.gupSection.hidden, false);
        assert.strictEqual(dom.gupMission.textContent, "Mission: Crab Rescue");
        assert.strictEqual(
          ctx.Missions.getSnapshot().selectedMissionId,
          "crab"
        );
        assert.deepStrictEqual(
          plain(ctx.Missions.getSnapshot().newMissionIds),
          []
        );
        """
    )
    _assert_node_ok(_run_node(harness))


def test_replay_keeps_same_mission_and_last_gup() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom({ includeMissionSuccess: true });
        const ctx = loadApp(dom.document);
        dom.document.domLoadedHandler();
        assert.strictEqual(ctx.App.boot(), true);
        dom.missionList.children[0].click();
        dom.gupList.children[2].click();
        dom.gupLaunch.click();
        assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
        assert.strictEqual(ctx.Gups.getSnapshot().lastGupId, "gup-x");
        ctx.timers.run(timerWithDelay(ctx, 6000).id);
        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        runToRescueActiveClean(ctx);
        completeMissionInteraction(dom, ctx, "sea-turtle");
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
        advanceFromRescueSuccessToComplete(dom, ctx);
        assert.strictEqual(ctx.Gups.getSnapshot().lastGupId, "gup-x");

        const progressionBefore = JSON.stringify(ctx.Missions.getSnapshot());
        dom.completeReplay.click();
        assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
        assert.strictEqual(dom.gupSection.hidden, true);
        assert.strictEqual(
          dom.rootEl.getAttribute("data-launch-mission-id"),
          "sea-turtle"
        );
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-gup-id"), "gup-x");
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-ready"), "true");
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-complete-action"),
          "replay"
        );
        const launchTimer = timerWithDelay(ctx, 6000);
        assert.strictEqual(launchTimer.delay, 6000);
        assert.strictEqual(ctx.timers.pending().length, 1);
        assert.strictEqual(JSON.stringify(ctx.Missions.getSnapshot()), progressionBefore);
        assert.strictEqual(dom.completeContinue.disabled, true);
        assert.strictEqual(dom.completeReplay.disabled, true);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_replay_completion_does_not_repeat_unlock_banner() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom({ includeMissionSuccess: true });
        const ctx = loadApp(dom.document);
        runSeaTurtleToRescueSuccess(dom, ctx);
        advanceFromRescueSuccessToComplete(dom, ctx);
        assert.strictEqual(dom.completeUnlock.hidden, false);
        assert.strictEqual(dom.completeUnlockName.textContent, "Crab Rescue");

        dom.completeReplay.click();
        assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
        runReplayFromLaunchToRescueSuccess(dom, ctx, "sea-turtle");
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
        advanceFromRescueSuccessToComplete(dom, ctx);
        assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_COMPLETE");

        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-first-completion"),
          "false"
        );
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-newly-unlocked-id"),
          ""
        );
        assert.strictEqual(dom.completeUnlock.hidden, true);
        assert.strictEqual(dom.completeUnlockName.textContent, "");
        assert.deepStrictEqual(
          plain(ctx.Missions.getSnapshot().completedMissionIds),
          ["sea-turtle"]
        );
        assert.deepStrictEqual(
          plain(ctx.Missions.getSnapshot().newMissionIds),
          ["crab"]
        );
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-continue-focus-id"),
          "crab"
        );

        dom.completeContinue.click();
        assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_SELECT");
        assert.strictEqual(hasNewBadge(dom.missionList.children[1]), true);
        assert.strictEqual(dom.missionList.children[1].scrollIntoViewCalls, 1);
        assert.deepStrictEqual(
          plain(ctx.Missions.getSnapshot().newMissionIds),
          ["crab"]
        );
        """
    )
    _assert_node_ok(_run_node(harness))


def test_crab_unlocks_whale_and_final_mission_unlocks_nothing() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const crabDom = makeBootDom({ includeMissionSuccess: true });
        const crabCtx = loadApp(crabDom.document);
        runCrabToRescueSuccess(crabDom, crabCtx);
        advanceFromRescueSuccessToComplete(crabDom, crabCtx);
        assert.strictEqual(
          crabCtx.State.getSnapshot().phase,
          "MISSION_COMPLETE"
        );
        assert.deepStrictEqual(
          plain(crabCtx.Missions.getSnapshot().completedMissionIds),
          ["sea-turtle", "crab"]
        );
        assert.deepStrictEqual(
          plain(crabCtx.Missions.getSnapshot().unlockedMissionIds),
          ["sea-turtle", "crab", "young-whale"]
        );
        assert.deepStrictEqual(
          plain(crabCtx.Missions.getSnapshot().newMissionIds),
          ["young-whale"]
        );
        assert.strictEqual(crabDom.completeUnlock.hidden, false);
        assert.strictEqual(
          crabDom.completeUnlockName.textContent,
          "Young Whale Rescue"
        );
        assert.strictEqual(
          crabDom.rootEl.getAttribute("data-mission-newly-unlocked-id"),
          "young-whale"
        );

        const whaleDom = makeBootDom({ includeMissionSuccess: true });
        const whaleCtx = loadApp(whaleDom.document);
        runYoungWhaleToRescueSuccess(whaleDom, whaleCtx);
        advanceFromRescueSuccessToComplete(whaleDom, whaleCtx);
        assert.strictEqual(
          whaleCtx.State.getSnapshot().phase,
          "MISSION_COMPLETE"
        );
        assert.strictEqual(whaleDom.completeUnlock.hidden, true);
        assert.strictEqual(
          whaleDom.rootEl.getAttribute("data-mission-newly-unlocked-id"),
          ""
        );
        assert.strictEqual(
          whaleDom.rootEl.getAttribute("data-mission-first-completion"),
          "true"
        );
        assert.deepStrictEqual(
          plain(whaleCtx.Missions.getSnapshot().completedMissionIds),
          ["sea-turtle", "crab", "young-whale"]
        );
        assert.deepStrictEqual(
          plain(whaleCtx.Missions.getSnapshot().unlockedMissionIds),
          ["sea-turtle", "crab", "young-whale"]
        );
        assert.strictEqual(whaleCtx.Missions.Catalog.length, 3);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_action_reentrancy_and_stale_events_are_idempotent() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const continueDom = makeBootDom({ includeMissionSuccess: true });
        const continueCtx = loadApp(continueDom.document);
        runSeaTurtleToRescueSuccess(continueDom, continueCtx);
        advanceFromRescueSuccessToComplete(continueDom, continueCtx);
        continueDom.completeContinue.click();
        continueDom.completeContinue.click();
        assert.strictEqual(
          continueCtx.State.getSnapshot().phase,
          "MISSION_SELECT"
        );
        assert.strictEqual(continueDom.completeContinue.disabled, true);
        assert.strictEqual(continueDom.completeReplay.disabled, true);
        assert.deepStrictEqual(
          plain(continueCtx.Missions.getSnapshot().completedMissionIds),
          ["sea-turtle"]
        );
        assert.deepStrictEqual(
          plain(continueCtx.Missions.getSnapshot().newMissionIds),
          ["crab"]
        );

        const replayDom = makeBootDom({ includeMissionSuccess: true });
        const replayCtx = loadApp(replayDom.document);
        runSeaTurtleToRescueSuccess(replayDom, replayCtx);
        advanceFromRescueSuccessToComplete(replayDom, replayCtx);
        replayDom.completeReplay.click();
        replayDom.completeReplay.click();
        assert.strictEqual(replayCtx.State.getSnapshot().phase, "LAUNCH");
        assert.strictEqual(replayDom.completeContinue.disabled, true);
        assert.strictEqual(replayDom.completeReplay.disabled, true);
        assert.strictEqual(replayCtx.timers.pending().length, 1);
        assert.strictEqual(replayCtx.timers.pending()[0].delay, 6000);
        assert.deepStrictEqual(
          plain(replayCtx.Missions.getSnapshot().completedMissionIds),
          ["sea-turtle"]
        );

        const continueThenReplay = makeBootDom({ includeMissionSuccess: true });
        const continueThenReplayCtx = loadApp(continueThenReplay.document);
        runSeaTurtleToRescueSuccess(continueThenReplay, continueThenReplayCtx);
        advanceFromRescueSuccessToComplete(continueThenReplay, continueThenReplayCtx);
        continueThenReplay.completeContinue.click();
        continueThenReplay.completeReplay.click();
        assert.strictEqual(
          continueThenReplayCtx.State.getSnapshot().phase,
          "MISSION_SELECT"
        );

        const replayThenContinue = makeBootDom({ includeMissionSuccess: true });
        const replayThenContinueCtx = loadApp(replayThenContinue.document);
        runSeaTurtleToRescueSuccess(replayThenContinue, replayThenContinueCtx);
        advanceFromRescueSuccessToComplete(replayThenContinue, replayThenContinueCtx);
        replayThenContinue.completeReplay.click();
        replayThenContinue.completeContinue.click();
        assert.strictEqual(
          replayThenContinueCtx.State.getSnapshot().phase,
          "LAUNCH"
        );
        """
    )
    _assert_node_ok(_run_node(harness))


def test_optional_action_and_launch_dom_boundaries_are_safe() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const noActions = makeBootDom({
          includeMissionSuccess: true,
          includeCompleteActions: false,
        });
        const noActionsCtx = loadApp(noActions.document);
        runSeaTurtleToRescueSuccess(noActions, noActionsCtx);
        advanceFromRescueSuccessToComplete(noActions, noActionsCtx);
        assert.strictEqual(noActionsCtx.State.getSnapshot().phase, "MISSION_COMPLETE");
        assert.deepStrictEqual(
          plain(noActionsCtx.Missions.getSnapshot().completedMissionIds),
          ["sea-turtle"]
        );
        assert.deepStrictEqual(
          plain(noActionsCtx.Missions.getSnapshot().unlockedMissionIds),
          ["sea-turtle", "crab"]
        );
        assert.deepStrictEqual(
          plain(noActionsCtx.Missions.getSnapshot().newMissionIds),
          ["crab"]
        );
        assert.strictEqual(
          noActions.rootEl.getAttribute("data-mission-completion-recorded"),
          "true"
        );
        assert.strictEqual(
          noActions.rootEl.getAttribute("data-mission-complete-ready"),
          "true"
        );

        const noScroll = makeBootDom({
          includeMissionSuccess: true,
          noElementScroll: true,
        });
        const noScrollCtx = loadApp(noScroll.document);
        runSeaTurtleToRescueSuccess(noScroll, noScrollCtx);
        advanceFromRescueSuccessToComplete(noScroll, noScrollCtx);
        noScroll.completeContinue.click();
        assert.strictEqual(noScrollCtx.State.getSnapshot().phase, "MISSION_SELECT");
        assert.strictEqual(noScroll.statusEl.textContent, "Choose a mission");
        assert.deepStrictEqual(
          plain(noScrollCtx.Missions.getSnapshot().newMissionIds),
          ["crab"]
        );

        const noLaunch = makeBootDom({ includeMissionSuccess: true });
        const noLaunchCtx = loadApp(noLaunch.document);
        runSeaTurtleToRescueSuccess(noLaunch, noLaunchCtx);
        advanceFromRescueSuccessToComplete(noLaunch, noLaunchCtx);
        noLaunch.elements["ocean-rescue-launch"] = null;
        noLaunch.elements["ocean-rescue-launch-gup-name"] = null;
        noLaunch.elements["ocean-rescue-launch-companion"] = null;
        noLaunch.elements["ocean-rescue-launch-briefing"] = null;
        noLaunch.elements["ocean-rescue-goal-banner"] = null;
        noLaunch.completeReplay.click();
        assert.strictEqual(noLaunchCtx.State.getSnapshot().phase, "LAUNCH");
        assert.strictEqual(
          noLaunch.rootEl.getAttribute("data-launch-mission-id"),
          "sea-turtle"
        );
        assert.strictEqual(
          noLaunch.rootEl.getAttribute("data-launch-gup-id"),
          "gup-c"
        );
        assert.strictEqual(noLaunch.rootEl.getAttribute("data-launch-ready"), "true");
        assert.strictEqual(
          noLaunch.rootEl.getAttribute("data-mission-complete-action"),
          "replay"
        );
        assert.strictEqual(noLaunchCtx.timers.pending().length, 0);

        const noTimers = makeBootDom({ includeMissionSuccess: true });
        const noTimersCtx = loadApp(noTimers.document);
        runSeaTurtleToRescueSuccess(noTimers, noTimersCtx);
        advanceFromRescueSuccessToComplete(noTimers, noTimersCtx);
        noTimersCtx.sandbox.window.setTimeout = undefined;
        noTimersCtx.sandbox.window.clearTimeout = undefined;
        noTimers.completeReplay.click();
        assert.strictEqual(noTimersCtx.State.getSnapshot().phase, "LAUNCH");
        assert.strictEqual(noTimers.rootEl.getAttribute("data-launch-ready"), "true");
        assert.strictEqual(
          noTimers.rootEl.getAttribute("data-launch-gup-id"),
          "gup-c"
        );

        const publicApp = makeBootDom({ includeMissionSuccess: true });
        const publicAppCtx = loadApp(publicApp.document);
        const requiredAppMethods = [
          "backToMissionSelect",
          "boot",
          "launchSelectedGup",
          "renderGupSelect",
          "renderMissionSelect",
          "selectGup",
          "selectMission"
        ];
        for (const m of requiredAppMethods) {
          assert.strictEqual(typeof publicAppCtx.App[m], "function", `App.${m} missing`);
        }
        """
    )
    _assert_node_ok(_run_node(harness))
