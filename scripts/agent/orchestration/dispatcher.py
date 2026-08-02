# Phase 2 — Dispatcher

"""
Dispatcher takes a list of TaskSpecs and executes them as parallel subagent calls.

INPUT:  list[TaskSpec]
OUTPUT: list[DiffResult] — one per TaskSpec

This module defines the interface and contract. The actual subagent invocation
is performed by the agent runtime (task tool calls). This module provides:
  - Prompt generation
  - Result parsing from subagent output
  - Validation of results
"""

from __future__ import annotations

from scripts.agent.orchestration.spec import (
    TaskSpec,
    DiffResult,
    TaskStatus,
)


def build_dispatch_instructions(
    task_specs: list[TaskSpec],
) -> list[dict[str, str]]:
    """Build the instruction payloads for parallel subagent dispatch.

    Returns a list of dicts suitable for task() tool calls:
      [
        {"description": "...", "subagent_type": "general", "prompt": "..."},
        ...
      ]
    """
    instructions: list[dict[str, str]] = []
    for ts in task_specs:
        instructions.append(
            {
                "description": f"Implement: {ts.task_id} — {ts.description}",
                "subagent_type": "general",
                "prompt": ts.parallel_prompt,
            }
        )
    return instructions


def parse_results(
    raw_outputs: list[dict[str, str | bool]],
) -> list[DiffResult]:
    """Parse raw subagent outputs into DiffResults.

    INPUT: list of {"task_id": "...", "output": "...", "error": bool}
    OUTPUT: list[DiffResult]

    Each dict corresponds to one TaskSpec by position.
    """
    results: list[DiffResult] = []
    for raw in raw_outputs:
        task_id = str(raw.get("task_id", "unknown"))
        output_text = str(raw.get("output", ""))
        has_error = bool(raw.get("error", False))
        results.append(DiffResult.from_subagent_output(task_id, output_text, has_error))
    return results


def validate_dispatch_results(
    task_specs: list[TaskSpec],
    diff_results: list[DiffResult],
) -> list[str]:
    """Validate that every TaskSpec has a corresponding DiffResult.

    Returns a list of error messages (empty if all valid).
    """
    errors: list[str] = []
    spec_ids = {ts.task_id for ts in task_specs}
    result_ids = {dr.task_id for dr in diff_results}

    missing = spec_ids - result_ids
    if missing:
        errors.append(f"Missing DiffResult for tasks: {missing}")

    extra = result_ids - spec_ids
    if extra:
        errors.append(f"Unexpected DiffResult for tasks: {extra}")

    failed = [dr for dr in diff_results if dr.status == TaskStatus.FAILED]
    if failed:
        for fr in failed:
            errors.append(
                f"Task {fr.task_id} FAILED: {fr.error or 'no output'}"
            )

    return errors
