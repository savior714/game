from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ESM_TRAVEL_SCENE = (
    REPO_ROOT / "domains" / "ocean-rescue" / "src" / "esm" / "travel-scene.js"
)
ACTOR_PRESENTATION = (
    REPO_ROOT
    / "domains"
    / "ocean-rescue"
    / "src"
    / "presentation"
    / "travel-actor-presentation.js"
)


def test_travel_scene_loads_canonical_sprite_actor_presentation():
    adapter = ESM_TRAVEL_SCENE.read_text(encoding="utf-8")
    actor = ACTOR_PRESENTATION.read_text(encoding="utf-8")

    assert 'import "../presentation/travel-actor-presentation.js";' in adapter
    assert "const baseTravelScene = root.TravelScene;" in actor
    assert "new PIXI.Sprite(hullTexture)" in actor
    assert "new PIXI.Sprite(propulsionTexture)" in actor
    assert 'RenderRuntime.getTexture("scene.submarine")' in actor
    assert 'RenderRuntime.getTexture("fx.bubbles")' in actor
    assert 'hullSprite.label = "travel-submarine";' in actor


def test_actor_is_projection_only_and_reuses_canonical_runtime():
    actor = ACTOR_PRESENTATION.read_text(encoding="utf-8")

    assert (
        "const result = baseTravelScene.sync(travelSnapshot, terrainSnapshot);" in actor
    )
    assert "latestTravelSnapshot = travelSnapshot || latestTravelSnapshot;" in actor
    assert "data-travel-scene-gup-actor-mode" in actor
    assert "data-travel-scene-parallax-layers" in actor
    assert "new PIXI.Application" not in actor
    assert 'document.createElement("canvas")' not in actor
    assert "Texture.from(" not in actor
    assert "baseSpeedMultiplier" not in actor
    assert "badge" not in actor.lower()
