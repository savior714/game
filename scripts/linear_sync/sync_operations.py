#!/usr/bin/env python3
"""Blueprint ↔ Linear incremental sync operations (push/pull)."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Optional

from scripts.linear_sync.lib.label_policy import (
    canonicalize_for_linear,
    normalize_label_names,
    resolve_label_names_for_team,
)
from scripts.linear_sync.lib.parser import PlanParser
from scripts.linear_sync.lib.plan_metadata import (
    is_conclusion_placeholder,
    is_linear_placeholder,
)
from scripts.linear_sync.lib.state_mapping import (
    linear_type_matches_blueprint,
    linear_type_to_blueprint_status,
    pick_linear_state_node_for_blueprint,
)
from scripts.linear_sync.linear_client import LinearClient


def _float_eq(a: float, b: float, tol: float = 1e-9) -> bool:
    """Float comparison with tolerance for floating-point precision."""
    return abs(float(a) - float(b)) < tol


class SyncEngine:
    def __init__(self, client: Optional[LinearClient] = None, dry_run: bool = False):
        self.client = client
        self.dry_run = dry_run
        self.push_failed = False
        self._issue_cache: dict[str, dict] = {}
        self._comments_cache: dict[str, list[dict]] = {}
        self._current_plan_path: Path | None = None
        self._synced_linear_ids: set[str] = set()

    def parse_tasks(self, file_path: Path) -> list[dict[str, Any]]:
        parser = PlanParser()
        tasks = parser.parse(file_path)
        return [task.to_dict() for task in tasks]

    @staticmethod
    def _effective_task_labels(task: dict, doc_meta_labels: list[str]) -> list[str]:
        if task.get("labels"):
            return list(task["labels"])
        return list(doc_meta_labels)

    def _fail_label_resolution(self, failures: list[str], linear_id: str) -> None:
        self.push_failed = True
        print(
            f"  ❌ Unresolved label(s) for {linear_id}: {', '.join(failures)}",
            file=sys.stderr,
        )

    def sync_task(self, task: dict, *, doc_meta_labels: Optional[list[str]] = None):
        linear_id = task["linear_id"]
        if not linear_id or is_linear_placeholder(linear_id):
            return

        print(f"🔄 Syncing {task['id']} -> {linear_id} ({task['status']})")

        # Skip state/priority/label sync if this linear_id was already synced
        # (multiple tasks may share the same Linear issue, e.g. subtasks under one parent)
        if linear_id in self._synced_linear_ids:
            print(f"  ⏭️  Skipped (linear_id {linear_id} already synced — only updating comment)")
            # Skip to comment sync below
            task_conclusion = task.get("conclusion", "")
            if task_conclusion and self.client:
                issue = self._issue_cache.get(linear_id)
                if not issue:
                    try:
                        issue = self.client.get_issue(linear_id)
                        if issue:
                            self._issue_cache[linear_id] = issue
                    except Exception:
                        pass
                if issue:
                    comment_body = (
                        f"### Task Done: {task['id']}\n**Title**: {task['title']}\n\n"
                        f"**Conclusion**:\n{task_conclusion}"
                    )
                    existing_comment = self.client.get_task_comment(issue["id"], task["id"])
                    needs_update = False
                    if not existing_comment:
                        needs_update = True
                    elif existing_comment.get("body", "").strip() != comment_body.strip():
                        needs_update = True
                    if needs_update:
                        if self.dry_run:
                            action = "update" if existing_comment else "add"
                            print(
                                f"  [Dry-Run] Would {action} comment to {linear_id}"
                            )
                        else:
                            try:
                                success = self.client.add_comment(issue["id"], comment_body)
                                if success:
                                    print("  ✅ Conclusion added/updated as comment")
                                else:
                                    self.push_failed = True
                                    print(f"  ❌ add_comment failed for {linear_id}")
                            except Exception as exc:
                                self.push_failed = True
                                print(
                                    f"  ❌ add_comment exception for {linear_id}: {exc}",
                                    file=sys.stderr,
                                )
            return

        target_raw = self._effective_task_labels(task, doc_meta_labels or [])
        resolved, unknown = normalize_label_names(target_raw)
        if unknown:
            self._fail_label_resolution(unknown, linear_id)
            return

        if not self.client:
            if self.dry_run:
                print(
                    "  [Dry-Run] Client not initialized (missing API key), but parsing looks correct."
                )
            return

        if linear_id in self._issue_cache:
            issue = self._issue_cache[linear_id]
        else:
            try:
                issue = self.client.get_issue(linear_id)
            except Exception as exc:
                self.push_failed = True
                err = str(exc).lower()
                if "401" in err or "unauthorized" in err:
                    print(
                        "  ❌ Linear API 401 — LINEAR_API_KEY가 잘못되었거나 만료되었을 수 있습니다."
                    )
                else:
                    print(f"  ❌ Linear API 오류: {exc}")
                return
            if issue:
                self._issue_cache[linear_id] = issue

        if not issue:
            self.push_failed = True
            print(f"  ⚠️ Linear issue {linear_id} not found.")
            return

        bp_status = task["status"]
        current_type = issue["state"]["type"]
        update_input: dict[str, Any] = {}

        if not linear_type_matches_blueprint(current_type, bp_status):
            states = self.client.get_team_states(linear_id)
            target_state = pick_linear_state_node_for_blueprint(states, bp_status)
            if target_state:
                update_input["stateId"] = target_state["id"]

        if task["priority"] is not None:
            current_priority = issue.get("priority")
            if current_priority is None:
                current_priority = 0.0
            target_priority = float(task["priority"])
            if not _float_eq(target_priority, float(current_priority)):
                update_input["priority"] = target_priority

        if resolved:
            current_nodes = issue.get("labels", {}).get("nodes", [])
            current_canon = canonicalize_for_linear(
                [str(label["name"]) for label in current_nodes]
            )
            target_canon = canonicalize_for_linear(resolved)
            if current_canon != target_canon:
                team_uuid = self.client.get_team_id_for_issue(linear_id)
                if not team_uuid:
                    self.push_failed = True
                    print(
                        f"  ❌ Could not resolve team for label sync on {linear_id}",
                        file=sys.stderr,
                    )
                else:
                    team_nodes = self.client.get_team_labels_for_team(team_uuid)
                    label_ids, label_failures = resolve_label_names_for_team(
                        resolved, team_nodes
                    )
                    if label_failures:
                        self._fail_label_resolution(label_failures, linear_id)
                        return
                    if label_ids:
                        update_input["labelIds"] = label_ids
                    else:
                        self._fail_label_resolution(resolved, linear_id)
                        return

        if update_input:
            if self.dry_run:
                print(f"  [Dry-Run] Would update {linear_id}: {update_input}")
            else:
                success = self.client.update_issue(issue["id"], **update_input)
                if success:
                    print(f"  ✅ Updated fields: {list(update_input.keys())}")
                else:
                    self.push_failed = True
                    print(f"  ❌ issueUpdate failed for {linear_id}")
            self._synced_linear_ids.add(linear_id)

        if task["conclusion"]:
            comment_body = (
                f"### Task Done: {task['id']}\n**Title**: {task['title']}\n\n"
                f"**Conclusion**:\n{task['conclusion']}"
            )
            existing_comment = self.client.get_task_comment(issue["id"], task["id"])

            needs_update = False
            if not existing_comment:
                needs_update = True
            elif existing_comment.get("body", "").strip() != comment_body.strip():
                needs_update = True

            if needs_update:
                if self.dry_run:
                    action = "update" if existing_comment else "add"
                    print(
                        f"  [Dry-Run] Would {action} comment to {linear_id} "
                        "(content mismatch or new)"
                    )
                else:
                    if existing_comment:
                        print(
                            f"  📝 Conclusion content changed for {task['id']}, "
                            "adding updated comment."
                        )

                    try:
                        success = self.client.add_comment(issue["id"], comment_body)
                        if success:
                            print("  ✅ Conclusion added/updated as comment")
                        else:
                            self.push_failed = True
                            print(f"  ❌ add_comment failed for {linear_id}")
                    except Exception as exc:
                        self.push_failed = True
                        print(
                            f"  ❌ add_comment exception for {linear_id}: {exc}",
                            file=sys.stderr,
                        )
            else:
                print(f"  ✔️ Conclusion already in sync for {task['id']}")

    def pull_sync_task(self, task: dict):
        linear_id = task["linear_id"]
        if not linear_id or is_linear_placeholder(linear_id):
            return

        print(f"🔄 Pulling {task['id']} <- {linear_id}")

        if not self.client:
            if self.dry_run:
                print(
                    "  [Dry-Run] Client not initialized (missing API key), but parsing looks correct."
                )
            return

        try:
            issue = self.client.get_issue(linear_id)
        except Exception as exc:
            err = str(exc).lower()
            if "401" in err or "unauthorized" in err:
                print(
                    "  ❌ Linear API 401 — LINEAR_API_KEY가 잘못되었거나 만료되었을 수 있습니다."
                )
            else:
                print(f"  ❌ Linear API 오류: {exc}")
            return

        if not issue:
            print(f"  ⚠️ Linear issue {linear_id} not found.")
            return

        linear_status_type = issue["state"]["type"]
        new_local_status = linear_type_to_blueprint_status(linear_status_type)
        new_priority = int(issue.get("priority") or 0)
        new_labels = [
            label["name"].lower()
            for label in issue.get("labels", {}).get("nodes", [])
        ]

        updates: dict[str, Any] = {}
        if new_local_status and new_local_status != task["status"]:
            updates["status"] = new_local_status

            if new_local_status == "done":
                local_conclusion = task.get("conclusion", "").strip()
                if not local_conclusion or is_conclusion_placeholder(local_conclusion):
                    pulled_conclusion = ""
                    comment = self.client.get_task_comment(issue["id"], task["id"])
                    if comment:
                        body = comment.get("body", "")
                        match = re.search(
                            r"\*\*Conclusion\*\*:\s*\n?(.*)",
                            body,
                            re.DOTALL | re.IGNORECASE,
                        )
                        if match:
                            pulled_conclusion = match.group(1).strip()

                    if pulled_conclusion and not is_conclusion_placeholder(pulled_conclusion):
                        print(
                            f"  📝 Pulled valid conclusion from Linear comment for "
                            f"{task['id']}: {pulled_conclusion[:50]}..."
                        )
                        updates["conclusion"] = pulled_conclusion
                    else:
                        print(
                            f"  ⚠️ Blocked Done status transition for {task['id']} - "
                            "empty/placeholder conclusion and no valid comment on Linear."
                        )
                        updates.pop("status", None)

        if task["priority"] is not None and new_priority != task["priority"]:
            updates["priority"] = new_priority

        if task["labels"] and set(new_labels) != set(task["labels"]):
            updates["labels"] = new_labels

        if updates:
            print(
                f"  📝 Local metadata differs from Linear for {task['id']}. Updates: {updates}"
            )
            if self.dry_run:
                print(f"  [Dry-Run] Would update {task['id']} metadata in blueprint file.")
            else:
                parser = PlanParser()
                if "conclusion" in updates:
                    parser.update_task_conclusion_in_file(
                        self._current_plan_path, task["id"], updates["conclusion"]
                    )
                meta_updates = {k: v for k, v in updates.items() if k != "conclusion"}
                if meta_updates:
                    success = parser.update_task_metadata_in_file(
                        self._current_plan_path, task["id"], **meta_updates
                    )
                    if success:
                        print("  ✅ Local blueprint updated")
                    else:
                        print(f"  ⚠️ Failed to update local file for {task['id']}.")
                else:
                    print("  ✅ Local blueprint updated (conclusion only)")
        else:
            print(f"  ✔️ Metadata in sync for {task['id']}")

    @property
    def plan_path(self) -> Path | None:
        return self._current_plan_path

    @plan_path.setter
    def plan_path(self, value: Path | str | None) -> None:
        self._current_plan_path = Path(value) if value else None


__all__ = ["SyncEngine", "_float_eq"]
