from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_english_engine_initializes_domain_keys_from_words_before_stats_load() -> None:
    engine = (ROOT / "english" / "engine.js").read_text(encoding="utf-8")

    assert "function initDomainKeys()" in engine
    assert "DOMAIN_KEYS = Object.keys(WORDS);" in engine
    assert "initDomainKeys();" in engine

    init_idx = engine.index("initDomainKeys();")
    load_idx = engine.index("let stats = loadStats();")
    assert init_idx < load_idx
