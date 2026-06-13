#!/usr/bin/env python3
"""Normalize legacy agent tool names in plan/docs markdown files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ARCHIVE_ROOT = Path("docs/plans/archive")
DOCS_ROOT = Path("docs")

# Intentional legacy references — cross-agent mapping, historical stats, poison examples.
EXCLUDE_REL_PATHS: frozenset[str] = frozenset(
    {
        "docs/specs/technical/SPEC_TECH_tech_multi_agent_tooling.md",
        "docs/reports/ai-log-rlhf-dataset-report.md",
        "docs/reports/ai-log-implementation.md",
    }
)

# Longest token first to avoid partial replacement chains.
_TOKEN_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("replace_file_content", "StrReplace"),
    ("codebase_search", "SemanticSearch"),
    ("execute_command", "Shell"),
    ("apply_diff", "StrReplace"),
    ("grep_search", "Grep"),
    ("search_files", "Grep"),
    ("read_file", "Read"),
    ("write_file", "Write"),
    ("view_file", "Read"),
    ("list_files", "Glob"),
    ("list_dir", "Glob"),
    ("run_command", "Shell"),
)

_LITERAL_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("[Edit File] (replace_file_content)", "StrReplace"),
    ("[Edit File] (apply_diff)", "StrReplace"),
    ("[Edit File]", "StrReplace"),
    # Tri-runtime neutral preread boilerplate (not Cursor-only tool names)
    ("`Write`/`StrReplace`", "`write`/`patch`"),
    ("`Write`/`StrReplace` 전", "`write`/`patch` 전"),
    ("patch/Write", "StrReplace/Write"),
    ("patch/write_file", "StrReplace/Write"),
    ("Action: run_command", "Action: Shell"),
    ("Action: read_file", "Action: Read"),
    ("Action: list_files", "Action: Glob"),
)

# Historical verify lines that glued tool name to Korean particle without space.
_PARTICLE_FIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bview_file로\b"), "Read로"),
    (re.compile(r"\bview_file`"), "Read`"),
    (re.compile(r"`view_file\b"), "`Read"),
)


def normalize_text(text: str) -> tuple[str, int]:
    """Return normalized copy and replacement count."""
    out = text
    count = 0
    for old, new in _LITERAL_REPLACEMENTS:
        n = out.count(old)
        if n:
            out = out.replace(old, new)
            count += n
    for old, new in _TOKEN_REPLACEMENTS:
        n = out.count(old)
        if n:
            out = out.replace(old, new)
            count += n
    for pat, repl in _PARTICLE_FIXES:
        out, n = pat.subn(repl, out)
        count += n
    return out, count


def repo_relative(path: Path, *, cwd: Path | None = None) -> str:
    """Path relative to repo cwd (``docs/...``), stable for exclude lists."""
    base = (cwd or Path.cwd()).resolve()
    return path.resolve().relative_to(base).as_posix()


def iter_markdown_files(
    root: Path,
    *,
    exclude_prefixes: tuple[Path, ...] = (),
    exclude_rel_paths: frozenset[str] = EXCLUDE_REL_PATHS,
    cwd: Path | None = None,
) -> list[Path]:
    base = (cwd or Path.cwd()).resolve()
    root = root.resolve()
    exclude_resolved = tuple((base / p).resolve() for p in exclude_prefixes)
    out: list[Path] = []
    for path in sorted(root.rglob("*.md")):
        if not path.is_file():
            continue
        resolved = path.resolve()
        rel = repo_relative(resolved, cwd=base)
        if rel in exclude_rel_paths:
            continue
        if any(resolved.is_relative_to(prefix) for prefix in exclude_resolved):
            continue
        out.append(path)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ARCHIVE_ROOT,
        help="Root directory to scan (default: docs/plans/archive)",
    )
    parser.add_argument(
        "--exclude-prefix",
        action="append",
        default=[],
        metavar="PATH",
        help="Skip markdown under this prefix (repeatable).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report only; do not write.")
    args = parser.parse_args(argv)

    root: Path = args.root
    if not root.is_dir():
        print(f"Missing directory: {root}")
        return 1

    exclude_prefixes = tuple(Path(p) for p in args.exclude_prefix)
    changed_files = 0
    total_replacements = 0
    skipped = 0
    for path in iter_markdown_files(root, exclude_prefixes=exclude_prefixes):
        original = path.read_text(encoding="utf-8")
        normalized, n = normalize_text(original)
        if n == 0:
            continue
        changed_files += 1
        total_replacements += n
        rel = repo_relative(path)
        print(f"{rel}: {n} replacement(s)")
        if not args.dry_run:
            path.write_text(normalized, encoding="utf-8")

    mode = "would update" if args.dry_run else "updated"
    print(f"\n{mode} {changed_files} file(s), {total_replacements} replacement(s) under {root}")
    if exclude_prefixes:
        print(f"exclude-prefix: {', '.join(p.as_posix() for p in exclude_prefixes)}")
    print(f"exclude-rel-paths: {', '.join(sorted(EXCLUDE_REL_PATHS))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
