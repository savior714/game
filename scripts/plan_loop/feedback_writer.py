#!/usr/bin/env python3
"""Feedback writer for plan execution writeback loop.

Updates plan file task status, appends conclusions, and generates
JSONL execution trails under docs/reports/plan-loop/.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.plan_loop.plan_lint import (
    EXECUTOR_REQUIRED_FIELDS,
    _parse_fields,
    _split_task_blocks,
)

REPORT_DIR = Path("docs/reports/plan-loop")


@dataclass
class FeedbackEntry:
    """Machine-readable feedback entry for writeback."""

    task_id: str
    previous_status: str
    new_status: str
    conclusion: str | None = None
    failure_reason: str | None = None
    blocked_by: str | None = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "conclusion": self.conclusion,
            "failure_reason": self.failure_reason,
            "blocked_by": self.blocked_by,
            "timestamp": self.timestamp,
        }


class FeedbackWriter:
    """Writes feedback back to plan files and generates JSONL logs."""

    def __init__(self, plan_path: Path) -> None:
        self.plan_path = plan_path
        self._original_text = plan_path.read_text(encoding="utf-8")
        self._tasks: dict[str, dict] = {}
        self._feedback_entries: list[FeedbackEntry] = []
        self._parse_tasks()

    def _parse_tasks(self) -> None:
        blocks = _split_task_blocks(self._original_text)
        for block in blocks:
            fields = _parse_fields(block)
            if not all(fields.get(f) for f in EXECUTOR_REQUIRED_FIELDS):
                continue
            self._tasks[fields["Task-ID"]] = {
                "fields": fields,
                "block": block,
            }

    def mark_done(self, task_id: str, conclusion: str | None = None) -> None:
        """Mark a task as done with conclusion."""
        if task_id not in self._tasks:
            raise ValueError(f"Task-ID {task_id} not found in plan")
        entry = FeedbackEntry(
            task_id=task_id,
            previous_status=self._tasks[task_id]["fields"]["Status"],
            new_status="done",
            conclusion=conclusion,
        )
        self._feedback_entries.append(entry)

    def mark_failed(self, task_id: str, reason: str = "") -> None:
        """Mark a task as failed with reason."""
        if task_id not in self._tasks:
            raise ValueError(f"Task-ID {task_id} not found in plan")
        entry = FeedbackEntry(
            task_id=task_id,
            previous_status=self._tasks[task_id]["fields"]["Status"],
            new_status="failed",
            failure_reason=reason,
        )
        self._feedback_entries.append(entry)

    def mark_blocked(self, task_id: str, blocked_by: str, action: str = "") -> None:
        """Mark a task as blocked with owner/action."""
        if task_id not in self._tasks:
            raise ValueError(f"Task-ID {task_id} not found in plan")
        entry = FeedbackEntry(
            task_id=task_id,
            previous_status=self._tasks[task_id]["fields"]["Status"],
            new_status="blocked",
            blocked_by=blocked_by,
            conclusion=action,
        )
        self._feedback_entries.append(entry)

    def apply_feedback(self) -> str:
        """Apply all feedback entries to the plan text and return updated content."""
        updated_text = self._original_text

        # Process in reverse order to preserve line offsets
        for entry in reversed(self._feedback_entries):
            task_data = self._tasks.get(entry.task_id)
            if not task_data:
                continue

            old_block = task_data["block"]
            fields = task_data["fields"]
            block = old_block

            # Replace Status line
            old_status_line = f"- Status: {fields['Status']}"
            new_status_line = f"- Status: {entry.new_status}"
            block = block.replace(old_status_line, new_status_line, 1)

            # Add/Update Conclusion
            if entry.conclusion is not None:
                existing_conclusion = self._find_field_line(block, "Conclusion")
                if existing_conclusion:
                    block = block.replace(
                        existing_conclusion,
                        f"- Conclusion: {entry.conclusion}",
                        1,
                    )
                else:
                    dep_line = self._find_field_line(block, "Dependency")
                    if dep_line:
                        block = block.replace(
                            dep_line,
                            f"- Conclusion: {entry.conclusion}\n{dep_line}",
                            1,
                        )

            # Add/Update FailureReason
            if entry.failure_reason:
                existing_fr = self._find_field_line(block, "FailureReason")
                if existing_fr:
                    block = block.replace(
                        existing_fr,
                        f"- FailureReason: {entry.failure_reason}",
                        1,
                    )
                else:
                    # Insert before Dependency (after Conclusion if present)
                    target_line = self._find_field_line(block, "Conclusion")
                    if not target_line:
                        target_line = self._find_field_line(block, "Dependency")
                    if target_line:
                        block = block.replace(
                            target_line,
                            f"- FailureReason: {entry.failure_reason}\n{target_line}",
                            1,
                        )

            # Add/Update BlockedBy
            if entry.blocked_by:
                existing_bb = self._find_field_line(block, "BlockedBy")
                if existing_bb:
                    block = block.replace(
                        existing_bb,
                        f"- BlockedBy: {entry.blocked_by}",
                        1,
                    )
                else:
                    # Insert before Dependency (after FailureReason if present)
                    target_line = self._find_field_line(block, "FailureReason")
                    if not target_line:
                        target_line = self._find_field_line(block, "Dependency")
                    if target_line:
                        block = block.replace(
                            target_line,
                            f"- BlockedBy: {entry.blocked_by}\n{target_line}",
                            1,
                        )

            # Replace old block with updated block in full text
            if old_block in updated_text:
                updated_text = updated_text.replace(old_block, block, 1)

        return updated_text

    def _find_field_line(self, block: str, field_name: str) -> str | None:
        """Find a specific field line in a task block."""
        for line in block.splitlines():
            if line.strip().startswith(f"- {field_name}:"):
                return line
        return None

    def write_plan(self, updated_text: str | None = None) -> None:
        """Write updated plan back to file."""
        text = updated_text or self.apply_feedback()
        self.plan_path.write_text(text, encoding="utf-8")

    def write_jsonl_log(self) -> Path:
        """Write feedback entries as JSONL to report directory."""
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        log_file = REPORT_DIR / "feedback.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            for entry in self._feedback_entries:
                f.write(json.dumps(entry.to_dict()) + "\n")
        return log_file

    def generate_summary(self) -> dict:
        """Generate a summary of feedback entries."""
        done_count = sum(1 for e in self._feedback_entries if e.new_status == "done")
        failed_count = sum(1 for e in self._feedback_entries if e.new_status == "failed")
        blocked_count = sum(1 for e in self._feedback_entries if e.new_status == "blocked")

        return {
            "total": len(self._feedback_entries),
            "done": done_count,
            "failed": failed_count,
            "blocked": blocked_count,
            "entries": [e.to_dict() for e in self._feedback_entries],
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Write feedback back to plan files."
    )
    parser.add_argument(
        "plan_file",
        type=Path,
        help="Path to plan markdown file",
    )
    parser.add_argument(
        "--task-id",
        required=True,
        help="Task-ID to update",
    )
    parser.add_argument(
        "--action",
        choices=["done", "failed", "blocked"],
        required=True,
        help="Feedback action to apply",
    )
    parser.add_argument(
        "--reason",
        default="",
        help="Reason for failure or conclusion for done",
    )
    parser.add_argument(
        "--blocked-by",
        default="",
        help="Task-ID or owner that blocks this task",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print updated plan without writing",
    )
    args = parser.parse_args()

    writer = FeedbackWriter(args.plan_file)

    if args.action == "done":
        writer.mark_done(args.task_id, conclusion=args.reason)
    elif args.action == "failed":
        writer.mark_failed(args.task_id, reason=args.reason)
    elif args.action == "blocked":
        writer.mark_blocked(
            args.task_id,
            blocked_by=args.blocked_by,
            action=args.reason,
        )

    updated_text = writer.apply_feedback()
    summary = writer.generate_summary()

    print(f"[FEEDBACK] Applied {summary['total']} entries:")
    print(f"  - done: {summary['done']}")
    print(f"  - failed: {summary['failed']}")
    print(f"  - blocked: {summary['blocked']}")

    if args.dry_run:
        print("\n[DRY-RUN] Updated plan content:")
        print(updated_text)
        return 0

    writer.write_plan(updated_text)
    log_file = writer.write_jsonl_log()
    print(f"\n[WRITEBACK] Plan updated: {args.plan_file}")
    print(f"[WRITEBACK] JSONL log: {log_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
