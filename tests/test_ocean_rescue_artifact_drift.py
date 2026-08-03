import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
OCEAN_DIR = REPO_ROOT / "domains" / "ocean-rescue"
BUILDER = REPO_ROOT / "scripts" / "ocean_rescue" / "build_single_html.py"
MANIFEST = OCEAN_DIR / "src" / "build-manifest.json"
ARTIFACT = REPO_ROOT / "ocean-rescue" / "index.html"
DIST_DIR = OCEAN_DIR / "dist"
PROD_BUNDLE = DIST_DIR / "ocean-rescue-app.js"
PROD_METADATA = DIST_DIR / "production-bundle-metadata.json"


@pytest.fixture(scope="session", autouse=True)
def production_bundle():
    """Build the canonical Vite production bundle once per test session."""
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    result = subprocess.run(
        [
            "corepack",
            "pnpm",
            "exec",
            "vite",
            "build",
            "--config",
            "vite.production.config.ts",
        ],
        cwd=str(OCEAN_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Vite production build failed (exit {result.returncode}): {result.stderr}"
    )
    assert PROD_BUNDLE.exists(), f"Production bundle not found: {PROD_BUNDLE}"
    assert PROD_METADATA.exists(), f"Production metadata not found: {PROD_METADATA}"
    yield
    shutil.rmtree(DIST_DIR, ignore_errors=True)


def _build(output_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--mode",
            "production",
            "--manifest",
            str(MANIFEST),
            "--output",
            str(output_path),
            "--bundle",
            str(PROD_BUNDLE),
            "--metadata",
            str(PROD_METADATA),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_tracked_artifact_exists():
    assert ARTIFACT.exists(), f"Artifact not found: {ARTIFACT}"
    assert ARTIFACT.is_file(), f"Artifact is not a regular file: {ARTIFACT}"
    assert ARTIFACT.stat().st_size > 0, f"Artifact is empty: {ARTIFACT}"


def test_artifact_matches_clean_rebuild(tmp_path: Path):
    tmp_output = tmp_path / "rebuild.html"
    result = _build(tmp_output)
    assert result.returncode == 0, (
        f"Builder failed (exit {result.returncode}): {result.stderr}"
    )
    committed = ARTIFACT.read_bytes()
    rebuilt = tmp_output.read_bytes()
    assert committed == rebuilt, (
        f"Artifact mismatch: committed {len(committed)}b != rebuilt {len(rebuilt)}b"
    )


def test_independent_rebuilds_are_deterministic(tmp_path: Path):
    build_a = tmp_path / "build_a.html"
    build_b = tmp_path / "build_b.html"
    result_a = _build(build_a)
    assert result_a.returncode == 0, (
        f"First build failed (exit {result_a.returncode}): {result_a.stderr}"
    )
    result_b = _build(build_b)
    assert result_b.returncode == 0, (
        f"Second build failed (exit {result_b.returncode}): {result_b.stderr}"
    )
    content_a = build_a.read_bytes()
    content_b = build_b.read_bytes()
    assert content_a == content_b, (
        f"Non-deterministic: build_a {len(content_a)}b != build_b {len(content_b)}b"
    )


def test_artifact_standalone_contract():
    content = ARTIFACT.read_text(encoding="utf-8")

    assert content.startswith("<!doctype html>"), "Missing doctype"
    assert content.count("<main") == 1, "Expected exactly one <main>"
    assert content.count("<h1") == 1, "Expected exactly one <h1>"
    assert content.count("<canvas") == 1, "Expected exactly one <canvas>"
    assert 'width="1280"' in content, 'Expected width="1280"'
    assert 'height="720"' in content, 'Expected height="720"'

    script_tag_count = content.count("<script>")
    assert script_tag_count == 2, (
        f"Artifact has {script_tag_count} <script> tags; production must have 2 "
        "(vendored Pixi + application bundle)"
    )

    pixi_idx = content.index("PIXI")
    registry_idx = content.index("OceanRescue.RenderAssets")

    assert pixi_idx < registry_idx, "PIXI vendor must precede registry"

    expected_namespaces = [
        "OceanRescue.RenderAssets",
        "OceanRescue.RenderRuntime",
        "OceanRescue.State",
        "OceanRescue.Profile",
        "OceanRescue.Missions",
        "OceanRescue.Gups",
        "OceanRescue.Launch",
        "OceanRescue.Travel",
        "OceanRescue.Terrain",
        "OceanRescue.TravelScene",
        "OceanRescue.Rescue",
        "OceanRescue.SeaTurtle",
        "OceanRescue.SeaTurtleScene",
        "OceanRescue.Crab",
        "OceanRescue.CrabScene",
        "OceanRescue.YoungWhale",
        "OceanRescue.MissionSuccess",
        "OceanRescue.App",
    ]
    for ns in expected_namespaces:
        assert ns in content, f"missing application namespace {ns} in artifact"

    assert 'id="ocean-rescue-pause-button"' in content
    assert 'aria-label="Pause game"' in content
    assert 'id="ocean-rescue-pause-overlay"' in content
    assert 'id="ocean-rescue-pause-menu"' in content
    assert 'id="ocean-rescue-pause-title"' in content
    assert 'id="ocean-rescue-pause-resume"' in content
    assert 'id="ocean-rescue-pause-countdown"' in content
    assert 'id="ocean-rescue-pause-menu-button"' in content
    assert "Game Paused" in content
    assert "Back to Missions" in content
    assert "<!-- OCEAN_RESCUE_CSS -->" not in content
    assert "<!-- OCEAN_RESCUE_SCRIPTS -->" not in content
    assert "asset://" not in content
    assert "<script src=" not in content
    assert '<link rel="stylesheet" href=' not in content

    script_re = re.compile(r"<script>(.*?)</script>", re.IGNORECASE | re.DOTALL)
    all_scripts = script_re.findall(content)
    assert len(all_scripts) == 2, "Expected exactly two inline script blocks"

    app_bundle = all_scripts[1]
    assert re.compile(r"OceanRescue\.App\b").search(app_bundle), (
        "Application bundle must define the OceanRescue.App namespace"
    )
    assert "sourceMappingURL" not in app_bundle, (
        "Application bundle must not reference a source map"
    )

    app_kind_patterns = [
        (re.compile(r"\bfetch\s*\("), "fetch()"),
        (re.compile(r"\bXMLHttpRequest\b"), "XMLHttpRequest"),
        (re.compile(r"\bWebSocket\b"), "WebSocket"),
        (re.compile(r"\bEventSource\b"), "EventSource"),
    ]
    for pattern, desc in app_kind_patterns:
        assert not pattern.search(app_bundle), (
            f"Application bundle contains forbidden {desc}"
        )


def test_artifact_is_single_deployable_file(tmp_path: Path):
    artifact_dir = ARTIFACT.parent
    files = sorted(
        p.relative_to(artifact_dir) for p in artifact_dir.iterdir() if p.is_file()
    )
    assert files == [Path("index.html")], f"Expected only index.html, found: {files}"


def _button_text(content: str, button_id: str) -> str:
    match = re.search(
        r"<button[^>]*id=\"" + re.escape(button_id) + r"\"[^>]*>(.*?)</button>",
        content,
        re.DOTALL,
    )
    assert match is not None, f"Missing button with id {button_id}"
    return match.group(1).strip()


def test_artifact_completion_action_contract():
    content = ARTIFACT.read_text(encoding="utf-8")
    assert content.count("<script>") == 2, (
        "Production artifact must have exactly two inline script blocks"
    )
    assert _button_text(content, "ocean-rescue-mission-complete-continue") == "Continue"
    assert _button_text(content, "ocean-rescue-mission-complete-replay") == "Replay"
    assert 'id="ocean-rescue-mission-complete-unlock"' in content
    assert 'id="ocean-rescue-mission-complete-unlock-name"' in content
