from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_TOOLS = ROOT / ".agents/core/runtime_edit_tools.md"
OPENCODE_TOOLS = ROOT / ".agents/core/opencode_tools.md"
ERROR_PATTERNS = ROOT / ".agents/core/error_patterns.md"
CODE_QUALITY = ROOT / ".agents/core/code_quality_lifecycle.md"
RESILIENCE = ROOT / ".agents/core/resilience.md"
SECURITY = ROOT / ".agents/core/security.md"
AUXILIARY_FILES = (
    RUNTIME_TOOLS,
    OPENCODE_TOOLS,
    ERROR_PATTERNS,
    CODE_QUALITY,
    RESILIENCE,
    SECURITY,
)


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


def test_auxiliary_core_links_resolve() -> None:
    for core_file in AUXILIARY_FILES:
        assert core_file.is_file()
        for target in markdown_targets(core_file):
            assert target.exists(), f"{core_file}: broken link -> {target}"


def test_auxiliary_core_removes_foreign_repository_contracts() -> None:
    combined = "\n".join(read(path) for path in AUXILIARY_FILES)
    forbidden = (
        "/Users/seungjulee/Desktop/Dev/emr",
        "apps/renderer",
        "Google Antigravity",
        "Cursor IDE",
        "SPEC_TECH_tech_multi_agent_tooling.md",
        "projects/ai-log",
        "MCP `emr-repo`",
        "HIRA",
        "PHI",
        "FHIR",
        "LINEAR_API_KEY",
        "just linear-sync",
        "just linear-pull",
        "just env-lint",
        "just route ",
        "route-gate-check",
        "prevent-tech-debt",
        "ddd-gate",
        "fe-boundary-gate",
        "be-boundary-gate",
        "frontend_function_length_baseline",
        "dependency_overrides",
        "FastAPI",
        "PostgreSQL",
    )
    for value in forbidden:
        assert value not in combined


def test_runtime_tools_follow_current_schema_and_safe_edit_rules() -> None:
    runtime = read(RUNTIME_TOOLS)

    assert "현재 세션에 실제로 노출된 도구 설명과 schema" in runtime
    assert "부분 수정은 현재 내용에서 정확히 식별되는 최소 블록" in runtime
    assert "실패 후 같은 입력을 반복하지 않고 파일을 다시 읽는다." in runtime
    assert "원본 blob과 후보 blob의 diff" in runtime
    assert "특정 IDE의 도구 이름을 저장소 전역 SSOT로 고정하지 않는다." in runtime


def test_opencode_contract_uses_game_workspace_and_single_tool_stability() -> None:
    opencode = read(OPENCODE_TOOLS)

    assert "한 assistant turn에 도구 하나만 호출" in opencode
    assert "/Users/seungjulee/Desktop/Dev/.worktrees/game/<task-slug>" in opencode
    assert "다른 저장소 경로나 OS 임시 디렉터리" in opencode
    assert "현재 OpenCode 세션의 schema가 authority" in opencode
    assert "RESULT: PASS | BLOCKED" in opencode


def test_error_patterns_cover_current_repeated_failures() -> None:
    patterns = read(ERROR_PATTERNS)

    required_sections = (
        "## 1. 읽지 않고 수정",
        "## 3. 다른 런타임 tool schema 혼용",
        "## 4. 계획 문서 자동 생성",
        "## 5. 최근 커밋 관성",
        "## 8. 일정 상태와 제품 테스트 결합",
        "## 9. 대형 파일 전체 교체 유실",
        "## 10. 원격 이동 처리 실패",
        "## 12. 비밀값 노출",
    )
    for section in required_sections:
        assert section in patterns


def test_code_quality_matches_static_web_and_browser_runtime() -> None:
    quality = read(CODE_QUALITY)

    assert "정적 HTML/CSS/JavaScript 런타임" in quality
    assert "event listener, pointer capture, timer, animation frame" in quality
    assert "문제 identity와 per-question state reset" in quality
    assert "page error와 request failure" in quality
    assert "두 개 이상의 실제 사용처" in quality
    assert "just lint" in quality
    assert "just typecheck" in quality
    assert "just verify" in quality


def test_resilience_handles_structural_failure_and_remote_movement() -> None:
    resilience = read(RESILIENCE)

    assert "구조적 실패" in resilience
    assert "같은 입력 재시도를 중단" in resilience
    assert "검색 0건만으로 부재를 단정하지 않는다." in resilience
    assert "원격 이동 자체만으로 BLOCKED 처리하지 않는다." in resilience
    assert "fast-forward로만 게시" in resilience


def test_security_uses_actual_hard_gate_without_service_specific_credentials() -> None:
    security = read(SECURITY)
    justfile = read(ROOT / "Justfile")

    assert "commit-gate-hard:" in justfile
    assert "just commit-gate-hard" in security
    assert "scripts/verify/lint_dotenv.py" in security
    assert "`cat .env`, `echo $TOKEN`" in security
    assert "commit gate 실패 시 `--no-verify`로 우회하지 않는다." in security
    assert "특정 서비스 credential을 AidenGame 공통 필수 계약으로 강제하지 않는다." in security
