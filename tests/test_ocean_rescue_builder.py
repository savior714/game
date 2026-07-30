import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.ocean_rescue.build_single_html import (
    BuildError,
    MARKER_CSS,
    MARKER_SCRIPTS,
    build,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "ocean_rescue_builder"
BASIC_FIXTURE = FIXTURE_DIR / "basic"


def build_cli(manifest, output):
    """Run the builder CLI and return CompletedProcess."""
    return subprocess.run(
        [
            sys.executable,
            str(
                Path(__file__).parent.parent
                / "scripts"
                / "ocean_rescue"
                / "build_single_html.py"
            ),
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )


def write_svg(path, content=None):
    """Write a minimal SVG file."""
    if content is None:
        content = (
            '<svg xmlns="http://www.w3.org/2000/svg"'
            ' width="1" height="1">'
            '<rect width="1" height="1" fill="red"/>'
            "</svg>"
        )
    path.write_text(content)
    return path


def write_text(path, content):
    """Write text content to a file."""
    path.write_text(content)
    return path


def basic_manifest(tmp_path, overrides=None):
    """Create a minimal valid build fixture in tmp_path."""
    src = tmp_path / "src"
    src.mkdir()
    assets = src / "assets"
    assets.mkdir()

    write_svg(assets / "logo.svg")
    write_svg(assets / "bg.svg")

    write_text(
        src / "template.html",
        "<!doctype html>\n<html>\n<head>\n"
        "<!-- OCEAN_RESCUE_CSS -->\n"
        "</head>\n<body>\n"
        '<img src="asset://logo">\n'
        "<!-- OCEAN_RESCUE_SCRIPTS -->\n"
        "</body>\n</html>\n",
    )
    write_text(
        src / "style.css",
        'body { background: url("asset://bg"); }\n',
    )
    write_text(
        src / "state.js",
        "var NS = NS || {}; NS.x = 1;\n",
    )
    write_text(
        src / "game.js",
        "(function(){ NS.x = 2; })();\n",
    )

    manifest = {
        "template": "template.html",
        "styles": ["style.css"],
        "scripts": [
            {
                "file": "state.js",
                "namespace": "App.State",
                "depends_on": [],
            },
            {
                "file": "game.js",
                "namespace": "App.Game",
                "depends_on": ["App.State"],
            },
        ],
        "assets": [
            {"id": "logo", "file": "assets/logo.svg", "mime": "image/svg+xml"},
            {"id": "bg", "file": "assets/bg.svg", "mime": "image/svg+xml"},
        ],
    }
    if overrides:
        manifest.update(overrides)

    write_text(src / "manifest.json", json.dumps(manifest))
    return src / "manifest.json"


# ---- Success behavior ----


class TestSuccessBehavior:
    def test_minimal_build(self, tmp_path):
        manifest_path = BASIC_FIXTURE / "manifest.json"
        output_path = tmp_path / "output" / "index.html"
        assert manifest_path.exists()

        build(manifest_path, output_path)

        assert output_path.exists()
        html = output_path.read_text(encoding="utf-8")

        assert "<!doctype html>" in html.lower() or html.strip().lower().startswith(
            "<!doctype html"
        )
        assert "<style>" in html
        assert "</style>" in html
        assert MARKER_CSS not in html
        assert MARKER_SCRIPTS not in html
        assert html.count("<script>") == 2
        assert "</script>" in html
        assert "data:image/svg+xml;base64," in html
        assert "asset://" not in html

        state_index = html.index("OceanRescue.State")
        game_index = html.index("OceanRescue.Game")
        assert state_index < game_index

    def test_byte_identical_rebuild(self, tmp_path):
        manifest_path = BASIC_FIXTURE / "manifest.json"
        out1 = tmp_path / "a.html"
        out2 = tmp_path / "b.html"

        build(manifest_path, out1)
        build(manifest_path, out2)

        assert out1.read_bytes() == out2.read_bytes()

    def test_output_parent_creation(self, tmp_path):
        manifest_path = BASIC_FIXTURE / "manifest.json"
        output_path = tmp_path / "new" / "deep" / "dir" / "index.html"

        build(manifest_path, output_path)

        assert output_path.exists()

    def test_atomic_replacement(self, tmp_path):
        manifest_path, output_path = _atomic_replace_setup(tmp_path, None)
        build(manifest_path, output_path)
        first_content = output_path.read_bytes()

        try:
            build(manifest_path, output_path)
        except BuildError:
            pass
        assert output_path.read_bytes() == first_content


def _atomic_replace_setup(tmp_path, manifest_overrides):
    src = tmp_path / "src"
    src.mkdir()
    assets = src / "assets"
    assets.mkdir()
    write_svg(assets / "a.svg")
    write_text(
        src / "style.css",
        'body { background: url("asset://a"); }\n',
    )
    write_text(
        src / "template.html",
        "<!doctype html>\n<!-- OCEAN_RESCUE_CSS -->\n<!-- OCEAN_RESCUE_SCRIPTS -->\n",
    )
    write_text(
        src / "script.js",
        "var x = 1;\n",
    )
    manifest_data = {
        "template": "template.html",
        "styles": ["style.css"],
        "scripts": [
            {"file": "script.js", "namespace": "App", "depends_on": []},
        ],
        "assets": [
            {"id": "a", "file": "assets/a.svg", "mime": "image/svg+xml"},
        ],
    }
    if manifest_overrides:
        manifest_data.update(manifest_overrides)
    write_text(src / "manifest.json", json.dumps(manifest_data))
    return src / "manifest.json", tmp_path / "out" / "index.html"


# ---- Marker failures ----


class TestMarkerFailures:
    def _make_template_fixture(self, tmp_path, template_content):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            template_content,
        )
        write_text(src / "style.css", "body {}\n")
        write_text(src / "script.js", "var x = 1;\n")
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "script.js", "namespace": "App", "depends_on": []},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        return src / "manifest.json"

    def test_missing_css_marker(self, tmp_path):
        tpl = "<!doctype html>\n<!-- OCEAN_RESCUE_SCRIPTS -->\n"
        mp = self._make_template_fixture(tmp_path, tpl)
        with pytest.raises(BuildError, match="Missing CSS marker"):
            build(mp, tmp_path / "out.html")

    def test_duplicate_css_marker(self, tmp_path):
        tpl = (
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n"
        )
        mp = self._make_template_fixture(tmp_path, tpl)
        with pytest.raises(BuildError, match="Duplicate CSS marker"):
            build(mp, tmp_path / "out.html")

    def test_missing_script_marker(self, tmp_path):
        tpl = "<!doctype html>\n<!-- OCEAN_RESCUE_CSS -->\n"
        mp = self._make_template_fixture(tmp_path, tpl)
        with pytest.raises(BuildError, match="Missing script marker"):
            build(mp, tmp_path / "out.html")

    def test_duplicate_script_marker(self, tmp_path):
        tpl = (
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n"
        )
        mp = self._make_template_fixture(tmp_path, tpl)
        with pytest.raises(BuildError, match="Duplicate script marker"):
            build(mp, tmp_path / "out.html")


# ---- JavaScript forbidden patterns ----


class TestJavaScriptForbidden:
    def _make_js_fixture(self, tmp_path, js_content):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", "body {}\n")
        write_text(src / "bad.js", js_content)
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "bad.js", "namespace": "App", "depends_on": []},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        return src / "manifest.json"

    def test_static_import(self, tmp_path):
        mp = self._make_js_fixture(tmp_path, 'import { foo } from "./bar.js";\n')
        with pytest.raises(BuildError, match="static import"):
            build(mp, tmp_path / "out.html")

    def test_export_declaration(self, tmp_path):
        mp = self._make_js_fixture(tmp_path, "export const x = 1;\n")
        with pytest.raises(BuildError, match="export declaration"):
            build(mp, tmp_path / "out.html")

    def test_dynamic_import_source(self, tmp_path):
        mp = self._make_js_fixture(
            tmp_path, 'import("./foo.js").then(m => m.default);\n'
        )
        with pytest.raises(BuildError, match="dynamic import"):
            build(mp, tmp_path / "out.html")


# ---- Inline script safety ----


class TestInlineScriptSafety:
    def _make_safety_fixture(self, tmp_path, js_content):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", "body {}\n")
        write_text(src / "bad.js", js_content)
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "bad.js", "namespace": "App", "depends_on": []},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        return src / "manifest.json"

    def test_raw_close_script(self, tmp_path):
        mp = self._make_safety_fixture(tmp_path, 'var x = "</script>";\n')
        with pytest.raises(BuildError, match="</script"):
            build(mp, tmp_path / "out.html")

    def test_raw_open_script(self, tmp_path):
        mp = self._make_safety_fixture(tmp_path, "if (x < 3) {} var s = '<script>';\n")
        with pytest.raises(BuildError, match="<script"):
            build(mp, tmp_path / "out.html")

    def test_raw_html_comment(self, tmp_path):
        mp = self._make_safety_fixture(tmp_path, "// <!-- comment in js\n")
        with pytest.raises(BuildError, match="<!--"):
            build(mp, tmp_path / "out.html")


# ---- Script dependency and namespace ----


class TestScriptDependencies:
    def _make_dep_fixture(self, tmp_path, scripts):
        src = tmp_path / "src"
        src.mkdir(exist_ok=True)
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", "body {}\n")
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": scripts,
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        return src / "manifest.json"

    def test_duplicate_namespace(self, tmp_path):
        scripts = [
            {"file": "a.js", "namespace": "App.Dup", "depends_on": []},
            {"file": "b.js", "namespace": "App.Dup", "depends_on": []},
        ]
        src = tmp_path / "src"
        src.mkdir()
        write_text(src / "a.js", "var x = 1;\n")
        write_text(src / "b.js", "var y = 2;\n")
        mp = self._make_dep_fixture(tmp_path, scripts)
        with pytest.raises(BuildError, match="Duplicate namespace"):
            build(mp, tmp_path / "out.html")

    def test_missing_dependency(self, tmp_path):
        scripts = [
            {
                "file": "a.js",
                "namespace": "App.A",
                "depends_on": ["App.Nonexistent"],
            },
        ]
        src = tmp_path / "src"
        src.mkdir()
        write_text(src / "a.js", "var x = 1;\n")
        mp = self._make_dep_fixture(tmp_path, scripts)
        with pytest.raises(BuildError, match="unknown namespace"):
            build(mp, tmp_path / "out.html")

    def test_forward_dependency(self, tmp_path):
        scripts = [
            {
                "file": "a.js",
                "namespace": "App.A",
                "depends_on": ["App.B"],
            },
            {
                "file": "b.js",
                "namespace": "App.B",
                "depends_on": [],
            },
        ]
        src = tmp_path / "src"
        src.mkdir()
        write_text(src / "a.js", "var x = 1;\n")
        write_text(src / "b.js", "var y = 2;\n")
        mp = self._make_dep_fixture(tmp_path, scripts)
        with pytest.raises(BuildError, match="Forward dependency"):
            build(mp, tmp_path / "out.html")


# ---- Asset failures ----


class TestAssetFailures:
    def test_duplicate_asset_id(self, tmp_path):
        mp, _ = _atomic_replace_setup(
            tmp_path,
            {
                "assets": [
                    {"id": "a", "file": "assets/a.svg", "mime": "image/svg+xml"},
                    {"id": "a", "file": "assets/a.svg", "mime": "image/svg+xml"},
                ],
            },
        )
        with pytest.raises(BuildError, match="Duplicate asset ID"):
            build(mp, tmp_path / "out.html")

    def test_missing_asset_file(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        assets = src / "assets"
        assets.mkdir()
        write_svg(assets / "existing.svg")
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", 'body { background: url("asset://missing"); }\n')
        write_text(src / "script.js", "var x = 1;\n")
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "script.js", "namespace": "App", "depends_on": []},
            ],
            "assets": [
                {
                    "id": "missing",
                    "file": "assets/does-not-exist.svg",
                    "mime": "image/svg+xml",
                },
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="File not found"):
            build(mp, tmp_path / "out.html")

    def test_unsupported_extension(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        assets = src / "assets"
        assets.mkdir()
        write_text(assets / "bad.txt", "not an image\n")
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            '<img src="asset://bad">\n'
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", "body {}\n")
        write_text(src / "script.js", "var x = 1;\n")
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "script.js", "namespace": "App", "depends_on": []},
            ],
            "assets": [
                {"id": "bad", "file": "assets/bad.txt", "mime": "image/png"},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="Unsupported asset extension"):
            build(mp, tmp_path / "out.html")

    def test_mime_mismatch(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        assets = src / "assets"
        assets.mkdir()
        write_svg(assets / "logo.svg")
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", 'body { background: url("asset://logo"); }\n')
        write_text(src / "script.js", "var x = 1;\n")
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "script.js", "namespace": "App", "depends_on": []},
            ],
            "assets": [
                {"id": "logo", "file": "assets/logo.svg", "mime": "image/png"},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="MIME mismatch"):
            build(mp, tmp_path / "out.html")

    def _make_asset_path_fixture(self, tmp_path, asset_file):
        src = tmp_path / "src"
        src.mkdir()
        assets = src / "assets"
        assets.mkdir()
        write_svg(assets / "legit.svg")
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            '<img src="asset://badref">\n'
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", 'body { background: url("asset://badref"); }\n')
        write_text(src / "script.js", "var x = 1;\n")
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "script.js", "namespace": "App", "depends_on": []},
            ],
            "assets": [
                {"id": "badref", "file": asset_file, "mime": "image/svg+xml"},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        return src / "manifest.json"

    def test_absolute_asset_path(self, tmp_path):
        mp = self._make_asset_path_fixture(tmp_path, "/etc/passwd")
        with pytest.raises(BuildError, match="Absolute path"):
            build(mp, tmp_path / "out.html")

    def test_path_traversal(self, tmp_path):
        mp = self._make_asset_path_fixture(tmp_path, "../outside.svg")
        with pytest.raises(BuildError, match="Path traversal"):
            build(mp, tmp_path / "out.html")

    def test_symlink_escape(self, tmp_path):
        if platform.system() == "Windows":
            pytest.skip("Symlinks not reliably available on Windows")

        src = tmp_path / "src"
        src.mkdir()
        assets = src / "assets"
        assets.mkdir()

        outside_file = tmp_path / "outside.txt"
        outside_file.write_text("sensitive data\n")

        symlink_target = assets / "escape.svg"
        try:
            os.symlink(outside_file, symlink_target)
        except (OSError, PermissionError):
            pytest.skip("Cannot create symlinks in this environment")

        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", 'body { background: url("asset://escape"); }\n')
        write_text(src / "script.js", "var x = 1;\n")
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "script.js", "namespace": "App", "depends_on": []},
            ],
            "assets": [
                {
                    "id": "escape",
                    "file": "assets/escape.svg",
                    "mime": "image/svg+xml",
                },
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="Path escapes"):
            build(mp, tmp_path / "out.html")

    def test_referenced_undeclared_asset(self, tmp_path):
        mp, _ = _atomic_replace_setup(
            tmp_path,
            {
                "assets": [],
            },
        )
        with pytest.raises(BuildError, match="Referenced but undeclared"):
            build(mp, tmp_path / "out.html")

    def test_unused_manifest_asset(self, tmp_path):
        mp, _ = _atomic_replace_setup(
            tmp_path,
            {
                "assets": [
                    {"id": "a", "file": "assets/a.svg", "mime": "image/svg+xml"},
                    {"id": "unused", "file": "assets/a.svg", "mime": "image/svg+xml"},
                ],
            },
        )
        with pytest.raises(BuildError, match="Declared but unused"):
            build(mp, tmp_path / "out.html")


# ---- Asset reference in JavaScript ----


class TestAssetInJS:
    def test_asset_reference_in_javascript(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", "body {}\n")
        write_text(
            src / "bad.js",
            'var img = "asset://logo";\n',
        )
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "bad.js", "namespace": "App", "depends_on": []},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="asset://"):
            build(mp, tmp_path / "out.html")


# ---- External references in template ----


class TestExternalReferences:
    def _make_ext_fixture(self, tmp_path, template_content):
        src = tmp_path / "src"
        src.mkdir()
        write_text(src / "template.html", template_content)
        write_text(src / "style.css", "body {}\n")
        write_text(src / "script.js", "var x = 1;\n")
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "script.js", "namespace": "App", "depends_on": []},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        return src / "manifest.json"

    def test_external_script_src(self, tmp_path):
        tpl = (
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            '<script src="https://cdn.example.com/lib.js"></script>\n'
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n"
        )
        mp = self._make_ext_fixture(tmp_path, tpl)
        with pytest.raises(BuildError, match="external <script src"):
            build(mp, tmp_path / "out.html")

    def test_external_stylesheet(self, tmp_path):
        tpl = (
            "<!doctype html>\n"
            '<link rel="stylesheet" href="https://cdn.example.com/style.css">\n'
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n"
        )
        mp = self._make_ext_fixture(tmp_path, tpl)
        with pytest.raises(BuildError, match="external stylesheet"):
            build(mp, tmp_path / "out.html")


# ---- Output network validation ----


class TestOutputNetworkValidation:
    def test_external_html_media_src(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            '<img src="http://example.com/img.png">\n'
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", "body {}\n")
        write_text(src / "script.js", "var x = 1;\n")
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "script.js", "namespace": "App", "depends_on": []},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="external HTML"):
            build(mp, tmp_path / "out.html")

    def test_external_css_url(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(
            src / "style.css",
            'body { background: url("http://example.com/bg.png"); }\n',
        )
        write_text(src / "script.js", "var x = 1;\n")
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "script.js", "namespace": "App", "depends_on": []},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="external CSS url"):
            build(mp, tmp_path / "out.html")

    def test_fetch_in_source(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", "body {}\n")
        write_text(
            src / "bad.js",
            "fetch('/api/data').then(r => r.json());\n",
        )
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "bad.js", "namespace": "App", "depends_on": []},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="fetch"):
            build(mp, tmp_path / "out.html")

    def test_xmlhttprequest_in_source(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", "body {}\n")
        write_text(
            src / "bad.js",
            "var xhr = new XMLHttpRequest();\n",
        )
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "bad.js", "namespace": "App", "depends_on": []},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="XMLHttpRequest"):
            build(mp, tmp_path / "out.html")

    def test_websocket_in_source(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", "body {}\n")
        write_text(
            src / "bad.js",
            "var ws = new WebSocket('ws://localhost');\n",
        )
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "bad.js", "namespace": "App", "depends_on": []},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="WebSocket"):
            build(mp, tmp_path / "out.html")

    def test_eventsource_in_source(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", "body {}\n")
        write_text(
            src / "bad.js",
            "var es = new EventSource('/events');\n",
        )
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "bad.js", "namespace": "App", "depends_on": []},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="EventSource"):
            build(mp, tmp_path / "out.html")


# ---- Manifest failures ----


class TestManifestFailures:
    def test_unknown_manifest_key(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", "body {}\n")
        write_text(src / "script.js", "var x = 1;\n")
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "script.js", "namespace": "App", "depends_on": []},
            ],
            "unknown_key": "should fail",
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="Unknown manifest key"):
            build(mp, tmp_path / "out.html")

    def test_wrong_manifest_value_type(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        manifest = {
            "template": "template.html",
            "styles": "not an array",
            "scripts": [],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="must be an array"):
            build(mp, tmp_path / "out.html")


# ---- Failure does not overwrite output ----


class TestFailureNoOverwrite:
    def test_failure_does_not_overwrite_output(self, tmp_path):
        manifest_path = BASIC_FIXTURE / "manifest.json"
        output_path = tmp_path / "preserved.html"

        build(manifest_path, output_path)
        original = output_path.read_bytes()

        bad_manifest = tmp_path / "bad.json"
        bad_manifest.write_text(
            json.dumps(
                {
                    "template": "template.html",
                    "styles": ["style.css"],
                    "scripts": [],
                }
            )
        )

        with pytest.raises(BuildError):
            build(bad_manifest, output_path)

        assert output_path.read_bytes() == original


# ---- No doctype test ----


class TestNoDoctype:
    def test_no_doctype_template(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            "<html>\n<head>\n<!-- OCEAN_RESCUE_CSS -->\n</head>\n<body>\n<!-- OCEAN_RESCUE_SCRIPTS -->\n</body>\n</html>\n",
        )
        write_text(src / "style.css", "body {}\n")
        write_text(src / "script.js", "var x = 1;\n")
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "script.js", "namespace": "App", "depends_on": []},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="Template must start with"):
            build(mp, tmp_path / "out.html")


# ---- Inline scripts in template ----


class TestInlineScriptTemplate:
    def test_inline_script_in_template(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        write_text(
            src / "template.html",
            "<!doctype html>\n"
            "<!-- OCEAN_RESCUE_CSS -->\n"
            "<script>var x = 1;</script>\n"
            "<!-- OCEAN_RESCUE_SCRIPTS -->\n",
        )
        write_text(src / "style.css", "body {}\n")
        write_text(src / "script.js", "var y = 2;\n")
        manifest = {
            "template": "template.html",
            "styles": ["style.css"],
            "scripts": [
                {"file": "script.js", "namespace": "App", "depends_on": []},
            ],
        }
        write_text(src / "manifest.json", json.dumps(manifest))
        mp = src / "manifest.json"
        with pytest.raises(BuildError, match="inline script"):
            build(mp, tmp_path / "out.html")
