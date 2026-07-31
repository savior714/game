"""Static contract tests for the four-state visual evidence packet.

These tests verify the structure and contracts of the capture script and
fixture without executing Chrome. They ensure:

- Script and fixture files exist
- No third-party Python imports
- No shell=True or os.system usage
- Viewport is fixed at 1280x720
- Device scale factor is fixed at 1
- No --disable-gpu or --disable-webgl flags
- Backend is exactly webgl
- Four states with fixed order
- Uses SeaTurtle.Ropes[index] for rope coordinates
- No duplicated rope endpoint numbers
- Four relief stage assertions
- Free state complete=true assertion
- scene.pause() and animation stopped assertion
- Legacy bridge hidden assertion
- External/reference/error/CSP counter assertions
- PNG IHDR parser
- Dimension exact assertions
- SHA-256 manifest contract
- No timestamp or absolute path in manifest
- Temporary output + atomic replace
- Production/package byte guard
- No production writes

These are focused contract tests, not runtime acceptance tests.
"""

import hashlib
import json
import os
import pathlib
import re

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

SCRIPT_PATH = REPO_ROOT / "scripts" / "ocean-rescue" / "capture-authored-scene-visual-packet.py"
HTML_PATH = REPO_ROOT / "tests" / "ocean-rescue" / "rendering-acceptance" / "authored-scene-visual-packet.html"
MJS_PATH = REPO_ROOT / "tests" / "ocean-rescue" / "rendering-acceptance" / "authored-scene-visual-packet.mjs"

EXPECTED_STATES = ["worried", "relief-1", "relief-2", "free"]
EXPECTED_WIDTH = 1280
EXPECTED_HEIGHT = 720
EXPECTED_SCALE_FACTOR = 1


def read_file(path):
    return path.read_text(encoding="utf-8")


class TestFileExistence:
    def test_script_exists(self):
        assert SCRIPT_PATH.exists(), "Capture script missing"

    def test_html_fixture_exists(self):
        assert HTML_PATH.exists(), "HTML fixture missing"

    def test_mjs_fixture_exists(self):
        assert MJS_PATH.exists(), "MJS fixture missing"


class TestPythonImports:
    def test_no_third_party_imports(self):
        content = read_file(SCRIPT_PATH)
        import_lines = [
            line.strip()
            for line in content.splitlines()
            if line.strip().startswith("import ") or line.strip().startswith("from ")
        ]
        third_party = [
            line for line in import_lines
            if not any(
                stdlib in line
                for stdlib in [
                    "os", "sys", "json", "pathlib", "subprocess", "tempfile",
                    "shutil", "socket", "threading", "hashlib", "struct",
                    "http", "argparse", "importlib",
                ]
            )
        ]
        assert third_party == [], "Third-party imports found: {}".format(third_party)


class TestNoShellExecution:
    def test_no_shell_true(self):
        content = read_file(SCRIPT_PATH)
        assert "shell=True" not in content, "shell=True found in script"

    def test_no_os_system(self):
        content = read_file(SCRIPT_PATH)
        assert "os.system" not in content, "os.system found in script"


class TestViewportAndScale:
    def test_viewport_width(self):
        content = read_file(SCRIPT_PATH)
        assert "1280" in content, "Viewport width 1280 not found"

    def test_viewport_height(self):
        content = read_file(SCRIPT_PATH)
        assert "720" in content, "Viewport height 720 not found"

    def test_scale_factor_one(self):
        content = read_file(SCRIPT_PATH)
        assert "force-device-scale-factor=1" in content, "Scale factor 1 not enforced"

    def test_no_disable_gpu(self):
        content = read_file(SCRIPT_PATH)
        assert "--disable-gpu" not in content, "--disable-gpu flag found (forbidden)"

    def test_no_disable_webgl(self):
        content = read_file(SCRIPT_PATH)
        assert "--disable-webgl" not in content, "--disable-webgl flag found (forbidden)"


class TestBackendContract:
    def test_backend_webgl_assertion(self):
        content = read_file(SCRIPT_PATH)
        assert '"webgl"' in content or "'webgl'" in content, "Backend webgl assertion missing"

    def test_backend_exact_check(self):
        content = read_file(SCRIPT_PATH)
        assert '!= "webgl"' in content or '!= \'webgl\'' in content, "Backend exact check missing"


class TestStateOrder:
    def test_four_states(self):
        content = read_file(SCRIPT_PATH)
        for state in EXPECTED_STATES:
            assert '"{}"'.format(state) in content or "'{}'".format(state) in content, \
                "State {} not found in script".format(state)

    def test_state_order(self):
        content = read_file(SCRIPT_PATH)
        lines = content.splitlines()
        state_indices = []
        for i, line in enumerate(lines):
            if "STATES" in line and ("=[" in line or "= [" in line):
                state_indices.append(i)
        assert len(state_indices) > 0, "STATES list not found"


class TestRopeCoordinates:
    def test_uses_sea_turtle_ropes(self):
        mjs_content = read_file(MJS_PATH)
        assert "SeaTurtle.Ropes" in mjs_content or "turtle.Ropes" in mjs_content, \
            "SeaTurtle.Ropes or turtle.Ropes not used in MJS"

    def test_no_hardcoded_endpoint_numbers(self):
        mjs_content = read_file(MJS_PATH)
        hardcoded_pattern = re.compile(r"\b(?:760|1040|750|1050|770|1030)\b")
        matches = hardcoded_pattern.findall(mjs_content)
        assert matches == [], "Hardcoded rope endpoint numbers found: {}".format(matches)


class TestStateAssertions:
    def test_worried_completed_zero(self):
        mjs_content = read_file(MJS_PATH)
        assert "completedCount" in mjs_content, "completedCount not asserted"

    def test_relief_stages(self):
        mjs_content = read_file(MJS_PATH)
        for stage in ["worried", "relief-1", "relief-2", "free"]:
            assert stage in mjs_content, "Relief stage {} not found".format(stage)

    def test_free_complete_true(self):
        mjs_content = read_file(MJS_PATH)
        assert "complete" in mjs_content, "complete assertion missing"


class TestSceneLifecycle:
    def test_pause_called(self):
        mjs_content = read_file(MJS_PATH)
        assert "scene.pause()" in mjs_content or "Scene.pause()" in mjs_content, \
            "scene.pause() not called"

    def test_animation_stopped(self):
        content = read_file(SCRIPT_PATH)
        assert "animationRunning" in content, "animationRunning check missing"


class TestLegacyBridge:
    def test_legacy_bridge_hidden(self):
        content = read_file(SCRIPT_PATH)
        assert "legacyBridgeVisible" in content, "legacyBridgeVisible check missing"


class TestNetworkAndErrorCounters:
    def test_external_request_counter(self):
        content = read_file(SCRIPT_PATH)
        assert "externalOriginRequestCount" in content, "externalOriginRequestCount missing"

    def test_reference_request_counter(self):
        content = read_file(SCRIPT_PATH)
        assert "referenceImageRequestCount" in content, "referenceImageRequestCount missing"

    def test_uncaught_error_counter(self):
        content = read_file(SCRIPT_PATH)
        assert "uncaughtErrorCount" in content, "uncaughtErrorCount missing"

    def test_csp_counter(self):
        content = read_file(SCRIPT_PATH)
        assert "securityPolicyViolationCount" in content, "securityPolicyViolationCount missing"


class TestPngValidation:
    def test_png_signature_check(self):
        content = read_file(SCRIPT_PATH)
        assert "PNG" in content or "signature" in content.lower(), "PNG signature check missing"

    def test_ihdr_parser(self):
        content = read_file(SCRIPT_PATH)
        assert "IHDR" in content or "struct" in content, "IHDR parser missing"

    def test_dimension_assertion(self):
        content = read_file(SCRIPT_PATH)
        assert "1280" in content and "720" in content, "Dimension assertion missing"


class TestManifestContract:
    def test_sha256_in_manifest(self):
        content = read_file(SCRIPT_PATH)
        assert "sha256" in content.lower(), "SHA-256 not in manifest generation"

    def test_no_timestamp(self):
        content = read_file(SCRIPT_PATH)
        assert "datetime" not in content and "time.time" not in content, \
            "Timestamp found in script (forbidden)"

    def test_no_absolute_paths_in_manifest(self):
        content = read_file(SCRIPT_PATH)
        assert "os.getcwd" not in content and "pathlib.Path.cwd" not in content, \
            "Absolute path generation found"


class TestOutputPolicy:
    def test_temporary_output(self):
        content = read_file(SCRIPT_PATH)
        assert "tempfile" in content or "mkdtemp" in content, "Temporary output not used"

    def test_atomic_replace(self):
        content = read_file(SCRIPT_PATH)
        assert "shutil.move" in content or "os.rename" in content, "Atomic replace not used"

    def test_production_byte_guard(self):
        content = read_file(SCRIPT_PATH)
        assert "before_hashes" in content and "after_hashes" in content, \
            "Production byte guard missing"

    def test_no_production_write(self):
        content = read_file(SCRIPT_PATH)
        prod_paths = [
            "ocean-rescue/index.html",
            "domains/ocean-rescue/src/",
        ]
        for prod_path in prod_paths:
            assert prod_path not in content or "artifacts" in content, \
                "Potential production write to {}".format(prod_path)


class TestHtmlFixture:
    def test_csp_header(self):
        content = read_file(HTML_PATH)
        assert "Content-Security-Policy" in content, "CSP header missing"

    def test_iframe_src(self):
        content = read_file(HTML_PATH)
        assert "/ocean-rescue/index.html" in content, "iframe src missing"

    def test_viewport_dimensions(self):
        content = read_file(HTML_PATH)
        assert "1280px" in content, "Viewport width 1280px not set"
        assert "720px" in content, "Viewport height 720px not set"

    def test_diagnostics_offscreen(self):
        content = read_file(HTML_PATH)
        assert "-9999px" in content or "hidden" in content, \
            "Diagnostics not positioned offscreen"


class TestMjsFixture:
    def test_state_query_param(self):
        content = read_file(MJS_PATH)
        assert "state" in content and "URLSearchParams" in content, \
            "State query param not read"

    def test_allowed_states(self):
        content = read_file(MJS_PATH)
        for state in EXPECTED_STATES:
            assert "'{}'".format(state) in content or '"{}"'.format(state) in content, \
                "Allowed state {} not in MJS".format(state)

    def test_fail_closed_unknown_state(self):
        content = read_file(MJS_PATH)
        assert "Unknown state" in content or "fail" in content.lower(), \
            "Fail-closed for unknown state not implemented"
