"""Focused contract for the first-time crew (Octonaut) selection presentation.

The profile step must let a child recognise each Octonaut by character art,
name, role and a one-line skill description instead of a bare name button.

Proof tiers used here (no browser required):

- static markup contract: the template ships three portrait symbols and the
  crew panel/action structure that the standalone artifact also carries;
- rendering contract: the legacy ordered-script renderer and the typed
  controller both build the same card structure;
- behaviour contract: the legacy renderer keeps the existing selection model
  (``aria-pressed``, disabled Continue, catalog order) while rendering art;
- style contract: the crew card, portrait and focus/selected treatments exist
  in the canonical stylesheet and are shipped in the built artifact.
"""

from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from test_ocean_rescue_profile_choice import (  # noqa: E402
    _FULL_BOOTSTRAP,
    _assert_node_ok,
    _run_node,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "domains" / "ocean-rescue" / "src"
TEMPLATE = SRC_DIR / "index.template.html"
STYLE = SRC_DIR / "style.css"
APP_JS = SRC_DIR / "app.js"
CONTROLLER_TS = SRC_DIR / "controllers" / "profile-mission-selection.ts"
ARTIFACT = REPO_ROOT / "ocean-rescue" / "index.html"

ANIMALS = ("arctic-fox", "beaver", "red-panda")
ROLES = {
    "arctic-fox": ("Ice Scout", "Sniffs out the safest path under the ice."),
    "beaver": ("Master Builder", "Fixes nets, hulls and anything that cracks."),
    "red-panda": ("High Climber", "Spots animals hiding in the kelp and rocks."),
}


# ── static markup contract ─────────────────────────────────────────────────


def test_template_ships_character_portraits_and_crew_panel() -> None:
    html = TEMPLATE.read_text(encoding="utf-8")

    assert 'id="ocean-rescue-profile-portrait-sprite"' in html
    for animal in ANIMALS:
        assert f'id="ocean-rescue-portrait-{animal}"' in html, (
            f"missing portrait symbol for {animal}"
        )

    assert 'class="ocean-rescue-crew-panel"' in html
    assert 'class="ocean-rescue-crew-scene"' in html
    assert 'class="ocean-rescue-crew-actions"' in html
    assert 'class="ocean-rescue-crew-lead"' in html

    # Headings and the selection-step marker contract stay intact.
    assert 'id="ocean-rescue-profile-choice-title">Choose your Octonaut' in html
    assert html.count('data-selection-step="profile"') == 1


def test_portrait_symbols_are_well_formed_svg() -> None:
    import xml.etree.ElementTree as ET

    html = TEMPLATE.read_text(encoding="utf-8")
    start = html.index('      <svg\n        id="ocean-rescue-profile-portrait-sprite"')
    end = html.index("      </svg>", start) + len("      </svg>")
    root = ET.fromstring(html[start:end])

    symbols = [node for node in root if node.tag.endswith("symbol")]
    assert [node.get("id") for node in symbols] == [
        f"ocean-rescue-portrait-{animal}" for animal in ANIMALS
    ]
    for symbol in symbols:
        assert symbol.get("viewBox") == "0 0 200 200"
        group = next(node for node in symbol if node.tag.endswith("g"))
        # art plus the circular backdrop is never a single empty group
        assert len(list(group)) > 10


def test_artifact_carries_the_same_crew_presentation() -> None:
    artifact = ARTIFACT.read_text(encoding="utf-8")
    for animal in ANIMALS:
        assert f'id="ocean-rescue-portrait-{animal}"' in artifact, (
            "the standalone artifact must inline the portrait sprite"
        )
    assert ".ocean-rescue-crew-card-portrait" in artifact
    assert 'class="ocean-rescue-crew-panel"' in artifact


# ── rendering contract ─────────────────────────────────────────────────────


def test_renderers_build_portrait_cards_with_roles() -> None:
    for path in (APP_JS, CONTROLLER_TS):
        source = path.read_text(encoding="utf-8")
        assert "ocean-rescue-crew-card-portrait" in source, path
        assert "ocean-rescue-crew-card-name" in source, path
        assert "ocean-rescue-crew-card-role" in source, path
        assert "ocean-rescue-crew-card-line" in source, path
        assert "ocean-rescue-crew-card-check" in source, path
        assert 'href="#ocean-rescue-portrait-' in source, path
        for animal, (role, line) in ROLES.items():
            assert animal in source, path
            assert role in source, path
            assert line in source, path


def test_legacy_renderer_outputs_recognisable_crew_cards() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const { document, profileAnimalList, profileContinue } = dom;
        const { Profile, App } = loadModules(document, makeStorage());
        document.domLoadedHandler();
        App.boot();

        assert.strictEqual(profileAnimalList.children.length, 3);
        const expected = {
          "arctic-fox": ["Arctic fox", "Ice Scout"],
          beaver: ["Beaver", "Master Builder"],
          "red-panda": ["Red panda", "High Climber"],
        };

        profileAnimalList.children.forEach((button) => {
          const id = button.attributes["data-profile-animal-id"];
          assert.ok(Object.prototype.hasOwnProperty.call(expected, id), id);

          const portrait = button.children[0];
          assert.strictEqual(
            portrait.className,
            "ocean-rescue-crew-card-portrait"
          );
          assert.strictEqual(portrait.attributes["aria-hidden"], "true");
          assert.ok(
            portrait.innerHTML.indexOf(
              'href="#ocean-rescue-portrait-' + id + '"'
            ) !== -1,
            "portrait must reference the inline symbol for " + id
          );
          assert.ok(portrait.innerHTML.indexOf("<svg") !== -1);

          const body = button.children[1];
          assert.strictEqual(body.className, "ocean-rescue-crew-card-body");
          const name = body.children[0];
          const role = body.children[1];
          const line = body.children[2];
          assert.strictEqual(name.className, "ocean-rescue-crew-card-name");
          assert.strictEqual(role.className, "ocean-rescue-crew-card-role");
          assert.strictEqual(line.className, "ocean-rescue-crew-card-line");
          assert.strictEqual(name.textContent, expected[id][0]);
          assert.strictEqual(role.textContent, expected[id][1]);
          assert.ok(line.textContent.length > 12, "each card keeps a skill line");

          const check = button.children[2];
          assert.strictEqual(check.className, "ocean-rescue-crew-card-check");
          assert.strictEqual(check.attributes["aria-hidden"], "true");

          assert.strictEqual(
            button.attributes["aria-label"],
            expected[id][0] + ", " + expected[id][1]
          );
          assert.strictEqual(button.attributes["aria-pressed"], "false");
        });

        assert.strictEqual(profileContinue.disabled, true);
        profileAnimalList.children[2].click();
        assert.strictEqual(
          profileAnimalList.children[2].attributes["aria-pressed"],
          "true"
        );
        assert.strictEqual(
          profileAnimalList.children[0].attributes["aria-pressed"],
          "false"
        );
        assert.strictEqual(profileContinue.disabled, false);
        assert.strictEqual(Profile.getSnapshot().selectedAnimalId, "red-panda");
        """
    )
    _assert_node_ok(_run_node(harness))


def test_legacy_renderer_keeps_catalog_order_and_confirm_flow() -> None:
    harness = _FULL_BOOTSTRAP + textwrap.dedent(
        """\
        const dom = makeBootDom();
        const { document, profileSection, profileAnimalList,
                profileContinue, missionSection, missionList } = dom;
        const { State, Profile, App } = loadModules(document, makeStorage());
        document.domLoadedHandler();
        App.boot();

        assert.deepStrictEqual(
          profileAnimalList.children.map(
            (b) => b.attributes["data-profile-animal-id"]
          ),
          ["arctic-fox", "beaver", "red-panda"]
        );

        profileAnimalList.children[0].click();
        profileContinue.click();
        assert.strictEqual(State.getSnapshot().phase, "MISSION_SELECT");
        assert.strictEqual(profileSection.style.display, "none");
        assert.strictEqual(missionSection.style.display, "block");
        assert.strictEqual(missionList.children.length, 3);
        assert.strictEqual(Profile.getSnapshot().chosenAnimalId, "arctic-fox");
        """
    )
    _assert_node_ok(_run_node(harness))


# ── style contract ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "selector",
    [
        ".ocean-rescue-crew-panel {",
        ".ocean-rescue-crew-scene {",
        ".ocean-rescue-crew-card-portrait {",
        ".ocean-rescue-crew-card-name {",
        ".ocean-rescue-crew-card-role {",
        ".ocean-rescue-crew-card-line {",
        ".ocean-rescue-crew-card-check {",
        ".ocean-rescue-crew-actions {",
    ],
)
def test_stylesheet_defines_crew_presentation_pieces(selector: str) -> None:
    css = STYLE.read_text(encoding="utf-8")
    assert selector in css


def test_crew_card_selection_and_focus_states_are_visible() -> None:
    css = STYLE.read_text(encoding="utf-8")

    assert '#ocean-rescue-profile-animal-list button[aria-pressed="true"] {' in css, (
        "selected crew card must have a dedicated treatment"
    )
    assert (
        '#ocean-rescue-profile-animal-list button[aria-pressed="true"]\n'
        "  .ocean-rescue-crew-card-portrait {" in css
    ), "selected portrait must get its own highlight"
    assert (
        "#ocean-rescue-profile-animal-list button:not(:disabled):focus-visible {" in css
    ), "keyboard focus must stay visible"

    # Primary control keeps the 48px touch floor.
    continue_block = css[css.index("#ocean-rescue-profile-continue {") :]
    continue_block = continue_block[: continue_block.index("}")]
    assert "min-height: 48px" in continue_block

    # The grid collapses to one column on narrow/portrait screens.
    portrait_block = css[css.index("@media (orientation: portrait)") :]
    assert "grid-template-columns: minmax(0, 1fr)" in portrait_block

    # Reduced motion is honoured for the new transitions.
    reduce_block = css[css.index("@media (prefers-reduced-motion: reduce)") :]
    assert "transition: none" in reduce_block


def test_artwork_uses_palette_ink_outlines() -> None:
    html = TEMPLATE.read_text(encoding="utf-8")
    start = html.index('      <svg\n        id="ocean-rescue-profile-portrait-sprite"')
    end = html.index("      </svg>", start)
    sprite = html[start:end]

    # Same ink outline and rescue-suit yellow as the approved character art.
    assert 'stroke="#243746"' in sprite
    assert 'fill="#f2b53c"' in sprite
    assert "asset://" not in sprite
    assert re.search(r"https?://www\.w3\.org/2000/svg", sprite)
