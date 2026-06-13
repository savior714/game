#!/usr/bin/env python3
"""CLI entry point and path sanitization for route_context."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from scripts.agent.route_bundle import get_route_bundle
from scripts.agent.route_context_printers import (
    _print_must_read_block,
    _print_project_skills_block,
)
from scripts.agent.route_context_utils import find_repo_root, normalize_repo_rel

_ROUTE_FLAG_TOKENS = frozenset(
    {
        "--json",
        "--full",
        "--tight",
        "--write-manifest",
        "--no-cap",
    }
)


def sanitize_route_paths(raw_paths: Sequence[str]) -> list[str]:
    """
    Drop stray ``--`` and CLI flags passed as paths (e.g. ``just route -- foo
    --json`` forwards ``--`` to Python when the just recipe uses ``*`` args).
    """
    out: list[str] = []
    skip_next = False
    for item in raw_paths:
        if skip_next:
            skip_next = False
            continue
        token = (item or "").strip()
        if not token or token == "--":  # noqa: S105
            continue
        if token in _ROUTE_FLAG_TOKENS:
            continue
        if token in ("--phase", "--intent"):
            skip_next = True
            continue
        if token.startswith("--"):
            continue
        rel = normalize_repo_rel(token)
        if rel:
            out.append(rel)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    """Resolve CONTEXT_ROUTING rules and PROJECT_SKILL_ROUTING skills."""
    parser = argparse.ArgumentParser(
        description=(
            "Resolve CONTEXT_ROUTING rules and PROJECT_SKILL_ROUTING skill candidates."
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Repo-relative or absolute file paths (use '.' for repo root heuristics only)",
    )
    parser.add_argument(
        "--intent",
        action="append",
        default=[],
        metavar="TEXT",
        help="Substring to match against project skill intent routes (repeatable).",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Disable tight mode and load all always-load rules",
    )
    parser.add_argument(
        "--tight",
        action="store_true",
        help="(Legacy) Now the default behavior",
    )
    parser.add_argument(
        "--no-cap",
        action="store_true",
        help="Do not apply the 5-skill agent cap (list full merged set).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON (rules + project skills + meta).",
    )
    parser.add_argument(
        "--write-manifest",
        action="store_true",
        help="Append this bundle to .agents/route/session-manifest.json (see route_gate.py).",
    )
    parser.add_argument(
        "--phase",
        default="pre_edit",
        choices=("turn1", "pre_edit"),
        help="Manifest phase when using --write-manifest (default: pre_edit).",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=None,
        metavar="TOKENS",
        help="Cap must_read estimated size; defer lazy detail paths over budget.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = find_repo_root()
    files = sanitize_route_paths(args.files)
    tight = not args.full
    skill_cap = 2 if tight else 5

    bundle = get_route_bundle(
        files,
        repo_root=repo_root,
        intent_queries=args.intent,
        apply_cap=not args.no_cap,
        cap=skill_cap,
        tight=tight,
    )

    if args.budget is not None:
        from scripts.agent.route_budget import (  # noqa: PLC0415
            apply_budget_to_must_read,
            budget_report_for_bundle,
        )

        must_read = list(bundle.get("must_read") or [])
        trimmed, budget_meta = apply_budget_to_must_read(
            must_read,
            repo_root=repo_root,
            budget_tokens=args.budget,
        )
        bundle["must_read"] = trimmed
        bundle["must_read_paths"] = [
            e["path"] for e in trimmed if e.get("installed")
        ]
        bundle["budget"] = budget_report_for_bundle(
            {**bundle, "must_read": must_read},
            repo_root=repo_root,
            budget_tokens=args.budget,
        )
        bundle["budget"]["applied"] = budget_meta

    if args.write_manifest:
        from scripts.agent.route_gate import append_bundle_from_route  # noqa: PLC0415

        append_bundle_from_route(bundle, phase=args.phase, repo_root=repo_root)

    if args.json:
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
        return 0

    rules = bundle["rules"]
    project_list = bundle["project_skills"]
    project_meta = bundle["project_meta"]

    if rules:
        print(f"Matched rules for {files!r}:")
        for rule in rules:
            print(f"  - {rule}")
    else:
        print(f"No rules matched for {files!r}")

    _print_project_skills_block(repo_root, project_list)
    if args.intent and project_meta.get("from_intent"):
        print("Project skill intent matches:")
        print(f"  {project_meta['from_intent']}")

    print()
    _print_must_read_block(
        bundle["must_read"],
        route_paths=files,
        emit_gate_check=args.write_manifest,
    )

    if args.no_cap:
        print(
            f"\n(Cap disabled: project={len(project_list)}; default cap is 5.)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
