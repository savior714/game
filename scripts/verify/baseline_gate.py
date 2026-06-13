#!/usr/bin/env python3
"""Baseline diff helpers for incremental verify gates."""

from __future__ import annotations

from pathlib import Path


def load_baseline(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def write_baseline(path: Path, entries: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = sorted(entries)
    header = (
        "# Incremental gate baseline — fail only on NEW entries.\n"
        "# Remove a line when fixed. Regenerate: gate script --update-baseline\n"
    )
    path.write_text(header + "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def filter_new_entries(entries: set[str], baseline: set[str]) -> list[str]:
    return sorted(entries - baseline)
