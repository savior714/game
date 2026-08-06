from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPACE_ROOT = ROOT / "experiments" / "space-explorer"
CANONICAL_SPACE_FILES = (
    SPACE_ROOT / "index.html",
    SPACE_ROOT / "main.js",
    SPACE_ROOT / "renderer.js",
    SPACE_ROOT / "controls.js",
    SPACE_ROOT / "interactions.js",
)


def test_space_explorer_plan_tracks_current_module_paths() -> None:
    plan = (ROOT / "docs" / "SPACE_EXPLORER_PLAN.md").read_text(encoding="utf-8")

    expected_paths = (
        "`experiments/space-explorer/index.html`",
        "`experiments/space-explorer/main.js`",
        "`experiments/space-explorer/renderer.js`",
        "`experiments/space-explorer/controls.js`",
        "`experiments/space-explorer/interactions.js`",
        "`vercel.json`",
    )
    for path in expected_paths:
        assert path in plan

    assert "`/space-explorer.html`" in plan
    assert "`experiments/space-explorer.html`" in plan
    assert "`space-explorer.js`" not in plan

    for path in CANONICAL_SPACE_FILES:
        assert path.is_file(), f"missing canonical Space Explorer file: {path}"


def test_design_doc_declares_runtime_entry_and_deploy_routing() -> None:
    design = (ROOT / "docs" / "specs" / "technical" / "DESIGN.md").read_text(
        encoding="utf-8"
    )

    assert "Runtime Entry and Routing SSOT" in design
    assert "`index.html`" in design
    assert "`experiments/space-explorer/index.html`" in design
    assert "`experiments/space-explorer/main.js`" in design
    assert "`vercel.json`" in design
    assert '"rewrites": []' in design
    assert "`/space-explorer.html`" in design
    assert "`experiments/space-explorer.html`" in design

    assert (ROOT / "index.html").is_file()
    assert (ROOT / "vercel.json").is_file()
    for path in CANONICAL_SPACE_FILES:
        assert path.is_file(), f"missing routing target: {path}"
