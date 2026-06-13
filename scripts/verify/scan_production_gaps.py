#!/usr/bin/env python3
"""Production readiness gap scanner — registry diff gate.

Scans apps/renderer/src for critical mock/TODO/hardcoded-user patterns and fails
when a match is not covered by SPEC_TECH_production_readiness_registry.md.

Usage:
  python3 scripts/verify/scan_production_gaps.py          # report only
  python3 scripts/verify/scan_production_gaps.py --check    # exit 1 on uncovered critical
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "docs/specs/technical/SPEC_TECH_production_readiness_registry.md"
RENDERER_SRC = ROOT / "apps/renderer/src"

# Critical signatures (PLAN_RISK02 conceptual sketch)
_CRITICAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("user-123", re.compile(r"user-123")),
    ("mockData", re.compile(r"\bmockData\b")),
    ("useMockData", re.compile(r"\buseMockData\b")),
    ("useMock", re.compile(r"\buseMock\b")),
    ("TODO: Phase", re.compile(r"TODO:\s*Phase\s*\d", re.IGNORECASE)),
]

_LINE_TOLERANCE = 3

_EXCLUDE_DIR_NAMES = {
    "node_modules",
    "__tests__",
    "mocks",
    "stories",
    "design-lab",
    "playground",
    "poc",
}

_EXCLUDE_FILE_SUFFIXES = (".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".stories.tsx")


@dataclass(frozen=True)
class RegistryEntry:
    pr_id: str
    file: str
    line: int | None
    pattern: str | None
    status: str


@dataclass(frozen=True)
class ScanHit:
    file: str
    line: int
    pattern: str
    text: str


def _parse_registry(path: Path) -> list[RegistryEntry]:
    text = path.read_text(encoding="utf-8")
    blocks = re.split(r"(?=^### PR-\d{3}\s*$)", text, flags=re.MULTILINE)
    entries: list[RegistryEntry] = []

    for block in blocks:
        m_id = re.search(r"^### (PR-\d{3})\s*$", block, re.MULTILINE)
        if not m_id:
            continue
        pr_id = m_id.group(1)

        def _field(name: str) -> str | None:
            fm = re.search(rf"- \*\*{name}\*\*:\s*`?([^`\n]+)`?", block)
            return fm.group(1).strip() if fm else None

        file_raw = _field("file")
        if not file_raw:
            continue
        line_raw = _field("line")
        line = int(line_raw) if line_raw and line_raw.isdigit() else None
        pattern = _field("pattern")
        status = _field("status") or "open"
        entries.append(
            RegistryEntry(
                pr_id=pr_id,
                file=file_raw,
                line=line,
                pattern=pattern,
                status=status,
            )
        )
    return entries


def _iter_renderer_files() -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in RENDERER_SRC.walk():
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIR_NAMES]
        rel_parts = Path(dirpath).relative_to(RENDERER_SRC).parts
        if any(p in _EXCLUDE_DIR_NAMES for p in rel_parts):
            continue
        for name in filenames:
            if not name.endswith((".ts", ".tsx")):
                continue
            if name.endswith(_EXCLUDE_FILE_SUFFIXES):
                continue
            out.append(Path(dirpath) / name)
    return sorted(out)


def _scan_file(path: Path) -> list[ScanHit]:
    rel = path.relative_to(ROOT).as_posix()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    hits: list[ScanHit] = []
    for i, line in enumerate(lines, start=1):
        for label, pat in _CRITICAL_PATTERNS:
            if pat.search(line):
                hits.append(ScanHit(file=rel, line=i, pattern=label, text=line.strip()))
    return hits


def _pattern_matches_entry(entry_pattern: str, hit: ScanHit) -> bool:
    ep = entry_pattern.lower()
    if ep in hit.pattern.lower() or ep in hit.text.lower():
        return True
    return bool(re.search(re.escape(entry_pattern), hit.text, re.IGNORECASE))


def _entry_covers(entry: RegistryEntry, hit: ScanHit) -> bool:
    if entry.file != hit.file:
        return False
    # file + pattern: one registry row covers all occurrences in that file (§2.1 dedupe)
    if entry.pattern:
        return _pattern_matches_entry(entry.pattern, hit)
    if entry.line is not None:
        return abs(entry.line - hit.line) <= _LINE_TOLERANCE
    return True


def _hit_covered(entries: list[RegistryEntry], hit: ScanHit) -> bool:
    return any(_entry_covers(e, hit) for e in entries)


def run_check(*, registry_path: Path = REGISTRY, verbose: bool = True) -> int:
    if not registry_path.is_file():
        print(f"ERROR: registry not found: {registry_path}", file=sys.stderr)
        return 1

    entries = _parse_registry(registry_path)
    if len(entries) < 20:
        print(
            f"ERROR: registry has {len(entries)} entries (expected ≥ 20)",
            file=sys.stderr,
        )
        return 1

    all_hits: list[ScanHit] = []
    for fp in _iter_renderer_files():
        all_hits.extend(_scan_file(fp))

    uncovered = [h for h in all_hits if not _hit_covered(entries, h)]

    if verbose:
        print(f"Registry entries: {len(entries)}")
        print(f"Critical hits scanned: {len(all_hits)}")
        print(f"Uncovered critical: {len(uncovered)}")
        for h in uncovered:
            print(f"  UNREGISTERED {h.file}:{h.line} [{h.pattern}] {h.text[:80]}")

    if uncovered:
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Production readiness gap scanner")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when critical hits are not in the registry",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=REGISTRY,
        help="Path to SPEC_TECH_production_readiness_registry.md",
    )
    args = parser.parse_args()

    if args.check:
        sys.exit(run_check(registry_path=args.registry))
    else:
        code = run_check(registry_path=args.registry)
        if code == 0:
            print("OK: all critical hits are registered.")
        sys.exit(code)


if __name__ == "__main__":
    main()
