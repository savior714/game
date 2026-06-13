#!/usr/bin/env python3
"""docs/plans/archive/ 하위 폴더 분류 규칙 (archive_plans SSOT)."""

from __future__ import annotations

import re


KEEP_AT_ARCHIVE_ROOT = frozenset({"README.md"})


def classify_archive_subdir(filename: str) -> str:
    """Return archive subdirectory (e.g. 'refactor', 'blueprints', 'by-date/202606')."""
    if filename in KEEP_AT_ARCHIVE_ROOT:
        raise ValueError(f"cannot classify archive root file: {filename}")

    n = filename.lower()

    # Date-prefixed blueprints
    if re.match(r"^\d{8}_", n):
        return f"by-date/{n[:6]}"

    # DDD / 구조 재편
    if any(k in n for k in ("ddd", "structure_reorg", "folder_reorg", "architecture")):
        return "refactor"

    # Refactoring / 리팩터링
    if any(k in n for k in ("refactor", "reorg", "restructure", "cleanup")):
        return "refactor"

    # UI / 디자인 관련
    if any(k in n for k in ("ui", "design", "css", "style", "theme", "visual")):
        return "ui-design"

    # Auth / 인증 관련
    if any(k in n for k in ("auth", "login", "signup", "oauth", "supabase")):
        return "auth"

    # Game / 과목별 게임
    if any(k in n for k in ("math", "english", "korean", "science", "subject", "quiz")):
        return "games"

    # Experiment / 실험 모듈
    if any(k in n for k in ("experiment", "space-explorer", "marble", "dino", "orbit")):
        return "experiments"

    # Reward / 보상 시스템
    if any(k in n for k in ("reward", "gem", "inventory", "shop")):
        return "reward"

    # Sync / 동기화
    if any(k in n for k in ("sync", "cloud", "backup")):
        return "sync"

    # Event bus / 이벤트
    if any(k in n for k in ("event", "bus", "pubsub")):
        return "shared"

    # Shared / 공용 모듈
    if any(k in n for k in ("shared", "common", "core", "utility")):
        return "shared"

    # Admin / 관리자
    if any(k in n for k in ("admin", "guardian", "dashboard")):
        return "admin"

    # Plan / 로드맵
    if any(k in n for k in ("roadmap", "planning", "blueprint")):
        return "planning"

    # Discuss / 논의
    if any(k in n for k in ("discuss", "discussion")):
        return "discussions"

    # Verify / 검증
    if any(k in n for k in ("verify", "test", "lint", "check")):
        return "verification"

    # Default: PLAN_ prefixed → blueprints, else by-date
    if filename.startswith("PLAN_"):
        return "blueprints"

    m = re.match(r"^(\d{8})_", filename)
    if m:
        return f"by-date/{m.group(1)[:6]}"

    return "misc"


def archive_relative_path(filename: str) -> str:
    """Return path relative to docs/plans/archive/ (e.g. 'refactor/PLAN_x.md')."""
    subdir = classify_archive_subdir(filename)
    return f"{subdir}/{filename}"
