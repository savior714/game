#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


TEXT_EXTENSIONS = {".md", ".txt"}


def collect_targets(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS
    )


def validate_file(path: Path) -> str | None:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        return f"{path}: UTF-8 decode failed ({error})"

    if "\ufffd" in content:
        return f"{path}: contains replacement character (�), possible mojibake"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate docs text files for UTF-8 readability and mojibake markers.",
    )
    parser.add_argument(
        "--dir",
        default="docs",
        help="Directory to scan (default: docs)",
    )
    args = parser.parse_args()

    target_dir = Path(args.dir)
    if not target_dir.exists():
        print(f"[ERROR] directory not found: {target_dir}")
        return 2
    if not target_dir.is_dir():
        print(f"[ERROR] not a directory: {target_dir}")
        return 2

    targets = collect_targets(target_dir)
    failures = [failure for path in targets if (failure := validate_file(path))]

    if failures:
        print("[FAIL] Korean text verification failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print(f"[PASS] Verified {len(targets)} file(s) under {target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
