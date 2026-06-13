#!/usr/bin/env python3
"""Print a single KEY=value from a dotenv file (no shell sourcing).

Used by verify so only ``DATABASE_URL`` is merged from ``.env`` without
polluting the process environment (e.g. ``ALLOWED_ORIGINS`` JSON for Settings).
"""

from __future__ import annotations

import sys
from pathlib import Path


def _parse_assignment(line: str) -> tuple[str, str] | None:
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        return None
    key, _, rest = s.partition("=")
    key = key.strip()
    if not key:
        return None
    val = rest.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
        val = val[1:-1]
    return key, val


def main() -> None:
    if len(sys.argv) < 3:
        sys.stderr.write("usage: read_dotenv_key.py <path-to-.env> <KEY>\n")
        raise SystemExit(2)
    path = Path(sys.argv[1])
    want = sys.argv[2]
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for raw in text.splitlines():
        parsed = _parse_assignment(raw)
        if parsed and parsed[0] == want:
            sys.stdout.write(parsed[1])
            return


if __name__ == "__main__":
    main()
