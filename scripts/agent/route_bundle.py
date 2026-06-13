"""Assemble route bundles and must_read checklists for agents."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

from scripts.agent.route_matching import (
    get_relevant_project_skills,
    get_relevant_rules,
    project_skill_path,
)
from scripts.agent.route_parsing import find_repo_root, normalize_repo_rel
from scripts.error_patterns.detail_paths import detail_paths_for_edit_files


def _strip_rule_annotation(rule: str) -> str:
    s = rule.strip().replace("`", "")
    return re.sub(r"\s+\([^)]*\)\s*$", "", s).strip()


def resolve_rule_tokens_to_paths(rule_tokens: Iterable[str], repo_root: Path) -> List[str]:
    """Map CONTEXT_ROUTING rule column tokens to repo-relative file paths."""
    paths: List[str] = []
    seen: Set[str] = set()

    def add(rel: str) -> None:
        rel = normalize_repo_rel(rel)
        if rel and rel not in seen:
            seen.add(rel)
            paths.append(rel)

    for raw in rule_tokens:
        for token in re.split(r",(?![^{]*\})", raw):
            token = _strip_rule_annotation(token)
            if not token:
                continue
            if token.startswith(".agents/"):
                if (repo_root / token).is_file():
                    add(token)
                continue
            if token == "adaptive/*.md":
                for p in sorted((repo_root / ".agents/adaptive").glob("*.md")):
                    add(str(p.relative_to(repo_root)))
                continue
            if token.endswith(".md"):
                if token.startswith("core/"):
                    core = repo_root / ".agents/core" / Path(token).name
                    if core.is_file():
                        add(str(core.relative_to(repo_root)))
                    continue
                domain = repo_root / ".agents/domains" / token
                if domain.is_file():
                    add(str(domain.relative_to(repo_root)))
                    continue
                core = repo_root / ".agents/core" / Path(token).name
                if core.is_file():
                    add(str(core.relative_to(repo_root)))
    return paths


def skill_detail_path(skill_rel: str) -> str | None:
    """SKILL.md → sibling SKILL_detail.md when present (Phase-2 lazy load)."""
    norm = normalize_repo_rel(skill_rel)
    if not norm.endswith("/SKILL.md"):
        return None
    detail = norm[: -len("SKILL.md")] + "SKILL_detail.md"
    return detail


def build_must_read(
    *,
    repo_root: Path,
    rules: Sequence[str],
    project_skills: Sequence[str],
    file_paths: Sequence[str] = (),
) -> List[Dict[str, object]]:
    """
    Ordered checklist of files the agent MUST Read before editing target paths.
    Order: domain/core rules → project skills.
    Project skills expose lazy_load + detail_path for two-phase loading.
    """
    must_read: List[Dict[str, object]] = []
    seen: Set[str] = set()

    def append_entry(rel: str, kind: str, *, lazy_load: bool = False) -> None:
        rel = normalize_repo_rel(rel)
        if not rel or rel in seen:
            return
        seen.add(rel)
        full = repo_root / rel
        entry: Dict[str, object] = {
            "path": rel,
            "kind": kind,
            "installed": full.is_file(),
        }
        if lazy_load:
            entry["lazy_load"] = True
            detail = skill_detail_path(rel)
            detail_candidates = [detail] if detail else []
            if detail and "/frontend/" in detail:
                detail_candidates.append(detail.replace("/frontend/", "/", 1))
            for cand in detail_candidates:
                if cand and (repo_root / cand).is_file():
                    entry["detail_path"] = cand
                    break
        must_read.append(entry)

    for rel in resolve_rule_tokens_to_paths(rules, repo_root):
        append_entry(rel, "rule")

    for skill in project_skills:
        append_entry(skill, "project_skill", lazy_load=True)

    for rel in detail_paths_for_edit_files(file_paths, repo_root):
        append_entry(rel, "error_pattern_detail")

    return must_read


def get_route_bundle(
    file_paths: Sequence[str],
    *,
    repo_root: Path | None = None,
    intent_queries: Sequence[str] = (),
    apply_cap: bool = True,
    cap: int = 5,
    tight: bool = True,
) -> Dict[str, object]:
    """Full routing payload for agents (rules + skills + mandatory read list)."""
    root = repo_root or find_repo_root()
    skill_cap = 2 if tight else cap
    apply_skill_cap = apply_cap if not tight else True
    rules = get_relevant_rules(
        file_paths,
        repo_root=root,
        include_always_load=not tight,
    )
    project_list, project_meta = get_relevant_project_skills(
        file_paths,
        repo_root=root,
        intent_queries=intent_queries,
        apply_cap=apply_skill_cap,
        cap=skill_cap,
    )
    must_read = build_must_read(
        repo_root=root,
        rules=rules,
        project_skills=project_list,
        file_paths=file_paths,
    )
    missing = [e["path"] for e in must_read if not e["installed"]]

    return {
        "repo_root": str(root),
        "files": list(file_paths),
        "tight": tight,
        "skill_cap": skill_cap,
        "rules": rules,
        "project_skills": project_list,
        "project_meta": project_meta,
        "project_install_paths": {s: str(project_skill_path(root, s)) for s in project_list},
        "project_installed": {s: project_skill_path(root, s).is_file() for s in project_list},
        "must_read": must_read,
        "must_read_paths": [e["path"] for e in must_read if e["installed"]],
        "missing_paths": missing,
        "gate": {
            "command": "just route <repo-relative-paths...> --json",
            "manifest": (
                "just route <paths> --json --write-manifest; Read must_read; "
                "just route-read <path>…; before edit: just route-gate-check <paths>"
            ),
            "before_edit": (
                "Run the command, then Read every path in must_read where installed=true. "
                "Record reads with `just route-read` and pass `just route-gate-check` before patch."
            ),
            "violation": "Editing without completing must_read is a policy breach; do not declare done.",
        },
    }
