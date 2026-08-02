#!/usr/bin/env python3
"""Sea turtle rope visual/hit geometry alignment — focused Chrome fixture runner.

Boots the published single HTML in a same-origin iframe harness and drives only
the public OceanRescue runtime namespaces, then reads the retained PIXI node
geometry through RenderRuntime.getContainer().

Gate the visible rope against the canonical SeaTurtle.Ropes axis:
  - active loop center == canonical midpoint while pointer intent is active
  - active loop rotation == canonical segment angle
  - cut ring stays on rope.end
  - drag arrow stays on the canonical segment
  - trace/tap input rules still resolve success/failure
  - CSS-scaled canvas maps back to the same logical coordinates

Two backend modes are supported:
  auto (default) - keep the default Chrome flags; the selected backend follows
                   WebGL preflight
  canvas         - disable WebGL in Chrome so the scene boots on PixiJS Canvas
                   backend
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

HARNESS_URL_PATH = "/tests/ocean-rescue/rendering-acceptance/rope-geometry-runtime.html"

TASK_ID = "AIDENGAME-OCEAN-RESCUE-SEA-TURTLE-ROPE-VISUAL-HIT-GEOMETRY-ALIGNMENT-01"

PRODUCTION_FILES = [
    "ocean-rescue/index.html",
    "domains/ocean-rescue/src/render-runtime.js",
    "domains/ocean-rescue/src/sea-turtle.js",
    "domains/ocean-rescue/src/sea-turtle-scene.js",
]

CHROME_TIMEOUT_SECONDS = 90

WEBGL_DISABLE_FLAG = "--disable-" + "webgl"

POSITION_EPS = 1.0
ANGLE_EPS = 0.01

# Visible-footprint measurement contract (PixiJS 8.19.0).
# texture.trim + orig + Sprite anchor + worldTransform produce the trimmed
# visible-frame center. It must converge with Sprite.visualBounds (the same
# trimmed rect) within 1px. Sprite.getBounds() in PixiJS 8 measures the
# UNTRIMMED orig rect, so its center is expected to differ by the trim/anchor
# artifact; it is kept as a sanity bound (<= 4px) only.
CROSS_CHECK_EPS = 1.0
GET_BOUNDS_ARTIFACT_MAX = 4.0
RESIDUAL_MIN = 2.0


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sea turtle rope geometry alignment — focused Chrome runner."
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "canvas"),
        default="auto",
        help="Pixi backend expectation. canvas disables WebGL in Chrome.",
    )
    parser.add_argument(
        "--allow-red",
        action="store_true",
        help="Allow the pointer-active loop to move off the canonical midpoint "
        "(used to reproduce the pre-fix displacement).",
    )
    return parser.parse_args()


def sha256_of(relative_path):
    digest = hashlib.sha256()
    with open(REPO_ROOT / relative_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head():
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
        return proc.stdout.strip() if proc.returncode == 0 else "unknown"
    except OSError:
        return "unknown"


def load_backend_helpers():
    helper_path = REPO_ROOT / "scripts/ocean-rescue/verify-pixi-backends.py"
    spec = importlib.util.spec_from_file_location(
        "ocean_rescue_backend_helpers", helper_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_diagnostics(output):
    match = output.find('"schemaVersion"')
    if match == -1:
        return None, "no diagnostics found"

    json_start = output.rfind("{", 0, match)
    if json_start == -1:
        return None, "invalid diagnostics JSON"

    depth = 0
    json_end = -1
    for idx in range(json_start, len(output)):
        ch = output[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                json_end = idx
                break

    if json_end == -1:
        return None, "unmatched braces in diagnostics"

    try:
        return json.loads(output[json_start : json_end + 1]), None
    except json.JSONDecodeError as exc:
        return None, "json parse: {}".format(exc)


def run_chrome(chrome_bin, url, backend_mode):
    user_data = tempfile.mkdtemp(prefix="chrome-ocean-ropedgeo-")

    chrome_args = [
        chrome_bin,
        url,
        "--headless",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-extensions",
        "--disable-sync",
        "--mute-audio",
        "--hide-scrollbars",
        "--dump-dom",
        "--virtual-time-budget=12000",
        "--user-data-dir={}".format(user_data),
    ]

    if backend_mode == "canvas":
        chrome_args.append(WEBGL_DISABLE_FLAG)

    try:
        process = subprocess.Popen(
            chrome_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(REPO_ROOT),
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )
        try:
            stdout, stderr = process.communicate(timeout=CHROME_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
    except OSError as exc:
        return None, "chrome launch: {}".format(exc)
    finally:
        shutil.rmtree(user_data, ignore_errors=True)

    return (stderr or "") + (stdout or ""), None


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def finite_number(value):
    return number(value) and math.isfinite(value)


def visible_footprint_checks(ropes, tag, checks, require_residual=False):
    """Validate the trimmed visible-footprint measurement for each rope.

    MEASUREMENT_VALID requires the trim-aware center to converge with
    Sprite.visualBounds (the trimmed visible rect) within 1px per axis. The
    getBounds() delta is reported under a documented sanity bound because
    PixiJS 8 getBounds() measures the untrimmed orig rect.
    """
    normals = []
    for idx, rope in enumerate(ropes):
        vt = "{}r{}.visible".format(tag, idx + 1)
        vf = rope.get("visibleFootprint") or {}
        checks.append(
            (
                "{}.present".format(vt),
                bool(vf),
                "{} visibleFootprint missing".format(vt),
            )
        )
        trim = vf.get("trimAwareCenter") or {}
        checks.append(
            (
                "{}.trimAwareFinite".format(vt),
                finite_number(trim.get("x")) and finite_number(trim.get("y")),
                "{} trimAware center not finite".format(vt),
            )
        )
        cross_visual = vf.get("crossCheckVsVisualBounds")
        checks.append(
            (
                "{}.crossVsVisual<=1px".format(vt),
                finite_number(cross_visual) and cross_visual <= CROSS_CHECK_EPS,
                "{} trim-aware vs visualBounds delta {:.3f}px > {:.0f}px".format(
                    vt, cross_visual, CROSS_CHECK_EPS
                ),
            )
        )
        cross_bounds = vf.get("crossCheckVsGetBounds")
        checks.append(
            (
                "{}.crossVsGetBounds<=4px".format(vt),
                finite_number(cross_bounds) and cross_bounds <= GET_BOUNDS_ARTIFACT_MAX,
                "{} trim-aware vs getBounds delta {:.3f}px (PixiJS getBounds uses "
                "untrimmed orig)".format(vt, cross_bounds),
            )
        )
        delta = vf.get("visibleCenterDelta")
        checks.append(
            (
                "{}.visibleDeltaFinite".format(vt),
                finite_number(delta),
                "{} visibleCenterDelta not finite".format(vt),
            )
        )
        normal = vf.get("normalOffset")
        if finite_number(normal):
            normals.append(normal)
    if require_residual and normals:
        checks.append(
            (
                "{}visibleResidualConfirmed".format(tag),
                all(abs(n) > RESIDUAL_MIN for n in normals),
                "{} visible footprint not > {:.0f}px from canonical midpoint".format(
                    tag, RESIDUAL_MIN
                ),
            )
        )
        checks.append(
            (
                "{}normalSignConsistent".format(tag),
                all(n > 0 for n in normals) or all(n < 0 for n in normals),
                "{} visible footprint normal offsets not same direction".format(tag),
            )
        )


def geometry_checks(diag, allow_red, checks):
    def check(name, ok, message):
        checks.append((name, ok, message))

    check("complete", diag.get("complete") is True, "harness did not complete")
    check(
        "error",
        diag.get("error") is None,
        "harness error: {}".format(diag.get("error")),
    )
    check(
        "selectedBackend",
        diag.get("selectedBackend") in ("webgl", "canvas"),
        "selectedBackend not in (webgl, canvas)",
    )
    check(
        "logicalSize",
        diag.get("logicalWidth") == 1280 and diag.get("logicalHeight") == 720,
        "logical size != 1280x720",
    )

    initial = diag.get("initial") or {}
    check("initial.mounted", initial.get("mounted") is True, "initial.mounted != true")
    check(
        "initial.activeRopeId",
        initial.get("activeRopeId") == "rope-1",
        "initial.activeRopeId != rope-1 (got {})".format(initial.get("activeRopeId")),
    )
    check(
        "initial.loopCount",
        initial.get("loopCount") == 3,
        "initial.loopCount != 3 (got {})".format(initial.get("loopCount")),
    )

    inactive = diag.get("pointerInactive") or {}
    ropes = inactive.get("ropes") or []
    check("pointerInactive.ropes", len(ropes) == 3, "pointerInactive ropes != 3")
    for idx, rope in enumerate(ropes):
        tag = "pointerInactive.r{}".format(idx + 1)
        check(
            "{}.loopPresent".format(tag),
            rope.get("loopPresent") is True,
            "{} loop missing".format(tag),
        )
        check(
            "{}.centerDelta".format(tag),
            finite_number(rope.get("centerDelta"))
            and abs(rope["centerDelta"]) <= POSITION_EPS,
            "{} centerDelta {} > {}".format(tag, rope.get("centerDelta"), POSITION_EPS),
        )
        check(
            "{}.angleDelta".format(tag),
            finite_number(rope.get("angleDelta"))
            and abs(rope["angleDelta"]) <= ANGLE_EPS,
            "{} angleDelta {} > {}".format(tag, rope.get("angleDelta"), ANGLE_EPS),
        )
        check(
            "{}.segmentLength".format(tag),
            finite_number(rope.get("segmentLength")) and rope["segmentLength"] > 0,
            "{} segmentLength not positive".format(tag),
        )
        footprint = rope.get("footprint") or {}
        check(
            "{}.footprintFinite".format(tag),
            all(
                finite_number(footprint.get(key))
                for key in ("frameWorldWidth", "frameWorldHeight")
            )
            and all(
                finite_number((footprint.get("frameWorldCenter") or {}).get(key))
                for key in ("x", "y")
            ),
            "{} loop footprint not finite".format(tag),
        )
    visible_footprint_checks(ropes, "pointerInactive.", checks, require_residual=True)

    active = diag.get("pointerActive") or {}
    active_ropes = (active.get("geometry") or {}).get("ropes") or []
    check("pointerActive.geometry", len(active_ropes) == 3, "pointerActive ropes != 3")
    if active_ropes:
        ar = active_ropes[0]
        center = ar.get("centerDelta")
        ok = finite_number(center) and abs(center) <= POSITION_EPS
        if allow_red:
            check(
                "pointerActive.r1.centerDelta (RED probe)",
                finite_number(center),
                "pointerActive.r1 centerDelta not finite",
            )
            print("  [RED] pointerActive.r1.centerDelta={}".format(center))
        else:
            check(
                "pointerActive.r1.centerDelta==0",
                ok,
                "pointerActive loop moved {}px off canonical midpoint while "
                "pointerIntent active".format(center),
            )
        check(
            "pointerActive.r1.angleDelta",
            finite_number(ar.get("angleDelta")) and abs(ar["angleDelta"]) <= ANGLE_EPS,
            "pointerActive.r1 angleDelta {} > {}".format(
                ar.get("angleDelta"), ANGLE_EPS
            ),
        )
        visible_footprint_checks(active_ropes[:1], "pointerActive.", checks)

    inactive_after = diag.get("pointerInactiveAfter") or {}
    after_ropes = inactive_after.get("ropes") or []
    check(
        "pointerInactiveAfter.ropes", len(after_ropes) == 3, "inactive-after ropes != 3"
    )
    if after_ropes:
        check(
            "pointerInactiveAfter.r1.centerDelta",
            finite_number(after_ropes[0].get("centerDelta"))
            and abs(after_ropes[0]["centerDelta"]) <= POSITION_EPS,
            "pointerInactiveAfter.r1 centerDelta {} > {}".format(
                after_ropes[0].get("centerDelta"), POSITION_EPS
            ),
        )
        visible_footprint_checks(after_ropes[:1], "pointerInactiveAfter.", checks)

    cut = (inactive or {}).get("cutRing") or {}
    check(
        "cutRing.endDelta==0",
        finite_number(cut.get("endDelta")) and abs(cut["endDelta"]) <= POSITION_EPS,
        "cut ring {}px off rope.end".format(cut.get("endDelta")),
    )

    trace = diag.get("traceSuccess") or {}
    result = trace.get("result") or {}
    check("trace.result.accepted", result.get("accepted") is True, "trace not accepted")
    check(
        "trace.result.outcome", result.get("outcome") == "success", "trace != success"
    )
    check(
        "trace.feedback.nextRopeId",
        (trace.get("feedback") or {}).get("nextRopeId") == "rope-2",
        "trace feedback nextRopeId != rope-2",
    )
    check(
        "trace.nextActiveRopeId",
        trace.get("nextActiveRopeId") == "rope-2",
        "trace next active rope != rope-2",
    )
    after_advance = trace.get("afterAdvance") or {}
    aa_ropes = after_advance.get("ropes") or []
    check(
        "trace.afterAdvance.ropes", len(aa_ropes) == 3, "trace afterAdvance ropes != 3"
    )
    if aa_ropes:
        check(
            "trace.afterAdvance.r2.centerDelta",
            finite_number(aa_ropes[1].get("centerDelta"))
            and abs(aa_ropes[1]["centerDelta"]) <= POSITION_EPS,
            "trace afterAdvance rope-2 centerDelta {} > {}".format(
                aa_ropes[1].get("centerDelta"), POSITION_EPS
            ),
        )
        check(
            "trace.afterAdvance.r1Hidden",
            aa_ropes[0].get("loopVisible") is False,
            "completed rope-1 loop still visible",
        )

    off_path = diag.get("traceOffPath") or {}
    off_result = off_path.get("result") or {}
    check(
        "offPath.result.outcome",
        off_result.get("outcome") == "failure",
        "off-path trace != failure (got {})".format(off_result.get("outcome")),
    )
    reset = off_path.get("afterReset") or {}
    reset_ropes = reset.get("ropes") or []
    check(
        "offPath.afterReset.ropes",
        len(reset_ropes) == 3,
        "offPath afterReset ropes != 3",
    )
    if reset_ropes:
        check(
            "offPath.afterReset.r2.centerDelta",
            finite_number(reset_ropes[1].get("centerDelta"))
            and abs(reset_ropes[1]["centerDelta"]) <= POSITION_EPS,
            "failure reset rope-2 centerDelta {} > {}".format(
                reset_ropes[1].get("centerDelta"), POSITION_EPS
            ),
        )
        check(
            "offPath.afterReset.activeRopeId",
            reset.get("activeRopeId") == "rope-2",
            "offPath afterReset activeRopeId != rope-2 (got {})".format(
                reset.get("activeRopeId")
            ),
        )

    tap = diag.get("tapSuccess") or {}
    tap_result = tap.get("result") or {}
    check(
        "tap.armed.outcome",
        (tap.get("armed") or {}).get("outcome") == "none",
        "tap arm failed",
    )
    check(
        "tap.result.outcome",
        tap_result.get("outcome") == "success",
        "tap success != success (got {})".format(tap_result.get("outcome")),
    )
    check(
        "tap.feedback.nextRopeId",
        (tap.get("feedback") or {}).get("nextRopeId") == "rope-3",
        "tap feedback nextRopeId != rope-3",
    )

    three = diag.get("threeRope") or {}
    final = three.get("finalDomain") or {}
    check(
        "three.feedbackComplete",
        three.get("feedbackComplete") is True,
        "complete != true",
    )
    check(
        "three.final.complete", final.get("complete") is True, "final complete != true"
    )
    check("three.final.active", final.get("active") is False, "final active != false")
    check(
        "three.final.completedRopeIds",
        (final.get("completedRopeIds") or []) == ["rope-1", "rope-2", "rope-3"],
        "final completedRopeIds != rope-1..3 (got {})".format(
            final.get("completedRopeIds")
        ),
    )

    css = diag.get("cssScaled") or {}
    round_trips = css.get("roundTrips") or []
    check("cssScaled.roundTrips", len(round_trips) == 6, "cssScaled roundTrips != 6")
    worst = 0.0
    for rt in round_trips:
        err = rt.get("err")
        if finite_number(err):
            worst = max(worst, err)
    check(
        "cssScaled.mapError",
        worst <= 2.0,
        "cssScaled mapClientToLogical error {:.3f}px > 2px".format(worst),
    )
    css_ropes = (css.get("geometry") or {}).get("ropes") or []
    check(
        "cssScaled.geometry.ropes", len(css_ropes) == 3, "cssScaled geometry ropes != 3"
    )
    if css_ropes:
        check(
            "cssScaled.geometry.r1.centerDelta",
            finite_number(css_ropes[0].get("centerDelta"))
            and abs(css_ropes[0]["centerDelta"]) <= POSITION_EPS,
            "cssScaled rope-1 centerDelta {} > {}".format(
                css_ropes[0].get("centerDelta"), POSITION_EPS
            ),
        )

    check(
        "uncaughtErrorCount",
        diag.get("uncaughtErrorCount") == 0,
        "uncaughtErrorCount != 0 (got {})".format(diag.get("uncaughtErrorCount")),
    )
    check(
        "unhandledRejectionCount",
        diag.get("unhandledRejectionCount") == 0,
        "unhandledRejectionCount != 0 (got {})".format(
            diag.get("unhandledRejectionCount")
        ),
    )
    check(
        "securityPolicyViolationCount",
        diag.get("securityPolicyViolationCount") == 0,
        "securityPolicyViolationCount != 0 (got {})".format(
            diag.get("securityPolicyViolationCount")
        ),
    )
    check(
        "externalOriginRequestCount",
        diag.get("externalOriginRequestCount") == 0,
        "externalOriginRequestCount != 0 (got {})".format(
            diag.get("externalOriginRequestCount")
        ),
    )


def main():
    args = parse_args()
    helpers = load_backend_helpers()
    chrome_bin = helpers.resolve_chrome()
    if not chrome_bin:
        print("BLOCKED: Chrome Stable not found", file=sys.stderr)
        return 2

    before_hashes = {path: sha256_of(path) for path in PRODUCTION_FILES}

    port = helpers.find_free_port()
    server = helpers.start_server(port)

    url = "http://127.0.0.1:{}{}".format(port, HARNESS_URL_PATH)

    try:
        output, launch_error = run_chrome(chrome_bin, url, args.backend)
        if launch_error is not None:
            print("BLOCKED: {}".format(launch_error), file=sys.stderr)
            return 2

        diag, parse_error = parse_diagnostics(output)
        if parse_error is not None or diag is None:
            print("FAIL: {}".format(parse_error), file=sys.stderr)
            if output:
                print(
                    "    raw output (last 800 chars): {}".format(output[-800:]),
                    file=sys.stderr,
                )
            return 1
    finally:
        server.shutdown()
        server.server_close()

    after_hashes = {path: sha256_of(path) for path in PRODUCTION_FILES}

    checks = []
    geometry_checks(diag, args.allow_red, checks)
    checks.append(
        (
            "productionByteIdentical",
            before_hashes == after_hashes,
            "production hashes changed",
        )
    )

    all_pass = True
    for name, ok, message in checks:
        result_str = "PASS" if ok else "FAIL: {}".format(message)
        print("  [{}] {}".format(result_str, name))
        if not ok:
            all_pass = False

    print()
    print("  head={}".format(git_head()))
    print(
        "  backend={} logical={}x{}".format(
            diag.get("selectedBackend"),
            diag.get("logicalWidth"),
            diag.get("logicalHeight"),
        )
    )
    print(
        "  pointerActive.r1.centerDelta={}".format(
            (
                ((diag.get("pointerActive") or {}).get("geometry") or {}).get("ropes")
                or [{}]
            )[0].get("centerDelta")
        )
    )
    inactive_ropes = (diag.get("pointerInactive") or {}).get("ropes") or []
    vf0 = (inactive_ropes[0].get("visibleFootprint") or {}) if inactive_ropes else {}
    print(
        "  pointerInactive.r1.visibleCenterDelta={} normalOffset={} "
        "crossVsVisual={} crossVsGetBounds={}".format(
            vf0.get("visibleCenterDelta"),
            vf0.get("normalOffset"),
            vf0.get("crossCheckVsVisualBounds"),
            vf0.get("crossCheckVsGetBounds"),
        )
    )
    print(
        "  external={} reference={} errors={} rejections={} csp={}".format(
            diag.get("externalOriginRequestCount"),
            diag.get("referenceImageRequestCount"),
            diag.get("uncaughtErrorCount"),
            diag.get("unhandledRejectionCount"),
            diag.get("securityPolicyViolationCount"),
        )
    )
    print("  production hashes unchanged={}".format(before_hashes == after_hashes))

    if not all_pass:
        print("\nSEA_TURTLE_ROPE_VISUAL_HIT_GEOMETRY_ALIGNMENT=FAIL", file=sys.stderr)
        return 1

    measurement_valid = True
    for name, ok, _ in checks:
        if "crossVsVisual" in name and not ok:
            measurement_valid = False
    residual_confirmed = all(
        ok for name, ok, _ in checks if name.endswith("visibleResidualConfirmed")
    )
    if measurement_valid and residual_confirmed:
        print(
            "\nSEA_TURTLE_ROPE_VISIBLE_FOOTPRINT_MEASUREMENT=VALID "
            "RESIDUAL_VISIBLE_OFFSET=CONFIRMED"
        )
    print("\nSEA_TURTLE_ROPE_VISUAL_HIT_GEOMETRY_ALIGNMENT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
