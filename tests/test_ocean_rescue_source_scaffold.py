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
APP_JS = SOURCE_ROOT / "app.js"

CANONICAL_SOURCE_FILES = [
    "index.template.html",
    "build-manifest.json",
    "style.css",
    "state.js",
    "app.js",
]


def test_canonical_source_files_exist():
    for name in CANONICAL_SOURCE_FILES:
        assert (SOURCE_ROOT / name).is_file(), f"Missing source file: {name}"
    assert len(list(SOURCE_ROOT.iterdir())) == len(CANONICAL_SOURCE_FILES)


class TestManifest:
    def test_manifest_is_canonical(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        assert set(data.keys()) == {"template", "styles", "scripts", "assets"}
        assert data["template"] == "index.template.html"
        assert data["styles"] == ["style.css"]
        assert len(data["scripts"]) == 2
        assert data["scripts"][0]["file"] == "state.js"
        assert data["scripts"][0]["namespace"] == "OceanRescue.State"
        assert data["scripts"][0]["depends_on"] == []
        assert data["scripts"][1]["file"] == "app.js"
        assert data["scripts"][1]["namespace"] == "OceanRescue.App"
        assert data["scripts"][1]["depends_on"] == ["OceanRescue.State"]
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
        assert '<script src=' not in content.lower()
        assert '<link rel="stylesheet"' not in content.lower()


class TestJavaScript:
    def test_state_defines_namespace(self):
        content = STATE_JS.read_text(encoding="utf-8")
        assert "window.OceanRescue" in content
        assert "root.State" in content or "OceanRescue.State" in content

    def test_app_defines_namespace_and_references_state(self):
        content = APP_JS.read_text(encoding="utf-8")
        assert "OceanRescue.App" in content
        assert "OceanRescue.State" in content

    @pytest.mark.parametrize(
        "path,forbidden",
        [
            (STATE_JS, ["import", "export", "fetch(", "XMLHttpRequest", "WebSocket", "EventSource"]),
            (APP_JS, ["import", "export", "fetch(", "XMLHttpRequest", "WebSocket", "EventSource"]),
        ],
    )
    def test_forbidden_tokens_absent(self, path, forbidden):
        content = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in content, f"{path.name} contains {token}"

    @pytest.mark.parametrize("path", [STATE_JS, APP_JS])
    def test_no_asset_sentinel(self, path):
        content = path.read_text(encoding="utf-8")
        assert "asset://" not in content


class TestBuild:
    def test_production_source_builds_to_temporary_output(self, tmp_path):
        output = tmp_path / "ocean-rescue.html"
        result = subprocess.run(
            [sys.executable, str(BUILDER), "--manifest", str(MANIFEST), "--output", str(output)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"
        assert output.is_file(), "Build output not created"
        assert output.stat().st_size > 0, "Build output is empty"

        html = output.read_text(encoding="utf-8")
        assert "<!-- OCEAN_RESCUE_CSS -->" not in html
        assert "<!-- OCEAN_RESCUE_SCRIPTS -->" not in html
        assert html.count("<style") == 1
        assert html.count("<script") == 2
        assert "asset://" not in html
        state_pos = html.index("OceanRescue.State")
        app_pos = html.index("OceanRescue.App")
        assert state_pos < app_pos, "State script must appear before App script"
        ext_src = '<script src='
        assert ext_src not in html.lower()
        ext_link = '<link rel="stylesheet"'
        assert ext_link not in html.lower()

    def test_production_source_build_is_deterministic(self, tmp_path):
        out1 = tmp_path / "build1.html"
        out2 = tmp_path / "build2.html"
        subprocess.run(
            [sys.executable, str(BUILDER), "--manifest", str(MANIFEST), "--output", str(out1)],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [sys.executable, str(BUILDER), "--manifest", str(MANIFEST), "--output", str(out2)],
            capture_output=True,
            check=True,
        )
        assert out1.read_bytes() == out2.read_bytes()
