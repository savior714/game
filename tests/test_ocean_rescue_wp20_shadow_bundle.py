"""WP-20 shadow production bundle contract.

Verifies the deterministic Vite application bundle lane for the Ocean Rescue
legacy global-namespace source:

- static contract: separate shadow config, shadow-scoped package script,
  tsconfig inclusion, Justfile recipes, git-ignored shadow output;
- build contract: exact output set, metadata integrity, vendor/application
  boundary, module membership, bundle hash/size matching, two-run byte
  determinism;
- browser contract: representative sea-turtle flow parity through the shadow
  document with the vendored Pixi prerequisite script, zero external/API
  requests, and the expected document shape;
- production immutability: canonical source and the tracked standalone artifact
  remain unchanged across the shadow work.

Production authority (build-manifest.json + Python standalone builder +
``ocean-rescue/index.html``) is never touched by these tests.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import shutil
import socketserver
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler
from pathlib import Path

from playwright.sync_api import sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp02_browser_baseline import (  # noqa: E402
    assert_evidence,
    collect_evidence,
)

REPO_ROOT = TESTS_DIR.parent
DOMAIN_DIR = REPO_ROOT / "domains" / "ocean-rescue"
SRC_DIR = DOMAIN_DIR / "src"
DIST_DIR = DOMAIN_DIR / "dist"
MANIFEST = SRC_DIR / "build-manifest.json"
TEMPLATE = SRC_DIR / "index.template.html"
VITE_CONFIG = DOMAIN_DIR / "vite.config.ts"
SHADOW_CONFIG = DOMAIN_DIR / "vite.shadow.config.ts"
PACKAGE_JSON = DOMAIN_DIR / "package.json"
TSCONFIG = DOMAIN_DIR / "tsconfig.json"
JUSTFILE = REPO_ROOT / "Justfile"
ARTIFACT = REPO_ROOT / "ocean-rescue" / "index.html"

BUNDLE_FILE = "ocean-rescue-app.shadow.js"
HTML_FILE = "index.shadow.html"
METADATA_FILE = "shadow-bundle-metadata.json"
SHADOW_FILES = {BUNDLE_FILE, HTML_FILE, METADATA_FILE}

EXPECTED_VENDOR_FILE = "vendor/pixi-8.19.0.min.js"
EXPECTED_VENDOR_NAMESPACE = "PIXI"
EXPECTED_APP_COUNT = 18
EXPECTED_SCHEMA_VERSION = 1

PRODUCTION_PATHS = (
    "domains/ocean-rescue/src",
    "domains/ocean-rescue/assets",
    "ocean-rescue/index.html",
    "scripts/ocean_rescue",
)

PLAN_DOC = (
    REPO_ROOT / "docs" / "plans" / "PLAN_ocean_rescue_vite_esm_typescript_migration.md"
)
PHASE3_EVIDENCE = (
    REPO_ROOT
    / "docs"
    / "evidence"
    / "ocean-rescue"
    / "migration"
    / "phase-3"
    / "shadow-production-bundle.md"
)

WP20_IMPLEMENTATION_BASE = "5b2e7c880146cec14568daef72d30a41406fc0fc"
WP20_IMPLEMENTATION_COMMIT = "33f3d43d7e7c83bcddda9edbfdebfe2934f5f33b"


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _load_package() -> dict:
    return json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))


def _non_vendor_scripts(manifest: dict) -> list[dict]:
    return [entry for entry in manifest["scripts"] if entry.get("kind") != "vendor"]


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _run_shadow_build() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "corepack",
            "pnpm",
            "exec",
            "vite",
            "build",
            "--config",
            "vite.shadow.config.ts",
        ],
        cwd=str(DOMAIN_DIR),
        capture_output=True,
        text=True,
    )


def _clean_shadow_build() -> subprocess.CompletedProcess[str]:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    result = _run_shadow_build()
    assert result.returncode == 0, (
        f"shadow build failed (exit {result.returncode}):\n{result.stderr}"
    )
    return result


# --- static contract ---


def test_separate_shadow_config_exists() -> None:
    assert SHADOW_CONFIG.exists(), "missing vite.shadow.config.ts"


def test_existing_vite_config_remains_development_only() -> None:
    text = VITE_CONFIG.read_text(encoding="utf-8")
    assert "outDir" not in text, "vite.config.ts must not declare a build outDir"
    assert "build:" not in text, "vite.config.ts must not own a production build"


def test_package_has_shadow_build_script() -> None:
    scripts = _load_package().get("scripts", {})
    shadow = scripts.get("build:shadow")
    assert shadow, "package.json must define a build:shadow script"
    assert "vite build" in shadow
    assert "--config vite.shadow.config.ts" in shadow


def test_no_generic_production_build_script() -> None:
    scripts = _load_package().get("scripts", {})
    assert "build" not in scripts, "package.json must not add a generic build script"


def test_tsconfig_includes_both_vite_configs() -> None:
    cfg = json.loads(TSCONFIG.read_text(encoding="utf-8"))
    include = cfg.get("include", [])
    assert "vite.config.ts" in include
    assert "vite.shadow.config.ts" in include


def test_justfile_has_shadow_recipes() -> None:
    text = JUSTFILE.read_text(encoding="utf-8")
    assert "build-ocean-rescue-shadow-bundle:" in text
    assert "check-ocean-rescue-shadow-bundle:" in text


def test_shadow_config_reads_canonical_manifest_and_template() -> None:
    text = SHADOW_CONFIG.read_text(encoding="utf-8")
    assert "build-manifest.json" in text
    assert "index.template.html" in text
    assert "OCEAN_RESCUE_SCRIPTS" in text


def test_shadow_config_uses_rolldown_options() -> None:
    text = SHADOW_CONFIG.read_text(encoding="utf-8")
    assert "rolldownOptions" in text, "shadow config must use build.rolldownOptions"


def test_shadow_config_does_not_import_pixi_package() -> None:
    text = SHADOW_CONFIG.read_text(encoding="utf-8")
    static_import = re.compile(r"\bimport\b[^\n]*?from\s+[\"']pixi\.js[\"']")
    dynamic_import = re.compile(r"\bimport\s*\([\"']pixi\.js[\"']\)")
    require_import = re.compile(r"\brequire\s*\([\"']pixi\.js[\"']\)")
    assert not static_import.search(text), "shadow config must not import pixi.js"
    assert not dynamic_import.search(text), "shadow config must not import pixi.js"
    assert not require_import.search(text), "shadow config must not import pixi.js"


def test_shadow_output_is_git_ignored() -> None:
    candidate = DIST_DIR / BUNDLE_FILE
    result = subprocess.run(
        ["git", "check-ignore", "-q", str(candidate)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"shadow output must be git-ignored: {candidate.relative_to(REPO_ROOT)}"
    )


def test_production_paths_outside_write_scope() -> None:
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", *PRODUCTION_PATHS],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "production source/artifact paths must remain unchanged:\n"
        + subprocess.run(
            ["git", "diff", "--", *PRODUCTION_PATHS],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        ).stdout
    )


# --- build contract ---


def test_clean_shadow_build_outputs_exact_file_set() -> None:
    _clean_shadow_build()
    files = {p.name for p in DIST_DIR.iterdir() if p.is_file()}
    assert files == SHADOW_FILES, f"expected {SHADOW_FILES}, found {files}"


def test_no_sourcemap_or_extra_chunk() -> None:
    _clean_shadow_build()
    files = {p.name for p in DIST_DIR.iterdir() if p.is_file()}
    assert files == SHADOW_FILES
    assert not any(name.endswith(".map") for name in files), "sourcemap emitted"


def test_shadow_metadata_is_valid_and_complete() -> None:
    _clean_shadow_build()
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
        "vendor",
        "application_script_count",
        "application_scripts",
        "expected_namespaces",
        "actual_module_files",
        "dynamic_import_count",
        "output_files",
    }
    assert required.issubset(metadata.keys()), (
        f"missing metadata keys: {required - set(metadata.keys())}"
    )
    assert metadata["schema_version"] == EXPECTED_SCHEMA_VERSION
    assert metadata["state"] == "SHADOW_BUNDLE"
    assert metadata["format"] == "iife"
    assert metadata["target"] == "baseline-widely-available"
    assert metadata["minifier"] == "oxc"
    assert metadata["sourcemap"] is False
    assert metadata["bundle_file"] == BUNDLE_FILE
    assert metadata["dynamic_import_count"] == 0
    raw = (DIST_DIR / METADATA_FILE).read_text(encoding="utf-8")
    assert raw.endswith("\n"), "metadata must end with a trailing newline"


def test_metadata_application_scripts_match_manifest_order() -> None:
    _clean_shadow_build()
    manifest = _load_manifest()
    expected = [entry["file"] for entry in _non_vendor_scripts(manifest)]
    assert len(expected) == EXPECTED_APP_COUNT
    metadata = json.loads((DIST_DIR / METADATA_FILE).read_text(encoding="utf-8"))
    assert metadata["application_scripts"] == expected
    assert metadata["application_script_count"] == EXPECTED_APP_COUNT


def test_metadata_vendor_boundary_external() -> None:
    _clean_shadow_build()
    metadata = json.loads((DIST_DIR / METADATA_FILE).read_text(encoding="utf-8"))
    vendor = metadata["vendor"]
    assert vendor["file"] == EXPECTED_VENDOR_FILE
    assert vendor["namespace"] == EXPECTED_VENDOR_NAMESPACE
    assert vendor["external"] is True


def test_metadata_actual_module_membership() -> None:
    _clean_shadow_build()
    metadata = json.loads((DIST_DIR / METADATA_FILE).read_text(encoding="utf-8"))
    assert metadata["actual_module_files"] == metadata["application_scripts"]
    assert metadata["expected_namespaces"] == [
        entry["namespace"] for entry in _non_vendor_scripts(_load_manifest())
    ]
    assert EXPECTED_VENDOR_FILE not in metadata["actual_module_files"]


def test_bundle_bytes_and_sha256_match_metadata() -> None:
    _clean_shadow_build()
    bundle = (DIST_DIR / BUNDLE_FILE).read_bytes()
    metadata = json.loads((DIST_DIR / METADATA_FILE).read_text(encoding="utf-8"))
    assert len(bundle) == metadata["bundle_bytes"]
    assert _sha256_bytes(bundle) == metadata["bundle_sha256"]


def test_bundle_is_nonempty_and_inspectable() -> None:
    _clean_shadow_build()
    text = (DIST_DIR / BUNDLE_FILE).read_text(encoding="utf-8")
    assert len(text) > 0, "bundle must not be empty"
    for entry in _non_vendor_scripts(_load_manifest()):
        assert f"OceanRescue.{entry['namespace'].split('.')[-1]}" in text, (
            f"bundle must reference namespace {entry['namespace']}"
        )
    assert not re.search(r"\bimport\b", text), "bundle must not contain import"
    assert not re.search(r"\bexport\b", text), "bundle must not contain export"
    assert "node_modules/pixi.js" not in text, "bundle must not embed the pixi package"


def test_bundle_sizes_recorded() -> None:
    _clean_shadow_build()
    bundle = (DIST_DIR / BUNDLE_FILE).read_bytes()
    gzipped = gzip.compress(bundle)
    assert len(bundle) > 0
    assert len(gzipped) > 0
    assert len(gzipped) < len(bundle)


# --- two-run determinism ---


def test_two_clean_shadow_builds_are_byte_identical(tmp_path: Path) -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    result_a = _run_shadow_build()
    assert result_a.returncode == 0, (
        f"shadow build A failed (exit {result_a.returncode}):\n{result_a.stderr}"
    )
    assert {p.name for p in DIST_DIR.iterdir() if p.is_file()} == SHADOW_FILES

    comparison = tmp_path / "build_a"
    comparison.mkdir()
    for path in DIST_DIR.iterdir():
        if path.is_file():
            shutil.copy2(path, comparison / path.name)

    result_b = _run_shadow_build()
    assert result_b.returncode == 0, (
        f"shadow build B failed (exit {result_b.returncode}):\n{result_b.stderr}"
    )
    files_a = sorted(p.name for p in comparison.iterdir() if p.is_file())
    files_b = sorted(p.name for p in DIST_DIR.iterdir() if p.is_file())
    assert files_a == files_b, f"relative file list differs: {files_a} vs {files_b}"
    for name in files_b:
        bytes_a = (comparison / name).read_bytes()
        bytes_b = (DIST_DIR / name).read_bytes()
        assert bytes_a == bytes_b, f"byte mismatch for {name}"
        assert _sha256_bytes(bytes_a) == _sha256_bytes(bytes_b), (
            f"sha256 mismatch for {name}"
        )


# --- shadow browser contract ---


class ShadowServerFixture:
    def __init__(self) -> None:
        self.server: socketserver.TCPServer | None = None
        self.thread: threading.Thread | None = None
        self.base_url = ""

    def start(self) -> str:
        class QuietHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(DOMAIN_DIR), **kwargs)

            def log_message(self, format: str, *args) -> None:
                return

        self.server = socketserver.TCPServer(("127.0.0.1", 0), QuietHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"
        return self.base_url

    def stop(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)

    def __enter__(self) -> "ShadowServerFixture":
        self.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()


def _shadow_document_evidence(page) -> dict:
    return page.evaluate(
        """() => {
          const srcs = Array.from(document.querySelectorAll('script[src]'))
            .map(s => s.getAttribute('src'));
          const moduleSrcs = Array.from(
            document.querySelectorAll('script[type="module"]')
          ).map(s => s.getAttribute('src'));
          return {
            script_srcs: srcs,
            module_script_srcs: moduleSrcs,
            has_pixi: typeof window.PIXI !== 'undefined',
            pixi_version: typeof window.PIXI === 'undefined' ? null : window.PIXI.VERSION,
            has_app: !!(window.OceanRescue && window.OceanRescue.App),
            has_render_assets: !!(window.OceanRescue && window.OceanRescue.RenderAssets),
            namespaces: window.OceanRescue ? Object.keys(window.OceanRescue) : []
          };
        }"""
    )


def test_shadow_browser_parity() -> None:
    _clean_shadow_build()
    with ShadowServerFixture() as server:
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
                        server.base_url,
                        {
                            "engine": "Playwright Chromium",
                            "version": browser.version,
                        },
                        entry_path="/dist/index.shadow.html",
                    )
                    doc = _shadow_document_evidence(page)
                finally:
                    page.close()
                    context.close()
            finally:
                browser.close()
    assert_evidence(evidence, network_mode="shadow")
    assert doc["script_srcs"] == [
        "/src/vendor/pixi-8.19.0.min.js",
        "/dist/ocean-rescue-app.shadow.js",
    ], "shadow document must load exactly vendor then bundle"
    assert doc["module_script_srcs"] == [], "no module scripts allowed"
    assert doc["has_pixi"] is True, "PIXI global must be present"
    assert doc["pixi_version"] == "8.19.0", "PIXI must be the pinned 8.19.0"
    assert doc["has_app"] is True, "OceanRescue.App must be present"
    assert doc["has_render_assets"] is True, "OceanRescue.RenderAssets must be present"
    for entry in _non_vendor_scripts(_load_manifest()):
        key = entry["namespace"].split(".")[-1]
        assert key in doc["namespaces"], (
            f"missing runtime namespace {entry['namespace']}"
        )
    script_requests = [
        r["url"]
        for r in evidence["network"]["all_requests"]
        if r["resource_type"] == "script"
    ]
    allowed_scripts = {
        f"{server.base_url}/src/vendor/pixi-8.19.0.min.js",
        f"{server.base_url}/dist/ocean-rescue-app.shadow.js",
    }
    assert set(script_requests) == allowed_scripts, (
        f"unexpected script requests: {script_requests}"
    )
    for request in evidence["network"]["all_requests"]:
        url = request["url"]
        assert "/@vite/" not in url, f"Vite dev client request detected: {url}"
        assert "/@fs/" not in url, f"Vite fs request detected: {url}"
        assert "/node_modules/.vite" not in url, f"dev dep request detected: {url}"
        if "/src/" in url and url.endswith(".js"):
            assert url.endswith("/src/vendor/pixi-8.19.0.min.js"), (
                f"individual source script request detected: {url}"
            )


# --- production immutability ---


def test_production_artifacts_unchanged_by_shadow_build() -> None:
    guarded = [
        ARTIFACT,
        MANIFEST,
        TEMPLATE,
        SRC_DIR / "render-assets.generated.js",
        SRC_DIR / "vendor" / "pixi-8.19.0.min.js",
    ]
    before = {path: _sha256_path(path) for path in guarded}
    _clean_shadow_build()
    after = {path: _sha256_path(path) for path in guarded}
    assert before == after, "shadow build must not modify production artifacts"
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", *PRODUCTION_PATHS],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "product path diff must be empty"


# --- migration documentation state ---


def test_migration_documentation_state() -> None:
    plan = PLAN_DOC.read_text(encoding="utf-8")
    evidence = PHASE3_EVIDENCE.read_text(encoding="utf-8")

    assert "WP-20: COMPLETE" in plan
    assert "WP-03: NOT_STARTED" in plan
    assert "Shadow bundle state: SHADOW_BUNDLE" in plan
    assert "Next executable work package: WP-03" in plan
    assert "WP-21 remains blocked until WP-03 completes" in plan

    assert f"Implementation base origin/main: `{WP20_IMPLEMENTATION_BASE}`" in evidence
    assert f"WP-20 implementation commit: `{WP20_IMPLEMENTATION_COMMIT}`" in evidence
    misleading = f"Final origin/main: {WP20_IMPLEMENTATION_BASE}"
    assert misleading not in evidence, (
        "evidence must not record the implementation base as Final origin/main"
    )
