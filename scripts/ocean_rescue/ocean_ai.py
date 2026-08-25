#!/usr/bin/env python3
"""
Ocean Rescue AI Studio Handoff CLI

prepare: Create deterministic flatpack + manifest for AI Studio
ingest:  Validate and apply AI Studio ZIP result to isolated BUILD worktree
"""

import argparse
import base64
import hashlib
import json
import os
import sys
import zipfile
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone


REPO_ROOT = Path(__file__).resolve().parents[2]
OCEAN_RESCUE_ROOT = REPO_ROOT / "domains" / "ocean-rescue"


@dataclass
class FileEntry:
    path: str
    role: str  # MUTABLE, READ_ONLY, GUIDANCE
    byte_length: int
    sha256: str
    encoding: str  # "utf-8" or "base64"
    content: Optional[str] = None  # Only in flatpack


@dataclass
class Manifest:
    packet_id: str
    base_sha: str
    created_at: str
    spec: Dict[str, Any]
    files: List[FileEntry]


@dataclass
class TaskSpec:
    task_id: str
    goal: str
    acceptance_criteria: List[str]
    mutable_paths: List[str]
    read_only_paths: List[str]
    allow_new_under: List[str] = field(default_factory=list)
    guidance_paths: List[str] = field(default_factory=list)
    verification_commands: List[List[str]] = field(default_factory=list)


def get_repo_base_sha() -> str:
    """Get current repository HEAD SHA."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_file_bytes(path: Path) -> bytes:
    return path.read_bytes()


def read_file_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def is_binary_file(path: Path) -> bool:
    """Heuristic: treat as binary if not valid UTF-8 or contains null bytes."""
    try:
        data = path.read_bytes()
        if b"\x00" in data:
            return True
        data.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def normalize_repo_path(path: str) -> str:
    """Normalize to repository-relative POSIX path."""
    return path.replace("\\", "/").lstrip("./")


def resolve_and_validate_path(repo_root: Path, rel_path: str) -> Path:
    """Resolve repository-relative path and ensure it stays within repo."""
    rel_path = normalize_repo_path(rel_path)
    abs_path = (repo_root / rel_path).resolve()
    repo_root_resolved = repo_root.resolve()
    try:
        abs_path.relative_to(repo_root_resolved)
    except ValueError:
        raise ValueError(f"Path escapes repository: {rel_path}")
    return abs_path


def collect_files(spec: TaskSpec) -> List[FileEntry]:
    """Collect all files specified in the task spec."""
    files = []
    seen_paths = set()

    def add_file(rel_path: str, role: str):
        norm = normalize_repo_path(rel_path)
        if norm in seen_paths:
            raise ValueError(f"Duplicate path in spec: {norm}")
        seen_paths.add(norm)

        abs_path = resolve_and_validate_path(REPO_ROOT, norm)
        if not abs_path.exists():
            raise FileNotFoundError(f"Specified path does not exist: {norm}")
        if not abs_path.is_file():
            raise ValueError(f"Path is not a file: {norm}")

        data = read_file_bytes(abs_path)
        sha = compute_sha256(data)
        is_bin = is_binary_file(abs_path)

        entry = FileEntry(
            path=norm,
            role=role,
            byte_length=len(data),
            sha256=sha,
            encoding="base64" if is_bin else "utf-8",
            content=base64.b64encode(data).decode("ascii") if is_bin else data.decode("utf-8")
        )
        files.append(entry)

    # Check for overlaps between roles
    mutable_set = set(normalize_repo_path(p) for p in spec.mutable_paths)
    readonly_set = set(normalize_repo_path(p) for p in spec.read_only_paths)
    guidance_set = set(normalize_repo_path(p) for p in spec.guidance_paths)
    allow_new_set = set(normalize_repo_path(p) for p in spec.allow_new_under)

    overlap = mutable_set & readonly_set
    if overlap:
        raise ValueError(f"Paths listed as both MUTABLE and READ_ONLY: {overlap}")
    overlap = mutable_set & guidance_set
    if overlap:
        raise ValueError(f"Paths listed as both MUTABLE and GUIDANCE: {overlap}")
    overlap = readonly_set & guidance_set
    if overlap:
        raise ValueError(f"Paths listed as both READ_ONLY and GUIDANCE: {overlap}")

    # Check forbidden paths
    forbidden_prefixes = [".git", "node_modules", "__pycache__", ".pytest_cache"]
    for p in list(mutable_set) + list(readonly_set) + list(guidance_set):
        for forbidden in forbidden_prefixes:
            if p.startswith(forbidden + "/") or p == forbidden:
                raise ValueError(f"Forbidden path in spec: {p} (matches {forbidden})")

    for p in spec.mutable_paths:
        add_file(p, "MUTABLE")
    for p in spec.read_only_paths:
        add_file(p, "READ_ONLY")
    for p in spec.guidance_paths:
        add_file(p, "GUIDANCE")

    return files


def generate_packet_id(base_sha: str, spec: TaskSpec) -> str:
    """Generate deterministic packet ID from base SHA and spec content."""
    spec_json = json.dumps({
        "task_id": spec.task_id,
        "goal": spec.goal,
        "acceptance_criteria": spec.acceptance_criteria,
        "mutable_paths": sorted(spec.mutable_paths),
        "read_only_paths": sorted(spec.read_only_paths),
        "allow_new_under": sorted(spec.allow_new_under),
        "guidance_paths": sorted(spec.guidance_paths),
    }, sort_keys=True, separators=(",", ":"))
    combined = f"{base_sha}|{spec_json}"
    return compute_sha256(combined.encode())[:16]


def build_flatpack(manifest: Manifest, spec: TaskSpec) -> str:
    """Build the single flatpack text file for AI Studio."""
    lines = []
    lines.append("=" * 60)
    lines.append("OCEAN RESCUE AI STUDIO HANDOFF PACKET")
    lines.append("=" * 60)
    lines.append("")
    lines.append("## START/EXECUTION CONTRACT")
    lines.append("")
    lines.append("This packet contains a complete vertical slice task for Ocean Rescue.")
    lines.append("You are the primary designer/implementer for this slice.")
    lines.append("")
    lines.append("## CURRENT TASK GOAL")
    lines.append("")
    lines.append(spec.goal)
    lines.append("")
    lines.append("## ACCEPTANCE CRITERIA")
    lines.append("")
    for i, criterion in enumerate(spec.acceptance_criteria, 1):
        lines.append(f"{i}. {criterion}")
    lines.append("")
    lines.append("## PROTECTED SURFACE RULES")
    lines.append("")
    lines.append("The following surfaces are PROTECTED. If you need changes,")
    lines.append("return a BOUNDARY_CHANGE_PROPOSAL section with rationale.")
    lines.append("Do NOT silently modify these in the candidate ZIP.")
    lines.append("")
    lines.append("- Pointer normalization authority")
    lines.append("- Global application phase-transition authority")
    lines.append("- Progression persistence/schema authority")
    lines.append("- Package/dependency/toolchain")
    lines.append("- Vite/build/standalone packaging")
    lines.append("- Ocean Rescue outside AidenGame")
    lines.append("")
    lines.append("## INCLUDED FILE MANIFEST")
    lines.append("")
    lines.append(f"Base SHA: {manifest.base_sha}")
    lines.append(f"Packet ID: {manifest.packet_id}")
    lines.append(f"Created: {manifest.created_at}")
    lines.append(f"File count: {len(manifest.files)}")
    lines.append("")
    for f in manifest.files:
        lines.append(f"- {f.path} [{f.role}] {f.byte_length} bytes SHA256={f.sha256[:16]}...")
    lines.append("")
    lines.append("## FILE CONTENTS")
    lines.append("")
    for f in manifest.files:
        lines.append(f"--- FILE: {f.path} [{f.role}] ---")
        lines.append(f"ENCODING: {f.encoding}")
        lines.append(f"SHA256: {f.sha256}")
        lines.append(f"BYTES: {f.byte_length}")
        lines.append("CONTENT:")
        if f.content:
            lines.append(f.content)
        lines.append("--- END FILE ---")
        lines.append("")
    lines.append("## RESTORATION INSTRUCTIONS")
    lines.append("")
    lines.append("When producing the result ZIP:")
    lines.append("1. Restore all files to their exact original relative paths.")
    lines.append("2. Binary files (base64) must be decoded back to exact original bytes.")
    lines.append("3. Text files must preserve exact UTF-8 encoding.")
    lines.append("4. Do NOT rename, reorganize, or change directory structure.")
    lines.append("")
    lines.append("## PACKAGE/TOOLCHAIN PRESERVATION")
    lines.append("")
    lines.append("CRITICAL: Do NOT change the following to your default React scaffold:")
    lines.append("- Package manager: pnpm (locked to 11.20.0)")
    lines.append("- Node: 24.19.0")
    lines.append("- Vite: 8.1.5")
    lines.append("- TypeScript: 7.0.2")
    lines.append("- PixiJS: 8.19.0 (pinned)")
    lines.append("- Build output: single standalone HTML (browser/PixiJS)")
    lines.append("- No React, Next.js, Phaser, Godot, Unity, Tauri, backend")
    lines.append("")
    lines.append("## RECEIPT GENERATION")
    lines.append("")
    lines.append("Your result ZIP MUST contain a receipt file at:")
    lines.append("  .ocean-rescue-ai-receipt.json")
    lines.append("")
    lines.append("With this exact content:")
    lines.append(f'{{"packetId": "{manifest.packet_id}", "base": "{manifest.base_sha}"}}')
    lines.append("")
    lines.append("## CHANGED / VERIFIED / KNOWN_LIMITATIONS / BOUNDARY_CHANGE_PROPOSAL")
    lines.append("")
    lines.append("In your response ZIP, include a file:")
    lines.append("  .ocean-rescue-ai-changes.json")
    lines.append("")
    lines.append("With structure:")
    lines.append('{"changed": [], "verified": [], "knownLimitations": [], "boundaryChangeProposals": []}')
    lines.append("")
    lines.append("Each changed entry: {\"path\": \"...\", \"summary\": \"...\"}")
    lines.append("Each boundaryChangeProposal: {\"surface\": \"...\", \"rationale\": \"...\", \"proposedChange\": \"...\"}")
    lines.append("")
    lines.append("=" * 60)
    lines.append("END OF PACKET")
    lines.append("=" * 60)
    return "\n".join(lines)


def write_manifest(manifest: Manifest, path: Path):
    """Write machine-readable manifest JSON."""
    data = {
        "packetId": manifest.packet_id,
        "baseSha": manifest.base_sha,
        "createdAt": manifest.created_at,
        "spec": manifest.spec,
        "files": [asdict(f) for f in manifest.files]
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_spec_from_json(path: Path) -> TaskSpec:
    """Load task spec from JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return TaskSpec(**data)


def cmd_prepare(args: argparse.Namespace) -> int:
    spec = load_spec_from_json(Path(args.spec).resolve())
    base_sha = get_repo_base_sha()
    packet_id = generate_packet_id(base_sha, spec)
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    files = collect_files(spec)

    manifest = Manifest(
        packet_id=packet_id,
        base_sha=base_sha,
        created_at=created_at,
        spec=asdict(spec),
        files=files
    )

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = out_dir / "manifest.json"
    flatpack_path = out_dir / "packet.txt"

    write_manifest(manifest, manifest_path)
    flatpack_content = build_flatpack(manifest, spec)
    flatpack_path.write_text(flatpack_content, encoding="utf-8")

    print(f"Prepared packet: {packet_id}")
    print(f"Base SHA: {base_sha}")
    print(f"Output: {out_dir}")
    print(f"  manifest.json ({manifest_path.stat().st_size} bytes)")
    print(f"  packet.txt ({flatpack_path.stat().st_size} bytes)")
    return 0


def validate_zip_structure(zip_path: Path) -> Tuple[List[str], Dict[str, Any]]:
    """Validate ZIP structure and return (file_list, receipt)."""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Check for absolute paths, traversal, duplicates
        seen = set()
        for info in zf.infolist():
            name = info.filename
            # Absolute path
            if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
                raise ValueError(f"Absolute path in ZIP: {name}")
            # Traversal
            if ".." in name.split("/"):
                raise ValueError(f"Path traversal in ZIP: {name}")
            # Normalized duplicate
            norm = os.path.normpath(name)
            if norm in seen:
                raise ValueError(f"Duplicate normalized path in ZIP: {norm}")
            seen.add(norm)
            # Symlink/special file (check external_attr)
            if info.external_attr & 0xA0000000:  # Symlink flag
                raise ValueError(f"Symlink in ZIP: {name}")

        # Find receipt
        receipt_names = [n for n in zf.namelist() if n.endswith(".ocean-rescue-ai-receipt.json")]
        if len(receipt_names) != 1:
            raise ValueError(f"Expected exactly one receipt file, found {len(receipt_names)}")
        receipt_name = receipt_names[0]
        with zf.open(receipt_name) as f:
            receipt = json.load(f)

        return zf.namelist(), receipt


def run_verification_commands(commands: List[List[str]], cwd: Path) -> Tuple[bool, str]:
    """Run verification commands and return (success, output)."""
    for cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode != 0:
                return False, f"Command failed: {' '.join(cmd)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return False, f"Command timed out: {' '.join(cmd)}"
        except Exception as e:
            return False, f"Command error: {' '.join(cmd)}: {e}"
    return True, "All verification commands passed"


def cmd_ingest(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).resolve()
    zip_path = Path(args.zip).resolve()

    # Load manifest
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = Manifest(
        packet_id=manifest_data["packetId"],
        base_sha=manifest_data["baseSha"],
        created_at=manifest_data["createdAt"],
        spec=manifest_data["spec"],
        files=[FileEntry(**f) for f in manifest_data["files"]]
    )

    # Preconditions
    current_sha = get_repo_base_sha()
    if current_sha != manifest.base_sha:
        print(f"FAIL: Current HEAD ({current_sha}) != manifest base ({manifest.base_sha})", file=sys.stderr)
        return 1

    # Check worktree clean (tracked files only; untracked files like new test files are OK)
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True
    )
    if result.stdout.strip():
        print(f"FAIL: Worktree not clean:\n{result.stdout}", file=sys.stderr)
        return 1

    # Validate ZIP
    try:
        zip_files, receipt = validate_zip_structure(zip_path)
    except ValueError as e:
        print(f"FAIL: ZIP validation failed: {e}", file=sys.stderr)
        return 1

    # Verify receipt
    if receipt.get("packetId") != manifest.packet_id:
        print(f"FAIL: Receipt packetId mismatch: {receipt.get('packetId')} != {manifest.packet_id}", file=sys.stderr)
        return 1
    if receipt.get("base") != manifest.base_sha:
        print(f"FAIL: Receipt base mismatch: {receipt.get('base')} != {manifest.base_sha}", file=sys.stderr)
        return 1

    # Extract to temp dir for validation
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(tmp_path)

        # Find candidate workspace root (directory containing the repo files)
        # Look for a directory that matches the repo structure
        candidate_root = None
        for item in tmp_path.iterdir():
            if item.is_dir():
                # Check if this looks like our repo structure
                if (item / ".git").exists() or (item / "domains").exists() or (item / "scripts").exists():
                    candidate_root = item
                    break
        if candidate_root is None:
            # Try tmp_path itself
            candidate_root = tmp_path

        # Validate candidate boundary
        spec = TaskSpec(**manifest.spec)
        mutable_set = set(normalize_repo_path(p) for p in spec.mutable_paths)
        readonly_set = set(normalize_repo_path(p) for p in spec.read_only_paths)
        allow_new_set = set(normalize_repo_path(p) for p in spec.allow_new_under)

        # Check each file in candidate
        for rel_path in zip_files:
            if rel_path.endswith(".ocean-rescue-ai-receipt.json") or rel_path.endswith(".ocean-rescue-ai-changes.json"):
                continue
            norm = normalize_repo_path(rel_path)

            candidate_file = candidate_root / rel_path
            if not candidate_file.exists() or not candidate_file.is_file():
                continue

            if norm in readonly_set:
                # Must be byte-identical
                original_file = REPO_ROOT / norm
                if not original_file.exists():
                    print(f"FAIL: READ_ONLY file missing in repo: {norm}", file=sys.stderr)
                    return 1
                orig_bytes = read_file_bytes(original_file)
                cand_bytes = read_file_bytes(candidate_file)
                if orig_bytes != cand_bytes:
                    print(f"FAIL: READ_ONLY file mutated: {norm}", file=sys.stderr)
                    return 1

            elif norm in mutable_set:
                # OK to change
                pass

            elif any(norm.startswith(p.rstrip("/") + "/") for p in allow_new_set):
                # OK - new file under allowed directory
                pass

            else:
                # Unexpected file
                print(f"FAIL: Unexpected file in candidate: {norm}", file=sys.stderr)
                return 1

            # Check for React/scaffold files outside boundary
            scaffold_patterns = ["package.json", "tsconfig.json", "vite.config.ts", "index.html", "src/main.tsx", "src/App.tsx"]
            for pattern in scaffold_patterns:
                if norm.endswith(pattern) and norm not in mutable_set and not any(norm.startswith(p.rstrip("/") + "/") for p in allow_new_set):
                    print(f"FAIL: Unexpected scaffold file: {norm}", file=sys.stderr)
                    return 1

        # All structural validation passed - now apply to current worktree
        print("Validation passed. Applying changes...")
        for rel_path in zip_files:
            if rel_path.endswith(".ocean-rescue-ai-receipt.json") or rel_path.endswith(".ocean-rescue-ai-changes.json"):
                continue
            norm = normalize_repo_path(rel_path)
            candidate_file = candidate_root / rel_path
            if not candidate_file.exists() or not candidate_file.is_file():
                continue

            target_file = REPO_ROOT / norm
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(candidate_file, target_file)

    # Run verification commands
    spec_obj = TaskSpec(**manifest.spec)
    success, output = run_verification_commands(spec_obj.verification_commands, REPO_ROOT)
    if not success:
        print(f"FAIL: Verification failed:\n{output}", file=sys.stderr)
        return 1

    print("SUCCESS: Ingest complete. Changes applied to worktree.")
    print("Run git diff to review, then commit/push per repository contract.")
    return 0


def main():
    parser = argparse.ArgumentParser(prog="ocean_ai.py", description="Ocean Rescue AI Studio Handoff CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_prepare = sub.add_parser("prepare", help="Create flatpack + manifest for AI Studio")
    p_prepare.add_argument("--spec", required=True, help="Path to task.json")
    p_prepare.add_argument("--out", required=True, help="Output directory")
    p_prepare.set_defaults(func=cmd_prepare)

    p_ingest = sub.add_parser("ingest", help="Validate and apply AI Studio ZIP result")
    p_ingest.add_argument("--manifest", required=True, help="Path to manifest.json from prepare")
    p_ingest.add_argument("--zip", required=True, help="Path to result ZIP from AI Studio")
    p_ingest.set_defaults(func=cmd_ingest)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())