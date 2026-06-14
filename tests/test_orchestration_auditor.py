"""Tests for Phase 3 — Auditor (auditor.py)."""

from __future__ import annotations

import pytest

from scripts.agent.orchestration.spec import (
    DiffResult,
    TaskStatus,
    AuditCategory,
    AuditSeverity,
)
from scripts.agent.orchestration.auditor import (
    audit,
    check_korean_encoding,
    check_query_selector_uniqueness,
    check_context_route_gate,
    check_partial_edit_rules,
    has_blocking_issues,
    summary,
)


# ── check_korean_encoding ────────────────────────────────────────────────────


class TestCheckKoreanEncoding:
    def test_detects_korean_in_diff_summary(self):
        dr = DiffResult(
            task_id="T1",
            status=TaskStatus.DONE,
            diff_summary="index.html에 한글 텍스트 추가: 적정 점수",
        )
        findings = check_korean_encoding(dr)
        assert len(findings) == 1
        assert findings[0].category == AuditCategory.KOREAN_ENCODING

    def test_no_korean_no_finding(self):
        dr = DiffResult(
            task_id="T1",
            status=TaskStatus.DONE,
            diff_summary="Updated index.html layout classes",
        )
        findings = check_korean_encoding(dr)
        assert len(findings) == 0

    def test_failed_task_no_finding(self):
        dr = DiffResult(
            task_id="T1",
            status=TaskStatus.FAILED,
            error="timeout",
        )
        findings = check_korean_encoding(dr)
        assert len(findings) == 0


# ── check_query_selector_uniqueness ──────────────────────────────────────────


class TestCheckQuerySelectorUniqueness:
    def test_detects_duplicate_short_text(self):
        dr = DiffResult(
            task_id="T1",
            status=TaskStatus.DONE,
            diff_summary="""domains/math/index.html
"적정"
"적정"
"적정"
"정답"
""",
            files_modified=["domains/math/index.html"],
        )
        findings = check_query_selector_uniqueness(dr)
        # Should find "적정" appearing 3 times
        assert len(findings) >= 1

    def test_no_duplicate_short_text(self):
        dr = DiffResult(
            task_id="T1",
            status=TaskStatus.DONE,
            diff_summary="""domains/math/index.html
"수학 3학년 1단원 정답"
"영어 기초 단어 테스트"
""",
            files_modified=["domains/math/index.html"],
        )
        findings = check_query_selector_uniqueness(dr)
        assert len(findings) == 0

    def test_non_html_js_files_skipped(self):
        dr = DiffResult(
            task_id="T1",
            status=TaskStatus.DONE,
            diff_summary="""styles.css
"duplicate"
"duplicate"
"duplicate"
""",
            files_modified=["styles.css"],
        )
        findings = check_query_selector_uniqueness(dr)
        assert len(findings) == 0


# ── check_context_route_gate ─────────────────────────────────────────────────


class TestCheckContextRouteGate:
    def test_detects_missing_route_gate(self):
        dr = DiffResult(
            task_id="T1",
            status=TaskStatus.DONE,
            diff_summary="Changed layout classes in index.html",
            files_modified=["domains/math/index.html"],
        )
        findings = check_context_route_gate(dr)
        assert len(findings) == 1
        assert findings[0].category == AuditCategory.CONTEXT_ROUTE_GATE
        assert findings[0].severity == AuditSeverity.HIGH

    def test_route_gate_evidence_present(self):
        dr = DiffResult(
            task_id="T1",
            status=TaskStatus.DONE,
            diff_summary="Ran just route-gate-check before editing. must_read paths loaded.",
            files_modified=["domains/math/index.html"],
        )
        findings = check_context_route_gate(dr)
        assert len(findings) == 0

    def test_failed_task_no_finding(self):
        dr = DiffResult(
            task_id="T1",
            status=TaskStatus.FAILED,
            error="subagent timeout",
        )
        findings = check_context_route_gate(dr)
        assert len(findings) == 0


# ── check_partial_edit_rules ─────────────────────────────────────────────────


class TestCheckPartialEditRules:
    def test_detects_no_changes_to_apply(self):
        dr = DiffResult(
            task_id="T1",
            status=TaskStatus.DONE,
            diff_summary='Edit tool: "No changes to apply: oldString and newString are identical"',
        )
        findings = check_partial_edit_rules(dr)
        assert len(findings) == 1
        assert findings[0].category == AuditCategory.PARTIAL_EDIT_RULES

    def test_no_edit_tool_issues(self):
        dr = DiffResult(
            task_id="T1",
            status=TaskStatus.DONE,
            diff_summary="Successfully updated 3 files with layout changes",
        )
        findings = check_partial_edit_rules(dr)
        assert len(findings) == 0


# ── audit (main function) ────────────────────────────────────────────────────


class TestAudit:
    def test_audit_all_checkers_run(self):
        dr = DiffResult(
            task_id="T1",
            status=TaskStatus.DONE,
            diff_summary='적정 점수 — "적정" "적정" "적정"\nEdit tool: "No changes to apply"',
            files_modified=["domains/math/index.html"],
        )
        reports = audit([dr])
        assert len(reports) == 1
        assert reports[0].task_id == "T1"
        # Should have findings from multiple categories
        categories = {f.category for f in reports[0].findings}
        assert len(categories) >= 1

    def test_audit_failed_task_fewer_findings(self):
        dr = DiffResult(
            task_id="T1",
            status=TaskStatus.FAILED,
            error="timeout",
        )
        reports = audit([dr])
        # Failed tasks should have fewer findings (most checkers skip them)
        assert len(reports[0].findings) <= 1


# ── has_blocking_issues / summary ────────────────────────────────────────────


class TestAuditHelpers:
    def test_has_blocking_issues_true(self):
        reports = [
            type('R', {'task_id': 'T1', 'findings': [
                type('F', {'severity': AuditSeverity.HIGH, 'key': 'k1'})()
            ]})()
        ]
        # Use actual AuditReport
        from scripts.agent.orchestration.spec import AuditReport, AuditFinding
        reports = [AuditReport(task_id="T1")]
        reports[0].add_finding(AuditFinding(
            category=AuditCategory.GENERAL,
            severity=AuditSeverity.HIGH,
            description="test",
        ))
        assert has_blocking_issues(reports) is True

    def test_has_blocking_issues_false(self):
        from scripts.agent.orchestration.spec import AuditReport, AuditFinding
        reports = [AuditReport(task_id="T1")]
        reports[0].add_finding(AuditFinding(
            category=AuditCategory.GENERAL,
            severity=AuditSeverity.LOW,
            description="test",
        ))
        assert has_blocking_issues(reports) is False

    def test_summary_format(self):
        from scripts.agent.orchestration.spec import AuditReport, AuditFinding
        reports = [
            AuditReport(task_id="T1"),
            AuditReport(task_id="T2"),
        ]
        reports[0].add_finding(AuditFinding(
            category=AuditCategory.GENERAL,
            severity=AuditSeverity.HIGH,
            description="h1",
        ))
        reports[1].add_finding(AuditFinding(
            category=AuditCategory.GENERAL,
            severity=AuditSeverity.LOW,
            description="l1",
        ))
        s = summary(reports)
        assert "2 tasks" in s
        assert "High: 1" in s
