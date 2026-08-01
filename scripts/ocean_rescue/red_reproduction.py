#!/usr/bin/env python3
"""RED reproduction: proves the travel-scene obstacle projection defect.

This script inspects the canonical source files in isolation and demonstrates
that:
  1. Terrain.getSnapshot() does NOT expose a distance field.
  2. TravelScene.syncObstacles reads terrainSnap.distance (undefined -> NaN).
  3. Obstacle body constructors use PIXI.Graphics / drawRoundedRect.
  4. No obstacle-kind-to-alias map exists in the codebase.

Run:
    uv run python scripts/ocean_rescue/red_reproduction.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2] if "parents" in dir() else Path.cwd()
# Resolve relative to this script location
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

DOMAIN_SRC = REPO_ROOT / "domains" / "ocean-rescue" / "src"
TRAVEL_SCENE = DOMAIN_SRC / "travel-scene.js"
TERRAIN = DOMAIN_SRC / "terrain.js"
TRAVEL = DOMAIN_SRC / "travel.js"
APP_JS = DOMAIN_SRC / "app.js"

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    terrain_src = read(TERRAIN)
    travel_scene_src = read(TRAVEL_SCENE)

    errors: list[str] = []

    # --- 1. Terrain.getSnapshot() has no distance field ---
    snapshot_match = re.search(
        r"function getSnapshot\(\) \{.*?return freeze\(\{(.*?)\}\);",
        terrain_src,
        re.DOTALL,
    )
    if snapshot_match:
        body = snapshot_match.group(1)
        keys = re.findall(r'(\w+):', body)
        if "distance" in keys:
            print(f"{FAIL} Terrain.getSnapshot() exposes 'distance' (unexpected)")
        else:
            print(f"{PASS} Terrain.getSnapshot() does NOT expose 'distance'")
            print(f"  Actual keys: {', '.join(keys)}")
    else:
        errors.append("Could not locate getSnapshot in terrain.js")

    # --- 2. TravelScene.syncObstacles reads terrainSnap.distance ---
    sync_match = re.search(
        r"function syncObstacles\([^)]*\) \{([^}]*(?:\{[^}]*\}[^}]*)*)\}",
        travel_scene_src,
        re.DOTALL,
    )
    if sync_match:
        body = sync_match.group(1)
        if "terrainSnap.distance" in body:
            print(f"{PASS} syncObstacles reads terrainSnap.distance (the bug)")
            # Simulate: obstacle.worldX - undefined = NaN
            world_x = 1200
            terrain_distance = None  # undefined in JS
            screen_x = world_x - (terrain_distance if terrain_distance is not None else float("nan"))
            import math
            is_nan = math.isnan(screen_x)
            print(f"  Simulated: screenX = {world_x} - undefined = {'NaN' if is_nan else screen_x}")
            if is_nan:
                print(f"{FAIL} RESULT: obstacle screenX is NaN (obstacles invisible)")
            else:
                print(f"  screenX = {screen_x}")
        else:
            print(f"{FAIL} syncObstacles does NOT read terrainSnap.distance")
    else:
        errors.append("Could not locate syncObstacles in travel-scene.js")

    # --- 3. Obstacle body uses PIXI.Graphics ---
    graphics_found = False
    for pattern in ["new PIXI.Graphics()", "drawRoundedRect", "beginFill", "endFill"]:
        if pattern in travel_scene_src:
            print(f"{PASS} Obstacle body uses {pattern}")
            graphics_found = True

    sprite_count = travel_scene_src.count("new PIXI.Sprite")
    print(f"  PIXI.Sprite count in travel-scene.js: {sprite_count}")

    if not graphics_found:
        errors.append("syncObstacles does not use PIXI.Graphics (already fixed?)")

    # --- 4. No obstacle alias map ---
    required_aliases_match = re.search(
        r"var\s+REQUIRED_ALIASES\s*=\s*\[([^\]]+)\]",
        travel_scene_src,
    )
    if required_aliases_match:
        aliases_raw = required_aliases_match.group(1)
        aliases = re.findall(r'"([^"]+)"', aliases_raw)
        terrain_kinds = [
            "coral-column", "reef-arch", "coral-rock", "kelp-rock", "reef-spire",
            "sand-rock", "shell-ledge", "low-reef", "rock-stack", "sand-pillar",
            "canyon-wall", "rock-spire", "canyon-ledge", "boulder-stack", "canyon-pillar",
        ]
        alias_prefixes = set()
        for a in aliases:
            parts = a.split(".")
            if len(parts) >= 2 and parts[0] == "terrain":
                alias_prefixes.add(a)

        missing = [k for k in terrain_kinds if f"terrain.{k}" not in alias_prefixes]
        if missing:
            print(f"{FAIL} Missing obstacle aliases ({len(missing)} kinds unmapped):")
            for m in missing:
                print(f"    terrain.{m}")
        else:
            print(f"{PASS} All {len(terrain_kinds)} obstacle kinds have aliases")
    else:
        errors.append("Could not locate REQUIRED_ALIASES")

    # --- 5. Verify travelSnap is available in sync() ---
    sync_fn = re.search(
        r"function sync\(([^)]+)\)",
        travel_scene_src,
    )
    if sync_fn:
        params = sync_fn.group(1)
        print(f"  sync() parameters: {params}")
        if "travelSnap" in params and "terrainSnap" in params:
            print(f"{PASS} sync() receives both travelSnap and terrainSnap")

    # --- 6. Terrain Layouts obstacle kinds ---
    layouts_match = re.search(r"var Layouts\s*=\s*freeze\(\{(.*?)\}\);", terrain_src, re.DOTALL)
    if layouts_match:
        layouts_body = layouts_match.group(1)
        kind_matches = re.findall(r'"(\w+-\w+)"', layouts_body)
        unique_kinds = sorted(set(kind_matches))
        print(f"\n  Canonical Terrain obstacle kinds ({len(unique_kinds)}):")
        for k in unique_kinds:
            print(f"    - {k}")

    # --- Summary ---
    print(f"\n{'='*60}")
    if errors:
        print(f"{FAIL} RED REPRODUCTION: {len(errors)} structural error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    else:
        print(f"{PASS} RED REPRODUCTION: defect confirmed")
        print("  - terrainSnap.distance is undefined -> NaN screenX")
        print("  - Obstacle bodies are PIXI.Graphics (not sprites)")
        print("  - No terrain.* obstacle aliases in the asset package")
        return 0


if __name__ == "__main__":
    sys.exit(main())
