"""
Linear WorkflowState.type ↔ Blueprint Task `Status` 값 정합성 (LIS 보강).

Linear 팀마다 워크플로 이름은 다르지만, GraphQL `WorkflowState.type`은 제한된 집합이다.
Blueprint는 `todo` | `in_progress` | `done` 만 사용하므로, 아래와 같이 묶어서 매핑한다.

- 미착수 계열: `backlog`, `unstarted`, `todo` → Blueprint `todo`
- 진행 계열: `started`, `in_progress` → Blueprint `in_progress`
- 완료: `completed` → Blueprint `done`

Push 시에는 팀에 실제로 존재하는 상태 노드 중 우선순위가 높은 것을 선택한다.
"""

from __future__ import annotations

from typing import Any, Optional

# Pull: Linear type → blueprint status (첫 매칭 우선)
_LINEAR_TO_BLUEPRINT: tuple[tuple[frozenset[str], str], ...] = (
    (frozenset({"completed"}), "done"),
    (frozenset({"started", "in_progress"}), "in_progress"),
    (frozenset({"backlog", "unstarted", "todo"}), "todo"),
)

# Push: blueprint status → 시도할 Linear `type` 순서 (팀에 없으면 다음 후보)
_BLUEPRINT_TO_LINEAR_PRIORITY: dict[str, tuple[str, ...]] = {
    "done": ("completed",),
    "in_progress": ("started", "in_progress"),
    "todo": ("unstarted", "todo", "backlog"),
}


def linear_type_to_blueprint_status(linear_type: str) -> Optional[str]:
    """Linear `state.type`을 Blueprint Status 문자열로 변환. 미지원이면 None."""
    for types, bp in _LINEAR_TO_BLUEPRINT:
        if linear_type in types:
            return bp
    return None


def linear_type_matches_blueprint(linear_type: str, blueprint_status: str) -> bool:
    """이슈가 이미 Blueprint 상태와 동등한 Linear 타입이면 True (불필요한 상태 변경 스킵)."""
    equiv = linear_type_to_blueprint_status(linear_type)
    return equiv is not None and equiv == blueprint_status


def pick_linear_state_node_for_blueprint(
    team_states: list[dict[str, Any]],
    blueprint_status: str,
) -> Optional[dict[str, Any]]:
    """
    팀의 states 노드 목록에서, Blueprint 상태를 반영할 단일 WorkflowState를 고른다.

    team_states: `[{ "id", "name", "type" }, ...]` (Linear `team.states.nodes`)
    """
    by_type = {s.get("type"): s for s in team_states if s.get("type")}
    for linear_type in _BLUEPRINT_TO_LINEAR_PRIORITY.get(blueprint_status, ()):
        node = by_type.get(linear_type)
        if node:
            return node
    return None
