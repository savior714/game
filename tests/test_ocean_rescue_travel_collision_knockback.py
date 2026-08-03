"""Focused contract test for Ocean Rescue TravelScene collision knockback.

Verifies that TravelScene applies a visible knockback displacement to the
submarine display object when terrain reports an active collision, and that
the submarine eases back to its canonical base x over a bounded duration.

Tests run the real travel-scene.js through Node's vm sandbox with a minimal
fake RenderRuntime that tracks setPosition calls on the submarine sprite.
No browser, no npm, no real Pixi runtime required.
"""

import subprocess
import textwrap
from pathlib import Path

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
          }}
          FakeSprite.prototype.setScale = function (x, y) {{
            this.scale.x = x;
            this.scale.y = typeof y === "number" ? y : x;
          }};
          function FakeContainer() {{
            this.children = [];
            this.position = new FakePoint(0, 0);
            this.scale = new FakePoint(1, 1);
            this.rotation = 0;
            this.alpha = 1;
            this.visible = true;
            this.label = "";
            this.name = "";
            this.eventMode = "none";
          }}
          FakeContainer.prototype.addChild = function (child) {{ this.children.push(child); }};
          FakeContainer.prototype.addChildAt = function (child, index) {{ this.children.splice(index, 0, child); }};
          FakeContainer.prototype.removeChild = function (child) {{
            var index = this.children.indexOf(child);
            if (index !== -1) this.children.splice(index, 1);
          }};
          function FakeGraphics() {{
            this.position = new FakePoint(0, 0);
            this.scale = new FakePoint(1, 1);
            this.rotation = 0;
            this.alpha = 1;
            this.visible = true;
            this.tint = 0xFFFFFF;
            this.blendMode = "normal";
            this.label = "";
            this.name = "";
            this.eventMode = "none";
            this.children = [];
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
        const sandbox = {{ window: window, PIXI: window.PIXI, document: window.document }};
        vm.createContext(sandbox);
        vm.runInContext(source, sandbox, {{ filename: "travel-scene.js" }});
        const TravelScene = sandbox.window.OceanRescue.TravelScene;
        const RenderRuntime = sandbox.window.OceanRescue.RenderRuntime;

        {script_body}
        """
    )
    return harness


def test_travel_scene_submarine_x_is_canonical_at_rest():
    """Submarine x must be 260 when there is no collision."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            const submarine = RenderRuntime.getContainer("submarine").children[0];
            assert.strictEqual(submarine.position.x, 260);
            assert.strictEqual(typeof submarine.position.y, "number");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_travel_scene_collision_moves_submarine_after_fix():
    """GREEN: collisionActive snapshot must push submarine x below canonical 260."""
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


def test_travel_scene_new_collision_triggers_knockback():
    """A fresh collision obstacle id must produce a leftward displacement."""
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


def test_travel_scene_knockback_eases_back_to_base():
    """Submarine must return to canonical x within the bounded envelope duration."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            const submarine = RenderRuntime.getContainer("submarine").children[0];
            const baseX = submarine.position.x;

            const terrainSnap = {
              active: true,
              missionId: "sea-turtle",
              collisionActive: true,
              lastCollisionObstacleId: "coral-column-1",
              shakeOffsetY: -6,
              knockbackOffsetX: 36,
            };
            TravelScene.sync({ y: 360, distance: 720 }, terrainSnap);

            var t = 1100;
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, t);
            t += 60;

            const displacement = baseX - submarine.position.x;
            assert.ok(displacement > 0, "displacement must be positive during envelope");

            for (let i = 0; i < 30; i += 1) {
              frameId = window._pendingFrames()[0].id;
              window._runFrame(frameId, t);
              t += 60;
            }

            const finalDisplacement = Math.abs(baseX - submarine.position.x);
            assert.ok(finalDisplacement < 2,
              "submarine must have returned to within 2px of base x after envelope duration");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_travel_scene_same_collision_id_does_not_restart_envelope():
    """Repeated snapshots with the same collision id must not restart the knockback."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            const submarine = RenderRuntime.getContainer("submarine").children[0];
            const baseX = submarine.position.x;

            const terrainSnap = {
              active: true,
              missionId: "sea-turtle",
              collisionActive: true,
              lastCollisionObstacleId: "coral-column-1",
              shakeOffsetY: -6,
              knockbackOffsetX: 36,
            };
            TravelScene.sync({ y: 360, distance: 720 }, terrainSnap);

            var t = 1100;
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, t);
            t += 60;
            const firstX = submarine.position.x;

            for (let i = 0; i < 10; i += 1) {
              frameId = window._pendingFrames()[0].id;
              window._runFrame(frameId, t);
              t += 60;
            }

            for (let i = 0; i < 30; i += 1) {
              frameId = window._pendingFrames()[0].id;
              window._runFrame(frameId, t);
              t += 60;
            }
            const finalX = submarine.position.x;

            assert.ok(firstX < baseX, "first frame must show knockback displacement");
            assert.ok(finalX >= firstX,
              "envelope must decay toward base, not restart on repeated same-id snapshots");
            assert.ok(Math.abs(baseX - finalX) < 2,
              "submarine must have returned to base after envelope duration");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_travel_scene_new_collision_id_resets_envelope():
    """A new collision obstacle id must restart the knockback envelope."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            const submarine = RenderRuntime.getContainer("submarine").children[0];
            const baseX = submarine.position.x;

            function collide(id) {
              const terrainSnap = {
                active: true,
                missionId: "sea-turtle",
                collisionActive: true,
                lastCollisionObstacleId: id,
                shakeOffsetY: -6,
                knockbackOffsetX: 36,
              };
              TravelScene.sync({ y: 360, distance: 720 }, terrainSnap);
              frameId = window._pendingFrames()[0].id;
              window._runFrame(frameId, frameTime);
              frameTime += 60;
            }

            let frameTime = 1100;
            collide("coral-column-1");
            const firstX = submarine.position.x;
            assert.ok(firstX < baseX, "first collision must produce knockback");

            for (let i = 0; i < 20; i += 1) {
              collide("coral-column-1");
            }

            TravelScene.sync({ y: 360, distance: 720 }, {
              active: true,
              missionId: "sea-turtle",
              collisionActive: true,
              lastCollisionObstacleId: "reef-arch-2",
              shakeOffsetY: -6,
              knockbackOffsetX: 36,
            });
            const secondX = submarine.position.x;
            assert.ok(secondX < baseX,
              "new collision id must push submarine left of canonical base");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_travel_scene_collision_off_restores_position():
    """When collisionActive goes false, submarine must return to base x with no drift."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            const submarine = RenderRuntime.getContainer("submarine").children[0];
            const baseX = submarine.position.x;

            const activeSnap = {
              active: true,
              missionId: "sea-turtle",
              collisionActive: true,
              lastCollisionObstacleId: "coral-column-1",
              shakeOffsetY: -6,
              knockbackOffsetX: 36,
            };
            TravelScene.sync({ y: 360, distance: 720 }, activeSnap);
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1100);

            const inactiveSnap = {
              active: true,
              missionId: "sea-turtle",
              collisionActive: false,
              lastCollisionObstacleId: null,
              shakeOffsetY: 0,
              knockbackOffsetX: 0,
            };
            TravelScene.sync({ y: 360, distance: 720 }, inactiveSnap);
            for (let i = 0; i < 30; i += 1) {
              frameId = window._pendingFrames()[0].id;
              window._runFrame(frameId, 1160 + i * 60);
            }

            assert.ok(Math.abs(baseX - submarine.position.x) < 2,
              "submarine must have no drift after collision ends");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_travel_scene_pause_stops_knockback_decay():
    """Pause must freeze knockback progress; resume continues from where it left off."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            const submarine = RenderRuntime.getContainer("submarine").children[0];
            const baseX = submarine.position.x;

            const activeSnap = {
              active: true,
              missionId: "sea-turtle",
              collisionActive: true,
              lastCollisionObstacleId: "coral-column-1",
              shakeOffsetY: -6,
              knockbackOffsetX: 36,
            };
            TravelScene.sync({ y: 360, distance: 720 }, activeSnap);

            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1100);
            const xAfterCollision = submarine.position.x;

            TravelScene.pause();
            TravelScene.resume();

            var t = 1200;
            for (let i = 0; i < 40; i += 1) {
              frameId = window._pendingFrames()[0].id;
              if (!frameId) break;
              window._runFrame(frameId, t);
              t += 60;
            }

            assert.ok(Math.abs(baseX - submarine.position.x) < 2,
              "submarine must return to base after resume completes remaining decay");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_travel_scene_obstacle_geometry_unchanged():
    """TravelScene knockback must not alter obstacle hitbox or travel distance."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);

            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            const terrainSnap = {
              active: true,
              missionId: "sea-turtle",
              collisionActive: true,
              lastCollisionObstacleId: "coral-column-1",
              shakeOffsetY: -6,
              knockbackOffsetX: 36,
            };

            for (let i = 0; i < 15; i += 1) {
              frameId = window._pendingFrames()[0].id;
              window._runFrame(frameId, 1100 + i * 60);
              TravelScene.sync({ y: 360, distance: 720 }, terrainSnap);
            }

            const submarine = RenderRuntime.getContainer("submarine").children[0];
            assert.strictEqual(submarine.position.x, submarine.position.x,
              "submarine position must be a finite number");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))
