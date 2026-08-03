"""Behavioral tests for Ocean Rescue first-time profile choice and boot gate.

Every JavaScript assertion runs the real tracked sources through the installed
Node runtime in a fresh VM sandbox.
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_BIN: str = shutil.which("node") or ""
if not NODE_BIN:
    raise RuntimeError("Node executable not found on PATH")

_STATE_SOURCE = "domains/ocean-rescue/src/state.js"
_PROFILE_SOURCE = "domains/ocean-rescue/src/profile.js"
_MISSIONS_SOURCE = "domains/ocean-rescue/src/missions.js"
_GUPS_SOURCE = "domains/ocean-rescue/src/gups.js"
_APP_SOURCE = "domains/ocean-rescue/src/app.js"

_FULL_BOOTSTRAP = textwrap.dedent(
    """\
    const fs = require("fs");
    const vm = require("vm");
    const assert = require("assert");

    const STATE_SOURCE = fs.readFileSync("domains/ocean-rescue/src/state.js", "utf8");
    const PROFILE_SOURCE = fs.readFileSync("domains/ocean-rescue/src/profile.js", "utf8");
    const MISSIONS_SOURCE = fs.readFileSync("domains/ocean-rescue/src/missions.js", "utf8");
    const GUPS_SOURCE = fs.readFileSync("domains/ocean-rescue/src/gups.js", "utf8");
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

    function makeBootDom(options) {
      const opts = options || {};
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

      const profileSection = makeElement("section");
      const profilePlayerName = makeElement("span");
      const profileAnimalList = makeElement("div");
      const profileContinue = makeElement("button");
      profileContinue.type = "button";
      profileSection.appendChild(profilePlayerName);
      profileSection.appendChild(profileAnimalList);
      profileSection.appendChild(profileContinue);

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
        "ocean-rescue-profile-choice": profileSection,
        "ocean-rescue-profile-player-name": profilePlayerName,
        "ocean-rescue-profile-animal-list": profileAnimalList,
        "ocean-rescue-profile-continue": profileContinue,
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
        profileSection,
        profilePlayerName,
        profileAnimalList,
        profileContinue,
        missionSection,
        missionList,
        gupSection,
        gupMission,
        gupList,
        gupBack,
        gupLaunch,
      };
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

    function loadModules(document, storage) {
      const win = {};
      if (storage) {
        win.localStorage = storage;
      }
      const sandbox = { window: win, document };
      vm.createContext(sandbox);
      vm.runInContext(STATE_SOURCE, sandbox, { filename: "state.js" });
      vm.runInContext(PROFILE_SOURCE, sandbox, { filename: "profile.js" });
      vm.runInContext(MISSIONS_SOURCE, sandbox, { filename: "missions.js" });
      vm.runInContext(GUPS_SOURCE, sandbox, { filename: "gups.js" });
      vm.runInContext(APP_SOURCE, sandbox, { filename: "app.js" });
      return {
        sandbox,
        State: sandbox.window.OceanRescue.State,
        Profile: sandbox.window.OceanRescue.Profile,
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


# ── 1. Profile catalog and public contract ──────────────────────────────

def test_profile_catalog_and_public_contract() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const { Profile } = loadModules(makeDocument({}), null);

        assert.strictEqual(Profile.Catalog.length, 3);
        assert.deepStrictEqual(
          plain(Profile.Catalog.map((a) => a.id)),
          ["arctic-fox", "beaver", "red-panda"]
        );
        assert.deepStrictEqual(
          plain(Profile.Catalog.map((a) => a.name)),
          ["Arctic fox", "Beaver", "Red panda"]
        );

        assert.strictEqual(Object.isFrozen(Profile.Catalog), true);
        for (let i = 0; i < Profile.Catalog.length; i += 1) {
          assert.strictEqual(Object.isFrozen(Profile.Catalog[i]), true);
        }

        const expectedMembers = [
          "Catalog",
          "getSnapshot",
          "selectAnimal",
          "confirmSelection",
        ];
        assert.deepStrictEqual(
          Object.keys(Profile).sort(),
          expectedMembers.slice().sort()
        );
        assert.strictEqual(Object.isFrozen(Profile), true);

        const s = Profile.getSnapshot();
        assert.strictEqual(s.playerName, "Aiden");
        assert.deepStrictEqual(plain(s), {
          playerName: "Aiden",
          selectedAnimalId: null,
          chosenAnimalId: null,
          complete: false,
        });
        """
    )
    _assert_node_ok(_run_node(harness))


# ── 2. Fresh storage state ──────────────────────────────────────────────

def test_fresh_storage_state() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const { Profile } = loadModules(makeDocument({}), makeStorage());
        const s = Profile.getSnapshot();
        assert.strictEqual(s.chosenAnimalId, null);
        assert.strictEqual(s.selectedAnimalId, null);
        assert.strictEqual(s.complete, false);
        assert.strictEqual(s.playerName, "Aiden");
        """
    )
    _assert_node_ok(_run_node(harness))


# ── 3. Selection does not persist ───────────────────────────────────────

def test_selection_does_not_persist() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const storage = makeStorage();
        const { Profile } = loadModules(makeDocument({}), storage);
        assert.strictEqual(Profile.selectAnimal("beaver"), true);
        assert.strictEqual(Profile.getSnapshot().selectedAnimalId, "beaver");
        assert.strictEqual(storage.getItem("aidengame.oceanRescue.profile"), null);
        """
    )
    _assert_node_ok(_run_node(harness))


# ── 4. Confirmation persists ────────────────────────────────────────────

def test_confirmation_persists() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const storage = makeStorage();
        const { Profile } = loadModules(makeDocument({}), storage);
        assert.strictEqual(Profile.selectAnimal("beaver"), true);
        assert.strictEqual(Profile.confirmSelection(), true);
        const s = Profile.getSnapshot();
        assert.strictEqual(s.chosenAnimalId, "beaver");
        assert.strictEqual(s.complete, true);
        assert.strictEqual(s.playerName, "Aiden");

        const stored = JSON.parse(storage.getItem("aidengame.oceanRescue.profile"));
        assert.deepStrictEqual(stored, {
          schemaVersion: 1,
          playerName: "Aiden",
          animalId: "beaver",
        });
        """
    )
    _assert_node_ok(_run_node(harness))


# ── 5. Reload hydration ─────────────────────────────────────────────────

def test_reload_hydration() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const storage = makeStorage();
        const { Profile: ProfileA } = loadModules(makeDocument({}), storage);
        ProfileA.selectAnimal("beaver");
        ProfileA.confirmSelection();

        const { Profile: ProfileB } = loadModules(makeDocument({}), storage);
        const s = ProfileB.getSnapshot();
        assert.strictEqual(s.chosenAnimalId, "beaver");
        assert.strictEqual(s.complete, true);
        assert.strictEqual(s.playerName, "Aiden");
        """
    )
    _assert_node_ok(_run_node(harness))


# ── 6. Invalid storage fallback ─────────────────────────────────────────

def test_invalid_storage_fallback() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const KEY = "aidengame.oceanRescue.profile";
        const cases = [
          { name: "invalid json", seed: { [KEY]: "{not json" } },
          { name: "null payload", seed: { [KEY]: "null" } },
          { name: "array payload", seed: { [KEY]: "[1, 2, 3]" } },
          {
            name: "future schemaVersion",
            seed: {
              [KEY]: JSON.stringify({
                schemaVersion: 999,
                playerName: "Aiden",
                animalId: "beaver",
              }),
            },
          },
          {
            name: "wrong playerName",
            seed: {
              [KEY]: JSON.stringify({
                schemaVersion: 1,
                playerName: "Bob",
                animalId: "beaver",
              }),
            },
          },
          {
            name: "unknown animalId",
            seed: {
              [KEY]: JSON.stringify({
                schemaVersion: 1,
                playerName: "Aiden",
                animalId: "dolphin",
              }),
            },
          },
        ];
        for (const c of cases) {
          const { Profile } = loadModules(makeDocument({}), makeStorage(c.seed));
          const s = Profile.getSnapshot();
          assert.strictEqual(s.chosenAnimalId, null, c.name);
          assert.strictEqual(s.complete, false, c.name);
        }
        """
    )
    _assert_node_ok(_run_node(harness))


# ── 7. Storage exception isolation ──────────────────────────────────────

def test_storage_exception_isolation() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        {
          const throwingGet = {
            getItem() { throw new Error("getItem failed"); },
            setItem() {},
            removeItem() {},
          };
          const { Profile } = loadModules(makeDocument({}), throwingGet);
          assert.deepStrictEqual(plain(Profile.getSnapshot()), {
            playerName: "Aiden",
            selectedAnimalId: null,
            chosenAnimalId: null,
            complete: false,
          });
        }

        {
          const throwingSet = {
            getItem() { return null; },
            setItem() { throw new Error("setItem failed"); },
            removeItem() {},
          };
          const { Profile } = loadModules(makeDocument({}), throwingSet);
          Profile.selectAnimal("beaver");
          assert.strictEqual(Profile.confirmSelection(), true);
          assert.strictEqual(Profile.getSnapshot().chosenAnimalId, "beaver");
          assert.strictEqual(Profile.getSnapshot().complete, false);
        }

        {
          const throwingRemove = {
            getItem() { return "{not json"; },
            setItem() {},
            removeItem() { throw new Error("removeItem failed"); },
          };
          const { Profile } = loadModules(makeDocument({}), throwingRemove);
          assert.deepStrictEqual(plain(Profile.getSnapshot()), {
            playerName: "Aiden",
            selectedAnimalId: null,
            chosenAnimalId: null,
            complete: false,
          });
        }

        {
          const { Profile } = loadModules(makeDocument({}), null);
          assert.deepStrictEqual(plain(Profile.getSnapshot()), {
            playerName: "Aiden",
            selectedAnimalId: null,
            chosenAnimalId: null,
            complete: false,
          });
        }
        """
    )
    _assert_node_ok(_run_node(harness))


# ── 8. State transition contract ────────────────────────────────────────

def test_state_transition_contract() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const { State } = loadModules(makeDocument({}), null);

        assert.strictEqual(State.canTransition("PROFILE_CHOICE"), true);
        assert.strictEqual(State.canTransition("MISSION_SELECT"), true);

        const t1 = State.beginTransition("PROFILE_CHOICE");
        assert.notStrictEqual(t1, null);
        assert.strictEqual(State.completeTransition(t1), true);
        assert.strictEqual(State.getSnapshot().phase, "PROFILE_CHOICE");

        const t2 = State.beginTransition("MISSION_SELECT");
        assert.notStrictEqual(t2, null);
        assert.strictEqual(State.completeTransition(t2), true);
        assert.strictEqual(State.getSnapshot().phase, "MISSION_SELECT");

        const t3 = State.beginTransition("GUP_SELECT");
        assert.notStrictEqual(t3, null);
        assert.strictEqual(State.completeTransition(t3), true);
        assert.strictEqual(State.getSnapshot().phase, "GUP_SELECT");

        assert.strictEqual(State.canTransition("PROFILE_CHOICE"), false);

        State.forcePhase("PROFILE_CHOICE");
        assert.strictEqual(State.canTransition("GUP_SELECT"), false);
        assert.strictEqual(State.canTransition("LAUNCH"), false);
        """
    )
    _assert_node_ok(_run_node(harness))


# ── 9. Fresh boot destination ───────────────────────────────────────────

def test_fresh_boot_enters_profile_choice() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const { document, rootEl, statusEl, profileSection, profilePlayerName,
                profileAnimalList, profileContinue,
                missionSection, missionList } = dom;
        const { State, Profile, App } = loadModules(document, makeStorage());
        document.domLoadedHandler();

        assert.strictEqual(App.boot(), true);
        assert.deepStrictEqual(snap(State), {
          phase: "PROFILE_CHOICE",
          ready: true,
          transitionLocked: false,
          pendingPhase: null,
        });
        assert.strictEqual(rootEl._ready, "true");

        assert.strictEqual(profileSection.style.display, "block");
        assert.strictEqual(profilePlayerName.textContent, "Aiden");
        assert.strictEqual(profileContinue.disabled, true);

        assert.strictEqual(profileAnimalList.children.length, 3);
        assert.deepStrictEqual(
          profileAnimalList.children.map((b) => b.attributes["data-profile-animal-id"]),
          ["arctic-fox", "beaver", "red-panda"]
        );
        profileAnimalList.children.forEach((b) => {
          assert.strictEqual(b.tagName, "button");
          assert.strictEqual(b.type, "button");
          assert.strictEqual(b.attributes["aria-pressed"], "false");
        });
        """
    )
    _assert_node_ok(_run_node(harness))


# ── 10. Selection UI ───────────────────────────────────────────────────

def test_selection_ui() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const { document, profileAnimalList, profileContinue } = dom;
        const { Profile, App } = loadModules(document, makeStorage());
        document.domLoadedHandler();
        App.boot();

        assert.strictEqual(profileContinue.disabled, true);

        const beaver = profileAnimalList.children[1];
        assert.strictEqual(beaver.attributes["data-profile-animal-id"], "beaver");
        beaver.click();

        assert.strictEqual(profileContinue.disabled, false);
        assert.strictEqual(beaver.attributes["aria-pressed"], "true");
        assert.strictEqual(profileAnimalList.children[0].attributes["aria-pressed"], "false");
        assert.strictEqual(profileAnimalList.children[2].attributes["aria-pressed"], "false");
        """
    )
    _assert_node_ok(_run_node(harness))


# ── 11. Confirmation flow ──────────────────────────────────────────────

def test_confirmation_flow() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const { document, statusEl, profileSection, profileAnimalList,
                profileContinue, missionSection, missionList } = dom;
        const { State, Profile, App } = loadModules(document, makeStorage());
        document.domLoadedHandler();
        App.boot();

        assert.strictEqual(snap(State).phase, "PROFILE_CHOICE");
        assert.strictEqual(profileSection.style.display, "block");

        profileAnimalList.children[1].click();
        profileContinue.click();

        assert.strictEqual(snap(State).phase, "MISSION_SELECT");
        assert.strictEqual(profileSection.style.display, "none");
        assert.strictEqual(Profile.getSnapshot().chosenAnimalId, "beaver");
        assert.strictEqual(Profile.getSnapshot().complete, true);

        assert.strictEqual(missionSection.style.display, "block");
        assert.strictEqual(missionList.children.length, 3);
        """
    )
    _assert_node_ok(_run_node(harness))


# ── 12. Reload skip ────────────────────────────────────────────────────

def test_reload_skip() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const { document, statusEl, profileSection, missionSection } = dom;
        const storage = makeStorage();
        storage.setItem("aidengame.oceanRescue.profile", JSON.stringify({
          schemaVersion: 1,
          playerName: "Aiden",
          animalId: "beaver",
        }));
        const { State, Profile, App } = loadModules(document, storage);
        document.domLoadedHandler();

        assert.strictEqual(App.boot(), true);
        assert.deepStrictEqual(snap(State), {
          phase: "MISSION_SELECT",
          ready: true,
          transitionLocked: false,
          pendingPhase: null,
        });
        assert.strictEqual(profileSection.style.display, "none");
        assert.strictEqual(missionSection.style.display, "block");
        """
    )
    _assert_node_ok(_run_node(harness))


# ── 13. Re-entrancy ────────────────────────────────────────────────────

def test_re_entrancy() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const { document, profileSection, profileAnimalList,
                profileContinue, missionSection } = dom;
        const { State, Profile, App } = loadModules(document, makeStorage());
        document.domLoadedHandler();
        App.boot();

        profileAnimalList.children[1].click();
        profileContinue.click();
        profileContinue.click();
        profileContinue.click();

        assert.strictEqual(snap(State).phase, "MISSION_SELECT");
        assert.strictEqual(profileSection.style.display, "none");
        assert.strictEqual(missionSection.style.display, "block");
        assert.strictEqual(Profile.getSnapshot().complete, true);
        assert.strictEqual(Profile.getSnapshot().chosenAnimalId, "beaver");
        """
    )
    _assert_node_ok(_run_node(harness))


# ── 14. Existing progression independence ───────────────────────────────

def test_progression_independence() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const PROG_KEY = "aidengame.oceanRescue.progression";
        const PROF_KEY = "aidengame.oceanRescue.profile";
        const progPayload = JSON.stringify({
          schemaVersion: 1,
          completedMissionIds: ["sea-turtle"],
          newMissionIds: ["crab"],
        });
        const storage = makeStorage({ [PROG_KEY]: progPayload });

        const { Profile } = loadModules(makeDocument({}), storage);
        Profile.selectAnimal("beaver");
        Profile.confirmSelection();

        assert.strictEqual(storage.getItem(PROG_KEY), progPayload);
        assert.deepStrictEqual(JSON.parse(storage.getItem(PROF_KEY)), {
          schemaVersion: 1,
          playerName: "Aiden",
          animalId: "beaver",
        });
        """
    )
    _assert_node_ok(_run_node(harness))
