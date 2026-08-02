"""Static contract tests for the sea turtle rope geometry alignment harness."""

import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

RENDER_DIR = REPO_ROOT / "tests/ocean-rescue/rendering-acceptance"
HTML_PATH = RENDER_DIR / "rope-geometry-runtime.html"
MJS_PATH = RENDER_DIR / "rope-geometry-runtime.mjs"
RUNNER_PATH = REPO_ROOT / "scripts/ocean-rescue/verify-rope-geometry-runtime.py"
SEA_TURTLE_SCENE_PATH = REPO_ROOT / "domains/ocean-rescue/src/sea-turtle-scene.js"


def _runner():
    return RUNNER_PATH.read_text(encoding="utf-8")


def _mjs():
    return MJS_PATH.read_text(encoding="utf-8")


def _html():
    return HTML_PATH.read_text(encoding="utf-8")


def _scene():
    return SEA_TURTLE_SCENE_PATH.read_text(encoding="utf-8")


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


def test_mjs_footprint_uses_trim_not_frame_as_offset():
    mjs = _mjs()
    assert "tex.trim" in mjs, "trim must be read from the runtime texture"
    assert "worldTransform.apply" in mjs, "world transform must be applied canonically"
    assert "trimX + trimW / 2 - anchor.x * origW" in mjs, (
        "trim-aware local center missing"
    )
    assert "trimY + trimH / 2 - anchor.y * origH" in mjs, (
        "trim-aware local center missing"
    )
    assert "tex.frame.x - anchorX" not in mjs, (
        "atlas frame position used as trim offset"
    )
    assert "tex.frame.x - anchor.x" not in mjs, (
        "atlas frame position used as trim offset"
    )


def test_mjs_has_visible_footprint_crosschecks():
    mjs = _mjs()
    assert "visibleFootprint" in mjs
    assert "crossCheckVsVisualBounds" in mjs
    assert "crossCheckVsGetBounds" in mjs
    assert "boundsCenter" in mjs
    assert "visualBoundsCenter" in mjs
    assert "visibleCenterDelta" in mjs
    assert "normalOffset" in mjs
    assert "tangentOffset" in mjs


def test_mjs_reports_runtime_texture_semantics():
    mjs = _mjs()
    assert (
        "trimX" in mjs and "trimY" in mjs and "trimWidth" in mjs and "trimHeight" in mjs
    )
    assert "defaultAnchorX" in mjs and "defaultAnchorY" in mjs
    assert "resolution" in mjs


def test_mjs_bounds_helper_does_not_call_update_transform():
    mjs = _mjs()
    assert "obj.updateTransform()" not in mjs, (
        "updateTransform() without parent transform throws in PixiJS 8"
    )


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


def test_runner_has_visible_footprint_contract():
    runner = _runner()
    assert "CROSS_CHECK_EPS" in runner
    assert "RESIDUAL_MIN" in runner
    assert "crossVsVisual<=1px" in runner
    assert "visibleResidualConfirmed" in runner
    assert "normalSignConsistent" in runner
    assert "RESIDUAL_VISIBLE_OFFSET=CONFIRMED" in runner
    assert "SEA_TURTLE_ROPE_VISIBLE_FOOTPRINT_MEASUREMENT=VALID" in runner
    assert "SEA_TURTLE_ROPE_VISIBLE_FOOTPRINT_ALIGNMENT=PASS" in runner


def test_runner_requires_alignment_in_post_fix_normal_invocation():
    runner = _runner()
    assert "ALIGN_EPS" in runner
    assert "require_alignment" in runner
    assert "visibleDelta<=1px" in runner
    assert "tangentOffset<=1px" in runner
    assert "normalOffset<=1px" in runner
    assert "pulseDrift<=1px" in runner
    assert "trace.afterAdvance." in runner
    assert "offPath.afterReset." in runner


def test_runner_reserves_residual_confirmation_for_red_reproduction():
    runner = _runner()
    assert "require_residual=allow_red" in runner
    assert "require_alignment=not allow_red" in runner
    # The post-fix normal invocation must not accept a > 2px residual as PASS.
    assert "if not all_pass:" in runner
    assert 'name.endswith("visibleResidualConfirmed")' in runner


def test_scene_has_trim_aware_loop_anchor_helper():
    scene = _scene()
    assert "function centerAnchorOnTrimmedVisibleFrame(sprite)" in scene
    assert "sprite.anchor.set(" in scene


def test_helper_derives_anchor_from_runtime_trim_and_orig():
    scene = _scene()
    helper = scene.split("function centerAnchorOnTrimmedVisibleFrame(sprite)", 1)[1]
    assert "texture.orig" in helper
    assert "texture.trim" in helper
    assert "orig.width" in helper and "orig.height" in helper
    assert "trim.x" in helper and "trim.width" in helper
    assert "(trim.x + trim.width / 2) / orig.width" in helper
    assert "(trim.y + trim.height / 2) / orig.height" in helper


def test_helper_never_reads_atlas_frame_coordinates():
    scene = _scene()
    helper = scene.split("function centerAnchorOnTrimmedVisibleFrame(sprite)", 1)[1]
    assert "texture.frame" not in helper
    assert ".frame.x" not in helper
    assert ".frame.y" not in helper


def test_scene_has_no_asset_specific_anchor_hardcodes():
    scene = _scene()
    assert "0.5175" not in scene
    assert "48.43" not in scene


def test_helper_applied_to_each_loop_sprite_at_creation():
    scene = _scene()
    assert 'makeSprite("scene.seaweed-loop.01"' in scene
    assert "centerAnchorOnTrimmedVisibleFrame(loopSprite)" in scene
    assert "nodes.loops.push(loopSprite)" in scene


def test_sync_loops_keeps_canonical_midpoint_position():
    scene = _scene()
    assert "loop.position.set(base.x, base.y)" in scene
    assert (
        "loop.rotation = Math.atan2(rope.end.y - rope.start.y, rope.end.x - rope.start.x)"
        in scene
    )


def test_loop_position_is_never_translated_by_pointer_intent():
    scene = _scene()
    sync = scene.split("function syncLoops", 1)[1]
    position_lines = [line for line in sync.splitlines() if "loop.position" in line]
    assert position_lines, "no loop.position references in syncLoops"
    for line in position_lines:
        assert "pointerIntent" not in line, (
            "loop.position driven by pointer: {}".format(line.strip())
        )
    assert any("base.x" in line and "base.y" in line for line in position_lines)


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
