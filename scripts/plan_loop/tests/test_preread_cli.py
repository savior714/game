"""Regression tests for scripts/plan_loop/preread_cli.py."""

from __future__ import annotations

from scripts.plan_loop.preread_cli import build_parser


def test_build_parser_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args(["docs/plans/PLAN_example.md"])
    assert args.extra_paths == []
    assert args.extra_intents == []
    assert args.phase == "turn1"
