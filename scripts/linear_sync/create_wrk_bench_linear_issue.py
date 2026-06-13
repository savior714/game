#!/usr/bin/env python3
"""Create a Linear issue for the wrk + HAPI Docker benchmark plan (one-off)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.linear_sync.lib.issue_factory import build_client, create_linear_issue  # noqa: E402
from scripts.linear_sync.sync_engine import LinearClient, load_env  # noqa: E402


def find_completed_state_id(client: LinearClient, issue_uuid: str) -> str | None:
    states = client.get_team_states(issue_uuid)
    for state in states:
        if str(state.get("type") or "").lower() == "completed":
            return state["id"]
        if str(state.get("name") or "").lower() in ("done", "completed"):
            return state["id"]
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env()
    client, api_key = build_client()
    if not api_key:
        print(
            "LINEAR_API_KEY not available after load_env(). "
            "Ensure repo root .env contains LINEAR_API_KEY (see .agents/workflows/linear.md).",
            file=sys.stderr,
        )
        return 1

    description = """## Context
- Plan: `docs/plans/archive/fhir/PLAN_wrk_benchmark_hapi_healthcheck_execution.md`
- Docker: `docker-compose.dev.yml` then `docker-compose.hapi_fhir.yml` on `emr_default`
- wrk: `scripts/benchmark_graphql.sh` + `scripts/wrk_graphql_bench.lua`

## Latest baseline (host)
- ~1135 req/s aggregate, 30s, Non-2xx: 0
- Raw: `scripts/benchmark_results_20260515_010532.txt`
- Spec: `docs/specs/technical/SPEC_TECH_graphql_benchmark_results.md` v0.2
"""

    try:
        issue = create_linear_issue(
            title="Bench: Docker wrk GraphQL + HAPI baseline (PLAN_wrk_benchmark)",
            description=description,
            priority=3,
            labels=["Backend", "FHIR", "Infra"],
            dry_run=args.dry_run,
            client=client,
        )
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    if args.dry_run or issue is None:
        return 0

    ident = issue.get("identifier") or ""
    iid = issue.get("id") or ""
    url = issue.get("url") or ""
    print(f"created_issue_identifier={ident}")
    print(f"created_issue_url={url}")

    assert client is not None
    body = (
        "Conclusion (bench): Docker stack + HAPI; wrk 30s ~1135 req/s, Non-2xx 0; "
        "logs `scripts/benchmark_results_20260515_010532.txt`; SPEC v0.2."
    )
    if not client.add_comment(iid, body):
        print("warning: commentCreate did not report success", file=sys.stderr)

    done_id = find_completed_state_id(client, iid)
    if done_id:
        if client.update_issue_state(iid, done_id):
            print("state_set=completed")
        else:
            print("warning: issueUpdate to completed failed", file=sys.stderr)
    else:
        print("warning: no completed state found; leave issue state manual", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
