#!/usr/bin/env python3
"""Linear GraphQL API client."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from scripts.linear_sync.linear_retry import query_with_retry

API_URL = "https://api.linear.app/graphql"


class LinearClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
        self.state_cache = {}
        self._team_states_cache: dict[str, list[dict]] = {}
        self._comments_cache: dict[str, list[dict]] = {}
        self._last_mutation_time: dict[str, float] = {}

    def _query_with_stale_protection(
        self, query: str, variables: Optional[dict] = None
    ) -> dict:
        """Avoid stale reads immediately after mutations."""
        result = self._query(query, variables)

        if "mutation" in query.lower():
            issue_id = None
            if variables:
                issue_id = variables.get("id") or variables.get("input", {}).get("id")
            if issue_id:
                self._last_mutation_time[issue_id] = time.time()

        return result

    def _query_with_retry(
        self,
        query: str,
        variables: Optional[dict] = None,
        max_retries: int = 5,
        base_delay: float = 1.0,
    ) -> dict:
        return query_with_retry(
            self._query,
            query,
            variables,
            max_retries=max_retries,
            base_delay=base_delay,
        )

    def _query(self, query: str, variables: Optional[dict] = None) -> dict:
        payload = {"query": query, "variables": variables or {}}
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=self.headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise Exception(f"Linear HTTP {exc.code}: {body}") from exc
        if "errors" in result:
            raise Exception(f"Linear API Error: {result['errors'][0].get('message')}")
        return result.get("data", {})

    def get_issue_by_identifier(self, identifier: str) -> Optional[dict]:
        q = """
        query GetIssueByIdentifier($id: String!) {
          issue(id: $id) {
            id
            identifier
            title
            url
            createdAt
            description
            state { id name type }
          }
        }
        """
        try:
            return self._query_with_retry(q, {"id": identifier}).get("issue")
        except Exception as exc:
            err = str(exc).lower()
            if "429" in err or "ratelimit" in err:
                raise
            if "not found" in err or "invalid input" in err:
                return None
            raise

    def issue_exists(self, identifier: str) -> bool:
        return self.get_issue_by_identifier(identifier) is not None

    def search_issues(self, term: str, first: int = 20) -> list[dict]:
        if not term or not term.strip():
            return []
        q = """
        query SearchIssues($term: String!, $first: Int!) {
          searchIssues(term: $term, first: $first) {
            nodes {
              id
              identifier
              title
              url
              createdAt
              description
              state { id name type }
            }
          }
        }
        """
        data = self._query_with_retry(q, {"term": term.strip(), "first": first})
        return (data.get("searchIssues") or {}).get("nodes") or []

    def get_issue(self, issue_id: str) -> Optional[dict]:
        q = """
        query GetIssue($id: String!) {
          issue(id: $id) {
            id
            title
            priority
            state { id name type }
            labels { nodes { id name } }
          }
        }
        """
        last_mut = self._last_mutation_time.get(issue_id)
        if last_mut:
            elapsed = time.time() - last_mut
            if elapsed < 0.5:
                print(
                    f"  ⏳ Stale protection: {elapsed * 1000:.0f}ms since mutation, waiting 500ms...",
                    file=sys.stderr,
                )
                time.sleep(0.5)

        try:
            return self._query_with_stale_protection(q, {"id": issue_id}).get("issue")
        except Exception as exc:
            err = str(exc).lower()
            if "429" in err or "ratelimit" in err:
                raise
            if "not found" in err:
                return None
            raise

    def get_team_states(self, issue_id: str) -> list[dict]:
        if issue_id in self._team_states_cache:
            return self._team_states_cache[issue_id]
        q1 = (
            "query GetTeam($id: String!) { issue(id: $id) "
            "{ team { id states { nodes { id name type } } } } }"
        )
        res = self._query_with_retry(q1, {"id": issue_id})
        states = res.get("issue", {}).get("team", {}).get("states", {}).get("nodes", [])
        self._team_states_cache[issue_id] = states
        return states

    def update_issue(self, issue_uuid: str, **kwargs) -> bool:
        input_fields = ", ".join([f"{k}: ${k}" for k in kwargs.keys()])
        variables_def = ", ".join(
            [f"${k}: {self._get_gql_type(k)}" for k in kwargs.keys()]
        )

        mutation = f"""
        mutation UpdateIssue($id: String!, {variables_def}) {{
          issueUpdate(id: $id, input: {{ {input_fields} }}) {{
            success
          }}
        }}
        """
        variables = {"id": issue_uuid}
        variables.update(kwargs)
        res = self._query_with_retry(mutation, variables)
        return res.get("issueUpdate", {}).get("success", False)

    def _get_gql_type(self, key: str) -> str:
        if key == "stateId":
            return "String"
        if key == "priority":
            return "Int"
        if key == "labelIds":
            return "[String!]"
        return "String"

    def list_teams(self) -> list[dict]:
        q = """
        query Teams {
          teams { nodes { id name key } }
        }
        """
        return self._query_with_retry(q, {}).get("teams", {}).get("nodes", [])

    def get_team_id_for_issue(self, issue_id: str) -> Optional[str]:
        q = """
        query GetIssueTeam($id: String!) {
          issue(id: $id) { team { id } }
        }
        """
        res = self._query_with_retry(q, {"id": issue_id})
        team = (res.get("issue") or {}).get("team") or {}
        team_id = team.get("id")
        return str(team_id) if team_id else None

    def get_team_labels(self, issue_id: str) -> list[dict]:
        q = """
        query GetTeamLabels($id: String!) {
          issue(id: $id) {
            team {
              labels {
                nodes { id name }
              }
            }
          }
        }
        """
        res = self._query_with_retry(q, {"id": issue_id})
        return res.get("issue", {}).get("team", {}).get("labels", {}).get("nodes", [])

    def get_team_labels_for_team(self, team_id: str) -> list[dict]:
        q = """
        query TeamLabels($id: String!) {
          team(id: $id) {
            labels { nodes { id name } }
          }
        }
        """
        res = self._query_with_retry(q, {"id": team_id})
        return res.get("team", {}).get("labels", {}).get("nodes", [])

    def create_issue(
        self,
        *,
        team_id: str,
        title: str,
        description: str,
        priority: Optional[float] = None,
        label_ids: Optional[list[str]] = None,
        parent_id: Optional[str] = None,
    ) -> Optional[dict]:
        issue_input: dict[str, Any] = {
            "teamId": team_id,
            "title": title,
            "description": description,
        }
        if priority is not None:
            issue_input["priority"] = float(priority)
        if label_ids:
            issue_input["labelIds"] = label_ids
        if parent_id:
            issue_input["parentId"] = parent_id

        mutation = """
        mutation IssueCreate($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue { id identifier title url }
          }
        }
        """
        row = self._query_with_retry(mutation, {"input": issue_input}).get("issueCreate") or {}
        if not row.get("success"):
            raise RuntimeError(f"issueCreate failed: {row}")
        return row.get("issue")

    def update_issue_state(self, issue_uuid: str, state_uuid: str) -> bool:
        return self.update_issue(issue_uuid, stateId=state_uuid)

    def add_comment(self, issue_uuid: str, body: str) -> bool:
        mutation = """
        mutation CreateComment($issueId: String!, $body: String!) {
          commentCreate(input: { issueId: $issueId, body: $body }) {
            success
          }
        }
        """
        res = self._query_with_retry(mutation, {"issueId": issue_uuid, "body": body})
        return res.get("commentCreate", {}).get("success", False)

    def get_issue_comments(self, issue_id: str, first: int = 50) -> list[dict]:
        q = """
        query GetIssueComments($issueId: String!, $first: Int!) {
          issue(id: $issueId) {
            id
            comments(first: $first) {
              nodes {
                id
                body
                createdAt
              }
            }
          }
        }
        """
        res = self._query_with_retry(q, {"issueId": issue_id, "first": first})
        return res.get("issue", {}).get("comments", {}).get("nodes", [])

    def get_task_comment(self, issue_id: str, task_id: str) -> Optional[dict]:
        if issue_id not in self._comments_cache:
            self._comments_cache[issue_id] = self.get_issue_comments(issue_id)
        comments = self._comments_cache[issue_id]
        marker = f"Task Done: {task_id}"
        return next((c for c in comments if marker in c.get("body", "")), None)

    def archive_issue(self, issue_uuid: str, *, trash: bool = False) -> bool:
        mutation = """
        mutation IssueArchive($id: String!, $trash: Boolean) {
          issueArchive(id: $id, trash: $trash) {
            success
          }
        }
        """
        res = self._query_with_retry(mutation, {"id": issue_uuid, "trash": trash})
        return res.get("issueArchive", {}).get("success", False)

    def delete_issue(self, issue_uuid: str) -> bool:
        mutation = """
        mutation IssueDelete($id: String!) {
          issueDelete(id: $id) {
            success
          }
        }
        """
        res = self._query_with_retry(mutation, {"id": issue_uuid})
        return res.get("issueDelete", {}).get("success", False)

    def iter_issues(
        self,
        *,
        issue_filter: dict[str, Any],
        first: int = 50,
        order_by: str = "updatedAt",
    ):
        """Yield non-archived issues matching ``issue_filter`` (paginated)."""
        q = """
        query ListIssues($filter: IssueFilter, $first: Int!, $after: String, $orderBy: PaginationOrderBy) {
          issues(filter: $filter, first: $first, after: $after, orderBy: $orderBy) {
            nodes {
              id
              identifier
              title
              description
              createdAt
              updatedAt
              completedAt
              archivedAt
              state { name type }
              team { key name }
            }
            pageInfo { hasNextPage endCursor }
          }
        }
        """
        after: str | None = None
        while True:
            variables: dict[str, Any] = {
                "filter": issue_filter,
                "first": first,
                "orderBy": order_by,
            }
            if after:
                variables["after"] = after
            data = self._query_with_retry(q, variables)
            block = data.get("issues") or {}
            nodes = block.get("nodes") or []
            for node in nodes:
                yield node
            page = block.get("pageInfo") or {}
            if not page.get("hasNextPage"):
                break
            after = page.get("endCursor")
            if not after:
                break

    def list_active_issues(self, first: int = 100) -> list[dict[str, Any]]:
        q = """
        query IssuesForCoverage($first: Int!) {
          issues(first: $first) {
            nodes {
              identifier
              title
              priority
              state { type }
            }
          }
        }
        """
        data = self._query_with_retry(q, {"first": first})
        nodes = data.get("issues", {}).get("nodes", [])
        terminal = {"completed", "canceled"}
        out: list[dict[str, Any]] = []
        for node in nodes:
            state_type = (node.get("state") or {}).get("type") or ""
            if str(state_type).lower() in terminal:
                continue
            out.append(
                {
                    "identifier": node.get("identifier") or "",
                    "title": node.get("title") or "",
                    "priority": node.get("priority")
                    if node.get("priority") is not None
                    else 0,
                    "state_type": state_type,
                }
            )
        return out
