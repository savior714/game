from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAYWRIGHT_WORKFLOW = ROOT / ".agents/workflows/playwright.md"
PLAYWRIGHT_RULE = ROOT / ".agents/domains/testing/playwright.md"
GIT_WORKFLOW = ROOT / ".agents/workflows/git.md"
FILES = (PLAYWRIGHT_WORKFLOW, PLAYWRIGHT_RULE, GIT_WORKFLOW)
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


def test_playwright_git_links_resolve() -> None:
    for document in FILES:
        assert document.is_file()
        for target in markdown_targets(document):
            assert target.exists(), f"{document}: broken link -> {target}"


def test_playwright_workflow_matches_static_aidengame_runtime() -> None:
    workflow = read(PLAYWRIGHT_WORKFLOW)
    rules = read(PLAYWRIGHT_RULE)
    combined = workflow + "\n" + rules

    for subject in ("math", "english", "korean", "science"):
        assert f"domains/{subject}/index.html" in workflow

    assert CURRENT_SPEC in rules
    assert "ephemeral port" in workflow
    assert "browser-generated" in workflow
    assert "pageerror" in workflow
    assert "requestfailed" in workflow
    assert "question identity" in workflow
    assert "마지막 문제와 result" in workflow
    assert "restart" in workflow
    assert "자동으로 Blueprint 파일로 만들지 않는다." in workflow
    assert "fixed sleep보다" in rules
    assert "production handler를 직접 호출" in rules

    forbidden = (
        "/login",
        "/dashboard",
        "apps/renderer",
        "next.config",
        "API_PROXY_URL",
        "PLAYWRIGHT_BASE_URL",
        "agent-browser",
        "127.0.0.1:9223",
        "api-response-errors",
        "test-frontend",
        "Blueprint Integration",
        "docs/plans/playwright_",
        "use client",
        "500 빌드 에러",
    )
    for value in forbidden:
        assert value not in combined


def test_git_workflow_matches_main_fast_forward_policy() -> None:
    workflow = read(GIT_WORKFLOW)
    justfile = read(ROOT / "Justfile")

    assert "통합·게시 기준은 `origin/main`" in workflow
    assert "main fast-forward push" in workflow
    assert "PR·feature branch는 사용자가 명시적으로 요청한 경우에만" in workflow
    assert "force push, history rewrite, `--no-verify`는 금지" in workflow
    assert "unrelated dirty state를 보존" in workflow
    assert "정확한 파일 경로" in workflow
    assert "원격 이동 자체만으로 BLOCKED 처리하지 않는다." in workflow
    assert "force=false" in workflow
    assert "게시하지 않은 작업에는 `COMMIT`을 적지 않는다." in workflow

    assert "commit-gate-hard:" in justfile
    assert "commit-gate-soft:" in justfile
    assert "just commit-gate-hard" in workflow
    assert "just commit-gate-soft" in workflow


def test_git_workflow_removes_foreign_paths_and_verification_bypass() -> None:
    workflow = read(GIT_WORKFLOW)
    forbidden = (
        "apps/renderer",
        "fix(backend)",
        "feat(renderer)",
        ".agents/route/session-manifest.json",
        ".kilo/",
        "just ty",
        "grep -oP",
        "pre-existing 에러인 경우 `--no-verify`",
        "--no-verify 사용 시",
        "git stash push",
        "git pull --rebase origin $(git branch --show-current)",
        "push 1회",
        "Blueprint 참조",
    )
    for value in forbidden:
        assert value not in workflow
