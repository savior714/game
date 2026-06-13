#!/usr/bin/env python3
"""Blueprint Task 역방향 리셋 게이트 — 승인·git SHA·Verify 재실행 검증."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.plan_loop.plan_lint.shared import _parse_fields, _split_task_blocks

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MIN_APPROVAL_LEN = 10
_CSF_CONCLUSION = "[판정 — 비개발자용 요약. 검증 결과]"


def _strip_arg(value: str, prefix: str) -> str:
    if value.startswith(f"{prefix}="):
        return value.split("=", 1)[1]
    return value


def _normalize_verify_cmd(verify: str) -> str:
    cmd = verify.strip()
    if cmd.startswith("`") and cmd.endswith("`"):
        cmd = cmd[1:-1].strip()
    return cmd


def _find_task_block(plan_text: str, task_id: str) -> str:
    needle = task_id.strip("[]")
    for block in _split_task_blocks(plan_text):
        fields = _parse_fields(block)
        block_task_id = (fields.get("Task-ID") or "").strip("[]")
        if block_task_id == needle or needle in block:
            return block
    print(f"❌ '{task_id}' 태스크를 Blueprint에서 찾을 수 없습니다.", file=sys.stderr)
    sys.exit(1)


def extract_verify_command(plan_path: Path, task_id: str) -> str:
    plan_text = plan_path.read_text(encoding="utf-8")
    block = _find_task_block(plan_text, task_id)
    fields = _parse_fields(block)
    verify = (fields.get("Verify") or "").strip()
    if not verify:
        print(f"❌ '{task_id}' Task 블록에 Verify 필드가 없습니다.", file=sys.stderr)
        sys.exit(1)
    return _normalize_verify_cmd(verify)


def validate_approval(approval: str) -> None:
    text = approval.strip()
    if len(text) < _MIN_APPROVAL_LEN:
        print(
            f"❌ 승인 문자열이 너무 짧습니다 (최소 {_MIN_APPROVAL_LEN}자).",
            file=sys.stderr,
        )
        sys.exit(1)


def validate_git_sha(sha: str) -> None:
    result = subprocess.run(  # noqa: S603,S607
        ["git", "rev-parse", "--verify", f"{sha}^{{commit}}"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"❌ git SHA를 확인할 수 없습니다: {sha}", file=sys.stderr)
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        sys.exit(1)


def run_verify_command(verify_cmd: str) -> None:
    print(f"🔍 Verify 실행: {verify_cmd}")
    result = subprocess.run(verify_cmd, shell=True, cwd=str(_REPO_ROOT), check=False)  # noqa: S602
    if result.returncode != 0:
        print(f"❌ Verify 실패 (exit {result.returncode})", file=sys.stderr)
        sys.exit(result.returncode or 1)
    print("✅ Verify 통과")


def run_reset_gate(
    *,
    plan_path: Path,
    task_id: str,
    sha: str,
    approval: str,
    skip_verify: bool = False,
) -> None:
    validate_approval(approval)
    validate_git_sha(sha)
    if not skip_verify:
        verify_cmd = extract_verify_command(plan_path, task_id)
        run_verify_command(verify_cmd)
    print(f"✅ plan-reset-gate 검증 통과 ({task_id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Blueprint Task 역방향 리셋 게이트")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--approval", required=True)
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="단위 테스트용: Verify 실행 생략",
    )
    args = parser.parse_args()

    plan_path = Path(_strip_arg(str(args.plan), "plan"))
    if not plan_path.is_absolute():
        plan_path = _REPO_ROOT / plan_path

    task_id = _strip_arg(str(args.task), "task")
    sha = _strip_arg(str(args.sha), "sha")
    approval = _strip_arg(str(args.approval), "approval")

    if not plan_path.exists():
        print(f"❌ Blueprint 파일을 찾을 수 없습니다: {plan_path}", file=sys.stderr)
        sys.exit(1)

    run_reset_gate(
        plan_path=plan_path,
        task_id=task_id,
        sha=sha,
        approval=approval,
        skip_verify=bool(args.skip_verify),
    )


if __name__ == "__main__":
    main()
