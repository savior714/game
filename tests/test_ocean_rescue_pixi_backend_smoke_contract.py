"""Static contract test for pixi backend smoke harness."""

import json
import pathlib

import pytest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

BACKEND_DIR = REPO_ROOT / "tests/ocean-rescue/rendering-acceptance/backend"
HTML_PATH = BACKEND_DIR / "pixi-backend-smoke.html"
MJS_PATH = BACKEND_DIR / "pixi-backend-smoke.mjs"
RUNNER_PATH = REPO_ROOT / "scripts/ocean-rescue/verify-pixi-backends.py"
PKG_PATH = REPO_ROOT / "domains/ocean-rescue/package.json"
LOCK_PATH = REPO_ROOT / "domains/ocean-rescue/package-lock.json"

CDN_HOSTNAMES = [
    "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com",
    "unpkg.com",
    "pixijs.download",
    "cdn.pixijs.com",
]


def test_fixture_files_exist():
    assert HTML_PATH.is_file(), "HTML fixture missing"
    assert MJS_PATH.is_file(), "MJS fixture missing"


def test_no_remote_urls_in_html():
    content = HTML_PATH.read_text(encoding="utf-8")
    assert "http://" not in content, "http:// found in HTML"
    assert "https://" not in content, "https:// found in HTML"
    assert "//cdn" not in content, "protocol-relative CDN found in HTML"
    assert "//unpkg" not in content, "protocol-relative unpkg found in HTML"


def test_no_remote_urls_in_mjs():
    content = MJS_PATH.read_text(encoding="utf-8")
    assert "http://" not in content, "http:// found in MJS"
    assert "https://" not in content, "https:// found in MJS"


def test_no_cdn_in_html():
    content = HTML_PATH.read_text(encoding="utf-8")
    for host in CDN_HOSTNAMES:
        assert host not in content, f"CDN hostname {host} found in HTML"


def test_no_cdn_in_mjs():
    content = MJS_PATH.read_text(encoding="utf-8")
    for host in CDN_HOSTNAMES:
        assert host not in content, f"CDN hostname {host} found in MJS"


def test_csp_exists_in_html():
    content = HTML_PATH.read_text(encoding="utf-8")
    assert "Content-Security-Policy" in content, "CSP missing"
    assert "default-src" in content, "CSP default-src missing"
    assert "connect-src 'self'" in content, "CSP connect-src is not local-only"
    assert "font-src 'none'" in content, "CSP font-src is not disabled"
    assert "securitypolicyviolation" in content, "CSP violation diagnostics missing"


def test_unsafe_eval_bundle_is_local():
    content = HTML_PATH.read_text(encoding="utf-8")
    assert (
        "/domains/ocean-rescue/node_modules/pixi.js/dist/packages/unsafe-eval.min.js"
        in content
    )


def test_preference_array_exists_in_mjs():
    content = MJS_PATH.read_text(encoding="utf-8")
    assert "'webgl', 'canvas'" in content, "preference array not found"


def test_forced_canvas_case_exists_in_mjs():
    content = MJS_PATH.read_text(encoding="utf-8")
    assert "'forced-canvas'" in content, "forced-canvas case missing"
    assert "'canvas'" in content, "canvas literal missing"


def test_schema_version_exists_in_mjs():
    content = MJS_PATH.read_text(encoding="utf-8")
    assert "schemaVersion" in content, "schemaVersion missing"
    assert "securityPolicyViolationCount" in content, (
        "security policy diagnostics missing"
    )


def test_runner_uses_localhost():
    if not RUNNER_PATH.is_file():
        pytest.skip("runner file not created yet")
    content = RUNNER_PATH.read_text(encoding="utf-8")
    assert "127.0.0.1" in content, "runner does not use 127.0.0.1"


def test_runner_validates_installed_pixi():
    content = RUNNER_PATH.read_text(encoding="utf-8")
    assert "installed pixi.js package is missing" in content
    assert "installed pixi.js != 8.19.0" in content


def test_runner_asserts_backend_selection_and_csp():
    content = RUNNER_PATH.read_text(encoding="utf-8")
    assert "webglPreflightAvailable" in content
    assert "securityPolicyViolationCount" in content
    assert "requestedPreference mismatch" in content


def test_runner_uses_ephemeral_port():
    if not RUNNER_PATH.is_file():
        pytest.skip("runner file not created yet")
    content = RUNNER_PATH.read_text(encoding="utf-8")
    assert "find_free_port" in content or "0)" in content, (
        "runner does not use ephemeral port"
    )


def test_runner_no_third_party_imports():
    if not RUNNER_PATH.is_file():
        pytest.skip("runner file not created yet")
    content = RUNNER_PATH.read_text(encoding="utf-8")
    prohibited = [
        "import playwright",
        "import selenium",
        "import puppeteer",
        "from playwright",
        "from selenium",
    ]
    for p in prohibited:
        assert p not in content, f"third-party import found: {p}"


def test_package_pinned_pixi():
    pkg = json.loads(PKG_PATH.read_text(encoding="utf-8"))
    assert pkg["dependencies"]["pixi.js"] == "8.19.0", "package.json pixi.js not 8.19.0"


def test_lock_pinned_pixi():
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    assert lock["packages"]["node_modules/pixi.js"]["version"] == "8.19.0", (
        "lock pixi.js not 8.19.0"
    )
