"""Plan archive package — collect, validate, move, rewrite."""

from scripts.plan_archive.collect import (
    canonical_plan_basename,
    collect_missing_plan_refs,
    find_archived_plan,
    iter_text_files,
    normalize_name,
    plan_reference_exists,
    resolve_plan_reference,
    should_skip_check_path,
)
from scripts.plan_archive.constants import (
    ARCHIVE,
    LEGACY_PLANS,
    PLAN_BASENAME_ALIASES,
    PLAN_REF_PATTERN,
    PLANS,
    REPO_ROOT,
)
from scripts.plan_archive.move import cmd_archive, cmd_sweep, cmd_unarchive
from scripts.plan_archive.rewrite import rewrite_to_archive
from scripts.plan_archive.validate import (
    cmd_check,
    cmd_guard_deleted,
    cmd_repair,
    run_unified_sync_check,
)

__all__ = [
    "ARCHIVE",
    "LEGACY_PLANS",
    "PLAN_BASENAME_ALIASES",
    "PLAN_REF_PATTERN",
    "PLANS",
    "REPO_ROOT",
    "canonical_plan_basename",
    "cmd_archive",
    "cmd_check",
    "cmd_guard_deleted",
    "cmd_repair",
    "cmd_sweep",
    "cmd_unarchive",
    "collect_missing_plan_refs",
    "find_archived_plan",
    "iter_text_files",
    "normalize_name",
    "plan_reference_exists",
    "resolve_plan_reference",
    "rewrite_to_archive",
    "run_unified_sync_check",
    "should_skip_check_path",
]
