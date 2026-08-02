#!/usr/bin/env python3
"""Unified Sync spec-drift classification & alignment.

Heuristics that map a `git diff` to a spec-drift level (skip / suggested /
required) and verify whether the change set satisfies spec alignment. Code
lock parsing is reused from ``code_sync``; report rendering lives in
``sync_report``.
"""

from __future__ import annotations

import datetime
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.agent.code_sync import LOCK_PATTERN, parse_metadata  # noqa: E402
from scripts.agent.sync_report import build_footer  # noqa: E402

REPO_ROOT = _REPO

# --- Spec Sync Nudge Patterns ---
HIGH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^apps/renderer/next\.config\.(ts|mjs|js)$"),
    re.compile(r"^apps/renderer/src/proxy\.ts$"),
    re.compile(r"^apps/renderer/src/middleware\.ts$"),
    re.compile(r"^apps/renderer/src/app/"),
)

MEDIUM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^docs/plans/"),
    re.compile(r"^docs/plans/architectures/"),
    re.compile(r"^docs/specs/"),
)

RENDERER_CODE = re.compile(r"^apps/renderer/src/(?!app/)")

DOC_PATH_PREFIXES: tuple[str, ...] = (
    "docs/specs/",
    "docs/plans/",
    "docs/knowledge/",
    "docs/reports/qa/",
    "docs/plans/architectures/",
)

# 코드 경로 → 역검증 후보 스펙 (휴리스틱; @code-sync-lock `spec:` 필드가 우선)
ROUTE_HINTS: tuple[tuple[re.Pattern[str], tuple[str, ...]], ...] = (
    (
        re.compile(
            r"(consultation/|ConsultationPage|useDndGridLayout|layoutPersistence|"
            r"WorkspaceGrid|preferenceService|dashboard_layout|layoutSync)"
        ),
        (
            "docs/specs/ui/SPEC_consultation_grid_layout.md",
            "docs/specs/technical/SPEC_TECH_frontend_layout_architecture.md",
            "docs/specs/ui/SPEC_ui_examination_room.md",
        ),
    ),
    (
        re.compile(r"apps/renderer/(next\.config|src/proxy|src/middleware|src/app/)"),
        (
            "docs/specs/technical/SPEC_TECH_frontend_layout_architecture.md",
        ),
    ),
)


def git_changed_paths() -> list[str]:
    cmds = [
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "diff", "--name-only", "--cached"],
    ]
    seen: set[str] = set()
    out: list[str] = []
    for cmd in cmds:
        try:
            proc = subprocess.run(
                cmd,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            continue
        for line in proc.stdout.splitlines():
            p = line.strip()
            if p and p not in seen:
                seen.add(p)
                out.append(p)
    return out


def classify_spec_drift(paths: list[str]) -> dict[str, object]:
    high: list[str] = []
    medium: list[str] = []
    renderer_other: list[str] = []

    for p in paths:
        norm = p.replace("\\", "/")

        # CSS 스타일 파일은 런타임/스펙 영향이 없으므로 감지 대상에서 제외
        if norm.endswith(".css"):
            continue

        if any(r.search(norm) for r in HIGH_PATTERNS):
            high.append(norm)
        elif any(r.search(norm) for r in MEDIUM_PATTERNS):
            medium.append(norm)
        elif RENDERER_CODE.search(norm):
            renderer_other.append(norm)

    if high:
        level = "required"
        reason = "라우트·Next 설정·프록시/미들웨어 변경 — 런타임과 문서 역검증 필수 ()."
    elif medium and renderer_other:
        level = "required"
        reason = "렌더러 코드와 Plan/스펙·아키텍처 문서를 함께 수정 — Conclusion·표 드리프트 위험."
    elif medium:
        level = "suggested"
        reason = "문서(Plan/스펙/아키텍처)만 변경 — Claim Inventory 권장."
    elif renderer_other:
        level = "suggested"
        reason = "렌더러 동작 변경 — 관련 ARCH/SPEC 문서가 있으면 역검증 권장."
    else:
        level = "skip"
        reason = "Spec Sync 트리거 경로 없음."

    smoke = bool(high) or any(
        "next.config" in p or "/src/app/" in p or "proxy.ts" in p for p in high + medium
    )

    return {
        "level": level,
        "reason": reason,
        "high_paths": high,
        "medium_paths": medium,
        "renderer_other_paths": renderer_other,
        "run_renderer_route_smoke": smoke,
        "footer_markdown": build_footer(level, smoke, medium),
    }


def extract_specs_from_changed_files(changed: list[str]) -> set[str]:
    """변경된 파일 안 @code-sync-lock 의 `spec:` 경로 수집."""
    specs: set[str] = set()
    for rel in changed:
        path = REPO_ROOT / rel.replace("\\", "/")
        if not path.is_file():
            continue
        if not rel.endswith((".ts", ".tsx", ".py", ".md")):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for lock_match in LOCK_PATTERN.finditer(content):
            meta = parse_metadata(lock_match.group(1))
            spec_path = meta.get("spec")
            if spec_path:
                specs.add(spec_path.replace("\\", "/"))
    return specs


def collect_candidate_spec_paths(changed: list[str]) -> set[str]:
    """git diff 기준 역검증 후보 스펙 경로."""
    changed_norm = [p.replace("\\", "/") for p in changed]
    candidates = extract_specs_from_changed_files(changed_norm)
    for pattern, spec_paths in ROUTE_HINTS:
        if any(pattern.search(p) for p in changed_norm):
            candidates.update(spec_paths)
    return candidates


def verify_spec_alignment(
    changed: list[str],
    classification: dict[str, object],
    *,
    ack_spec: bool = False,
) -> tuple[bool, dict[str, object]]:
    """스펙 정합 검증 — 문서 갱신·후보 스펙·명시 ack 중 하나 필요 (required 시)."""
    level = str(classification.get("level", "skip"))
    report: dict[str, object] = {
        "level": level,
        "satisfied": True,
        "docs_touched": [],
        "candidate_specs": [],
        "missing_specs": [],
        "ack_spec": ack_spec,
    }

    if level == "skip" or ack_spec:
        return True, report

    changed_norm = [p.replace("\\", "/") for p in changed]
    docs_touched = [p for p in changed_norm if p.startswith(DOC_PATH_PREFIXES)]
    report["docs_touched"] = docs_touched

    if docs_touched:
        return True, report

    candidates = collect_candidate_spec_paths(changed_norm)
    report["candidate_specs"] = sorted(candidates)
    touched_candidates = sorted(s for s in candidates if s in changed_norm)

    if touched_candidates:
        report["touched_candidates"] = touched_candidates
        return True, report

    if level == "suggested":
        report["missing_specs"] = sorted(candidates)
        return True, report

    report["missing_specs"] = sorted(candidates)
    report["satisfied"] = False
    return False, report


def auto_fix_suggested_drift(candidates: list[str]) -> int:
    """Auto-fix suggested drift by updating metadata in candidate spec files.

    Updates: Last Verified (today), Claim (add drift note if missing).
    Returns number of files fixed.
    """

    today = datetime.date.today().isoformat()
    fixed = 0

    for spec_path in candidates:
        full_path = REPO_ROOT / spec_path.replace("\\", "/")
        if not full_path.is_file():
            continue

        content = full_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # Update Last Verified if present
        updated = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("**Last Verified**"):
                lines[i] = f"**Last Verified**: {today}"
                updated = True
                break

        # Add Claim if missing and file has a Claim section
        if not updated:
            for i, line in enumerate(lines):
                if "## Claim" in line or "**Claim**" in line:
                    # Check if there's already a drift note
                    has_drift = any("drift" in line.lower() or "sync" in line.lower() for line in lines[i:i+5])
                    if not has_drift:
                        indent = len(line) - len(line.lstrip())
                        lines.insert(i + 1, f"{' ' * indent}- Auto-synced by `sync --fix` on {today}")
                        updated = True
                    break

        if updated:
            full_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            fixed += 1

    return fixed
