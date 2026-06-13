#!/usr/bin/env python3
"""CLI: estimate route bundle token budget."""
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from scripts.agent.route_budget import budget_report_for_bundle
from scripts.agent.route_context import find_repo_root, get_route_bundle, sanitize_route_paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Estimate must_read token budget for route bundle.")
    parser.add_argument("files", nargs="*", help="Repo-relative paths to route.")
    parser.add_argument("--target", type=int, default=None, help="Budget cap in estimated tokens.")
    parser.add_argument("--full", action="store_true", help="Include always-load rules (non-tight).")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo_root = find_repo_root()
    files = sanitize_route_paths(args.files)
    bundle = get_route_bundle(files, repo_root=repo_root, tight=not args.full)
    report = budget_report_for_bundle(
        bundle,
        repo_root=repo_root,
        budget_tokens=args.target,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        est = report["estimate"]["total_tokens"]
        print(f"Estimated must_read tokens: {est}")
        if args.target is not None:
            b = report.get("budget", {})
            print(f"Budget target: {args.target}")
            print(f"Within budget: {b.get('within_budget')}")
            deferred = b.get("would_defer") or []
            for path in deferred:
                print(f"  defer: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
