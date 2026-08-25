#!/usr/bin/env python3
"""Deterministic, fail-closed Ocean Rescue <-> AI Studio handoff CLI."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
PIXI_SKILLS = "domains/ocean-rescue/node_modules/pixi.js/skills/"
FORBIDDEN_PARTS = {".git", "__pycache__", ".pytest_cache"}
PROTECTED = {
    "domains/ocean-rescue/package.json",
    "domains/ocean-rescue/pnpm-lock.yaml",
    "domains/ocean-rescue/tsconfig.json",
    "domains/ocean-rescue/vite.config.ts",
    "domains/ocean-rescue/vite.bundle.ts",
    "domains/ocean-rescue/vite.production.config.ts",
    "domains/ocean-rescue/vite.shadow.config.ts",
    "domains/ocean-rescue/src/build-manifest.json",
    "domains/ocean-rescue/src/build-manifest.legacy.json",
    "domains/ocean-rescue/src/contracts/pointer-input.ts",
    "domains/ocean-rescue/src/pointer-input.js",
    "domains/ocean-rescue/src/state/state.ts",
    "domains/ocean-rescue/src/state.js",
    "domains/ocean-rescue/src/missions.js",
}
BAD_NEW_NAMES = {
    "package.json", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock",
    "bun.lock", "bun.lockb", "pnpm-lock.yaml", "tsconfig.json",
    "vite.config.ts", "vite.config.js", "App.tsx", "main.tsx",
}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


def fail(message):
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def canonical(raw):
    if not isinstance(raw, str) or not raw:
        raise ValueError("Path must be a non-empty string")
    value = raw.replace("\\", "/")
    if value.startswith("/") or re.match(r"^[A-Za-z]:/", value):
        raise ValueError(f"Path escapes repository: {raw}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"Path must be canonical and traversal-free: {raw}")
    return PurePosixPath(value).as_posix()


def repo_file(path):
    rel = canonical(path)
    resolved = (ROOT / rel).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"Path escapes repository: {rel}") from exc
    return resolved


def secret_like(path):
    for part in (p.lower() for p in PurePosixPath(path).parts):
        if (
            part.startswith(".env") or part.endswith(".env")
            or part.startswith("secret") or part.startswith("credential")
            or part in {"id_rsa", "id_ed25519"}
            or part.endswith(SECRET_SUFFIXES)
        ):
            return True
    return False


def validate_path(path, role):
    rel = canonical(path)
    parts = set(PurePosixPath(rel).parts)
    if parts & FORBIDDEN_PARTS:
        raise ValueError(f"Forbidden path in spec: {rel}")
    if secret_like(rel):
        raise ValueError(f"Secret-like path is forbidden: {rel}")
    if "node_modules" in parts and not (
        role == "GUIDANCE" and rel.startswith(PIXI_SKILLS)
    ):
        raise ValueError(f"Forbidden node_modules path in spec: {rel}")
    if role == "MUTABLE" and rel in PROTECTED:
        raise ValueError(f"Protected surface cannot be MUTABLE: {rel}")
    return rel


def normalize_spec(data):
    required = {
        "task_id", "goal", "acceptance_criteria", "mutable_paths",
        "read_only_paths",
    }
    missing = required - set(data)
    if missing:
        raise ValueError(f"Missing task spec fields: {sorted(missing)}")
    if not str(data["task_id"]).strip() or not str(data["goal"]).strip():
        raise ValueError("task_id and goal must not be empty")
    if not data["acceptance_criteria"]:
        raise ValueError("acceptance_criteria must not be empty")
    commands = data.get("verification_commands", [])
    if any(not isinstance(cmd, list) or not cmd for cmd in commands):
        raise ValueError("verification_commands must contain non-empty argv arrays")
    spec = {
        "task_id": data["task_id"],
        "goal": data["goal"],
        "acceptance_criteria": list(data["acceptance_criteria"]),
        "mutable_paths": sorted(validate_path(p, "MUTABLE") for p in data["mutable_paths"]),
        "read_only_paths": sorted(validate_path(p, "READ_ONLY") for p in data["read_only_paths"]),
        "allow_new_under": sorted(canonical(p) for p in data.get("allow_new_under", [])),
        "guidance_paths": sorted(validate_path(p, "GUIDANCE") for p in data.get("guidance_paths", [])),
        "verification_commands": [list(cmd) for cmd in commands],
    }
    roles = [set(spec[k]) for k in ("mutable_paths", "read_only_paths", "guidance_paths")]
    if roles[0] & roles[1] or roles[0] & roles[2] or roles[1] & roles[2]:
        raise ValueError("Path may appear in only one MUTABLE/READ_ONLY/GUIDANCE role")
    for path in spec["allow_new_under"]:
        parts = set(PurePosixPath(path).parts)
        if secret_like(path) or parts & FORBIDDEN_PARTS or "node_modules" in parts:
            raise ValueError(f"Forbidden allow-new path: {path}")
        if path in PROTECTED:
            raise ValueError(f"Protected surface cannot be allow-new: {path}")
    return spec


def encode_file(path, role):
    source = repo_file(path)
    if not source.exists():
        raise FileNotFoundError(f"Specified path does not exist: {path}")
    if not source.is_file():
        raise ValueError(f"Path is not a file: {path}")
    data = source.read_bytes()
    try:
        text = data.decode("utf-8")
        binary = "\x00" in text
    except UnicodeDecodeError:
        binary = True
        text = ""
    return {
        "path": path,
        "role": role,
        "byte_length": len(data),
        "sha256": digest(data),
        "encoding": "base64" if binary else "utf-8",
        "content": base64.b64encode(data).decode("ascii") if binary else text,
    }


def collect(spec):
    files = []
    for role, key in (
        ("MUTABLE", "mutable_paths"),
        ("READ_ONLY", "read_only_paths"),
        ("GUIDANCE", "guidance_paths"),
    ):
        files.extend(encode_file(path, role) for path in spec[key])
    return files


def identity(base, spec, files):
    return {
        "baseSha": base,
        "spec": spec,
        "files": [
            {
                "path": f["path"], "role": f["role"],
                "byteLength": f["byte_length"], "sha256": f["sha256"],
                "encoding": f["encoding"],
            }
            for f in files
        ],
    }


def packet_id(base, spec, files):
    raw = json.dumps(identity(base, spec, files), sort_keys=True, separators=(",", ":"))
    return digest(raw.encode())[:16]


def flatpack(manifest, files):
    spec = manifest["spec"]
    out = [
        "=" * 60, "OCEAN RESCUE AI STUDIO HANDOFF PACKET", "=" * 60, "",
        "## START/EXECUTION CONTRACT", "",
        "You are the primary designer/implementer for this bounded playable vertical slice.",
        "Preserve the existing browser/PixiJS/Vite architecture; do not scaffold React or another app.",
        "", "## CURRENT TASK GOAL", "", spec["goal"], "",
        "## ACCEPTANCE CRITERIA", "",
    ]
    out.extend(f"{i}. {c}" for i, c in enumerate(spec["acceptance_criteria"], 1))
    out += [
        "", "## PROTECTED SURFACES", "",
        "Protected surfaces are proposal-only: pointer normalization; global phase transitions; progression persistence/schema; package/dependency/toolchain; Vite/build/standalone packaging; AidenGame outside this slice.",
        "If needed, return BOUNDARY_CHANGE_PROPOSAL instead of silently modifying them.",
        "", "## INCLUDED FILE MANIFEST", "",
        f"Base SHA: {manifest['baseSha']}", f"Packet ID: {manifest['packetId']}",
        f"Source commit time: {manifest['createdAt']}", f"File count: {len(files)}", "",
    ]
    out.extend(
        f"- {f['path']} [{f['role']}] {f['byte_length']} bytes SHA256={f['sha256']}"
        for f in files
    )
    out += ["", "## FILE CONTENTS", ""]
    for f in files:
        out += [
            f"--- FILE: {f['path']} [{f['role']}] ---",
            f"ENCODING: {f['encoding']}", f"SHA256: {f['sha256']}",
            f"BYTES: {f['byte_length']}", "CONTENT:", f["content"],
            "--- END FILE ---", "",
        ]
    receipt = json.dumps(
        {"packetId": manifest["packetId"], "base": manifest["baseSha"]},
        separators=(",", ":"),
    )
    out += [
        "## RESULT ZIP CONTRACT", "",
        "Preserve MUTABLE and READ_ONLY repository-relative paths exactly.",
        "GUIDANCE is reference-only and MUST NOT be emitted into the result ZIP.",
        "Do not add package/toolchain/build or React/Next.js/Phaser/Godot/Unity/Tauri/backend scaffolding.",
        "The project root MUST contain .ocean-rescue-ai-receipt.json with:",
        receipt,
        "Optionally include .ocean-rescue-ai-changes.json for CHANGED / VERIFIED / KNOWN_LIMITATIONS / BOUNDARY_CHANGE_PROPOSAL.",
        "", "=" * 60, "END OF PACKET", "=" * 60, "",
    ]
    return "\n".join(out)


def prepare(args):
    try:
        raw = json.loads(Path(args.spec).resolve().read_text(encoding="utf-8"))
        spec = normalize_spec(raw)
        base = git("rev-parse", "HEAD")
        created = git("show", "-s", "--format=%cI", base)
        files = collect(spec)
        packet = packet_id(base, spec, files)
        manifest = {
            "packetId": packet, "baseSha": base, "createdAt": created, "spec": spec,
            "files": [{k: v for k, v in f.items() if k != "content"} for f in files],
        }
        out = Path(args.out).resolve()
        out.mkdir(parents=True, exist_ok=True)
        (out / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (out / "packet.txt").write_text(flatpack(manifest, files), encoding="utf-8")
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        return fail(str(exc))
    print(f"Prepared packet: {packet}\nBase SHA: {base}\nOutput: {out}")
    return 0


def zip_path(name):
    value = name.replace("\\", "/")
    if value.startswith("/") or re.match(r"^[A-Za-z]:/", value):
        raise ValueError(f"Absolute path in ZIP: {name}")
    trimmed = value[:-1] if value.endswith("/") else value
    parts = trimmed.split("/")
    if ".." in parts:
        raise ValueError(f"Path traversal in ZIP: {name}")
    if not trimmed or any(p in {"", "."} for p in parts):
        raise ValueError(f"Non-canonical path in ZIP: {name}")
    return PurePosixPath(trimmed).as_posix()


def inspect_zip(path):
    with zipfile.ZipFile(path, "r") as archive:
        members = {}
        receipts = []
        for info in archive.infolist():
            norm = zip_path(info.filename)
            if norm in members:
                raise ValueError(f"Duplicate normalized path in ZIP: {norm}")
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}:
                raise ValueError(f"Special file in ZIP is forbidden: {info.filename}")
            members[norm] = info
            if PurePosixPath(norm).name == ".ocean-rescue-ai-receipt.json":
                receipts.append(norm)
        if len(receipts) != 1:
            raise ValueError(f"Expected exactly one receipt file, found {len(receipts)}")
        receipt_path = receipts[0]
        parent = PurePosixPath(receipt_path).parent.as_posix()
        prefix = "" if parent == "." else parent + "/"
        try:
            receipt = json.loads(archive.read(members[receipt_path]).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Receipt is not valid UTF-8 JSON") from exc
        candidate = {}
        for norm, info in members.items():
            if info.is_dir():
                continue
            if prefix:
                if not norm.startswith(prefix):
                    raise ValueError(f"ZIP file exists outside candidate root: {norm}")
                rel = norm[len(prefix):]
            else:
                rel = norm
            if PurePosixPath(rel).name in {
                ".ocean-rescue-ai-receipt.json", ".ocean-rescue-ai-changes.json"
            }:
                continue
            rel = canonical(rel)
            if rel in candidate:
                raise ValueError(f"Duplicate candidate path in ZIP: {rel}")
            candidate[rel] = archive.read(info)
        return candidate, receipt


def validate_manifest(manifest):
    spec = normalize_spec(manifest["spec"])
    if spec != manifest["spec"]:
        raise ValueError("Manifest spec is not canonical")
    files = manifest["files"]
    if len({f["path"] for f in files}) != len(files):
        raise ValueError("Manifest contains duplicate file paths")
    expected_roles = {}
    for role, key in (("MUTABLE", "mutable_paths"), ("READ_ONLY", "read_only_paths"), ("GUIDANCE", "guidance_paths")):
        expected_roles.update({p: role for p in spec[key]})
    if set(expected_roles) != {f["path"] for f in files}:
        raise ValueError("Manifest file set does not match spec")
    if any(expected_roles[f["path"]] != f["role"] for f in files):
        raise ValueError("Manifest file role does not match spec")
    expected = digest(
        json.dumps(identity(manifest["baseSha"], spec, files), sort_keys=True, separators=(",", ":")).encode()
    )[:16]
    if manifest["packetId"] != expected:
        raise ValueError("Manifest packetId does not match manifest contents")
    return spec


def under(path, roots):
    return any(path.startswith(root.rstrip("/") + "/") for root in roots)


def run_verify(commands):
    for command in commands:
        try:
            result = subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True, timeout=120
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"Command error: {command}: {exc}"
        if result.returncode:
            return False, f"Command failed: {' '.join(command)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    return True, ""


def ingest(args):
    try:
        manifest = json.loads(Path(args.manifest).resolve().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return fail(f"Manifest validation failed: {exc}")
    current = git("rev-parse", "HEAD")
    if current != manifest.get("baseSha"):
        return fail(f"Current HEAD ({current}) != manifest base ({manifest.get('baseSha')})")
    try:
        spec = validate_manifest(manifest)
    except (ValueError, TypeError, KeyError) as exc:
        return fail(f"Manifest validation failed: {exc}")
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True
    ).stdout
    if status.strip():
        return fail(f"Worktree not clean:\n{status}")
    try:
        candidate, receipt = inspect_zip(Path(args.zip).resolve())
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        return fail(f"ZIP validation failed: {exc}")
    if receipt.get("packetId") != manifest["packetId"]:
        return fail(f"Receipt packetId mismatch: {receipt.get('packetId')} != {manifest['packetId']}")
    if receipt.get("base") != manifest["baseSha"]:
        return fail(f"Receipt base mismatch: {receipt.get('base')} != {manifest['baseSha']}")
    mutable = set(spec["mutable_paths"])
    read_only = set(spec["read_only_paths"])
    guidance = set(spec["guidance_paths"])
    allow_new = set(spec["allow_new_under"])
    originals = {f["path"]: f for f in manifest["files"]}
    pending = []
    try:
        for rel, data in candidate.items():
            if rel in guidance:
                raise ValueError(f"GUIDANCE file must not be emitted in candidate: {rel}")
            if rel in PROTECTED:
                target = ROOT / rel
                if not target.exists() or target.read_bytes() != data:
                    raise ValueError(f"Protected surface mutation rejected: {rel}")
            if rel in read_only:
                target = ROOT / rel
                if not target.exists() or target.read_bytes() != data:
                    raise ValueError(f"READ_ONLY file mutated: {rel}")
            elif rel in mutable:
                pass
            elif under(rel, allow_new):
                if PurePosixPath(rel).name in BAD_NEW_NAMES:
                    raise ValueError(f"Unexpected scaffold/toolchain file: {rel}")
                if (ROOT / rel).exists():
                    raise ValueError(f"Existing file under allow-new requires MUTABLE role: {rel}")
            else:
                raise ValueError(f"Unexpected file in candidate: {rel}")
            entry = originals.get(rel)
            if entry and entry["role"] == "READ_ONLY" and digest(data) != entry["sha256"]:
                raise ValueError(f"READ_ONLY file hash mismatch: {rel}")
            pending.append((ROOT / rel, data))
    except (OSError, ValueError) as exc:
        return fail(str(exc))
    for target, data in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    ok, output = run_verify(spec["verification_commands"])
    if not ok:
        return fail(f"Verification failed:\n{output}")
    print("SUCCESS: Ingest complete. Changes applied to worktree.")
    return 0


def main():
    parser = argparse.ArgumentParser(prog="ocean_ai.py")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--spec", required=True)
    prep.add_argument("--out", required=True)
    prep.set_defaults(func=prepare)
    take = sub.add_parser("ingest")
    take.add_argument("--manifest", required=True)
    take.add_argument("--zip", required=True)
    take.set_defaults(func=ingest)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
