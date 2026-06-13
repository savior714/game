"""Stale route bundle heal — pure helpers and gate orchestration (PLAN_stale_route_bundle_heal)."""

from __future__ import annotations

import uuid
from collections.abc import MutableMapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.agent.route_context import (
    find_repo_root,
    get_route_bundle,
    normalize_repo_rel,
    sanitize_route_paths,
)


def compute_delta_missing_reads(
    required_paths: Sequence[str],
    session_reads: set[str],
) -> list[str]:
    """Paths in required_paths not yet recorded in the session read set."""
    return [p for p in required_paths if p not in session_reads]


def mark_superseded_overlapping_bundles(
    manifest: MutableMapping[str, Any],
    edit_files: Sequence[str],
    *,
    exclude_bundle_id: str | None = None,
) -> None:
    """Mark older bundles that overlap edit paths but use a different files_key."""
    _bundle_files_key, _utc_now_iso, files_fingerprint = _get_route_gate_functions()
    targets = {normalize_repo_rel(f) for f in edit_files if normalize_repo_rel(f)}
    if not targets:
        return
    new_key = files_fingerprint(edit_files)
    stamp = _utc_now_iso()
    bundles = manifest.get("bundles", [])
    if not isinstance(bundles, list):
        return
    for bundle in bundles:
        if not isinstance(bundle, MutableMapping):
            continue
        if exclude_bundle_id and bundle.get("bundle_id") == exclude_bundle_id:
            continue
        if bundle.get("superseded_at"):
            continue
        bfiles = {normalize_repo_rel(str(f)) for f in bundle.get("files", [])}
        if not (bfiles & targets):
            continue
        if _bundle_files_key(bundle) != new_key:
            bundle["superseded_at"] = stamp


def _parse_routed_at(value: object) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=None)
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return datetime.min.replace(tzinfo=None)
    if parsed.tzinfo is not None:
        return parsed.astimezone().replace(tzinfo=None)
    return parsed


def _slim_stored_bundle(bundle: MutableMapping[str, Any]) -> None:
    """Drop heavy must_read payloads from bundles no longer active for gating."""
    if bundle.get("complete") or bundle.get("superseded_at"):
        bundle.pop("must_read", None)


def prune_superseded_and_old_complete_bundles(
    manifest: MutableMapping[str, Any],
    *,
    max_active: int = 10,
    max_complete: int = 20,
    max_superseded: int = 30,
    max_all_reads: int = 200,
) -> MutableMapping[str, Any]:
    """Cap session manifest growth while preserving recent routing context."""
    bundles = manifest.get("bundles", [])
    if not isinstance(bundles, list) or not bundles:
        bundles = []

    active: list[MutableMapping[str, Any]] = []
    complete: list[MutableMapping[str, Any]] = []
    superseded: list[MutableMapping[str, Any]] = []
    stamp = _get_route_gate_functions()[1]()
    for raw in bundles:
        if not isinstance(raw, MutableMapping):
            continue
        if raw.get("superseded_at"):
            superseded.append(raw)
            continue
        if raw.get("complete"):
            complete.append(raw)
        else:
            active.append(raw)

    if len(active) > max_active:
        active.sort(
            key=lambda b: _parse_routed_at(b.get("routed_at")),
            reverse=True,
        )
        overflow = active[max_active:]
        active = active[:max_active]
        for bundle in overflow:
            bundle["superseded_at"] = stamp
            superseded.append(bundle)

    if len(complete) > max_complete:
        complete.sort(
            key=lambda b: _parse_routed_at(b.get("routed_at")),
            reverse=True,
        )
        overflow = complete[max_complete:]
        complete = complete[:max_complete]
        for bundle in overflow:
            bundle["superseded_at"] = stamp
            superseded.append(bundle)

    if len(superseded) > max_superseded:
        superseded.sort(
            key=lambda b: _parse_routed_at(
                b.get("superseded_at") or b.get("routed_at")
            ),
            reverse=True,
        )
        superseded = superseded[:max_superseded]

    merged = active + complete + superseded
    for bundle in merged:
        if isinstance(bundle, MutableMapping):
            _slim_stored_bundle(bundle)
    manifest["bundles"] = merged

    all_reads = manifest.get("all_reads", [])
    if isinstance(all_reads, list) and len(all_reads) > max_all_reads:
        sorted_reads = sorted(
            [r for r in all_reads if isinstance(r, MutableMapping)],
            key=lambda r: _parse_routed_at(r.get("at")),
            reverse=True,
        )
        manifest["all_reads"] = sorted_reads[:max_all_reads]

    return manifest


def _get_route_gate_functions():
    """Lazy import to avoid circular dependency."""
    from scripts.agent.route_gate import (
        _bundle_files_key,
        _utc_now_iso,
        files_fingerprint,
    )

    return _bundle_files_key, _utc_now_iso, files_fingerprint


def heal_stale_overlap_gate(
    edit_files: Sequence[str],
    *,
    repo_root: Path | None = None,
    full_route: bool = True,
    require_detail: bool | None = None,
    phase: str = "pre_edit",
) -> dict[str, Any]:
    """
    Live-route heal for stale overlap: supersede old bundles, append fresh bundle,
    return gate-shaped result with healed=True (no stale flag).
    """
    from scripts.agent.route_gate import (  # noqa: PLC0415
        _mutate_manifest,
        _needs_detail_paths,
        _required_paths_from_bundle,
        _utc_now_iso,
        files_fingerprint,
    )

    root = repo_root or find_repo_root()
    files = sanitize_route_paths(edit_files)
    if not files:
        return {
            "ok": False,
            "message": "No edit paths provided.",
            "missing": [],
            "bundle_id": None,
        }

    if require_detail is None:
        require_detail = _needs_detail_paths(files)

    live = get_route_bundle(
        files,
        repo_root=root,
        tight=not full_route,
    )
    required = _required_paths_from_bundle(
        {
            "must_read_paths": live.get("must_read_paths", []),
            "must_read": live.get("must_read"),
        },
        include_detail=require_detail,
    )

    bundle_id_holder: list[str] = []
    missing_holder: list[str] = []

    def _heal(manifest: dict[str, Any]) -> None:
        mark_superseded_overlapping_bundles(manifest, files)
        bundle_id = uuid.uuid4().hex[:12]
        routed_files = [normalize_repo_rel(str(f)) for f in live.get("files", files)]
        key = files_fingerprint(routed_files)
        entry: dict[str, Any] = {
            "bundle_id": bundle_id,
            "phase": phase,
            "routed_at": _utc_now_iso(),
            "files": routed_files,
            "files_key": key,
            "must_read_paths": list(live.get("must_read_paths", [])),
            "must_read": live.get("must_read"),
            "reads": [],
            "complete": False,
        }
        if live.get("query"):
            entry["query"] = live["query"]
        if live.get("classified_intents"):
            entry["classified_intents"] = live["classified_intents"]
        manifest.setdefault("bundles", []).append(entry)
        mark_superseded_overlapping_bundles(
            manifest,
            files,
            exclude_bundle_id=bundle_id,
        )
        missing_holder[:] = compute_delta_missing_reads(required, set())
        bundle_id_holder.append(bundle_id)

    _mutate_manifest(root, _heal)
    bundle_id = bundle_id_holder[0] if bundle_id_holder else None
    missing = list(missing_holder)

    if missing:
        return {
            "ok": False,
            "message": (
                f"Bundle {bundle_id}: healed route; read missing paths, "
                "then `just route-read <path>…`."
            ),
            "missing": missing,
            "bundle_id": bundle_id,
            "must_read_paths": required,
            "healed": True,
        }
    return {
        "ok": True,
        "message": f"Bundle {bundle_id}: healed route; all required paths recorded.",
        "missing": [],
        "bundle_id": bundle_id,
        "must_read_paths": required,
        "healed": True,
    }
