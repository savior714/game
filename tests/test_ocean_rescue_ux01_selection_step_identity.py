"""UX-01 focused browser test: selection flow step identity.

The three selection screens (profile choice, mission select, GUP select) must
expose distinct, stable step identity (number, glyph, label, accent color), and
mission selection state must be restored after a GUP Back navigation.

This test drives the tracked standalone HTML through Playwright across three
viewports and asserts the runtime DOM, accessibility attributes, computed
styles, and geometry. Pixel hashes are not used for PASS.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
from test_ocean_rescue_wp02_browser_baseline import HTTPServerFixture  # noqa: E402

REPO_ROOT = TESTS_DIR.parent
ARTIFACT = REPO_ROOT / "ocean-rescue" / "index.html"
TEMPLATE = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "index.template.html"
STYLE = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "style.css"
APP_JS = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "app.js"
MISSIONS_CATALOG = (
    REPO_ROOT / "domains" / "ocean-rescue" / "src" / "missions" / "catalog.ts"
)
GUPS_CATALOG = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "gups" / "catalog.ts"

STEP_CONTRACT = {
    "profile": {"number": "1", "glyph": "★", "label": "CREW"},
    "mission": {"number": "2", "glyph": "⚑", "label": "MISSION"},
    "gup": {"number": "3", "glyph": "▲", "label": "GUP"},
}

EXPECTED_ACCENTS = {"profile": "#ffd166", "mission": "#3ddad7", "gup": "#ff9f80"}

VIEWPORTS = [(1280, 720), (1280, 800), (1024, 768)]

_MARKER_RE = re.compile(
    r'class="ocean-rescue-selection-step"\s+aria-hidden="true"\s*>'
    r'\s*<span class="ocean-rescue-selection-step-number">(\d+)</span>'
    r"\s*<span class=\"ocean-rescue-selection-step-glyph\">([^<]+)</span>"
    r'\s*<span class="ocean-rescue-selection-step-label">([^<]+)</span>'
)


def _visible(page, selector: str) -> bool:
    return bool(
        page.evaluate(
            """sel => {
              const el = document.querySelector(sel);
              return !!el && !el.hidden && getComputedStyle(el).display !== 'none';
            }""",
            selector,
        )
    )


def _section_state(page, step: str, section_sel: str) -> dict:
    return page.evaluate(
        """(args) => {
          const section = document.querySelector(args.sectionSel);
          const marker = section.querySelector('.ocean-rescue-selection-step');
          const h2 = section.querySelector('h2');
          const accent = getComputedStyle(section)
            .getPropertyValue('--ocean-rescue-selection-accent').trim();
          const markerRect = marker.getBoundingClientRect();
          const sectionRect = section.getBoundingClientRect();
          const h2Rect = h2.getBoundingClientRect();
          const glyph = marker.querySelector('.ocean-rescue-selection-step-glyph');
          const markerStyle = getComputedStyle(marker);
          return {
            step: section.getAttribute('data-selection-step'),
            number: marker.querySelector('.ocean-rescue-selection-step-number').textContent.trim(),
            glyph: glyph.textContent.trim(),
            label: marker.querySelector('.ocean-rescue-selection-step-label').textContent.trim(),
            markerAriaHidden: marker.getAttribute('aria-hidden'),
            markerVisible: markerStyle.display !== 'none' &&
              markerStyle.visibility !== 'hidden' &&
              markerRect.width > 0 && markerRect.height > 0,
            accent: accent,
            borderTopColor: getComputedStyle(section).borderTopColor,
            markerGlyphColor: getComputedStyle(glyph).color,
            markerInSection: markerRect.left >= sectionRect.left - 1 &&
              markerRect.right <= sectionRect.right + 1 &&
              markerRect.top >= sectionRect.top - 1 &&
              markerRect.bottom <= sectionRect.bottom + 1,
            markerAboveHeading: markerRect.bottom <= h2Rect.top + 1,
            sectionOverflowX: section.scrollWidth <= section.clientWidth + 1,
            headingText: h2.textContent.trim(),
          };
        }""",
        {"sectionSel": section_sel},
    )


def _mission_cards(page) -> list[dict]:
    return page.evaluate(
        """() => Array.from(
          document.querySelectorAll('#ocean-rescue-mission-list [data-mission-id]')
        ).map(b => ({
          id: b.getAttribute('data-mission-id'),
          pressed: b.getAttribute('aria-pressed'),
          disabled: b.disabled,
          borderColor: getComputedStyle(b).borderTopColor,
          background: getComputedStyle(b).backgroundColor,
          boxShadow: getComputedStyle(b).boxShadow,
        }))"""
    )


def _mission_section_state(page) -> dict:
    return page.evaluate(
        """() => {
          const section = document.getElementById('ocean-rescue-mission-select');
          return {
            selectedId: section.getAttribute('data-selected-mission-id'),
          };
        }"""
    )


def _rgb_to_hex(rgb: str) -> str | None:
    match = re.fullmatch(r"rgb\((\d+), (\d+), (\d+)\)", rgb)
    if not match:
        return None
    return "#{:02x}{:02x}{:02x}".format(
        int(match.group(1)), int(match.group(2)), int(match.group(3))
    )


@pytest.mark.parametrize(
    "viewport", VIEWPORTS, ids=["1280x720", "1280x800", "1024x768"]
)
def test_browser_selection_step_identity_flow(viewport: tuple[int, int]) -> None:
    width, height = viewport
    server = HTTPServerFixture()
    base_url = server.start()
    page_errors: list[str] = []
    console_errors: list[str] = []
    request_failures: list[str] = []
    requests: list[dict] = []

    accents: dict[str, str] = {}

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--disable-background-networking", "--disable-component-update"],
            )
            try:
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )
                context.add_init_script("window.localStorage.clear();")
                page = context.new_page()
                page.on("pageerror", lambda e: page_errors.append(str(e)))
                page.on(
                    "console",
                    lambda m: (
                        console_errors.append(m.text) if m.type == "error" else None
                    ),
                )
                page.on("requestfailed", lambda r: request_failures.append(r.url))
                page.on(
                    "request",
                    lambda r: requests.append({"url": r.url, "type": r.resource_type}),
                )

                page.goto(f"{base_url}/ocean-rescue/index.html")
                page.wait_for_selector(
                    "#ocean-rescue-root[data-ocean-rescue-ready=true]", timeout=30000
                )
                page.wait_for_selector(
                    "#ocean-rescue-profile-choice:not([style*='display:none'])",
                    timeout=10000,
                )

                # Profile screen.
                profile = _section_state(
                    page, "profile", "#ocean-rescue-profile-choice"
                )
                assert profile["step"] == "profile"
                assert profile["number"] == STEP_CONTRACT["profile"]["number"]
                assert profile["glyph"] == STEP_CONTRACT["profile"]["glyph"]
                assert profile["label"] == STEP_CONTRACT["profile"]["label"]
                assert profile["markerAriaHidden"] == "true"
                assert profile["markerVisible"] is True
                assert profile["headingText"] == "Choose your Octonaut"
                assert profile["accent"] == EXPECTED_ACCENTS["profile"]
                assert (
                    _rgb_to_hex(profile["borderTopColor"])
                    == EXPECTED_ACCENTS["profile"]
                )
                assert (
                    _rgb_to_hex(profile["markerGlyphColor"])
                    == EXPECTED_ACCENTS["profile"]
                )
                assert profile["markerInSection"] is True
                assert profile["markerAboveHeading"] is True
                assert profile["sectionOverflowX"] is True
                accents["profile"] = profile["accent"]

                assert _visible(page, "#ocean-rescue-profile-choice") is True

                # Select profile animal and continue to mission select.
                page.click('[data-profile-animal-id="beaver"]')
                page.click("#ocean-rescue-profile-continue")
                page.wait_for_selector(
                    "#ocean-rescue-mission-select:not([style*='display:none'])",
                    timeout=10000,
                )

                # Mission screen.
                mission = _section_state(
                    page, "mission", "#ocean-rescue-mission-select"
                )
                assert mission["step"] == "mission"
                assert mission["number"] == STEP_CONTRACT["mission"]["number"]
                assert mission["glyph"] == STEP_CONTRACT["mission"]["glyph"]
                assert mission["label"] == STEP_CONTRACT["mission"]["label"]
                assert mission["markerAriaHidden"] == "true"
                assert mission["markerVisible"] is True
                assert mission["headingText"] == "Choose a Mission"
                assert mission["accent"] == EXPECTED_ACCENTS["mission"]
                assert (
                    _rgb_to_hex(mission["borderTopColor"])
                    == EXPECTED_ACCENTS["mission"]
                )
                assert (
                    _rgb_to_hex(mission["markerGlyphColor"])
                    == EXPECTED_ACCENTS["mission"]
                )
                assert mission["markerInSection"] is True
                assert mission["markerAboveHeading"] is True
                assert mission["sectionOverflowX"] is True
                accents["mission"] = mission["accent"]

                cards = _mission_cards(page)
                assert [c["id"] for c in cards] == ["sea-turtle", "crab", "young-whale"]
                assert all(c["pressed"] == "false" for c in cards), (
                    "initial mission cards must be explicitly aria-pressed=false"
                )
                assert [c["disabled"] for c in cards] == [False, True, True], (
                    "locked mission cards must remain disabled"
                )
                assert _mission_section_state(page)["selectedId"] is None

                # Locked cards are disabled and have explicit aria-pressed=false.
                for card in cards[1:]:
                    assert card["disabled"] is True
                    assert card["pressed"] == "false"

                # Select the first unlocked mission -> GUP screen.
                page.click('#ocean-rescue-mission-list [data-mission-id="sea-turtle"]')
                page.wait_for_selector("#ocean-rescue-gup-select:not([hidden])")

                # GUP screen.
                gup = _section_state(page, "gup", "#ocean-rescue-gup-select")
                assert gup["step"] == "gup"
                assert gup["number"] == STEP_CONTRACT["gup"]["number"]
                assert gup["glyph"] == STEP_CONTRACT["gup"]["glyph"]
                assert gup["label"] == STEP_CONTRACT["gup"]["label"]
                assert gup["markerAriaHidden"] == "true"
                assert gup["markerVisible"] is True
                assert gup["headingText"] == "Choose a GUP"
                assert gup["accent"] == EXPECTED_ACCENTS["gup"]
                assert _rgb_to_hex(gup["borderTopColor"]) == EXPECTED_ACCENTS["gup"]
                assert _rgb_to_hex(gup["markerGlyphColor"]) == EXPECTED_ACCENTS["gup"]
                assert gup["markerInSection"] is True
                assert gup["markerAboveHeading"] is True
                assert gup["sectionOverflowX"] is True
                accents["gup"] = gup["accent"]

                # Three computed accents are pairwise distinct.
                assert accents["profile"] != accents["mission"]
                assert accents["mission"] != accents["gup"]
                assert accents["profile"] != accents["gup"]

                # GUP cards expose existing aria-pressed.
                gup_cards = page.evaluate(
                    """() => Array.from(
                      document.querySelectorAll('#ocean-rescue-gup-list [data-gup-id]')
                    ).map(b => b.getAttribute('aria-pressed'))"""
                )
                assert gup_cards == ["true", "false", "false"]

                # Back to mission select.
                page.click("#ocean-rescue-gup-back")
                page.wait_for_selector(
                    "#ocean-rescue-mission-select:not([style*='display:none'])",
                    timeout=10000,
                )

                # Selected mission restored.
                restored = _mission_cards(page)
                by_id = {c["id"]: c for c in restored}
                assert by_id["sea-turtle"]["pressed"] == "true", (
                    "previously selected mission must be aria-pressed=true"
                )
                assert by_id["crab"]["pressed"] == "false"
                assert by_id["young-whale"]["pressed"] == "false"
                assert by_id["sea-turtle"]["disabled"] is False
                assert by_id["crab"]["disabled"] is True
                assert by_id["young-whale"]["disabled"] is True

                assert _mission_section_state(page)["selectedId"] == "sea-turtle", (
                    "mission section must expose the selected mission id"
                )

                # Selected vs non-selected computed treatment must differ.
                assert (
                    by_id["sea-turtle"]["borderColor"] != by_id["crab"]["borderColor"]
                ), "selected mission card must have a visibly distinct border"

                # Focus outline retained: focus-visible outline must still render
                # on the selected mission card after keyboard navigation.
                focus_info = _focus_mission_card_via_keyboard(page, "sea-turtle")
                assert focus_info is not None, (
                    "sea-turtle card must be keyboard focusable"
                )
                assert focus_info["outlineWidth"] != "0px", (
                    "selected card focus-visible outline must be preserved"
                )

                # Primary controls keep the 48px floor.
                for control_sel in [
                    "#ocean-rescue-profile-continue",
                    "#ocean-rescue-gup-back",
                    "#ocean-rescue-gup-launch",
                ]:
                    min_h = float(
                        page.evaluate(
                            """sel => parseFloat(
                              getComputedStyle(document.querySelector(sel)).minHeight
                            )""",
                            control_sel,
                        )
                    )
                    assert min_h >= 48, f"{control_sel} dropped below the 48px floor"

                # No horizontal overflow for the visible mission section.
                assert mission["sectionOverflowX"] is True
                assert (
                    page.evaluate(
                        "() => document.documentElement.scrollWidth <= "
                        "document.documentElement.clientWidth + 1"
                    )
                    is True
                )
            finally:
                browser.close()
    finally:
        server.stop()

    assert page_errors == [], f"page errors: {page_errors}"
    assert console_errors == [], f"console errors: {console_errors}"
    assert request_failures == [], f"failed requests: {request_failures}"
    assert all(r["url"].startswith(base_url) for r in requests), (
        f"external requests: {[r for r in requests if not r['url'].startswith(base_url)]}"
    )


def _focus_mission_card_via_keyboard(page, mission_id: str) -> dict | None:
    page.keyboard.press("Tab")
    for _ in range(12):
        info = page.evaluate(
            """id => {
              const el = document.activeElement;
              if (!el || el.getAttribute('data-mission-id') !== id) {
                return null;
              }
              const style = getComputedStyle(el);
              return {
                focusedId: el.getAttribute('data-mission-id'),
                outlineWidth: style.outlineWidth,
                outlineStyle: style.outlineStyle,
                matchesFocusVisible: el.matches(':focus-visible'),
              };
            }""",
            mission_id,
        )
        if info is not None:
            return info
        page.keyboard.press("Tab")
    return None


# ── static contract checks ─────────────────────────────────────────────────


def test_template_step_identity_contract() -> None:
    html = TEMPLATE.read_text(encoding="utf-8")

    for step in STEP_CONTRACT:
        assert html.count(f'data-selection-step="{step}"') == 1, (
            f"{step} data-selection-step must appear exactly once"
        )

    markers = _MARKER_RE.findall(html)
    assert len(markers) == 3, f"expected exactly 3 step markers, got {len(markers)}"
    markers_by_step = {
        "profile": (markers[0][0], markers[0][1], markers[0][2]),
        "mission": (markers[1][0], markers[1][1], markers[1][2]),
        "gup": (markers[2][0], markers[2][1], markers[2][2]),
    }
    for step, expected in STEP_CONTRACT.items():
        assert markers_by_step[step] == (
            expected["number"],
            expected["glyph"],
            expected["label"],
        ), f"{step} marker content mismatch"

    assert html.count('aria-hidden="true"') >= 3
    for marker_block in _MARKER_RE.finditer(html):
        block = marker_block.group(0)
        assert 'aria-hidden="true"' in block

    # Existing headings and accessible names are preserved.
    for heading in [
        'id="ocean-rescue-profile-choice-title">Choose your Octonaut',
        'id="ocean-rescue-mission-select-title">Choose a Mission',
        'id="ocean-rescue-gup-select-title">Choose a GUP',
    ]:
        assert heading in html

    # The standalone artifact is regenerated from the template.
    artifact = ARTIFACT.read_text(encoding="utf-8")
    for step in STEP_CONTRACT:
        assert f'data-selection-step="{step}"' in artifact


def test_css_step_identity_contract() -> None:
    css = STYLE.read_text(encoding="utf-8")

    # Shared marker primitive (no per-section copies).
    for selector in [
        ".ocean-rescue-selection-step {",
        ".ocean-rescue-selection-step-number,",
        ".ocean-rescue-selection-step-glyph,",
        ".ocean-rescue-selection-step-label {",
    ]:
        assert selector in css

    # Stage accents pairwise distinct and exposed as a custom property.
    accents = set(EXPECTED_ACCENTS.values())
    assert len(accents) == 3
    for step, color in EXPECTED_ACCENTS.items():
        assert f'[data-selection-step="{step}"]' in css
        assert color in css

    # Selected mission card treatment.
    assert '#ocean-rescue-mission-list button[aria-pressed="true"]' in css
    assert "--ocean-rescue-selection-accent" in css

    # Focus outline rule preserved for mission cards.
    assert "#ocean-rescue-mission-list button:not(:disabled):focus-visible" in css

    # No new animation was added.
    assert "@keyframes ocean-rescue-selection-step" not in css


def test_app_js_selected_state_contract() -> None:
    source = APP_JS.read_text(encoding="utf-8")

    # renderMissionSelect computes aria-pressed from the snapshot.
    assert 'progression.selectedMissionId === mission.id ? "true" : "false"' in source

    # renderMissionSelect owns the section selected-mission-id state.
    assert "data-selected-mission-id" in source
    assert 'section.removeAttribute("data-selected-mission-id")' in source
    assert 'section.setAttribute(\n        "data-selected-mission-id",' in source or (
        'section.setAttribute("data-selected-mission-id",' in source
    )

    # backToMissionSelect no longer owns the removal (render owns final state).
    assert 'missionSection.removeAttribute("data-selected-mission-id")' not in source

    # Typed static catalogs remain structurally unchanged.
    missions = MISSIONS_CATALOG.read_text(encoding="utf-8")
    gups = GUPS_CATALOG.read_text(encoding="utf-8")
    assert (
        '"sea-turtle"' in missions
        and '"crab"' in missions
        and '"young-whale"' in missions
    )
    assert '"gup-c"' in gups and '"gup-i"' in gups and '"gup-x"' in gups
