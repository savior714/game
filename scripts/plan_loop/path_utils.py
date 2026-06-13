#!/usr/bin/env python3
"""Path extraction utilities for plan preread manifest generation."""
from __future__ import annotations

import re
from pathlib import Path

from scripts.agent.route_context import normalize_repo_rel

SECTION_HEADING = "## \U0001f9ed Context Pre-read Gate (\uc2e4\ud589 \uc804 \ud544\uc218)"
SECTION_RE = re.compile(
    rf"^{re.escape(SECTION_HEADING)}\s*\n"
    rf"(?:.*?\n)*?"
    rf"(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)

_REPO_PATH = re.compile(
    r"(?<![\w./])"
    r"((?:apps|src|tests|scripts|packages|\.agents|docs)/[\w./-]+\."
    r"(?:py|ts|tsx|jsx|js|md|json|yaml|yml|sql|toml|gradle|kt|java|rs|go))"
)

_ABS_REPO_PATH = re.compile(
    r"/(?:Users/[^/]+/)?[\w.-]+/Desktop/Dev/emr/([\w./-]+\.\w+)"
)

_TARGET_FIELD = re.compile(
    r"(?:\*\*Target\*\*|Target):\s*`?([^`\n|]+)`?",
    re.IGNORECASE,
)


def _to_repo_rel(path: str, repo_root: Path) -> str | None:
    raw = path.strip().strip("`").strip()
    if not raw or raw in {".", "..", "TBD", "N/A"}:
        return None
    raw = raw.replace("\\", "/")
    m = _ABS_REPO_PATH.search(raw)
    if m:
        raw = m.group(1)
    if raw.startswith(str(repo_root)):
        raw = raw[len(str(repo_root)) :].lstrip("/")
    raw = normalize_repo_rel(raw)
    if raw.startswith("docs/plans/"):
        return None
    if "docs/specs/" in raw:
        return None
    if "/" not in raw and not raw.startswith("."):
        return None
    return raw


def _strip_preread_gate(text: str) -> str:
    """Remove machine-generated gate so its rule paths are not fed back into routing."""
    return SECTION_RE.sub("", text, count=1)


def _is_incidental_repo_path(rel: str) -> bool:
    """Paths cited in prose/gate lists — not edit targets for this blueprint."""
    return rel.startswith(".agents/") or "docs/specs/" in rel


def _target_field_values(block: str) -> list[str]:
    """Raw Target payloads from task lines (supports `Action | **Target**:` packed rows)."""
    values: list[str] = []
    for line in block.splitlines():
        if not re.search(r"(?:\*\*Target\*\*|Target):", line, re.IGNORECASE):
            continue
        m = re.search(r"(?:\*\*Target\*\*|Target):\s*(.+?)\s*$", line, re.IGNORECASE)
        if m:
            values.append(m.group(1).strip())
    return values


def _paths_from_target_payload(raw: str, repo_root: Path) -> list[str]:
    """Align with plan_lint._extract_target_paths — every backtick path, not only the first."""
    quoted = re.findall(r"`([^`]+)`", raw)
    parts = [p.strip() for p in quoted] if quoted else re.split(r"[,;\xb7]\s*", raw)
    out: list[str] = []
    for part in parts:
        rel = _to_repo_rel(part, repo_root)
        if rel and not _is_incidental_repo_path(rel):
            out.append(rel)
    return out


def extract_task_paths(block: str, repo_root: Path) -> list[str]:
    """Paths from a single Task block (Target field only — avoids .ts/.tsx double match)."""
    found: set[str] = set()
    for raw in _target_field_values(block):
        for rel in _paths_from_target_payload(raw, repo_root):
            found.add(rel)
    return sorted(found)


def extract_plan_paths(text: str, repo_root: Path) -> list[str]:
    body = _strip_preread_gate(text)
    found: set[str] = set()
    for m in _REPO_PATH.finditer(body):
        rel = _to_repo_rel(m.group(1), repo_root)
        if rel and not _is_incidental_repo_path(rel):
            found.add(rel)
    for m in _TARGET_FIELD.finditer(body):
        for part in re.split(r"[,;]\s*", m.group(1)):
            rel = _to_repo_rel(part, repo_root)
            if rel:
                found.add(rel)
    return sorted(found)
