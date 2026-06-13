#!/usr/bin/env python3
"""CLI commands for Context Route Gate session manifest."""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from scripts.agent.route_gate_core import (
    VALID_PHASES,
    gate_check,
    gate_check_touched,
)
from scripts.agent.route_gate_manifest import (
    load_manifest,
    manifest_abs_path,
)


def cmd_write_bundle(args: argparse.Namespace) -> int:
    from pathlib import Path  # noqa: PLC0415

    from scripts.agent.route_context import find_repo_root  # noqa: PLC0415
    from scripts.agent.route_gate_core import append_bundle_from_route  # noqa: PLC0415

    root = find_repo_root()
    if args.bundle_json:
        bundle = json.loads(Path(args.bundle_json).read_text(encoding="utf-8"))
    else:
        raw = sys.stdin.read()
        if not raw.strip():
            print("error: provide --bundle-json or pipe route JSON on stdin", file=sys.stderr)
            return 2
        bundle = json.loads(raw)
    bundle_id = append_bundle_from_route(bundle, phase=args.phase, repo_root=root)
    out = {"bundle_id": bundle_id, "manifest": str(manifest_abs_path(root))}
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote bundle {bundle_id} -> {manifest_abs_path(root)}")
    return 0


def cmd_record_read(args: argparse.Namespace) -> int:
    from scripts.agent.route_gate_core import record_reads  # noqa: PLC0415

    detail = None if not args.require_detail else True
    if args.no_detail:
        detail = False
    paths = record_reads(
        args.paths,
        via=args.via,
        bundle_id=args.bundle_id,
        include_detail=detail,
    )
    if args.json:
        print(json.dumps({"recorded": paths}, ensure_ascii=False, indent=2))
    else:
        for p in paths:
            print(f"recorded: {p}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    detail = None
    if args.require_detail:
        detail = True
    if args.no_detail:
        detail = False
    result = gate_check(
        args.paths,
        full_route=not args.tight,
        require_detail=detail,
        patch_file=args.file,
        patch_old_string=args.patch_old_string,
        patch_new_string=args.patch_new_string,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["message"])
        for m in result.get("missing", []):
            print(f"  missing: {m}")
    return 0 if result["ok"] else 1


def cmd_check_touched(args: argparse.Namespace) -> int:
    result = gate_check_touched(skip_if_no_manifest=not args.require_manifest)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["message"])
        for m in result.get("missing", []):
            print(f"  missing: {m}")
        for p in result.get("touched_paths", []):
            print(f"  touched: {p}")
    return 0 if result["ok"] else 1


def cmd_status(_args: argparse.Namespace) -> int:
    manifest = load_manifest()
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    from scripts.agent.route_gate_manifest import (  # noqa: PLC0415
        _mutate_manifest,
        load_manifest,
    )
    from scripts.agent.route_gate_heal import (  # noqa: PLC0415
        prune_superseded_and_old_complete_bundles,
    )

    before = load_manifest()
    before_bundles = len(before.get("bundles", []))
    before_reads = len(before.get("all_reads", []))

    def _prune(manifest: dict) -> dict:
        prune_superseded_and_old_complete_bundles(
            manifest,
            max_active=args.max_active,
            max_complete=args.max_complete,
            max_superseded=args.max_superseded,
            max_all_reads=args.max_all_reads,
        )
        return {
            "bundles_before": before_bundles,
            "bundles_after": len(manifest.get("bundles", [])),
            "all_reads_before": before_reads,
            "all_reads_after": len(manifest.get("all_reads", [])),
        }

    from scripts.agent.route_context import find_repo_root  # noqa: PLC0415

    summary = _mutate_manifest(find_repo_root(), _prune)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"Pruned manifest: bundles {summary['bundles_before']} -> "
            f"{summary['bundles_after']}, reads "
            f"{summary['all_reads_before']} -> {summary['all_reads_after']}"
        )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Context route session manifest gate.")
    sub = parser.add_subparsers(dest="command", required=True)

    w = sub.add_parser("write-bundle", help="Append a route JSON bundle to the session manifest.")
    w.add_argument("--phase", default="pre_edit", choices=sorted(VALID_PHASES))
    w.add_argument("--bundle-json", help="Path to route bundle JSON (else stdin).")
    w.add_argument("--json", action="store_true")
    w.set_defaults(func=cmd_write_bundle)

    r = sub.add_parser("record-read", help="Record that must_read paths were Read.")
    r.add_argument("paths", nargs="+", help="Repo-relative paths that were read.")
    r.add_argument("--via", default="mcp")
    r.add_argument("--bundle-id", default=None)
    r.add_argument("--require-detail", action="store_true")
    r.add_argument("--no-detail", action="store_true")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_record_read)

    c = sub.add_parser("check", help="Verify must_read complete before edit.")
    c.add_argument("paths", nargs="+", help="Repo-relative paths about to be edited.")
    c.add_argument("--tight", action="store_true", help="Use tight route when inferring without bundle.")
    c.add_argument("--require-detail", action="store_true")
    c.add_argument("--no-detail", action="store_true")
    c.add_argument("--json", action="store_true")
    c.add_argument(
        "--file",
        default=None,
        help="Repo-relative patch target (with --old-string for pattern 1.2).",
    )
    c.add_argument(
        "--old-string",
        default=None,
        dest="patch_old_string",
        help="Patch old_string to verify uniqueness in --file.",
    )
    c.add_argument(
        "--new-string",
        default=None,
        dest="patch_new_string",
        help="Patch new_string; with --old-string verifies old != new before edit.",
    )
    c.set_defaults(func=cmd_check)

    t = sub.add_parser("check-touched", help="Verify must_read for git-touched paths.")
    t.add_argument(
        "--require-manifest",
        action="store_true",
        help="Fail when manifest is empty (default: skip).",
    )
    t.add_argument("--json", action="store_true")
    t.set_defaults(func=cmd_check_touched)

    s = sub.add_parser("status", help="Print session manifest JSON.")
    s.set_defaults(func=cmd_status)

    p = sub.add_parser("prune", help="Cap session manifest bundles and all_reads.")
    p.add_argument("--max-active", type=int, default=10)
    p.add_argument("--max-complete", type=int, default=20)
    p.add_argument("--max-superseded", type=int, default=30)
    p.add_argument("--max-all-reads", type=int, default=200)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_prune)

    args = parser.parse_args(list(argv) if argv is not None else None)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
