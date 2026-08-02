#!/usr/bin/env python3
"""Build a deterministic HTML review contact sheet from the Ocean Rescue art packet.

Usage:
    python build_art_contact_sheet.py <source_root> [--output <path>]

Reads art-packet.json and SVG sources. Produces standalone HTML with no external
network requests. Deterministic: same input always produces identical bytes.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path


def build_contact_sheet(source_root: Path) -> str:
    packet_path = source_root / "art-packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))

    assets_by_bundle: dict[str, list[dict]] = {"characters": [], "scene": [], "effects-ui": []}
    for asset in packet["assets"]:
        assets_by_bundle[asset["bundle"]].append(asset)

    bundle_order = ["characters", "scene", "effects-ui"]
    role_order = {
        "characters": [
            "otter.head", "otter.torso", "otter.arm.near", "otter.arm.far", "otter.tail",
            "otter.eyes.open", "otter.eyes.closed",
            "otter.mouth.neutral", "otter.mouth.concern", "otter.mouth.smile",
            "turtle.worried", "turtle.free",
        ],
        "scene": [
            "scene.submarine", "scene.water.far", "scene.reef.mid",
            "scene.coral.foreground", "scene.seaweed-loop.01",
        ],
        "effects-ui": ["ui.drag-arrow", "fx.success-burst"],
    }

    def asset_sort_key(a: dict) -> int:
        bundle = a["bundle"]
        order = role_order.get(bundle, [])
        try:
            return order.index(a["alias"])
        except ValueError:
            return 999

    cards_html: list[str] = []
    for bundle_name in bundle_order:
        assets = sorted(assets_by_bundle[bundle_name], key=asset_sort_key)
        cards_html.append(f'<h2 class="bundle-header">{bundle_name}</h2>')
        cards_html.append('<div class="card-grid">')
        for asset in assets:
            svg_path = source_root / asset["source"]
            svg_bytes = svg_path.read_bytes()
            svg_b64 = base64.b64encode(svg_bytes).decode("ascii")
            w, h = asset["logicalSize"]
            px, py = asset["pivot"]
            sha_prefix = asset["sourceSha256"][:12]
            card = f'''<div class="card">
  <div class="preview-full">
    <img src="data:image/svg+xml;base64,{svg_b64}" alt="{asset['alias']}" width="{w}" height="{h}"/>
  </div>
  <div class="preview-quarter">
    <img src="data:image/svg+xml;base64,{svg_b64}" alt="{asset['alias']}" width="{w // 4}" height="{h // 4}"/>
  </div>
  <div class="card-info">
    <span class="alias">{asset['alias']}</span>
    <span class="meta">{w}x{h} pivot=[{px},{py}] sha={sha_prefix}</span>
  </div>
</div>'''
            cards_html.append(card)
        cards_html.append("</div>")

    cards_block = "\n".join(cards_html)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Ocean Rescue Proof Art Contact Sheet</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 24px; }}
  h1 {{ font-size: 20px; margin-bottom: 4px; color: #ffffff; }}
  .subtitle {{ font-size: 12px; color: #888; margin-bottom: 24px; }}
  .bundle-header {{ font-size: 16px; color: #5a9fd5; margin: 20px 0 10px; border-bottom: 1px solid #333; padding-bottom: 4px; }}
  .card-grid {{ display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 24px; }}
  .card {{ background: #16213e; border: 1px solid #333; border-radius: 8px; padding: 12px; width: 260px; }}
  .preview-full {{ background: repeating-conic-gradient(#2a2a3e 0% 25%, #3a3a4e 0% 50%) 50% / 20px 20px; border-radius: 4px; padding: 8px; display: flex; justify-content: center; align-items: center; min-height: 80px; margin-bottom: 8px; }}
  .preview-quarter {{ background: repeating-conic-gradient(#2a2a3e 0% 25%, #3a3a4e 0% 50%) 50% / 20px 20px; border-radius: 4px; padding: 8px; display: flex; justify-content: center; align-items: center; min-height: 40px; margin-bottom: 8px; }}
  .card-info {{ display: flex; flex-direction: column; gap: 2px; }}
  .alias {{ font-weight: 600; font-size: 13px; color: #e8a83e; }}
  .meta {{ font-size: 11px; color: #888; font-family: monospace; }}
</style>
</head>
<body>
<h1>Ocean Rescue — Proof Art Contact Sheet</h1>
<div class="subtitle">schemaVersion: {packet['schemaVersion']} | viewport: {packet['logicalViewport'][0]}x{packet['logicalViewport'][1]} | rasterScale: {packet['declaredRasterScale']}x | palette: {packet['paletteVersion']} | assets: {len(packet['assets'])}</div>
{cards_block}
</body>
</html>'''


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: build_art_contact_sheet.py <source_root> [--output <path>]", file=sys.stderr)
        sys.exit(1)

    source_root = Path(sys.argv[1])
    output_path: Path | None = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_path = Path(sys.argv[idx + 1])

    html = build_contact_sheet(source_root)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        print(f"Contact sheet written to: {output_path}")
    else:
        print(html)


if __name__ == "__main__":
    main()
