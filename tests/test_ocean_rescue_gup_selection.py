"""Behavioral tests for Ocean Rescue GUP selection and the launch transition.

Every JavaScript assertion runs the real tracked sources (``state.js``,
``missions.js``, ``gups.js``, and ``app.js``) through the installed Node runtime
in a fresh VM sandbox. No npm packages and no separate JavaScript test file are
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

_GUPS_BOOTSTRAP = textwrap.dedent(
    """\
    const fs = require("fs");
    const vm = require("vm");
    const assert = require("assert");

    const GUPS_SOURCE = fs.readFileSync("domains/ocean-rescue/src/gups.js", "utf8");

    function freshGups() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(GUPS_SOURCE, sandbox, { filename: "gups.js" });
      return sandbox.window.OceanRescue.Gups;
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
    const POINTER_INPUT_SOURCE = fs.readFileSync("domains/ocean-rescue/src/pointer-input.js", "utf8");
    const APP_SOURCE = fs.readFileSync("domains/ocean-rescue/src/app.js", "utf8");

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
        listeners: {},
        scrollIntoViewCalls: 0,
        appendChild(child) {
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
          list.forEach((fn) => fn());
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
      const rootEl = {
        _ready: "false",
        attributes: {},
        getAttribute(name) {
          if (name === "data-ocean-rescue-ready") {
            return this._ready;
          }
          return Object.prototype.hasOwnProperty.call(this.attributes, name)
            ? this.attributes[name]
            : null;
        },
        setAttribute(name, value) {
          if (name === "data-ocean-rescue-ready") {
            this._ready = String(value);
          } else {
            this.attributes[name] = String(value);
          }
        },
        removeAttribute(name) {
          delete this.attributes[name];
        },
      };
      const statusEl = { textContent: null };
      const missionSection = makeElement("section");
      const missionList = makeElement("div");
      const gupSection = makeElement("section");
      gupSection.hidden = true;
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
        gupBack,
        gupLaunch,
      };
    }

    function loadApp(document) {
      const sandbox = { window: {}, document };
      vm.createContext(sandbox);
      vm.runInContext(STATE_SOURCE, sandbox, { filename: "state.js" });
      vm.runInContext(MISSIONS_SOURCE, sandbox, { filename: "missions.js" });
      vm.runInContext(GUPS_SOURCE, sandbox, { filename: "gups.js" });
      vm.runInContext(POINTER_INPUT_SOURCE, sandbox, { filename: "pointer-input.js" });
      vm.runInContext(APP_SOURCE, sandbox, { filename: "app.js" });
      return {
        sandbox,
        State: sandbox.window.OceanRescue.State,
        Missions: sandbox.window.OceanRescue.Missions,
        Gups: sandbox.window.OceanRescue.Gups,
        App: sandbox.window.OceanRescue.App,
      };
    }

    function snap(State) {
      const s = State.getSnapshot();
      return {
        phase: s.phase,
        ready: s.ready,
        transitionLocked: s.transitionLocked,
        pendingPhase: s.pendingPhase,
      };
    }

    function plain(value) {
      return JSON.parse(JSON.stringify(value));
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


def test_gup_catalog_and_public_contract() -> None:
    harness = _GUPS_BOOTSTRAP + textwrap.dedent(
        """\
        const Gups = freshGups();

        const expectedCatalog = [
          {
            id: "gup-c",
            name: "GUP-C",
            description: "Yellow rescue sub",
          },
          {
            id: "gup-i",
            name: "GUP-I",
            description: "White and blue rescue sub",
          },
          {
            id: "gup-x",
            name: "GUP-X",
            description: "Red rescue sub",
          },
        ];
        assert.strictEqual(Gups.Catalog.length, 3);
        for (let i = 0; i < Gups.Catalog.length; i += 1) {
          assert.deepStrictEqual(plain(Gups.Catalog[i]), expectedCatalog[i]);
        }
        assert.strictEqual(Object.isFrozen(Gups.Catalog), true);
        for (let i = 0; i < Gups.Catalog.length; i += 1) {
          assert.strictEqual(Object.isFrozen(Gups.Catalog[i]), true);
        }

        const expectedMembers = [
          "Catalog",
          "confirmSelection",
          "getSnapshot",
          "isValidGup",
          "prepareSelection",
          "selectGup",
        ];
        assert.deepStrictEqual(Object.keys(Gups).sort(), expectedMembers.slice().sort());
        assert.strictEqual(Object.isFrozen(Gups), true);

        assert.deepStrictEqual(plain(Gups.getSnapshot()), {
          selectedGupId: "gup-c",
          lastGupId: "gup-c",
        });
        """
    )
    _assert_node_ok(_run_node(harness))


def test_gup_selection_and_last_gup_contract() -> None:
    harness = _GUPS_BOOTSTRAP + textwrap.dedent(
        """\
        const Gups = freshGups();

        assert.strictEqual(Gups.getSnapshot().selectedGupId, "gup-c");
        assert.strictEqual(Gups.getSnapshot().lastGupId, "gup-c");

        assert.strictEqual(Gups.selectGup("gup-i"), true);
        assert.strictEqual(Gups.getSnapshot().selectedGupId, "gup-i");
        assert.strictEqual(Gups.getSnapshot().lastGupId, "gup-c");
        assert.strictEqual(Gups.selectGup("gup-i"), true);
        assert.strictEqual(Gups.getSnapshot().selectedGupId, "gup-i");

        assert.strictEqual(Gups.prepareSelection(), "gup-c");
        assert.strictEqual(Gups.getSnapshot().selectedGupId, "gup-c");
        assert.strictEqual(Gups.getSnapshot().lastGupId, "gup-c");
        assert.strictEqual(Gups.prepareSelection(), "gup-c");

        assert.strictEqual(Gups.selectGup("gup-x"), true);
        assert.strictEqual(Gups.confirmSelection(), "gup-x");
        assert.strictEqual(Gups.getSnapshot().lastGupId, "gup-x");
        assert.strictEqual(Gups.getSnapshot().selectedGupId, "gup-x");

        assert.strictEqual(Gups.prepareSelection(), "gup-x");
        assert.strictEqual(Gups.getSnapshot().selectedGupId, "gup-x");
        assert.strictEqual(Gups.getSnapshot().lastGupId, "gup-x");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_invalid_gup_and_snapshot_immutability() -> None:
    harness = _GUPS_BOOTSTRAP + textwrap.dedent(
        """\
        const Gups = freshGups();
        const expected = {
          selectedGupId: "gup-c",
          lastGupId: "gup-c",
        };

        assert.strictEqual(Gups.isValidGup("gup-c"), true);
        assert.strictEqual(Gups.isValidGup("gup-i"), true);
        assert.strictEqual(Gups.isValidGup("gup-x"), true);
        assert.strictEqual(Gups.isValidGup("unknown"), false);
        assert.strictEqual(Gups.isValidGup(""), false);
        assert.strictEqual(Gups.isValidGup(undefined), false);
        assert.strictEqual(Gups.isValidGup(null), false);
        assert.strictEqual(Gups.isValidGup({}), false);
        assert.strictEqual(Gups.isValidGup(1), false);

        assert.strictEqual(Gups.selectGup("unknown"), false);
        assert.strictEqual(Gups.selectGup(""), false);
        assert.strictEqual(Gups.selectGup(undefined), false);
        assert.strictEqual(Gups.selectGup(null), false);
        assert.strictEqual(Gups.selectGup({}), false);
        assert.strictEqual(Gups.selectGup(1), false);
        assert.deepStrictEqual(plain(Gups.getSnapshot()), expected);

        const snapshotA = Gups.getSnapshot();
        const snapshotB = Gups.getSnapshot();
        assert.notStrictEqual(snapshotA, snapshotB);
        assert.strictEqual(Object.isFrozen(snapshotA), true);
        assert.strictEqual(Object.isFrozen(snapshotB), true);
        snapshotA.selectedGupId = "gup-x";
        snapshotA.lastGupId = "gup-x";
        snapshotB.selectedGupId = "gup-i";
        assert.deepStrictEqual(plain(Gups.getSnapshot()), expected);

        Gups.Catalog[0].name = "HACKED";
        Gups.Catalog[0].description = "HACKED";
        assertThrows(() => {
          Gups.Catalog.push({
            id: "gup-h",
            name: "GUP-H",
            description: "Hacked sub",
          });
        });
        assert.strictEqual(Gups.Catalog.length, 3);
        assert.strictEqual(Gups.Catalog[0].name, "GUP-C");
        assert.strictEqual(Gups.Catalog[1].name, "GUP-I");
        assert.strictEqual(Gups.Catalog[2].name, "GUP-X");
        assert.strictEqual(Gups.Catalog[0].description, "Yellow rescue sub");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_real_mission_button_click_opens_gup_selection() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const { document, statusEl, missionSection, missionList, gupSection, gupMission, gupList } = dom;
        const { State, Missions, Gups, App } = loadApp(document);
        document.domLoadedHandler();
        assert.strictEqual(App.boot(), true);

        assert.strictEqual(missionList.children.length, 3);
        const seaTurtle = missionList.children[0];
        assert.strictEqual(seaTurtle.attributes["data-mission-id"], "sea-turtle");
        assert.strictEqual(Array.isArray(seaTurtle.listeners["click"]), true);

        seaTurtle.click();

        assert.strictEqual(snap(State).phase, "GUP_SELECT");
        assert.strictEqual(Missions.getSnapshot().selectedMissionId, "sea-turtle");
        assert.strictEqual(missionSection.style.display, "none");
        assert.strictEqual(gupSection.hidden, false);
        assert.strictEqual(gupMission.textContent, "Mission: Sea Turtle Rescue");
        assert.strictEqual(statusEl.textContent, "Choose a GUP for Sea Turtle Rescue");

        assert.strictEqual(gupList.children.length, 3);
        assert.deepStrictEqual(
          gupList.children.map((button) => button.attributes["data-gup-id"]),
          ["gup-c", "gup-i", "gup-x"]
        );
        gupList.children.forEach((button) => {
          assert.strictEqual(button.tagName, "button");
          assert.strictEqual(button.type, "button");
          assert.strictEqual(button.disabled, false);
        });
        assert.strictEqual(gupList.children[0].attributes["aria-pressed"], "true");
        assert.strictEqual(gupList.children[1].attributes["aria-pressed"], "false");
        assert.strictEqual(gupList.children[2].attributes["aria-pressed"], "false");
        assert.strictEqual(Gups.getSnapshot().selectedGupId, "gup-c");
        assert.strictEqual(Gups.getSnapshot().lastGupId, "gup-c");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_gup_button_click_updates_preview_without_transition() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const { document, statusEl, missionList, gupSection, gupList } = dom;
        const { State, Missions, Gups, App } = loadApp(document);
        document.domLoadedHandler();

        missionList.children[0].click();

        const gupI = gupList.children[1];
        assert.strictEqual(gupI.attributes["aria-pressed"], "false");
        gupI.click();

        assert.strictEqual(Gups.getSnapshot().selectedGupId, "gup-i");
        assert.strictEqual(Gups.getSnapshot().lastGupId, "gup-c");
        assert.strictEqual(gupI.attributes["aria-pressed"], "true");
        assert.strictEqual(gupList.children[0].attributes["aria-pressed"], "false");
        assert.strictEqual(gupList.children[2].attributes["aria-pressed"], "false");
        assert.strictEqual(gupSection.attributes["data-selected-gup-id"], "gup-i");
        assert.strictEqual(statusEl.textContent, "Selected GUP: GUP-I");
        assert.strictEqual(snap(State).phase, "GUP_SELECT");
        assert.strictEqual(Missions.getSnapshot().selectedMissionId, "sea-turtle");

        gupI.click();
        assert.strictEqual(snap(State).phase, "GUP_SELECT");
        assert.strictEqual(Gups.getSnapshot().selectedGupId, "gup-i");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_back_returns_to_mission_selection_without_confirming_gup() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const { document, statusEl, missionSection, missionList, gupSection, gupList, gupBack } = dom;
        const { State, Missions, Gups, App } = loadApp(document);
        document.domLoadedHandler();

        missionList.children[0].click();
        gupList.children[1].click();
        assert.strictEqual(Gups.getSnapshot().selectedGupId, "gup-i");

        gupBack.click();

        assert.strictEqual(snap(State).phase, "MISSION_SELECT");
        assert.strictEqual(missionSection.style.display, "block");
        assert.strictEqual(gupSection.hidden, true);
        assert.strictEqual(statusEl.textContent, "Choose a mission");
        assert.strictEqual(Gups.getSnapshot().lastGupId, "gup-c");
        assert.strictEqual(Missions.getSnapshot().selectedMissionId, "sea-turtle");

        assert.strictEqual(missionList.children.length, 3);
        assert.strictEqual(
          missionList.children.filter((b) => b.attributes["data-mission-id"] === "sea-turtle").length,
          1
        );
        assert.strictEqual(
          missionList.children.filter((b) => b.attributes["data-mission-id"] === "crab").length,
          1
        );
        assert.strictEqual(
          missionList.children.filter((b) => b.attributes["data-mission-id"] === "young-whale").length,
          1
        );
        assert.strictEqual(missionList.children[0].disabled, false);

        gupBack.click();
        assert.strictEqual(snap(State).phase, "MISSION_SELECT");

        missionList.children[0].click();
        assert.strictEqual(snap(State).phase, "GUP_SELECT");
        assert.strictEqual(Gups.getSnapshot().selectedGupId, "gup-c");
        assert.strictEqual(gupList.children[0].attributes["aria-pressed"], "true");
        assert.strictEqual(Gups.getSnapshot().lastGupId, "gup-c");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_launch_confirms_gup_and_commits_launch_phase() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const { document, statusEl, missionList, gupList, gupBack, gupLaunch, rootEl } = dom;
        const { State, Missions, Gups, App } = loadApp(document);
        document.domLoadedHandler();

        missionList.children[0].click();
        gupList.children[2].click();
        assert.strictEqual(Gups.getSnapshot().selectedGupId, "gup-x");

        gupLaunch.click();

        assert.strictEqual(snap(State).phase, "LAUNCH");
        assert.strictEqual(snap(State).pendingPhase, null);
        assert.strictEqual(Gups.getSnapshot().lastGupId, "gup-x");
        assert.strictEqual(Gups.getSnapshot().selectedGupId, "gup-x");
        assert.strictEqual(rootEl.attributes["data-launch-mission-id"], "sea-turtle");
        assert.strictEqual(rootEl.attributes["data-launch-gup-id"], "gup-x");
        assert.strictEqual(rootEl.attributes["data-launch-ready"], "true");
        assert.strictEqual(statusEl.textContent, "Launch ready: GUP-X — Sea Turtle Rescue");

        gupList.children.forEach((button) => {
          assert.strictEqual(button.disabled, true);
        });
        assert.strictEqual(gupBack.disabled, true);
        assert.strictEqual(gupLaunch.disabled, true);

        assert.strictEqual(Missions.getSnapshot().selectedMissionId, "sea-turtle");

        gupLaunch.click();
        assert.strictEqual(snap(State).phase, "LAUNCH");
        gupBack.click();
        assert.strictEqual(snap(State).phase, "LAUNCH");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_locked_mission_click_and_missing_optional_dom_are_safe() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const { document, missionList } = dom;
        const { State, Missions, App } = loadApp(document);
        document.domLoadedHandler();

        const crab = missionList.children[1];
        assert.strictEqual(crab.attributes["data-mission-id"], "crab");
        assert.strictEqual(crab.disabled, true);
        assert.strictEqual(crab.listeners["click"], undefined);

        const before = snap(State);
        crab.click();
        assert.deepStrictEqual(snap(State), before);
        assert.strictEqual(Missions.getSnapshot().selectedMissionId, null);

        const rootEl = {
          _ready: "false",
          getAttribute(name) {
            return name === "data-ocean-rescue-ready" ? this._ready : null;
          },
          setAttribute(name, value) {
            if (name === "data-ocean-rescue-ready") {
              this._ready = String(value);
            }
          },
        };
        const statusEl = { textContent: null };
        const section = makeElement("section");
        const list = makeElement("div");
        const document2 = makeDocument({
          "ocean-rescue-root": rootEl,
          "ocean-rescue-status": statusEl,
          "ocean-rescue-mission-select": section,
          "ocean-rescue-mission-list": list,
        });
        const ctx = loadApp(document2);
        assert.strictEqual(ctx.App.boot(), true);
        assert.strictEqual(snap(ctx.State).phase, "MISSION_SELECT");
        assert.strictEqual(ctx.App.selectMission("sea-turtle"), true);
        assert.strictEqual(snap(ctx.State).phase, "GUP_SELECT");
        assert.strictEqual(statusEl.textContent, "Mission selected: Sea Turtle Rescue");
        """
    )
    _assert_node_ok(_run_node(harness))
