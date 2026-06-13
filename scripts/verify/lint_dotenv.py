#!/usr/bin/env python3
"""Lint dotenv files for KEY=VALUE-only format (Docker Compose / run_dev.sh safe).

Rejects shell commands (unset, export, source, $(...), redirects) that break
docker-compose env_file parsing and confuse run_dev loaders.

Usage:
  python3 scripts/verify/lint_dotenv.py .env.example
  python3 scripts/verify/lint_dotenv.py .env.example .env
  just env-lint
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

_VALID_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Whole-line or leading-token patterns that must never appear in committed/local .env
_FORBIDDEN: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^\s*(unset|export|source|readonly|declare|set)\b"), "shell command"),
    (re.compile(r"\$\("), "command substitution $(...)"),
    (re.compile(r"`"), "backtick command"),
    (re.compile(r"[<>|;&]"), "shell operator (redirect/pipe/;)"),
)


@dataclass(frozen=True, slots=True)
class DotenvIssue:
    path: Path
    line_no: int
    message: str
    hint: str = ""

    def format(self) -> str:
        loc = f"{self.path}:{self.line_no}"
        base = f"{loc}: {self.message}"
        return f"{base}\n  → {self.hint}" if self.hint else base


def lint_dotenv_text(path: Path, text: str) -> list[DotenvIssue]:
    issues: list[DotenvIssue] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for pattern, label in _FORBIDDEN:
            if pattern.search(raw):
                issues.append(
                    DotenvIssue(
                        path,
                        line_no,
                        f"forbidden {label} in .env",
                        "See .env.example header and `just env-lint`; fix before run_dev / docker-compose.",
                    )
                )
                break
        else:
            if "=" not in line:
                issues.append(
                    DotenvIssue(
                        path,
                        line_no,
                        "not a KEY=VALUE assignment",
                        "Use # comments or KEY=value only; shell commands belong in the terminal.",
                    )
                )
                continue
            key_part, _, _value_part = line.partition("=")
            key = key_part.strip()
            if not key:
                issues.append(
                    DotenvIssue(path, line_no, "empty variable name before '='"),
                )
                continue
            if not _VALID_KEY.match(key):
                issues.append(
                    DotenvIssue(
                        path,
                        line_no,
                        f"invalid variable name {key!r}",
                        "Names must match [A-Za-z_][A-Za-z0-9_]* (no spaces or redirects).",
                    )
                )
    return issues


def lint_dotenv_file(path: Path) -> list[DotenvIssue]:
    if not path.is_file():
        return [
            DotenvIssue(
                path,
                0,
                "file not found",
                "Create from .env.example or pass an existing path.",
            )
        ]
    return lint_dotenv_text(path, path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        root = Path(__file__).resolve().parents[2]
        args = [str(root / ".env.example")]
        env_path = root / ".env"
        if env_path.is_file():
            args.append(str(env_path))

    all_issues: list[DotenvIssue] = []
    for arg in args:
        all_issues.extend(lint_dotenv_file(Path(arg)))

    if not all_issues:
        return 0

    sys.stderr.write("dotenv lint FAILED\n")
    for issue in all_issues:
        sys.stderr.write(issue.format() + "\n")
    sys.stderr.write(
        "\nFix: remove shell commands from .env; use KEY=VALUE only. "
        "Run `just env-lint` after edits.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
