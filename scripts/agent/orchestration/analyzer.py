# Phase 1 — Analyzer

"""
Analyzer takes a WorkSpec and produces a list of TaskSpecs.

INPUT:  WorkSpec (description, file_groups, success_criteria)
OUTPUT: list[TaskSpec] — one per FileGroup

Rules:
  - Each FileGroup becomes exactly one TaskSpec
  - Task IDs are assigned sequentially (T1, T2, ...)
  - Dependencies: None by default (all groups are independent)
  - Scope is derived from the FileGroup's domain_path
"""

from __future__ import annotations

from scripts.agent.orchestration.spec import (
    WorkSpec,
    TaskSpec,
    validate_task_ids_unique,
    validate_no_circular_dependencies,
)


def analyze(work_spec: WorkSpec) -> list[TaskSpec]:
    """Convert a WorkSpec into independent TaskSpecs.

    Args:
        work_spec: The full scope of work to decompose.

    Returns:
        List of TaskSpecs, one per FileGroup in work_spec.file_groups.

    Raises:
        ValueError: If task IDs would collide or dependencies are circular.
    """
    if not work_spec.file_groups:
        raise ValueError("Cannot analyze WorkSpec with zero file groups")

    tasks: list[TaskSpec] = []
    for idx, fg in enumerate(work_spec.file_groups, start=1):
        task_id = f"T{idx}"
        tasks.append(
            TaskSpec(
                task_id=task_id,
                description=f"{work_spec.description} — {fg.domain_path}",
                target_paths=fg.files,
                goal=work_spec.success_criteria[0] if work_spec.success_criteria else f"Complete changes in {fg.domain_path}",
                scope=f"Only modify files within '{fg.domain_path}'. Do not touch files in other domain directories or shared/ unless explicitly listed.",
                dependencies=[],
            )
        )

    validate_task_ids_unique(tasks)
    validate_no_circular_dependencies(tasks)
    return tasks


def estimate_parallelism(task_specs: list[TaskSpec]) -> int:
    """Return the recommended number of parallel subagents.

    Scaling rules (from AGENTS.md §2.2):
      - file count <= 5  → N = 2~3
      - file count > 5   → N = 4~5
    """
    total_files = sum(len(t.target_paths) for t in task_specs)
    n_tasks = len(task_specs)

    if total_files <= 5:
        return min(max(n_tasks, 2), 3)
    else:
        return min(max(n_tasks, 4), 5)
