"""Behavioral tests for the Ocean Rescue mission success presentation.

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
NODE_BIN = shutil.which("node")
if NODE_BIN is None:
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
    const APP_SOURCE = fs.readFileSync("domains/ocean-rescue/src/app.js", "utf8");

    function plain(value) {
      return JSON.parse(JSON.stringify(value));
    }

    function freshMissionSuccess() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(MISSION_SUCCESS_SOURCE, sandbox, {
        filename: "mission-success.js",
      });
      return sandbox.window.OceanRescue.MissionSuccess;
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
      const includeMissionSuccess = options.includeMissionSuccess === true;
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

      const dom = {
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
        const completeUnlock = makeElement("div");
        completeUnlock.hidden = true;
        completeUnlock.textContent = "Next Mission Unlocked!";
        const completeUnlockName = makeElement("p");
        const completeActions = makeElement("div");
        const completeContinue = makeElement("button");
        completeContinue.textContent = "Continue";
        const completeReplay = makeElement("button");
        completeReplay.textContent = "Replay";

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
        completeUnlock.appendChild(completeUnlockName);
        completeCard.appendChild(completeName);
        completeCard.appendChild(completeEcology);
        completeCard.appendChild(completeUnlock);
        completeCard.appendChild(completeActions);
        completeActions.appendChild(completeContinue);
        completeActions.appendChild(completeReplay);
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
        elements["ocean-rescue-mission-complete-unlock"] = completeUnlock;
        elements["ocean-rescue-mission-complete-unlock-name"] = completeUnlockName;
        elements["ocean-rescue-mission-complete-actions"] = completeActions;
        elements["ocean-rescue-mission-complete-continue"] = completeContinue;
        elements["ocean-rescue-mission-complete-replay"] = completeReplay;

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
        dom.completeUnlock = completeUnlock;
        dom.completeUnlockName = completeUnlockName;
        dom.completeActions = completeActions;
        dom.completeContinue = completeContinue;
        dom.completeReplay = completeReplay;
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
      if (!opts.skipMissionSuccess) {
        vm.runInContext(MISSION_SUCCESS_SOURCE, sandbox, {
          filename: "mission-success.js",
        });
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

    function runSeaTurtleToFinalFeedbackScheduled(dom, ctx) {
      startLaunchToTravel(dom, ctx, 0);
      runToRescueActiveClean(ctx);
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
    }

    function runSeaTurtleToRescueSuccess(dom, ctx) {
      runSeaTurtleToFinalFeedbackScheduled(dom, ctx);
      runSuccessFeedback(ctx);
      assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
    }

    function runCrabToRescueSuccess(dom, ctx) {
      ctx.Missions.completeMission("sea-turtle");
      startLaunchToTravel(dom, ctx, 0, 1);
      runToRescueActiveClean(ctx);
      completeRockByHoldDrag(dom, ctx, 1, { x: 900, y: 440 }, { x: 310, y: 290 });
      runSuccessFeedback(ctx);
      dispatch(dom.canvas, "pointerdown", pointerEvent(11, 1060, 510));
      dispatch(dom.canvas, "pointerup", pointerEvent(11, 1060, 510));
      dispatch(dom.canvas, "pointerdown", pointerEvent(12, 310, 290));
      dispatch(dom.canvas, "pointerup", pointerEvent(12, 310, 290));
      runSuccessFeedback(ctx);
      completeRockByHoldDrag(dom, ctx, 22, { x: 930, y: 575 }, { x: 330, y: 215 });
      runSuccessFeedback(ctx);
      assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
    }

    function runYoungWhaleToRescueSuccess(dom, ctx) {
      ctx.Missions.completeMission("sea-turtle");
      ctx.Missions.completeMission("crab");
      startLaunchToTravel(dom, ctx, 0, 2);
      runToRescueActiveClean(ctx);
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
      assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
    }

    function advanceToNarration1(ctx) {
      const anim = timerWithDelay(ctx, 4000);
      ctx.timers.run(anim.id);
      const eco = timerWithDelay(ctx, 3000);
      ctx.timers.run(eco.id);
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

    function hasButton(node) {
      if (node.tagName === "button") {
        return true;
      }
      return node.children.some(hasButton);
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


def test_mission_success_catalog_timing_and_public_contract() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const MissionSuccess = freshMissionSuccess();

        assert.strictEqual(MissionSuccess.SuccessAnimationMs, 4000);
        assert.strictEqual(MissionSuccess.EcologyDurationMs, 3000);
        assert.strictEqual(MissionSuccess.NarrationSentenceMs, 3000);
        assert.strictEqual(Object.isFrozen(MissionSuccess), true);

        assert.deepStrictEqual(plain(MissionSuccess.Catalog), [
          {
            missionId: "sea-turtle",
            animationKey: "sea-turtle-swim-free",
            ecology:
              "Sea turtles can get tangled in ocean trash. Keep ropes and nets out of the sea!",
            companionLine:
              "Wonderful rescue, Aiden! You freed every rope safely.",
            animalLine:
              "The sea turtle is swimming calmly through the clean coral reef."
          },
          {
            missionId: "crab",
            animationKey: "crab-to-burrow",
            ecology:
              "Crabs need safe spaces under rocks and sand. Let\\u2019s keep their homes clean!",
            companionLine:
              "Great job, Aiden! You moved every rock carefully.",
            animalLine:
              "The crab is safe again in its clean sandy home."
          },
          {
            missionId: "young-whale",
            animationKey: "young-whale-to-family",
            ecology:
              "Whales need space to swim safely. Clear the way and watch from a distance!",
            companionLine:
              "Well done, Aiden! You cleared the path and gave the young whale space.",
            animalLine:
              "The young whale is swimming safely with its family."
          }
        ]);
        assert.strictEqual(Object.isFrozen(MissionSuccess.Catalog), true);
        assert.strictEqual(Object.isFrozen(MissionSuccess.Catalog[0]), true);
        assert.strictEqual(Object.isFrozen(MissionSuccess.Catalog[1]), true);
        assert.strictEqual(Object.isFrozen(MissionSuccess.Catalog[2]), true);

        assert.deepStrictEqual(
          Object.keys(MissionSuccess).sort(),
          [
            "Catalog",
            "EcologyDurationMs",
            "NarrationSentenceMs",
            "SuccessAnimationMs",
            "getContent"
          ].sort()
        );

        assert.strictEqual(
          MissionSuccess.getContent("sea-turtle"),
          MissionSuccess.Catalog[0]
        );
        assert.strictEqual(
          MissionSuccess.getContent("crab"),
          MissionSuccess.Catalog[1]
        );
        assert.strictEqual(
          MissionSuccess.getContent("young-whale"),
          MissionSuccess.Catalog[2]
        );
        assert.strictEqual(MissionSuccess.getContent("bogus"), null);
        assert.strictEqual(MissionSuccess.getContent(null), null);
        assert.strictEqual(MissionSuccess.getContent(42), null);
        assert.strictEqual(MissionSuccess.getContent({}), null);

        const hidden = [
          "start",
          "finish",
          "skip",
          "transition",
          "setStage",
          "setTimer",
          "completeMission",
          "unlock",
          "subscribe",
          "dispatch",
          "serialize",
          "hydrate",
          "save",
          "load",
          "history"
        ];
        for (const name of hidden) {
          assert.strictEqual(MissionSuccess[name], undefined, "exposed " + name);
        }

        MissionSuccess.extra = 1;
        MissionSuccess.Catalog.extra = 1;
        MissionSuccess.Catalog[0].extra = 1;
        assert.strictEqual(MissionSuccess.extra, undefined);
        assert.strictEqual(MissionSuccess.Catalog.extra, undefined);
        assert.strictEqual(MissionSuccess.Catalog[0].extra, undefined);

        const snapshot = MissionSuccess.getSnapshot;
        assert.strictEqual(snapshot, undefined);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_sea_turtle_success_starts_exact_animation_stage() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom({ includeMissionSuccess: true });
        const ctx = loadApp(dom.document);
        runSeaTurtleToRescueSuccess(dom, ctx);

        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "success-presentation");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "disabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-active"), "true");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-mission-id"), "sea-turtle");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-stage"), "animation");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-input"), "disabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-complete-ready"), null);

        assert.strictEqual(dom.stage.hidden, true);
        assert.strictEqual(dom.rescueOverlay.hidden, true);
        assert.strictEqual(dom.missionSuccessSection.hidden, false);
        assert.strictEqual(
          dom.missionSuccessVisual.getAttribute("data-mission-success-anim"),
          "sea-turtle-swim-free"
        );
        assert.strictEqual(
          dom.missionSuccessVisual.classList.contains(
            "ocean-rescue-mission-success-anim-active"
          ),
          true
        );
        assert.strictEqual(
          dom.missionSuccessAnimal.getAttribute("data-mission-success-animal"),
          "sea-turtle"
        );
        assert.strictEqual(
          dom.missionSuccessSecondaryAnimal.getAttribute(
            "data-mission-success-secondary-animal"
          ),
          "sea-turtle"
        );
        assert.strictEqual(
          dom.missionSuccessDestination.getAttribute(
            "data-mission-success-destination"
          ),
          "sea-turtle"
        );
        assert.strictEqual(dom.statusEl.textContent, "Mission success: Sea Turtle Rescue");

        const pending = ctx.timers.pending();
        assert.strictEqual(pending.length, 1);
        assert.strictEqual(pending[0].delay, 4000);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_all_mission_content_and_visual_variants() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const expected = plain(freshMissionSuccess().Catalog);
        const animationKeys = [];

        function assertMissionPresentation(index, missionId, missionIndex, drive) {
          const dom = makeBootDom({ includeMissionSuccess: true });
          const ctx = loadApp(dom.document);
          drive(dom, ctx);
          const mission = ctx.Missions.Catalog[missionIndex];
          const content = expected[index];
          assert.strictEqual(mission.id, missionId);
          assert.strictEqual(
            dom.rootEl.getAttribute("data-mission-success-mission-id"),
            missionId
          );
          assert.strictEqual(
            dom.statusEl.textContent,
            "Mission success: " + mission.title
          );
          const animKey = dom.missionSuccessVisual.getAttribute(
            "data-mission-success-anim"
          );
          assert.strictEqual(animKey, content.animationKey);
          animationKeys.push(animKey);

          let anim = timerWithDelay(ctx, 4000);
          ctx.timers.run(anim.id);
          assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-stage"), "ecology");
          assert.strictEqual(dom.missionSuccessEcology.hidden, false);
          assert.strictEqual(dom.missionSuccessEcology.textContent, content.ecology);
          assert.strictEqual(dom.statusEl.textContent, content.ecology);

          let eco = timerWithDelay(ctx, 3000);
          ctx.timers.run(eco.id);
          assert.strictEqual(
            dom.rootEl.getAttribute("data-mission-success-stage"),
            "narration-1"
          );
          assert.strictEqual(dom.missionSuccessNarration.hidden, false);
          assert.strictEqual(dom.missionSuccessSpeaker.textContent, mission.companion + ":");
          assert.strictEqual(dom.missionSuccessLine.textContent, content.companionLine);
          assert.strictEqual(dom.statusEl.textContent, content.companionLine);

          let n1 = timerWithDelay(ctx, 3000);
          ctx.timers.run(n1.id);
          assert.strictEqual(
            dom.rootEl.getAttribute("data-mission-success-stage"),
            "narration-2"
          );
          assert.strictEqual(dom.missionSuccessSpeaker.textContent, "Narrator:");
          assert.strictEqual(dom.missionSuccessLine.textContent, content.animalLine);
          assert.strictEqual(dom.statusEl.textContent, content.animalLine);
          assert.strictEqual(dom.missionSuccessTapHelp.hidden, false);

          let n2 = timerWithDelay(ctx, 3000);
          ctx.timers.run(n2.id);
          assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_COMPLETE");
          assert.strictEqual(dom.rootEl.getAttribute("data-mission-complete-ready"), "true");
        }

        assertMissionPresentation(0, "sea-turtle", 0, runSeaTurtleToRescueSuccess);
        assertMissionPresentation(1, "crab", 1, runCrabToRescueSuccess);
        assertMissionPresentation(2, "young-whale", 2, runYoungWhaleToRescueSuccess);

        assert.strictEqual(animationKeys.length, 3);
        assert.strictEqual(new Set(animationKeys).size, 3);
        assert.deepStrictEqual(
          animationKeys.sort(),
          ["crab-to-burrow", "sea-turtle-swim-free", "young-whale-to-family"]
        );
        """
    )
    _assert_node_ok(_run_node(harness))


def test_automatic_presentation_reaches_mission_complete() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom({ includeMissionSuccess: true });
        const ctx = loadApp(dom.document);
        runSeaTurtleToRescueSuccess(dom, ctx);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");

        const anim = timerWithDelay(ctx, 4000);
        ctx.timers.run(anim.id);
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-stage"), "ecology");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-input"), "disabled");
        assert.strictEqual(dom.missionSuccessEcology.hidden, false);
        assert.strictEqual(dom.missionSuccessNarration.hidden, true);
        assert.strictEqual(dom.completeCard.hidden, true);
        assert.strictEqual(
          dom.missionSuccessEcology.textContent,
          "Sea turtles can get tangled in ocean trash. Keep ropes and nets out of the sea!"
        );
        assert.strictEqual(
          dom.statusEl.textContent,
          "Sea turtles can get tangled in ocean trash. Keep ropes and nets out of the sea!"
        );
        assert.strictEqual(
          dom.missionSuccessVisual.classList.contains(
            "ocean-rescue-mission-success-anim-active"
          ),
          false
        );

        const eco = timerWithDelay(ctx, 3000);
        ctx.timers.run(eco.id);
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-success-stage"),
          "narration-1"
        );
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-input"), "enabled");
        assert.strictEqual(dom.missionSuccessNarration.hidden, false);
        assert.strictEqual(dom.missionSuccessSpeaker.textContent, "Peso:");
        assert.strictEqual(
          dom.missionSuccessLine.textContent,
          "Wonderful rescue, Aiden! You freed every rope safely."
        );
        assert.strictEqual(dom.missionSuccessTapHelp.hidden, false);
        assert.strictEqual(
          dom.statusEl.textContent,
          "Wonderful rescue, Aiden! You freed every rope safely."
        );

        const n1 = timerWithDelay(ctx, 3000);
        ctx.timers.run(n1.id);
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-success-stage"),
          "narration-2"
        );
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-input"), "enabled");
        assert.strictEqual(dom.missionSuccessSpeaker.textContent, "Narrator:");
        assert.strictEqual(
          dom.missionSuccessLine.textContent,
          "The sea turtle is swimming calmly through the clean coral reef."
        );
        assert.strictEqual(
          dom.statusEl.textContent,
          "The sea turtle is swimming calmly through the clean coral reef."
        );

        const n2 = timerWithDelay(ctx, 3000);
        ctx.timers.run(n2.id);
        assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_COMPLETE");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-phase"), "mission-complete");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "disabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-active"), "false");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-stage"), "complete");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-input"), "disabled");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-complete-ready"), "true");
        assert.strictEqual(dom.missionSuccessVisual.hidden, true);
        assert.strictEqual(dom.missionSuccessEcology.hidden, true);
        assert.strictEqual(dom.missionSuccessNarration.hidden, true);
        assert.strictEqual(dom.missionSuccessTapHelp.hidden, true);
        assert.strictEqual(dom.completeCard.hidden, false);
        assert.strictEqual(dom.completeName.textContent, "Sea Turtle Rescue");
        assert.strictEqual(
          dom.completeEcology.textContent,
          "Sea turtles can get tangled in ocean trash. Keep ropes and nets out of the sea!"
        );
        assert.strictEqual(dom.statusEl.textContent, "Mission complete: Sea Turtle Rescue");
        assert.strictEqual(ctx.timers.pending().length, 0);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_narration_pointer_advance_contract() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom({ includeMissionSuccess: true });
        const ctx = loadApp(dom.document);
        runSeaTurtleToRescueSuccess(dom, ctx);

        dispatch(dom.missionSuccessSection, "pointerdown", pointerEvent(500, 10, 10));
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-stage"), "animation");
        const afterAnimTap = ctx.timers.pending();
        assert.strictEqual(afterAnimTap.length, 1);
        assert.strictEqual(afterAnimTap[0].delay, 4000);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");

        const anim = timerWithDelay(ctx, 4000);
        ctx.timers.run(anim.id);
        dispatch(dom.missionSuccessSection, "pointerdown", pointerEvent(501, 10, 10));
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-stage"), "ecology");
        const afterEcologyTap = ctx.timers.pending();
        assert.strictEqual(afterEcologyTap.length, 1);
        assert.strictEqual(afterEcologyTap[0].delay, 3000);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");

        const eco = timerWithDelay(ctx, 3000);
        ctx.timers.run(eco.id);
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-stage"), "narration-1");
        assert.strictEqual(
          dom.missionSuccessLine.textContent,
          "Wonderful rescue, Aiden! You freed every rope safely."
        );

        dispatch(dom.missionSuccessSection, "pointerdown", pointerEvent(502, 10, 10));
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-success-stage"),
          "narration-2"
        );
        assert.strictEqual(dom.missionSuccessSpeaker.textContent, "Narrator:");
        assert.strictEqual(
          dom.missionSuccessLine.textContent,
          "The sea turtle is swimming calmly through the clean coral reef."
        );
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-complete-ready"), null);

        dispatch(dom.missionSuccessSection, "pointerdown", pointerEvent(503, 10, 10));
        assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_COMPLETE");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-complete-ready"), "true");
        assert.strictEqual(dom.completeCard.hidden, false);
        assert.strictEqual(dom.completeName.textContent, "Sea Turtle Rescue");

        dispatch(dom.missionSuccessSection, "pointerdown", pointerEvent(504, 10, 10));
        assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_COMPLETE");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-complete-ready"), "true");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_stale_timers_and_rapid_input_are_idempotent() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom({ includeMissionSuccess: true });
        const ctx = loadApp(dom.document);
        runSeaTurtleToRescueSuccess(dom, ctx);

        const anim = timerWithDelay(ctx, 4000);
        ctx.timers.run(anim.id);
        anim.fn();
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-success-stage"), "ecology");
        const pendingEcology = ctx.timers.pending();
        assert.strictEqual(pendingEcology.length, 1);
        assert.strictEqual(pendingEcology[0].delay, 3000);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");

        const eco = timerWithDelay(ctx, 3000);
        ctx.timers.run(eco.id);
        eco.fn();
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-success-stage"),
          "narration-1"
        );
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");

        const n1 = timerWithDelay(ctx, 3000);
        ctx.timers.run(n1.id);
        n1.fn();
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-success-stage"),
          "narration-2"
        );
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SUCCESS");

        const n2 = timerWithDelay(ctx, 3000);
        ctx.timers.run(n2.id);
        assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_COMPLETE");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-complete-ready"), "true");

        n2.fn();
        assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_COMPLETE");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-complete-ready"), "true");

        dispatch(dom.missionSuccessSection, "pointerdown", pointerEvent(600, 10, 10));
        assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_COMPLETE");
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-complete-ready"), "true");
        assert.strictEqual(dom.completeName.textContent, "Sea Turtle Rescue");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_completion_card_records_progression_once_without_auto_action() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom({ includeMissionSuccess: true });
        const ctx = loadApp(dom.document);
        runSeaTurtleToRescueSuccess(dom, ctx);
        const before = JSON.stringify(ctx.Missions.getSnapshot());
        const beforePhase = ctx.State.getSnapshot().phase;
        assert.strictEqual(beforePhase, "RESCUE_SUCCESS");

        advanceToNarration1(ctx);
        const n1 = timerWithDelay(ctx, 3000);
        ctx.timers.run(n1.id);
        assert.strictEqual(
          dom.rootEl.getAttribute("data-mission-success-stage"),
          "narration-2"
        );
        assert.strictEqual(JSON.stringify(ctx.Missions.getSnapshot()), before);

        const n2 = timerWithDelay(ctx, 3000);
        ctx.timers.run(n2.id);
        assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_COMPLETE");

        assert.strictEqual(dom.completeCard.hidden, false);
        assert.strictEqual(dom.completeName.textContent, "Sea Turtle Rescue");
        assert.strictEqual(
          dom.completeEcology.textContent,
          "Sea turtles can get tangled in ocean trash. Keep ropes and nets out of the sea!"
        );
        assert.strictEqual(dom.rootEl.getAttribute("data-mission-complete-ready"), "true");
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
        assert.strictEqual(hasButton(dom.completeCard), true);
        assert.strictEqual(dom.completeContinue.disabled, false);
        assert.strictEqual(dom.completeReplay.disabled, false);
        assert.strictEqual(dom.completeContinue.textContent, "Continue");
        assert.strictEqual(dom.completeReplay.textContent, "Replay");

        const visibleText = collectVisibleText(dom.missionSuccessSection).join(" ");
        assert.strictEqual(/next mission unlocked/i.test(visibleText), true);

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


def test_existing_interactions_and_optional_runtime_boundaries() -> None:
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const seaDom = makeBootDom({ includeMissionSuccess: true });
        const seaCtx = loadApp(seaDom.document);
        runSeaTurtleToRescueSuccess(seaDom, seaCtx);
        assert.strictEqual(
          seaDom.rootEl.getAttribute("data-rescue-phase"),
          "success-presentation"
        );
        assert.strictEqual(seaDom.rootEl.getAttribute("data-mission-success-stage"), "animation");

        const crabDom = makeBootDom({ includeMissionSuccess: true });
        const crabCtx = loadApp(crabDom.document);
        runCrabToRescueSuccess(crabDom, crabCtx);
        assert.strictEqual(
          crabDom.rootEl.getAttribute("data-rescue-phase"),
          "success-presentation"
        );
        assert.strictEqual(
          crabDom.missionSuccessVisual.getAttribute("data-mission-success-anim"),
          "crab-to-burrow"
        );

        const whaleDom = makeBootDom({ includeMissionSuccess: true });
        const whaleCtx = loadApp(whaleDom.document);
        runYoungWhaleToRescueSuccess(whaleDom, whaleCtx);
        assert.strictEqual(
          whaleDom.rootEl.getAttribute("data-rescue-phase"),
          "success-presentation"
        );
        assert.strictEqual(
          whaleDom.missionSuccessVisual.getAttribute("data-mission-success-anim"),
          "young-whale-to-family"
        );

        const missingModuleDom = makeBootDom({ includeMissionSuccess: true });
        const missingModuleCtx = loadApp(
          missingModuleDom.document,
          {},
          { skipMissionSuccess: true }
        );
        assert.strictEqual(missingModuleCtx.MissionSuccess, undefined);
        runSeaTurtleToRescueSuccess(missingModuleDom, missingModuleCtx);
        assert.strictEqual(
          missingModuleCtx.State.getSnapshot().phase,
          "RESCUE_SUCCESS"
        );
        assert.strictEqual(
          missingModuleDom.rootEl.getAttribute("data-rescue-phase"),
          "success"
        );
        assert.strictEqual(
          missingModuleDom.rootEl.getAttribute("data-mission-success-active"),
          null
        );
        assert.strictEqual(missingModuleDom.missionSuccessSection.hidden, true);
        assert.strictEqual(missingModuleCtx.timers.pending().length, 0);

        const missingDom = makeBootDom();
        const missingDomCtx = loadApp(missingDom.document);
        runSeaTurtleToRescueSuccess(missingDom, missingDomCtx);
        assert.strictEqual(missingDomCtx.State.getSnapshot().phase, "RESCUE_SUCCESS");
        assert.strictEqual(missingDomCtx.timers.pending().length, 0);

        const missingTimersDom = makeBootDom({ includeMissionSuccess: true });
        const missingTimersCtx = loadApp(missingTimersDom.document);
        runSeaTurtleToFinalFeedbackScheduled(missingTimersDom, missingTimersCtx);
        missingTimersCtx.sandbox.window.setTimeout = undefined;
        missingTimersCtx.sandbox.window.clearTimeout = undefined;
        const finalTimer = timerWithDelay(missingTimersCtx, 400);
        missingTimersCtx.timers.run(finalTimer.id);
        assert.strictEqual(
          missingTimersCtx.State.getSnapshot().phase,
          "RESCUE_SUCCESS"
        );
        assert.strictEqual(
          missingTimersDom.rootEl.getAttribute("data-rescue-phase"),
          "success"
        );
        assert.strictEqual(
          missingTimersDom.rootEl.getAttribute("data-mission-success-active"),
          null
        );
        assert.strictEqual(missingTimersDom.missionSuccessSection.hidden, true);
        assert.strictEqual(missingTimersCtx.timers.pending().length, 0);
        """
    )
    _assert_node_ok(_run_node(harness))
