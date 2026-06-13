#!/usr/bin/env python3
"""Unified Sync Engine (Code Lock & Spec Drift Gate).

Combines code integrity locks (code-sync) and spec-to-code reverse verification (spec-sync)
into a single CLI. Command parsing and execution orchestration live here; the
implementation is split across sibling modules:

  - ``code_sync``      — code integrity lock hashing / scan / apply / update
  - ``sync_specdrift`` — git-diff spec-drift classification & alignment
  - ``sync_report``    — footer + terminal report rendering
  - ``sync_cli``       — CLI argument parsing and main entry point (IMP-014)
  - ``sync_checker``   — integrity-check orchestration (IMP-014)

Usage:
  python3 scripts/agent/sync.py --check          # full integrity check (code-lock + spec-drift)
  python3 scripts/agent/sync.py --check --fix    # auto-fix suggested drift (update metadata)
  python3 scripts/agent/sync.py --check --strict # fail on required drift (CI gate)
  python3 scripts/agent/sync.py --lock <id> --file <path>   # auto-insert lock or fill hash
  python3 scripts/agent/sync.py --lock <id> --file <path> --lines 10-30   # specify line range
  python3 scripts/agent/sync.py --update <id>     # refresh hash after legitimate change
"""

from __future__ import annotations

# Re-export all public names so existing imports (tests, scripts) keep working.
from scripts.agent.code_sync import (
    LOCK_PATTERN,
    UNLOCK_PATTERN,
    apply_lock,
    check_all_locks,
    compute_normalized_hash,
    iter_source_files,
    parse_metadata,
    scan_file_locks,
    update_lock,
)
from scripts.agent.sync_checker import run_check
from scripts.agent.sync_cli import main
from scripts.agent.sync_report import print_spec_alignment_result
from scripts.agent.sync_specdrift import (
    DOC_PATH_PREFIXES,
    HIGH_PATTERNS,
    MEDIUM_PATTERNS,
    REPO_ROOT,
    ROUTE_HINTS,
    auto_fix_suggested_drift,
    classify_spec_drift,
    collect_candidate_spec_paths,
    extract_specs_from_changed_files,
    git_changed_paths,
    verify_spec_alignment,
)

__all__ = [
    "DOC_PATH_PREFIXES",
    "HIGH_PATTERNS",
    "LOCK_PATTERN",
    "MEDIUM_PATTERNS",
    "REPO_ROOT",
    "ROUTE_HINTS",
    "UNLOCK_PATTERN",
    "apply_lock",
    "auto_fix_suggested_drift",
    "check_all_locks",
    "classify_spec_drift",
    "collect_candidate_spec_paths",
    "compute_normalized_hash",
    "extract_specs_from_changed_files",
    "git_changed_paths",
    "iter_source_files",
    "main",
    "parse_metadata",
    "print_spec_alignment_result",
    "run_check",
    "scan_file_locks",
    "update_lock",
    "verify_spec_alignment",
]

if __name__ == "__main__":
    import sys

    sys.exit(main())
