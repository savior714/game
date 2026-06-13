#!/usr/bin/env python3
"""Pattern 1.2: patch old_string must appear exactly once in target file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.agent.route_context import find_repo_root, normalize_repo_rel


def check_patch_strings_differ(old_string: str, new_string: str) -> tuple[bool, str]:
    """Return (ok, message). Fail when old and new are identical (pre-call guard)."""
    if old_string == new_string:
        return (
            False,
            "[1.2] old_string과 new_string이 동일합니다(StrReplace/edit 호출 금지).",
        )
    return True, ""


def check_old_string_in_file(
    repo_root: Path,
    file_rel: str,
    old_string: str,
) -> tuple[bool, str]:
    """Return (ok, message). On fail message is one stderr line with [1.2] prefix."""
    rel = normalize_repo_rel(file_rel)
    if not rel:
        return False, "[1.2] 파일 경로가 비어 있습니다."

    path = repo_root / rel
    if not path.is_file():
        return False, f"[1.2] 파일을 찾을 수 없습니다: {rel}"

    content = path.read_text(encoding="utf-8")
    count = content.count(old_string)
    if count == 1:
        return True, ""

    if count == 0:
        return False, f"[1.2] old_string이 파일에 없습니다: {rel}"
    return False, f"[1.2] old_string이 파일에 {count}번 있습니다(정확히 1번이어야 합니다): {rel}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pattern 1.2 old_string uniqueness check.")
    parser.add_argument("--file", required=True, help="Repo-relative file path.")
    parser.add_argument("--old-string", required=True, dest="old_string", help="Patch old_string.")
    parser.add_argument(
        "--new-string",
        default=None,
        dest="new_string",
        help="Patch new_string; when set, also verify old_string != new_string.",
    )
    args = parser.parse_args(argv)

    root = find_repo_root()
    if args.new_string is not None:
        diff_ok, diff_msg = check_patch_strings_differ(args.old_string, args.new_string)
        if not diff_ok:
            print(diff_msg, file=sys.stderr)
            return 1

    ok, msg = check_old_string_in_file(root, args.file, args.old_string)
    if not ok:
        print(msg, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
