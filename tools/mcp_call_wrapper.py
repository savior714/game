from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _coerce_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def build_sequentialthinking_arguments(
    prompt: str,
    thought_number: int,
    total_thoughts: int,
    next_thought_needed: bool,
) -> dict[str, Any]:
    if not prompt.strip():
        raise ValueError("prompt must not be empty")
    if thought_number < 1:
        raise ValueError("thought_number must be >= 1")
    if total_thoughts < 1:
        raise ValueError("total_thoughts must be >= 1")
    return {
        "thought": prompt.strip(),
        "nextThoughtNeeded": next_thought_needed,
        "thoughtNumber": thought_number,
        "totalThoughts": total_thoughts,
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {"server": args.server, "toolName": args.tool}

    if args.tool == "sequentialthinking":
        payload["arguments"] = build_sequentialthinking_arguments(
            prompt=args.prompt,
            thought_number=args.thought_number,
            total_thoughts=args.total_thoughts,
            next_thought_needed=args.next_thought_needed,
        )
        return payload

    if not args.arguments_json:
        raise ValueError(
            "Non-sequentialthinking tools require --arguments-json to prevent missing arguments."
        )

    try:
        parsed = json.loads(args.arguments_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid --arguments-json: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("--arguments-json must be a JSON object")

    payload["arguments"] = parsed
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build validated MCP CallMcpTool payloads with mandatory arguments mapping."
    )
    parser.add_argument("--server", required=True, help="MCP server identifier")
    parser.add_argument("--tool", required=True, help="MCP tool name")
    parser.add_argument(
        "--prompt",
        default="",
        help="Natural-language prompt to map into tool arguments (required for sequentialthinking)",
    )
    parser.add_argument(
        "--thought-number",
        type=int,
        default=1,
        help="sequentialthinking thoughtNumber",
    )
    parser.add_argument(
        "--total-thoughts",
        type=int,
        default=3,
        help="sequentialthinking totalThoughts",
    )
    parser.add_argument(
        "--next-thought-needed",
        type=_coerce_bool,
        default=True,
        help="sequentialthinking nextThoughtNeeded (true/false)",
    )
    parser.add_argument(
        "--arguments-json",
        default="",
        help="Raw JSON object for non-sequentialthinking tools",
    )
    parser.add_argument(
        "--emit",
        choices=["payload", "arguments"],
        default="payload",
        help="Output full CallMcpTool payload or arguments object only",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print output JSON",
    )
    parser.add_argument(
        "--output-file",
        default="",
        help="Optional path to write output JSON",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    result: dict[str, Any]
    if args.emit == "arguments":
        result = payload["arguments"]
    else:
        result = payload

    if args.pretty:
        output = json.dumps(result, ensure_ascii=True, indent=2)
    else:
        output = json.dumps(result, ensure_ascii=True)

    if args.output_file:
        Path(args.output_file).write_text(f"{output}\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
