"""홈 내비게이션 전수 계약 — 사용자 런타임 화면은 모두 루트 허브로 돌아갈 수 있어야 한다.

배경: 개별 화면(과목 퀴즈, 주간 시험, Ocean Rescue, 실험실, 보호자/관리자 등)에
진입한 뒤 홈으로 돌아갈 컨트롤이 없거나, 있어도 상대 경로가 어긋나 404로
빠지는 화면이 있었다. 이 테스트는 runtime HTML을 자동으로 훑어 다음을 강제한다.

1. runtime 페이지에는 루트 ``index.html``로 해석되는 앵커가 최소 하나 있다.
2. 그 앵커의 해석 경로는 실제 파일로 존재한다 (깨진 상대 경로 금지).
3. runtime 페이지 안의 ``.html`` 앵커는 모두 실제 파일을 가리킨다.
4. 종료/결과/차단 화면(퀴즈 결과, Ocean Rescue 일시정지·미션 완료, 물감 성공
   모달, 주간 시험 결과, Dino Escape 시작 화면, Space Explorer 로딩·오류 화면,
   Marble 로딩 실패 화면)에는 해당 화면만의 홈 CTA가 있다.
5. 폐기된 ``domains/ocean-rescue/`` URL은 정식 artifact로 리다이렉트하되,
   직접 홈 링크도 남긴다.

검증용 proof artifact, 테스트 fixture, 개발 전용 빈 entry, template source는
runtime 페이지가 아니므로 제외한다.
"""

from __future__ import annotations

import os
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "index.html"

# runtime HTML을 담는 디렉터리. internal proof/asset/source 디렉터리는 별도 처리한다.
RUNTIME_ROOTS = ("domains", "experiments", "ocean-rescue")
RUNTIME_FILES = ("index.html",)

# runtime 디렉터리 안에 있지만 사용자 화면이 아닌 파일.
EXEMPT = {
    # Vite dev 전용 빈 entry (template marker만 있음).
    "domains/ocean-rescue/index.dev.html",
    # 아트 검수용 contact sheet — 앱 내비게이션 대상이 아니다.
    "domains/ocean-rescue/assets/review/proof-art-contact-sheet.html",
}

# 산출물 빌드 입력. ``../index.html``은 생성 위치(ocean-rescue/index.html) 기준이다.
OCEAN_TEMPLATE = "domains/ocean-rescue/src/index.template.html"

QUIZ_PAGES = (
    "domains/math/index.html",
    "domains/english/index.html",
    "domains/korean/index.html",
    "domains/science/index.html",
)

OCEAN_PAGES = (
    "ocean-rescue/index.html",
    OCEAN_TEMPLATE,
)

LEGACY_OCEAN_PAGE = "domains/ocean-rescue/index.html"


class AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, str]] = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attributes = {key: value for key, value in attrs if value is not None}
        self.anchors.append(attributes)


def _collect_runtime_pages() -> list[Path]:
    pages: list[Path] = []
    for rel in RUNTIME_FILES:
        page = ROOT / rel
        if page.is_file():
            pages.append(page)

    for root_name in RUNTIME_ROOTS:
        root = ROOT / root_name
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            current = Path(dirpath)
            # generated assets, vendor node_modules, Ocean Rescue source는 runtime이 아니다.
            dirnames[:] = [
                name
                for name in dirnames
                if name != "node_modules"
                and not (current / name)
                .as_posix()
                .endswith("domains/ocean-rescue/assets")
                and not (current / name).as_posix().endswith("domains/ocean-rescue/src")
            ]
            for filename in filenames:
                if not filename.endswith(".html"):
                    continue
                page = current / filename
                rel = page.relative_to(ROOT).as_posix()
                if rel in EXEMPT:
                    continue
                pages.append(page)

    return sorted(set(pages), key=lambda path: path.relative_to(ROOT).as_posix())


def _anchors(page: Path) -> list[dict[str, str]]:
    parser = AnchorCollector()
    parser.feed(page.read_text(encoding="utf-8"))
    return parser.anchors


def _resolve(page: Path, href: str) -> Path | None:
    """페이지 기준 상대 href를 실제 파일 경로로 해석한다. 외부/특수 URL은 None."""
    value = (href or "").strip()
    if not value or value.startswith(("#", "mailto:", "javascript:", "data:")):
        return None
    if value.startswith(("http://", "https://", "//")):
        return None

    path = value.split("#", 1)[0].split("?", 1)[0]
    if not path:
        return None

    if path.startswith("/"):
        return Path(os.path.normpath(ROOT / path.lstrip("/")))
    return Path(os.path.normpath(ROOT / page.relative_to(ROOT).parent / path))


def _home_targets(page: Path) -> list[Path]:
    targets: list[Path] = []
    for anchor in _anchors(page):
        target = _resolve(page, anchor.get("href", ""))
        if target is not None and target == HOME:
            targets.append(target)
    return targets


def test_every_runtime_page_has_a_home_link() -> None:
    missing = []
    for page in _collect_runtime_pages():
        if not _home_targets(page):
            missing.append(page.relative_to(ROOT).as_posix())

    assert not missing, (
        "runtime 페이지에 루트 홈으로 가는 앵커가 없습니다: " + ", ".join(missing)
    )


def test_home_links_resolve_to_an_existing_root_index() -> None:
    broken = []
    for page in _collect_runtime_pages():
        for anchor in _anchors(page):
            target = _resolve(page, anchor.get("href", ""))
            if target is None:
                continue
            text = " ".join(
                value for value in anchor.values() if isinstance(value, str)
            )
            href = anchor.get("href", "")
            is_home_candidate = (
                "홈" in text or "home" in text.lower() or href.endswith("index.html")
            )
            if is_home_candidate and not target.is_file():
                broken.append(
                    f"{page.relative_to(ROOT).as_posix()} -> "
                    f"{href} ({target.relative_to(ROOT).as_posix()})"
                )

    assert not broken, "깨진 홈/인덱스 링크가 있습니다: " + ", ".join(broken)


def test_all_runtime_html_anchors_point_to_existing_files() -> None:
    broken = []
    for page in _collect_runtime_pages():
        for anchor in _anchors(page):
            href = anchor.get("href", "")
            if not href.split("#", 1)[0].lower().endswith(".html"):
                continue
            target = _resolve(page, href)
            if target is not None and not target.is_file():
                broken.append(f"{page.relative_to(ROOT).as_posix()} -> {href}")

    assert not broken, "존재하지 않는 HTML 링크가 있습니다: " + ", ".join(broken)


def test_quiz_result_screen_has_explicit_home_cta() -> None:
    for rel_path in QUIZ_PAGES:
        html = (ROOT / rel_path).read_text(encoding="utf-8")
        result_index = html.find('id="result-screen"')
        actions_index = html.find('class="quiz-result-actions"')
        assert result_index != -1, f"{rel_path} must keep #result-screen"
        assert actions_index != -1, (
            f"{rel_path} result screen must provide result actions"
        )
        assert result_index < actions_index, (
            f"{rel_path} result actions must live inside #result-screen"
        )
        snippet = html[actions_index : actions_index + 500]
        assert 'href="../../index.html"' in snippet, (
            f"{rel_path} result screen must link back to the main hub"
        )


def test_ocean_rescue_pause_and_completion_have_home_cta() -> None:
    for rel_path in OCEAN_PAGES:
        html = (ROOT / rel_path).read_text(encoding="utf-8")
        for element_id in (
            "ocean-rescue-pause-home",
            "ocean-rescue-mission-complete-home",
        ):
            pattern = re.compile(
                r"<a\b"
                + r"(?=[^>]*\bid=\""
                + re.escape(element_id)
                + r"\")"
                + r"(?=[^>]*\bhref=\"\.\./index\.html\")"
                + r"[^>]*>",
                re.IGNORECASE,
            )
            assert pattern.search(html), (
                f"{rel_path} must expose #{element_id} -> ../index.html"
            )


def test_paint_success_modal_has_home_cta() -> None:
    html = (ROOT / "experiments/space-explorer/paint-mixing.html").read_text(
        encoding="utf-8"
    )
    modal_index = html.find('id="paint-success-modal"')
    home_markup = 'href="../../index.html" class="paint-ghost-button paint-home-link"'
    home_index = html.find(home_markup)
    assert modal_index != -1, "paint success modal must exist"
    assert home_index != -1, "paint success modal must offer a home link"
    assert modal_index < home_index, "home link must live inside the success modal"


def test_weekly_test_result_screen_has_explicit_home_cta() -> None:
    html = (ROOT / "domains/english/weekly-test/index.html").read_text(encoding="utf-8")
    result_index = html.find('id="result-screen"')
    home_markup = '<a href="../../../index.html" class="wt-btn wt-btn-home">'
    home_index = html.find(home_markup)
    assert result_index != -1 and home_index != -1
    assert result_index < home_index
    snippet = html[home_index : home_index + 300]
    assert "메인 홈으로" in snippet


def test_reward_design_preview_redirects_to_main_hub() -> None:
    html = (ROOT / "domains/reward/reward_design_preview.html").read_text(
        encoding="utf-8"
    )
    assert "window.location.href = '../../index.html'" in html, (
        "reward design preview must return to the main hub, not /domains/index.html"
    )


def test_js_injected_marble_hud_exposes_home_link() -> None:
    html = (ROOT / "experiments/marble/index.html").read_text(encoding="utf-8")
    assert 'href="../../index.html" target="_top" class="brand-badge"' in html, (
        "marble must inject a top-level home affordance into its HUD"
    )


def test_legacy_domains_ocean_rescue_redirects_to_canonical_artifact() -> None:
    html = (ROOT / LEGACY_OCEAN_PAGE).read_text(encoding="utf-8")
    assert (
        'http-equiv="refresh" content="0; url=../../ocean-rescue/index.html"' in html
    ), "legacy /domains/ocean-rescue/ URL must forward to the canonical artifact"
    assert 'href="../../index.html"' in html, (
        "legacy redirect page must still expose a direct home link"
    )


def test_dino_escape_start_screen_has_home_cta() -> None:
    """입장 게이트를 통과한 뒤 첫 화면(시작 화면)도 홈으로 나갈 수 있어야 한다."""
    html = (ROOT / "experiments/space-explorer/dino-escape.html").read_text(
        encoding="utf-8"
    )
    start_index = html.find('id="screen-start"')
    settings_index = html.find('id="btn-start-settings"')
    section_end = html.find("</section>", settings_index)
    assert start_index != -1 and settings_index != -1
    assert section_end != -1
    assert 'href="../../index.html"' in html[settings_index:section_end], (
        "Dino Escape 시작 화면에 홈 CTA가 없습니다"
    )


def test_space_explorer_loading_and_fatal_states_offer_home() -> None:
    """로딩/치명적 오류 화면은 헤더를 덮으므로 자체 홈 동선이 필요하다."""
    html = (ROOT / "experiments/space-explorer/index.html").read_text(encoding="utf-8")

    loading_start = html.find('id="loading-screen"')
    loading_end = html.find("</section>", loading_start)
    assert loading_start != -1 and loading_end != -1
    assert 'href="../../index.html"' in html[loading_start:loading_end], (
        "Space Explorer 로딩 화면에 홈 CTA가 없습니다"
    )

    fatal_start = html.find('id="fatal-error"')
    fatal_end = html.find("</div>", fatal_start)
    assert fatal_start != -1 and fatal_end != -1
    assert 'href="../../index.html"' in html[fatal_start:fatal_end], (
        "Space Explorer 오류 화면에 홈 CTA가 없습니다"
    )


def test_marble_load_failure_state_offers_home() -> None:
    """압축 해제/로딩 실패 시 HUD가 주입되지 않으므로 정적 홈 링크가 필요하다."""
    html = (ROOT / "experiments/marble/index.html").read_text(encoding="utf-8")
    loading_index = html.find('id="loadError"')
    home_index = html.find('class="load-error-home"')
    assert loading_index != -1 and home_index != -1
    assert loading_index < home_index
    assert 'href="../../index.html"' in html[home_index : home_index + 200]
