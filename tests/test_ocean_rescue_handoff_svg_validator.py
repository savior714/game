"""Focused tests for the Ocean Rescue handoff SVG intake validator (Gate A/B)."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = REPO_ROOT / "scripts" / "ocean-rescue" / "validate-handoff-svg.py"

ASSET_ID = "scene-submarine-01"
ALIAS = "scene.submarine"
CANONICAL_TARGET = "domains/ocean-rescue/assets/source/scene/submarine.svg"

BRIEF_TEMPLATE = """# Asset identity

- Asset ID: `{asset_id}`
- Runtime alias: `{alias}`
- Target canonical path: `{target}`

# Required structure

- Root viewBox: `{viewbox}`
- Required root group: `scene-submarine`
- `submarine-hull`
- `submarine-cockpit`
- `submarine-propulsion`
- `submarine-rescue-gear`
- `submarine-lights`
"""

VALID_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200">
  <g id="scene-submarine">
    <g id="submarine-hull"><path d="M10 10 L110 10 L110 60 L10 60 Z" fill="#168B8C"/></g>
    <g id="submarine-cockpit"><path d="M60 20 L90 20 L90 40 L60 40 Z" fill="#82D7E7"/></g>
    <g id="submarine-propulsion"><path d="M20 30 L40 20 L40 50 L20 40 Z" fill="#F47B3A"/></g>
    <g id="submarine-rescue-gear"><path d="M70 60 L90 60 L90 80 L70 80 Z" fill="#F4E9CC"/></g>
    <g id="submarine-lights"><circle cx="100" cy="50" r="4" fill="#102E46"/></g>
  </g>
</svg>
"""


def _write_brief(tmp_path: Path) -> Path:
    briefs = tmp_path / "briefs"
    briefs.mkdir(parents=True, exist_ok=True)
    brief = briefs / f"{ASSET_ID}.md"
    brief.write_text(
        BRIEF_TEMPLATE.format(
            asset_id=ASSET_ID,
            alias=ALIAS,
            target=CANONICAL_TARGET,
            viewbox="0 0 320 200",
        ),
        encoding="utf-8",
    )
    return brief


def _write_svg(tmp_path: Path, content: str, name: str = f"{ASSET_ID}.svg") -> Path:
    inbox = tmp_path / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    svg = inbox / name
    svg.write_text(content, encoding="utf-8")
    return svg


def _run(brief: Path, svg: Path, tmp_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--brief",
            str(brief),
            "--svg",
            str(svg),
            "--report-json",
            str(tmp_path / "structure-report.json"),
            "--report-md",
            str(tmp_path / "structure-report.md"),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _load_report(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "structure-report.json").read_text(encoding="utf-8"))


class TestHandoffSvgValidator:
    def test_minimal_valid_svg_accepts(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        svg = _write_svg(tmp_path, VALID_SVG)
        proc = _run(brief, svg, tmp_path)
        assert proc.returncode == 0, proc.stderr
        report = _load_report(tmp_path)
        assert report["verdict"] == "STRUCTURE_PASS"

    def test_brief_and_svg_hashes_recorded(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        svg = _write_svg(tmp_path, VALID_SVG)
        _run(brief, svg, tmp_path)
        report = _load_report(tmp_path)
        assert report["briefSha256"] == hashlib.sha256(brief.read_bytes()).hexdigest()
        assert report["svgSha256"] == hashlib.sha256(svg.read_bytes()).hexdigest()

    def test_missing_required_group_rejects(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        content = VALID_SVG.replace('<g id="submarine-lights">', "<g>")
        svg = _write_svg(tmp_path, content)
        proc = _run(brief, svg, tmp_path)
        assert proc.returncode != 0
        report = _load_report(tmp_path)
        assert report["verdict"] == "STRUCTURE_REJECTED"
        assert "submarine-lights" in report["missingRequiredGroups"]

    def test_empty_required_group_rejects(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        content = VALID_SVG.replace(
            '<g id="submarine-lights">'
            '<circle cx="100" cy="50" r="4" fill="#102E46"/></g>',
            '<g id="submarine-lights"></g>',
        )
        svg = _write_svg(tmp_path, content)
        proc = _run(brief, svg, tmp_path)
        assert proc.returncode != 0
        report = _load_report(tmp_path)
        assert "submarine-lights" in report["emptyRequiredGroups"]

    def test_wrong_viewbox_rejects(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        content = VALID_SVG.replace('viewBox="0 0 320 200"', 'viewBox="0 0 100 100"')
        svg = _write_svg(tmp_path, content)
        proc = _run(brief, svg, tmp_path)
        assert proc.returncode != 0
        report = _load_report(tmp_path)
        assert report["verdict"] == "STRUCTURE_REJECTED"

    def test_duplicate_id_rejects(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        content = VALID_SVG.replace(
            '<circle cx="100" cy="50" r="4" fill="#102E46"/>',
            '<circle cx="100" cy="50" r="4" fill="#102E46" id="submarine-lights"/>',
        )
        svg = _write_svg(tmp_path, content)
        proc = _run(brief, svg, tmp_path)
        assert proc.returncode != 0
        report = _load_report(tmp_path)
        assert "submarine-lights" in report["duplicateIds"]

    def test_script_element_rejects(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        content = VALID_SVG.replace("</svg>", "<script>alert(1)</script></svg>")
        svg = _write_svg(tmp_path, content)
        proc = _run(brief, svg, tmp_path)
        assert proc.returncode != 0
        report = _load_report(tmp_path)
        assert "script" in "".join(report["forbiddenElements"])

    def test_event_handler_attribute_rejects(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        content = VALID_SVG.replace(
            '<path d="M10 10',
            '<path onload="alert(1)" d="M10 10',
        )
        svg = _write_svg(tmp_path, content)
        proc = _run(brief, svg, tmp_path)
        assert proc.returncode != 0
        report = _load_report(tmp_path)
        assert "onload" in report["forbiddenAttributes"]

    def test_external_href_rejects(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        content = VALID_SVG.replace(
            "</svg>", '<use href="http://evil.example.com/x.svg"/></svg>'
        )
        svg = _write_svg(tmp_path, content)
        proc = _run(brief, svg, tmp_path)
        assert proc.returncode != 0
        report = _load_report(tmp_path)
        assert any("http://evil" in item for item in report["externalReferences"])

    def test_embedded_raster_rejects(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        content = VALID_SVG.replace(
            "</svg>",
            '<image href="data:image/png;base64,iVBORw0KGgo="/></svg>',
        )
        svg = _write_svg(tmp_path, content)
        proc = _run(brief, svg, tmp_path)
        assert proc.returncode != 0
        report = _load_report(tmp_path)
        assert any("data:image" in item for item in report["externalReferences"])

    def test_unresolved_local_reference_rejects(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        content = VALID_SVG.replace("</svg>", '<use href="#does-not-exist"/></svg>')
        svg = _write_svg(tmp_path, content)
        proc = _run(brief, svg, tmp_path)
        assert proc.returncode != 0
        report = _load_report(tmp_path)
        assert any("does-not-exist" in item for item in report["unresolvedReferences"])

    def test_full_canvas_opaque_rect_rejects(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        content = VALID_SVG.replace(
            '<g id="scene-submarine">',
            '<g id="scene-submarine">'
            '<rect x="0" y="0" width="320" height="200" fill="#000000"/>',
        )
        svg = _write_svg(tmp_path, content)
        proc = _run(brief, svg, tmp_path)
        assert proc.returncode != 0
        report = _load_report(tmp_path)
        assert report["backgroundTransparencyPass"] is False

    def test_candidate_input_never_modified(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        svg = _write_svg(tmp_path, VALID_SVG)
        before = svg.read_bytes()
        _run(brief, svg, tmp_path)
        assert svg.read_bytes() == before

    def test_json_and_markdown_verdicts_agree(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        svg = _write_svg(tmp_path, VALID_SVG)
        proc = _run(brief, svg, tmp_path)
        report = _load_report(tmp_path)
        markdown = (tmp_path / "structure-report.md").read_text(encoding="utf-8")
        assert report["verdict"] == "STRUCTURE_PASS"
        assert "STRUCTURE_PASS" in markdown
        assert proc.returncode == 0

    def test_report_is_deterministic(self, tmp_path: Path):
        brief = _write_brief(tmp_path)
        svg = _write_svg(tmp_path, VALID_SVG)
        _run(brief, svg, tmp_path)
        first = (tmp_path / "structure-report.json").read_text(encoding="utf-8")
        _run(brief, svg, tmp_path)
        second = (tmp_path / "structure-report.json").read_text(encoding="utf-8")
        assert first == second


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
