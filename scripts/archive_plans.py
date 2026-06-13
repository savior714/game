#!/usr/bin/env python3
"""
완료된 docs/plans/*.md 를 docs/plans/archive/<분류>/ 로 이동하고,
저장소 내 텍스트 참조를 일괄 갱신한다.

Usage:
  python3 scripts/archive_plans.py check
  python3 scripts/archive_plans.py archive PLAN.md [PLAN2.md ...]
  python3 scripts/archive_plans.py archive --dry-run PLAN.md

  python3 scripts/archive_plans.py archive --skip-unified-sync PLAN.md
  python3 scripts/archive_plans.py archive --skip-linear-sync PLAN.md
  python3 scripts/archive_plans.py unarchive PLAN.md   # archive -> plans root
  python3 scripts/archive_plans.py sweep [--dry-run]   # archive 루트에 남은 *.md 재분류
  python3 scripts/archive_plans.py repair [--dry-run] # 끊긴 docs/plans/*.md 참조를 SSOT 경로로 일괄 치환
  python3 scripts/archive_plans.py guard-deleted       # 추적 중인 archive 파일 워킹트리 삭제 감지

제외: .git, node_modules, __pycache__, .venv, dist, build, .next
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from scripts.archive_plans_cli import main  # noqa: E402
from scripts.plan_archive import (  # noqa: E402
    PLAN_BASENAME_ALIASES,
    PLAN_REF_PATTERN,
    canonical_plan_basename,
    cmd_archive,
    cmd_check,
    cmd_guard_deleted,
    cmd_repair,
    cmd_sweep,
    cmd_unarchive,
    plan_reference_exists,
    resolve_plan_reference,
    rewrite_to_archive,
    run_unified_sync_check,
)

__all__ = [
    "PLAN_BASENAME_ALIASES",
    "PLAN_REF_PATTERN",
    "canonical_plan_basename",
    "cmd_archive",
    "cmd_check",
    "cmd_guard_deleted",
    "cmd_repair",
    "cmd_sweep",
    "cmd_unarchive",
    "main",
    "plan_reference_exists",
    "resolve_plan_reference",
    "rewrite_to_archive",
    "run_unified_sync_check",
]


if __name__ == "__main__":
    raise SystemExit(main())
