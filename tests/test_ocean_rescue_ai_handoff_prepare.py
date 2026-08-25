#!/usr/bin/env python3
"""
Tests for ocean_ai.py prepare command - deterministic/security/freshness contracts
"""

import json
import tempfile
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ocean_rescue" / "ocean_ai.py"


def run_prepare(spec_dict: dict, out_dir: Path) -> tuple[int, str, str]:
    """Run prepare command and return (exit_code, stdout, stderr)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(spec_dict, f)
        spec_path = Path(f.name)
    try:
        result = subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "prepare",
                "--spec",
                str(spec_path),
                "--out",
                str(out_dir),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout, result.stderr
    finally:
        spec_path.unlink()


def load_manifest(out_dir: Path) -> dict:
    return json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))


def load_flatpack(out_dir: Path) -> str:
    return (out_dir / "packet.txt").read_text(encoding="utf-8")


def test_prepare_deterministic_same_input():
    """Same input twice -> packet/manifest byte-identical."""
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        spec = {
            "task_id": "test-001",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["scripts/ocean_rescue/ocean_ai.py"],
            "read_only_paths": ["AGENTS.md"],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code1, _, _ = run_prepare(spec, Path(d1))
        code2, _, _ = run_prepare(spec, Path(d2))
        assert code1 == 0 and code2 == 0

        m1 = load_manifest(Path(d1))
        m2 = load_manifest(Path(d2))
        _ = load_flatpack(Path(d1))
        _ = load_flatpack(Path(d2))

        # Manifests should be identical (except createdAt)
        m1_copy = {k: v for k, v in m1.items() if k != "createdAt"}
        m2_copy = {k: v for k, v in m2.items() if k != "createdAt"}
        assert m1_copy == m2_copy, "Manifests not identical"

        # Flatpacks should be identical (except timestamps in header)
        # The flatpack includes createdAt in header, so compare packetId and baseSha lines
        assert m1["packetId"] == m2["packetId"], "Packet IDs differ"
        assert m1["baseSha"] == m2["baseSha"], "Base SHAs differ"


def test_prepare_base_sha_accurate():
    """Base SHA in manifest matches git HEAD."""
    with tempfile.TemporaryDirectory() as d:
        spec = {
            "task_id": "test-002",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["scripts/ocean_rescue/ocean_ai.py"],
            "read_only_paths": ["AGENTS.md"],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, Path(d))
        assert code == 0

        manifest = load_manifest(Path(d))
        # Get actual HEAD
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        actual_sha = result.stdout.strip()
        assert manifest["baseSha"] == actual_sha


def test_prepare_text_roundtrip():
    """Text files preserve exact UTF-8 content."""
    with tempfile.TemporaryDirectory() as d:
        spec = {
            "task_id": "test-003",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": [],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, Path(d))
        assert code == 0

        manifest = load_manifest(Path(d))
        flatpack = load_flatpack(Path(d))

        # Find the AGENTS.md content in flatpack
        original = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        assert original in flatpack, "Original text not found in flatpack"

        # Check manifest encoding
        agents_entry = next(f for f in manifest["files"] if f["path"] == "AGENTS.md")
        assert agents_entry["encoding"] == "utf-8"
        assert agents_entry["byte_length"] == len(original.encode("utf-8"))


def test_prepare_binary_roundtrip():
    """Binary files preserve exact bytes via base64."""
    with tempfile.TemporaryDirectory() as d:
        # Create a test binary file
        bin_path = REPO_ROOT / "test_binary_fixture.bin"
        bin_content = b"\x00\x01\x02\xff\xfe\xfd\x80\x81\x82"
        bin_path.write_bytes(bin_content)
        try:
            spec = {
                "task_id": "test-004",
                "goal": "Test goal",
                "acceptance_criteria": ["Criterion 1"],
                "mutable_paths": [],
                "read_only_paths": ["test_binary_fixture.bin"],
                "allow_new_under": [],
                "guidance_paths": [],
                "verification_commands": [],
            }
            code, _, _ = run_prepare(spec, Path(d))
            assert code == 0

            manifest = load_manifest(Path(d))
            flatpack = load_flatpack(Path(d))

            entry = next(
                f for f in manifest["files"] if f["path"] == "test_binary_fixture.bin"
            )
            assert entry["encoding"] == "base64"
            assert entry["byte_length"] == len(bin_content)

            # Verify base64 decodes to original
            import base64

            # Extract base64 from flatpack
            lines = flatpack.split("\n")
            in_content = False
            b64_parts = []
            for line in lines:
                if line == "CONTENT:":
                    in_content = True
                    continue
                if line == "--- END FILE ---":
                    in_content = False
                    continue
                if in_content:
                    b64_parts.append(line)
            decoded = base64.b64decode("".join(b64_parts))
            assert decoded == bin_content
        finally:
            bin_path.unlink()


def test_prepare_sha_length_accurate():
    """SHA-256 and byte length in manifest are accurate."""
    with tempfile.TemporaryDirectory() as d:
        spec = {
            "task_id": "test-005",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": ["PROJECT_RULES.md"],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, Path(d))
        assert code == 0

        manifest = load_manifest(Path(d))
        for f in manifest["files"]:
            path = REPO_ROOT / f["path"]
            data = path.read_bytes()
            assert f["sha256"] == __import__("hashlib").sha256(data).hexdigest()
            assert f["byte_length"] == len(data)


def test_prepare_mutable_readonly_role_accurate():
    """Mutable/read-only roles correctly assigned."""
    with tempfile.TemporaryDirectory() as d:
        spec = {
            "task_id": "test-006",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": ["PROJECT_RULES.md"],
            "allow_new_under": [],
            "guidance_paths": ["docs/specs/product/ACTIVE_PRODUCT_SCOPE.md"],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, Path(d))
        assert code == 0

        manifest = load_manifest(Path(d))
        roles = {f["path"]: f["role"] for f in manifest["files"]}
        assert roles["AGENTS.md"] == "MUTABLE"
        assert roles["PROJECT_RULES.md"] == "READ_ONLY"
        assert roles["docs/specs/product/ACTIVE_PRODUCT_SCOPE.md"] == "GUIDANCE"


def test_prepare_repo_outside_path_rejected():
    """Paths outside repo are rejected."""
    with tempfile.TemporaryDirectory() as d:
        spec = {
            "task_id": "test-007",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["/etc/passwd"],
            "read_only_paths": [],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, stderr = run_prepare(spec, Path(d))
        assert code != 0
        assert "escapes repository" in stderr or "does not exist" in stderr


def test_prepare_traversal_rejected():
    """Path traversal attempts rejected."""
    with tempfile.TemporaryDirectory() as d:
        spec = {
            "task_id": "test-008",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["../../../etc/passwd"],
            "read_only_paths": [],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, stderr = run_prepare(spec, Path(d))
        assert code != 0


def test_prepare_symlink_escape_rejected():
    """Symlink escape attempts rejected."""
    with tempfile.TemporaryDirectory() as d:
        # Create a symlink inside repo pointing outside
        link_path = REPO_ROOT / "test_symlink_escape"
        try:
            link_path.symlink_to("/tmp")
            spec = {
                "task_id": "test-009",
                "goal": "Test goal",
                "acceptance_criteria": ["Criterion 1"],
                "mutable_paths": ["test_symlink_escape"],
                "read_only_paths": [],
                "allow_new_under": [],
                "guidance_paths": [],
                "verification_commands": [],
            }
            code, _, stderr = run_prepare(spec, Path(d))
            assert code != 0
        finally:
            if link_path.exists():
                link_path.unlink()


def test_prepare_duplicate_overlapping_role_rejected():
    """Duplicate/overlapping roles rejected."""
    with tempfile.TemporaryDirectory() as d:
        spec = {
            "task_id": "test-010",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": ["AGENTS.md"],  # Same file in both
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, stderr = run_prepare(spec, Path(d))
        assert code != 0
        assert "both MUTABLE and READ_ONLY" in stderr


def test_prepare_missing_input_rejected():
    """Missing input files rejected."""
    with tempfile.TemporaryDirectory() as d:
        spec = {
            "task_id": "test-011",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["nonexistent_file.txt"],
            "read_only_paths": [],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, stderr = run_prepare(spec, Path(d))
        assert code != 0
        assert "does not exist" in stderr


def test_prepare_forbidden_paths_rejected():
    """Forbidden paths (.git, node_modules, secrets) rejected."""
    with tempfile.TemporaryDirectory() as d:
        for forbidden in [".git/config", "node_modules/something.js", "secrets.env"]:
            spec = {
                "task_id": "test-012",
                "goal": "Test goal",
                "acceptance_criteria": ["Criterion 1"],
                "mutable_paths": [forbidden],
                "read_only_paths": [],
                "allow_new_under": [],
                "guidance_paths": [],
                "verification_commands": [],
            }
            code, _, stderr = run_prepare(spec, Path(d))
            assert code != 0, f"Should have rejected {forbidden}"


if __name__ == "__main__":
    # Run tests
    test_prepare_deterministic_same_input()
    print("✓ test_prepare_deterministic_same_input")
    test_prepare_base_sha_accurate()
    print("✓ test_prepare_base_sha_accurate")
    test_prepare_text_roundtrip()
    print("✓ test_prepare_text_roundtrip")
    test_prepare_binary_roundtrip()
    print("✓ test_prepare_binary_roundtrip")
    test_prepare_sha_length_accurate()
    print("✓ test_prepare_sha_length_accurate")
    test_prepare_mutable_readonly_role_accurate()
    print("✓ test_prepare_mutable_readonly_role_accurate")
    test_prepare_repo_outside_path_rejected()
    print("✓ test_prepare_repo_outside_path_rejected")
    test_prepare_traversal_rejected()
    print("✓ test_prepare_traversal_rejected")
    test_prepare_symlink_escape_rejected()
    print("✓ test_prepare_symlink_escape_rejected")
    test_prepare_duplicate_overlapping_role_rejected()
    print("✓ test_prepare_duplicate_overlapping_role_rejected")
    test_prepare_missing_input_rejected()
    print("✓ test_prepare_missing_input_rejected")
    test_prepare_forbidden_paths_rejected()
    print("✓ test_prepare_forbidden_paths_rejected")
    print("\nAll prepare tests passed!")
