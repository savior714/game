"""태양계 3D 탐험대 — 엔트리/의존성 계약.

이 페이지는 정적 배포되므로 three.js와 애드온을 저장소 안에서 제공해야 한다.
CDN import가 되살아나면 오프라인/사내망에서 3D 장면이 통째로 뜨지 않는다.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPACE_DIR = ROOT / "experiments" / "space-explorer"
INDEX = SPACE_DIR / "index.html"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_three_is_served_from_the_repository_not_a_cdn() -> None:
    html = read(INDEX)

    import_map = re.search(r'<script type="importmap">(.*?)</script>', html, re.DOTALL)
    assert import_map is not None, "index.html must declare an import map"
    mapping = import_map.group(1)

    assert '"three": "./vendor/three/build/three.module.min.js"' in mapping
    assert '"three/addons/": "./vendor/three/addons/"' in mapping
    # WebGPU 경로도 CDN 없이 저장소 안의 벤더 빌드를 쓴다.
    assert '"three/webgpu": "./vendor/three/build/three.webgpu.min.js"' in mapping
    assert '"three/tsl": "./vendor/three/build/three.tsl.min.js"' in mapping
    assert "cdn.jsdelivr.net" not in html
    assert "unpkg.com" not in html
    assert "https://" not in "".join(re.findall(r'<script[^>]*src="([^"]+)"', html))


@pytest.mark.parametrize(
    "relative_path",
    [
        "vendor/three/build/three.module.min.js",
        "vendor/three/build/three.core.min.js",
        "vendor/three/build/three.webgpu.min.js",
        "vendor/three/build/three.tsl.min.js",
        "vendor/three/addons/controls/OrbitControls.js",
        "vendor/three/addons/postprocessing/EffectComposer.js",
        "vendor/three/addons/postprocessing/RenderPass.js",
        "vendor/three/addons/postprocessing/UnrealBloomPass.js",
        "vendor/three/addons/postprocessing/OutputPass.js",
        "vendor/three/addons/tsl/display/BloomNode.js",
        "vendor/three/LICENSE/THREE_LICENSE.txt",
        "webgpu/renderer-factory.js",
        "webgpu/tsl.js",
        "webgpu/instanced-sprites.js",
        "webgpu/noise.js",
        "webgpu/solar-webgpu.js",
    ],
)
def test_vendored_three_files_exist(relative_path: str) -> None:
    assert (SPACE_DIR / relative_path).is_file(), relative_path


def test_module_entry_is_connected() -> None:
    html = read(INDEX)

    assert 'script type="module" src="./main.js"' in html
    assert 'id="space-canvas"' in html
    assert 'id="labels-layer"' in html
    assert 'id="loading-screen"' in html
    assert (SPACE_DIR / "main.js").is_file()


def test_main_imports_the_scene_pipeline_modules() -> None:
    js = read(SPACE_DIR / "main.js")

    assert 'import { createSolarScene } from "./renderer.js";' in js
    assert 'import { createUiController } from "./controls.js";' in js
    assert 'import { attachSceneInteractions } from "./interactions.js";' in js
    assert "import { createAppState" in js
    assert "requestAnimationFrame(frame);" in js


def test_license_and_texture_credits_are_visible_to_users() -> None:
    html = read(INDEX)

    assert "Solar System Scope" in html
    assert "CC BY 4.0" in html
    assert "NASA" in html
    assert "three.js" in html
    assert 'rel="noopener noreferrer"' in html
