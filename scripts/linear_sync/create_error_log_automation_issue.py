#!/usr/bin/env python3
"""Create a Linear issue for the Error Log Automation loop.

Loads ``LINEAR_API_KEY`` from the repo root ``.env`` via ``sync_engine.load_env()``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.linear_sync.lib.issue_factory import create_linear_issue  # noqa: E402
from scripts.linear_sync.sync_engine import load_env  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env()

    title = "[Infra] FE/BE 통합 에러 로그 수집 자동화 및 에이전트 해결 루프 구축"
    description = """## 개요
프론트엔드와 백엔드 전체에서 발생하는 에러 로그를 자동으로 수집하고, 이를 기반으로 Linear 이슈 생성부터 에이전트 해결까지 이어지는 통합 자동화 워크플로우를 구축합니다.

## 주요 목표
1. **로그 수집 자동화**: FE(Console/Sentry) 및 BE(FastAPI/Audit) 로그의 실시간 집계.
2. **이슈 도출**: 수집된 로그를 분석하여 중복 제거 및 Linear 이슈 자동 생성.
3. **상세 계획 수립**: 생성된 이슈에 대해 `docs/plans` Blueprint 초안 자동 생성.
4. **에이전트 이관**: 에이전트가 Blueprint를 기반으로 작업을 수행하고 해결하는 루프 완성.

## 기술 참고
- 관련 워크플로우: `.agents/workflows/linear.md`, `.agents/workflows/plan.md`
- 로깅 시스템: `src/shared/logging`, `apps/renderer/src/utils/logger` (FE)
"""

    try:
        issue = create_linear_issue(
            title=title,
            description=description,
            priority=2,
            labels=["Infra", "Backend", "Feature"],
            dry_run=args.dry_run,
        )
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    if args.dry_run or issue is None:
        return 0

    print(f"created_issue_identifier={issue.get('identifier') or ''}")
    print(f"created_issue_url={issue.get('url') or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
