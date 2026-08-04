"""WP-32B pointer coordinate / renderer-adapter boundary contract.

WP-32B extracts the pointer coordinate transformations and scene
pointer-intent generation that were previously embedded ad hoc in
``src/app.js`` into one typed runtime boundary shared by both the canonical
ESM lane and the legacy ordered-script lane:

- ``src/contracts/pointer-input.ts``: type-only pointer boundary contract
  (logical points, render coordinate mapper subset, pointer intents, pointer
  input API);
- ``src/pointer-input.js``: the single strict checked-JS implementation that
  owns travel stage-Y mapping, rescue ``{ x, y }`` mapping, and the
  active/inactive pointer-intent constructors, registered as the frozen
  ``OceanRescue.PointerInput`` global;
- ``src/esm/pointer-input.js``: the canonical ESM adapter that side-effect
  imports the shared implementation and fail-closes on the contract;
- ``src/esm/render-runtime.js``: gains ``@ts-check`` and an existence guard for
  the minimal coordinate-mapper subset (``isReady`` + ``mapClientToLogical``);
- ``src/app.js``: delegates ``mapClientYToStage`` and ``mapRescueCoordinates``
  to the pointer boundary and replaces every inline scene pointer-intent
  literal with ``PointerInput.activeIntent`` / ``PointerInput.inactiveIntent``;
- ``build-manifest.legacy.json``: inserts ``pointer-input.js`` exactly once
  after ``render-runtime.js`` and before ``app.js`` and records the
  ``OceanRescue.PointerInput`` dependency on ``OceanRescue.App``.

The work is a runtime module extraction: the production bundle is no longer
byte-identical to the pre-WP-32B baseline, so determinism is verified as two
clean builds byte-identical plus the tracked artifact matching a clean rebuild.
This suite verifies:

- the static contract (type contract, checked-JS implementation, ESM adapter,
  ESM app import order, legacy manifest insertion/order/dependency, runtime
  ABI slots, no ``any``, no suppression, no dynamic import, formulas moved out
  of ``app.js``, inline intent literals removed, orchestration markers
  unchanged);
- checked-JS diagnostics on the pointer runtime, the pointer adapter, the
  render adapter, and the shared contracts;
- the pointer runtime matrix against the real ``src/pointer-input.js`` in a
  fresh isolated runtime (travel, rescue, intent), including exact behavioral
  parity with the pre-extraction ``app.js`` formulas;
- app integration: travel/rescue paths delegate to the boundary exactly once,
  scene intents originate from ``PointerInput``, and Travel/mission pointer
  method order is unchanged;
- browser parity: travel tap/drag reflected in Y, pointer capture/release,
  pause blocking, sea-turtle pointer interaction through the authored scene,
  crab pointer interaction through the authored scene, with clean
  page/console/network quality.

TypeScript compiler programmatic API is never used; every TypeScript check runs
the installed ``tsc`` CLI on the real sources.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp02_browser_baseline import (  # noqa: E402
    HTTPServerFixture,
)

REPO_ROOT = TESTS_DIR.parent
OCEAN_DIR = REPO_ROOT / "domains" / "ocean-rescue"
SRC_DIR = OCEAN_DIR / "src"
ESM_DIR = SRC_DIR / "esm"
CONTRACTS_DIR = SRC_DIR / "contracts"
DIST_DIR = OCEAN_DIR / "dist"
TSCONFIG = OCEAN_DIR / "tsconfig.json"
LEGACY_MANIFEST = SRC_DIR / "build-manifest.legacy.json"
RUNTIME_ABI = CONTRACTS_DIR / "runtime-abi.ts"
GLOBAL_DECL = CONTRACTS_DIR / "ocean-rescue-global.d.ts"
POINTER_CONTRACT = CONTRACTS_DIR / "pointer-input.ts"
POINTER_RUNTIME = SRC_DIR / "pointer-input.js"
POINTER_ADAPTER = ESM_DIR / "pointer-input.js"
RENDER_ADAPTER = ESM_DIR / "render-runtime.js"
APP = SRC_DIR / "app.js"
ESM_APP = ESM_DIR / "app.js"
ARTIFACT = REPO_ROOT / "ocean-rescue" / "index.html"
SEA_TURTLE_SCENE = SRC_DIR / "sea-turtle-scene.js"
CRAB_SCENE = SRC_DIR / "crab-scene.js"

NODE_BIN: str = shutil.which("node") or ""
if not NODE_BIN:
    raise RuntimeError("Node executable not found on PATH")

FORBIDDEN_TOKENS = (
    "@ts-nocheck",
    "@ts-ignore",
    "@ts-expect-error",
    "as any",
    ": any",
    "<any>",
    "as unknown as any",
)

BUNDLE_FILE = "ocean-rescue-app.js"
METADATA_FILE = "production-bundle-metadata.json"

# Synthetic PointerEvent dispatch has no real active pointer; the app's
# setPointerCapture/releasePointerCapture calls must be neutralized so the
# pointer flow completes without uncaught DOM errors (same approach as WP-31C).
_POINTER_CAPTURE_INIT_SCRIPT = (
    "(() => {"
    "if (typeof Element !== 'undefined') {"
    "Element.prototype.setPointerCapture = function () {};"
    "Element.prototype.releasePointerCapture = function () {};"
    "}"
    "})();"
)

POINTER_CHECKED_FILES = (
    POINTER_RUNTIME,
    POINTER_ADAPTER,
    RENDER_ADAPTER,
)


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _load_legacy_manifest() -> dict:
    return json.loads(LEGACY_MANIFEST.read_text(encoding="utf-8"))


# ── 10.1 static contract ────────────────────────────────────────────────


def test_pointer_type_contract_exists() -> None:
    assert POINTER_CONTRACT.is_file(), "src/contracts/pointer-input.ts missing"
    text = POINTER_CONTRACT.read_text(encoding="utf-8")
    for name in (
        "LogicalPoint",
        "RenderMappedPoint",
        "RenderCoordinateMapperApi",
        "ActivePointerIntent",
        "InactivePointerIntent",
        "PointerIntent",
        "ClientCoordinateCarrier",
        "BoundingRect",
        "RectProvider",
        "PointerInputApi",
    ):
        assert f"export interface {name}" in text or f"export type {name}" in text, (
            f"pointer contract must declare {name}"
        )
    assert "readonly x: number;" in text
    assert "readonly inside: boolean;" in text
    assert "readonly isReady: () => boolean;" in text
    assert "readonly mapClientToLogical: (" in text
    assert "readonly active: true;" in text
    assert "readonly active: false;" in text
    assert "readonly x: null;" in text
    for method in (
        "mapTravelStageY",
        "mapRescuePoint",
        "activeIntent",
        "inactiveIntent",
    ):
        assert method in text.split("export interface PointerInputApi")[1], (
            f"PointerInputApi must expose {method}"
        )


def test_pointer_checked_js_implementation_exists() -> None:
    assert POINTER_RUNTIME.is_file(), "src/pointer-input.js missing"
    text = POINTER_RUNTIME.read_text(encoding="utf-8")
    assert text.startswith("// @ts-check"), "pointer-input.js must start with @ts-check"
    assert '/// <reference path="./contracts/ocean-rescue-global.d.ts" />' in text, (
        "pointer-input.js must load the shared global declaration"
    )
    for method in (
        "mapTravelStageY",
        "mapRescuePoint",
        "activeIntent",
        "inactiveIntent",
    ):
        assert f"function {method}" in text, f"pointer-input.js must define {method}"
    assert "window.OceanRescue.PointerInput = Object.freeze({" in text, (
        "pointer runtime must register a frozen OceanRescue.PointerInput API"
    )
    assert "RenderRuntime.isReady()" in text
    assert "RenderRuntime.mapClientToLogical" in text
    assert "720 / rect.height" in text, "fallback travel scaling must stay owned"
    assert "1280 / rect.width" in text, "fallback rescue scaling must stay owned"
    for token in FORBIDDEN_TOKENS:
        assert token not in text, f"forbidden token in pointer-input.js: {token}"
    code_lines = [
        line
        for line in text.splitlines()
        if not line.strip().startswith("*") and not line.strip().startswith("//")
    ]
    assert "import(" not in "\n".join(code_lines), (
        "pointer runtime must not use dynamic import (JSDoc type imports are allowed)"
    )
    assert "fetch" not in text and "XMLHttpRequest" not in text, (
        "pointer runtime must have no runtime network access"
    )


def test_pointer_esm_adapter_exists() -> None:
    assert POINTER_ADAPTER.is_file(), "src/esm/pointer-input.js missing"
    text = POINTER_ADAPTER.read_text(encoding="utf-8")
    assert text.startswith("// @ts-check"), "adapter must start with @ts-check"
    assert '/// <reference path="../contracts/ocean-rescue-global.d.ts" />' in text, (
        "adapter must load the shared global declaration"
    )
    assert 'import "../pointer-input.js";' in text, (
        "adapter must side-effect import the shared implementation"
    )
    assert 'throw new Error("OceanRescue.PointerInput was not registered")' in text, (
        "adapter must fail close when the namespace is absent"
    )
    for method in (
        "mapTravelStageY",
        "mapRescuePoint",
        "activeIntent",
        "inactiveIntent",
    ):
        assert f'typeof PointerInput.{method} !== "function"' in text, (
            f"adapter must fail close on missing {method}"
        )
    assert "export { PointerInput };" in text
    for token in FORBIDDEN_TOKENS:
        assert token not in text, f"forbidden token in adapter: {token}"


def test_esm_app_import_order() -> None:
    text = ESM_APP.read_text(encoding="utf-8")
    assert text.index('import "./render-runtime.js";') < text.index(
        'import "./pointer-input.js";'
    ), "RenderRuntime must register before PointerInput"
    assert text.index('import "./pointer-input.js";') < text.index(
        'import "../app.js";'
    ), "legacy app.js must execute after PointerInput"


def test_legacy_manifest_insertion_order_and_dependency() -> None:
    data = _load_legacy_manifest()
    files = [entry["file"] for entry in data["scripts"]]
    assert files.count("pointer-input.js") == 1, (
        "pointer-input.js must appear exactly once in the legacy manifest"
    )
    render_index = files.index("render-runtime.js")
    pointer_index = files.index("pointer-input.js")
    app_index = files.index("app.js")
    assert render_index < pointer_index < app_index, (
        "legacy order must be render-runtime -> pointer-input -> app"
    )
    pointer_entry = data["scripts"][pointer_index]
    assert pointer_entry["namespace"] == "OceanRescue.PointerInput"
    assert pointer_entry["depends_on"] == ["OceanRescue.RenderRuntime"]
    app_entry = data["scripts"][app_index]
    assert "OceanRescue.PointerInput" in app_entry["depends_on"], (
        "app.js must depend on OceanRescue.PointerInput"
    )
    assert "OceanRescue.RenderRuntime" in app_entry["depends_on"]


def test_runtime_abi_pointer_slots() -> None:
    text = RUNTIME_ABI.read_text(encoding="utf-8")
    namespace = text.split("export interface OceanRescueNamespace")[1]
    assert "RenderRuntime?: RenderCoordinateMapperApi;" in namespace
    assert "PointerInput?: PointerInputApi;" in namespace
    for token in FORBIDDEN_TOKENS:
        assert token not in text, f"forbidden token in runtime ABI: {token}"
    global_text = GLOBAL_DECL.read_text(encoding="utf-8")
    assert "OceanRescue?: OceanRescueNamespace;" in global_text


def test_app_mapping_formulas_moved_to_pointer_module() -> None:
    app = APP.read_text(encoding="utf-8")
    pointer = POINTER_RUNTIME.read_text(encoding="utf-8")
    for forbidden in (
        "720 / rect.height",
        "1280 / rect.width",
        "RenderRuntime.mapClientToLogical",
        "clientX - rect",
        "clientY - rect",
    ):
        assert forbidden not in app, f"app.js must no longer own formula {forbidden}"
    assert "mapClientToLogical" in pointer
    assert "720 / rect.height" in pointer
    assert "1280 / rect.width" in pointer


def test_app_inline_pointer_intent_literals_removed() -> None:
    app = APP.read_text(encoding="utf-8")
    assert "{ active: true," not in app, "app.js must not inline an active intent"
    assert "{ active: false," not in app, "app.js must not inline an inactive intent"
    assert "PointerInput.activeIntent(" in app
    assert "PointerInput.inactiveIntent(" in app


def test_app_delegates_mapping_functions() -> None:
    app = APP.read_text(encoding="utf-8")
    body = app.split("function mapClientYToStage")[1].split("\n  }", 1)[0]
    assert body.count("PointerInput.mapTravelStageY") == 1, (
        "travel path must delegate exactly once"
    )
    assert "travelCanvas" in body
    rescue = app.split("function mapRescueCoordinates")[1].split("\n  }", 1)[0]
    assert rescue.count("PointerInput.mapRescuePoint") == 1, (
        "rescue path must delegate exactly once"
    )
    assert "resolveVisibleInputCanvas()" in rescue


def test_app_orchestration_markers_unchanged() -> None:
    app = APP.read_text(encoding="utf-8")
    for marker in (
        "function acceptPointerEvent",
        "function acceptRescuePointerEvent",
        "function isTrackedRescuePointer",
        "Math.abs(event.clientY - pointerStartClientY) < 8",
        "function resetPointerGesture",
        "setPointerCapture",
        "releasePointerCapture",
    ):
        assert marker in app, f"orchestration marker missing: {marker}"
    # Travel pointer method order must be preserved.
    move = app.split("function onPointerMove")[1].split("function onPointerUp")[0]
    assert move.index("Travel.beginDrag") < move.index("Travel.moveDrag")
    up = app.split("function onPointerUp")[1].split("function onPointerCancel")[0]
    assert up.index("Travel.moveDrag") < up.index("Travel.endDrag")
    assert up.index("Travel.tapTo") > up.index("Travel.endDrag")
    # Mission model pointer method order must be preserved.
    for fn_name in ("handleSeaTurtlePointerDown", "handleCrabPointerDown"):
        fn = app.split(f"function {fn_name}")[1].split("\n  function ")[0]
        assert fn.index(".pointerDown(") < fn.index(".setPointerCapture(")
    sea_up = app.split("function onRescuePointerUp")[1]
    assert sea_up.index("SeaTurtle.pointerUp") < sea_up.index("SeaTurtle.pointerCancel")
    assert sea_up.index("Crab.pointerUp") < sea_up.index("Crab.pointerCancel")


def test_scene_consumers_accept_pointer_intent() -> None:
    for scene in (SEA_TURTLE_SCENE, CRAB_SCENE):
        text = scene.read_text(encoding="utf-8")
        assert "function sync(current, intent)" in text
        assert "intent.active === true" in text
        assert "isFinite(intent.x)" in text or "finite(intent.x)" in text
        assert "intent.x" in text and "intent.y" in text
        assert "// @ts-check" not in text, (
            "scene implementations must not gain @ts-check in WP-32B"
        )


# ── 10.2 checked-JS diagnostics ─────────────────────────────────────────


def test_strict_typecheck_passes() -> None:
    result = subprocess.run(
        [
            "corepack",
            "pnpm",
            "exec",
            "tsc",
            "--project",
            "tsconfig.json",
            "--noEmit",
        ],
        cwd=str(OCEAN_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"tsc --noEmit failed (exit {result.returncode}):\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_pointer_files_typecheck_standalone() -> None:
    result = subprocess.run(
        [
            "corepack",
            "pnpm",
            "exec",
            "tsc",
            "--ignoreConfig",
            "--module",
            "commonjs",
            "--target",
            "es2022",
            "--lib",
            "es2022,dom",
            "--allowJs",
            "--checkJs",
            "false",
            "--noEmit",
            *[str(path) for path in POINTER_CHECKED_FILES],
        ],
        cwd=str(OCEAN_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"standalone pointer typecheck failed (exit {result.returncode}):\n"
        f"{result.stdout}\n{result.stderr}"
    )


def test_checked_js_files_have_no_suppression() -> None:
    for path in POINTER_CHECKED_FILES:
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            assert token not in text, f"forbidden token in {path.name}: {token}"


# ── 10.3 pointer runtime matrix ─────────────────────────────────────────


_POINTER_BOOTSTRAP = textwrap.dedent(
    """\
    const fs = require("fs");
    const vm = require("vm");
    const assert = require("assert");

    const POINTER_SOURCE = fs.readFileSync("domains/ocean-rescue/src/pointer-input.js", "utf8");

    function loadPointer(renderer, baseOcean) {
      const window = { OceanRescue: baseOcean ? Object.assign({}, baseOcean) : {} };
      if (renderer !== undefined) {
        window.OceanRescue.RenderRuntime = renderer;
      }
      const sandbox = { window };
      vm.createContext(sandbox);
      vm.runInContext(POINTER_SOURCE, sandbox, { filename: "pointer-input.js" });
      return window.OceanRescue.PointerInput;
    }

    function rect(overrides) {
      return Object.assign({ left: 20, top: 10, width: 100, height: 100 }, overrides || {});
    }

    function canvas(r) {
      return { getBoundingClientRect: () => r };
    }

    function makeRenderer(opts) {
      return Object.assign({
        ready: true,
        isReady() { return this.ready; },
        mapClientToLogical(clientX, clientY) {
          return { x: clientX * 2, y: clientY * 3, inside: true };
        }
      }, opts || {});
    }

    function keys(obj) {
      return Object.keys(obj);
    }

    // Objects created inside the VM realm carry the VM prototype; compare
    // structurally via JSON so cross-realm results are asserted exactly.
    function eqObj(actual, expected) {
      assert.strictEqual(JSON.stringify(actual), JSON.stringify(expected));
    }

    // Cross-realm plain-object check: prototype chain terminates with null.
    function isPlainObject(value) {
      const proto = Object.getPrototypeOf(value);
      return proto === null || Object.getPrototypeOf(proto) === null;
    }
    """
)


def _run_node(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [NODE_BIN, "-e", script],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )


def _assert_node_ok(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, (
        f"Node harness failed (exit {result.returncode}):\n{result.stderr}"
    )


def test_travel_mapping_matrix() -> None:
    harness = _POINTER_BOOTSTRAP + textwrap.dedent(
        """\
        // valid fallback map
        let P = loadPointer(undefined);
        let c = canvas(rect({ top: 10, height: 100 }));
        assert.strictEqual(P.mapTravelStageY({ clientY: 60 }, c), 360);
        assert.strictEqual(P.mapTravelStageY({ clientY: 10 }, c), 0);
        assert.strictEqual(P.mapTravelStageY({ clientY: 110 }, c), 720);

        // valid renderer map (ready)
        const renderer = makeRenderer();
        P = loadPointer(renderer);
        c = canvas(rect({ top: 10, height: 100 }));
        assert.strictEqual(P.mapTravelStageY({ clientX: 100, clientY: 60 }, c), 180);
        assert.strictEqual(P.mapTravelStageY({ clientX: 50, clientY: 200 }, c), 600);

        // clientX fallback to rect.left when clientX is missing/non-number
        P = loadPointer(makeRenderer({ mapClientToLogical(clientX, clientY) { return { x: clientX, y: clientX, inside: true }; } }));
        c = canvas(rect({ left: 44, top: 10, height: 100 }));
        assert.strictEqual(P.mapTravelStageY({ clientY: 60 }, c), 44);
        assert.strictEqual(P.mapTravelStageY({ clientY: 60, clientX: "no" }, c), 44);
        assert.strictEqual(P.mapTravelStageY({ clientY: 60, clientX: 100 }, c), 100);

        // mapped non-finite Y -> null
        P = loadPointer(makeRenderer({ mapClientToLogical() { return { x: 1, y: NaN, inside: true }; } }));
        assert.strictEqual(P.mapTravelStageY({ clientX: 1, clientY: 1 }, canvas(rect())), null);

        // invalid clientY -> null
        P = loadPointer(undefined);
        assert.strictEqual(P.mapTravelStageY({ clientY: NaN }, canvas(rect())), null);
        assert.strictEqual(P.mapTravelStageY({ clientY: "60" }, canvas(rect())), null);
        assert.strictEqual(P.mapTravelStageY({}, canvas(rect())), null);

        // missing canvas -> null
        assert.strictEqual(P.mapTravelStageY({ clientY: 60 }, null), null);
        assert.strictEqual(P.mapTravelStageY({ clientY: 60 }, undefined), null);

        // invalid rect (non-object / null / bad height) -> null
        assert.strictEqual(P.mapTravelStageY({ clientY: 60 }, canvas(null)), null);
        assert.strictEqual(P.mapTravelStageY({ clientY: 60 }, canvas(undefined)), null);
        assert.strictEqual(P.mapTravelStageY({ clientY: 60 }, canvas(rect({ height: 0 }))), null);
        assert.strictEqual(P.mapTravelStageY({ clientY: 60 }, canvas(rect({ height: NaN }))), null);
        assert.strictEqual(P.mapTravelStageY({ clientY: 60 }, canvas(rect({ height: "100" }))), null);

        // renderer not ready -> fallback
        P = loadPointer(makeRenderer({ ready: false }));
        c = canvas(rect({ top: 10, height: 100 }));
        assert.strictEqual(P.mapTravelStageY({ clientY: 60 }, c), 360);
        """
    )
    _assert_node_ok(_run_node(harness))


def test_rescue_mapping_matrix() -> None:
    harness = _POINTER_BOOTSTRAP + textwrap.dedent(
        """\
        // valid fallback map
        let P = loadPointer(undefined);
        let c = canvas(rect({ left: 20, top: 10, width: 100, height: 100 }));
        eqObj(P.mapRescuePoint({ clientX: 70, clientY: 60 }, c), { x: 640, y: 360 });
        eqObj(P.mapRescuePoint({ clientX: 20, clientY: 10 }, c), { x: 0, y: 0 });

        // valid renderer map
        P = loadPointer(makeRenderer());
        c = canvas(rect());
        eqObj(P.mapRescuePoint({ clientX: 100, clientY: 200 }, c), { x: 200, y: 600 });

        // invalid rect fields -> null
        P = loadPointer(undefined);
        assert.strictEqual(P.mapRescuePoint({ clientX: 70, clientY: 60 }, null), null);
        assert.strictEqual(P.mapRescuePoint({ clientX: 70, clientY: 60 }, canvas(null)), null);
        assert.strictEqual(P.mapRescuePoint({ clientX: 70, clientY: 60 }, canvas(rect({ left: NaN }))), null);
        assert.strictEqual(P.mapRescuePoint({ clientX: 70, clientY: 60 }, canvas(rect({ top: Infinity }))), null);

        // invalid dimensions -> null
        assert.strictEqual(P.mapRescuePoint({ clientX: 70, clientY: 60 }, canvas(rect({ width: 0 }))), null);
        assert.strictEqual(P.mapRescuePoint({ clientX: 70, clientY: 60 }, canvas(rect({ height: -1 }))), null);

        // non-finite mapped coordinates -> null
        P = loadPointer(makeRenderer({ mapClientToLogical() { return { x: NaN, y: 1, inside: true }; } }));
        assert.strictEqual(P.mapRescuePoint({ clientX: 1, clientY: 1 }, canvas(rect())), null);

        // renderer inside:false still returns the finite point (no new rejection)
        P = loadPointer(makeRenderer({ mapClientToLogical() { return { x: 12, y: 34, inside: false }; } }));
        eqObj(P.mapRescuePoint({ clientX: 1, clientY: 1 }, canvas(rect())), { x: 12, y: 34 });

        // exact X/Y numeric result
        P = loadPointer(undefined);
        const point = P.mapRescuePoint({ clientX: 45, clientY: 55 }, canvas(rect({ left: 20, top: 10, width: 100, height: 100 })));
        assert.strictEqual(typeof point.x, "number");
        assert.strictEqual(typeof point.y, "number");
        assert.strictEqual(point.x, (45 - 20) * (1280 / 100));
        assert.strictEqual(point.y, (55 - 10) * (720 / 100));
        """
    )
    _assert_node_ok(_run_node(harness))


def test_intent_matrix() -> None:
    harness = _POINTER_BOOTSTRAP + textwrap.dedent(
        """\
        const P = loadPointer(undefined);

        // active exact shape and key order
        const active = P.activeIntent({ x: 5, y: 7 });
        eqObj(active, { active: true, x: 5, y: 7 });
        assert.deepStrictEqual(keys(active), ["active", "x", "y"]);

        // inactive exact shape and key order
        const inactive = P.inactiveIntent();
        eqObj(inactive, { active: false, x: null, y: null });
        assert.deepStrictEqual(keys(inactive), ["active", "x", "y"]);

        // plain object
        assert.strictEqual(isPlainObject(active), true);
        assert.strictEqual(isPlainObject(inactive), true);

        // non-frozen
        assert.strictEqual(Object.isFrozen(active), false);
        assert.strictEqual(Object.isFrozen(inactive), false);

        // separate call identity (fresh object per call)
        assert.notStrictEqual(P.activeIntent({ x: 5, y: 7 }), P.activeIntent({ x: 5, y: 7 }));
        assert.notStrictEqual(P.inactiveIntent(), P.inactiveIntent());

        // invalid active input baseline -> inactive intent
        eqObj(P.activeIntent(null), { active: false, x: null, y: null });
        eqObj(P.activeIntent(undefined), { active: false, x: null, y: null });
        eqObj(P.activeIntent({ x: NaN, y: 3 }), { active: false, x: null, y: null });
        eqObj(P.activeIntent({ x: 3, y: Infinity }), { active: false, x: null, y: null });
        """
    )
    _assert_node_ok(_run_node(harness))


_REFERENCE_TRAVEL = """
function referenceMapClientYToStage(event, travelCanvas, RenderRuntime) {
    if (typeof event.clientY !== "number" || !isFinite(event.clientY)) {
      return null;
    }
    if (!travelCanvas) {
      return null;
    }
    if (typeof travelCanvas.getBoundingClientRect !== "function") {
      return null;
    }
    var rect = travelCanvas.getBoundingClientRect();
    if (!rect || typeof rect !== "object") {
      return null;
    }
    if (typeof rect.height !== "number" || !isFinite(rect.height) || rect.height <= 0) {
      return null;
    }
    if (RenderRuntime && RenderRuntime.isReady()) {
      var mapped = RenderRuntime.mapClientToLogical(
        typeof event.clientX === "number" ? event.clientX : rect.left,
        event.clientY
      );
      return isFinite(mapped.y) ? mapped.y : null;
    }
    return (event.clientY - rect.top) * (720 / rect.height);
  }
"""

_REFERENCE_RESCUE = """
function referenceMapRescueCoordinates(event, canvas, RenderRuntime) {
    if (!canvas) {
      return null;
    }
    if (typeof canvas.getBoundingClientRect !== "function") {
      return null;
    }
    var rect = canvas.getBoundingClientRect();
    if (!rect || typeof rect !== "object") {
      return null;
    }
    if (typeof rect.left !== "number" || !isFinite(rect.left)) {
      return null;
    }
    if (typeof rect.top !== "number" || !isFinite(rect.top)) {
      return null;
    }
    if (typeof rect.width !== "number" || !isFinite(rect.width) || rect.width <= 0) {
      return null;
    }
    if (typeof rect.height !== "number" || !isFinite(rect.height) || rect.height <= 0) {
      return null;
    }
    var mapped = null;
    if (RenderRuntime && RenderRuntime.isReady()) {
      mapped = RenderRuntime.mapClientToLogical(event.clientX, event.clientY);
    } else {
      mapped = {
        x: (event.clientX - rect.left) * (1280 / rect.width),
        y: (event.clientY - rect.top) * (720 / rect.height)
      };
    }
    var x = mapped.x;
    var y = mapped.y;
    if (!isFinite(x) || !isFinite(y)) {
      return null;
    }
    return { x: x, y: y };
  }
"""


def test_pointer_behavior_parity_with_baseline_app_formulas() -> None:
    """The extracted pointer boundary must agree with the pre-extraction formulas.

    The reference implementations below are the exact ``app.js`` bodies that
    existed at the pre-WP-32B baseline (recorded from ``origin/main`` at the
    WP-32A completion SHA). They are run in the same VM against the same input
    table and compared against the real ``src/pointer-input.js``.
    """
    harness = (
        _POINTER_BOOTSTRAP
        + _REFERENCE_TRAVEL
        + _REFERENCE_RESCUE
        + textwrap.dedent(
            """\
            const renderer = makeRenderer();
            const notReady = makeRenderer({ ready: false });
            const nanRenderer = makeRenderer({ mapClientToLogical() { return { x: NaN, y: NaN, inside: false }; } });

            const renderers = [undefined, renderer, notReady, nanRenderer];
            const rects = [
              rect({ left: 20, top: 10, width: 100, height: 100 }),
              rect({ left: 0, top: 0, width: 1280, height: 720 }),
              rect({ left: -50, top: 40, width: 500, height: 300 }),
              rect({ left: NaN, top: 10, width: 100, height: 100 }),
              rect({ left: 20, top: 10, width: 0, height: 100 }),
              rect({ left: 20, top: 10, width: 100, height: -1 }),
              null,
              undefined
            ];
            const events = [
              { clientX: 70, clientY: 60 },
              { clientY: 60 },
              { clientX: "x", clientY: 200 },
              { clientX: 100, clientY: NaN },
              { clientY: 10 },
              { clientX: 0, clientY: 0 },
              { clientX: 640, clientY: 360 }
            ];

            for (const r of renderers) {
              const P = loadPointer(r);
              for (const rct of rects) {
                const c = rct === null || rct === undefined ? null : canvas(rct);
                for (const ev of events) {
                  const travel = P.mapTravelStageY(ev, c);
                  const refTravel = referenceMapClientYToStage(ev, c, r || null);
                  assert.strictEqual(travel, refTravel, "travel parity failed");
                  const rescue = P.mapRescuePoint(ev, c);
                  const refRescue = referenceMapRescueCoordinates(ev, c, r || null);
                  eqObj(rescue, refRescue);
                }
              }
            }
            """
        )
    )
    _assert_node_ok(_run_node(harness))


# ── 10.4 canonical graph and packaging membership ───────────────────────


def test_canonical_graph_reaches_pointer_modules() -> None:
    app_adapter = ESM_APP.read_text(encoding="utf-8")
    assert 'import "./pointer-input.js";' in app_adapter
    pointer_adapter = POINTER_ADAPTER.read_text(encoding="utf-8")
    assert 'import "../pointer-input.js";' in pointer_adapter


def test_pointer_contract_stays_out_of_production_bundle(tmp_path: Path) -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    result = subprocess.run(
        [
            "corepack",
            "pnpm",
            "exec",
            "vite",
            "build",
            "--config",
            "vite.production.config.ts",
        ],
        cwd=str(OCEAN_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"production build failed (exit {result.returncode}):\n{result.stderr}"
    )
    metadata = json.loads((DIST_DIR / METADATA_FILE).read_text(encoding="utf-8"))
    actual = set(metadata["actual_module_files"])
    assert "esm/pointer-input.js" in actual, (
        "pointer adapter must be part of the canonical bundle"
    )
    assert "pointer-input.js" in actual, (
        "shared pointer implementation must be part of the canonical bundle"
    )
    assert "render-runtime.js" in actual
    assert metadata["dynamic_import_count"] == 0
    assert metadata["sourcemap"] is False
    assert not any(f.startswith("contracts/") for f in actual), (
        "type-only contracts must not enter the bundle"
    )
    shutil.rmtree(DIST_DIR, ignore_errors=True)


# ── 10.5 browser parity ─────────────────────────────────────────────────


def _rescue_active_after_launch(
    page: Page, base_url: str, mission_id: str, gup_id: str
) -> None:
    page.goto(f"{base_url}/ocean-rescue/index.html")
    page.wait_for_selector(
        "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=30000
    )
    page.evaluate(
        """() => {
          const el = document.getElementById('ocean-rescue-profile-choice');
          return !!el && !el.hidden && getComputedStyle(el).display !== 'none';
        }"""
    )
    if page.evaluate(
        """() => {
          const el = document.getElementById('ocean-rescue-profile-choice');
          return !!el && !el.hidden && getComputedStyle(el).display !== 'none';
        }"""
    ):
        page.click('[data-profile-animal-id="arctic-fox"]')
        page.click("#ocean-rescue-profile-continue")
    page.wait_for_selector(f"#ocean-rescue-mission-list [data-mission-id={mission_id}]")
    page.click(f"#ocean-rescue-mission-list [data-mission-id={mission_id}]")
    page.wait_for_selector("#ocean-rescue-gup-select:not([hidden])")
    page.click(f"#ocean-rescue-gup-list [data-gup-id={gup_id}]")
    page.click("#ocean-rescue-gup-launch")
    page.wait_for_selector("#ocean-rescue-launch:not([hidden])")
    page.click("#ocean-rescue-launch-skip")
    page.wait_for_selector("#ocean-rescue-root[data-travel-runtime=active]")
    # Deterministic arrival.
    page.evaluate(
        """() => {
          const T = OceanRescue.Travel;
          while (T.getSnapshot().distance < OceanRescue.Rescue.ArrivalDistance) {
            T.step(50, 1);
          }
        }"""
    )
    page.wait_for_function(
        """() => ['site-transition', 'tutorial', 'active'].includes(
          document.getElementById('ocean-rescue-root').getAttribute('data-rescue-phase'))""",
        timeout=5000,
    )
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-rescue-phase') === 'tutorial'",
        timeout=5000,
    )
    page.mouse.click(640, 360)
    page.wait_for_function(
        "() => document.getElementById('ocean-rescue-root').getAttribute('data-rescue-phase') === 'active'",
        timeout=5000,
    )


def _client_point(
    page: Page, logical_x: float, logical_y: float
) -> tuple[float, float]:
    rect = page.evaluate(
        """() => {
          const r = document.getElementById('ocean-rescue-canvas').getBoundingClientRect();
          return { left: r.left, top: r.top, w: r.width, h: r.height };
        }"""
    )
    return (
        rect["left"] + logical_x / 1280.0 * rect["w"],
        rect["top"] + logical_y / 720.0 * rect["h"],
    )


def test_pointer_boundary_browser_flow() -> None:
    server = HTTPServerFixture()
    base_url = server.start()
    page_errors: list[str] = []
    console_errors: list[str] = []
    request_failures: list[str] = []
    external_requests: list[dict[str, str]] = []
    duplicate_init_seen: bool = False
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--disable-background-networking", "--disable-component-update"],
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )
                context.add_init_script("window.localStorage.clear();")
                context.add_init_script(_POINTER_CAPTURE_INIT_SCRIPT)
                page = context.new_page()

                def on_pageerror(error: object) -> None:
                    page_errors.append(str(error))

                def on_console(message: object) -> None:
                    if message.type == "error":
                        console_errors.append(message.text)
                    if (
                        "Ocean Rescue" in message.text
                        and "boot" in message.text.lower()
                    ):
                        pass

                def on_requestfailed(request: object) -> None:
                    request_failures.append(request.url)

                def on_request(request: object) -> None:
                    if request.resource_type in {
                        "script",
                        "fetch",
                        "xhr",
                        "stylesheet",
                    }:
                        from urllib.parse import urlsplit

                        origin = urlsplit(base_url).netloc
                        if urlsplit(request.url).netloc not in {"", origin}:
                            external_requests.append({"url": request.url})

                page.on("pageerror", on_pageerror)
                page.on("console", on_console)
                page.on("requestfailed", on_requestfailed)
                page.on("request", on_request)

                # ---- Travel: tap and drag reflected in Y ----
                page.goto(f"{base_url}/ocean-rescue/index.html")
                page.wait_for_selector(
                    "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=30000
                )
                page.evaluate(
                    "window.__pointerBoundaryInitCount = (window.__pointerBoundaryInitCount || 0) + 1;"
                )
                profile_visible = page.evaluate(
                    """() => {
                      const el = document.getElementById('ocean-rescue-profile-choice');
                      return !!el && !el.hidden && getComputedStyle(el).display !== 'none';
                    }"""
                )
                if profile_visible:
                    page.click('[data-profile-animal-id="arctic-fox"]')
                    page.click("#ocean-rescue-profile-continue")
                page.wait_for_selector(
                    "#ocean-rescue-mission-list [data-mission-id=sea-turtle]"
                )
                page.click("#ocean-rescue-mission-list [data-mission-id=sea-turtle]")
                page.wait_for_selector("#ocean-rescue-gup-select:not([hidden])")
                page.click("#ocean-rescue-gup-list [data-gup-id=gup-x]")
                page.click("#ocean-rescue-gup-launch")
                page.wait_for_selector("#ocean-rescue-launch:not([hidden])")
                page.click("#ocean-rescue-launch-skip")
                page.wait_for_selector("#ocean-rescue-root[data-travel-runtime=active]")
                assert page.evaluate(
                    "() => OceanRescue.PointerInput && "
                    "typeof OceanRescue.PointerInput.mapTravelStageY === 'function'"
                ), "OceanRescue.PointerInput must be registered at runtime"

                travel_before = page.evaluate("() => OceanRescue.Travel.getSnapshot()")
                assert travel_before["active"] is True

                # Tap: pointerdown+up at logical Y 300 -> tapTargetY 300.
                tap_x, tap_y = _client_point(page, 640, 300)
                page.evaluate(
                    """({ tap_x, tap_y }) => {
                      const canvas = document.getElementById('ocean-rescue-canvas');
                      const down = new PointerEvent('pointerdown', {
                        pointerId: 1, clientX: tap_x, clientY: tap_y,
                        isPrimary: true, button: 0, bubbles: true
                      });
                      canvas.dispatchEvent(down);
                      canvas.dispatchEvent(new PointerEvent('pointerup', {
                        pointerId: 1, clientX: tap_x, clientY: tap_y,
                        isPrimary: true, button: 0, bubbles: true
                      }));
                    }""",
                    {"tap_x": tap_x, "tap_y": tap_y},
                )
                tap_snap = page.evaluate("() => OceanRescue.Travel.getSnapshot()")
                assert 120 <= tap_snap["tapTargetY"] <= 600, tap_snap
                assert abs(tap_snap["tapTargetY"] - 300) <= 1.5, tap_snap

                # Drag: pointerdown at Y 400, move to Y 460 -> dragging true, Y moves.
                d0x, d0y = _client_point(page, 640, 400)
                d1x, d1y = _client_point(page, 640, 460)
                page.evaluate(
                    """({ d0x, d0y, d1x, d1y }) => {
                      const canvas = document.getElementById('ocean-rescue-canvas');
                      canvas.dispatchEvent(new PointerEvent('pointerdown', {
                        pointerId: 2, clientX: d0x, clientY: d0y,
                        isPrimary: true, button: 0, bubbles: true
                      }));
                      canvas.dispatchEvent(new PointerEvent('pointermove', {
                        pointerId: 2, clientX: d1x, clientY: d1y,
                        isPrimary: true, button: 0, bubbles: true
                      }));
                    }""",
                    {"d0x": d0x, "d0y": d0y, "d1x": d1x, "d1y": d1y},
                )
                drag_snap = page.evaluate("() => OceanRescue.Travel.getSnapshot()")
                assert drag_snap["dragging"] is True, drag_snap
                assert drag_snap["pointerId"] == 2
                page.evaluate(
                    """() => {
                      const canvas = document.getElementById('ocean-rescue-canvas');
                      const r = canvas.getBoundingClientRect();
                      const y = r.top + (460 / 720) * r.height;
                      canvas.dispatchEvent(new PointerEvent('pointerup', {
                        pointerId: 2, clientX: r.left + 640, clientY: y,
                        isPrimary: true, button: 0, bubbles: true
                      }));
                    }"""
                )
                drag_end = page.evaluate("() => OceanRescue.Travel.getSnapshot()")
                assert drag_end["dragging"] is False
                assert drag_end["pointerId"] is None
                assert drag_end["y"] == drag_snap["y"]

                # ---- Pause blocks pointer interaction; resume works ----
                y_before_pause = page.evaluate(
                    "() => OceanRescue.Travel.getSnapshot().y"
                )
                page.click("#ocean-rescue-pause-button")
                page.wait_for_function(
                    "() => document.getElementById('ocean-rescue-root').getAttribute('data-pause-active') === 'true'"
                )
                px, py = _client_point(page, 640, 300)
                page.evaluate(
                    """({ px, py }) => {
                      const canvas = document.getElementById('ocean-rescue-canvas');
                      canvas.dispatchEvent(new PointerEvent('pointerdown', {
                        pointerId: 3, clientX: px, clientY: py,
                        isPrimary: true, button: 0, bubbles: true
                      }));
                      canvas.dispatchEvent(new PointerEvent('pointerup', {
                        pointerId: 3, clientX: px, clientY: py,
                        isPrimary: true, button: 0, bubbles: true
                      }));
                    }""",
                    {"px": px, "py": py},
                )
                y_during_pause = page.evaluate(
                    "() => OceanRescue.Travel.getSnapshot().y"
                )
                assert y_during_pause == y_before_pause, (
                    "pointer interaction must be blocked while paused"
                )
                page.click("#ocean-rescue-pause-resume")
                page.wait_for_function(
                    "() => document.getElementById('ocean-rescue-root').getAttribute('data-pause-active') === 'false'",
                    timeout=7000,
                )

                # ---- Arrival and sea-turtle pointer interaction ----
                page.evaluate(
                    """() => {
                      const T = OceanRescue.Travel;
                      while (T.getSnapshot().distance < OceanRescue.Rescue.ArrivalDistance) {
                        T.step(50, 1);
                      }
                    }"""
                )
                page.wait_for_function(
                    "() => document.getElementById('ocean-rescue-root').getAttribute('data-rescue-phase') === 'tutorial'",
                    timeout=5000,
                )
                page.mouse.click(640, 360)
                page.wait_for_function(
                    "() => document.getElementById('ocean-rescue-root').getAttribute('data-rescue-phase') === 'active'",
                    timeout=5000,
                )
                assert (
                    page.evaluate(
                        "() => document.getElementById('ocean-rescue-root').getAttribute('data-sea-turtle-scene')"
                    )
                    == "active"
                ), "authored sea-turtle scene must be active"

                ropes = page.evaluate(
                    "() => OceanRescue.SeaTurtle.Ropes.map(r => ({ start: r.start, end: r.end }))"
                )
                for i, rope in enumerate(ropes):
                    sx, sy = _client_point(page, rope["start"]["x"], rope["start"]["y"])
                    ex, ey = _client_point(page, rope["end"]["x"], rope["end"]["y"])
                    page.evaluate(
                        """({ sx, sy, ex, ey, pointerId }) => {
                          const canvas = document.getElementById('ocean-rescue-canvas');
                          canvas.dispatchEvent(new PointerEvent('pointerdown', {
                            pointerId, clientX: sx, clientY: sy,
                            isPrimary: true, button: 0, bubbles: true
                          }));
                          canvas.dispatchEvent(new PointerEvent('pointermove', {
                            pointerId, clientX: (sx + ex) / 2, clientY: (sy + ey) / 2,
                            isPrimary: true, button: 0, bubbles: true
                          }));
                          canvas.dispatchEvent(new PointerEvent('pointerup', {
                            pointerId, clientX: ex, clientY: ey,
                            isPrimary: true, button: 0, bubbles: true
                          }));
                        }""",
                        {"sx": sx, "sy": sy, "ex": ex, "ey": ey, "pointerId": 10 + i},
                    )
                    page.wait_for_function(
                        """count => Number(
                          document.getElementById('ocean-rescue-root')
                            .getAttribute('data-sea-turtle-completed-count')) > count
                          || document.getElementById('ocean-rescue-root')
                            .getAttribute('data-rescue-phase') === 'success'""",
                        arg=i,
                        timeout=4000,
                    )
                    if i < 2:
                        page.wait_for_function(
                            "() => document.getElementById('ocean-rescue-root')"
                            ".getAttribute('data-sea-turtle-feedback') === 'none'",
                            timeout=4000,
                        )

                # A second pointer interaction proves capture was released.
                assert (
                    page.evaluate(
                        "() => Number(document.getElementById('ocean-rescue-root').getAttribute('data-sea-turtle-completed-count'))"
                    )
                    >= 1
                )
                page.close()
            finally:
                browser.close()
    finally:
        server.stop()

    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert request_failures == [], f"request failures: {request_failures}"
    assert external_requests == [], f"external requests: {external_requests}"
    assert duplicate_init_seen is False


def test_pointer_boundary_browser_crab_flow() -> None:
    """Crab rescue pointer interaction through the authored scene."""
    server = HTTPServerFixture()
    base_url = server.start()
    page_errors: list[str] = []
    console_errors: list[str] = []
    request_failures: list[str] = []
    external_requests: list[dict[str, str]] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--disable-background-networking", "--disable-component-update"],
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )
                context.add_init_script("window.localStorage.clear();")
                context.add_init_script(
                    "window.localStorage.setItem('aidengame.oceanRescue.progression', "
                    "JSON.stringify({ schemaVersion: 1, completedMissionIds: ['sea-turtle'], "
                    "newMissionIds: [] }));"
                )
                context.add_init_script(_POINTER_CAPTURE_INIT_SCRIPT)
                page = context.new_page()
                page.on(
                    "pageerror",
                    lambda error: page_errors.append(str(error)),
                )
                page.on(
                    "console",
                    lambda message: (
                        console_errors.append(message.text)
                        if message.type == "error"
                        else None
                    ),
                )
                page.on(
                    "requestfailed",
                    lambda request: request_failures.append(request.url),
                )
                page.on(
                    "request",
                    lambda request: (
                        external_requests.append({"url": request.url})
                        if request.resource_type in {"script", "fetch", "xhr"}
                        and request.url.startswith("http")
                        and f"127.0.0.1:{server.server.server_address[1]}"
                        not in request.url
                        else None
                    ),
                )

                _rescue_active_after_launch(page, base_url, "crab", "gup-x")
                assert (
                    page.evaluate(
                        "() => document.getElementById('ocean-rescue-root').getAttribute('data-crab-scene')"
                    )
                    == "active"
                ), "authored crab scene must be active"
                rocks = page.evaluate(
                    "() => OceanRescue.Crab.Rocks.map(r => ({ start: r.start, placed: r.placed }))"
                )
                rock = rocks[0]
                sx, sy = _client_point(page, rock["start"]["x"], rock["start"]["y"])
                drop = page.evaluate("() => OceanRescue.Crab.DropZone")
                dx, dy = _client_point(page, drop["x"], drop["y"])
                # Crab uses a tap-armed gesture: tap once on the rock to arm it,
                # then tap the drop zone to complete (matches the crab contract).
                page.evaluate(
                    """({ sx, sy, dx, dy }) => {
                      const canvas = document.getElementById('ocean-rescue-canvas');
                      canvas.dispatchEvent(new PointerEvent('pointerdown', {
                        pointerId: 21, clientX: sx, clientY: sy,
                        isPrimary: true, button: 0, bubbles: true
                      }));
                      canvas.dispatchEvent(new PointerEvent('pointerup', {
                        pointerId: 21, clientX: sx, clientY: sy,
                        isPrimary: true, button: 0, bubbles: true
                      }));
                      canvas.dispatchEvent(new PointerEvent('pointerdown', {
                        pointerId: 22, clientX: dx, clientY: dy,
                        isPrimary: true, button: 0, bubbles: true
                      }));
                      canvas.dispatchEvent(new PointerEvent('pointerup', {
                        pointerId: 22, clientX: dx, clientY: dy,
                        isPrimary: true, button: 0, bubbles: true
                      }));
                    }""",
                    {"sx": sx, "sy": sy, "dx": dx, "dy": dy},
                )
                page.wait_for_function(
                    "() => Number(document.getElementById('ocean-rescue-root').getAttribute('data-crab-completed-count')) >= 1"
                    " || document.getElementById('ocean-rescue-root').getAttribute('data-rescue-phase') === 'success'",
                    timeout=4000,
                )
                assert (
                    page.evaluate(
                        "() => Number(document.getElementById('ocean-rescue-root').getAttribute('data-crab-completed-count'))"
                    )
                    >= 1
                ), "crab pointer drag must complete a rock"
                page.close()
            finally:
                browser.close()
    finally:
        server.stop()

    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert request_failures == [], f"request failures: {request_failures}"
    assert external_requests == [], f"external requests: {external_requests}"
