#!/usr/bin/env python3
"""
Query-intent wrapper for route_context — narrows project skills from user text.

Usage:
  python3 scripts/agent/route_smart.py "리팩터 consultation grid" apps/renderer/src/foo.tsx --json
  just route-smart -- "UI 리뷰" apps/renderer/src/components/ui/badge.tsx
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.agent.route_context import (  # noqa: E402
    find_repo_root,
    get_route_bundle,
    normalize_repo_rel,
)

# (keyword regexes, intent_queries for PROJECT_SKILL_ROUTING, optional path hints)
_INTENT_RULES: list[tuple[re.Pattern[str], list[str], list[str]]] = [
    (
        re.compile(
            r"리팩터|refactor|composition|compound|컴파운드|boolean\s*prop",
            re.I,
        ),
        ["리팩터", "composition"],
        [],
    ),
    (
        re.compile(r"리뷰|review|접근성|a11y|audit|가이드라인", re.I),
        ["UI 리뷰", "review"],
        [],
    ),
    (
        re.compile(r"디자인|design|ui|ux|랜딩|landing|브랜드|visual", re.I),
        ["디자인", "design"],
        [],
    ),
    (
        re.compile(r"보안|security|vault|phi|hira|암호", re.I),
        [],
        ["src/security/", "vault/"],
    ),
    (
        re.compile(r"시딩|seeding|csv|인코딩|encoding|cp949|utf-8", re.I),
        [],
        ["scripts/", "src/infrastructure/"],
    ),
    (
        re.compile(
            r"discuss|/discuss|논의|방향\s*합의|개선\s*방향|DISCUSS_|handed-off|막연",
            re.I,
        ),
        ["discuss", "논의"],
        ["docs/discussions/"],
    ),
    (
        re.compile(r"테스트|test|tdd|e2e|playwright", re.I),
        ["test"],
        ["tests/"],
    ),
    (
        re.compile(r"docker|compose|컨테이너", re.I),
        [],
        ["docker-compose.yml", "Dockerfile"],
    ),
]

_DEFAULT_PATH_HINTS = ["apps/renderer/src/components/ui/badge.tsx"]


def classify_query(query: str) -> tuple[list[str], list[str], bool]:
    """
    Returns (intent_queries, extra_path_hints, suggest_tight).
    suggest_tight when query is short/generic (reduces always-load noise).
    """
    intents: list[str] = []
    paths: list[str] = []
    for pattern, intent_list, path_hints in _INTENT_RULES:
        if pattern.search(query):
            for i in intent_list:
                if i not in intents:
                    intents.append(i)
            for p in path_hints:
                if p not in paths:
                    paths.append(p)

    q = query.strip()
    suggest_tight = len(q) < 24 and not paths and len(intents) <= 1
    return intents, paths, suggest_tight


def merge_paths(cli_paths: Sequence[str], hints: Sequence[str]) -> list[str]:
    out: list[str] = []
    for raw in list(cli_paths) + list(hints):
        rel = normalize_repo_rel(raw)
        if rel and rel not in out:
            out.append(rel)
    return out or list(_DEFAULT_PATH_HINTS)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve routing from natural-language query + optional file paths.",
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="",
        help="User message or intent text (quoted).",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Repo-relative paths to route (optional).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON bundle.",
    )
    parser.add_argument(
        "--tight",
        action="store_true",
        help="Force ultra-light routing (skip Always Load; cap skills at 2).",
    )
    parser.add_argument(
        "--no-tight",
        action="store_true",
        help="Disable automatic tight mode for short queries.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include Always Load rules (disable tight); preferred for turn-1 manifest.",
    )
    parser.add_argument(
        "--write-manifest",
        action="store_true",
        help="Append bundle to session manifest (phase default: turn1).",
    )
    parser.add_argument(
        "--phase",
        default="turn1",
        choices=("turn1", "pre_edit"),
        help="Manifest phase when using --write-manifest.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    query = (args.query or "").strip()
    if not query and not args.files:
        parser.error("Provide a query string and/or file paths.")

    intents, hints, suggest_tight = classify_query(query) if query else ([], [], False)
    use_tight = not args.full and (
        args.tight or (suggest_tight and not args.no_tight)
    )
    file_paths = merge_paths(args.files, hints)

    root = find_repo_root()
    bundle = get_route_bundle(
        file_paths,
        repo_root=root,
        intent_queries=intents,
        tight=use_tight,
    )
    bundle["query"] = query
    bundle["classified_intents"] = intents
    bundle["path_hints"] = hints

    if args.write_manifest:
        from scripts.agent.route_gate import append_bundle_from_route

        append_bundle_from_route(bundle, phase=args.phase, repo_root=root)

    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
        return 0

    print(f"Query: {query!r}")
    print(f"Files: {file_paths}")
    print(f"Intents: {intents or '(none)'}")
    print(f"Tight: {use_tight}")
    print(f"Project skills ({len(bundle['project_skills'])}): {bundle['project_skills']}")
    print(f"must_read_paths ({len(bundle['must_read_paths'])}):")
    for p in bundle["must_read_paths"]:
        print(f"  - {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
