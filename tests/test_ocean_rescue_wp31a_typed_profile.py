"""WP-31A typed profile vertical slice contract.

The canonical Ocean Rescue profile model, persistence schema, storage
validation, and exported API are implemented by a strictly typed TypeScript
module (`domains/ocean-rescue/src/profile/profile.ts`) that is cut into the
canonical ESM graph through the compatibility adapter
(`domains/ocean-rescue/src/esm/profile.js`). The legacy `src/profile.js`
remains unchanged and is referenced only by the legacy rollback graph.

This suite verifies:

- static contract: typed module path, adapter cutover, tsconfig inclusion, no
  suppression or broad-`any` escapes;
- strict TypeScript diagnostics (`tsc --project tsconfig.json --noEmit`);
- the WP-31A behavioral matrix on the real typed implementation (fresh state,
  every valid animal, invalid/non-string IDs, selection, confirmation,
  persistence-failure semantics, hydration, malformed payloads, storage
  exception behavior, unusable storage, immutability);
- legacy-versus-typed parity: the unchanged `src/profile.js` and the typed
  module must produce identical return values, snapshots, serialized storage
  writes, removal attempts, thrown/not-thrown behavior, global API shape, and
  catalog order/values;
- the profile browser flow against the tracked standalone artifact:
  first visit, selection, stored payload, reload hydration, invalid-payload
  cleanup, and runtime request/console/page-error quality.

The behavioral matrix runs the real typed implementation through a test-only
Node harness that transpiles the module with the already-installed TypeScript
package (no new test dependency) before isolated VM execution.
"""

from __future__ import annotations

import json
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
PROFILE_TS = SRC_DIR / "profile" / "profile.ts"
ADAPTER = SRC_DIR / "esm" / "profile.js"
LEGACY_PROFILE_JS = SRC_DIR / "profile.js"
TSCONFIG = OCEAN_DIR / "tsconfig.json"

NODE_BIN: str = shutil.which("node") or ""
if not NODE_BIN:
    raise RuntimeError("Node executable not found on PATH")


# ── static contract ───────────────────────────────────────────────────


def test_typed_profile_module_exists() -> None:
    assert PROFILE_TS.is_file(), "src/profile/profile.ts missing"
    assert LEGACY_PROFILE_JS.is_file(), "rollback-only src/profile.js must remain"


def test_adapter_cuts_to_typed_module_and_not_legacy() -> None:
    text = ADAPTER.read_text(encoding="utf-8")
    assert 'import { Profile } from "../profile/profile";' in text
    assert "../profile.js" not in text, "adapter must not import the legacy module"
    assert 'throw new Error("OceanRescue.Profile was not registered")' in text
    assert "registered !== Profile" in text, "global ABI identity assertion missing"
    assert "export { Profile };" in text


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


def test_typed_module_has_no_suppression_or_broad_any() -> None:
    text = PROFILE_TS.read_text(encoding="utf-8")
    forbidden = (
        "@ts-nocheck",
        "@ts-ignore",
        "@ts-expect-error",
        "as any",
        ": any",
        "<any>",
        "as unknown as any",
    )
    for token in forbidden:
        assert token not in text, f"forbidden token in typed module: {token}"
    assert "export type ProfileAnimalId" in text
    assert "export interface ProfileApi" in text
    assert "export interface ProfileStorage" in text
    assert "export interface ProfileSnapshot" in text
    assert "export interface ProfileStoredPayloadV1" in text


def test_typed_module_keeps_exact_contract_literals() -> None:
    text = PROFILE_TS.read_text(encoding="utf-8")
    assert 'STORAGE_KEY = "aidengame.oceanRescue.profile"' in text
    assert "SCHEMA_VERSION = 1" in text
    assert 'PLAYER_NAME = "Aiden"' in text
    assert '"arctic-fox"' in text and '"beaver"' in text and '"red-panda"' in text


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


# ── behavioral matrix + legacy-versus-typed parity (Node harness) ──────

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
    const LEGACY_SOURCE = fs.readFileSync(path.join(SRC, "profile.js"), "utf8");
    const KEY = "aidengame.oceanRescue.profile";

    const emitDir = fs.mkdtempSync(path.join(os.tmpdir(), "wp31a-typed-profile-"));
    let TYPED_SOURCE;
    try {
      execSync(
        `node "${TSC}" --outDir "${emitDir}" --module commonjs ` +
          `--target es2022 --lib es2022,dom ` +
          `"${path.join(SRC, "profile", "profile.ts")}"`,
        { stdio: "pipe" }
      );
      TYPED_SOURCE = fs.readFileSync(
        path.join(emitDir, "profile", "profile.js"),
        "utf8"
      );
    } finally {
      fs.rmSync(emitDir, { recursive: true, force: true });
    }

    function plain(value) {
      return JSON.parse(JSON.stringify(value));
    }

    function makeStorage(opts) {
      opts = opts || {};
      const store = {};
      const trace = { getItem: [], setItem: [], removeItem: [] };
      if (opts.seed) Object.assign(store, opts.seed);
      const storage = {
        getItem(key) {
          trace.getItem.push(key);
          if (opts.getItemThrows) throw new Error("getItem failed");
          return Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null;
        },
        setItem(key, value) {
          trace.setItem.push({ key: key, value: String(value) });
          if (opts.setItemThrows) throw new Error("setItem failed");
          store[key] = String(value);
        },
        removeItem(key) {
          trace.removeItem.push(key);
          if (opts.removeItemThrows) throw new Error("removeItem failed");
          delete store[key];
        },
      };
      return { storage: storage, trace: trace };
    }

    function loadLegacy(storage) {
      const win = {};
      if (storage) win.localStorage = storage;
      const sandbox = { window: win };
      vm.createContext(sandbox);
      vm.runInContext(LEGACY_SOURCE, sandbox, { filename: "profile.js" });
      return { Profile: win.OceanRescue.Profile, win: win, storage: storage };
    }

    function loadTyped(storage) {
      const win = {};
      if (storage) win.localStorage = storage;
      const exportsObj = {};
      const sandbox = {
        window: win,
        exports: exportsObj,
        module: { exports: exportsObj },
        console: console,
      };
      vm.createContext(sandbox);
      vm.runInContext(TYPED_SOURCE, sandbox, { filename: "profile.ts" });
      return {
        Profile: win.OceanRescue.Profile,
        exported: exportsObj.Profile,
        win: win,
        storage: storage,
      };
    }

    const ACTIONS = {
      "select-arctic-fox": ["select", "arctic-fox"],
      "select-beaver": ["select", "beaver"],
      "select-red-panda": ["select", "red-panda"],
      "select-dolphin": ["select", "dolphin"],
      "select-42": ["select", 42],
      "select-null": ["select", null],
      confirm: ["confirm"],
      snapshot: ["snapshot"],
    };

    function buildStorage(spec) {
      if (spec.rawStorage) {
        return {
          storage: spec.rawStorage,
          trace: { getItem: [], setItem: [], removeItem: [] },
        };
      }
      if (spec.storage === undefined || spec.storage === null) {
        return { storage: null, trace: { getItem: [], setItem: [], removeItem: [] } };
      }
      return makeStorage(spec.storage);
    }

    function runScenario(kind, spec) {
      const built = buildStorage(spec);
      const loaded =
        kind === "typed" ? loadTyped(built.storage) : loadLegacy(built.storage);
      const P = loaded.Profile;
      const out = {
        apiKeys: Object.keys(P).sort(),
        apiFrozen: Object.isFrozen(P),
        catalogIds: P.Catalog.map(function (a) { return a.id; }),
        catalogNames: P.Catalog.map(function (a) { return a.name; }),
        catalogFrozen: Object.isFrozen(P.Catalog),
        catalogEntriesFrozen: P.Catalog.every(function (a) { return Object.isFrozen(a); }),
        snapshot0: plain(P.getSnapshot()),
        snapshotFrozen: Object.isFrozen(P.getSnapshot()),
        setItem: built.trace.setItem,
        removeItem: built.trace.removeItem,
        returns: [],
        thrown: null,
      };
      try {
        for (const action of spec.actions || []) {
          const step = ACTIONS[action];
          if (!step) throw new Error("unknown action " + action);
          if (step[0] === "select") {
            out.returns.push(["select", P.selectAnimal(step[1])]);
          } else if (step[0] === "confirm") {
            out.returns.push(["confirm", P.confirmSelection()]);
          } else if (step[0] === "snapshot") {
            out.returns.push(["snapshot", plain(P.getSnapshot())]);
          }
        }
      } catch (error) {
        out.thrown = String(error && error.message);
      }
      if (kind === "typed") {
        assert.strictEqual(
          loaded.exported,
          P,
          "typed ESM export must be the same frozen global API object"
        );
      }
      return out;
    }

    const scenarios = {
      fresh_no_storage: { storage: null, actions: [] },
      fresh_empty_storage: { storage: {}, actions: [] },
      valid_arctic_fox: { storage: {}, actions: ["select-arctic-fox", "snapshot"] },
      valid_beaver: { storage: {}, actions: ["select-beaver", "snapshot"] },
      valid_red_panda: { storage: {}, actions: ["select-red-panda", "snapshot"] },
      invalid_string_id: { storage: {}, actions: ["select-dolphin", "snapshot"] },
      non_string_id: { storage: {}, actions: ["select-42", "snapshot"] },
      null_id: { storage: {}, actions: ["select-null", "snapshot"] },
      select_and_confirm: { storage: {}, actions: ["select-beaver", "confirm", "snapshot"] },
      confirm_without_selection: { storage: {}, actions: ["confirm", "snapshot"] },
      second_confirm_after_complete: {
        storage: {},
        actions: ["select-beaver", "confirm", "confirm", "snapshot"],
      },
      hydrate_valid_payload: {
        storage: {
          seed: {
            [KEY]: JSON.stringify({
              schemaVersion: 1,
              playerName: "Aiden",
              animalId: "red-panda",
            }),
          },
        },
        actions: ["snapshot"],
      },
      malformed_json: { storage: { seed: { [KEY]: "{not json" } }, actions: ["snapshot"] },
      parsed_primitive: { storage: { seed: { [KEY]: "42" } }, actions: ["snapshot"] },
      parsed_array: { storage: { seed: { [KEY]: "[1, 2, 3]" } }, actions: ["snapshot"] },
      missing_schema_version: {
        storage: { seed: { [KEY]: JSON.stringify({ playerName: "Aiden", animalId: "beaver" }) } },
        actions: ["snapshot"],
      },
      wrong_schema_version: {
        storage: {
          seed: { [KEY]: JSON.stringify({ schemaVersion: 999, playerName: "Aiden", animalId: "beaver" }) },
        },
        actions: ["snapshot"],
      },
      wrong_player_name: {
        storage: {
          seed: { [KEY]: JSON.stringify({ schemaVersion: 1, playerName: "Bob", animalId: "beaver" }) },
        },
        actions: ["snapshot"],
      },
      unknown_animal_id: {
        storage: {
          seed: { [KEY]: JSON.stringify({ schemaVersion: 1, playerName: "Aiden", animalId: "dolphin" }) },
        },
        actions: ["snapshot"],
      },
      get_item_throws: { storage: { getItemThrows: true }, actions: ["snapshot"] },
      set_item_throws: {
        storage: { setItemThrows: true },
        actions: ["select-beaver", "confirm", "snapshot"],
      },
      remove_item_throws: {
        storage: { removeItemThrows: true, seed: { [KEY]: "{not json" } },
        actions: ["snapshot"],
      },
      non_function_storage: {
        rawStorage: { getItem: "nope", setItem: "nope", removeItem: "nope" },
        actions: ["snapshot"],
      },
    };

    for (const name of Object.keys(scenarios)) {
      const spec = scenarios[name];
      const legacyOut = runScenario("legacy", spec);
      const typedOut = runScenario("typed", spec);
      const legacyJson = JSON.stringify(legacyOut);
      const typedJson = JSON.stringify(typedOut);
      assert.strictEqual(
        typedJson,
        legacyJson,
        "typed/legacy parity mismatch for " + name + "\\nlegacy=" + legacyJson + "\\ntyped=" + typedJson
      );
    }

    function typed(name) {
      return runScenario("typed", scenarios[name]);
    }

    const emptySnapshot = {
      playerName: "Aiden",
      selectedAnimalId: null,
      chosenAnimalId: null,
      complete: false,
    };

    for (const name of ["fresh_no_storage", "fresh_empty_storage"]) {
      const s = typed(name);
      assert.deepStrictEqual(s.snapshot0, emptySnapshot, name);
      assert.strictEqual(s.setItem.length, 0, name + " must not write storage");
      assert.strictEqual(s.removeItem.length, 0, name + " must not remove storage");
    }

    for (const animal of ["arctic-fox", "beaver", "red-panda"]) {
      const s = runScenario("typed", {
        storage: {},
        actions: ["select-" + animal, "snapshot"],
      });
      assert.strictEqual(s.returns[0][1], true, animal + " selection must return true");
      assert.strictEqual(s.returns[1][1].selectedAnimalId, animal, animal);
    }

    {
      const s = typed("invalid_string_id");
      assert.strictEqual(s.returns[0][1], false);
      assert.strictEqual(s.returns[1][1].selectedAnimalId, null);
    }
    {
      const s = typed("non_string_id");
      assert.strictEqual(s.returns[0][1], false);
    }
    {
      const s = typed("null_id");
      assert.strictEqual(s.returns[0][1], false);
    }
    {
      const s = typed("select_and_confirm");
      assert.strictEqual(s.returns[0][1], true);
      assert.strictEqual(s.returns[1][1], true);
      assert.strictEqual(s.setItem.length, 1);
      assert.deepStrictEqual(s.setItem[0], {
        key: KEY,
        value: JSON.stringify({
          schemaVersion: 1,
          playerName: "Aiden",
          animalId: "beaver",
        }),
      });
      const snap = s.returns[2][1];
      assert.strictEqual(snap.chosenAnimalId, "beaver");
      assert.strictEqual(snap.complete, true);
    }
    {
      const s = typed("confirm_without_selection");
      assert.strictEqual(s.returns[0][1], false);
    }
    {
      const s = typed("second_confirm_after_complete");
      assert.strictEqual(s.returns[1][1], true);
      assert.strictEqual(s.returns[2][1], false);
    }
    {
      const s = typed("set_item_throws");
      assert.strictEqual(s.thrown, null);
      assert.strictEqual(s.returns[0][1], true);
      assert.strictEqual(s.returns[1][1], true, "confirm returns true on persist failure");
      const snap = s.returns[2][1];
      assert.strictEqual(snap.chosenAnimalId, "beaver");
      assert.strictEqual(snap.complete, false, "complete stays false on persist failure");
    }
    {
      const s = typed("hydrate_valid_payload");
      assert.strictEqual(s.snapshot0.chosenAnimalId, "red-panda");
      assert.strictEqual(s.snapshot0.complete, true);
      assert.strictEqual(s.snapshot0.selectedAnimalId, null);
    }
    for (const name of [
      "malformed_json",
      "parsed_primitive",
      "parsed_array",
      "missing_schema_version",
      "wrong_schema_version",
      "wrong_player_name",
      "unknown_animal_id",
    ]) {
      const s = typed(name);
      assert.strictEqual(s.thrown, null, name);
      assert.strictEqual(s.removeItem.some(function (k) { return k === KEY; }), true,
        name + " must attempt best-effort removal");
      assert.strictEqual(s.snapshot0.chosenAnimalId, null, name);
      assert.strictEqual(s.snapshot0.complete, false, name);
    }
    {
      const s = typed("get_item_throws");
      assert.strictEqual(s.thrown, null);
      assert.deepStrictEqual(s.snapshot0, emptySnapshot);
    }
    {
      const s = typed("remove_item_throws");
      assert.strictEqual(s.thrown, null);
      assert.deepStrictEqual(s.snapshot0, emptySnapshot);
    }
    {
      const s = typed("non_function_storage");
      assert.deepStrictEqual(s.snapshot0, emptySnapshot);
      assert.strictEqual(s.setItem.length, 0);
      assert.strictEqual(s.removeItem.length, 0);
    }

    {
      const built = makeStorage({});
      const loaded = loadTyped(built.storage);
      const P = loaded.Profile;
      assert.strictEqual(Object.isFrozen(P), true);
      assert.strictEqual(Object.isFrozen(P.Catalog), true);
      assert.ok(P.Catalog.every(function (a) { return Object.isFrozen(a); }));
      const snap = P.getSnapshot();
      assert.strictEqual(Object.isFrozen(snap), true);
      let pushed = false;
      try { P.Catalog.push({ id: "x", name: "X" }); pushed = true; } catch (e) { /* frozen */ }
      assert.strictEqual(pushed, false, "catalog must reject mutation");
      snap.complete = true;
      assert.strictEqual(snap.complete, false, "snapshot must reject mutation");
      P.extra = 1;
      assert.strictEqual(P.extra, undefined, "public API must reject mutation");
    }

    console.log("WP31A typed profile behavioral matrix + parity: PASS");
    """
)


def _run_behavior_harness() -> subprocess.CompletedProcess[str]:
    harness = _BEHAVIOR_HARNESS.replace("__REPO_ROOT__", repr(str(REPO_ROOT)))
    return subprocess.run(
        [NODE_BIN, "-e", harness],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_typed_profile_behavioral_matrix_and_parity() -> None:
    result = _run_behavior_harness()
    assert result.returncode == 0, (
        f"WP-31A behavior harness failed (exit {result.returncode}):\n"
        f"{result.stdout}\n{result.stderr}"
    )


# ── profile browser flow against the tracked artifact ──────────────────


def _profile_visible(page) -> bool:
    return bool(
        page.evaluate(
            """() => {
              const el = document.getElementById('ocean-rescue-profile-choice');
              return !!el && !el.hidden && getComputedStyle(el).display !== 'none';
            }"""
        )
    )


def _mission_visible(page) -> bool:
    return bool(
        page.evaluate(
            """() => {
              const el = document.getElementById('ocean-rescue-mission-select');
              return !!el && !el.hidden && getComputedStyle(el).display !== 'none';
            }"""
        )
    )


def _animal_order(page) -> list[str]:
    return page.evaluate(
        """() =>
          Array.from(
            document.querySelectorAll(
              '#ocean-rescue-profile-animal-list [data-profile-animal-id]'
            )
          ).map(b => b.getAttribute('data-profile-animal-id'))"""
    )


def _profile_snapshot(page) -> dict:
    return page.evaluate("() => OceanRescue.Profile.getSnapshot()")


def test_profile_browser_flow() -> None:
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
                # A. First visit: fresh storage, profile choice with the three
                # animals in canonical order, disabled continue, valid selection
                # enables continue, confirmation enters mission selection and
                # stores the exact versioned payload. A fresh Playwright context
                # is isolated, so storage starts empty without a clearing script.
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )
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
                assert _profile_visible(page) is True, "A: profile choice must appear"
                assert _mission_visible(page) is False, "A: mission select hidden"
                assert _animal_order(page) == ["arctic-fox", "beaver", "red-panda"], (
                    "A: animals must appear in canonical order"
                )
                assert page.is_disabled("#ocean-rescue-profile-continue") is True, (
                    "A: continue must start disabled"
                )
                page.click('[data-profile-animal-id="beaver"]')
                assert page.is_disabled("#ocean-rescue-profile-continue") is False, (
                    "A: valid selection must enable continue"
                )
                page.click("#ocean-rescue-profile-continue")
                page.wait_for_function(
                    """() => {
                      const el = document.getElementById('ocean-rescue-mission-select');
                      return !!el && getComputedStyle(el).display !== 'none';
                    }""",
                    timeout=10000,
                )
                assert _profile_visible(page) is False, "A: profile choice must hide"
                assert _mission_visible(page) is True, (
                    "A: mission selection must appear"
                )
                snap = _profile_snapshot(page)
                assert snap["chosenAnimalId"] == "beaver"
                assert snap["complete"] is True
                stored = page.evaluate(
                    "() => localStorage.getItem('aidengame.oceanRescue.profile')"
                )
                assert json.loads(stored) == {
                    "schemaVersion": 1,
                    "playerName": "Aiden",
                    "animalId": "beaver",
                }, "A: exact versioned payload must be stored"

                # B. Reload: valid stored profile hydrates, profile choice is
                # skipped, mission selection appears, chosen animal preserved.
                page.reload(wait_until="load")
                page.wait_for_selector(
                    "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=30000
                )
                assert _profile_visible(page) is False, (
                    "B: profile choice must be skipped"
                )
                assert _mission_visible(page) is True, (
                    "B: mission selection must appear"
                )
                snap = _profile_snapshot(page)
                assert snap["chosenAnimalId"] == "beaver", "B: chosen animal preserved"
                assert snap["complete"] is True
                page.close()
                context.close()

                # C. Invalid stored payload: no completion, best-effort cleanup,
                # profile choice appears.
                context2 = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )
                context2.add_init_script(
                    "window.localStorage.setItem("
                    "'aidengame.oceanRescue.profile', '{not json');"
                )
                page2 = context2.new_page()
                page2.on("pageerror", lambda e: page_errors.append(str(e)))
                page2.on(
                    "console",
                    lambda m: (
                        console_errors.append(m.text) if m.type == "error" else None
                    ),
                )
                page2.on("requestfailed", lambda r: request_failures.append(r.url))
                page2.on(
                    "request",
                    lambda r: requests.append({"url": r.url, "type": r.resource_type}),
                )
                page2.goto(f"{base_url}/ocean-rescue/index.html")
                page2.wait_for_selector(
                    "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=30000
                )
                assert _profile_visible(page2) is True, (
                    "C: invalid payload must fall back to profile choice"
                )
                snap = _profile_snapshot(page2)
                assert snap["complete"] is False
                assert snap["chosenAnimalId"] is None
                cleaned = page2.evaluate(
                    "() => localStorage.getItem('aidengame.oceanRescue.profile')"
                )
                assert cleaned is None, "C: invalid payload must be best-effort removed"

                # D. Runtime quality.
                assert page_errors == [], f"D: page errors: {page_errors}"
                assert console_errors == [], f"D: console errors: {console_errors}"
                assert request_failures == [], (
                    f"D: request failures: {request_failures}"
                )
                external = [
                    r
                    for r in requests
                    if r["url"].startswith(("http://", "https://"))
                    and not r["url"].startswith(base_url)
                ]
                assert external == [], f"D: forbidden external requests: {external}"

                page2.close()
                context2.close()
            finally:
                browser.close()
    finally:
        server.stop()
