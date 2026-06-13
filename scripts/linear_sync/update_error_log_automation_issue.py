#!/usr/bin/env python3
"""Update Linear issue TEM-39 description from Blueprint SSOT (CLI v1)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.linear_sync.sync_engine import load_env  # noqa: E402

API_URL = "https://api.linear.app/graphql"
BLUEPRINT = "docs/plans/archive/agent/PLAN_TEM39_error_log_automation_loop_blueprint.md"


def build_description() -> str:
    return f"""## 개요 (SSOT: {BLUEPRINT})

FE/BE 에러 로그를 **CLI 복사·붙여넣기** 단일 경로로 정규화·PII 마스킹·spec 매핑·agent 프롬프트·(옵션) Blueprint 초안까지 생성합니다.

## v1 범위 (구현 완료)
- `scripts/automation/process_error.py` — `--domain FE|BE`, `--format json|prompt`, `--draft-plan`
- `scripts/automation/lib/` — parsers, sanitizer(`pii_masking.py` 래핑), enricher, prompt_engine, drafter
- `just process-error` — 개발자 단일 진입점
- 검증: `pytest tests/automation/ -q`

## 진단 요약
- **현상**: FE `console.error`, BE `logging` 등 출처별 형식 상이 → LLM/`/diagnose` 전 수동 정규화·마스킹
- **근본 원인**: Raw 로그 → UnifiedLog → 마스킹 → spec → 프롬프트/Blueprint 공통 파이프라인 부재
- **결정 D-TEM39-01**: v1 = CLI 단일 경로 (File Watcher·Fingerprint는 후속)

## 아키텍처 (Seam)
`process_error.py` ↔ parsers ↔ `UnifiedLog` ↔ sanitizer ↔ enricher ↔ prompt_engine ↔ drafter(`plan_lint`)

## Out of Scope (v1)
- 실시간 File Watcher / `watchdog` tail (의존성만 예약)
- Sentry/Telemetry API 자동 수집·Fingerprint 기반 Linear 자동 생성
- 파이프라인 내부 LLM 호출 (분석은 생성된 프롬프트를 에이전트가 수행)
- `/error_ab` 대체 — `scripts/generate_ab_prompt.py` 별도 유지

## 참고
- Blueprint: `{BLUEPRINT}`
- 워크플로: `.agents/workflows/diagnose.md`, `.agents/workflows/plan.md`
- Linear: [TEM-39](https://linear.app/templaremr/issue/TEM-39)
"""


def _graphql(api_key: str, query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        API_URL,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode())
    if payload.get("errors"):
        msg = payload["errors"][0].get("message", str(payload["errors"]))
        raise RuntimeError(msg)
    return payload.get("data") or {}


def _fetch_issue_uuid(api_key: str, identifier: str = "TEM-39") -> str | None:
    q = """
    query GetIssue($id: String!) {
      issue(id: $id) { id }
    }
    """
    res = _graphql(api_key, q, {"id": identifier})
    row = res.get("issue") or {}
    return row.get("id")


def update_issue(api_key: str, issue_id: str, *, dry_run: bool) -> bool:
    title = "Project Blueprint: FE/BE 통합 에러 로그 수집 일원화 및 LLM 프롬프트 자동화"
    description = build_description()
    if dry_run:
        print(f"[dry-run] Would update {issue_id}")
        print(f"Title: {title}")
        print("Description preview (first 400 chars):")
        print(description[:400])
        return True

    mutation = """
    mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
      issueUpdate(id: $id, input: $input) { success }
    }
    """
    variables = {
        "id": issue_id,
        "input": {
            "title": title,
            "description": description,
            "priority": 2,
        },
    }
    data = _graphql(api_key, mutation, variables)
    return bool((data.get("issueUpdate") or {}).get("success"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync TEM-39 Linear description to Blueprint SSOT.")
    parser.add_argument("--dry-run", action="store_true", help="Print payload without API write")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env()
    api_key = (os.environ.get("LINEAR_API_KEY") or "").strip()

    if args.dry_run:
        if update_issue(api_key or "dry", "TEM-39", dry_run=True):
            return 0
        return 1

    if not api_key:
        print("LINEAR_API_KEY not available.", file=sys.stderr)
        return 1

    issue_uuid = _fetch_issue_uuid(api_key)
    if not issue_uuid:
        print("Issue TEM-39 not found.", file=sys.stderr)
        return 1

    if update_issue(api_key, issue_uuid, dry_run=False):
        if not args.dry_run:
            print("TEM-39 description updated successfully.")
        return 0
    print("Failed to update TEM-39 description.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
