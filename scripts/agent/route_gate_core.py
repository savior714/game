#!/usr/bin/env python3
"""Core gate logic for Context Route Gate session manifest."""
from __future__ import annotations

import uuid
from collections.abc import Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import Any

from scripts.agent.route_context import (
    find_repo_root,
    get_route_bundle,
    normalize_repo_rel,
    sanitize_route_paths,
)
from scripts.agent.route_gate_bundle import (
    _bundle_files_key,
    _bundle_read_paths,
    _mark_bundle_complete,
    _needs_detail_paths,
    _read_paths_set,
    _required_paths_from_bundle,
)
from scripts.agent.route_gate_manifest import (
    _mutate_manifest,
    _utc_now_iso,
    agent_id,
    files_fingerprint,
    load_manifest,
)

VALID_PHASES = frozenset({"turn1", "pre_edit"})


def append_bundle_from_route(
    bundle: Mapping[str, Any],
    *,
    phase: str = "pre_edit",
    repo_root: Path | None = None,
) -> str:
    if phase not in VALID_PHASES:
        allowed = ", ".join(sorted(VALID_PHASES))
        msg = f"phase must be one of: {allowed}"
        raise ValueError(msg)
    root = repo_root or find_repo_root()
    bundle_id = uuid.uuid4().hex[:12]
    routed_files = [normalize_repo_rel(str(f)) for f in bundle.get("files", [])]
    key = files_fingerprint(routed_files)

    def _append(manifest: dict[str, Any]) -> str:
        entry: dict[str, Any] = {
            "bundle_id": bundle_id,
            "phase": phase,
            "routed_at": _utc_now_iso(),
            "files": routed_files,
            "files_key": key,
            "must_read_paths": list(bundle.get("must_read_paths", [])),
            "must_read": bundle.get("must_read"),
            "reads": [],
            "complete": False,
        }
        if bundle.get("query"):
            entry["query"] = bundle["query"]
        if bundle.get("classified_intents"):
            entry["classified_intents"] = bundle["classified_intents"]
        manifest.setdefault("bundles", []).append(entry)
        from scripts.agent.route_gate_heal import (  # noqa: PLC0415
            mark_superseded_overlapping_bundles,
            prune_superseded_and_old_complete_bundles,
        )

        mark_superseded_overlapping_bundles(
            manifest,
            routed_files,
            exclude_bundle_id=bundle_id,
        )
        prune_superseded_and_old_complete_bundles(manifest)
        return bundle_id

    return _mutate_manifest(root, _append)


def record_reads(
    paths: Sequence[str],
    *,
    via: str = "mcp",
    bundle_id: str | None = None,
    repo_root: Path | None = None,
    include_detail: bool | None = None,
) -> list[str]:
    root = repo_root or find_repo_root()
    normalized = [normalize_repo_rel(p) for p in paths if normalize_repo_rel(p)]
    if not normalized:
        return []

    if include_detail is None:
        include_detail = _needs_detail_paths(normalized)

    def _record(manifest: dict[str, Any]) -> list[str]:
        all_reads: list[Any] = list(manifest.get("all_reads", []))
        known = _read_paths_set(manifest)
        stamp = _utc_now_iso()
        recorded: list[str] = []
        for rel in normalized:
            if rel in known:
                continue
            all_reads.append({"path": rel, "at": stamp, "via": via, "agent": agent_id()})
            known.add(rel)
            recorded.append(rel)

        manifest["all_reads"] = all_reads
        bundles: list[MutableMapping[str, Any]] = [
            dict(b) if isinstance(b, Mapping) else {} for b in manifest.get("bundles", [])
        ]

        target: MutableMapping[str, Any] | None = None
        if bundle_id:
            for b in bundles:
                if b.get("bundle_id") == bundle_id:
                    target = b
                    break
        else:
            for b in reversed(bundles):
                if not b.get("complete", False):
                    target = b
                    break

        if target is not None:
            reads: list[Any] = list(target.get("reads", []))
            read_set = _bundle_read_paths(target)
            for rel in normalized:
                if rel in read_set:
                    continue
                reads.append({"path": rel, "at": stamp, "via": via, "agent": agent_id()})
                read_set.add(rel)
            target["reads"] = reads
            detail = include_detail or _needs_detail_paths(target.get("files", []))
            _mark_bundle_complete(target, include_detail=detail)

        manifest["bundles"] = bundles
        from scripts.agent.route_gate_heal import (  # noqa: PLC0415
            prune_superseded_and_old_complete_bundles,
        )

        prune_superseded_and_old_complete_bundles(manifest)
        return recorded

    return _mutate_manifest(root, _record)


def _find_bundle_for_files(
    manifest: Mapping[str, Any],
    edit_files: Sequence[str],
) -> dict[str, Any] | None:
    key = files_fingerprint(edit_files)
    matches: list[Mapping[str, Any]] = []
    for bundle in manifest.get("bundles", []):
        if not isinstance(bundle, Mapping):
            continue
        if _bundle_files_key(bundle) == key:
            matches.append(bundle)
    if not matches:
        return None
    return dict(sorted(matches, key=lambda b: str(b.get("routed_at", "")))[-1])


def _find_stale_overlap_bundle(
    manifest: Mapping[str, Any],
    edit_files: Sequence[str],
) -> Mapping[str, Any] | None:
    """Bundle overlaps edit paths but files_key differs (outdated pre_edit)."""
    targets = {normalize_repo_rel(f) for f in edit_files if normalize_repo_rel(f)}
    if not targets:
        return None
    key = files_fingerprint(edit_files)
    for bundle in reversed(list(manifest.get("bundles", []))):
        if not isinstance(bundle, Mapping):
            continue
        bfiles = {normalize_repo_rel(str(f)) for f in bundle.get("files", [])}
        if not (bfiles & targets):
            continue
        if _bundle_files_key(bundle) != key:
            return bundle
    return None


def gate_check(
    edit_files: Sequence[str],
    *,
    repo_root: Path | None = None,
    full_route: bool = True,
    require_detail: bool | None = None,
    patch_file: str | None = None,
    patch_old_string: str | None = None,
    patch_new_string: str | None = None,
) -> dict[str, Any]:
    """
    Returns {"ok": bool, "message": str, "missing": [...], "bundle_id": str|None, ...}
    """
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

    manifest = load_manifest(root)
    bundle = _find_bundle_for_files(manifest, files)

    # Prefer an exact files_key match. Stale overlap only blocks when no current bundle exists.
    if bundle is None:
        stale = _find_stale_overlap_bundle(manifest, files)
        if stale is not None:
            from scripts.agent.route_gate_heal import (  # noqa: PLC0415
                heal_stale_overlap_gate,
            )

            return heal_stale_overlap_gate(
                files,
                repo_root=root,
                full_route=full_route,
                require_detail=require_detail,
            )

    if bundle is None:
        live = get_route_bundle(
            files,
            repo_root=root,
            tight=not full_route,
        )
        required = _required_paths_from_bundle(
            {"must_read_paths": live.get("must_read_paths", []), "must_read": live.get("must_read")},
            include_detail=require_detail,
        )
        return {
            "ok": False,
            "message": (
                "No route bundle for these paths. Run "
                "`just route <paths> --json --write-manifest`, "
                "Read must_read, then `just route-read <path>…`."
            ),
            "missing": list(required),
            "bundle_id": None,
            "must_read_paths": required,
        }

    required = _required_paths_from_bundle(bundle, include_detail=require_detail)
    reads = _bundle_read_paths(bundle)
    missing = [p for p in required if p not in reads]
    if missing:
        return {
            "ok": False,
            "message": (
                f"Bundle {bundle.get('bundle_id')}: must_read incomplete. "
                "Read missing paths, then `just route-read <path>…`."
            ),
            "missing": missing,
            "bundle_id": bundle.get("bundle_id"),
            "must_read_paths": required,
        }

    from scripts.error_patterns.agent_gates import (  # noqa: PLC0415
        needs_agent_pattern_gates,
        run_agent_pattern_gates,
    )

    if needs_agent_pattern_gates(files):
        gates_ok, gates_msg = run_agent_pattern_gates(root)
        if not gates_ok:
            return {
                "ok": False,
                "message": gates_msg,
                "missing": [],
                "bundle_id": bundle.get("bundle_id"),
                "must_read_paths": required,
            }

    if patch_file and patch_old_string:
        from scripts.error_patterns.check_old_string import (  # noqa: PLC0415
            check_old_string_in_file,
            check_patch_strings_differ,
        )

        if patch_new_string is not None:
            diff_ok, diff_msg = check_patch_strings_differ(
                patch_old_string,
                patch_new_string,
            )
            if not diff_ok:
                return {
                    "ok": False,
                    "message": diff_msg,
                    "missing": [],
                    "bundle_id": bundle.get("bundle_id"),
                    "must_read_paths": required,
                }

        old_ok, old_msg = check_old_string_in_file(
            root,
            patch_file,
            patch_old_string,
        )
        if not old_ok:
            return {
                "ok": False,
                "message": old_msg,
                "missing": [],
                "bundle_id": bundle.get("bundle_id"),
                "must_read_paths": required,
            }

    return {
        "ok": True,
        "message": f"Bundle {bundle.get('bundle_id')} complete.",
        "missing": [],
        "bundle_id": bundle.get("bundle_id"),
        "must_read_paths": required,
    }


def gate_check_touched(
    *,
    repo_root: Path | None = None,
    skip_if_no_manifest: bool = True,
) -> dict[str, Any]:
    from scripts.agent.route_gate_touched import collect_touched_route_paths  # noqa: PLC0415

    root = repo_root or find_repo_root()
    paths = collect_touched_route_paths(root)
    if not paths:
        return {"ok": True, "message": "No touched source paths for route gate.", "skipped": True}

    manifest = load_manifest(root)
    if skip_if_no_manifest and not manifest.get("bundles") and not manifest.get("all_reads"):
        return {
            "ok": True,
            "message": "No session manifest; route gate skipped.",
            "skipped": True,
        }

    result = gate_check(paths, repo_root=root)
    result["touched_paths"] = paths
    return result
