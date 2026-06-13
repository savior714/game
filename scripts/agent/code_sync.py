# @code-sync-lock { id: "code_sync_engine", hash: "sha256-0536eaa705464d58a643fc77fc2e4b306be1994e27d80bdc6e30d0881475a0af", spec: "docs/specs/technical/spec_soap_mode.md" }
#!/usr/bin/env python3
"""Code Integrity Lock Engine (code-sync).

Validates, auto-inserts, and updates cryptographic code locks
to ensure synchronization between critical implementation boundaries.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# @code-sync-lock parse pattern
LOCK_PATTERN = re.compile(
    r"(?://|#|{/\*)\s*@code-sync-lock\s*(\{[^}]+\})", re.IGNORECASE
)
UNLOCK_PATTERN = re.compile(
    r"(?://|#|{/\*)\s*@code-sync-unlock\s*\{[^}]*id\s*:\s*\"([^\"]+)\"[^}]*\}",
    re.IGNORECASE,
)

# Regex to detect function/class boundaries for auto-insert
_TS_FUNCTION = re.compile(
    r"^(?:export\s+)?(?:(?:async\s+)?)?(?:"
    r"function\s+\w+|const\s+\w+\s*=\s*(?:async\s+)?\(.*?\)\s*=>|"
    r"(?:\w+)\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*\{)"
)
_PY_FUNCTION = re.compile(r"^(?:async\s+)?def\s+\w+\s*\(")


def compute_normalized_hash(code_lines: list[str]) -> str:
    """Calculates a whitespace-robust SHA-256 hash of code block lines.

    Normalization: strip comments, collapse whitespace to single space,
    trim leading/trailing.
    """
    normalized_lines = []
    for line in code_lines:
        cleaned = line.strip()
        if not cleaned:
            continue
        # Strip single-line comments
        if cleaned.startswith("//") or cleaned.startswith("#"):
            continue
        # Collapse internal whitespace to single space
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            normalized_lines.append(cleaned)
    normalized_text = "\n".join(normalized_lines)
    return "sha256-" + hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()


def parse_metadata(meta_str: str) -> dict[str, str]:
    """Parses JSON-like metadata inside the lock comment."""
    cleaned = meta_str.strip()
    cleaned = re.sub(r"([a-zA-Z0-9_]+)\s*:", r'"\1":', cleaned)
    cleaned = re.sub(r':\s*\'([^\']*)\'', r': "\1"', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        meta = {}
        for m in re.finditer(r'([a-zA-Z0-9_]+)\s*:\s*"([^"]+)"', meta_str):
            meta[m.group(1)] = m.group(2)
        return meta


def scan_file_locks(filepath: Path) -> list[dict[str, object]]:
    """Scans a file for code-sync lock blocks."""
    try:
        content = filepath.read_text("utf-8")
    except Exception:
        return []

    lines = content.splitlines()
    locks = []
    active_lock = None
    block_start_idx = -1

    for idx, line in enumerate(lines):
        lock_match = LOCK_PATTERN.search(line)
        if lock_match:
            meta_str = lock_match.group(1)
            meta = parse_metadata(meta_str)
            if "id" in meta:
                active_lock = meta
                block_start_idx = idx + 1
            continue

        unlock_match = UNLOCK_PATTERN.search(line)
        if unlock_match:
            unlock_id = unlock_match.group(1)
            if active_lock and active_lock.get("id") == unlock_id:
                block_lines = lines[block_start_idx:idx]
                expected_hash = active_lock.get("hash", "")
                calculated_hash = compute_normalized_hash(block_lines)

                locks.append({
                    "id": unlock_id,
                    "filepath": filepath,
                    "start_line": block_start_idx + 1,
                    "end_line": idx,
                    "expected_hash": expected_hash,
                    "calculated_hash": calculated_hash,
                    "spec": active_lock.get("spec", ""),
                    "block_lines": block_lines,
                })
                active_lock = None
                block_start_idx = -1

    return locks


def iter_source_files(target_extensions: set[str]) -> list[Path]:
    """Efficiently walks REPO_ROOT skipping ignored directories."""
    paths = []
    ignored = {"node_modules", ".next", "dist", ".git", "__pycache__", "build", "out", "venv", ".venv"}
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in ignored]
        for file in files:
            p = Path(root) / file
            if p.suffix in target_extensions:
                paths.append(p)
    return paths


def check_all_locks() -> int:
    """Scans the repository and validates all code integrity locks."""
    print("🔍 Scanning repository for code integrity locks...")
    target_extensions = {".tsx", ".ts", ".jsx", ".js", ".py", ".css"}
    error_count = 0
    lock_count = 0

    for p in iter_source_files(target_extensions):
        file_locks = scan_file_locks(p)
        for lock in file_locks:
            lock_count += 1
            rel_path = p.relative_to(REPO_ROOT).as_posix()
            if not lock["expected_hash"]:
                print(
                    f"⚠️  [WARN] Lock ID '{lock['id']}' in {rel_path}:{lock['start_line']} has no hash defined."
                )
                continue

            if lock["expected_hash"] != lock["calculated_hash"]:
                print(
                    f"❌ [FAIL] Integrity Lock Violation!"
                    f"\n   Lock ID:  {lock['id']}"
                    f"\n   File:     {rel_path}:{lock['start_line']}-{lock['end_line']}"
                    f"\n   Expected: {lock['expected_hash']}"
                    f"\n   Actual:   {lock['calculated_hash']}"
                    f"\n   Referenced Spec: {lock['spec'] or 'None'}"
                )
                error_count += 1
            else:
                print(f"✅ [PASS] Lock ID '{lock['id']}' is secure.")

    print(f"\n📊 Summary: Checked {lock_count} lock(s), {error_count} violation(s) found.")
    return error_count


def _detect_comment_style(path: Path) -> str:
    if path.suffix in (".py", ".yml", ".yaml"):
        return "py"
    if "{/*" in path.read_text("utf-8", errors="")[:500]:
        return "jsx"
    return "ts"


def _find_function_start(lines: list[str], start_from: int = 0) -> int | None:
    for i in range(start_from, len(lines)):
        raw = lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("#") or stripped.startswith("/*"):
            continue
        code_only = re.sub(r"//.*$", "", stripped)
        if _TS_FUNCTION.match(code_only) or _PY_FUNCTION.match(code_only):
            return i
    return None


def _find_function_end(lines: list[str], func_start: int) -> int | None:
    depth = 0
    started = False
    for i in range(func_start, len(lines)):
        for ch in lines[i]:
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
        if started and depth <= 0:
            return i
    return None


def apply_lock(lock_id: str, file_path: str, spec: str | None,
               lines_range: tuple[int, int] | None = None) -> int:
    path = Path(file_path).resolve()
    if not path.exists():
        print(f"❌ File not found: {file_path}")
        return 1

    content = path.read_text("utf-8")
    lines = content.splitlines()
    comment_style = _detect_comment_style(path)

    start_idx = -1
    end_idx = -1
    lock_comment_line = ""

    for idx, line in enumerate(lines):
        m = LOCK_PATTERN.search(line)
        if m:
            meta = parse_metadata(m.group(1))
            if meta.get("id") == lock_id:
                start_idx = idx
                lock_comment_line = line
                continue
        um = UNLOCK_PATTERN.search(line)
        if um and um.group(1) == lock_id:
            end_idx = idx
            break

    if start_idx != -1 and end_idx != -1:
        block_lines = lines[start_idx + 1 : end_idx]
        h = compute_normalized_hash(block_lines)
        spec_path = spec or "docs/specs/technical/spec_soap_mode.md"

        if comment_style == "py":
            new_comment = f"# @code-sync-lock {{ id: \"{lock_id}\", hash: \"{h}\", spec: \"{spec_path}\" }}"
        elif "{/*" in lock_comment_line:
            indent = len(lock_comment_line) - len(lock_comment_line.lstrip())
            new_comment = f"{' ' * indent}{{/* @code-sync-lock {{ id: \"{lock_id}\", hash: \"{h}\", spec: \"{spec_path}\" }} */}}"
        else:
            new_comment = f"// @code-sync-lock {{ id: \"{lock_id}\", hash: \"{h}\", spec: \"{spec_path}\" }}"

        lines[start_idx] = new_comment
        path.write_text("\n".join(lines) + "\n", "utf-8")
        print(f"🔒 Updated existing lock '{lock_id}' in {file_path}.")
        print(f"   Hash: {h}")
        return 0

    print(f"ℹ️  No existing lock pair for '{lock_id}' in {file_path}.")
    print("   Auto-inserting lock comments …")

    func_end = 0
    func_start = 0

    if lines_range:
        block_start, block_end = lines_range
        if block_start < 1 or block_end > len(lines):
            print(f"❌ Line range {block_start}-{block_end} out of bounds (file has {len(lines)} lines).")
            return 1
        block_lines = lines[block_start - 1 : block_end]
        insert_before = block_start - 1
    else:
        func_start = _find_function_start(lines)
        if func_start is None:
            print("❌ Could not auto-detect a function/class boundary.")
            print("   Hint: use --lines START-END to specify the range manually.")
            return 1
        func_end = _find_function_end(lines, func_start)
        if func_end is None:
            print(f"❌ Could not find closing brace for function at line {func_start + 1}.")
            return 1
        block_lines = lines[func_start + 1 : func_end]
        insert_before = func_start

    h = compute_normalized_hash(block_lines)
    spec_path = spec or "docs/specs/technical/spec_soap_mode.md"

    if comment_style == "py":
        lock_comment = f"# @code-sync-lock {{ id: \"{lock_id}\", hash: \"{h}\", spec: \"{spec_path}\" }}"
        unlock_comment = f"# @code-sync-unlock {{ id: \"{lock_id}\" }}"
    elif comment_style == "jsx":
        indent = len(lines[insert_before]) - len(lines[insert_before].lstrip()) if insert_before < len(lines) else 0
        lock_comment = f"{' ' * indent}{{/* @code-sync-lock {{ id: \"{lock_id}\", hash: \"{h}\", spec: \"{spec_path}\" }} */}}"
        unlock_comment = f"{' ' * indent}{{/* @code-sync-unlock {{ id: \"{lock_id}\" }} */}}"
    else:
        lock_comment = f"// @code-sync-lock {{ id: \"{lock_id}\", hash: \"{h}\", spec: \"{spec_path}\" }}"
        unlock_comment = f"// @code-sync-unlock {{ id: \"{lock_id}\" }}"

    lines.insert(insert_before, lock_comment)
    if lines_range:
        lines.insert(insert_before + 1 + len(block_lines), unlock_comment)
    else:
        lines.insert(int(func_end) + 2, unlock_comment)

    path.write_text("\n".join(lines) + "\n", "utf-8")
    print(f"🔒 Success! Created lock '{lock_id}' in {file_path}.")
    print(f"   Lines: {insert_before + 1}–{insert_before + len(block_lines)}")
    print(f"   Hash:  {h}")
    return 0


def update_lock(lock_id: str) -> int:
    print(f"🔄 Searching for lock ID '{lock_id}' to update...")
    target_extensions = {".tsx", ".ts", ".jsx", ".js", ".py", ".css"}
    found_lock = None

    for p in iter_source_files(target_extensions):
        file_locks = scan_file_locks(p)
        for lock in file_locks:
            if lock["id"] == lock_id:
                found_lock = lock
                break
        if found_lock:
            break

    if not found_lock:
        print(f"❌ Lock ID '{lock_id}' not found anywhere in the repository.")
        return 1

    filepath = found_lock["filepath"]
    content = filepath.read_text("utf-8")
    lines = content.splitlines()

    start_line_idx = found_lock["start_line"] - 2
    block_lines = lines[
        found_lock["start_line"] - 1 : found_lock["end_line"]
    ]
    new_hash = compute_normalized_hash(block_lines)

    orig_line = lines[start_line_idx]
    replaced_line = re.sub(
        r'hash\s*:\s*"[^"]*"', f'hash: "{new_hash}"', orig_line
    )
    if replaced_line == orig_line:
        replaced_line = re.sub(
            r'id\s*:\s*"([^"]+)"',
            f'id: "\\1", hash: "{new_hash}"',
            orig_line,
        )

    lines[start_line_idx] = replaced_line
    filepath.write_text("\n".join(lines) + "\n", "utf-8")
    print(f"✅ Success! Updated lock ID '{lock_id}' in {filepath.relative_to(REPO_ROOT).as_posix()}.")
    print(f"   New Hash: {new_hash}")
    return 0
# @code-sync-unlock { id: "code_sync_engine" }
