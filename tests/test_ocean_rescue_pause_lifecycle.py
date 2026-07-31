"""Behavioral tests for the Ocean Rescue pause/resume lifecycle.

Every JavaScript assertion runs the real tracked sources through the installed
Node runtime in a fresh VM sandbox using a minimal fake DOM, a fake canvas 2D
context, a deterministic fake timer queue, a deterministic fake animation-frame
queue, and a deterministic monotonic clock. No npm packages, no browser
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


_SOURCES = textwrap.dedent(
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

    function freshSeaTurtle() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(SEA_TURTLE_SOURCE, sandbox, { filename: "sea-turtle.js" });
      return sandbox.window.OceanRescue.SeaTurtle;
    }

    function freshCrab() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(CRAB_SOURCE, sandbox, { filename: "crab.js" });
      return sandbox.window.OceanRescue.Crab;
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

    function loadApp(document) {
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
      vm.runInContext(TERRAIN_SOURCE, sandbox, { filename: "terrain.js" });
      vm.runInContext(RESCUE_SOURCE, sandbox, { filename: "rescue.js" });
      vm.runInContext(SEA_TURTLE_SOURCE, sandbox, { filename: "sea-turtle.js" });
      vm.runInContext(CRAB_SOURCE, sandbox, { filename: "crab.js" });
      vm.runInContext(YOUNG_WHALE_SOURCE, sandbox, { filename: "young-whale.js" });
      vm.runInContext(APP_SOURCE, sandbox, { filename: "app.js" });
      const O = sandbox.window.OceanRescue;
      return { timers, frames, State: O.State, Travel: O.Travel, SeaTurtle: O.SeaTurtle,
        Crab: O.Crab, YoungWhale: O.YoungWhale, App: O.App };
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

    function dispatch(element, type, event) {
      const list = element.listeners[type] || [];
      for (const fn of list.slice()) fn(event);
    }

    function pointerEvent(pointerId, x, y) {
      return { pointerId, clientX: x, clientY: y, isPrimary: true, button: 0,
        preventDefault() {}, stopPropagation() {} };
    }
"""
)

_JS_TEST_1 = _SOURCES + textwrap.dedent(
    """
    const dom = makeBootDom();
    const ctx = loadApp(dom.document);
    bootToLaunch(dom, ctx);
    completeLaunch(ctx);
    assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");

    dom.pauseButton.click();

    assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
    assert.strictEqual(dom.pauseOverlay.hidden, false);
    assert.strictEqual(dom.rootEl.getAttribute("data-pause-active"), "true");
    assert.strictEqual(dom.pauseButton.hidden, true);
    assert.strictEqual(dom.pauseResume.hidden, false);
    assert.strictEqual(dom.pauseCountdown.hidden, true);
    process.exit(0);
    """
)

_JS_TEST_2 = _SOURCES + textwrap.dedent(
    """
    const dom = makeBootDom();
    const ctx = loadApp(dom.document);
    bootToLaunch(dom, ctx);
    completeLaunch(ctx);
    dom.pauseButton.click();
    dom.pauseResume.click();

    assert.strictEqual(dom.pauseCountdown.hidden, false);
    assert.strictEqual(dom.pauseCountdown.textContent, "3");

    const t1000a = ctx.timers.pending().filter((t) => t.delay === 1000);
    assert.strictEqual(t1000a.length >= 1, true);
    ctx.timers.run(t1000a[0].id);
    assert.strictEqual(dom.pauseCountdown.textContent, "2");

    const t1000b = ctx.timers.pending().filter((t) => t.delay === 1000);
    assert.strictEqual(t1000b.length >= 1, true);
    ctx.timers.run(t1000b[0].id);
    assert.strictEqual(dom.pauseCountdown.textContent, "1");

    const t1000c = ctx.timers.pending().filter((t) => t.delay === 1000);
    assert.strictEqual(t1000c.length >= 1, true);
    ctx.timers.run(t1000c[0].id);
    assert.strictEqual(dom.pauseCountdown.textContent, "Go!");

    const t700 = ctx.timers.pending().filter((t) => t.delay === 700);
    assert.strictEqual(t700.length >= 1, true);
    ctx.timers.run(t700[0].id);

    assert.strictEqual(dom.pauseOverlay.hidden, true);
    assert.strictEqual(dom.rootEl.getAttribute("data-pause-active"), "false");
    assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
    process.exit(0);
    """
)

_JS_TEST_3 = _SOURCES + textwrap.dedent(
    """
    const dom = makeBootDom();
    const ctx = loadApp(dom.document);
    bootToLaunch(dom, ctx);
    completeLaunch(ctx);

    const goalTimers = ctx.timers.pending().filter((t) => t.delay === 3000);
    assert.strictEqual(goalTimers.length, 1, "expected a goal banner timer");

    dom.pauseButton.click();
    const frozenGoal = ctx.timers.pending().filter((t) => t.delay === 3000);
    assert.strictEqual(frozenGoal.length, 0, "goal timer should be cleared on pause");

    dom.pauseResume.click();
    const seq = ctx.timers.pending().filter((t) => t.delay === 1000);
    assert.strictEqual(seq.length >= 1, true);
    ctx.timers.run(seq[0].id);
    ctx.timers.run(ctx.timers.pending().filter((t) => t.delay === 1000)[0].id);
    ctx.timers.run(ctx.timers.pending().filter((t) => t.delay === 1000)[0].id);
    ctx.timers.run(ctx.timers.pending().filter((t) => t.delay === 700)[0].id);

    const rearmed = ctx.timers.pending().filter((t) => t.delay === 3000);
    assert.strictEqual(rearmed.length >= 1, true, "goal timer should be rearmed after resume");
    process.exit(0);
    """
)

_JS_TEST_4 = _SOURCES + textwrap.dedent(
    """
    const dom = makeBootDom();
    const ctx = loadApp(dom.document);
    bootToLaunch(dom, ctx);
    completeLaunch(ctx);
    dom.pauseButton.click();

    const ev = pointerEvent(1, 640, 360);
    dispatch(dom.canvas, "pointerdown", ev);
    assert.strictEqual(ctx.Travel.getSnapshot().dragging, false,
      "pointer should be ignored during pause");
    process.exit(0);
    """
)

_JS_TEST_5 = _SOURCES + textwrap.dedent(
    """
    const dom = makeBootDom();
    const ctx = loadApp(dom.document);
    bootToLaunch(dom, ctx);
    completeLaunch(ctx);

    const preFrames = ctx.frames.pending();
    assert.strictEqual(preFrames.length >= 1, true, "should have a travel frame pending before pause");

    dom.pauseButton.click();

    const postFrames = ctx.frames.pending();
    assert.strictEqual(postFrames.length, 0, "travel frame should be cancelled during pause");
    assert.strictEqual(ctx.Travel.getSnapshot().distance, 0,
      "distance should not change while paused");
    process.exit(0);
    """
)

_JS_TEST_6 = _SOURCES + textwrap.dedent(
    """
    const dom = makeBootDom();
    const ctx = loadApp(dom.document);
    bootToLaunch(dom, ctx);
    completeLaunch(ctx);
    dom.pauseButton.click();
    dom.pauseMenuButton.click();

    assert.strictEqual(ctx.State.getSnapshot().phase, "MISSION_SELECT");
    assert.strictEqual(dom.pauseOverlay.hidden, true);
    assert.strictEqual(dom.rootEl.getAttribute("data-pause-active"), "false");
    assert.strictEqual(dom.stage.hidden, true);
    process.exit(0);
    """
)

_JS_TEST_7 = _SOURCES + textwrap.dedent(
    """
    const st = freshSeaTurtle();
    st.start("sea-turtle");
    st.pointerDown(1, 760, 300);
    let snap = st.getSnapshot();
    assert.strictEqual(snap.pointerActive, true);
    assert.strictEqual(snap.tapStartArmed, false, "tapStartArmed is set by finishTap, not pointerDown");
    st.pauseCancel();
    snap = st.getSnapshot();
    assert.strictEqual(snap.pointerActive, false);
    assert.strictEqual(snap.tapStartArmed, false);
    assert.strictEqual(snap.active, true, "active should be preserved");

    const cr = freshCrab();
    cr.start("crab");
    cr.pointerDown(1, 760, 300);
    snap = cr.getSnapshot();
    assert.strictEqual(snap.pointerActive, true);
    assert.strictEqual(snap.holding, true);
    cr.pauseCancel();
    snap = cr.getSnapshot();
    assert.strictEqual(snap.pointerActive, false);
    assert.strictEqual(snap.holding, false);
    assert.strictEqual(snap.grabbed, false);
    assert.strictEqual(snap.active, true, "active should be preserved");

    const yw = freshYoungWhale();
    yw.start("young-whale");
    yw.pointerDown(1, 820, 260);
    snap = yw.getSnapshot();
    assert.strictEqual(snap.pointerActive, true);
    yw.pauseCancel();
    snap = yw.getSnapshot();
    assert.strictEqual(snap.pointerActive, false);
    assert.strictEqual(snap.active, true, "active should be preserved");
    process.exit(0);
    """
)

_JS_TEST_8 = _SOURCES + textwrap.dedent(
    """
    const dom = makeBootDom();
    const ctx = loadApp(dom.document);
    bootToLaunch(dom, ctx);
    completeLaunch(ctx);

    assert.notStrictEqual(dom.rootEl.getAttribute("data-pause-active"), "true",
      "should not be paused before click");
    dom.pauseButton.click();
    assert.strictEqual(dom.rootEl.getAttribute("data-pause-active"), "true");

    dom.pauseResume.click();
    const seq = ctx.timers.pending().filter((t) => t.delay === 1000);
    ctx.timers.run(seq[0].id);
    ctx.timers.run(ctx.timers.pending().filter((t) => t.delay === 1000)[0].id);
    ctx.timers.run(ctx.timers.pending().filter((t) => t.delay === 1000)[0].id);
    ctx.timers.run(ctx.timers.pending().filter((t) => t.delay === 700)[0].id);

    assert.strictEqual(dom.rootEl.getAttribute("data-pause-active"), "false");
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


def test_enter_pause_freezes_phase_and_shows_overlay():
    result = _run_js(_JS_TEST_1)
    assert result.returncode == 0, (
        f"JS failed (exit {result.returncode}):\n{result.stderr}\n{result.stdout}"
    )


def test_countdown_delays():
    result = _run_js(_JS_TEST_2)
    assert result.returncode == 0, (
        f"JS failed (exit {result.returncode}):\n{result.stderr}\n{result.stdout}"
    )


def test_timer_freeze_and_rearm():
    result = _run_js(_JS_TEST_3)
    assert result.returncode == 0, (
        f"JS failed (exit {result.returncode}):\n{result.stderr}\n{result.stdout}"
    )


def test_pause_blocks_pointer_events():
    result = _run_js(_JS_TEST_4)
    assert result.returncode == 0, (
        f"JS failed (exit {result.returncode}):\n{result.stderr}\n{result.stdout}"
    )


def test_travel_frame_skips_when_paused():
    result = _run_js(_JS_TEST_5)
    assert result.returncode == 0, (
        f"JS failed (exit {result.returncode}):\n{result.stderr}\n{result.stdout}"
    )


def test_exit_pause_to_menu():
    result = _run_js(_JS_TEST_6)
    assert result.returncode == 0, (
        f"JS failed (exit {result.returncode}):\n{result.stderr}\n{result.stdout}"
    )


def test_pause_cancel_clears_interaction_state():
    result = _run_js(_JS_TEST_7)
    assert result.returncode == 0, (
        f"JS failed (exit {result.returncode}):\n{result.stderr}\n{result.stdout}"
    )


def test_css_animation_pause_attribute():
    result = _run_js(_JS_TEST_8)
    assert result.returncode == 0, (
        f"JS failed (exit {result.returncode}):\n{result.stderr}\n{result.stdout}"
    )
