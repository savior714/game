#!/usr/bin/env python3
"""CLI argument parsing and subcommand dispatch for archive_plans."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.plan_archive import (
    cmd_archive,
    cmd_check,
    cmd_guard_deleted,
    cmd_repair,
    cmd_sweep,
    cmd_unarchive,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="docs/plans 아카이브 이동 및 참조 일괄 갱신")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="끊긴 plans 링크 검사")

    p_ar = sub.add_parser("archive", help="plans -> plans/archive/<분류>/ 이동 + 참조 갱신")
    p_ar.add_argument(
        "names",
        nargs="+",
        help="플랜 파일명 (예: PLAN_ddd_structure_reorg.md)",
    )
    p_ar.add_argument("--dry-run", action="store_true")
    p_ar.add_argument(
        "--skip-unified-sync",
        action="store_true",
        help="아카이브 후 just sync --check(코드 락·스펙 정합) 생략. 기본은 이동·참조 갱신 후 반드시 실행.",
    )

    p_un = sub.add_parser("unarchive", help="archive -> plans 루트 복귀 + 참조 역갱신")
    p_un.add_argument("names", nargs="+", help="플랜 파일명")
    p_un.add_argument("--dry-run", action="store_true")

    p_sw = sub.add_parser("sweep", help="archive 루트에 남은 *.md 재분류")
    p_sw.add_argument("--dry-run", action="store_true")

    p_rp = sub.add_parser("repair", help="끊긴 docs/plans/*.md 참조 일괄 치환")
    p_rp.add_argument("--dry-run", action="store_true")

    sub.add_parser("guard-deleted", help="추적 archive 플랜 워킹트리 삭제 감지")

    return ap


def dispatch(args: argparse.Namespace) -> int:
    # Strip key=value prefix and path prefix from names (justfile passes plan=docs/plans/PLAN_xxx.md)
    if hasattr(args, 'names') and args.names:
        from pathlib import Path
        cleaned = []
        for n in args.names:
            # Strip key=value prefix
            if '=' in n:
                n = n.split('=', 1)[-1]
            # Keep only basename
            n = Path(n).name
            cleaned.append(n)
        args.names = cleaned

    if args.cmd == "check":
        return cmd_check()
    if args.cmd == "repair":
        return cmd_repair(dry_run=args.dry_run)
    if args.cmd == "guard-deleted":
        return cmd_guard_deleted()
    if args.cmd == "archive":
        return cmd_archive(
            args.names,
            dry_run=args.dry_run,
            skip_unified_sync=args.skip_unified_sync,
        )
    if args.cmd == "unarchive":
        return cmd_unarchive(args.names, dry_run=args.dry_run)
    if args.cmd == "sweep":
        return cmd_sweep(dry_run=args.dry_run)
    return 1


def main() -> int:
    ap = build_parser()
    args = ap.parse_args()
    return dispatch(args)
