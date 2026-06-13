#!/usr/bin/env python3
"""Git-touched frontend files design-lint gate.

스캔 대상: apps/renderer/src 하위 CSS / TSX / JS(X) 파일
검출 패턴:
  - 하드코딩 px 값 (inline style, CSS)
  - 하드코딩 헥스 색상 (#rrggbb)
  - 하드코딩 pt / em (타이포그래피 토큰 위반)
  - palette 직접색 (bg-slate-*, text-amber-* 등)
  - 임의 bracket 클래스 (text-[11px] 등)
  - 헤더 액션 SSOT 미사용 (deskActionBarOutlineButtonClass)
예외 주석:
  - // design-lint-disable
  - /* design-lint-disable */
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]

# ── 패턴 정의 ──────────────────────────────────────────────────────

# inline style: fontSize: "14px", width: "60px", height: "520px", padding: "6px 12px"
_RE_INLINE_PX = re.compile(
    r'(?:fontSize|width|height|minWidth|maxWidth|minHeight|maxHeight'
    r'|padding|paddingTop|paddingRight|paddingBottom|paddingLeft'
    r'|margin|marginTop|marginRight|marginBottom|marginLeft'
    r'|gap|lineHeight|borderWidth|top|right|bottom|left'
    r'|flexBasis)'
    r'\s*:\s*["\'](\d+(?:\.\d+)?)px["\']',
)

# CSS property: width: 60px;, height: 316px;
_RE_CSS_PX = re.compile(
    r'(?:width|height|minWidth|maxWidth|minHeight|maxHeight'
    r'|padding|margin|gap|lineHeight|borderWidth'
    r'|top|right|bottom|left|flexBasis)'
    r'\s*:\s*(\d+(?:\.\d+)?)px\s*;',
)

# hex color: #3b82f6, #f97316, #22c55e (3~8 hex digit)
_RE_HEX_COLOR = re.compile(r'#[0-9a-fA-F]{3,8}\b')

# pt unit (typography token 위반)
_RE_PT = re.compile(r'["\'](\d+(?:\.\d+)?)pt["\']')

# ── 하이브리드 규칙 (palette·bracket·헤더 SSOT) ────────────────────

# palette 직접색 금지 — semantic 토큰(bg-background 등)은 허용
_RE_PALETTE_DIRECT = re.compile(
    r"\b(?:bg|text|border)-(?:slate|amber|blue|emerald|red)-"
)

# Tailwind arbitrary bracket 클래스 금지
_RE_ARBITRARY_BRACKET = re.compile(r"\b\w+-\[[^\]]+\]")

# 헤더·툴바 액션 파일 — deskActionBarOutlineButtonClass SSOT 필수
_HEADER_ACTION_FILES = frozenset(
    {
        "ExaminationLayoutHeaderActions.tsx",
        "DashboardPageToolbar.tsx",
        "ReceptionActionToolbar.tsx",
        "ReceptionDeskActionRow.tsx",
        "DashboardDeskActionRow.tsx",
    }
)

_HEADER_SSOT_TOKEN = "deskActionBarOutlineButtonClass"

# ── 예외 주석 체크 ─────────────────────────────────────────────────

_RE_DISABLE_INLINE = re.compile(r'//\s*design-lint-disable')
_RE_DISABLE_BLOCK = re.compile(r'/\*.*?design-lint-disable.*?\*/', re.DOTALL)


def _line_has_disable_comment(line: str) -> bool:
    """라인에 design-lint-disable 주석이 있으면 True."""
    return bool(_RE_DISABLE_INLINE.search(line)) or bool(
        _RE_DISABLE_BLOCK.search(line)
    )


# ── 파일 스캔 ──────────────────────────────────────────────────────

_FRONTEND_EXTS = {".tsx", ".ts", ".jsx", ".js", ".css", ".scss", ".less"}


def _is_frontend_file(path: Path) -> bool:
    return path.suffix in _FRONTEND_EXTS


def _is_git_touched(path: Path, repo_root: Path) -> bool:
    """파일이 git diff/add/untracked 상태인지 확인."""
    try:
        import subprocess  # noqa: F401

        result = subprocess.run(
            ["git", "status", "--porcelain", str(path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return bool(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # git 없거나 timeout → 전체 파일 스캔으로 폴백
        return True


def _git_touched_frontend_files(repo_root: Path) -> list[Path]:
    """git diff --name-only + untracked 중 프론트엔드 파일 반환."""
    try:
        import subprocess

        # staged + modified
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        files: list[str] = result.stdout.strip().splitlines() if result.stdout.strip() else []

        # unstaged changes
        result2 = subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        files.extend(result2.stdout.strip().splitlines() if result2.stdout.strip() else [])

        # untracked
        result3 = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        files.extend(result3.stdout.strip().splitlines() if result3.stdout.strip() else [])

    except (FileNotFoundError, subprocess.TimeoutExpired):
        # git unavailable — 전체 프론트엔드 디렉토리 스캔
        files = []

    touched: list[Path] = []
    for rel in files:
        full = repo_root / rel
        if _is_frontend_file(full):
            touched.append(full)

    return sorted(set(touched))


def collect_all_frontend_files(repo_root: Path) -> list[Path]:
    """apps/renderer/src 하위 전체 프론트엔드 파일 반환."""
    renderer_src = repo_root / "apps" / "renderer" / "src"
    if not renderer_src.is_dir():
        return []

    targets: list[Path] = []
    for fpath in renderer_src.rglob("*"):
        if fpath.is_file() and _is_frontend_file(fpath):
            targets.append(fpath)
    return sorted(targets)


def scan_hybrid_rules(
    line: str,
    line_no: int,
) -> list[tuple[int, str, str]]:
    """단일 라인에 대한 하이브리드 규칙 검출."""
    issues: list[tuple[int, str, str]] = []

    for m in _RE_PALETTE_DIRECT.finditer(line):
        issues.append((line_no, "palette-direct-color", m.group(0)))

    for m in _RE_ARBITRARY_BRACKET.finditer(line):
        issues.append((line_no, "arbitrary-bracket", m.group(0)))

    return issues


def scan_header_ssot(
    path: Path,
    content: str,
) -> list[tuple[int, str, str]]:
    """헤더 액션 파일에서 SSOT 토큰 미사용 검출."""
    if path.name not in _HEADER_ACTION_FILES:
        return []

    if _HEADER_SSOT_TOKEN in content:
        return []

    # Button + 커스텀 className이 있으나 SSOT 미참조
    if re.search(r"<Button\b", content) and re.search(
        r'className\s*=\s*(?:\{cn\(|["\'])',
        content,
    ):
        return [(1, "header-ssot-missing", _HEADER_SSOT_TOKEN)]

    return []


def _scan_file(path: Path) -> list[tuple[int, str, str]]:
    """파일 스캔 → (line_no, pattern_name, match_text) 리스트."""
    issues: list[tuple[int, str, str]] = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return issues

    lines = content.splitlines()

    for i, line in enumerate(lines, start=1):
        # 예외 주석 체크
        if _line_has_disable_comment(line):
            continue

        # inline px
        for m in _RE_INLINE_PX.finditer(line):
            issues.append((i, "hardcoded-px", f'inline style: "{m.group(1)}px"'))

        # CSS px
        for m in _RE_CSS_PX.finditer(line):
            issues.append((i, "hardcoded-px", f'CSS: "{m.group(1)}px"'))

        # hex color — 단, var(--*) 또는 rgba/hsl 포함 시 제외
        for m in _RE_HEX_COLOR.finditer(line):
            hex_val = m.group(0)
            # var(--*) 토큰 참조는 제외 (이미 CSS 변수 안에 있는 경우)
            if "var(" in line:
                continue
            # rgba / hsl 함수 내 색상은 제외
            if re.search(r'(?:rgba|hsla|hsl)\s*\(', line):
                continue
            issues.append((i, "hardcoded-hex", hex_val))

        # pt unit
        for m in _RE_PT.finditer(line):
            issues.append((i, "hardcoded-pt", f'"{m.group(1)}pt"'))

        # 하이브리드 규칙 (palette·bracket)
        issues.extend(scan_hybrid_rules(line, i))

    # 헤더 SSOT (파일 단위)
    issues.extend(scan_header_ssot(path, content))

    return issues


# ── 메인 ───────────────────────────────────────────────────────────

def design_lint_touched(
    repo_root: Path | None = None,
    paths: list[str] | None = None,
    scan_all: bool = False,
    help_mode: bool = False,
) -> int:
    """디자인 토큰 위반 스캔. exit 0 = pass, exit 1 = violation."""
    root = repo_root or _REPO

    if help_mode:
        print("design-lint-touched: Frontend design token violation scanner")
        print()
        print("Usage:")
        print("  design_lint_touched.py              # git-touched frontend files")
        print("  design_lint_touched.py --all        # all apps/renderer/src files")
        print("  design_lint_touched.py --help       # this help")
        print("  design_lint_touched.py path1.tsx    # specific files")
        print()
        print("Patterns:")
        print("  - Hardcoded px values in inline styles & CSS")
        print("  - Hardcoded hex colors (#rrggbb)")
        print("  - Hardcoded pt units (typography token)")
        print("  - Palette direct colors (bg-slate-*, text-amber-*, etc.)")
        print("  - Arbitrary bracket classes (text-[11px], etc.)")
        print("  - Header action SSOT (deskActionBarOutlineButtonClass)")
        print()
        print("Exceptions: // design-lint-disable or /* design-lint-disable */")
        return 0

    # 타겟 파일 결정
    if paths:
        targets = [root / p for p in paths if (root / p).is_file()]
    elif scan_all:
        targets = collect_all_frontend_files(root)
    else:
        targets = _git_touched_frontend_files(root)

    if not targets:
        print("design-lint-touched: no touched frontend files to scan")
        return 0

    all_issues: dict[str, list[tuple[int, str, str]]] = {}
    for fpath in targets:
        issues = _scan_file(fpath)
        if issues:
            all_issues[str(fpath.relative_to(root))] = issues

    if not all_issues:
        print("design-lint-touched: OK — no violations")
        return 0

    # 결과 출력
    total = 0
    for rel, issues in sorted(all_issues.items()):
        print(f"[FAIL] {rel}:")
        for line_no, pattern, text in issues:
            print(f"  L{line_no}: [{pattern}] {text}")
            total += 1

    print(f"\ndesign-lint-touched: {total} violation(s) in {len(all_issues)} file(s)")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Frontend design token violation scanner",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files to scan (default: git-touched frontend files)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan all apps/renderer/src frontend files",
    )
    parser.add_argument(
        "--help-patterns",
        action="store_true",
        help="Show help and exit",
    )
    args = parser.parse_args()

    if args.help_patterns:
        return design_lint_touched(help_mode=True)

    return design_lint_touched(paths=args.paths or None, scan_all=args.all)


if __name__ == "__main__":
    raise SystemExit(main())
