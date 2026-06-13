"""Blueprint → Linear issue description (team-facing natural language).

SSOT layout: docs/templates/TEMPLATE_linear_issue_description.md
Natural-language sections appear above ``---``; paths and Blueprint links below.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.linear_sync.lib.parser import PlanParser, Task
from scripts.linear_sync.lib.plan_metadata import BlueprintDocMeta, parse_doc_meta
from scripts.linear_sync.lib.table_formatter import format_linear_body  # Linear 렌더링 호환성 향상

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

_META_FIELD_RE = re.compile(
    r"^- \*\*(?P<key>[^*]+)\*\*:\s*(?P<value>.*)$",
    re.MULTILINE,
)
_PHENOMENON_RE = re.compile(
    r"(?:###\s*현상[^\n]*|[-*]\s*\*\*현상[^*]*\*\*)\s*\n+"
    r"(?P<body>(?:[-*].+\n|(?![#|`]).+\n?)+)",
    re.MULTILINE | re.IGNORECASE,
)
_CONCLUSION_SECTION_RE = re.compile(
    r"##\s*🔁\s*Conclusion[^\n]*\n+(?P<body>.*?)(?=\n##\s|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)
_OUT_OF_SCOPE_RE = re.compile(
    r"(?:##\s*[^\n]*(?:Out of Scope|비목표|범위 경계)[^\n]*|###\s*[^\n]*(?:Out of Scope|비목표)[^\n]*)\n+"
    r"(?P<body>(?:[-*].+\n|(?![#|`]).+\n?)+)",
    re.MULTILINE | re.IGNORECASE,
)

_BACKTICK_RE = re.compile(r"`+")
_PATHISH_RE = re.compile(
    r"\b(?:apps|src|docs)/[\w./\-]+\b|"
    r"\b[\w/]+\.(?:tsx?|py|md|css)\b",
    re.IGNORECASE,
)
_TASK_UNIT_TAG_RE = re.compile(r"\s*\[Unit:\s*Atomic\]\s*", re.IGNORECASE)
_TABLE_LINE_RE = re.compile(r"^\s*\|")


def _strip_noise(text: str, *, max_len: int = 600) -> str:
    """Remove paths, backticks, tables; cap length for Linear readability."""
    if not text:
        return ""
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or _TABLE_LINE_RE.match(line):
            continue
        if line.startswith("```"):
            continue
        line = _BACKTICK_RE.sub("", line)
        line = _PATHISH_RE.sub("", line)
        line = re.sub(r"\s+", " ", line).strip(" -•")
        if len(line) < 4:
            continue
        lines.append(line)
    out = " ".join(lines)
    out = re.sub(r"\s+", " ", out).strip()
    if len(out) > max_len:
        out = out[: max_len - 1].rstrip() + "…"
    return out


def _meta_value(content: str, key: str) -> str:
    for m in _META_FIELD_RE.finditer(content):
        if m.group("key").strip() == key:
            return _strip_noise(m.group("value").strip(), max_len=400)
    return ""


def _extract_phenomenon(content: str) -> str:
    m = _PHENOMENON_RE.search(content)
    if m:
        return _strip_noise(m.group("body"), max_len=500)
    # Fallback: first bullet under Diagnosis heading
    diag = re.search(
        r"##\s*🔍\s*Diagnosis[^\n]*\n+(?P<body>.*?)(?=\n##\s|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if diag:
        for raw_line in diag.group("body").splitlines():
            stripped = raw_line.strip()
            if stripped.startswith(("-", "*")) and "현상" not in stripped[:20]:
                cleaned = _strip_noise(stripped.lstrip("-* ").strip(), max_len=500)
                if cleaned:
                    return cleaned
    return ""


def _extract_conclusion_summary(content: str) -> str:
    m = _CONCLUSION_SECTION_RE.search(content)
    if not m:
        return ""
    bullets: list[str] = []
    for raw_line in m.group("body").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith(("-", "*")) and not stripped.startswith("- ["):
            text = _strip_noise(stripped.lstrip("-* ").strip(), max_len=200)
            if text and "placeholder" not in text.lower():
                bullets.append(text)
    return bullets[0] if bullets else _strip_noise(m.group("body"), max_len=300)


def _extract_out_of_scope(content: str) -> str:
    m = _OUT_OF_SCOPE_RE.search(content)
    if not m:
        return ""
    parts: list[str] = []
    for raw_line in m.group("body").splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith(("-", "*")):
            continue
        text = _strip_noise(stripped.lstrip("-* ").strip(), max_len=160)
        if text and ("제외" in text or "비목표" in text or "out of scope" in text.lower()):
            parts.append(text)
    return " · ".join(parts[:4])


def _human_task_title(title: str) -> str:
    t = _TASK_UNIT_TAG_RE.sub("", title).strip()
    t = re.sub(r"^Task\s+[\d.]+\s*:\s*", "", t, flags=re.IGNORECASE)
    t = _BACKTICK_RE.sub("", t)
    t = _PATHISH_RE.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t or title


def _summarize_tasks(
    tasks: list[Task | dict[str, Any]],
) -> tuple[str, list[str], list[str], int, int]:
    done = todo = blocked = 0
    todo_titles: list[str] = []
    done_titles: list[str] = []
    for t in tasks:
        if isinstance(t, Task):
            status = (t.status or "todo").lower()
            title = _human_task_title(t.title)
        else:
            status = str(t.get("status", "todo")).lower()
            title = _human_task_title(str(t.get("title", "")))
        if status == "done":
            done += 1
            if title:
                done_titles.append(title)
        elif status == "blocked":
            blocked += 1
        else:
            todo += 1
            if title and len(todo_titles) < 6:
                todo_titles.append(title)
    total = done + todo + blocked
    progress = f"전체 {total}개 작업 중 완료 {done}개"
    if blocked:
        progress += f", 보류 {blocked}개"
    if todo:
        progress += f", 남음 {todo}개"
    return progress, done_titles[-3:], todo_titles, done, todo


def build_issue_description_from_blueprint(
    plan_path: Path,
    content: str,
    tasks: list[Task | dict[str, Any]],
    meta: BlueprintDocMeta | None = None,
    *,
    linear_identifier: str | None = None,
    linear_url: str | None = None,
) -> str:
    """Render a Linear issue body from Blueprint content (template-aligned)."""
    if meta is None:
        meta = parse_doc_meta(content, plan_path)

    title = (meta.title or plan_path.stem).strip()
    goal = _meta_value(content, "Architectural Goal")
    status_link = _meta_value(content, "Project Status Link")
    phenomenon = _extract_phenomenon(content)
    conclusion = _extract_conclusion_summary(content)
    out_of_scope = _extract_out_of_scope(content)
    progress, recent_done, next_todos, done_count, todo_count = _summarize_tasks(tasks)

    overview_parts = [p for p in (goal, phenomenon) if p]
    if not overview_parts:
        overview_parts = [title]
    overview = " ".join(overview_parts[:2])

    progress_lines = [progress]
    if conclusion:
        progress_lines.append(conclusion)
    elif status_link:
        progress_lines.append(status_link)
    if recent_done:
        progress_lines.append("최근 완료: " + "; ".join(recent_done))

    include_items = [goal] if goal else [title]
    exclude_items = [out_of_scope] if out_of_scope else []

    action_lines: list[str] = []
    for t in next_todos:
        action_lines.append(f"- [ ] {t}")
    if not action_lines:
        if done_count > 0 and todo_count == 0:
            action_lines.append(
                "- [x] Blueprint 상 작업이 모두 완료되었습니다. Linear 상태·검수만 확인하면 됩니다."
            )
        else:
            action_lines.append(
                "- [ ] Blueprint Task 순서대로 착수 (세부는 개발용 Blueprint 참고)"
            )

    try:
        rel = plan_path.resolve().relative_to(_REPO_ROOT.resolve())
    except ValueError:
        rel = plan_path.resolve()

    ident = linear_identifier or meta.linear_issue or ""
    tech_lines = [
        f"- Blueprint: `{rel}`",
    ]
    if plan_path.name.startswith("PLAN_"):
        discuss_name = "DISCUSS_" + plan_path.name[len("PLAN_") :]
        discuss_path = plan_path.resolve().parent.parent / "discussions" / discuss_name
        if discuss_path.is_file():
            try:
                discuss_rel = discuss_path.relative_to(_REPO_ROOT.resolve())
            except ValueError:
                discuss_rel = discuss_path
            tech_lines.append(f"- 제품 결정 (DISCUSS): `{discuss_rel}`")
    if ident:
        tech_lines.append(f"- Linear: {ident}")
    if linear_url:
        tech_lines.append(f"- URL: {linear_url}")

    parts = [
        "## 개요",
        "",
        overview,
        "",
        "## 1. 진행 상황·맥락",
        "",
    ]
    for line in progress_lines:
        parts.append(f"- {line}")
    parts.extend(
        [
            "",
            "## 2. 범위·비범위",
            "",
            f"- **포함:** {' · '.join(x for x in include_items if x)}",
        ]
    )
    if exclude_items and exclude_items[0]:
        parts.append(f"- **제외:** {exclude_items[0]}")
    else:
        parts.append("- **제외:** Blueprint 「비목표」 절 참고")
    parts.extend(
        [
            "",
            "## 3. 다음 액션·승인 필요",
            "",
            *action_lines,
            "",
            "## 4. 더 밝혀 두면 좋은 점",
            "",
            "해당 없음 — 세부 기술 분기는 Blueprint와 코멘트로 이어 갑니다.",
            "",
            "---",
            "",
            "## 기술 참고 (개발자·에이전트용)",
            "",
            "※ 위 절은 비개발자 협업용 요약입니다. 실행·검증·파일 경로는 Blueprint가 SSOT입니다.",
            "",
            *tech_lines,
            "",
            "### 안내",
            "",
            "- Task Conclusion 댓글은 `just linear-sync` 로 동기화됩니다.",
            "- 본문 갱신: `just linear-sync --plan <blueprint> --refresh-description`",
        ]
    )
    body = "\n".join(parts)
    # Linear 렌더링 호환성 향상: GFM 표 → 불릿 카드 변환
    body = format_linear_body(body)
    return body


def refresh_issue_description_for_plan(
    client: Any,
    plan_path: Path,
    *,
    dry_run: bool = False,
) -> bool:
    """Push a refreshed description to the plan's Linear issue."""
    plan_path = plan_path.resolve()
    content = plan_path.read_text(encoding="utf-8")
    meta = parse_doc_meta(content, plan_path)
    linear_id = meta.linear_issue
    if not linear_id or linear_id.upper() in {"TEM-XXX", "XXX"}:
        print(f"  ⚠️ No Linear-Issue on {plan_path.name} — skip description refresh")
        return False

    tasks = PlanParser().parse(plan_path)
    issue = client.get_issue(linear_id)
    if not issue:
        print(f"  ⚠️ Linear issue {linear_id} not found — skip description refresh")
        return False

    body = build_issue_description_from_blueprint(
        plan_path,
        content,
        tasks,
        meta,
        linear_identifier=linear_id,
    )
    if dry_run:
        print(f"  [Dry-Run] Would refresh description on {linear_id} ({len(body)} chars)")
        return True

    ok = client.update_issue(issue["id"], title=issue.get("title"), description=body)
    if ok:
        print(f"  ✅ Refreshed description on {linear_id}")
    else:
        print(f"  ❌ Failed to refresh description on {linear_id}", file=__import__("sys").stderr)
    return bool(ok)
