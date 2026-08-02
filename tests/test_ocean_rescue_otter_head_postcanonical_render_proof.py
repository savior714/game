"""Focused tests for the otter-head-01 post-canonical render proof harness.

These tests verify the gate, validation, reconstruction, and manifest logic of
the post-canonical proof script. The real atlas reconstruction tests operate on
the tracked production atlas PNG and canonical SVG (exactly like
``test_ocean_rescue_atlas_rgba_copy_contract``); the browser-facing capture
logic is validated structurally and via pure fixtures only.

Covered contracts:

1. Task ID suffix is ``PROOF-02``.
2. The atlas-repair commit is bound as an ancestry/input contract.
3. The canonical SVG is the isolated render input.
4. The handoff inbox candidate is never a runtime input.
5. Candidate texture injection tokens/behavior are absent.
6. The real atlas PNG is reconstructed as RGBA.
7. The reconstruction uses the expected 400x400 source canvas.
8. The reconstruction pixel SHA equals the approved 2x SHA.
9. Mismatched pixel/channel counts are 0.
10. The runtime head texture label is ``otter.head``.
11. Four face states are captured.
12. Face-state visibility/rotation contract is exact.
13. Two independent browser runs are performed.
14. CDP capture happens immediately after diagnostics on the same target.
15. Runtime error counters are inspected.
16. Production hash snapshot is compared before/after.
17. Pre-canonical evidence snapshot is compared before/after.
18. The manifest contains every required field.
19. The eight proof PNG SHA/dimension records are valid.
20. The output root is under ``post-canonical/``.
21. Existing pre-canonical proof files are never overwritten.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import re

CAIRO_LIB_DIR = "/opt/homebrew/opt/cairo/lib"
os.environ["DYLD_LIBRARY_PATH"] = (
    f"{CAIRO_LIB_DIR}:{os.environ.get('DYLD_LIBRARY_PATH', '')}"
)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PROOF_SCRIPT = (
    REPO_ROOT
    / "scripts"
    / "ocean-rescue"
    / "capture-otter-head-postcanonical-render-proof.py"
)

STRUCTURE_REPORT = (
    REPO_ROOT
    / "domains"
    / "ocean-rescue"
    / "assets"
    / "review"
    / "handoff-intake"
    / "otter-head-01"
    / "structure-report.json"
)
PRECANONICAL_MANIFEST = (
    REPO_ROOT
    / "domains"
    / "ocean-rescue"
    / "assets"
    / "review"
    / "handoff-proof"
    / "otter-head-01"
    / "manifest.json"
)
CANONICAL_SVG = (
    REPO_ROOT
    / "domains"
    / "ocean-rescue"
    / "assets"
    / "source"
    / "characters"
    / "otter-head.svg"
)


def _load_proof():
    spec = importlib.util.spec_from_file_location(
        "ocean_rescue_otter_head_postcanonical_render_proof", PROOF_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load proof script {PROOF_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROOF = _load_proof()

ASSET_ID = "otter-head-01"
ALIAS = "otter.head"


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


class TestTaskIdentity:
    def test_task_id_suffix_is_proof_02(self):
        assert PROOF.TASK_ID.endswith("PROOF-02")
        assert (
            PROOF.TASK_ID
            == "AIDENGAME-OCEAN-RESCUE-OTTER-HEAD-POST-CANONICAL-RENDER-PROOF-02"
        )

    def test_asset_and_alias(self):
        assert PROOF.ASSET_ID == "otter-head-01"
        assert PROOF.ALIAS == "otter.head"


class TestAtlasRepairAncestryBinding:
    def test_repair_commit_constant(self):
        assert PROOF.ATLAS_REPAIR_COMMIT == "e8bb970c0c8dac394c662bead5fbc3d4160927c3"
        assert (
            PROOF.CANONICALIZATION_COMMIT == "fba9c1a3a581d89c1b98cb903f78eb43c6652db5"
        )

    def test_repair_ancestry_holds_in_repo(self):
        assert PROOF.check_repair_ancestry(REPO_ROOT) is True

    def test_repair_ancestry_missing_in_non_git_dir(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            assert PROOF.check_repair_ancestry(pathlib.Path(d)) is False

    def test_input_gate_binds_repair_ancestry_contract(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            svg = tmp / "canonical.svg"
            svg.write_bytes(CANONICAL_SVG.read_bytes())
            args = type(
                "Args",
                (),
                {
                    "canonical_svg": str(svg),
                    "structure_report": str(STRUCTURE_REPORT),
                    "precanonical_manifest": str(PRECANONICAL_MANIFEST),
                },
            )()
            ok, code = PROOF.run_input_gate(tmp, args)
            assert ok is False
            assert code == "ATLAS_REPAIR_COMMIT_NOT_IN_ANCESTRY"


class TestCanonicalSourceIsIsolatedInput:
    def test_canonical_svg_path(self):
        assert PROOF.CANONICAL_SVG_PATH == (
            "domains/ocean-rescue/assets/source/characters/otter-head.svg"
        )

    def test_canonical_svg_sha_is_approved(self):
        assert PROOF.APPROVED_CANDIDATE_SHA == (
            "87e6b35d67e0d856d389570614bb47abef9f6271402e881660f98f400e40c5ec"
        )
        assert _sha256_bytes(CANONICAL_SVG.read_bytes()) == PROOF.APPROVED_CANDIDATE_SHA

    def test_isolated_1x_approved_pixel(self):
        png = PROOF.render_svg_to_png(CANONICAL_SVG, 200, 200)
        analysis = PROOF.analyze_isolated_png(png, 200, 200)
        ok, reasons = PROOF.check_isolated_approved(analysis)
        assert ok is True, reasons
        assert analysis["pixelSha256"] == PROOF.APPROVED_1X_PIXEL_SHA

    def test_isolated_2x_approved_pixel(self):
        png = PROOF.render_svg_to_png(CANONICAL_SVG, 400, 400)
        analysis = PROOF.analyze_isolated_png(png, 400, 400)
        ok, reasons = PROOF.check_isolated_approved(analysis)
        assert ok is True, reasons
        assert analysis["pixelSha256"] == PROOF.APPROVED_2X_PIXEL_SHA

    def test_input_gate_rejects_wrong_canonical_sha(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            svg = tmp / "canonical.svg"
            svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
                '<g id="otter-head"></g></svg>',
                encoding="utf-8",
            )
            args = type(
                "Args",
                (),
                {
                    "canonical_svg": str(svg),
                    "structure_report": str(STRUCTURE_REPORT),
                    "precanonical_manifest": str(PRECANONICAL_MANIFEST),
                },
            )()
            ok, code = PROOF.run_input_gate(tmp, args)
            assert ok is False
            assert code == "CANONICAL_SVG_SHA_MISMATCH"


class TestInboxNotRuntimeInput:
    def test_inbox_not_referenced(self):
        source = PROOF_SCRIPT.read_text(encoding="utf-8")
        assert "assets/handoff/inbox" not in source
        assert "handoff/inbox" not in source

    def test_forbidden_write_prefixes_exclude_inbox(self):
        assert "domains/ocean-rescue/assets/handoff/inbox/" not in (
            PROOF.FORBIDDEN_WRITE_PREFIXES
        )


class TestCandidateInjectionAbsent:
    def test_no_candidate_injection_tokens(self):
        source = PROOF_SCRIPT.read_text(encoding="utf-8")
        tokens = PROOF.find_injection_tokens(source)
        assert tokens == [], "injection tokens present: {}".format(tokens)

    def test_known_forbidden_tokens_covered(self):
        for tok in (
            "candidate-otter-head-01",
            "PIXI.Texture.from",
            "base64",
            "head.texture =",
            "ImageSource",
        ):
            assert tok in PROOF.FORBIDDEN_INJECTION_TOKENS

    def test_apply_candidate_script_absent(self):
        source = PROOF_SCRIPT.read_text(encoding="utf-8")
        assert "APPLY_CANDIDATE_SCRIPT" not in source
        assert "candidate_data_uri" not in source


class TestRealAtlasReconstruction:
    def test_reconstruction_uses_real_atlas_png(self):
        recon = PROOF.reconstruct_atlas_frame(REPO_ROOT)
        assert recon["frame"] == PROOF.ATLAS_FRAME
        assert recon["sourceSize"] == {"w": 400, "h": 400}
        assert recon["spriteSourceSize"] == PROOF.ATLAS_SPRITE_SOURCE
        assert recon["rotated"] is False
        assert recon["trimmed"] is True

    def test_reconstruction_source_canvas_is_400x400(self):
        recon = PROOF.reconstruct_atlas_frame(REPO_ROOT)
        assert recon["reconstructedSize"] == [400, 400]

    def test_reconstruction_sha_equals_approved_2x(self):
        recon = PROOF.reconstruct_atlas_frame(REPO_ROOT)
        assert recon["reconstructedPixelSha256"] == PROOF.APPROVED_2X_PIXEL_SHA
        assert recon["canonical2xPixelSha256"] == PROOF.APPROVED_2X_PIXEL_SHA
        assert PROOF.APPROVED_2X_PIXEL_SHA == (
            "dee47164ab12d192d93fd66efdbb0909febac683a0be09aafe56c3ae92221d14"
        )

    def test_reconstruction_mismatch_zero(self):
        recon = PROOF.reconstruct_atlas_frame(REPO_ROOT)
        assert recon["pixelExact"] is True
        assert recon["mismatchedPixels"] == 0
        assert recon["mismatchedChannels"] == 0

    def test_reconstruction_passes_gate(self):
        recon = PROOF.reconstruct_atlas_frame(REPO_ROOT)
        ok, reasons = PROOF.check_atlas_reconstruction(recon)
        assert ok is True, reasons


def _head_sprite(**overrides):
    head = {
        "label": "sea-otter-head",
        "isSprite": True,
        "visible": True,
        "renderable": True,
        "x": 0,
        "y": -42,
        "rotation": 0.0,
        "scaleX": 0.62,
        "scaleY": 0.62,
        "anchor": {"x": 0.5, "y": 0.55},
        "textureLabel": PROOF.HEAD_TEXTURE_LABEL,
        "textureFrame": {"x": 2, "y": 2, "w": 170, "h": 169},
        "textureOrig": {"w": 200, "h": 200},
        "textureResolution": 2,
        "bounds": {"x": 528, "y": 310, "width": 124, "height": 124},
    }
    head.update(overrides)
    return head


class TestRuntimeTextureIdentity:
    def test_head_texture_label_is_otter_head(self):
        assert PROOF.HEAD_TEXTURE_LABEL == "otter.head"
        assert PROOF.HEAD_SPRITE_LABEL == "sea-otter-head"

    def test_production_head_sprite_passes(self):
        result = {"headSprite": _head_sprite()}
        ok, reasons = PROOF.check_head_sprite(result)
        assert ok is True, reasons

    def test_head_missing_rejects(self):
        ok, reasons = PROOF.check_head_sprite({"headSprite": None})
        assert ok is False
        assert any("head sprite missing" in r for r in reasons)

    def test_candidate_label_rejects(self):
        result = {"headSprite": _head_sprite(textureLabel="candidate-otter-head-01")}
        ok, reasons = PROOF.check_head_sprite(result)
        assert ok is False
        assert any("texture label != otter.head" in r for r in reasons)

    def test_wrong_texture_orig_rejects(self):
        result = {"headSprite": _head_sprite(textureOrig={"w": 400, "h": 400})}
        ok, reasons = PROOF.check_head_sprite(result)
        assert ok is False
        assert any("texture orig" in r for r in reasons)

    def test_anchor_scale_contract(self):
        assert PROOF.PIVOT == [0.5, 0.55]
        assert PROOF.RUNTIME_SCALE == [0.62, 0.62]

    def test_overlay_alias_contract(self):
        assert PROOF.OVERLAY_TEXTURE_ALIASES["sea-otter-eyes-open"] == "otter.eyes.open"
        assert (
            PROOF.OVERLAY_TEXTURE_ALIASES["sea-otter-eyes-closed"]
            == "otter.eyes.closed"
        )
        assert (
            PROOF.OVERLAY_TEXTURE_ALIASES["sea-otter-mouth-neutral"]
            == "otter.mouth.neutral"
        )
        assert (
            PROOF.OVERLAY_TEXTURE_ALIASES["sea-otter-mouth-concern"]
            == "otter.mouth.concern"
        )
        assert (
            PROOF.OVERLAY_TEXTURE_ALIASES["sea-otter-mouth-smile"]
            == "otter.mouth.smile"
        )
        assert PROOF.OVERLAY_TEXTURE_ALIASES["sea-otter-torso"] == "otter.torso"
        assert PROOF.OVERLAY_TEXTURE_ALIASES["sea-otter-arm-near"] == "otter.arm.near"
        assert PROOF.OVERLAY_TEXTURE_ALIASES["sea-otter-arm-far"] == "otter.arm.far"
        assert PROOF.OVERLAY_TEXTURE_ALIASES["sea-otter-tail"] == "otter.tail"

    def test_overlay_identities_pass(self):
        overlays = {
            label: {
                "label": label,
                "textureLabel": alias,
                "textureResolution": 2,
            }
            for label, alias in PROOF.OVERLAY_TEXTURE_ALIASES.items()
        }
        ok, reasons = PROOF.check_overlay_identities({"overlays": overlays})
        assert ok is True, reasons

    def test_overlay_change_rejects(self):
        overlays = {
            label: {"label": label, "textureLabel": alias, "textureResolution": 2}
            for label, alias in PROOF.OVERLAY_TEXTURE_ALIASES.items()
        }
        overlays["sea-otter-eyes-open"]["textureLabel"] = "otter.eyes.closed"
        ok, reasons = PROOF.check_overlay_identities({"overlays": overlays})
        assert ok is False
        assert any("sea-otter-eyes-open" in r for r in reasons)


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
    def test_four_states_captured(self):
        names = [s["name"] for s in PROOF.FACE_STATES]
        assert names == ["base-only", "neutral", "concern", "smile"]

    def test_face_states_valid(self):
        for spec in PROOF.FACE_STATES:
            ok, reasons = PROOF.validate_face_state(
                spec["name"], _state_result(spec["name"])
            )
            assert ok is True, "{}: {}".format(spec["name"], reasons)

    def test_rotations(self):
        expected = {"base-only": 0.0, "neutral": 0.0, "concern": 0.035, "smile": -0.025}
        for name, rotation in expected.items():
            assert _state_result(name)["headRotation"] == rotation

    def test_concern_visibility(self):
        state = _state_result("concern")
        assert state["eyesOpenVisible"] is True
        assert state["mouthConcernVisible"] is True
        assert state["mouthNeutralVisible"] is False
        assert state["mouthSmileVisible"] is False

    def test_smile_visibility(self):
        state = _state_result("smile")
        assert state["eyesClosedVisible"] is True
        assert state["eyesOpenVisible"] is False
        assert state["mouthSmileVisible"] is True
        assert state["mouthNeutralVisible"] is False

    def test_base_only_hides_all(self):
        state = _state_result("base-only")
        assert not any(
            [
                state["eyesOpenVisible"],
                state["eyesClosedVisible"],
                state["mouthNeutralVisible"],
                state["mouthConcernVisible"],
                state["mouthSmileVisible"],
            ]
        )

    def test_wrong_visibility_rejects(self):
        bad = _state_result("neutral")
        bad["eyesClosedVisible"] = True
        ok, reasons = PROOF.validate_face_state("neutral", bad)
        assert ok is False
        assert any("eyes-closed also visible" in r for r in reasons)


class TestTwoRunDeterminism:
    def test_two_independent_runs(self):
        source = PROOF_SCRIPT.read_text(encoding="utf-8")
        assert "for run_index in (1, 2):" in source
        assert "run_in_context_capture(repo_root, base_url, run_index)" in source

    def test_cdp_capture_same_target_after_diagnostics(self):
        source = PROOF_SCRIPT.read_text(encoding="utf-8")
        assert "pg.evaluate(COLLECT_SCRIPT)" in source
        assert 'pg.locator("#ocean-rescue-canvas")' in source
        assert "canvas.screenshot()" in source
        # Diagnostics are read before the screenshot of each state on the same
        # page target inside run_in_context_capture.
        assert source.index("pg.evaluate(COLLECT_SCRIPT)") < source.index(
            "full_png, state_result = capture_face_state(pg, state_spec)"
        )
        assert "def capture_face_state" in source
        # No separate dump-DOM process.
        assert "dump-DOM" not in source
        assert "dump_dom" not in source

    def test_compare_runs_equality(self):
        def run():
            return {
                "diag": {
                    "data-render-backend": "webgl",
                    "data-sea-turtle-scene": "paused",
                    "data-sea-turtle-scene-animation": "paused",
                    "data-sea-turtle-scene-legacy-visible": "false",
                    "data-rescue-phase": "active",
                },
                "headSprite": _head_sprite(),
                "overlays": {
                    label: {
                        "label": label,
                        "textureLabel": alias,
                        "textureResolution": 2,
                    }
                    for label, alias in PROOF.OVERLAY_TEXTURE_ALIASES.items()
                },
                "candidateInjectionAbsent": True,
                "frozen": True,
                "legacyBridgeVisible": False,
                "states": {
                    name: {
                        "cropPixelSha256": "a" * 64,
                        "stateResult": _state_result(name),
                    }
                    for name in ("base-only", "neutral", "concern", "smile")
                },
                "context": {"pixelSha256": "b" * 64},
                "externalOriginRequestCount": 0,
                "pageErrorCount": 0,
                "consoleErrorCount": 0,
                "unhandledRejectionCount": 0,
                "securityPolicyViolationCount": 0,
            }

        ok, reasons = PROOF.compare_runs(run(), run())
        assert ok is True, reasons

    def test_compare_runs_detects_crop_difference(self):
        r1 = {
            "diag": {
                "data-render-backend": "webgl",
                "data-sea-turtle-scene": "paused",
                "data-sea-turtle-scene-animation": "paused",
                "data-sea-turtle-scene-legacy-visible": "false",
                "data-rescue-phase": "active",
            },
            "headSprite": _head_sprite(),
            "overlays": {},
            "candidateInjectionAbsent": True,
            "frozen": True,
            "legacyBridgeVisible": False,
            "states": {
                name: {"cropPixelSha256": "a" * 64, "stateResult": _state_result(name)}
                for name in ("base-only", "neutral", "concern", "smile")
            },
            "context": {"pixelSha256": "b" * 64},
        }
        r2 = dict(r1)
        r2["states"] = {
            name: {
                "cropPixelSha256": ("c" if name == "smile" else "a") * 64,
                "stateResult": _state_result(name),
            }
            for name in ("base-only", "neutral", "concern", "smile")
        }
        ok, reasons = PROOF.compare_runs(r1, r2)
        assert ok is False
        assert any("smile crop pixel differs" in r for r in reasons)


class TestRuntimeErrorContract:
    def _result(self, **overrides):
        result = {
            "diag": {
                "data-ocean-rescue-ready": "true",
                "data-render-runtime": "ready",
                "data-render-backend": "webgl",
                "data-rescue-phase": "active",
                "data-sea-turtle-scene": "paused",
                "data-sea-turtle-scene-animation": "paused",
                "data-sea-turtle-scene-legacy-visible": "false",
            },
            "frozen": True,
            "legacyBridgeVisible": False,
            "candidateInjectionAbsent": True,
            "externalOriginRequestCount": 0,
            "pageErrorCount": 0,
            "consoleErrorCount": 0,
            "unhandledRejectionCount": 0,
            "securityPolicyViolationCount": 0,
            "states": {
                name: {
                    "fullWidth": 1280,
                    "fullHeight": 720,
                    "cropWidth": 300,
                    "cropHeight": 300,
                }
                for name in ("base-only", "neutral", "concern", "smile")
            },
            "context": {"pixelSha256": "1" * 64},
        }
        result.update(overrides)
        return result

    def test_all_zero_passes(self):
        ok, reasons = PROOF.check_capture_state(self._result())
        assert ok is True, reasons

    def test_page_error_rejects(self):
        ok, reasons = PROOF.check_capture_state(
            self._result(pageErrorCount=1, pageErrors=["boom"])
        )
        assert ok is False
        assert any("page errors != 0" in r for r in reasons)

    def test_external_request_rejects(self):
        ok, reasons = PROOF.check_capture_state(
            self._result(externalOriginRequestCount=1, externalRequests=["http://x"])
        )
        assert ok is False
        assert any("external-origin requests != 0" in r for r in reasons)

    def test_candidate_injection_flag_rejects(self):
        ok, reasons = PROOF.check_capture_state(
            self._result(candidateInjectionAbsent=False)
        )
        assert ok is False
        assert any("candidate texture injection detected" in r for r in reasons)


class TestImmutabilityContracts:
    def test_production_files_guard(self):
        for rel in PROOF.PRODUCTION_FILES:
            assert not rel.startswith(
                "domains/ocean-rescue/assets/review/handoff-proof/"
            )
            assert (REPO_ROOT / rel).is_file(), "missing production file {}".format(rel)

    def test_production_files_include_core_runtime(self):
        assert "ocean-rescue/index.html" in PROOF.PRODUCTION_FILES
        assert (
            "domains/ocean-rescue/src/render-assets.generated.js"
            in PROOF.PRODUCTION_FILES
        )
        assert "domains/ocean-rescue/assets/generated/characters/characters-0.png" in (
            PROOF.PRODUCTION_FILES
        )

    def test_pre_canonical_evidence_guard(self):
        assert len(PROOF.PRECANONICAL_EVIDENCE_FILES) == 10
        for rel in PROOF.PRECANONICAL_EVIDENCE_FILES:
            assert (REPO_ROOT / rel).is_file(), "missing evidence file {}".format(rel)

    def test_production_snapshot_before_after_in_main(self):
        source = PROOF_SCRIPT.read_text(encoding="utf-8")
        assert "sha256_file(repo_root / p) for p in PRODUCTION_FILES" in source
        assert "PRODUCTION_FILES_MUTATED_DURING_PROOF" in source

    def test_pre_evidence_snapshot_before_after_in_main(self):
        source = PROOF_SCRIPT.read_text(encoding="utf-8")
        assert (
            "sha256_file(repo_root / p) for p in PRECANONICAL_EVIDENCE_FILES" in source
        )
        assert "PRECANONICAL_EVIDENCE_MUTATED_DURING_PROOF" in source

    def test_canonical_svg_immutability_guard(self):
        source = PROOF_SCRIPT.read_text(encoding="utf-8")
        assert "CANONICAL_SVG_MUTATED_DURING_PROOF" in source


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


class TestOutputRootContract:
    def test_output_root_under_post_canonical(self):
        out = PROOF.PRECANONICAL_PROOF_DIR / "post-canonical"
        assert str(out).endswith("handoff-proof/otter-head-01/post-canonical")

    def test_pre_canonical_proof_dir_not_writable(self):
        assert str(PROOF.PRECANONICAL_PROOF_DIR / "post-canonical") != str(
            PROOF.PRECANONICAL_PROOF_DIR
        )
        forbidden = PROOF.FORBIDDEN_WRITE_PREFIXES
        assert (
            "domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/"
            in forbidden
        )

    def test_no_overwrite_of_existing_proof_files(self):
        source = PROOF_SCRIPT.read_text(encoding="utf-8")
        assert PROOF.PRECANONICAL_PROOF_DIR.name == "otter-head-01"
        assert PROOF.PRECANONICAL_PROOF_DIR.parts[-3:] == (
            "review",
            "handoff-proof",
            "otter-head-01",
        )
        post_canonical = PROOF.PRECANONICAL_PROOF_DIR / "post-canonical"
        assert post_canonical.parts[-4:] == (
            "review",
            "handoff-proof",
            "otter-head-01",
            "post-canonical",
        )
        # Every write target must be an output_dir-relative path under the
        # post-canonical evidence root; the pre-canonical proof dir is never
        # written.
        write_calls = re.findall(r"(?:\.write_bytes|\.write_text)\(", source)
        assert write_calls, "expected write calls in the harness"
        for prefix in (
            "domains/ocean-rescue/assets/source",
            "domains/ocean-rescue/assets/generated",
            "domains/ocean-rescue/assets/review/handoff-proof/otter-head-01/",
            "domains/ocean-rescue/src",
            "ocean-rescue/index.html",
        ):
            assert not re.search(
                r'(?:write_text|write_bytes)\(\s*[^)]*["\']' + re.escape(prefix),
                source,
            ), "harness writes into forbidden path: {}".format(prefix)
        assert re.search(r"output_dir\s*/\s*[\"']", source)


def _manifest_fixture(tmp_path):
    out = tmp_path / "post-canonical"
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
            "pixelSha256": PROOF.APPROVED_1X_PIXEL_SHA,
            "byteSize": 1,
            "width": 200,
            "height": 200,
            "alphaPresent": True,
            "visibleAlphaBounds": {"x": 15, "y": 21, "width": 170, "height": 169},
        },
        "2x": {
            "fileSha256": _sha256_bytes((out / "isolated-2x.png").read_bytes()),
            "pixelSha256": PROOF.APPROVED_2X_PIXEL_SHA,
            "byteSize": 1,
            "width": 400,
            "height": 400,
            "alphaPresent": True,
            "visibleAlphaBounds": {"x": 30, "y": 42, "width": 340, "height": 338},
        },
    }
    atlas_recon = {
        "frame": PROOF.ATLAS_FRAME,
        "sourceSize": {"w": 400, "h": 400},
        "spriteSourceSize": PROOF.ATLAS_SPRITE_SOURCE,
        "rotated": False,
        "trimmed": True,
        "anchor": {"x": 0.5, "y": 0.55},
        "reconstructedSize": [400, 400],
        "reconstructedPixelSha256": PROOF.APPROVED_2X_PIXEL_SHA,
        "canonical2xPixelSha256": PROOF.APPROVED_2X_PIXEL_SHA,
        "pixelExact": True,
        "mismatchedPixels": 0,
        "mismatchedChannels": 0,
    }
    head = _head_sprite()
    run = {
        "runIndex": 1,
        "diag": {
            "data-render-backend": "webgl",
            "data-sea-turtle-scene": "paused",
            "data-sea-turtle-scene-animation": "paused",
            "data-sea-turtle-scene-legacy-visible": "false",
            "data-rescue-phase": "active",
        },
        "headSprite": head,
        "overlays": {
            label: {
                "label": label,
                "textureLabel": alias,
                "textureResolution": 2,
            }
            for label, alias in PROOF.OVERLAY_TEXTURE_ALIASES.items()
        },
        "faceState": _state_result("neutral"),
        "candidateInjectionAbsent": True,
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
            "repo_root": str(REPO_ROOT),
            "canonical_svg": str(CANONICAL_SVG),
            "structure_report": str(STRUCTURE_REPORT),
            "precanonical_manifest": str(PRECANONICAL_MANIFEST),
            "output_dir": str(out),
        },
    )
    return args, REPO_ROOT, out, isolated, atlas_recon, [run]


class TestManifestContract:
    REQUIRED_FIELDS = [
        "schemaVersion",
        "taskId",
        "assetId",
        "alias",
        "sourceCommit",
        "canonicalizationCommit",
        "atlasRepairCommit",
        "humanApproval",
        "approvedCandidateSha256",
        "structureReportPath",
        "structureReportSha256",
        "structureVerdict",
        "preCanonicalProofManifestPath",
        "preCanonicalProofManifestSha256",
        "preCanonicalProofVerdict",
        "canonicalSourcePath",
        "canonicalSourceSha256",
        "artPacketPath",
        "artPacketSha256",
        "artPacketAssetSourceSha256",
        "artApprovalPath",
        "artApprovalSha256",
        "atlasManifestPath",
        "atlasManifestSha256",
        "charactersAtlasJsonPath",
        "charactersAtlasJsonSha256",
        "charactersAtlasPngPath",
        "charactersAtlasPngSha256",
        "renderAssetsPath",
        "renderAssetsSha256",
        "singleHtmlPath",
        "singleHtmlSha256",
        "rasterizer",
        "rasterizerVersion",
        "rendererBackend",
        "logicalViewport",
        "deviceScaleFactor",
        "sourceLogicalSize",
        "physicalRasterSize",
        "pivot",
        "runtimeScale",
        "isolated1x",
        "isolated2x",
        "atlasFrame",
        "atlasReconstructionPixelSha256",
        "canonical2xPixelSha256",
        "atlasCanonicalPixelExact",
        "atlasMismatchPixelCount",
        "atlasMismatchChannelCount",
        "headSprite",
        "overlaySprites",
        "runs",
        "twoRunDeterministic",
        "productionFilesUnchanged",
        "preCanonicalEvidenceUnchanged",
        "verdict",
        "rejectionReasons",
    ]

    def test_manifest_has_all_required_fields(self, tmp_path):
        args, repo_root, out, isolated, atlas_recon, runs = _manifest_fixture(tmp_path)
        manifest = PROOF.build_manifest(
            args,
            repo_root,
            out,
            isolated,
            atlas_recon,
            runs,
            "POST_CANONICAL_RENDER_PROOF_READY",
            [],
        )
        for field in self.REQUIRED_FIELDS:
            assert field in manifest, "missing manifest field: {}".format(field)

    def test_manifest_human_approval(self, tmp_path):
        args, repo_root, out, isolated, atlas_recon, runs = _manifest_fixture(tmp_path)
        manifest = PROOF.build_manifest(
            args,
            repo_root,
            out,
            isolated,
            atlas_recon,
            runs,
            "POST_CANONICAL_RENDER_PROOF_READY",
            [],
        )
        assert manifest["humanApproval"]["decision"] == "APPROVED"
        assert manifest["humanApproval"]["date"] == "2026-08-02"
        assert manifest["humanApproval"]["input"] == "승인"
        assert manifest["approvedCandidateSha256"] == PROOF.APPROVED_CANDIDATE_SHA
        assert manifest["humanApproval"]["approvedProofTaskId"] == (
            "AIDENGAME-OCEAN-RESCUE-OTTER-HEAD-HANDOFF-RENDER-PROOF-01"
        )

    def test_manifest_verdict(self, tmp_path):
        args, repo_root, out, isolated, atlas_recon, runs = _manifest_fixture(tmp_path)
        manifest = PROOF.build_manifest(
            args,
            repo_root,
            out,
            isolated,
            atlas_recon,
            runs,
            "POST_CANONICAL_RENDER_PROOF_READY",
            [],
        )
        assert manifest["verdict"] == "POST_CANONICAL_RENDER_PROOF_READY"

    def test_manifest_rejected_verdict(self, tmp_path):
        args, repo_root, out, isolated, atlas_recon, runs = _manifest_fixture(tmp_path)
        manifest = PROOF.build_manifest(
            args,
            repo_root,
            out,
            isolated,
            atlas_recon,
            runs,
            "POST_CANONICAL_RENDER_REJECTED",
            ["boom"],
        )
        assert manifest["verdict"] == "POST_CANONICAL_RENDER_REJECTED"
        assert manifest["rejectionReasons"] == ["boom"]

    def test_manifest_commit_bindings(self, tmp_path):
        args, repo_root, out, isolated, atlas_recon, runs = _manifest_fixture(tmp_path)
        manifest = PROOF.build_manifest(
            args,
            repo_root,
            out,
            isolated,
            atlas_recon,
            runs,
            "POST_CANONICAL_RENDER_PROOF_READY",
            [],
        )
        assert manifest["sourceCommit"] == PROOF.CANONICALIZATION_COMMIT
        assert manifest["canonicalizationCommit"] == PROOF.CANONICALIZATION_COMMIT
        assert manifest["atlasRepairCommit"] == PROOF.ATLAS_REPAIR_COMMIT

    def test_manifest_runtime_contract(self, tmp_path):
        args, repo_root, out, isolated, atlas_recon, runs = _manifest_fixture(tmp_path)
        manifest = PROOF.build_manifest(
            args,
            repo_root,
            out,
            isolated,
            atlas_recon,
            runs,
            "POST_CANONICAL_RENDER_PROOF_READY",
            [],
        )
        assert manifest["rendererBackend"] == "webgl"
        assert manifest["logicalViewport"] == [1280, 720]
        assert manifest["deviceScaleFactor"] == 1
        assert manifest["sourceLogicalSize"] == [200, 200]
        assert manifest["physicalRasterSize"] == [400, 400]
        assert manifest["pivot"] == [0.5, 0.55]
        assert manifest["runtimeScale"] == [0.62, 0.62]
        assert manifest["rasterizer"] == "CairoSVG"
        assert manifest["rasterizerVersion"] == "2.9.0"

    def test_manifest_atlas_reconstruction(self, tmp_path):
        args, repo_root, out, isolated, atlas_recon, runs = _manifest_fixture(tmp_path)
        manifest = PROOF.build_manifest(
            args,
            repo_root,
            out,
            isolated,
            atlas_recon,
            runs,
            "POST_CANONICAL_RENDER_PROOF_READY",
            [],
        )
        assert manifest["atlasReconstructionPixelSha256"] == PROOF.APPROVED_2X_PIXEL_SHA
        assert manifest["canonical2xPixelSha256"] == PROOF.APPROVED_2X_PIXEL_SHA
        assert manifest["atlasCanonicalPixelExact"] is True
        assert manifest["atlasMismatchPixelCount"] == 0
        assert manifest["atlasMismatchChannelCount"] == 0
        assert manifest["isolated1x"]["pixelSha256"] == PROOF.APPROVED_1X_PIXEL_SHA
        assert manifest["isolated2x"]["pixelSha256"] == PROOF.APPROVED_2X_PIXEL_SHA

    def test_manifest_8_proof_png_records(self, tmp_path):
        args, repo_root, out, isolated, atlas_recon, runs = _manifest_fixture(tmp_path)
        manifest = PROOF.build_manifest(
            args,
            repo_root,
            out,
            isolated,
            atlas_recon,
            runs,
            "POST_CANONICAL_RENDER_PROOF_READY",
            [],
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
            assert image["width"] >= 1 and image["height"] >= 1
        assert manifest["isolated1x"]["width"] == 200
        assert manifest["isolated1x"]["height"] == 200
        assert manifest["isolated2x"]["width"] == 400
        assert manifest["isolated2x"]["height"] == 400
