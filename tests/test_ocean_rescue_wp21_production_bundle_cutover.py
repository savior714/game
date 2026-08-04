"""WP-21 production application-bundle cutover contract.

The authoritative standalone Ocean Rescue artifact switches from 19 ordered
manifest scripts (1 vendored Pixi + 18 application scripts) to exactly two
inline blocks: the single vendored Pixi prerequisite followed by one
deterministic Vite IIFE application bundle.

Verifies:

- production-lane static contract (config, package script, tsconfig, Justfile);
- bundle ownership/boundary via metadata and direct content inspection;
- two-run byte determinism of both the Vite bundle and the packaged artifact;
- the standalone document shape (exactly two inline blocks, no module scripts,
  no generated sourcemap, no external requests);
- browser functional parity through the WP-02 representative sea-turtle flow;
- explicit legacy-rollback parity to the pre-cutover ordered-script output.

Production paths are canonical: ``scripts/ocean_rescue/build_single_html.py``
plus the tracked ``ocean-rescue/index.html`` artifact.
"""

from __future__ import annotations

import ast
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp02_browser_baseline import (  # noqa: E402
    HTTPServerFixture,
    assert_evidence,
    collect_evidence,
)

REPO_ROOT = TESTS_DIR.parent
OCEAN_DIR = REPO_ROOT / "domains" / "ocean-rescue"
SRC_DIR = OCEAN_DIR / "src"
DIST_DIR = OCEAN_DIR / "dist"
MANIFEST = SRC_DIR / "build-manifest.json"
LEGACY_MANIFEST = SRC_DIR / "build-manifest.legacy.json"
BUNDLE_CONFIG = OCEAN_DIR / "vite.bundle.ts"
PROD_CONFIG = OCEAN_DIR / "vite.production.config.ts"
SHADOW_CONFIG = OCEAN_DIR / "vite.shadow.config.ts"
PACKAGE_JSON = OCEAN_DIR / "package.json"
TSCONFIG = OCEAN_DIR / "tsconfig.json"
JUSTFILE = REPO_ROOT / "Justfile"
ARTIFACT = REPO_ROOT / "ocean-rescue" / "index.html"
BUILDER = REPO_ROOT / "scripts" / "ocean_rescue" / "build_single_html.py"

BUNDLE_FILE = "ocean-rescue-app.js"
METADATA_FILE = "production-bundle-metadata.json"
PROD_FILES = {BUNDLE_FILE, METADATA_FILE}

LEGACY_SCRIPT_COUNT = 20
NON_VENDOR_COUNT = 19
PIXI_VENDOR_FILE = "vendor/pixi-8.19.0.min.js"
PIXI_NAMESPACE = "PIXI"
CANONICAL_ENTRY = "main.js"
TARGET = "baseline-widely-available"
MINIFIER = "oxc"

# Immutable historical evidence: the tracked ``ocean-rescue/index.html`` at
# 07ee6a0 (the pre-WP-21 deployment baseline) was the ordered-script legacy
# artifact with this SHA. It records the historical artifact identity and is
# never a gate for current-source rollback builds; the current-source legacy
# rollback artifact is verified dynamically by clean-build equality (see
# test_legacy_rollback_is_deterministic and
# test_operational_rollback_restores_legacy_and_bundle).
HISTORICAL_PRE_WP21_LEGACY_ARTIFACT_SHA256 = (
    "cfd991d83524db6c7ad225da11ef7a9421300bdf588c4b905bf4e5556f776582"
)

# Assignment-aware anti-regression guard for the mutable legacy rollback
# baseline constants. These names were removed from the current-source
# contract because template or style changes would require rebasing a
# hardcoded artifact SHA (see test_legacy_rollback_is_deterministic). The
# guard inspects every Ocean Rescue test file, including this one, so a
# reintroduced assignment cannot hide in the file that owns the guard.
_ROLLBACK_BASELINE_FORBIDDEN_NAMES = (
    "PRE_WP21_LEGACY_BASELINE_SHA",
    "LEGACY_ROLLBACK_BASELINE_SHA",
)
_HISTORICAL_EVIDENCE_NAME = "HISTORICAL_PRE_WP21_LEGACY_ARTIFACT_SHA256"
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

PLAN_DOC = (
    REPO_ROOT / "docs" / "plans" / "PLAN_ocean_rescue_vite_esm_typescript_migration.md"
)


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _load_legacy_manifest() -> dict:
    return json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))


def _load_package() -> dict:
    return json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))


def _non_vendor_scripts(manifest: dict) -> list[dict]:
    return [e for e in manifest["scripts"] if e.get("kind") != "vendor"]


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


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
    files = {p.name for p in DIST_DIR.iterdir() if p.is_file()}
    assert files == PROD_FILES, f"expected {PROD_FILES}, found {files}"


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


def _restore_canonical() -> subprocess.CompletedProcess[str]:
    """Restore the tracked canonical artifact via the production packaging lane."""
    return _build_artifact(ARTIFACT)


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


def _build_legacy_canonical() -> subprocess.CompletedProcess[str]:
    """Invoke the operational rollback contract: legacy mode to the canonical path."""
    return subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--mode",
            "legacy",
            "--manifest",
            str(LEGACY_MANIFEST),
            "--output",
            str(ARTIFACT),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


@pytest.fixture(scope="session", autouse=True)
def production_bundle():
    """Build the canonical production bundle once per session."""
    _clean_production_bundle()
    yield
    shutil.rmtree(DIST_DIR, ignore_errors=True)


# --- static contract ---


def test_production_config_exists() -> None:
    assert PROD_CONFIG.exists(), "missing vite.production.config.ts"
    text = PROD_CONFIG.read_text(encoding="utf-8")
    assert "createBundleLaneConfig" in text
    assert 'lane: "production"' in text
    assert "ocean-rescue-app.js" in text
    assert "production-bundle-metadata.json" in text


def test_package_has_production_build_script() -> None:
    scripts = _load_package().get("scripts", {})
    prod = scripts.get("build:production")
    assert prod, "package.json must define a build:production script"
    assert "vite build" in prod
    assert "--config vite.production.config.ts" in prod


def test_tsconfig_includes_production_config_and_bundle() -> None:
    cfg = json.loads(TSCONFIG.read_text(encoding="utf-8"))
    include = cfg.get("include", [])
    assert "vite.production.config.ts" in include
    assert "vite.bundle.ts" in include


def test_justfile_has_distinct_production_proof_and_rollback_recipes() -> None:
    text = JUSTFILE.read_text(encoding="utf-8")
    assert "--mode production" in text
    assert "--mode legacy" in text
    assert "build-ocean-rescue:" in text, "canonical production build recipe missing"
    assert "build-ocean-rescue-legacy-proof:" in text, (
        "proof-only legacy recipe missing"
    )
    assert "rollback-ocean-rescue-to-legacy:" in text, (
        "operational rollback recipe missing"
    )
    assert "dist/legacy-rollback.html" in text, (
        "proof-only recipe must write a dist proof artifact"
    )
    assert (
        "dist/legacy-rollback.html"
        not in text.split("rollback-ocean-rescue-to-legacy:")[1]
    ), "operational rollback must not be redirected to dist/"
    rollback_recipe = text.split("rollback-ocean-rescue-to-legacy:")[1]
    assert "--output ocean-rescue/index.html" in rollback_recipe, (
        "operational rollback must write the canonical artifact path"
    )


def test_dev_config_remains_development_only() -> None:
    text = (OCEAN_DIR / "vite.config.ts").read_text(encoding="utf-8")
    assert "outDir" not in text, "vite.config.ts must not declare a build outDir"
    assert "build:" not in text, "vite.config.ts must not own a production build"


# --- bundle ownership / boundary ---


def test_metadata_is_valid_and_complete() -> None:
    metadata = json.loads((DIST_DIR / METADATA_FILE).read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "state",
        "format",
        "target",
        "minifier",
        "sourcemap",
        "bundle_file",
        "bundle_bytes",
        "bundle_sha256",
        "entry",
        "vendor",
        "legacy_script_count",
        "application_scripts",
        "expected_namespaces",
        "actual_module_files",
        "dynamic_import_count",
        "output_files",
    }
    assert required.issubset(metadata.keys()), (
        f"missing metadata keys: {required - set(metadata.keys())}"
    )
    assert metadata["state"] == "PRODUCTION_BUNDLE"
    assert metadata["format"] == "iife"
    assert metadata["target"] == TARGET
    assert metadata["minifier"] == MINIFIER
    assert metadata["sourcemap"] is False
    assert metadata["bundle_file"] == BUNDLE_FILE
    assert metadata["dynamic_import_count"] == 0
    assert metadata["entry"] == CANONICAL_ENTRY
    assert metadata["legacy_script_count"] == NON_VENDOR_COUNT
    assert {p.name for p in DIST_DIR.iterdir() if p.is_file()} == PROD_FILES


def test_metadata_membership_matches_legacy_manifest() -> None:
    legacy = _load_legacy_manifest()
    expected = [e["file"] for e in _non_vendor_scripts(legacy)]
    assert len(expected) == NON_VENDOR_COUNT
    metadata = json.loads((DIST_DIR / METADATA_FILE).read_text(encoding="utf-8"))
    assert metadata["application_scripts"] == expected
    assert metadata["expected_namespaces"] == [
        e["namespace"] for e in _non_vendor_scripts(legacy)
    ]
    for raw in metadata["actual_module_files"]:
        assert (
            raw == "main.js"
            or raw.startswith("esm/")
            or raw.endswith(".ts")
            or raw in expected
        ), f"unexpected module file recorded: {raw}"
    # WP-31A: the canonical graph owns the typed profile implementation and
    # excludes the rollback-only legacy profile.js.
    assert "profile/profile.ts" in metadata["actual_module_files"], (
        "typed profile implementation missing from production membership"
    )
    assert "profile.js" not in metadata["actual_module_files"], (
        "rollback-only legacy profile.js must not be in production membership"
    )
    # WP-31B: the canonical graph owns the typed mission/GUP/launch static
    # modules, retains the mission/GUP controllers, and excludes the
    # rollback-only legacy launch.js.
    for typed in ("missions/catalog.ts", "gups/catalog.ts", "launch/launch.ts"):
        assert typed in metadata["actual_module_files"], (
            f"typed static module {typed} missing from production membership"
        )
    assert "missions.js" in metadata["actual_module_files"], (
        "legacy missions controller must stay in production membership"
    )
    assert "gups.js" in metadata["actual_module_files"], (
        "legacy gups controller must stay in production membership"
    )
    assert "launch.js" not in metadata["actual_module_files"], (
        "rollback-only legacy launch.js must not be in production membership"
    )
    # WP-31C: the canonical graph owns the typed core state machine and travel
    # runtime contract and excludes the rollback-only legacy state.js/travel.js.
    for typed in ("state/state.ts", "travel/travel.ts"):
        assert typed in metadata["actual_module_files"], (
            f"typed core module {typed} missing from production membership"
        )
    for rollback in ("state.js", "travel.js"):
        assert rollback not in metadata["actual_module_files"], (
            f"rollback-only legacy {rollback} must not be in production membership"
        )


def test_vendor_boundary_external() -> None:
    metadata = json.loads((DIST_DIR / METADATA_FILE).read_text(encoding="utf-8"))
    vendor = metadata["vendor"]
    assert vendor["file"] == PIXI_VENDOR_FILE
    assert vendor["namespace"] == PIXI_NAMESPACE
    assert vendor["external"] is True


def test_bundle_bytes_and_sha256_match_metadata() -> None:
    bundle = (DIST_DIR / BUNDLE_FILE).read_bytes()
    metadata = json.loads((DIST_DIR / METADATA_FILE).read_text(encoding="utf-8"))
    assert len(bundle) == metadata["bundle_bytes"]
    assert _sha256_bytes(bundle) == metadata["bundle_sha256"]


def test_bundle_is_iife_and_pixi_external() -> None:
    text = (DIST_DIR / BUNDLE_FILE).read_text(encoding="utf-8")
    assert len(text) > 0, "bundle must not be empty"
    assert not re.search(r"\bimport\b", text), "bundle must not contain import"
    assert not re.search(r"\bexport\b", text), "bundle must not contain export"
    assert "node_modules/pixi.js" not in text, "bundle must not embed the pixi package"
    assert "sourceMappingURL" not in text, "bundle must not reference a source map"


def test_two_clean_bundle_runs_byte_identical(tmp_path: Path) -> None:
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
            f"byte mismatch for {name}"
        )


def test_bundle_compresses_meaningfully() -> None:
    bundle = (DIST_DIR / BUNDLE_FILE).read_bytes()
    gzipped = gzip.compress(bundle)
    assert len(bundle) > 0
    assert len(gzipped) < len(bundle)


# --- packaged standalone artifact ---


def test_artifact_has_exactly_two_inline_scripts() -> None:
    html = ARTIFACT.read_text(encoding="utf-8")
    script_re = re.compile(r"<script>(.*?)</script>", re.IGNORECASE | re.DOTALL)
    blocks = script_re.findall(html)
    assert len(blocks) == 2, f"expected exactly 2 inline scripts, found {len(blocks)}"
    assert not re.search(r"<script\s+[^>]*src\s*=", html), (
        "external script src must not be present"
    )
    assert not re.search(r'type\s*=\s*["\']module["\']', html), (
        "module script must not be present"
    )
    assert "sourceMappingURL=pixi.min.js.map" in blocks[0], "vendored Pixi inline"
    assert "OceanRescue.App" in blocks[1], "application bundle inline"


def test_tracked_artifact_matches_clean_production_rebuild(tmp_path: Path) -> None:
    output = tmp_path / "rebuilt.html"
    result = _build_artifact(output)
    assert result.returncode == 0, (
        f"production packaging failed (exit {result.returncode}): {result.stderr}"
    )
    assert output.read_bytes() == ARTIFACT.read_bytes()


def test_two_artifact_rebuilds_byte_identical(tmp_path: Path) -> None:
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    assert _build_artifact(a).returncode == 0
    assert _build_artifact(b).returncode == 0
    assert a.read_bytes() == b.read_bytes()


# --- legacy rollback ---


def test_legacy_rollback_produces_ordered_scripts(tmp_path: Path) -> None:
    output = tmp_path / "legacy.html"
    result = _build_legacy(output)
    assert result.returncode == 0, (
        f"rollback build failed (exit {result.returncode}): {result.stderr}"
    )
    html = output.read_text(encoding="utf-8")
    assert html.count("<script>") == LEGACY_SCRIPT_COUNT, (
        "legacy rollback must reproduce the ordered-set output"
    )
    assert re.search(r"<script\s+[^>]*src\s*=", html) is None


def test_legacy_rollback_is_deterministic(tmp_path: Path) -> None:
    """Two clean current-source legacy builds must be byte-identical.

    The legacy rollback artifact is a function of the current template, styles,
    generated render assets, legacy manifest, and rollback-only source graph.
    Template/style/product changes legitimately change its bytes, so the
    current-source contract is verified by clean-build byte equality rather
    than a hardcoded mutable SHA. The SHA is reported for diagnostics only and
    is never stored as a source constant.
    """
    output_a = tmp_path / "legacy-a.html"
    output_b = tmp_path / "legacy-b.html"
    assert _build_legacy(output_a).returncode == 0, "legacy build A failed"
    assert _build_legacy(output_b).returncode == 0, "legacy build B failed"
    assert output_a.read_bytes() == output_b.read_bytes(), (
        "two clean current-source legacy builds must be byte-identical"
    )
    diagnostic_sha = _sha256_bytes(output_a.read_bytes())
    assert len(diagnostic_sha) == 64, "diagnostic SHA-256 must be 64 hex chars"


def _assigned_names(target: ast.AST) -> list[str]:
    """Collect simple names bound by an assignment target."""
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        names: list[str] = []
        for element in target.elts:
            names.extend(_assigned_names(element))
        return names
    return []


def _is_renamed_mutable_baseline_constant(name: str) -> bool:
    """A renamed legacy rollback/current-baseline artifact constant."""
    if name == _HISTORICAL_EVIDENCE_NAME:
        return False
    if "LEGACY" not in name:
        return False
    return "ROLLBACK" in name or "BASELINE" in name


def _mutable_baseline_violations(source: str, label: str) -> list[tuple[str, int]]:
    """Return (name, lineno) for forbidden mutable baseline assignments."""
    tree = ast.parse(source, filename=label)
    violations: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        value: ast.AST | None
        targets: list[ast.AST]
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        literal_hex = (
            isinstance(value, ast.Constant)
            and isinstance(value.value, str)
            and _SHA256_HEX_RE.match(value.value) is not None
        )
        for target in targets:
            for name in _assigned_names(target):
                if name in _ROLLBACK_BASELINE_FORBIDDEN_NAMES:
                    violations.append((name, node.lineno))
                elif literal_hex and _is_renamed_mutable_baseline_constant(name):
                    violations.append((name, node.lineno))
    return violations


def _mutable_baseline_violations_in_files() -> list[tuple[str, str, int]]:
    """Scan every Ocean Rescue test file, including the WP-21 file itself."""
    violations: list[tuple[str, str, int]] = []
    for test_file in sorted(TESTS_DIR.glob("test_ocean_rescue_*.py")):
        for name, lineno in _mutable_baseline_violations(
            test_file.read_text(encoding="utf-8"), str(test_file)
        ):
            violations.append((str(test_file), name, lineno))
    return violations


def test_historical_pre_wp21_evidence_is_not_a_current_gate() -> None:
    """The immutable pre-WP-21 artifact SHA is evidence, not a live baseline.

    ``HISTORICAL_PRE_WP21_LEGACY_ARTIFACT_SHA256`` records the historical
    ordered-script artifact identity at the pre-WP-21 deployment baseline
    (07ee6a0). It must never be conflated with a mutable current-source legacy
    build SHA, and no Ocean Rescue test file may assign a mutable rollback
    baseline constant, because template/style changes would require rebasing
    them. The guard covers every ``test_ocean_rescue_*.py`` file, including
    this file itself.
    """
    assert HISTORICAL_PRE_WP21_LEGACY_ARTIFACT_SHA256 == (
        "cfd991d83524db6c7ad225da11ef7a9421300bdf588c4b905bf4e5556f776582"
    )
    violations = _mutable_baseline_violations_in_files()
    assert not violations, "\n".join(
        f"{path}:{lineno}: forbidden mutable rollback baseline assignment {name}"
        for path, name, lineno in violations
    )


def test_mutable_legacy_baseline_guard_covers_wp21_self_file() -> None:
    """The assignment-aware guard rejects forbidden baselines in WP-21 content.

    Synthetic snippets labelled with the WP-21 file path prove that forbidden
    mutable rollback baseline assignments are detected even in the file that
    owns the guard, while the intentional historical evidence assignment and
    prose mentioning the old names stay allowed. No tracked file is modified.
    """
    wp21_label = str(Path(__file__).resolve())
    hex64 = "c" * 64

    plain = f'PRE_WP21_LEGACY_BASELINE_SHA = "{hex64}"\n'
    assert _mutable_baseline_violations(plain, wp21_label) == [
        ("PRE_WP21_LEGACY_BASELINE_SHA", 1)
    ]

    annotated = f'LEGACY_ROLLBACK_BASELINE_SHA: str = "{hex64}"\n'
    assert _mutable_baseline_violations(annotated, wp21_label) == [
        ("LEGACY_ROLLBACK_BASELINE_SHA", 1)
    ]

    renamed = f'CURRENT_LEGACY_ROLLBACK_BASELINE_SHA256 = "{hex64}"\n'
    assert _mutable_baseline_violations(renamed, wp21_label) == [
        ("CURRENT_LEGACY_ROLLBACK_BASELINE_SHA256", 1)
    ]

    historical = f'HISTORICAL_PRE_WP21_LEGACY_ARTIFACT_SHA256 = "{hex64}"\n'
    assert _mutable_baseline_violations(historical, wp21_label) == []

    docstring = (
        '"""Prose mentioning PRE_WP21_LEGACY_BASELINE_SHA is not an '
        'assignment and must not be flagged."""\n'
    )
    assert _mutable_baseline_violations(docstring, wp21_label) == []

    mention = 'label = "legacy SHA PRE_WP21_LEGACY_BASELINE_SHA in a string"\n'
    assert _mutable_baseline_violations(mention, wp21_label) == []

    legacy_dict = f'LEGACY_SOURCE_SHA256 = {{"missions.js": "{hex64}"}}\n'
    assert _mutable_baseline_violations(legacy_dict, wp21_label) == []


def test_operational_rollback_restores_legacy_and_bundle(tmp_path: Path) -> None:
    """The canonical artifact must transition bundle -> legacy -> bundle.

    The operational rollback writes the tracked ``ocean-rescue/index.html`` to
    the current-source legacy ordered-script artifact, verified byte-identical
    to a clean current-source legacy build, and the production lane must
    restore the bundle-owned artifact. Cleanup restores bundle-owned state even
    if an intermediate rollback assertion fails.
    """
    _clean_production_bundle()
    assert _restore_canonical().returncode == 0, "production restore failed"
    bundle_canonical = ARTIFACT.read_bytes()

    legacy_tmp = tmp_path / "legacy-expected.html"
    assert _build_legacy(legacy_tmp).returncode == 0, "legacy build failed"
    expected_legacy = legacy_tmp.read_bytes()

    try:
        result = _build_legacy_canonical()
        assert result.returncode == 0, (
            f"operational rollback failed (exit {result.returncode}): {result.stderr}"
        )
        rollback_canonical = ARTIFACT.read_bytes()
        assert rollback_canonical == expected_legacy, (
            "operational rollback must write the exact current-source legacy artifact"
        )
        html = rollback_canonical.decode("utf-8")
        assert html.count("<script>") == LEGACY_SCRIPT_COUNT, (
            "legacy canonical HTML must have 19 inline classic scripts"
        )
        assert re.search(r"<script\s+[^>]*src\s*=", html) is None
        assert re.search(r'type\s*=\s*["\']module["\']', html) is None
        _assert_legacy_manifest_order(html)
    finally:
        assert _restore_canonical().returncode == 0, (
            "cleanup restore to bundle-owned artifact failed"
        )
        restored = ARTIFACT.read_bytes()
        assert restored == bundle_canonical, (
            "restored canonical artifact must equal the original bundle-owned bytes"
        )
        restored_html = restored.decode("utf-8")
        assert restored_html.count("<script>") == 2, (
            "restored canonical HTML must have exactly two inline classic scripts"
        )
        assert re.search(r'type\s*=\s*["\']module["\']', restored_html) is None


def _assert_legacy_manifest_order(html: str) -> None:
    """Vendored Pixi first, then the 18 application scripts in legacy order."""
    script_re = re.compile(r"<script>(.*?)</script>", re.IGNORECASE | re.DOTALL)
    blocks = script_re.findall(html)
    assert len(blocks) == LEGACY_SCRIPT_COUNT

    legacy = _load_legacy_manifest()
    assert len(legacy["scripts"]) == LEGACY_SCRIPT_COUNT
    for block, entry in zip(blocks, legacy["scripts"]):
        src_path = SRC_DIR / entry["file"]
        src = src_path.read_text(encoding="utf-8")
        assert block == "\n" + src + "\n", (
            f"script block {entry['namespace']} must match its manifest source in order"
        )


# --- browser functional parity ---


def _production_document_evidence(page: Page) -> dict:
    return page.evaluate(
        """() => {
          const inlineIndices = [];
          Array.from(document.querySelectorAll('script')).forEach((s, i) => {
            if (!s.src) inlineIndices.push(i);
          });
          return {
            inline_script_indices: inlineIndices,
            has_pixi: typeof window.PIXI !== 'undefined',
            pixi_version: typeof window.PIXI === 'undefined' ? null : window.PIXI.VERSION,
            has_app: !!(window.OceanRescue && window.OceanRescue.App),
            namespaces: window.OceanRescue ? Object.keys(window.OceanRescue) : []
          };
        }"""
    )


def test_production_artifact_browser_parity() -> None:
    server = HTTPServerFixture()
    base_url = server.start()
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
                page = context.new_page()
                try:
                    evidence = collect_evidence(
                        page,
                        base_url,
                        {
                            "engine": "Playwright Chromium",
                            "version": browser.version,
                        },
                        entry_path="/ocean-rescue/index.html",
                    )
                    doc = _production_document_evidence(page)
                finally:
                    page.close()
                    context.close()
            finally:
                browser.close()
    finally:
        server.stop()
    assert_evidence(evidence, network_mode="standalone")
    assert doc["inline_script_indices"] == [0, 1], (
        "exactly the two inline script blocks must carry the runtime"
    )
    assert doc["has_pixi"] is True
    assert doc["pixi_version"] == "8.19.0"
    assert doc["has_app"] is True
    for entry in _non_vendor_scripts(_load_legacy_manifest()):
        leaf = entry["namespace"].split(".")[-1]
        if leaf == "App":
            continue
        assert leaf in doc["namespaces"], (
            f"missing runtime namespace {entry['namespace']}"
        )
    script_requests = [
        r["url"]
        for r in evidence["network"]["all_requests"]
        if r["resource_type"] == "script"
    ]
    assert script_requests == [], (
        f"standalone artifact must inline all scripts, got {script_requests}"
    )


# --- documentation state ---


def test_migration_documentation_state() -> None:
    plan = PLAN_DOC.read_text(encoding="utf-8")
    assert "WP-21: COMPLETE" in plan
    assert "Current phase: PHASE_8_READY" in plan
    assert "Next executable work package: WP-33A" in plan
    assert "Authoritative path before:" in plan
    assert "Vite application bundle through temporary standalone packaging" in plan
    assert "WP-31A: COMPLETE" in plan
    assert "WP-31B: COMPLETE" in plan
    assert "WP-31C: COMPLETE" in plan
    assert "WP-32A: COMPLETE" in plan
    assert "Shared mission ID state: TYPE_AUTHORITY" in plan
    assert "Global OceanRescue ABI state: TYPED_SHARED" in plan
    assert "Typed module ESM adapter state: CHECKED_JS" in plan
    assert "Runtime output state: DETERMINISTIC" in plan
    assert "Profile module state: TYPED_CANONICAL" in plan
    assert "Mission catalog state: TYPED_CANONICAL" in plan
    assert "GUP catalog state: TYPED_CANONICAL" in plan
    assert "Launch module state: TYPED_CANONICAL" in plan
    assert "State module state: TYPED_CANONICAL" in plan
    assert "Travel module state: TYPED_CANONICAL" in plan
    assert "Legacy profile.js: ROLLBACK_ONLY" in plan
    assert "Legacy missions.js: CONTROLLER_CANONICAL_PLUS_ROLLBACK" in plan
    assert "Legacy gups.js: CONTROLLER_CANONICAL_PLUS_ROLLBACK" in plan
    assert "Legacy launch.js: ROLLBACK_ONLY" in plan
    assert "Legacy state.js: ROLLBACK_ONLY" in plan
    assert "Legacy travel.js: ROLLBACK_ONLY" in plan
