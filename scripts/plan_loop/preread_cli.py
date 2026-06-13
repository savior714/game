#!/usr/bin/env python3
"""CLI argument parsing for plan-preread-manifest entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.agent.route_gate_core import VALID_PHASES


def build_parser() -> argparse.ArgumentParser:
    """Return a configured ArgumentParser for the plan-preread-manifest CLI."""
    parser = argparse.ArgumentParser(
        description="Generate Blueprint Context Pre-read Gate section.",
        epilog=(
            "참고: --json 단독 사용 시 JSON 출력 후 종료하며, --write와 함께 지정하면 "
            "JSON 출력 뒤 같은 실행에서 플랜 upsert가 이어집니다."
        ),
    )
    parser.add_argument(
        "plan",
        type=Path,
        help="Path to docs/plans/*.md Blueprint",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Upsert section into the plan file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON manifest",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        dest="extra_paths",
        help="Additional repo-relative path for routing (repeatable)",
    )
    parser.add_argument(
        "--intent",
        action="append",
        default=[],
        dest="extra_intents",
        help="Additional intent keyword for routing (repeatable)",
    )
    parser.add_argument(
        "--write-manifest",
        action="store_true",
        help="Append normalized route bundle to session manifest.",
    )
    parser.add_argument(
        "--phase",
        choices=sorted(VALID_PHASES),
        default="turn1",
        help="Manifest phase when using --write-manifest (default: turn1).",
    )
    return parser
