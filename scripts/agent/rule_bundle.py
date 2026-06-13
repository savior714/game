#!/usr/bin/env python3
"""On-demand RULE_BUNDLE export from .agents/ (not tracked in git)."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / ".agents"
DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "share"

LINK_PATTERN = re.compile(r"\]\(([^)]+\.md)\)")

REGISTERED_SLUGS: tuple[str, ...] = ("discuss",)

CROSS_REVIEW_TEMPLATE = """## Cross-Review Prompt (copy to external LLM)

당신은 에이전트 운영 규칙 편집자입니다. 아래는 EMR 저장소의 `{slug}` 규칙 합본(스킬·워크플로·1-hop 참조)입니다.

검토 초점:
1. **중복** — 동일 규칙이 여러 절에 반복되는가?
2. **누락** — 실행에 필수인 단계·금지·핸드오프가 빠졌는가?
3. **모순** — SKILL vs workflow vs 1-hop 참조 간 상충하는가?
4. **구조** — 절 제목·우선순위·When/NOT 표가 탐색 가능한가?
5. **톤** — 비개발자-facing 문장에 불필요한 경로·Phase·린트가 섞였는가?
6. **역할 겹침** — `/assess`(코드 분석)·`/plan`(Blueprint)·`/discuss`(무코드 방향)과 경계가 흐려졌는가?

출력 형식:
- P0: 반드시 고칠 모순·누락 (파일 경로 + 제안 문장)
- P1: 구조·중복 정리 제안
- P2: 톤·표현 다듬기

코드베이스·앱 소스 수정 제안은 하지 마세요. `.agents/` 규칙 문서만 대상입니다.
"""


def _agents_rel(path: Path) -> str:
    return path.relative_to(AGENTS_DIR).as_posix()


def _resolve_agents_link(source_file: Path, link: str) -> Path | None:
    if link.startswith(("http://", "https://", "mailto:", "tel:")):
        return None
    clean = link.split("#")[0].strip()
    if not clean:
        return None
    resolved = (source_file.parent / clean).resolve()
    try:
        resolved.relative_to(AGENTS_DIR.resolve())
    except ValueError:
        return None
    return resolved if resolved.is_file() else None


def _extract_links(content: str, source_file: Path) -> list[Path]:
    found: list[Path] = []
    for match in LINK_PATTERN.finditer(content):
        target = _resolve_agents_link(source_file, match.group(1))
        if target is not None:
            found.append(target)
    return found


def collect_sources(slug: str) -> list[Path]:
    seeds = [
        AGENTS_DIR / "skills" / slug / "SKILL.md",
        AGENTS_DIR / "workflows" / f"{slug}.md",
    ]
    ordered: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        key = path.resolve()
        if key not in seen and key.is_file():
            seen.add(key)
            ordered.append(path)

    for seed in seeds:
        add(seed)

    for seed in list(ordered):
        one_hop = _extract_links(seed.read_text(encoding="utf-8"), seed)
        for path in one_hop:
            add(path)

    missing = [p for p in seeds if not p.is_file()]
    if missing:
        names = ", ".join(str(p) for p in missing)
        raise FileNotFoundError(f"Missing seed file(s) for slug '{slug}': {names}")
    return ordered


def build_bundle_text(slug: str) -> str:
    sources = collect_sources(slug)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    source_lines = "\n".join(f"  - .agents/{_agents_rel(p)}" for p in sources)

    parts = [
        "---\n",
        f"bundled_at: {ts}\n",
        f"target: {slug}\n",
        "sources:\n",
        f"{source_lines}\n",
        "---\n\n",
        f"# RULE_BUNDLE: {slug}\n\n",
    ]

    for path in sources:
        parts.append(f"## Inlined: {_agents_rel(path)}\n\n")
        body = path.read_text(encoding="utf-8")
        parts.append(body)
        if not body.endswith("\n"):
            parts.append("\n")
        parts.append("\n")

    parts.append(CROSS_REVIEW_TEMPLATE.format(slug=slug))
    if not parts[-1].endswith("\n"):
        parts.append("\n")
    return "".join(parts)


def build(slug: str, *, out_dir: Path, stdout: bool) -> int:
    text = build_bundle_text(slug)
    if stdout:
        sys.stdout.write(text)
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"RULE_BUNDLE_{slug}.md"
    out.write_text(text, encoding="utf-8")
    print(f"✅ Wrote {out.relative_to(REPO_ROOT)} (gitignored — paste for external LLM review)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export RULE_BUNDLE_<slug>.md from .agents/ (on demand)",
    )
    parser.add_argument("slug", choices=REGISTERED_SLUGS)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUT_DIR.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print bundle to stdout instead of writing a file",
    )
    args = parser.parse_args(argv)
    return build(args.slug, out_dir=args.out_dir.resolve(), stdout=args.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
