"""Plan reference collection and resolution."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from scripts.plan_archive.constants import (
    ARCHIVE,
    CHECK_SKIP_PATH_PARTS,
    LEGACY_PLANS,
    PLAN_BASENAME_ALIASES,
    PLAN_REF_PATTERN,
    PLANS,
    REPO_ROOT,
    SKIP_DIRS,
    TEMPLATE_PLAN_PLACEHOLDER_BASENAMES,
    TEXT_SUFFIXES,
)


def iter_text_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield p


def normalize_name(name: str) -> str:
    name = name.strip()
    if not name.endswith(".md"):
        name += ".md"
    if "/" in name or name.startswith(".."):
        raise ValueError(f"파일명만 지정하세요(경로 금지): {name!r}")
    return name


def canonical_plan_basename(basename: str) -> str:
    return PLAN_BASENAME_ALIASES.get(basename, basename)


def _rglob_plan_named(root: Path, basename: str) -> list[Path]:
    if not root.is_dir():
        return []
    return [p for p in root.rglob(basename) if p.is_file() and p.name == basename]


def find_archived_plan(basename: str) -> Path | None:
    """docs/plans/archive/ 내 basename 위치 탐색 (별칭·하위 폴더 포함)."""
    canon = canonical_plan_basename(basename)
    direct = ARCHIVE / canon
    if direct.is_file():
        return direct
    matches = _rglob_plan_named(ARCHIVE, canon)
    if not matches:
        return None
    if len(matches) > 1:
        print(
            f"경고: archive 내 '{canon}' 중복 {len(matches)}건 — 첫 경로 사용: "
            f"{matches[0].relative_to(REPO_ROOT)}",
            file=sys.stderr,
        )
    return matches[0]


def find_legacy_archived_plan(basename: str) -> Path | None:
    """docs/archive/plans/ 레거시 보관 경로 탐색."""
    canon = canonical_plan_basename(basename)
    direct = LEGACY_PLANS / canon
    if direct.is_file():
        return direct
    matches = _rglob_plan_named(LEGACY_PLANS, canon)
    return matches[0] if matches else None


def resolve_plan_reference(basename: str) -> str | None:
    """docs/plans/<basename> 참조가 가리켜야 할 repo-relative 경로."""
    canon = canonical_plan_basename(basename)
    root_path = PLANS / canon
    if root_path.is_file():
        return root_path.relative_to(REPO_ROOT).as_posix()
    arch = find_archived_plan(basename)
    if arch is not None:
        return arch.relative_to(REPO_ROOT).as_posix()
    legacy = find_legacy_archived_plan(basename)
    if legacy is not None:
        return legacy.relative_to(REPO_ROOT).as_posix()
    return None


def plan_reference_exists(basename: str) -> bool:
    return resolve_plan_reference(basename) is not None


def should_skip_check_path(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT).as_posix()
    return any(part in rel for part in CHECK_SKIP_PATH_PARTS)


DISCUSS_LINKED_PLAN_RE = re.compile(r"^linked_plan:\s*(.*?)\s*$", re.MULTILINE)


def collect_missing_plan_refs() -> dict[str, list[str]]:
    missing: dict[str, list[str]] = {}
    for path in iter_text_files(REPO_ROOT):
        if should_skip_check_path(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in PLAN_REF_PATTERN.finditer(text):
            base = m.group(1)
            if base in TEMPLATE_PLAN_PLACEHOLDER_BASENAMES:
                continue
            if plan_reference_exists(base):
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            missing.setdefault(base, []).append(rel)

    # DISCUSS frontmatter linked_plan 중 파일 없는 것 추가 감지
    discussions_dir = REPO_ROOT / "docs" / "discussions"
    if discussions_dir.is_dir():
        for path in sorted(discussions_dir.glob("DISCUSS_*.md")):
            if "/archive/" in path.as_posix():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            m = DISCUSS_LINKED_PLAN_RE.search(text)
            if not m:
                continue
            value = m.group(1).strip()
            if not value or value in ("", '""', "null", "~", "none"):
                continue
            import re as _re
            plan_name_match = _re.search(r"(PLAN_[A-Za-z0-9_.-]+\.md)", value)
            if not plan_name_match:
                continue
            linked_basename = plan_name_match.group(1)
            if not plan_reference_exists(linked_basename):
                rel = path.relative_to(REPO_ROOT).as_posix()
                missing.setdefault(linked_basename, []).append(rel)

    return missing
