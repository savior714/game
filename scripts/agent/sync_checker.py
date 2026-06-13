#!/usr/bin/env python3
"""Integrity-check orchestration for the Unified Sync Engine.

Extracted from ``scripts/agent/sync.py`` as part of IMP-014 module split.
"""

from __future__ import annotations

from scripts.agent.code_sync import check_all_locks
from scripts.agent.sync_report import append_drift_snapshot, print_spec_alignment_result
from scripts.agent.sync_specdrift import (
    auto_fix_suggested_drift,
    classify_spec_drift,
    git_changed_paths,
    verify_spec_alignment,
)


def run_check(*, strict: bool, ack_spec: bool, fix: bool, skip_spec_check: bool = False) -> int:
    """Full integrity check: code-lock integrity + spec-drift alignment."""
    # 1. Code lock integrity
    violations = check_all_locks()
    if violations > 0:
        print("\n❌ [FAIL] Code integrity lock violation(s) detected.")
        print("   Fix the locked code or run `just sync --update <id>` to refresh the hash.")
        return 1

    if skip_spec_check:
        print("\n⏭️  Skipping spec alignment verification (--skip-spec-check).")
        print("\n📊 Summary: code locks OK · spec alignment SKIPPED")
        return 0

    # 2. Spec drift classification + alignment (docs touched / candidate specs / --ack-spec)
    changed = git_changed_paths()
    classification = classify_spec_drift(changed)
    level = classification["level"]
    print(f"\n🔍 Spec drift level: {level}")
    print(f"   Reason: {classification['reason']}")

    spec_ok, spec_report = verify_spec_alignment(
        changed, classification, ack_spec=ack_spec
    )

    # Auto-fix suggested drift if --fix is set
    if fix and level == "suggested" and not spec_report.get("docs_touched"):
        raw = spec_report.get("missing_specs") or []
        candidates: list[str] = list(raw) if isinstance(raw, list) else []  # type: ignore[assignment]
        if candidates:
            fixed = auto_fix_suggested_drift(candidates)
            if fixed > 0:
                print(f"\n🔧 Auto-fixed {fixed} candidate spec(s) (Last Verified updated).")
                # Re-verify after fix
                spec_ok, spec_report = verify_spec_alignment(
                    changed, classification, ack_spec=ack_spec
                )

    print_spec_alignment_result(spec_ok, spec_report)

    if not spec_ok:
        return 1

    if (
        strict
        and level == "required"
        and not spec_report.get("docs_touched")
        and not ack_spec
        and spec_report.get("missing_specs")
    ):
        print(
            "\n❌ [FAIL] Strict mode: required drift — "
            "commit docs/specs or knowledge updates, or use --ack-spec with documented reason."
        )
        return 2

    print("\n📊 Summary: code locks OK · spec alignment OK")

    # Append drift snapshot to rolling history
    missing = spec_report.get("missing_specs") or []
    drift_count = len(missing) if isinstance(missing, list) else 0
    append_drift_snapshot(drift_count=drift_count)

    return 0
