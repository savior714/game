# Multi-Agent Orchestration — data contracts

"""
Phase 1: Analyzer  ->  WorkSpec  ->  list[TaskSpec]
Phase 2: Dispatcher ->  list[TaskSpec]  ->  list[DiffResult]
Phase 3: Auditor    ->  list[DiffResult]  ->  list[AuditReport]
Phase 4: Fixer      ->  list[AuditReport]  ->  list[DiffResult] (updated)
Phase 5: FinalAuditor ->  list[DiffResult], list[AuditReport]  ->  OrchestrationResult
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any


# -- Enums -------------------------------------------------------------------


class TaskStatus(str, Enum):
    TODO = "todo"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"


class AuditSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def weight(self) -> int:
        return {"high": 3, "medium": 2, "low": 1}[self.value]


class AuditCategory(str, Enum):
    KOREAN_ENCODING = "korean_encoding"
    QUERY_SELECTOR_UNIQUENESS = "query_selector_uniqueness"
    CONTEXT_ROUTE_GATE = "context_route_gate"
    PARTIAL_EDIT_RULES = "partial_edit_rules"
    FILE_OVERLAP = "file_overlap"
    MISSING_VERIFICATION = "missing_verification"
    GENERAL = "general"


class OrchestrationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# -- Phase 1: WorkSpec / TaskSpec --------------------------------------------


@dataclass
class FileGroup:
    """A group of files that can be modified independently (Phase 1 input)."""

    domain_path: str
    files: list[str]
    description: str = ""

    def __post_init__(self) -> None:
        if not self.domain_path:
            raise ValueError("FileGroup.domain_path must not be empty")
        if not self.files:
            raise ValueError(f"FileGroup '{self.domain_path}' must have at least one file")


@dataclass
class WorkSpec:
    """Phase 1 input -- describes the full scope of work to orchestrate.

    INPUT:
        description: human-readable task description
        file_groups: independent groups of files to modify
        success_criteria: list of conditions that must all pass

    OUTPUT (via analyze()): list[TaskSpec]
    """

    description: str
    file_groups: list[FileGroup]
    success_criteria: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.description:
            raise ValueError("WorkSpec.description must not be empty")
        if not self.file_groups:
            raise ValueError("WorkSpec.file_groups must not be empty")
        # Validate no file overlap between groups
        all_files: set[str] = set()
        for fg in self.file_groups:
            for f in fg.files:
                if f in all_files:
                    raise ValueError(
                        f"File '{f}' appears in multiple FileGroups -- "
                        "groups must be mutually exclusive"
                    )
                all_files.add(f)


@dataclass
class TaskSpec:
    """Phase 1 output -- a single subagent task to execute.

    Each TaskSpec maps to one `task` tool call with subagent_type="general".
    """

    task_id: str
    description: str
    target_paths: list[str]
    goal: str
    scope: str
    dependencies: list[str] = field(default_factory=list)

    @property
    def parallel_prompt(self) -> str:
        """Formatted prompt suitable for subagent task() call."""
        return (
            f"Task ID: {self.task_id}\n"
            f"Task: {self.description}\n"
            f"Target paths: {', '.join(self.target_paths)}\n"
            f"Goal: {self.goal}\n"
            f"Scope boundary: {self.scope}\n"
            f"Rules:\n"
            f"  - Modify ONLY the target paths listed above\n"
            f"  - Do NOT touch any other files\n"
            f"  - After making changes, run `git diff` and include the summary in your output\n"
            f"  - Follow AGENTS.md section 4.1 (Korean encoding rules)\n"
            f"  - Follow AGENTS.md section 4.2 (message uniqueness for HTML/JS)\n"
            f"  - Follow routing.md section 2 (Context Route Gate) before editing\n"
        )


# -- Phase 2 Output / Phase 3 Input: DiffResult ------------------------------


@dataclass
class DiffResult:
    """Phase 2 output -- the result of executing a single subagent task.

    Captures what the subagent reported after its work.
    """

    task_id: str
    status: TaskStatus
    diff_summary: str = ""
    files_modified: list[str] = field(default_factory=list)
    error: str | None = None

    @classmethod
    def from_subagent_output(
        cls, task_id: str, output_text: str, has_error: bool = False
    ) -> DiffResult:
        """Parse a subagent's text output into a DiffResult.

        INPUT: task_id, raw output text, error flag
        OUTPUT: DiffResult with parsed fields
        """
        if has_error:
            return cls(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error=output_text.strip(),
            )

        files: list[str] = []
        summary_lines: list[str] = []
        for line in output_text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("diff --git", "---", "+++")):
                continue
            if stripped.startswith("domains/") or stripped.startswith("shared/"):
                if not any(stripped in f for f in files):
                    files.append(stripped)
            elif stripped:
                summary_lines.append(stripped)

        return cls(
            task_id=task_id,
            status=TaskStatus.DONE if files or summary_lines else TaskStatus.FAILED,
            diff_summary="\n".join(summary_lines[:50]),
            files_modified=files,
        )


# -- Phase 3 Output / Phase 4 Input: AuditReport / AuditFinding --------------


@dataclass
class AuditFinding:
    """A single issue found during audit (Phase 3)."""

    category: AuditCategory
    severity: AuditSeverity
    file_path: str = ""
    line_number: int | None = None
    description: str = ""
    evidence: str = ""
    suggested_fix: str = ""

    @property
    def key(self) -> str:
        """Unique key for deduplication: category + file + line."""
        return f"{self.category.value}:{self.file_path}:{self.line_number or 0}"


@dataclass
class AuditReport:
    """Phase 3 output -- audit results for a single task's diff.

    Each DiffResult gets exactly one AuditReport (1:1 mapping).
    """

    task_id: str
    findings: list[AuditFinding] = field(default_factory=list)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == AuditSeverity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == AuditSeverity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == AuditSeverity.LOW)

    @property
    def has_blocking_issues(self) -> bool:
        """True if any HIGH severity findings exist."""
        return self.high_count > 0

    def add_finding(self, finding: AuditFinding) -> None:
        if finding.key not in (f.key for f in self.findings):
            self.findings.append(finding)


# -- Phase 4 Input: FixRequest -----------------------------------------------


@dataclass
class FixRequest:
    """Phase 4 -- instructions for fixing a specific audit finding."""

    task_id: str
    finding_key: str
    category: AuditCategory
    description: str
    action: str
    """What the fixer subagent should do."""


# -- Phase 5 Output: OrchestrationResult -------------------------------------


@dataclass
class OrchestrationResult:
    """Phase 5 output -- final result of the entire orchestration pipeline."""

    status: OrchestrationStatus
    overall_summary: str = ""
    task_results: list[DiffResult] = field(default_factory=list)
    audit_reports: list[AuditReport] = field(default_factory=list)
    total_findings: int = 0
    blocking_issues_remaining: int = 0

    @property
    def is_success(self) -> bool:
        return (
            self.status == OrchestrationStatus.COMPLETED
            and self.blocking_issues_remaining == 0
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "overall_summary": self.overall_summary,
            "task_results": [asdict(tr) for tr in self.task_results],
            "audit_reports": [
                {"task_id": ar.task_id, "findings_count": len(ar.findings)}
                for ar in self.audit_reports
            ],
            "total_findings": self.total_findings,
            "blocking_issues_remaining": self.blocking_issues_remaining,
            "is_success": self.is_success,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# -- Validation helpers ------------------------------------------------------


def validate_task_ids_unique(task_specs: list[TaskSpec]) -> None:
    """Ensure all TaskSpec.task_id values are unique."""
    ids = [t.task_id for t in task_specs]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate task_ids found: {[i for i in ids if ids.count(i) > 1]}")


def validate_no_circular_dependencies(task_specs: list[TaskSpec]) -> None:
    """Detect circular dependencies among TaskSpec values."""
    id_set = {t.task_id for t in task_specs}
    dep_map = {t.task_id: set(t.dependencies) & id_set for t in task_specs}

    visited: set[str] = set()
    in_stack: set[str] = set()

    def dfs(tid: str) -> bool:
        if tid in in_stack:
            return True  # cycle detected
        if tid in visited:
            return False
        visited.add(tid)
        in_stack.add(tid)
        for dep in dep_map.get(tid, set()):
            if dfs(dep):
                return True
        in_stack.discard(tid)
        return False

    for tid in dep_map:
        if dfs(tid):
            raise ValueError(f"Circular dependency detected involving task '{tid}'")


def validate_file_groups_non_overlapping(file_groups: list[FileGroup]) -> None:
    """Ensure no file appears in more than one FileGroup."""
    all_files: dict[str, str] = {}
    for fg in file_groups:
        for f in fg.files:
            if f in all_files:
                raise ValueError(
                    f"File '{f}' in both '{all_files[f]}' and '{fg.domain_path}'"
                )
            all_files[f] = fg.domain_path
