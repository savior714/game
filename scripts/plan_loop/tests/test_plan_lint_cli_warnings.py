"""plan_lint CLI exit code when only warnings are present."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.plan_loop.plan_lint import lint_plan_text


def _warnings_only_blueprint_body() -> str:
    """Minimal active-root blueprint: no issues, governance warning only."""
    return """<!-- Language: ko -->

# 🗺️ Project Blueprint: 경고만 있는 CLI 픽스처

## 문서 메타
- **SSOT Check**: scripts/plan_loop/plan_lint/cli.py
- **Project Status Link**: N/A
- **Architectural Goal**: CLI warnings-only exit code regression
- **Linear-Issue**: N/A
- **Priority**: 1
- **Labels**: tooling

## 📋 업무 요약 (협업용)

### 개요

테스트용 최소 계획서.

### staff·경영에서 바뀌는 점

- 없음

### 끝났을 때 확인할 것

- 없음

## 🧭 Context Pre-read Gate (실행 전 필수)

<!-- plan-preread:v1 generated=2026-06-04T00:00:00Z paths=0 must_read_installed=0 -->

### Read SSOT

### 재검증 (구현 세션에서 편집 전)

```bash
just route scripts/plan_loop/plan_lint/cli.py --json
```

## 🔍 Diagnosis & Findings

- **현상**: governance warning only

## 🏗️ Architectural Deepening

- **Seam**: cli.py

## 📜 Conceptual Sketch

```text
warnings only → exit 1
```

## 🛡️ Risk & Strategy

- **Risk**: x — **Strategy**: y

## 🔍 Impact Scope

| 영역 | 경로 |
| :--- | :--- |
| CLI | scripts/plan_loop/plan_lint/cli.py |

## Agent Completion Contract

| 허용 | 금지 |
| :--- | :--- |
| Verify PASS | warnings 무시 |

**Task 완료 정의**: Verify → plan-lint PASS.

## 🛠️ Step-by-Step Execution Plan

> **에이전트 스코프**: Task 1개씩. `Verify` PASS → **Conclusion** → `just plan-lint docs/plans/PLAN_fixture.md`.

#### Task 1.1: Governance warning only [Unit: Atomic]
- Task-ID: [WARN-001] | Linear-Issue: N/A | Status: todo | Priority: 1 | Labels: tooling | RetryPolicy: none
- **MCP**: desktop-commander
- **Pre-read**: 이 Task만 Read <!-- plan-task-preread:v1 paths=1 must_read_installed=1 -->
  1. `[rule]` scripts/plan_loop/plan_lint/cli.py
- **Action**: Edit File | **Target**: `scripts/plan_loop/plan_lint/cli.py`
- **Goal**: archive 경로 DoD checkbox는 warning만 발생하는지 검증한다
- **Diagnostics**: 0
- **Verify**: `just lint`
- **Conclusion**: [판정 — 비개발자용 요약. 검증 결과]
- **Dependency**: None

## 🔁 Conclusion & Summary

- **Roll-up**: ok

## ✅ Definition of Done (DoD)

1. [ ] `just lint`
"""


class TestPlanLintCliWarnings(unittest.TestCase):
    def test_fixture_is_warnings_only_at_linter_level(self) -> None:
        path = Path("docs/plans/archive/PLAN_test_cli_warnings_only.md")
        issues, warnings = lint_plan_text(_warnings_only_blueprint_body(), file_path=path)
        self.assertEqual(issues, [], issues)
        self.assertTrue(
            any("checkbox format" in w for w in warnings),
            warnings,
        )

    def test_plan_lint_warnings_only_exit_code_one(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        script = repo_root / "scripts" / "plan_loop" / "plan_lint.py"
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as plan:
            plan.write(_warnings_only_blueprint_body())
            plan_path = Path(plan.name)
        try:
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "python",
                    str(script),
                    str(plan_path),
                    "--skip-linear-ensure",
                ],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            plan_path.unlink(missing_ok=True)

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        combined = result.stdout + result.stderr
        self.assertIn("fix required before implementation", combined)


if __name__ == "__main__":
    unittest.main()
