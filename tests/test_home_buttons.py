"""단일 홈 affordance 계약 — 상단 크롬에는 "놀이터 홈" 컨트롤이 정확히 하나만 존재한다.

canonical home control = brand wordmark 링크 (로고/워드마크).
brand cluster가 없는 페이지(예: ocean-rescue)는 명시적 홈 링크를 유지한다.
별도 맥락(인게임 일시정지/결과 화면, 시험 결과 화면)의 홈 CTA는 중복이 아니라
그 맥락의 유일한 종료 동선이므로 유지한다.
"""

from pathlib import Path
from html.parser import HTMLParser

REPO_ROOT = Path(__file__).parent.parent

# brand cluster(워드마크 링크)를 가진 페이지 → 홈 목적지
BRAND_HOME_PAGES = [
    ("index.html", "./index.html"),
    ("domains/math/index.html", "../../index.html"),
    ("domains/english/index.html", "../../index.html"),
    ("domains/english/weekly-test/index.html", "../../../index.html"),
    ("domains/korean/index.html", "../../index.html"),
    ("domains/science/index.html", "../../index.html"),
    ("domains/reward/guardian/index.html", "../../../index.html"),
    ("domains/auth/admin/index.html", "../../../index.html"),
    ("experiments/space-explorer/index.html", "../../index.html"),
    ("experiments/space-explorer/dino-escape.html", "../../index.html"),
    ("experiments/space-explorer/orbit-eclipse.html", "../../index.html"),
    ("experiments/space-explorer/paint-mixing.html", "../../index.html"),
    ("experiments/magnet/index.html", "../../index.html"),
    ("experiments/electricity/index.html", "../../index.html"),
    ("experiments/bubble/index.html", "../../index.html"),
    ("experiments/marble/index.html", "../../index.html"),
]

# brand cluster가 없는 페이지 → 명시적 홈 링크가 유일한 홈 컨트롤
EXPLICIT_HOME_PAGES = [
    ("ocean-rescue/index.html", "../index.html"),
    ("domains/ocean-rescue/index.html", "../../index.html"),
    ("domains/ocean-rescue/src/index.template.html", "../index.html"),
    ("domains/reward/reward_design_preview.html", "../../index.html"),
]

BRAND_CLASSES = (
    "ag-hud__brand",
    "lab-brand",
    "brand-badge",
    "hud-brand",
    "admin-brand",
)

# brand가 이미 홈 역할을 겸할 때 중복이 되는 별도 홈 버튼 클래스
STANDALONE_HOME_CLASSES = (
    "ag-hud__home",
    "compact-hud-home",
    "home-btn",
    "top-home",
)


class AnchorParser(HTMLParser):
    """header(상단 크롬) 안의 anchor만 href/클래스와 함께 수집한다."""

    def __init__(self) -> None:
        super().__init__()
        self.chrome_anchors: list[dict[str, object]] = []
        self.all_anchors: list[dict[str, object]] = []
        self._header_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "header":
            self._header_depth += 1
        elif tag == "a":
            attr_dict = dict(attrs)
            record = {
                "href": attr_dict.get("href"),
                "class": (attr_dict.get("class") or "").split(),
            }
            self.all_anchors.append(record)
            if self._header_depth > 0:
                self.chrome_anchors.append(record)

    def handle_endtag(self, tag):
        if tag == "header":
            self._header_depth = max(0, self._header_depth - 1)


def test_brand_is_the_only_home_control_in_page_chrome() -> None:
    """brand cluster가 있는 페이지: brand 링크가 홈 목적지의 유일한 상단 컨트롤."""
    for rel_path, target in BRAND_HOME_PAGES:
        file_path = REPO_ROOT / rel_path
        assert file_path.exists(), f"File missing: {rel_path}"

        content = file_path.read_text(encoding="utf-8")
        parser = AnchorParser()
        parser.feed(content)
        chrome_anchors = parser.chrome_anchors

        if not chrome_anchors:
            # JS가 주입하는 크롬(marble): 소스 레벨에서 brand 링크를 확인한다.
            assert 'class="brand-badge"' in content, (
                f"{rel_path} must expose the brand home link"
            )
            assert "home-btn" not in content, (
                f"{rel_path} must not keep a standalone home button"
            )
            continue

        home_links = [a for a in chrome_anchors if a["href"] == target]
        assert home_links, f"{rel_path} must expose a chrome home link to {target}"

        for anchor in home_links:
            classes = anchor["class"]
            assert any(c in BRAND_CLASSES for c in classes), (
                f"{rel_path} chrome home link must be the brand cluster, got {classes}"
            )

        for anchor in chrome_anchors:
            classes = anchor["class"]
            for standalone in STANDALONE_HOME_CLASSES:
                assert standalone not in classes, (
                    f"{rel_path} must not keep a standalone home button "
                    f"({standalone}) next to the brand link"
                )


def test_no_standalone_home_button_class_remains() -> None:
    """brand 링크와 중복되는 별도 홈 버튼 클래스는 저장소에 남아있지 않아야 한다."""
    for rel_path, _ in BRAND_HOME_PAGES:
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        for standalone in STANDALONE_HOME_CLASSES:
            assert standalone not in content, (
                f"{rel_path} still declares standalone home control '{standalone}'"
            )


def test_pages_without_brand_keep_explicit_home_link() -> None:
    """brand cluster가 없는 페이지에는 명시적 홈 링크가 남아야 한다."""
    for rel_path, target in EXPLICIT_HOME_PAGES:
        file_path = REPO_ROOT / rel_path
        assert file_path.exists(), f"File missing: {rel_path}"

        content = file_path.read_text(encoding="utf-8")
        parser = AnchorParser()
        parser.feed(content)
        assert any(a["href"] == target for a in parser.all_anchors), (
            f"{rel_path} must keep an explicit home link to {target}"
        )


def test_subject_chip_is_not_nested_inside_a_link() -> None:
    """과목/위치 칩은 링크 라벨이 아니다 (위치 표시에만 사용한다)."""
    for rel_path in (
        "index.html",
        "domains/math/index.html",
        "domains/english/index.html",
        "domains/korean/index.html",
        "domains/science/index.html",
        "domains/english/weekly-test/index.html",
        "domains/reward/guardian/index.html",
    ):
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "ag-hud__subject" in content, f"{rel_path} must have subject chip"

        parser = AnchorParser()
        parser.feed(content)
        for anchor in parser.all_anchors:
            classes = anchor["class"]
            assert "ag-hud__subject" not in classes, (
                f"{rel_path} subject chip must not be the link label itself"
            )


def test_main_page_core_quiz_subject_buttons_styling() -> None:
    index_path = REPO_ROOT / "index.html"
    assert index_path.exists()
    content = index_path.read_text(encoding="utf-8")

    assert "core-subject-grid" in content
    assert "core-subject-btn" in content
    assert "수학 놀이" in content
    assert "영어 놀이" in content
    assert "국어 놀이" in content
    assert "과학 놀이" in content

    styles_path = REPO_ROOT / "styles.css"
    assert styles_path.exists()
    styles_content = styles_path.read_text(encoding="utf-8")

    assert ".core-subject-grid" in styles_content
    assert ".core-subject-btn" in styles_content


def test_guardian_home_control_is_the_brand_link() -> None:
    """보호자 화면의 홈 이동은 brand 링크가 담당한다 (go-home 액션은 제거됨)."""
    guardian_html = (REPO_ROOT / "domains/reward/guardian/index.html").read_text(
        encoding="utf-8"
    )
    assert 'href="../../../index.html"' in guardian_html
    assert 'data-action="go-home"' not in guardian_html, (
        "guardian must not keep a dead go-home action"
    )

    for rel_path in (
        "domains/reward/guardian/guardian.js",
        "domains/reward/guardian/guardian-events.js",
    ):
        source = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "go-home" not in source, (
            f"{rel_path} must not keep a dead go-home handler"
        )


def test_reward_minigame_home_buttons_have_top_target() -> None:
    """Ensure Marble and Bubble brand home links use target='_top' to prevent iframe nesting."""
    for rel_path in ("experiments/marble/index.html", "experiments/bubble/index.html"):
        content = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert 'href="../../index.html" target="_top"' in content, (
            f"Expected target='_top' on ../../index.html links in {rel_path}"
        )
