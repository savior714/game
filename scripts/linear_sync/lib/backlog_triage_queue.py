"""JSON queue and history for Linear backlog triage."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_QUEUE_PATH = _REPO_ROOT / "artifacts" / "linear_backlog_triage" / "queue.json"


class ReviewChoice(StrEnum):
    PROCESS = "process"
    DELETE = "delete"
    DEFER_7D = "defer_7d"
    SKIP = "skip"


def _empty_schema() -> dict[str, Any]:
    return {"version": 1, "candidates": [], "history": []}


def _parse_iso(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


@dataclass
class BacklogTriageQueue:
    path: Path
    now_fn: Callable[[], datetime] | None = None

    def __post_init__(self) -> None:
        self._now_fn = self.now_fn or (lambda: datetime.now(UTC))
        self._data = self._load()

    def _now(self) -> datetime:
        return self._now_fn()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return _empty_schema()
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return _empty_schema()
        if not isinstance(data, dict):
            return _empty_schema()
        data.setdefault("version", 1)
        data.setdefault("candidates", [])
        data.setdefault("history", [])
        return data

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(self.path)

    def prune_history(self, days: int = 30) -> None:
        cutoff = self._now() - timedelta(days=days)
        kept: list[dict[str, Any]] = []
        for row in self._data.get("history", []):
            at_raw = row.get("at")
            if not at_raw:
                continue
            try:
                if _parse_iso(str(at_raw)) >= cutoff:
                    kept.append(row)
            except ValueError:
                continue
        self._data["history"] = kept
        self._save()

    def enqueue(self, candidate: dict[str, Any]) -> None:
        issue_id = str(candidate.get("issue_id") or "")
        existing = [
            c
            for c in self._data["candidates"]
            if str(c.get("issue_id")) == issue_id and c.get("status") in {"pending", "skipped"}
        ]
        if existing:
            return
        self._data["candidates"].append(candidate)
        self.prune_history()

    def next_pending(self) -> dict[str, Any] | None:
        now = self._now()
        pending: list[dict[str, Any]] = []
        for cand in self._data.get("candidates", []):
            if cand.get("status") != "pending":
                continue
            defer_raw = cand.get("defer_until")
            if defer_raw:
                try:
                    if _parse_iso(str(defer_raw)) > now:
                        continue
                except ValueError:
                    pass
            pending.append(cand)
        if not pending:
            return None
        pending.sort(key=lambda c: (str(c.get("scanned_at") or ""), str(c.get("created_at") or "")))
        return pending[0]

    def apply_review(
        self,
        choice: ReviewChoice,
        *,
        action_taken: str | None = None,
    ) -> dict[str, Any] | None:
        cand = self.next_pending()
        if not cand:
            return None
        now_iso = self._now().isoformat().replace("+00:00", "Z")
        cand["reviewed_at"] = now_iso
        cand["review_choice"] = choice.value

        if choice == ReviewChoice.PROCESS:
            cand["status"] = "processed"
            self._data["history"].append(
                {
                    "issue_id": cand.get("issue_id"),
                    "pattern": cand.get("pattern"),
                    "review_choice": choice.value,
                    "action_taken": action_taken,
                    "at": now_iso,
                }
            )
        elif choice == ReviewChoice.DELETE:
            cand["status"] = "completed"
            self._data["history"].append(
                {
                    "issue_id": cand.get("issue_id"),
                    "pattern": cand.get("pattern"),
                    "review_choice": choice.value,
                    "action_taken": action_taken,
                    "at": now_iso,
                }
            )
        elif choice == ReviewChoice.DEFER_7D:
            cand["status"] = "deferred"
            cand["defer_until"] = (self._now() + timedelta(days=7)).isoformat().replace("+00:00", "Z")
        elif choice == ReviewChoice.SKIP:
            cand["status"] = "skipped"

        self.prune_history()
        return cand

    def list_summary(self) -> dict[str, Any]:
        now = self._now()
        pending: list[dict[str, Any]] = []
        deferred: list[dict[str, Any]] = []
        for cand in self._data.get("candidates", []):
            status = cand.get("status")
            if status == "pending":
                defer_raw = cand.get("defer_until")
                if defer_raw:
                    try:
                        if _parse_iso(str(defer_raw)) > now:
                            deferred.append(cand)
                            continue
                    except ValueError:
                        pass
                pending.append(cand)
            elif status == "deferred":
                deferred.append(cand)
        return {
            "pending": pending,
            "deferred": deferred,
            "history": list(self._data.get("history", [])),
        }

    def has_pending_issue(self, issue_id: str) -> bool:
        ident = issue_id.upper()
        for cand in self._data.get("candidates", []):
            if str(cand.get("issue_id", "")).upper() == ident and cand.get("status") == "pending":
                return True
        return False

    def is_deferred_active(self, issue_id: str) -> bool:
        ident = issue_id.upper()
        now = self._now()
        for cand in self._data.get("candidates", []):
            if str(cand.get("issue_id", "")).upper() != ident:
                continue
            defer_raw = cand.get("defer_until")
            if not defer_raw:
                continue
            try:
                if _parse_iso(str(defer_raw)) > now:
                    return True
            except ValueError:
                continue
        return False

    def has_skipped_issue(self, issue_id: str) -> bool:
        ident = issue_id.upper()
        for cand in self._data.get("candidates", []):
            if str(cand.get("issue_id", "")).upper() == ident and cand.get("status") == "skipped":
                return True
        return False
