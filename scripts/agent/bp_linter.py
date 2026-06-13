#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
베스트 프랙티스 검증 Linter 모듈
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.agent.bp_rules_parser import parse_rules_from_file


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

# 테스트·목업 경로 — BP 규칙 기본 제외 (기존 any 허용 구간)
SKIP_REL_PATH_MARKERS = (
    "/__tests__/",
    "/__test__/",
    ".test.ts",
    ".test.tsx",
    ".spec.ts",
    ".spec.tsx",
)


def is_skipped_scan_path(file_path: Path, repo_root: Path) -> bool:
    rel = file_path.relative_to(repo_root).as_posix()
    return any(marker in rel for marker in SKIP_REL_PATH_MARKERS)


def line_has_biome_ignore(prev_line: str) -> bool:
    return "biome-ignore" in prev_line


def line_has_ruff_noqa(prev_line: str) -> bool:
    return "# noqa" in prev_line.lower()


def line_has_lint_ignore(prev_line: str) -> bool:
    return line_has_biome_ignore(prev_line) or line_has_ruff_noqa(prev_line)


def is_comment_only_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("//") or stripped.startswith("*")


def find_empty_catch_line_numbers(content: str) -> list[int]:
    """1-based line numbers for empty or comment-only catch blocks."""
    lines = content.splitlines()
    hits: list[int] = []
    i = 0
    while i < len(lines):
        if not re.search(r"catch\s*\([^)]*\)\s*\{", lines[i]):
            i += 1
            continue
        start_line = i + 1
        catch_part = lines[i].split("catch", 1)[1] if "catch" in lines[i] else lines[i]
        brace = catch_part.count("{") - catch_part.count("}")
        j = i + 1
        while j < len(lines) and brace > 0:
            brace += lines[j].count("{") - lines[j].count("}")
            j += 1
        body = lines[i + 1 : max(i + 1, j - 1)]
        meaningful = [
            ln
            for ln in body
            if ln.strip() and not is_comment_only_line(ln)
        ]
        if not meaningful:
            hits.append(start_line)
        i = j if j > i else i + 1
    return hits


def check_empty_catch_blocks(
    content: str,
    *,
    only_line_numbers: set[int] | None = None,
) -> tuple[bool, str, int | None]:
    lines = content.splitlines()
    for line_num in find_empty_catch_line_numbers(content):
        if only_line_numbers is not None and line_num not in only_line_numbers:
            continue
        prev = lines[line_num - 2] if line_num >= 2 else ""
        if line_has_lint_ignore(prev):
            continue
        return False, "Empty catch block (including comment-only body).", line_num
    return True, "", None


def get_git_modified_files(repo_root: Path) -> list[Path]:
    """git status를 통해 수정·추가(untracked 포함) 파일 목록을 가져옴"""
    import subprocess
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True
        )
        files = []
        for line in proc.stdout.splitlines():
            if line.strip():
                parts = line.strip().split(None, 1)
                if len(parts) > 1:
                    filepath = repo_root / parts[1]
                    if filepath.is_file():
                        files.append(filepath.resolve())
        return files
    except Exception as e:
        print(f"ERROR: Failed to get git status ({e}). Aborting — no fallback.", file=sys.stderr)
        sys.exit(1)


def get_git_untracked_rel_paths(repo_root: Path) -> set[str]:
    """git status ?? (untracked) 파일의 repo-relative 경로."""
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        untracked: set[str] = set()
        for line in proc.stdout.splitlines():
            if line.startswith("??"):
                rel = line[3:].strip()
                if rel:
                    untracked.add(rel)
        return untracked
    except Exception:
        return set()


def should_check_file(file_path: Path, repo_root: Path, glob_pattern: str) -> bool:
    """파일이 규칙의 glob 패턴과 매치되는지 확인"""
    try:
        # repo root에 대한 상대 경로 기준으로 매칭 시도
        rel_path = file_path.relative_to(repo_root)
        # pathlib.Path.match를 이용한 glob 매칭
        if rel_path.match(glob_pattern):
            return True
    except Exception:
        pass
    
    # fallback: fnmatch
    rel_path_str = file_path.relative_to(repo_root).as_posix()
    return fnmatch.fnmatch(rel_path_str, glob_pattern) or fnmatch.fnmatch(file_path.name, glob_pattern)


def get_git_added_lines_map(repo_root: Path, check_path: Path | None = None) -> dict[str, set[int]]:
    """git diff HEAD + cached에서 추가·변경된 라인 번호(신규 파일 기준)를 반환."""
    import subprocess

    path_filter = "."
    if check_path is not None:
        try:
            path_filter = check_path.relative_to(repo_root).as_posix()
        except ValueError:
            path_filter = str(check_path)

    added_lines: dict[str, set[int]] = {}
    try:
        diff_parts: list[str] = []
        for diff_cmd in (
            ["git", "diff", "HEAD", "--", path_filter],
            ["git", "diff", "--cached", "--", path_filter],
        ):
            proc = subprocess.run(
                diff_cmd,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                diff_parts.append(proc.stdout)

        current_file: str | None = None
        current_line = 0
        for chunk in diff_parts:
            for line in chunk.splitlines():
                if line.startswith("+++ b/"):
                    current_file = line[6:].strip()
                    added_lines.setdefault(current_file, set())
                elif line.startswith("@@"):
                    match = re.search(r"\+(\d+)", line)
                    if match:
                        current_line = int(match.group(1))
                elif line.startswith("+") and not line.startswith("+++"):
                    if current_file:
                        added_lines.setdefault(current_file, set()).add(current_line)
                    current_line += 1
                elif not line.startswith("-"):
                    current_line += 1
    except Exception:
        return {}

    return added_lines


def rule_checks_diff_added_lines_only(rule_id: str) -> bool:
    """레거시 허용: incremental 시 신규/변경 라인에만 적용하는 규칙."""
    return rule_id.startswith(("BP-TS-004", "BP-TS-005", "BP-PY-"))


def check_regex_not(
    content: str,
    pattern: str,
    *,
    line_aware: bool = False,
    only_line_numbers: set[int] | None = None,
) -> tuple[bool, str, int | None]:
    """금지된 패턴이 존재하는지 검증. line_aware 시 주석·biome-ignore 직전 줄 제외."""
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return False, f"Invalid regex pattern '{pattern}': {e}", None

    if not line_aware:
        match = rx.search(content)
        if match:
            idx = match.start()
            line_num = content[:idx].count("\n") + 1
            if only_line_numbers is not None and line_num not in only_line_numbers:
                return True, "", None
            return False, f"Forbidden pattern '{pattern}' found.", line_num
        return True, "", None

    lines = content.splitlines()
    for line_num, line in enumerate(lines, start=1):
        if only_line_numbers is not None and line_num not in only_line_numbers:
            continue
        if is_comment_only_line(line):
            continue
        prev = lines[line_num - 2] if line_num >= 2 else ""
        if line_has_lint_ignore(prev):
            continue
        if rx.search(line):
            return False, f"Forbidden pattern '{pattern}' found.", line_num
    return True, "", None


def check_regex_must(content: str, pattern: str) -> tuple[bool, str, int | None]:
    """필수 패턴이 존재하지 않는지 검증"""
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return False, f"Invalid regex pattern '{pattern}': {e}", None
        
    match = rx.search(content)
    if not match:
        return False, f"Required pattern '{pattern}' not found.", None
    return True, "", None


def check_file_compliance(
    file_path: Path,
    rule: dict,
    *,
    only_line_numbers: set[int] | None = None,
) -> tuple[bool, str, int | None]:
    """단일 파일에 대해 규칙 준수 여부 검증"""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"Failed to read file: {e}", None
        
    logic = rule.get("pass_criteria", "")
    if not logic:
        return True, "", None

    rule_id = rule.get("rule_id", "")
    if rule_id.startswith("BP-TS-005"):
        return check_empty_catch_blocks(content, only_line_numbers=only_line_numbers)
        
    if logic.startswith("regex_not::"):
        pattern = logic.split("::", 1)[1]
        line_aware = rule.get("rule_id", "").startswith(("BP-TS-", "BP-PY-"))
        return check_regex_not(
            content,
            pattern,
            line_aware=line_aware,
            only_line_numbers=only_line_numbers,
        )
    elif logic.startswith("regex_must::"):
        pattern = logic.split("::", 1)[1]
        return check_regex_must(content, pattern)
    else:
        return False, f"Unsupported pass_criteria prefix: '{logic}'", None


def run_linter(rules_path: Path, check_path: Path, repo_root: Path, incremental: bool = False, verbose: bool = False) -> int:
    """Linter 실행 메인 로직"""
    # 1. 규칙 파일 탐색 및 파싱
    rules = []
    if rules_path.is_file():
        rules.extend(parse_rules_from_file(rules_path))
    elif rules_path.is_dir():
        for p in rules_path.rglob("*.md"):
            try:
                rules.extend(parse_rules_from_file(p))
            except Exception as e:
                if verbose:
                    print(f"Skipping rule file {p}: {e}")
                    
    if not rules:
        print("No rules found to enforce.")
        return 0
        
    if verbose:
        print(f"Loaded {len(rules)} compliance rules.")

    # 2. 검사 대상 파일 수집
    target_files = []
    if incremental:
        target_files = get_git_modified_files(repo_root)
        if verbose:
            print(f"Incremental mode: checking {len(target_files)} modified files.")
            
    if not target_files:
        # full scan or fallback
        if check_path.is_file():
            target_files = [check_path.resolve()]
        elif check_path.is_dir():
            for p in check_path.rglob("*"):
                if p.is_file():
                    # skip directories in SKIP_DIRS
                    if any(part in SKIP_DIRS for part in p.parts):
                        continue
                    target_files.append(p.resolve())

    # 3. 규칙별로 대상 파일 매칭 및 검사
    violations_count = 0
    added_lines_map = get_git_added_lines_map(repo_root, check_path) if incremental else {}
    untracked_rel_paths = get_git_untracked_rel_paths(repo_root) if incremental else set()
    
    for rule in rules:
        rule_id = rule.get("rule_id", "UNKNOWN")
        glob_pattern = rule.get("glob", "**/*")
        diff_line_only = incremental and rule_checks_diff_added_lines_only(rule_id)
        
        matched_files = [f for f in target_files if should_check_file(f, repo_root, glob_pattern)]
        
        if verbose:
            print(f"Rule {rule_id} ({glob_pattern}) matches {len(matched_files)} files.")
            
        for filepath in matched_files:
            if is_skipped_scan_path(filepath, repo_root):
                continue
            # Linter 자체 파일 및 테스트 파일은 검사에서 배제 (false positives 방지)
            if "bp_linter" in filepath.name or "test_bp_linter" in filepath.name:
                continue

            only_lines: set[int] | None = None
            if diff_line_only:
                rel = filepath.relative_to(repo_root).as_posix()
                if rel in untracked_rel_paths:
                    # 신규 untracked 파일: diff hunk 없음 → 전체 검사
                    only_lines = None
                else:
                    only_lines = added_lines_map.get(rel, set())
                    if not only_lines:
                        continue
                
            success, msg, line_num = check_file_compliance(
                filepath,
                rule,
                only_line_numbers=only_lines,
            )
            if not success:
                rel_path = filepath.relative_to(repo_root).as_posix()
                line_info = f":{line_num}" if line_num else ""
                print(f"❌ Compliance violation [{rule_id}] in {rel_path}{line_info}: {msg}")
                violations_count += 1

    if violations_count > 0:
        print(f"\nTotal compliance violations found: {violations_count}")
        return 1
        
    print("✅ All compliance checks passed successfully.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Best Practice Compliance Linter")
    parser.add_argument("--rules-path", type=str, default=".agents/domains/",
                        help="Path to markdown rules file or directory (default: .agents/domains/)")
    parser.add_argument("--check-path", type=str, default=".",
                        help="Path to directory or file to check (default: .)")
    parser.add_argument("--incremental", action="store_true",
                        help="Only scan git modified files")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose debugging output")
                        
    args = parser.parse_args()
    
    repo_root = Path(__file__).resolve().parents[2]
    rules_path = repo_root / args.rules_path if not Path(args.rules_path).is_absolute() else Path(args.rules_path)
    check_path = repo_root / args.check_path if not Path(args.check_path).is_absolute() else Path(args.check_path)
    
    return run_linter(
        rules_path=rules_path,
        check_path=check_path,
        repo_root=repo_root,
        incremental=args.incremental,
        verbose=args.verbose
    )


if __name__ == "__main__":
    sys.exit(main())
