#!/usr/bin/env python3
"""Environment loading and Linear API key validation."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from scripts.linear_sync.linear_client import LinearClient

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

__all__ = ["load_env", "validate_api_key"]


def load_env() -> None:
    """Populate os.environ from repo-root ``.env`` (including ``LINEAR_API_KEY``).

    경로는 **저장소 루트** 기준(스크립트 위치에서 계산) — 호출 시 CWD와 무관하게 동일 파일을 읽는다.
    LINEAR_API_KEY는 .env 값을 항상 우선한다(쉘 export 무시).
    """
    env_path = _REPO_ROOT / ".env"
    if env_path.exists():
        for _line in env_path.read_text().splitlines():
            line = _line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                if key == "LINEAR_API_KEY" or key not in os.environ:
                    os.environ[key] = value.strip()


def validate_api_key(api_key: str) -> LinearClient:
    """Validate a Linear API key and return an authenticated client.

    Raises SystemExit(2) on any validation failure.
    """
    if not api_key:
        print("❌ LINEAR_API_KEY 가 없습니다. 루트 `.env` 파일에 설정하세요.", file=sys.stderr)
        print("   예: LINEAR_API_KEY=lin_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx", file=sys.stderr)
        raise SystemExit(2)

    if not api_key.startswith("lin_"):
        print("❌ LINEAR_API_KEY 형식이 올바르지 않습니다. 'lin_' 로 시작해야 합니다.", file=sys.stderr)
        print(f"   현재 값: {api_key[:20]}...", file=sys.stderr)
        raise SystemExit(2)

    if len(api_key) < 30:
        print("❌ LINEAR_API_KEY 길이가 너무 짧습니다. 최소 30 자 이상이어야 합니다.", file=sys.stderr)
        print(f"   현재 길이: {len(api_key)} 자", file=sys.stderr)
        raise SystemExit(2)

    client = LinearClient(api_key)
    try:
        test_query = """
        query {
            viewer {
                id
                teams {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
            }
        }
        """
        response = client._query_with_stale_protection(test_query)

        if "errors" in response:
            error_msg = str(response["errors"])
            if "Invalid API key" in error_msg or "Authentication" in error_msg:
                print(
                    "❌ LINEAR_API_KEY 가 유효하지 않습니다. Linear 에서 인증에 실패했습니다.",
                    file=sys.stderr,
                )
                print(f"   에러: {error_msg}", file=sys.stderr)
                raise SystemExit(2)
        elif "viewer" not in response or not response["viewer"]:
            print(
                "❌ LINEAR_API_KEY 가 유효하지 않습니다. Linear API 응답이 없습니다.",
                file=sys.stderr,
            )
            raise SystemExit(2)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"❌ LINEAR_API_KEY 검증 실패: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    print("✅ LINEAR_API_KEY 검증 통과 — Linear API 사용 가능.", file=sys.stderr)
    return client
