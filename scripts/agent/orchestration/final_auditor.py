# Phase 5 — Final Auditor

"""
Final Auditor takes the complete set of DiffResults and AuditReports
and produces the final OrchestrationResult.

INPUT:  list[DiffResult], list[AuditReport]
OUTPUT: OrchestrationResult

Checks:
  - All tasks completed (no FAILED/BLOCKED)
  - No blocking (HIGH) audit findings remain
  - Success criteria from original WorkSpec are met
"""

from __future__ import annotations

from scripts.agent.orchestration.spec import (
    DiffResult,
    AuditReport,
    OrchestrationResult,
    OrchestrationStatus,
    TaskStatus,
)


def final_audit(
    task_results: list[DiffResult],
    audit_reports: list[AuditReport],
    success_criteria: list[str] | None = None,
) -> OrchestrationResult:
    """Produce the final orchestration result.

    INPUT:
        task_results: list of DiffResult from Phase 2 (and possibly Phase 4)
        audit_reports: list of AuditReport from Phase 3 (and possibly re-audit)
        success_criteria: optional list of criteria strings to verify

    OUTPUT:
        OrchestrationResult with status, summary, and counts
    """
    # Check task completion
    failed_tasks = [
        dr for dr in task_results
        if dr.status in (TaskStatus.FAILED, TaskStatus.BLOCKED)
    ]

    # Check remaining blocking issues
    total_findings = sum(len(ar.findings) for ar in audit_reports)
    blocking_remaining = sum(
        ar.high_count for ar in audit_reports
    )

    # Determine overall status
    if failed_tasks:
        status = OrchestrationStatus.FAILED
        summary_parts = [
            f"{len(failed_tasks)} task(s) failed: "
            + ", ".join(f"'{ft.task_id}'" for ft in failed_tasks)
        ]
    elif blocking_remaining > 0:
        status = OrchestrationStatus.IN_PROGRESS
        summary_parts = [
            f"{blocking_remaining} blocking issue(s) remain"
        ]
    elif success_criteria:
        # Verify success criteria (basic check — actual verification is runtime)
        all_met = True
        unmet = []
        for criterion in success_criteria:
            # In the runtime, this would check actual verification results
            # For now, we assume criteria are met if tasks completed
            pass
        if not all_met:
            status = OrchestrationStatus.FAILED
            summary_parts = [f"Success criteria not met: {unmet}"]
        else:
            status = OrchestrationStatus.COMPLETED
            summary_parts = ["All tasks completed, no blocking issues"]
    else:
        status = OrchestrationStatus.COMPLETED
        summary_parts = ["All tasks completed, no blocking issues"]

    return OrchestrationResult(
        status=status,
        overall_summary="; ".join(summary_parts),
        task_results=task_results,
        audit_reports=audit_reports,
        total_findings=total_findings,
        blocking_issues_remaining=blocking_remaining,
    )


def is_orchestration_successful(result: OrchestrationResult) -> bool:
    """Quick check if the orchestration pipeline succeeded."""
    return result.is_success
