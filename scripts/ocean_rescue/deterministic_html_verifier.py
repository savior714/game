#!/usr/bin/env python3
"""Deterministic HTML byte-identity verifier.

Compares two single-HTML files for byte-identical content and reports
SHA-256 hashes, byte sizes, and first differing offset when they differ.

Exit codes:
  0  — files are byte-identical
  1  — files differ or input error
  2  — unexpected internal error
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path


def read_bytes_strict(path: Path) -> bytes:
    """Read file as raw bytes. Raises on any failure."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if path.is_dir():
        raise IsADirectoryError(f"Path is a directory: {path}")
    return path.read_bytes()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def first_differ_offset(a: bytes, b: bytes) -> int | None:
    """Return the byte offset of the first difference, or None if identical."""
    limit = min(len(a), len(b))
    for i in range(limit):
        if a[i] != b[i]:
            return i
    return None


def compare(file_a: Path, file_b: Path, *, json_output: bool = False) -> int:
    """Compare two files. Returns exit code."""
    try:
        data_a = read_bytes_strict(file_a)
        data_b = read_bytes_strict(file_b)
    except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
        if json_output:
            print(json.dumps({"result": "ERROR", "error": str(e)}))
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    hash_a = sha256_hex(data_a)
    hash_b = sha256_hex(data_b)
    size_a = len(data_a)
    size_b = len(data_b)

    identical = (hash_a == hash_b) and (size_a == size_b)

    if identical:
        if json_output:
            print(
                json.dumps(
                    {
                        "result": "PASS",
                        "sha256": hash_a,
                        "byte_size": size_a,
                    }
                )
            )
        else:
            print("PASS: files are byte-identical")
            print(f"  SHA-256:   {hash_a}")
            print(f"  Byte size: {size_a}")
        return 0

    offset = first_differ_offset(data_a, data_b)

    if json_output:
        print(
            json.dumps(
                {
                    "result": "FAIL",
                    "sha256_a": hash_a,
                    "sha256_b": hash_b,
                    "byte_size_a": size_a,
                    "byte_size_b": size_b,
                    "first_differ_offset": offset,
                }
            )
        )
    else:
        print("FAIL: files differ")
        print(f"  SHA-256 (A):   {hash_a}")
        print(f"  SHA-256 (B):   {hash_b}")
        print(f"  Byte size (A): {size_a}")
        print(f"  Byte size (B): {size_b}")
        if offset is not None:
            print(f"  First differing offset: {offset}")
        else:
            print(
                "  First differing offset: N/A (different sizes, common prefix identical)"
            )

    return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministic HTML byte-identity verifier",
    )
    parser.add_argument("file_a", help="Path to first HTML file")
    parser.add_argument("file_b", help="Path to second HTML file")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output result as JSON",
    )
    args = parser.parse_args()

    try:
        exit_code = compare(
            Path(args.file_a),
            Path(args.file_b),
            json_output=args.json_output,
        )
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        exit_code = 2

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
