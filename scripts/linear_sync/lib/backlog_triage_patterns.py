"""Pattern detection for Linear backlog triage."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal

from scripts.linear_sync.lib.duplicate_guard import (
    LINEAR_ID_RE,
    extract_blueprint_path_from_description,
)
from scripts.linear_sync.lib.parser import PlanParser

_LOOSE_PLAN_PATH_RE = re.compile(r"(docs/plans/PLAN_[^\s`]+\.md)")
_TERMINAL_TASK_STATUSES = frozenset({"done", "cancelled", "canceled"})
_IN_PROGRESS_TASK_STATUSES = frozenset({"todo", "running", "blocked", "in_progress"})


class PatternKind(StrEnum):
    NO_PLAN = "no_plan"
    PLAN_ARCHIVED = "plan_archived"
    PLAN_DONE_ISSUE_OPEN = "plan_done_issue_open"


class PlanLifecycle(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    ALL_DONE = "all_done"
    IN_PROGRESS = "in_progress"


@dataclass(frozen=True)
class LinkedPlan:
    path: Path
    lifecycle: PlanLifecycle


@dataclass(frozen=True)
class RecommendedAction:
    verb: Literal["archive", "cancel"]


def _resolve_plan_path(raw: str, *, repo_root: Path) -> Path | None:
    rel = raw.replace("\\", "/").strip()
    if not rel:
        return None
    candidate = (repo_root / rel).resolve()
    if candidate.exists():
        return candidate
    alt = Path(rel)
    if alt.exists():
        return alt.resolve()
    # Fallback: try archive/ prefix if not found in docs/plans/
    if rel.startswith("docs/plans/") and not rel.startswith("docs/plans/archive/"):
        archive_rel = rel.replace("docs/plans/", "docs/plans/archive/", 1)
        archive_candidate = (repo_root / archive_rel).resolve()
        if archive_candidate.exists():
            return archive_candidate
    return None


def _lifecycle_for_path(plan_path: Path, *, repo_root: Path) -> PlanLifecycle:
    try:
        rel = plan_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        rel = plan_path.as_posix()
    if rel.startswith("docs/plans/archive/"):
        return PlanLifecycle.ARCHIVED
    return plan_task_aggregate(plan_path)


def plan_task_aggregate(plan_path: Path) -> PlanLifecycle:
    """Classify plan task statuses into lifecycle buckets."""
    if not plan_path.exists():
        return PlanLifecycle.IN_PROGRESS
    tasks = PlanParser().parse(plan_path)
    if not tasks:
        return PlanLifecycle.IN_PROGRESS
    statuses = {t.status.lower() for t in tasks}
    if statuses & _IN_PROGRESS_TASK_STATUSES:
        return PlanLifecycle.IN_PROGRESS
    if statuses <= _TERMINAL_TASK_STATUSES:
        return PlanLifecycle.ALL_DONE
    return PlanLifecycle.IN_PROGRESS


def _scan_plan_by_issue_identifier(identifier: str, *, repo_root: Path) -> Path | None:
    ident = identifier.upper()
    plans_root = repo_root / "docs" / "plans"
    if not plans_root.exists():
        return None

    active_match: Path | None = None
    archive_match: Path | None = None

    for path in plans_root.rglob("*.md"):
        if path.name == "README.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        tokens = {t.upper() for t in LINEAR_ID_RE.findall(text)}
        if ident not in tokens:
            continue
        try:
            rel_posix = path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            rel_posix = path.as_posix()
        if rel_posix.startswith("docs/plans/archive/"):
            archive_match = path
        else:
            active_match = path

    return active_match or archive_match


def resolve_linked_plan(issue: dict, *, repo_root: Path) -> LinkedPlan | None:
    """Resolve the first matching PLAN path for a Linear issue."""
    description = str(issue.get("description") or "")

    desc_path = extract_blueprint_path_from_description(description)
    if desc_path:
        resolved = _resolve_plan_path(desc_path, repo_root=repo_root)
        if resolved:
            return LinkedPlan(path=resolved, lifecycle=_lifecycle_for_path(resolved, repo_root=repo_root))

    identifier = str(issue.get("identifier") or "").upper()
    if identifier:
        scanned = _scan_plan_by_issue_identifier(identifier, repo_root=repo_root)
        if scanned:
            return LinkedPlan(path=scanned, lifecycle=_lifecycle_for_path(scanned, repo_root=repo_root))

    loose = _LOOSE_PLAN_PATH_RE.search(description)
    if loose:
        resolved = _resolve_plan_path(loose.group(1), repo_root=repo_root)
        if resolved:
            return LinkedPlan(path=resolved, lifecycle=_lifecycle_for_path(resolved, repo_root=repo_root))

    return None


def detect_pattern(linked: LinkedPlan | None) -> PatternKind | None:
    if linked is None:
        return PatternKind.NO_PLAN
    if linked.lifecycle == PlanLifecycle.ARCHIVED:
        return PatternKind.PLAN_ARCHIVED
    if linked.lifecycle == PlanLifecycle.ALL_DONE:
        return PatternKind.PLAN_DONE_ISSUE_OPEN
    return None


def recommend_action(pattern: PatternKind) -> RecommendedAction:
    return RecommendedAction(verb="archive")
