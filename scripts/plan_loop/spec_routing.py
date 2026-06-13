#!/usr/bin/env python3
"""Spec routing utilities for plan preread manifest generation."""
from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

# Strategy 2 — filename keywords → spec files (case-insensitive, fallback)
_KEYWORD_TO_SPEC_GLOB: dict[str, str] = {
    "hira": "*hira*",
    "knass": "*knass*",
    "fhir": "*fhir*",
    "billing": "*billing*",
    "draft": "*draft*",
    "staging": "*staging*",
    "publish": "*publish*",
    "sync": "*sync*",
    "vault": "*vault*",
    "reference_data": "*reference_data*",
    "master_router": "*master*",
    "prescription": "*prescription*",
    "diagnosis": "*diagnosis*",
    "consultation": "*consultation*",
    "frontend": "*frontend*",
    "renderer": "*renderer*",
    "desktop": "*desktop*",
}

# Strategy 3 — path prefix → spec subdirectory (fallback, for UI work)
_PATH_TO_SPEC_DIR: dict[str, str] = {
    "apps/renderer/src/": "ui",
    "apps/renderer/pages/": "ui",
}


def _read_spec_domains(spec_path: Path) -> set[str]:
    """Read 'domain:' tags from a spec file's header (first 20 lines).

    Supports both YAML frontmatter and comment-style:
      # domain: hira, reference_data, billing
      domain: hira, reference_data
    """
    domains: set[str] = set()
    try:
        with spec_path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 20:
                    break
                m = re.match(r"\s*#\s*domain:\s*(.+)", line)
                if not m:
                    m = re.match(r"\s*domain:\s*(.+)", line)
                if m:
                    for d in m.group(1).split(","):
                        domains.add(d.strip().lower())
    except (OSError, UnicodeDecodeError):
        pass
    return domains


def _spec_dir_specs(repo_root: Path, sub_dir: str) -> list[str]:
    """Return all .md files under docs/specs/<sub_dir>."""
    out: list[str] = []
    spec_dir = repo_root / "docs/specs" / sub_dir
    if spec_dir.is_dir():
        for p in sorted(spec_dir.glob("*.md")):
            out.append(str(p.relative_to(repo_root)))
    return out


def route_spec_files(paths: Sequence[str], repo_root: Path) -> list[str]:
    """Given plan target paths, return relevant docs/specs/*.md files.

    Priority:
      1. domain tag in spec header matches target path keywords
      2. filename keyword matching (fallback)
      3. path prefix → spec subdirectory (fallback, UI work)
    """
    matched: set[str] = set()

    # Strategy 1: domain tag in spec header
    specs_dir = repo_root / "docs/specs"
    if specs_dir.is_dir():
        for spec_file in sorted(specs_dir.rglob("*.md")):
            rel = str(spec_file.relative_to(repo_root))
            domains = _read_spec_domains(spec_file)
            if not domains:
                continue
            for rel_path in paths:
                lower = rel_path.lower()
                if any(d in lower for d in domains):
                    matched.add(rel)
                    break

    # Strategy 2: filename keywords (fallback, for specs without domain tags)
    for rel in paths:
        lower = rel.lower()
        for keyword, glob_pat in _KEYWORD_TO_SPEC_GLOB.items():
            if keyword in lower:
                for p in sorted((repo_root / "docs/specs").glob(f"**/{glob_pat}.md")):
                    matched.add(str(p.relative_to(repo_root)))

    # Strategy 3: path prefix → spec subdirectory (secondary, for UI work)
    for rel in paths:
        lower = rel.lower()
        for prefix, sub_dir in _PATH_TO_SPEC_DIR.items():
            if prefix.replace("/", "/") in lower:
                matched.update(_spec_dir_specs(repo_root, sub_dir))
                break

    return sorted(matched)
