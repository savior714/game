"""Focused tests for the submarine post-canonical render proof harness.

These tests verify the gate and validation logic of the proof script using
synthetic fixtures only. They never modify or clone the real inbox SVG and
they never launch a browser.

Covered contracts:

1. Structure report SVG SHA mismatch rejects before browser launch.
2. Candidate/canonical SHA mismatch blocks proof.
3. Art-packet source SHA mismatch blocks proof.
4. Isolated 1x dimensions are exactly 320x200.
5. Isolated 2x dimensions are exactly 640x400.
6. Blank raster rejects.
7. Opaque full-canvas background rejects.
8. Runtime sprite label mismatch rejects.
9. Texture alias mismatch rejects.
10. Active collision state rejects capture.
11. Active impact state rejects capture.
12. Visible impact overlay rejects capture.
13. Manifest records out-of-order workflow state.
14. Production source/atlas/runtime paths remain untouched.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PROOF_SCRIPT = (
    REPO_ROOT / "scripts" / "ocean-rescue" / "capture-submarine-handoff-render-proof.py"
)


def _load_proof():
    spec = importlib.util.spec_from_file_location(
        "ocean_rescue_submarine_render_proof", PROOF_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load proof script {PROOF_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROOF = _load_proof()

ASSET_ID = "scene-submarine-01"
ALIAS = "scene.submarine"
CANONICAL_TARGET = "domains/ocean-rescue/assets/source/scene/submarine.svg"

MINIMAL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200">'
    '<g id="scene-submarine">'
    '<g id="submarine-hull"><path d="M10 10 L110 10 L110 60 L10 60 Z" fill="#168B8C"/></g>'
    '<g id="submarine-cockpit"><path d="M60 20 L90 20 L90 40 L60 40 Z" fill="#82D7E7"/></g>'
    '<g id="submarine-propulsion"><path d="M20 30 L40 20 L40 50 L20 40 Z" fill="#F47B3A"/></g>'
    '<g id="submarine-rescue-gear"><path d="M70 60 L90 60 L90 80 L70 80 Z" fill="#F4E9CC"/></g>'
    '<g id="submarine-lights"><circle cx="100" cy="50" r="4" fill="#102E46"/></g>'
    "</g></svg>"
)

BLANK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200">'
    '<g id="scene-submarine">'
    '<g id="submarine-hull"><path d="M10 10 L110 10 L110 60 L10 60 Z" fill="transparent"/></g>'
    "</g></svg>"
)

OPAQUE_BG_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200">'
    '<rect x="0" y="0" width="320" height="200" fill="#000000"/>'
    '<g id="scene-submarine">'
    '<g id="submarine-hull"><path d="M10 10 L110 10 L110 60 L10 60 Z" fill="#168B8C"/></g>'
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
    """Create a complete synthetic input set for the input gate."""
    svg = MINIMAL_SVG if svg is None else svg
    svg_path = _write(tmp_path / "inbox" / "scene-submarine-01.svg", svg)
    brief = _write(tmp_path / "briefs" / "scene-submarine-01.md", "# Asset identity\n")
    canonical = _write(tmp_path / CANONICAL_TARGET, svg)
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
        / "scene-submarine-01"
        / "structure-report.json",
        json.dumps(structure),
    )
    packet = {
        "assets": [
            {
                "alias": ALIAS,
                "source": "scene/submarine.svg",
                "sourceSha256": _sha256_bytes(svg.encode("utf-8")),
            }
        ]
    }
    packet_path = _write(tmp_path / "source" / "art-packet.json", json.dumps(packet))
    manifest_path = _write(
        tmp_path / "generated" / "atlas-manifest.json", json.dumps({"files": {}})
    )
    single_html = _write(tmp_path / "ocean-rescue" / "index.html", "<html></html>")
    return {
        "brief": str(brief),
        "svg": str(svg_path),
        "inbox_canonical_path": str(svg_path),
        "structure_report": str(structure_path),
        "canonical_source": str(canonical),
        "art_packet": str(packet_path),
        "atlas_manifest": str(manifest_path),
        "single_html": str(single_html),
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

        # Tamper the structure report so svgSha256 no longer matches the inbox.
        structure_path = pathlib.Path(fixture["structure_report"])
        structure = json.loads(structure_path.read_text(encoding="utf-8"))
        structure["svgSha256"] = "0" * 64
        structure_path.write_text(json.dumps(structure), encoding="utf-8")
        ok, code = PROOF.run_input_gate(tmp_path, args)
        assert ok is False
        assert code == "STRUCTURE_REPORT_INPUT_SHA_MISMATCH"

    def test_missing_structure_report_rejects(self, tmp_path):
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


class TestHashLineage:
    def _lineage_fixture(self, tmp_path, svg):
        svg = MINIMAL_SVG if svg is None else svg
        svg_bytes = svg.encode("utf-8")
        inbox = _write(tmp_path / "inbox" / "scene-submarine-01.svg", svg)
        canonical = _write(tmp_path / CANONICAL_TARGET, svg)
        structure = {
            "svgSha256": _sha256_bytes(svg_bytes),
        }
        structure_path = _write(
            tmp_path
            / "review"
            / "handoff-intake"
            / "scene-submarine-01"
            / "structure-report.json",
            json.dumps(structure),
        )
        packet = {
            "assets": [
                {
                    "alias": ALIAS,
                    "source": "scene/submarine.svg",
                    "sourceSha256": _sha256_bytes(svg_bytes),
                }
            ]
        }
        packet_path = _write(
            tmp_path / "source" / "art-packet.json", json.dumps(packet)
        )
        approval = {"artPacketSha256": None, "sourceSetSha256": None}
        approval_path = _write(
            tmp_path / "source" / "art-approval.json", json.dumps(approval)
        )
        manifest = {
            "sourcePacketSha256": None,
            "approvalRecordSha256": None,
            "sourceSetSha256": None,
            "files": {"scene/scene-0.json": "0" * 64, "scene/scene-0.png": "0" * 64},
        }
        manifest_path = _write(
            tmp_path / "generated" / "atlas-manifest.json", json.dumps(manifest)
        )
        scene_json = _write(tmp_path / "generated" / "scene" / "scene-0.json", "{}")
        scene_png = _write(
            tmp_path / "generated" / "scene" / "scene-0.png", b"\x89PNG\r\n\x1a\n"
        )
        render_assets = _write(
            tmp_path / "src" / "render-assets.generated.js", "window.OceanRescue = {};"
        )
        single_html = _write(tmp_path / "ocean-rescue" / "index.html", "<html></html>")
        return {
            "svg": str(inbox),
            "inbox_canonical_path": str(inbox),
            "canonical_source": str(canonical),
            "structure_report": str(structure_path),
            "art_packet": str(packet_path),
            "art_approval": str(approval_path),
            "atlas_manifest": str(manifest_path),
            "scene_atlas_json": str(scene_json),
            "scene_atlas_png": str(scene_png),
            "render_assets": str(render_assets),
            "single_html": str(single_html),
            "build_manifest": str(
                _write(
                    tmp_path / "src" / "build-manifest.json",
                    json.dumps({"scripts": []}),
                )
            ),
        }

    def test_candidate_canonical_mismatch_blocks(self, tmp_path):
        fixture = self._lineage_fixture(tmp_path, MINIMAL_SVG)
        args = type("Args", (), fixture)()
        lineage = PROOF.compute_lineage(tmp_path, args)
        assert lineage["inboxSvgSha256"] == lineage["canonicalSourceSha256"]
        checks = PROOF.lineage_checks(lineage)
        # Art packet fields are deliberately malformed in this fixture, so the
        # candidate/canonical equality itself must still be the binding gate.
        assert lineage["inboxSvgSha256"] == lineage["structureReportSvgSha256"]

        # Now make canonical differ from the inbox candidate.
        canonical_path = pathlib.Path(fixture["canonical_source"])
        canonical_path.write_text(MINIMAL_SVG + "<!-- tampered -->", encoding="utf-8")
        lineage = PROOF.compute_lineage(tmp_path, args)
        checks = PROOF.lineage_checks(lineage)
        candidate_check = next(
            c for c in checks if c["name"] == "candidateStructureCanonicalPacket"
        )
        assert candidate_check["ok"] is False

    def test_art_packet_source_sha_mismatch_blocks(self, tmp_path):
        fixture = self._lineage_fixture(tmp_path, MINIMAL_SVG)
        args = type("Args", (), fixture)()
        packet_path = pathlib.Path(fixture["art_packet"])
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        packet["assets"][0]["sourceSha256"] = "f" * 64
        packet_path.write_text(json.dumps(packet), encoding="utf-8")
        lineage = PROOF.compute_lineage(tmp_path, args)
        checks = PROOF.lineage_checks(lineage)
        candidate_check = next(
            c for c in checks if c["name"] == "candidateStructureCanonicalPacket"
        )
        assert candidate_check["ok"] is False


class TestIsolatedRender:
    def _render(self, tmp_path, svg, w, h):
        svg_path = _write(tmp_path / "fixture.svg", svg)
        png = PROOF.render_svg_to_png(svg_path, w, h)
        return PROOF.analyze_isolated_png(png, w, h)

    def test_isolated_1x_dimensions_exactly_320x200(self, tmp_path):
        analysis = self._render(tmp_path, MINIMAL_SVG, 320, 200)
        assert analysis["width"] == 320
        assert analysis["height"] == 200
        ok, reasons = PROOF.check_isolated(analysis)
        assert ok is True, reasons

    def test_isolated_2x_dimensions_exactly_640x400(self, tmp_path):
        analysis = self._render(tmp_path, MINIMAL_SVG, 640, 400)
        assert analysis["width"] == 640
        assert analysis["height"] == 400
        ok, reasons = PROOF.check_isolated(analysis)
        assert ok is True, reasons

    def test_blank_raster_rejects(self, tmp_path):
        analysis = self._render(tmp_path, BLANK_SVG, 320, 200)
        ok, reasons = PROOF.check_isolated(analysis)
        assert ok is False
        assert any("completely transparent" in r for r in reasons)

    def test_opaque_full_canvas_background_rejects(self, tmp_path):
        analysis = self._render(tmp_path, OPAQUE_BG_SVG, 320, 200)
        ok, reasons = PROOF.check_isolated(analysis)
        assert ok is False
        assert any("opaque full-canvas background" in r for r in reasons)


def _sprite(label="travel-submarine", is_sprite=True, texture_label=ALIAS, **overrides):
    sprite = {
        "label": label,
        "isSprite": is_sprite,
        "visible": True,
        "renderable": True,
        "x": 260,
        "y": 360,
        "rotation": 0,
        "scaleX": 1.1,
        "scaleY": 1.1,
        "anchor": {"x": 0.5, "y": 0.55},
        "hasTexture": True,
    }
    sprite.update(overrides)
    texture = {
        "label": texture_label,
        "exists": True,
        "frame": {
            "x": 2,
            "y": 2,
            "w": 271.5,
            "h": 160,
            "finite": True,
            "nonzero": True,
        },
        "orig": {"w": 320, "h": 200, "finite": True, "nonzero": True},
        "sourceSize": {"w": 2016, "h": 1263},
        "resolution": 2,
        "defaultAnchor": {"x": 0.5, "y": 0.55},
    }
    return sprite, texture


class TestRuntimeIdentity:
    def _run(self, sprite, texture):
        result = {
            "diag": {
                "data-ocean-rescue-ready": "true",
                "data-render-runtime": "ready",
                "data-travel-scene": "active",
                "data-travel-scene-animation": "paused",
                "data-travel-scene-legacy-visible": "false",
                "data-travel-scene-impact-active": "false",
                "data-travel-scene-impact-phase": "idle",
            },
            "sprite": sprite,
            "texture": texture,
            "terrain": {"collisionCount": 0, "collisionActive": False},
            "impactRootVisible": False,
            "overlayVisible": False,
            "legacyBridgeVisible": False,
            "frozen": True,
            "screenshot": {"width": 1280, "height": 720},
            "externalOriginRequestCount": 0,
            "externalRequests": [],
            "referenceImageRequestCount": 0,
            "referenceRequests": [],
            "pageErrorCount": 0,
            "pageErrors": [],
            "consoleErrorCount": 0,
            "consoleErrors": [],
            "unhandledRejectionCount": 0,
            "unhandledRejections": [],
            "securityPolicyViolationCount": 0,
            "cspViolations": [],
        }
        return result

    def test_runtime_sprite_label_mismatch_rejects(self):
        sprite, texture = _sprite(label="travel-submarine-WRONG")
        result = self._run(sprite, texture)
        ok, reasons = PROOF.check_sprite_identity(result)
        assert ok is False
        assert any("label != travel-submarine" in r for r in reasons)

    def test_texture_alias_mismatch_rejects(self):
        sprite, texture = _sprite(texture_label="scene.wrong")
        result = self._run(sprite, texture)
        ok, reasons = PROOF.check_sprite_identity(result)
        assert ok is False
        assert any("texture alias" in r for r in reasons)

    def test_valid_identity_passes(self):
        sprite, texture = _sprite()
        result = self._run(sprite, texture)
        ok, reasons = PROOF.check_sprite_identity(result)
        assert ok is True, reasons


class TestCaptureState:
    def _base(self):
        return {
            "diag": {
                "data-ocean-rescue-ready": "true",
                "data-render-runtime": "ready",
                "data-travel-scene": "active",
                "data-travel-scene-animation": "paused",
                "data-travel-scene-legacy-visible": "false",
                "data-travel-scene-impact-active": "false",
                "data-travel-scene-impact-phase": "idle",
            },
            "terrain": {"collisionCount": 0, "collisionActive": False},
            "impactRootVisible": False,
            "overlayVisible": False,
            "legacyBridgeVisible": False,
            "frozen": True,
            "screenshot": {"width": 1280, "height": 720},
            "externalOriginRequestCount": 0,
            "externalRequests": [],
            "referenceImageRequestCount": 0,
            "referenceRequests": [],
            "pageErrorCount": 0,
            "pageErrors": [],
            "consoleErrorCount": 0,
            "consoleErrors": [],
            "unhandledRejectionCount": 0,
            "unhandledRejections": [],
            "securityPolicyViolationCount": 0,
            "cspViolations": [],
        }

    def test_active_collision_state_rejects(self):
        result = self._base()
        result["terrain"]["collisionCount"] = 1
        result["terrain"]["collisionActive"] = True
        ok, reasons = PROOF.check_capture_state(result)
        assert ok is False
        assert any("collisionCount != 0" in r for r in reasons)

    def test_active_impact_state_rejects(self):
        result = self._base()
        result["diag"]["data-travel-scene-impact-active"] = "true"
        result["diag"]["data-travel-scene-impact-phase"] = "core"
        ok, reasons = PROOF.check_capture_state(result)
        assert ok is False
        assert any("impact-active" in r for r in reasons)

    def test_visible_impact_overlay_rejects(self):
        result = self._base()
        result["impactRootVisible"] = True
        ok, reasons = PROOF.check_capture_state(result)
        assert ok is False
        assert any("impact-root visible" in r for r in reasons)

    def test_clean_state_passes(self):
        ok, reasons = PROOF.check_capture_state(self._base())
        assert ok is True, reasons


class TestManifestWorkflowRecord:
    def test_manifest_records_out_of_order_workflow_state(self, tmp_path):
        args = type(
            "Args",
            (),
            {
                "repo_root": str(tmp_path),
                "brief": "briefs/scene-submarine-01.md",
                "svg": "inbox/scene-submarine-01.svg",
                "inbox_canonical_path": "inbox/scene-submarine-01.svg",
                "structure_report": "review/structure-report.json",
                "canonical_source": CANONICAL_TARGET,
                "art_packet": "source/art-packet.json",
                "art_approval": "source/art-approval.json",
                "atlas_manifest": "generated/atlas-manifest.json",
                "scene_atlas_json": "generated/scene/scene-0.json",
                "scene_atlas_png": "generated/scene/scene-0.png",
                "render_assets": "src/render-assets.generated.js",
                "single_html": "ocean-rescue/index.html",
                "build_manifest": "src/build-manifest.json",
            },
        )
        _write(tmp_path / "briefs" / "scene-submarine-01.md", "brief")
        _write(tmp_path / "inbox" / "scene-submarine-01.svg", MINIMAL_SVG)
        _write(
            tmp_path / "review" / "structure-report.json",
            json.dumps({"svgSha256": "0" * 64}),
        )
        _write(tmp_path / CANONICAL_TARGET, MINIMAL_SVG)
        _write(
            tmp_path / "source" / "art-packet.json",
            json.dumps(
                {
                    "assets": [
                        {
                            "alias": ALIAS,
                            "source": "scene/submarine.svg",
                            "sourceSha256": "0" * 64,
                        }
                    ]
                }
            ),
        )
        _write(tmp_path / "source" / "art-approval.json", json.dumps({}))
        _write(
            tmp_path / "generated" / "atlas-manifest.json", json.dumps({"files": {}})
        )
        _write(tmp_path / "generated" / "scene" / "scene-0.json", "{}")
        _write(tmp_path / "generated" / "scene" / "scene-0.png", b"\x89PNG\r\n\x1a\n")
        _write(
            tmp_path / "src" / "render-assets.generated.js", "window.OceanRescue = {};"
        )
        _write(tmp_path / "ocean-rescue" / "index.html", "<html></html>")
        _write(
            tmp_path / "src" / "build-manifest.json",
            json.dumps(
                {
                    "template": "index.template.html",
                    "styles": ["style.css"],
                    "vendor": {
                        "file": "vendor/pixi-8.19.0.min.js",
                        "namespace": "PIXI",
                        "kind": "vendor",
                        "sha256": "0" * 64,
                    },
                    "generated": {
                        "file": "render-assets.generated.js",
                        "sha256": "0" * 64,
                    },
                    "entry": "main.js",
                    "assets": [],
                }
            ),
        )

        lineage = PROOF.compute_lineage(tmp_path, args)
        isolated = {
            "1x": {
                "fileSha256": "0" * 64,
                "pixelSha256": "0" * 64,
                "byteSize": 1,
                "width": 320,
                "height": 200,
                "alphaPresent": True,
                "visibleAlphaBounds": {"x": 0, "y": 0, "width": 320, "height": 200},
            },
            "2x": {
                "fileSha256": "0" * 64,
                "pixelSha256": "0" * 64,
                "byteSize": 1,
                "width": 640,
                "height": 400,
                "alphaPresent": True,
                "visibleAlphaBounds": {"x": 0, "y": 0, "width": 640, "height": 400},
            },
        }
        runs = [
            {
                "rendererBackend": "webgl",
                "logicalViewport": [1280, 720],
                "deviceScaleFactor": 1,
                "sprite": {
                    "label": "travel-submarine",
                    "isSprite": True,
                    "anchor": {"x": 0.5, "y": 0.55},
                    "scaleX": 1.1,
                    "scaleY": 1.1,
                    "x": 260,
                    "y": 360,
                },
                "texture": {"label": ALIAS, "frame": {}, "orig": {}, "resolution": 2},
                "diag": {
                    "data-travel-scene": "active",
                    "data-travel-scene-animation": "paused",
                    "data-travel-scene-impact-active": "false",
                    "data-travel-scene-impact-phase": "idle",
                    "data-travel-scene-obstacle-renderer": "sprite",
                    "data-travel-scene-obstacle-boundary-mode": "dual-silhouette",
                    "data-travel-scene-placeholder-obstacle-count": "0",
                    "data-travel-scene-nonfinite-obstacle-count": "0",
                    "data-travel-scene-impact-mode": "contact-burst-v1",
                },
                "terrain": {"collisionCount": 0, "collisionActive": False},
                "impactRootVisible": False,
                "overlayVisible": False,
                "externalOriginRequestCount": 0,
                "referenceImageRequestCount": 0,
                "pageErrorCount": 0,
                "consoleErrorCount": 0,
                "unhandledRejectionCount": 0,
                "securityPolicyViolationCount": 0,
                "screenshot": {
                    "fileSha256": "0" * 64,
                    "pixelSha256": "0" * 64,
                    "byteSize": 1,
                    "width": 1280,
                    "height": 720,
                },
            }
        ]
        manifest = PROOF.build_manifest(
            args, tmp_path, lineage, True, isolated, runs, "RENDER_PROOF_READY", []
        )
        assert manifest["workflowOrderViolation"] is True
        assert (
            manifest["preexistingCanonicalizationCommit"]
            == PROOF.PREEXISTING_CANONICALIZATION_COMMIT
        )
        assert manifest["candidateWasCanonicalBeforeStructureProof"] is True
        assert manifest["humanVisualDecisionAfterThisProofRequired"] is True
        assert manifest["verdict"] == "RENDER_PROOF_READY"


class TestForbiddenProductionMutation:
    def test_production_paths_untouched_by_harness(self):
        # The proof harness must never write into these paths.
        forbidden = PROOF.FORBIDDEN_WRITE_PREFIXES
        assert "domains/ocean-rescue/assets/handoff/inbox/" in forbidden
        assert "domains/ocean-rescue/assets/source/" in forbidden
        assert "domains/ocean-rescue/assets/generated/" in forbidden
        assert "domains/ocean-rescue/src/" in forbidden
        assert "ocean-rescue/index.html" in forbidden

        source = PROOF_SCRIPT.read_text(encoding="utf-8")

        # Every write call in the harness must target the output dir (evidence root).
        write_calls = re.findall(
            r"(?:\.write_bytes|\.write_text|open\([^)]+['\"]w[^)]*\))", source
        )
        assert write_calls, "expected write calls in the harness"

        # No direct writes to production paths may exist.
        for prefix in (
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
