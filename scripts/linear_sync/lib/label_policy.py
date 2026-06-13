"""Linear team label allowlist, aliases, and normalization (SSOT: linear_team_labels.json)."""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

_POLICY_PATH = Path(__file__).resolve().parent.parent / "data" / "linear_team_labels.json"


class LabelPolicyError(ValueError):
    """Raised when Blueprint labels cannot be resolved to the team allowlist."""

    def __init__(self, unknown: list[str], message: str | None = None) -> None:
        self.unknown = list(unknown)
        text = message or f"Unknown Linear team labels: {', '.join(self.unknown)}"
        super().__init__(text)


@lru_cache(maxsize=1)
def load_label_policy() -> dict[str, Any]:
    data = json.loads(_POLICY_PATH.read_text(encoding="utf-8"))
    labels: list[str] = list(data.get("labels") or [])
    aliases: dict[str, str] = dict(data.get("aliases") or {})
    lower_to_canonical = {name.lower(): name for name in labels}
    allowed = set(lower_to_canonical.keys())
    orphan_aliases = sorted(
        f"{key!r} -> {target!r}"
        for key, target in aliases.items()
        if str(target).strip().lower() not in allowed
    )
    if orphan_aliases:
        raise LabelPolicyError(
            [],
            message=(
                "linear_team_labels.json aliases must target API team labels only: "
                + ", ".join(orphan_aliases)
            ),
        )
    return {
        "version": data.get("version"),
        "synced_at": data.get("synced_at"),
        "team_key": data.get("team_key"),
        "labels": labels,
        "aliases": aliases,
        "lower_to_canonical": lower_to_canonical,
    }


def normalize_label_names(raw: list[str]) -> tuple[list[str], list[str]]:
    """Map raw Blueprint labels through aliases and allowlist.

    Returns (resolved_team_labels, unknown_raw_names). Order preserved; deduped by canonical name.
    """
    if not raw:
        return [], []

    policy = load_label_policy()
    lower_to_canonical: dict[str, str] = policy["lower_to_canonical"]
    aliases: dict[str, str] = policy["aliases"]

    resolved: list[str] = []
    unknown: list[str] = []
    seen_resolved: set[str] = set()

    for name in raw:
        if not name or not str(name).strip():
            continue
        original = str(name).strip()
        key = original.lower()
        mapped = aliases.get(key, original)
        canonical = lower_to_canonical.get(mapped.lower())
        if canonical:
            canon_key = canonical.lower()
            if canon_key not in seen_resolved:
                seen_resolved.add(canon_key)
                resolved.append(canonical)
        else:
            unknown.append(original)

    return resolved, unknown


def validate_labels_or_raise(raw: list[str]) -> list[str]:
    """Return resolved labels or raise ``LabelPolicyError`` when any name is unknown."""
    resolved, unknown = normalize_label_names(raw)
    if unknown:
        raise LabelPolicyError(unknown)
    return resolved


def canonicalize_for_linear(labels: list[str]) -> set[str]:
    """Lowercase canonical set for Linear vs Blueprint label comparison."""
    resolved, _ = normalize_label_names(labels)
    return {name.lower() for name in resolved}


def format_label_validation_issue(location: str, raw: str) -> str | None:
    """Return a lint error message when raw label tokens include unknown names."""
    from scripts.linear_sync.lib.plan_metadata import split_label_tokens

    if not raw or not str(raw).strip():
        return None
    _, unknown = normalize_label_names(split_label_tokens(raw))
    if not unknown:
        return None
    policy = load_label_policy()
    allowed = ", ".join(policy["labels"])
    sample_aliases = ", ".join(sorted(policy["aliases"].keys())[:6])
    return (
        f"{location} unknown label(s): {', '.join(unknown)}. "
        f"Allowed team labels: {allowed}. "
        f"Alias examples (see linear_team_labels.json): {sample_aliases}, …"
    )


def validate_blueprint_labels(content: str) -> list[str]:
    """Collect label allowlist violations from Blueprint doc meta and task Labels fields."""
    from scripts.linear_sync.lib.plan_metadata import iter_blueprint_label_sources

    issues: list[str] = []
    for location, raw in iter_blueprint_label_sources(content):
        message = format_label_validation_issue(location, raw)
        if message:
            issues.append(message)
    return issues


def map_resolved_labels_to_ids(
    resolved_names: list[str],
    team_label_nodes: list[dict],
) -> tuple[list[str], list[str]]:
    """Map canonical team label names to Linear label IDs.

    Returns ``(label_ids, missing_on_team)`` — no silent skip when a resolved
    name is absent from ``team_label_nodes``.
    """
    if not resolved_names:
        return [], []

    label_map = {str(node["name"]).lower(): str(node["id"]) for node in team_label_nodes}
    ids: list[str] = []
    missing: list[str] = []
    for name in resolved_names:
        lid = label_map.get(name.lower())
        if lid and lid not in ids:
            ids.append(lid)
        else:
            missing.append(name)
    return ids, missing


def resolve_label_names_for_team(
    label_names: list[str],
    team_label_nodes: list[dict],
) -> tuple[list[str], list[str]]:
    """Normalize via policy, then map to Linear label IDs."""
    resolved, unknown = normalize_label_names(label_names)
    if unknown:
        return [], unknown
    ids, missing = map_resolved_labels_to_ids(resolved, team_label_nodes)
    return ids, missing


def apply_label_policy_drop_unknown(raw: list[str], *, context: str = "Blueprint") -> list[str]:
    """Normalize labels; drop unknown with one stderr line (plan_metadata path)."""
    resolved, unknown = normalize_label_names(raw)
    if unknown:
        print(
            f"  ⚠️ {context} labels dropped (not on team allowlist): {', '.join(unknown)}",
            file=sys.stderr,
        )
    return resolved
