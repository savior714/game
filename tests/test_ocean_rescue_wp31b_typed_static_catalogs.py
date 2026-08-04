"""WP-31B typed static catalog group contract.

The Ocean Rescue mission catalog, GUP catalog, and static launch content move
from untyped rollback-oriented JavaScript modules to strictly typed canonical
TypeScript modules while preserving all runtime values, ordering, immutability,
mutable controller behavior, browser behavior, deterministic packaging, and the
byte-identical legacy rollback sources.

Ownership after WP-31B:

- mission static catalog: `src/missions/catalog.ts` (typed canonical);
  `src/missions.js` keeps the unchanged mutable progression controller in the
  canonical graph;
- GUP static catalog: `src/gups/catalog.ts` (typed canonical);
  `src/gups.js` keeps the unchanged mutable GUP controller in the canonical
  graph;
- launch static API: `src/launch/launch.ts` (typed canonical); the canonical
  graph no longer executes `src/launch.js`, which is retained byte-for-byte as a
  rollback-only source.

This suite verifies:

- static ownership: typed modules exist and are cut into the canonical graph,
  mission/GUP adapters retain only their required legacy controller imports,
  the launch adapter no longer imports legacy launch, no suppressions, no
  strictness weakening, no WP-32-style shared type module;
- runtime identity and immutability on the real compiled/transformed modules:
  global API === ESM export, global Catalog === typed catalog export, frozen
  API/array/entries, mutation rejection, exact enumerable API shape;
- exact catalog parity between typed canonical data and unchanged legacy
  runtime data;
- mission controller preservation (fresh progression, unlock, selection,
  completion, New badge, persistence, hydration, malformed-payload cleanup,
  storage failure isolation);
- GUP controller preservation (initial/last IDs, preparation, valid/invalid
  selection, confirmation, snapshots);
- launch behavior (every entry, exact timing constants, exact lookup
  semantics);
- legacy byte identity (SHA-256 before/after for the three legacy files);
- the focused browser flow (deterministic storage -> mission cards -> GUP
  cards -> launch briefing/goal/timing) with clean page/console/network
  quality;
- deterministic production bundle + standalone HTML, tracked-artifact match,
  canonical module membership (typed modules in, rollback launch.js/profile.js
  out), and legacy rollback artifact byte identity.

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

BUNDLE_FILE = "ocean-rescue-app.js"
METADATA_FILE = "production-bundle-metadata.json"

PROG_KEY = "aidengame.oceanRescue.progression"

# Pre-WP-21 canonical legacy artifact baseline; the rollback build reads only
# unchanged legacy sources and must stay byte-identical. Rebased by UX-01
# because the rollback artifact embeds the shared template/styles, which that
# work legitimately updated; the legacy sources and manifest are unchanged.
LEGACY_ROLLBACK_BASELINE_SHA = (
    "9562d991a64852da59531e830742d6936c759eb8792179a1ce993a8cd49a2729"
)

LEGACY_SOURCE_SHA256 = {
    "missions.js": ("f636fed0c9d0bb0b6746bcb7c7aaea19c6f9e81466096d8324aa514b24aa4d33"),
    "gups.js": ("bf10d685522bbb16d2886d2f8c73ee807295688f4f36a347f037db725172e219"),
    "launch.js": ("1e466a6a611545874e4099d4c55417a17f36a729cb0b2e841f64d87c5491cfce"),
}

TYPED_MODULE_PATHS = {
    "missions": "missions/catalog.ts",
    "gups": "gups/catalog.ts",
    "launch": "launch/launch.ts",
}
ADAPTER_PATHS = {
    "missions": "esm/missions.js",
    "gups": "esm/gups.js",
    "launch": "esm/launch.js",
}

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


def test_typed_static_modules_exist() -> None:
    for label, rel in TYPED_MODULE_PATHS.items():
        assert (SRC_DIR / rel).is_file(), f"{label} typed module missing: {rel}"
    for label, rel in ADAPTER_PATHS.items():
        assert (ESM_DIR / rel.rsplit("/", 1)[-1]).is_file(), (
            f"{label} adapter missing: {rel}"
        )
    for name in ("missions.js", "gups.js", "launch.js"):
        assert (SRC_DIR / name).is_file(), f"legacy rollback source missing: {name}"


def test_adapters_import_typed_modules_and_required_legacy_only() -> None:
    missions = (ESM_DIR / "missions.js").read_text(encoding="utf-8")
    assert 'import { Catalog } from "../missions/catalog";' in missions
    assert 'import "../missions.js";' in missions
    assert "getSnapshot" in missions and "completeMission" in missions
    assert "markMissionViewed" in missions
    assert "OceanRescue.Missions = Missions;" in missions
    assert "export { Missions };" in missions and "export { Catalog };" in missions

    gups = (ESM_DIR / "gups.js").read_text(encoding="utf-8")
    assert 'import { Catalog } from "../gups/catalog";' in gups
    assert 'import "../gups.js";' in gups
    assert "prepareSelection" in gups and "confirmSelection" in gups
    assert "OceanRescue.Gups = Gups;" in gups
    assert "export { Gups };" in gups and "export { Catalog };" in gups

    launch = (ESM_DIR / "launch.js").read_text(encoding="utf-8")
    assert 'import { Launch } from "../launch/launch";' in launch
    assert "../launch.js" not in launch, (
        "launch adapter must not import the legacy launch module"
    )
    assert "registered !== Launch" in launch


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
    paths = [SRC_DIR / rel for rel in TYPED_MODULE_PATHS.values()]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"forbidden token in {path.name}: {token}"
    for adapter in ADAPTER_PATHS.values():
        text = (ESM_DIR / adapter.rsplit("/", 1)[-1]).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"forbidden token in {adapter}: {token}"


def test_tsconfig_strictness_not_weakened() -> None:
    cfg = json.loads(TSCONFIG.read_text(encoding="utf-8"))
    compiler = cfg.get("compilerOptions", {})
    assert compiler.get("strict") is True
    assert compiler.get("noEmit") is True
    assert compiler.get("checkJs") is False
    assert compiler.get("allowJs") is True
    assert compiler.get("module") == "ESNext"
    assert compiler.get("moduleResolution") == "Bundler"
    assert "src/**/*.ts" in cfg.get("include", [])
    assert (
        "skipLibCheck" not in cfg.get("compilerOptions", {})
        or cfg.get("compilerOptions", {}).get("skipLibCheck") is True
    )


def test_no_shared_cross_domain_type_module_introduced() -> None:
    forbidden_shared = {
        SRC_DIR / "types.ts",
        SRC_DIR / "shared-types.ts",
        SRC_DIR / "boundary-types.ts",
        SRC_DIR / "types" / "index.ts",
    }
    for path in forbidden_shared:
        assert not path.exists(), f"WP-32-style shared type module present: {path}"
    for rel in TYPED_MODULE_PATHS.values():
        parts = Path(rel).parts
        assert parts[0] in {"missions", "gups", "launch"}, (
            f"typed module must be domain-local, got {rel}"
        )


def test_typed_module_exports_typed_types() -> None:
    missions = (SRC_DIR / "missions/catalog.ts").read_text(encoding="utf-8")
    assert "export type MissionId" in missions
    assert "export interface MissionCatalogEntry" in missions
    assert "export type MissionCatalog" in missions
    assert "export const Catalog" in missions
    gups = (SRC_DIR / "gups/catalog.ts").read_text(encoding="utf-8")
    assert "export type GupId" in gups
    assert "export interface GupCatalogEntry" in gups
    assert "export type GupCatalog" in gups
    assert "export const Catalog" in gups
    launch = (SRC_DIR / "launch/launch.ts").read_text(encoding="utf-8")
    assert "export type LaunchMissionId" in launch
    assert "export interface LaunchCatalogEntry" in launch
    assert "export interface LaunchApi" in launch
    assert "export const DurationMs" in launch
    assert "export const GoalDurationMs" in launch
    assert "export function getMissionContent" in launch
    assert "export const Launch" in launch


# ── legacy byte identity ─────────────────────────────────────────────────


def test_legacy_sources_remain_byte_identical() -> None:
    for name, expected in LEGACY_SOURCE_SHA256.items():
        actual = _sha256_path(SRC_DIR / name)
        assert actual == expected, (
            f"legacy {name} changed (WP-31B must not modify it): {actual}"
        )


# ── strict typecheck ─────────────────────────────────────────────────────


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


# ── behavioral matrix + parity (Node harness) ────────────────────────────

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

    const LEGACY_MISSIONS = fs.readFileSync(path.join(SRC, "missions.js"), "utf8");
    const LEGACY_GUPS = fs.readFileSync(path.join(SRC, "gups.js"), "utf8");
    const LEGACY_LAUNCH = fs.readFileSync(path.join(SRC, "launch.js"), "utf8");

    const TMP = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "wp31b-static-catalogs-")));
    try {
      execSync(
        `node "${TSC}" --ignoreConfig --module commonjs --target es2022 ` +
          `--lib es2022,dom --outDir "${TMP}" ` +
          `"${path.join(SRC, "missions", "catalog.ts")}" ` +
          `"${path.join(SRC, "gups", "catalog.ts")}" ` +
          `"${path.join(SRC, "launch", "launch.ts")}"`,
        { stdio: "pipe" }
      );
      execSync(
        `node "${TSC}" --ignoreConfig --module commonjs --target es2022 ` +
          `--lib es2022,dom --allowJs --checkJs false --outDir "${TMP}" ` +
          `"${path.join(SRC, "esm", "missions.js")}" ` +
          `"${path.join(SRC, "esm", "gups.js")}" ` +
          `"${path.join(SRC, "esm", "launch.js")}"`,
        { stdio: "pipe" }
      );
      fs.copyFileSync(path.join(SRC, "missions.js"), path.join(TMP, "missions.js"));
      fs.copyFileSync(path.join(SRC, "gups.js"), path.join(TMP, "gups.js"));
      fs.copyFileSync(path.join(SRC, "launch.js"), path.join(TMP, "launch.js"));
    } catch (error) {
      fs.rmSync(TMP, { recursive: true, force: true });
      throw error;
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

    function resetRequireCache() {
      for (const key of Object.keys(require.cache)) {
        if (key.startsWith(TMP + path.sep)) {
          delete require.cache[key];
        }
      }
    }

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

    function loadCanonical(kind, storage) {
      resetRequireCache();
      globalThis.window = { localStorage: storage };
      if (kind === "missions") {
        const adapter = require(path.join(TMP, "esm", "missions.js"));
        return {
          api: adapter.Missions,
          typedCatalog: adapter.Catalog,
          win: globalThis.window,
        };
      }
      if (kind === "gups") {
        const adapter = require(path.join(TMP, "esm", "gups.js"));
        return {
          api: adapter.Gups,
          typedCatalog: adapter.Catalog,
          win: globalThis.window,
        };
      }
      if (kind === "launch") {
        const adapter = require(path.join(TMP, "esm", "launch.js"));
        const typed = require(path.join(TMP, "launch", "launch.js"));
        return {
          api: adapter.Launch,
          typedCatalog: typed.Catalog,
          typed: typed,
          win: globalThis.window,
        };
      }
      throw new Error("unknown canonical kind " + kind);
    }

    function loadLegacy(kind, storage) {
      const win = {};
      if (storage) win.localStorage = storage;
      const sandbox = { window: win };
      vm.createContext(sandbox);
      if (kind === "missions") {
        vm.runInContext(LEGACY_MISSIONS, sandbox, { filename: "missions.js" });
        return win.OceanRescue.Missions;
      }
      if (kind === "gups") {
        vm.runInContext(LEGACY_GUPS, sandbox, { filename: "gups.js" });
        return win.OceanRescue.Gups;
      }
      if (kind === "launch") {
        vm.runInContext(LEGACY_LAUNCH, sandbox, { filename: "launch.js" });
        return win.OceanRescue.Launch;
      }
      throw new Error("unknown legacy kind " + kind);
    }

    // ── mission controller ────────────────────────────────────────────

    const MISSION_ACTIONS = {
      "select-sea-turtle": ["select", "sea-turtle"],
      "select-crab": ["select", "crab"],
      "select-young-whale": ["select", "young-whale"],
      "select-unknown": ["select", "unknown"],
      "select-42": ["select", 42],
      "select-null": ["select", null],
      "complete-sea-turtle": ["complete", "sea-turtle"],
      "complete-crab": ["complete", "crab"],
      "complete-young-whale": ["complete", "young-whale"],
      "complete-unknown": ["complete", "unknown"],
      "mark-viewed-crab": ["markViewed", "crab"],
      "mark-viewed-young-whale": ["markViewed", "young-whale"],
      "mark-viewed-unknown": ["markViewed", "unknown"],
      snapshot: ["snapshot"],
    };

    function runMissionScenario(kind, spec) {
      const built = buildStorage(spec);
      const loaded =
        kind === "canonical"
          ? loadCanonical("missions", built.storage)
          : { api: loadLegacy("missions", built.storage) };
      const M = loaded.api;
      const out = {
        apiKeys: Object.keys(M).sort(),
        apiFrozen: Object.isFrozen(M),
        catalogIds: M.Catalog.map(function (e) { return e.id; }),
        catalogOrders: M.Catalog.map(function (e) { return e.order; }),
        catalogTitles: M.Catalog.map(function (e) { return e.title; }),
        catalogCompanions: M.Catalog.map(function (e) { return e.companion; }),
        catalogSummaries: M.Catalog.map(function (e) { return e.summary; }),
        catalogFrozen: Object.isFrozen(M.Catalog),
        catalogEntriesFrozen: M.Catalog.every(function (e) { return Object.isFrozen(e); }),
        snapshot0: plain(M.getSnapshot()),
        setItem: built.trace.setItem,
        removeItem: built.trace.removeItem,
        returns: [],
        thrown: null,
      };
      try {
        for (const action of spec.actions || []) {
          const step = MISSION_ACTIONS[action];
          if (!step) throw new Error("unknown mission action " + action);
          if (step[0] === "select") {
            out.returns.push(["select", M.selectMission(step[1])]);
          } else if (step[0] === "complete") {
            out.returns.push(["complete", plain(M.completeMission(step[1]))]);
          } else if (step[0] === "markViewed") {
            out.returns.push(["markViewed", M.markMissionViewed(step[1])]);
          } else if (step[0] === "snapshot") {
            out.returns.push(["snapshot", plain(M.getSnapshot())]);
          }
        }
      } catch (error) {
        out.thrown = String(error && error.message);
      }
      if (kind === "canonical") {
        assert.strictEqual(
          loaded.api,
          globalThis.window.OceanRescue.Missions,
          "canonical Missions export must be the same global facade object"
        );
        assert.strictEqual(
          loaded.api.Catalog,
          loaded.typedCatalog,
          "canonical Missions.Catalog must be the typed mission catalog export"
        );
      }
      return out;
    }

    const MISSION_SCENARIOS = {
      fresh_no_storage: { storage: null, actions: [] },
      fresh_empty_storage: { storage: {}, actions: [] },
      valid_select: { storage: {}, actions: ["select-sea-turtle", "snapshot"] },
      locked_select: { storage: {}, actions: ["select-crab", "snapshot"] },
      invalid_string: { storage: {}, actions: ["select-unknown", "snapshot"] },
      non_string_select: { storage: {}, actions: ["select-42", "snapshot"] },
      null_select: { storage: {}, actions: ["select-null", "snapshot"] },
      first_completion_unlock: {
        storage: {},
        actions: ["complete-sea-turtle", "snapshot"],
      },
      complete_unknown: { storage: {}, actions: ["complete-unknown", "snapshot"] },
      complete_locked: { storage: {}, actions: ["complete-crab", "snapshot"] },
      full_progression: {
        storage: {},
        actions: [
          "complete-sea-turtle",
          "complete-crab",
          "complete-young-whale",
          "snapshot",
        ],
      },
      repeat_completion: {
        storage: {},
        actions: ["complete-sea-turtle", "complete-sea-turtle", "snapshot"],
      },
      new_badge_removal: {
        storage: {},
        actions: ["complete-sea-turtle", "mark-viewed-crab", "snapshot"],
      },
      mark_viewed_unknown: {
        storage: {},
        actions: ["mark-viewed-unknown", "snapshot"],
      },
      hydrate_valid_payload: {
        storage: {
          seed: {
            [KEY]: JSON.stringify({
              schemaVersion: 1,
              completedMissionIds: ["sea-turtle"],
              newMissionIds: ["crab"],
            }),
          },
        },
        actions: ["snapshot"],
      },
      malformed_json: { storage: { seed: { [KEY]: "{not json" } }, actions: ["snapshot"] },
      parsed_primitive: { storage: { seed: { [KEY]: "42" } }, actions: ["snapshot"] },
      parsed_array: { storage: { seed: { [KEY]: "[1,2,3]" } }, actions: ["snapshot"] },
      wrong_schema_version: {
        storage: {
          seed: {
            [KEY]: JSON.stringify({
              schemaVersion: 999,
              completedMissionIds: ["sea-turtle"],
              newMissionIds: [],
            }),
          },
        },
        actions: ["snapshot"],
      },
      unknown_mission_id: {
        storage: {
          seed: {
            [KEY]: JSON.stringify({
              schemaVersion: 1,
              completedMissionIds: ["dolphin"],
              newMissionIds: [],
            }),
          },
        },
        actions: ["snapshot"],
      },
      out_of_order_completion: {
        storage: {
          seed: {
            [KEY]: JSON.stringify({
              schemaVersion: 1,
              completedMissionIds: ["crab"],
              newMissionIds: [],
            }),
          },
        },
        actions: ["snapshot"],
      },
      get_item_throws: { storage: { getItemThrows: true }, actions: ["snapshot"] },
      set_item_throws: {
        storage: { setItemThrows: true },
        actions: ["complete-sea-turtle", "snapshot"],
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

    for (const name of Object.keys(MISSION_SCENARIOS)) {
      const spec = MISSION_SCENARIOS[name];
      const legacyOut = runMissionScenario("legacy", spec);
      const canonicalOut = runMissionScenario("canonical", spec);
      assert.strictEqual(
        JSON.stringify(canonicalOut),
        JSON.stringify(legacyOut),
        "mission legacy/canonical parity mismatch for " + name +
          "\\nlegacy=" + JSON.stringify(legacyOut) +
          "\\ncanonical=" + JSON.stringify(canonicalOut)
      );
    }

    function canonicalMission(name) {
      return runMissionScenario("canonical", MISSION_SCENARIOS[name]);
    }

    {
      const s = canonicalMission("fresh_empty_storage");
      assert.deepStrictEqual(s.snapshot0, {
        selectedMissionId: null,
        unlockedMissionIds: ["sea-turtle"],
        completedMissionIds: [],
        newMissionIds: [],
      });
      assert.strictEqual(s.setItem.length, 0);
      assert.strictEqual(s.removeItem.length, 0);
    }
    {
      const s = canonicalMission("valid_select");
      assert.strictEqual(s.returns[0][1], true);
      assert.strictEqual(s.returns[1][1].selectedMissionId, "sea-turtle");
    }
    {
      const s = canonicalMission("locked_select");
      assert.strictEqual(s.returns[0][1], false);
    }
    {
      const s = canonicalMission("first_completion_unlock");
      assert.deepStrictEqual(s.returns[0][1], {
        changed: true,
        newlyUnlockedMissionId: "crab",
      });
      const snap = s.returns[1][1];
      assert.deepStrictEqual(snap.unlockedMissionIds, ["sea-turtle", "crab"]);
      assert.deepStrictEqual(snap.completedMissionIds, ["sea-turtle"]);
      assert.deepStrictEqual(snap.newMissionIds, ["crab"]);
      assert.strictEqual(s.setItem.length, 1);
    }
    {
      const s = canonicalMission("full_progression");
      assert.deepStrictEqual(s.snapshot0.unlockedMissionIds, ["sea-turtle"]);
      assert.deepStrictEqual(s.returns[0][1].newlyUnlockedMissionId, "crab");
      assert.deepStrictEqual(s.returns[1][1].newlyUnlockedMissionId, "young-whale");
      assert.deepStrictEqual(s.returns[2][1], {
        changed: true,
        newlyUnlockedMissionId: null,
      });
      const snap = s.returns[3][1];
      assert.deepStrictEqual(snap.completedMissionIds, [
        "sea-turtle",
        "crab",
        "young-whale",
      ]);
    }
    {
      const s = canonicalMission("new_badge_removal");
      assert.strictEqual(s.returns[1][1], true);
      assert.deepStrictEqual(s.returns[2][1].newMissionIds, []);
      assert.strictEqual(s.returns[1][1], true);
    }
    {
      const s = canonicalMission("hydrate_valid_payload");
      assert.deepStrictEqual(s.snapshot0.unlockedMissionIds, [
        "sea-turtle",
        "crab",
      ]);
      assert.deepStrictEqual(s.snapshot0.completedMissionIds, ["sea-turtle"]);
      assert.deepStrictEqual(s.snapshot0.newMissionIds, ["crab"]);
    }
    for (const name of [
      "malformed_json",
      "parsed_primitive",
      "parsed_array",
      "wrong_schema_version",
      "unknown_mission_id",
      "out_of_order_completion",
    ]) {
      const s = canonicalMission(name);
      assert.strictEqual(s.thrown, null, name);
      assert.strictEqual(
        s.removeItem.some(function (k) { return k === KEY; }),
        true,
        name + " must attempt best-effort removal"
      );
      assert.deepStrictEqual(s.snapshot0.unlockedMissionIds, ["sea-turtle"], name);
      assert.deepStrictEqual(s.snapshot0.completedMissionIds, [], name);
    }
    {
      const s = canonicalMission("get_item_throws");
      assert.strictEqual(s.thrown, null);
    }
    {
      const s = canonicalMission("set_item_throws");
      assert.strictEqual(s.thrown, null);
      assert.deepStrictEqual(s.returns[0][1], {
        changed: true,
        newlyUnlockedMissionId: "crab",
      });
      assert.deepStrictEqual(s.returns[1][1].completedMissionIds, ["sea-turtle"]);
      assert.deepStrictEqual(s.returns[1][1].unlockedMissionIds, [
        "sea-turtle",
        "crab",
      ]);
    }
    {
      const s = canonicalMission("remove_item_throws");
      assert.strictEqual(s.thrown, null);
    }
    {
      const s = canonicalMission("non_function_storage");
      assert.strictEqual(s.setItem.length, 0);
      assert.strictEqual(s.removeItem.length, 0);
    }

    // ── GUP controller ────────────────────────────────────────────────

    const GUP_ACTIONS = {
      "select-c": ["select", "gup-c"],
      "select-i": ["select", "gup-i"],
      "select-x": ["select", "gup-x"],
      "select-unknown": ["select", "unknown"],
      "select-42": ["select", 42],
      "select-null": ["select", null],
      prepare: ["prepare"],
      confirm: ["confirm"],
      snapshot: ["snapshot"],
    };

    function runGupScenario(kind, spec) {
      const built = buildStorage(spec);
      const loaded =
        kind === "canonical"
          ? loadCanonical("gups", built.storage)
          : { api: loadLegacy("gups", built.storage) };
      const G = loaded.api;
      const out = {
        apiKeys: Object.keys(G).sort(),
        apiFrozen: Object.isFrozen(G),
        catalogIds: G.Catalog.map(function (e) { return e.id; }),
        catalogNames: G.Catalog.map(function (e) { return e.name; }),
        catalogDescriptions: G.Catalog.map(function (e) { return e.description; }),
        catalogFrozen: Object.isFrozen(G.Catalog),
        catalogEntriesFrozen: G.Catalog.every(function (e) { return Object.isFrozen(e); }),
        snapshot0: plain(G.getSnapshot()),
        returns: [],
        thrown: null,
      };
      try {
        for (const action of spec.actions || []) {
          const step = GUP_ACTIONS[action];
          if (!step) throw new Error("unknown gup action " + action);
          if (step[0] === "select") {
            out.returns.push(["select", G.selectGup(step[1])]);
          } else if (step[0] === "prepare") {
            out.returns.push(["prepare", G.prepareSelection()]);
          } else if (step[0] === "confirm") {
            out.returns.push(["confirm", G.confirmSelection()]);
          } else if (step[0] === "snapshot") {
            out.returns.push(["snapshot", plain(G.getSnapshot())]);
          }
        }
      } catch (error) {
        out.thrown = String(error && error.message);
      }
      if (kind === "canonical") {
        assert.strictEqual(
          loaded.api,
          globalThis.window.OceanRescue.Gups,
          "canonical Gups export must be the same global facade object"
        );
        assert.strictEqual(
          loaded.api.Catalog,
          loaded.typedCatalog,
          "canonical Gups.Catalog must be the typed GUP catalog export"
        );
      }
      return out;
    }

    const GUP_SCENARIOS = {
      fresh: { storage: {}, actions: [] },
      select_i: { storage: {}, actions: ["select-i", "snapshot"] },
      select_i_twice: { storage: {}, actions: ["select-i", "select-i", "snapshot"] },
      prepare_after_select: {
        storage: {},
        actions: ["select-i", "prepare", "snapshot"],
      },
      select_and_confirm: {
        storage: {},
        actions: ["select-x", "confirm", "snapshot"],
      },
      prepare_after_confirm: {
        storage: {},
        actions: ["select-x", "confirm", "prepare", "snapshot"],
      },
      invalid_string: { storage: {}, actions: ["select-unknown", "snapshot"] },
      non_string_select: { storage: {}, actions: ["select-42", "snapshot"] },
      null_select: { storage: {}, actions: ["select-null", "snapshot"] },
      confirm_without_select: { storage: {}, actions: ["confirm", "snapshot"] },
      repeated_operations: {
        storage: {},
        actions: ["select-i", "select-x", "select-i", "snapshot"],
      },
    };

    for (const name of Object.keys(GUP_SCENARIOS)) {
      const spec = GUP_SCENARIOS[name];
      const legacyOut = runGupScenario("legacy", spec);
      const canonicalOut = runGupScenario("canonical", spec);
      assert.strictEqual(
        JSON.stringify(canonicalOut),
        JSON.stringify(legacyOut),
        "gup legacy/canonical parity mismatch for " + name +
          "\\nlegacy=" + JSON.stringify(legacyOut) +
          "\\ncanonical=" + JSON.stringify(canonicalOut)
      );
    }

    function canonicalGup(name) {
      return runGupScenario("canonical", GUP_SCENARIOS[name]);
    }

    {
      const s = canonicalGup("fresh");
      assert.deepStrictEqual(s.snapshot0, { selectedGupId: "gup-c", lastGupId: "gup-c" });
    }
    {
      const s = canonicalGup("select_and_confirm");
      assert.strictEqual(s.returns[0][1], true);
      assert.strictEqual(s.returns[1][1], "gup-x");
      assert.deepStrictEqual(s.returns[2][1], { selectedGupId: "gup-x", lastGupId: "gup-x" });
    }
    {
      const s = canonicalGup("prepare_after_select");
      assert.strictEqual(s.returns[0][1], true);
      assert.strictEqual(s.returns[1][1], "gup-c");
      assert.strictEqual(s.returns[2][1].selectedGupId, "gup-c");
      assert.strictEqual(s.returns[2][1].lastGupId, "gup-c");
    }
    {
      const s = canonicalGup("invalid_string");
      assert.strictEqual(s.returns[0][1], false);
      assert.deepStrictEqual(s.returns[1][1], { selectedGupId: "gup-c", lastGupId: "gup-c" });
    }
    {
      const s = canonicalGup("confirm_without_select");
      assert.strictEqual(s.returns[0][1], "gup-c");
    }

    // ── launch static behavior ─────────────────────────────────────────

    const launchCanonical = loadCanonical("launch", null);
    const L = launchCanonical.api;
    const legacyLaunch = loadLegacy("launch", null);

    assert.strictEqual(
      L,
      globalThis.window.OceanRescue.Launch,
      "canonical Launch export must be the same global frozen API object"
    );
    assert.strictEqual(
      L.Catalog,
      launchCanonical.typedCatalog,
      "canonical Launch.Catalog must be the typed launch catalog export"
    );
    assert.strictEqual(L, launchCanonical.typed.Launch);
    assert.strictEqual(Object.isFrozen(L), true);
    assert.strictEqual(Object.isFrozen(L.Catalog), true);
    assert.ok(L.Catalog.every(function (e) { return Object.isFrozen(e); }));
    assert.strictEqual(L.DurationMs, 6000);
    assert.strictEqual(L.GoalDurationMs, 3000);
    assert.strictEqual(launchCanonical.typed.DurationMs, 6000);
    assert.strictEqual(launchCanonical.typed.GoalDurationMs, 3000);

    const LAUNCH_EXPECTED = [
      {
        missionId: "sea-turtle",
        briefing: "A sea turtle is trapped in a net. Let’s find it and cut the ropes!",
        goal: "Rescue the sea turtle!",
      },
      {
        missionId: "crab",
        briefing: "A crab is trapped under some rocks. Let’s move them with the grabber!",
        goal: "Help the trapped crab!",
      },
      {
        missionId: "young-whale",
        briefing: "A young whale’s path is blocked. Let’s tow the debris away!",
        goal: "Clear a path for the young whale!",
      },
    ];

    assert.deepStrictEqual(
      L.Catalog.map(function (e) { return plain(e); }),
      LAUNCH_EXPECTED
    );
    assert.deepStrictEqual(
      plain(legacyLaunch.Catalog.map(function (e) { return plain(e); })),
      LAUNCH_EXPECTED
    );

    for (let i = 0; i < L.Catalog.length; i += 1) {
      assert.strictEqual(L.getMissionContent(LAUNCH_EXPECTED[i].missionId), L.Catalog[i]);
      assert.deepStrictEqual(
        plain(legacyLaunch.getMissionContent(LAUNCH_EXPECTED[i].missionId)),
        plain(L.Catalog[i])
      );
    }

    const INVALID_INPUTS = ["unknown", "", undefined, null, 42, {}, [], NaN, true];
    for (const input of INVALID_INPUTS) {
      assert.strictEqual(L.getMissionContent(input), null, "typed lookup for " + String(input));
      assert.strictEqual(legacyLaunch.getMissionContent(input), null, "legacy lookup for " + String(input));
    }

    // ── runtime immutability ───────────────────────────────────────────

    {
      const loaded = loadCanonical("missions", {});
      const M = loaded.api;
      assert.strictEqual(Object.isFrozen(M), true);
      assert.strictEqual(Object.isFrozen(M.Catalog), true);
      assert.ok(M.Catalog.every(function (e) { return Object.isFrozen(e); }));
      let pushed = false;
      try { M.Catalog.push({ id: "x", order: 4, title: "X", companion: "Y", summary: "Z" }); pushed = true; } catch (e) { /* frozen */ }
      assert.strictEqual(pushed, false, "mission catalog must reject mutation");
      assert.strictEqual(M.Catalog.length, 3);
      M.Catalog[0].title = "HACKED";
      assert.strictEqual(M.Catalog[0].title, "Sea Turtle Rescue");
      M.extra = 1;
      assert.strictEqual(M.extra, undefined, "mission API must reject mutation");
      assert.deepStrictEqual(
        Object.keys(M).sort(),
        ["Catalog", "completeMission", "getSnapshot", "isUnlocked", "markMissionViewed", "selectMission"]
      );
    }
    {
      const loaded = loadCanonical("gups", {});
      const G = loaded.api;
      assert.strictEqual(Object.isFrozen(G), true);
      assert.strictEqual(Object.isFrozen(G.Catalog), true);
      assert.ok(G.Catalog.every(function (e) { return Object.isFrozen(e); }));
      let pushed = false;
      try { G.Catalog.push({ id: "gup-h", name: "GUP-H", description: "H" }); pushed = true; } catch (e) { /* frozen */ }
      assert.strictEqual(pushed, false, "gup catalog must reject mutation");
      assert.strictEqual(G.Catalog.length, 3);
      G.Catalog[0].name = "HACKED";
      assert.strictEqual(G.Catalog[0].name, "GUP-C");
      G.extra = 1;
      assert.strictEqual(G.extra, undefined, "gup API must reject mutation");
      assert.deepStrictEqual(
        Object.keys(G).sort(),
        ["Catalog", "confirmSelection", "getSnapshot", "isValidGup", "prepareSelection", "selectGup"]
      );
    }
    {
      const loaded = loadCanonical("launch", null);
      const L2 = loaded.api;
      let pushed = false;
      try { L2.Catalog.push({ missionId: "dolphin", briefing: "X", goal: "Y" }); pushed = true; } catch (e) { /* frozen */ }
      assert.strictEqual(pushed, false, "launch catalog must reject mutation");
      assert.strictEqual(L2.Catalog.length, 3);
      L2.DurationMs = 9999;
      assert.strictEqual(L2.DurationMs, 6000);
      L2.extra = 1;
      assert.strictEqual(L2.extra, undefined, "launch API must reject mutation");
      assert.deepStrictEqual(
        Object.keys(L2).sort(),
        ["Catalog", "DurationMs", "GoalDurationMs", "getMissionContent"]
      );
    }

    console.log("WP31B typed static catalog matrix + parity: PASS");
    """
).replace("KEY", '"aidengame.oceanRescue.progression"')


def _run_behavior_harness() -> subprocess.CompletedProcess[str]:
    harness = _BEHAVIOR_HARNESS.replace("__REPO_ROOT__", repr(str(REPO_ROOT)))
    return subprocess.run(
        [NODE_BIN, "-e", harness],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_typed_static_catalog_behavioral_matrix_and_parity() -> None:
    result = _run_behavior_harness()
    assert result.returncode == 0, (
        f"WP-31B behavior harness failed (exit {result.returncode}):\n"
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
    for typed in TYPED_MODULE_PATHS.values():
        assert typed in actual, f"typed module {typed} missing from canonical bundle"
    assert "missions.js" in actual, "legacy missions controller must stay in bundle"
    assert "gups.js" in actual, "legacy gups controller must stay in bundle"
    assert "launch.js" not in actual, "rollback-only legacy launch.js must be excluded"
    assert "profile.js" not in actual, (
        "rollback-only legacy profile.js must be excluded"
    )


def test_legacy_rollback_references_all_sources_and_matches_baseline(
    tmp_path: Path,
) -> None:
    legacy = _load_legacy_manifest()
    files = {e["file"] for e in legacy["scripts"]}
    for name in ("missions.js", "gups.js", "launch.js", "profile.js"):
        assert name in files, f"legacy rollback manifest must reference {name}"
    output = tmp_path / "legacy.html"
    result = _build_legacy(output)
    assert result.returncode == 0, (
        f"legacy rollback build failed (exit {result.returncode}): {result.stderr}"
    )
    assert _sha256_bytes(output.read_bytes()) == LEGACY_ROLLBACK_BASELINE_SHA, (
        "legacy rollback artifact must be byte-identical to the pre-WP-31B baseline"
    )
    html = output.read_text(encoding="utf-8")
    assert html.count("<script>") == 19
    assert re.search(r"<script\s+[^>]*src\s*=", html) is None


# ── focused browser flow ─────────────────────────────────────────────────


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


def test_browser_static_catalog_flow() -> None:
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
                assert _visible(page, "#ocean-rescue-profile-choice") is False

                mission_cards = page.evaluate(
                    """() => Array.from(
                      document.querySelectorAll('#ocean-rescue-mission-list [data-mission-id]')
                    ).map(b => ({
                      id: b.getAttribute('data-mission-id'),
                      disabled: b.disabled,
                      title: b.querySelector('.ocean-rescue-mission-title').textContent,
                      companion: b.querySelector('.ocean-rescue-mission-companion').textContent,
                      summary: b.querySelector('.ocean-rescue-mission-summary').textContent,
                      status: b.querySelector('.ocean-rescue-mission-status').textContent,
                      hasNew: !!b.querySelector('.ocean-rescue-mission-new')
                    }))"""
                )
                assert [c["id"] for c in mission_cards] == [
                    "sea-turtle",
                    "crab",
                    "young-whale",
                ], "mission cards must be in canonical order"
                assert [c["title"] for c in mission_cards] == [
                    "Sea Turtle Rescue",
                    "Crab Rescue",
                    "Young Whale Rescue",
                ]
                assert [c["companion"] for c in mission_cards] == [
                    "Peso",
                    "Tweak",
                    "Captain Barnacles",
                ]
                assert [c["summary"] for c in mission_cards] == [
                    "Cut the ropes and free the trapped sea turtle.",
                    "Move the rocks and help the trapped crab.",
                    "Tow the debris and clear a path for the young whale.",
                ]
                assert [c["status"] for c in mission_cards] == [
                    "Available",
                    "Locked",
                    "Locked",
                ], "exact initial lock/availability state required"
                assert [c["disabled"] for c in mission_cards] == [False, True, True]
                assert all(c["hasNew"] is False for c in mission_cards)

                page.click('#ocean-rescue-mission-list [data-mission-id="sea-turtle"]')
                page.wait_for_selector("#ocean-rescue-gup-select:not([hidden])")

                gup_cards = page.evaluate(
                    """() => Array.from(
                      document.querySelectorAll('#ocean-rescue-gup-list [data-gup-id]')
                    ).map(b => ({
                      id: b.getAttribute('data-gup-id'),
                      name: b.querySelector('.ocean-rescue-gup-name').textContent,
                      description: b.querySelector('.ocean-rescue-gup-description').textContent,
                      pressed: b.getAttribute('aria-pressed')
                    }))"""
                )
                assert [g["id"] for g in gup_cards] == ["gup-c", "gup-i", "gup-x"]
                assert [g["name"] for g in gup_cards] == ["GUP-C", "GUP-I", "GUP-X"]
                assert [g["description"] for g in gup_cards] == [
                    "Yellow rescue sub",
                    "White and blue rescue sub",
                    "Red rescue sub",
                ]
                assert [g["pressed"] for g in gup_cards] == ["true", "false", "false"]

                page.click('#ocean-rescue-gup-list [data-gup-id="gup-i"]')
                page.wait_for_function(
                    """() => document.getElementById('ocean-rescue-gup-list')
                             .querySelector('[data-gup-id="gup-i"]')
                             .getAttribute('aria-pressed') === 'true'"""
                )
                page.click("#ocean-rescue-gup-launch")
                page.wait_for_selector("#ocean-rescue-launch:not([hidden])")

                briefing = page.evaluate(
                    "() => document.getElementById('ocean-rescue-launch-briefing').textContent"
                )
                assert briefing == (
                    "A sea turtle is trapped in a net. Let’s find it and cut the ropes!"
                ), "launch briefing must come from the typed launch catalog"
                gup_name = page.evaluate(
                    "() => document.getElementById('ocean-rescue-launch-gup-name').textContent"
                )
                assert gup_name == "GUP-I"
                companion = page.evaluate(
                    "() => document.getElementById('ocean-rescue-launch-companion').textContent"
                )
                assert companion == "Peso:"

                runtime = page.evaluate(
                    """() => {
                      const M = OceanRescue.Missions;
                      const G = OceanRescue.Gups;
                      const L = OceanRescue.Launch;
                      const content = L.getMissionContent('sea-turtle');
                      return {
                        missionCatalogFrozen: Object.isFrozen(M.Catalog),
                        missionEntriesFrozen: M.Catalog.every(e => Object.isFrozen(e)),
                        missionCatalog: M.Catalog.map(e => ({id: e.id, order: e.order})),
                        gupCatalogFrozen: Object.isFrozen(G.Catalog),
                        gupEntriesFrozen: G.Catalog.every(e => Object.isFrozen(e)),
                        gupCatalog: G.Catalog.map(e => e.id),
                        launchFrozen: Object.isFrozen(L),
                        launchCatalogFrozen: Object.isFrozen(L.Catalog),
                        launchCatalog: L.Catalog.map(e => e.missionId),
                        durationMs: L.DurationMs,
                        goalDurationMs: L.GoalDurationMs,
                        briefing: content.briefing,
                        goal: content.goal,
                        unknown: L.getMissionContent('unknown')
                      };
                    }"""
                )
                assert runtime["missionCatalogFrozen"] is True
                assert runtime["missionEntriesFrozen"] is True
                assert [e["id"] for e in runtime["missionCatalog"]] == [
                    "sea-turtle",
                    "crab",
                    "young-whale",
                ]
                assert [e["order"] for e in runtime["missionCatalog"]] == [1, 2, 3]
                assert runtime["gupCatalogFrozen"] is True
                assert runtime["gupEntriesFrozen"] is True
                assert runtime["gupCatalog"] == ["gup-c", "gup-i", "gup-x"]
                assert runtime["launchFrozen"] is True
                assert runtime["launchCatalogFrozen"] is True
                assert runtime["launchCatalog"] == [
                    "sea-turtle",
                    "crab",
                    "young-whale",
                ]
                assert runtime["durationMs"] == 6000
                assert runtime["goalDurationMs"] == 3000
                assert runtime["briefing"] == (
                    "A sea turtle is trapped in a net. Let’s find it and cut the ropes!"
                )
                assert runtime["goal"] == "Rescue the sea turtle!"
                assert runtime["unknown"] is None

                mutation = page.evaluate(
                    """() => {
                      const M = OceanRescue.Missions;
                      const G = OceanRescue.Gups;
                      const L = OceanRescue.Launch;
                      let missionPushThrew = false;
                      try { M.Catalog.push({id: 'x', order: 4, title: 'X', companion: 'Y', summary: 'Z'}); } catch (e) { missionPushThrew = true; }
                      M.Catalog[0].title = 'HACKED';
                      G.Catalog[0].name = 'HACKED';
                      L.DurationMs = 9999;
                      return {
                        missionPushThrew,
                        missionTitle: M.Catalog[0].title,
                        gupName: G.Catalog[0].name,
                        durationMs: L.DurationMs,
                        missionLength: M.Catalog.length,
                        gupLength: G.Catalog.length,
                        launchLength: L.Catalog.length
                      };
                    }"""
                )
                assert mutation["missionLength"] == 3
                assert mutation["missionTitle"] == "Sea Turtle Rescue"
                assert mutation["gupName"] == "GUP-C"
                assert mutation["durationMs"] == 6000
                assert mutation["launchLength"] == 3

                page.click("#ocean-rescue-launch-skip")
                page.wait_for_function(
                    """() => document.getElementById('ocean-rescue-goal-banner').hidden === false"""
                )
                goal = page.evaluate(
                    "() => document.getElementById('ocean-rescue-goal-banner').textContent"
                )
                assert goal == "Rescue the sea turtle!", (
                    "goal banner must show the typed launch goal"
                )

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
                startup_count = page.evaluate(
                    """() => {
                      const root = document.getElementById('ocean-rescue-root');
                      return {
                        ready: root.getAttribute('data-ocean-rescue-ready'),
                        appNamespaces: Object.keys(OceanRescue).sort()
                      };
                    }"""
                )
                assert startup_count["ready"] == "true"
                assert "App" in startup_count["appNamespaces"]

                page.close()
                context.close()
            finally:
                browser.close()
    finally:
        server.stop()
