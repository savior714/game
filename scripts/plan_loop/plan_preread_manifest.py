#!/usr/bin/env python3
"""Build or refresh the «Context Pre-read Gate» section on Blueprint plans.

Scans the plan for target paths and stack signals, runs route_context.get_route_bundle,
and emits a must_read checklist for implementers (IDE-agnostic).

This module re-exports key symbols from its submodules for backward compatibility.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.agent.route_context import find_repo_root  # noqa: E402
from scripts.agent.route_gate import append_bundle_from_route  # noqa: E402

# Re-export public symbols from submodules for backward compatibility.
from scripts.plan_loop.intent_utils import (  # noqa: E402,F401
    extract_plan_intents,
)
from scripts.plan_loop.path_utils import (  # noqa: E402,F401
    extract_plan_paths,
    extract_task_paths,
)
from scripts.plan_loop.preread_cli import build_parser  # noqa: E402
from scripts.plan_loop.preread_render import (  # noqa: E402
    TASK_PREREAD_MARKER,  # noqa: F401
    _normalize_packed_headings,
    build_manifest_for_plan,
    render_preread_section,
    upsert_preread_section,
    upsert_task_prereads_in_plan,
)

# Also re-export internal symbols used by tests / callers.
from scripts.plan_loop.stack_utils import (  # noqa: E402,F401
    _actionable_missing,
    infer_stack_labels,
)

SECTION_HEADING = "## 🧭 Context Pre-read Gate (실행 전 필수)"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    plan_path = args.plan.resolve()
    if not plan_path.is_file():
        print(f"Plan not found: {plan_path}", file=sys.stderr)
        return 1

    manifest = build_manifest_for_plan(
        plan_path,
        extra_paths=args.extra_paths,
        extra_intents=args.extra_intents,
    )

    if not args.write_manifest and args.phase != "turn1":
        print(
            "WARN: --phase는 --write-manifest 없이 무시됩니다. "
            "manifest phase를 기록하려면 --write-manifest를 함께 사용하세요.",
            file=sys.stderr,
        )

    bundle_id: str | None = None
    if args.write_manifest:
        bundle_id = append_bundle_from_route(manifest["route_bundle"], phase=args.phase)
        manifest["section_markdown"] = render_preread_section(
            plan_rel=manifest["plan"],
            plan_text=plan_path.read_text(encoding="utf-8"),
            paths=manifest["paths"],
            intents=manifest["intents"],
            bundle=manifest["bundle"],
            bundle_id=bundle_id,
        )

    if args.json:
        out = {
            "plan": manifest["plan"],
            "paths": manifest["paths"],
            "intents": manifest["intents"],
            "stack_labels": manifest["stack_labels"],
            "must_read_paths": manifest["bundle"]["must_read_paths"],
            "project_skills": manifest["bundle"]["project_skills"],
            "route_bundle": manifest["route_bundle"],
        }
        if bundle_id:
            out["manifest_write"] = {"bundle_id": bundle_id, "phase": args.phase}
        print(json.dumps(out, ensure_ascii=False, indent=2))

    if args.write:
        root = find_repo_root(plan_path.parent)
        original = _normalize_packed_headings(plan_path.read_text(encoding="utf-8"))
        updated = upsert_preread_section(original, manifest["section_markdown"])
        updated, task_count = upsert_task_prereads_in_plan(
            updated,
            repo_root=root,
            intents=manifest["intents"],
        )
        plan_path.write_text(updated, encoding="utf-8")
        print(
            f"Updated {plan_path} — Context Pre-read Gate "
            f"({len(manifest['bundle']['must_read_paths'])} installed paths), "
            f"Task Pre-read blocks: {task_count}"
        )
    elif not args.json:
        print(manifest["section_markdown"])
        print("\n(dry-run: pass --write to upsert into the plan file)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
