"""Behavioral tests for Ocean Rescue launch presentation and travel handoff.

Every JavaScript assertion runs the real tracked sources (``state.js``,
``missions.js``, ``gups.js``, ``launch.js``, and ``app.js``) through the
installed Node runtime in a fresh VM sandbox using a minimal fake DOM and a
deterministic fake timer queue. No npm packages, no browser automation, and no
separate JavaScript test file are used.
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_BIN = shutil.which("node")
if NODE_BIN is None:
    raise RuntimeError("Node executable not found on PATH")


_LAUNCH_BOOTSTRAP = textwrap.dedent(
    """\
    const fs = require("fs");
    const vm = require("vm");
    const assert = require("assert");

    const LAUNCH_SOURCE = fs.readFileSync(
      "domains/ocean-rescue/src/launch.js",
      "utf8"
    );

    function freshLaunch() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(LAUNCH_SOURCE, sandbox, { filename: "launch.js" });
      return sandbox.window.OceanRescue.Launch;
    }

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
    """
)

_APP_BOOTSTRAP = textwrap.dedent(
    """\
    const fs = require("fs");
    const vm = require("vm");
    const assert = require("assert");

    const STATE_SOURCE = fs.readFileSync("domains/ocean-rescue/src/state.js", "utf8");
    const MISSIONS_SOURCE = fs.readFileSync("domains/ocean-rescue/src/missions.js", "utf8");
    const GUPS_SOURCE = fs.readFileSync("domains/ocean-rescue/src/gups.js", "utf8");
    const LAUNCH_SOURCE = fs.readFileSync("domains/ocean-rescue/src/launch.js", "utf8");
    const APP_SOURCE = fs.readFileSync("domains/ocean-rescue/src/app.js", "utf8");

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
      const canvas = makeElement("canvas");

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

    function loadAppRaw(document, windowExtras) {
      const sandbox = {
        window: windowExtras || {},
        document,
      };
      vm.createContext(sandbox);
      vm.runInContext(STATE_SOURCE, sandbox, { filename: "state.js" });
      vm.runInContext(MISSIONS_SOURCE, sandbox, { filename: "missions.js" });
      vm.runInContext(GUPS_SOURCE, sandbox, { filename: "gups.js" });
      vm.runInContext(LAUNCH_SOURCE, sandbox, { filename: "launch.js" });
      vm.runInContext(APP_SOURCE, sandbox, { filename: "app.js" });
      return {
        sandbox,
        State: sandbox.window.OceanRescue.State,
        Missions: sandbox.window.OceanRescue.Missions,
        Gups: sandbox.window.OceanRescue.Gups,
        Launch: sandbox.window.OceanRescue.Launch,
        App: sandbox.window.OceanRescue.App,
      };
    }

    function loadApp(document) {
      const timers = makeTimerQueue();
      const ctx = loadAppRaw(document, {
        setTimeout: timers.setTimeout,
        clearTimeout: timers.clearTimeout,
      });
      ctx.timers = timers;
      return ctx;
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


def test_launch_catalog_public_contract_and_timing() -> None:
    harness = _LAUNCH_BOOTSTRAP + textwrap.dedent(
        """\
        const Launch = freshLaunch();

        const expected = [
          {
            missionId: "sea-turtle",
            briefing:
              "A sea turtle is trapped in a net. Let’s find it and cut the ropes!",
            goal: "Rescue the sea turtle!",
          },
          {
            missionId: "crab",
            briefing:
              "A crab is trapped under some rocks. Let’s move them with the grabber!",
            goal: "Help the trapped crab!",
          },
          {
            missionId: "young-whale",
            briefing:
              "A young whale’s path is blocked. Let’s tow the debris away!",
            goal: "Clear a path for the young whale!",
          },
        ];
        assert.strictEqual(Launch.Catalog.length, 3);
        for (let i = 0; i < Launch.Catalog.length; i += 1) {
          assert.deepStrictEqual(plain(Launch.Catalog[i]), expected[i]);
        }
        assert.deepStrictEqual(
          plain(Launch.Catalog.map((entry) => entry.missionId)),
          ["sea-turtle", "crab", "young-whale"]
        );

        assert.strictEqual(Object.isFrozen(Launch.Catalog), true);
        for (let i = 0; i < Launch.Catalog.length; i += 1) {
          assert.strictEqual(Object.isFrozen(Launch.Catalog[i]), true);
        }
        assertThrows(() => {
          Launch.Catalog.push({
            missionId: "dolphin",
            briefing: "Hacked",
            goal: "Hacked",
          });
        });
        assert.strictEqual(Launch.Catalog.length, 3);

        const expectedMembers = [
          "Catalog",
          "DurationMs",
          "GoalDurationMs",
          "getMissionContent",
        ];
        assert.deepStrictEqual(Object.keys(Launch).sort(), expectedMembers.slice().sort());
        assert.strictEqual(Object.isFrozen(Launch), true);

        assert.strictEqual(Launch.DurationMs, 6000);
        assert.strictEqual(Launch.GoalDurationMs, 3000);
        Launch.DurationMs = 9999;
        Launch.GoalDurationMs = 9999;
        assert.strictEqual(Launch.DurationMs, 6000);
        assert.strictEqual(Launch.GoalDurationMs, 3000);

        assert.strictEqual(Launch.getMissionContent("sea-turtle"), Launch.Catalog[0]);
        assert.strictEqual(Launch.getMissionContent("crab"), Launch.Catalog[1]);
        assert.strictEqual(Launch.getMissionContent("young-whale"), Launch.Catalog[2]);
        assert.strictEqual(Launch.getMissionContent("unknown"), null);
        assert.strictEqual(Launch.getMissionContent(""), null);
        assert.strictEqual(Launch.getMissionContent(undefined), null);
        assert.strictEqual(Launch.getMissionContent(null), null);
        assert.strictEqual(Launch.getMissionContent(42), null);
        assert.strictEqual(Launch.getMissionContent({}), null);

        const before = JSON.stringify(plain(Launch.Catalog));
        Launch.getMissionContent("sea-turtle");
        Launch.getMissionContent("unknown");
        assert.strictEqual(JSON.stringify(plain(Launch.Catalog)), before);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_launch_selected_gup_starts_exact_presentation() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToLaunch(dom, ctx, 2);

        assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
        assert.strictEqual(dom.launchSection.hidden, false);
        assert.strictEqual(dom.gupSection.hidden, true);
        assert.strictEqual(dom.launchGupName.textContent, "GUP-X");
        assert.strictEqual(dom.launchCompanion.textContent, "Peso:");
        assert.strictEqual(
          dom.launchBriefing.textContent,
          "A sea turtle is trapped in a net. Let’s find it and cut the ropes!"
        );
        assert.strictEqual(
          dom.launchSection.classList.contains("ocean-rescue-launch-active"),
          true
        );
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-sequence"), "active");
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-skipped"), "false");
        assert.strictEqual(dom.statusEl.textContent, "A sea turtle is trapped in a net. Let’s find it and cut the ropes!");

        assert.strictEqual(ctx.timers.pending().length, 1);
        assert.strictEqual(ctx.timers.pending()[0].delay, 6000);

        assert.strictEqual(dom.stage.hidden, true);
        assert.strictEqual(dom.goalBanner.hidden, true);
        assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_all_mission_briefings_and_goals_match_prd() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        const expected = [
          {
            missionId: "sea-turtle",
            companion: "Peso",
            briefing:
              "A sea turtle is trapped in a net. Let’s find it and cut the ropes!",
            goal: "Rescue the sea turtle!",
          },
          {
            missionId: "crab",
            companion: "Tweak",
            briefing:
              "A crab is trapped under some rocks. Let’s move them with the grabber!",
            goal: "Help the trapped crab!",
          },
          {
            missionId: "young-whale",
            companion: "Captain Barnacles",
            briefing:
              "A young whale’s path is blocked. Let’s tow the debris away!",
            goal: "Clear a path for the young whale!",
          },
        ];

        let ctx;
        for (let i = 0; i < expected.length; i += 1) {
          const dom = makeBootDom();
          ctx = loadApp(dom.document);
          assert.strictEqual(
            ctx.Missions.Catalog[i].companion,
            expected[i].companion
          );
          const content = ctx.Launch.getMissionContent(expected[i].missionId);
          assert.notStrictEqual(content, null);
          assert.strictEqual(content.briefing, expected[i].briefing);
          assert.strictEqual(content.goal, expected[i].goal);
          assert.strictEqual(content, ctx.Launch.Catalog[i]);
          assert.strictEqual(Object.isFrozen(content), true);
        }

        assert.strictEqual(ctx.Missions.isUnlocked("crab"), false);
        assert.strictEqual(ctx.Missions.isUnlocked("young-whale"), false);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_automatic_launch_completion_enters_travel_once() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToLaunch(dom, ctx, 2);

        const launchTimer = ctx.timers.pending()[0];
        assert.strictEqual(launchTimer.delay, 6000);
        ctx.timers.run(launchTimer.id);

        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        assert.strictEqual(dom.launchSection.hidden, true);
        assert.strictEqual(
          dom.launchSection.classList.contains("ocean-rescue-launch-active"),
          false
        );
        assert.strictEqual(dom.stage.hidden, false);
        assert.strictEqual(dom.stage.getAttribute("aria-hidden"), "false");
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-mission-id"), "sea-turtle");
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-gup-id"), "gup-x");
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-ready"), "true");
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-skipped"), "false");
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-ready"), null);
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-sequence"), null);
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-mission-id"), "sea-turtle");
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-gup-id"), "gup-x");

        assert.strictEqual(dom.goalBanner.hidden, false);
        assert.strictEqual(dom.goalBanner.textContent, "Rescue the sea turtle!");
        assert.strictEqual(dom.statusEl.textContent, "Travel ready: Rescue the sea turtle!");

        assert.strictEqual(ctx.timers.pending().length, 1);
        assert.strictEqual(ctx.timers.pending()[0].delay, 3000);

        launchTimer.fn();
        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        assert.strictEqual(dom.goalBanner.hidden, false);
        assert.strictEqual(dom.goalBanner.textContent, "Rescue the sea turtle!");
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-ready"), "true");
        assert.strictEqual(ctx.timers.pending().length, 1);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_surface_tap_skips_launch_and_stale_timer_is_ignored() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToLaunch(dom, ctx, 2);

        const launchTimer = ctx.timers.pending()[0];
        dom.launchSection.click();

        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        assert.strictEqual(dom.launchSection.hidden, true);
        assert.strictEqual(dom.stage.hidden, false);
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-skipped"), "true");
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-ready"), "true");
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-sequence"), null);
        assert.strictEqual(ctx.timers.pending().length, 1);
        assert.strictEqual(ctx.timers.pending()[0].delay, 3000);

        assert.strictEqual(dom.goalBanner.hidden, false);
        assert.strictEqual(dom.goalBanner.textContent, "Rescue the sea turtle!");
        assert.strictEqual(dom.statusEl.textContent, "Travel ready: Rescue the sea turtle!");

        launchTimer.fn();
        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        assert.strictEqual(dom.goalBanner.hidden, false);
        assert.strictEqual(dom.goalBanner.textContent, "Rescue the sea turtle!");
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-ready"), "true");
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-skipped"), "true");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_skip_button_completes_only_once() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const ctx = loadApp(dom.document);
        startLaunchToLaunch(dom, ctx, 2);

        dom.skipButton.click();

        assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        assert.strictEqual(ctx.State.getSnapshot().transitionLocked, false);
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-ready"), "true");
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-skipped"), "true");
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-sequence"), null);
        assert.strictEqual(dom.goalBanner.hidden, false);
        assert.strictEqual(dom.goalBanner.textContent, "Rescue the sea turtle!");
        assert.strictEqual(dom.statusEl.textContent, "Travel ready: Rescue the sea turtle!");
        assert.strictEqual(ctx.timers.pending().length, 1);
        assert.strictEqual(ctx.timers.pending()[0].delay, 3000);

        const phaseAfterFirst = ctx.State.getSnapshot().phase;
        const travelReady = dom.rootEl.getAttribute("data-travel-ready");
        const skipped = dom.rootEl.getAttribute("data-launch-skipped");
        const statusText = dom.statusEl.textContent;
        const goalVisible = dom.goalBanner.hidden;

        dom.skipButton.click();
        assert.strictEqual(ctx.State.getSnapshot().phase, phaseAfterFirst);
        assert.strictEqual(dom.rootEl.getAttribute("data-travel-ready"), travelReady);
        assert.strictEqual(dom.rootEl.getAttribute("data-launch-skipped"), skipped);
        assert.strictEqual(dom.statusEl.textContent, statusText);
        assert.strictEqual(dom.goalBanner.hidden, goalVisible);
        assert.strictEqual(ctx.timers.pending().length, 1);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_goal_banner_hides_after_exact_duration() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        function assertNormalCompletionGoalDismissal() {
          const dom = makeBootDom();
          const ctx = loadApp(dom.document);
          startLaunchToLaunch(dom, ctx, 2);
          ctx.timers.run(ctx.timers.pending()[0].id);

          assert.strictEqual(dom.goalBanner.hidden, false);
          assert.strictEqual(dom.goalBanner.textContent, "Rescue the sea turtle!");
          const goalTimer = ctx.timers.pending()[0];
          assert.strictEqual(goalTimer.delay, 3000);

          ctx.timers.run(goalTimer.id);
          assert.strictEqual(dom.goalBanner.hidden, true);
          assert.strictEqual(dom.goalBanner.textContent, "");
          assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
          assert.strictEqual(ctx.timers.pending().length, 0);
        }

        function assertSkippedCompletionGoalDismissal() {
          const dom = makeBootDom();
          const ctx = loadApp(dom.document);
          startLaunchToLaunch(dom, ctx, 2);
          dom.launchSection.click();

          assert.strictEqual(dom.goalBanner.hidden, false);
          assert.strictEqual(dom.goalBanner.textContent, "Rescue the sea turtle!");
          const goalTimer = ctx.timers.pending()[0];
          assert.strictEqual(goalTimer.delay, 3000);

          ctx.timers.run(goalTimer.id);
          assert.strictEqual(dom.goalBanner.hidden, true);
          assert.strictEqual(dom.goalBanner.textContent, "");
          assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
          assert.strictEqual(ctx.timers.pending().length, 0);
        }

        function assertStaleGoalCallbackCannotHideNewerBanner() {
          const dom = makeBootDom();
          const ctx = loadApp(dom.document);
          startLaunchToLaunch(dom, ctx, 2);
          const firstLaunchTimer = ctx.timers.pending()[0];
          ctx.timers.run(firstLaunchTimer.id);
          const firstGoalTimer = ctx.timers.pending()[0];

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
          assert.strictEqual(dom.goalBanner.hidden, true);
          assert.strictEqual(dom.launchSection.hidden, false);
          assert.strictEqual(ctx.timers.pending().length, 1);
          assert.strictEqual(ctx.timers.pending()[0].delay, 6000);

          const secondLaunchTimer = ctx.timers.pending()[0];
          ctx.timers.run(secondLaunchTimer.id);
          assert.strictEqual(dom.goalBanner.hidden, false);
          assert.strictEqual(dom.goalBanner.textContent, "Rescue the sea turtle!");
          const secondGoalTimer = ctx.timers.pending()[0];
          assert.strictEqual(secondGoalTimer.delay, 3000);

          firstGoalTimer.fn();
          assert.strictEqual(dom.goalBanner.hidden, false);
          assert.strictEqual(dom.goalBanner.textContent, "Rescue the sea turtle!");
          assert.strictEqual(ctx.timers.pending().length, 1);

          ctx.timers.run(secondGoalTimer.id);
          assert.strictEqual(dom.goalBanner.hidden, true);
          assert.strictEqual(dom.goalBanner.textContent, "");
          assert.strictEqual(ctx.State.getSnapshot().phase, "TRAVEL");
        }

        assertNormalCompletionGoalDismissal();
        assertSkippedCompletionGoalDismissal();
        assertStaleGoalCallbackCannotHideNewerBanner();
        """
    )
    _assert_node_ok(_run_node(harness))


def test_missing_optional_launch_dom_and_timer_api_are_safe() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        function assertMissingLaunchDomIsSafe() {
          const rootEl = makeElement("main");
          const statusEl = makeElement("p");
          const missionSection = makeElement("section");
          const missionList = makeElement("div");
          const gupSection = makeElement("section");
          const gupMission = makeElement("p");
          const gupList = makeElement("div");
          const actions = makeElement("div");
          const gupBack = makeElement("button");
          const gupLaunch = makeElement("button");
          actions.appendChild(gupBack);
          actions.appendChild(gupLaunch);
          gupSection.appendChild(gupMission);
          gupSection.appendChild(gupList);
          gupSection.appendChild(actions);
          rootEl.appendChild(missionSection);
          rootEl.appendChild(gupSection);
          const document2 = makeDocument({
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
          });

          const ctx = loadAppRaw(document2);
          document2.domLoadedHandler();
          assert.strictEqual(ctx.App.boot(), true);
          assert.strictEqual(ctx.App.selectMission("sea-turtle"), true);
          assert.strictEqual(ctx.App.selectGup("gup-x"), true);
          assert.strictEqual(ctx.App.launchSelectedGup(), true);
          assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
          assert.strictEqual(rootEl.getAttribute("data-launch-mission-id"), "sea-turtle");
          assert.strictEqual(rootEl.getAttribute("data-launch-gup-id"), "gup-x");
          assert.strictEqual(rootEl.getAttribute("data-launch-ready"), "true");
          assert.strictEqual(rootEl.getAttribute("data-travel-ready"), null);
        }

        function assertMissingTimerApisAreSafe() {
          const dom = makeBootDom();
          const ctx = loadAppRaw(dom.document);
          dom.document.domLoadedHandler();
          assert.strictEqual(ctx.App.boot(), true);
          dom.missionList.children[0].click();
          dom.gupList.children[2].click();
          assert.strictEqual(ctx.App.launchSelectedGup(), true);
          assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
          assert.strictEqual(dom.launchSection.hidden, false);
          assert.strictEqual(dom.launchGupName.textContent, "GUP-X");
          assert.strictEqual(
            dom.launchBriefing.textContent,
            "A sea turtle is trapped in a net. Let’s find it and cut the ropes!"
          );
          assert.strictEqual(dom.stage.hidden, true);
          assert.strictEqual(dom.goalBanner.hidden, true);
          assert.strictEqual(ctx.State.getSnapshot().phase, "LAUNCH");
        }

        assertMissingLaunchDomIsSafe();
        assertMissingTimerApisAreSafe();
        """
    )
    _assert_node_ok(_run_node(harness))
