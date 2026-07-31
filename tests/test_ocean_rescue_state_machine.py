"""Behavioral tests for the Ocean Rescue gameplay state machine.

Every JavaScript assertion runs the real tracked source (``state.js`` and
``app.js``) through the installed Node runtime in a fresh VM sandbox. No npm
packages and no separate JavaScript test file are used.
"""

import shutil
import subprocess
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_BIN = shutil.which("node")
if NODE_BIN is None:
    raise RuntimeError("Node executable not found on PATH")

_INITIAL_SNAPSHOT = {
    "phase": "BOOT",
    "ready": False,
    "transitionLocked": False,
    "pendingPhase": None,
}

_STATE_BOOTSTRAP = textwrap.dedent(
    """\
    const fs = require("fs");
    const vm = require("vm");
    const assert = require("assert");

    const STATE_SOURCE = fs.readFileSync("domains/ocean-rescue/src/state.js", "utf8");

    function freshState() {
      const sandbox = { window: {} };
      vm.createContext(sandbox);
      vm.runInContext(STATE_SOURCE, sandbox, { filename: "state.js" });
      return sandbox.window.OceanRescue.State;
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
    """
)

_APP_BOOTSTRAP = textwrap.dedent(
    """\
    const fs = require("fs");
    const vm = require("vm");
    const assert = require("assert");

    const STATE_SOURCE = fs.readFileSync("domains/ocean-rescue/src/state.js", "utf8");
    const APP_SOURCE = fs.readFileSync("domains/ocean-rescue/src/app.js", "utf8");

    function loadApp(document) {
      const sandbox = { window: {}, document };
      vm.createContext(sandbox);
      vm.runInContext(STATE_SOURCE, sandbox, { filename: "state.js" });
      vm.runInContext(APP_SOURCE, sandbox, { filename: "app.js" });
      return {
        sandbox,
        State: sandbox.window.OceanRescue.State,
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


def test_state_machine_public_contract() -> None:
    harness = _STATE_BOOTSTRAP + textwrap.dedent(
        """\
        const State = freshState();

        const expectedPhases = {
          BOOT: "BOOT",
          MISSION_SELECT: "MISSION_SELECT",
          GUP_SELECT: "GUP_SELECT",
          LAUNCH: "LAUNCH",
          TRAVEL: "TRAVEL",
          RESCUE_SITE_TRANSITION: "RESCUE_SITE_TRANSITION",
          RESCUE_TUTORIAL: "RESCUE_TUTORIAL",
          RESCUE_ACTIVE: "RESCUE_ACTIVE",
          RESCUE_SUCCESS: "RESCUE_SUCCESS",
          MISSION_COMPLETE: "MISSION_COMPLETE",
        };
        assert.deepStrictEqual(Object.assign({}, State.Phases), expectedPhases);

        const expectedMembers = [
          "Phases",
          "beginTransition",
          "canTransition",
          "completeTransition",
          "forcePhase",
          "getSnapshot",
          "markReady",
        ];
        assert.deepStrictEqual(Object.keys(State).sort(), expectedMembers.slice().sort());

        assert.deepStrictEqual(snap(State), {
          phase: "BOOT",
          ready: false,
          transitionLocked: false,
          pendingPhase: null,
        });
        assert.strictEqual(Object.isFrozen(State.Phases), true);
        assert.strictEqual(Object.isFrozen(State), true);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_valid_transition_commits_only_on_matching_completion() -> None:
    harness = _STATE_BOOTSTRAP + textwrap.dedent(
        """\
        const State = freshState();

        const token = State.beginTransition("MISSION_SELECT");
        assert.notStrictEqual(token, null);

        assert.deepStrictEqual(snap(State), {
          phase: "BOOT",
          ready: false,
          transitionLocked: true,
          pendingPhase: "MISSION_SELECT",
        });
        assert.strictEqual(State.canTransition("GUP_SELECT"), false);

        assert.strictEqual(State.completeTransition(token), true);
        assert.deepStrictEqual(snap(State), {
          phase: "MISSION_SELECT",
          ready: false,
          transitionLocked: false,
          pendingPhase: null,
        });
        """
    )
    _assert_node_ok(_run_node(harness))


def test_invalid_duplicate_and_stale_transitions_are_rejected() -> None:
    harness = _STATE_BOOTSTRAP + textwrap.dedent(
        """\
        const State = freshState();

        assert.strictEqual(State.beginTransition("BOOT"), null);
        assert.strictEqual(State.beginTransition("NOT_A_PHASE"), null);
        assert.strictEqual(State.beginTransition("LAUNCH"), null);
        assert.strictEqual(State.canTransition("LAUNCH"), false);

        const first = State.beginTransition("MISSION_SELECT");
        assert.notStrictEqual(first, null);
        assert.strictEqual(State.beginTransition("GUP_SELECT"), null);

        assert.strictEqual(State.completeTransition(null), false);
        assert.strictEqual(State.completeTransition({}), false);
        assert.strictEqual(
          State.completeTransition({ id: first.id, from: "LAUNCH", to: first.to }),
          false
        );
        assert.strictEqual(
          State.completeTransition({ id: first.id, from: first.from, to: "LAUNCH" }),
          false
        );

        assert.strictEqual(State.completeTransition(first), true);
        assert.strictEqual(State.completeTransition(first), false);

        const second = State.beginTransition("GUP_SELECT");
        assert.notStrictEqual(second, null);
        assert.strictEqual(State.completeTransition(first), false);
        assert.strictEqual(State.completeTransition(second), true);
        assert.strictEqual(snap(State).phase, "GUP_SELECT");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_prd_happy_path_and_completion_branches() -> None:
    harness = _STATE_BOOTSTRAP + textwrap.dedent(
        """\
        const State = freshState();

        function step(expectedFrom, to) {
          const token = State.beginTransition(to);
          assert.notStrictEqual(token, null, "begin " + expectedFrom + " -> " + to);
          assert.strictEqual(token.from, expectedFrom);
          assert.strictEqual(token.to, to);
          assert.strictEqual(snap(State).phase, expectedFrom);
          assert.strictEqual(State.completeTransition(token), true);
          assert.strictEqual(snap(State).phase, to);
        }

        step("BOOT", "MISSION_SELECT");
        step("MISSION_SELECT", "GUP_SELECT");
        step("GUP_SELECT", "LAUNCH");
        step("LAUNCH", "TRAVEL");
        step("TRAVEL", "RESCUE_SITE_TRANSITION");
        step("RESCUE_SITE_TRANSITION", "RESCUE_TUTORIAL");
        step("RESCUE_TUTORIAL", "RESCUE_ACTIVE");
        step("RESCUE_ACTIVE", "RESCUE_SUCCESS");
        step("RESCUE_SUCCESS", "MISSION_COMPLETE");

        step("MISSION_COMPLETE", "MISSION_SELECT");
        step("MISSION_SELECT", "GUP_SELECT");
        step("GUP_SELECT", "LAUNCH");
        step("LAUNCH", "TRAVEL");
        step("TRAVEL", "RESCUE_SITE_TRANSITION");
        step("RESCUE_SITE_TRANSITION", "RESCUE_TUTORIAL");
        step("RESCUE_TUTORIAL", "RESCUE_ACTIVE");
        step("RESCUE_ACTIVE", "RESCUE_SUCCESS");
        step("RESCUE_SUCCESS", "MISSION_COMPLETE");

        step("MISSION_COMPLETE", "LAUNCH");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_snapshots_and_tokens_cannot_mutate_internal_state() -> None:
    harness = _STATE_BOOTSTRAP + textwrap.dedent(
        """\
        const State = freshState();

        const snapshotA = State.getSnapshot();
        const snapshotB = State.getSnapshot();
        assert.notStrictEqual(snapshotA, snapshotB);
        assert.strictEqual(Object.isFrozen(snapshotA), true);
        assert.strictEqual(Object.isFrozen(snapshotB), true);

        snapshotA.phase = "GUP_SELECT";
        snapshotA.pendingPhase = "LAUNCH";
        snapshotA.transitionLocked = true;
        snapshotB.ready = true;
        assert.deepStrictEqual(snap(State), {
          phase: "BOOT",
          ready: false,
          transitionLocked: false,
          pendingPhase: null,
        });

        const token = State.beginTransition("MISSION_SELECT");
        assert.strictEqual(Object.isFrozen(token), true);
        token.id = 999;
        token.from = "LAUNCH";
        token.to = "GUP_SELECT";
        assert.strictEqual(State.completeTransition(token), true);
        assert.strictEqual(snap(State).phase, "MISSION_SELECT");

        State.Phases.BOOT = "HACKED";
        State.Phases.LAUNCH = "HACKED";
        assert.strictEqual(State.Phases.BOOT, "BOOT");
        assert.strictEqual(State.Phases.LAUNCH, "LAUNCH");
        assert.strictEqual(State.beginTransition("HACKED"), null);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_app_boot_enters_mission_select_and_is_idempotent() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
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
        const document = {
          domListenerCount: 0,
          domLoadedHandler: null,
          getElementById(id) {
            if (id === "ocean-rescue-root") return rootEl;
            if (id === "ocean-rescue-status") return statusEl;
            return null;
          },
          addEventListener(type, fn) {
            if (type === "DOMContentLoaded") {
              this.domListenerCount += 1;
              this.domLoadedHandler = fn;
            }
          },
        };

        const { State, App } = loadApp(document);

        assert.strictEqual(document.domListenerCount, 1);
        assert.strictEqual(typeof document.domLoadedHandler, "function");

        document.domLoadedHandler();

        assert.deepStrictEqual(snap(State), {
          phase: "MISSION_SELECT",
          ready: true,
          transitionLocked: false,
          pendingPhase: null,
        });
        assert.strictEqual(rootEl._ready, "true");
        assert.strictEqual(statusEl.textContent, "Ocean Rescue ready");

        const before = snap(State);
        assert.strictEqual(App.boot(), true);
        assert.deepStrictEqual(snap(State), before);
        assert.strictEqual(document.domListenerCount, 1);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_app_boot_without_required_dom_is_safe() -> None:
    harness = _APP_BOOTSTRAP + textwrap.dedent(
        """\
        const expectedIdle = {
          phase: "BOOT",
          ready: false,
          transitionLocked: false,
          pendingPhase: null,
        };

        const ctxMissingRoot = loadApp({
          addEventListener(type, fn) {},
          getElementById(id) {
            return null;
          },
        });
        assert.strictEqual(ctxMissingRoot.App.boot(), false);
        assert.deepStrictEqual(snap(ctxMissingRoot.State), expectedIdle);

        const rootEl = {
          getAttribute(name) {
            return "false";
          },
          setAttribute(name, value) {},
        };
        const ctxMissingStatus = loadApp({
          addEventListener(type, fn) {},
          getElementById(id) {
            return id === "ocean-rescue-root" ? rootEl : null;
          },
        });
        assert.strictEqual(ctxMissingStatus.App.boot(), false);
        assert.deepStrictEqual(snap(ctxMissingStatus.State), expectedIdle);
        """
    )
    _assert_node_ok(_run_node(harness))
