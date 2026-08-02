"""Static contract tests for the authored crab scene runtime acceptance harness."""

import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

RENDER_DIR = REPO_ROOT / "tests/ocean-rescue/rendering-acceptance"
HTML_PATH = RENDER_DIR / "crab-scene-runtime.html"
MJS_PATH = RENDER_DIR / "crab-scene-runtime.mjs"
RUNNER_PATH = REPO_ROOT / "scripts/ocean-rescue/verify-crab-scene-runtime.py"

CDN_HOSTNAMES = [
    "cdn.jsdelivr.net",
    "cdnjs.cloudflare.com",
    "unpkg.com",
    "pixijs.download",
    "cdn.pixijs.com",
]

CRAB_APIS = [
    "crab.start",
    "crab.pointerDown",
    "crab.finishHold",
    "crab.pointerMove",
    "crab.pointerUp",
    "crab.finishFeedback",
    "crab.getSnapshot",
    "crab.Layout",
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


def test_harness_does_not_require_production_changes():
    runner = _runner()
    assert '"w"' not in runner, "runner opens a file for writing"
    assert '"wb"' not in runner, "runner opens a file for writing"
    assert "build_single_html" not in runner, "runner rebuilds production HTML"
    assert "--output" not in runner, "runner writes a generated artifact"
    assert "ocean-rescue/index.html" in runner, "runner does not guard production HTML"
    assert "render-runtime.js" in runner, "runner does not guard render-runtime.js"
    assert "crab.js" in runner, "runner does not guard crab.js"
    assert "crab-scene.js" in runner, "runner does not guard crab-scene.js"


def test_harness_uses_production_single_html_iframe():
    assert 'src="/ocean-rescue/index.html"' in _html(), (
        "iframe does not load production HTML"
    )
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


def test_uses_canonical_rock_one():
    assert "crab.Layout.rocks[0]" in _mjs(), "canonical Layout.rocks[0] not used"


def test_no_hardcoded_rock_coordinates():
    mjs = _mjs()
    for literal in ("870", "1030", "420", "500", "560", "240", "390", "330", "215"):
        assert literal not in mjs, f"hardcoded coordinate literal {literal} found"
    for token in (
        "rock.start.x",
        "rock.start.y",
        "rock.placed.x",
        "rock.placed.y",
    ):
        assert token in mjs, f"canonical coordinate token {token} missing"


def test_uses_public_crab_api_only():
    mjs = _mjs()
    for api in CRAB_APIS:
        assert api in mjs, f"public Crab API {api} missing"
    assert "crab.state" not in mjs, "internal Crab state accessed"
    assert "crab.completedRockIds" not in mjs, "internal Crab state accessed"


def test_uses_public_crab_scene_api_only():
    mjs = _mjs()
    for api in SCENE_APIS:
        assert api in mjs, f"public CrabScene API {api} missing"
    assert "scene.nodes" not in mjs, "internal scene graph accessed"


def test_geometry_contract_assertions_exist():
    mjs = _mjs()
    assert "startIntersectsDropZone" in mjs, "start/drop-zone check missing"
    assert "placedInsideDropZone" in mjs, "placed/drop-zone check missing"
    assert "startPressesCrab" in mjs, "start/crab check missing"
    assert "placedClearOfCrab" in mjs, "placed/crab check missing"


def test_initial_state_assertions_exist():
    runner = _runner()
    assert "initial.activeRockId" in runner, "initial activeRockId assertion missing"
    assert "initial.completedCount" in runner, (
        "initial completedCount assertion missing"
    )
    assert '"trapped"' in runner, "trapped crab state assertion missing"
    assert "initial.legacyBridgeVisible" in runner, "initial bridge assertion missing"
    assert "initial.missingAliases" in runner, "missing aliases assertion missing"


def test_relief_one_assertion_exists():
    assert '"relief-1"' in _runner(), "relief-1 assertion missing"


def test_free_assertion_exists():
    assert '"free"' in _runner(), "free assertion missing"


def test_rock_two_and_three_assertions_exist():
    runner = _runner()
    assert '"rock-2"' in runner, "rock-2 assertion missing"
    assert '"rock-3"' in runner, "rock-3 assertion missing"


def test_legacy_bridge_transition_assertions_exist():
    runner = _runner()
    assert "initial.legacyBridgeVisible" in runner, "initial bridge assertion missing"
    assert "afterFirstRock.legacyBridgeVisible" in runner, (
        "release bridge assertion missing"
    )
    assert "afterExit.legacyBridgeVisible" in runner, "exit bridge assertion missing"


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
    assert "crab-scene-runtime.mjs" in html, "local test module not referenced"


def test_runner_imports_backend_verifier_without_modifying():
    runner = _runner()
    assert "verify-pixi-backends.py" in runner, "existing verifier not reused"
    assert "spec_from_file_location" in runner, (
        "existing verifier not imported via spec"
    )
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
    assert "crab-scene-runtime.html" in runner, "runner does not target harness"


def test_runner_uses_virtual_time_budget():
    assert "--virtual-time-budget=12000" in _runner(), "virtual time budget missing"


def test_runner_keeps_native_backend_defaults():
    runner = _runner()
    assert "--disable-webgl" not in runner, "WebGL disabled in normal runtime"
    assert "--disable-gpu" not in runner, "GPU disabled in normal runtime"
    assert "--disable-software-rasterizer" not in runner, "software rasterizer disabled"


def test_runner_guards_main():
    assert '__name__ == "__main__"' in _runner(), "main not guarded"


def test_runner_has_argparse_backend_and_flow_choices():
    runner = _runner()
    assert "argparse" in runner, "argparse missing"
    assert '"--backend"' in runner, "backend CLI option missing"
    assert '"--flow"' in runner, "flow CLI option missing"
    assert 'choices=("auto", "canvas")' in runner, "backend choices missing"
    assert 'choices=("first-rock", "complete")' in runner, "flow choices missing"


def test_runner_defaults_are_auto_and_first_rock():
    runner = _runner()
    assert 'default="auto"' in runner, "backend default != auto"
    assert 'default="first-rock"' in runner, "flow default != first-rock"


def test_complete_flow_query_passed_to_harness():
    runner = _runner()
    assert 'args.flow == "complete"' in runner, "complete flow branch missing"
    assert '"?flow=complete"' in runner, "complete flow query not appended"


def test_complete_flow_loops_three_rocks_in_order():
    mjs = _mjs()
    assert "for (let i = 0; i < 3; i += 1)" in mjs, "three-rock loop missing"
    runner = _runner()
    assert '["rock-1", "rock-2", "rock-3"]' in runner, "expected rock order missing"


def test_crab_stage_progression_assertions_exist():
    runner = _runner()
    assert '"relief-1"' in runner, "relief-1 assertion missing"
    assert '"relief-2"' in runner, "relief-2 assertion missing"
    assert '"free"' in runner, "free assertion missing"


def test_final_domain_assertions_exist():
    runner = _runner()
    assert "finalDomain.complete" in runner, "final complete assertion missing"
    assert "finalDomain.active" in runner, "final active=false assertion missing"
    assert "finalDomain.activeRockId" in runner, "final activeRockId assertion missing"
    assert "finalDomain.completedRockIds" in runner, (
        "final completed ids assertion missing"
    )
    assert "beforeExit.crabState" in runner, "beforeExit crab state assertion missing"
    assert "afterExit.legacyBridgeVisible" in runner, (
        "legacy bridge restoration assertion missing"
    )


def test_geometry_evidence_collected():
    mjs = _mjs()
    assert "computeGeometry" in mjs, "geometry computation missing"
    assert "crabCenter" in mjs, "crab center geometry missing"
    assert "dropZoneRect" in mjs, "drop zone rect geometry missing"
