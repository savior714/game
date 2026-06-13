#!/usr/bin/env python3
"""Blueprint Task 역방향 리셋 적용 — Status·Conclusion 되돌리기 및 Audit append."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from scripts.plan_loop.plan_reset_gate import _CSF_CONCLUSION, _strip_arg

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_AUDIT_HEADING = "## Task Reset Audit"


def _find_task_start(lines: list[str], task_id: str) -> int:
    task_id_pattern = re.compile(rf"Task-ID:\s*\[?{re.escape(task_id)}\]?")
    for i, line in enumerate(lines):
        if task_id_pattern.search(line):
            return i
    header_pattern = re.compile(rf"^#{{3,5}}\s+Task.*{re.escape(task_id)}")
    for i, line in enumerate(lines):
        if header_pattern.search(line):
            return i
    print(f"❌ '{task_id}' 태스크를 Blueprint에서 찾을 수 없습니다.", file=sys.stderr)
    sys.exit(1)


def reset_task_in_markdown(
    plan_path: Path,
    task_id: str,
    *,
    sha: str,
    approval: str,
) -> None:
    text = plan_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    target_idx = _find_task_start(lines, task_id.strip("[]"))

    status_updated = False
    conclusion_updated = False

    for i in range(target_idx, min(target_idx + 30, len(lines))):
        if i > target_idx and re.match(r"^#{2,5}\s+", lines[i]):
            break

        if not status_updated and re.match(
            r"^(\s*-\s*Status:\s*)(done|running|blocked|failed)(\s*)$",
            lines[i],
            re.IGNORECASE,
        ):
            lines[i] = re.sub(
                r"^(.*?Status:\s*)(done|running|blocked|failed)(.*)$",
                r"\g<1>todo\g<3>",
                lines[i],
                flags=re.IGNORECASE,
            )
            status_updated = True
        elif not status_updated and re.search(
            r"\|\s*Status:\s*(done|running|blocked|failed)\s*\|",
            lines[i],
            re.IGNORECASE,
        ):
            lines[i] = re.sub(
                r"(Status:\s*)(done|running|blocked|failed)",
                r"\g<1>todo",
                lines[i],
                flags=re.IGNORECASE,
            )
            status_updated = True

        if not conclusion_updated and re.match(r"^\s*-\s*\*\*Conclusion\*\*:.*", lines[i]):
            indent = re.match(r"^(\s*)", lines[i]).group(1)  # type: ignore[union-attr]
            lines[i] = f"{indent}- **Conclusion**: {_CSF_CONCLUSION}"
            conclusion_updated = True

    if not status_updated and not conclusion_updated:
        print(
            f"❌ '{task_id}' 태스크 블록에서 되돌릴 Status/Conclusion을 찾지 못했습니다.",
            file=sys.stderr,
        )
        sys.exit(1)

    updated_text = "\n".join(lines) + "\n"
    updated_text = _append_audit_row(updated_text, task_id, sha, approval)
    plan_path.write_text(updated_text, encoding="utf-8")

    print(f"✅ {plan_path.name} — '{task_id}' 역방향 리셋 적용")
    if status_updated:
        print("  - Status: todo")
    if conclusion_updated:
        print(f"  - Conclusion: {_CSF_CONCLUSION}")
    print("  - Task Reset Audit: 1행 append")


def _append_audit_row(text: str, task_id: str, sha: str, approval: str) -> str:
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe_approval = approval.replace("|", "\\|").replace("\n", " ")
    row = f"| {ts} | {task_id} | `{sha[:12]}` | {safe_approval} |"

    if _AUDIT_HEADING in text:
        lines = text.splitlines()
        insert_at = len(lines)
        for i, line in enumerate(lines):
            if line.strip() == _AUDIT_HEADING:
                j = i + 1
                while j < len(lines) and not lines[j].startswith("|"):
                    j += 1
                while j < len(lines) and (lines[j].startswith("|") or lines[j].strip() == ""):
                    if lines[j].startswith("|") and not lines[j].startswith("| :"):
                        insert_at = j + 1
                    j += 1
                break
        lines.insert(insert_at, row)
        return "\n".join(lines) + "\n"

    anchor = "## 🔁 Conclusion & Summary"
    section = (
        f"\n{_AUDIT_HEADING}\n\n"
        "| Timestamp (UTC) | Task-ID | Git SHA | Approval |\n"
        "| :--- | :--- | :--- | :--- |\n"
        f"{row}\n"
    )
    if anchor in text:
        return text.replace(anchor, section + anchor, 1)
    return text.rstrip() + section


def main() -> None:
    parser = argparse.ArgumentParser(description="Blueprint Task 역방향 리셋 적용")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--approval", required=True)
    args = parser.parse_args()

    plan_path = Path(_strip_arg(str(args.plan), "plan"))
    if not plan_path.is_absolute():
        plan_path = _REPO_ROOT / plan_path

    reset_task_in_markdown(
        plan_path,
        _strip_arg(str(args.task), "task"),
        sha=_strip_arg(str(args.sha), "sha"),
        approval=_strip_arg(str(args.approval), "approval"),
    )


if __name__ == "__main__":
    main()
