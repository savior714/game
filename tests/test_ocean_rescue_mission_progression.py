"""Behavioral tests for Ocean Rescue mission selection and fixed progression.

Every JavaScript assertion runs the real tracked sources (``state.js``,
``missions.js``, and ``app.js``) through the installed Node runtime in a fresh
VM sandbox. No npm packages and no separate JavaScript test file are used.
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_BIN: str = shutil.which("node") or ""
if not NODE_BIN:
    raise RuntimeError("Node executable not found on PATH")

_MISSIONS_BOOTSTRAP = textwrap.dedent(
    """\
    const fs = require("fs");
    const vm = require("vm");
    const assert = require("assert");

    const MISSIONS_SOURCE = fs.readFileSync(
      "domains/ocean-rescue/src/missions.js",
      "utf8"
    );

    function freshMissions() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(MISSIONS_SOURCE, sandbox, { filename: "missions.js" });
      return sandbox.window.OceanRescue.Missions;
    }

    function makeStorage(seed) {
      const store = Object.assign({}, seed || {});
      return {
        getItem(key) {
          return Object.prototype.hasOwnProperty.call(store, key)
            ? store[key]
            : null;
        },
        setItem(key, value) {
          store[key] = String(value);
        },
        removeItem(key) {
          delete store[key];
        },
      };
    }

    function freshMissionsWithStorage(storage) {
      const sandbox = { window: { localStorage: storage } };
      vm.createContext(sandbox);
      vm.runInContext(MISSIONS_SOURCE, sandbox, { filename: "missions.js" });
      return sandbox.window.OceanRescue.Missions;
    }

    function plain(value) {
      return JSON.parse(JSON.stringify(value));
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
      const elements = {
        "ocean-rescue-root": rootEl,
        "ocean-rescue-status": statusEl,
        "ocean-rescue-mission-select": section,
        "ocean-rescue-mission-list": list,
      };
      return {
        document: makeDocument(elements),
        rootEl,
        statusEl,
        section,
        list,
      };
    }

    function loadApp(document) {
      const sandbox = { window: {}, document };
      vm.createContext(sandbox);
      vm.runInContext(STATE_SOURCE, sandbox, { filename: "state.js" });
      vm.runInContext(MISSIONS_SOURCE, sandbox, { filename: "missions.js" });
      vm.runInContext(APP_SOURCE, sandbox, { filename: "app.js" });
      return {
        sandbox,
        State: sandbox.window.OceanRescue.State,
        Missions: sandbox.window.OceanRescue.Missions,
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


def test_mission_catalog_and_public_contract() -> None:
    harness = _MISSIONS_BOOTSTRAP + textwrap.dedent(
        """\
        const Missions = freshMissions();

        assert.strictEqual(Missions.Catalog.length, 3);
        assert.deepStrictEqual(
          plain(Missions.Catalog.map((m) => m.id)),
          ["sea-turtle", "crab", "young-whale"]
        );
        assert.deepStrictEqual(
          plain(Missions.Catalog.map((m) => m.order)),
          [1, 2, 3]
        );

        const expected = [
          {
            id: "sea-turtle",
            order: 1,
            title: "Sea Turtle Rescue",
            companion: "Peso",
            summary: "Cut the ropes and free the trapped sea turtle.",
          },
          {
            id: "crab",
            order: 2,
            title: "Crab Rescue",
            companion: "Tweak",
            summary: "Move the rocks and help the trapped crab.",
          },
          {
            id: "young-whale",
            order: 3,
            title: "Young Whale Rescue",
            companion: "Captain Barnacles",
            summary: "Tow the debris and clear a path for the young whale.",
          },
        ];
        for (let i = 0; i < Missions.Catalog.length; i += 1) {
          assert.deepStrictEqual(plain(Missions.Catalog[i]), expected[i]);
        }

        assert.strictEqual(Object.isFrozen(Missions.Catalog), true);
        for (let i = 0; i < Missions.Catalog.length; i += 1) {
          assert.strictEqual(Object.isFrozen(Missions.Catalog[i]), true);
        }

        const expectedMembers = [
          "Catalog",
          "completeMission",
          "getSnapshot",
          "isUnlocked",
          "markMissionViewed",
          "selectMission",
        ];
        assert.deepStrictEqual(Object.keys(Missions).sort(), expectedMembers.slice().sort());
        assert.strictEqual(Object.isFrozen(Missions), true);

        assert.deepStrictEqual(plain(Missions.getSnapshot()), {
          selectedMissionId: null,
          unlockedMissionIds: ["sea-turtle"],
          completedMissionIds: [],
          newMissionIds: [],
        });

        assert.strictEqual(Missions.isUnlocked("sea-turtle"), true);
        assert.strictEqual(Missions.isUnlocked("crab"), false);
        assert.strictEqual(Missions.isUnlocked("young-whale"), false);
        assert.strictEqual(Missions.isUnlocked("unknown"), false);
        assert.strictEqual(Missions.isUnlocked(""), false);
        assert.strictEqual(Missions.isUnlocked(undefined), false);
        assert.strictEqual(Missions.isUnlocked(null), false);
        assert.strictEqual(Missions.isUnlocked({}), false);
        assert.strictEqual(Missions.isUnlocked(1), false);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_completed_mission_and_unlock_restore_across_reload() -> None:
    harness = _MISSIONS_BOOTSTRAP + textwrap.dedent(
        """\
        const storage = makeStorage();

        const MissionsA = freshMissionsWithStorage(storage);
        const result = MissionsA.completeMission("sea-turtle");
        assert.strictEqual(result.changed, true);
        assert.strictEqual(result.newlyUnlockedMissionId, "crab");

        const MissionsB = freshMissionsWithStorage(storage);
        assert.deepStrictEqual(plain(MissionsB.getSnapshot()), {
          selectedMissionId: null,
          unlockedMissionIds: ["sea-turtle", "crab"],
          completedMissionIds: ["sea-turtle"],
          newMissionIds: ["crab"],
        });
        assert.strictEqual(MissionsB.isUnlocked("crab"), true);
        assert.strictEqual(MissionsB.isUnlocked("young-whale"), false);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_selected_mission_state_is_not_persisted() -> None:
    harness = _MISSIONS_BOOTSTRAP + textwrap.dedent(
        """\
        const storage = makeStorage();

        const MissionsA = freshMissionsWithStorage(storage);
        assert.strictEqual(MissionsA.selectMission("sea-turtle"), true);
        assert.strictEqual(MissionsA.getSnapshot().selectedMissionId, "sea-turtle");

        const MissionsB = freshMissionsWithStorage(storage);
        assert.strictEqual(MissionsB.getSnapshot().selectedMissionId, null);
        assert.deepStrictEqual(plain(MissionsB.getSnapshot().unlockedMissionIds), ["sea-turtle"]);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_new_marker_removal_restores_across_reload() -> None:
    harness = _MISSIONS_BOOTSTRAP + textwrap.dedent(
        """\
        const storage = makeStorage();

        const MissionsA = freshMissionsWithStorage(storage);
        MissionsA.completeMission("sea-turtle");
        assert.strictEqual(MissionsA.markMissionViewed("crab"), true);
        assert.deepStrictEqual(plain(MissionsA.getSnapshot().newMissionIds), []);

        const MissionsB = freshMissionsWithStorage(storage);
        const snapshot = MissionsB.getSnapshot();
        assert.deepStrictEqual(plain(snapshot.newMissionIds), []);
        assert.deepStrictEqual(plain(snapshot.unlockedMissionIds), ["sea-turtle", "crab"]);
        assert.deepStrictEqual(plain(snapshot.completedMissionIds), ["sea-turtle"]);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_canonical_three_stage_progression_restores_across_reload() -> None:
    harness = _MISSIONS_BOOTSTRAP + textwrap.dedent(
        """\
        const storage = makeStorage();

        const MissionsA = freshMissionsWithStorage(storage);
        MissionsA.completeMission("sea-turtle");
        MissionsA.completeMission("crab");

        const MissionsB = freshMissionsWithStorage(storage);
        const snapshot = MissionsB.getSnapshot();
        assert.deepStrictEqual(plain(snapshot.unlockedMissionIds), [
          "sea-turtle",
          "crab",
          "young-whale",
        ]);
        assert.deepStrictEqual(plain(snapshot.completedMissionIds), [
          "sea-turtle",
          "crab",
        ]);
        assert.strictEqual(MissionsB.isUnlocked("young-whale"), true);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_corrupt_stored_payload_falls_back_to_initial_state() -> None:
    harness = _MISSIONS_BOOTSTRAP + textwrap.dedent(
        """\
        const KEY = "aidengame.oceanRescue.progression";
        const cases = [
          { name: "invalid json", seed: { [KEY]: "{not json" } },
          { name: "null payload", seed: { [KEY]: "null" } },
          { name: "array payload", seed: { [KEY]: "[1, 2, 3]" } },
          {
            name: "future schemaVersion",
            seed: {
              [KEY]: JSON.stringify({
                schemaVersion: 999,
                completedMissionIds: ["sea-turtle"],
                newMissionIds: ["crab"],
              }),
            },
          },
          {
            name: "unknown mission id",
            seed: {
              [KEY]: JSON.stringify({
                schemaVersion: 1,
                completedMissionIds: ["dolphin"],
                newMissionIds: [],
              }),
            },
          },
          {
            name: "out-of-order completion",
            seed: {
              [KEY]: JSON.stringify({
                schemaVersion: 1,
                completedMissionIds: ["crab"],
                newMissionIds: [],
              }),
            },
          },
        ];
        const expectedInitial = {
          selectedMissionId: null,
          unlockedMissionIds: ["sea-turtle"],
          completedMissionIds: [],
          newMissionIds: [],
        };
        for (const c of cases) {
          const storage = makeStorage(c.seed);
          const Missions = freshMissionsWithStorage(storage);
          assert.deepStrictEqual(
            plain(Missions.getSnapshot()),
            expectedInitial,
            "case: " + c.name
          );
        }
        """
    )
    _assert_node_ok(_run_node(harness))


def test_storage_exception_isolation() -> None:
    harness = _MISSIONS_BOOTSTRAP + textwrap.dedent(
        """\
        const expectedInitial = {
          selectedMissionId: null,
          unlockedMissionIds: ["sea-turtle"],
          completedMissionIds: [],
          newMissionIds: [],
        };

        {
          const throwingGet = {
            getItem() {
              throw new Error("getItem failed");
            },
            setItem() {},
            removeItem() {},
          };
          const Missions = freshMissionsWithStorage(throwingGet);
          assert.deepStrictEqual(plain(Missions.getSnapshot()), expectedInitial);
          assert.strictEqual(Missions.completeMission("sea-turtle").changed, true);
        }

        {
          const throwingSet = {
            getItem() {
              return null;
            },
            setItem() {
              throw new Error("setItem failed");
            },
            removeItem() {},
          };
          const Missions = freshMissionsWithStorage(throwingSet);
          const result = Missions.completeMission("sea-turtle");
          assert.strictEqual(result.changed, true);
          assert.deepStrictEqual(
            plain(Missions.getSnapshot().completedMissionIds),
            ["sea-turtle"]
          );
          assert.deepStrictEqual(
            plain(Missions.getSnapshot().unlockedMissionIds),
            ["sea-turtle", "crab"]
          );
        }

        {
          const throwingRemove = {
            getItem() {
              return "{not json";
            },
            setItem() {},
            removeItem() {
              throw new Error("removeItem failed");
            },
          };
          const Missions = freshMissionsWithStorage(throwingRemove);
          assert.deepStrictEqual(plain(Missions.getSnapshot()), expectedInitial);
        }
        """
    )
    _assert_node_ok(_run_node(harness))


def test_fixed_unlock_progression() -> None:
    harness = _MISSIONS_BOOTSTRAP + textwrap.dedent(
        """\
        const Missions = freshMissions();

        assert.deepStrictEqual(plain(Missions.getSnapshot().unlockedMissionIds), ["sea-turtle"]);
        assert.deepStrictEqual(plain(Missions.getSnapshot().completedMissionIds), []);
        assert.deepStrictEqual(plain(Missions.getSnapshot().newMissionIds), []);
        assert.strictEqual(Missions.isUnlocked("crab"), false);
        assert.strictEqual(Missions.isUnlocked("young-whale"), false);

        let result = Missions.completeMission("sea-turtle");
        assert.strictEqual(result.changed, true);
        assert.strictEqual(result.newlyUnlockedMissionId, "crab");
        assert.deepStrictEqual(
          plain(Missions.getSnapshot().unlockedMissionIds),
          ["sea-turtle", "crab"]
        );
        assert.deepStrictEqual(plain(Missions.getSnapshot().completedMissionIds), ["sea-turtle"]);
        assert.deepStrictEqual(plain(Missions.getSnapshot().newMissionIds), ["crab"]);
        assert.strictEqual(Missions.isUnlocked("crab"), true);

        result = Missions.completeMission("crab");
        assert.strictEqual(result.changed, true);
        assert.strictEqual(result.newlyUnlockedMissionId, "young-whale");
        assert.deepStrictEqual(
          plain(Missions.getSnapshot().unlockedMissionIds),
          ["sea-turtle", "crab", "young-whale"]
        );
        assert.deepStrictEqual(
          plain(Missions.getSnapshot().completedMissionIds),
          ["sea-turtle", "crab"]
        );
        assert.deepStrictEqual(plain(Missions.getSnapshot().newMissionIds), ["crab", "young-whale"]);
        assert.strictEqual(Missions.isUnlocked("young-whale"), true);

        result = Missions.completeMission("young-whale");
        assert.strictEqual(result.changed, true);
        assert.strictEqual(result.newlyUnlockedMissionId, null);
        assert.deepStrictEqual(
          plain(Missions.getSnapshot().unlockedMissionIds),
          ["sea-turtle", "crab", "young-whale"]
        );
        assert.deepStrictEqual(
          plain(Missions.getSnapshot().completedMissionIds),
          ["sea-turtle", "crab", "young-whale"]
        );
        assert.deepStrictEqual(plain(Missions.getSnapshot().newMissionIds), ["crab", "young-whale"]);

        const finalSnap = Missions.getSnapshot();
        assert.deepStrictEqual(
          plain(finalSnap.unlockedMissionIds),
          ["sea-turtle", "crab", "young-whale"]
        );
        assert.deepStrictEqual(
          plain(finalSnap.completedMissionIds),
          ["sea-turtle", "crab", "young-whale"]
        );
        """
    )
    _assert_node_ok(_run_node(harness))


def test_invalid_locked_and_duplicate_completion_are_idempotent() -> None:
    harness = _MISSIONS_BOOTSTRAP + textwrap.dedent(
        """\
        const Missions = freshMissions();
        const expectedIdle = {
          selectedMissionId: null,
          unlockedMissionIds: ["sea-turtle"],
          completedMissionIds: [],
          newMissionIds: [],
        };

        let result = Missions.completeMission("dolphin");
        assert.deepStrictEqual(plain(result), { changed: false, newlyUnlockedMissionId: null });
        assert.deepStrictEqual(plain(Missions.getSnapshot()), expectedIdle);

        result = Missions.completeMission("crab");
        assert.deepStrictEqual(plain(result), { changed: false, newlyUnlockedMissionId: null });
        assert.deepStrictEqual(plain(Missions.getSnapshot()), expectedIdle);

        result = Missions.completeMission("sea-turtle");
        assert.strictEqual(result.changed, true);
        assert.strictEqual(result.newlyUnlockedMissionId, "crab");
        assert.strictEqual(Missions.isUnlocked("young-whale"), false);

        result = Missions.completeMission("sea-turtle");
        assert.deepStrictEqual(plain(result), { changed: false, newlyUnlockedMissionId: null });

        const snapshot = Missions.getSnapshot();
        assert.deepStrictEqual(plain(snapshot.unlockedMissionIds), ["sea-turtle", "crab"]);
        assert.deepStrictEqual(plain(snapshot.completedMissionIds), ["sea-turtle"]);
        assert.deepStrictEqual(plain(snapshot.newMissionIds), ["crab"]);
        assert.strictEqual(
          snapshot.unlockedMissionIds.filter((id) => id === "crab").length,
          1
        );
        assert.strictEqual(
          snapshot.completedMissionIds.filter((id) => id === "sea-turtle").length,
          1
        );
        assert.strictEqual(
          snapshot.newMissionIds.filter((id) => id === "crab").length,
          1
        );
        """
    )
    _assert_node_ok(_run_node(harness))


def test_selection_and_new_marker_contract() -> None:
    harness = _MISSIONS_BOOTSTRAP + textwrap.dedent(
        """\
        const Missions = freshMissions();

        assert.strictEqual(Missions.selectMission("crab"), false);
        assert.strictEqual(Missions.getSnapshot().selectedMissionId, null);

        assert.strictEqual(Missions.selectMission("sea-turtle"), true);
        assert.strictEqual(Missions.getSnapshot().selectedMissionId, "sea-turtle");
        assert.strictEqual(Missions.selectMission("sea-turtle"), true);
        assert.strictEqual(Missions.getSnapshot().selectedMissionId, "sea-turtle");

        Missions.completeMission("sea-turtle");
        Missions.completeMission("crab");
        assert.deepStrictEqual(plain(Missions.getSnapshot().newMissionIds), ["crab", "young-whale"]);

        assert.strictEqual(Missions.isUnlocked("crab"), true);
        assert.strictEqual(Missions.selectMission("crab"), true);
        assert.strictEqual(Missions.getSnapshot().selectedMissionId, "crab");

        assert.strictEqual(Missions.markMissionViewed("crab"), true);
        assert.deepStrictEqual(plain(Missions.getSnapshot().newMissionIds), ["young-whale"]);
        assert.deepStrictEqual(
          plain(Missions.getSnapshot().completedMissionIds),
          ["sea-turtle", "crab"]
        );
        assert.deepStrictEqual(
          plain(Missions.getSnapshot().unlockedMissionIds),
          ["sea-turtle", "crab", "young-whale"]
        );
        assert.strictEqual(Missions.getSnapshot().selectedMissionId, "crab");

        assert.strictEqual(Missions.markMissionViewed("crab"), false);
        assert.strictEqual(Missions.markMissionViewed("unknown"), false);
        assert.deepStrictEqual(plain(Missions.getSnapshot().newMissionIds), ["young-whale"]);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_mission_snapshots_cannot_mutate_internal_state() -> None:
    harness = _MISSIONS_BOOTSTRAP + textwrap.dedent(
        """\
        const Missions = freshMissions();

        function assertThrows(fn) {
          let threw = false;
          try {
            fn();
          } catch (err) {
            threw = true;
          }
          assert.strictEqual(threw, true);
        }

        const snapshotA = Missions.getSnapshot();
        const snapshotB = Missions.getSnapshot();
        assert.notStrictEqual(snapshotA, snapshotB);
        assert.strictEqual(Object.isFrozen(snapshotA), true);
        assert.strictEqual(Object.isFrozen(snapshotB), true);
        assert.strictEqual(Object.isFrozen(snapshotA.unlockedMissionIds), true);
        assert.strictEqual(Object.isFrozen(snapshotA.completedMissionIds), true);
        assert.strictEqual(Object.isFrozen(snapshotA.newMissionIds), true);
        assert.notStrictEqual(snapshotA.unlockedMissionIds, snapshotB.unlockedMissionIds);
        assert.notStrictEqual(snapshotA.completedMissionIds, snapshotB.completedMissionIds);
        assert.notStrictEqual(snapshotA.newMissionIds, snapshotB.newMissionIds);

        assertThrows(() => {
          snapshotA.unlockedMissionIds.push("hacked");
        });
        assertThrows(() => {
          snapshotA.completedMissionIds.push("hacked");
        });
        assertThrows(() => {
          snapshotA.newMissionIds.push("hacked");
        });
        snapshotA.selectedMissionId = "young-whale";
        snapshotB.unlockedMissionIds[0] = "hacked";

        assert.deepStrictEqual(plain(Missions.getSnapshot()), {
          selectedMissionId: null,
          unlockedMissionIds: ["sea-turtle"],
          completedMissionIds: [],
          newMissionIds: [],
        });

        Missions.Catalog[0].title = "HACKED";
        Missions.Catalog[0].companion = "HACKED";
        assertThrows(() => {
          Missions.Catalog.push({
            id: "hacked",
            order: 4,
            title: "X",
            companion: "Y",
            summary: "Z",
          });
        });
        assert.strictEqual(Missions.Catalog.length, 3);
        assert.strictEqual(Missions.Catalog[0].title, "Sea Turtle Rescue");
        assert.strictEqual(Missions.Catalog[1].title, "Crab Rescue");
        assert.strictEqual(Missions.Catalog[2].title, "Young Whale Rescue");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_app_boot_renders_three_accessible_mission_cards() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        const { document, rootEl, statusEl, section, list } = makeBootDom();
        const { State, Missions, App } = loadApp(document);

        assert.strictEqual(document.domListenerCount, 1);
        document.domLoadedHandler();

        assert.strictEqual(App.boot(), true);
        assert.deepStrictEqual(snap(State), {
          phase: "MISSION_SELECT",
          ready: true,
          transitionLocked: false,
          pendingPhase: null,
        });
        assert.strictEqual(rootEl._ready, "true");
        assert.strictEqual(statusEl.textContent, "Ocean Rescue ready");
        assert.strictEqual(section.style.display, "block");

        assert.strictEqual(list.children.length, 3);
        assert.deepStrictEqual(
          list.children.map((button) => button.attributes["data-mission-id"]),
          ["sea-turtle", "crab", "young-whale"]
        );
        list.children.forEach((button) => {
          assert.strictEqual(button.tagName, "button");
          assert.strictEqual(button.type, "button");
        });
        assert.strictEqual(list.children[0].disabled, false);
        assert.strictEqual(list.children[1].disabled, true);
        assert.strictEqual(list.children[2].disabled, true);

        assert.strictEqual(list.children[0].children[0].textContent, "Sea Turtle Rescue");
        assert.strictEqual(list.children[1].children[0].textContent, "Crab Rescue");
        assert.strictEqual(list.children[2].children[0].textContent, "Young Whale Rescue");
        assert.strictEqual(list.children[0].children[3].textContent, "Available");
        assert.strictEqual(list.children[1].children[3].textContent, "Locked");
        assert.strictEqual(list.children[2].children[3].textContent, "Locked");

        const before = snap(State);
        const stateBefore = Missions.getSnapshot();
        assert.strictEqual(App.boot(), true);
        assert.deepStrictEqual(snap(State), before);
        assert.deepStrictEqual(Missions.getSnapshot(), stateBefore);
        assert.strictEqual(list.children.length, 3);
        assert.strictEqual(document.domListenerCount, 1);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_app_selection_and_new_mission_scroll_integration() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const { document, statusEl, section, list } = dom;
        const { State, Missions, App } = loadApp(document);
        document.domLoadedHandler();

        const phaseBefore = snap(State).phase;
        assert.strictEqual(App.selectMission("crab"), false);
        assert.strictEqual(snap(State).phase, phaseBefore);
        assert.strictEqual(Missions.getSnapshot().selectedMissionId, null);
        assert.strictEqual(statusEl.textContent, "Ocean Rescue ready");

        assert.strictEqual(App.selectMission("sea-turtle"), true);
        assert.strictEqual(snap(State).phase, "GUP_SELECT");
        assert.strictEqual(Missions.getSnapshot().selectedMissionId, "sea-turtle");
        assert.strictEqual(section.attributes["data-selected-mission-id"], "sea-turtle");
        assert.strictEqual(statusEl.textContent, "Mission selected: Sea Turtle Rescue");
        assert.strictEqual(
          list.children.every((button) => button.disabled === true),
          true
        );

        assert.strictEqual(App.selectMission("sea-turtle"), false);
        assert.strictEqual(App.selectMission("crab"), false);
        assert.strictEqual(snap(State).phase, "GUP_SELECT");
        assert.strictEqual(Missions.getSnapshot().selectedMissionId, "sea-turtle");

        const dom2 = makeBootDom();
        const { State: State2, Missions: Missions2, App: App2 } = loadApp(dom2.document);
        dom2.document.domLoadedHandler();

        const result = Missions2.completeMission("sea-turtle");
        assert.strictEqual(result.changed, true);
        assert.strictEqual(result.newlyUnlockedMissionId, "crab");
        assert.deepStrictEqual(plain(Missions2.getSnapshot().newMissionIds), ["crab"]);

        assert.strictEqual(App2.renderMissionSelect({ focusMissionId: "crab" }), true);
        assert.strictEqual(dom2.section.style.display, "block");

        const crabCard = dom2.list.children[1];
        assert.strictEqual(crabCard.attributes["data-mission-id"], "crab");
        assert.strictEqual(crabCard.disabled, false);
        const newBadge = crabCard.children[crabCard.children.length - 1];
        assert.strictEqual(newBadge.className, "ocean-rescue-mission-new");
        assert.strictEqual(newBadge.textContent, "New!");
        assert.strictEqual(crabCard.scrollIntoViewCalls, 1);

        assert.deepStrictEqual(plain(Missions2.getSnapshot().newMissionIds), ["crab"]);
        assert.strictEqual(Missions2.getSnapshot().selectedMissionId, null);

        assert.strictEqual(App2.selectMission("crab"), true);
        assert.strictEqual(snap(State2).phase, "GUP_SELECT");
        assert.deepStrictEqual(plain(Missions2.getSnapshot().newMissionIds), []);
        assert.strictEqual(Missions2.getSnapshot().selectedMissionId, "crab");
        """
    )
    _assert_node_ok(_run_node(harness))
