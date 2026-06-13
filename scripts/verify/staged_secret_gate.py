"""staged_secret_gate.py — 스테이징된 민감 파일·비밀 검사 (커밋 층).

git diff --cached 로 스테이징된 파일만 빠르게 검사:
  - .env 형식 파일 → 차단
  - *.pem / *.key → 차단 (허용 경로 제외)
  - trufflehog 가 있으면 스테이징 blob 에 --only-verified 스캔 수행

허용 목록: config/git/staged_secret_allowlist.txt
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]  # repo root
ALLOWLIST_PATH = ROOT / "config" / "git" / "staged_secret_allowlist.txt"

# 민감 파일 패턴 — basename 또는 확장자 매칭
SENSITIVE_EXTENSIONS = (".pem", ".key", ".crt", ".p12", ".pfx", ".jks")
SENSITIVE_BASENAMES = (
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    ".env.development",
    ".env.test",
    ".aws/credentials",
    ".ssh/id_rsa",
    ".ssh/id_ed25519",
    "service-account.json",
    "credentials.json",
    ".netrc",
    ".npmrc",
    ".pypirc",
    ".pgpass",
    ".mylogin.cnf",
)

# ---------------------------------------------------------------------------
# Allowlist loader
# ---------------------------------------------------------------------------


def load_allowlist() -> list[str]:
    """허용 목록 파일을 읽어 접두사 리스트로 반환한다."""
    if not ALLOWLIST_PATH.is_file():
        return []

    prefixes: list[str] = []
    for line in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            prefixes.append(stripped)
    return prefixes


# ---------------------------------------------------------------------------
# Sensitive path detection
# ---------------------------------------------------------------------------


def is_sensitive_path(path: str, allowlist: list[str] | None = None) -> bool:
    """경로가 민감 파일인지 판정한다.

    Args:
        path: git diff --cached 로 얻은 파일 경로.
        allowlist: 허용 접두사 리스트 (로딩되지 않으면 파일에서 읽음).

    Returns:
        True if the path is sensitive and should be blocked.
    """
    if allowlist is None:
        allowlist = load_allowlist()

    normalized = str(Path(path).as_posix())

    # Allowlist 체크 — 접두사 매칭
    for prefix in allowlist:
        if normalized.startswith(prefix):
            return False

    # basename 매칭
    basename = os.path.basename(normalized)
    if basename in SENSITIVE_BASENAMES:
        return True

    # 확장자 매칭
    if normalized.lower().endswith(SENSITIVE_EXTENSIONS):
        return True

    # .env 기반 패턴 — .env 로 시작하거나 .env_ 로 시작하는 파일
    if re.match(r"^\.env(\.|-|$)", basename):
        return True

    return False


# ---------------------------------------------------------------------------
# Staged file collection
# ---------------------------------------------------------------------------


def get_staged_files() -> list[str]:
    """git diff --cached --name-only 로 스테이징된 파일 리스트를 반환한다."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(ROOT),
        )
        return [f for f in result.stdout.strip().splitlines() if f]
    except subprocess.CalledProcessError as exc:
        print(f"[warn] git diff --cached 실패: {exc.stderr.strip()}", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("[warn] git 명령어를 찾을 수 없습니다.", file=sys.stderr)
        return []


def staged_scannable_paths(staged_files: list[str]) -> list[str]:
    """디스크에 존재하는 스테이징 파일만 반환한다 (삭제-only 스테이징 제외)."""
    scannable: list[str] = []
    for path in staged_files:
        if (ROOT / path).is_file():
            scannable.append(path)
    return scannable


# ---------------------------------------------------------------------------
# TruffleHog scan (optional)
# ---------------------------------------------------------------------------


def _parse_trufflehog_findings(stdout: str) -> list[str]:
    findings: list[str] = []
    for line in stdout.splitlines():
        try:
            entry = json.loads(line)
            if entry.get("Final"):
                findings.append(f"trufflehog 시크릿: {entry.get('SourceName', 'unknown')}")
        except (ValueError, KeyError):
            pass
    return findings


def run_trufflehog_scan(staged_files: list[str]) -> list[str]:
    """trufflehog 가 설치되어 있으면 스테이징 파일에 --only-verified 스캔 수행."""
    if shutil.which("trufflehog") is None:
        print("[info] trufflehog 미설치 — 경로 차단만 수행.", file=sys.stderr)
        return []

    scannable = staged_scannable_paths(staged_files)
    if not scannable:
        print("[info] trufflehog 스캔 대상 없음(삭제-only) — 경로 차단만 수행.", file=sys.stderr)
        return []

    result = subprocess.run(
        [
            "trufflehog",
            "filesystem",
            "--only-verified",
            "--json",
            "--fail",
            *scannable,
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )

    if result.returncode != 0:
        return _parse_trufflehog_findings(result.stdout)
    return []


# ---------------------------------------------------------------------------
# Main gate
# ---------------------------------------------------------------------------


def main() -> int:
    """커밋 게이트 진입점. 민감 파일 발견 시 1 반환."""
    allowlist = load_allowlist()
    staged = get_staged_files()

    if not staged:
        print("[info] 스테이징된 파일 없음 — 통과.", file=sys.stderr)
        return 0

    # 1) 경로 차단 검사
    blocked: list[str] = []
    for path in staged:
        if is_sensitive_path(path, allowlist):
            blocked.append(path)

    if blocked:
        print("[ERROR] 민감 파일이 스테이징되었습니다. 커밋을 거부합니다:", file=sys.stderr)
        for p in blocked:
            print(f"  🚫 {p}", file=sys.stderr)
        print(
            "\n  config/git/staged_secret_allowlist.txt 에 허용 경로를 추가하세요.",
            file=sys.stderr,
        )
        return 1

    # 2) trufflehog 스캔 (선택)
    findings = run_trufflehog_scan(staged)
    if findings:
        print("[ERROR] trufflehog 가 스테이징 blob 에서 시크릿을 발견했습니다:", file=sys.stderr)
        for f in findings:
            print(f"  🚫 {f}", file=sys.stderr)
        return 1

    print("[OK] 스테이징 검사 통과.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
