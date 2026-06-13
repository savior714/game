#!/usr/bin/env python3
"""Refresh team label allowlist in linear_team_labels.json from Linear GraphQL.

Updates ``labels`` and ``synced_at`` from the API; preserves curated ``aliases``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.linear_sync.lib.issue_factory import build_client, pick_team_id  # noqa: E402
from scripts.linear_sync.sync_engine import load_env  # noqa: E402

DATA_PATH = Path(__file__).resolve().parent / "data" / "linear_team_labels.json"


def _load_snapshot(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "version": 1,
        "synced_at": "",
        "team_key": "TEM",
        "labels": [],
        "aliases": {},
    }


def _team_key_from_client(client, team_id: str) -> str:
    teams = client.list_teams()
    for node in teams:
        if node.get("id") == team_id:
            return str(node.get("key") or "")
    return ""


def sync_labels_snapshot(*, dry_run: bool = False) -> int:
    load_env()
    client, api_key = build_client()
    if client is None or not api_key:
        print("LINEAR_API_KEY not available — cannot refresh labels from API.", file=sys.stderr)
        return 1

    snapshot = _load_snapshot(DATA_PATH)
    preserved_aliases = dict(snapshot.get("aliases") or {})

    teams = client.list_teams()
    team_id = pick_team_id(teams)
    team_key = _team_key_from_client(client, team_id) or str(snapshot.get("team_key") or "TEM")

    nodes = client.get_team_labels_for_team(team_id)
    api_labels = sorted({str(n["name"]) for n in nodes if n.get("name")})

    synced_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    previous_labels = list(snapshot.get("labels") or [])

    print(f"team_key={team_key}")
    print(f"labels_api_count={len(api_labels)}")
    if previous_labels != api_labels:
        added = sorted(set(api_labels) - set(previous_labels))
        removed = sorted(set(previous_labels) - set(api_labels))
        if added:
            print(f"labels_added={', '.join(added)}")
        if removed:
            print(f"labels_removed={', '.join(removed)}")
    else:
        print("labels_unchanged=true")

    if dry_run:
        print("dry_run=true — no file written")
        print(f"would_write={DATA_PATH}")
        return 0

    out = {
        "version": int(snapshot.get("version") or 1),
        "synced_at": synced_at,
        "team_key": team_key,
        "labels": api_labels,
        "aliases": preserved_aliases,
    }
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote={DATA_PATH}")

    from scripts.linear_sync.lib.label_policy import LabelPolicyError, load_label_policy

    load_label_policy.cache_clear()
    try:
        load_label_policy()
    except LabelPolicyError as exc:
        print(
            "aliases_invalid_after_snapshot: "
            f"{exc}. Re-point aliases in {DATA_PATH.name} to labels_api only.",
            file=sys.stderr,
        )
        return 2

    print("aliases_valid=true")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync Linear team labels into linear_team_labels.json")
    parser.add_argument("--dry-run", action="store_true", help="Print diff only; do not write JSON")
    args = parser.parse_args()
    return sync_labels_snapshot(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
