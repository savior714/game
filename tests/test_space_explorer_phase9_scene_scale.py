"""태양계 3D 탐험대 — 3D 장면 구성/셰이더 계약."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPACE_DIR = ROOT / "experiments" / "space-explorer"


def read(name: str) -> str:
    return (SPACE_DIR / name).read_text(encoding="utf-8")


def test_scene_builds_every_body_from_textures() -> None:
    renderer = read("renderer.js")

    assert (
        "const textures = createTextureLibrary(renderer, onTextureProgress);"
        in renderer
    )
    assert "const maps = await textures.loadAll();" in renderer
    assert (
        "function createPlanetGroup(planet, maps, scene, gfx, gpuMaterials)"
        in renderer
    )
    assert "function createMoonRecord(moon, maps, scene)" in renderer
    assert "new THREE.SphereGeometry(planet.displayRadius, 128, 64)" in renderer
    assert 'maps.get("earth_day.jpg")' in renderer


def test_post_processing_brings_out_sun_and_city_lights() -> None:
    renderer = read("renderer.js")

    assert (
        'import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";'
        in renderer
    )
    assert (
        'import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";'
        in renderer
    )
    assert (
        'import { OutputPass } from "three/addons/postprocessing/OutputPass.js";'
        in renderer
    )
    # WebGL 경로는 기존 EffectComposer 체인을 그대로 유지한다.
    assert "composer = new EffectComposer(renderer);" in renderer
    assert "composer.addPass(new RenderPass(scene, camera));" in renderer
    assert "composer.addPass(bloomPass);" in renderer
    assert "composer.addPass(new OutputPass());" in renderer
    # WebGPU 경로는 TSL BloomNode 기반 RenderPipeline(r183+ PostProcessing 후신)으로
    # 동일한 블룸을 만들며, 톤매핑/색공간 변환은 파이프라인이 자동 적용한다.
    assert 'BACKEND_WEBGPU' in renderer
    assert "gpuMaterials.createSolarPostProcessing(renderer, scene, camera" in renderer
    webgpu_pipeline = (
        ROOT / "experiments" / "space-explorer" / "webgpu" / "solar-webgpu.js"
    ).read_text(encoding="utf-8")
    assert 'import { bloom } from "three/addons/tsl/display/BloomNode.js";' in webgpu_pipeline
    assert "new RenderPipeline(renderer)" in webgpu_pipeline
    assert "post.outputNode = sceneColor.add(bloomNode);" in webgpu_pipeline


def test_shader_materials_are_limited_to_real_effects() -> None:
    shaders = read("shaders.js")

    assert "export const EARTH_FRAGMENT" in shaders
    assert "uniform sampler2D nightMap;" in shaders
    assert "uniform sampler2D normalMap;" in shaders
    assert "uniform sampler2D specularMap;" in shaders
    assert "export const CLOUD_FRAGMENT" in shaders
    assert "export const ATMOSPHERE_FRAGMENT" in shaders
    assert "export const SUN_FRAGMENT" in shaders
    assert "export const RING_FRAGMENT" in shaders
    assert "float valueNoise(vec3 p)" in shaders
    assert "export function createSkyMaterial(" in shaders
    # 톤매핑/색공간 청크를 붙여 컴포저 유무와 상관없이 색이 일치해야 한다.
    assert "#include <tonemapping_fragment>" in shaders
    assert "#include <colorspace_fragment>" in shaders


def test_saturn_ring_casts_a_planet_shadow() -> None:
    shaders = read("shaders.js")
    data = read("data.js")

    assert "uniform vec3 planetWorldPosition;" in shaders
    assert "uniform float planetRadius;" in shaders
    assert (
        "shadow = smoothstep(planetRadius * 0.92, planetRadius * 1.12, distanceToAxis);"
        in shaders
    )
    assert 'ringTexture: "saturn_ring_alpha.png"' in data
    assert "ringInner: 1.24" in data
    assert "ringOuter: 2.32" in data


def test_sun_has_glow_sprites_and_live_plasma() -> None:
    renderer = read("renderer.js")

    assert "function createGlowSprites(scene, sunRadius)" in renderer
    assert "sunMaterial.uniforms.uTime.value = elapsed;" in renderer
    # 태양은 후처리 타깃에 HDR 값으로 그려야 블룸과 톤매핑이 자연스럽게 압축된다.
    assert "createSunMaterial(maps.get(SUN.texture)" in renderer
    intensity = float(
        re.search(
            r"createSunMaterial\(maps\.get\(SUN\.texture\), \{ intensity: ([0-9.]+) \}\)",
            renderer,
        ).group(1)
    )
    assert 0.9 <= intensity <= 2.0


def test_asteroid_and_kuiper_belts_exist() -> None:
    renderer = read("renderer.js")
    data = read("data.js")

    assert "function createBelt(scene," in renderer
    assert "function createKuiperBelt(scene," in renderer
    assert "export const BELT = {" in data
    assert "export const KUIPER_BELT = {" in data
    assert "new THREE.InstancedMesh(geometry, material, count)" in renderer
