#!/usr/bin/env python3
"""error_patterns.md에 새 패턴 추가 — 중복 감지 + 자동 카테고리 분류."""

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PATTERN_FILE = REPO_ROOT / ".agents" / "core" / "error_patterns.md"
DETAIL_DIR = REPO_ROOT / ".agents" / "core" / "error_patterns" / "detail"

from scripts.error_patterns.detail_paths import detail_file_for_category  # noqa: E402
from scripts.error_patterns.patterns_store import load_patterns, save_patterns  # noqa: E402

CATEGORIES = [
    "파일 편집 실수",
    "테스트 실수",
    "React 실수",
    "도구 사용 실수",
    "계획서 (Blueprint) 실수",
    "기타 실수",
]


def find_similar(new_name: str, existing: list) -> list:
    """신규 패턴명과 기존 패턴명 간 유사도 계산 (단어 기반)."""
    new_words = set(new_name.lower().split())
    results = []
    for p in existing:
        old_words = set(p["name"].lower().split())
        overlap = new_words & old_words
        if len(overlap) >= 2:  # 최소 2개 단어 겹침
            results.append((p, len(overlap)))
    return sorted(results, key=lambda x: -x[1])


def bump_existing_pattern(name: str, patterns: list) -> bool:
    """동일 패턴명이 있으면 occurrence_count·last_seen만 갱신."""
    match = next((p for p in patterns if p.get("name") == name), None)
    if not match:
        return False

    pattern_id = match["id"]
    new_count = int(match.get("occurrence_count", 1)) + 1
    match["occurrence_count"] = new_count
    match["last_seen"] = date.today().isoformat()
    save_patterns(patterns)
    print(f"갱신됨: {pattern_id} - {name} (occurrence_count={new_count})")
    return True


def find_category(new_name: str) -> str:
    """패턴명으로 카테고리 자동 분류."""
    keywords = {
        "파일 편집 실수": ["patch", "write_file", "read_file", "replace_content", "edit_block", "closing tag", "JSX", "TSX"],
        "테스트 실수": ["test", "mock", "Vitest", "localStorage", "testId", "destructuring"],
        "React 실수": ["useEffect", "useRef", "Fast Refresh", "render", "mount"],
        "도구 사용 실수": ["Biome", "auto-fix", "os.getenv", "MCP"],
        "계획서 (Blueprint) 실수": ["plan-lint", "Blueprint", "Task", "plan-reset"],
        "기타 실수": ["mermaid", "AskQuestion", "MEMORY.md", "discuss"],
    }
    new_lower = new_name.lower()
    scores = {}
    for cat, words in keywords.items():
        score = sum(1 for w in words if w.lower() in new_lower)
        scores[cat] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "기타 실수"


def add_pattern(name: str, symptom: str, cause: str, fix: str):
    """새 패턴 추가 (중복 감지 포함)."""
    patterns = load_patterns()

    if bump_existing_pattern(name, patterns):
        return

    # 중복 감지
    similar = find_similar(name, patterns)
    if similar:
        print(f"경고: 유사한 패턴이 있습니다:")
        for p, score in similar:
            print(f"  - {p['id']}: {p['name']} (공통 단어: {score})")
        print()

    # 카테고리 자동 분류
    category = find_category(name)

    # 카테고리별 최대 서브-ID 계산 — 기존 카테고리 내 다음 번호 할당
    cat_max: dict[str, int] = {}
    for p in patterns:
        try:
            cat, sub = p["id"].split(".")
            cat_max[cat] = max(cat_max.get(cat, 0), int(sub))
        except (ValueError, IndexError):
            pass

    # 새 ID 생성 — 기존 카테고리 내에서 다음 번호, 없으면 새 카테고리 1.1
    existing_cats = sorted(cat_max.keys(), key=lambda x: int(x))
    if existing_cats:
        last_cat = existing_cats[-1]
        if cat_max[last_cat] > 0:
            new_id = f"{last_cat}.{cat_max[last_cat] + 1}"
        else:
            new_id = f"{last_cat}.1"
    else:
        new_id = "1.1"

    patterns.append(
        {
            "id": new_id,
            "name": name,
            "category": category,
            "last_seen": date.today().isoformat(),
            "occurrence_count": 1,
        }
    )
    save_patterns(patterns)

    # detail 파일에 섹션 추가
    detail_name = detail_file_for_category(category)
    detail_path = DETAIL_DIR / detail_name
    section_num = new_id.split(".")[0]
    new_block = (
        f"\n### {new_id} {name}\n\n"
        f"**증상**: {symptom}\n\n**원인**: {cause}\n\n```\n{fix}\n```\n"
    )
    if detail_path.is_file():
        detail_text = detail_path.read_text(encoding="utf-8")
        if f"### {new_id} " not in detail_text:
            if f"## {section_num}." not in detail_text:
                detail_text = detail_text.rstrip() + f"\n\n## {section_num}. {category}\n"
            detail_path.write_text(detail_text.rstrip() + new_block + "\n", encoding="utf-8")
    else:
        DETAIL_DIR.mkdir(parents=True, exist_ok=True)
        detail_path.write_text(
            f"## {section_num}. {category}\n{new_block}\n",
            encoding="utf-8",
        )

    print(f"추가됨: {new_id} - {name}")
    print(f"카테고리: {category}")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python add.py <name> <symptom> <cause> <fix>")
        sys.exit(1)

    name = sys.argv[1]
    symptom = sys.argv[2]
    cause = sys.argv[3]
    fix = sys.argv[4]

    add_pattern(name, symptom, cause, fix)
