from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.mcp_call_wrapper import build_payload


def _ns(**kwargs: object) -> argparse.Namespace:
    defaults = {
        "server": "user-sequentialthinking",
        "tool": "sequentialthinking",
        "prompt": "원인 분석",
        "thought_number": 1,
        "total_thoughts": 3,
        "next_thought_needed": True,
        "arguments_json": "",
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_build_payload_maps_sequentialthinking_prompt() -> None:
    payload = build_payload(_ns())
    assert payload["server"] == "user-sequentialthinking"
    assert payload["toolName"] == "sequentialthinking"
    assert payload["arguments"]["thought"] == "원인 분석"
    assert payload["arguments"]["nextThoughtNeeded"] is True
    assert payload["arguments"]["thoughtNumber"] == 1
    assert payload["arguments"]["totalThoughts"] == 3


def test_build_payload_requires_prompt_for_sequentialthinking() -> None:
    with pytest.raises(ValueError, match="prompt must not be empty"):
        build_payload(_ns(prompt="   "))


def test_build_payload_requires_arguments_json_for_other_tools() -> None:
    with pytest.raises(ValueError, match="require --arguments-json"):
        build_payload(_ns(tool="searxng_search"))


def test_build_payload_accepts_arguments_json_for_other_tools() -> None:
    payload = build_payload(
        _ns(
            server="user-searxng",
            tool="searxng_search",
            arguments_json='{"query":"cursor mcp"}',
        )
    )
    assert payload["server"] == "user-searxng"
    assert payload["toolName"] == "searxng_search"
    assert payload["arguments"]["query"] == "cursor mcp"
