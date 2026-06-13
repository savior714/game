#!/usr/bin/env python3
"""Record / validate docs-yaml hub check stamp after lint-turn-end (same git HEAD)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_MAX_AGE_SEC = 1800
_STAMP_REL = Path("artifacts/verify/docs-yaml-stamp.json")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def stamp_path() -> Path:
    override = os.environ.get("DOCS_YAML_STAMP_PATH")
    if override:
        return Path(override)
    return repo_root() / _STAMP_REL


def git_head() -> str:
    out = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],  # noqa: S607
        cwd=repo_root(),
        text=True,
    )
    return out.strip()


def write_stamp() -> None:
    path = stamp_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "head": git_head(),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def is_stamp_valid(max_age_sec: int = DEFAULT_MAX_AGE_SEC) -> bool:
    path = stamp_path()
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        recorded_head = str(data["head"]).strip()
        recorded_at = datetime.fromisoformat(str(data["timestamp"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False

    if not recorded_head or recorded_head != git_head():
        return False

    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=UTC)

    age_sec = (datetime.now(UTC) - recorded_at.astimezone(UTC)).total_seconds()
    return 0 <= age_sec <= max_age_sec


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] == "write":
        write_stamp()
        return 0
    if args[0] == "check":
        return 0 if is_stamp_valid() else 1
    print(f"usage: {Path(sys.argv[0]).name} [write|check]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
