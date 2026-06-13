"""Glob matching and rule/skill resolution for context routing."""
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

from scripts.agent.route_parsing import (
    PROJECT_SKILL_ROUTING_FILE,
    ROUTING_FILE,
    expand_curly_braces,
    find_repo_root,
    get_always_load_rules,
    load_project_skill_routing,
    normalize_repo_rel,
    parse_context_routing_md,
    parse_context_routing_project_skill_globs,
)


def match_glob(fp: str, pattern: str) -> bool:
    """Robust glob matching that handles ** and recursive directory patterns."""
    if fnmatch.fnmatch(fp, pattern):
        return True

    if "/**/*" in pattern:
        if fnmatch.fnmatch(fp, pattern.replace("/**/*", "/*")):
            return True
        prefix, suffix = pattern.split("/**/*", 1)
        if fp.startswith(prefix + "/") or fp == prefix:
            if not suffix:
                return True
            if fnmatch.fnmatch(fp, f"{prefix}/**/{suffix.lstrip('/')}"):
                return True
            if "/" not in suffix:
                basename = fp.rsplit("/", 1)[-1]
                if fnmatch.fnmatch(basename, suffix):
                    return True

    if pattern.startswith("**/"):
        suffix = pattern[2:]
        if fnmatch.fnmatch(fp, "*" + suffix):
            return True

    return False


def get_rule_priority(rule: str) -> int:
    """LOAD_ORDER-style priority (lower = earlier)."""
    path = rule.lower()

    if "project_rules.md" in path:
        return 10
    if "agents.md" in path:
        return 11

    if "load_order.md" in path:
        return 20
    if "context_routing.md" in path:
        return 21
    if "memory.md" in path:
        return 30

    if "core/" in path or ".agents/core/" in path:
        return 40

    if (
        "domains/" in path
        or ".agents/domains/" in path
        or any(
            d in path
            for d in [
                "backend/",
                "frontend/",
                "infra/",
                "medical/",
                "testing/",
                "tech-stack/",
                "documentation/",
            ]
        )
    ):
        return 50

    if "workflows/" in path or ".agents/workflows/" in path:
        return 60

    if "adaptive/" in path or ".agents/adaptive/" in path:
        return 70

    return 100


def get_relevant_rules(
    file_paths: Sequence[str],
    *,
    repo_root: Path | None = None,
    include_always_load: bool = True,
) -> List[str]:
    """Domain / always-load rules from CONTEXT_ROUTING.md."""
    root = repo_root or find_repo_root()
    mapping = parse_context_routing_md(str(root / ROUTING_FILE))
    relevant_rules: Set[str] = set()
    if include_always_load:
        relevant_rules.update(get_always_load_rules(str(root / ROUTING_FILE)))

    for fp in file_paths:
        for pattern, rule in mapping:
            if match_glob(fp, pattern):
                relevant_rules.add(rule)

    return sorted(relevant_rules, key=lambda x: (get_rule_priority(x), x))


def project_skill_path(repo_root: Path, rel_path: str) -> Path:
    return repo_root / normalize_repo_rel(rel_path)


def _project_skill_priority_index(priority: Sequence[str]) -> Dict[str, int]:
    return {p: i for i, p in enumerate(priority)}


def cap_project_skills(skills: Iterable[str], *, priority: Sequence[str], limit: int) -> List[str]:
    uniq = sorted({s for s in skills if s.endswith("SKILL.md")})
    ranked = sorted(uniq, key=lambda s: (_project_skill_priority_index(priority).get(s, 999), s))
    return ranked[:limit]


def match_project_intent(
    intent_queries: Sequence[str],
    intent_routes: Sequence[Dict[str, object]],
) -> Set[str]:
    out: Set[str] = set()
    if not intent_queries:
        return out
    for route in intent_routes:
        keywords = route.get("match_any") or []
        skills = route.get("skills") or []
        if not isinstance(keywords, list) or not isinstance(skills, list):
            continue
        for q in intent_queries:
            qn = (q or "").strip().lower()
            if not qn:
                continue
            for kw in keywords:
                kn = str(kw).lower()
                if kn in qn or qn in kn:
                    out.update(str(s) for s in skills)
                    break
    return out


def collect_project_skills_from_globs(
    file_paths: Sequence[str],
    mappings: Sequence[Tuple[str, Sequence[str]]],
) -> Set[str]:
    out: Set[str] = set()
    for fp in file_paths:
        for pattern, skills in mappings:
            if match_glob(fp, pattern):
                out.update(skills)
    return out


def get_relevant_project_skills(
    file_paths: Sequence[str],
    *,
    repo_root: Path | None = None,
    intent_queries: Sequence[str] = (),
    apply_cap: bool = True,
    cap: int | None = None,
) -> Tuple[List[str], Dict[str, object]]:
    root = repo_root or find_repo_root()
    rel_paths = [normalize_repo_rel(p) for p in file_paths]

    cfg = load_project_skill_routing(root)
    skill_cap = int(cap if cap is not None else cfg.get("cap", 5))
    priority = list(cfg.get("priority") or [])

    json_routes: List[Tuple[str, List[str]]] = []
    for route in cfg.get("path_routes") or []:
        if not isinstance(route, dict):
            continue
        skills = [str(s) for s in (route.get("skills") or [])]
        for glob_pat in route.get("globs") or []:
            for expanded in expand_curly_braces(str(glob_pat)):
                json_routes.append((expanded, skills))

    ctx_routes = parse_context_routing_project_skill_globs(str(root / ROUTING_FILE))
    combined = list(json_routes) + list(ctx_routes)

    from_paths = collect_project_skills_from_globs(rel_paths, combined)
    intent_routes = cfg.get("intent_routes") or []
    from_intent = match_project_intent(intent_queries, intent_routes)  # type: ignore[arg-type]

    merged = set(from_paths) | set(from_intent)
    capped = (
        cap_project_skills(merged, priority=priority, limit=skill_cap)
        if apply_cap
        else sorted(merged)
    )

    meta: Dict[str, object] = {
        "from_path_globs": sorted(from_paths),
        "from_intent": sorted(from_intent),
        "merged": sorted(merged),
        "capped": apply_cap,
        "cap": skill_cap,
        "ssot": PROJECT_SKILL_ROUTING_FILE,
    }
    return capped, meta


