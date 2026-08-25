from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ocean_rescue" / "ocean_ai.py"


def run_prepare(spec: dict, out_dir: Path) -> subprocess.CompletedProcess[str]:
    spec_path = out_dir / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    return subprocess.run(
        ["python3", str(SCRIPT), "prepare", "--spec", str(spec_path), "--out", str(out_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def run_ingest(manifest: Path, result_zip: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python3",
            str(SCRIPT),
            "ingest",
            "--manifest",
            str(manifest),
            "--zip",
            str(result_zip),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def base_spec() -> dict:
    return {
        "task_id": "contract-regression",
        "goal": "Prove AI handoff contract",
        "acceptance_criteria": ["contract holds"],
        "mutable_paths": ["AGENTS.md"],
        "read_only_paths": [],
        "allow_new_under": [],
        "guidance_paths": [],
        "verification_commands": [],
    }


def manifest(out_dir: Path) -> dict:
    return json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))


def write_result_zip(
    path: Path,
    packet: dict,
    files: dict[str, bytes],
    prefix: str = "",
) -> None:
    if prefix and not prefix.endswith("/"):
        prefix += "/"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel_path, data in files.items():
            archive.writestr(prefix + rel_path, data)
        archive.writestr(
            prefix + ".ocean-rescue-ai-receipt.json",
            json.dumps({"packetId": packet["packetId"], "base": packet["baseSha"]}),
        )


def test_prepare_outputs_are_byte_deterministic() -> None:
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        first_path = Path(first)
        second_path = Path(second)
        assert run_prepare(base_spec(), first_path).returncode == 0
        assert run_prepare(base_spec(), second_path).returncode == 0
        assert (first_path / "manifest.json").read_bytes() == (
            second_path / "manifest.json"
        ).read_bytes()
        assert (first_path / "packet.txt").read_bytes() == (
            second_path / "packet.txt"
        ).read_bytes()


def test_packet_identity_includes_verification_commands() -> None:
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        one = base_spec()
        two = base_spec()
        one["verification_commands"] = [["python3", "-c", "print(1)"]]
        two["verification_commands"] = [["python3", "-c", "print(2)"]]
        assert run_prepare(one, Path(first)).returncode == 0
        assert run_prepare(two, Path(second)).returncode == 0
        assert manifest(Path(first))["packetId"] != manifest(Path(second))["packetId"]


def test_existing_secret_like_file_is_rejected() -> None:
    secret = REPO_ROOT / "secrets.env"
    secret.write_text("TOKEN=not-a-real-secret", encoding="utf-8")
    try:
        with tempfile.TemporaryDirectory() as out:
            spec = base_spec()
            spec["mutable_paths"] = ["secrets.env"]
            result = run_prepare(spec, Path(out))
            assert result.returncode != 0
            assert "Secret-like" in result.stderr
    finally:
        secret.unlink(missing_ok=True)


def test_targeted_pixi_skill_guidance_is_allowed_and_identity_bound() -> None:
    skill_dir = (
        REPO_ROOT
        / "domains"
        / "ocean-rescue"
        / "node_modules"
        / "pixi.js"
        / "skills"
        / "__ocean_ai_contract_test__"
    )
    skill = skill_dir / "SKILL.md"
    skill_dir.mkdir(parents=True, exist_ok=True)
    try:
        skill.write_text("Pixi guidance v1\n", encoding="utf-8")
        spec = base_spec()
        spec["guidance_paths"] = [
            "domains/ocean-rescue/node_modules/pixi.js/skills/"
            "__ocean_ai_contract_test__/SKILL.md"
        ]
        with tempfile.TemporaryDirectory() as first:
            first_path = Path(first)
            result = run_prepare(spec, first_path)
            assert result.returncode == 0, result.stderr
            first_packet = manifest(first_path)
            guidance = next(
                item for item in first_packet["files"] if item["role"] == "GUIDANCE"
            )
            assert guidance["path"].endswith("SKILL.md")
            assert "Pixi guidance v1" in (first_path / "packet.txt").read_text(
                encoding="utf-8"
            )

        skill.write_text("Pixi guidance v2\n", encoding="utf-8")
        with tempfile.TemporaryDirectory() as second:
            second_path = Path(second)
            result = run_prepare(spec, second_path)
            assert result.returncode == 0, result.stderr
            assert first_packet["packetId"] != manifest(second_path)["packetId"]
    finally:
        shutil.rmtree(skill_dir, ignore_errors=True)


def test_protected_surface_cannot_be_declared_mutable() -> None:
    with tempfile.TemporaryDirectory() as out:
        spec = base_spec()
        spec["mutable_paths"] = ["domains/ocean-rescue/package.json"]
        result = run_prepare(spec, Path(out))
        assert result.returncode != 0
        assert "Protected surface" in result.stderr


def test_wrapped_project_zip_applies_candidate_bytes() -> None:
    target = REPO_ROOT / "AGENTS.md"
    original = target.read_bytes()
    changed = original + b"\n# ocean-ai wrapped-root proof\n"
    try:
        with tempfile.TemporaryDirectory() as out:
            out_path = Path(out)
            assert run_prepare(base_spec(), out_path).returncode == 0
            packet = manifest(out_path)
            result_zip = out_path / "wrapped.zip"
            write_result_zip(
                result_zip,
                packet,
                {"AGENTS.md": changed},
                prefix="ai-studio-export",
            )
            result = run_ingest(out_path / "manifest.json", result_zip)
            assert result.returncode == 0, result.stderr
            assert target.read_bytes() == changed
    finally:
        target.write_bytes(original)


def test_untracked_pre_ingest_worktree_is_rejected() -> None:
    marker = REPO_ROOT / "ocean_ai_untracked_dirty_marker"
    with tempfile.TemporaryDirectory() as out:
        out_path = Path(out)
        assert run_prepare(base_spec(), out_path).returncode == 0
        packet = manifest(out_path)
        result_zip = out_path / "result.zip"
        write_result_zip(result_zip, packet, {"AGENTS.md": (REPO_ROOT / "AGENTS.md").read_bytes()})
        marker.write_text("dirty", encoding="utf-8")
        try:
            result = run_ingest(out_path / "manifest.json", result_zip)
            assert result.returncode != 0
            assert "not clean" in result.stderr
        finally:
            marker.unlink(missing_ok=True)
