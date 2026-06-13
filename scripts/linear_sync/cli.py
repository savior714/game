#!/usr/bin/env python3
"""CLI entry point for the Blueprint-Linear Sync Engine (LIS-007).

Blueprint 내의 Linear-Issue 태그를 파싱하고 상태/댓글을 자동으로 동기화하는
CLI 엔트리 포인트입니다.

실제 `TEM-숫자` ID가 하나도 없는 Major 플랜이면, 푸시 모드에서 API 키가 있을 때
`issue_factory.ensure_plan_linear_issue(..., sync=False)`로 이슈를 만들고 Blueprint를 패치한 뒤
아래 루프에서 상태·댓글을 반영한다. 생성 전 `searchIssues`로 동일 Blueprint 이슈가 있으면 패치만 수행(중복 생성 방지).
그 외 신규 이슈는 Linear UI 또는 `create_*` 스크립트로 만든 뒤 `Linear-Issue:`를 넣는다.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from pathlib import Path

from scripts.linear_sync.env import load_env
from scripts.linear_sync.env import validate_api_key as _validate_api_key
from scripts.linear_sync.lib.plan_metadata import (
    is_linear_placeholder,
    needs_linear_issue_creation,
    parse_doc_meta,
)
from scripts.linear_sync.sync_operations import SyncEngine

_INFO = "\u2139\ufe0f"


class BackupCleanup:
    """Track .bak files created during sync and clean them up on exit."""
    
    def __init__(self):
        self.bak_files = []
    
    def track(self, bak_path: Path):
        self.bak_files.append(bak_path)
    
    def cleanup(self):
        for bak_path in self.bak_files:
            try:
                if bak_path.exists():
                    bak_path.unlink()
                    print(f"  🧹 Cleanup: {bak_path.name}", file=sys.stderr)
            except OSError:
                pass
    
    def remove(self, bak_path: Path):
        if bak_path in self.bak_files:
            self.bak_files.remove(bak_path)


cleanup_handler = BackupCleanup()


def _signal_handler(signum, frame):
    """Clean up .bak files on interrupt."""
    print(f"\n⚠️  Interrupted (signal {signum}), cleaning up .bak files...", file=sys.stderr)
    cleanup_handler.cleanup()
    sys.exit(128 + signum)


# Register signal handlers for graceful cleanup
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def _process_plan(
    engine: SyncEngine,
    plan: Path,
    args: argparse.Namespace,
) -> bool:
    """Process a single blueprint plan file.

    Returns True if the push for this plan failed (for --strict mode).
    """
    engine.plan_path = plan
    engine.push_failed = False

    if not args.pull and engine.client and not engine.dry_run:
        try:
            from scripts.linear_sync.lib.issue_factory import ensure_plan_linear_issue  # noqa: PLC0415

            pre = plan.read_text(encoding="utf-8")
            if needs_linear_issue_creation(pre, plan):
                print(
                    "  🌱 Major blueprint에 실제 Linear 이슈 ID 없음 — "
                    "ensure_plan_linear_issue(sync=False) 실행"
                )
                # Retry up to 3 times with 2 second delays
                res = None
                for attempt in range(3):
                    res = ensure_plan_linear_issue(plan, dry_run=False, sync=False)
                    if res.created and res.identifier:
                        break
                    time.sleep(2)
                
                if res.created and res.identifier:
                    print(f"     ✅ 생성·패치: {res.identifier}")
                elif res and res.message:
                    print(f"     {_INFO}  {res.message}")
                post = plan.read_text(encoding="utf-8")
                if needs_linear_issue_creation(post, plan):
                    engine.push_failed = True
                    print(
                        "  ❌ ensure 후에도 실제 TEM-NN ID가 없습니다 "
                        "(키·API·플랜 분류·plan_lint 계약 확인).",
                        file=sys.stderr,
                    )
        except Exception as exc:
            engine.push_failed = True
            print(f"  ❌ ensure_plan_linear_issue 실패: {exc}", file=sys.stderr)

    plan_content = plan.read_text(encoding="utf-8")
    doc_meta_labels = parse_doc_meta(plan_content, plan).labels

    tasks = engine.parse_tasks(plan)
    for task in tasks:
        linear_id = task.get("linear_id")
        if not linear_id or is_linear_placeholder(linear_id):
            continue
        if args.pull:
            engine.pull_sync_task(task)
        else:
            engine.sync_task(task, doc_meta_labels=doc_meta_labels)

    if args.refresh_description and not args.pull and engine.client:
        from scripts.linear_sync.lib.issue_description import (  # noqa: PLC0415
            refresh_issue_description_for_plan,
        )

        if not is_linear_placeholder(
            parse_doc_meta(plan_content, plan).linear_issue or ""
        ) and not refresh_issue_description_for_plan(
            engine.client, plan, dry_run=engine.dry_run
        ):
            return True

    bak_path = plan.with_suffix(plan.suffix + ".bak")
    if bak_path.exists():
        cleanup_handler.remove(bak_path)
        try:
            bak_path.unlink()
            print(f"  🧹 Removed backup: {bak_path.name}")
        except OSError:
            pass

    return engine.push_failed


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="Blueprint-Linear Sync Engine")
    parser.add_argument("--plan", type=Path, nargs="+", help="Target blueprint file(s)")
    parser.add_argument("--dry-run", action="store_true", help="Do not perform actual updates")
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Pull Linear state changes to local blueprint (reverse sync)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Push mode: exit non-zero if LINEAR_API_KEY is missing (when not --dry-run) "
        "or if any Linear status update fails. Used by archive_plans.py before moving files.",
    )
    parser.add_argument(
        "--refresh-description",
        action="store_true",
        help="After task sync, rebuild Linear issue description from Blueprint (team-facing).",
    )
    args = parser.parse_args()

    api_key = (os.environ.get("LINEAR_API_KEY") or "").strip()
    client = _validate_api_key(api_key) if api_key else None

    dry_run = bool(args.dry_run or args.pull)

    if args.strict and not args.pull and not args.dry_run and not client:
        print(
            "❌ --strict: LINEAR_API_KEY가 없어 Linear에 반영할 수 없습니다. "
            "루트 `.env`에 키를 두거나 오프라인이면 "
            "`archive_plans.py archive --skip-linear-sync …`를 사용하세요.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    if client:
        mode = "dry-run (읽기·시뮬레이션)" if dry_run else "live (GraphQL 반영)"
        print(f"{_INFO}  LINEAR_API_KEY 감지 — Linear API 사용 ({mode}).\n")
    else:
        print(
            f"{_INFO}  LINEAR_API_KEY 없음 — Blueprint 파싱·시뮬레이션만 수행합니다.\n"
            "실제 Linear 반영: 루트 `.env`에 키를 두거나(권장) CI/셸에서 export한 뒤 재실행하세요.\n"
            "오판 방지: 셸에 export가 없어도 `.env`만 있으면 load_env()가 주입합니다 — "
            '표·체크리스트는 .agents/workflows/linear.md 의 "실행 절차" 아래 "API 키·.env SSOT" 절.\n'
        )

    engine = SyncEngine(client=client, dry_run=dry_run)

    plans = args.plan if args.plan else list(Path("docs/plans").glob("PLAN_*.md"))

    exit_code = 0
    is_first_plan = True
    for plan in plans:
        if plan.name == "README.md":
            continue
        if not is_first_plan:
            time.sleep(2.1)
        is_first_plan = False
        print(f"\n📂 Processing {plan.name}")

        push_failed = _process_plan(engine, plan, args)

        if args.strict and not args.pull and push_failed:
            exit_code = 1

    # Final cleanup of any remaining .bak files
    cleanup_handler.cleanup()

    if exit_code:
        print(
            "\n❌ --strict: 하나 이상의 Linear 상태 반영에 실패했습니다. "
            "로그를 확인한 뒤 재실행하세요.",
            file=sys.stderr,
        )
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
