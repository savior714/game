from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = ROOT / "agents"
COMPAT_ROOT = ROOT / ".agents"
MIGRATED_DIRECTORIES = ("core", "domains", "registry", "skills", "workflows")


def test_agent_documents_have_one_canonical_root() -> None:
    for name in MIGRATED_DIRECTORIES:
        canonical = CANONICAL_ROOT / name
        compatibility = COMPAT_ROOT / name

        assert canonical.is_dir(), f"missing canonical agent directory: {canonical}"
        assert compatibility.is_symlink(), f"compatibility path must be a symlink: {compatibility}"
        assert compatibility.resolve() == canonical.resolve()


def test_compatibility_root_contains_only_expected_links() -> None:
    assert COMPAT_ROOT.is_dir()
    assert sorted(path.name for path in COMPAT_ROOT.iterdir()) == sorted(MIGRATED_DIRECTORIES)
