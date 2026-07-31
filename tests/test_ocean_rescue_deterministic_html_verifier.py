"""Focused tests for the deterministic HTML byte-identity verifier.

Tests use synthetic fixtures only — no production artifacts.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERIFIER = REPO_ROOT / "scripts" / "ocean_rescue" / "deterministic_html_verifier.py"


def _run_verifier(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VERIFIER), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def _write_fixture(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

SAMPLE_A = b"<!doctype html><html><head></head><body>Hello</body></html>"
SAMPLE_B = b"<!doctype html><html><head></head><body>Hello</body></html>"


def test_identical_pair_exits_zero(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, SAMPLE_A)
    _write_fixture(b, SAMPLE_B)

    result = _run_verifier(str(a), str(b))

    assert result.returncode == 0, (
        f"Expected exit 0 for identical files, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_identical_pair_output_format(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, SAMPLE_A)
    _write_fixture(b, SAMPLE_B)

    result = _run_verifier(str(a), str(b))

    assert "PASS" in result.stdout
    assert "SHA-256:" in result.stdout
    assert "Byte size:" in result.stdout


def test_first_byte_mismatch_non_zero(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, b"AAAA")
    _write_fixture(b, b"BAAB")

    result = _run_verifier(str(a), str(b))

    assert result.returncode != 0, (
        f"Expected non-zero exit for first-byte mismatch, got {result.returncode}"
    )


def test_first_byte_mismatch_output_info(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, b"AAAA")
    _write_fixture(b, b"BAAB")

    result = _run_verifier(str(a), str(b))

    assert "FAIL" in result.stdout
    assert "SHA-256 (A):" in result.stdout
    assert "SHA-256 (B):" in result.stdout
    assert "Byte size (A):" in result.stdout
    assert "Byte size (B):" in result.stdout
    assert "First differing offset: 0" in result.stdout


def test_middle_byte_mismatch_non_zero(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, b"AABB")
    _write_fixture(b, b"ABAB")

    result = _run_verifier(str(a), str(b))

    assert result.returncode != 0


def test_middle_byte_mismatch_offset(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, b"AABB")
    _write_fixture(b, b"ABAB")

    result = _run_verifier(str(a), str(b))

    assert "First differing offset: 1" in result.stdout


def test_appended_byte_mismatch_non_zero(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, b"AAAA")
    _write_fixture(b, b"AAAAZ")

    result = _run_verifier(str(a), str(b))

    assert result.returncode != 0


def test_appended_byte_mismatch_output(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, b"AAAA")
    _write_fixture(b, b"AAAAZ")

    result = _run_verifier(str(a), str(b))

    assert "FAIL" in result.stdout
    assert "Byte size (A): 4" in result.stdout
    assert "Byte size (B): 5" in result.stdout


def test_missing_file_exits_non_zero(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, SAMPLE_A)
    # b does not exist

    result = _run_verifier(str(a), str(b))

    assert result.returncode != 0
    assert "ERROR" in result.stderr


def test_both_missing_files_exits_non_zero(tmp_path: Path):
    a = tmp_path / "nonexistent_a.html"
    b = tmp_path / "nonexistent_b.html"

    result = _run_verifier(str(a), str(b))

    assert result.returncode != 0
    assert "ERROR" in result.stderr


def test_directory_input_exits_non_zero(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, SAMPLE_A)
    b.mkdir()  # make b a directory

    result = _run_verifier(str(a), str(b))

    assert result.returncode != 0
    assert "ERROR" in result.stderr


def test_json_output_identical(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, SAMPLE_A)
    _write_fixture(b, SAMPLE_B)

    result = _run_verifier(str(a), str(b), "--json")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["result"] == "PASS"
    assert "sha256" in payload
    assert "byte_size" in payload


def test_json_output_different(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, b"AAAA")
    _write_fixture(b, b"BBBB")

    result = _run_verifier(str(a), str(b), "--json")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["result"] == "FAIL"
    assert "sha256_a" in payload
    assert "sha256_b" in payload
    assert "byte_size_a" in payload
    assert "byte_size_b" in payload
    assert "first_differ_offset" in payload
    assert payload["first_differ_offset"] == 0


def test_json_output_missing_file(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "missing.html"
    _write_fixture(a, SAMPLE_A)

    result = _run_verifier(str(a), str(b), "--json")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["result"] == "ERROR"


def test_shas_are_deterministic(tmp_path: Path):
    """Same content always produces the same SHA-256."""
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    c = tmp_path / "c.html"
    content = b"deterministic content"
    _write_fixture(a, content)
    _write_fixture(b, content)
    _write_fixture(c, content)

    r1 = _run_verifier(str(a), str(b), "--json")
    r2 = _run_verifier(str(b), str(c), "--json")

    assert r1.returncode == 0
    assert r2.returncode == 0
    p1 = json.loads(r1.stdout)
    p2 = json.loads(r2.stdout)
    assert p1["sha256"] == p2["sha256"]


def test_binary_content_supported(tmp_path: Path):
    """Verifier handles null bytes and high-byte content."""
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, b"\x00\x01\x02\xff\xfe\xfd")
    _write_fixture(b, b"\x00\x01\x02\xff\xfe\xfd")

    result = _run_verifier(str(a), str(b))

    assert result.returncode == 0


def test_empty_files_identical(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, b"")
    _write_fixture(b, b"")

    result = _run_verifier(str(a), str(b))

    assert result.returncode == 0
    assert "Byte size: 0" in result.stdout


def test_empty_vs_nonempty_differs(tmp_path: Path):
    a = tmp_path / "a.html"
    b = tmp_path / "b.html"
    _write_fixture(a, b"")
    _write_fixture(b, b"x")

    result = _run_verifier(str(a), str(b))

    assert result.returncode != 0
    assert "Byte size (A): 0" in result.stdout
    assert "Byte size (B): 1" in result.stdout
