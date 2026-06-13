#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Language: ko

"""session_end_gate — 세션 종료 게이트 오케스트레이터.

lint-turn-end tail 에서 다음 세 단계를 순차 실행한다.
  1. route-gate-check (변경된 파일 목록)
  2. plan-lint        (git diff 에 등장한 PLAN 파일)
  3. compliance_guard

어느 단계라도 실패하면 exit code 1, stderr 에 실패 단계명 출력.
"""

from __future__ import annotations

import os
import subprocess
import sys


def _run(cmd: list[str], label: str) -> int:
    """subprocess.run 을 호출하고 exit code 를 반환한다."""
    print(f"🚀 [{label}] {cmd}")  # noqa: T201
    result = subprocess.run(cmd, check=False)
    if result.returncode == 0:
        print(f"✅ [{label}] passed")
    else:
        print(f"❌ [{label}] failed (exit {result.returncode})", file=sys.stderr)
    return result.returncode


def _get_touched_plan_files() -> list[str]:
    """git diff HEAD 에 등장한 docs/plans/PLAN_*.md 파일 목록을 반환한다.

    archive 하위 경로는 제외한다.
    """
    try:
        diff_output = subprocess.check_output(
            ["git", "diff", "HEAD", "--name-only", "--", "docs/plans/"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="ignore")
    except Exception:
        return []

    files: list[str] = []
    for line in diff_output.splitlines():
        line = line.strip()
        if line and "/archive/" not in line and line.startswith("docs/plans/PLAN_"):
            files.append(line)
    return files


def run_gate() -> int:
    """세 단계를 순차 실행 — 첫 실패 시 1 을 반환하고 종료한다."""
    # Phase 1: route-gate-check on changed files
    try:
        changed = subprocess.check_output(
            ["git", "diff", "HEAD", "--name-only"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="ignore").splitlines()
    except Exception:
        changed = []

    if changed:
        rc = _run(["just", "route-gate-check"] + changed, "route")
        if rc != 0:
            return rc

    # Phase 2: plan-lint on touched PLAN files
    plan_files = _get_touched_plan_files()
    if plan_files:
        for pf in plan_files:
            rc = _run(["just", "plan-lint", pf], "plan-lint")
            if rc != 0:
                return rc

    # Phase 3: compliance_guard
    script = os.path.join(os.path.dirname(__file__), "compliance_guard.py")
    rc = _run(["uv", "run", "python", script], "compliance")
    if rc != 0:
        return rc

    print("🎉 All gate checks passed!")
    return 0


def main() -> None:
    sys.exit(run_gate())


if __name__ == "__main__":
    main()
