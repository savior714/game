from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAYWRIGHT_WORKFLOW = ROOT / ".agents/workflows/playwright.md"
PLAYWRIGHT_RULE = ROOT / ".agents/domains/testing/playwright.md"
GIT_WORKFLOW = ROOT / ".agents/workflows/git.md"
EXECUTION_RULE = ROOT / ".agents/core/execution.md"
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


def test_git_workflow_is_a_minimal_destructive_safety_kernel() -> None:
    workflow = read(GIT_WORKFLOW)

    assert "소유권 × 의도 × 복구 가능성" in workflow
    assert "명령 blacklist 없음" in workflow
    assert "안전은 명령 문자열이 아니라 상태 전이에 대한 것이다" in workflow
    assert "이 저장소가 금지하는 전이" in workflow
    assert "공유 ref에 대한 force push와 공유 history rewrite" in workflow
    assert (
        "`--no-verify` 또는 동등한 우회로 필수 검증과 commit gate를 건너뛰는 것"
        in workflow
    )
    assert "launcher, queue," in workflow
    assert "../core/execution.md" in workflow
    assert "../core/verification.md" in workflow

    for delegated in (
        "main fast-forward push",
        "worktree add",
        "just commit-gate",
        "git push origin",
    ):
        assert delegated not in workflow, delegated


def test_execution_owns_workspace_commit_and_publication_procedure() -> None:
    execution = read(EXECUTION_RULE)
    justfile = read(ROOT / "Justfile")

    assert "통합·게시 기준은 `origin/main`" in execution
    assert "main fast-forward push" in execution
    assert "PR·feature branch는" in execution
    assert "사용자가 명시적으로 요청한 경우에만" in execution
    assert "force push, history rewrite, `--no-verify`는 금지한다." in execution
    assert "unrelated dirty state를 보존" in execution
    assert "정확한 파일 경로" in execution
    assert "원격 이동 자체만으로 자동 중단하거나 BLOCKED 처리하지 않는다." in execution
    assert "`force=false`로 ref를 이동한다" in execution
    assert "게시하지 않은 작업에는 `COMMIT`을 적지 않는다." in execution
    assert "git worktree add" in execution
    assert "--lock" in execution
    assert "git worktree remove" in execution

    assert "commit-gate-hard:" in justfile
    assert "commit-gate-soft:" in justfile
    assert "just commit-gate-hard" in execution
    assert "just commit-gate-soft" in execution


def test_git_and_execution_docs_remove_foreign_paths_and_verification_bypass() -> None:
    combined = read(GIT_WORKFLOW) + "\n" + read(EXECUTION_RULE)
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
        assert value not in combined
