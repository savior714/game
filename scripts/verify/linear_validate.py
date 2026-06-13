#!/usr/bin/env python3
"""Linear-Issue 참조 유효성 검증 ().

모든 Blueprint 파일을 스캔해 Linear-Issue 로 참조된 ID 가
실제로 Linear 에 존재하는지 확인하고, 없으면 보고한다.

사용법:
    just linear-validate          # 전체 스캔
    just linear-validate --plan docs/examples/PLAN_xxx.md  # 단일 파일
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# Repo root: scripts/verify/ → parent의 parent = repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.linear_sync.sync_engine import LinearClient, load_env  # noqa: E402
from scripts.linear_sync.lib.plan_metadata import (  # noqa: E402
    collect_linear_ids_from_content,
    is_linear_placeholder,
)

LINEAR_PLANS_DIR = _REPO_ROOT / "docs" / "plans"
LINEAR_ID_RE = re.compile(r"TEM-\d+", re.IGNORECASE)


def validate_plan(plan_path: Path, client: LinearClient) -> list[str]:
    """단일 Blueprint 파일의 Linear-Issue 참조를 검증.

    Returns:
        발견된 문제 목록 (없으면 빈 리스트).
    """
    content = plan_path.read_text(encoding="utf-8")
    ids = collect_linear_ids_from_content(content)
    real_ids = {i for i in ids if not is_linear_placeholder(i)}

    problems = []
    for ident in sorted(real_ids):
        try:
            exists = client.issue_exists(ident)
        except Exception as exc:
            problems.append(f"  ⚠️  {plan_path.name}: {ident} — API error: {exc}")
            continue

        if not exists:
            problems.append(f"  ❌ {plan_path.name}: {ident} not found in Linear")

    return problems


def main():
    parser = argparse.ArgumentParser(description="Linear-Issue 참조 유효성 검증")
    parser.add_argument("--plan", type=Path, help="검증할 단일 Blueprint 파일")
    args = parser.parse_args()

    load_env()
    api_key = (os.environ.get("LINEAR_API_KEY") or "").strip()
    if not api_key:
        print("❌ LINEAR_API_KEY 가 없습니다. .env 에 키를 설정하세요.")
        sys.exit(2)

    client = LinearClient(api_key)

    if args.plan:
        # 단일 파일 모드
        if not args.plan.exists():
            print(f"❌ 파일 없음: {args.plan}")
            sys.exit(1)
        problems = validate_plan(args.plan, client)
        if problems:
            for p in problems:
                print(p)
            print(f"\n❌ {len(problems)}개 문제 발견")
            sys.exit(1)
        else:
            print(f"✅ {args.plan.name}: Linear-Issue 참조 모두 유효")
            sys.exit(0)

    # 전체 스캔 모드
    if not LINEAR_PLANS_DIR.exists():
        print(f"❌ plans 디렉토리 없음: {LINEAR_PLANS_DIR}")
        sys.exit(1)

    plan_files = sorted(LINEAR_PLANS_DIR.glob("PLAN_*.md"))
    if not plan_files:
        print(f"ℹ️  PLAN_*.md 파일 없음 ({LINEAR_PLANS_DIR})")
        sys.exit(0)

    all_problems: list[str] = []
    total_refs = 0

    for pf in plan_files:
        content = pf.read_text(encoding="utf-8")
        ids = collect_linear_ids_from_content(content)
        real_ids = {i for i in ids if not is_linear_placeholder(i)}
        total_refs += len(real_ids)

        problems = validate_plan(pf, client)
        all_problems.extend(problems)

    print(f"🔍 Scanning {len(plan_files)} plans, {total_refs} Linear-Issue references...")

    if all_problems:
        for p in all_problems:
            print(p)
        print(f"\n❌ {len(all_problems)}개 문제 발견 — plan-close 를 막습니다.")
        sys.exit(1)
    else:
        print(f"✅ All {total_refs} Linear-Issue references valid across {len(plan_files)} plans")
        sys.exit(0)


if __name__ == "__main__":
    main()
