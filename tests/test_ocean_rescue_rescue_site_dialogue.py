"""Behavioral tests for the Ocean Rescue rescue-site English dialogue.

The rescue site is where the child meets the animal that needs help. The
animal has to say so, in English, in its own speech bubble, and the travel
chrome of the previous stage must not stay on top of the rescue scene.

Every JavaScript assertion runs the real tracked sources (``state.js``,
``missions.js``, ``gups.js``, ``launch.js``, ``travel.js``, ``terrain.js``,
``rescue.js``, ``pointer-input.js``, ``sea-turtle.js`` and ``app.js``) through
the installed Node runtime in a fresh VM sandbox using a minimal fake DOM, a
fake canvas 2D context, a deterministic fake timer queue, a deterministic fake
animation-frame queue, and a recording speech-synthesis stub. No npm
packages, no browser automation, and no real-time sleeps are used.

Covered defects:

- the rescue target never said anything: there was no speech bubble and no
  English line for the trapped animal;
- the spoken dialogue used a Korean utterance language for English copy, so
  the rescue request was pronounced with the wrong voice;
- the travel instruction line and the "distance to rescue site" meter stayed
  on screen during the rescue site;
- the rescue handoff had two different owners (the travel loop called a
  private arrival copy while the installed controller exposed a public one),
  so the rescue site could open with different rules depending on the lane.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_BIN: str = shutil.which("node") or ""
if not NODE_BIN:
    raise RuntimeError("Node executable not found on PATH")

SRC_DIR = REPO_ROOT / "domains" / "ocean-rescue" / "src"
LEGACY_APP = SRC_DIR / "app.js"
TYPED_CONTROLLER = SRC_DIR / "controllers" / "rescue-site-tutorial.ts"


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
    const POINTER_INPUT_SOURCE = fs.readFileSync("domains/ocean-rescue/src/pointer-input.js", "utf8");
    const SEA_TURTLE_SOURCE = fs.readFileSync("domains/ocean-rescue/src/sea-turtle.js", "utf8");
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
        scrollIntoView() {},
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
      const record = (name) =>
        function (...args) {
          calls.push([name, ...args]);
        };
      ctx.save = record("save");
      ctx.restore = record("restore");
      ctx.translate = record("translate");
      ctx.rotate = record("rotate");
      ctx.scale = record("scale");
      ctx.clearRect = record("clearRect");
      ctx.fillRect = record("fillRect");
      ctx.beginPath = record("beginPath");
      ctx.closePath = record("closePath");
      ctx.arc = record("arc");
      ctx.fill = record("fill");
      ctx.stroke = record("stroke");
      ctx.moveTo = record("moveTo");
      ctx.lineTo = record("lineTo");
      ctx.quadraticCurveTo = record("quadraticCurveTo");
      ctx.bezierCurveTo = record("bezierCurveTo");
      ctx.setLineDash = record("setLineDash");
      ctx.fillText = record("fillText");
      return ctx;
    }

    function makeCanvasElement() {
      const el = makeElement("canvas");
      el.width = 1280;
      el.height = 720;
      el.rect = { top: 0, left: 0, width: 1280, height: 720 };
      el._context = makeContext();
      el.getContext = function (type) {
        return type === "2d" ? el._context : null;
      };
      el.getBoundingClientRect = function () {
        return el.rect;
      };
      el.setPointerCapture = function () {};
      el.releasePointerCapture = function () {};
      return el;
    }

    function makeSpeechRecorder() {
      const utterances = [];
      const recorder = {
        utterances,
        speechSynthesis: {
          speak(utterance) {
            utterances.push({
              text: utterance.text,
              lang: utterance.lang,
              pitch: utterance.pitch,
              rate: utterance.rate,
            });
            if (typeof utterance.onend === "function") {
              utterance.onend();
            }
          },
          cancel() {},
          speaking: false,
        },
        SpeechSynthesisUtterance: function (text) {
          this.text = text;
          this.lang = "";
          this.pitch = 1;
          this.rate = 1;
          this.volume = 1;
        },
      };
      return recorder;
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
      const gupList = makeElement("div");
      const gupBack = makeElement("button");
      const gupLaunch = makeElement("button");
      const launchSection = makeElement("section");
      launchSection.hidden = true;
      const launchVisual = makeElement("div");
      const launchGupName = makeElement("span");
      const launchCompanion = makeElement("p");
      const launchBriefing = makeElement("p");
      const launchSkip = makeElement("button");
      const goalBanner = makeElement("div");
      goalBanner.hidden = true;
      const stage = makeElement("section");
      stage.hidden = true;
      const canvas = makeCanvasElement();
      const travelHelp = makeElement("p");
      const travelProgress = makeElement("div");
      travelProgress.hidden = true;
      const travelProgressBar = makeElement("progress");
      const travelProgressValue = makeElement("span");
      const travelScan = makeElement("button");
      travelScan.hidden = true;

      const rescueOverlay = makeElement("section");
      rescueOverlay.hidden = true;
      const rescueTitle = makeElement("h2");
      const rescueCompanion = makeElement("p");
      const rescueSituation = makeElement("p");
      const rescueReady = makeElement("div");
      rescueReady.hidden = true;
      const rescueBubbles = makeElement("div");
      rescueBubbles.hidden = true;
      const companionBubble = makeElement("div");
      const companionLine = makeElement("p");
      const companionName = makeElement("span");
      const targetBubble = makeElement("div");
      const targetLine = makeElement("p");
      const targetName = makeElement("span");
      const rescueTutorial = makeElement("div");
      rescueTutorial.hidden = true;
      const rescueInstruction = makeElement("p");
      const rescueHand = makeElement("div");
      const rescueProgress = makeElement("p");

      missionSection.appendChild(missionList);
      gupSection.appendChild(gupList);
      gupSection.appendChild(gupBack);
      gupSection.appendChild(gupLaunch);
      launchVisual.appendChild(launchGupName);
      launchSection.appendChild(launchVisual);
      launchSection.appendChild(launchCompanion);
      launchSection.appendChild(launchBriefing);
      launchSection.appendChild(launchSkip);
      stage.appendChild(canvas);
      stage.appendChild(travelHelp);
      stage.appendChild(travelProgress);
      travelProgress.appendChild(travelProgressBar);
      travelProgress.appendChild(travelProgressValue);
      stage.appendChild(travelScan);
      companionBubble.appendChild(companionLine);
      companionBubble.appendChild(companionName);
      targetBubble.appendChild(targetLine);
      targetBubble.appendChild(targetName);
      rescueBubbles.appendChild(companionBubble);
      rescueBubbles.appendChild(targetBubble);
      rescueOverlay.appendChild(rescueTitle);
      rescueOverlay.appendChild(rescueCompanion);
      rescueOverlay.appendChild(rescueSituation);
      rescueOverlay.appendChild(rescueBubbles);
      rescueOverlay.appendChild(rescueReady);
      rescueOverlay.appendChild(rescueTutorial);
      rescueTutorial.appendChild(rescueInstruction);
      rescueTutorial.appendChild(rescueHand);
      rescueOverlay.appendChild(rescueProgress);
      stage.appendChild(rescueOverlay);
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
        "ocean-rescue-gup-list": gupList,
        "ocean-rescue-gup-actions": gupSection,
        "ocean-rescue-gup-back": gupBack,
        "ocean-rescue-gup-launch": gupLaunch,
        "ocean-rescue-launch": launchSection,
        "ocean-rescue-launch-visual": launchVisual,
        "ocean-rescue-launch-gup-name": launchGupName,
        "ocean-rescue-launch-companion": launchCompanion,
        "ocean-rescue-launch-briefing": launchBriefing,
        "ocean-rescue-launch-skip": launchSkip,
        "ocean-rescue-goal-banner": goalBanner,
        "ocean-rescue-stage": stage,
        "ocean-rescue-canvas": canvas,
        "ocean-rescue-travel-help": travelHelp,
        "ocean-rescue-travel-progress": travelProgress,
        "ocean-rescue-travel-progress-bar": travelProgressBar,
        "ocean-rescue-travel-progress-value": travelProgressValue,
        "ocean-rescue-travel-scan": travelScan,
        "ocean-rescue-rescue-overlay": rescueOverlay,
        "ocean-rescue-rescue-companion": rescueCompanion,
        "ocean-rescue-rescue-situation": rescueSituation,
        "ocean-rescue-rescue-bubbles": rescueBubbles,
        "ocean-rescue-rescue-companion-bubble": companionBubble,
        "ocean-rescue-rescue-companion-line": companionLine,
        "ocean-rescue-rescue-companion-name": companionName,
        "ocean-rescue-rescue-target-bubble": targetBubble,
        "ocean-rescue-rescue-target-line": targetLine,
        "ocean-rescue-rescue-target-name": targetName,
        "ocean-rescue-rescue-ready": rescueReady,
        "ocean-rescue-rescue-tutorial": rescueTutorial,
        "ocean-rescue-rescue-instruction": rescueInstruction,
        "ocean-rescue-rescue-hand": rescueHand,
        "ocean-rescue-rescue-progress": rescueProgress,
      };

      return {
        document: makeDocument(elements),
        rootEl,
        statusEl,
        missionList,
        gupList,
        gupLaunch,
        stage,
        canvas,
        travelHelp,
        travelProgress,
        travelScan,
        rescueOverlay,
        rescueCompanion,
        rescueSituation,
        rescueBubbles,
        companionLine,
        companionName,
        targetLine,
        targetName,
        rescueReady,
        rescueTutorial,
        rescueInstruction,
        rescueProgress,
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
      vm.runInContext(RESCUE_SOURCE, sandbox, { filename: "rescue.js" });
      vm.runInContext(POINTER_INPUT_SOURCE, sandbox, { filename: "pointer-input.js" });
      vm.runInContext(SEA_TURTLE_SOURCE, sandbox, { filename: "sea-turtle.js" });
      vm.runInContext(APP_SOURCE, sandbox, { filename: "app.js" });
      const OceanRescue = sandbox.window.OceanRescue;
      return {
        sandbox,
        timers,
        frames,
        State: OceanRescue.State,
        Missions: OceanRescue.Missions,
        Gups: OceanRescue.Gups,
        Travel: OceanRescue.Travel,
        Rescue: OceanRescue.Rescue,
        SeaTurtle: OceanRescue.SeaTurtle,
        Audio: OceanRescue.Audio,
        App: OceanRescue.App,
      };
    }

    function startLaunchToTravel(dom, ctx) {
      dom.document.domLoadedHandler();
      assert.strictEqual(ctx.App.boot(), true);
      dom.missionList.children[0].click();
      dom.gupList.children[0].click();
      dom.gupLaunch.click();
      assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
      // The launch stage queues both the spoken briefing and the travel
      // hand-over timer, so drain the queue until the travel phase starts.
      for (let guard = 0; guard < 50; guard += 1) {
        if (ctx.State.getSnapshot().phase === "TRAVEL") {
          break;
        }
        const pending = ctx.timers.pending();
        assert.strictEqual(pending.length >= 1, true);
        ctx.timers.run(pending[0].id);
      }
      assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
    }

    function runToArrival(ctx, maxFrames) {
      let frameTime = 1000;
      let frames = 0;
      for (;;) {
        const pending = ctx.frames.pending();
        if (pending.length === 0) {
          return { arrived: false, frames };
        }
        frames += 1;
        if (frames > maxFrames) {
          return { arrived: false, frames };
        }
        ctx.frames.run(pending[0].id, frameTime);
        frameTime += 1000;
        if (ctx.State.getSnapshot().phase !== "TRAVEL") {
          return { arrived: true, frames };
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

    function drainZeroTimers(ctx) {
      for (let guard = 0; guard < 50; guard += 1) {
        const zero = ctx.timers.pending().filter((t) => t.delay === 0);
        if (zero.length === 0) {
          return;
        }
        ctx.timers.run(zero[0].id);
      }
      throw new Error("speech queue did not settle");
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


def test_rescue_catalog_owns_the_english_rescue_dialogue() -> None:
    """The rescue catalogue owns one English line per rescue-site speaker."""
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document, {});

        const expected = {
          "sea-turtle": {
            target: "Help! I am tangled in ropes. Please cut them and save me!",
            companion: "I found a sea turtle tangled in ropes. Let\\u2019s cut them free!"
          },
          "crab": {
            target: "Help! Rocks are on my back. Please move them and save me!",
            companion: "A crab is stuck under rocks. Let\\u2019s lift them and set it free!"
          },
          "young-whale": {
            target: "Help! Trash blocks my way. Please tow it away and save me!",
            companion: "A young whale is stuck behind debris. Let\\u2019s tow it away!"
          }
        };

        for (const missionId of Object.keys(expected)) {
          const content = ctx.Rescue.getMissionContent(missionId);
          assert.ok(content, "missing mission content for " + missionId);
          assert.strictEqual(content.targetLine, expected[missionId].target);
          assert.strictEqual(content.companionLine, expected[missionId].companion);
          assert.strictEqual(
            ctx.Rescue.getDialogueLine(missionId, "target"),
            expected[missionId].target
          );
          assert.strictEqual(
            ctx.Rescue.getDialogueLine(missionId, "companion"),
            expected[missionId].companion
          );
          // The rescue request must be plain English, not Korean copy.
          assert.strictEqual(/[\\uac00-\\ud7af]/.test(content.targetLine), false);
          assert.strictEqual(/[\\uac00-\\ud7af]/.test(content.companionLine), false);
          assert.strictEqual(content.targetLine.indexOf("!") > 0, true);
        }

        assert.strictEqual(ctx.Rescue.getDialogueLine("unknown-mission", "target"), null);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_rescue_site_shows_the_target_speech_bubble_and_hides_travel_chrome() -> None:
    """The rescue target shouts for help in a bubble; travel chrome disappears."""
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const speech = makeSpeechRecorder();
        const ctx = loadApp(dom.document, {
          speechSynthesis: speech.speechSynthesis,
          SpeechSynthesisUtterance: speech.SpeechSynthesisUtterance,
        });

        startLaunchToTravel(dom, ctx);
        // The travel stage owns its own instruction line and distance meter.
        assert.strictEqual(dom.travelHelp.hidden, false);
        assert.strictEqual(dom.travelProgress.hidden, false);

        const result = runToArrival(ctx, 4000);
        assert.strictEqual(result.arrived, true);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SITE_TRANSITION");

        // The travel chrome must not survive into the rescue site.
        assert.strictEqual(dom.travelHelp.hidden, true);
        assert.strictEqual(dom.travelProgress.hidden, true);
        assert.strictEqual(dom.travelScan.hidden, true);

        // The rescue target asks for help in an English speech bubble.
        assert.strictEqual(dom.rescueBubbles.hidden, false);
        const content = ctx.Rescue.getMissionContent("sea-turtle");
        assert.strictEqual(dom.targetLine.textContent, content.targetLine);
        assert.strictEqual(dom.targetName.textContent, "Sea turtle");
        assert.strictEqual(dom.companionLine.textContent, content.companionLine);
        assert.strictEqual(dom.companionName.textContent, "Peso");

        // Both lines are spoken in English, the target first.
        drainZeroTimers(ctx);
        const spoken = speech.utterances.map((u) => u.text);
        assert.strictEqual(
          spoken.indexOf(content.targetLine) < spoken.indexOf(content.companionLine),
          true,
          "the target must shout before the companion answers"
        );
        for (const utterance of speech.utterances) {
          if (
            utterance.text === content.targetLine ||
            utterance.text === content.companionLine
          ) {
            assert.strictEqual(utterance.lang, "en-US");
          }
        }
        const targetUtterance = speech.utterances.find(
          (u) => u.text === content.targetLine
        );
        assert.ok(targetUtterance);
        const companionUtterance = speech.utterances.find(
          (u) => u.text === content.companionLine
        );
        assert.ok(companionUtterance);
        assert.strictEqual(
          targetUtterance.pitch !== companionUtterance.pitch,
          true,
          "the target and the companion must use different voices"
        );
        """
    )
    _assert_node_ok(_run_node(harness))


def test_rescue_dialogue_is_cleared_when_the_rescue_is_cancelled() -> None:
    """Leaving the rescue site must not leave a stale speech bubble behind."""
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const speech = makeSpeechRecorder();
        const ctx = loadApp(dom.document, {
          speechSynthesis: speech.speechSynthesis,
          SpeechSynthesisUtterance: speech.SpeechSynthesisUtterance,
        });

        startLaunchToTravel(dom, ctx);
        const result = runToArrival(ctx, 4000);
        assert.strictEqual(result.arrived, true);
        assert.strictEqual(dom.rescueBubbles.hidden, false);

        assert.strictEqual(ctx.App.cancelRescueSiteRuntime(), true);
        assert.strictEqual(dom.rescueBubbles.hidden, true);
        assert.strictEqual(dom.targetLine.textContent, "");
        assert.strictEqual(dom.companionLine.textContent, "");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_rescue_interaction_still_works_after_the_dialogue_refactor() -> None:
    """The rescue site stays playable: a rope drag still frees rope 1."""
    harness = _BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document, {});

        startLaunchToTravel(dom, ctx);
        const result = runToArrival(ctx, 4000);
        assert.strictEqual(result.arrived, true);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_SITE_TRANSITION");

        const transitionTimer = lastPendingTimer(ctx);
        assert.strictEqual(transitionTimer.delay, 1500);
        ctx.timers.run(transitionTimer.id);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_TUTORIAL");
        assert.strictEqual(dom.rescueInstruction.textContent, "Start here. Follow the rope to the end!");

        const tutorialTimer = lastPendingTimer(ctx);
        assert.strictEqual(tutorialTimer.delay, 3000);
        ctx.timers.run(tutorialTimer.id);
        assert.strictEqual(ctx.State.getSnapshot().phase, "RESCUE_ACTIVE");
        assert.strictEqual(dom.rootEl.getAttribute("data-rescue-input"), "enabled");

        // Drag rope 1 from its start to its end.
        dispatch(dom.canvas, "pointerdown", pointerEvent(7, 760, 300));
        dispatch(dom.canvas, "pointermove", pointerEvent(7, 900, 315));
        dispatch(dom.canvas, "pointermove", pointerEvent(7, 1040, 330));
        dispatch(dom.canvas, "pointerup", pointerEvent(7, 1040, 330));

        const snapshot = ctx.SeaTurtle.getSnapshot();
        assert.strictEqual(snapshot.completedRopeIds.length, 1);
        assert.strictEqual(snapshot.feedback, "success");

        // The success feedback hands over to the next rope.
        const feedbackTimer = timerWithDelay(ctx, 400);
        ctx.timers.run(feedbackTimer.id);
        const afterFeedback = ctx.SeaTurtle.getSnapshot();
        assert.strictEqual(afterFeedback.activeRopeId, "rope-2");
        assert.strictEqual(afterFeedback.completedRopeIds.length, 1);
        """
    )
    _assert_node_ok(_run_node(harness))


def _legacy_app_export_keys() -> set[str]:
    """Return the public keys of the legacy ``App`` object literal."""
    text = LEGACY_APP.read_text(encoding="utf-8")
    start = text.index("var App = {")
    end = text.index("\n  };", start)
    block = text[start:end]
    return set(re.findall(r"^    ([A-Za-z_][A-Za-z0-9_]*):", block, re.MULTILINE))


def test_legacy_app_exposes_the_rescue_speech_and_travel_chrome_bridges() -> None:
    """The typed controller talks to the legacy app through published bridges."""
    keys = _legacy_app_export_keys()
    for bridge in (
        "showRescueSpeech",
        "hideRescueSpeech",
        "hideTravelChrome",
        "showTravelChrome",
        "handoffTravelArrival",
    ):
        assert bridge in keys, f"legacy App must publish {bridge}"


def _typed_controller_bridges() -> set[str]:
    """Return the app keys the typed controllers install on the shared app."""
    bridges: set[str] = set()
    for path in sorted((SRC_DIR / "controllers").glob("*.ts")):
        text = path.read_text(encoding="utf-8")
        bridges.update(re.findall(r"\bcontroller\.([A-Za-z_][A-Za-z0-9_]*)\s*=", text))
    return bridges


def test_typed_controller_only_calls_host_bridges_the_legacy_app_publishes() -> None:
    """Every ``host.*`` call of the typed controller resolves on the shared app."""
    published = _legacy_app_export_keys() | _typed_controller_bridges()
    controller = TYPED_CONTROLLER.read_text(encoding="utf-8")
    used = set(re.findall(r"\bhost\.([A-Za-z_][A-Za-z0-9_]*)\s*\(", controller))
    missing = sorted(name for name in used if name not in published)
    assert missing == [], f"typed controller calls missing host bridges: {missing}"


def test_the_travel_loop_hands_the_arrival_over_through_the_public_bridge() -> None:
    """The travel loop must not call a private arrival copy any more."""
    text = LEGACY_APP.read_text(encoding="utf-8")
    assert "App.handoffTravelArrival()" in text
    assert "tryBeginRescueArrival();" not in text.replace(
        "function tryBeginRescueArrival()", ""
    ).replace("return tryBeginRescueArrival", "")
