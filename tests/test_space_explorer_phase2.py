import json
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT


def test_space_explorer_script_is_connected() -> None:
    html = (TEMPLATES / "space-explorer.html").read_text(encoding="utf-8")
    assert 'script type="module" src="./space-explorer/main.js"' in html


def test_space_explorer_renderer_contract_is_executable() -> None:
    renderer_url = (TEMPLATES / "space-explorer" / "renderer.js").as_uri()
    state_url = (TEMPLATES / "space-explorer" / "state.js").as_uri()
    node_script = textwrap.dedent(
        """
        import { createRenderer } from "__RENDERER_URL__";
        import { state, planets } from "__STATE_URL__";

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
        globalThis.window = { devicePixelRatio: 1 };

        const canvas = {
          width: 0,
          height: 0,
          style: {},
          parentElement: { getBoundingClientRect: () => ({ width: 960 }) },
        };
        const ctx = {
          setTransform: () => {},
          beginPath: () => {},
          ellipse: () => {},
          arc: () => {},
          stroke: () => {},
          clearRect: () => {},
          drawImage: () => {},
          fill: () => {},
          fillText: () => {},
          createRadialGradient: () => ({ addColorStop: () => {} }),
        };

        const renderer = createRenderer(canvas, ctx, state, planets);
        renderer.resizeCanvas();
        renderer.render();
        console.log(JSON.stringify({
          hasResizeCanvas: typeof renderer.resizeCanvas === "function",
          hasRender: typeof renderer.render === "function",
          planetCount: planets.length,
        }));
        """
    ).replace("__RENDERER_URL__", renderer_url).replace("__STATE_URL__", state_url)
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", node_script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout.strip())
    assert payload["hasResizeCanvas"] is True
    assert payload["hasRender"] is True
    assert payload["planetCount"] >= 8
