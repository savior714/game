from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_space_explorer_plan_tracks_current_module_paths() -> None:
    plan = (ROOT / "docs" / "SPACE_EXPLORER_PLAN.md").read_text(encoding="utf-8")

    assert "`index.html`" in plan
    assert "`space-explorer.html`" in plan
    assert "`space-explorer/main.js`" in plan
    assert "`space-explorer/renderer.js`" in plan
    assert "`space-explorer/interactions.js`" in plan
    assert "`space-explorer.js`" not in plan


def test_design_doc_declares_runtime_entry_and_deploy_routing() -> None:
    design = (ROOT / "templates" / "docs" / "specs" / "technical" / "DESIGN.md").read_text(
        encoding="utf-8"
    )

    assert "Runtime Entry and Routing SSOT" in design
    assert "`index.html`" in design
    assert "`space-explorer.html`" in design
    assert "`vercel.json`" in design
