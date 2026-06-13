#!/usr/bin/env python3
"""CLI-based Task Closeout 도구.

LLM이 마크다운 파일을 In-place로 직접 수정하다가 다른 Task의 Conclusion을 덮어쓰는
현상을 원천 차단하기 위해, 이 스크립트를 통해 기계적으로 상태를 업데이트합니다.

사용법:
    uv run python scripts/plan_loop/plan_task_close.py \
        --plan docs/plans/PLAN_xxx.md \
        --task XXX-001 \
        --conclusion "[PASS] 버튼 UI 수정 및 Verify 통과."
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

PLAN_TASK_CLOSE_MARKER = "[closed-by:plan-task-close]"


def _with_closeout_marker(conclusion: str) -> str:
    text = conclusion.strip()
    if PLAN_TASK_CLOSE_MARKER in text:
        return text
    return f"{text} {PLAN_TASK_CLOSE_MARKER}"


def _validate_conclusion_before_close(conclusion: str) -> list[str]:
    """close 시점 Conclusion 품질 사전 검증 (plan-lint 규칙 SSOT 재사용).

    검증 항목:
    1. 줄바꿈 거부 (단일 라인 Conclusion만 허용)
    2. placeholder 거부 ([TBD], 완료 시 기입 등)
    3. thin pattern 거부 ([PASS] 단독, 완료 단독 등)
    4. 최소 25자 미만 거부
    """
    issues: list[str] = []
    if "\n" in conclusion or "\r" in conclusion:
        issues.append(
            "Conclusion에 줄바꿈이 포함되어 있습니다. 한 줄로 입력하세요."
        )
        return issues

    import sys as _sys

    _repo = str(_REPO_ROOT)
    if _repo not in _sys.path:
        _sys.path.insert(0, _repo)
    from scripts.plan_loop.plan_lint.quality import _lint_conclusion_quality
    from scripts.plan_loop.plan_lint.verification import _is_conclusion_placeholder

    if _is_conclusion_placeholder(conclusion):
        issues.append(f"Conclusion이 placeholder입니다: {conclusion}")
    issues.extend(
        _lint_conclusion_quality(0, "done", conclusion, require_closeout_marker=False)
    )
    return issues


def _count_matching_task_blocks(text: str, task_id: str) -> int:
    from scripts.plan_loop.plan_lint.shared import _parse_fields, _split_task_blocks

    needle = task_id.strip("[]")
    count = 0
    for block in _split_task_blocks(text):
        fields = _parse_fields(block)
        block_task_id = (fields.get("Task-ID") or "").strip("[]")
        if block_task_id == needle:
            count += 1
    return count


def _find_task_block_span(text: str, task_id: str) -> tuple[int, int]:
    from scripts.plan_loop.plan_lint.shared import TASK_HEADING_RE, _parse_fields

    needle = task_id.strip("[]")
    matches = list(TASK_HEADING_RE.finditer(text))
    hits: list[tuple[int, int]] = []

    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block_text = text[start:end]
        fields = _parse_fields(block_text)
        block_task_id = (fields.get("Task-ID") or "").strip("[]")
        if block_task_id == needle:
            hits.append((start, end))

    if not hits:
        print(f"❌ '{task_id}' 태스크를 Blueprint에서 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)
    if len(hits) > 1:
        print(
            f"❌ '{task_id}' Task-ID가 Blueprint에 {len(hits)}회 중복됩니다. "
            "중복을 수동으로 정리한 뒤 다시 close 하세요.",
            file=sys.stderr,
        )
        sys.exit(1)
    return hits[0]


def _patch_task_block(block_text: str, conclusion: str) -> tuple[str, bool, bool]:
    lines = block_text.splitlines()
    status_updated = False
    conclusion_updated = False

    for i, line in enumerate(lines):
        if not status_updated and re.match(
            r"^(\s*-\s*Status:\s*)(todo|running|blocked|failed)(\s*)$",
            line,
            re.IGNORECASE,
        ):
            lines[i] = re.sub(
                r"^(.*?Status:\s*)(todo|running|blocked|failed)(.*)$",
                r"\g<1>done\g<3>",
                line,
                flags=re.IGNORECASE,
            )
            status_updated = True
        elif not status_updated and re.search(
            r"\|\s*Status:\s*(todo|running|blocked|failed)\s*\|", line, re.IGNORECASE
        ):
            lines[i] = re.sub(
                r"(Status:\s*)(todo|running|blocked|failed)",
                r"\g<1>done",
                line,
                flags=re.IGNORECASE,
            )
            status_updated = True

        if not conclusion_updated and re.match(r"^\s*-\s*\*\*Conclusion\*\*:.*", line):
            indent_match = re.match(r"^(\s*)", line)
            indent = indent_match.group(1) if indent_match else ""
            lines[i] = f"{indent}- **Conclusion**: {_with_closeout_marker(conclusion)}"
            conclusion_updated = True

    return "\n".join(lines), status_updated, conclusion_updated


def close_task_in_markdown(plan_path: Path, task_id: str, conclusion: str) -> None:
    issues = _validate_conclusion_before_close(conclusion)
    if issues:
        print("❌ Conclusion 품질 검증 실패:", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        print(
            "\n💡 Conclusion은 최소 25자 이상이며 구체적 내용을 포함해야 합니다."
            " 예: '[PASS] 청구 항목 저장 시 단가 기록 ID 연결. billing_service 수정. Verify pytest exit 0.'",
            file=sys.stderr,
        )
        sys.exit(1)

    if not plan_path.exists():
        print(f"❌ Blueprint 파일을 찾을 수 없습니다: {plan_path}", file=sys.stderr)
        sys.exit(1)

    text = plan_path.read_text(encoding="utf-8")

    match_count = _count_matching_task_blocks(text, task_id)
    if match_count == 0:
        print(f"❌ '{task_id}' 태스크를 Blueprint에서 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)
    if match_count > 1:
        print(
            f"❌ '{task_id}' Task-ID가 Blueprint에 {match_count}회 중복됩니다. "
            "중복을 수동으로 정리한 뒤 다시 close 하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    start, end = _find_task_block_span(text, task_id)
    block_text = text[start:end]

    from scripts.plan_loop.plan_lint.shared import EPIC_UNIT_TAG, FEATURE_UNIT_TAG, _task_unit_tag

    unit_tag = _task_unit_tag(block_text)
    if unit_tag in (EPIC_UNIT_TAG, FEATURE_UNIT_TAG):
        print(
            f"❌ '{task_id}' 태스크는 Epic/Feature 태그를 가지고 있어 직접 완료(close)할 수 없습니다. "
            "하위 플랜으로 쪼개주세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    new_block, status_updated, conclusion_updated = _patch_task_block(block_text, conclusion)

    if not status_updated or not conclusion_updated:
        missing: list[str] = []
        if not status_updated:
            missing.append("Status")
        if not conclusion_updated:
            missing.append("Conclusion")
        print(
            f"❌ '{task_id}' 태스크 블록 내에서 {', '.join(missing)} 필드를 갱신하지 못했습니다. "
            "파일은 변경하지 않았습니다.",
            file=sys.stderr,
        )
        sys.exit(1)

    new_text = text[:start] + new_block + text[end:]
    plan_path.write_text(new_text, encoding="utf-8")

    print(f"✅ {plan_path.name} 파일 내 '{task_id}' 태스크 갱신 완료.")
    print("  - Status: done 변경")
    print(f"  - Conclusion: {conclusion}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Blueprint Task 상태를 안전하게 Close(완료) 처리합니다.")
    parser.add_argument("--plan", required=True, help="대상 Blueprint 마크다운 파일 경로")
    parser.add_argument("--task", required=True, help="완료 처리할 태스크 ID (예: XXX-001)")
    parser.add_argument("--conclusion", required=True, help="기입할 Conclusion 텍스트")
    parser.add_argument(
        "--verify-cmd",
        default=None,
        help="선택: close 전에 실행할 Verify 셸 명령 (exit 0 이어야 함)",
    )

    args = parser.parse_args()

    plan_arg = str(args.plan)
    if plan_arg.startswith("plan="):
        plan_arg = plan_arg.split("=", 1)[1]

    task_arg = str(args.task)
    if task_arg.startswith("task="):
        task_arg = task_arg.split("=", 1)[1]

    conclusion_arg = str(args.conclusion)
    if conclusion_arg.startswith("conclusion="):
        conclusion_arg = conclusion_arg.split("=", 1)[1]

    plan_path = Path(plan_arg)
    if not plan_path.is_absolute():
        plan_path = _REPO_ROOT / plan_path

    if args.verify_cmd:
        print(f"🔍 Verify 실행: {args.verify_cmd}")
        verify_result = subprocess.run(
            args.verify_cmd,
            shell=True,
            cwd=str(_REPO_ROOT),
            check=False,
        )
        if verify_result.returncode != 0:
            print(
                f"❌ Verify 실패 (exit {verify_result.returncode}) — Task close 중단",
                file=sys.stderr,
            )
            sys.exit(verify_result.returncode)

    close_task_in_markdown(plan_path, task_arg, conclusion_arg)


if __name__ == "__main__":
    main()
