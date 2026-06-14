# Phase 3 — Auditor

"""
Auditor takes a list of DiffResults and produces AuditReports.

INPUT:  list[DiffResult]
OUTPUT: list[AuditReport] — one per DiffResult (1:1 mapping)

Checklist (from AGENTS.md §2.2 Phase 3):
  1. Korean/encoding — edit tool failure patterns
  2. Message uniqueness — querySelector in static HTML/JS
  3. Context Route Gate — just route procedure compliance
  4. Partial Edit rules — oldString != newString, single match
"""

from __future__ import annotations

import re
from scripts.agent.orchestration.spec import (
    DiffResult,
    AuditReport,
    AuditFinding,
    AuditSeverity,
    AuditCategory,
    TaskStatus,
)


# ── Individual check functions ───────────────────────────────────────────────


def check_korean_encoding(diff_result: DiffResult) -> list[AuditFinding]:
    """Check for Korean text that may cause edit tool failures.

    Symptom: edit tool returns 'JSON parsing failed' on Korean content.
    Rule: AGENTS.md section 4.1 — Korean/large content should use bash + cat << 'EOF'.
    """
    findings: list[AuditFinding] = []
    if diff_result.status != TaskStatus.DONE:
        return findings

    # Heuristic: look for Korean characters in diff summaries that suggest
    # direct edit tool usage with Korean content
    korean_pattern = re.compile(r"[\uac00-\ud7af\u3130-\u318f\u1100-\u11ff]")
    if korean_pattern.search(diff_result.diff_summary):
        findings.append(
            AuditFinding(
                category=AuditCategory.KOREAN_ENCODING,
                severity=AuditSeverity.MEDIUM,
                file_path=diff_result.files_modified[0] if diff_result.files_modified else "",
                description="Korean text detected in diff — verify edit tool was not used directly with Korean content",
                evidence=f"Diff summary contains Korean characters: {diff_result.diff_summary[:100]}",
                suggested_fix="Use bash + cat << 'EOF' or python3 -c for Korean content changes",
            )
        )
    return findings


def check_query_selector_uniqueness(diff_result: DiffResult) -> list[AuditFinding]:
    """Check for duplicate text that would break querySelector/getByText.

    Rule: AGENTS.md §4.2 — messages must have unique identifiers.
    Bad: "적정"  Good: "수학 3학년 1단원 정답"
    """
    findings: list[AuditFinding] = []
    if diff_result.status != TaskStatus.DONE:
        return findings

    html_js_files = [f for f in diff_result.files_modified if f.endswith((".html", ".js"))]
    if not html_js_files:
        return findings

    # Look for short text strings that might be duplicated
    short_text_pattern = re.compile(r'"([^"]{2,15})"')
    text_counts: dict[str, int] = {}

    for line in diff_result.diff_summary.splitlines():
        # Check if this line belongs to any of the modified HTML/JS files
        # Either the file path appears in the line, or we scan all lines
        # when no clear file-path-per-line format is used
        belongs = any(fp in line for fp in html_js_files)
        if not belongs:
            # If no file path found in line, still check for quoted text
            # (diff summaries often have filename on first line only)
            pass
        for match in short_text_pattern.finditer(line):
            text = match.group(1)
            if text not in ('', ' ', 'class', 'id', 'data-'):
                text_counts[text] = text_counts.get(text, 0) + 1

    for text, count in text_counts.items():
        if count > 2:
            findings.append(
                AuditFinding(
                    category=AuditCategory.QUERY_SELECTOR_UNIQUENESS,
                    severity=AuditSeverity.HIGH if count > 5 else AuditSeverity.MEDIUM,
                    file_path=html_js_files[0],
                    description=f"Text '{text}' appears {count} times — may break querySelector",
                    evidence=f"Found {count} occurrences across modified files",
                    suggested_fix="Add unique identifiers (e.g., subject+grade+lesson) to make each message unique",
                )
            )
    return findings


def check_context_route_gate(diff_result: DiffResult) -> list[AuditFinding]:
    """Check whether Context Route Gate procedure was followed.

    Rule: routing.md §2 — must run `just route <paths> --json --write-manifest`
    before editing, then must_read, then route-read, then route-gate-check.
    """
    findings: list[AuditFinding] = []
    if diff_result.status != TaskStatus.DONE:
        return findings

    # Heuristic: check if diff summary mentions route gate compliance
    route_mentions = [
        "just route",
        "route-gate-check",
        "must_read",
        "route-read",
        "context route",
    ]
    has_route_evidence = any(
        rm.lower() in diff_result.diff_summary.lower()
        for rm in route_mentions
    )

    if not has_route_evidence and diff_result.files_modified:
        findings.append(
            AuditFinding(
                category=AuditCategory.CONTEXT_ROUTE_GATE,
                severity=AuditSeverity.HIGH,
                file_path=diff_result.files_modified[0],
                description="No evidence of Context Route Gate procedure in diff output",
                evidence="Diff summary does not mention `just route`, `route-gate-check`, or `must_read`",
                suggested_fix="Run `just route <paths> --json --write-manifest` → Read must_read → `just route-read` → `just route-gate-check` before editing",
            )
        )
    return findings


def check_partial_edit_rules(diff_result: DiffResult) -> list[AuditFinding]:
    """Check partial edit tool compliance.

    Rules:
      - oldString != newString (no identical pairs)
      - Single match only (oldString appears exactly once)
      - Byte-identical oldString from disk
    """
    findings: list[AuditFinding] = []
    if diff_result.status != TaskStatus.DONE:
        return findings

    # Check for "No changes to apply" or identical pair indicators
    no_change_patterns = [
        "no changes to apply",
        "identical",
        "oldString and newString are identical",
        "no change",
    ]
    for pattern in no_change_patterns:
        if pattern in diff_result.diff_summary.lower():
            findings.append(
                AuditFinding(
                    category=AuditCategory.PARTIAL_EDIT_RULES,
                    severity=AuditSeverity.MEDIUM,
                    file_path=diff_result.files_modified[0] if diff_result.files_modified else "",
                    description=f"Edit tool reported: '{pattern}' — possible identical old/new pair",
                    evidence=diff_result.diff_summary[:200],
                    suggested_fix="Verify oldString != newString before calling edit tool; re-read disk for exact content",
                )
            )
            break

    return findings


# ── Main audit function ─────────────────────────────────────────────────────


def audit(
    diff_results: list[DiffResult],
) -> list[AuditReport]:
    """Run all checklist items against each DiffResult.

    INPUT:  list[DiffResult] from Phase 2
    OUTPUT: list[AuditReport] — one per DiffResult, 1:1 mapping

    Each AuditReport contains findings from all checklist categories.
    """
    all_checkers = [
        check_korean_encoding,
        check_query_selector_uniqueness,
        check_context_route_gate,
        check_partial_edit_rules,
    ]

    reports: list[AuditReport] = []
    for dr in diff_results:
        report = AuditReport(task_id=dr.task_id)
        for checker in all_checkers:
            report.findings.extend(checker(dr))
        reports.append(report)

    return reports


def has_blocking_issues(reports: list[AuditReport]) -> bool:
    """Return True if any report has HIGH severity findings."""
    return any(r.has_blocking_issues for r in reports)


def summary(reports: list[AuditReport]) -> str:
    """Human-readable summary of all audit findings."""
    total_high = sum(r.high_count for r in reports)
    total_medium = sum(r.medium_count for r in reports)
    total_low = sum(r.low_count for r in reports)
    total_tasks = len(reports)
    tasks_with_issues = sum(1 for r in reports if r.findings)

    return (
        f"Audit summary: {total_tasks} tasks reviewed, "
        f"{tasks_with_issues} with issues. "
        f"High: {total_high}, Medium: {total_medium}, Low: {total_low}"
    )
