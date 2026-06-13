#!/usr/bin/env python3
"""
Linear GraphQL Schema Introspection Layer (LIS-012).

Linear API mutation signature는 버전별로 변경될 수 있으므로,
에이전트 자동화 시 동적 스키마 인트로스펙션을 통해 최신 서명을 확인한다.

주요 기능:
  - Mutation 필드명·인자 타입 동적 조회
  - WorkflowState 타입별 ID 매핑 캐싱
  - API 변경 감지 및 경고

SSOT: scripts/linear_sync/lib/schema_introspector.py
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from typing import Any

# ============================================================================
# Cache Location (repo-root relative)
# ============================================================================
_CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / ".cache" / "linear_schema"
_SCHEMA_CACHE_FILE = _CACHE_DIR / "introspection.json"
_TTL_SECONDS = 3600  # 1시간 캐시 유효기간


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class MutationField:
    """Mutation 필드 정보."""
    name: str
    input_type: str
    args: list[dict[str, Any]] = dc_field(default_factory=list)


@dataclass
class WorkflowStateNode:
    """WorkflowState 노드 (ID + 타입 매핑용)."""
    id: str
    name: str
    type: str  # "todo", "in_progress", "completed", "canceled"


@dataclass
class SchemaSnapshot:
    """인트로스펙션 결과 스냅샷."""
    timestamp: float
    mutations: dict[str, MutationField] = dc_field(default_factory=dict)
    team_states: list[WorkflowStateNode] = dc_field(default_factory=list)
    issue_update_input_fields: list[str] = dc_field(default_factory=list)
    api_version_hint: str = ""


# ============================================================================
# GraphQL Introspection Queries
# ============================================================================

QUERY_MUTATION_FIELDS = """
query GetMutationFields {
  __type(name: "Mutation") {
    name
    fields {
      name
      type { name kind }
      args { name type { name kind } }
    }
  }
}
"""

QUERY_ISSUE_UPDATE_INPUT = """
query GetIssueUpdateInput {
  __type(name: "IssueUpdateInput") {
    name
    inputFields {
      name
      type { name kind }
    }
  }
}
"""

QUERY_TEAM_STATES = """
query GetTeamStates($teamId: String!) {
  team(id: $teamId) {
    id
    states { nodes { id name type } }
  }
}
"""


# ============================================================================
# HTTP Client (same pattern as sync_engine.py for consistency)
# ============================================================================

def _http_post(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    """GraphQL POST 요청 — sync_engine과 동일한 패턴."""
    req = urllib.request.Request(  # noqa: S310
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:  # noqa: S310
            result = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        msg = f"HTTP 요청 실패: {exc}"
        raise RuntimeError(msg) from exc

    if "errors" in result:
        err_msg = result["errors"][0].get("message", "Unknown error")
        msg = f"GraphQL 에러: {err_msg}"
        raise RuntimeError(msg)
    return result.get("data", {})


# ============================================================================
# Schema Introspector Class
# ============================================================================

class SchemaIntrospector:
    """Linear GraphQL 스키마 동적 인트로스펙션."""

    API_URL = "https://api.linear.app/graphql"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
        }
        self._snapshot: SchemaSnapshot | None = None
        self._team_id_cache: str | None = None

    # ------------------------------------------------------------------
    # Cache Management
    # ------------------------------------------------------------------

    def _load_cache(self) -> SchemaSnapshot | None:  # pyright: ignore[reportUnknownVariableType]
        if not _SCHEMA_CACHE_FILE.exists():
            return None
        try:
            data = json.loads(_SCHEMA_CACHE_FILE.read_text())
            age = time.time() - data.get("timestamp", 0)
            if age > _TTL_SECONDS:
                return None  # 만료됨
            snap = SchemaSnapshot(**data)
            snap.timestamp = data["timestamp"]
            return snap
        except Exception:
            return None

    def _save_cache(self, snapshot: SchemaSnapshot):  # pyright: ignore[reportUnknownVariableType]
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "timestamp": snapshot.timestamp,
            "mutations": {k: v.__dict__ for k, v in snapshot.mutations.items()},
            "team_states": [s.__dict__ for s in snapshot.team_states],
            "issue_update_input_fields": snapshot.issue_update_input_fields,
            "api_version_hint": snapshot.api_version_hint,
        }
        _SCHEMA_CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False))

    # ------------------------------------------------------------------
    # Introspection Methods
    # ------------------------------------------------------------------

    def fetch_snapshot(self, team_id: str | None = None) -> SchemaSnapshot:  # pyright: ignore[reportUnknownVariableType]
        """스냅샷을 새로고침 (캐시 무시)."""
        data = _http_post(
            self.API_URL,
            self.headers,
            {"query": QUERY_MUTATION_FIELDS},
        )

        snapshot = SchemaSnapshot(timestamp=time.time())

        # Mutation 필드 파싱
        mutation_type = data.get("__type") or {}  # pyright: ignore[reportUnknownVariableType]
        for mf in mutation_type.get("fields", []):  # pyright: ignore[reportUnknownVariableType]
            if "issueUpdate" in mf["name"]:
                type_name = (mf.get("type") or {}).get("name", "")  # pyright: ignore[reportUnknownVariableType]
                args = [a.get("type", {}).get("name", "") for a in mf.get("args", [])]
                snapshot.mutations[mf["name"]] = MutationField(
                    name=mf["name"],  # pyright: ignore[reportUnknownArgumentType]
                    input_type=type_name,  # pyright: ignore[reportUnknownArgumentType]
                    args=args,  # pyright: ignore[reportUnknownArgumentType]
                )

        # IssueUpdateInput 필드 파싱
        update_input = _http_post(
            self.API_URL,
            self.headers,
            {"query": QUERY_ISSUE_UPDATE_INPUT},
        )
        type_info = update_input.get("__type") or {}  # pyright: ignore[reportUnknownVariableType]
        for f in type_info.get("inputFields", []):  # pyright: ignore[reportUnknownVariableType]
            snapshot.issue_update_input_fields.append(f["name"])

        # 팀 상태 노드 (team_id 제공 시)
        if team_id:
            self._team_id_cache = team_id
            states_data = _http_post(
                self.API_URL,
                self.headers,
                {"query": QUERY_TEAM_STATES, "variables": {"teamId": team_id}},
            )
            team_info = states_data.get("team") or {}  # pyright: ignore[reportUnknownVariableType]
            for node in (team_info.get("states") or {}).get("nodes", []):  # pyright: ignore[reportUnknownVariableType]
                snapshot.team_states.append(WorkflowStateNode(
                    id=node["id"],
                    name=node["name"],
                    type=node["type"],
                ))

        self._save_cache(snapshot)
        self._snapshot = snapshot
        return snapshot

    def get_cached_snapshot(self, team_id: str | None = None) -> SchemaSnapshot:  # pyright: ignore[reportUnknownVariableType]
        """캐시된 스냅샷 반환 (만료 시 새로고침)."""
        if self._snapshot and time.time() - self._snapshot.timestamp < _TTL_SECONDS:
            # 캐시가 유효하지만 team_states가 없으면 team_id로 보완
            if not self._snapshot.team_states and team_id:
                return self.fetch_snapshot(team_id)
            return self._snapshot

        # 캐시 로드 시도
        cached = self._load_cache()
        if cached:
            # team_states 보강 필요 시
            if not cached.team_states and team_id:
                return self.fetch_snapshot(team_id)
            self._snapshot = cached
            return cached

        # 캐시 없음 — 새로고침
        return self.fetch_snapshot(team_id)

    # ------------------------------------------------------------------
    # Query Builders (스키마 기반 동적 쿼리 생성)
    # ------------------------------------------------------------------

    def build_issue_update_mutation(self, issue_uuid: str, **kwargs: Any) -> tuple[str, dict[str, Any]]:  # pyright: ignore[reportUnknownVariableType]
        """인트로스펙션 기반으로 issueUpdate mutation 빌드."""
        if not self._snapshot or "issueUpdate" not in self._snapshot.mutations:
            msg = "Mutation 'issueUpdate'를 찾을 수 없습니다. 스키마 인트로스펙션을 먼저 실행하세요."
            raise RuntimeError(msg)

        input_fields = ", ".join([f"{k}: ${k}" for k in kwargs])
        variables_def = ", ".join([f"${k}: String" for k in kwargs])  # 기본값: String

        query = f"""
        mutation UpdateIssue($id: String!, {variables_def}) {{
          issueUpdate(id: $id, input: {{ {input_fields} }}) {{
            success
            issue {{ id title state {{ name type }} }}
          }}
        }}
        """
        variables: dict[str, Any] = {"id": issue_uuid}
        variables.update(kwargs)
        return query, variables

    def find_state_id_by_type(self, state_type: str) -> str | None:  # pyright: ignore[reportUnknownVariableType]
        """타입별 WorkflowState ID 조회 (예: 'completed' → UUID)."""
        if not self._snapshot or not self._snapshot.team_states:
            msg = "팀 상태 노드가 없습니다. fetch_snapshot(team_id=...)를 먼저 호출하세요."
            raise RuntimeError(msg)

        # 타입 매핑: Linear API type -> blueprint status
        type_map = {
            "completed": "done",
            "in_progress": "in_progress",
            "started": "in_progress",
            "todo": "todo",
            "backlog": "todo",
            "unstarted": "todo",
            "canceled": "cancelled",
        }

        target = type_map.get(state_type, state_type)
        for node in self._snapshot.team_states:
            if node.type == target or (state_type == "done" and node.type == "completed"):
                return node.id
        return None

    # ------------------------------------------------------------------
    # Schema Change Detection
    # ------------------------------------------------------------------

    def check_for_changes(self, team_id: str | None = None) -> list[str]:  # pyright: ignore[reportUnknownVariableType]
        """이전 스냅샷과 비교하여 API 변경사항 감지."""
        if not self._snapshot:
            return ["스냅샷 없음 — 먼저 fetch_snapshot() 호출 필요"]

        current = self.fetch_snapshot(team_id)
        warnings: list[str] = []

        # Mutation 필드 변화 감지
        old_mutations = set(self._snapshot.mutations.keys())
        new_mutations = set(current.mutations.keys())
        if old_mutations != new_mutations:
            removed = old_mutations - new_mutations
            added = new_mutations - old_mutations
            if removed:
                warnings.append(f"\u26a0\ufe0f Mutation 필드 제거됨: {removed}")
            if added:
                warnings.append(f"i Mutation 필드 추가됨: {added}")

        # IssueUpdateInput 필드 변화 감지
        old_fields = set(self._snapshot.issue_update_input_fields)
        new_fields = set(current.issue_update_input_fields)
        if old_fields != new_fields:
            removed = old_fields - new_fields
            added = new_fields - old_fields
            if removed:
                warnings.append(f"\u26a0\ufe0f IssueUpdateInput 필드 제거됨: {removed}")
            if added:
                warnings.append(f"i IssueUpdateInput 필드 추가됨: {added}")

        return warnings or ["\u2705 API 스키마 변경사항 없음"]


# ============================================================================
# CLI Entry Point (just linear-schema-check)
def main() -> None:  # pyright: ignore[reportUnknownVariableType]
    from scripts.linear_sync.sync_engine import load_env  # noqa: PLC0415

    load_env()
    api_key = (os.environ.get("LINEAR_API_KEY") or "").strip()
    if not api_key:
        print("❌ LINEAR_API_KEY가 없습니다. 루트 .env에 키를 두세요.")
        raise SystemExit(1)

    parser = argparse.ArgumentParser(description="Linear GraphQL Schema Introspection (LIS-012)")
    parser.add_argument("--refresh", action="store_true", help="캐시 무시하고 새로고침")
    parser.add_argument("--team-id", type=str, default="", help="팀 ID (상태 노드 조회용)")
    args = parser.parse_args()

    introspector = SchemaIntrospector(api_key)
    snapshot = introspector.fetch_snapshot(args.team_id) if args.refresh else introspector.get_cached_snapshot(args.team_id)

    print("=== 🛰️ Linear Schema Introspection Report ===")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(snapshot.timestamp))}")
    print(f"Cached TTL: {_TTL_SECONDS}s")
    print()

    # Mutation 필드
    print("📝 Available Mutations:")
    for name, mfield in snapshot.mutations.items():
        arg_strs = []
        for a in mfield.args:
            if isinstance(a, dict):
                arg_strs.append(a["type"]["name"])
            else:
                arg_strs.append(str(a))
        print(f"  - {name}({', '.join(arg_strs)})")
    print()

    # IssueUpdateInput 필드
    print("📋 IssueUpdateInput Fields:")
    for f in snapshot.issue_update_input_fields:
        marker = "⭐" if f == "stateId" else "  "
        print(f"  {marker} {f}")
    print()

    # 팀 상태 노드
    if snapshot.team_states:
        print("🏷️ Workflow States:")
        for node in snapshot.team_states:
            print(f"  - {node.name} ({node.type}) -> ID: {node.id[:8]}...")
        print()

    # 변경 감지 (새로고침 시)
    if args.refresh and args.team_id:
        warnings = introspector.check_for_changes(args.team_id)
        for w in warnings:
            print(w)


if __name__ == "__main__":
    main()
