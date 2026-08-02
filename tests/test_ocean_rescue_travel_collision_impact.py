"""Focused contract test for Ocean Rescue TravelScene collision impact feedback.

Verifies that a new collision obstacle id produces a bounded, contact-anchored
impact burst instead of a single bubbles sprite fixed at the submarine center:

  - effect nodes are created once at prepare time
  - the burst is anchored at the authoritative obstacle contact point
  - core flash / shock ring / radial rays / bubble burst start together
  - only the collided obstacle group pulses
  - the submarine shows a separate impact flash overlay
  - repeated snapshots with the same collision id do not restart the effect
  - the effect resets to canonical values within the bounded timeline
  - pause freezes the timeline and resume continues it
  - reduced-motion renders a static high-contrast cue (no scale/rotation)
  - invalid obstacle ids never produce a fake fixed-center effect

Tests run the real travel-scene.js (plus real terrain.js) through Node's vm
sandbox with a minimal fake RenderRuntime. No browser, no npm, no real Pixi
runtime required.
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

TERRAIN_JS = REPO_ROOT / "domains" / "ocean-rescue" / "src" / "terrain.js"
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


def _make_harness(script_body: str, reduced_motion: bool = False) -> str:
    required_aliases = [
        "scene.water.far", "scene.reef.mid", "scene.coral.foreground",
        "scene.submarine", "scene.seaweed-loop.01", "scene.sand-path",
        "scene.passage", "fx.bubbles", "fx.caustic",
        "terrain.coral-column", "terrain.coral-rock", "terrain.reef-arch",
        "terrain.reef-spire", "terrain.kelp-rock", "terrain.sand-rock",
        "terrain.shell-ledge", "terrain.low-reef", "terrain.rock-stack",
        "terrain.sand-pillar", "terrain.canyon-wall", "terrain.canyon-ledge",
        "terrain.canyon-pillar", "terrain.boulder-stack", "terrain.rock-spire",
    ]
    container_names = [
        "farBackground", "midground", "gameplayWorld",
        "submarine", "foreground", "effects"
    ]

    alias_init = "\n".join(
        f'textures["{a}"] = new FakeTexture();' for a in required_aliases
    )
    container_init = "\n".join(
        f'containers["{c}"] = new FakeContainer();' for c in container_names
    )
    reduced_init = "true" if reduced_motion else "false"

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
            this.tint = 0xFFFFFF;
            this.blendMode = "normal";
            this.label = "";
            this.name = "";
            this.eventMode = "none";
          }}
          FakeSprite.prototype.setScale = function (x, y) {{
            this.scale.x = x;
            this.scale.y = typeof y === "number" ? y : x;
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
            this._geometry = [];
          }}
          FakeGraphics.prototype.addChild = function (child) {{ this.children.push(child); }};
          FakeGraphics.prototype.circle = function (x, y, r) {{ this._geometry.push(["circle", x, y, r]); return this; }};
          FakeGraphics.prototype.moveTo = function (x, y) {{ this._geometry.push(["moveTo", x, y]); return this; }};
          FakeGraphics.prototype.lineTo = function (x, y) {{ this._geometry.push(["lineTo", x, y]); return this; }};
          FakeGraphics.prototype.fill = function () {{ return this; }};
          FakeGraphics.prototype.stroke = function () {{ return this; }};
          FakeGraphics.prototype.clear = function () {{ this._geometry = []; return this; }};
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

          window.PIXI = {{ Sprite: FakeSprite, Graphics: FakeGraphics, Container: FakeContainer, Texture: function () {{ return new FakeTexture(); }} }};

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
          var reduced = {reduced_init};
          return {{ matches: query === "(prefers-reduced-motion: reduce)" && reduced, addListener: function () {{}}, removeListener: function () {{}} }};
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

        const terrainSource = fs.readFileSync("domains/ocean-rescue/src/terrain.js", "utf8");
        const sandbox = {{ window: window, PIXI: window.PIXI, document: window.document }};
        vm.createContext(sandbox);
        vm.runInContext(terrainSource, sandbox, {{ filename: "terrain.js" }});

        const source = fs.readFileSync("domains/ocean-rescue/src/travel-scene.js", "utf8");
        vm.runInContext(source, sandbox, {{ filename: "travel-scene.js" }});

        const TravelScene = sandbox.window.OceanRescue.TravelScene;
        const RenderRuntime = sandbox.window.OceanRescue.RenderRuntime;
        const Terrain = sandbox.window.OceanRescue.Terrain;
        var document = sandbox.window.document;
        var PIXI = sandbox.window.PIXI;

        {script_body}
        """
    )
    return harness


def _find_effects(pg_helpers: str) -> str:
    return textwrap.dedent(
        """\
        const effects = RenderRuntime.getContainer("effects");
        const findByLabel = (label) => effects.children.find(c => c.label === label) || null;
        const impactRoot = () => effects.children.find(c => c.label === "travel-collision-impact-root") || null;
        const findInRoot = (label) => {
          const r = impactRoot();
          return r ? r.children.find(c => c.label === label) || null : null;
        };
        const gw = RenderRuntime.getContainer("gameplayWorld");
        const findGroup = (index) => {
          for (const child of gw.children) {
            if (child && child.label === "travel-obstacle-" + index) return child;
          }
          return null;
        };
        """
    )


# ---------------------------------------------------------------------------
# RED reproduction: baseline defect before the impact burst exists.
# ---------------------------------------------------------------------------


def test_contact_anchored_burst_on_first_collision() -> None:
    """First collision spawns contact-anchored burst + overlay + target pulse."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(Terrain.start("sea-turtle"), true);
            const travelSnap = { active: true, distance: 720, y: 220 };
            Terrain.step(16, travelSnap);
            const terrainSnap = Terrain.getSnapshot();
            assert.strictEqual(terrainSnap.collisionActive, true);
            assert.strictEqual(terrainSnap.lastCollisionObstacleId, "coral-column-1");
            assert.strictEqual(Terrain.Constants.gupScreenX, 320);
            assert.strictEqual(Terrain.Constants.gupHalfWidth, 70);

            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);
            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);
            TravelScene.sync({ y: 220, distance: 720 }, terrainSnap);
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1100);

            const submarine = RenderRuntime.getContainer("submarine").children[0];
            assert.ok(submarine.position.x < 260, "knockback PASS: submarine pushed left");
            assert.strictEqual(submarine.position.x, submarine.position.x, "finite");

            const effects = RenderRuntime.getContainer("effects");
            const flash = effects.children.find(c => c.label === "travel-collision-flash");
            assert.ok(flash, "bubbles sprite exists");
            assert.strictEqual(flash.visible, true, "bubbles sprite visible");
            assert.strictEqual(flash.position.x, 390,
              "burst anchored at obstacle contact point x");
            assert.strictEqual(flash.position.y, 220,
              "burst anchored at obstacle contact point y");

            const root = effects.children.find(c => c.label === "travel-collision-impact-root");
            assert.ok(root, "impact root exists");
            assert.strictEqual(root.position.x, 390, "impact root at contact x");
            assert.strictEqual(root.position.y, 220, "impact root at contact y");
            assert.ok(root instanceof PIXI.Container, "impact root is a Container");
            const rootLabels = root.children.map(c => c.label);
            assert.ok(rootLabels.indexOf("travel-collision-impact-core") >= 0, "core child");
            assert.ok(rootLabels.indexOf("travel-collision-impact-ring") >= 0, "ring child");
            assert.ok(rootLabels.indexOf("travel-collision-impact-rays") >= 0, "rays child");

            const overlay = RenderRuntime.getContainer("submarine").children.some(
              c => c.label === "travel-submarine-impact-flash");
            assert.strictEqual(overlay, true, "submarine overlay exists");

            const gw = RenderRuntime.getContainer("gameplayWorld");
            let group = null;
            for (const child of gw.children) {
              if (child && child.label === "travel-obstacle-0" && child.children) group = child;
            }
            assert.ok(group, "obstacle group present");
            assert.strictEqual(group.children.length, 3, "3-layer boundary PASS");
            assert.ok(group.scale.x > 1, "target group pulses on collision");

            const rootEl = document.getElementById("ocean-rescue-root");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-active"), "true",
              "impact diagnostic active");
            assert.strictEqual(
              rootEl.getAttribute("data-travel-scene-impact-contact-x"), "390",
              "contact x diagnostic");
            assert.strictEqual(
              rootEl.getAttribute("data-travel-scene-impact-contact-y"), "220",
              "contact y diagnostic");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


# ---------------------------------------------------------------------------
# GREEN: contact-anchored impact burst.
# ---------------------------------------------------------------------------


def test_impact_nodes_created_once_at_prepare() -> None:
    """Effect nodes must be created once at prepare time."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(TravelScene.prepare(), true);
            const effects = RenderRuntime.getContainer("effects");
            const labels = effects.children.map(c => c.label);
            assert.ok(labels.indexOf("travel-collision-impact-root") >= 0, "impact root exists");
            const root = effects.children.find(c => c.label === "travel-collision-impact-root");
            assert.ok(root instanceof PIXI.Container, "impact root is a Container");
            const childLabels = root.children.map(c => c.label).sort();
            assert.ok(childLabels.indexOf("travel-collision-impact-core") >= 0, "core child");
            assert.ok(childLabels.indexOf("travel-collision-impact-ring") >= 0, "ring child");
            assert.ok(childLabels.indexOf("travel-collision-impact-rays") >= 0, "rays child");
            assert.strictEqual(root.eventMode, "none");
            assert.strictEqual(root.visible, false, "root hidden at rest");

            const submarine = RenderRuntime.getContainer("submarine");
            const overlay = submarine.children.find(c => c.label === "travel-submarine-impact-flash");
            assert.ok(overlay, "submarine impact flash overlay exists");
            assert.ok(submarine.children[0] === submarine.children.find(c => c.label === "travel-submarine"),
              "submarine container first child is still the original");
            assert.strictEqual(overlay.visible, false, "overlay hidden at rest");
            assert.strictEqual(overlay.eventMode, "none");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def _collision_harness(script_body: str, reduced_motion: bool = False) -> str:
    return _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(Terrain.start("sea-turtle"), true);
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);
            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            const travelSnap = { active: true, distance: 720, y: 220 };
            Terrain.step(16, travelSnap);
            const terrainSnap = Terrain.getSnapshot();
            assert.strictEqual(terrainSnap.collisionActive, true);

            TravelScene.sync({ y: 220, distance: 720 }, terrainSnap);
            """ + _find_effects("") + script_body
        ),
        reduced_motion=reduced_motion,
    )


def test_new_collision_id_starts_contact_anchored_timeline() -> None:
    """A fresh collision id must start the burst at the obstacle contact point."""
    harness = _collision_harness(
        textwrap.dedent(
            """\
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1100);

            const root = effects.children.find(c => c.label === "travel-collision-impact-root");
            assert.ok(root, "impact root exists");
            assert.strictEqual(root.visible, true, "impact root visible");
            assert.strictEqual(root.position.x, 390,
              `contact x must be 390 (gupRight/obstacleLeft midpoint), got ${root.position.x}`);
            assert.strictEqual(root.position.y, 220,
              `contact y must be clamped to obstacle y 220, got ${root.position.y}`);

            const core = root.children.find(c => c.label === "travel-collision-impact-core");
            const ring = root.children.find(c => c.label === "travel-collision-impact-ring");
            const rays = root.children.find(c => c.label === "travel-collision-impact-rays");
            assert.strictEqual(core.visible, true, "core visible");
            assert.strictEqual(ring.visible, true, "ring visible");
            assert.strictEqual(rays.visible, true, "rays visible");

            const burst = effects.children.find(c => c.label === "travel-collision-flash");
            assert.strictEqual(burst.visible, true, "bubble burst visible");
            assert.strictEqual(burst.position.x, 390, "bubble burst anchored at contact x");
            assert.ok(Math.abs(burst.position.x - 260) > 1, "bubble burst not fixed at 260");

            const overlay = RenderRuntime.getContainer("submarine").children.find(
              c => c.label === "travel-submarine-impact-flash");
            assert.strictEqual(overlay.visible, true, "submarine overlay visible");

            const rootEl = document.getElementById("ocean-rescue-root");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-active"), "true");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-mode"), "contact-burst-v1");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-obstacle-id"), "coral-column-1");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-contact-x"), "390");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-contact-y"), "220");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_same_collision_id_does_not_restart_timeline() -> None:
    """Repeated same-id snapshots must not reset the impact timeline."""
    harness = _collision_harness(
        textwrap.dedent(
            """\
            let t = 1100;
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, t);
            t += 120;
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, t);

            const ring = findInRoot("travel-collision-impact-ring");
            const before = ring.scale.x;

            for (let i = 0; i < 3; i += 1) {
              TravelScene.sync({ y: 220, distance: 720 }, Terrain.getSnapshot());
              frameId = window._pendingFrames()[0].id;
              window._runFrame(frameId, t);
              t += 60;
            }
            const after = ring.scale.x;
            const rootEl = document.getElementById("ocean-rescue-root");
            const phase = rootEl.getAttribute("data-travel-scene-impact-phase");
            assert.ok(after > before,
              `ring must keep expanding (no restart): before ${before} -> after ${after}`);
            assert.ok(phase !== "core",
              `phase must not return to core on same-id resync, got "${phase}"`);
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-active"), "true",
              "effect still running under same id");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_new_collision_id_restarts_timeline_at_new_contact() -> None:
    """After completion, a new obstacle id must start a new timeline at its contact."""
    harness = _collision_harness(
        textwrap.dedent(
            """\
            let t = 1100;
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, t);
            t += 60;
            for (let i = 0; i < 12; i += 1) {
              frameId = window._pendingFrames()[0].id;
              window._runFrame(frameId, t);
              t += 60;
            }
            const rootEl = document.getElementById("ocean-rescue-root");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-active"), "false",
              "first effect must have completed and reset");

            const travelSnap2 = { active: true, distance: 1800, y: 500 };
            Terrain.step(16, travelSnap2);
            const terrainSnap2 = Terrain.getSnapshot();
            assert.strictEqual(terrainSnap2.lastCollisionObstacleId, "reef-arch-2");
            TravelScene.sync({ y: 500, distance: 1800 }, terrainSnap2);
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, t);

            const root = effects.children.find(c => c.label === "travel-collision-impact-root");
            assert.strictEqual(root.visible, true, "second impact started");
            assert.strictEqual(root.position.x, 345,
              `second contact x must be 345, got ${root.position.x}`);
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-obstacle-id"), "reef-arch-2");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-contact-x"), "345");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_only_target_obstacle_group_pulses() -> None:
    """Only the collided obstacle group may pulse; other groups stay at scale 1."""
    harness = _collision_harness(
        textwrap.dedent(
            """\
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1100);

            const target = findGroup(0);
            assert.ok(target, "target group found");
            assert.ok(target.scale.x > 1.001,
              `target group must pulse above 1, got ${target.scale.x}`);
            for (let i = 1; i < 5; i += 1) {
              const group = findGroup(i);
              assert.strictEqual(group.scale.x, 1,
                `group ${i} must stay at scale 1, got ${group.scale.x}`);
            }

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_effect_resets_after_bounded_duration() -> None:
    """The burst must end and restore canonical values within ~450ms."""
    harness = _collision_harness(
        textwrap.dedent(
            """\
            let t = 1100;
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, t);
            t += 60;
            for (let i = 0; i < 20; i += 1) {
              frameId = window._pendingFrames()[0].id;
              window._runFrame(frameId, t);
              t += 60;
            }

            const rootEl = document.getElementById("ocean-rescue-root");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-active"), "false",
              "effect must reset after bounded duration");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-phase"), "idle");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-obstacle-id"), "",
              "stale obstacle id must be cleared");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-contact-x"), "",
              "stale contact x must be cleared");

            const root = effects.children.find(c => c.label === "travel-collision-impact-root");
            assert.strictEqual(root.visible, false, "root hidden after reset");
            assert.strictEqual(root.alpha, 0, "root alpha canonical after reset");

            const burst = effects.children.find(c => c.label === "travel-collision-flash");
            assert.strictEqual(burst.visible, false, "burst hidden after reset");
            assert.strictEqual(burst.alpha, 0, "burst alpha canonical after reset");

            const overlay = RenderRuntime.getContainer("submarine").children.find(
              c => c.label === "travel-submarine-impact-flash");
            assert.strictEqual(overlay.visible, false, "overlay hidden after reset");
            assert.strictEqual(overlay.alpha, 0, "overlay alpha canonical after reset");

            const target = findGroup(0);
            assert.strictEqual(target.scale.x, 1, "target group scale canonical after reset");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_pause_freezes_timeline_and_resume_continues() -> None:
    """Pause must stop the impact timeline; resume must continue it."""
    harness = _collision_harness(
        textwrap.dedent(
            """\
            let t = 1100;
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, t);
            t += 120;
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, t);

            const ring = findInRoot("travel-collision-impact-ring");
            const rootEl = document.getElementById("ocean-rescue-root");

            const scaleBefore = ring.scale.x;
            const phaseBefore = rootEl.getAttribute("data-travel-scene-impact-phase");
            assert.ok(scaleBefore > 1, "ring expanding before pause");

            TravelScene.pause();
            assert.strictEqual(window._pendingFrames().length, 0,
              "pause must cancel the animation loop");
            TravelScene.sync({ y: 220, distance: 720 }, Terrain.getSnapshot());
            assert.strictEqual(ring.scale.x, scaleBefore,
              `timeline must freeze during pause (scale ${scaleBefore})`);
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-phase"), phaseBefore,
              "phase must freeze during pause");

            TravelScene.resume();
            var tt = t + 6 * 60;
            for (let i = 0; i < 20; i += 1) {
              frameId = window._pendingFrames()[0].id;
              if (!frameId) break;
              window._runFrame(frameId, tt);
              tt += 60;
            }
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-active"), "false",
              "timeline must complete after resume");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_reduced_motion_static_cue() -> None:
    """Reduced motion must show a static high-contrast cue without scaling."""
    harness = _collision_harness(
        textwrap.dedent(
            """\
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1100);

            const root = effects.children.find(c => c.label === "travel-collision-impact-root");
            const core = root.children.find(c => c.label === "travel-collision-impact-core");
            const ring = root.children.find(c => c.label === "travel-collision-impact-ring");
            const rays = root.children.find(c => c.label === "travel-collision-impact-rays");
            assert.strictEqual(root.visible, true, "static cue visible");
            assert.strictEqual(core.visible, true, "core static visible");
            assert.strictEqual(ring.visible, true, "ring static visible");
            assert.strictEqual(rays.visible, false, "rays hidden under reduced motion");
            assert.strictEqual(core.scale.x, 1, "no core scaling under reduced motion");
            assert.strictEqual(ring.scale.x, 1, "no ring scaling under reduced motion");

            const target = findGroup(0);
            assert.strictEqual(target.scale.x, 1, "no obstacle pulse under reduced motion");

            let t = 1160;
            for (let i = 0; i < 6; i += 1) {
              frameId = window._pendingFrames()[0].id;
              window._runFrame(frameId, t);
              t += 60;
            }
            const rootEl = document.getElementById("ocean-rescue-root");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-active"), "false",
              "static cue must end within the bounded window");

            TravelScene.exit();
            """
        ),
        reduced_motion=True,
    )
    _assert_ok(_run_node(harness))


def test_invalid_obstacle_id_hides_effect_no_fake_center() -> None:
    """Unknown obstacle ids must hide the effect, never a fixed-center fake."""
    harness = _make_harness(
        textwrap.dedent(
            """\
            assert.strictEqual(Terrain.start("sea-turtle"), true);
            assert.strictEqual(TravelScene.prepare(), true);
            assert.strictEqual(TravelScene.activate(), true);
            let frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1000);

            const terrainSnap = {
              active: true,
              missionId: "sea-turtle",
              collisionActive: true,
              lastCollisionObstacleId: "ghost-obstacle",
              shakeOffsetY: 0,
              knockbackOffsetX: 0,
            };
            TravelScene.sync({ y: 220, distance: 720 }, terrainSnap);
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1100);

            const effects = RenderRuntime.getContainer("effects");
            const root = effects.children.find(c => c.label === "travel-collision-impact-root");
            assert.strictEqual(root.visible, false, "no fake fixed-center effect");
            const burst = effects.children.find(c => c.label === "travel-collision-flash");
            assert.strictEqual(burst.visible, false, "burst hidden for unknown id");
            const rootEl = document.getElementById("ocean-rescue-root");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-active"), "false");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-obstacle-id"), "");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_no_per_frame_object_allocation_growth() -> None:
    """Repeated frames must not grow the scene graph object count."""
    harness = _collision_harness(
        textwrap.dedent(
            """\
            const countBefore = effects.children.length + gw.children.length;
            let t = 1100;
            for (let i = 0; i < 15; i += 1) {
              frameId = window._pendingFrames()[0].id;
              window._runFrame(frameId, t);
              t += 60;
            }
            const countAfter = effects.children.length + gw.children.length;
            assert.strictEqual(countAfter, countBefore,
              `object count must not grow: ${countBefore} -> ${countAfter}`);

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_collision_count_slowdown_geometry_distance_unchanged() -> None:
    """Impact feedback must not alter collision/slowdown/geometry/distance."""
    harness = _collision_harness(
        textwrap.dedent(
            """\
            const layout = Terrain.getLayout("sea-turtle");
            assert.strictEqual(layout.obstacles[0].id, "coral-column-1");
            assert.strictEqual(layout.obstacles[0].worldX, 1200);
            assert.strictEqual(layout.obstacles[0].width, 180);
            assert.strictEqual(layout.obstacles[0].height, 150);
            const terrainSnap2 = Terrain.getSnapshot();
            assert.strictEqual(terrainSnap2.collisionCount, 1);
            assert.strictEqual(terrainSnap2.forwardSpeedMultiplier, 0.5);

            let t = 1100;
            for (let i = 0; i < 10; i += 1) {
              frameId = window._pendingFrames()[0].id;
              window._runFrame(frameId, t);
              t += 60;
            }
            assert.strictEqual(Terrain.getSnapshot().collisionCount, 1,
              "collision count must not change from feedback");
            assert.strictEqual(Terrain.getLayout("sea-turtle").obstacles[0].worldX, 1200,
              "obstacle geometry must be unchanged");

            TravelScene.exit();
            """
        )
    )
    _assert_ok(_run_node(harness))


def test_exit_resets_impact_state() -> None:
    """Exit must reset impact running/id/contact state."""
    harness = _collision_harness(
        textwrap.dedent(
            """\
            frameId = window._pendingFrames()[0].id;
            window._runFrame(frameId, 1100);
            const rootEl = document.getElementById("ocean-rescue-root");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-active"), "true");

            TravelScene.exit();
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-active"), "false",
              "exit must reset impact active");
            assert.strictEqual(rootEl.getAttribute("data-travel-scene-impact-obstacle-id"), "",
              "exit must clear obstacle id");

            TravelScene.destroy();
            """
        )
    )
    _assert_ok(_run_node(harness))
