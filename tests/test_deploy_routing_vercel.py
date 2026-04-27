from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_rewrites_include_space_explorer_route() -> None:
    config_path = ROOT / "vercel.json"
    assert config_path.exists()

    config = json.loads(config_path.read_text(encoding="utf-8"))
    rewrites = config.get("rewrites", [])

    assert not any(
        item.get("destination", "").startswith("/templates/") for item in rewrites
    )


def test_vercel_rewrites_do_not_override_root_route() -> None:
    config_path = ROOT / "vercel.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    rewrites = config.get("rewrites", [])

    assert not any(item.get("source") == "/" for item in rewrites)
    assert not any(item.get("source") == "/(.*)" for item in rewrites)
