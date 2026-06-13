#!/usr/bin/env python3
"""error_patterns stale 패턴 정리 — 30일 이상 미사용 패턴을 archive로 이동."""

import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PATTERN_FILE = REPO_ROOT / ".agents" / "core" / "error_patterns.md"
DETAIL_DIR = REPO_ROOT / ".agents" / "core" / "error_patterns" / "detail"
ARCHIVE_DIR = REPO_ROOT / ".agents" / "core" / "error_patterns_archive"
INCIDENTS_FILE = ARCHIVE_DIR / "incidents.md"

from scripts.error_patterns.patterns_store import load_patterns, save_patterns  # noqa: E402


def remove_pattern_from_yaml(patterns: list, pattern_id: str) -> list:
    """patterns.yaml 목록에서 id 항목 제거."""
    return [p for p in patterns if p.get("id") != pattern_id]


def _extract_section_from_text(content: str, pattern_id: str) -> tuple[str, str] | tuple[None, None]:
    """패턴 ID에 해당하는 마크다운 섹션 추출. (section, full_content) 또는 (None, None)."""
    pattern_match = re.search(
        rf"### {re.escape(pattern_id)} .*?(?=\n\n## |\n\n### |\Z)",
        content,
        re.DOTALL,
    )
    if pattern_match:
        return pattern_match.group(0).strip(), content
    return None, None


def find_section_source(pattern_id: str) -> tuple[Path, str, str] | None:
    """detail/*.md 또는 incidents.md 에서 섹션 탐색. (path, content, section)."""
    candidates: list[Path] = []
    if DETAIL_DIR.is_dir():
        candidates.extend(sorted(DETAIL_DIR.glob("*.md")))
    if INCIDENTS_FILE.is_file():
        candidates.append(INCIDENTS_FILE)
    candidates.append(PATTERN_FILE)

    for path in candidates:
        text = path.read_text(encoding="utf-8")
        section, _ = _extract_section_from_text(text, pattern_id)
        if section:
            return path, text, section
    return None


def archive_pattern(pattern_id: str):
    """패턴을 archive 디렉토리로 이동."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    found = find_section_source(pattern_id)
    if not found:
        print(f"경고: 패턴 {pattern_id}의 섹션을 찾을 수 없음", file=sys.stderr)
        return

    source_path, source_text, section = found

    archive_file = ARCHIVE_DIR / f"{pattern_id}.md"
    archive_file.write_text(
        f"# Archived: {pattern_id}\n\n{section}\n",
        encoding="utf-8",
    )

    pattern_match = re.search(
        rf"### {re.escape(pattern_id)} .*?(?=\n\n## |\n\n### |\Z)",
        source_text,
        re.DOTALL,
    )
    if pattern_match:
        new_text = source_text[: pattern_match.start()] + source_text[pattern_match.end() :]
        source_path.write_text(new_text, encoding="utf-8")

    patterns = load_patterns()
    save_patterns(remove_pattern_from_yaml(patterns, pattern_id))

    print(f"아카이브됨: {pattern_id}")


def main():
    today = date.today()
    threshold = today - timedelta(days=30)

    patterns = load_patterns()

    archived = []
    for p in patterns:
        try:
            last_seen = datetime.strptime(p["last_seen"], "%Y-%m-%d").date()
            if last_seen < threshold:
                archived.append(p["id"])
        except (ValueError, KeyError):
            continue

    if not archived:
        print("아카이브할 패턴 없음")
        return

    for pid in archived:
        archive_pattern(pid)

    print(f"\n총 {len(archived)}개 패턴 아카이브 완료")


if __name__ == "__main__":
    main()
