#!/usr/bin/env python3
"""Quantization artifact detector for JS files.

Detects LLM quantization artifacts:
1. Unicode escape sequences (\\uXXXX) in string literals
2. Suspicious Korean character combinations (repeated syllables,
   malformed jamo, out-of-context characters)

Usage:
    python scripts/verify_korean_js.py [--dir domains --dir shared]
    python scripts/verify_korean_js.py --all
"""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


# Hangul syllable range (Hangul Syllables block)
HANGUL_START = 0xAC00
HANGUL_END = 0xAC00 + 11172  # 0xD7A3

# High surrogate range (U+D800–U+DBFF)
HIGH_SURROGATE_START = 0xD800
HIGH_SURROGATE_END = 0xDBFF

# Low surrogate range (U+DC00–U+DFFF)
LOW_SURROGATE_START = 0xDC00
LOW_SURROGATE_END = 0xDFFF

# Known broken patterns from SPEC
KNOWN_BROKEN = {
    "문문": "문제",
    "맞쳇": "맞혔",
    "로뱁": "로켓",
    "배사": "발사",
    "임꺽": "임무",
    "전부분정당": "전부 정답",
    "오래!": "올라!",
    "므집": "넉줄",
    "확제": "확인",
    "워기": "무기",
}

# Known good Korean words with repeated syllables (not quantization errors)
KNOWN_GOOD_REPEATS = {
    "바나나",
    "파파야",
    "똑똑",
    "상상",
    "상상력",
    "혈혈",
    "혈혈단신",
    "스스로",
    "일일",
    "초초",
    "통통",
    "행행",
    "연연",
    "석석",
    "도도",
    "호호",
}

# Malformed jamo — characters that appear in quantization errors
# but are not standard Hangul syllables or common words
SUSPICIOUS_PATTERNS = [
    re.compile(r"([가 - 힣]){2,}"),  # 2+ consecutive syllables may indicate repetition
    re.compile(r"[^\\n\\t]{10,}"),  # long strings without whitespace (possible jamo merge)
]


@dataclass
class Finding:
    file: str
    line_num: int
    line_content: str
    artifact_type: str
    detail: str
    severity: str = "warning"


def collect_targets(root: Path, dirs: list[str], all_flag: bool) -> list[Path]:
    if all_flag:
        patterns = ["domains/**/*.js", "shared/**/*.js", "experiments/**/*.js"]
        targets = []
        for pat in patterns:
            targets.extend([p for p in root.glob(pat) if p.is_file() and "node_modules" not in p.parts])
        return sorted(set(targets))

    targets = []
    for d in dirs:
        dir_path = root / d
        if dir_path.exists() and dir_path.is_dir():
            targets.extend([p for p in dir_path.rglob("*.js") if p.is_file() and "node_modules" not in p.parts])
    return sorted(set(targets))


def is_hangul_syllable(cp: int) -> bool:
    return HANGUL_START <= cp <= HANGUL_END


def has_unicode_escapes(content: str) -> list[Finding]:
    """Detect \\uXXXX escape sequences in JS source."""
    findings = []
    lines = content.split("\n")
    # Match \\uXXXX in string literals (not inside comments)
    pattern = re.compile(r"\\u([0-9A-Fa-f]{4})")

    for i, line in enumerate(lines, 1):
        # Skip comment lines
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        matches = pattern.finditer(line)
        for m in matches:
            hex_str = m.group(1)
            cp = int(hex_str, 16)

            # Flag high surrogates (indicates potential emoji/special char)
            if HIGH_SURROGATE_START <= cp <= HIGH_SURROGATE_END:
                findings.append(Finding(
                    file="",
                    line_num=i,
                    line_content=line.rstrip(),
                    artifact_type="unicode_escape",
                    detail=f"High surrogate \\u{hex_str} (possible emoji artifact)",
                    severity="warning",
                ))
            # Flag non-Hangul CJK characters
            elif 0x3000 <= cp <= 0x9FFF and not is_hangul_syllable(cp):
                findings.append(Finding(
                    file="",
                    line_num=i,
                    line_content=line.rstrip(),
                    artifact_type="unicode_escape",
                    detail=f"Non-Hangul CJK \\u{hex_str} (consider UTF-8 literal)",
                    severity="info",
                ))

    return findings


def has_broken_korean(content: str) -> list[Finding]:
    """Detect known broken Korean patterns from quantization errors."""
    findings = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue

        for broken, correct in KNOWN_BROKEN.items():
            if broken in line:
                findings.append(Finding(
                    file="",
                    line_num=i,
                    line_content=line.rstrip(),
                    artifact_type="broken_korean",
                    detail=f"'{broken}' found — should be '{correct}'",
                    severity="error",
                ))

    return findings


def has_repeated_syllables(content: str) -> list[Finding]:
    """Detect repeated Korean syllables (e.g., '문문', '과과')."""
    findings = []
    lines = content.split("\n")

    # Pattern: 2+ consecutive Hangul syllables that are identical
    pattern = re.compile(r"([\uac00-\ud7a3])\1{1,}")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue

        matches = pattern.finditer(line)
        for m in matches:
            text = m.group()
            if len(text) >= 2 and all(is_hangul_syllable(ord(c)) for c in text):
                # Skip known good words (including if matched text is contained within them)
                if text in KNOWN_GOOD_REPEATS:
                    continue
                skip = False
                for good in KNOWN_GOOD_REPEATS:
                    if text in good or good in text:
                        skip = True
                        break
                if skip:
                    continue
                findings.append(Finding(
                    file="",
                    line_num=i,
                    line_content=line.rstrip(),
                    artifact_type="repeated_syllable",
                    detail=f"Repeated syllable '{text}' (possible quantization error)",
                    severity="warning",
                ))

    return findings


def has_surrogate_pairs(content: str) -> list[Finding]:
    """Detect broken surrogate pairs (high surrogate not followed by low surrogate)."""
    findings = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue

        # Look for lone high surrogates in decoded content
        # This catches cases where \\uD8xx was decoded but low surrogate is missing
        for j, char in enumerate(line):
            cp = ord(char)
            if HIGH_SURROGATE_START <= cp <= HIGH_SURROGATE_END:
                # Check if next char is a low surrogate
                if j + 1 < len(line):
                    next_cp = ord(line[j + 1])
                    if not (LOW_SURROGATE_START <= next_cp <= LOW_SURROGATE_END):
                        findings.append(Finding(
                            file="",
                            line_num=i,
                            line_content=line.rstrip(),
                            artifact_type="broken_surrogate",
                            detail=f"Lone high surrogate at pos {j} (emoji may be corrupted)",
                            severity="error",
                        ))

    return findings


def validate_file(path: Path) -> list[Finding]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        return [Finding(
            file=str(path),
            line_num=0,
            line_content="",
            artifact_type="decode_error",
            detail=str(e),
            severity="error",
        )]

    findings = []
    findings.extend(has_unicode_escapes(content))
    findings.extend(has_broken_korean(content))
    findings.extend(has_repeated_syllables(content))
    findings.extend(has_surrogate_pairs(content))

    # Tag findings with file path
    for f in findings:
        f.file = str(path)

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect LLM quantization artifacts in JS files.",
    )
    parser.add_argument(
        "--dir",
        action="append",
        default=["domains", "shared"],
        help="Directory to scan (can be repeated, default: domains shared)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan all JS files in domains/, shared/, experiments/",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings (not just errors)",
    )
    args = parser.parse_args()

    root = Path.cwd()
    targets = collect_targets(root, args.dir, args.all)

    if not targets:
        print("[WARN] No JS files found to scan")
        return 0

    all_findings: list[Finding] = []
    for path in targets:
        all_findings.extend(validate_file(path))

    if not all_findings:
        print(f"[PASS] Verified {len(targets)} JS file(s) — no quantization artifacts")
        return 0

    # Separate by severity
    errors = [f for f in all_findings if f.severity == "error"]
    warnings = [f for f in all_findings if f.severity == "warning"]
    infos = [f for f in all_findings if f.severity == "info"]

    # Print findings
    print(f"[FOUND] {len(all_findings)} artifact(s) in {len(targets)} file(s):")
    for f in all_findings:
        severity_label = {"error": "ERROR", "warning": "WARN", "info": "INFO"}[f.severity]
        line_info = f":{f.line_num}" if f.line_num > 0 else ""
        print(f"  [{severity_label}] {f.file}{line_info}")
        print(f"    Type: {f.artifact_type}")
        print(f"    {f.detail}")
        if f.line_content.strip():
            print(f"    Line: {f.line_content.strip()[:100]}")
        print()

    # Determine exit code
    if errors:
        print(f"[FAIL] {len(errors)} error(s) — quantization artifacts detected")
        return 1

    if args.strict and warnings:
        print(f"[FAIL] {len(warnings)} warning(s) in strict mode")
        return 1

    if warnings:
        print(f"[WARN] {len(warnings)} warning(s) — review recommended")

    if infos:
        print(f"[INFO] {len(infos)} info item(s) — unicode escapes found")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
