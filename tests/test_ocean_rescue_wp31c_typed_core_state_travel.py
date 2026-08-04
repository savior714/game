"""WP-31C typed core state and travel contract.

The Ocean Rescue core state machine (`src/state.js`) and the tightly coupled
travel runtime state (`src/travel.js`) move from untyped rollback-oriented
JavaScript modules to strictly typed canonical TypeScript modules while
preserving every observable runtime contract: public API shape, return values,
invalid-input rejection, frozen object identity and immutability, transition
order, state mutation order, browser-visible flow, deterministic production
artifact, byte-identical legacy rollback sources, and the temporary
`window.OceanRescue.State`/`window.OceanRescue.Travel` compatibility ABIs
consumed by `src/app.js`.

Ownership after WP-31C:

- core state machine: `src/state/state.ts` (typed canonical);
  `src/state.js` becomes rollback-only;
- travel runtime state: `src/travel/travel.ts` (typed canonical);
  `src/travel.js` becomes rollback-only;
- adapters `src/esm/state.js` and `src/esm/travel.js` import and re-export the
  typed modules, assert the temporary global ABI identity, and no longer
  side-effect-import the legacy implementations.

This suite verifies:

- static ownership: typed modules exist and are cut into the canonical graph,
  adapters import the typed implementation and not the legacy implementation,
  no suppressions, no broad `any`, no strictness weakening, no WP-32-style
  shared type module, legacy sources byte-identical, rollback manifest
  ownership retained;
- strict TypeScript diagnostics;
- the WP-31C behavioral matrix on the real typed implementations (fresh
  runtime, independent per scenario) versus the unchanged legacy sources
  running in the same strict-mode context: return values, thrown/not-thrown,
  snapshots, transition token shape and ID sequence, frozen status, exact
  enumerable API shape, and float-exact travel results;
- runtime identity and immutability: global ABI === ESM export, frozen
  APIs/Phases/Bounds/snapshots/tokens, mutation rejection;
- deterministic production bundle + standalone HTML, tracked-artifact match,
  canonical module membership (typed state/travel in, rollback state.js/travel.js
  out), exactly-once implementation ownership;
- legacy rollback artifact byte identity and unchanged legacy sources;
- the focused browser flow with a deterministic clock (controlled
  requestAnimationFrame): deterministic profile -> mission select -> first
  mission -> GUP confirm -> launch -> TRAVEL -> active travel snapshot ->
  distance progress -> tap and drag reflected in Y -> arrival ->
  RESCUE_SITE_TRANSITION, with clean page/console/network quality and no
  leftover transition lock.

The behavioral matrix runs the real typed modules and the real ESM adapters
through a test-only Node harness that transpiles them with the already-installed
TypeScript package (no new test dependency).
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from playwright.sync_api import sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp02_browser_baseline import HTTPServerFixture  # noqa: E402

REPO_ROOT = TESTS_DIR.parent
OCEAN_DIR = REPO_ROOT / "domains" / "ocean-rescue"
SRC_DIR = OCEAN_DIR / "src"
ESM_DIR = SRC_DIR / "esm"
DIST_DIR = OCEAN_DIR / "dist"
TSCONFIG = OCEAN_DIR / "tsconfig.json"
MANIFEST = SRC_DIR / "build-manifest.json"
LEGACY_MANIFEST = SRC_DIR / "build-manifest.legacy.json"
ARTIFACT = REPO_ROOT / "ocean-rescue" / "index.html"
BUILDER = REPO_ROOT / "scripts" / "ocean_rescue" / "build_single_html.py"
JUSTFILE = REPO_ROOT / "Justfile"

BUNDLE_FILE = "ocean-rescue-app.js"
METADATA_FILE = "production-bundle-metadata.json"

STATE_LEGACY = SRC_DIR / "state.js"
TRAVEL_LEGACY = SRC_DIR / "travel.js"
STATE_TYPED = SRC_DIR / "state" / "state.ts"
TRAVEL_TYPED = SRC_DIR / "travel" / "travel.ts"
STATE_ADAPTER = ESM_DIR / "state.js"
TRAVEL_ADAPTER = ESM_DIR / "travel.js"

STATE_LEGACY_SHA256 = "ca8328a21dbe4d8719ebedb689574d03f1211749ce2b0e84016976498881d04d"
TRAVEL_LEGACY_SHA256 = (
    "78a422ab86d93cb003ec33aecd6ede4a25b5d5d78ee534c86c28a84117518cec"
)

# Pre-WP-21 canonical legacy artifact baseline; unchanged legacy sources and an
# unchanged legacy manifest must keep the rollback build byte-identical.
LEGACY_ROLLBACK_BASELINE_SHA = (
    "cfd991d83524db6c7ad225da11ef7a9421300bdf588c4b905bf4e5556f776582"
)

NODE_BIN: str = shutil.which("node") or ""
if not NODE_BIN:
    raise RuntimeError("Node executable not found on PATH")


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_legacy_manifest() -> dict:
    return json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))


# ── static ownership contract ────────────────────────────────────────────


def test_typed_modules_and_adapters_exist() -> None:
    assert STATE_TYPED.is_file(), "src/state/state.ts missing"
    assert TRAVEL_TYPED.is_file(), "src/travel/travel.ts missing"
    assert STATE_LEGACY.is_file(), "rollback-only src/state.js must remain"
    assert TRAVEL_LEGACY.is_file(), "rollback-only src/travel.js must remain"
    assert STATE_ADAPTER.is_file(), "src/esm/state.js adapter missing"
    assert TRAVEL_ADAPTER.is_file(), "src/esm/travel.js adapter missing"


def test_typed_module_exports_required_types() -> None:
    state = STATE_TYPED.read_text(encoding="utf-8")
    for token in (
        "export type Phase",
        "export interface PhaseMap",
        "export type TransitionMap",
        "export interface TransitionToken",
        "export interface StateSnapshot",
        "export interface StateApi",
        "export const Phases",
        "export { State }",
    ):
        assert token in state, f"state.ts missing declaration: {token}"
    travel = TRAVEL_TYPED.read_text(encoding="utf-8")
    for token in (
        "export interface TravelBounds",
        "export interface TravelSnapshot",
        "export interface TravelApi",
        "export const Bounds",
        "export { Travel }",
    ):
        assert token in travel, f"travel.ts missing declaration: {token}"


def test_state_module_preserves_exact_contract_literals() -> None:
    text = STATE_TYPED.read_text(encoding="utf-8")
    assert 'BOOT: "BOOT"' in text
    assert 'PROFILE_CHOICE: "PROFILE_CHOICE"' in text
    assert 'MISSION_SELECT: "MISSION_SELECT"' in text
    assert 'GUP_SELECT: "GUP_SELECT"' in text
    assert 'LAUNCH: "LAUNCH"' in text
    assert 'TRAVEL: "TRAVEL"' in text
    assert 'RESCUE_SITE_TRANSITION: "RESCUE_SITE_TRANSITION"' in text
    assert 'RESCUE_TUTORIAL: "RESCUE_TUTORIAL"' in text
    assert 'RESCUE_ACTIVE: "RESCUE_ACTIVE"' in text
    assert 'RESCUE_SUCCESS: "RESCUE_SUCCESS"' in text
    assert 'MISSION_COMPLETE: "MISSION_COMPLETE"' in text
    assert "transitionId: 0" in text
    assert "root.State = State;" in text


def test_travel_module_preserves_exact_contract_literals() -> None:
    text = TRAVEL_TYPED.read_text(encoding="utf-8")
    assert "minY: 120" in text
    assert "maxY: 600" in text
    assert "startY: 360" in text
    assert "const AutoForwardSpeed = 120;" in text
    assert "const TapSpeed = 360;" in text
    assert "applied > 50" in text
    assert "applied = 50" in text
    assert "root.Travel = Travel;" in text


def test_adapters_import_typed_implementation_and_not_legacy() -> None:
    state = STATE_ADAPTER.read_text(encoding="utf-8")
    assert 'import { State } from "../state/state";' in state
    assert "../state.js" not in state, (
        "state adapter must not import the legacy implementation"
    )
    assert 'throw new Error("OceanRescue.State was not registered")' in state
    assert "registered !== State" in state, "global ABI identity assertion missing"
    assert "export { State };" in state

    travel = TRAVEL_ADAPTER.read_text(encoding="utf-8")
    assert 'import { Travel } from "../travel/travel";' in travel
    assert "../travel.js" not in travel, (
        "travel adapter must not import the legacy implementation"
    )
    assert 'throw new Error("OceanRescue.Travel was not registered")' in travel
    assert "registered !== Travel" in travel, "global ABI identity assertion missing"
    assert "export { Travel };" in travel


def test_tsconfig_includes_typescript_sources_with_required_strictness() -> None:
    cfg = json.loads(TSCONFIG.read_text(encoding="utf-8"))
    include = cfg.get("include", [])
    assert "src/**/*.ts" in include, "tsconfig must include TypeScript sources"
    compiler = cfg.get("compilerOptions", {})
    assert compiler.get("strict") is True
    assert compiler.get("noEmit") is True
    assert compiler.get("checkJs") is False
    assert compiler.get("allowJs") is True
    assert compiler.get("module") == "ESNext"
    assert compiler.get("moduleResolution") == "Bundler"
    assert "skipLibCheck" not in compiler or compiler.get("skipLibCheck") is True, (
        "skipLibCheck must be the only relaxation"
    )


def test_no_forbidden_suppression_or_broad_any_in_typed_sources() -> None:
    forbidden = (
        "@ts-nocheck",
        "@ts-ignore",
        "@ts-expect-error",
        "as any",
        ": any",
        "<any>",
        "as unknown as any",
    )
    for path in (STATE_TYPED, TRAVEL_TYPED, STATE_ADAPTER, TRAVEL_ADAPTER):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"forbidden token in {path.name}: {token}"


def test_no_shared_cross_domain_type_module_introduced() -> None:
    forbidden_shared = {
        SRC_DIR / "types.ts",
        SRC_DIR / "shared-types.ts",
        SRC_DIR / "boundary-types.ts",
        SRC_DIR / "contracts.ts",
        SRC_DIR / "types" / "index.ts",
    }
    for path in forbidden_shared:
        assert not path.exists(), f"WP-32-style shared type module present: {path}"
    assert STATE_TYPED.relative_to(SRC_DIR).parts[0] == "state"
    assert TRAVEL_TYPED.relative_to(SRC_DIR).parts[0] == "travel"


def test_legacy_sources_remain_byte_identical() -> None:
    assert _sha256_path(STATE_LEGACY) == STATE_LEGACY_SHA256, (
        "legacy state.js changed (WP-31C must not modify it)"
    )
    assert _sha256_path(TRAVEL_LEGACY) == TRAVEL_LEGACY_SHA256, (
        "legacy travel.js changed (WP-31C must not modify it)"
    )


def test_legacy_rollback_manifest_keeps_state_and_travel_ownership() -> None:
    data = _load_legacy_manifest()
    files = {e["file"] for e in data["scripts"]}
    assert "state.js" in files, "legacy rollback manifest must reference state.js"
    assert "travel.js" in files, "legacy rollback manifest must reference travel.js"
    assert len(data["scripts"]) == 19, (
        "legacy manifest must keep the 19 ordered entries"
    )


def test_strict_typecheck_passes() -> None:
    result = subprocess.run(
        [
            "corepack",
            "pnpm",
            "exec",
            "tsc",
            "--project",
            "tsconfig.json",
            "--noEmit",
        ],
        cwd=str(OCEAN_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"tsc --noEmit failed (exit {result.returncode}):\n"
        f"{result.stdout}\n{result.stderr}"
    )


# ── behavioral matrix + legacy-versus-typed parity (Node harness) ────────

_BEHAVIOR_HARNESS = textwrap.dedent(
    """\
    const fs = require("fs");
    const os = require("os");
    const path = require("path");
    const vm = require("vm");
    const assert = require("assert");
    const { execSync } = require("child_process");

    const REPO = __REPO_ROOT__;
    const SRC = path.join(REPO, "domains", "ocean-rescue", "src");
    const TSC = path.join(
      REPO, "domains", "ocean-rescue", "node_modules", "typescript", "lib", "tsc.js"
    );

    const LEGACY_STATE = fs.readFileSync(path.join(SRC, "state.js"), "utf8");
    const LEGACY_TRAVEL = fs.readFileSync(path.join(SRC, "travel.js"), "utf8");

    const TMP = fs.realpathSync(
      fs.mkdtempSync(path.join(os.tmpdir(), "wp31c-core-state-travel-"))
    );
    try {
      execSync(
        `node "${TSC}" --ignoreConfig --module commonjs --target es2022 ` +
          `--lib es2022,dom --skipLibCheck --allowJs --checkJs false ` +
          `--outDir "${TMP}" ` +
          `"${path.join(SRC, "state", "state.ts")}" ` +
          `"${path.join(SRC, "travel", "travel.ts")}" ` +
          `"${path.join(SRC, "esm", "state.js")}" ` +
          `"${path.join(SRC, "esm", "travel.js")}"`,
        { stdio: "pipe" }
      );
    } catch (error) {
      fs.rmSync(TMP, { recursive: true, force: true });
      throw error;
    }

    function plain(value) {
      return JSON.parse(JSON.stringify(value));
    }

    // Both implementations run in strict mode to match the real ESM/bundle
    // execution context (imported modules are always strict). The legacy
    // sources are evaluated with a "use strict" prologue, exactly as ESM
    // module semantics require in production.
    function runLegacy(source, filename) {
      const win = {};
      const sandbox = { window: win };
      vm.createContext(sandbox);
      vm.runInContext('"use strict";\\n' + source, sandbox, { filename: filename });
      return win.OceanRescue;
    }

    function loadTypedState() {
      const win = {};
      const exportsObj = {};
      const sandbox = {
        window: win,
        exports: exportsObj,
        module: { exports: exportsObj },
      };
      vm.createContext(sandbox);
      const code = fs.readFileSync(path.join(TMP, "state", "state.js"), "utf8");
      vm.runInContext(code, sandbox, { filename: "state.ts" });
      return { State: win.OceanRescue.State, exported: exportsObj.State };
    }

    function loadTypedTravel() {
      const win = {};
      const exportsObj = {};
      const sandbox = {
        window: win,
        exports: exportsObj,
        module: { exports: exportsObj },
      };
      vm.createContext(sandbox);
      const code = fs.readFileSync(path.join(TMP, "travel", "travel.js"), "utf8");
      vm.runInContext(code, sandbox, { filename: "travel.ts" });
      return { Travel: win.OceanRescue.Travel, exported: exportsObj.Travel };
    }

    function loadTypedAdapters() {
      const win = {};
      globalThis.window = win;
      const adapterState = require(path.join(TMP, "esm", "state.js"));
      const adapterTravel = require(path.join(TMP, "esm", "travel.js"));
      assert.strictEqual(
        adapterState.State,
        win.OceanRescue.State,
        "state ESM export must be the frozen global API"
      );
      assert.strictEqual(
        adapterTravel.Travel,
        win.OceanRescue.Travel,
        "travel ESM export must be the frozen global API"
      );
      return { adapterState: adapterState, adapterTravel: adapterTravel, win: win };
    }

    // ── State parity matrix ─────────────────────────────────────────────

    const STATE_SCENARIOS = {
      initial_snapshot: { steps: [] },
      mark_ready_first: { steps: [["markReady"], ["markReady"], ["snapshot"]] },
      boot_to_profile_choice: {
        steps: [["begin", "PROFILE_CHOICE"], ["completeCurrent"], ["snapshot"]],
      },
      boot_to_mission_select: {
        steps: [["begin", "MISSION_SELECT"], ["completeCurrent"], ["snapshot"]],
      },
      forbidden_boot_to_travel: {
        steps: [["begin", "TRAVEL"], ["snapshot"]],
      },
      same_phase_rejected: {
        steps: [["begin", "BOOT"], ["snapshot"]],
      },
      invalid_string_phase: {
        steps: [["begin", "NOT_A_PHASE"], ["snapshot"]],
      },
      non_string_phase: {
        steps: [["begin", 42], ["begin", null], ["begin", {}], ["begin", undefined], ["snapshot"]],
      },
      second_transition_rejected: {
        steps: [
          ["begin", "MISSION_SELECT"],
          ["begin", "GUP_SELECT"],
          ["completeCurrent"],
          ["snapshot"],
        ],
      },
      valid_token_complete: {
        steps: [
          ["begin", "MISSION_SELECT"],
          ["completeCurrent"],
          ["snapshot"],
          ["can", "GUP_SELECT"],
        ],
      },
      stale_token_complete: {
        steps: [
          ["begin", "MISSION_SELECT"],
          ["completeCurrent"],
          ["completeCurrent"],
          ["snapshot"],
        ],
      },
      forged_id_token: {
        steps: [
          ["begin", "MISSION_SELECT"],
          ["completeForgedId"],
          ["snapshot"],
        ],
      },
      forged_from_token: {
        steps: [
          ["begin", "MISSION_SELECT"],
          ["completeForgedFrom"],
          ["snapshot"],
        ],
      },
      forged_to_token: {
        steps: [
          ["begin", "MISSION_SELECT"],
          ["completeForgedTo"],
          ["snapshot"],
        ],
      },
      null_token: {
        steps: [
          ["begin", "MISSION_SELECT"],
          ["completeNull"],
          ["completeUndefined"],
          ["snapshot"],
        ],
      },
      primitive_token: {
        steps: [
          ["begin", "MISSION_SELECT"],
          ["completePrimitive"],
          ["completeString"],
          ["completeEmptyObject"],
          ["snapshot"],
        ],
      },
      force_phase_valid: {
        steps: [["force", "TRAVEL"], ["snapshot"]],
      },
      force_phase_invalid: {
        steps: [["force", "NOT_A_PHASE"], ["force", 42], ["snapshot"]],
      },
      force_clears_active_transition: {
        steps: [
          ["begin", "MISSION_SELECT"],
          ["force", "TRAVEL"],
          ["completeCurrent"],
          ["begin", "RESCUE_SITE_TRANSITION"],
          ["completeCurrent"],
          ["snapshot"],
        ],
      },
      full_progression: {
        steps: [
          ["begin", "MISSION_SELECT"],
          ["completeCurrent"],
          ["begin", "GUP_SELECT"],
          ["completeCurrent"],
          ["begin", "LAUNCH"],
          ["completeCurrent"],
          ["begin", "TRAVEL"],
          ["completeCurrent"],
          ["begin", "RESCUE_SITE_TRANSITION"],
          ["completeCurrent"],
          ["begin", "RESCUE_TUTORIAL"],
          ["completeCurrent"],
          ["begin", "RESCUE_ACTIVE"],
          ["completeCurrent"],
          ["begin", "RESCUE_SUCCESS"],
          ["completeCurrent"],
          ["begin", "MISSION_COMPLETE"],
          ["completeCurrent"],
          ["snapshot"],
        ],
      },
      mission_complete_to_mission_select: {
        steps: [
          ["force", "MISSION_COMPLETE"],
          ["begin", "MISSION_SELECT"],
          ["completeCurrent"],
          ["snapshot"],
        ],
      },
      mission_complete_to_launch: {
        steps: [
          ["force", "MISSION_COMPLETE"],
          ["begin", "LAUNCH"],
          ["completeCurrent"],
          ["snapshot"],
        ],
      },
      snapshot_mutation_attempt: {
        steps: [["snapshot"], ["mutateSnapshot"], ["snapshot"]],
      },
      token_mutation_attempt: {
        steps: [
          ["begin", "MISSION_SELECT"],
          ["mutateToken"],
          ["completeCurrent"],
          ["snapshot"],
        ],
      },
      api_mutation_attempt: {
        steps: [["mutateApi"], ["snapshot"]],
      },
      phases_mutation_attempt: {
        steps: [["mutatePhases"], ["snapshot"]],
      },
    };

    function runStateScenario(kind, spec) {
      let S;
      let loaded = null;
      if (kind === "typed") {
        loaded = loadTypedState();
        S = loaded.State;
      } else {
        S = runLegacy(LEGACY_STATE, "state.js").State;
      }
      const out = {
        apiKeys: Object.keys(S).sort(),
        apiFrozen: Object.isFrozen(S),
        phasesKeys: Object.keys(S.Phases),
        phasesValues: plain(S.Phases),
        phasesFrozen: Object.isFrozen(S.Phases),
        snapshot0: plain(S.getSnapshot()),
        snapshotFrozen: Object.isFrozen(S.getSnapshot()),
        steps: [],
        thrown: null,
      };
      let lastToken = null;
      try {
        for (const step of spec.steps || []) {
          const op = step[0];
          if (op === "snapshot") {
            out.steps.push(["snapshot", plain(S.getSnapshot())]);
          } else if (op === "markReady") {
            out.steps.push(["markReady", S.markReady()]);
          } else if (op === "can") {
            out.steps.push(["can", S.canTransition(step[1])]);
          } else if (op === "begin") {
            const token = S.beginTransition(step[1]);
            lastToken = token;
            out.steps.push([
              "begin",
              token === null
                ? null
                : {
                    id: token.id,
                    from: token.from,
                    to: token.to,
                    frozen: Object.isFrozen(token),
                    keys: Object.keys(token),
                  },
            ]);
          } else if (op === "completeCurrent") {
            out.steps.push([
              "completeCurrent",
              S.completeTransition(lastToken),
              plain(S.getSnapshot()),
            ]);
          } else if (op === "completeNull") {
            out.steps.push(["completeNull", S.completeTransition(null)]);
          } else if (op === "completeUndefined") {
            out.steps.push(["completeUndefined", S.completeTransition(undefined)]);
          } else if (op === "completePrimitive") {
            out.steps.push(["completePrimitive", S.completeTransition(42)]);
          } else if (op === "completeString") {
            out.steps.push(["completeString", S.completeTransition("token")]);
          } else if (op === "completeEmptyObject") {
            out.steps.push(["completeEmptyObject", S.completeTransition({})]);
          } else if (op === "completeForgedId") {
            out.steps.push([
              "completeForgedId",
              S.completeTransition({
                id: lastToken ? lastToken.id + 100 : 100,
                from: "BOOT",
                to: "MISSION_SELECT",
              }),
            ]);
          } else if (op === "completeForgedFrom") {
            out.steps.push([
              "completeForgedFrom",
              S.completeTransition({
                id: lastToken ? lastToken.id : 1,
                from: "LAUNCH",
                to: lastToken ? lastToken.to : "MISSION_SELECT",
              }),
            ]);
          } else if (op === "completeForgedTo") {
            out.steps.push([
              "completeForgedTo",
              S.completeTransition({
                id: lastToken ? lastToken.id : 1,
                from: lastToken ? lastToken.from : "BOOT",
                to: "LAUNCH",
              }),
            ]);
          } else if (op === "force") {
            out.steps.push(["force", S.forcePhase(step[1]), plain(S.getSnapshot())]);
          } else if (op === "mutateSnapshot") {
            let threw = false;
            const snap = S.getSnapshot();
            try {
              snap.phase = "LAUNCH";
              snap.ready = true;
              snap.transitionLocked = true;
              snap.pendingPhase = "TRAVEL";
            } catch (error) {
              threw = true;
            }
            out.steps.push([
              "mutateSnapshot",
              { threw: threw, phaseAfter: snap.phase },
            ]);
          } else if (op === "mutateToken") {
            let threw = false;
            const before = lastToken ? plain(lastToken) : null;
            if (lastToken) {
              try {
                lastToken.id = 999;
                lastToken.from = "LAUNCH";
                lastToken.to = "GUP_SELECT";
              } catch (error) {
                threw = true;
              }
            }
            out.steps.push([
              "mutateToken",
              { threw: threw, before: before, after: lastToken ? plain(lastToken) : null },
            ]);
          } else if (op === "mutateApi") {
            let threw = false;
            try {
              S.extra = 1;
            } catch (error) {
              threw = true;
            }
            out.steps.push(["mutateApi", { threw: threw, extra: S.extra }]);
          } else if (op === "mutatePhases") {
            let threw = false;
            try {
              S.Phases.BOOT = "HACKED";
            } catch (error) {
              threw = true;
            }
            out.steps.push([
              "mutatePhases",
              { threw: threw, boot: S.Phases.BOOT, launch: S.Phases.LAUNCH },
            ]);
          } else {
            throw new Error("unknown state op " + op);
          }
        }
      } catch (error) {
        out.thrown = String(error && error.message);
      }
      if (kind === "typed") {
        assert.strictEqual(
          loaded.exported,
          S,
          "typed State ESM export must be the frozen global API object"
        );
      }
      return out;
    }

    for (const name of Object.keys(STATE_SCENARIOS)) {
      const spec = STATE_SCENARIOS[name];
      const legacyOut = runStateScenario("legacy", spec);
      const typedOut = runStateScenario("typed", spec);
      const legacyJson = JSON.stringify(legacyOut);
      const typedJson = JSON.stringify(typedOut);
      assert.strictEqual(
        typedJson,
        legacyJson,
        "state legacy/typed parity mismatch for " + name +
          "\\nlegacy=" + legacyJson + "\\ntyped=" + typedJson
      );
    }

    {
      const s = runStateScenario("typed", STATE_SCENARIOS.initial_snapshot);
      assert.deepStrictEqual(s.snapshot0, {
        phase: "BOOT",
        ready: false,
        transitionLocked: false,
        pendingPhase: null,
      });
      assert.deepStrictEqual(s.phasesKeys, [
        "BOOT",
        "PROFILE_CHOICE",
        "MISSION_SELECT",
        "GUP_SELECT",
        "LAUNCH",
        "TRAVEL",
        "RESCUE_SITE_TRANSITION",
        "RESCUE_TUTORIAL",
        "RESCUE_ACTIVE",
        "RESCUE_SUCCESS",
        "MISSION_COMPLETE",
      ]);
      assert.deepStrictEqual(s.apiKeys, [
        "Phases",
        "beginTransition",
        "canTransition",
        "completeTransition",
        "forcePhase",
        "getSnapshot",
        "markReady",
      ]);
    }
    {
      const s = runStateScenario("typed", STATE_SCENARIOS.full_progression);
      const beginIds = s.steps
        .filter(function (step) { return step[0] === "begin"; })
        .map(function (step) { return step[1].id; });
      assert.deepStrictEqual(beginIds, [1, 2, 3, 4, 5, 6, 7, 8, 9],
        "transition IDs must be monotonically increasing");
      assert.deepStrictEqual(s.snapshot0.phase, "BOOT");
      assert.strictEqual(
        s.steps[s.steps.length - 1][1].phase,
        "MISSION_COMPLETE"
      );
    }

    // ── Travel parity matrix ────────────────────────────────────────────

    function tapMovement(target, steps) {
      const out = [["tapTo", target]];
      for (let i = 0; i < steps; i += 1) {
        out.push(["step", 50]);
      }
      out.push(["snapshot"]);
      return out;
    }

    const TRAVEL_SCENARIOS = {
      initial_snapshot: { steps: [] },
      inactive_stop: { steps: [["stop"], ["snapshot"]] },
      inactive_step: { steps: [["step", 50], ["snapshot"]] },
      inactive_tap_to: { steps: [["tapTo", 400], ["snapshot"]] },
      inactive_begin_drag: { steps: [["beginDrag", 1, 400], ["snapshot"]] },
      start: { steps: [["start"], ["snapshot"]] },
      repeated_start: { steps: [["start"], ["start"], ["snapshot"]] },
      positive_step: { steps: [["start"], ["step", 1000], ["snapshot"]] },
      delta_over_50_cap: { steps: [["start"], ["step", 5000], ["snapshot"]] },
      multiplier_omitted: { steps: [["start"], ["step", 1000, undefined], ["snapshot"]] },
      multiplier_zero: { steps: [["start"], ["stepM", 1000, 0], ["snapshot"]] },
      multiplier_one: { steps: [["start"], ["stepM", 1000, 1], ["snapshot"]] },
      multiplier_negative: { steps: [["start"], ["stepM", 1000, -0.5], ["snapshot"]] },
      multiplier_over_one: { steps: [["start"], ["stepM", 1000, 1.5], ["snapshot"]] },
      multiplier_nan: { steps: [["start"], ["stepM", 1000, NaN], ["snapshot"]] },
      multiplier_infinity: {
        steps: [["start"], ["stepM", 1000, Infinity], ["snapshot"]],
      },
      invalid_delta: {
        steps: [
          ["start"],
          ["step", 0],
          ["step", -5],
          ["step", NaN],
          ["step", Infinity],
          ["step", "50"],
          ["step", null],
          ["step", {}],
          ["snapshot"],
        ],
      },
      tap_above_max_y: { steps: [["start"], ["tapTo", 700], ["snapshot"]] },
      tap_below_min_y: { steps: [["start"], ["tapTo", -50], ["snapshot"]] },
      tap_equal_current_y: { steps: [["start"], ["tapTo", 360], ["snapshot"]] },
      tap_movement_completion: {
        steps: tapMovement(600, 15),
      },
      drag_begin: { steps: [["start"], ["beginDrag", 7, 400], ["snapshot"]] },
      second_drag_begin_rejected: {
        steps: [["start"], ["beginDrag", 7, 400], ["beginDrag", 8, 500], ["snapshot"]],
      },
      wrong_pointer_move: {
        steps: [["start"], ["beginDrag", 7, 400], ["moveDrag", 8, 420], ["snapshot"]],
      },
      correct_pointer_move: {
        steps: [["start"], ["beginDrag", 7, 400], ["moveDrag", 7, 420], ["snapshot"]],
      },
      drag_clamping: {
        steps: [
          ["start"],
          ["beginDrag", 7, 400],
          ["moveDrag", 7, 1000],
          ["moveDrag", 7, 980],
          ["moveDrag", 7, -100],
          ["moveDrag", 7, -80],
          ["snapshot"],
        ],
      },
      wrong_pointer_end: {
        steps: [["start"], ["beginDrag", 7, 400], ["endDrag", 8], ["snapshot"]],
      },
      correct_pointer_end: {
        steps: [
          ["start"],
          ["beginDrag", 7, 400],
          ["moveDrag", 7, 430],
          ["endDrag", 7],
          ["snapshot"],
        ],
      },
      tap_while_dragging_rejected: {
        steps: [["start"], ["beginDrag", 7, 400], ["tapTo", 500], ["snapshot"]],
      },
      stop_during_tap: {
        steps: [["start"], ["tapTo", 500], ["stop"], ["step", 50], ["snapshot"]],
      },
      stop_during_drag: {
        steps: [
          ["start"],
          ["beginDrag", 7, 400],
          ["moveDrag", 7, 450],
          ["stop"],
          ["moveDrag", 7, 500],
          ["endDrag", 7],
          ["snapshot"],
        ],
      },
      restart_after_stop: {
        steps: [["start"], ["step", 1000], ["stop"], ["start"], ["snapshot"]],
      },
      bounds_mutation_attempt: { steps: [["mutateBounds"], ["snapshot"]] },
      snapshot_mutation_attempt: {
        steps: [["snapshot"], ["mutateSnapshot"], ["snapshot"]],
      },
      api_mutation_attempt: { steps: [["mutateApi"], ["snapshot"]] },
    };

    function runTravelScenario(kind, spec) {
      let T;
      let loaded = null;
      if (kind === "typed") {
        loaded = loadTypedTravel();
        T = loaded.Travel;
      } else {
        T = runLegacy(LEGACY_TRAVEL, "travel.js").Travel;
      }
      const out = {
        apiKeys: Object.keys(T).sort(),
        apiFrozen: Object.isFrozen(T),
        bounds: plain(T.Bounds),
        boundsKeys: Object.keys(T.Bounds),
        boundsFrozen: Object.isFrozen(T.Bounds),
        autoForwardSpeed: T.AutoForwardSpeed,
        tapSpeed: T.TapSpeed,
        snapshot0: plain(T.getSnapshot()),
        snapshotFrozen: Object.isFrozen(T.getSnapshot()),
        steps: [],
        thrown: null,
      };
      try {
        for (const step of spec.steps || []) {
          const op = step[0];
          if (op === "snapshot") {
            out.steps.push(["snapshot", plain(T.getSnapshot())]);
          } else if (op === "start") {
            out.steps.push(["start", T.start()]);
          } else if (op === "stop") {
            out.steps.push(["stop", T.stop()]);
          } else if (op === "step") {
            out.steps.push(["step", step[1], T.step(step[1])]);
          } else if (op === "stepM") {
            out.steps.push(["stepM", step[1], step[2], T.step(step[1], step[2])]);
          } else if (op === "tapTo") {
            out.steps.push(["tapTo", step[1], T.tapTo(step[1])]);
          } else if (op === "beginDrag") {
            out.steps.push(["beginDrag", step[1], step[2], T.beginDrag(step[1], step[2])]);
          } else if (op === "moveDrag") {
            out.steps.push(["moveDrag", step[1], step[2], T.moveDrag(step[1], step[2])]);
          } else if (op === "endDrag") {
            out.steps.push(["endDrag", step[1], T.endDrag(step[1])]);
          } else if (op === "mutateBounds") {
            let threw = false;
            try {
              T.Bounds.extra = 1;
              T.Bounds.minY = 0;
              T.Bounds.maxY = 0;
            } catch (error) {
              threw = true;
            }
            out.steps.push([
              "mutateBounds",
              { threw: threw, bounds: plain(T.Bounds) },
            ]);
          } else if (op === "mutateSnapshot") {
            let threw = false;
            const snap = T.getSnapshot();
            try {
              snap.active = true;
              snap.distance = 999;
              snap.y = 999;
              snap.tapTargetY = 111;
            } catch (error) {
              threw = true;
            }
            out.steps.push([
              "mutateSnapshot",
              { threw: threw, snap: plain(T.getSnapshot()) },
            ]);
          } else if (op === "mutateApi") {
            let threw = false;
            try {
              T.extra = 1;
              T.AutoForwardSpeed = 999;
              T.Bounds.startY = 0;
            } catch (error) {
              threw = true;
            }
            out.steps.push([
              "mutateApi",
              {
                threw: threw,
                extra: T.extra,
                autoForwardSpeed: T.AutoForwardSpeed,
                startY: T.Bounds.startY,
              },
            ]);
          } else {
            throw new Error("unknown travel op " + op);
          }
        }
      } catch (error) {
        out.thrown = String(error && error.message);
      }
      if (kind === "typed") {
        assert.strictEqual(
          loaded.exported,
          T,
          "typed Travel ESM export must be the frozen global API object"
        );
      }
      return out;
    }

    for (const name of Object.keys(TRAVEL_SCENARIOS)) {
      const spec = TRAVEL_SCENARIOS[name];
      const legacyOut = runTravelScenario("legacy", spec);
      const typedOut = runTravelScenario("typed", spec);
      const legacyJson = JSON.stringify(legacyOut);
      const typedJson = JSON.stringify(typedOut);
      assert.strictEqual(
        typedJson,
        legacyJson,
        "travel legacy/typed parity mismatch for " + name +
          "\\nlegacy=" + legacyJson + "\\ntyped=" + typedJson
      );
    }

    {
      const s = runTravelScenario("typed", TRAVEL_SCENARIOS.initial_snapshot);
      assert.deepStrictEqual(s.snapshot0, {
        active: false,
        distance: 0,
        y: 360,
        tapTargetY: null,
        dragging: false,
        pointerId: null,
      });
      assert.deepStrictEqual(s.bounds, { minY: 120, maxY: 600, startY: 360 });
      assert.strictEqual(s.autoForwardSpeed, 120);
      assert.strictEqual(s.tapSpeed, 360);
      assert.deepStrictEqual(s.apiKeys, [
        "AutoForwardSpeed",
        "Bounds",
        "TapSpeed",
        "beginDrag",
        "endDrag",
        "getSnapshot",
        "moveDrag",
        "start",
        "step",
        "stop",
        "tapTo",
      ]);
    }
    {
      const s = runTravelScenario("typed", TRAVEL_SCENARIOS.correct_pointer_move);
      const lastSnap = s.steps[s.steps.length - 1][1];
      assert.strictEqual(lastSnap.y, 380);
    }

    // Adapter identity (global ABI === ESM export) through the real adapters.
    const adapters = loadTypedAdapters();

    console.log("WP31C typed core state/travel matrix + parity: PASS");
    """
).replace("__REPO_ROOT__", repr(str(REPO_ROOT)))


def _run_behavior_harness() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [NODE_BIN, "-e", _BEHAVIOR_HARNESS],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_typed_core_state_travel_behavioral_matrix_and_parity() -> None:
    result = _run_behavior_harness()
    assert result.returncode == 0, (
        f"WP-31C behavior harness failed (exit {result.returncode}):\n"
        f"{result.stdout}\n{result.stderr}"
    )


# ── production determinism + membership ──────────────────────────────────


def _run_vite_build(config: str) -> subprocess.CompletedProcess[str]:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    return subprocess.run(
        [
            "corepack",
            "pnpm",
            "exec",
            "vite",
            "build",
            "--config",
            config,
        ],
        cwd=str(OCEAN_DIR),
        capture_output=True,
        text=True,
    )


def _build_artifact(output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--mode",
            "production",
            "--manifest",
            str(MANIFEST),
            "--output",
            str(output),
            "--bundle",
            str(DIST_DIR / BUNDLE_FILE),
            "--metadata",
            str(DIST_DIR / METADATA_FILE),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def _build_legacy(output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--mode",
            "legacy",
            "--manifest",
            str(LEGACY_MANIFEST),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_two_clean_production_bundles_byte_identical(tmp_path: Path) -> None:
    result_a = _run_vite_build("vite.production.config.ts")
    assert result_a.returncode == 0, result_a.stderr
    comparison = tmp_path / "bundle_a"
    comparison.mkdir()
    for path in DIST_DIR.iterdir():
        if path.is_file():
            shutil.copy2(path, comparison / path.name)
    result_b = _run_vite_build("vite.production.config.ts")
    assert result_b.returncode == 0, result_b.stderr
    files_a = sorted(p.name for p in comparison.iterdir() if p.is_file())
    files_b = sorted(p.name for p in DIST_DIR.iterdir() if p.is_file())
    assert files_a == files_b
    for name in files_b:
        assert (comparison / name).read_bytes() == (DIST_DIR / name).read_bytes(), (
            f"production bundle byte mismatch for {name}"
        )


def test_two_standalone_html_builds_byte_identical(tmp_path: Path) -> None:
    result = _run_vite_build("vite.production.config.ts")
    assert result.returncode == 0, result.stderr
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    assert _build_artifact(a).returncode == 0
    assert _build_artifact(b).returncode == 0
    assert a.read_bytes() == b.read_bytes()


def test_tracked_artifact_matches_clean_production_rebuild(tmp_path: Path) -> None:
    result = _run_vite_build("vite.production.config.ts")
    assert result.returncode == 0, result.stderr
    output = tmp_path / "rebuilt.html"
    assert _build_artifact(output).returncode == 0
    assert output.read_bytes() == ARTIFACT.read_bytes()


def test_canonical_production_membership() -> None:
    result = _run_vite_build("vite.production.config.ts")
    assert result.returncode == 0, result.stderr
    metadata = json.loads((DIST_DIR / METADATA_FILE).read_text(encoding="utf-8"))
    actual = set(metadata["actual_module_files"])
    for typed in ("state/state.ts", "travel/travel.ts"):
        assert typed in actual, f"typed module {typed} missing from canonical bundle"
    for rollback in ("state.js", "travel.js"):
        assert rollback not in actual, (
            f"rollback-only legacy {rollback} must be excluded from the bundle"
        )
    for retained in (
        "profile/profile.ts",
        "missions/catalog.ts",
        "gups/catalog.ts",
        "launch/launch.ts",
        "missions.js",
        "gups.js",
    ):
        assert retained in actual, (
            f"existing typed/controller module {retained} must stay in the bundle"
        )
    for excluded in ("profile.js", "launch.js"):
        assert excluded not in actual, (
            f"rollback-only legacy {excluded} must be excluded from the bundle"
        )


def test_exactly_once_implementation_ownership() -> None:
    result = _run_vite_build("vite.production.config.ts")
    assert result.returncode == 0, result.stderr
    metadata = json.loads((DIST_DIR / METADATA_FILE).read_text(encoding="utf-8"))
    actual = metadata["actual_module_files"]
    for raw in actual:
        if raw.endswith(".ts") and raw.startswith("state/"):
            assert actual.count(raw) == 1, f"typed {raw} must occur exactly once"
        if raw.endswith(".ts") and raw.startswith("travel/"):
            assert actual.count(raw) == 1, f"typed {raw} must occur exactly once"
    assert metadata["dynamic_import_count"] == 0


def test_legacy_rollback_references_sources_and_matches_baseline(
    tmp_path: Path,
) -> None:
    legacy = _load_legacy_manifest()
    files = {e["file"] for e in legacy["scripts"]}
    for name in ("state.js", "travel.js"):
        assert name in files, f"legacy rollback manifest must reference {name}"
    output = tmp_path / "legacy.html"
    result = _build_legacy(output)
    assert result.returncode == 0, (
        f"legacy rollback build failed (exit {result.returncode}): {result.stderr}"
    )
    assert _sha256_bytes(output.read_bytes()) == LEGACY_ROLLBACK_BASELINE_SHA, (
        "legacy rollback artifact must be byte-identical to the pre-WP-31C baseline"
    )
    html = output.read_text(encoding="utf-8")
    assert html.count("<script>") == 19
    assert re.search(r"<script\s+[^>]*src\s*=", html) is None


# ── focused browser flow ─────────────────────────────────────────────────


_RAF_INIT_SCRIPT = """(() => {
  if (typeof Element !== 'undefined') {
    Element.prototype.setPointerCapture = function () {};
    Element.prototype.releasePointerCapture = function () {};
  }
  window.__rafCallbacks = {};
  window.__rafQueue = [];
  window.__rafNextId = 1;
  window.__rafTime = 0;
  window.requestAnimationFrame = (cb) => {
    const id = window.__rafNextId++;
    window.__rafCallbacks[id] = cb;
    window.__rafQueue.push(id);
    return id;
  };
  window.cancelAnimationFrame = (id) => {
    delete window.__rafCallbacks[id];
    const idx = window.__rafQueue.indexOf(id);
    if (idx !== -1) window.__rafQueue.splice(idx, 1);
  };
  window.__rafRun = (ms) => {
    window.__rafTime += ms;
    if (window.__rafQueue.length === 0) return 0;
    const id = window.__rafQueue.shift();
    const cb = window.__rafCallbacks[id];
    delete window.__rafCallbacks[id];
    if (typeof cb === "function") cb(window.__rafTime);
    return 1;
  };
  window.__rafPending = () => window.__rafQueue.length;
})()"""


def _visible(page, selector: str) -> bool:
    return bool(
        page.evaluate(
            """sel => {
              const el = document.querySelector(sel);
              return !!el && !el.hidden && getComputedStyle(el).display !== 'none';
            }""",
            selector,
        )
    )


def _run_raf_frames(page, count: int, step_ms: int = 50) -> int:
    return page.evaluate(
        """(args) => {
          let ran = 0;
          for (let i = 0; i < args.count; i += 1) {
            ran += window.__rafRun(args.stepMs);
          }
          return ran;
        }""",
        {"count": count, "stepMs": step_ms},
    )


def test_browser_state_travel_flow() -> None:
    server = HTTPServerFixture()
    base_url = server.start()
    page_errors: list[str] = []
    console_errors: list[str] = []
    request_failures: list[str] = []
    requests: list[dict] = []

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--disable-background-networking", "--disable-component-update"],
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )
                context.add_init_script("window.localStorage.clear();")
                context.add_init_script(
                    "window.localStorage.setItem("
                    "'aidengame.oceanRescue.profile', JSON.stringify("
                    "{schemaVersion:1, playerName:'Aiden', animalId:'beaver'}));"
                )
                context.add_init_script(_RAF_INIT_SCRIPT)
                page = context.new_page()
                page.on("pageerror", lambda e: page_errors.append(str(e)))
                page.on(
                    "console",
                    lambda m: (
                        console_errors.append(m.text) if m.type == "error" else None
                    ),
                )
                page.on("requestfailed", lambda r: request_failures.append(r.url))
                page.on(
                    "request",
                    lambda r: requests.append({"url": r.url, "type": r.resource_type}),
                )

                page.goto(f"{base_url}/ocean-rescue/index.html")
                page.wait_for_selector(
                    "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=30000
                )
                page.wait_for_function(
                    """() => {
                      const el = document.getElementById('ocean-rescue-mission-select');
                      return !!el && getComputedStyle(el).display !== 'none';
                    }""",
                    timeout=10000,
                )
                assert _visible(page, "#ocean-rescue-profile-choice") is False, (
                    "deterministic seeded profile must skip the profile choice"
                )

                # Mission select -> first mission -> GUP select -> confirm.
                page.click('#ocean-rescue-mission-list [data-mission-id="sea-turtle"]')
                page.wait_for_selector("#ocean-rescue-gup-select:not([hidden])")
                page.click('#ocean-rescue-gup-list [data-gup-id="gup-x"]')
                page.click("#ocean-rescue-gup-launch")
                page.wait_for_selector("#ocean-rescue-launch:not([hidden])")

                runtime = page.evaluate(
                    """() => {
                      const S = OceanRescue.State;
                      const T = OceanRescue.Travel;
                      return {
                        phase: S.getSnapshot().phase,
                        ready: S.getSnapshot().ready,
                        locked: S.getSnapshot().transitionLocked,
                        pending: S.getSnapshot().pendingPhase,
                        stateFrozen: Object.isFrozen(S),
                        phasesFrozen: Object.isFrozen(S.Phases),
                        phases: Object.keys(S.Phases),
                        travelFrozen: Object.isFrozen(T),
                        bounds: T.Bounds,
                        boundsFrozen: Object.isFrozen(T.Bounds),
                        autoForwardSpeed: T.AutoForwardSpeed,
                        tapSpeed: T.TapSpeed
                      };
                    }"""
                )
                assert runtime["phase"] == "LAUNCH", runtime
                assert runtime["ready"] is True
                assert runtime["locked"] is False, "no transition lock may remain"
                assert runtime["pending"] is None
                assert runtime["stateFrozen"] is True
                assert runtime["phasesFrozen"] is True
                assert runtime["phases"][0] == "BOOT"
                assert runtime["phases"][10] == "MISSION_COMPLETE"
                assert runtime["travelFrozen"] is True
                assert runtime["bounds"] == {
                    "minY": 120,
                    "maxY": 600,
                    "startY": 360,
                }
                assert runtime["boundsFrozen"] is True
                assert runtime["autoForwardSpeed"] == 120
                assert runtime["tapSpeed"] == 360

                # Skip the launch sequence into TRAVEL.
                page.click("#ocean-rescue-launch-skip")
                page.wait_for_selector(
                    "#ocean-rescue-root[data-travel-scene=active]", timeout=15000
                )

                travel = page.evaluate(
                    """() => {
                      const S = OceanRescue.State;
                      const T = OceanRescue.Travel;
                      const snap = T.getSnapshot();
                      return {
                        phase: S.getSnapshot().phase,
                        locked: S.getSnapshot().transitionLocked,
                        active: snap.active,
                        distance: snap.distance,
                        y: snap.y,
                        tapTargetY: snap.tapTargetY,
                        dragging: snap.dragging,
                        pointerId: snap.pointerId
                      };
                    }"""
                )
                assert travel["phase"] == "TRAVEL", travel
                assert travel["locked"] is False
                assert travel["active"] is True
                assert travel["distance"] == 0
                assert travel["y"] == 360
                assert travel["tapTargetY"] is None
                assert travel["dragging"] is False
                assert travel["pointerId"] is None

                # Drive the deterministic travel clock; distance must advance.
                _run_raf_frames(page, 20, 50)
                advanced = page.evaluate(
                    "() => ({ distance: OceanRescue.Travel.getSnapshot().distance, "
                    "phase: OceanRescue.State.getSnapshot().phase })"
                )
                assert advanced["phase"] == "TRAVEL", advanced
                assert advanced["distance"] > 0, (
                    "travel distance must advance under the deterministic clock"
                )
                distance_before = advanced["distance"]

                # Tap input reflected in Y state.
                tap = page.evaluate(
                    """() => {
                      const canvas = document.getElementById('ocean-rescue-canvas');
                      const rect = canvas.getBoundingClientRect();
                      const clientX = rect.left + 640;
                      const clientY = rect.top + (200 / 720) * rect.height;
                      canvas.dispatchEvent(new PointerEvent('pointerdown', {
                        pointerId: 11, clientX, clientY, isPrimary: true, button: 0,
                        bubbles: true
                      }));
                      canvas.dispatchEvent(new PointerEvent('pointerup', {
                        pointerId: 11, clientX, clientY, isPrimary: true, button: 0,
                        bubbles: true
                      }));
                      return OceanRescue.Travel.getSnapshot();
                    }"""
                )
                assert tap["tapTargetY"] is not None, "tap must set a Y target"
                assert 120 <= tap["tapTargetY"] <= 600, tap
                assert tap["y"] != tap["tapTargetY"], "tap target must differ from Y"

                # Drive frames; Y must move toward the tap target and clear it.
                _run_raf_frames(page, 60, 50)
                tap_done = page.evaluate(
                    """() => {
                      const snap = OceanRescue.Travel.getSnapshot();
                      return { y: snap.y, tapTargetY: snap.tapTargetY,
                               distance: snap.distance,
                               phase: OceanRescue.State.getSnapshot().phase };
                    }"""
                )
                assert tap_done["phase"] == "TRAVEL", tap_done
                assert tap_done["tapTargetY"] is None, (
                    "tap target must clear after the movement completes"
                )
                assert tap_done["y"] == 200, (
                    "tap input must move the Y state to the target"
                )
                assert tap_done["distance"] > distance_before, (
                    "distance must keep advancing with the tap movement"
                )
                y_before_drag = tap_done["y"]

                # Drag input reflected in Y state.
                drag = page.evaluate(
                    """() => {
                      const canvas = document.getElementById('ocean-rescue-canvas');
                      const rect = canvas.getBoundingClientRect();
                      const y0 = rect.top + (400 / 720) * rect.height;
                      const y1 = rect.top + (460 / 720) * rect.height;
                      const clientX = rect.left + 640;
                      const down = new PointerEvent('pointerdown', {
                        pointerId: 21, clientX, clientY: y0, isPrimary: true,
                        button: 0, bubbles: true
                      });
                      canvas.dispatchEvent(down);
                      canvas.dispatchEvent(new PointerEvent('pointermove', {
                        pointerId: 21, clientX, clientY: y1, isPrimary: true,
                        button: 0, bubbles: true
                      }));
                      return OceanRescue.Travel.getSnapshot();
                    }"""
                )
                assert drag["dragging"] is True, "drag must begin"
                assert drag["pointerId"] == 21
                assert drag["y"] != y_before_drag, "drag must move the Y state"
                drag_end = page.evaluate(
                    """() => {
                      const canvas = document.getElementById('ocean-rescue-canvas');
                      const rect = canvas.getBoundingClientRect();
                      const clientX = rect.left + 640;
                      const clientY = rect.top + (460 / 720) * rect.height;
                      canvas.dispatchEvent(new PointerEvent('pointerup', {
                        pointerId: 21, clientX, clientY, isPrimary: true,
                        button: 0, bubbles: true
                      }));
                      return OceanRescue.Travel.getSnapshot();
                    }"""
                )
                assert drag_end["dragging"] is False
                assert drag_end["pointerId"] is None
                assert drag_end["y"] == drag["y"], (
                    "Y must be preserved after the drag ends"
                )

                # Arrival: advance the authoritative distance, then let the
                # travel loop detect arrival and reach RESCUE_SITE_TRANSITION.
                arrival = page.evaluate(
                    """() => {
                      const T = OceanRescue.Travel;
                      const current = T.getSnapshot();
                      T.tapTo(current.y);
                      for (let i = 0; i < 1000; i += 1) {
                        T.step(50);
                      }
                      return { distance: T.getSnapshot().distance };
                    }"""
                )
                assert arrival["distance"] >= 6000, arrival
                _run_raf_frames(page, 4, 50)
                page.wait_for_function(
                    """() => {
                      const s = OceanRescue.State.getSnapshot();
                      return s.phase === 'RESCUE_SITE_TRANSITION' &&
                             s.transitionLocked === false;
                    }""",
                    timeout=10000,
                )
                arrival_state = page.evaluate(
                    """() => {
                      const S = OceanRescue.State;
                      const snap = S.getSnapshot();
                      return {
                        phase: snap.phase,
                        locked: snap.transitionLocked,
                        ready: snap.ready,
                        travelActive: OceanRescue.Travel.getSnapshot().active
                      };
                    }"""
                )
                assert arrival_state["phase"] == "RESCUE_SITE_TRANSITION"
                assert arrival_state["locked"] is False, (
                    "no transition lock may remain after arrival"
                )
                assert arrival_state["ready"] is True

                # Runtime quality: no page/console/network errors, single init.
                startup = page.evaluate(
                    """() => {
                      const root = document.getElementById('ocean-rescue-root');
                      return {
                        ready: root.getAttribute('data-ocean-rescue-ready'),
                        namespaces: Object.keys(OceanRescue).sort()
                      };
                    }"""
                )
                assert startup["ready"] == "true"
                assert startup["namespaces"].count("App") == 1
                assert page_errors == [], f"page errors: {page_errors}"
                assert console_errors == [], f"console errors: {console_errors}"
                assert request_failures == [], f"request failures: {request_failures}"
                external = [
                    r
                    for r in requests
                    if r["url"].startswith(("http://", "https://"))
                    and not r["url"].startswith(base_url)
                ]
                assert external == [], f"forbidden external requests: {external}"

                page.close()
                context.close()
            finally:
                browser.close()
    finally:
        server.stop()
