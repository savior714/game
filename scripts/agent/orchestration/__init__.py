# Multi-Agent Orchestration Pipeline

"""
Main entry point — coordinates the 5-phase orchestration pipeline.

Usage (agent runtime):
    from scripts.agent.orchestration import PipelineOrchestrator

    orchestrator = PipelineOrchestrator()
    result = orchestrator.run(work_spec)

The actual subagent dispatch (task tool calls) and fix execution
are performed by the agent runtime. This module provides the
coordination logic, data contracts, and validation gates.
"""

from __future__ import annotations

from scripts.agent.orchestration.spec import (
    WorkSpec,
    DiffResult,
    OrchestrationResult,
    OrchestrationStatus,
)
from scripts.agent.orchestration.analyzer import analyze
from scripts.agent.orchestration.dispatcher import (
    build_dispatch_instructions,
    parse_results,
    validate_dispatch_results,
)
from scripts.agent.orchestration.auditor import audit as audit_diffs, summary
from scripts.agent.orchestration.fixer import build_fix_requests, should_retry
from scripts.agent.orchestration.final_auditor import final_audit


class PipelineOrchestrator:
    """Coordinates the 5-phase multi-agent orchestration pipeline.

    The orchestrator manages data flow between phases. Actual subagent
    execution (task tool calls) is performed by the agent runtime,
    with results passed back to the orchestrator.
    """

    def __init__(self, max_fix_retries: int = 1) -> None:
        """
        Args:
            max_fix_retries: Maximum Phase 4 retry attempts (default: 1)
        """
        self.max_fix_retries = max_fix_retries
        self.phase_log: list[str] = []

    def run(
        self,
        work_spec: WorkSpec,
        dispatch_fn=None,
        fix_dispatch_fn=None,
    ) -> OrchestrationResult:
        """Execute the full 5-phase orchestration pipeline.

        Args:
            work_spec: Phase 1 input describing the full scope of work.
            dispatch_fn: Optional callable(task_instructions) -> raw_outputs
                for Phase 2. If None, returns PENDING status.
            fix_dispatch_fn: Optional callable(fix_instructions) -> raw_outputs
                for Phase 4. If None, fixes are not applied.

        Returns:
            OrchestrationResult with final status and summary.
        """
        self.phase_log = []

        # ── Phase 1: Analyze ─────────────────────────────────────────────
        self.phase_log.append("Phase 1: Analyzing work scope")
        task_specs = analyze(work_spec)
        self.phase_log.append(f"  → {len(task_specs)} tasks created")

        # ── Phase 2: Dispatch (parallel) ─────────────────────────────────
        self.phase_log.append("Phase 2: Dispatching implementation subagents")
        if dispatch_fn is None:
            return OrchestrationResult(
                status=OrchestrationStatus.PENDING,
                overall_summary="Pipeline defined but no dispatch function provided",
            )

        dispatch_instructions = build_dispatch_instructions(task_specs)
        raw_outputs = dispatch_fn(dispatch_instructions)
        diff_results = parse_results(raw_outputs)
        validation_errors = validate_dispatch_results(task_specs, diff_results)

        if validation_errors:
            self.phase_log.append(f"  → Validation errors: {validation_errors}")

        self.phase_log.append(
            f"  → {len(diff_results)} results received, "
            f"{sum(1 for dr in diff_results if dr.status.name == 'DONE')} done"
        )

        # ── Phase 3: Audit (parallel) ────────────────────────────────────
        self.phase_log.append("Phase 3: Auditing diffs")
        audit_reports = audit_diffs(diff_results)
        audit_summary_text = summary(audit_reports)
        self.phase_log.append(f"  → {audit_summary_text}")

        # ── Phase 4: Fix (parallel, optional retry) ──────────────────────
        fix_round = 0
        current_diff_results = diff_results
        current_audit_reports = audit_reports

        while should_retry(current_audit_reports) and fix_round < self.max_fix_retries:
            fix_round += 1
            self.phase_log.append(f"Phase 4 (round {fix_round}): Fixing issues")

            fix_instructions = build_fix_requests(current_audit_reports)
            if not fix_instructions:
                break

            if fix_dispatch_fn is None:
                self.phase_log.append("  → No fix dispatch function, skipping fixes")
                break

            fix_raw_outputs = fix_dispatch_fn(fix_instructions)
            current_diff_results = fixer_apply_fixes(fix_instructions, fix_raw_outputs)

            # Re-audit after fixes
            self.phase_log.append("Phase 3 (re-audit): Checking fixes")
            current_audit_reports = audit_diffs(current_diff_results)

        # ── Phase 5: Final Audit ─────────────────────────────────────────
        self.phase_log.append("Phase 5: Final audit")
        result = final_audit(
            task_results=current_diff_results,
            audit_reports=current_audit_reports,
            success_criteria=work_spec.success_criteria,
        )

        self.phase_log.append(f"  → Status: {result.status.value}")
        self.phase_log.append(f"  → Summary: {result.overall_summary}")

        return result

    def get_log(self) -> list[str]:
        """Return the phase execution log."""
        return self.phase_log


def fixer_apply_fixes(
    fix_instructions: list[dict],
    raw_outputs: list[dict[str, str]],
) -> list[DiffResult]:
    """Helper to apply fix results (imported to avoid circular dep)."""
    from scripts.agent.orchestration.fixer import apply_fixes
    return apply_fixes(fix_instructions, raw_outputs)
