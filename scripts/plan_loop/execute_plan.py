#!/usr/bin/env python3
"""Sequential plan executor with verification gate integration."""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.plan_loop.plan_lint import (
    EXECUTOR_REQUIRED_FIELDS,
    _parse_fields,
    _split_task_blocks,
    lint_plan_text,
)

VERIFY_RESULT_FILE = Path("artifacts/verify/verify-last-result.json")
_DEFAULT_REPORT_DIR = Path("docs/reports/plan-loop")


@dataclass
class TaskRecord:
    """Machine-readable representation of a plan task block."""

    task_id: str
    status: str
    target: str
    action: str
    verify: str
    writeback: str
    dependency: str
    retry_policy: str
    index: int = 0


@dataclass
class ExecutionLog:
    """Per-task execution log entry."""

    task_id: str
    step_index: int
    started_at: str
    finished_at: str | None = None
    exit_code: int | None = None
    verification_passed: bool | None = None
    error: str | None = None
    writeback_path: str | None = None


def _load_tasks_from_plan(plan_path: Path) -> list[TaskRecord]:
    text = plan_path.read_text(encoding="utf-8")
    blocks = _split_task_blocks(text)
    tasks: list[TaskRecord] = []
    for idx, block in enumerate(blocks, start=1):
        fields = _parse_fields(block)
        if not all(fields.get(f) for f in EXECUTOR_REQUIRED_FIELDS):
            continue
        tasks.append(
            TaskRecord(
                task_id=fields["Task-ID"],
                status=fields["Status"],
                target=fields["Target"],
                action=fields["Action"],
                verify=fields["Verify"],
                writeback=fields["Writeback"],
                dependency=fields["Dependency"],
                retry_policy=fields["RetryPolicy"],
                index=idx,
            )
        )
    return tasks


def _resolve_dependencies(tasks: list[TaskRecord]) -> dict[str, list[str]]:
    """Build adjacency map: task_id -> list of dependency task_ids."""
    id_map = {t.task_id: t for t in tasks}
    deps: dict[str, list[str]] = {}
    for t in tasks:
        dep_str = t.dependency.strip().lower()
        if dep_str == "none":
            deps[t.task_id] = []
        else:
            # Preserve original case of task IDs in dependencies
            deps[t.task_id] = [d.strip() for d in t.dependency.split(",") if d.strip()]
    return deps


def _topological_sort(tasks: list[TaskRecord]) -> list[TaskRecord]:
    """Return tasks in topological order by dependency."""
    id_map = {t.task_id: t for t in tasks}
    deps = _resolve_dependencies(tasks)
    visited: set[str] = set()
    order: list[TaskRecord] = []

    def _visit(task_id: str) -> None:
        if task_id in visited:
            return
        visited.add(task_id)
        for dep_id in deps.get(task_id, []):
            dep_task = id_map.get(dep_id)
            if dep_task and dep_task.status != "done":
                _visit(dep_id)
        task = id_map.get(task_id)
        if task:
            order.append(task)

    for t in tasks:
        _visit(t.task_id)
    return order


def _run_command(cmd: str) -> subprocess.CompletedProcess[bytes]:
    """Run a shell command and return the result."""
    return subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        timeout=300,
    )


def _check_verify_result() -> bool:
    """Parse verify-last-result.json and return whether verification passed."""
    if not VERIFY_RESULT_FILE.exists():
        return True  # No result file means no global verification failure
    try:
        data = json.loads(VERIFY_RESULT_FILE.read_text(encoding="utf-8"))
        return data.get("status", "unknown").lower() == "pass"
    except (json.JSONDecodeError, KeyError):
        return False


def _execute_task(task: TaskRecord) -> ExecutionLog:
    """Execute a single task's verify command."""
    log = ExecutionLog(
        task_id=task.task_id,
        step_index=task.index,
        started_at=datetime.now(UTC).isoformat(),
        writeback_path=task.writeback,
    )
    try:
        result = _run_command(task.verify)
        log.exit_code = result.returncode
        log.finished_at = datetime.now(UTC).isoformat()
        if result.returncode != 0:
            log.error = result.stderr.decode("utf-8", errors="replace")[:500]
        return log
    except subprocess.TimeoutExpired:
        log.error = "Command timed out after 300s"
        log.finished_at = datetime.now(UTC).isoformat()
        return log
    except Exception as e:
        log.error = str(e)
        log.finished_at = datetime.now(UTC).isoformat()
        return log


def _write_jsonl_log(log: ExecutionLog, writeback_path: str, report_dir: Path = _DEFAULT_REPORT_DIR) -> None:
    """Append execution log as JSONL entry."""
    report_dir.mkdir(parents=True, exist_ok=True)
    log_file = Path(writeback_path) if writeback_path else report_dir / "execution.jsonl"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "task_id": log.task_id,
            "step_index": log.step_index,
            "started_at": log.started_at,
            "finished_at": log.finished_at,
            "exit_code": log.exit_code,
            "error": log.error,
            "writeback_path": log.writeback_path,
        }) + "\n")


def execute_plan(
    plan_path: Path,
    dry_run: bool = False,
    max_steps: int | None = None,
    report_dir: Path = _DEFAULT_REPORT_DIR,
) -> dict[str, str]:
    """
    Execute a validated plan file sequentially.

    Returns a summary dict with keys: status, executed, failed, blocked.
    """
    # Lint first
    lint_issues, lint_warnings = lint_plan_text(
        plan_path.read_text(encoding="utf-8"), file_path=plan_path
    )
    for warning in lint_warnings:
        print(f"[WARN] {warning}")
    if lint_issues:
        print("[FAIL] Plan lint failed:")
        for issue in lint_issues:
            print(f" - {issue}")
        return {
            "status": "failed",
            "reason": "lint_failed",
            "halted_before_execution": True,
            "executed": 0,
            "details": lint_issues,
        }

    tasks = _load_tasks_from_plan(plan_path)
    if not tasks:
        return {"status": "skipped", "reason": "no_tasks"}

    ordered_tasks = _topological_sort(tasks)
    results: dict[str, str] = {}
    failed_tasks: list[str] = []
    blocked_tasks: list[str] = []

    for step_idx, task in enumerate(ordered_tasks):
        if max_steps is not None and step_idx >= max_steps:
            print(f"[SKIP] Max steps reached ({max_steps})")
            break

        # Check dependencies
        deps = _resolve_dependencies(tasks)
        task_deps = deps.get(task.task_id, [])
        for dep_id in task_deps:
            dep_status = results.get(dep_id)
            if dep_status not in ("done",):
                blocked_tasks.append(task.task_id)
                results[task.task_id] = "blocked"
                print(f"[BLOCKED] {task.task_id} - dependency {dep_id} not done")
                continue

        if task.status == "done":
            print(f"[SKIP] {task.task_id} already done")
            results[task.task_id] = "done"
            continue

        if dry_run:
            print(f"[DRY-RUN] {task.task_id}: {task.verify}")
            results[task.task_id] = "dry_run"
            continue

        print(f"[RUN] {task.task_id}: {task.verify}")
        log = _execute_task(task)

        # Verification gate
        verify_ok = log.exit_code == 0
        if not verify_ok:
            # Check global verification
            global_ok = _check_verify_result()
            if not global_ok:
                results[task.task_id] = "failed"
                failed_tasks.append(task.task_id)
                print(f"[FAIL] {task.task_id} - verification failed")
            else:
                results[task.task_id] = "failed"
                failed_tasks.append(task.task_id)
                print(f"[FAIL] {task.task_id} - exit code {log.exit_code}")
        else:
            results[task.task_id] = "done"
            print(f"[PASS] {task.task_id}")

        _write_jsonl_log(log, task.writeback, report_dir)

    # Roll-up status
    if failed_tasks:
        final_status = "partial_failed"
    elif blocked_tasks:
        final_status = "partial_blocked"
    elif all(r == "done" for r in results.values()):
        final_status = "success"
    else:
        final_status = "partial_incomplete"

    return {
        "status": final_status,
        "executed": len(results),
        "failed": len(failed_tasks),
        "blocked": len(blocked_tasks),
        "details": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sequential plan executor with verification gate."
    )
    parser.add_argument(
        "plan_file",
        type=Path,
        help="Path to plan markdown file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview execution without running commands",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Maximum number of steps to execute",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for execution reports",
    )
    args = parser.parse_args()

    report_dir = args.output_dir or _DEFAULT_REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)

    if not args.plan_file.exists():
        print(f"[ERROR] Plan file not found: {args.plan_file}")
        return 1

    result = execute_plan(args.plan_file, dry_run=args.dry_run, max_steps=args.max_steps, report_dir=report_dir)
    print(f"\n[RESULT] Status: {result.get('status', 'unknown')}")

    if result.get("details"):
        for tid, status in result["details"].items():
            print(f"  - {tid}: {status}")

    if result.get("status") == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
