#!/usr/bin/env python3
"""Manifest I/O for Context Route Gate session manifest."""
from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.agent.route_context import find_repo_root, normalize_repo_rel

try:
    import fcntl

    _HAS_FCNTL = True
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore[assignment]
    _HAS_FCNTL = False

SCHEMA_VERSION = "1"
DEFAULT_MANIFEST_REL = ".agents/route/session-manifest.json"


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def manifest_rel_path() -> str:
    return os.environ.get("ROUTE_MANIFEST_PATH", DEFAULT_MANIFEST_REL).strip()


def manifest_abs_path(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    rel = manifest_rel_path()
    p = Path(rel)
    return p if p.is_absolute() else root / rel


def session_key() -> str:
    explicit = os.environ.get("ROUTE_SESSION_KEY", "").strip()
    if explicit:
        return explicit
    return f"{os.getpid()}-{_utc_now_iso()[:10]}"


def agent_id() -> str:
    return (
        os.environ.get("ROUTE_AGENT_ID", "").strip()
        or os.environ.get("AGENT_NAME", "").strip()
        or "unknown"
    )


def files_fingerprint(paths: Sequence[str]) -> str:
    normalized = sorted({normalize_repo_rel(p) for p in paths if normalize_repo_rel(p)})
    return "|".join(normalized)


def empty_manifest(*, repo_root: Path) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "session_key": session_key(),
        "agent": agent_id(),
        "repo_root": str(repo_root),
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
        "all_reads": [],
        "bundles": [],
    }


def _normalize_manifest(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("schema_version") != SCHEMA_VERSION:
        data["schema_version"] = SCHEMA_VERSION
    data.setdefault("all_reads", [])
    data.setdefault("bundles", [])
    return data


def load_manifest(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or find_repo_root()
    path = manifest_abs_path(root)
    if not path.is_file():
        return empty_manifest(repo_root=root)
    data = json.loads(path.read_text(encoding="utf-8"))
    return _normalize_manifest(data)


def _mutate_manifest(
    repo_root: Path,
    mutate: Callable[[dict[str, Any]], Any],
) -> Any:
    path = manifest_abs_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            json.dumps(empty_manifest(repo_root=repo_root), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    with path.open("r+", encoding="utf-8") as fp:
        if _HAS_FCNTL and fcntl is not None:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
        try:
            fp.seek(0)
            raw = fp.read()
            data = (
                _normalize_manifest(json.loads(raw))
                if raw.strip()
                else empty_manifest(repo_root=repo_root)
            )
            result = mutate(data)
            fp.seek(0)
            fp.truncate()
            payload = dict(data)
            payload["updated_at"] = _utc_now_iso()
            json.dump(payload, fp, ensure_ascii=False, indent=2)
            fp.write("\n")
            fp.flush()
            return result
        finally:
            if _HAS_FCNTL and fcntl is not None:
                fcntl.flock(fp.fileno(), fcntl.LOCK_UN)


def save_manifest(data: Mapping[str, Any], repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()

    def _write(manifest: dict[str, Any]) -> None:
        manifest.clear()
        manifest.update(_normalize_manifest(dict(data)))

    _mutate_manifest(root, _write)
    return manifest_abs_path(root)
