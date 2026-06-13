#!/usr/bin/env python3
"""Plan close gate: block premature completion declarations.

Checks:
1) No `[완료 시 기입]` placeholders remain anywhere in the target plan.
2) Every line that declares a finished status (`Status: done` or legacy
   `Status: completed`) must have a non-empty, non-placeholder **Conclusion**
   field within the next few lines of that task block (same pattern as
   blueprint Task sections).
3) Optional `verify` specs must all exit 0.
4) : Plan 의 기술적 목표와 실제 코드 구현 불일치 검증 — Plan 에 명시된
   기술적 목표 (예: "VitalsChart 컴포넌트 구현") 가 실제로 코드로 구현되었는지 확인.

Operational note (humans/agents): fill each task's `- **Conclusion**:` as soon
as that task's Verify passes, *before* running this gate — the gate enforces
what the blueprint contract already expects.

Usage example:
  python3 scripts/verify/plan_close_gate.py \
    --plan docs/plans/archive/frontend/20260507_tdd_red_first_p2_frontend_desktop_execution_blueprint.md \
    --verify "apps/renderer::pnpm run test:run tests/unit/consultation/VitalsChart.test.tsx|||apps/renderer::pnpm run test:e2e e2e/unauthorized_redirect.spec.ts"
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
from scripts.plan_loop.plan_lint.verification import check_rollup_summary_for_close

# Inline is_conclusion_placeholder (copied from plan_lint.verification for standalone use)
import re as _re

_CANONICAL_TODO_CONCLUSION_SLOTS = (
    "[판정 — 비개발자용 요약. 검증 결과]",
    "[판정 — 비개발자용 요약. 검증 결과. 코드 이름 배제]",
    "[완료 시 기입]",
)

_BAD_PATTERNS = [
    r"\[TBD\]",
    r"완료 시 기입",
]

def is_conclusion_placeholder(value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return True
    for marker in ["[PASS]", "[FAIL]", "[성공]", "[실패]", "[DONE]", "[OK]"]:
        if normalized.startswith(marker):
            return False
    for pattern in _BAD_PATTERNS:
        if _re.search(pattern, normalized):
            return True
    return False

PLACEHOLDER = "[완료 시 기입]"
KOREAN_PLACEHOLDER = "[해결 건수/잔여 건수 요약]"


@dataclass
class VerifyResult:
    cwd: str
    command: str
    exit_code: int
    output: str


def parse_verify_specs(raw: str) -> list[tuple[str, str]]:
    if not raw.strip():
        return []
    specs: list[tuple[str, str]] = []
    for chunk in raw.split("|||"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "::" not in chunk:
            raise ValueError(f"invalid verify spec (expected 'cwd::command'): {chunk}")
        cwd, command = chunk.split("::", 1)
        cwd = cwd.strip()
        command = command.strip()
        if not cwd or not command:
            raise ValueError(f"invalid verify spec (empty cwd/command): {chunk}")
        specs.append((cwd, command))
    return specs


def check_placeholders(plan_text: str) -> list[str]:
    issues: list[str] = []
    if PLACEHOLDER in plan_text:
        issues.append(f"placeholder remains: {PLACEHOLDER}")
    return issues


def extract_dod_verify_specs(plan_path: Path) -> list[tuple[str, str]]:
    """Extract backticked commands from the DoD section to be run as verify specs."""
    plan_text = plan_path.read_text(encoding="utf-8")
    lines = plan_text.splitlines()
    
    in_dod = False
    specs = []
    for line in lines:
        if re.match(r"^##\s*✅\s*Definition of Done\s*\(\s*DoD\s*\)", line):
            in_dod = True
            continue
        if in_dod and re.match(r"^##\s", line):
            break
            
        if in_dod:
            if re.match(r"^\s*[-*]\s+|\s*\d+\.\s+", line):
                matches = re.findall(r"`([^`]+)`", line)
                for cmd in matches:
                    cmd = cmd.strip()
                    prefixes = ("just ", "pytest ", "pnpm ", "npm ", "yarn ", "python3 ", "uv run ", "playwright ")
                    if cmd.startswith(prefixes):
                        # Treat DoD commands as running from repo root
                        specs.append(("cwd", cmd))
    return specs


def _line_declares_finished_status(line: str) -> bool:
    return "Status: done" in line or "Status: completed" in line


def _line_declares_incomplete_status(line: str) -> bool:
    """Returns True if line declares an incomplete task status."""
    for status in ("Status: todo", "Status: running", "Status: blocked", "Status: failed"):
        if status in line:
            return True
    return False


def check_all_tasks_done(lines: list[str]) -> list[str]:
    """: Blueprint 의 모든 Task 가 완료 상태인지 검증.

    plan-close 게이트 진입 전, Blueprint 내 모든 Task 가 Status: done 또는
    Status: completed 이어야 한다. 미완료 Task (todo/running/blocked/failed) 가
    있으면 plan-close 를 차단한다.

    이 체크는 check_done_has_conclusion() 과 상호보완적이다:
    - check_done_has_conclusion(): done → Conclusion 검증 (완료된 Task 의 Conclusion 이 있는지)
    - check_all_tasks_done: incomplete → blocking 검증 (미완료 Task 가 있는지)
    """
    issues: list[str] = []
    incomplete_tasks: list[int] = []

    for idx, line in enumerate(lines):
        if _line_declares_incomplete_status(line):
            incomplete_tasks.append(idx + 1)

    if incomplete_tasks:
        for lineno in incomplete_tasks[:5]:  # 최대 5개만 표시
            issues.append(f"line {lineno}: incomplete task (Status: todo/running/blocked/failed)")
        if len(incomplete_tasks) > 5:
            issues.append(f"... and {len(incomplete_tasks) - 5} more incomplete tasks")

    return issues


def check_done_has_conclusion(lines: list[str]) -> list[str]:
    """: Status 가 done/completed 인 Task 에 Conclusion 필드가 없거나
    플레이스홀더이면 실패.

    플레이스홀더 패턴:
    - `[완료 시 기입]` (영어)
    - `[해결 건수/잔여 건수 요약]` (한국어)
    - `[...]` (30자 이하 대괄호 텍스트 — 포괄 방지)
    """
    issues: list[str] = []
    for idx, line in enumerate(lines):
        if not _line_declares_finished_status(line):
            continue
        window = lines[idx : min(idx + 30, len(lines))]
        conclusion_line = next((w for w in window if "Conclusion" in w), "")
        if not conclusion_line:
            issues.append(f"line {idx + 1}: finished-status task without Conclusion field")
            continue
        value = conclusion_line.split(":", 1)[1].strip() if ":" in conclusion_line else ""
        if not value or is_conclusion_placeholder(value):
            issues.append(
                f"line {idx + 1}: finished-status task has empty/placeholder Conclusion"
            )
    return issues


def check_plan_technical_goals_implementation(repo_root: Path, plan_path: Path) -> list[str]:
    """: Plan 의 기술적 목표와 실제 코드 구현 불일치 검증.

    Plan 에 명시된 기술적 목표 (예: "VitalsChart 컴포넌트 구현") 가 실제로
    코드로 구현되었는지 확인한다.

    검증 방법:
    1. Plan 의 각 Task 블록에서 기술적 목표를 추출 (Goal/Description 필드)
    2. 목표에 언급된 파일/컴포넌트/함수가 실제로 존재하는지 확인
    3. 구현이 누락되거나 불완전한 경우 실패

    예시:
      - Plan: "VitalsChart 컴포넌트 구현" → apps/renderer/src/components/consultation/VitalsChart.tsx 존재 확인
      - Plan: "VitalsChart 단위 테스트 작성" → tests/unit/consultation/VitalsChart.test.tsx 존재 확인
    """
    issues: list[str] = []
    plan_text = plan_path.read_text(encoding="utf-8")
    lines = plan_text.splitlines()

    # Plan 의 Task 블록을 추출 (Goal/Description 기반)
    task_blocks: list[tuple[int, str]] = []  # (start_line, goal_text)
    current_task_start: int | None = None
    current_goal: list[str] = []

    for idx, line in enumerate(lines):
        # Task 블록 시작 감지 (예: "- **Task 1**: ..." 또는 "### Task 1")
        if re.match(r"^\s*[-#]\s*\*?Task\s*\d+\*?:?\s*", line) or re.match(r"^\s*-+\s*$", line):
            if current_task_start is not None and current_goal:
                task_blocks.append((current_task_start, " ".join(current_goal).strip()))
            current_task_start = idx
            current_goal = []
        elif current_task_start is not None:
            # Goal/Description 필드 추출
            if re.match(r"^\s*(Goal|Description):?\s*", line):
                value = line.split(":", 1)[1].strip() if ":" in line else ""
                if value and value != PLACEHOLDER:
                    current_goal.append(value)

    # 마지막 Task 블록 추가
    if current_task_start is not None and current_goal:
        task_blocks.append((current_task_start, " ".join(current_goal).strip()))

    # 각 Task 의 기술적 목표에 대해 구현 상태 확인
    for start_line, goal_text in task_blocks:
        if not goal_text or goal_text == PLACEHOLDER:
            continue

        # 목표 텍스트에서 파일/컴포넌트/함수 이름 추출
        # 패턴: "VitalsChart 컴포넌트 구현", "VitalsChart 단위 테스트 작성" 등
        component_match = re.search(r"(\w+)\s*(컴포넌트|함수|모듈|스크립트)", goal_text)
        test_match = re.search(r"(\w+)\s*(단위 테스트|테스트)", goal_text)
        file_match = re.search(r"([\w/_.-]+\.(tsx?|py|jsx?))", goal_text)

        targets: list[str] = []
        if component_match:
            targets.append(component_match.group(1))
        if test_match:
            targets.append(test_match.group(1))
        if file_match:
            targets.append(file_match.group(1))

        # 추출된 타겟에 대해 구현 상태 확인
        for target in targets:
            # 파일 존재 여부 확인 (여러 패턴 시도)
            possible_paths = [
                repo_root / "apps" / "renderer" / "src" / "components" / target,
                repo_root / "apps" / "renderer" / "src" / "components" / f"{target}.tsx",
                repo_root / "apps" / "renderer" / "src" / "components" / target / f"{target}.tsx",
                repo_root / "tests" / "unit" / target,
                repo_root / "tests" / "unit" / f"{target}.test.tsx",
                repo_root / "tests" / "unit" / target / f"{target}.test.tsx",
                repo_root / "apps" / "renderer" / "src" / target,
                repo_root / "apps" / "renderer" / "src" / f"{target}.ts",
            ]

            found = False
            for path in possible_paths:
                if path.exists():
                    found = True
                    break

            # 테스트 파일의 경우 별도 확인
            if "테스트" in goal_text or "test" in goal_text.lower():
                test_paths = [
                    repo_root / "tests" / "unit" / f"{target}.test.tsx",
                    repo_root / "tests" / "unit" / target / f"{target}.test.tsx",
                    repo_root / "tests" / "unit" / f"{target}.test.ts",
                    repo_root / "apps" / "renderer" / "__tests__" / f"{target}.test.tsx",
                ]
                for path in test_paths:
                    if path.exists():
                        found = True
                        break

            if not found:
                issues.append(
                    f"line {start_line + 1}: 기술적 목표 구현 누락 — '{goal_text}' "
                    f"(타겟: {target})"
                )

    return issues


def run_verify_commands(repo_root: Path, specs: list[tuple[str, str]]) -> list[VerifyResult]:
    results: list[VerifyResult] = []
    for cwd, command in specs:
        # "cwd"는 special keyword — 현재 레포지토리 루트를 의미함
        if cwd == "cwd":
            run_cwd = repo_root.resolve()
        else:
            run_cwd = (repo_root / cwd).resolve()
        if not run_cwd.exists():
            results.append(
                VerifyResult(cwd=cwd, command=command, exit_code=2, output=f"cwd not found: {run_cwd}")
            )
            continue
        proc = subprocess.run(
            command,
            cwd=str(run_cwd),
            shell=True,
            text=True,
            capture_output=True,
            check=False,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        results.append(
            VerifyResult(cwd=cwd, command=command, exit_code=proc.returncode, output=output.strip())
        )
    return results


def write_report(path: Path, *, plan: str, issues: list[str], verify_results: list[VerifyResult]) -> None:
    payload = {
        "plan": plan,
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "verify_results": [
            {
                "cwd": vr.cwd,
                "command": vr.command,
                "exit_code": vr.exit_code,
                "script_not_found": "script not found" in vr.output.lower(),
            }
            for vr in verify_results
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate completion for plan documents.")
    parser.add_argument("--plan", required=True, type=Path, help="Path to target plan markdown")
    parser.add_argument(
        "--verify",
        default="",
        help="Optional verify specs: 'cwd::command|||subdir::command' (cwd = repo root)",
    )
    parser.add_argument(
        "--report",
        default="artifacts/verify/verify-last-result.json",
        type=Path,
        help="Output report path (default: artifacts/verify/verify-last-result.json)",
    )
    parser.add_argument(
        "--skip-tech-goal-check",
        action="store_true",
        help="Skip plan technical goal implementation check",
    )
    args = parser.parse_args()

    repo_root = Path.cwd()
    plan_arg = str(args.plan)
    if plan_arg.startswith("plan="):
        plan_arg = plan_arg.split("=", 1)[1]
    plan_path_raw = Path(plan_arg)
    plan_path = plan_path_raw if plan_path_raw.is_absolute() else (repo_root / plan_path_raw)
    if not plan_path.exists():
        print(f"[FAIL] plan file not found: {plan_path}")
        return 1

    plan_text = plan_path.read_text(encoding="utf-8")
    issues: list[str] = []
    issues.extend(check_placeholders(plan_text))
    issues.extend(check_rollup_summary_for_close(plan_text))
    issues.extend(check_done_has_conclusion(plan_text.splitlines()))

    # : Blueprint 의 모든 Task 가 완료되었는지 검증
    issues.extend(check_all_tasks_done(plan_text.splitlines()))

    # : Plan 의 기술적 목표와 실제 코드 구현 불일치 검증
    if not args.skip_tech_goal_check:
        issues.extend(check_plan_technical_goals_implementation(repo_root, plan_path))

    verify_results: list[VerifyResult] = []
    verify_arg = args.verify
    if verify_arg.startswith("verify="):
        verify_arg = verify_arg.split("=", 1)[1]
    verify_specs = parse_verify_specs(verify_arg)
    
    # Automatically add DoD verify specs
    dod_specs = extract_dod_verify_specs(plan_path)
    verify_specs.extend(dod_specs)

    if verify_specs:
        verify_results = run_verify_commands(repo_root, verify_specs)
        for result in verify_results:
            if result.exit_code != 0:
                issues.append(
                    f"verify failed [{result.cwd}] {result.command} (exit={result.exit_code})"
                )

    write_report(
        args.report if args.report.is_absolute() else (repo_root / args.report),
        plan=str(plan_path),
        issues=issues,
        verify_results=verify_results,
    )

    if issues:
        print("[FAIL] plan close gate failed")
        for issue in issues:
            print(f" - {issue}")
        print(
            "hint: (1) 각 Task 의 Verify 직후 `- **Conclusion**:` 기입, "
            "(2) `[완료 시 기입]` 및 `(Roll-up: … 기입.)` placeholder 제거, "
            "(3) Closeout Task 전 `## 🔁 Conclusion & Summary` Roll-up 1문단 작성."
        )
        return 1

    print("[PASS] plan close gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
