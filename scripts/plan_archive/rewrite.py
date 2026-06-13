"""Plan link rewriting across the repository."""

from __future__ import annotations

from scripts.plan_archive.collect import (
    canonical_plan_basename,
    iter_text_files,
    resolve_plan_reference,
    should_skip_check_path,
)
from scripts.plan_archive.constants import ARCHIVE_SCRIPT, REPO_ROOT


def build_repair_path_map(missing: dict[str, list[str]]) -> dict[str, str]:
    """basename (참조 키) -> docs/plans/archive/<rel> (rewrite_to_archive용)."""
    path_map: dict[str, str] = {}
    for base in missing:
        target = resolve_plan_reference(base)
        if target is None:
            continue
        if target.startswith("docs/plans/archive/"):
            path_map[base] = target.removeprefix("docs/plans/archive/")
        elif target.startswith("docs/archive/plans/"):
            path_map[base] = f"__legacy__:{target}"
        elif target.startswith("docs/plans/"):
            continue
        else:
            path_map[base] = f"__legacy__:{target}"
    return path_map


def rewrite_plan_links(content: str, path_map: dict[str, str]) -> str:
    """끊긴 plans 참조를 archive/legacy SSOT 경로로 치환."""
    archive_map: dict[str, str] = {}
    legacy_pairs: list[tuple[str, str]] = []
    for base, rel in path_map.items():
        if rel.startswith("__legacy__:"):
            legacy_pairs.append((base, rel.removeprefix("__legacy__:")))
        else:
            archive_map[base] = rel

    out = rewrite_to_archive(content, archive_map, to_archive=True) if archive_map else content
    for base, target in sorted(legacy_pairs, key=lambda x: -len(x[0])):
        out = out.replace(f"docs/plans/{base}", target)
        out = out.replace(f"/plans/{base}", f"/{target}")
        if target.startswith("docs/archive/plans/"):
            out = out.replace(f"../plans/{base}", "../archive/plans/" + canonical_plan_basename(base))
    return out


def patch_broken_plan_references(path_map: dict[str, str], *, dry_run: bool) -> int:
    if not path_map:
        return 0
    changed = 0
    for path in iter_text_files(REPO_ROOT):
        if path.resolve() == ARCHIVE_SCRIPT.resolve():
            continue
        if should_skip_check_path(path):
            continue
        try:
            old = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        new = rewrite_plan_links(old, path_map)
        if new != old:
            changed += 1
            if dry_run:
                print(f"[dry-run] repair: {path.relative_to(REPO_ROOT)}")
            else:
                path.write_text(new, encoding="utf-8")
    return changed


def rewrite_to_archive(
    content: str,
    path_map: dict[str, str],
    *,
    to_archive: bool,
) -> str:
    """path_map: basename -> archive 상대 경로 (예: refactor/PLAN_x.md)."""
    out = content
    for base in sorted(path_map.keys(), key=len, reverse=True):
        rel = path_map[base]
        if to_archive:
            out = out.replace(f"docs/plans/archive/{rel}", f"\x00ARC:{base}\x00")
            out = out.replace(f"docs/plans/archive/{base}", f"\x00ARCLEG:{base}\x00")
            out = out.replace(f"../plans/archive/{rel}", f"\x00ARCR:{base}\x00")
            out = out.replace(f"../plans/archive/{base}", f"\x00ARCRLEG:{base}\x00")
            out = out.replace(f"](./archive/{rel})", f"\x00ARCL:{base}\x00")
            out = out.replace(f"](./archive/{base})", f"\x00ARCLLEG:{base}\x00")
            out = out.replace(f"/plans/archive/{rel}", f"\x00ARC2:{base}\x00")
            out = out.replace(f"/plans/archive/{base}", f"\x00ARC2LEG:{base}\x00")
            out = out.replace(f"../plans/{base}", f"../plans/archive/{rel}")
            out = out.replace(f"docs/plans/{base}", f"docs/plans/archive/{rel}")
            out = out.replace(f"/plans/{base}", f"/plans/archive/{rel}")
            out = out.replace(f"](./{base})", f"](./archive/{rel})")
            out = out.replace(f"\x00ARC:{base}\x00", f"docs/plans/archive/{rel}")
            out = out.replace(f"\x00ARCLEG:{base}\x00", f"docs/plans/archive/{rel}")
            out = out.replace(f"\x00ARCR:{base}\x00", f"../plans/archive/{rel}")
            out = out.replace(f"\x00ARCRLEG:{base}\x00", f"../plans/archive/{rel}")
            out = out.replace(f"\x00ARC2:{base}\x00", f"/plans/archive/{rel}")
            out = out.replace(f"\x00ARC2LEG:{base}\x00", f"/plans/archive/{rel}")
            out = out.replace(f"\x00ARCL:{base}\x00", f"](./archive/{rel})")
            out = out.replace(f"\x00ARCLLEG:{base}\x00", f"](./archive/{rel})")
        else:
            out = out.replace(f"](./archive/{rel})", f"](./{base})")
            out = out.replace(f"](./archive/{base})", f"](./{base})")
            out = out.replace(f"../plans/archive/{rel}", f"../plans/{base}")
            out = out.replace(f"../plans/archive/{base}", f"../plans/{base}")
            out = out.replace(f"docs/plans/archive/{rel}", f"docs/plans/{base}")
            out = out.replace(f"docs/plans/archive/{base}", f"docs/plans/{base}")
            out = out.replace(f"/plans/archive/{rel}", f"/plans/{base}")
            out = out.replace(f"/plans/archive/{base}", f"/plans/{base}")
    return out


def patch_repo_references(path_map: dict[str, str], *, to_archive: bool, dry_run: bool) -> int:
    changed = 0
    for path in iter_text_files(REPO_ROOT):
        if path.resolve() == ARCHIVE_SCRIPT.resolve():
            continue
        try:
            old = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        new = rewrite_to_archive(old, path_map, to_archive=to_archive)
        if new != old:
            changed += 1
            if dry_run:
                print(f"[dry-run] patch: {path.relative_to(REPO_ROOT)}")
            else:
                path.write_text(new, encoding="utf-8")
    return changed
