#!/usr/bin/env python3
"""Unified Sync report generation (footers + terminal output).

Pure presentation layer for the spec-drift gate: builds the post-run
follow-up footer and renders the spec-alignment verdict to the terminal.
Kept import-free of sibling sync modules to avoid cycles.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def build_footer(
    level: str,
    smoke: bool,
    medium_paths: list[str] | None = None,
) -> str:
    if level == "skip":
        return ""
    lines = ["### 후속 (Unified Sync)"]
    if level == "required":
        lines.append(
            "코드·스펙 정합이 필요합니다. 관련 `docs/specs/**`·`docs/knowledge/**`를 갱신한 뒤 "
            "`just sync --check`가 PASS하는지 확인하세요."
        )
    else:
        lines.append("관련 명세가 있으면 Claim을 코드에 맞게 갱신한 뒤 `just sync --check`를 실행하세요.")
    steps = [
        "1. `/sync` — [.agents/workflows/sync.md](.agents/workflows/sync.md) Phase 2~4",
        "2. `just sync --check` — code lock + spec alignment",
    ]
    step_no = 3
    plan_touched = any(
        p.replace("\\", "/").startswith("docs/plans/PLAN_") for p in (medium_paths or [])
    )
    if plan_touched:
        steps.append(f"{step_no}. `just linear-dedup` — Blueprint↔Linear 중복 이슈 점검")
        step_no += 1
        
    product_plan_touched = False
    for p in (medium_paths or []):
        p_norm = p.replace("\\", "/")
        if p_norm.startswith("docs/plans/PLAN_"):
            try:
                from scripts.plan_archive_classify import archive_relative_path
                from scripts.plan_lifecycle.roadmap_product_allowlist import is_product_archive
                import pathlib
                filename = pathlib.Path(p_norm).name
                rel = archive_relative_path(filename)
                if is_product_archive(rel):
                    product_plan_touched = True
                    break
            except ImportError:
                pass
                
    if product_plan_touched:
        steps.append(f"{step_no}. `ROADMAP.md` 갱신 — 제품 Blueprint 완료 시 ROADMAP 상태 및 focus를 맞춰주세요.")
        step_no += 1
    if smoke:
        steps.append(f"{step_no}. `just renderer-route-smoke` — dev 서버(`:3000`) 기동 후")
        step_no += 1
    steps.append(f"{step_no}. 필요 시 `/asset` — 재발 패턴이면 knowledge에 기록")
    lines.extend(steps)
    return "\n".join(lines)


def print_spec_alignment_result(ok: bool, report: dict[str, object]) -> None:
    """Spec alignment 검증 결과를 터미널에 출력."""
    level = report.get("level", "skip")
    docs = report.get("docs_touched") or []
    missing = report.get("missing_specs") or []

    if report.get("ack_spec"):
        print("\n✅ [PASS] Spec alignment: `--ack-spec` (수동 역검증 완료 선언)")
        return

    if level == "skip":
        print("\n✅ [PASS] Spec alignment: skip (스펙 동기화 트리거 경로 없음)")
        return

    if docs:
        print(f"\n✅ [PASS] Spec alignment: 문서 갱신 {len(docs)}건 (docs/specs·plans·knowledge·qa)")
        for p in docs[:8]:
            print(f"   · {p}")
        if len(docs) > 8:
            print(f"   · … 외 {len(docs) - 8}건")
        return

    if ok and level == "suggested" and missing:
        print("\n⚠️  [WARN] Spec alignment: suggested — 후보 스펙을 검토하세요.")
        for sp in missing[:12]:
            print(f"   · {sp}")
        return

    if ok:
        print("\n✅ [PASS] Spec alignment")
        return

    print("\n❌ [FAIL] Spec alignment: 코드만 변경되고 관련 문서·스펙이 git diff에 없습니다.")
    print("   다음 중 하나를 수행하세요:")
    print("   1. 후보 스펙·knowledge를 코드 동작에 맞게 수정 (Last Verified·Claim 갱신)")
    for sp in missing[:12]:
        print(f"      · {sp}")
    if len(missing) > 12:
        print(f"      · … 외 {len(missing) - 12}건")
    print("   2. 수동 역검증 후 `just sync --check --ack-spec` (사유는 커밋/PR 본문에 남기기)")


# ─── Drift History ──────────────────────────────────────────────

_HISTORY_MAX = 30


def append_drift_snapshot(
    *, drift_count: int, history_path: str | Path | None = None
) -> None:
    """Append a drift-count snapshot to the rolling history JSON.

    Keeps the most recent ``_HISTORY_MAX`` records.
    """
    if history_path is None:
        history_path = Path(__file__).resolve().parents[3] / "docs" / "agent-context" / "memory" / "spec_drift_history.json"
    history_path = Path(history_path)

    # Load existing records
    if history_path.exists():
        try:
            data = json.loads(history_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        except (json.JSONDecodeError, OSError):
            data = []
    else:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        data = []

    # Append new record
    data.append(
        {
            "drift_count": drift_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    # Rolling window: keep only the last _HISTORY_MAX entries
    if len(data) > _HISTORY_MAX:
        data = data[-_HISTORY_MAX:]

    history_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
