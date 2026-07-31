import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER = REPO_ROOT / "scripts" / "ocean_rescue" / "build_single_html.py"
MANIFEST = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "build-manifest.json"
ARTIFACT = REPO_ROOT / "ocean-rescue" / "index.html"

BUILDER_ARGS = [
    sys.executable,
    str(BUILDER),
    "--manifest",
    str(MANIFEST),
    "--output",
]


def _build(output_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [*BUILDER_ARGS, str(output_path)],
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
    assert content.count("<style>") == 1, "Expected exactly one <style>"
    assert content.count("<script>") == 7, "Expected exactly seven <script>"
    state_idx = content.index("OceanRescue.State")
    missions_idx = content.index("OceanRescue.Missions")
    gups_idx = content.index("OceanRescue.Gups")
    launch_idx = content.index("OceanRescue.Launch")
    travel_idx = content.index("OceanRescue.Travel")
    terrain_idx = content.index("OceanRescue.Terrain")
    app_idx = content.index("OceanRescue.App")
    assert state_idx < missions_idx, "State content must precede Missions content"
    assert missions_idx < gups_idx, "Missions content must precede Gups content"
    assert gups_idx < launch_idx, "Gups content must precede Launch content"
    assert launch_idx < travel_idx, "Launch content must precede Travel content"
    assert travel_idx < terrain_idx, "Travel content must precede Terrain content"
    assert terrain_idx < app_idx, "Terrain content must precede App content"
    assert "<!-- OCEAN_RESCUE_CSS -->" not in content
    assert "<!-- OCEAN_RESCUE_SCRIPTS -->" not in content
    assert "asset://" not in content
    assert "<script src=" not in content
    assert '<link rel="stylesheet" href=' not in content
    external_urls = ["fetch(", "XMLHttpRequest", "WebSocket", "EventSource"]
    for token in external_urls:
        assert token not in content, f"Found forbidden token: {token}"


def test_artifact_is_single_deployable_file(tmp_path: Path):
    artifact_dir = ARTIFACT.parent
    files = sorted(
        p.relative_to(artifact_dir) for p in artifact_dir.iterdir() if p.is_file()
    )
    assert files == [Path("index.html")], f"Expected only index.html, found: {files}"
