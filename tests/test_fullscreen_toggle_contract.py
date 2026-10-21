"""태블릿 전체 화면 토글 계약 — 버튼 하나로 전체 화면 진입과 되돌아오기를 보장한다.

버튼 마크업은 shared/ui/fullscreen-toggle.js가 HUD 우측 클러스터에 주입한다.
따라서 페이지마다 스크립트를 빠뜨리면 버튼이 조용히 사라진다 — 그 회귀를 막는다.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PAGES = {
    "index.html": "./shared/ui/fullscreen-toggle.js",
    "domains/math/index.html": "../../shared/ui/fullscreen-toggle.js",
    "domains/english/index.html": "../../shared/ui/fullscreen-toggle.js",
    "domains/korean/index.html": "../../shared/ui/fullscreen-toggle.js",
    "domains/science/index.html": "../../shared/ui/fullscreen-toggle.js",
    "domains/english/weekly-test/index.html": (
        "../../../shared/ui/fullscreen-toggle.js"
    ),
    "domains/reward/guardian/index.html": (
        "../../../shared/ui/fullscreen-toggle.js"
    ),
}


def read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_every_hud_page_wires_the_fullscreen_toggle_once() -> None:
    for rel_path, script_src in PAGES.items():
        html = read(rel_path)
        script_tag = f'<script src="{script_src}"></script>'
        assert script_tag in html, (
            f"{rel_path} must load the shared fullscreen toggle ({script_src})"
        )
        assert html.count("fullscreen-toggle.js") == 1, (
            f"{rel_path} must load the fullscreen toggle exactly once"
        )


def test_toggle_enters_and_returns_from_fullscreen() -> None:
    source = read("shared/ui/fullscreen-toggle.js")

    # 진입과 복귀가 같은 버튼 하나에 묶여 있어야 한다.
    assert "requestFullscreen" in source
    assert "exitFullscreen" in source
    assert "isFullscreen()" in source
    assert 'button.addEventListener("click", toggle)' in source

    # 벤더 prefix와 옛 API를 함께 처리한다.
    for prefix in ("webkit", "moz", "ms"):
        assert prefix in source, f"fullscreen toggle must support {prefix} prefixes"

    # 버튼 클릭 결과를 추측하지 않고 실제 fullscreen 상태로 라벨을 맞춘다.
    for event_name in (
        "fullscreenchange",
        "webkitfullscreenchange",
        "mozfullscreenchange",
        "MSFullscreenChange",
    ):
        assert event_name in source, (
            f"fullscreen state must re-sync on {event_name} (Esc · 브라우저 UI 포함)"
        )

    # 되돌아오기 라벨/역할이 명시되어야 한다.
    assert "전체 화면으로 보기" in source
    assert "전체 화면 끄기" in source
    assert "나가기" in source
    assert "aria-pressed" in source

    # Fullscreen API가 아예 없는 브라우저에서는 죽은 버튼을 만들지 않는다.
    assert 'typeof requestFullscreen !== "function"' in source
    assert 'typeof exitFullscreen !== "function"' in source

    # 권한이 막힌 문서(iframe 등)에서는 숨기지 않고 "쓸 수 없음"으로 표시하고 클릭을 배선하지 않는다.
    assert "fullscreenEnabled" in source
    assert "var blocked =" in source
    assert "if (!blocked)" in source
    assert "ag-fs-toggle--blocked" in source
    assert 'setAttribute("aria-disabled", "true")' in source

    # 단일 HUD 버튼: 중복 주입 방지와 HUD 부재 시 fallback이 있어야 한다.
    assert 'querySelector("[data-ag-fullscreen-toggle]")' in source
    assert 'querySelector(".ag-hud__right")' in source
    assert "ag-fs-toggle--floating" in source


def test_toggle_styles_are_shared_and_accessible() -> None:
    css = read("shared/ui/hud.css")

    # Tailwind preflight([type="button"])와 같은 specificity에서 밀리지 않도록
    # 클래스 단독 선택자가 아니라 button.ag-fs-toggle로 스타일한다.
    assert "button.ag-fs-toggle {" in css
    assert "background-color: rgba(255, 255, 255, 0.08);" in css
    assert 'button.ag-fs-toggle[aria-pressed="true"]' in css, (
        "active (되돌아오기) 상태 스타일이 있어야 한다"
    )
    assert "button.ag-fs-toggle:focus-visible" in css, (
        "키보드 포커스 표시가 필요하다"
    )
    assert "button.ag-fs-toggle--blocked" in css, (
        "fullscreen 권한이 막힌 상태의 표시가 필요하다"
    )
    assert "env(safe-area-inset-bottom)" in css, (
        "floating fallback은 태블릿 안전 영역을 피해야 한다"
    )
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "html:fullscreen" in css
