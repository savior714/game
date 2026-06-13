#!/usr/bin/env python3
"""plan-loop 보고서 생성 자동화 스크립트

docs/plans/*.md 파일에서 Task 블록을 추출하여 JSONL 보고서 파일을 생성합니다.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.plan_loop.plan_lint.shared import (
    _parse_fields,
    _split_task_blocks,
)

# 보고서 파일 목록
REPORT_FILES = [
    "dependency_graph.jsonl",
    "dod_checklist.jsonl",
    "path_verification.jsonl",
    "readme_registration.jsonl",
    "risk_audit.jsonl",
    "sdd_analysis.jsonl",
    "sdd_process_definition.jsonl",
    "sdd_structure_analysis.jsonl",
    "ssot_role_definition.jsonl",
    "template_structure.jsonl",
]


def extract_task_info(task_block: str, index: int) -> dict[str, str]:
    """Task 블록에서 정보 추출"""
    fields = _parse_fields(task_block)

    # Task-ID 추출
    task_id = fields.get("Task-ID", f"TASK-{index:03d}")

    # Status 추출
    status = fields.get("Status", "todo")

    # Target 추출
    target = fields.get("Target", "")

    # Goal 추출
    goal = fields.get("Goal", "")

    # Verify 추출
    verify = fields.get("Verify", "")

    # Conclusion 추출
    conclusion = fields.get("Conclusion", "")

    return {
        "task_id": task_id,
        "status": status,
        "target": target,
        "goal": goal,
        "verify": verify,
        "conclusion": conclusion,
        "extracted_at": datetime.now().isoformat(),
    }


def generate_report_files(plan_file: Path, output_dir: Path) -> list[str]:
    """plan-loop 보고서 파일 생성"""
    created_files: list[str] = []

    # 계획 파일 읽기
    text = plan_file.read_text(encoding="utf-8")

    # Task 블록 분할
    task_blocks = _split_task_blocks(text)

    if not task_blocks:
        print(f"[WARN] No task blocks found in {plan_file}")
        return created_files

    # 각 Task 블록에서 정보 추출
    tasks = []
    for idx, block in enumerate(task_blocks, start=1):
        task_info = extract_task_info(block, idx)
        tasks.append(task_info)

    # 보고서 파일 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    # dependency_graph.jsonl
    dep_file = output_dir / "dependency_graph.jsonl"
    with open(dep_file, "w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
    created_files.append(str(dep_file))

    # dod_checklist.jsonl
    dod_file = output_dir / "dod_checklist.jsonl"
    with open(dod_file, "w", encoding="utf-8") as f:
        for task in tasks:
            if task["status"] == "done":
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
    created_files.append(str(dod_file))

    # path_verification.jsonl
    path_file = output_dir / "path_verification.jsonl"
    with open(path_file, "w", encoding="utf-8") as f:
        for task in tasks:
            if "path" in task["verify"].lower() or "verify" in task["verify"].lower():
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
    created_files.append(str(path_file))

    # readme_registration.jsonl
    readme_file = output_dir / "readme_registration.jsonl"
    with open(readme_file, "w", encoding="utf-8") as f:
        for task in tasks:
            if "readme" in task["target"].lower() or "readme" in task["goal"].lower():
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
    created_files.append(str(readme_file))

    # risk_audit.jsonl
    risk_file = output_dir / "risk_audit.jsonl"
    with open(risk_file, "w", encoding="utf-8") as f:
        for task in tasks:
            if "risk" in task["goal"].lower() or "risk" in task["verify"].lower():
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
    created_files.append(str(risk_file))

    # sdd_analysis.jsonl
    sdd_file = output_dir / "sdd_analysis.jsonl"
    with open(sdd_file, "w", encoding="utf-8") as f:
        for task in tasks:
            if "sdd" in task["goal"].lower() or "behavioral" in task["goal"].lower():
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
    created_files.append(str(sdd_file))

    # sdd_process_definition.jsonl
    sdd_process_file = output_dir / "sdd_process_definition.jsonl"
    with open(sdd_process_file, "w", encoding="utf-8") as f:
        for task in tasks:
            if "process" in task["goal"].lower() or "workflow" in task["goal"].lower():
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
    created_files.append(str(sdd_process_file))

    # sdd_structure_analysis.jsonl
    sdd_structure_file = output_dir / "sdd_structure_analysis.jsonl"
    with open(sdd_structure_file, "w", encoding="utf-8") as f:
        for task in tasks:
            if "structure" in task["goal"].lower() or "template" in task["goal"].lower():
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
    created_files.append(str(sdd_structure_file))

    # ssot_role_definition.jsonl
    ssot_file = output_dir / "ssot_role_definition.jsonl"
    with open(ssot_file, "w", encoding="utf-8") as f:
        for task in tasks:
            if "ssot" in task["goal"].lower() or "role" in task["goal"].lower():
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
    created_files.append(str(ssot_file))

    # template_structure.jsonl
    template_file = output_dir / "template_structure.jsonl"
    with open(template_file, "w", encoding="utf-8") as f:
        for task in tasks:
            if "template" in task["goal"].lower() or "structure" in task["goal"].lower():
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
    created_files.append(str(template_file))

    return created_files


def main() -> int:
    parser = argparse.ArgumentParser(description="plan-loop 보고서 생성 자동화 스크립트")
    parser.add_argument("plan_file", type=Path, help="계획 파일 경로")
    parser.add_argument("--output-dir", type=Path, default=None, help="출력 디렉토리 (기본값: docs/reports/plan-loop)")
    args = parser.parse_args()

    # 출력 디렉토리 설정
    output_dir = args.output_dir or Path("docs/reports/plan-loop")

    # 보고서 파일 생성
    created_files = generate_report_files(args.plan_file, output_dir)

    if created_files:
        print(f"[INFO] Generated {len(created_files)} report files:")
        for f in created_files:
            print(f"  - {f}")
    else:
        print("[WARN] No report files generated.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
