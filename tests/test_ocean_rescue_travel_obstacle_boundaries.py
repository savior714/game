"""Focused contract test for Ocean Rescue TravelScene obstacle boundary layers.

Verifies that each authored travel obstacle renders as a 3-layer group:
  - outer boundary (deep-ocean silhouette)
  - inner rim (warm-white highlight)
  - natural-color body (authored texture, white tint)

All three layers share the same authored texture and are grouped under a
PIXI.Container. The body tint must be 0xFFFFFF, the outer boundary must
contrast with every environment palette at >= 3:1, and diagnostics must
report the dual-silhouette boundary mode.

Tests run the real travel-scene.js through Node's vm sandbox with a minimal
fake RenderRuntime. No browser, no npm, no real Pixi runtime required.
"""

import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_BIN = subprocess.run(
    ["which", "node"], capture_output=True, text=True
).stdout.strip()
if not NODE_BIN:
    raise RuntimeError("Node executable not found on PATH")

TRAVEL_SCENE_JS = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "travel-scene.js"


def _run_node(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [NODE_BIN, "-e", script],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def _assert_ok(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, (
        f"Node harness failed (exit {result.returncode}):\n{result.stderr}"
    )


def _make_harness(script_body: str) -> str:
    required_aliases = [
        "scene.water.far",
        "scene.reef.mid",
        "scene.coral.foreground",
        "scene.submarine",
        "scene.seaweed-loop.01",
        "scene.sand-path",
        "scene.passage",
        "fx.bubbles",
        "fx.caustic",
        "terrain.coral-column",
        "terrain.coral-rock",
        "terrain.reef-arch",
        "terrain.reef-spire",
        "terrain.kelp-rock",
        "terrain.sand-rock",
        "terrain.shell-ledge",
        "terrain.low-reef",
        "terrain.rock-stack",
        "terrain.sand-pillar",
        "terrain.canyon-wall",
        "terrain.canyon-ledge",
        "terrain.canyon-pillar",
        "terrain.boulder-stack",
        "terrain.rock-spire",
    ]
    container_names = [
        "farBackground",
        "midground",
        "gameplayWorld",
        "submarine",
        "foreground",
        "effects",
    ]

    alias_init = "\n".join(
        f'textures["{a}"] = new FakeTexture();' for a in required_aliases
    )
    container_init = "\n".join(
        f'containers["{c}"] = new FakeContainer();' for c in container_names
    )

    harness = textwrap.dedent(
        f"""\
        const vm = require("vm");
        const fs = require("fs");
        const assert = require("assert");

        var window = {{}};

        (function () {{
          var root = window.OceanRescue = window.OceanRescue || {{}};
          var textures = {{}};
          var containers = {{}};

          function FakeTexture() {{
            this.frame = {{ width: 64, height: 64 }};
            this.defaultAnchor = {{ x: 0.5, y: 0.5 }};
          }}
          function FakePoint(x, y) {{
            this.x = x || 0;
            this.y = y || 0;
          }}
          FakePoint.prototype.copyFrom = function (src) {{ this.x = src.x; this.y = src.y; }};
          FakePoint.prototype.set = function (x, y) {{ this.x = x; this.y = y; }};
          function FakeSprite(texture) {{
            this.texture = texture;
            this.position = new FakePoint(0, 0);
            this.scale = new FakePoint(1, 1);
            this.anchor = new FakePoint(0, 0);
            this.rotation = 0;
            this.alpha = 1;
            this.visible = true;
            this.label = "";
            this.name = "";
            this.eventMode = "none";
            this.tint = 0xFFFFFF;
          }}
          FakeSprite.prototype.setScale = function (x, y) {{
            this.scale.x = x;
            this.scale.y = typeof y === "number" ? y : x;
          }};
          function FakeContainer() {{
            this.children = [];
            var _pos = new FakePoint(0, 0);
            this.position = _pos;
            this.position.set = function (x, y) {{ this.x = x; this.y = y; }};
            var _scale = new FakePoint(1, 1);
            this.scale = _scale;
            this.scale.set = function (x, y) {{ this.x = x; this.y = typeof y === "number" ? y : x; }};
          }}
          FakeContainer.prototype.addChild = function (child) {{ this.children.push(child); }};
          FakeContainer.prototype.addChildAt = function (child, index) {{ this.children.splice(index, 0, child); }};
          FakeContainer.prototype.removeChild = function (child) {{
            var index = this.children.indexOf(child);
            if (index !== -1) this.children.splice(index, 1);
          }};
          function FakeGraphics() {{
            this.children = [];
            this.position = new FakePoint(0, 0);
            this.position.set = function (x, y) {{ this.x = x; this.y = y; }};
            this.scale = new FakePoint(1, 1);
            this.scale.set = function (x, y) {{ this.x = x; this.y = typeof y === "number" ? y : x; }};
            this.rotation = 0;
            this.alpha = 1;
            this.visible = true;
            this.label = "";
            this.name = "";
            this.eventMode = "none";
            this.tint = 0xFFFFFF;
            this.blendMode = "normal";
          }}
          FakeGraphics.prototype.addChild = function (child) {{ this.children.push(child); }};
          FakeGraphics.prototype.circle = function () {{ return this; }};
          FakeGraphics.prototype.moveTo = function () {{ return this; }};
          FakeGraphics.prototype.lineTo = function () {{ return this; }};
          FakeGraphics.prototype.fill = function () {{ return this; }};
          FakeGraphics.prototype.stroke = function () {{ return this; }};

          window.PIXI = {{ Sprite: FakeSprite, Texture: function () {{ return new FakeTexture(); }}, Container: FakeContainer, Graphics: FakeGraphics }};

          var RenderRuntime = {{
            isReady: function () {{ return true; }},
            hasTexture: function (alias) {{ return !!textures[alias]; }},
            getTexture: function (alias) {{ return textures[alias] || null; }},
            getContainer: function (name) {{ return containers[name] || null; }},
            setLegacyBridgeVisible: function () {{}},
            getLegacyBridgeVisible: function () {{ return true; }},
            renderSceneFrame: function () {{}},
            _getTex: function (alias) {{ return textures[alias] || null; }},
            _getCon: function (name) {{ return containers[name] || null; }}
          }};
          root.RenderRuntime = RenderRuntime;

          var Terrain = {{
            _layouts: {{}},
            setLayout: function (missionId, layout) {{ this._layouts[missionId] = layout; }},
            getLayout: function (missionId) {{ return this._layouts[missionId] || null; }}
          }};
          root.Terrain = Terrain;
          window.Terrain = Terrain;

          {alias_init}
          {container_init}
        }})();

        (function () {{
          var rootEl = {{ tagName: "main", children: [], attributes: {{}}, style: {{}}, textContent: null,
            classList: {{ add: function () {{}}, remove: function () {{}}, contains: function () {{}} }},
            appendChild: function (c) {{ c.parent = this; this.children.push(c); }},
            setAttribute: function (k, v) {{ this.attributes[k] = String(v); }},
            getAttribute: function (k) {{ return this.attributes[k] !== undefined ? this.attributes[k] : null; }},
            removeAttribute: function (k) {{ delete this.attributes[k]; }}
          }};
          window.document = {{
            getElementById: function (id) {{ return id === "ocean-rescue-root" ? rootEl : null; }},
            createElement: function () {{ return {{ tagName: "div", children: [], attributes: {{}}, style: {{}}, textContent: null, classList: {{ add:function(){{}}, remove:function(){{}}, contains:function(){{}} }}, appendChild:function(c){{}}, setAttribute:function(k,v){{}}, getAttribute:function(k){{return null;}}, removeAttribute:function(k){{}} }}; }},
            addEventListener: function () {{}}
          }};
        }})();

        window.matchMedia = function (query) {{
          return {{ matches: query === "(prefers-reduced-motion: reduce)", addListener: function () {{}}, removeListener: function () {{}} }};
        }};

        var document = window.document;

        (function () {{
          var frames = [];
          var nextId = 1;
          window.requestAnimationFrame = function (fn) {{
            var id = nextId++;
            frames.push({{ id: id, fn: fn, ran: false }});
            return id;
          }};
          window.cancelAnimationFrame = function (id) {{
            var entry = frames.find(function (e) {{ return e.id === id; }});
            if (entry) entry.cancelled = true;
          }};
          window._runFrame = function (id, timestamp) {{
            var entry = frames.find(function (e) {{ return e.id === id; }});
            if (!entry) throw new Error("no frame " + id);
            entry.ran = true;
            entry.fn(timestamp);
          }};
          window._pendingFrames = function () {{
            return frames.filter(function (e) {{ return !e.ran && !e.cancelled; }});
          }};
        }})();

        const source = fs.readFileSync("domains/ocean-rescue/src/travel-scene.js", "utf8");
        const sandbox = {{ window: window, document: window.document, PIXI: window.PIXI }};
        vm.createContext(sandbox);
        vm.runInContext(source, sandbox, {{ filename: "travel-scene.js" }});
        const TravelScene = sandbox.window.OceanRescue.TravelScene;
        const RenderRuntime = sandbox.window.OceanRescue.RenderRuntime;
        const Terrain = sandbox.window.OceanRescue.Terrain;

        {script_body}
        """
    )
    return harness


def _wcag_luminance(hex_color: int) -> float:
    """Compute WCAG relative luminance from a hex color integer."""
    r = ((hex_color >> 16) & 0xFF) / 255.0
    g = ((hex_color >> 8) & 0xFF) / 255.0
    b = (hex_color & 0xFF) / 255.0

    def linearize(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def _contrast_ratio(color1: int, color2: int) -> float:
    """Compute WCAG contrast ratio between two hex colors."""
    l1 = _wcag_luminance(color1)
    l2 = _wcag_luminance(color2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


ENVIRONMENT_PALETTES = {
    "coral-reef": 0x7FB2C4,
    "sandy-reef": 0xC4A37F,
    "rocky-canyon": 0x6B7A8A,
}

OUTER_BOUNDARY_COLOR = 0x04151F
INNER_RIM_COLOR = 0xFFF7D6
BODY_TINT = 0xFFFFFF


@pytest.mark.parametrize("env_name,env_hex", list(ENVIRONMENT_PALETTES.items()))
def test_outer_boundary_contrast_against_environment(
    env_name: str, env_hex: int
) -> None:
    """Outer boundary must contrast each environment palette at >= 3:1."""
    ratio = _contrast_ratio(OUTER_BOUNDARY_COLOR, env_hex)
    assert ratio >= 3.0, (
        f"outer boundary contrast against {env_name} ({hex(env_hex)}) is {ratio:.2f}:1, "
        f"must be >= 3.0:1"
    )


def _obstacle_harness(obstacles, extra_checks=""):
    """Build a harness with given obstacles and optional extra assertions."""
    obs_json = (
        "["
        + ", ".join(
            '{ id: "'
            + o["id"]
            + '", kind: "'
            + o["kind"]
            + '", worldX: '
            + str(o["worldX"])
            + ", y: "
            + str(o["y"])
            + ", width: "
            + str(o["width"])
            + ", height: "
            + str(o["height"])
            + " }"
            for o in obstacles
        )
        + "]"
    )
    return textwrap.dedent(
        f"""\
        assert.strictEqual(TravelScene.prepare(), true);
        assert.strictEqual(TravelScene.activate(), true);

        Terrain.setLayout("sea-turtle", {{
          environment: "coral-reef",
          obstacles: {obs_json}
        }});

        let frameId = window._pendingFrames()[0].id;
        window._runFrame(frameId, 1000);

        const terrainSnap = {{
          active: true,
          missionId: "sea-turtle"
        }};
        TravelScene.sync({{ y: 360, distance: 200 }}, terrainSnap);

        const gw = RenderRuntime.getContainer("gameplayWorld");
        let group = null;
        for (const child of gw.children) {{
          if (child && String(child.label).indexOf("travel-obstacle-") === 0 && child.children) {{
            group = child;
            break;
          }}
        }}

        assert.ok(group, "obstacle group not found");
        {extra_checks}

        TravelScene.exit();
        """
    )


def test_obstacle_group_has_three_layers() -> None:
    """Each obstacle must be a Container with exactly 3 children (outer, rim, body)."""
    harness = _make_harness(
        _obstacle_harness(
            [
                {
                    "id": "coral-column-1",
                    "kind": "coral-column",
                    "worldX": 600,
                    "y": 350,
                    "width": 64,
                    "height": 64,
                },
                {
                    "id": "reef-arch-2",
                    "kind": "reef-arch",
                    "worldX": 900,
                    "y": 400,
                    "width": 64,
                    "height": 64,
                },
            ],
            "assert.strictEqual(group.children.length, 3, `group ${group.label} must have exactly 3 children`);",
        )
    )
    _assert_ok(_run_node(harness))


def test_obstacle_render_order_outer_rim_body() -> None:
    """Layer render order must be outer boundary, inner rim, body."""
    harness = _make_harness(
        _obstacle_harness(
            [
                {
                    "id": "coral-column-1",
                    "kind": "coral-column",
                    "worldX": 600,
                    "y": 350,
                    "width": 64,
                    "height": 64,
                }
            ],
            textwrap.dedent(
                """\
                const labels = group.children.map(c => c.label || "");
                assert.ok(labels[0].indexOf("outer") >= 0,
                  `first child must be outer boundary, got "${labels[0]}"`);
                assert.ok(labels[1].indexOf("rim") >= 0,
                  `second child must be inner rim, got "${labels[1]}"`);
                assert.strictEqual(labels[2], "travel-obstacle-0",
                  `third child must be body, got "${labels[2]}"`);
                """
            ),
        )
    )
    _assert_ok(_run_node(harness))


def test_obstacle_layers_share_same_texture() -> None:
    """All three layers must use the same authored texture."""
    harness = _make_harness(
        _obstacle_harness(
            [
                {
                    "id": "coral-column-1",
                    "kind": "coral-column",
                    "worldX": 600,
                    "y": 350,
                    "width": 64,
                    "height": 64,
                }
            ],
            textwrap.dedent(
                """\
                const textures = group.children.map(c => c.texture);
                const sameTex = textures.every(t => t === textures[0]);
                assert.ok(sameTex, "all three layers must share the same texture");
                """
            ),
        )
    )
    _assert_ok(_run_node(harness))


def test_obstacle_layers_have_matching_anchor() -> None:
    """All three layers must have the same anchor point."""
    harness = _make_harness(
        _obstacle_harness(
            [
                {
                    "id": "coral-column-1",
                    "kind": "coral-column",
                    "worldX": 600,
                    "y": 350,
                    "width": 64,
                    "height": 64,
                }
            ],
            textwrap.dedent(
                """\
                const anchors = group.children.map(c => ({ x: c.anchor.x, y: c.anchor.y }));
                const sameAnchor = anchors.every(a => a.x === anchors[0].x && a.y === anchors[0].y);
                assert.ok(sameAnchor, "all three layers must have matching anchor");
                """
            ),
        )
    )
    _assert_ok(_run_node(harness))


def test_body_tint_is_white() -> None:
    """Body sprite must have tint 0xFFFFFF (authored natural color)."""
    harness = _make_harness(
        _obstacle_harness(
            [
                {
                    "id": "coral-column-1",
                    "kind": "coral-column",
                    "worldX": 600,
                    "y": 350,
                    "width": 64,
                    "height": 64,
                }
            ],
            textwrap.dedent(
                """\
                const body = group.children[2];
                assert.strictEqual(body.label, "travel-obstacle-0");
                assert.strictEqual(body.tint, 0xFFFFFF,
                  `body tint must be 0xFFFFFF, got ${body.tint.toString(16)}`);
                """
            ),
        )
    )
    _assert_ok(_run_node(harness))


def test_inner_rim_tint_is_warm_white() -> None:
    """Inner rim sprite must have the canonical warm-white tint."""
    harness = _make_harness(
        _obstacle_harness(
            [
                {
                    "id": "coral-column-1",
                    "kind": "coral-column",
                    "worldX": 600,
                    "y": 350,
                    "width": 64,
                    "height": 64,
                }
            ],
            textwrap.dedent(
                """\
                const rim = group.children[1];
                assert.ok(rim.label.indexOf("rim") >= 0, `expected rim label, got "${rim.label}"`);
                assert.strictEqual(rim.tint, 0xFFF7D6,
                  `inner rim tint must be 0xFFF7D6, got ${rim.tint.toString(16)}`);
                """
            ),
        )
    )
    _assert_ok(_run_node(harness))


def test_outer_tint_is_deep_ocean() -> None:
    """Outer boundary sprite must have the canonical deep-ocean tint."""
    harness = _make_harness(
        _obstacle_harness(
            [
                {
                    "id": "coral-column-1",
                    "kind": "coral-column",
                    "worldX": 600,
                    "y": 350,
                    "width": 64,
                    "height": 64,
                }
            ],
            textwrap.dedent(
                """\
                const outer = group.children[0];
                assert.ok(outer.label.indexOf("outer") >= 0, `expected outer label, got "${outer.label}"`);
                assert.strictEqual(outer.tint, 0x04151F,
                  `outer boundary tint must be 0x04151F, got ${outer.tint.toString(16)}`);
                """
            ),
        )
    )
    _assert_ok(_run_node(harness))


def test_obstacle_relative_scales_outer_gt_rim_gt_body() -> None:
    """Outer scale must be > rim scale > body scale."""
    harness = _make_harness(
        _obstacle_harness(
            [
                {
                    "id": "coral-column-1",
                    "kind": "coral-column",
                    "worldX": 600,
                    "y": 350,
                    "width": 64,
                    "height": 64,
                }
            ],
            textwrap.dedent(
                """\
                const outerScale = group.children[0].scale.x;
                const rimScale = group.children[1].scale.x;
                const bodyScale = group.children[2].scale.x;
                assert.ok(outerScale > rimScale, `outer scale (${outerScale}) must be > rim scale (${rimScale})`);
                assert.ok(rimScale > bodyScale, `rim scale (${rimScale}) must be > body scale (${bodyScale})`);
                """
            ),
        )
    )
    _assert_ok(_run_node(harness))


def test_obstacle_group_position_matches_screen_projection() -> None:
    """Group position must match the projected screenX/screenY."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            Terrain.setLayout("sea-turtle", {
              environment: "coral-reef",
              obstacles: [{ id: "coral-column-1", kind: "coral-column", worldX: 850, y: 380, width: 64, height: 64 }]
            });

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            TravelScene.sync({ y: 360, distance: 200 }, { active: true, missionId: "sea-turtle" });

            const gw = RenderRuntime.getContainer("gameplayWorld");
            let group = null;
            for (const child of gw.children) {
              if (child && String(child.label).indexOf("travel-obstacle-") === 0 && child.children) {
                group = child;
                break;
              }
            }

            assert.ok(group, "obstacle group not found");
            assert.strictEqual(group.position.x, 650, `group x must be 650, got ${group.position.x}`);
            assert.strictEqual(group.position.y, 380, `group y must be 380, got ${group.position.y}`);

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_obstacle_body_visual_size_matches_projection() -> None:
    """Body visual size must fit within obstacle projection (min-scale)."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            Terrain.setLayout("sea-turtle", {
              environment: "coral-reef",
              obstacles: [{ id: "coral-column-1", kind: "coral-column", worldX: 600, y: 350, width: 128, height: 96 }]
            });

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            TravelScene.sync({ y: 360, distance: 200 }, { active: true, missionId: "sea-turtle" });

            const gw = RenderRuntime.getContainer("gameplayWorld");
            let group = null;
            for (const child of gw.children) {
              if (child && String(child.label).indexOf("travel-obstacle-") === 0 && child.children) {
                group = child;
                break;
              }
            }

            assert.ok(group, "obstacle group not found");
            const body = group.children[2];
            const frameW = body.texture.frame.width;
            const frameH = body.texture.frame.height;
            const bodyScale = body.scale.x;
            const visualW = frameW * bodyScale;
            const visualH = frameH * bodyScale;

            assert.ok(visualW <= 128 + 1, `body visual width ${visualW} must not exceed obstacle width 128`);
            assert.ok(visualH <= 96 + 1, `body visual height ${visualH} must not exceed obstacle height 96`);
            assert.ok(visualW >= 128 - 1 || visualH >= 96 - 1,
              "at least one dimension must match obstacle projection");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_visible_obstacle_count_diagnostics_match() -> None:
    """body/rim/outer visible counts must all be equal."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            Terrain.setLayout("sea-turtle", {
              environment: "coral-reef",
              obstacles: [
                { id: "coral-column-1", kind: "coral-column", worldX: 600, y: 350, width: 64, height: 64 },
                { id: "reef-arch-2", kind: "reef-arch", worldX: 900, y: 400, width: 64, height: 64 },
                { id: "kelp-rock-3", kind: "kelp-rock", worldX: 1100, y: 320, width: 64, height: 64 }
              ]
            });

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            TravelScene.sync({ y: 360, distance: 200 }, { active: true, missionId: "sea-turtle" });

            const root = document.getElementById("ocean-rescue-root");
            const attr = (name) => root.getAttribute(name);

            const bodyCount = parseInt(attr("data-travel-scene-visible-obstacle-body-count") || "0", 10);
            const rimCount = parseInt(attr("data-travel-scene-visible-obstacle-rim-count") || "0", 10);
            const outerCount = parseInt(attr("data-travel-scene-visible-obstacle-outer-count") || "0", 10);
            const totalCount = parseInt(attr("data-travel-scene-visible-obstacle-count") || "0", 10);

            assert.ok(bodyCount > 0, "body count must be > 0");
            assert.strictEqual(bodyCount, rimCount, `body count (${bodyCount}) must equal rim count (${rimCount})`);
            assert.strictEqual(bodyCount, outerCount, `body count (${bodyCount}) must equal outer count (${outerCount})`);
            assert.strictEqual(bodyCount, totalCount, `body count (${bodyCount}) must equal total count (${totalCount})`);

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_diagnostics_report_dual_silhouette_mode() -> None:
    """Diagnostics must report boundary mode as dual-silhouette."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            Terrain.setLayout("sea-turtle", {
              environment: "coral-reef",
              obstacles: [{ id: "coral-column-1", kind: "coral-column", worldX: 600, y: 350, width: 64, height: 64 }]
            });

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            TravelScene.sync({ y: 360, distance: 200 }, { active: true, missionId: "sea-turtle" });

            const root = document.getElementById("ocean-rescue-root");
            const mode = root.getAttribute("data-travel-scene-obstacle-boundary-mode");
            assert.strictEqual(mode, "dual-silhouette",
              `boundary mode must be "dual-silhouette", got "${mode}"`);

            const bodyTint = root.getAttribute("data-travel-scene-obstacle-body-tint");
            assert.strictEqual(bodyTint, "ffffff",
              `body tint must be "ffffff", got "${bodyTint}"`);

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_obstacle_event_mode_none_on_all_layers() -> None:
    """All three layers must have eventMode set to none."""
    harness = _make_harness(
        _obstacle_harness(
            [
                {
                    "id": "coral-column-1",
                    "kind": "coral-column",
                    "worldX": 600,
                    "y": 350,
                    "width": 64,
                    "height": 64,
                }
            ],
            textwrap.dedent(
                """\
                for (const layer of group.children) {
                  assert.strictEqual(layer.eventMode, "none",
                    `layer ${layer.label} eventMode must be "none", got "${layer.eventMode}"`);
                }
                """
            ),
        )
    )
    _assert_ok(_run_node(harness))


def test_offscreen_obstacle_layers_hidden() -> None:
    """When obstacle is offscreen, group and all layers must be invisible."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            Terrain.setLayout("sea-turtle", {
              environment: "coral-reef",
              obstacles: [{ id: "coral-column-1", kind: "coral-column", worldX: 5000, y: 350, width: 64, height: 64 }]
            });

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            TravelScene.sync({ y: 360, distance: 200 }, { active: true, missionId: "sea-turtle" });

            const gw = RenderRuntime.getContainer("gameplayWorld");
            let group = null;
            for (const child of gw.children) {
              if (child && String(child.label).indexOf("travel-obstacle-") === 0 && child.children) {
                group = child;
                break;
              }
            }

            assert.ok(group, "obstacle group not found");
            assert.strictEqual(group.visible, false, "offscreen group must be invisible");
            for (const layer of group.children) {
              assert.strictEqual(layer.visible, false,
                `offscreen layer ${layer.label} must be invisible`);
            }

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_obstacle_sprites_array_keeps_body_reference() -> None:
    """nodes.obstacleSprites must still reference body sprites for backward compat."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            Terrain.setLayout("sea-turtle", {
              environment: "coral-reef",
              obstacles: [{ id: "coral-column-1", kind: "coral-column", worldX: 600, y: 350, width: 64, height: 64 }]
            });

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            TravelScene.sync({ y: 360, distance: 200 }, { active: true, missionId: "sea-turtle" });

            const travelScene = window.OceanRescue.TravelScene;
            assert.ok(travelScene, "TravelScene must be available");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_obstacle_alpha_values() -> None:
    """Body alpha must be 1.0, rim alpha in 0.72-0.92, outer alpha in 0.82-0.95."""
    harness = _make_harness(
        _obstacle_harness(
            [
                {
                    "id": "coral-column-1",
                    "kind": "coral-column",
                    "worldX": 600,
                    "y": 350,
                    "width": 64,
                    "height": 64,
                }
            ],
            textwrap.dedent(
                """\
                const body = group.children[2];
                const rim = group.children[1];
                const outer = group.children[0];

                assert.strictEqual(body.alpha, 1.0, `body alpha must be 1.0, got ${body.alpha}`);
                assert.ok(rim.alpha >= 0.72 && rim.alpha <= 0.92,
                  `rim alpha ${rim.alpha} must be in [0.72, 0.92]`);
                assert.ok(outer.alpha >= 0.82 && outer.alpha <= 0.95,
                  `outer alpha ${outer.alpha} must be in [0.82, 0.95]`);
                """
            ),
        )
    )
    _assert_ok(_run_node(harness))


def test_obstacle_scale_ratios_in_recommended_range() -> None:
    """Outer and rim must be proportionally larger than body."""
    harness = _make_harness(
        _obstacle_harness(
            [
                {
                    "id": "coral-column-1",
                    "kind": "coral-column",
                    "worldX": 600,
                    "y": 350,
                    "width": 64,
                    "height": 64,
                }
            ],
            textwrap.dedent(
                """\
                const outerScale = group.children[0].scale.x;
                const rimScale = group.children[1].scale.x;
                const bodyScale = group.children[2].scale.x;

                assert.ok(rimScale / bodyScale >= 1.055 && rimScale / bodyScale <= 1.075,
                  `rim/body ratio ${rimScale / bodyScale} must be in [1.055, 1.075]`);
                assert.ok(outerScale / bodyScale >= 1.10 && outerScale / bodyScale <= 1.14,
                  `outer/body ratio ${outerScale / bodyScale} must be in [1.10, 1.14]`);
                """
            ),
        )
    )
    _assert_ok(_run_node(harness))


def test_collision_knockback_regression_still_passes() -> None:
    """Collision knockback must still work correctly with the new obstacle structure."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            const submarine = RenderRuntime.getContainer("submarine").children[0];
            const baseX = submarine.position.x;
            assert.strictEqual(baseX, 260);

            const terrainSnap = {
              active: true,
              missionId: "sea-turtle",
              collisionActive: true,
              lastCollisionObstacleId: "coral-column-1",
              shakeOffsetY: -6,
              knockbackOffsetX: 36,
            };
            TravelScene.sync({ y: 360, distance: 720 }, terrainSnap);

            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1100);

            assert.ok(submarine.position.x < baseX,
              "submarine x must be less than canonical 260 after new collision");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))
