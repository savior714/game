"""Plan archive paths, aliases, and scan patterns."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_SCRIPT = REPO_ROOT / "scripts" / "archive_plans.py"
PLANS = REPO_ROOT / "docs" / "plans"
ARCHIVE = PLANS / "archive"
LEGACY_PLANS = REPO_ROOT / "docs" / "archive" / "plans"

# docs/plans/<old> 참조 → archive/legacy 내 실제 파일명 (리네임·축약 SSOT)
PLAN_BASENAME_ALIASES: dict[str, str] = {}

# check/repair 스캔 제외 (생성물·일회성 스크래치·거대 검증 JSON)
CHECK_SKIP_PATH_PARTS = (
    ".agents/brain/",
    "artifacts/verify/",
    "verify-korean-text-result.json",
    "tests/",
    ".agents/core/reporting.md",
    ".agents/registry/CONTEXT_ROUTING.md",
    ".agents/workflows/archive.md",
    ".agents/workflows/go.md",
    ".agents/workflows/sync.md",
    "scripts/linear_sync/",
    "scripts/agent/auto_load_preread.py",
)

# Blueprint/워크플로 템플릿용 플레이스홀더 — 실제 파일이 아님 (plans-index check 제외)
TEMPLATE_PLAN_PLACEHOLDER_BASENAMES = frozenset({
    "PLAN_xxx.md",
    "PLAN_XYZ.md",
    "PLAN_x.md",
    "PLAN_discover_implement_dead_code_queue.md",
})

# docs/plans/<basename> 참조 패턴
PLAN_REF_PATTERN = re.compile(
    r"(?:"
    r"docs/plans/(?!archive/)"
    r"|(?<![\w./-])/plans/(?!archive/)"
    r"|(?:\.\./)+plans/(?!archive/)"
    r")([A-Za-z0-9_.-]+\.md)"
)

# 스캔할 확장자
TEXT_SUFFIXES = {".md", ".mdx", ".mjs", ".js", ".ts", ".tsx", ".py", ".html", ".json", ".yml", ".yaml"}
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".turbo",
}
