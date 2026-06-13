#!/usr/bin/env python3
"""
Session manifest for Context Route Gate — multi-agent, IDE-agnostic.

Agents run `just route <paths> --json --write-manifest`, Read must_read paths, then
`just route-read <paths>`. Before edit: `just route-gate-check <paths>` (exit 1 = block).

Manifest default: `.agents/route/session-manifest.json` (gitignored).
Override: ROUTE_MANIFEST_PATH, ROUTE_SESSION_KEY, ROUTE_AGENT_ID.

This module re-exports all public API from split submodules for backward compatibility.
"""
from __future__ import annotations

# -- Bundle helpers ----------------------------------------------------------
from scripts.agent.route_gate_bundle import (  # noqa: F401
    _bundle_files_key,
    _bundle_read_paths,
    _mark_bundle_complete,
    _needs_detail_paths,
    _read_paths_set,
    _required_paths_from_bundle,
)

# -- CLI commands ------------------------------------------------------------
from scripts.agent.route_gate_cli import (  # noqa: F401
    cmd_check,
    cmd_check_touched,
    cmd_record_read,
    cmd_status,
    cmd_write_bundle,
    main,
)

# -- Core gate logic ---------------------------------------------------------
from scripts.agent.route_gate_core import (  # noqa: F401
    VALID_PHASES,
    append_bundle_from_route,
    gate_check,
    gate_check_touched,
    record_reads,
)

# Re-export everything from split modules for backward compatibility.
# Importers that use `from scripts.agent.route_gate import ...` continue to work.
# -- Manifest I/O -----------------------------------------------------------
from scripts.agent.route_gate_manifest import (  # noqa: F401
    _HAS_FCNTL,
    SCHEMA_VERSION,
    _mutate_manifest,
    _normalize_manifest,
    _utc_now_iso,
    agent_id,
    empty_manifest,
    files_fingerprint,
    load_manifest,
    manifest_abs_path,
    manifest_rel_path,
    save_manifest,
    session_key,
)
