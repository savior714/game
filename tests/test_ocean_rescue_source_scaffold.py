"""Tests for the Ocean Rescue production source scaffold."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = REPO_ROOT / "domains" / "ocean-rescue" / "src"
BUILDER = REPO_ROOT / "scripts" / "ocean_rescue" / "build_single_html.py"
MANIFEST = SOURCE_ROOT / "build-manifest.json"
TEMPLATE = SOURCE_ROOT / "index.template.html"
STYLE = SOURCE_ROOT / "style.css"
STATE_JS = SOURCE_ROOT / "state.js"
MISSIONS_JS = SOURCE_ROOT / "missions.js"
GUPS_JS = SOURCE_ROOT / "gups.js"
LAUNCH_JS = SOURCE_ROOT / "launch.js"
TRAVEL_JS = SOURCE_ROOT / "travel.js"
TERRAIN_JS = SOURCE_ROOT / "terrain.js"
RESCUE_JS = SOURCE_ROOT / "rescue.js"
SEA_TURTLE_JS = SOURCE_ROOT / "sea-turtle.js"
SEA_TURTLE_SCENE_JS = SOURCE_ROOT / "sea-turtle-scene.js"
CRAB_JS = SOURCE_ROOT / "crab.js"
YOUNG_WHALE_JS = SOURCE_ROOT / "young-whale.js"
MISSION_SUCCESS_JS = SOURCE_ROOT / "mission-success.js"
APP_JS = SOURCE_ROOT / "app.js"

CANONICAL_SOURCE_FILES = [
    "index.template.html",
    "build-manifest.json",
    "style.css",
    "render-assets.generated.js",
    "state.js",
    "missions.js",
    "gups.js",
    "launch.js",
    "travel.js",
    "terrain.js",
    "rescue.js",
    "sea-turtle.js",
    "sea-turtle-scene.js",
    "crab.js",
    "young-whale.js",
    "mission-success.js",
    "app.js",
]


def test_canonical_source_files_exist():
    for name in CANONICAL_SOURCE_FILES:
        assert (SOURCE_ROOT / name).is_file(), f"Missing source file: {name}"
    assert (SOURCE_ROOT / "vendor").is_dir(), "Missing vendor directory"


class TestManifest:
    def test_manifest_is_canonical(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        assert set(data.keys()) == {"template", "styles", "scripts", "assets"}
        assert data["template"] == "index.template.html"
        assert data["styles"] == ["style.css"]
        assert len(data["scripts"]) == 16

        assert data["scripts"][0]["file"] == "vendor/pixi-8.19.0.min.js"
        assert data["scripts"][0]["namespace"] == "PIXI"
        assert data["scripts"][0]["kind"] == "vendor"

        assert data["scripts"][1]["file"] == "render-assets.generated.js"
        assert data["scripts"][1]["namespace"] == "OceanRescue.RenderAssets"
        assert data["scripts"][1]["kind"] == "generated-assets"

        assert data["scripts"][2]["file"] == "render-runtime.js"
        assert data["scripts"][2]["namespace"] == "OceanRescue.RenderRuntime"
        assert data["scripts"][3]["file"] == "state.js"
        assert data["scripts"][3]["namespace"] == "OceanRescue.State"
        assert data["scripts"][3]["depends_on"] == []
        assert data["scripts"][4]["file"] == "missions.js"
        assert data["scripts"][4]["namespace"] == "OceanRescue.Missions"
        assert data["scripts"][4]["depends_on"] == []
        assert data["scripts"][5]["file"] == "gups.js"
        assert data["scripts"][5]["namespace"] == "OceanRescue.Gups"
        assert data["scripts"][5]["depends_on"] == []
        assert data["scripts"][6]["file"] == "launch.js"
        assert data["scripts"][6]["namespace"] == "OceanRescue.Launch"
        assert data["scripts"][6]["depends_on"] == []
        assert data["scripts"][7]["file"] == "travel.js"
        assert data["scripts"][7]["namespace"] == "OceanRescue.Travel"
        assert data["scripts"][7]["depends_on"] == []
        assert data["scripts"][8]["file"] == "terrain.js"
        assert data["scripts"][8]["namespace"] == "OceanRescue.Terrain"
        assert data["scripts"][8]["depends_on"] == []
        assert data["scripts"][9]["file"] == "rescue.js"
        assert data["scripts"][9]["namespace"] == "OceanRescue.Rescue"
        assert data["scripts"][9]["depends_on"] == []
        assert data["scripts"][10]["file"] == "sea-turtle.js"
        assert data["scripts"][10]["namespace"] == "OceanRescue.SeaTurtle"
        assert data["scripts"][10]["depends_on"] == []
        assert data["scripts"][11]["file"] == "sea-turtle-scene.js"
        assert data["scripts"][11]["namespace"] == "OceanRescue.SeaTurtleScene"
        assert data["scripts"][11]["depends_on"] == [
            "OceanRescue.RenderRuntime",
            "OceanRescue.SeaTurtle",
        ]
        assert data["scripts"][12]["file"] == "crab.js"
        assert data["scripts"][12]["namespace"] == "OceanRescue.Crab"
        assert data["scripts"][12]["depends_on"] == []
        assert data["scripts"][13]["file"] == "young-whale.js"
        assert data["scripts"][13]["namespace"] == "OceanRescue.YoungWhale"
        assert data["scripts"][13]["depends_on"] == []
        assert data["scripts"][14]["file"] == "mission-success.js"
        assert data["scripts"][14]["namespace"] == "OceanRescue.MissionSuccess"
        assert data["scripts"][14]["depends_on"] == []
        assert data["scripts"][15]["file"] == "app.js"
        assert data["scripts"][15]["namespace"] == "OceanRescue.App"
        assert data["scripts"][15]["depends_on"] == [
            "OceanRescue.State",
            "OceanRescue.RenderRuntime",
            "OceanRescue.Missions",
            "OceanRescue.Gups",
            "OceanRescue.Launch",
            "OceanRescue.Travel",
            "OceanRescue.Terrain",
            "OceanRescue.Rescue",
            "OceanRescue.SeaTurtle",
            "OceanRescue.SeaTurtleScene",
            "OceanRescue.Crab",
            "OceanRescue.YoungWhale",
            "OceanRescue.MissionSuccess",
        ]
        assert data["assets"] == []


class TestTemplate:
    def test_template_semantic_contract(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        assert content.strip().lower().startswith("<!doctype html")
        assert 'lang="en"' in content
        assert content.count("<main") == 1
        assert content.count("<h1") == 1
        assert content.count("<canvas") == 1
        assert 'width="1280"' in content
        assert 'height="720"' in content
        assert content.count("<!-- OCEAN_RESCUE_CSS -->") == 1
        assert content.count("<!-- OCEAN_RESCUE_SCRIPTS -->") == 1
        assert 'role="application"' not in content
        assert "<script src=" not in content.lower()
        assert '<link rel="stylesheet"' not in content.lower()


class TestJavaScript:
    def test_state_defines_namespace(self):
        content = STATE_JS.read_text(encoding="utf-8")
        assert "window.OceanRescue" in content
        assert "root.State" in content or "OceanRescue.State" in content

    def test_missions_defines_namespace(self):
        content = MISSIONS_JS.read_text(encoding="utf-8")
        assert "window.OceanRescue" in content
        assert "root.Missions" in content or "OceanRescue.Missions" in content

    def test_gups_defines_namespace(self):
        content = GUPS_JS.read_text(encoding="utf-8")
        assert "window.OceanRescue" in content
        assert "root.Gups" in content or "OceanRescue.Gups" in content

    def test_launch_defines_namespace(self):
        content = LAUNCH_JS.read_text(encoding="utf-8")
        assert "window.OceanRescue" in content
        assert "root.Launch" in content or "OceanRescue.Launch" in content

    def test_travel_defines_namespace(self):
        content = TRAVEL_JS.read_text(encoding="utf-8")
        assert "window.OceanRescue" in content
        assert "root.Travel" in content or "OceanRescue.Travel" in content

    def test_terrain_defines_namespace(self):
        content = TERRAIN_JS.read_text(encoding="utf-8")
        assert "window.OceanRescue" in content
        assert "root.Terrain" in content or "OceanRescue.Terrain" in content

    def test_rescue_defines_namespace(self):
        content = RESCUE_JS.read_text(encoding="utf-8")
        assert "window.OceanRescue" in content
        assert "root.Rescue" in content or "OceanRescue.Rescue" in content

    def test_sea_turtle_defines_namespace(self):
        content = SEA_TURTLE_JS.read_text(encoding="utf-8")
        assert "window.OceanRescue" in content
        assert "root.SeaTurtle" in content or "OceanRescue.SeaTurtle" in content

    def test_sea_turtle_scene_defines_namespace(self):
        content = SEA_TURTLE_SCENE_JS.read_text(encoding="utf-8")
        assert "window.OceanRescue" in content
        assert "root.SeaTurtleScene" in content

    def test_crab_defines_namespace(self):
        content = CRAB_JS.read_text(encoding="utf-8")
        assert "window.OceanRescue" in content
        assert "root.Crab" in content or "OceanRescue.Crab" in content

    def test_young_whale_defines_namespace(self):
        content = YOUNG_WHALE_JS.read_text(encoding="utf-8")
        assert "window.OceanRescue" in content
        assert "root.YoungWhale" in content or "OceanRescue.YoungWhale" in content

    def test_mission_success_defines_namespace(self):
        content = MISSION_SUCCESS_JS.read_text(encoding="utf-8")
        assert "window.OceanRescue" in content
        assert (
            "root.MissionSuccess" in content or "OceanRescue.MissionSuccess" in content
        )

    def test_app_defines_namespace_and_references_state(self):
        content = APP_JS.read_text(encoding="utf-8")
        assert "OceanRescue.App" in content
        assert "OceanRescue.State" in content
        assert "OceanRescue.Missions" in content
        assert "OceanRescue.Gups" in content

    @pytest.mark.parametrize(
        "path,forbidden",
        [
            (
                STATE_JS,
                [
                    "import",
                    "export",
                    "fetch(",
                    "XMLHttpRequest",
                    "WebSocket",
                    "EventSource",
                ],
            ),
            (
                MISSIONS_JS,
                [
                    "import",
                    "export",
                    "fetch(",
                    "XMLHttpRequest",
                    "WebSocket",
                    "EventSource",
                ],
            ),
            (
                GUPS_JS,
                [
                    "import",
                    "export",
                    "fetch(",
                    "XMLHttpRequest",
                    "WebSocket",
                    "EventSource",
                ],
            ),
            (
                LAUNCH_JS,
                [
                    "import",
                    "export",
                    "fetch(",
                    "XMLHttpRequest",
                    "WebSocket",
                    "EventSource",
                ],
            ),
            (
                TRAVEL_JS,
                [
                    "import",
                    "export",
                    "fetch(",
                    "XMLHttpRequest",
                    "WebSocket",
                    "EventSource",
                ],
            ),
            (
                TERRAIN_JS,
                [
                    "import",
                    "export",
                    "fetch(",
                    "XMLHttpRequest",
                    "WebSocket",
                    "EventSource",
                ],
            ),
            (
                RESCUE_JS,
                [
                    "import",
                    "export",
                    "fetch(",
                    "XMLHttpRequest",
                    "WebSocket",
                    "EventSource",
                ],
            ),
            (
                SEA_TURTLE_JS,
                [
                    "import",
                    "export",
                    "fetch(",
                    "XMLHttpRequest",
                    "WebSocket",
                    "EventSource",
                ],
            ),
            (
                SEA_TURTLE_SCENE_JS,
                [
                    "import",
                    "export",
                    "fetch(",
                    "XMLHttpRequest",
                    "WebSocket",
                    "EventSource",
                ],
            ),
            (
                CRAB_JS,
                [
                    "import",
                    "export",
                    "fetch(",
                    "XMLHttpRequest",
                    "WebSocket",
                    "EventSource",
                ],
            ),
            (
                YOUNG_WHALE_JS,
                [
                    "import",
                    "export",
                    "fetch(",
                    "XMLHttpRequest",
                    "WebSocket",
                    "EventSource",
                ],
            ),
            (
                MISSION_SUCCESS_JS,
                [
                    "import",
                    "export",
                    "fetch(",
                    "XMLHttpRequest",
                    "WebSocket",
                    "EventSource",
                ],
            ),
            (
                APP_JS,
                [
                    "import",
                    "export",
                    "fetch(",
                    "XMLHttpRequest",
                    "WebSocket",
                    "EventSource",
                ],
            ),
        ],
    )
    def test_forbidden_tokens_absent(self, path, forbidden):
        content = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in content, f"{path.name} contains {token}"

    @pytest.mark.parametrize(
        "path",
        [
            STATE_JS,
            MISSIONS_JS,
            GUPS_JS,
            LAUNCH_JS,
            TRAVEL_JS,
            TERRAIN_JS,
            RESCUE_JS,
            SEA_TURTLE_JS,
            SEA_TURTLE_SCENE_JS,
            CRAB_JS,
            YOUNG_WHALE_JS,
            MISSION_SUCCESS_JS,
            APP_JS,
        ],
    )
    def test_no_asset_sentinel(self, path):
        content = path.read_text(encoding="utf-8")
        assert "asset://" not in content


class TestBuild:
    def test_production_source_builds_to_temporary_output(self, tmp_path):
        output = tmp_path / "ocean-rescue.html"
        result = subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--manifest",
                str(MANIFEST),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output.is_file(), "Build output not created"
        assert output.stat().st_size > 0, "Build output is empty"

        html = output.read_text(encoding="utf-8")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        script_count = len(manifest["scripts"])

        assert "<!-- OCEAN_RESCUE_CSS -->" not in html
        assert "<!-- OCEAN_RESCUE_SCRIPTS -->" not in html
        assert html.count("<script") == script_count
        assert "asset://" not in html
        state_pos = html.index("OceanRescue.State")
        missions_pos = html.index("OceanRescue.Missions")
        gups_pos = html.index("OceanRescue.Gups")
        launch_pos = html.index("OceanRescue.Launch")
        travel_pos = html.index("OceanRescue.Travel")
        terrain_pos = html.index("OceanRescue.Terrain")
        rescue_pos = html.index("OceanRescue.Rescue")
        sea_turtle_pos = html.index("OceanRescue.SeaTurtle")
        sea_turtle_scene_pos = html.index("OceanRescue.SeaTurtleScene")
        crab_pos = html.index("OceanRescue.Crab")
        young_whale_pos = html.index("OceanRescue.YoungWhale")
        mission_success_pos = html.index("OceanRescue.MissionSuccess")
        app_pos = html.index("OceanRescue.App")
        assert state_pos < missions_pos, (
            "State script must appear before Missions script"
        )
        assert missions_pos < gups_pos, "Missions script must appear before Gups script"
        assert gups_pos < launch_pos, "Gups script must appear before Launch script"
        assert launch_pos < travel_pos, "Launch script must appear before Travel script"
        assert travel_pos < terrain_pos, (
            "Travel script must appear before Terrain script"
        )
        assert terrain_pos < rescue_pos, (
            "Terrain script must appear before Rescue script"
        )
        assert rescue_pos < sea_turtle_pos, (
            "Rescue script must appear before SeaTurtle script"
        )
        assert sea_turtle_pos < sea_turtle_scene_pos, (
            "SeaTurtle script must appear before SeaTurtleScene script"
        )
        assert sea_turtle_scene_pos < crab_pos, (
            "SeaTurtleScene script must appear before Crab script"
        )
        assert crab_pos < young_whale_pos, (
            "Crab script must appear before YoungWhale script"
        )
        assert young_whale_pos < mission_success_pos, (
            "YoungWhale script must appear before MissionSuccess script"
        )
        assert mission_success_pos < app_pos, (
            "MissionSuccess script must appear before App script"
        )
        ext_src = "<script src="
        assert ext_src not in html.lower()
        ext_link = '<link rel="stylesheet"'
        assert ext_link not in html.lower()

    def test_production_source_build_is_deterministic(self, tmp_path):
        out1 = tmp_path / "build1.html"
        out2 = tmp_path / "build2.html"
        subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--manifest",
                str(MANIFEST),
                "--output",
                str(out1),
            ],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--manifest",
                str(MANIFEST),
                "--output",
                str(out2),
            ],
            capture_output=True,
            check=True,
        )
        assert out1.read_bytes() == out2.read_bytes()
