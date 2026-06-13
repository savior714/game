#!/usr/bin/env python3
"""
Compile vercel-react-best-practices rules/*.md → COMPILED.md.

Upstream Vercel agent-skills emits AGENTS.md; EMR renames output to COMPILED.md
so Cursor does not always-apply inject ~27k tokens.

Schema (upstream packages/react-best-practices-build):
- rules/_sections.md: section order, impact, intro
- rules/<prefix>-<name>.md: YAML frontmatter (title, impact, impactDescription, tags)
- Output: single markdown document with numbered sections/rules
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

OUTPUT_NAME = "COMPILED.md"
FORBIDDEN_NAME = "AGENTS.md"
RULE_BODY_LINK = re.compile(r"\]\(\./([^)#]+\.md)(#[^)]+)?\)")


def rewrite_rule_body_links(body: str) -> str:
    """Rules live under rules/; compiled output sits one level up."""

    def repl(match: re.Match[str]) -> str:
        path = match.group(1)
        anchor = match.group(2) or ""
        if path.startswith("rules/"):
            return match.group(0)
        return f"](./rules/{path}{anchor})"

    return RULE_BODY_LINK.sub(repl, body)


@dataclass(frozen=True)
class SkillProfile:
    id: str
    rel: str
    title: str
    description: str


SKILL_PROFILES: dict[str, SkillProfile] = {
    "vercel-react-best-practices": SkillProfile(
        id="vercel-react-best-practices",
        rel=".agents/skills/frontend/vercel-react-best-practices",
        title="React Best Practices",
        description="React and Next.js codebases",
    ),
    "vercel-composition-patterns": SkillProfile(
        id="vercel-composition-patterns",
        rel=".agents/skills/frontend/vercel-composition-patterns",
        title="React Composition Patterns",
        description="React component libraries",
    ),
}

DEFAULT_SKILL = "vercel-react-best-practices"


@dataclass
class SectionMeta:
    number: int
    title: str
    prefix: str
    impact: str
    introduction: str


@dataclass
class RuleMeta:
    title: str
    impact: str
    impact_description: str
    body: str
    prefix: str
    rule_id: str = ""


def find_repo_root(start: Path | None = None) -> Path:
    cur = (start or Path(__file__)).resolve()
    if cur.is_file():
        cur = cur.parent
    for parent in [cur, *cur.parents]:
        if (parent / "AGENTS.md").is_file() and (parent / ".agents").is_dir():
            return parent
    msg = "Could not find repo root"
    raise RuntimeError(msg)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip()] = val.strip()
    return meta, body


def parse_sections(sections_file: Path) -> list[SectionMeta]:
    content = sections_file.read_text(encoding="utf-8")
    blocks = re.split(r"(?=^## \d+\. )", content, flags=re.MULTILINE)
    sections: list[SectionMeta] = []
    for block in blocks:
        header = re.match(r"^## (\d+)\.\s+(.+?)(?:\s+\(([^)]+)\))?\s*$", block, re.MULTILINE)
        if not header:
            continue
        number = int(header.group(1))
        title = header.group(2).strip()
        prefix = (header.group(3) or "").strip()
        impact_m = re.search(r"\*\*Impact:\*\*\s+(\S+)", block)
        desc_m = re.search(r"\*\*Description:\*\*\s+(.+?)(?=\n\n|\Z)", block, re.DOTALL)
        sections.append(
            SectionMeta(
                number=number,
                title=title,
                prefix=prefix,
                impact=impact_m.group(1).upper() if impact_m else "MEDIUM",
                introduction=desc_m.group(1).strip() if desc_m else "",
            )
        )
    return sections


def rule_prefix(filename: str) -> str:
    base = filename.removesuffix(".md")
    if "-" not in base:
        return base
    return base.split("-", 1)[0]


def strip_duplicate_heading(body: str, title: str) -> str:
    lines = body.splitlines()
    if lines and lines[0].startswith("## "):
        heading = lines[0][3:].strip()
        if heading == title or heading.lower() == title.lower():
            body = "\n".join(lines[1:]).lstrip("\n")
    return body.strip()


def load_rules(rules_dir: Path, prefix_to_section: dict[str, SectionMeta]) -> dict[int, list[RuleMeta]]:
    by_section: dict[int, list[RuleMeta]] = {s.number: [] for s in prefix_to_section.values()}
    for path in sorted(rules_dir.glob("*.md")):
        name = path.name
        if name.startswith("_") or name == "README.md":
            continue
        prefix = rule_prefix(name)
        section = prefix_to_section.get(prefix)
        if section is None:
            continue
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        title = meta.get("title", name)
        body = strip_duplicate_heading(body, title)
        body = rewrite_rule_body_links(body)
        by_section[section.number].append(
            RuleMeta(
                title=title,
                impact=meta.get("impact", section.impact).upper(),
                impact_description=meta.get("impactDescription", ""),
                body=body,
                prefix=prefix,
            )
        )
    for rules in by_section.values():
        rules.sort(key=lambda r: r.title.casefold())
        for idx, rule in enumerate(rules, start=1):
            section_num = prefix_to_section[rule.prefix].number
            rule.rule_id = f"{section_num}.{idx}"
    return by_section


def slug_anchor(text: str) -> str:
    return re.sub(r"[^\w-]", "", text.lower().replace(" ", "-"))


def impact_line(impact: str, description: str) -> str:
    if description:
        return f"**Impact: {impact} ({description})**"
    return f"**Impact: {impact}**"


def generate_markdown(
    sections: list[SectionMeta],
    rules_by_section: dict[int, list[RuleMeta]],
    metadata: dict[str, object],
    *,
    title: str,
    description: str,
) -> str:
    version = str(metadata.get("version", "1.0.0"))
    org = str(metadata.get("organization", "Vercel Engineering"))
    date = str(metadata.get("date", "January 2026"))
    abstract = str(metadata.get("abstract", ""))
    references = list(metadata.get("references") or [])

    lines: list[str] = [
        f"# {title}",
        "",
        f"**Version {version}**  ",
        org,
        date,
        "",
        "> **Note:**  ",
        "> This document is mainly for agents and LLMs to follow when maintaining,  ",
        f"> generating, or refactoring {description}. Humans  ",
        "> may also find it useful, but guidance here is optimized for automation  ",
        "> and consistency by AI-assisted workflows.",
        "",
        "---",
        "",
        "## Abstract",
        "",
        abstract,
        "",
        "---",
        "",
        "## Table of Contents",
        "",
    ]

    for section in sections:
        sec_anchor = slug_anchor(f"{section.number} {section.title}")
        lines.append(
            f"{section.number}. [{section.title}](#{sec_anchor}) — **{section.impact}**"
        )
        for rule in rules_by_section.get(section.number, []):
            rule_anchor = slug_anchor(f"{rule.rule_id} {rule.title}")
            lines.append(f"   - {rule.rule_id} [{rule.title}](#{rule_anchor})")
    lines.extend(["", "---", ""])

    for section in sections:
        sec_anchor = slug_anchor(f"{section.number} {section.title}")
        lines.append(f"## {section.number}. {section.title}")
        lines.append("")
        lines.append(impact_line(section.impact, ""))
        lines.append("")
        if section.introduction:
            lines.append(section.introduction)
            lines.append("")
        for rule in rules_by_section.get(section.number, []):
            lines.append(f"### {rule.rule_id} {rule.title}")
            lines.append("")
            lines.append(impact_line(rule.impact, rule.impact_description))
            lines.append("")
            lines.append(rule.body)
            lines.append("")
        lines.extend(["---", ""])

    if references:
        lines.append("## References")
        lines.append("")
        for i, ref in enumerate(references, start=1):
            lines.append(f"{i}. [{ref}]({ref})")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build(
    skill_dir: Path,
    profile: SkillProfile,
    *,
    check_only: bool = False,
) -> dict[str, int]:
    rules_dir = skill_dir / "rules"
    metadata_file = skill_dir / "metadata.json"
    output_file = skill_dir / OUTPUT_NAME
    forbidden = skill_dir / FORBIDDEN_NAME

    sections = parse_sections(rules_dir / "_sections.md")
    prefix_to_section = {s.prefix: s for s in sections if s.prefix}
    rules_by_section = load_rules(rules_dir, prefix_to_section)
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    markdown = generate_markdown(
        sections,
        rules_by_section,
        metadata,
        title=profile.title,
        description=profile.description,
    )
    rule_count = sum(len(v) for v in rules_by_section.values())

    if check_only:
        if not output_file.is_file():
            msg = f"Missing {OUTPUT_NAME}; run build first"
            raise SystemExit(msg)
        if forbidden.is_file():
            msg = f"{FORBIDDEN_NAME} must not exist (Cursor always-applied risk)"
            raise SystemExit(msg)
        return {"sections": len(sections), "rules": rule_count}

    output_file.write_text(markdown, encoding="utf-8")
    if forbidden.is_file():
        forbidden.unlink()
    return {"sections": len(sections), "rules": rule_count}


def resolve_profile(skill_id: str) -> SkillProfile:
    profile = SKILL_PROFILES.get(skill_id)
    if profile is None:
        allowed = ", ".join(sorted(SKILL_PROFILES))
        msg = f"Unknown skill {skill_id!r}; allowed: {allowed}"
        raise SystemExit(msg)
    return profile


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile vendored agent skill rules → COMPILED.md (not AGENTS.md).",
    )
    parser.add_argument(
        "--skill",
        default=DEFAULT_SKILL,
        choices=sorted(SKILL_PROFILES),
        help="Skill profile id",
    )
    parser.add_argument(
        "--skill-dir",
        type=Path,
        default=None,
        help="Override skill directory (default: profile rel under repo root)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Build every registered skill profile",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify COMPILED.md exists and AGENTS.md absent",
    )
    args = parser.parse_args()

    repo = find_repo_root()
    targets: list[tuple[SkillProfile, Path]] = []
    if args.all:
        for profile in SKILL_PROFILES.values():
            targets.append((profile, repo / profile.rel))
    else:
        profile = resolve_profile(args.skill)
        skill_dir = args.skill_dir or (repo / profile.rel)
        targets.append((profile, skill_dir))

    for profile, skill_dir in targets:
        stats = build(skill_dir, profile, check_only=args.check)
        if args.check:
            print(
                f"OK [{profile.id}]: {OUTPUT_NAME} present, "
                f"{FORBIDDEN_NAME} absent ({stats['rules']} rules)"
            )
        else:
            print(
                f"Wrote {skill_dir / OUTPUT_NAME} [{profile.id}] "
                f"({stats['sections']} sections, {stats['rules']} rules); "
                f"removed {FORBIDDEN_NAME} if present"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
