"""Focused tests for the Ocean Rescue TRAVEL distance progress HUD.

The progress bar is the single authoritative visual of how far Aiden has
traveled toward the rescue site. Its value MUST be derived exclusively from
``Travel.getSnapshot().distance`` and ``Rescue.ArrivalDistance`` so that it
stays in lockstep with collision slowdowns, pause/resume, and the arrival
transition.

Every behavioral assertion runs the real tracked sources through the installed
Node runtime in a fresh VM sandbox using a minimal fake DOM, a fake canvas 2D
context, a deterministic fake timer queue, and a deterministic fake animation
frame queue. No npm packages, no browser automation, and no real-time sleeps
are used. Source-identity assertions read the canonical sources directly.
"""

import re
import shutil
import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_BIN = shutil.which("node")
if NODE_BIN is None:
    raise RuntimeError("Node executable not found on PATH")
assert NODE_BIN is not None

APP_JS = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "app.js"
TEMPLATE = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "index.template.html"


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

    function makeClassList() {
      const names = [];
      return {
        add(token) { if (names.indexOf(token) === -1) names.push(token); },
        remove(token) { const i = names.indexOf(token); if (i !== -1) names.splice(i, 1); },
        contains(token) { return names.indexOf(token) !== -1; },
      };
    }

    function makeElement(tagName) {
      const el = {
        tagName, children: [], attributes: {}, style: {},
        textContent: null, className: "", disabled: false, hidden: false,
        parent: null, listeners: {}, classList: makeClassList(),
        appendChild(child) { child.parent = this; this.children.push(child); },
        setAttribute(name, value) { this.attributes[name] = String(value); },
        getAttribute(name) {
          return Object.prototype.hasOwnProperty.call(this.attributes, name)
            ? this.attributes[name] : null;
        },
        removeAttribute(name) { delete this.attributes[name]; },
        addEventListener(type, fn) {
          if (!this.listeners[type]) this.listeners[type] = [];
          this.listeners[type].push(fn);
        },
        click() {
          const list = this.listeners["click"] || [];
          for (const fn of list.slice()) fn({ stopPropagation() {} });
          if (this.parent) this.parent.click();
        },
        querySelectorAll(selector) {
          if (selector === "button") return this.children.filter((c) => c.tagName === "button");
          return [];
        },
      };
      Object.defineProperty(el, "innerHTML", {
        enumerable: false,
        get() { return this._innerHTML || ""; },
        set(value) { this._innerHTML = value; this.children = []; },
      });
      return el;
    }

    function makeContext() {
      const calls = [];
      const ctx = { calls };
      const props = { fillStyle: null, strokeStyle: null, lineWidth: null, lineCap: null, font: null, textAlign: null, globalAlpha: null };
      for (const name of Object.keys(props)) {
        Object.defineProperty(ctx, name, {
          get() { return props[name]; },
          set(value) { props[name] = value; calls.push(["set:" + name, value]); },
        });
      }
      ctx.save = function () { calls.push(["save"]); };
      ctx.restore = function () { calls.push(["restore"]); };
      ctx.translate = function (...a) { calls.push(["translate", ...a]); };
      ctx.clearRect = function (...a) { calls.push(["clearRect", ...a]); };
      ctx.fillRect = function (...a) { calls.push(["fillRect", ...a]); };
      ctx.beginPath = function () { calls.push(["beginPath"]); };
      ctx.arc = function (...a) { calls.push(["arc", ...a]); };
      ctx.fill = function () { calls.push(["fill"]); };
      ctx.fillText = function (...a) { calls.push(["fillText", ...a]); };
      ctx.moveTo = function (...a) { calls.push(["moveTo", ...a]); };
      ctx.lineTo = function (...a) { calls.push(["lineTo", ...a]); };
      ctx.stroke = function () { calls.push(["stroke"]); };
      ctx.setLineDash = function (...a) { calls.push(["setLineDash", ...a]); };
      return ctx;
    }

    function makeCanvasElement(canvasContext) {
      const el = makeElement("canvas");
      el.width = 1280; el.height = 720;
      el.rect = { left: 0, top: 0, width: 1280, height: 720 };
      el._context = canvasContext || makeContext();
      el.getContext = function (type) { return type === "2d" ? el._context : null; };
      el.getBoundingClientRect = function () { return el.rect; };
      return el;
    }

    function makeDocument(elements) {
      return {
        domLoadedHandler: null,
        getElementById(id) {
          return Object.prototype.hasOwnProperty.call(elements, id) ? elements[id] : null;
        },
        createElement(tagName) { return makeElement(tagName); },
        addEventListener(type, fn) { if (type === "DOMContentLoaded") this.domLoadedHandler = fn; },
      };
    }

    function makeBootDom() {
      const rootEl = makeElement("main");
      const statusEl = makeElement("p");
      const missionSection = makeElement("section");
      const missionList = makeElement("div");
      const gupSection = makeElement("section"); gupSection.hidden = true;
      const gupMission = makeElement("p");
      const gupList = makeElement("div");
      const actions = makeElement("div");
      const gupBack = makeElement("button");
      const gupLaunch = makeElement("button");
      const launchSection = makeElement("section"); launchSection.hidden = true;
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
      const goalBanner = makeElement("div"); goalBanner.hidden = true;
      const stage = makeElement("section"); stage.hidden = true;
      const canvas = makeCanvasElement();
      const travelProgress = makeElement("div"); travelProgress.hidden = true;
      const progressStart = makeElement("span");
      const progressBar = makeElement("progress");
      progressBar.max = 100;
      progressBar.value = 0;
      const progressEnd = makeElement("span");
      const progressValue = makeElement("span");
      progressValue.textContent = "0%";
      travelProgress.appendChild(progressStart);
      travelProgress.appendChild(progressBar);
      travelProgress.appendChild(progressEnd);
      travelProgress.appendChild(progressValue);
      const rescueOverlay = makeElement("section"); rescueOverlay.hidden = true;
      const rescueTitle = makeElement("h2");
      const rescueCompanion = makeElement("p");
      const rescueSituation = makeElement("p");
      const rescueReady = makeElement("div"); rescueReady.hidden = true;
      const rescueTutorial = makeElement("div"); rescueTutorial.hidden = true;
      const rescueInstruction = makeElement("p");
      const rescueHand = makeElement("div");
      const rescueProgress = makeElement("p");
      const rescueAssistHand = makeElement("div"); rescueAssistHand.hidden = true;
      const pauseButton = makeElement("button"); pauseButton.hidden = true;
      const pauseOverlay = makeElement("div"); pauseOverlay.hidden = true;
      const pauseMenu = makeElement("div");
      const pauseTitle = makeElement("h2");
      const pauseResume = makeElement("button");
      const pauseCountdown = makeElement("div"); pauseCountdown.hidden = true;
      const pauseMenuButton = makeElement("button");

      missionSection.appendChild(missionList);
      actions.appendChild(gupBack); actions.appendChild(gupLaunch);
      gupSection.appendChild(gupMission); gupSection.appendChild(gupList); gupSection.appendChild(actions);
      launchSection.appendChild(launchTitle);
      launchVisual.appendChild(launchDoorLeft); launchVisual.appendChild(launchDoorRight);
      launchVisual.appendChild(launchGup); launchGup.appendChild(launchGupName);
      launchSection.appendChild(launchVisual); launchSection.appendChild(launchCompanion);
      launchSection.appendChild(launchBriefing); launchSection.appendChild(launchTapHint);
      launchSection.appendChild(launchSkip);
      stage.appendChild(canvas);
      stage.appendChild(travelProgress);
      rescueOverlay.appendChild(rescueTitle); rescueOverlay.appendChild(rescueCompanion);
      rescueOverlay.appendChild(rescueSituation); rescueOverlay.appendChild(rescueReady);
      rescueOverlay.appendChild(rescueTutorial); rescueTutorial.appendChild(rescueInstruction);
      rescueTutorial.appendChild(rescueHand);
      rescueOverlay.appendChild(rescueProgress); rescueOverlay.appendChild(rescueAssistHand);
      stage.appendChild(rescueOverlay);
      pauseMenu.appendChild(pauseTitle); pauseMenu.appendChild(pauseResume);
      pauseMenu.appendChild(pauseCountdown); pauseMenu.appendChild(pauseMenuButton);
      pauseOverlay.appendChild(pauseMenu);
      rootEl.appendChild(missionSection); rootEl.appendChild(gupSection);
      rootEl.appendChild(launchSection); rootEl.appendChild(goalBanner);
      rootEl.appendChild(stage); rootEl.appendChild(pauseButton); rootEl.appendChild(pauseOverlay);

      const elements = {
        "ocean-rescue-root": rootEl, "ocean-rescue-status": statusEl,
        "ocean-rescue-mission-select": missionSection, "ocean-rescue-mission-list": missionList,
        "ocean-rescue-gup-select": gupSection, "ocean-rescue-gup-mission": gupMission,
        "ocean-rescue-gup-list": gupList, "ocean-rescue-gup-actions": actions,
        "ocean-rescue-gup-back": gupBack, "ocean-rescue-gup-launch": gupLaunch,
        "ocean-rescue-launch": launchSection, "ocean-rescue-launch-title": launchTitle,
        "ocean-rescue-launch-visual": launchVisual,
        "ocean-rescue-launch-gup-name": launchGupName,
        "ocean-rescue-launch-companion": launchCompanion,
        "ocean-rescue-launch-briefing": launchBriefing,
        "ocean-rescue-launch-skip": launchSkip,
        "ocean-rescue-goal-banner": goalBanner,
        "ocean-rescue-stage": stage, "ocean-rescue-canvas": canvas,
        "ocean-rescue-travel-progress": travelProgress,
        "ocean-rescue-travel-progress-start": progressStart,
        "ocean-rescue-travel-progress-bar": progressBar,
        "ocean-rescue-travel-progress-end": progressEnd,
        "ocean-rescue-travel-progress-value": progressValue,
        "ocean-rescue-rescue-overlay": rescueOverlay,
        "ocean-rescue-rescue-companion": rescueCompanion,
        "ocean-rescue-rescue-situation": rescueSituation,
        "ocean-rescue-rescue-ready": rescueReady,
        "ocean-rescue-rescue-tutorial": rescueTutorial,
        "ocean-rescue-rescue-instruction": rescueInstruction,
        "ocean-rescue-rescue-hand": rescueHand,
        "ocean-rescue-rescue-progress": rescueProgress,
        "ocean-rescue-rescue-assist-hand": rescueAssistHand,
        "ocean-rescue-pause-button": pauseButton,
        "ocean-rescue-pause-overlay": pauseOverlay,
        "ocean-rescue-pause-menu": pauseMenu,
        "ocean-rescue-pause-title": pauseTitle,
        "ocean-rescue-pause-resume": pauseResume,
        "ocean-rescue-pause-countdown": pauseCountdown,
        "ocean-rescue-pause-menu-button": pauseMenuButton,
      };
      return { document: makeDocument(elements), rootEl, statusEl, missionSection, missionList,
        gupSection, gupList, gupBack, gupLaunch, launchSection, launchGupName,
        launchCompanion, launchBriefing, launchSkip, goalBanner, stage, canvas,
        travelProgress, progressStart, progressBar, progressEnd, progressValue,
        rescueOverlay, rescueCompanion, rescueSituation, rescueReady,
        rescueTutorial, rescueInstruction, rescueHand, rescueProgress, rescueAssistHand,
        pauseButton, pauseOverlay, pauseMenu, pauseResume, pauseCountdown, pauseMenuButton };
    }

    function makeTimerQueue() {
      let nextId = 1;
      const timers = [];
      return {
        timers,
        setTimeout(fn, delay) {
          const id = nextId++; timers.push({ id, fn, delay, cancelled: false }); return id;
        },
        clearTimeout(id) {
          const e = timers.find((e) => e.id === id); if (e) e.cancelled = true;
        },
        pending() { return timers.filter((e) => !e.cancelled); },
        run(id) {
          const e = timers.find((e) => e.id === id);
          if (!e) throw new Error("no such timer " + id);
          if (e.cancelled) throw new Error("timer already cancelled " + id);
          e.cancelled = true; e.fn();
        },
      };
    }

    function makeFrameQueue() {
      let nextId = 1;
      const frames = [];
      return {
        frames,
        requestAnimationFrame(fn) {
          const id = nextId++; frames.push({ id, fn, ran: false, cancelled: false }); return id;
        },
        cancelAnimationFrame(id) {
          const e = frames.find((e) => e.id === id); if (e) e.cancelled = true;
        },
        pending() { return frames.filter((e) => !e.cancelled && !e.ran); },
        run(id, timestamp) {
          const e = frames.find((e) => e.id === id);
          if (!e) throw new Error("no such frame " + id);
          if (e.cancelled) throw new Error("frame already cancelled " + id);
          e.ran = true; e.fn(timestamp);
        },
      };
    }

    function loadApp(document, opts) {
      const timers = makeTimerQueue();
      const frames = makeFrameQueue();
      const extras = {
        setTimeout: timers.setTimeout, clearTimeout: timers.clearTimeout,
        requestAnimationFrame: frames.requestAnimationFrame,
        cancelAnimationFrame: frames.cancelAnimationFrame,
        performance: { now: () => 0 },
      };
      const sandbox = { window: extras, document };
      vm.createContext(sandbox);
      vm.runInContext(STATE_SOURCE, sandbox, { filename: "state.js" });
      vm.runInContext(MISSIONS_SOURCE, sandbox, { filename: "missions.js" });
      vm.runInContext(GUPS_SOURCE, sandbox, { filename: "gups.js" });
      vm.runInContext(LAUNCH_SOURCE, sandbox, { filename: "launch.js" });
      vm.runInContext(TRAVEL_SOURCE, sandbox, { filename: "travel.js" });
      if (!opts || opts.withTerrain !== true) {
        // No terrain: Travel.step always runs at full speed so distances are
        // exactly 6 per 50ms frame. The collision-coupling test opts in to the
        // real terrain module.
      } else {
        vm.runInContext(TERRAIN_SOURCE, sandbox, { filename: "terrain.js" });
      }
      vm.runInContext(RESCUE_SOURCE, sandbox, { filename: "rescue.js" });
      vm.runInContext(APP_SOURCE, sandbox, { filename: "app.js" });
      const O = sandbox.window.OceanRescue;
      return { timers, frames, State: O.State, Travel: O.Travel,
        Terrain: O.Terrain || null, Rescue: O.Rescue, App: O.App,
        TravelProgress: O.TravelProgress };
    }

    function makeComputeContext(opts) {
      const sandbox = { window: {}, document: makeDocument({}) };
      vm.createContext(sandbox);
      vm.runInContext(STATE_SOURCE, sandbox, { filename: "state.js" });
      if (!opts || opts.withRescue !== false) {
        vm.runInContext(RESCUE_SOURCE, sandbox, { filename: "rescue.js" });
      }
      vm.runInContext(APP_SOURCE, sandbox, { filename: "app.js" });
      return sandbox.window.OceanRescue.TravelProgress;
    }

    function bootToLaunch(dom, ctx) {
      dom.document.domLoadedHandler();
      assert.strictEqual(ctx.App.boot(), true);
      dom.missionList.children[0].click();
      dom.gupList.children[0].click();
      dom.gupLaunch.click();
      assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
    }

    function completeLaunch(ctx) {
      const pending = ctx.timers.pending();
      assert.strictEqual(pending.length >= 1, true);
      ctx.timers.run(pending[0].id);
      assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
    }

    function runFrames(ctx, count, startTime, delta) {
      let time = startTime;
      for (let i = 0; i < count; i += 1) {
        const pending = ctx.frames.pending();
        if (pending.length === 0) {
          return time;
        }
        ctx.frames.run(pending[0].id, time);
        time += delta;
      }
      return time;
    }

    function oraclePercent(ctx, distance) {
      const ratio = distance / ctx.Rescue.ArrivalDistance;
      return Math.round(Math.max(0, Math.min(1, ratio)) * 100);
    }
    """
)


_JS_PURE = _BOOTSTRAP + textwrap.dedent(
    """
    const noRescue = makeComputeContext({ withRescue: false });
    assert.strictEqual(Object.isFrozen(noRescue), true);
    assert.strictEqual(typeof noRescue.compute, "function");
    assert.strictEqual(noRescue.compute({ active: true, distance: 3000 }).valid, false);

    const tp = makeComputeContext({ withRescue: true });
    assert.strictEqual(Object.isFrozen(tp), true);
    assert.strictEqual(typeof tp.compute, "function");

    function expectPercent(distance, expected) {
      const r = tp.compute({ active: true, distance: distance });
      assert.strictEqual(r.valid, true, "valid for distance " + distance);
      assert.strictEqual(r.percent, expected, "percent for distance " + distance);
      assert.strictEqual(r.distance, distance);
      assert.strictEqual(r.arrivalDistance, 6000);
      return r;
    }

    expectPercent(0, 0);
    expectPercent(3000, 50);
    expectPercent(5950, 99);
    expectPercent(5999, 100);
    expectPercent(6000, 100);
    expectPercent(7000, 100);

    const invalids = [
      { active: true, distance: -1 },
      { active: true, distance: NaN },
      { active: true, distance: Infinity },
      { active: true, distance: -Infinity },
      { active: true, distance: "3000" },
      {},
      null,
      undefined,
      42,
    ];
    for (const input of invalids) {
      const result = tp.compute(input);
      assert.strictEqual(result.valid, false, "invalid for " + JSON.stringify(input));
    }
    process.exit(0);
    """
)

_JS_LIFECYCLE = _BOOTSTRAP + textwrap.dedent(
    """
    const dom = makeBootDom();
    const ctx = loadApp(dom.document);
    bootToLaunch(dom, ctx);
    completeLaunch(ctx);
    assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");

    assert.strictEqual(dom.travelProgress.hidden, false, "progress HUD must be visible during TRAVEL");
    assert.strictEqual(dom.progressBar.value, 0, "must start at exactly 0%");
    assert.strictEqual(dom.progressValue.textContent, "0%");
    assert.strictEqual(dom.travelProgress.getAttribute("data-travel-progress-state"), "active");
    assert.strictEqual(dom.travelProgress.getAttribute("data-travel-progress-percent"), "0");
    assert.strictEqual(dom.travelProgress.getAttribute("data-travel-progress-distance"), "0");
    assert.strictEqual(dom.travelProgress.getAttribute("data-travel-progress-arrival-distance"), "6000");

    let prevPercent = -1;
    let prevDistance = -1;
    const seen = {};
    let time = 1000;
    let frames = 0;
    for (;;) {
      const pending = ctx.frames.pending();
      if (pending.length === 0) {
        break;
      }
      frames += 1;
      if (frames > 2000) {
        throw new Error("travel never reached arrival within frame budget");
      }
      ctx.frames.run(pending[0].id, time);
      time += 50;
      const snap = ctx.Travel.getSnapshot();
      if (ctx.State.getSnapshot().phase !== "TRAVEL") {
        break;
      }
      const expected = oraclePercent(ctx, snap.distance);
      assert.strictEqual(dom.progressBar.value, expected,
        "progress must mirror authoritative distance at frame " + frames);
      assert.strictEqual(dom.progressValue.textContent, expected + "%");
      assert.strictEqual(dom.travelProgress.getAttribute("data-travel-progress-state"), "active");
      assert.strictEqual(dom.travelProgress.getAttribute("data-travel-progress-percent"), String(expected));
      assert.strictEqual(dom.travelProgress.getAttribute("data-travel-progress-distance"), String(snap.distance));
      assert.strictEqual(dom.travelProgress.getAttribute("data-travel-progress-arrival-distance"), String(ctx.Rescue.ArrivalDistance));
      assert.ok(expected <= 100, "never exceeds 100");
      assert.ok(expected >= prevPercent,
        "monotonic non-decreasing percent (frame " + frames + ": " + prevPercent + " -> " + expected + ")");
      assert.ok(snap.distance >= prevDistance, "distance non-decreasing");
      if (!Object.prototype.hasOwnProperty.call(seen, expected)) {
        seen[expected] = snap.distance;
      }
      prevPercent = expected;
      prevDistance = snap.distance;
    }

    assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SITE_TRANSITION",
      "arrival transition begins once distance reaches ArrivalDistance");
    assert.strictEqual(dom.travelProgress.hidden, true, "HUD hidden on arrival");
    assert.strictEqual(dom.rescueOverlay.hidden, false, "rescue overlay shown on arrival");
    assert.strictEqual(dom.travelProgress.getAttribute("data-travel-progress-state"), "hidden");

    assert.strictEqual(seen[0], 0, "0% reached exactly at distance 0");
    assert.strictEqual(seen[50], 2970, "50% first reached at the Math.round boundary distance 2970");
    assert.strictEqual(seen[99], 5910, "99% first reached at the Math.round boundary distance 5910");
    assert.ok(Object.prototype.hasOwnProperty.call(seen, 100), "100% reached before arrival");
    assert.strictEqual(seen[100], 5970, "100% first reached at the Math.round boundary distance 5970");
    assert.ok(seen[100] < 6000, "clamped to 100 before arrival distance, at " + seen[100]);
    process.exit(0);
    """
)

_JS_PAUSE_RESUME = _BOOTSTRAP + textwrap.dedent(
    """
    const dom = makeBootDom();
    const ctx = loadApp(dom.document);
    bootToLaunch(dom, ctx);
    completeLaunch(ctx);
    runFrames(ctx, 60, 1000, 50);
    const before = ctx.Travel.getSnapshot().distance;
    const beforeValue = dom.progressBar.value;
    assert.ok(before > 0, "progress should have advanced before pause");
    assert.ok(beforeValue > 0, "percent should be positive before pause");
    assert.strictEqual(dom.travelProgress.hidden, false);

    dom.pauseButton.click();
    assert.strictEqual(ctx.frames.pending().length, 0, "travel frame cancelled while paused");
    assert.strictEqual(dom.progressBar.value, beforeValue, "DOM value unchanged while paused");
    assert.strictEqual(dom.progressValue.textContent, beforeValue + "%", "text unchanged while paused");
    assert.strictEqual(ctx.Travel.getSnapshot().distance, before, "distance unchanged while paused");

    dom.pauseResume.click();
    const t1000a = ctx.timers.pending().filter((t) => t.delay === 1000);
    assert.strictEqual(t1000a.length >= 1, true);
    ctx.timers.run(t1000a[0].id);
    ctx.timers.run(ctx.timers.pending().filter((t) => t.delay === 1000)[0].id);
    ctx.timers.run(ctx.timers.pending().filter((t) => t.delay === 1000)[0].id);
    ctx.timers.run(ctx.timers.pending().filter((t) => t.delay === 700)[0].id);

    assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
    assert.strictEqual(dom.progressBar.value, beforeValue, "unchanged immediately after resume");
    runFrames(ctx, 40, 5000, 50);
    assert.ok(dom.progressBar.value > beforeValue,
      "progress resumes increasing: " + beforeValue + " -> " + dom.progressBar.value);
    const snap = ctx.Travel.getSnapshot();
    assert.strictEqual(dom.progressBar.value, oraclePercent(ctx, snap.distance),
      "after resume progress still mirrors authoritative distance");
    process.exit(0);
    """
)

_JS_MISSION_SELECT = _BOOTSTRAP + textwrap.dedent(
    """
    const dom = makeBootDom();
    const ctx = loadApp(dom.document);
    bootToLaunch(dom, ctx);
    completeLaunch(ctx);
    runFrames(ctx, 60, 1000, 50);
    assert.ok(dom.progressBar.value > 0, "progress advanced before menu exit");

    dom.pauseButton.click();
    dom.pauseMenuButton.click();
    assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_SELECT");
    assert.strictEqual(dom.travelProgress.hidden, true, "HUD hidden on mission select");
    assert.strictEqual(dom.progressBar.value, 0, "value reset to 0 on mission select");
    assert.strictEqual(dom.progressValue.textContent, "0%", "text reset to 0% on mission select");
    assert.strictEqual(dom.travelProgress.getAttribute("data-travel-progress-state"), "hidden");

    dom.missionList.children[0].click();
    assert.strictEqual(ctx.State.getSnapshot().phase, "GUP_SELECT");
    dom.gupList.children[0].click();
    dom.gupLaunch.click();
    assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
    completeLaunch(ctx);
    assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
    assert.strictEqual(dom.travelProgress.hidden, false, "HUD visible on the new run");
    assert.strictEqual(dom.progressBar.value, 0, "second run starts at 0%");
    assert.strictEqual(dom.progressValue.textContent, "0%");
    assert.strictEqual(dom.travelProgress.getAttribute("data-travel-progress-state"), "active");
    assert.strictEqual(dom.travelProgress.getAttribute("data-travel-progress-percent"), "0");
    process.exit(0);
    """
)

_JS_COLLISION = _BOOTSTRAP + textwrap.dedent(
    """
    const dom = makeBootDom();
    const ctx = loadApp(dom.document, { withTerrain: true });
    bootToLaunch(dom, ctx);
    completeLaunch(ctx);
    assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");

    let sawCollision = false;
    let sawSlowdown = false;
    const freeDeltas = [];
    const slowDeltas = [];
    const freePercentDeltas = [];
    const slowPercentDeltas = [];
    let lastDistance = null;
    let lastPercent = null;
    let time = 1000;
    let frames = 0;
    for (;;) {
      const pending = ctx.frames.pending();
      if (pending.length === 0) {
        break;
      }
      frames += 1;
      if (frames > 1500) {
        break;
      }
      ctx.frames.run(pending[0].id, time);
      time += 50;
      const terrainSnap = ctx.Terrain.getSnapshot();
      if (terrainSnap.collisionCount > 0) {
        sawCollision = true;
      }
      const slowing = terrainSnap.forwardSpeedMultiplier === 0.5;
      if (slowing) {
        sawSlowdown = true;
      }
      if (ctx.State.getSnapshot().phase !== "TRAVEL") {
        break;
      }
      const snap = ctx.Travel.getSnapshot();
      const expected = oraclePercent(ctx, snap.distance);
      assert.strictEqual(dom.progressBar.value, expected,
        "progress must equal round(min(distance/ArrivalDistance,1)*100) even during collision slowdown (frame " + frames + ")");
      assert.strictEqual(dom.progressValue.textContent, expected + "%");
      if (lastDistance !== null) {
        const distanceDelta = snap.distance - lastDistance;
        const percentDelta = expected - lastPercent;
        if (slowing) {
          slowDeltas.push(distanceDelta);
          slowPercentDeltas.push(percentDelta);
        } else {
          freeDeltas.push(distanceDelta);
          freePercentDeltas.push(percentDelta);
        }
      }
      lastDistance = snap.distance;
      lastPercent = expected;
    }

    assert.strictEqual(sawCollision, true, "a terrain collision must occur");
    assert.strictEqual(sawSlowdown, true, "the slowdown multiplier window must occur");
    assert.ok(freeDeltas.length > 0 && slowDeltas.length > 0, "both free and slowed frames observed");
    const maxSlow = Math.max.apply(null, slowDeltas);
    const minFree = Math.min.apply(null, freeDeltas);
    assert.ok(maxSlow < minFree,
      "distance grows slower during collision slowdown (" + maxSlow + " < " + minFree + ")");
    const maxSlowPercent = Math.max.apply(null, slowPercentDeltas);
    assert.ok(maxSlowPercent <= Math.max.apply(null, freePercentDeltas),
      "percent growth is never faster during collision slowdown");
    process.exit(0);
    """
)


def _run_js(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [NODE_BIN, "-e", code],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def _assert_node_ok(result: subprocess.CompletedProcess) -> None:
    assert result.returncode == 0, (
        f"JS harness failed (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_pure_compute_is_authoritative_and_fail_closed() -> None:
    _assert_node_ok(_run_js(_JS_PURE))


def test_lifecycle_initial_zero_track_and_arrival_hide() -> None:
    _assert_node_ok(_run_js(_JS_LIFECYCLE))


def test_pause_frozen_resume_continues() -> None:
    _assert_node_ok(_run_js(_JS_PAUSE_RESUME))


def test_hidden_on_mission_select_and_second_run_resets() -> None:
    _assert_node_ok(_run_js(_JS_MISSION_SELECT))


def test_collision_slowdown_coupling() -> None:
    _assert_node_ok(_run_js(_JS_COLLISION))


def test_source_identity_progress_derived_from_authoritative_contract() -> None:
    app_js = APP_JS.read_text(encoding="utf-8")
    template = TEMPLATE.read_text(encoding="utf-8")

    assert "Rescue.ArrivalDistance" in app_js, (
        "progress must derive from Rescue.ArrivalDistance"
    )
    assert "6000" not in app_js, (
        "progress must not hardcode ArrivalDistance 6000 in app.js"
    )
    assert "setInterval" not in app_js, (
        "progress must not introduce a new interval timer"
    )

    assert "function syncTravelProgress(travelSnapshot)" in app_js
    assert "function showTravelProgress(travelSnapshot)" in app_js
    assert "function hideTravelProgress()" in app_js
    assert "function computeTravelProgress(travelSnapshot)" in app_js
    assert "window.OceanRescue.TravelProgress = Object.freeze({" in app_js

    for token in (
        "data-travel-progress-state",
        "data-travel-progress-percent",
        "data-travel-progress-distance",
        "data-travel-progress-arrival-distance",
    ):
        assert token in app_js, f"missing diagnostics attribute {token}"

    match = re.search(
        r"function computeTravelProgress\(travelSnapshot\) \{([\s\S]*?)\n  \}",
        app_js,
    )
    assert match is not None, "could not isolate computeTravelProgress body"
    body = match.group(1)
    for forbidden in (
        "collisionCount",
        "lastCollisionObstacleId",
        "obstacle",
        "performance",
        "Date",
        "elapsed",
        "nowMs",
        "setTimeout",
        "setInterval",
        "requestAnimationFrame",
    ):
        assert forbidden not in body, (
            f"computeTravelProgress must be pure distance/ArrivalDistance math, found '{forbidden}'"
        )
    assert "Math.round(" in body, "rounding policy must be applied once"
    assert "Rescue.ArrivalDistance" in body

    assert 'id="ocean-rescue-travel-progress"' in template
    assert 'id="ocean-rescue-travel-progress-bar"' in template
    assert "<progress" in template
    assert 'max="100"' in template
    assert 'aria-label="Travel progress"' in template
    assert 'id="ocean-rescue-travel-progress-value"' in template
    assert 'aria-label="Distance to rescue site"' in template
    assert "hidden" in template

    progress_markup = re.search(
        r'<div\s+id="ocean-rescue-travel-progress"[\s\S]*?</div>',
        template,
    )
    assert progress_markup is not None, "could not isolate travel progress markup"
    progress_block = progress_markup.group(0)
    assert "aria-live" not in progress_block, (
        "progress HUD must not use aria-live (no per-frame screen reader announcements)"
    )
