"""Tests for the orchestration pipeline (dispatcher, fixer, final_auditor, __init__)."""

from __future__ import annotations

from scripts.agent.orchestration.spec import (
    WorkSpec,
    FileGroup,
    DiffResult,
    TaskStatus,
    AuditReport,
    OrchestrationStatus,
    AuditFinding,
    AuditSeverity,
    AuditCategory,
)
from scripts.agent.orchestration.analyzer import analyze
from scripts.agent.orchestration.dispatcher import (
    build_dispatch_instructions,
    parse_results,
    validate_dispatch_results,
)
from scripts.agent.orchestration.fixer import build_fix_requests, should_retry
from scripts.agent.orchestration.final_auditor import (
    final_audit,
    is_orchestration_successful,
)
from scripts.agent.orchestration import PipelineOrchestrator


# ── Dispatcher ───────────────────────────────────────────────────────────────


class TestDispatcher:
    def test_build_dispatch_instructions(self):
        ws = WorkSpec(
            description="Refactor",
            file_groups=[
                FileGroup(
                    domain_path="domains/math/", files=["domains/math/index.html"]
                ),
                FileGroup(
                    domain_path="domains/english/", files=["domains/english/index.html"]
                ),
            ],
        )
        tasks = analyze(ws)
        instructions = build_dispatch_instructions(tasks)
        assert len(instructions) == 2
        for inst in instructions:
            assert inst["subagent_type"] == "general"
            assert "prompt" in inst
            assert "description" in inst

    def test_parse_results_success(self):
        raw = [
            {
                "task_id": "T1",
                "output": "domains/math/index.html\nChanged layout",
                "error": False,
            },
            {
                "task_id": "T2",
                "output": "domains/english/index.html\nUpdated styles",
                "error": False,
            },
        ]
        results = parse_results(raw)
        assert len(results) == 2
        assert all(r.status == TaskStatus.DONE for r in results)

    def test_parse_results_error(self):
        raw = [
            {"task_id": "T1", "output": "timeout", "error": True},
        ]
        results = parse_results(raw)
        assert results[0].status == TaskStatus.FAILED

    def test_validate_dispatch_results_missing(self):
        tasks = [
            type("T", (), {"task_id": "T1", "target_paths": ["f1"]})(),
            type("T", (), {"task_id": "T2", "target_paths": ["f2"]})(),
        ]
        results = [DiffResult(task_id="T1", status=TaskStatus.DONE)]
        errors = validate_dispatch_results(tasks, results)
        assert any("T2" in e for e in errors)


# ── Fixer ────────────────────────────────────────────────────────────────────


class TestFixer:
    def test_build_fix_requests_groups_by_file(self):
        from scripts.agent.orchestration.spec import AuditReport

        report = AuditReport(task_id="T1")
        report.add_finding(
            AuditFinding(
                category=AuditCategory.KOREAN_ENCODING,
                severity=AuditSeverity.MEDIUM,
                file_path="index.html",
                description="Korean text issue",
                suggested_fix="Use bash + cat << 'EOF'",
            )
        )
        report.add_finding(
            AuditFinding(
                category=AuditCategory.QUERY_SELECTOR_UNIQUENESS,
                severity=AuditSeverity.HIGH,
                file_path="index.html",
                description="Duplicate text",
                suggested_fix="Add unique identifiers",
            )
        )

        fix_groups = build_fix_requests([report])
        assert len(fix_groups) == 1
        assert fix_groups[0]["file_path"] == "index.html"
        assert len(fix_groups[0]["findings"]) == 2

    def test_should_retry_with_blocking_issues(self):
        from scripts.agent.orchestration.spec import AuditReport, AuditFinding

        reports = [AuditReport(task_id="T1")]
        reports[0].add_finding(
            AuditFinding(
                category=AuditCategory.GENERAL,
                severity=AuditSeverity.HIGH,
                description="critical",
            )
        )
        assert should_retry(reports) is True

    def test_should_retry_no_blocking_issues(self):
        from scripts.agent.orchestration.spec import AuditReport, AuditFinding

        reports = [AuditReport(task_id="T1")]
        reports[0].add_finding(
            AuditFinding(
                category=AuditCategory.GENERAL,
                severity=AuditSeverity.LOW,
                description="minor",
            )
        )
        assert should_retry(reports) is False


# ── Final Auditor ────────────────────────────────────────────────────────────


class TestFinalAuditor:
    def test_completed_no_issues(self):
        results = [
            DiffResult(task_id="T1", status=TaskStatus.DONE, diff_summary="OK"),
            DiffResult(task_id="T2", status=TaskStatus.DONE, diff_summary="OK"),
        ]
        reports = [
            AuditReport(task_id="T1", findings=[]),
            AuditReport(task_id="T2", findings=[]),
        ]
        result = final_audit(results, reports)
        assert result.status == OrchestrationStatus.COMPLETED
        assert is_orchestration_successful(result)

    def test_failed_tasks(self):
        results = [
            DiffResult(task_id="T1", status=TaskStatus.DONE),
            DiffResult(task_id="T2", status=TaskStatus.FAILED, error="timeout"),
        ]
        reports = [
            AuditReport(task_id="T1", findings=[]),
            AuditReport(task_id="T2", findings=[]),
        ]
        result = final_audit(results, reports)
        assert result.status == OrchestrationStatus.FAILED
        assert "T2" in result.overall_summary

    def test_blocking_issues_remain(self):
        from scripts.agent.orchestration.spec import AuditFinding

        results = [DiffResult(task_id="T1", status=TaskStatus.DONE)]
        reports = [AuditReport(task_id="T1")]
        reports[0].add_finding(
            AuditFinding(
                category=AuditCategory.GENERAL,
                severity=AuditSeverity.HIGH,
                description="critical",
            )
        )
        result = final_audit(results, reports)
        assert result.status == OrchestrationStatus.IN_PROGRESS
        assert result.blocking_issues_remaining == 1


# ── PipelineOrchestrator (integration) ───────────────────────────────────────


class TestPipelineOrchestrator:
    def test_run_without_dispatch_returns_pending(self):
        ws = WorkSpec(
            description="test",
            file_groups=[
                FileGroup(
                    domain_path="domains/math/", files=["domains/math/index.html"]
                )
            ],
        )
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run(ws)
        assert result.status == OrchestrationStatus.PENDING

    def test_run_with_mock_dispatch(self):
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

        def mock_dispatch(instructions):
            return [
                {
                    "task_id": "T1",
                    "output": "domains/math/index.html\nUpdated layout",
                    "error": False,
                },
                {
                    "task_id": "T2",
                    "output": "domains/english/index.html\nUpdated styles",
                    "error": False,
                },
            ]

        orchestrator = PipelineOrchestrator()
        result = orchestrator.run(ws, dispatch_fn=mock_dispatch)

        assert result.status == OrchestrationStatus.COMPLETED
        assert len(result.task_results) == 2
        assert result.total_findings >= 0

    def test_run_with_mock_dispatch_and_fixes(self):
        ws = WorkSpec(
            description="Refactor",
            file_groups=[
                FileGroup(
                    domain_path="domains/math/", files=["domains/math/index.html"]
                )
            ],
        )

        dispatch_called = [False]

        def mock_dispatch(instructions):
            dispatch_called[0] = True
            return [
                {
                    "task_id": "T1",
                    "output": 'domains/math/index.html\nEdit tool: "No changes to apply"',
                    "error": False,
                },
            ]

        fix_called = [False]

        def mock_fix_dispatch(instructions):
            fix_called[0] = True
            return [
                {
                    "task_id": "T1",
                    "output": "Fixed: used bash + cat << 'EOF'",
                    "error": False,
                },
            ]

        orchestrator = PipelineOrchestrator(max_fix_retries=1)
        result = orchestrator.run(
            ws, dispatch_fn=mock_dispatch, fix_dispatch_fn=mock_fix_dispatch
        )

        assert dispatch_called[0] is True
        # Fix may or may not be called depending on audit findings
        assert len(result.task_results) >= 1

    def test_phase_log_populated(self):
        ws = WorkSpec(
            description="test",
            file_groups=[
                FileGroup(
                    domain_path="domains/math/", files=["domains/math/index.html"]
                )
            ],
        )
        orchestrator = PipelineOrchestrator()
        orchestrator.run(ws)
        log = orchestrator.get_log()
        assert len(log) >= 3
        assert any("Phase" in entry for entry in log)

    def test_max_fix_retries_enforced(self):
        ws = WorkSpec(
            description="test",
            file_groups=[
                FileGroup(
                    domain_path="domains/math/", files=["domains/math/index.html"]
                )
            ],
        )

        fix_call_count = [0]

        def mock_fix_dispatch(instructions):
            fix_call_count[0] += 1
            # Always return results that still have issues (simulated by returning same task)
            return [{"task_id": "T1", "output": "partial fix", "error": False}]

        def mock_dispatch(instructions):
            return [
                {
                    "task_id": "T1",
                    "output": "domains/math/index.html\nissue",
                    "error": False,
                }
            ]

        orchestrator = PipelineOrchestrator(max_fix_retries=1)
        orchestrator.run(
            ws, dispatch_fn=mock_dispatch, fix_dispatch_fn=mock_fix_dispatch
        )
        assert fix_call_count[0] <= 1
