"""Estimate and cap route bundle context size (token budget gate)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

BYTES_PER_TOKEN = 4


def estimate_bytes(path: Path) -> int:
    if not path.is_file():
        return 0
    return path.stat().st_size


def estimate_tokens(path: Path) -> int:
    return estimate_bytes(path) // BYTES_PER_TOKEN


def estimate_must_read_tokens(
    must_read: Sequence[Mapping[str, Any]],
    *,
    repo_root: Path,
    include_lazy_detail: bool = True,
) -> dict[str, Any]:
    """Sum estimated tokens for must_read entries (installed paths only)."""
    per_path: list[dict[str, Any]] = []
    total = 0
    for entry in must_read:
        rel = str(entry.get("path", "")).strip()
        if not rel or not entry.get("installed", True):
            continue
        full = repo_root / rel
        tokens = estimate_tokens(full)
        per_path.append({"path": rel, "tokens": tokens, "kind": entry.get("kind")})
        total += tokens
        if include_lazy_detail and entry.get("lazy_load"):
            detail = str(entry.get("detail_path", "")).strip()
            if detail:
                detail_full = repo_root / detail
                detail_tokens = estimate_tokens(detail_full)
                per_path.append(
                    {
                        "path": detail,
                        "tokens": detail_tokens,
                        "kind": "lazy_detail",
                    }
                )
                total += detail_tokens
    return {"total_tokens": total, "paths": per_path}


def apply_budget_to_must_read(
    must_read: list[dict[str, Any]],
    *,
    repo_root: Path,
    budget_tokens: int,
    include_lazy_detail: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Keep must_read within budget. Non-lazy entries first; lazy detail deferred.
    Returns (trimmed_must_read, budget_report).
    """
    if budget_tokens <= 0:
        return list(must_read), {"total_tokens": 0, "deferred": [], "within_budget": True}

    kept: list[dict[str, Any]] = []
    deferred: list[str] = []
    used = 0

    def _cost(entry: Mapping[str, Any], *, with_detail: bool) -> int:
        rel = str(entry.get("path", "")).strip()
        if not rel:
            return 0
        cost = estimate_tokens(repo_root / rel)
        if with_detail and entry.get("lazy_load"):
            detail = str(entry.get("detail_path", "")).strip()
            if detail:
                cost += estimate_tokens(repo_root / detail)
        return cost

    for entry in must_read:
        if not entry.get("installed", True):
            kept.append(dict(entry))
            continue
        if entry.get("lazy_load") and not include_lazy_detail:
            cost_header = _cost(entry, with_detail=False)
            if used + cost_header <= budget_tokens:
                slim = dict(entry)
                slim["deferred_detail"] = True
                kept.append(slim)
                used += cost_header
            else:
                deferred.append(str(entry.get("path", "")))
            continue
        cost = _cost(entry, with_detail=True)
        if used + cost <= budget_tokens:
            kept.append(dict(entry))
            used += cost
        else:
            deferred.append(str(entry.get("path", "")))

    report = {
        "budget_tokens": budget_tokens,
        "used_tokens": used,
        "within_budget": not deferred,
        "deferred": deferred,
    }
    return kept, report


def budget_report_for_bundle(
    bundle: Mapping[str, Any],
    *,
    repo_root: Path,
    budget_tokens: int | None = None,
) -> dict[str, Any]:
    must_read = list(bundle.get("must_read") or [])
    estimate = estimate_must_read_tokens(must_read, repo_root=repo_root)
    out: dict[str, Any] = {
        "estimate": estimate,
        "files": list(bundle.get("files", [])),
    }
    if budget_tokens is not None:
        _, applied = apply_budget_to_must_read(
            must_read,
            repo_root=repo_root,
            budget_tokens=budget_tokens,
        )
        out["budget"] = applied
        out["would_defer"] = applied.get("deferred", [])
    return out
