#!/usr/bin/env python3
"""Assert renderer local vs Vercel demo env example profiles stay in sync.

Usage:
  uv run python scripts/verify/check_renderer_deployment_profiles.py
  just verify-renderer-profiles
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RENDERER = _REPO_ROOT / "apps" / "renderer"
_LOCAL_EXAMPLE = _RENDERER / ".env.local.example"
_VERCEL_EXAMPLE = _RENDERER / ".env.vercel.example"


def _parse_dotenv(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, rest = line.partition("=")
        key = key.strip()
        if key:
            out[key] = rest.strip()
    return out


def _fail(msg: str) -> None:
    print(f"check_renderer_deployment_profiles: {msg}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    local = _parse_dotenv(_LOCAL_EXAMPLE)
    vercel = _parse_dotenv(_VERCEL_EXAMPLE)

    local_msw = local.get("NEXT_PUBLIC_MSW_ENABLED", "")
    local_api = local.get("NEXT_PUBLIC_API_BASE_URL", "")
    vercel_msw = vercel.get("NEXT_PUBLIC_MSW_ENABLED", "")
    vercel_api = vercel.get("NEXT_PUBLIC_API_BASE_URL", "")

    if local_msw not in ("false", "0"):
        _fail(
            f"{_LOCAL_EXAMPLE}: NEXT_PUBLIC_MSW_ENABLED must be false (got {local_msw!r})",
        )
    if local_api != "http://127.0.0.1:8000":
        _fail(
            f"{_LOCAL_EXAMPLE}: NEXT_PUBLIC_API_BASE_URL must be http://127.0.0.1:8000 "
            f"(got {local_api!r})",
        )

    if vercel_msw not in ("true", "1"):
        _fail(
            f"{_VERCEL_EXAMPLE}: NEXT_PUBLIC_MSW_ENABLED must be true (got {vercel_msw!r})",
        )
    if vercel_api.strip():
        _fail(
            f"{_VERCEL_EXAMPLE}: NEXT_PUBLIC_API_BASE_URL must be empty for demo "
            f"(got {vercel_api!r})",
        )

    print("check_renderer_deployment_profiles: OK")


if __name__ == "__main__":
    main()
