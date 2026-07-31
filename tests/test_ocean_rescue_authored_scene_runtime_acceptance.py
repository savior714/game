"""Static contract tests for the authored scene runtime acceptance harness."""

import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

RENDER_DIR = REPO_ROOT / "tests/ocean-rescue/rendering-acceptance"
HTML_PATH = RENDER_DIR / "authored-scene-runtime.html"
MJS_PATH = RENDER_DIR / "authored-scene-runtime.mjs"
RUNNER_PATH = REPO_ROOT / "scripts/ocean-rescue/verify-authored-scene-runtime.py"
STATIC_TEST_PATH = REPO_ROOT / "tests/test_ocean_rescue_authored_scene_runtime_acceptance.py"

CDN_HOSTNAMES = [
    "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com",
    "unpkg.com",
    "pixijs.download",
    "cdn.pixijs.com",
]

SEA_TURTLE_APIS = [
    "turtle.start",
    "turtle.pointerDown",
    "turtle.pointerMove",
    "turtle.pointerUp",
    "turtle.finishFeedback",
    "turtle.getSnapshot",
    "turtle.Ropes",
]

SCENE_APIS = [
    "scene.prepare",
    "scene.activate",
    "scene.sync",
    "scene.exit",
    "scene.getDiagnostics",
]


def _runner():
    return RUNNER_PATH.read_text(encoding="utf-8")


def _mjs():
    return MJS_PATH.read_text(encoding="utf-8")


def _html():
    return HTML_PATH.read_text(encoding="utf-8")


def test_runner_and_fixtures_exist():
    assert RUNNER_PATH.is_file(), "runner missing"
    assert HTML_PATH.is_file(), "HTML fixture missing"
    assert MJS_PATH.is_file(), "MJS fixture missing"
    assert STATIC_TEST_PATH.is_file(), "static contract test missing"


def test_harness_does_not_require_production_changes():
    runner = _runner()
    assert '"w"' not in runner, "runner opens a file for writing"
    assert '"wb"' not in runner, "runner opens a file for writing"
    assert "build_single_html" not in runner, "runner rebuilds production HTML"
    assert "--output" not in runner, "runner writes a generated artifact"
    assert "ocean-rescue/index.html" in runner, "runner does not guard production HTML"
    assert "render-runtime.js" in runner, "runner does not guard render-runtime.js"
    assert "sea-turtle.js" in runner, "runner does not guard sea-turtle.js"
    assert "sea-turtle-scene.js" in runner, "runner does not guard sea-turtle-scene.js"


def test_harness_uses_production_single_html_iframe():
    assert 'src="/ocean-rescue/index.html"' in _html(), "iframe does not load production HTML"
    assert "/ocean-rescue/index.html" in _mjs(), "MJS iframe source literal missing"


def test_no_remote_urls_in_fixtures():
    for path in (HTML_PATH, MJS_PATH):
        content = path.read_text(encoding="utf-8")
        assert "http://" not in content, f"http:// found in {path.name}"
        assert "https://" not in content, f"https:// found in {path.name}"
        assert "//cdn" not in content, f"protocol-relative CDN found in {path.name}"
        assert "//unpkg" not in content, f"protocol-relative unpkg found in {path.name}"


def test_no_cdn_hostnames_in_fixtures():
    for path in (HTML_PATH, MJS_PATH):
        content = path.read_text(encoding="utf-8")
        for host in CDN_HOSTNAMES:
            assert host not in content, f"CDN hostname {host} found in {path.name}"


def test_reference_runtime_is_guarded_not_loaded():
    html = _html()
    mjs = _mjs()
    combined = html + mjs
    assert "docs/reference/ocean-rescue" in mjs, "reference prefix guard missing"
    assert 'src="/docs/reference' not in combined, "reference asset loaded via src"
    assert 'href="/docs/reference' not in combined, "reference asset loaded via href"
    assert 'import "/docs/reference' not in combined, "reference asset imported"
    assert 'fetch("/docs/reference' not in combined, "reference asset fetched"


def test_uses_canonical_rope_one():
    assert "turtle.Ropes[0]" in _mjs(), "canonical Ropes[0] not used"


def test_no_hardcoded_rope_coordinates():
    mjs = _mjs()
    for literal in ("760", "1040", "300,", "330"):
        assert literal not in mjs, f"hardcoded coordinate literal {literal} found"
    for token in ("rope.start.x", "rope.end.x", "rope.start.y", "rope.end.y"):
        assert token in mjs, f"coordinate token {token} missing"


def test_uses_public_sea_turtle_api_only():
    mjs = _mjs()
    for api in SEA_TURTLE_APIS:
        assert api in mjs, f"public SeaTurtle API {api} missing"
    assert "turtle.state" not in mjs, "internal SeaTurtle state accessed"
    assert "turtle.completedRopeIds" not in mjs, "internal SeaTurtle state accessed"


def test_uses_public_sea_turtle_scene_api_only():
    mjs = _mjs()
    for api in SCENE_APIS:
        assert api in mjs, f"public SeaTurtleScene API {api} missing"
    assert "scene.nodes" not in mjs, "internal scene graph accessed"


def test_initial_worried_assertion_exists():
    runner = _runner()
    assert '"worried"' in runner, "worried assertion missing"
    assert "initial.reliefStage" in runner, "initial reliefStage assertion missing"
    assert "initial.activeRopeId" in runner, "initial activeRopeId assertion missing"
    assert "initial.completedCount" in runner, "initial completedCount assertion missing"


def test_relief_one_assertion_exists():
    assert '"relief-1"' in _runner(), "relief-1 assertion missing"


def test_rope_two_assertion_exists():
    assert '"rope-2"' in _runner(), "rope-2 assertion missing"


def test_legacy_bridge_transition_assertions_exist():
    runner = _runner()
    assert "initial.legacyBridgeVisible" in runner, "initial bridge assertion missing"
    assert "afterRelease.legacyBridgeVisible" in runner, "release bridge assertion missing"
    assert "afterExit.legacyBridgeVisible" in runner, "exit bridge assertion missing"


def test_external_origin_assertion_exists():
    assert "externalOriginRequestCount" in _mjs(), "external origin collection missing"
    assert "externalOriginRequestCount" in _runner(), "external origin assertion missing"


def test_reference_request_assertion_exists():
    assert "referenceImageRequestCount" in _mjs(), "reference request collection missing"
    assert "referenceImageRequestCount" in _runner(), "reference request assertion missing"


def test_error_rejection_collection_exists():
    mjs = _mjs()
    assert "uncaughtErrorCount" in mjs, "error collection missing"
    assert "unhandledRejectionCount" in mjs, "rejection collection missing"
    assert "securitypolicyviolation" in mjs, "CSP violation collection missing"
    runner = _runner()
    assert "uncaughtErrorCount" in runner, "error assertion missing"
    assert "unhandledRejectionCount" in runner, "rejection assertion missing"
    assert "securityPolicyViolationCount" in runner, "CSP violation assertion missing"


def test_harness_html_contract():
    html = _html()
    assert "Content-Security-Policy" in html, "CSP missing"
    assert "default-src 'self'" in html, "CSP default-src not self"
    assert "script-src 'self'" in html, "CSP script-src not self-only"
    assert "frame-src 'self'" in html, "CSP frame-src not self"
    assert "font-src 'none'" in html, "CSP font-src not none"
    assert "object-src 'none'" in html, "CSP object-src not none"
    assert html.count("<iframe") == 1, "expected exactly one iframe"
    assert 'id="diagnostics"' in html, "diagnostics element missing"


def test_harness_loads_local_test_module():
    html = _html()
    assert 'type="module"' in html, "local test module not loaded"
    assert "authored-scene-runtime.mjs" in html, "local test module not referenced"


def test_runner_imports_backend_verifier_without_modifying():
    runner = _runner()
    assert "verify-pixi-backends.py" in runner, "existing verifier not reused"
    assert "spec_from_file_location" in runner, "existing verifier not imported via spec"
    assert '"w"' not in runner, "runner writes files"
    assert '"wb"' not in runner, "runner writes files"


def test_runner_has_production_hash_guard():
    runner = _runner()
    assert "hashlib" in runner, "hashlib missing"
    assert "sha256" in runner, "sha256 missing"
    assert "sha256_of" in runner, "hash helper missing"
    assert "before_hashes" in runner, "pre-run hash capture missing"
    assert "after_hashes" in runner, "post-run hash capture missing"


def test_runner_no_third_party_imports():
    runner = _runner()
    prohibited = [
        "import playwright",
        "from playwright",
        "import selenium",
        "from selenium",
        "import puppeteer",
        "from puppeteer",
        "import jsdom",
    ]
    for pattern in prohibited:
        assert pattern not in runner, f"third-party import found: {pattern}"
    assert "import subprocess" in runner, "subprocess import missing"


def test_runner_has_no_shell_true():
    assert "shell=True" not in _runner(), "shell=True used"


def test_runner_targets_harness_locally():
    runner = _runner()
    assert "127.0.0.1" in runner, "runner does not use loopback"
    assert "authored-scene-runtime.html" in runner, "runner does not target harness"


def test_runner_uses_virtual_time_budget():
    assert "--virtual-time-budget=12000" in _runner(), "virtual time budget missing"


def test_runner_keeps_native_backend_defaults():
    runner = _runner()
    assert "--disable-webgl" not in runner, "WebGL disabled in normal runtime"
    assert "--disable-gpu" not in runner, "GPU disabled in normal runtime"
    assert "--disable-software-rasterizer" not in runner, "software rasterizer disabled"


def test_runner_guards_main():
    assert '__name__ == "__main__"' in _runner(), "main not guarded"


def test_mjs_records_initial_scene_state():
    mjs = _mjs()
    assert "diag.initial = scene.getDiagnostics()" in mjs, "initial diagnostics missing"
    assert "diag.releaseResult = turtle.pointerUp" in mjs, "release result missing"
    assert "diag.afterReleaseInterim" in mjs, "interim diagnostics missing"
    assert "diag.feedback = turtle.finishFeedback()" in mjs, "feedback missing"
    assert "diag.afterRelease" in mjs, "post-feedback diagnostics missing"
    assert "diag.afterExit" in mjs, "exit diagnostics missing"


def test_runner_has_argparse_backend_and_flow_choices():
    runner = _runner()
    assert "argparse" in runner, "argparse missing"
    assert '"--backend"' in runner, "backend CLI option missing"
    assert '"--flow"' in runner, "flow CLI option missing"
    assert 'choices=("auto", "canvas")' in runner, "backend choices missing"
    assert 'choices=("first-rope", "complete")' in runner, "flow choices missing"


def test_runner_defaults_are_auto_and_first_rope():
    runner = _runner()
    assert 'default="auto"' in runner, "backend default != auto"
    assert 'default="first-rope"' in runner, "flow default != first-rope"


def test_webgl_disable_flag_only_in_canvas_mode():
    runner = _runner()
    assert "WEBGL_DISABLE_FLAG" in runner, "webgl disable flag constant missing"
    assert "chrome_args.append(WEBGL_DISABLE_FLAG)" in runner, "flag not appended"
    assert 'backend_mode == "canvas"' in runner, "flag not guarded by canvas mode"
    assert "--disable-gpu" not in runner, "disable-gpu added"
    assert "--disable-software-rasterizer" not in runner, "software rasterizer disabled"
    assert "--disable-webgl" not in runner, "webgl disable flag leaked into default path"


def test_complete_flow_query_passed_to_harness():
    runner = _runner()
    assert 'args.flow == "complete"' in runner, "complete flow branch missing"
    assert '"?flow=complete"' in runner, "complete flow query not appended"


def test_harness_uses_indexed_canonical_ropes():
    mjs = _mjs()
    assert "releaseCanonicalRope" in mjs, "canonical rope helper missing"
    assert "turtle.Ropes[ropeIndex]" in mjs, "indexed canonical rope read missing"


def test_complete_flow_reads_endpoints_from_canonical_ropes():
    mjs = _mjs()
    for token in ("rope.start.x", "rope.start.y", "rope.end.x", "rope.end.y"):
        assert token in mjs, f"rope endpoint token {token} missing"
    for literal in (
        "760", "1040", "300", "330",
        "750", "1050", "420", "440",
        "770", "1030", "540", "570",
    ):
        assert literal not in mjs, f"hardcoded rope coordinate {literal} found"


def test_complete_flow_loops_three_ropes_in_order():
    mjs = _mjs()
    assert "for (let i = 0; i < 3; i += 1)" in mjs, "three-rope loop missing"
    runner = _runner()
    assert '["rope-1", "rope-2", "rope-3"]' in runner, "expected rope order missing"


def test_relief_stage_progression_assertions_exist():
    runner = _runner()
    assert '"relief-1"' in runner, "relief-1 assertion missing"
    assert '"relief-2"' in runner, "relief-2 assertion missing"
    assert '"free"' in runner, "free assertion missing"


def test_pause_resume_cycle_exists():
    mjs = _mjs()
    assert "turtle.pauseCancel()" in mjs, "pauseCancel call missing"
    assert "game.RenderRuntime.pause()" in mjs, "RenderRuntime.pause call missing"
    assert "scene.pause()" in mjs, "scene.pause call missing"
    assert "game.RenderRuntime.resume()" in mjs, "RenderRuntime.resume call missing"
    assert "scene.resume()" in mjs, "scene.resume call missing"
    runner = _runner()
    assert "pauseCycle" in runner, "pauseCycle assertion missing"


def test_pause_domain_equality_assertion_exists():
    mjs = _mjs()
    assert "domainBeforePause" in mjs, "pre-pause snapshot missing"
    assert "domainDuringPause" in mjs, "during-pause snapshot missing"
    assert "domainAfterResume" in mjs, "post-resume snapshot missing"
    runner = _runner()
    assert "pauseCycle.domainUnchanged" in runner, "pause domain equality assertion missing"


def test_final_domain_assertions_exist():
    runner = _runner()
    assert "finalDomain.complete" in runner, "final complete assertion missing"
    assert "finalDomain.active" in runner, "final active=false assertion missing"
    assert "finalDomain.activeRopeId" in runner, "final activeRopeId assertion missing"
    assert "beforeExit.reliefStage" in runner, "beforeExit relief assertion missing"
    assert "afterExit.legacyBridgeVisible" in runner, "legacy bridge restoration assertion missing"


def test_existing_first_rope_contract_preserved():
    runner = _runner()
    for name in (
        "singleHtmlReady",
        "renderRuntimeReady",
        "release.accepted",
        "release.outcome",
        "release.ropeId",
        "afterRelease.reliefStage",
        "feedback.nextRopeId",
        "afterExit.mounted",
    ):
        assert name in runner, f"first-rope check {name} removed"
    assert "OCEAN_RESCUE_AUTHORED_SCENE_RUNTIME_ACCEPTANCE=PASS" in runner, (
        "existing first-rope PASS marker removed"
    )
    assert "OCEAN_RESCUE_CANVAS_COMPLETE_RESCUE_RUNTIME_ACCEPTANCE=PASS" in runner, (
        "canvas complete PASS marker missing"
    )


def test_runner_touches_no_package_metadata():
    runner = _runner()
    assert "package-lock.json" not in runner, "runner references package-lock.json"
    assert "package.json" not in runner, "runner references package.json"
    assert "npm" not in runner, "runner references npm"
