"""Focused acceptance test for Ocean Rescue browser→logical coordinate fixtures.

Verifies that the canonical rescue-phase mapping (mapRescueCoordinates in
``app.js:1866-1867``) produces the expected logical coordinates for every
fixture case.  The production code is NOT imported; the formula is implemented
as a pure function to keep the test isolated.

Run: pytest tests/ocean-rescue/rendering-acceptance/coordinates/test_coordinates.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_PATH = (
    Path(__file__).resolve().parents[3]
    / "fixtures"
    / "ocean-rescue"
    / "rendering-acceptance"
    / "coordinates.json"
)

CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720


def _load_fixture():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _map_rescue_coordinates(
    client_x: float,
    client_y: float,
    rect_left: float,
    rect_top: float,
    rect_width: float,
    rect_height: float,
) -> tuple[float, float]:
    """Pure implementation of the canonical mapping from app.js:1866-1867."""
    x = (client_x - rect_left) * (CANVAS_WIDTH / rect_width)
    y = (client_y - rect_top) * (CANVAS_HEIGHT / rect_height)
    return x, y


def _close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol + 1e-9


def _run_production_js_mapping(
    cases: list[dict], with_render_runtime: bool = False
) -> list[dict[str, float]]:
    """Execute production domains/ocean-rescue/src/pointer-input.js via Node.js."""
    import shutil
    import subprocess

    node_bin = shutil.which("node")
    if not node_bin:
        pytest.skip("node executable not found on PATH")

    repo_root = Path(__file__).resolve().parents[4]
    pointer_js_path = (
        repo_root / "domains" / "ocean-rescue" / "src" / "pointer-input.js"
    )
    assert pointer_js_path.is_file(), f"pointer-input.js missing at {pointer_js_path}"

    runner_js = f"""
const fs = require('fs');
const vm = require('vm');

const pointerJsCode = fs.readFileSync({json.dumps(str(pointer_js_path))}, 'utf-8');

const cases = {json.dumps(cases)};
const withRenderRuntime = {json.dumps(with_render_runtime)};

const context = {{
    window: {{}},
    console: console,
    Math: Math,
    isFinite: isFinite
}};

vm.createContext(context);
vm.runInContext(pointerJsCode, context);

if (withRenderRuntime) {{
    context.window.OceanRescue.RenderRuntime = {{
        isReady: () => true,
        mapClientToLogical: (cx, cy) => ({{ x: cx * (1280 / 1280), y: cy * (720 / 720), inside: true }})
    }};
}}

const PointerInput = context.window.OceanRescue.PointerInput;
if (!PointerInput || typeof PointerInput.mapRescuePoint !== 'function') {{
    console.error("PointerInput.mapRescuePoint not found on window.OceanRescue");
    process.exit(1);
}}

const results = cases.map(c => {{
    const canvas = {{
        getBoundingClientRect: () => ({{
            left: c.canvasRectLeft,
            top: c.canvasRectTop,
            width: c.canvasRectWidth,
            height: c.canvasRectHeight
        }})
    }};
    const event = {{ clientX: c.browserX, clientY: c.browserY }};
    const pt = PointerInput.mapRescuePoint(event, canvas);
    return pt ? {{ x: pt.x, y: pt.y }} : null;
}});

console.log(JSON.stringify(results));
"""
    res = subprocess.run(
        [node_bin, "-e", runner_js],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(res.stdout.strip())


# ---------------------------------------------------------------------------
# Contract assertions on the fixture file itself
# ---------------------------------------------------------------------------


class TestFixtureContract:
    """Verify the fixture file satisfies the minimum required fields."""

    @pytest.fixture(scope="class")
    def fixture_data(self):
        return _load_fixture()

    def test_fixture_file_exists(self, fixture_data):
        assert "meta" in fixture_data
        assert "cases" in fixture_data
        assert len(fixture_data["cases"]) > 0

    def test_meta_fields(self, fixture_data):
        meta = fixture_data["meta"]
        assert meta["logicalWidth"] == 1280
        assert meta["logicalHeight"] == 720
        assert meta["tolerance"] <= 0.25

    def test_all_required_viewports_present(self, fixture_data):
        viewports = {c["viewportLabel"] for c in fixture_data["cases"]}
        assert "1280x720 exact-16:9" in viewports
        assert "1920x1080 exact-16:9" in viewports
        assert "1600x1200 4:3 vertical-letterbox" in viewports
        assert "1200x1600 portrait horizontal-letterbox" in viewports
        assert "2560x720 ultrawide canvas-centered" in viewports

    def test_dpr_coverage(self, fixture_data):
        dprs = {c["effectiveDpr"] for c in fixture_data["cases"]}
        assert 1 in dprs
        assert 1.5 in dprs
        assert 2 in dprs

    def test_representative_points_present(self, fixture_data):
        ids = {c["id"] for c in fixture_data["cases"]}
        has_turtle = any("turtle" in i for i in ids)
        has_crab = any("crab" in i for i in ids)
        has_corners = any("top-left" in i for i in ids) and any(
            "bottom-right" in i for i in ids
        )
        has_center = any("center" in i for i in ids)
        assert has_turtle, "No turtle rope coordinate fixture found"
        assert has_crab, "No crab dropzone coordinate fixture found"
        assert has_corners, "Not all four corners present"
        assert has_center, "No center fixture found"

    def test_letterbox_cases_present(self, fixture_data):
        outside = [c for c in fixture_data["cases"] if c.get("outsideViewport")]
        assert len(outside) >= 2, "Need at least two outside-viewport letterbox cases"

    def test_each_case_has_required_fields(self, fixture_data):
        required = {
            "id",
            "canvasRectLeft",
            "canvasRectTop",
            "canvasRectWidth",
            "canvasRectHeight",
            "effectiveDpr",
            "browserX",
            "browserY",
            "expectedLogicalX",
            "expectedLogicalY",
        }
        for case in fixture_data["cases"]:
            missing = required - set(case.keys())
            assert not missing, f"Case {case.get('id')}: missing {missing}"


# ---------------------------------------------------------------------------
# Coordinate accuracy verification
# ---------------------------------------------------------------------------


class TestCoordinateMapping:
    """Verify every fixture case matches the canonical formula."""

    @pytest.fixture(scope="class")
    def fixture_data(self):
        return _load_fixture()

    @pytest.fixture(scope="class")
    def tolerance(self, fixture_data):
        return fixture_data["meta"]["tolerance"]

    @pytest.mark.parametrize(
        "case",
        _load_fixture()["cases"],
        ids=[c["id"] for c in _load_fixture()["cases"]],
    )
    def test_mapping_matches_fixture(self, case, tolerance):
        got_x, got_y = _map_rescue_coordinates(
            client_x=case["browserX"],
            client_y=case["browserY"],
            rect_left=case["canvasRectLeft"],
            rect_top=case["canvasRectTop"],
            rect_width=case["canvasRectWidth"],
            rect_height=case["canvasRectHeight"],
        )
        assert _close(got_x, case["expectedLogicalX"], tolerance), (
            f"[{case['id']}] X mismatch: got {got_x}, "
            f"expected {case['expectedLogicalX']}"
        )
        assert _close(got_y, case["expectedLogicalY"], tolerance), (
            f"[{case['id']}] Y mismatch: got {got_y}, "
            f"expected {case['expectedLogicalY']}"
        )

    def test_letterbox_outside_bounds(self, fixture_data, tolerance):
        outside = [c for c in fixture_data["cases"] if c.get("outsideViewport")]
        for case in outside:
            _, got_y = _map_rescue_coordinates(
                client_x=case["browserX"],
                client_y=case["browserY"],
                rect_left=case["canvasRectLeft"],
                rect_top=case["canvasRectTop"],
                rect_width=case["canvasRectWidth"],
                rect_height=case["canvasRectHeight"],
            )
            in_bounds = 0 <= got_y <= CANVAS_HEIGHT
            assert not in_bounds, (
                f"[{case['id']}] Letterbox Y {got_y} should be outside [0, {CANVAS_HEIGHT}]"
            )

    def test_dpr_invariance(self, fixture_data, tolerance):
        """Same viewport + same CSS pointer → same logical result regardless of DPR."""
        by_viewport_point: dict[tuple, list] = {}
        for c in fixture_data["cases"]:
            if c.get("outsideViewport"):
                continue
            key = (
                c["viewportLabel"],
                c["canvasRectLeft"],
                c["canvasRectTop"],
                c["canvasRectWidth"],
                c["canvasRectHeight"],
                c["browserX"],
                c["browserY"],
            )
            by_viewport_point.setdefault(key, []).append(c)

        for key, cases in by_viewport_point.items():
            if len(cases) < 2:
                continue
            first = cases[0]
            ref_x, ref_y = _map_rescue_coordinates(
                first["browserX"],
                first["browserY"],
                first["canvasRectLeft"],
                first["canvasRectTop"],
                first["canvasRectWidth"],
                first["canvasRectHeight"],
            )
            for c in cases[1:]:
                got_x, got_y = _map_rescue_coordinates(
                    c["browserX"],
                    c["browserY"],
                    c["canvasRectLeft"],
                    c["canvasRectTop"],
                    c["canvasRectWidth"],
                    c["canvasRectHeight"],
                )
                assert _close(got_x, ref_x, tolerance), (
                    f"DPR divergence X: {first['id']} vs {c['id']}"
                )
                assert _close(got_y, ref_y, tolerance), (
                    f"DPR divergence Y: {first['id']} vs {c['id']}"
                )

    def test_no_canvas_rect_zero_dimensions(self, fixture_data):
        for c in fixture_data["cases"]:
            assert c["canvasRectWidth"] > 0
            assert c["canvasRectHeight"] > 0

    def test_tolerated_round_trip_error(self, fixture_data, tolerance):
        """Forward mapping then inverse should recover the original within tolerance."""
        for c in fixture_data["cases"]:
            if c.get("outsideViewport"):
                continue
            lx, ly = _map_rescue_coordinates(
                c["browserX"],
                c["browserY"],
                c["canvasRectLeft"],
                c["canvasRectTop"],
                c["canvasRectWidth"],
                c["canvasRectHeight"],
            )
            inv_x = lx / (CANVAS_WIDTH / c["canvasRectWidth"]) + c["canvasRectLeft"]
            inv_y = ly / (CANVAS_HEIGHT / c["canvasRectHeight"]) + c["canvasRectTop"]
            assert _close(inv_x, c["browserX"], tolerance), (
                f"[{c['id']}] Round-trip X: {inv_x} vs {c['browserX']}"
            )
            assert _close(inv_y, c["browserY"], tolerance), (
                f"[{c['id']}] Round-trip Y: {inv_y} vs {c['browserY']}"
            )


# ---------------------------------------------------------------------------
# Production JS runtime coordinate mapping verification (WP-33E / Track A)
# ---------------------------------------------------------------------------


class TestProductionRuntimeCoordinateMapping:
    """Verify production pointer-input.js via Node.js satisfies coordinate acceptance."""

    @pytest.fixture(scope="class")
    def fixture_data(self):
        return _load_fixture()

    @pytest.fixture(scope="class")
    def tolerance(self, fixture_data):
        return fixture_data["meta"]["tolerance"]

    def test_production_js_runtime_matches_fixture(self, fixture_data, tolerance):
        cases = fixture_data["cases"]
        results = _run_production_js_mapping(cases)
        assert len(results) == len(cases)

        for case, res in zip(cases, results):
            assert res is not None, f"[{case['id']}] Production mapping returned null"
            got_x = res["x"]
            got_y = res["y"]
            exp_x = case["expectedLogicalX"]
            exp_y = case["expectedLogicalY"]
            assert _close(got_x, exp_x, tolerance), (
                f"[{case['id']}] JS Production X mismatch: got {got_x}, expected {exp_x}"
            )
            assert _close(got_y, exp_y, tolerance), (
                f"[{case['id']}] JS Production Y mismatch: got {got_y}, expected {exp_y}"
            )

    def test_production_js_dpr_coverage(self, fixture_data, tolerance):
        """Verify DPR 1, 1.5, and 2 cases pass through actual production pointer-input.js."""
        cases = fixture_data["cases"]
        dpr_map = {1: False, 1.5: False, 2: False}
        results = _run_production_js_mapping(cases)

        for case, res in zip(cases, results):
            dpr = case["effectiveDpr"]
            if dpr in dpr_map:
                dpr_map[dpr] = True
            assert res is not None
            assert _close(res["x"], case["expectedLogicalX"], tolerance)
            assert _close(res["y"], case["expectedLogicalY"], tolerance)

        assert all(dpr_map.values()), f"Missing DPR coverage verification: {dpr_map}"
