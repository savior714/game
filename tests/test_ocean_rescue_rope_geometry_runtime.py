"""Static contract tests for the sea turtle rope geometry alignment harness."""

import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

RENDER_DIR = REPO_ROOT / "tests/ocean-rescue/rendering-acceptance"
HTML_PATH = RENDER_DIR / "rope-geometry-runtime.html"
MJS_PATH = RENDER_DIR / "rope-geometry-runtime.mjs"
RUNNER_PATH = REPO_ROOT / "scripts/ocean-rescue/verify-rope-geometry-runtime.py"


def _runner():
    return RUNNER_PATH.read_text(encoding="utf-8")


def _mjs():
    return MJS_PATH.read_text(encoding="utf-8")


def _html():
    return HTML_PATH.read_text(encoding="utf-8")


def test_harness_files_exist():
    assert HTML_PATH.is_file(), "HTML fixture missing"
    assert MJS_PATH.is_file(), "MJS fixture missing"
    assert RUNNER_PATH.is_file(), "runner missing"


def test_harness_loads_production_single_html_iframe():
    assert 'src="/ocean-rescue/index.html"' in _html()
    assert "/ocean-rescue/index.html" in _mjs()


def test_harness_html_contract():
    html = _html()
    assert "Content-Security-Policy" in html
    assert "default-src 'self'" in html
    assert "script-src 'self'" in html
    assert "frame-src 'self'" in html
    assert html.count("<iframe") == 1
    assert 'id="diagnostics"' in html
    assert 'type="module"' in html
    assert "rope-geometry-runtime.mjs" in html


def test_no_remote_urls_in_fixtures():
    for path in (HTML_PATH, MJS_PATH):
        content = path.read_text(encoding="utf-8")
        assert "http://" not in content
        assert "https://" not in content
        assert "//cdn" not in content


def test_no_hardcoded_rope_coordinates():
    mjs = _mjs()
    for literal in ("760", "1040", "750", "1050", "770", "1030", "300,", "330"):
        assert literal not in mjs, f"hardcoded coordinate literal {literal} found"
    for token in ("rope.start.x", "rope.end.x", "rope.start.y", "rope.end.y"):
        assert token in mjs, f"coordinate token {token} missing"


def test_mjs_uses_public_runtime_apis_only():
    mjs = _mjs()
    for token in (
        "turtle.Ropes",
        "turtle.pointerDown",
        "turtle.pointerMove",
        "turtle.pointerUp",
        "turtle.finishFeedback",
        "scene.prepare",
        "scene.activate",
        "scene.sync",
        "scene.getDiagnostics",
        "game.RenderRuntime.getContainer",
        "mapClientToLogical",
    ):
        assert token in mjs, f"public API token {token} missing"
    assert "scene.nodes" not in mjs, "internal scene graph accessed"


def test_mjs_probes_retained_pixi_nodes():
    mjs = _mjs()
    assert "sea-turtle-loop-" in mjs
    assert "sea-turtle-cut-ring" in mjs
    assert "sea-turtle-drag-arrow" in mjs
    assert "pointerActive" in mjs
    assert "centerDelta" in mjs


def test_runner_has_production_hash_guard():
    runner = _runner()
    assert "hashlib" in runner
    assert "sha256" in runner
    assert "before_hashes" in runner
    assert "after_hashes" in runner


def test_runner_argparse_backend_and_allow_red():
    runner = _runner()
    assert "argparse" in runner
    assert '"--backend"' in runner
    assert 'choices=("auto", "canvas")' in runner
    assert '"--allow-red"' in runner


def test_runner_targets_harness_locally():
    runner = _runner()
    assert "127.0.0.1" in runner
    assert "rope-geometry-runtime.html" in runner
    assert '"w"' not in runner, "runner opens a file for writing"
    assert "shell=True" not in runner


def test_runner_keeps_native_backend_defaults():
    runner = _runner()
    assert "--disable-webgl" not in runner
    assert "--disable-gpu" not in runner
    assert "--disable-software-rasterizer" not in runner


def test_runner_guards_main_and_pass_marker():
    runner = _runner()
    assert '__name__ == "__main__"' in runner
    assert "SEA_TURTLE_ROPE_VISUAL_HIT_GEOMETRY_ALIGNMENT=PASS" in runner


def test_runner_no_third_party_imports():
    runner = _runner()
    for pattern in (
        "import playwright",
        "from playwright",
        "import selenium",
        "from selenium",
        "import puppeteer",
        "from puppeteer",
        "import jsdom",
    ):
        assert pattern not in runner, f"third-party import found: {pattern}"
