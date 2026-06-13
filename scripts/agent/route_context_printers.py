#!/usr/bin/env python3
"""CLI display helpers for route_context."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from scripts.agent.route_matching import project_skill_path


def _print_project_skills_block(repo_root: Path, skills: Sequence[str]) -> None:
    """Print project skill entries with installation status."""
    print("Project skills (.agents/skills/<name>/SKILL.md, non-ecc):")
    if not skills:
        print("  (none)")
        return
    for rel in skills:
        p = project_skill_path(repo_root, rel)
        status = "installed" if p.is_file() else "missing"
        print(f"  - {rel:52} [{status}]")


def _print_must_read_block(
    entries: Sequence[dict[str, object]],
    *,
    route_paths: Sequence[str] | None = None,
    emit_gate_check: bool = False,
) -> None:
    """Print MUST READ entries, separated into installed and missing."""
    print("MUST READ before edit (installed paths — read all, in order):")
    installed = [e for e in entries if e.get("installed")]
    if not installed:
        print("  (none installed — check missing_paths in --json)")
        return
    for e in installed:
        lazy = " lazy" if e.get("lazy_load") else ""
        print(f"  - [{e.get('kind', '?'):14}{lazy}] {e.get('path')}")
        detail = e.get("detail_path")
        if detail:
            print(f"      detail (Phase 2): {detail}")
    missing = [e for e in entries if not e.get("installed")]
    if missing:
        print("Missing (skip Read; note in session):")
        for e in missing:
            print(f"  - [{e.get('kind', '?'):14}] {e.get('path')}")

    print("\n[Next Action for Agent]")
    print("Run the following command to register these files as read:")
    read_paths = [str(e.get("path")) for e in installed if e.get("path")]
    print("just route-read " + " ".join(read_paths))
    if emit_gate_check and route_paths:
        print("Run before write/patch/delete:")
        print("just route-gate-check " + " ".join(route_paths))
    print("(lazy_load: Phase 1 — read path; header only when detail_path is set)")
    print("(Phase 2 — read detail_path before UI/FE work; see CONTEXT_ROUTING.md)")
