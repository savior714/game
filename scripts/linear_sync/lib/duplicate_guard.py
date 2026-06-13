"""Linear issue duplicate detection for Blueprint-linked issues."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
LINEAR_ID_RE = re.compile(r"TEM-\d+", re.IGNORECASE)
BLUEPRINT_PATH_IN_DESC_RE = re.compile(r"`(docs/plans/[^`]+\.md)`")
TITLE_SUFFIX_RE = re.compile(r"\s*\(TEM-(?:XXX|\d+)\)\s*$", re.IGNORECASE)
TERMINAL_STATE_TYPES = frozenset({"completed", "canceled"})


@dataclass
class LinearIssueBrief:
    identifier: str
    id: str
    title: str
    state_name: str
    state_type: str
    url: str = ""
    description: str = ""
    created_at: str = ""

    @classmethod
    def from_node(cls, node: dict[str, Any]) -> LinearIssueBrief:
        st = node.get("state") or {}
        return cls(
            identifier=str(node.get("identifier") or "").upper(),
            id=str(node.get("id") or ""),
            title=str(node.get("title") or ""),
            state_name=str(st.get("name") or ""),
            state_type=str(st.get("type") or ""),
            url=str(node.get("url") or ""),
            description=str(node.get("description") or ""),
            created_at=str(node.get("createdAt") or ""),
        )

    @property
    def is_terminal(self) -> bool:
        return self.state_type in TERMINAL_STATE_TYPES


@dataclass
class DuplicateGroup:
    plan_rel: str
    normalized_title: str
    canonical: str
    issues: list[LinearIssueBrief] = field(default_factory=list)

    @property
    def duplicates(self) -> list[LinearIssueBrief]:
        return [i for i in self.issues if i.identifier != self.canonical]


def normalize_title(title: str) -> str:
    """Strip trailing (TEM-XXX) / (TEM-NN) for fuzzy title grouping."""
    t = title.strip()
    while True:
        nxt = TITLE_SUFFIX_RE.sub("", t).strip()
        if nxt == t:
            break
        t = nxt
    return t


def blueprint_rel_path(plan_path: Path) -> str:
    try:
        return plan_path.resolve().relative_to(_REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return plan_path.resolve().as_posix()


def extract_blueprint_path_from_description(description: str) -> Optional[str]:
    m = BLUEPRINT_PATH_IN_DESC_RE.search(description or "")
    return m.group(1) if m else None


def scan_repo_linear_ids_for_plan(plan_rel: str) -> list[str]:
    """Collect TEM-NN tokens from plan files that reference this blueprint path."""
    root = _REPO_ROOT / "docs" / "plans"
    if not root.exists():
        return []
    counts: dict[str, int] = {}
    needle = plan_rel.replace("\\", "/")
    for path in root.rglob("*.md"):
        if path.name == "README.md":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = path.relative_to(_REPO_ROOT).as_posix()
        if rel != needle and needle not in text:
            continue
        for m in LINEAR_ID_RE.finditer(text):
            ident = m.group(0).upper()
            if ident == "TEM-XXX":
                continue
            counts[ident] = counts.get(ident, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: (-x[1], _tem_number(x[0])))
    return [ident for ident, _ in ranked]


def _tem_number(identifier: str) -> int:
    m = re.search(r"TEM-(\d+)", identifier, re.I)
    return int(m.group(1)) if m else 10**9


def search_issues_for_plan(client: Any, plan_path: Path, title: str) -> list[LinearIssueBrief]:
    """Query Linear for issues likely tied to this blueprint (path + title)."""
    rel = blueprint_rel_path(plan_path)
    stem = plan_path.name
    seen: dict[str, LinearIssueBrief] = {}
    for term in (rel, stem, normalize_title(title)[:48]):
        term = term.strip()
        if len(term) < 8:
            continue
        for node in client.search_issues(term, first=20):
            brief = LinearIssueBrief.from_node(node)
            if not brief.identifier.startswith("TEM-"):
                continue
            desc_path = extract_blueprint_path_from_description(brief.description)
            if not desc_path and brief.description:
                if rel in brief.description or Path(rel).name in brief.description:
                    desc_path = rel

            if desc_path:
                paths_match = (
                    desc_path == rel
                    or desc_path.endswith(rel)
                    or rel.endswith(desc_path)
                    or Path(desc_path).name == Path(rel).name
                )
                if not paths_match:
                    continue

            norm_brief_title = normalize_title(brief.title)
            norm_target_title = normalize_title(title)
            title_matched = (
                norm_brief_title == norm_target_title
                or (
                    len(norm_brief_title) >= 8
                    and len(norm_target_title) >= 8
                    and (norm_brief_title in norm_target_title or norm_target_title in norm_brief_title)
                )
            )

            if desc_path == rel or (desc_path and Path(desc_path).name == Path(rel).name) or title_matched:
                seen[brief.identifier] = brief
    return list(seen.values())


def pick_canonical_identifier(
    issues: list[LinearIssueBrief],
    *,
    plan_rel: str,
    prefer: Optional[str] = None,
) -> str:
    """Choose one canonical issue id for a duplicate cluster."""
    if not issues:
        raise ValueError("pick_canonical_identifier requires at least one issue")
    ids = {i.identifier for i in issues}
    if prefer and prefer.upper() in ids:
        return prefer.upper()

    repo_ranked = scan_repo_linear_ids_for_plan(plan_rel)
    for ident in repo_ranked:
        if ident in ids:
            return ident

    active = [i for i in issues if not i.is_terminal]
    pool = active if active else issues
    pool_sorted = sorted(pool, key=lambda i: (_tem_number(i.identifier), i.created_at))
    return pool_sorted[0].identifier


def build_duplicate_group(
    plan_path: Path,
    issues: list[LinearIssueBrief],
    *,
    prefer: Optional[str] = None,
) -> Optional[DuplicateGroup]:
    if len(issues) < 2:
        return None
    rel = blueprint_rel_path(plan_path)
    title = normalize_title(issues[0].title)
    canonical = pick_canonical_identifier(issues, plan_rel=rel, prefer=prefer)
    return DuplicateGroup(
        plan_rel=rel,
        normalized_title=title,
        canonical=canonical,
        issues=sorted(issues, key=lambda i: _tem_number(i.identifier)),
    )


def format_duplicate_report(group: DuplicateGroup, *, apply_hint: bool = True) -> str:
    lines = [
        f"⚠️  [Linear Dedup] Blueprint `{group.plan_rel}` — "
        f"{len(group.issues)} issues share the same scope.",
        f"   Canonical (SSOT): **{group.canonical}**",
    ]
    for dup in group.duplicates:
        lines.append(
            f"   Duplicate: {dup.identifier} ({dup.state_name}) — "
            f"{dup.url or dup.identifier}"
        )
    if apply_hint and any(not d.is_terminal for d in group.duplicates):
        lines.append(
            "   → `just linear-dedup --plan "
            f"{group.plan_rel} --apply` 로 고아 이슈를 Duplicate 처리할 수 있습니다."
        )
    return "\n".join(lines)


def find_duplicate_state_id(client: Any, issue_identifier: str) -> Optional[str]:
    states = client.get_team_states(issue_identifier)
    for name in ("Duplicate", "Canceled"):
        for st in states:
            if str(st.get("name")) == name and st.get("type") == "canceled":
                return str(st.get("id"))
    for st in states:
        if st.get("type") == "canceled":
            return str(st.get("id"))
    return None


def mark_issue_duplicate(
    client: Any,
    issue: LinearIssueBrief,
    *,
    canonical: str,
    dry_run: bool = False,
) -> bool:
    if issue.identifier == canonical or issue.is_terminal:
        return False
    state_id = find_duplicate_state_id(client, issue.identifier)
    if not state_id:
        return False
    comment = (
        f"## 중복 이슈 자동 정리\n\n"
        f"**Canonical**: [{canonical}](https://linear.app/templaremr/issue/{canonical})\n\n"
        f"`just linear-dedup` / `ensure_plan_linear_issue` 중복 가드에 의해 Duplicate 처리되었습니다."
    )
    if dry_run:
        print(f"  [dry-run] Would mark {issue.identifier} Duplicate → canonical {canonical}")
        return True
    ok = client.update_issue(issue.id, stateId=state_id)
    if ok:
        client.add_comment(issue.id, comment)
    return ok
