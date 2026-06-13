#!/usr/bin/env python3
"""Bundle helper functions for Context Route Gate session manifest."""
from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

from scripts.agent.route_context import normalize_repo_rel
from scripts.agent.route_gate_manifest import files_fingerprint


def _read_paths_set(manifest: Mapping[str, Any]) -> set[str]:
    out: set[str] = set()
    for raw in manifest.get("all_reads", []):
        if isinstance(raw, str):
            out.add(normalize_repo_rel(raw))
        elif isinstance(raw, Mapping) and raw.get("path"):
            out.add(normalize_repo_rel(str(raw["path"])))
    for bundle in manifest.get("bundles", []):
        if not isinstance(bundle, Mapping):
            continue
        for entry in bundle.get("reads", []):
            if isinstance(entry, str):
                out.add(normalize_repo_rel(entry))
            elif isinstance(entry, Mapping) and entry.get("path"):
                out.add(normalize_repo_rel(str(entry["path"])))
    return out


def _bundle_read_paths(bundle: Mapping[str, Any]) -> set[str]:
    out: set[str] = set()
    for entry in bundle.get("reads", []):
        if isinstance(entry, str):
            out.add(normalize_repo_rel(entry))
        elif isinstance(entry, Mapping) and entry.get("path"):
            out.add(normalize_repo_rel(str(entry["path"])))
    return out


def _bundle_files_key(bundle: Mapping[str, Any]) -> str:
    stored = bundle.get("files_key")
    if isinstance(stored, str) and stored:
        return stored
    return files_fingerprint(bundle.get("files", []))


def _needs_detail_paths(edit_files: Sequence[str]) -> bool:
    for raw in edit_files:
        rel = normalize_repo_rel(str(raw)).lower()
        if rel.endswith((".tsx", ".jsx")) and "apps/renderer" in rel:
            return True
    return False


def _required_paths_from_bundle(
    bundle: Mapping[str, Any],
    *,
    include_detail: bool = False,
) -> list[str]:
    required: list[str] = []
    seen: set[str] = set()

    def add(rel: str) -> None:
        norm = normalize_repo_rel(rel)
        if norm and norm not in seen:
            seen.add(norm)
            required.append(norm)

    must_read = bundle.get("must_read")
    if include_detail and isinstance(must_read, list):
        for entry in must_read:
            if not isinstance(entry, Mapping):
                continue
            if not entry.get("installed", True):
                continue
            path = entry.get("path")
            if path:
                add(str(path))
            if entry.get("lazy_load") and entry.get("detail_path"):
                add(str(entry["detail_path"]))
        if required:
            return required

    for raw in bundle.get("must_read_paths", []):
        add(str(raw))
    return required


def _mark_bundle_complete(bundle: MutableMapping[str, Any], *, include_detail: bool = False) -> None:
    required = set(_required_paths_from_bundle(bundle, include_detail=include_detail))
    reads = _bundle_read_paths(bundle)
    bundle["complete"] = required.issubset(reads) if required else True
