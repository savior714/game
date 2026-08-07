"""Focused tests for the seaweed-loop-02 handoff render proof harness (B23)."""

from __future__ import annotations

import json
import pathlib
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PROOF_DIR = REPO_ROOT / "domains/ocean-rescue/assets/review/proof-seaweed-loop-02-handoff"
MANIFEST_FILE = PROOF_DIR / "manifest.json"


def test_seaweed_loop_02_proof_artifacts_exist():
    assert PROOF_DIR.exists()
    assert MANIFEST_FILE.exists()
    assert (PROOF_DIR / "isolated-1x.png").exists()
    assert (PROOF_DIR / "isolated-2x.png").exists()
    assert (PROOF_DIR / "in-context-proof.png").exists()


def test_seaweed_loop_02_proof_manifest_contract():
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    assert manifest["assetId"] == "scene-seaweed-loop-02-01"
    assert manifest["alias"] == "scene.seaweed-loop.02"
    assert manifest["proofs"]["isolated1x"]["dimensions"] == [120, 200]
    assert manifest["proofs"]["isolated2x"]["dimensions"] == [240, 400]
    assert manifest["proofs"]["inContextProof"]["dimensions"] == [1280, 720]
    assert len(manifest["svgHash"]) == 64
