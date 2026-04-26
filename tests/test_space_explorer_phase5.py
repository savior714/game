import json
import subprocess
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT
SPACE_EXPLORER_DIR = TEMPLATES / "space-explorer"


def test_space_explorer_uses_module_entrypoint() -> None:
    html = (TEMPLATES / "space-explorer.html").read_text(encoding="utf-8")
    assert 'script type="module" src="./space-explorer/main.js"' in html


def test_attach_controls_syncs_default_ui_state() -> None:
    controls_url = (SPACE_EXPLORER_DIR / "controls.js").as_uri()
    node_script = textwrap.dedent(
        """
        import { attachControls } from "__CONTROLS_URL__";

        const listeners = new Map();
        const playBtn = { classList: { toggle: () => {} }, addEventListener: () => {} };
        const pauseBtn = { classList: { toggle: () => {} }, addEventListener: () => {} };
        const resetBtn = { addEventListener: () => {} };
        const labelToggle = { checked: false, addEventListener: () => {} };
        const speed = { value: "", addEventListener: () => {} };
        const quality = { value: "", addEventListener: () => {} };
        const status = { textContent: "" };

        const controlsPanel = {
          querySelector: (selector) => {
            if (selector === '[data-action="play"]') return playBtn;
            if (selector === '[data-action="pause"]') return pauseBtn;
            if (selector === '[data-action="reset"]') return resetBtn;
            if (selector === 'input[type="checkbox"]') return labelToggle;
            return null;
          },
        };

        globalThis.document = {
          querySelector: (selector) => (selector === ".controls-panel" ? controlsPanel : null),
          getElementById: (id) => {
            if (id === "time-scale") return speed;
            if (id === "render-quality") return quality;
            if (id === "simulation-status") return status;
            return null;
          },
        };

        const state = { isPlaying: true, timeScale: 0.5, showLabels: true, renderMode: "2d", elapsedTime: 0, lastTs: 0 };
        const planets = [{ angle: 0.1 }, { angle: 0.2 }];
        const initialAngles = [0.1, 0.2];
        const render = () => {};

        const api = attachControls({ state, planets, initialAngles, render });
        console.log(JSON.stringify({
          hasSetPlaying: typeof api.setPlaying === "function",
          speedValue: speed.value,
          qualityValue: quality.value,
          labelChecked: labelToggle.checked,
          statusText: status.textContent,
        }));
        """
    ).replace("__CONTROLS_URL__", controls_url)
    completed = subprocess.run(
        ["node", "--input-type=module", "--eval", node_script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout.strip())
    assert payload["hasSetPlaying"] is True
    assert payload["speedValue"] == "0.5"
    assert payload["qualityValue"] == "2d"
    assert payload["labelChecked"] is True
    assert "재생 중" in payload["statusText"]
