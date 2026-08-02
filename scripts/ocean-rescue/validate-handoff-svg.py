#!/usr/bin/env python3
"""Deterministic Gate A/B validation for a manual Ocean Rescue SVG handoff asset.

Reads the active asset brief and the inbox SVG candidate for the handoff,
validates intake identity and SVG structure and security, and writes JSON +
Markdown evidence reports.

The intake contract (asset ID, alias, canonical target, viewBox, required groups)
and the optional facial base contract are read from the per-asset brief.

The candidate SVG is only ever read, never written.

Exit codes:
    0  STRUCTURE_PASS
    1  STRUCTURE_REJECTED
    2  invalid invocation
    3  unexpected internal error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import overload

import xml.etree.ElementTree as ET

TASK_ID = "AIDENGAME-OCEAN-RESCUE-SUBMARINE-HANDOFF-SVG-INTAKE-STRUCTURE-GATE-02"
REPORT_SCHEMA_VERSION = 1

SVG_NS = "http://www.w3.org/2000/svg"

REQUIRED_BRIEF_FIELDS = (
    "assetId",
    "alias",
    "canonicalTarget",
    "viewBox",
    "rootGroup",
)

FACE_FEATURE_FIELDS = (
    ("eyes", "Fixed eyes"),
    ("mouth", "Fixed mouth"),
    ("brows", "Fixed brows"),
)

FACE_FEATURE_ID_PATTERNS = {
    "eyes": ("eye", "pupil", "iris", "eyelid"),
    "mouth": ("mouth", "lip", "smile", "frown", "grin"),
    "brows": ("brow",),
}

FORBIDDEN_ELEMENTS = {
    "script",
    "foreignobject",
    "iframe",
    "object",
    "embed",
    "audio",
    "video",
    "canvas",
}

FORBIDDEN_ANIMATION_ELEMENTS = {
    "animate",
    "animatetransform",
    "animatemotion",
    "set",
    "mpath",
}

FORBIDDEN_STYLE_TOKENS = re.compile(
    r"@import|javascript:|vbscript:|expression\(|behavior:|url\(|animation",
    re.IGNORECASE,
)

URI_FORBIDDEN_RE = re.compile(
    r"javascript:|vbscript:|data:\s*(?:image|text|application)/|base64|"
    r"https?://|ftp://|file://|^//",
    re.IGNORECASE,
)

CANVAS_RECT_PATH_RE = re.compile(
    r"M\s*0\s*,?\s*0\s*(?:L|H)\s*320\s*,?\s*0\s*(?:L|V)\s*320\s*,?\s*200\s*"
    r"(?:L|H)\s*0\s*,?\s*200\s*Z",
    re.IGNORECASE,
)

NUMERIC_ATTRS = {
    "viewbox",
    "width",
    "height",
    "x",
    "y",
    "x1",
    "x2",
    "y1",
    "y2",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "stroke-width",
    "opacity",
    "fill-opacity",
    "stroke-opacity",
    "transform",
    "d",
    "points",
}

SHAPE_TAGS = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}

NON_FINITE_WORDS = {"nan", "inf", "infinity"}

LETTER_WORD_RE = re.compile(r"[A-Za-z]+")
NUMERIC_TOKEN_RE = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")
PATH_TOKEN_RE = re.compile(
    r"[MmLlHhVvCcSsQqTtAaZz]|[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
)
URL_FULL_RE = re.compile(r"url\(\s*([^)]*?)\s*\)")
DOCTYPE_RE = re.compile(r"<!\s*(?:DOCTYPE|ENTITY)", re.IGNORECASE)

COMMAND_CHARS = "MmLlHhVvCcSsQqTtAaZz"


def _local_name(name: str) -> str:
    return name.split("}")[-1]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _dedup_ordered(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _section(text: str, title: str) -> str:
    match = re.search(rf"(?im)^#\s*{re.escape(title)}\s*$", text)
    if not match:
        return ""
    rest = text[match.end() :]
    end = re.search(r"(?m)^#\s", rest)
    return rest if end is None else rest[: end.start()]


def _field(text: str, label: str) -> str | None:
    match = re.search(rf"(?im)^\s*-\s*{re.escape(label)}\s*:\s*`([^`]+)`", text)
    return match.group(1) if match else None


def _semantic_groups(section: str) -> list[str]:
    return re.findall(r"(?im)^\s*-\s*`([a-z0-9][a-z0-9-]*)`(?:\s|$)", section)


def _parse_brief(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    structure = _section(text, "Required structure")
    face = _section(text, "Facial base contract")
    return {
        "taskId": _field(text, "Task ID"),
        "assetId": _field(text, "Asset ID"),
        "alias": _field(text, "Runtime alias"),
        "canonicalTarget": _field(text, "Target canonical path"),
        "viewBox": _field(structure, "Root viewBox"),
        "rootGroup": _field(structure, "Required root group"),
        "semanticGroups": _semantic_groups(structure),
        "face": {label: _field(face, label) for _, label in FACE_FEATURE_FIELDS},
    }


def _contract_from_brief(brief: dict) -> dict:
    missing = [name for name in REQUIRED_BRIEF_FIELDS if not brief.get(name)]
    if missing:
        raise ValueError(f"Brief is missing required fields: {', '.join(missing)}")
    groups = [brief["rootGroup"]]
    for group in brief["semanticGroups"]:
        if group not in groups:
            groups.append(group)
    return {
        "assetId": brief["assetId"],
        "alias": brief["alias"],
        "canonicalTarget": brief["canonicalTarget"],
        "viewBox": brief["viewBox"],
        "requiredGroups": groups,
    }


def _enforced_face_features(brief: dict) -> list[str]:
    face = brief.get("face") or {}
    return [
        name
        for name, label in FACE_FEATURE_FIELDS
        if (face.get(label) or "").strip().lower() == "none"
    ]


def _parse_viewbox(value: str | None) -> list[float] | None:
    if value is None or "%" in value:
        return None
    parts = value.split()
    if len(parts) != 4:
        return None
    numbers = []
    for part in parts:
        try:
            number = float(part)
        except ValueError:
            return None
        if not math.isfinite(number):
            return None
        numbers.append(number)
    if numbers[2] < 0 or numbers[3] < 0:
        return None
    return numbers


def _new_report(
    repo_root: Path,
    brief_path: Path,
    svg_path: Path,
    brief: dict,
    contract: dict,
) -> dict:
    return {
        "schemaVersion": REPORT_SCHEMA_VERSION,
        "taskId": brief.get("taskId") or TASK_ID,
        "assetId": contract["assetId"],
        "alias": contract["alias"],
        "briefPath": _repo_relative(brief_path, repo_root),
        "briefSha256": _sha256(brief_path.read_bytes()),
        "svgPath": _repo_relative(svg_path, repo_root),
        "svgSha256": _sha256(svg_path.read_bytes()),
        "canonicalTargetPath": contract["canonicalTarget"],
        "viewBoxExpected": contract["viewBox"],
        "viewBoxActual": "",
        "requiredGroupsExpected": list(contract["requiredGroups"]),
        "requiredGroupsFound": [],
        "missingRequiredGroups": [],
        "emptyRequiredGroups": [],
        "duplicateIds": [],
        "unresolvedReferences": [],
        "externalReferences": [],
        "forbiddenElements": [],
        "forbiddenAttributes": [],
        "nonFiniteFindings": [],
        "backgroundTransparencyPass": True,
        "warnings": [],
        "verdict": "STRUCTURE_PASS",
        "rejectionReasons": [],
    }


def _check_unique_brief(
    brief_path: Path, asset_id: str, alias: str, rejection: list[str]
) -> None:
    matches = 0
    for other in sorted(brief_path.parent.glob("*.md")):
        if not other.is_file():
            continue
        other_text = other.read_text(encoding="utf-8")
        other_id = _field(other_text, "Asset ID")
        other_alias = _field(other_text, "Runtime alias")
        if other_id == asset_id:
            matches += 1
        if other_alias == alias and other != brief_path:
            rejection.append(f"Another active brief shares runtime alias: {other.name}")
    if matches != 1:
        rejection.append(
            f"Candidate maps to {matches} active brief(s) (expected exactly 1)"
        )


def _gate_a(
    brief_path: Path,
    svg_path: Path,
    brief: dict,
    contract: dict,
    rejection: list[str],
) -> None:
    asset_id = contract["assetId"]
    alias = contract["alias"]
    target = contract["canonicalTarget"]
    viewbox = contract["viewBox"]
    required = contract["requiredGroups"]

    if brief["assetId"] != asset_id:
        rejection.append(f"Brief Asset ID mismatch: {brief['assetId']} != {asset_id}")
    if brief["alias"] != alias:
        rejection.append(f"Brief runtime alias mismatch: {brief['alias']} != {alias}")
    if brief["canonicalTarget"] != target:
        rejection.append(
            f"Brief canonical target mismatch: {brief['canonicalTarget']} != {target}"
        )
    if _parse_viewbox(brief["viewBox"]) != _parse_viewbox(viewbox):
        rejection.append(f"Brief viewBox mismatch: {brief['viewBox']} != {viewbox}")

    brief_groups = []
    if brief["rootGroup"]:
        brief_groups.append(brief["rootGroup"])
    for group in brief["semanticGroups"]:
        if group not in brief_groups:
            brief_groups.append(group)
    if set(brief_groups) != set(required):
        rejection.append(
            f"Brief required groups mismatch: {sorted(brief_groups)} != {sorted(required)}"
        )

    if svg_path.name != f"{asset_id}.svg":
        rejection.append(f"Input basename mismatch: {svg_path.name} != {asset_id}.svg")
    if brief_path.name != f"{asset_id}.md":
        rejection.append(f"Brief basename mismatch: {brief_path.name} != {asset_id}.md")

    _check_unique_brief(brief_path, asset_id, alias, rejection)


def _check_required_groups(
    root: ET.Element,
    groups_by_id: dict,
    report: dict,
    rejection: list[str],
) -> list[str]:
    required = report["requiredGroupsExpected"]
    found = []
    missing = []
    for gid in required:
        occurrences = groups_by_id.get(gid, [])
        if not occurrences:
            if gid in report["duplicateIds"] or any(
                e.get("id") == gid for e in root.iter() if e.get("id")
            ):
                rejection.append(f"Required ID {gid} exists but is not a <g> element")
            missing.append(gid)
            rejection.append(f"Missing required group: {gid}")
        elif len(occurrences) > 1:
            missing.append(gid)
            rejection.append(f"Required group <g id={gid}> occurs more than once")
        else:
            found.append(gid)
    report["requiredGroupsFound"] = found
    report["missingRequiredGroups"] = missing

    root_groups = groups_by_id.get(required[0], [])
    if len(root_groups) == 1:
        root_group = root_groups[0]
        if not any(child is root_group for child in list(root)):
            rejection.append("scene-submarine must be a direct child of the <svg> root")
        descendants = set(root_group.iter())
        for gid in required[1:]:
            for occurrence in groups_by_id.get(gid, []):
                if occurrence not in descendants:
                    rejection.append(
                        f"Semantic group <g id={gid}> is not a descendant of scene-submarine"
                    )
    return found


def _check_empty_groups(
    found: list[str],
    groups_by_id: dict,
    report: dict,
    rejection: list[str],
) -> None:
    empty = []
    for gid in found:
        group = groups_by_id[gid][0]
        has_shape = any(
            _local_name(elem.tag).lower() in SHAPE_TAGS for elem in group.iter()
        )
        if not has_shape:
            empty.append(gid)
            rejection.append(f"Empty required group: {gid}")
    report["emptyRequiredGroups"] = empty


def _check_href(
    element_local: str,
    value: str,
    all_ids: set,
    unresolved: list[str],
    external: list[str],
) -> None:
    if value.startswith("#"):
        ref = value[1:]
        if not ref:
            external.append(f"{element_local}: href={value!r}")
        elif ref not in all_ids:
            unresolved.append(f"{element_local}: href={value!r}")
    else:
        external.append(f"{element_local}: href={value!r}")


def _check_references(
    elements: list[ET.Element],
    ids: dict,
    report: dict,
    rejection: list[str],
) -> None:
    all_ids = set(ids)
    unresolved: list[str] = []
    external: list[str] = []
    for elem in elements:
        element_local = _local_name(elem.tag)
        for attr, value in elem.attrib.items():
            attr_local = _local_name(attr)
            if attr_local == "href":
                _check_href(element_local, value, all_ids, unresolved, external)
            for match in URL_FULL_RE.finditer(value):
                inner = match.group(1).strip()
                if inner.startswith("#"):
                    ref = inner[1:]
                    if ref and ref not in all_ids:
                        unresolved.append(f"{element_local}: url(#{ref})")
                elif inner:
                    external.append(f"{element_local}: url({inner})")
            if attr_local != "href" and URI_FORBIDDEN_RE.search(value):
                external.append(f"{element_local}: {_local_name(attr)}={value!r}")
    report["unresolvedReferences"] = _dedup_ordered(unresolved)
    report["externalReferences"] = _dedup_ordered(external)
    for item in report["unresolvedReferences"]:
        rejection.append(f"Unresolved local reference: {item}")
    for item in report["externalReferences"]:
        rejection.append(f"External reference: {item}")


def _check_security(
    elements: list[ET.Element],
    report: dict,
    rejection: list[str],
) -> None:
    forbidden_elements: list[str] = []
    forbidden_attributes: list[str] = []
    for elem in elements:
        local = _local_name(elem.tag).lower()
        if local in FORBIDDEN_ELEMENTS:
            forbidden_elements.append(f"<{local}>")
            rejection.append(f"Forbidden element <{local}>")
        if local in FORBIDDEN_ANIMATION_ELEMENTS:
            forbidden_elements.append(f"<{local}>")
            rejection.append(f"Forbidden animation element <{local}>")
        if local == "style":
            forbidden_elements.append("<style>")
            rejection.append(
                "<style> present; deterministic CSS safety cannot be guaranteed"
            )
        for attr, value in elem.attrib.items():
            attr_local = _local_name(attr).lower()
            if attr_local.startswith("on"):
                forbidden_attributes.append(attr_local)
                rejection.append(f"Forbidden event-handler attribute: {attr_local}")
            if attr_local == "style" and FORBIDDEN_STYLE_TOKENS.search(value):
                forbidden_attributes.append("style")
                rejection.append(f"Forbidden inline style on <{local}>")
    report["forbiddenElements"] = _dedup_ordered(forbidden_elements)
    report["forbiddenAttributes"] = _dedup_ordered(forbidden_attributes)


def _has_non_finite(value: str) -> bool:
    for word in LETTER_WORD_RE.findall(value):
        if word.lower() in NON_FINITE_WORDS:
            return True
    for match in NUMERIC_TOKEN_RE.finditer(value):
        try:
            number = float(match.group(0))
        except ValueError:
            continue
        if not math.isfinite(number):
            return True
    return False


def _check_finite(
    elements: list[ET.Element],
    report: dict,
    rejection: list[str],
) -> None:
    findings = []
    for elem in elements:
        element_local = _local_name(elem.tag)
        for attr, value in elem.attrib.items():
            if _local_name(attr).lower() not in NUMERIC_ATTRS:
                continue
            if _has_non_finite(value):
                findings.append(f"<{element_local}> {attr}={value!r}")
    report["nonFiniteFindings"] = findings
    for finding in findings:
        rejection.append(f"Non-finite numeric value: {finding}")


@overload
def _float(value: str | None, default: float) -> float: ...


@overload
def _float(value: str | None, default: None) -> float | None: ...


def _float(value: str | None, default: float | None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _points_bbox(points: list[tuple[float, float]]) -> tuple | None:
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs), min(ys), max(xs), max(ys))


def _polygon_points(value: str) -> list[tuple[float, float]]:
    numbers = NUMERIC_TOKEN_RE.findall(value)
    points = []
    for i in range(0, len(numbers) - 1, 2):
        points.append((float(numbers[i]), float(numbers[i + 1])))
    return points


def _is_number_token(token: str) -> bool:
    return token[0] not in COMMAND_CHARS


def _path_points(d: str) -> list[tuple[float, float]] | None:
    tokens = PATH_TOKEN_RE.findall(d)
    if not tokens:
        return None
    points = []
    i = 0
    cmd = "M"
    cx = 0.0
    cy = 0.0
    while i < len(tokens):
        token = tokens[i]
        if not _is_number_token(token):
            cmd = token
            i += 1
            continue
        upper = cmd.upper()
        rel = cmd.islower()
        if upper == "Z":
            break
        if upper in ("M", "L", "T"):
            count = 2
        elif upper in ("H", "V"):
            count = 1
        elif upper in ("S", "Q"):
            count = 4
        elif upper == "C":
            count = 6
        elif upper == "A":
            count = 7
        else:
            return None
        if i + count > len(tokens):
            return None
        try:
            values = [float(token) for token in tokens[i : i + count]]
        except ValueError:
            return None
        i += count
        if upper in ("M", "L", "T"):
            x = values[0] + (cx if rel else 0.0)
            y = values[1] + (cy if rel else 0.0)
            cx, cy = x, y
            points.append((x, y))
            if upper == "M":
                cmd = "l" if rel else "L"
        elif upper == "H":
            x = values[0] + (cx if rel else 0.0)
            cx = x
            points.append((x, cy))
        elif upper == "V":
            y = values[0] + (cy if rel else 0.0)
            cy = y
            points.append((cx, y))
        elif upper in ("C", "S", "Q", "A"):
            x = values[-2] + (cx if rel else 0.0)
            y = values[-1] + (cy if rel else 0.0)
            cx, cy = x, y
            points.append((x, y))
    return points


def _shape_bbox(elem: ET.Element, local: str) -> tuple | None:
    if local == "rect":
        x = _float(elem.get("x"), 0.0)
        y = _float(elem.get("y"), 0.0)
        width = _float(elem.get("width"), None)
        height = _float(elem.get("height"), None)
        if width is None or height is None or width < 0 or height < 0:
            return None
        return (x, y, x + width, y + height)
    if local in ("polygon", "polyline"):
        return _points_bbox(_polygon_points(elem.get("points", "")))
    if local == "circle":
        cx = _float(elem.get("cx"), 0.0)
        cy = _float(elem.get("cy"), 0.0)
        r = _float(elem.get("r"), 0.0)
        return (cx - r, cy - r, cx + r, cy + r)
    if local == "ellipse":
        cx = _float(elem.get("cx"), 0.0)
        cy = _float(elem.get("cy"), 0.0)
        rx = _float(elem.get("rx"), 0.0)
        ry = _float(elem.get("ry"), 0.0)
        return (cx - rx, cy - ry, cx + rx, cy + ry)
    if local == "path":
        points = _path_points(elem.get("d", ""))
        return _points_bbox(points) if points else None
    return None


def _coverage_fraction(bbox: tuple, vb_w: float, vb_h: float) -> float | None:
    if bbox is None:
        return None
    x0, y0, x1, y1 = bbox
    cx0 = max(0.0, x0)
    cy0 = max(0.0, y0)
    cx1 = min(vb_w, x1)
    cy1 = min(vb_h, y1)
    if cx1 <= cx0 or cy1 <= cy0:
        return 0.0
    return ((cx1 - cx0) * (cy1 - cy0)) / (vb_w * vb_h)


def _effective_opacity(elem: ET.Element) -> float:
    values = []
    for attr in ("opacity", "fill-opacity"):
        value = elem.get(attr)
        if value is not None:
            try:
                values.append(float(value))
            except ValueError:
                pass
    if not values:
        return 1.0
    return min(values)


def _fill_opaque(elem: ET.Element) -> bool:
    fill = elem.get("fill")
    if fill is None:
        return True
    normalized = fill.strip().lower()
    if normalized == "none" or normalized == "transparent":
        return False
    return _effective_opacity(elem) >= 0.9


def _is_transparent(elem: ET.Element) -> bool:
    fill = elem.get("fill")
    if fill is not None:
        normalized = fill.strip().lower()
        if normalized == "none" or normalized == "transparent":
            return True
    return _effective_opacity(elem) < 0.05


def _rect_covers_canvas(elem: ET.Element, vb_w: float, vb_h: float) -> bool:
    x = _float(elem.get("x"), 0.0)
    y = _float(elem.get("y"), 0.0)
    width = _float(elem.get("width"), None)
    height = _float(elem.get("height"), None)
    if width is None or height is None:
        return False
    return (
        x <= 1.0 and y <= 1.0 and x + width >= vb_w - 1.0 and y + height >= vb_h - 1.0
    )


def _is_full_canvas(
    elem: ET.Element, local: str, bbox: tuple, vb_w: float, vb_h: float
) -> bool:
    if local == "rect":
        return _rect_covers_canvas(elem, vb_w, vb_h)
    if local in ("polygon", "polyline"):
        return (_coverage_fraction(bbox, vb_w, vb_h) or 0.0) >= 0.95
    if local == "path":
        return bool(CANVAS_RECT_PATH_RE.search(elem.get("d", "")))
    return False


def _check_background(
    elements: list[ET.Element],
    report: dict,
    rejection: list[str],
) -> None:
    viewbox = _parse_viewbox(report["viewBoxExpected"])
    if viewbox is None:
        return
    vb_w, vb_h = viewbox[2], viewbox[3]
    passes = True
    for elem in elements:
        local = _local_name(elem.tag).lower()
        if local not in SHAPE_TAGS:
            continue
        bbox = _shape_bbox(elem, local)
        if bbox is None:
            continue
        coverage = _coverage_fraction(bbox, vb_w, vb_h)
        if coverage is None:
            continue
        opaque = _fill_opaque(elem)
        transparent = _is_transparent(elem)
        pointer_events = (elem.get("pointer-events") or "").strip().lower()
        eid = elem.get("id")
        if opaque and _is_full_canvas(elem, local, bbox, vb_w, vb_h):
            passes = False
            rejection.append(
                f"Opaque full-canvas background: <{local} id={eid or '-'}>"
            )
        elif transparent and coverage >= 0.8:
            if pointer_events == "none":
                report["warnings"].append(
                    f"Transparent full-canvas helper with pointer-events='none': "
                    f"<{local} id={eid or '-'}>"
                )
            else:
                passes = False
                rejection.append(f"Invisible tracking layer: <{local} id={eid or '-'}>")
        elif opaque and coverage >= 0.8 and local == "path":
            report["warnings"].append(
                f"Opaque shape covers {coverage:.0%} of canvas "
                f"(uncertain background): <path id={eid or '-'}>"
            )
    report["backgroundTransparencyPass"] = passes


def _check_face_base(
    elements: list[ET.Element],
    report: dict,
    rejection: list[str],
    enforced: list[str],
) -> None:
    if not enforced:
        return
    fixed_ids: list[str] = []
    for elem in elements:
        eid = elem.get("id")
        if not eid:
            continue
        low = eid.lower()
        for feature in enforced:
            if any(
                token in low
                for token in FACE_FEATURE_ID_PATTERNS.get(feature, ())
            ):
                fixed_ids.append(f"{eid} (fixed {feature})")
                break
    fixed_ids = _dedup_ordered(fixed_ids)
    report["faceBaseContract"] = {
        "enforced": list(enforced),
        "fixedFeatureIds": fixed_ids,
        "geometryLevelAssertion": False,
    }
    for item in fixed_ids:
        rejection.append(f"Fixed face feature present in face base: {item}")
    if not fixed_ids:
        report["warnings"].append(
            "Face base verified by element ID structure only; "
            "geometry-level eye/mouth presence is not automatically asserted."
        )


def _gate_b(
    svg_path: Path,
    report: dict,
    rejection: list[str],
    enforced_face: list[str],
) -> None:
    raw = svg_path.read_bytes()
    try:
        raw_text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raw_text = ""
        rejection.append("SVG is not valid UTF-8")

    if DOCTYPE_RE.search(raw_text):
        rejection.append("DOCTYPE or entity declaration present")

    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        rejection.append(f"Malformed XML: {exc}")
        return

    root_tag = root.tag
    root_local = _local_name(root_tag)
    if root_local.lower() != "svg":
        rejection.append(f"Root element is not <svg>: <{root_local}>")
    if not root_tag.startswith("{"):
        rejection.append("Root <svg> has no XML namespace")
    else:
        namespace = root_tag[1:].split("}")[0]
        if namespace != SVG_NS:
            rejection.append(f"Root <svg> namespace mismatch: {namespace}")

    viewbox = root.get("viewBox")
    if viewbox is None:
        rejection.append("Missing viewBox")
    else:
        report["viewBoxActual"] = " ".join(viewbox.split())
        parsed = _parse_viewbox(viewbox)
        if parsed is None:
            rejection.append(f"Invalid viewBox: {viewbox!r}")
        elif parsed != _parse_viewbox(report["viewBoxExpected"]):
            rejection.append(
                f"viewBox mismatch: expected {report['viewBoxExpected']}, got {viewbox!r}"
            )

    elements = list(root.iter())
    ids: dict[str, list[ET.Element]] = {}
    groups_by_id: dict[str, list[ET.Element]] = {}
    for elem in elements:
        eid = elem.get("id")
        if eid is None:
            continue
        ids.setdefault(eid, []).append(elem)
        if _local_name(elem.tag).lower() == "g":
            groups_by_id.setdefault(eid, []).append(elem)

    duplicate_ids = sorted(
        eid for eid, occurrences in ids.items() if len(occurrences) > 1
    )
    report["duplicateIds"] = duplicate_ids
    for duplicate in duplicate_ids:
        rejection.append(f"Duplicate ID: {duplicate}")

    found = _check_required_groups(root, groups_by_id, report, rejection)
    _check_empty_groups(found, groups_by_id, report, rejection)
    _check_references(elements, ids, report, rejection)
    _check_security(elements, report, rejection)
    _check_finite(elements, report, rejection)
    _check_background(elements, report, rejection)
    _check_face_base(elements, report, rejection, enforced_face)


def _write_json(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def _join_or_none(items: list[str]) -> str:
    return ", ".join(items) if items else "(none)"


def _write_markdown(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    verdict = report["verdict"]
    if verdict == "STRUCTURE_PASS":
        next_action = "Proceed to render proof. Do not canonicalize yet."
    else:
        next_action = (
            "Return the rejection reasons to the frontier model. "
            "Do not modify or canonicalize the candidate locally."
        )
    face_lines: list[str] = []
    if "faceBaseContract" in report:
        face_lines = [
            "",
            "## Face base contract",
            f"- Enforced absent features: "
            f"{_join_or_none(report['faceBaseContract'].get('enforced', []))}",
            f"- Fixed feature IDs found: "
            f"{_join_or_none(report['faceBaseContract'].get('fixedFeatureIds', []))}",
            f"- Geometry-level assertion: "
            f"{report['faceBaseContract'].get('geometryLevelAssertion', False)}",
        ]
    lines = [
        "# Ocean Rescue — Handoff SVG Structure Report",
        "",
        f"- Task ID: {report['taskId']}",
        f"- Verdict: {verdict}",
        "",
        "## Asset identity",
        f"- Asset ID: {report['assetId']}",
        f"- Runtime alias: {report['alias']}",
        f"- Canonical target path: {report['canonicalTargetPath']}",
        f"- Expected viewBox: {report['viewBoxExpected']}",
        f"- Required groups: {', '.join(report['requiredGroupsExpected'])}",
        "",
        "## Input hashes",
        f"- Brief path: {report['briefPath']}",
        f"- Brief SHA-256: {report['briefSha256']}",
        f"- Inbox SVG path: {report['svgPath']}",
        f"- Inbox SVG SHA-256: {report['svgSha256']}",
        "",
        "## Gate A — Intake identity",
        f"- Asset ID: {report['assetId']}",
        f"- Runtime alias: {report['alias']}",
        f"- Canonical target path: {report['canonicalTargetPath']}",
        f"- Expected viewBox: {report['viewBoxExpected']}",
        "",
        "## Gate B — XML and SVG structure",
        f"- viewBox actual: {report['viewBoxActual'] or '(missing)'}",
        f"- Required groups found: {_join_or_none(report['requiredGroupsFound'])}",
        f"- Missing required groups: {_join_or_none(report['missingRequiredGroups'])}",
        f"- Empty required groups: {_join_or_none(report['emptyRequiredGroups'])}",
        f"- Duplicate IDs: {_join_or_none(report['duplicateIds'])}",
        f"- Unresolved references: {_join_or_none(report['unresolvedReferences'])}",
        f"- External dependencies: {_join_or_none(report['externalReferences'])}",
        f"- Forbidden elements: {_join_or_none(report['forbiddenElements'])}",
        f"- Forbidden attributes: {_join_or_none(report['forbiddenAttributes'])}",
        f"- Non-finite numeric values: {_join_or_none(report['nonFiniteFindings'])}",
        f"- Transparent background: {report['backgroundTransparencyPass']}",
        "",
    ] + face_lines + [
        "## Warnings",
        _join_or_none(report["warnings"]),
        "",
        "## Final verdict",
        verdict,
        "",
        "## Rejection reasons",
        _join_or_none(report["rejectionReasons"]),
        "",
        "## Next permitted action",
        next_action,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parent.parent.parent
    brief_path = Path(args.brief)
    svg_path = Path(args.svg)

    if not brief_path.is_file():
        print(f"ERROR: active brief not found: {brief_path}", file=sys.stderr)
        return 2
    if not svg_path.is_file():
        print(f"ERROR: inbox SVG not found: {svg_path}", file=sys.stderr)
        return 2

    rejection: list[str] = []

    try:
        brief = _parse_brief(brief_path)
        contract = _contract_from_brief(brief)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = _new_report(repo_root, brief_path, svg_path, brief, contract)
    _gate_a(brief_path, svg_path, brief, contract, rejection)
    _gate_b(svg_path, report, rejection, _enforced_face_features(brief))

    report["warnings"] = _dedup_ordered(report["warnings"])
    report["rejectionReasons"] = _dedup_ordered(rejection)

    if report["rejectionReasons"]:
        report["verdict"] = "STRUCTURE_REJECTED"
    else:
        report["verdict"] = "STRUCTURE_PASS"

    if args.report_json:
        _write_json(Path(args.report_json), report)
    if args.report_md:
        _write_markdown(Path(args.report_md), report)

    summary = (
        f"{report['verdict']}  {report['assetId']}  "
        f"svg_sha256={report['svgSha256'][:12]}"
    )
    print(summary)
    if report["rejectionReasons"]:
        for reason in report["rejectionReasons"]:
            print(f"REJECT: {reason}", file=sys.stderr)
        return 1
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate an Ocean Rescue manual SVG handoff candidate "
            "against the active brief (Gate A/B)."
        )
    )
    parser.add_argument("--brief", required=True, help="Active handoff brief path")
    parser.add_argument("--svg", required=True, help="Inbox SVG candidate path")
    parser.add_argument(
        "--report-json", default=None, help="Output path for the JSON evidence report"
    )
    parser.add_argument(
        "--report-md", default=None, help="Output path for the Markdown evidence report"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    try:
        return run(args)
    except Exception as exc:  # pragma: no cover - defensive crash boundary
        print(f"ERROR: validator crashed: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
