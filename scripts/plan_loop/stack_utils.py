#!/usr/bin/env python3
"""Stack inference and bundle helper utilities for plan preread manifest generation."""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


def infer_stack_labels(paths: Sequence[str], text: str) -> list[str]:
    labels: list[str] = []
    exts = {Path(p).suffix.lower() for p in paths}
    lower = text.lower()

    if exts & {".tsx", ".jsx"} or "apps/renderer" in lower or "frontend" in lower:
        labels.append("React/Next (renderer)")
    if exts & {".ts", ".tsx"}:
        labels.append("TypeScript")
    if exts & {".py"} or "src/api" in lower or "backend" in lower:
        labels.append("Python (API/domain)")
    if "tests/e2e" in lower or ".spec.ts" in lower or "playwright" in lower:
        labels.append("Playwright E2E")
    if "dockerfile" in lower or "docker-compose" in lower:
        labels.append("Docker/infra")
    if "fhir" in lower:
        labels.append("FHIR/medical")
    return labels or ["(경로에서 스택 신호 미확인 — Impact Scope·Target 보강 권장)"]


def _actionable_missing(must_read: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    """Missing entries that require user-visible follow-up in plans."""
    return [e for e in must_read if not e.get("installed")]
