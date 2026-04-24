from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_rewrites_include_space_explorer_route() -> None:
    config_path = ROOT / "vercel.json"
    assert config_path.exists()

    config = json.loads(config_path.read_text(encoding="utf-8"))
    rewrites = config.get("rewrites", [])

    assert any(
        item.get("source") == "/space-explorer.html"
        and item.get("destination") == "/templates/space-explorer.html"
        for item in rewrites
    )
