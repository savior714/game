#!/usr/bin/env python3
"""Fix relative links in docs/knowledge/research/**/*.md.

Rewrites broken relative paths (e.g. `../plans/` → `../../plans/`)
that are one directory level too shallow inside the research/ tree.

Also resolves dead PLAN links by matching against archive/.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

RULES: list[tuple[str, str]] = [
    # Link targets that are one level too shallow
    (r"\(\.\./plans/", r"(../../plans/"),
    (r"\(\.\./specs/", r"(../../specs/"),
]

# Markdown link syntax variants (full bracket+paren)
LINK_RULES: list[tuple[str, str]] = [
    (r"\]\(\.\./plans/", r"](../../plans/"),
    (r"\]\(\.\./specs/", r"](../../specs/"),
]

RESEARCH_DIR = Path("docs/knowledge/research")


def apply_rules(content: str) -> str:
    """Apply all rewrite rules to *content* and return the result."""
    for pattern, replacement in LINK_RULES + RULES:
        content = re.sub(pattern, replacement, content)
    return content


@dataclass
class LinkFixResult:
    file: str
    changes: list[tuple[str, str]] = field(default_factory=list)


def _walk_research_md(research_dir: Path) -> list[Path]:
    """Yield all .md files under *research_dir*."""
    if not research_dir.is_dir():
        return []
    base = research_dir.resolve()
    return sorted(base.rglob("*.md"))


def dry_run(research_dir: Path | None = None) -> list[LinkFixResult]:
    """Show what would change without writing."""
    base = (research_dir or RESEARCH_DIR).resolve()
    results: list[LinkFixResult] = []
    for path in _walk_research_md(base):
        content = path.read_text(encoding="utf-8")
        new_content = apply_rules(content)
        if new_content != content:
            changes: list[tuple[str, str]] = []
            for pattern, replacement in LINK_RULES + RULES:
                for match in re.finditer(pattern, content):
                    changes.append((match.group(), replacement))
            rel = str(path.relative_to(base.parent.parent))
            results.append(LinkFixResult(file=rel, changes=changes))
    return results


def apply(research_dir: Path | None = None) -> list[LinkFixResult]:
    """Rewrite links in-place and return summary."""
    base = (research_dir or RESEARCH_DIR).resolve()
    results: list[LinkFixResult] = []
    for path in _walk_research_md(base):
        content = path.read_text(encoding="utf-8")
        new_content = apply_rules(content)
        if new_content != content:
            changes: list[tuple[str, str]] = []
            for pattern, replacement in LINK_RULES + RULES:
                for match in re.finditer(pattern, content):
                    changes.append((match.group(), replacement))
            path.write_text(new_content, encoding="utf-8")
            rel = str(path.relative_to(base.parent.parent))
            results.append(LinkFixResult(file=rel, changes=changes))
    return results


def resolve_dead_links(research_dir: Path | None = None) -> dict[str, int]:
    """Resolve dead PLAN links in research docs.

    Strategy:
    1. Find broken links pointing to docs/plans/PLAN_xxx.md
    2. Search docs/plans/archive/ for matching basename
    3. Replace with correct relative path from research/, or remove link + add footnote
    """
    base = (research_dir or RESEARCH_DIR).resolve()
    plans_base = Path("docs/plans").resolve()
    archive_base = plans_base / "archive"
    stats: dict[str, int] = {"resolved": 0, "removed": 0, "files_scanned": 0}

    if not base.is_dir():
        return stats

    for path in _walk_research_md(base):
        content = path.read_text(encoding="utf-8")
        modified = False

        # Find broken plan links: [text](../../plans/PLAN_xxx.md) or [text](../plans/PLAN_xxx.md)
        plan_link_pat = re.compile(r"\]\(\.\./plan(s)?/([^)]+\.md)\)")
        # Also match ../../plans/ variants
        plan_link_pat_deep = re.compile(r"\]\(\.\./\.\./plan(s)?/([^)]+\.md)\)")
        # Also match plans/archive/ variants (from previous resolve pass)
        plan_link_pat_archive = re.compile(r"\]\(plans/archive/([^)]+\.md)\)")

        for match in plan_link_pat_deep.finditer(content):
            link_target = match.group(2)
            basename = Path(link_target).name

            # Try archive first (exact path match)
            archive_path = archive_base / link_target
            if archive_path.exists():
                # Compute correct relative path from research dir to archive file
                new_link = f"](../../plans/archive/{link_target})"
                content = content[:match.start()] + new_link + content[match.end():]
                modified = True
                stats["resolved"] += 1
                continue

            # Try plans/ (non-archive) — check if file exists at resolved path
            candidate = plans_base / link_target
            if candidate.exists():
                new_link = f"](../../plans/{link_target})"
                content = content[:match.start()] + new_link + content[match.end():]
                modified = True
                stats["resolved"] += 1
                continue

            # Try archive with just basename (search subdirs)
            archive_candidates = list(archive_base.rglob(basename))
            if archive_candidates:
                best = archive_candidates[0]
                # Compute relative path from research dir to the found file
                rel = os.path.relpath(str(best), str(base))
                new_link = f"]({rel})"
                content = content[:match.start()] + new_link + content[match.end():]
                modified = True
                stats["resolved"] += 1
                continue

            # No match — remove link, keep text as plain with footnote
            link_text_match = re.search(r"\[([^\]]+)\]" + re.escape(match.group(0)), content[:match.start()])
            if link_text_match:
                link_text = link_text_match.group(1)
                replacement = link_text + " [⚠️ 계획서 아카이브·삭제]"
                content = content[:match.start()] + replacement + content[match.end():]
            else:
                replacement = " [⚠️ 계획서 아카이브·삭제]"
                content = content[:match.start()] + replacement + content[match.end():]
            modified = True
            stats["removed"] += 1

        # Also handle ../plans/ (single level) links
        for match in plan_link_pat.finditer(content):
            link_target = match.group(2)
            basename = Path(link_target).name

            # Try archive first (exact path match)
            archive_path = archive_base / link_target
            if archive_path.exists():
                new_link = f"](../../plans/archive/{link_target})"
                content = content[:match.start()] + new_link + content[match.end():]
                modified = True
                stats["resolved"] += 1
                continue

            # Try plans/ (non-archive) — check if file exists at resolved path
            candidate = plans_base / link_target
            if candidate.exists():
                new_link = f"](../../plans/{link_target})"
                content = content[:match.start()] + new_link + content[match.end():]
                modified = True
                stats["resolved"] += 1
                continue

            # Try archive with just basename (search subdirs)
            archive_candidates = list(archive_base.rglob(basename))
            if archive_candidates:
                best = archive_candidates[0]
                # Compute relative path from research dir to the found file
                rel = os.path.relpath(str(best), str(base))
                new_link = f"]({rel})"
                content = content[:match.start()] + new_link + content[match.end():]
                modified = True
                stats["resolved"] += 1
                continue

            # No match — remove link, keep text as plain with footnote
            link_text_match = re.search(r"\[([^\]]+)\]" + re.escape(match.group(0)), content[:match.start()])
            if link_text_match:
                link_text = link_text_match.group(1)
                replacement = link_text + " [⚠️ 계획서 아카이브·삭제]"
                content = content[:match.start()] + replacement + content[match.end():]
            else:
                replacement = " [⚠️ 계획서 아카이브·삭제]"
                content = content[:match.start()] + replacement + content[match.end():]
            modified = True
            stats["removed"] += 1

        # Also handle plans/archive/PLAN_xxx.md (no prefix) links
        for match in plan_link_pat_archive.finditer(content):
            link_target = match.group(1)
            basename = Path(link_target).name

            # Try archive first (exact path match)
            archive_path = archive_base / link_target
            if archive_path.exists():
                # Compute relative path from research dir to the found file
                rel = os.path.relpath(str(archive_path), str(base))
                new_link = f"]({rel})"
                content = content[:match.start()] + new_link + content[match.end():]
                modified = True
                stats["resolved"] += 1
                continue

            # Try archive with just basename (search subdirs)
            archive_candidates = list(archive_base.rglob(basename))
            if archive_candidates:
                best = archive_candidates[0]
                # Compute relative path from research dir to the found file
                rel = str(best.relative_to(base))
                new_link = f"]({rel})"
                content = content[:match.start()] + new_link + content[match.end():]
                modified = True
                stats["resolved"] += 1
                continue

            # No match — remove link, keep text as plain with footnote
            link_text_match = re.search(r"\[([^\]]+)\]" + re.escape(match.group(0)), content[:match.start()])
            if link_text_match:
                link_text = link_text_match.group(1)
                replacement = link_text + " [⚠️ 계획서 아카이브·삭제]"
                content = content[:match.start()] + replacement + content[match.end():]
            else:
                replacement = " [⚠️ 계획서 아카이브·삭제]"
                content = content[:match.start()] + replacement + content[match.end():]
            modified = True
            stats["removed"] += 1

        if modified:
            path.write_text(content, encoding="utf-8")
        stats["files_scanned"] += 1

    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fix relative links in research docs")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    parser.add_argument("--apply", action="store_true", help="Apply link fixes in-place")
    parser.add_argument("--resolve", action="store_true", help="Resolve dead PLAN links")
    parser.add_argument("--research-dir", type=Path, default=None, help="Override research directory")
    args = parser.parse_args(argv)

    if args.dry_run:
        results = dry_run(args.research_dir)
        if not results:
            print("✅ No changes needed")
            return 0
        print(f"📋 {len(results)} file(s) would change:\n")
        for r in results:
            print(f"  {r.file}")
            for old, new in r.changes[:5]:
                print(f"    {old} → {new}")
            if len(r.changes) > 5:
                print(f"    ... and {len(r.changes) - 5} more")
        return 0

    if args.apply:
        results = apply(args.research_dir)
        if not results:
            print("✅ No changes needed")
            return 0
        total_changes = sum(len(r.changes) for r in results)
        print(f"✅ Fixed {total_changes} link(s) in {len(results)} file(s)")
        return 0

    if args.resolve:
        stats = resolve_dead_links(args.research_dir)
        print(f"📋 Resolved: {stats['resolved']}, Removed: {stats['removed']}, Scanned: {stats['files_scanned']}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
