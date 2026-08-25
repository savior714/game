#!/usr/bin/env python3
"""
Tests for ocean_ai.py ingest command - deterministic/security/freshness contracts
"""

import json
import tempfile
import subprocess
import zipfile
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


def run_ingest(manifest_path: Path, zip_path: Path) -> tuple[int, str, str]:
    """Run ingest command and return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "ingest",
            "--manifest",
            str(manifest_path),
            "--zip",
            str(zip_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def create_test_zip(zip_path: Path, files: dict, receipt: dict, changes: dict = None):
    """Create a test ZIP file with given files and receipt."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path, content in files.items():
            zf.writestr(rel_path, content)
        zf.writestr(".ocean-rescue-ai-receipt.json", json.dumps(receipt))
        if changes:
            zf.writestr(".ocean-rescue-ai-changes.json", json.dumps(changes))


def get_head_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_ingest_valid_zip_acceptance():
    """Valid ZIP with correct receipt is accepted."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        # Prepare
        spec = {
            "task_id": "test-ingest-001",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": ["PROJECT_RULES.md"],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, d)
        assert code == 0

        manifest_path = d / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        # Create valid ZIP with no changes (just the same files)
        files = {}
        for f in manifest["files"]:
            orig = REPO_ROOT / f["path"]
            files[f["path"]] = orig.read_bytes()

        receipt = {"packetId": manifest["packetId"], "base": manifest["baseSha"]}
        zip_path = d / "result.zip"
        create_test_zip(zip_path, files, receipt)

        # Ingest
        code, stdout, stderr = run_ingest(manifest_path, zip_path)
        assert code == 0, f"Ingest failed: {stderr}"
        assert "SUCCESS" in stdout


def test_ingest_wrong_packetid_rejected():
    """Wrong packetId in receipt is rejected."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        spec = {
            "task_id": "test-ingest-002",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": [],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, d)
        assert code == 0

        manifest_path = d / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        files = {
            f["path"]: (REPO_ROOT / f["path"]).read_bytes() for f in manifest["files"]
        }
        receipt = {"packetId": "wrong-packet-id", "base": manifest["baseSha"]}
        zip_path = d / "result.zip"
        create_test_zip(zip_path, files, receipt)

        code, _, stderr = run_ingest(manifest_path, zip_path)
        assert code != 0
        assert "packetId mismatch" in stderr


def test_ingest_wrong_base_rejected():
    """Wrong base SHA in receipt is rejected."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        spec = {
            "task_id": "test-ingest-003",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": [],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, d)
        assert code == 0

        manifest_path = d / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        files = {
            f["path"]: (REPO_ROOT / f["path"]).read_bytes() for f in manifest["files"]
        }
        receipt = {"packetId": manifest["packetId"], "base": "wrong-base-sha"}
        zip_path = d / "result.zip"
        create_test_zip(zip_path, files, receipt)

        code, _, stderr = run_ingest(manifest_path, zip_path)
        assert code != 0
        assert "base mismatch" in stderr


def test_ingest_stale_head_rejected():
    """Stale current HEAD (not matching manifest base) is rejected."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        spec = {
            "task_id": "test-ingest-004",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": [],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, d)
        assert code == 0

        manifest_path = d / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        # Modify a file to change HEAD
        test_file = REPO_ROOT / "test_stale_head.txt"
        test_file.write_text("stale")
        subprocess.run(["git", "add", "test_stale_head.txt"], cwd=REPO_ROOT, check=True)
        subprocess.run(["git", "commit", "-m", "stale"], cwd=REPO_ROOT, check=True)

        try:
            files = {
                f["path"]: (REPO_ROOT / f["path"]).read_bytes()
                for f in manifest["files"]
            }
            receipt = {"packetId": manifest["packetId"], "base": manifest["baseSha"]}
            zip_path = d / "result.zip"
            create_test_zip(zip_path, files, receipt)

            code, _, stderr = run_ingest(manifest_path, zip_path)
            assert code != 0
            assert "HEAD" in stderr
        finally:
            # Clean up
            subprocess.run(
                ["git", "reset", "--hard", "HEAD~1"], cwd=REPO_ROOT, check=True
            )
            if test_file.exists():
                test_file.unlink()


def test_ingest_dirty_worktree_rejected():
    """Dirty pre-ingest worktree is rejected."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        spec = {
            "task_id": "test-ingest-005",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": [],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, d)
        assert code == 0

        manifest_path = d / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        # Make worktree dirty by modifying a tracked file
        agents_file = REPO_ROOT / "AGENTS.md"
        original_content = agents_file.read_text()
        agents_file.write_text(original_content + "\n# DIRTY")

        try:
            files = {
                f["path"]: (REPO_ROOT / f["path"]).read_bytes()
                for f in manifest["files"]
            }
            receipt = {"packetId": manifest["packetId"], "base": manifest["baseSha"]}
            zip_path = d / "result.zip"
            create_test_zip(zip_path, files, receipt)

            code, _, stderr = run_ingest(manifest_path, zip_path)
            assert code != 0
            assert "not clean" in stderr
        finally:
            agents_file.write_text(original_content)


def test_ingest_traversal_zip_rejected():
    """ZIP with path traversal is rejected."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        spec = {
            "task_id": "test-ingest-006",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": [],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, d)
        assert code == 0

        manifest_path = d / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        files = {"../escape.txt": b"escape"}
        receipt = {"packetId": manifest["packetId"], "base": manifest["baseSha"]}
        zip_path = d / "result.zip"
        create_test_zip(zip_path, files, receipt)

        code, _, stderr = run_ingest(manifest_path, zip_path)
        assert code != 0
        assert "traversal" in stderr.lower()


def test_ingest_duplicate_normalized_zip_rejected():
    """ZIP with duplicate normalized paths is rejected."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        spec = {
            "task_id": "test-ingest-007",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": [],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, d)
        assert code == 0

        manifest_path = d / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        files = {
            "AGENTS.md": b"content1",
            "AGENTS.md/": b"content2",  # Normalizes to same
        }
        receipt = {"packetId": manifest["packetId"], "base": manifest["baseSha"]}
        zip_path = d / "result.zip"
        create_test_zip(zip_path, files, receipt)

        code, _, stderr = run_ingest(manifest_path, zip_path)
        assert code != 0
        assert "duplicate" in stderr.lower()


def test_ingest_readonly_mutation_rejected():
    """READ_ONLY file mutation is rejected."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        spec = {
            "task_id": "test-ingest-008",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": [],
            "read_only_paths": ["AGENTS.md"],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, d)
        assert code == 0

        manifest_path = d / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        files = {"AGENTS.md": b"MUTATED CONTENT"}
        receipt = {"packetId": manifest["packetId"], "base": manifest["baseSha"]}
        zip_path = d / "result.zip"
        create_test_zip(zip_path, files, receipt)

        code, _, stderr = run_ingest(manifest_path, zip_path)
        assert code != 0
        assert "READ_ONLY file mutated" in stderr


def test_ingest_unexpected_react_scaffold_rejected():
    """Unexpected React/package/scaffold files are rejected."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        spec = {
            "task_id": "test-ingest-009",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": [],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, d)
        assert code == 0

        manifest_path = d / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        files = {
            "AGENTS.md": (REPO_ROOT / "AGENTS.md").read_bytes(),
            "package.json": b'{"name": "react-app"}',  # Unexpected scaffold
        }
        receipt = {"packetId": manifest["packetId"], "base": manifest["baseSha"]}
        zip_path = d / "result.zip"
        create_test_zip(zip_path, files, receipt)

        code, _, stderr = run_ingest(manifest_path, zip_path)
        assert code != 0
        assert "Unexpected file" in stderr


def test_ingest_unauthorized_new_path_rejected():
    """New files outside allow_new_under are rejected."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        spec = {
            "task_id": "test-ingest-010",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": [],
            "allow_new_under": ["scripts/ocean_rescue"],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, d)
        assert code == 0

        manifest_path = d / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        files = {
            "AGENTS.md": (REPO_ROOT / "AGENTS.md").read_bytes(),
            "unauthorized/new_file.txt": b"unauthorized",
        }
        receipt = {"packetId": manifest["packetId"], "base": manifest["baseSha"]}
        zip_path = d / "result.zip"
        create_test_zip(zip_path, files, receipt)

        code, _, stderr = run_ingest(manifest_path, zip_path)
        assert code != 0
        assert "Unexpected file" in stderr


def test_ingest_allowed_new_path_accepted():
    """New files under allow_new_under are accepted."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        spec = {
            "task_id": "test-ingest-011",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": [],
            "allow_new_under": ["scripts/ocean_rescue"],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, d)
        assert code == 0

        manifest_path = d / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        files = {
            "AGENTS.md": (REPO_ROOT / "AGENTS.md").read_bytes(),
            "scripts/ocean_rescue/new_allowed_file.py": b"# new file",
        }
        receipt = {"packetId": manifest["packetId"], "base": manifest["baseSha"]}
        zip_path = d / "result.zip"
        create_test_zip(zip_path, files, receipt)

        code, stdout, stderr = run_ingest(manifest_path, zip_path)
        assert code == 0, f"Ingest failed: {stderr}"
        assert "SUCCESS" in stdout


def test_ingest_verification_failure_propagated():
    """Verification command failure is propagated."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        spec = {
            "task_id": "test-ingest-012",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": ["AGENTS.md"],
            "read_only_paths": [],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [["python3", "-c", "import sys; sys.exit(1)"]],
        }
        code, _, _ = run_prepare(spec, d)
        assert code == 0

        manifest_path = d / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        files = {
            f["path"]: (REPO_ROOT / f["path"]).read_bytes() for f in manifest["files"]
        }
        receipt = {"packetId": manifest["packetId"], "base": manifest["baseSha"]}
        zip_path = d / "result.zip"
        create_test_zip(zip_path, files, receipt)

        code, _, stderr = run_ingest(manifest_path, zip_path)
        assert code != 0
        assert "Verification failed" in stderr or "Command failed" in stderr


def test_ingest_no_mutation_before_validation():
    """Worktree is not mutated before full validation passes."""
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        spec = {
            "task_id": "test-ingest-013",
            "goal": "Test goal",
            "acceptance_criteria": ["Criterion 1"],
            "mutable_paths": [],
            "read_only_paths": ["AGENTS.md"],
            "allow_new_under": [],
            "guidance_paths": [],
            "verification_commands": [],
        }
        code, _, _ = run_prepare(spec, d)
        assert code == 0

        manifest_path = d / "manifest.json"
        manifest = json.loads(manifest_path.read_text())

        # Create ZIP that will fail validation (READ_ONLY mutation)
        files = {"AGENTS.md": b"MUTATED"}
        receipt = {"packetId": manifest["packetId"], "base": manifest["baseSha"]}
        zip_path = d / "result.zip"
        create_test_zip(zip_path, files, receipt)

        # Get original content
        original = (REPO_ROOT / "AGENTS.md").read_bytes()

        code, _, _ = run_ingest(manifest_path, zip_path)
        assert code != 0

        # Verify worktree unchanged
        current = (REPO_ROOT / "AGENTS.md").read_bytes()
        assert current == original, "Worktree was mutated before validation!"


if __name__ == "__main__":
    test_ingest_valid_zip_acceptance()
    print("✓ test_ingest_valid_zip_acceptance")
    test_ingest_wrong_packetid_rejected()
    print("✓ test_ingest_wrong_packetid_rejected")
    test_ingest_wrong_base_rejected()
    print("✓ test_ingest_wrong_base_rejected")
    test_ingest_stale_head_rejected()
    print("✓ test_ingest_stale_head_rejected")
    test_ingest_dirty_worktree_rejected()
    print("✓ test_ingest_dirty_worktree_rejected")
    test_ingest_traversal_zip_rejected()
    print("✓ test_ingest_traversal_zip_rejected")
    test_ingest_duplicate_normalized_zip_rejected()
    print("✓ test_ingest_duplicate_normalized_zip_rejected")
    test_ingest_readonly_mutation_rejected()
    print("✓ test_ingest_readonly_mutation_rejected")
    test_ingest_unexpected_react_scaffold_rejected()
    print("✓ test_ingest_unexpected_react_scaffold_rejected")
    test_ingest_unauthorized_new_path_rejected()
    print("✓ test_ingest_unauthorized_new_path_rejected")
    test_ingest_allowed_new_path_accepted()
    print("✓ test_ingest_allowed_new_path_accepted")
    test_ingest_verification_failure_propagated()
    print("✓ test_ingest_verification_failure_propagated")
    test_ingest_no_mutation_before_validation()
    print("✓ test_ingest_no_mutation_before_validation")
    print("\nAll ingest tests passed!")
