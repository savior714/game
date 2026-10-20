"""Playtest regressions for Dino Escape 3D.

A real player reported four defects after the 3D rebuild: mirrored steering, a
music-less hiss, no tablet ergonomics and visible stutter. These tests pin the
fixes so they cannot silently regress:

* steering is checked behaviourally (run ``player.js`` in node),
* the music scheduler is checked for both wiring and content,
* the touch contract is checked on markup, style and input bindings,
* the frame-budget contract is checked on the render path.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments" / "space-explorer"
PAGE = EXPERIMENTS / "dino-escape.html"
STYLESHEET = EXPERIMENTS / "dino-escape.css"
SCRIPT = EXPERIMENTS / "dino-escape.js"
DINO = EXPERIMENTS / "dino"


def _run_node(source: str) -> dict:
    node = shutil.which("node")
    if not node:
        return {}
    result = subprocess.run(
        [node, "--input-type=module", "-e", source],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_steering_follows_the_screen_not_the_world_axis() -> None:
    """+1 axis must move the runner to the player's right on screen.

    The chase camera sits behind the runner looking down +z, so screen-right is
    world -x. The conversion lives once in ``player.js`` and every input source
    (keyboard, drag, gamepad, thumb paddles) inherits it.
    """
    data = _run_node(
        """
        import { createPlayerState, resetPlayer, stepPlayer } from
          "./experiments/space-explorer/dino/player.js";
        const player = createPlayerState();
        resetPlayer(player, 0);
        for (let i = 0; i < 30; i += 1) stepPlayer(player, 1 / 60, { axis: 1 });
        const right = { x: player.x, tilt: player.tilt };
        resetPlayer(player, 0);
        for (let i = 0; i < 30; i += 1) stepPlayer(player, 1 / 60, { axis: -1 });
        const left = { x: player.x, tilt: player.tilt };
        console.log(JSON.stringify({ right, left }));
        """
    )
    if not data:
        return
    assert data["right"]["x"] < -0.5, "holding right must travel toward world -x"
    assert data["left"]["x"] > 0.5, "holding left must travel toward world +x"
    # Lean must agree with the turn, otherwise the runner skates sideways.
    assert data["right"]["tilt"] < 0 < data["left"]["tilt"]


def test_player_forgives_near_miss_jump_timing() -> None:
    """Coyote time and jump buffering are part of the child-friendly contract."""
    data = _run_node(
        """
        import { createPlayerState, resetPlayer, stepPlayer } from
          "./experiments/space-explorer/dino/player.js";
        const player = createPlayerState();
        resetPlayer(player, 0);
        stepPlayer(player, 1 / 60, { jump: true });
        const airborne = !player.grounded && player.y > 0;
        // Press jump just before touching down: the buffered press must fire on
        // landing instead of being thrown away.
        let pressedLate = false;
        let landedAt = -1;
        let relaunched = false;
        for (let i = 0; i < 300; i += 1) {
          const press = !pressedLate && !player.grounded && player.vy < 0 && player.y < 0.9;
          if (press) pressedLate = true;
          const events = stepPlayer(player, 1 / 60, { jump: press });
          if (events.landed && landedAt < 0) landedAt = i;
          if (landedAt >= 0 && !player.grounded) { relaunched = true; break; }
        }
        // Walk off a ledge, then press jump a frame later (coyote window).
        const coyote = createPlayerState();
        resetPlayer(coyote, 0);
        stepPlayer(coyote, 1 / 60, {});
        coyote.y = 0.35;
        coyote.grounded = false;
        coyote.vy = -0.5;
        stepPlayer(coyote, 1 / 60, { jump: true });
        console.log(JSON.stringify({
          airborne,
          buffered: pressedLate && relaunched,
          coyoteJump: coyote.vy > 10,
        }));
        """
    )
    if not data:
        return
    assert data["airborne"], "a jump request while grounded must leave the ground"
    assert data["buffered"], "a press just before landing must still jump"
    assert data["coyoteJump"], "a slightly late jump must still fire"


def test_music_scheduler_is_ticked_and_has_a_real_bed() -> None:
    """The old build never called ``tick()``: wind played, music never started."""
    script = SCRIPT.read_text(encoding="utf-8")
    audio = (DINO / "audio.js").read_text(encoding="utf-8")

    assert "audio.tick();" in script, "the render loop must drive the music scheduler"
    for part in ("scheduleKick", "scheduleSnare", "scheduleBass", "schedulePad", "schedulePluck"):
        assert f"function {part}(" in audio, f"missing {part}"

    # The menu must have music too, not just silence behind the start screen.
    menu_block = audio.split('if (state.mode === "menu") {', 1)[1].split("return;", 1)[0]
    assert "schedulePad(" in menu_block and "schedulePluck(" in menu_block

    # The old continuous 2.4 kHz highpass was the "쉬이익" the player heard.
    assert "2400" not in audio
    # Wind must be modulated, not a static wall of noise.
    assert "gustDepth" in audio and "driftDepth" in audio
    # Ambience follows the master sound switch, separate from the music switch.
    assert "settings.sound ? (musicPaused ? 0.22 : 0.6) : 0.0001" in audio


def test_tablet_controls_are_large_and_always_visible() -> None:
    html = PAGE.read_text(encoding="utf-8")
    css = STYLESHEET.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    input_js = (DINO / "input.js").read_text(encoding="utf-8")

    for control in ("btn-steer-left", "btn-steer-right", "btn-jump", "btn-slide", "btn-fullscreen"):
        assert f'id="{control}"' in html

    assert "body.is-touch .touch-controls" in css
    for selector, minimum in (
        (".touch-steer", 78),
        (".touch-jump", 90),
        (".touch-slide", 74),
        (".touch-sprint", 64),
        (".touch-bait", 64),
    ):
        block = re.search(rf"{re.escape(selector)} \{{(.*?)\}}", css, re.S)
        assert block is not None, f"missing {selector} sizing"
        width = int(re.search(r"width:\s*(\d+)px", block.group(1)).group(1))
        assert width >= minimum, f"{selector} is only {width}px wide"

    assert "setSteer(-1" in input_js and "setSteer(1" in input_js
    assert "touchAxis" in input_js
    # A quick tap anywhere on the canvas is a jump.
    assert "< 320" in input_js and "queueJump();" in input_js

    # Gesture hints swap for device-appropriate copy.
    assert "왼쪽 · 오른쪽 버튼" in html
    assert "body.is-touch .howto-touch" in css
    assert "isTouchDevice()" in script

    # Portrait tablets get a rotate prompt, and a way out of it.
    assert 'id="rotate-hint"' in html and 'id="btn-rotate-dismiss"' in html
    assert "syncRotateHint" in script


def test_render_path_keeps_a_frame_budget() -> None:
    """Two render passes must not double the shadow pass, and DPR adapts."""
    script = SCRIPT.read_text(encoding="utf-8")

    assert "renderer.shadowMap.autoUpdate = false;" in script
    assert "renderer.shadowMap.needsUpdate = true;" in script
    assert "REX_INSET_HZ = 30" in script
    assert "watchFrameTime" in script and "setRenderScale" in script
    assert "minScale: 0.7" in script, "the governor needs a floor"
    assert "Math.min(raw, 1.75)" in script, "retina tablets must not render at 2x"
    # Layout reads must not run every frame.
    assert "game.frameCount % 120 === 0" in script
