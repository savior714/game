#!/usr/bin/env python3
"""Repair Linear issue titles corrupted with Global Pre-read heading text.

Maps TEM-NNN → blueprint via doc meta, restores title from H1
(``# 🗺️ Project Blueprint: …``) via ``extract_blueprint_title``.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.linear_sync.lib.plan_metadata import (  # noqa: E402
    parse_doc_meta,
)
from scripts.linear_sync.lib.issue_factory import (  # noqa: E402
    _default_issue_title,
    build_client,
)
from scripts.linear_sync.sync_engine import load_env  # noqa: E402

STALE_TITLE_RE = re.compile(
    r"Global\s+Pre-read|세션\s*시작\s*시\s*한\s*번\s*로드",
    re.IGNORECASE,
)
DOC_LINEAR_ISSUE_RE = re.compile(
    r"^- \*\*Linear-Issue\*\*:\s*\[?(TEM-\d+)",
    re.MULTILINE | re.IGNORECASE,
)


def _scan_tem_to_plan() -> dict[str, Path]:
    """Map TEM-NNN → blueprint path (doc meta Linear-Issue line)."""
    mapping: dict[str, Path] = {}
    plans_root = _REPO / "docs" / "plans"
    for path in sorted(plans_root.rglob("*.md")):
        if path.name == "README.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        m = DOC_LINEAR_ISSUE_RE.search(text)
        if not m:
            continue
        ident = m.group(1).upper()
        if ident not in mapping:
            mapping[ident] = path
    return mapping


def _desired_title(plan_path: Path) -> str | None:
    text = plan_path.read_text(encoding="utf-8")
    meta = parse_doc_meta(text, plan_path)
    return _default_issue_title(meta, plan_path)


def repair(*, dry_run: bool = False) -> int:
    load_env()
    client, api_key = build_client()
    if not api_key or client is None:
        print("LINEAR_API_KEY missing — cannot repair titles.")
        return 1

    tem_to_plan = _scan_tem_to_plan()
    teams = client.list_teams()
    team_id = teams[0]["id"]
    query = (
        'query { team(id: "%s") { issues(first: 250) '
        "{ nodes { id identifier title } } } }"
    ) % team_id
    res = client._query(query)
    issues = res.get("team", {}).get("issues", {}).get("nodes", [])

    updated = 0
    skipped = 0
    for node in issues:
        title = str(node.get("title") or "")
        if not STALE_TITLE_RE.search(title):
            continue
        ident = str(node.get("identifier") or "").upper()
        plan_path = tem_to_plan.get(ident)
        if not plan_path:
            print(f"  ⚠ {ident}: no blueprint with doc meta Linear-Issue — skip")
            skipped += 1
            continue
        new_title = _desired_title(plan_path)
        if not new_title:
            print(f"  ⚠ {ident}: could not extract H1 title from {plan_path}")
            skipped += 1
            continue
        if new_title == title:
            continue
        print(f"  {ident}: {title!r} -> {new_title!r}")
        if dry_run:
            updated += 1
            continue
        ok = client.update_issue(node["id"], title=new_title)
        if ok:
            updated += 1
        else:
            print(f"  ❌ {ident}: issueUpdate failed")
            skipped += 1

    print(f"Done. {'Would update' if dry_run else 'Updated'} {updated}, skipped {skipped}.")
    return 0 if skipped == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    return repair(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
