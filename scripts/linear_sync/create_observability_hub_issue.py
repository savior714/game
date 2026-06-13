#!/usr/bin/env python3
"""Create Linear issue TEM-50 for the Unified Error Observability Hub (TEM-39 follow-up)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.linear_sync.lib.issue_factory import build_client, create_linear_issue  # noqa: E402
from scripts.linear_sync.sync_engine import load_env  # noqa: E402

BLUEPRINT = "docs/plans/archive/blueprints/PLAN_TEM50_unified_error_observability_hub_blueprint.md"
PARENT_ISSUE = "TEM-39"


def build_description() -> str:
    return f"""## 개요 (SSOT: `{BLUEPRINT}`)

런타임 **전 구간**(FE·BE·BFF·Desktop·Worker 등) 에러를 **단일 허브**(`var/log/emr/hub/events.jsonl`)에 모아 **CLI·Admin UI**에서 조회한다. TEM-39 v1의 `process_error`·PII sanitizer는 ingest 직후 재사용한다.

## v2 구현 상태 (2026-05-16) — **완료·아카이브**
| Phase | 내용 | 상태 |
|:---|:---|:---|
| 0 | Blueprint·Linear·gitignore | done |
| 1 | HubEvent·jsonl store·fingerprint | done |
| 2 | Ingest API·BE handler·PII·prompt | done |
| 3 | FE/BFF telemetry `flushToHub` | done |
| 4 | `just error-logs`·`error-hub-watch` | done |
| 5 | Admin `/dashboard/admin/errors` | done |
| 6 | Desktop IPC stub·`SPEC_TECH_error_observability_hub.md` | done |
| 7 | E2E sequential pytest | done |

**종료 게이트**: `pytest tests/observability/` 46건·`plan_close_gate` PASS (2026-05-16).

## 운영 SSOT
- Spec: `docs/specs/technical/SPEC_TECH_error_observability_hub.md`
- CLI: `just error-logs`, `just error-hub-watch`
- Admin: `/dashboard/admin/errors`
- Desktop: `apps/desktop-tauri/src-tauri/src/hub_forward.rs` → loopback POST (`domain=DESKTOP`)

## 선행 완료 (TEM-39 v1)
- `just process-error`, `scripts/automation/lib/` — Transform 파이프라인
- Blueprint: `docs/plans/archive/agent/PLAN_TEM39_error_log_automation_loop_blueprint.md`

## Out of Scope (본 트랙)
- Sentry/OTEL SSOT, Sidecar 전체 파서, Linear 자동 이슈 생성

## 참고
- 부모/연관: [{PARENT_ISSUE}](https://linear.app/templaremr/issue/TEM-39)
- 워크플로: `.agents/workflows/diagnose.md`, `.agents/workflows/plan.md`
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env()
    client, api_key = build_client()
    if not api_key and not args.dry_run:
        print("LINEAR_API_KEY not available.", file=sys.stderr)
        return 1

    if client:
        existing = client.get_issue("TEM-50")
        if existing:
            print("TEM-50 already exists — skip create.")
            return 0

    parent_uuid = None
    if client:
        parent = client.get_issue(PARENT_ISSUE)
        parent_uuid = parent.get("id") if parent else None

    try:
        issue = create_linear_issue(
            title="[Infra] 전 구간 통합 에러 관측 허브 (Unified Error Observability Hub)",
            description=build_description(),
            priority=2,
            labels=["Infra", "Backend", "Feature"],
            parent_id=parent_uuid,
            dry_run=args.dry_run,
            client=client,
        )
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    if args.dry_run or issue is None:
        return 0

    print(f"created_issue_identifier={issue.get('identifier')}")
    print(f"created_issue_url={issue.get('url')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
