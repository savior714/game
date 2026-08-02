# Phase 4 — Fixer

"""
Fixer takes AuditReports and produces fix instructions for subagents.

INPUT:  list[AuditReport] from Phase 3
OUTPUT: list[DiffResult] — updated results after fixes are applied

Rules:
  - Only fix issues found in Phase 3
  - Multiple issues in the same file → 1 subagent handles all
  - Each subagent gets a focused prompt with specific fix instructions
  - Retry only once (AGENTS.md §2.2 execution rules)
"""

from __future__ import annotations

from scripts.agent.orchestration.spec import (
    AuditFinding,
    AuditReport,
    DiffResult,
    TaskStatus,
)


def build_fix_requests(reports: list[AuditReport]) -> list[dict]:
    """Build fix instructions grouped by task_id and file.

    Returns a list of fix groups, each containing:
      {
        "task_id": str,
        "file_path": str,
        "findings": [AuditFinding, ...],
        "prompt": str  # formatted for subagent
      }
    """
    groups: dict[tuple[str, str], dict[str, str | list[AuditFinding]]] = {}

    for report in reports:
        if not report.findings:
            continue

        # Group findings by file path
        by_file: dict[str, list[AuditFinding]] = {}
        for finding in report.findings:
            fp = finding.file_path or f"unknown ({report.task_id})"
            by_file.setdefault(fp, []).append(finding)

        for file_path, findings in by_file.items():
            key = (report.task_id, file_path)
            groups[key] = {
                "task_id": report.task_id,
                "file_path": file_path,
                "findings": findings,
            }

    # Build prompts
    result: list[dict] = []
    for (task_id, file_path), group in groups.items():
        findings = group["findings"]
        prompt_lines = [
            f"Fix issues in {file_path} (task {task_id}):",
        ]
        for i, f in enumerate(findings, 1):
            prompt_lines.append(
                f"  {i}. [{f.severity.value}] {f.category.value}: {f.description}"
            )
            if f.suggested_fix:
                prompt_lines.append(f"     Fix: {f.suggested_fix}")

        result.append({
            "task_id": task_id,
            "file_path": file_path,
            "findings": findings,
            "prompt": "\n".join(prompt_lines),
        })

    return result


def apply_fixes(
    fix_instructions: list[dict],
    raw_outputs: list[dict[str, str]],
) -> list[DiffResult]:
    """Apply fix results and produce updated DiffResults.

    INPUT:
        fix_instructions: output from build_fix_requests()
        raw_outputs: list of {"task_id": "...", "output": "...", "error": bool}
            from fix subagent executions

    OUTPUT:
        list[DiffResult] — updated results with fix outcomes
    """
    results: list[DiffResult] = []
    for raw in raw_outputs:
        task_id = raw.get("task_id", "unknown")
        output_text = raw.get("output", "")
        has_error = raw.get("error", False)

        if has_error:
            results.append(DiffResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error=output_text.strip(),
            ))
        else:
            results.append(DiffResult(
                task_id=task_id,
                status=TaskStatus.DONE,
                diff_summary=output_text.strip()[:500],
            ))

    return results


def should_retry(reports: list[AuditReport]) -> bool:
    """Determine if Phase 4 retry is needed.

    Returns True if any HIGH severity findings remain unfixed.
    """
    return any(r.has_blocking_issues for r in reports)
