#!/usr/bin/env python3
"""Preread section rendering for plan preread manifest generation."""
from __future__ import annotations

import re
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from scripts.agent.route_context import find_repo_root, get_route_bundle, normalize_repo_rel
from scripts.plan_loop.intent_utils import extract_plan_intents
from scripts.plan_loop.path_utils import SECTION_RE, extract_plan_paths, extract_task_paths
from scripts.plan_loop.spec_routing import route_spec_files
from scripts.plan_loop.stack_utils import _actionable_missing, infer_stack_labels

MARKER_PREFIX = "<!-- plan-preread:v1"
TASK_PREREAD_MARKER = "plan-task-preread:v1"

# Tri-runtime neutral: file write / partial edit gate (not Cursor tool names).
PREREAD_EDIT_GATE = "`write`/`patch`"
RUNTIME_EDIT_TOOLS_LINK = ".agents/core/runtime_edit_tools.md"

LEGACY_MCP_PREREAD_BLURBS: tuple[str, ...] = (
    "> **💡 MCP 도구 적극 활용**: 브라우저 테스트, 외부 검색, 기타 도구 연동이 필요한 작업이라면, 직접 스크립트를 작성하거나 추측하기 전에 **반드시 관련 MCP 도구(chrome-devtools, fia, playwright 등)를 먼저 호출**하여 확인하세요.",
    "> **💡 MCP 도구 적극 활용**: 브라우저 테스트, 외부 검색, 기타 도구 연동이 필요한 작업이라면, 직접 스크립트를 작성하거나 추측하기 전에 **반드시 관련 MCP 도구 (chrome-devtools, fia, playwright 등) 를 먼저 호출**하여 확인하세요.",
    "> **💡 MCP 도구 적극 활용**: 브라우저 테스트·외부 검색·파일 편집 등 MCP로 해결 가능한 작업은 스크립트 추측 전에 "
    "**[mcp_tools.md](.agents/reference/mcp_tools.md) SSOT**의 서버·도구명을 확인하고 호출하세요.",
)

TASK_HEADING_RE = re.compile(r"^####\s+Task\b.*$", re.MULTILINE)
PACKED_TASK_META_RE = re.compile(r"^-\s*Task-ID:\s*(?P<rest>.*)$")
TASK_PREREAD_BLOCK_RE = re.compile(
    r"^- \*\*Pre-read\*\*:.*\n(?:  \d+\. [^\n]+\n)*",
    re.MULTILINE,
)

MAX_INSTALLED_PREREAD = 5
MAX_RULE_PREREAD_SLOTS = 2

_KIND_PRIORITY: dict[str, int] = {
    "rule": 0,
    "spec": 1,
    "project_skill": 2,
    "skill": 2,
}


def _kind_priority(kind: object) -> int:
    return _KIND_PRIORITY.get(str(kind or ""), 99)


def cap_installed_entries(
    entries: Sequence[dict[str, object]],
    *,
    max_n: int = MAX_INSTALLED_PREREAD,
) -> list[dict[str, object]]:
    """Trim installed must_read rows to *max_n*, preserving rules and kind priority."""
    installed = [e for e in entries if e.get("installed")]
    if len(installed) <= max_n:
        return list(installed)

    indexed = list(enumerate(installed))
    rules = [(i, e) for i, e in indexed if e.get("kind") == "rule"]
    others = [(i, e) for i, e in indexed if e.get("kind") != "rule"]

    kept_rule_count = min(len(rules), MAX_RULE_PREREAD_SLOTS, max_n)
    kept_indices = {i for i, _ in rules[:kept_rule_count]}

    slots_left = max_n - len(kept_indices)
    if slots_left > 0 and others:
        others_sorted = sorted(others, key=lambda t: (_kind_priority(t[1].get("kind")), t[0]))
        for i, _ in others_sorted[:slots_left]:
            kept_indices.add(i)

    result = [installed[i] for i in sorted(kept_indices)]
    dropped = [e for i, e in enumerate(installed) if i not in kept_indices]
    if dropped:
        dropped_paths = ", ".join(str(e.get("path", "")) for e in dropped)
        print(
            f"WARN plan-preread: cap installed {len(installed)}->{max_n}, dropped: {dropped_paths}",
            file=sys.stderr,
        )
    return result


def render_task_preread_field(
    *,
    paths: Sequence[str],
    bundle: dict[str, object],
) -> str:
    """Per-task Pre-read block — co-located so single-task sessions cannot skip the doc gate."""
    must_read = bundle.get("must_read") or []
    installed = cap_installed_entries(list(must_read))
    ts_paths = len(paths)
    ts_installed = len(installed)

    lines = [
        "- **Pre-read**: "
        f"이 Task만 — {PREREAD_EDIT_GATE} 전 **전부** Read "
        f"<!-- {TASK_PREREAD_MARKER} paths={ts_paths} must_read_installed={ts_installed} -->",
    ]
    if installed:
        for i, entry in enumerate(installed, start=1):
            kind = entry.get("kind", "?")
            path = entry.get("path", "")
            lines.append(f"  {i}. `[{kind}]` `{path}`")
    else:
        lines.append(
            "  1. _(없음 — `Target`에 경로를 넣은 뒤 `just plan-preread <plan> --write` 재실행)_",
        )
    return "\n".join(lines)


def upsert_preread_in_task_block(block: str, preread_field: str) -> str:
    """Insert or replace **Pre-read** immediately after the Task-ID meta line."""
    if TASK_PREREAD_BLOCK_RE.search(block):
        return TASK_PREREAD_BLOCK_RE.sub(preread_field + "\n", block, count=1)

    lines = block.splitlines()
    insert_idx = 1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if PACKED_TASK_META_RE.match(stripped) or stripped.startswith("- Task-ID:"):
            insert_idx = i + 1
            break
    lines.insert(insert_idx, preread_field)
    return "\n".join(lines)


def upsert_task_prereads_in_plan(
    content: str,
    *,
    repo_root: Path,
    intents: Sequence[str],
) -> tuple[str, int]:
    """Patch every Task block with a routed **Pre-read** list (local-LLM co-location SSOT)."""
    matches = list(TASK_HEADING_RE.finditer(content))
    if not matches:
        return content, 0

    updated = 0
    parts: list[str] = []
    cursor = 0
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        parts.append(content[cursor:start])
        block = content[start:end]
        paths = extract_task_paths(block, repo_root)
        if paths:
            bundle = get_route_bundle(paths, repo_root=repo_root, intent_queries=intents, tight=True)
            preread = render_task_preread_field(paths=paths, bundle=bundle)
            new_block = upsert_preread_in_task_block(block, preread)
            if new_block != block:
                updated += 1
            parts.append(new_block)
        else:
            parts.append(block)
        cursor = end
    parts.append(content[cursor:])
    return "".join(parts), updated


def _merge_specs_into_bundle(bundle: dict[str, object], spec_files: list[str], repo_root: Path) -> None:
    """Add routed spec files to bundle's must_read (after rules, before skills)."""
    if not spec_files:
        return

    must_read = bundle.get("must_read") or []
    must_read_paths = list(bundle.get("must_read_paths") or [])
    seen = set(must_read_paths)

    for rel in spec_files:
        if rel in seen:
            continue
        full = repo_root / rel
        entry = {"path": rel, "kind": "spec", "installed": full.is_file()}
        must_read.append(entry)
        if entry["installed"]:
            must_read_paths.append(rel)
            seen.add(rel)

    bundle["must_read"] = must_read
    bundle["must_read_paths"] = must_read_paths
    bundle["spec_files"] = spec_files


def render_preread_section(
    *,
    plan_rel: str,
    plan_text: str,
    paths: Sequence[str],
    intents: Sequence[str],
    bundle: dict[str, object],
    bundle_id: str | None = None,
) -> str:
    stacks = infer_stack_labels(paths, plan_text)
    must_read = bundle.get("must_read") or []
    installed = cap_installed_entries(list(must_read))
    missing_actionable = _actionable_missing(must_read)

    route_cmd_paths = " ".join(paths[:8])
    if len(paths) > 8:
        route_cmd_paths += f" … (+{len(paths) - 8} more)"

    intent_note = ", ".join(intents) if intents else "(없음 — 필요 시 `--intent` 추가)"
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    marker = f"{MARKER_PREFIX} generated={ts} paths={len(paths)} must_read_installed={len(installed)}"
    if bundle_id:
        marker += f" bundle_id={bundle_id}"
    marker += " -->"

    lines = [
        "## 🧭 Context Pre-read Gate (실행 전 필수)",
        "",
        marker,
        "",
        "**정책 (IDE 공통)**: [execution.md §2.8](.agents/core/execution.md) Context Route Gate. "
        f"**Read SSOT**은 각 Task 블록의 **`Pre-read`** 목록이다 — {PREREAD_EDIT_GATE} 전 **해당 Task** 목록을 전부 Read "
        f"(`write`/`patch` = 파일 쓰기·부분 수정 직전; 호스트 도구명은 [runtime_edit_tools.md §1]({RUNTIME_EDIT_TOOLS_LINK})). "
        "상단 게이트만 읽고 Task `Pre-read`를 건너뛰면 정책 위반.",
        "",
        f"**기술 스택 (계획서 추론)**: {', '.join(stacks)}",
        f"**의도 키워드 (계획서 추론)**: {intent_note}",
        f"**라우팅 입력 경로 ({len(paths)}개)**: "
        + (", ".join(f"`{p}`" for p in paths[:10]) if paths else "(없음 — Task `Target`·Impact Scope에 경로 추가 후 재생성)"),
        "",
        "### Read SSOT",
        "",
        "- **단일 Task 실행**(예: 「Task 1.1만」): 그 Task의 `Pre-read`만 Read.",
        "- **플랜 전체 순차 실행**: Task마다 해당 `Pre-read`를 **그 Task 착수 직전**에 Read(상단에 must_read 목록 없음 — 중복 제거).",
        f"- **플랜 전체 must_read 합집합(참고)**: installed {len(installed)}개 — 상세 경로는 각 Task `Pre-read`에만 나열.",
        "",
    ]

    if missing_actionable:
        lines.extend(
            [
                "",
                "### 미설치·누락 (Read 생략, 세션에만 기록)",
                "",
            ]
        )
        for entry in missing_actionable:
            lines.append(f"- `[{entry.get('kind', '?')}]` `{entry.get('path')}`")

    lines.extend(
        [
            "",
            "### 재검증 (구현 세션에서 편집 직전)",
            "",
            "```bash",
            f"just route {route_cmd_paths or '<paths...>'} --json",
            "```",
            "",
            f"플랜 갱신 시 본 절 재생성: `just plan-preread {plan_rel} --write` → `just plan-lint {plan_rel}`",
            "",
        ]
    )
    return "\n".join(lines)


def _normalize_packed_headings(text: str) -> str:
    """Re-break inline headings so plan-preread anchors stay bounded (never split `####` into `##`)."""
    text = re.sub(r"(?<!\n)(#### Task\b)", r"\n\n\1", text)
    text = re.sub(r"(?<!\n)(### Phase\b)", r"\n\n\1", text)
    text = re.sub(r"(?<!\n)(?<!#)(## (?!#))", r"\n\n\1", text)
    return text.lstrip("\n")


_MAX_GATE_SECTION_LINES = 80


def upsert_preread_section(content: str, section: str) -> str:
    match = SECTION_RE.search(content)
    if match and match.group(0).count("\n") <= _MAX_GATE_SECTION_LINES:
        return SECTION_RE.sub(section.rstrip() + "\n\n", content, count=1)

    anchor = re.search(r"^## 🔍 Diagnosis & Findings", content, re.MULTILINE)
    if anchor:
        pos = anchor.start()
        return content[:pos] + section.rstrip() + "\n\n\n" + content[pos:]

    meta_end = re.search(r"^## 문서 메타\s*$", content, re.MULTILINE)
    if meta_end:
        after = content.find("\n## ", meta_end.end())
        insert_at = after if after != -1 else len(content)
        return content[:insert_at] + "\n\n" + section.rstrip() + "\n\n" + content[insert_at:]

    return section.rstrip() + "\n\n\n" + content


def build_manifest_for_plan(
    plan_path: Path,
    *,
    repo_root: Path | None = None,
    extra_paths: Sequence[str] = (),
    extra_intents: Sequence[str] = (),
) -> dict[str, object]:
    root = repo_root or find_repo_root(plan_path.parent)
    text = plan_path.read_text(encoding="utf-8")
    paths = sorted(set(extract_plan_paths(text, root)) | {normalize_repo_rel(p) for p in extra_paths})
    intents = sorted(set(extract_plan_intents(text)) | set(extra_intents))
    bundle = get_route_bundle(paths, repo_root=root, intent_queries=intents, tight=True)

    # Route relevant spec files based on target paths
    spec_files = route_spec_files(paths, root)
    _merge_specs_into_bundle(bundle, spec_files, root)

    plan_rel = normalize_repo_rel(str(plan_path.relative_to(root)))
    section = render_preread_section(
        plan_rel=plan_rel,
        plan_text=text,
        paths=paths,
        intents=intents,
        bundle=bundle,
    )
    route_bundle = {
        "files": paths,
        "must_read": bundle.get("must_read", []),
        "must_read_paths": bundle.get("must_read_paths", []),
        "query": f"plan-preread:{plan_rel}",
        "classified_intents": intents,
    }

    return {
        "plan": plan_rel,
        "paths": paths,
        "intents": intents,
        "stack_labels": infer_stack_labels(paths, text),
        "bundle": bundle,
        "route_bundle": route_bundle,
        "section_markdown": section,
    }
