"""Focused tests for the otter-head-01 handoff render proof harness.

These tests verify the gate and validation logic of the proof script using
synthetic fixtures only. They never modify or clone the real inbox SVG and
they never launch a browser.

Covered contracts:

1. Structure report SVG SHA mismatch blocks before browser launch.
2. Isolated 1x dimensions are exactly 200x200.
3. Isolated 2x dimensions are exactly 400x400.
4. Blank raster rejects.
5. Head sprite not found blocks the proof.
6. Candidate texture is applied to the head sprite only.
7. Eye/mouth overlay textures remain unchanged.
8. The four face states have exact overlay visibility and head rotation.
9. Production paths are never written by the harness.
10. Manifest records every proof image SHA.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PROOF_SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "ocean-rescue"
    / "capture-otter-head-handoff-render-proof.py"
)


def _load_proof():
    spec = importlib.util.spec_from_file_location(
        "ocean_rescue_otter_head_render_proof", PROOF_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load proof script {PROOF_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROOF = _load_proof()

ASSET_ID = "otter-head-01"
ALIAS = "otter.head"

MINIMAL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
    '<g id="otter-head">'
    '<g id="otter-head-ears"><path d="M40 40 L60 40 L60 60 L40 60 Z" fill="#765037"/></g>'
    '<g id="otter-head-silhouette"><path d="M30 60 L170 60 L170 180 L30 180 Z" fill="#8A6246"/></g>'
    '<g id="otter-head-muzzle"><ellipse cx="100" cy="150" rx="40" ry="25" fill="#EED7A8"/></g>'
    '<g id="otter-head-details"><circle cx="60" cy="130" r="3" fill="#5E4636"/></g>'
    "</g></svg>"
)

BLANK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
    '<g id="otter-head">'
    '<g id="otter-head-silhouette"><path d="M30 60 L170 60 L170 180 L30 180 Z" fill="transparent"/></g>'
    "</g></svg>"
)


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _write(path: pathlib.Path, content) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        path.write_text(content, encoding="utf-8")
    else:
        path.write_bytes(content)
    return path


def _make_input_fixture(tmp_path: pathlib.Path, svg: str | None = None):
    svg = MINIMAL_SVG if svg is None else svg
    svg_path = _write(tmp_path / "inbox" / "otter-head-01.svg", svg)
    brief = _write(tmp_path / "briefs" / "otter-head-01.md", "# Asset identity\n")
    structure = {
        "schemaVersion": 1,
        "taskId": "synthetic",
        "assetId": ASSET_ID,
        "alias": ALIAS,
        "svgSha256": _sha256_bytes(svg.encode("utf-8")),
        "verdict": "STRUCTURE_PASS",
    }
    structure_path = _write(
        tmp_path
        / "review"
        / "handoff-intake"
        / "otter-head-01"
        / "structure-report.json",
        json.dumps(structure),
    )
    return {
        "brief": str(brief),
        "svg": str(svg_path),
        "structure_report": str(structure_path),
    }


class TestInputGate:
    def test_structure_report_svg_sha_mismatch_rejects_before_browser_launch(
        self, tmp_path
    ):
        fixture = _make_input_fixture(tmp_path)
        args = type("Args", (), fixture)()
        ok, code = PROOF.run_input_gate(tmp_path, args)
        assert ok is True
        assert code == ""

        structure_path = pathlib.Path(fixture["structure_report"])
        structure = json.loads(structure_path.read_text(encoding="utf-8"))
        structure["svgSha256"] = "0" * 64
        structure_path.write_text(json.dumps(structure), encoding="utf-8")
        ok, code = PROOF.run_input_gate(tmp_path, args)
        assert ok is False
        assert code == "STRUCTURE_REPORT_INPUT_SHA_MISMATCH"

    def test_structure_report_missing_rejects(self, tmp_path):
        fixture = _make_input_fixture(tmp_path)
        fixture["structure_report"] = str(
            tmp_path / "missing" / "structure-report.json"
        )
        args = type("Args", (), fixture)()
        ok, code = PROOF.run_input_gate(tmp_path, args)
        assert ok is False
        assert code == "STRUCTURE_REPORT_MISSING"

    def test_structure_verdict_not_passed_rejects(self, tmp_path):
        fixture = _make_input_fixture(tmp_path)
        structure_path = pathlib.Path(fixture["structure_report"])
        structure = json.loads(structure_path.read_text(encoding="utf-8"))
        structure["verdict"] = "STRUCTURE_REJECTED"
        structure_path.write_text(json.dumps(structure), encoding="utf-8")
        args = type("Args", (), fixture)()
        ok, code = PROOF.run_input_gate(tmp_path, args)
        assert ok is False
        assert code == "STRUCTURE_GATE_NOT_PASSED"


class TestIsolatedRender:
    def _render(self, tmp_path, svg, w, h):
        svg_path = _write(tmp_path / "fixture.svg", svg)
        png = PROOF.render_svg_to_png(svg_path, w, h)
        return PROOF.analyze_isolated_png(png, w, h)

    def test_isolated_1x_dimensions_exactly_200x200(self, tmp_path):
        analysis = self._render(tmp_path, MINIMAL_SVG, 200, 200)
        assert analysis["width"] == 200
        assert analysis["height"] == 200
        ok, reasons = PROOF.check_isolated(analysis)
        assert ok is True, reasons

    def test_isolated_2x_dimensions_exactly_400x400(self, tmp_path):
        analysis = self._render(tmp_path, MINIMAL_SVG, 400, 400)
        assert analysis["width"] == 400
        assert analysis["height"] == 400
        ok, reasons = PROOF.check_isolated(analysis)
        assert ok is True, reasons

    def test_blank_raster_rejects(self, tmp_path):
        analysis = self._render(tmp_path, BLANK_SVG, 200, 200)
        ok, reasons = PROOF.check_isolated(analysis)
        assert ok is False
        assert any("completely transparent" in r for r in reasons)


class TestHeadApplyBlocked:
    def test_head_sprite_not_found_blocks(self):
        blocked, error = PROOF.head_apply_blocked(
            {"ok": False, "error": "sea-otter-head sprite not found"}
        )
        assert blocked == "HEAD_SPRITE_NOT_FOUND"
        assert error == "sea-otter-head sprite not found"

    def test_missing_apply_result_blocks(self):
        blocked, _ = PROOF.head_apply_blocked(None)
        assert blocked == "HEAD_SPRITE_NOT_FOUND"

    def test_successful_apply_does_not_block(self):
        blocked, _ = PROOF.head_apply_blocked({"ok": True, "headFound": True})
        assert blocked is None

    def test_main_flow_blocks_when_head_missing(self, tmp_path):
        # The main flow maps a blocked capture result to exit code 2 before any
        # further capture work. The decision lives in head_apply_blocked; verify
        # the harness documents the blocked code.
        source = PROOF_SCRIPT.read_text(encoding="utf-8")
        assert "HEAD_SPRITE_NOT_FOUND" in source
        assert 'result["blocked"]' in source
        blocked, _ = PROOF.head_apply_blocked({"ok": False})
        assert blocked == "HEAD_SPRITE_NOT_FOUND"


def _head_sprite(**overrides):
    head = {
        "label": "sea-otter-head",
        "isSprite": True,
        "visible": True,
        "renderable": True,
        "x": 0,
        "y": -42,
        "rotation": -0.025,
        "scaleX": 0.62,
        "scaleY": 0.62,
        "anchor": {"x": 0.5, "y": 0.55},
        "textureLabel": PROOF.CANDIDATE_TEXTURE_LABEL,
        "textureOrig": {"w": 200, "h": 200},
        "bounds": {"x": 528, "y": 310, "width": 124, "height": 124},
    }
    head.update(overrides)
    return head


class TestHeadSpriteIdentity:
    def test_candidate_texture_applied_to_head_only(self):
        result = {"headSprite": _head_sprite(), "texturesUnchanged": True}
        ok, reasons = PROOF.check_head_sprite(result)
        assert ok is True, reasons

    def test_head_missing_rejects(self):
        result = {"headSprite": None, "texturesUnchanged": None}
        ok, reasons = PROOF.check_head_sprite(result)
        assert ok is False
        assert any("head sprite missing" in r for r in reasons)

    def test_candidate_texture_not_applied_rejects(self):
        result = {
            "headSprite": _head_sprite(textureLabel="otter.head"),
            "texturesUnchanged": None,
        }
        ok, reasons = PROOF.check_head_sprite(result)
        assert ok is False
        assert any("candidate texture not applied" in r for r in reasons)

    def test_abnormal_anchor_rejects(self):
        result = {
            "headSprite": _head_sprite(anchor={"x": 0.5, "y": 0.3}),
            "texturesUnchanged": None,
        }
        ok, reasons = PROOF.check_head_sprite(result)
        assert ok is False
        assert any("anchor" in r for r in reasons)

    def test_abnormal_display_bounds_rejects(self):
        result = {
            "headSprite": _head_sprite(
                bounds={"x": 400, "y": 300, "width": 248, "height": 248}
            ),
            "texturesUnchanged": None,
        }
        ok, reasons = PROOF.check_head_sprite(result)
        assert ok is False
        assert any("display bounds" in r for r in reasons)


class TestOtherTexturesUnchanged:
    def _result(self, textures_unchanged=True, **after_overrides):
        after = {
            "sea-otter-eyes-open": "otter.eyes.open",
            "sea-otter-eyes-closed": "otter.eyes.closed",
            "sea-otter-mouth-neutral": "otter.mouth.neutral",
            "sea-otter-mouth-concern": "otter.mouth.concern",
            "sea-otter-mouth-smile": "otter.mouth.smile",
            "sea-otter-torso": "otter.torso",
        }
        after.update(after_overrides)
        return {"texturesUnchanged": textures_unchanged, "otherRigTextures": after}

    def test_overlays_unchanged_passes(self):
        ok, reasons = PROOF.check_other_textures(self._result())
        assert ok is True, reasons

    def test_overlay_texture_change_rejects(self):
        result = self._result(**{"sea-otter-eyes-open": "otter.eyes.closed"})
        ok, reasons = PROOF.check_other_textures(result)
        assert ok is False
        assert any(
            "overlay texture changed" in r and "sea-otter-eyes-open" in r
            for r in reasons
        )

    def test_texture_map_change_rejects(self):
        result = self._result(textures_unchanged=False)
        ok, reasons = PROOF.check_other_textures(result)
        assert ok is False
        assert any("other rig textures changed" in r for r in reasons)


def _state_result(name):
    spec = {s["name"]: s for s in PROOF.FACE_STATES}[name]
    return {
        "headRotation": spec["rotation"],
        "eyesOpenVisible": spec["eyes"] == "open",
        "eyesClosedVisible": spec["eyes"] == "closed",
        "mouthNeutralVisible": spec["mouth"] == "neutral",
        "mouthConcernVisible": spec["mouth"] == "concern",
        "mouthSmileVisible": spec["mouth"] == "smile",
    }


class TestFaceStates:
    def test_all_four_states_valid(self):
        for spec in PROOF.FACE_STATES:
            ok, reasons = PROOF.validate_face_state(
                spec["name"], _state_result(spec["name"])
            )
            assert ok is True, "{}: {}".format(spec["name"], reasons)

    def test_base_only_hides_all_overlays(self):
        state = _state_result("base-only")
        assert state["eyesOpenVisible"] is False
        assert state["eyesClosedVisible"] is False
        assert state["mouthNeutralVisible"] is False
        assert state["mouthConcernVisible"] is False
        assert state["mouthSmileVisible"] is False

    def test_neutral_visibility(self):
        state = _state_result("neutral")
        assert state["eyesOpenVisible"] is True
        assert state["eyesClosedVisible"] is False
        assert state["mouthNeutralVisible"] is True
        assert state["mouthConcernVisible"] is False
        assert state["mouthSmileVisible"] is False

    def test_concern_visibility_and_rotation(self):
        state = _state_result("concern")
        assert state["headRotation"] == 0.035
        assert state["eyesOpenVisible"] is True
        assert state["mouthConcernVisible"] is True
        assert state["mouthNeutralVisible"] is False
        assert state["mouthSmileVisible"] is False

    def test_smile_visibility_and_rotation(self):
        state = _state_result("smile")
        assert state["headRotation"] == -0.025
        assert state["eyesClosedVisible"] is True
        assert state["eyesOpenVisible"] is False
        assert state["mouthSmileVisible"] is True
        assert state["mouthNeutralVisible"] is False
        assert state["mouthConcernVisible"] is False

    def test_wrong_visibility_rejects(self):
        bad = _state_result("neutral")
        bad["eyesClosedVisible"] = True
        ok, reasons = PROOF.validate_face_state("neutral", bad)
        assert ok is False
        assert any("eyes-closed also visible" in r for r in reasons)

    def test_wrong_rotation_rejects(self):
        bad = _state_result("concern")
        bad["headRotation"] = 0.0
        ok, reasons = PROOF.validate_face_state("concern", bad)
        assert ok is False
        assert any("head rotation" in r for r in reasons)


class TestForbiddenProductionMutation:
    def test_production_paths_untouched_by_harness(self):
        forbidden = PROOF.FORBIDDEN_WRITE_PREFIXES
        assert "domains/ocean-rescue/assets/handoff/inbox/" in forbidden
        assert "domains/ocean-rescue/assets/source/" in forbidden
        assert "domains/ocean-rescue/assets/generated/" in forbidden
        assert "domains/ocean-rescue/src/" in forbidden
        assert "ocean-rescue/index.html" in forbidden

        source = PROOF_SCRIPT.read_text(encoding="utf-8")

        write_calls = re.findall(
            r"(?:\.write_bytes|\.write_text|open\([^)]+['\"]w[^)]*\))", source
        )
        assert write_calls, "expected write calls in the harness"

        for prefix in (
            "domains/ocean-rescue/assets/handoff/inbox",
            "domains/ocean-rescue/assets/source",
            "domains/ocean-rescue/assets/generated",
            "domains/ocean-rescue/src",
            "ocean-rescue/index.html",
        ):
            assert not re.search(
                r'(?:write_text|write_bytes|open)\(\s*[^)]*["\']' + re.escape(prefix),
                source,
            ), "harness writes into forbidden production path: {}".format(prefix)

    def test_production_files_guard_list(self):
        for rel in PROOF.PRODUCTION_FILES:
            assert not rel.startswith(
                "domains/ocean-rescue/assets/review/handoff-proof/"
            )
            assert (REPO_ROOT / rel).is_file(), "missing production file {}".format(rel)


def _tiny_png() -> bytes:
    import struct
    import zlib

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    raw = b"\x00" + b"\x00\x00\x00\x00"
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class TestManifestProofImages:
    def _fixture(self, tmp_path):
        svg = MINIMAL_SVG
        svg_path = _write(tmp_path / "inbox" / "otter-head-01.svg", svg)
        structure = {
            "assetId": ASSET_ID,
            "alias": ALIAS,
            "svgSha256": _sha256_bytes(svg.encode("utf-8")),
            "verdict": "STRUCTURE_PASS",
        }
        structure_path = _write(
            tmp_path / "review" / "structure-report.json", json.dumps(structure)
        )
        out = tmp_path / "out"
        out.mkdir(parents=True, exist_ok=True)
        for name in (
            "isolated-1x.png",
            "isolated-2x.png",
            "rig-base-only.png",
            "rig-neutral.png",
            "rig-concern.png",
            "rig-smile.png",
            "face-rig-contact-sheet.png",
            "sea-turtle-context.png",
        ):
            (out / name).write_bytes(_tiny_png())

        isolated = {
            "1x": {
                "fileSha256": _sha256_bytes((out / "isolated-1x.png").read_bytes()),
                "pixelSha256": "0" * 64,
                "byteSize": 1,
                "width": 200,
                "height": 200,
                "alphaPresent": True,
                "visibleAlphaBounds": {"x": 10, "y": 10, "width": 180, "height": 180},
            },
            "2x": {
                "fileSha256": _sha256_bytes((out / "isolated-2x.png").read_bytes()),
                "pixelSha256": "0" * 64,
                "byteSize": 1,
                "width": 400,
                "height": 400,
                "alphaPresent": True,
                "visibleAlphaBounds": {"x": 20, "y": 20, "width": 360, "height": 360},
            },
        }
        head = _head_sprite()
        run = {
            "runIndex": 1,
            "diag": {
                "data-render-backend": "webgl",
                "data-sea-turtle-scene": "active",
                "data-sea-turtle-scene-animation": "paused",
                "data-sea-turtle-scene-legacy-visible": "false",
                "data-rescue-phase": "active",
            },
            "headSprite": head,
            "faceState": _state_result("smile"),
            "texturesUnchanged": True,
            "otherRigTextures": {"sea-otter-eyes-open": "otter.eyes.open"},
            "frozen": True,
            "legacyBridgeVisible": False,
            "states": {
                name: {
                    "cropFileSha256": _sha256_bytes(
                        (out / "rig-{}.png".format(name)).read_bytes()
                    ),
                    "cropPixelSha256": "0" * 64,
                    "cropWidth": 300,
                    "cropHeight": 300,
                    "stateResult": _state_result(name),
                }
                for name in ("base-only", "neutral", "concern", "smile")
            },
            "context": {"pixelSha256": "1" * 64},
            "externalOriginRequestCount": 0,
            "pageErrorCount": 0,
            "consoleErrorCount": 0,
            "unhandledRejectionCount": 0,
            "securityPolicyViolationCount": 0,
        }
        args = type(
            "Args",
            (),
            {
                "repo_root": str(tmp_path),
                "brief": "briefs/otter-head-01.md",
                "svg": "inbox/otter-head-01.svg",
                "structure_report": "review/structure-report.json",
                "output_dir": str(out),
            },
        )
        return args, tmp_path, out, isolated, [run], structure_path, svg_path

    def test_manifest_records_all_proof_file_shas(self, tmp_path):
        args, repo_root, out, isolated, runs, structure_path, svg_path = self._fixture(
            tmp_path
        )
        manifest = PROOF.build_manifest(
            args, repo_root, out, isolated, runs, "RENDER_PROOF_READY", []
        )
        images = manifest["proofImages"]
        names = [i["path"] for i in images]
        assert names == [
            "isolated-1x.png",
            "isolated-2x.png",
            "rig-base-only.png",
            "rig-neutral.png",
            "rig-concern.png",
            "rig-smile.png",
            "face-rig-contact-sheet.png",
            "sea-turtle-context.png",
        ]
        for image in images:
            path = out / image["path"]
            assert path.is_file()
            assert image["fileSha256"] == _sha256_bytes(path.read_bytes())
        assert manifest["candidateSvgSha256"] == _sha256_bytes(svg_path.read_bytes())
        assert manifest["structureReportSha256"] == _sha256_bytes(
            structure_path.read_bytes()
        )
        assert manifest["candidateTextureApplied"] is True
        assert manifest["otherTexturesUnchanged"] is True
        assert manifest["viewBox"] == "0 0 200 200"
        assert manifest["pivot"] == [0.5, 0.55]
        assert manifest["runtimeScale"] == [0.62, 0.62]
