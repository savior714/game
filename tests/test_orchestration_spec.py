"""Tests for orchestration data contracts (spec.py)."""

from __future__ import annotations

import pytest

from scripts.agent.orchestration.spec import (
    WorkSpec,
    FileGroup,
    TaskSpec,
    DiffResult,
    AuditReport,
    AuditFinding,
    OrchestrationResult,
    TaskStatus,
    AuditSeverity,
    AuditCategory,
    OrchestrationStatus,
    validate_task_ids_unique,
    validate_no_circular_dependencies,
    validate_file_groups_non_overlapping,
)


# ── FileGroup ────────────────────────────────────────────────────────────────


class TestFileGroup:
    def test_valid_file_group(self):
        fg = FileGroup(domain_path="domains/math/", files=["index.html", "main.js"])
        assert fg.domain_path == "domains/math/"
        assert len(fg.files) == 2

    def test_empty_domain_path_raises(self):
        with pytest.raises(ValueError, match="domain_path must not be empty"):
            FileGroup(domain_path="", files=["index.html"])

    def test_empty_files_raises(self):
        with pytest.raises(ValueError, match="must have at least one file"):
            FileGroup(domain_path="domains/math/", files=[])


# ── WorkSpec ─────────────────────────────────────────────────────────────────


class TestWorkSpec:
    def test_valid_work_spec(self):
        ws = WorkSpec(
            description="Refactor UI",
            file_groups=[
                FileGroup(
                    domain_path="domains/math/", files=["domains/math/index.html"]
                ),
                FileGroup(
                    domain_path="domains/english/", files=["domains/english/index.html"]
                ),
            ],
        )
        assert len(ws.file_groups) == 2

    def test_empty_description_raises(self):
        with pytest.raises(ValueError, match="description must not be empty"):
            WorkSpec(description="", file_groups=[])

    def test_empty_file_groups_raises(self):
        with pytest.raises(ValueError, match="file_groups must not be empty"):
            WorkSpec(description="test", file_groups=[])

    def test_overlapping_files_raises(self):
        with pytest.raises(ValueError, match="appears in multiple FileGroups"):
            WorkSpec(
                description="test",
                file_groups=[
                    FileGroup(domain_path="domains/math/", files=["shared.js"]),
                    FileGroup(domain_path="domains/english/", files=["shared.js"]),
                ],
            )


# ── TaskSpec ─────────────────────────────────────────────────────────────────


class TestTaskSpec:
    def test_parallel_prompt_contains_required_info(self):
        ts = TaskSpec(
            task_id="T1",
            description="Refactor math UI",
            target_paths=["domains/math/index.html"],
            goal="Improve layout",
            scope="Only domains/math/",
        )
        prompt = ts.parallel_prompt
        assert "T1" in prompt
        assert "domains/math/index.html" in prompt
        assert "Refactor math UI" in prompt
        assert "AGENTS.md section 4.1" in prompt
        assert "routing.md section 2" in prompt

    def test_empty_target_paths_allowed_at_creation(self):
        # Target paths validated at runtime, not construction
        ts = TaskSpec(
            task_id="T1",
            description="test",
            target_paths=[],
            goal="test",
            scope="test",
        )
        assert ts.target_paths == []


# ── DiffResult ───────────────────────────────────────────────────────────────


class TestDiffResult:
    def test_from_subagent_output_success(self):
        output = """
diff --git a/domains/math/index.html b/domains/math/index.html
--- a/domains/math/index.html
+++ b/domains/math/index.html
domains/math/index.html
domains/math/main.js
"""
        dr = DiffResult.from_subagent_output("T1", output)
        assert dr.status == TaskStatus.DONE
        assert "domains/math/index.html" in dr.files_modified

    def test_from_subagent_output_error(self):
        dr = DiffResult.from_subagent_output(
            "T1", "JSON parsing failed", has_error=True
        )
        assert dr.status == TaskStatus.FAILED
        assert dr.error == "JSON parsing failed"

    def test_from_subagent_output_empty(self):
        dr = DiffResult.from_subagent_output("T1", "")
        assert dr.status == TaskStatus.FAILED


# ── AuditReport ──────────────────────────────────────────────────────────────


class TestAuditReport:
    def test_finding_counts(self):
        report = AuditReport(task_id="T1")
        report.add_finding(
            AuditFinding(
                category=AuditCategory.KOREAN_ENCODING,
                severity=AuditSeverity.HIGH,
                description="test",
            )
        )
        report.add_finding(
            AuditFinding(
                category=AuditCategory.QUERY_SELECTOR_UNIQUENESS,
                severity=AuditSeverity.MEDIUM,
                description="test",
            )
        )
        report.add_finding(
            AuditFinding(
                category=AuditCategory.GENERAL,
                severity=AuditSeverity.LOW,
                description="test",
            )
        )

        assert report.high_count == 1
        assert report.medium_count == 1
        assert report.low_count == 1
        assert report.has_blocking_issues is True

    def test_deduplication(self):
        report = AuditReport(task_id="T1")
        f1 = AuditFinding(
            category=AuditCategory.KOREAN_ENCODING,
            severity=AuditSeverity.HIGH,
            file_path="index.html",
            line_number=10,
            description="test1",
        )
        f2 = AuditFinding(
            category=AuditCategory.KOREAN_ENCODING,
            severity=AuditSeverity.HIGH,
            file_path="index.html",
            line_number=10,
            description="different text same key",
        )
        report.add_finding(f1)
        report.add_finding(f2)
        assert len(report.findings) == 1

    def test_no_blocking_issues(self):
        report = AuditReport(task_id="T1")
        report.add_finding(
            AuditFinding(
                category=AuditCategory.GENERAL,
                severity=AuditSeverity.LOW,
                description="minor",
            )
        )
        assert report.has_blocking_issues is False


# ── OrchestrationResult ──────────────────────────────────────────────────────


class TestOrchestrationResult:
    def test_is_success_completed_no_blocking(self):
        result = OrchestrationResult(
            status=OrchestrationStatus.COMPLETED,
            blocking_issues_remaining=0,
        )
        assert result.is_success is True

    def test_is_failure_with_blocking(self):
        result = OrchestrationResult(
            status=OrchestrationStatus.IN_PROGRESS,
            blocking_issues_remaining=2,
        )
        assert result.is_success is False

    def test_to_dict_serializable(self):
        result = OrchestrationResult(
            status=OrchestrationStatus.COMPLETED,
            overall_summary="All done",
        )
        d = result.to_dict()
        assert d["status"] == "completed"
        assert d["is_success"] is True

    def test_to_json_serializable(self):
        result = OrchestrationResult(
            status=OrchestrationStatus.COMPLETED,
        )
        json_str = result.to_json()
        assert '"status": "completed"' in json_str


# ── Validation helpers ───────────────────────────────────────────────────────


class TestValidationHelpers:
    def test_validate_unique_task_ids(self):
        tasks = [
            TaskSpec(
                task_id="T1", description="a", target_paths=["f1"], goal="g", scope="s"
            ),
            TaskSpec(
                task_id="T2", description="b", target_paths=["f2"], goal="g", scope="s"
            ),
        ]
        validate_task_ids_unique(tasks)  # should not raise

    def test_validate_duplicate_task_ids_raises(self):
        tasks = [
            TaskSpec(
                task_id="T1", description="a", target_paths=["f1"], goal="g", scope="s"
            ),
            TaskSpec(
                task_id="T1", description="b", target_paths=["f2"], goal="g", scope="s"
            ),
        ]
        with pytest.raises(ValueError, match="Duplicate task_ids"):
            validate_task_ids_unique(tasks)

    def test_validate_no_circular_deps(self):
        tasks = [
            TaskSpec(
                task_id="T1", description="a", target_paths=["f1"], goal="g", scope="s"
            ),
            TaskSpec(
                task_id="T2",
                description="b",
                target_paths=["f2"],
                goal="g",
                scope="s",
                dependencies=["T1"],
            ),
        ]
        validate_no_circular_dependencies(tasks)  # should not raise

    def test_validate_circular_deps_raises(self):
        tasks = [
            TaskSpec(
                task_id="T1",
                description="a",
                target_paths=["f1"],
                goal="g",
                scope="s",
                dependencies=["T2"],
            ),
            TaskSpec(
                task_id="T2",
                description="b",
                target_paths=["f2"],
                goal="g",
                scope="s",
                dependencies=["T1"],
            ),
        ]
        with pytest.raises(ValueError, match="Circular dependency"):
            validate_no_circular_dependencies(tasks)

    def test_validate_non_overlapping_file_groups(self):
        fgs = [
            FileGroup(domain_path="domains/math/", files=["a.html"]),
            FileGroup(domain_path="domains/english/", files=["b.html"]),
        ]
        validate_file_groups_non_overlapping(fgs)  # should not raise

    def test_validate_overlapping_file_groups_raises(self):
        fgs = [
            FileGroup(domain_path="domains/math/", files=["shared.html"]),
            FileGroup(domain_path="domains/english/", files=["shared.html"]),
        ]
        with pytest.raises(ValueError, match="in both"):
            validate_file_groups_non_overlapping(fgs)
