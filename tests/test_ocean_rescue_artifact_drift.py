import json
import re
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


def _load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


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
    manifest = _load_manifest()
    script_count = len(manifest["scripts"])

    assert content.startswith("<!doctype html>"), "Missing doctype"
    assert content.count("<main") == 1, "Expected exactly one <main>"
    assert content.count("<h1") == 1, "Expected exactly one <h1>"
    assert content.count("<canvas") == 1, "Expected exactly one <canvas>"
    assert 'width="1280"' in content, 'Expected width="1280"'
    assert 'height="720"' in content, 'Expected height="720"'

    script_tag_count = content.count("<script>")
    assert script_tag_count == script_count, (
        f"Artifact has {script_tag_count} <script> tags, manifest has {script_count}"
    )

    pixi_idx = content.index("PIXI")
    registry_idx = content.index("OceanRescue.RenderAssets")
    state_idx = content.index("OceanRescue.State")
    app_idx = content.index("OceanRescue.App")

    assert pixi_idx < registry_idx, "PIXI vendor must precede registry"
    assert registry_idx < state_idx, "Registry must precede app scripts"
    assert state_idx < app_idx, "State must precede App"

    missions_idx = content.index("OceanRescue.Missions")
    gups_idx = content.index("OceanRescue.Gups")
    launch_idx = content.index("OceanRescue.Launch")
    travel_idx = content.index("OceanRescue.Travel")
    terrain_idx = content.index("OceanRescue.Terrain")
    rescue_idx = content.index("OceanRescue.Rescue")
    sea_turtle_idx = content.index("OceanRescue.SeaTurtle")
    sea_turtle_scene_idx = content.index("OceanRescue.SeaTurtleScene")
    crab_idx = content.index("OceanRescue.Crab")
    young_whale_idx = content.index("OceanRescue.YoungWhale")
    mission_success_idx = content.index("OceanRescue.MissionSuccess")

    assert missions_idx < gups_idx, "Missions content must precede Gups content"
    assert gups_idx < launch_idx, "Gups content must precede Launch content"
    assert launch_idx < travel_idx, "Launch content must precede Travel content"
    assert travel_idx < terrain_idx, "Travel content must precede Terrain content"
    assert terrain_idx < rescue_idx, "Terrain content must precede Rescue content"
    assert rescue_idx < sea_turtle_idx, "Rescue content must precede SeaTurtle content"
    assert sea_turtle_idx < sea_turtle_scene_idx, (
        "SeaTurtle content must precede SeaTurtleScene content"
    )
    assert sea_turtle_scene_idx < crab_idx, (
        "SeaTurtleScene content must precede Crab content"
    )
    assert crab_idx < young_whale_idx, "Crab content must precede YoungWhale content"
    assert young_whale_idx < mission_success_idx, (
        "YoungWhale content must precede MissionSuccess content"
    )
    assert mission_success_idx < app_idx, (
        "MissionSuccess content must precede App content"
    )

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

    app_kind_patterns = [
        (re.compile(r"\bfetch\s*\("), "fetch()"),
        (re.compile(r"\bXMLHttpRequest\b"), "XMLHttpRequest"),
        (re.compile(r"\bWebSocket\b"), "WebSocket"),
        (re.compile(r"\bEventSource\b"), "EventSource"),
    ]

    for i, entry in enumerate(manifest["scripts"]):
        kind = entry.get("kind", "app")
        if kind == "app" and i < len(all_scripts):
            for pattern, desc in app_kind_patterns:
                assert not pattern.search(all_scripts[i]), (
                    f"App script '{entry['namespace']}' contains forbidden {desc}"
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
    manifest = _load_manifest()
    script_count = len(manifest["scripts"])
    assert content.count("<script>") == script_count
    assert _button_text(content, "ocean-rescue-mission-complete-continue") == "Continue"
    assert _button_text(content, "ocean-rescue-mission-complete-replay") == "Replay"
    assert 'id="ocean-rescue-mission-complete-unlock"' in content
    assert 'id="ocean-rescue-mission-complete-unlock-name"' in content
