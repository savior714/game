from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSE_WORKFLOW = ROOT / ".agents/workflows/diagnose.md"
DIAGNOSE_SKILL = ROOT / ".agents/skills/diagnose/SKILL.md"
INVESTIGATE_WORKFLOW = ROOT / ".agents/workflows/investigate.md"
INVESTIGATE_SKILL = ROOT / ".agents/skills/investigate/SKILL.md"
REVIEW_WORKFLOW = ROOT / ".agents/workflows/review.md"
REVIEW_SKILL = ROOT / ".agents/skills/review/SKILL.md"
FILES = (
    DIAGNOSE_WORKFLOW,
    DIAGNOSE_SKILL,
    INVESTIGATE_WORKFLOW,
    INVESTIGATE_SKILL,
    REVIEW_WORKFLOW,
    REVIEW_SKILL,
)
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


def test_diagnostic_review_links_resolve() -> None:
    for document in FILES:
        assert document.is_file()
        for target in markdown_targets(document):
            assert target.exists(), f"{document}: broken link -> {target}"


def test_workflow_and_skill_pairs_reference_each_other() -> None:
    pairs = (
        (DIAGNOSE_WORKFLOW, DIAGNOSE_SKILL, "diagnose"),
        (INVESTIGATE_WORKFLOW, INVESTIGATE_SKILL, "investigate"),
        (REVIEW_WORKFLOW, REVIEW_SKILL, "review"),
    )
    for workflow, skill, name in pairs:
        assert f"../skills/{name}/SKILL.md" in read(workflow)
        assert f"../../workflows/{name}.md" in read(skill)


def test_diagnostic_contracts_remove_foreign_runtime_assumptions() -> None:
    combined = "\n".join(read(path) for path in FILES)
    forbidden = (
        "var/log/emr",
        "api-response-errors",
        "just raw-logs",
        "apps/renderer",
        "next.config",
        "proxy.ts",
        "src/app/",
        "renderer-route-smoke",
        "Fast Refresh",
        "React Render Cascade",
        "patient",
        "HIRA",
        "cognitive_logging",
        "knowledge-asset",
        "error-pattern-add",
        "route-gate-check",
        "domains/documentation",
        "domains/frontend",
        "docs/plans/adr",
    )
    for value in forbidden:
        assert value not in combined


def test_diagnose_uses_feedback_loop_without_forced_checkpoints() -> None:
    workflow = read(DIAGNOSE_WORKFLOW)
    skill = read(DIAGNOSE_SKILL)
    combined = workflow + "\n" + skill

    assert CURRENT_SPEC in workflow
    assert "빠르고 반복 가능한 PASS/FAIL 신호" in skill
    assert "가설 개수" in workflow
    assert "형식적으로 강제하지 않는다" in workflow
    assert "사용자 체크포인트를 형식적으로 요구하지 않는다" in skill
    assert "pageerror" in workflow
    assert "requestfailed" in workflow
    assert "한 failure domain" in workflow
    assert "3–5 ranked hypotheses" not in combined
    assert "Show the ranked list to the user" not in combined


def test_investigate_is_read_first_and_separates_facts_from_hypotheses() -> None:
    workflow = read(INVESTIGATE_WORKFLOW)
    skill = read(INVESTIGATE_SKILL)

    assert "기본적으로 read-only다." in workflow
    assert "사용자 요청이 분석만이면 production code를 수정하지 않는다." in workflow
    assert "사실, 추정, 미확인 항목을 구분한다." in workflow
    assert "## 4. 사실과 가설" in skill
    assert "확정되지 않은 가설을 root cause라고 보고하지 않는다." in skill
    assert "첫 failure domain" in workflow


def test_review_is_findings_first_without_mandatory_handoff_or_auto_plan() -> None:
    workflow = read(REVIEW_WORKFLOW)
    skill = read(REVIEW_SKILL)
    combined = workflow + "\n" + skill

    assert "findings를 요약보다 먼저" in workflow
    assert "구체적인 실패 시나리오" in workflow
    assert "종료 시 사용자 선택 질문을 형식적으로 강제하지 않는다." in workflow
    assert "review 결과를 자동으로 Blueprint 파일로 변환하지 않는다." in workflow
    assert "필수 질문이나 handoff menu를 자동으로 붙이지 않는다." in skill
    assert "사용자가 review-only를 요청했다면 코드를 변경하지 않는다." in skill
    assert "close 턴 필수" not in combined
    assert "same-session `/plan`" not in combined
    assert "AskQuestion" not in combined
    assert "question`(병용)" not in combined
