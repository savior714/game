#!/usr/bin/env python3
"""Resolve CONTEXT_ROUTING + project skill routes against file paths (and optional intent).

SSOT tables:
  - .agents/registry/CONTEXT_ROUTING.md
  - .agents/registry/PROJECT_SKILL_ROUTING.json

This module re-exports everything from the split sub-modules for backward
compatibility.  Consumers should continue importing from ``scripts.agent.route_context``.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Re-export bundle helpers (from route_bundle)
# ---------------------------------------------------------------------------
from scripts.agent.route_bundle import (
    build_must_read,
    get_route_bundle,
    resolve_rule_tokens_to_paths,
    skill_detail_path,
)

# ---------------------------------------------------------------------------
# Re-export CLI helpers (from route_context_cli + route_context_printers)
# ---------------------------------------------------------------------------
from scripts.agent.route_context_cli import (
    _ROUTE_FLAG_TOKENS,
    main,
    sanitize_route_paths,
)
from scripts.agent.route_context_printers import (
    _print_must_read_block,
    _print_project_skills_block,
)

# ---------------------------------------------------------------------------
# Re-export matching helpers (from route_matching)
# ---------------------------------------------------------------------------
from scripts.agent.route_matching import (
    get_relevant_project_skills,
    get_relevant_rules,
    match_glob,
    project_skill_path,
)

# ---------------------------------------------------------------------------
# Re-export constants and parsing helpers (from route_parsing)
# ---------------------------------------------------------------------------
from scripts.agent.route_parsing import (
    PROJECT_SKILL_ROUTING_FILE,
    ROUTING_FILE,
    expand_curly_braces,
    extract_project_skill_paths,
    find_repo_root,
    get_always_load_rules,
    load_project_skill_routing,
    normalize_repo_rel,
    parse_context_routing_md,
    parse_context_routing_project_skill_globs,
    strip_pattern_annotation,
)

__all__ = [
    "PROJECT_SKILL_ROUTING_FILE",
    "ROUTING_FILE",
    "_ROUTE_FLAG_TOKENS",
    "_print_must_read_block",
    "_print_project_skills_block",
    "build_must_read",
    "expand_curly_braces",
    "extract_project_skill_paths",
    "find_repo_root",
    "get_always_load_rules",
    "get_relevant_project_skills",
    "get_relevant_rules",
    "get_route_bundle",
    "load_project_skill_routing",
    "main",
    "match_glob",
    "normalize_repo_rel",
    "parse_context_routing_md",
    "parse_context_routing_project_skill_globs",
    "project_skill_path",
    "resolve_rule_tokens_to_paths",
    "sanitize_route_paths",
    "skill_detail_path",
    "strip_pattern_annotation",
]

if __name__ == "__main__":
    from scripts.agent.route_context_cli import main

    raise SystemExit(main())

