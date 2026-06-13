#!/usr/bin/env python3
"""Linear-Blueprint Synchronization Engine (LIS-007).

Backward-compatibility re-export shim.

All public symbols are re-exported from their canonical modules:
  - CLI entry point: ``scripts.linear_sync.cli``
  - Sync operations: ``scripts.linear_sync.sync_operations``
  - Environment/API key: ``scripts.linear_sync.env``
  - Linear client:     ``scripts.linear_sync.linear_client``

This file is kept small (under 50 lines) and delegates to focused modules.
"""

from __future__ import annotations

# Backward-compatibility re-exports (symbols moved to canonical modules)
from scripts.linear_sync.cli import main
from scripts.linear_sync.env import load_env
from scripts.linear_sync.env import validate_api_key as _validate_api_key
from scripts.linear_sync.linear_client import API_URL, LinearClient
from scripts.linear_sync.sync_operations import SyncEngine, _float_eq

__all__ = [
    "API_URL",
    "LinearClient",
    "SyncEngine",
    "_float_eq",
    "_validate_api_key",
    "load_env",
    "main",
]

if __name__ == "__main__":
    main()
