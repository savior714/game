from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRINCIPLES = ROOT / ".agents/core/principles.md"
EXECUTION = ROOT / ".agents/core/execution.md"
VERIFICATION = ROOT / ".agents/core/verification.md"
REPORTING = ROOT / ".agents/core/reporting.md"
CORE_FILES = (PRINCIPLES, EXECUTION, VERIFICATION, REPORTING)
CURRENT_SPEC = "docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def markdown_targets(path: Path) -> list[Path]:
    targets: list[Path] = []
    for raw_target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", read(path)):
        target = raw_target.split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        targets.append((path.parent / target).resolve())
    return targets


def test_core_contract_links_resolve() -> None:
    for core_file in CORE_FILES:
        assert core_file.is_file()
        for target in markdown_targets(core_file):
            assert target.exists(), f"{core_file}: broken link -> {target}"


def test_core_contract_uses_current_aidengame_scope() -> None:
    combined = "\n".join(read(path) for path in CORE_FILES)

    assert CURRENT_SPEC in combined
    assert "Math, English, Korean, Science" in combined
    assert "Ocean Rescue" in combined
    assert "experiments/" in combined
    assert "한 failure domain" in combined
    assert "한 binary criterion" in combined
    assert "최신 `origin/main`" in combined


def test_execution_and_verification_use_real_repository_commands() -> None:
    justfile = read(ROOT / "Justfile")
    verification = read(VERIFICATION)

    commands = ("verify", "lint", "typecheck", "test", "ci")
    for command in commands:
        assert re.search(rf"^{command}(?:\s|:)", justfile, re.MULTILINE)
        assert f"just {command}" in verification

    assert (ROOT / "verify.sh").is_file()
    assert "bash ./verify.sh" in verification


def test_core_contract_removes_foreign_tooling_and_fake_gates() -> None:
    combined = "\n".join(read(path) for path in CORE_FILES)
    forbidden = (
        "apps/renderer",
        "typecheck:strict",
        "grid-verify",
        "/directory_verify",
        "artifacts/verify/verify-last-result.json",
        "just route ",
        "route-read",
        "route-gate-check",
        "Google Antigravity",
        "Cursor `Read`",
        "StrReplace",
        "emr_security.md",
        "Async DB Testing",
        "PostgreSQL",
        "packages/",
        "services/",
        "just raw-logs",
        "just api-response-errors",
        "Plan First (강제 트리거)",
    )
    for value in forbidden:
        assert value not in combined


def test_questions_are_reserved_for_material_context_gaps() -> None:
    principles = read(PRINCIPLES)

    assert "불확실성이 있다는 이유만으로 항상 질문하지 않는다." in principles
    assert "사용자 결정이 반드시 필요할 때만 질문 하나" in principles
    assert "하나의 결정축" in principles
    assert "권장 기본값은 정확히 하나" in principles


def test_verification_is_risk_based_and_schedule_decoupled() -> None:
    verification = read(VERIFICATION)

    assert "가장 작은 항목부터 시작" in verification
    assert "전체 suite는" in verification
    assert "제품 테스트의 PASS/FAIL criterion이 아니다" in verification
    assert "다음 WP" in verification
    assert "현재 WP" in verification
    assert "plan의 COMPLETE 문자열" in verification
    assert "page error와 `requestfailed`" in verification


def test_reporting_distinguishes_executed_tests_from_source_review() -> None:
    reporting = read(REPORTING)

    assert "테스트를 실행하지 않고 source contract만 확인했다면 “pytest PASS”라고 쓰지 않는다." in reporting
    assert "문서 작업은 제품 기능이 완료됐다는 뜻이 아니다." in reporting
    assert "실제 게시 시에만 `COMMIT`" in reporting
    assert "중단 시에만 `BLOCKER`와 `NEXT`" in reporting
