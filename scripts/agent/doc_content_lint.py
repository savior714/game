#!/usr/bin/env python3
"""Hybrid content-quality lint for agent pre-read documents.

FAIL: broken internal cross-refs, explicit MUST vs MUST NOT conflicts in a section.
WARN: stale last_verified, duplicate MUST lines — merged into assess queue JSON.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from scripts.agent.verify_rules import verify_links

Severity = Literal["fail", "warn"]

SCAN_ROOTS = (".agents", "docs/knowledge")
WARNINGS_REL = Path("docs/agent-context/memory/doc_quality_warnings.json")
DEFAULT_STALE_DAYS = 90
MAX_FILES_CAP = 500
# Assess queue triggers (RES_agent_context_gate §1 — B+D)
ASSESS_WARN_TOTAL = 50
ASSESS_WARN_DELTA = 20

SECTION_SPLIT = re.compile(r"(?=^##\s)", re.MULTILINE)
MUST_PATTERN = re.compile(r"\bMUST\s+(?!NOT\b)(.+)", re.IGNORECASE)
MUST_NOT_PATTERN = re.compile(r"\bMUST\s+NOT\s+(.+)", re.IGNORECASE)
LAST_VERIFIED_PATTERNS = (
    re.compile(r"^last_verified:\s*(\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE | re.IGNORECASE),
    re.compile(
        r"\*\*Last Verified\*\*:\s*(\d{4}-\d{2}-\d{2})",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class DocLintIssue:
    severity: Severity
    file: str
    rule: str
    message: str


@dataclass
class DocLintReport:
    fails: list[DocLintIssue] = field(default_factory=list)
    warns: list[DocLintIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.fails


def _normalize_normative(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower().rstrip("."))


def _iter_markdown_files(repo_root: Path, *, max_files: int) -> list[Path]:
    files: list[Path] = []
    for root_name in SCAN_ROOTS:
        base = repo_root / root_name
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            if "vendor" in path.parts:
                continue
            if path.name == "COMPILED.md":
                continue
            files.append(path)
            if len(files) >= max_files:
                return files
    return files


def _cross_ref_severity(rel: str) -> Severity:
    """Tier-1 FAIL: `.agents/**`. Tier-2 FAIL: `docs/knowledge/<file>.md` (루트). 하위는 WARN."""
    parts = Path(rel).parts
    if parts and parts[0] == ".agents":
        return "fail"
    if len(parts) >= 2 and parts[0] == "docs" and parts[1] == "knowledge":
        if len(parts) == 3:
            return "fail"
        return "warn"
    return "fail"


def assess_trigger_message(
    warnings_path: Path,
    *,
    warn_total_threshold: int = ASSESS_WARN_TOTAL,
    warn_delta_threshold: int = ASSESS_WARN_DELTA,
) -> str | None:
    """Return human-readable assess trigger reason, or None if no trigger."""
    if not warnings_path.is_file():
        return None
    try:
        data = json.loads(warnings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    warnings = data.get("warnings", [])
    if not isinstance(warnings, list):
        return None
    count = len(warnings)
    prev = int(data.get("last_assess_snapshot_count", 0))
    if count >= warn_total_threshold:
        return f"WARN 총 {count}건 ≥ {warn_total_threshold} — assess 후보"
    if count - prev >= warn_delta_threshold:
        return f"WARN +{count - prev}건(≥{warn_delta_threshold}) since last snapshot — assess 후보"
    return None


def check_broken_cross_refs(repo_root: Path, files: list[Path]) -> list[DocLintIssue]:
    issues: list[DocLintIssue] = []
    for path in files:
        rel = str(path.relative_to(repo_root))
        severity = _cross_ref_severity(rel)
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(
                DocLintIssue(
                    severity,
                    rel,
                    "broken_cross_ref",
                    f"Failed to read file: {exc}",
                )
            )
            continue
        for err in verify_links(path, content):
            issues.append(
                DocLintIssue(
                    severity,
                    rel,
                    "broken_cross_ref",
                    err,
                )
            )
    return issues


def _section_conflicts(section_text: str) -> list[str]:
    musts = [_normalize_normative(m.group(1)) for m in MUST_PATTERN.finditer(section_text)]
    must_nots = [
        _normalize_normative(m.group(1)) for m in MUST_NOT_PATTERN.finditer(section_text)
    ]
    conflicts: list[str] = []
    for subject in musts:
        if subject in must_nots:
            conflicts.append(f"MUST and MUST NOT conflict on: {subject}")
    return conflicts


def check_must_conflicts(repo_root: Path, files: list[Path]) -> list[DocLintIssue]:
    issues: list[DocLintIssue] = []
    for path in files:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = str(path.relative_to(repo_root))
        for section in SECTION_SPLIT.split(content):
            if not section.strip():
                continue
            for msg in _section_conflicts(section):
                issues.append(
                    DocLintIssue("fail", rel, "must_conflict", msg),
                )
    return issues


def _parse_last_verified(content: str) -> date | None:
    for pattern in LAST_VERIFIED_PATTERNS:
        match = pattern.search(content)
        if match:
            try:
                return date.fromisoformat(match.group(1))
            except ValueError:
                return None
    return None


def check_stale_last_verified(
    repo_root: Path,
    files: list[Path],
    *,
    stale_days: int = DEFAULT_STALE_DAYS,
    today: date | None = None,
) -> list[DocLintIssue]:
    ref = today or date.today()
    cutoff = ref - timedelta(days=stale_days)
    issues: list[DocLintIssue] = []
    for path in files:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        verified = _parse_last_verified(content)
        if verified is None:
            continue
        if verified < cutoff:
            issues.append(
                DocLintIssue(
                    "warn",
                    str(path.relative_to(repo_root)),
                    "stale_last_verified",
                    f"last_verified {verified.isoformat()} is older than {stale_days} days",
                )
            )
    return issues


def check_duplicate_must_blocks(repo_root: Path, files: list[Path]) -> list[DocLintIssue]:
    issues: list[DocLintIssue] = []
    line_pat = re.compile(r"^\s*(?:[-*]\s+)?(?:\*\*)?MUST\b", re.IGNORECASE | re.MULTILINE)
    for path in files:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        counts: dict[str, int] = {}
        for match in line_pat.finditer(content):
            line = content[match.start() : content.find("\n", match.start())]
            norm = _normalize_normative(line)
            if len(norm) < 12:
                continue
            counts[norm] = counts.get(norm, 0) + 1
        for line, count in counts.items():
            if count >= 2:
                issues.append(
                    DocLintIssue(
                        "warn",
                        str(path.relative_to(repo_root)),
                        "duplicate_must_block",
                        f"Duplicate MUST line ({count}x): {line[:120]}",
                    )
                )
    return issues


def merge_warnings_file(
    warnings_path: Path,
    warns: list[DocLintIssue],
) -> None:
    warnings_path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {"warnings": []}
    if warnings_path.is_file():
        try:
            existing = json.loads(warnings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {"warnings": []}
    keyed = {
        (w["file"], w["rule"], w["message"]): w
        for w in existing.get("warnings", [])
        if isinstance(w, dict)
    }
    for issue in warns:
        keyed[(issue.file, issue.rule, issue.message)] = {
            "file": issue.file,
            "rule": issue.rule,
            "message": issue.message,
            "severity": issue.severity,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
    merged = list(keyed.values())
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "warnings": merged,
        "warning_count": len(merged),
        "assess_policy": {
            "warn_total": ASSESS_WARN_TOTAL,
            "warn_delta": ASSESS_WARN_DELTA,
            "cadence": "weekly_or_on_trigger",
        },
    }
    warnings_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def prune_warnings(
    repo_root: Path,
    *,
    warnings_path: Path | None = None,
    max_files: int = MAX_FILES_CAP,
    stale_days: int = DEFAULT_STALE_DAYS,
    today: date | None = None,
) -> dict:
    """Run a fresh scan and keep only WARN entries that match current results.

    Removes stale / ghost WARN entries from the warnings JSON file that no
    longer correspond to actual issues in the repository.
    """
    root = repo_root.resolve()
    files = _iter_markdown_files(root, max_files=max_files)

    # Build set of current warn keys
    current_keys: set[tuple[str, str, str]] = set()

    # broken_cross_ref warns
    for issue in check_broken_cross_refs(root, files):
        if issue.severity == "warn":
            current_keys.add((issue.file, issue.rule, issue.message))

    # stale_last_verified warns
    for issue in check_stale_last_verified(root, files, stale_days=stale_days, today=today):
        current_keys.add((issue.file, issue.rule, issue.message))

    # duplicate_must_block warns
    for issue in check_duplicate_must_blocks(root, files):
        current_keys.add((issue.file, issue.rule, issue.message))

    # Prune the warnings file
    out = warnings_path or (root / WARNINGS_REL)
    if not out.is_file():
        return {"removed": 0, "remaining": 0}

    try:
        data = json.loads(out.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {"warnings": []}

    warnings = data.get("warnings", [])
    if not isinstance(warnings, list):
        warnings = []

    pruned = [w for w in warnings if (w.get("file", ""), w.get("rule", ""), w.get("message", "")) in current_keys]
    removed = len(warnings) - len(pruned)

    data["warnings"] = pruned
    data["warning_count"] = len(pruned)
    data["pruned_at"] = datetime.now(timezone.utc).isoformat()
    data["removed_count"] = removed

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {"removed": removed, "remaining": len(pruned)}


def run(
    repo_root: Path | None = None,
    *,
    warnings_path: Path | None = None,
    write_warnings: bool = True,
    max_files: int = MAX_FILES_CAP,
    stale_days: int = DEFAULT_STALE_DAYS,
    today: date | None = None,
) -> DocLintReport:
    root = (repo_root or Path.cwd()).resolve()
    files = _iter_markdown_files(root, max_files=max_files)
    report = DocLintReport()
    cross_ref_issues = check_broken_cross_refs(root, files)
    for issue in cross_ref_issues:
        if issue.severity == "fail":
            report.fails.append(issue)
        else:
            report.warns.append(issue)
    report.fails.extend(check_must_conflicts(root, files))
    report.warns.extend(check_stale_last_verified(root, files, stale_days=stale_days, today=today))
    report.warns.extend(check_duplicate_must_blocks(root, files))
    if write_warnings and report.warns:
        out = warnings_path or (root / WARNINGS_REL)
        merge_warnings_file(out, report.warns)
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Agent document content quality lint")
    parser.add_argument(
        "--warnings-path",
        type=Path,
        default=None,
        help="Override warnings JSON path (default: docs/agent-context/memory/doc_quality_warnings.json)",
    )
    parser.add_argument(
        "--no-write-warnings",
        action="store_true",
        help="Do not merge WARN entries into the warnings queue file",
    )
    parser.add_argument("--max-files", type=int, default=MAX_FILES_CAP)
    parser.add_argument(
        "--assess-status",
        action="store_true",
        help="Print assess trigger hint from warnings JSON and exit",
    )
    parser.add_argument(
        "--assess-snapshot",
        action="store_true",
        help="Reset assess delta baseline to current warning count",
    )
    args = parser.parse_args(argv)

    out_path = args.warnings_path or (Path.cwd() / WARNINGS_REL)
    if args.assess_snapshot:
        count = snapshot_assess_count(out_path)
        print(f"📸 Assess snapshot recorded ({count} warnings)")
        return 0
    if args.assess_status:
        hint = assess_trigger_message(out_path)
        if hint:
            print(f"📋 {hint}")
            return 0
        print("✅ No assess trigger (WARN below thresholds)")
        return 0

    report = run(
        write_warnings=not args.no_write_warnings,
        warnings_path=args.warnings_path,
        max_files=args.max_files,
    )

    # Prune stale WARN entries that no longer correspond to current scan results
    if not args.no_write_warnings:
        prune_warnings(
            repo_root=Path.cwd(),
            max_files=args.max_files,
            warnings_path=args.warnings_path,
        )

    for issue in report.fails:
        print(f"FAIL [{issue.rule}] {issue.file}: {issue.message}")
    for issue in report.warns:
        print(f"WARN [{issue.rule}] {issue.file}: {issue.message}")
    if report.fails:
        print(f"\n❌ {len(report.fails)} content FAIL(s), {len(report.warns)} WARN(s)")
        return 1
    print(f"✨ Content lint OK ({len(report.warns)} WARN(s))")
    hint = assess_trigger_message(out_path)
    if hint:
        print(f"📋 Assess trigger: {hint}")
    return 0


def snapshot_assess_count(warnings_path: Path | None = None) -> int:
    """Record current warning count after assess review (resets delta trigger)."""
    path = warnings_path or (Path.cwd() / WARNINGS_REL)
    if not path.is_file():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    count = len(data.get("warnings", []))
    data["last_assess_snapshot_count"] = count
    data["last_assess_snapshot_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return count


if __name__ == "__main__":
    sys.exit(main())
