"""WebGPU remains available without destabilizing existing Three.js game pages."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_renderer_policy_keeps_webgl_as_the_default_and_webgpu_opt_in() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the renderer policy smoke test")

    result = subprocess.run(
        [node, "tests/fixtures/webgpu_renderer_policy.mjs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WebGPU renderer policy smoke test passed" in result.stdout
