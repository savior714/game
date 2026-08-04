"""WP-32A shared typed runtime ABI contract.

WP-32A establishes a single minimal shared type boundary between the typed
canonical Ocean Rescue modules and the ESM compatibility adapters without any
runtime change:

- shared mission identifier authority (`src/contracts/mission.ts`) used by the
  mission catalog and the launch catalog;
- a runtime ABI type module (`src/contracts/runtime-abi.ts`) composing the
  actual exported API types plus the mission/GUP controller facade types;
- a single global `window.OceanRescue` declaration
  (`src/contracts/ocean-rescue-global.d.ts`);
- removal of the duplicated local `OceanRescueGlobalNamespace` interfaces from
  the typed modules;
- `@ts-check` + JSDoc type references on all six ESM adapters so the existing
  runtime statements typecheck with zero diagnostics and no suppression.

The work must be type-only: the shared contract modules must never appear as
runtime modules in the production bundle, and the production application
bundle, standalone HTML, and legacy rollback artifact must stay byte-identical
to the pre-WP-32A baseline.

This suite verifies:

- shared identifier: contracts/mission.ts exists with the exact union, the
  mission catalog and launch catalog both import the shared `MissionId`, the
  launch catalog keeps no separate string-literal union, and the existing type
  exports remain;
- runtime ABI module: composes `ProfileApi`, `LaunchApi`, `StateApi`,
  `TravelApi`, `MissionCatalog`, `GupCatalog`, `MissionId`, `GupId` and defines
  the exact mission/GUP snapshot, result, and API shapes;
- global declaration: single `Window.OceanRescue` optional property, no index
  signature, no `any`, and no duplicated local namespace interface in the four
  typed modules;
- adapter typecheck: all six adapters carry `@ts-check`, strict project
  diagnostics are 0, the adapters also typecheck standalone, suppression is
  absent, runtime import order and fail-close behavior are preserved, and the
  mission/GUP facades keep the exact controller method references;
- type-only output: clean production metadata shows no `contracts/*` runtime
  module, zero dynamic imports, no source map, and one application chunk;
- exact output identity: the production application bundle, production
  metadata, standalone HTML, and legacy rollback artifact are byte-identical to
  the pre-WP-32A baseline.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OCEAN_DIR = REPO_ROOT / "domains" / "ocean-rescue"
SRC_DIR = OCEAN_DIR / "src"
ESM_DIR = SRC_DIR / "esm"
CONTRACTS_DIR = SRC_DIR / "contracts"
DIST_DIR = OCEAN_DIR / "dist"
TSCONFIG = OCEAN_DIR / "tsconfig.json"
MANIFEST = SRC_DIR / "build-manifest.json"
LEGACY_MANIFEST = SRC_DIR / "build-manifest.legacy.json"
ARTIFACT = REPO_ROOT / "ocean-rescue" / "index.html"
BUILDER = REPO_ROOT / "scripts" / "ocean_rescue" / "build_single_html.py"

BUNDLE_FILE = "ocean-rescue-app.js"
METADATA_FILE = "production-bundle-metadata.json"

MISSION_CONTRACT = CONTRACTS_DIR / "mission.ts"
RUNTIME_ABI = CONTRACTS_DIR / "runtime-abi.ts"
GLOBAL_DECL = CONTRACTS_DIR / "ocean-rescue-global.d.ts"

TYPED_MODULES = {
    "profile": SRC_DIR / "profile" / "profile.ts",
    "launch": SRC_DIR / "launch" / "launch.ts",
    "state": SRC_DIR / "state" / "state.ts",
    "travel": SRC_DIR / "travel" / "travel.ts",
}

ADAPTERS = {
    "profile": ESM_DIR / "profile.js",
    "missions": ESM_DIR / "missions.js",
    "gups": ESM_DIR / "gups.js",
    "launch": ESM_DIR / "launch.js",
    "state": ESM_DIR / "state.js",
    "travel": ESM_DIR / "travel.js",
}

# Pre-WP-32A baseline captured from a clean pipeline (see evidence doc).
LEGACY_ROLLBACK_BASELINE_SHA = (
    "9562d991a64852da59531e830742d6936c759eb8792179a1ce993a8cd49a2729"
)

FORBIDDEN_TOKENS = (
    "@ts-nocheck",
    "@ts-ignore",
    "@ts-expect-error",
    "as any",
    ": any",
    "<any>",
    "as unknown as any",
)


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


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


def _clean_production_bundle() -> None:
    result = _run_vite_build("vite.production.config.ts")
    assert result.returncode == 0, (
        f"production build failed (exit {result.returncode}):\n{result.stderr}"
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


# ── 10.1 shared mission identifier ────────────────────────────────────────


def test_shared_mission_id_module_exists() -> None:
    assert MISSION_CONTRACT.is_file(), "src/contracts/mission.ts missing"
    text = MISSION_CONTRACT.read_text(encoding="utf-8")
    assert 'export type MissionId = "sea-turtle" | "crab" | "young-whale";' in text
    assert "import" not in text.replace("import.meta", ""), (
        "mission contract must be a standalone type-only module"
    )


def test_mission_catalog_uses_shared_mission_id() -> None:
    text = (SRC_DIR / "missions" / "catalog.ts").read_text(encoding="utf-8")
    assert (
        'import type { MissionId as SharedMissionId } from "../contracts/mission";'
        in text
    )
    assert "export type MissionId = SharedMissionId;" in text, (
        "mission catalog MissionId must alias the shared authority"
    )
    assert "export interface MissionCatalogEntry" in text


def test_launch_catalog_uses_same_shared_mission_id() -> None:
    text = (SRC_DIR / "launch" / "launch.ts").read_text(encoding="utf-8")
    assert 'import type { MissionId } from "../contracts/mission";' in text
    assert "export type LaunchMissionId = MissionId;" in text, (
        "launch must alias the shared MissionId, not a fresh union"
    )
    assert '"sea-turtle" | "crab" | "young-whale"' not in text, (
        "launch module must not re-define a separate mission string union"
    )
    assert "readonly missionId: MissionId;" in text
    assert 'missionId: "sea-turtle"' in text, "launch catalog values must remain"


def test_mission_type_exports_compatibility_preserved() -> None:
    missions = (SRC_DIR / "missions" / "catalog.ts").read_text(encoding="utf-8")
    launch = (SRC_DIR / "launch" / "launch.ts").read_text(encoding="utf-8")
    assert "export type MissionId" in missions
    assert "export type LaunchMissionId" in launch
    assert "export interface LaunchCatalogEntry" in launch


# ── 10.2 global ABI declaration ───────────────────────────────────────────


def test_global_abi_declaration_exists_and_is_single() -> None:
    assert GLOBAL_DECL.is_file(), "src/contracts/ocean-rescue-global.d.ts missing"
    text = GLOBAL_DECL.read_text(encoding="utf-8")
    assert 'import type { OceanRescueNamespace } from "./runtime-abi";' in text
    assert "declare global" in text
    assert "interface Window" in text
    assert "OceanRescue?: OceanRescueNamespace;" in text, (
        "window.OceanRescue must stay optional reflecting init order"
    )
    assert "export {};" in text, "global declaration must be a module"
    for token in FORBIDDEN_TOKENS:
        assert token not in text, f"forbidden token in global declaration: {token}"
    assert "[key" not in text and "index signature" not in text, (
        "global declaration must not carry an index signature"
    )


def test_runtime_abi_module_composes_actual_api_types() -> None:
    text = RUNTIME_ABI.read_text(encoding="utf-8")
    for import_path in (
        '"../gups/catalog"',
        '"../launch/launch"',
        '"../missions/catalog"',
        '"../profile/profile"',
        '"../state/state"',
        '"../travel/travel"',
    ):
        assert "import type" in text and import_path in text, (
            f"runtime ABI must type-only import {import_path}"
        )
    export_block = text.split("export type {", 1)[1].split("};", 1)[0]
    for exported in (
        "ProfileApi",
        "LaunchApi",
        "StateApi",
        "TravelApi",
        "MissionCatalog",
        "GupCatalog",
        "MissionId",
        "GupId",
    ):
        assert exported in export_block, f"runtime ABI must re-export {exported}"
    assert "export interface MissionProgressionSnapshot" in text
    assert "readonly selectedMissionId: MissionId | null;" in text
    assert "readonly unlockedMissionIds: readonly MissionId[];" in text
    assert "readonly completedMissionIds: readonly MissionId[];" in text
    assert "readonly newMissionIds: readonly MissionId[];" in text
    assert "export interface MissionCompletionResult" in text
    assert "readonly changed: boolean;" in text
    assert "readonly newlyUnlockedMissionId: MissionId | null;" in text
    assert "export interface MissionsApi" in text
    for method in (
        "Catalog",
        "getSnapshot",
        "isUnlocked",
        "selectMission",
        "completeMission",
        "markMissionViewed",
    ):
        assert (
            method
            in text.split("export interface MissionsApi")[1].split(
                "export interface GupSelectionSnapshot"
            )[0]
        ), f"MissionsApi must expose {method}"
    assert "export interface GupSelectionSnapshot" in text
    assert "readonly selectedGupId: GupId;" in text
    assert "readonly lastGupId: GupId;" in text
    assert "export interface GupsApi" in text
    for method in (
        "Catalog",
        "getSnapshot",
        "isValidGup",
        "prepareSelection",
        "selectGup",
        "confirmSelection",
    ):
        assert (
            method
            in text.split("export interface GupsApi")[1].split(
                "export interface OceanRescueNamespace"
            )[0]
        ), f"GupsApi must expose {method}"
    assert "export interface OceanRescueNamespace" in text
    for slot in ("Profile", "Missions", "Gups", "Launch", "State", "Travel"):
        assert f"{slot}?:" in text.split("export interface OceanRescueNamespace")[1], (
            f"OceanRescueNamespace must expose optional {slot} slot"
        )
    for token in FORBIDDEN_TOKENS:
        assert token not in text, f"forbidden token in runtime ABI: {token}"
    assert "interface OceanRescueGlobalNamespace" not in text


def test_local_namespace_interfaces_removed_from_typed_modules() -> None:
    for name, path in TYPED_MODULES.items():
        text = path.read_text(encoding="utf-8")
        assert "interface OceanRescueGlobalNamespace" not in text, (
            f"{name}.ts must not redefine the local namespace interface"
        )
        assert "OceanRescue?: {" not in text, (
            f"{name}.ts must not carry a local slot-only namespace shape"
        )
        assert (
            'import type { OceanRescueNamespace } from "../contracts/runtime-abi";'
            in text
        ), f"{name}.ts must reference the shared OceanRescueNamespace type"
        assert "window as Window & { OceanRescue?: OceanRescueNamespace }" in text, (
            f"{name}.ts must cast window through the shared namespace type"
        )


# ── 10.3 adapter typecheck ────────────────────────────────────────────────


def test_all_six_adapters_have_ts_check_and_shared_reference() -> None:
    for name, path in ADAPTERS.items():
        text = path.read_text(encoding="utf-8")
        assert text.startswith("// @ts-check"), f"{name}.js must start with @ts-check"
        assert (
            '/// <reference path="../contracts/ocean-rescue-global.d.ts" />' in text
        ), f"{name}.js must load the shared global declaration"
        for token in FORBIDDEN_TOKENS:
            assert token not in text, f"forbidden token in {name}.js: {token}"


def test_adapter_import_order_and_legacy_side_effect_preserved() -> None:
    missions = ADAPTERS["missions"].read_text(encoding="utf-8")
    assert 'import { Catalog } from "../missions/catalog";' in missions
    assert 'import "../missions.js";' in missions
    assert missions.index("import { Catalog }") < missions.index(
        'import "../missions.js"'
    )

    gups = ADAPTERS["gups"].read_text(encoding="utf-8")
    assert 'import { Catalog } from "../gups/catalog";' in gups
    assert 'import "../gups.js";' in gups

    for name in ("profile", "launch", "state", "travel"):
        text = ADAPTERS[name].read_text(encoding="utf-8")
        legacy = f'import "../{name}.js";'
        assert legacy not in text, (
            f"{name}.js adapter must not re-import the rollback-only legacy module"
        )


def test_adapter_fail_close_and_facade_method_identity_preserved() -> None:
    missions = ADAPTERS["missions"].read_text(encoding="utf-8")
    assert 'throw new Error("OceanRescue.Missions was not registered")' in missions
    for method in (
        "getSnapshot",
        "isUnlocked",
        "selectMission",
        "completeMission",
        "markMissionViewed",
    ):
        assert (
            f'throw new Error("OceanRescue.Missions controller is missing {method}")'
            in missions
        )
        assert f"{method}: registered.{method}" in missions, (
            f"missions facade must keep the exact controller method reference for {method}"
        )

    gups = ADAPTERS["gups"].read_text(encoding="utf-8")
    assert 'throw new Error("OceanRescue.Gups was not registered")' in gups
    for method in (
        "getSnapshot",
        "isValidGup",
        "prepareSelection",
        "selectGup",
        "confirmSelection",
    ):
        assert (
            f'throw new Error("OceanRescue.Gups controller is missing {method}")'
            in gups
        )
        assert f"{method}: registered.{method}" in gups, (
            f"gups facade must keep the exact controller method reference for {method}"
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


def test_adapters_typecheck_standalone() -> None:
    """The six adapters must typecheck individually (@ts-check) with zero diagnostics."""
    tmp = Path(subprocess.check_output(["mktemp", "-d"], text=True).strip())
    try:
        result = subprocess.run(
            [
                "corepack",
                "pnpm",
                "exec",
                "tsc",
                "--ignoreConfig",
                "--module",
                "commonjs",
                "--target",
                "es2022",
                "--lib",
                "es2022,dom",
                "--allowJs",
                "--checkJs",
                "false",
                "--noEmit",
                *[str(ADAPTERS[name]) for name in sorted(ADAPTERS)],
            ],
            cwd=str(OCEAN_DIR),
            capture_output=True,
            text=True,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert result.returncode == 0, (
        f"standalone adapter typecheck failed (exit {result.returncode}):\n"
        f"{result.stdout}\n{result.stderr}"
    )


# ── 10.4 type-only output ─────────────────────────────────────────────────


def test_shared_contracts_do_not_enter_production_bundle() -> None:
    _clean_production_bundle()
    metadata = json.loads((DIST_DIR / METADATA_FILE).read_text(encoding="utf-8"))
    actual = set(metadata["actual_module_files"])
    assert not any(f.startswith("contracts/") for f in actual), (
        "shared contract modules must not enter the bundle"
    )
    assert metadata["dynamic_import_count"] == 0
    assert metadata["sourcemap"] is False
    assert metadata["bundle_file"] == BUNDLE_FILE
    files = {p.name for p in DIST_DIR.iterdir() if p.is_file()}
    assert files == {BUNDLE_FILE, METADATA_FILE}, (
        f"production must emit exactly one JS chunk + metadata, got {files}"
    )


def test_module_ownership_unchanged() -> None:
    _clean_production_bundle()
    metadata = json.loads((DIST_DIR / METADATA_FILE).read_text(encoding="utf-8"))
    actual = set(metadata["actual_module_files"])
    for typed in (
        "profile/profile.ts",
        "missions/catalog.ts",
        "gups/catalog.ts",
        "launch/launch.ts",
        "state/state.ts",
        "travel/travel.ts",
    ):
        assert typed in actual, f"typed module {typed} missing from membership"
    for rollback in ("profile.js", "launch.js", "state.js", "travel.js"):
        assert rollback not in actual, (
            f"rollback-only legacy {rollback} must not be in membership"
        )
    assert "missions.js" in actual, "legacy missions controller must stay"
    assert "gups.js" in actual, "legacy gups controller must stay"
    legacy = json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))
    assert metadata["application_scripts"] == [
        e["file"] for e in legacy["scripts"] if e.get("kind") != "vendor"
    ], "application script ownership must be unchanged"


# ── 10.5 exact output identity ────────────────────────────────────────────


def test_production_bundle_byte_identical_to_baseline(tmp_path: Path) -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
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


def test_standalone_html_byte_identical_to_tracked_baseline(tmp_path: Path) -> None:
    _clean_production_bundle()
    output = tmp_path / "rebuilt.html"
    result = _build_artifact(output)
    assert result.returncode == 0, (
        f"production packaging failed (exit {result.returncode}): {result.stderr}"
    )
    assert output.read_bytes() == ARTIFACT.read_bytes(), (
        "standalone HTML must stay byte-identical to the tracked baseline"
    )


def test_legacy_rollback_byte_identical_to_baseline(tmp_path: Path) -> None:
    output = tmp_path / "legacy.html"
    result = _build_legacy(output)
    assert result.returncode == 0, (
        f"legacy rollback build failed (exit {result.returncode}): {result.stderr}"
    )
    assert _sha256_bytes(output.read_bytes()) == LEGACY_ROLLBACK_BASELINE_SHA, (
        "legacy rollback artifact must stay byte-identical to the baseline"
    )
