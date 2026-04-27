import json
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT
SPACE_EXPLORER_DIR = TEMPLATES / "space-explorer"


def test_renderer_applies_hidpi_transform_and_draws_cached_layer() -> None:
    renderer_url = (SPACE_EXPLORER_DIR / "renderer.js").as_uri()
    state_url = (SPACE_EXPLORER_DIR / "state.js").as_uri()
    node_script = (
        textwrap.dedent(
            """
        import { createRenderer } from "__RENDERER_URL__";
        import { state, planets } from "__STATE_URL__";

        let setTransformArgs = null;
        let drawImageCount = 0;

        globalThis.document = {
          createElement: () => ({
            width: 0,
            height: 0,
            getContext: () => ({
              fillStyle: "",
              fillRect: () => {},
              createRadialGradient: () => ({ addColorStop: () => {} }),
            }),
          }),
        };
        globalThis.window = { devicePixelRatio: 2 };

        const canvas = {
          width: 0,
          height: 0,
          style: {},
          parentElement: { getBoundingClientRect: () => ({ width: 980 }) },
        };
        const ctx = {
          setTransform: (...args) => { setTransformArgs = args; },
          beginPath: () => {},
          ellipse: () => {},
          arc: () => {},
          stroke: () => {},
          clearRect: () => {},
          drawImage: () => { drawImageCount += 1; },
          fill: () => {},
          fillText: () => {},
          createRadialGradient: () => ({ addColorStop: () => {} }),
        };

        const renderer = createRenderer(canvas, ctx, state, planets);
        renderer.resizeCanvas();
        renderer.render();

        console.log(JSON.stringify({
          transformScaleX: setTransformArgs?.[0] ?? null,
          transformScaleY: setTransformArgs?.[3] ?? null,
          drawImageCount,
        }));
        """
        )
        .replace("__RENDERER_URL__", renderer_url)
        .replace("__STATE_URL__", state_url)
    )
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", node_script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout.strip())
    assert payload["transformScaleX"] == 2
    assert payload["transformScaleY"] == 2
    assert payload["drawImageCount"] >= 1


def test_cached_starfield_and_pointer_events_exist() -> None:
    renderer_js = (SPACE_EXPLORER_DIR / "renderer.js").read_text(encoding="utf-8")
    interactions_js = (SPACE_EXPLORER_DIR / "interactions.js").read_text(
        encoding="utf-8"
    )
    html = (TEMPLATES / "space-explorer.html").read_text(encoding="utf-8")

    assert 'document.createElement("canvas")' in renderer_js
    assert "ctx.drawImage(" in renderer_js
    assert 'canvas.addEventListener("pointerdown"' in interactions_js
    assert 'canvas.addEventListener("pointermove"' in interactions_js
    assert 'canvas.addEventListener("pointerup"' in interactions_js
    assert "핀치로 확대/축소" in html
