#!/usr/bin/env python3
"""SSOT 헤더(문서 메타·경계) 검사 — `verify_doc_ssot_headers.py` 래퍼.

`docs/plans/PLAN_TEM20_*.md` 등에서 `spec_header_verify.py <dir>` 호출명을 사용한다.
구현은 `scripts/verify_doc_ssot_headers.py`에 위임한다.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    runner = root / "scripts" / "verify_doc_ssot_headers.py"
    if len(sys.argv) < 2:
        print("Usage: spec_header_verify.py <directory>", file=sys.stderr)
        return 2
    target = (root / sys.argv[1]).resolve() if not Path(sys.argv[1]).is_absolute() else Path(sys.argv[1]).resolve()
    if not target.is_dir():
        print(f"[ERROR] not a directory: {target}", file=sys.stderr)
        return 2
    return subprocess.call([sys.executable, str(runner), "--dir", str(target)], cwd=root)


if __name__ == "__main__":
    raise SystemExit(main())
