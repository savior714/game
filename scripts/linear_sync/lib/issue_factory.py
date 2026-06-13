"""Shared Linear issue creation from Blueprint metadata."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.linear_sync.lib.duplicate_guard import (  # noqa: E402
    blueprint_rel_path,
    build_duplicate_group,
    format_duplicate_report,
    pick_canonical_identifier,
    search_issues_for_plan,
)
from scripts.linear_sync.lib.issue_description import (  # noqa: E402
    build_issue_description_from_blueprint,
)
from scripts.linear_sync.lib.label_policy import (  # noqa: E402
    resolve_label_names_for_team,
    validate_labels_or_raise,
)
from scripts.linear_sync.lib.parser import PlanParser  # noqa: E402
from scripts.linear_sync.lib.plan_metadata import (  # noqa: E402
    BlueprintDocMeta,
    is_linear_placeholder,
    needs_linear_issue_creation,
    parse_doc_meta,
)
from scripts.linear_sync.sync_engine import LinearClient, load_env  # noqa: E402

# : Korean character check
KOREAN_CHAR_RE = re.compile(r"[\uac00-\ud7a3]")

STALE_LINEAR_TITLE_RE = re.compile(
    r"Global\s+Pre-read|세션\s*시작\s*시\s*한\s*번\s*로드",
    re.IGNORECASE,
)

LINEAR_ISSUE_LINE_RE = re.compile(
    r"(\*\*Linear-Issue\*\*|Linear-Issue):\s*"
    r"(?:"
    r"\[(?:TEM-\d+|TEM-XXX)\](?:\([^)]*\))?"
    r"|TEM-\d+"
    r"|TEM-XXX"
    r")",
    re.IGNORECASE,
)


@dataclass
class EnsureLinearResult:
    created: bool
    identifier: str | None = None
    url: str | None = None
    synced: bool = False
    message: str = ""


def pick_team_id(teams: list[dict]) -> str:
    preferred = (os.environ.get("LINEAR_TEAM_KEY") or "").strip().lower()
    if preferred:
        for node in teams:
            if str(node.get("key") or "").lower() == preferred:
                return node["id"]
    for node in teams:
        if "templar" in str(node.get("name") or "").lower():
            return node["id"]
    if not teams:
        raise RuntimeError("No Linear teams returned for this API key.")  # noqa: EM101, TRY003
    return teams[0]["id"]


def build_client() -> tuple[LinearClient | None, str]:
    load_env()
    api_key = (os.environ.get("LINEAR_API_KEY") or "").strip()
    if not api_key:
        return None, ""
    return LinearClient(api_key), api_key


def resolve_label_ids(
    client: LinearClient,
    team_id: str,
    label_names: list[str],
) -> tuple[list[str], list[str]]:
    """Resolve normalized team label names to Linear label IDs (no silent skip)."""
    nodes = client.get_team_labels_for_team(team_id)
    return resolve_label_names_for_team(label_names, nodes)


def create_linear_issue(
    *,
    title: str,
    description: str,
    priority: int | None = None,
    labels: list[str] | None = None,
    parent_id: str | None = None,
    dry_run: bool = False,
    client: LinearClient | None = None,
) -> dict | None:
    """Create a Linear issue; returns issue dict (identifier, id, url) or None on dry-run."""
    if client is None:
        client, _ = build_client()
    if client is None:
        raise RuntimeError("LINEAR_API_KEY not available after load_env().")  # noqa: EM101, TRY003

    # : Korean-first title enforcement
    if not KOREAN_CHAR_RE.search(title):
        print(f"  ❌ [] Linear issue title must contain Korean: '{title}'")
        raise ValueError(f"Issue title must contain Korean characters (): {title}")  # noqa: EM102, TRY003

    teams = client.list_teams()
    team_id = pick_team_id(teams)
    label_ids, label_failures = resolve_label_ids(client, team_id, labels or [])
    if label_failures:
        raise ValueError(  # noqa: TRY003
            f"Linear labels not on team allowlist or workspace: {', '.join(label_failures)}"  # noqa: EM102
        )

    if dry_run:
        print(f"[dry-run] Would create issue on teamId={team_id}")
        print(f"  title={title}")
        print(f"  priority={priority}")
        print(f"  labels={labels or []}")
        if parent_id:
            print(f"  parentId={parent_id}")
        return None

    return client.create_issue(
        team_id=team_id,
        title=title,
        description=description,
        priority=priority,
        label_ids=label_ids or None,
        parent_id=parent_id,
    )


def maybe_repair_stale_linear_title(
    client: LinearClient,
    issue: dict,
    meta: BlueprintDocMeta,
    plan_path: Path,
    *,
    dry_run: bool = False,
) -> bool:
    """Fix Linear titles that were set to Global Pre-read boilerplate."""
    current = str(issue.get("title") or "")
    if not STALE_LINEAR_TITLE_RE.search(current):
        return False
    new_title = _default_issue_title(meta, plan_path)
    if not new_title or new_title == current:
        return False
    ident = str(issue.get("identifier") or "")
    if dry_run:
        print(f"  [dry-run] Would repair title for {ident}: {current!r} -> {new_title!r}")
        return True
    ok = client.update_issue(issue["id"], title=new_title)
    if ok:
        print(f"  ✅ Repaired stale Linear title for {ident}: {new_title}")
    return ok


def _default_issue_title(meta: BlueprintDocMeta, plan_path: Path) -> str:
    if meta.title:
        title = meta.title
    else:
        stem = plan_path.stem.replace("_blueprint", "").replace("PLAN_", "")
        title = f"Blueprint: {stem}"

    if not KOREAN_CHAR_RE.search(title):
        title = f"{title} (상세 내용 참조)"

    return title


def _default_issue_description(plan_path: Path, meta: BlueprintDocMeta) -> str:
    content = plan_path.read_text(encoding="utf-8")
    tasks = PlanParser().parse(plan_path)
    return build_issue_description_from_blueprint(
        plan_path,
        content,
        tasks,
        meta,
        linear_identifier=meta.linear_issue,
    )


def patch_blueprint_linear_refs(
    plan_path: Path,
    identifier: str,
    url: str,
) -> bool:
    content = plan_path.read_text(encoding="utf-8")
    link = f"[{identifier}]({url})" if url else identifier

    new_content = content

    def _task_repl(m: re.Match[str]) -> str:
        return f"{m.group(1)}: {identifier}"

    task_lines: list[str] = []
    n_tasks = 0
    for line in new_content.splitlines():
        if "Task-ID:" in line:
            patched, count = LINEAR_ISSUE_LINE_RE.subn(_task_repl, line)
            n_tasks += count
            task_lines.append(patched)
        else:
            task_lines.append(line)
    new_content = "\n".join(task_lines)

    def _meta_repl(m: re.Match[str]) -> str:
        prefix = m.group(1)
        placeholder = m.group(2)
        suffix = m.group(3)
        if placeholder.startswith("("):
            return f"{prefix}({identifier}){suffix}"
        return f"{prefix}{identifier}{suffix}"

    new_content, n_h1 = re.subn(  # noqa: RUF059
        r"^(#\s*(?:🗺️\s*)?(?:Project Blueprint:\s*)?.*?)(\(TEM-XXX\)|\bTEM-XXX\b)(.*)$",
        _meta_repl,
        new_content,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    new_content, n_title = re.subn(  # noqa: RUF059
        r"^(\s*title:\s*.*?)(\(TEM-XXX\)|\bTEM-XXX\b)(.*)$",
        _meta_repl,
        new_content,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    new_content, n_doc = re.subn(
        r"^(- \*\*Linear-Issue\*\*:\s*).*$",
        rf"\1{link}",
        new_content,
        count=1,
        flags=re.MULTILINE,
    )
    if n_doc == 0:
        insert = f"- **Linear-Issue**: {link}\n"
        marker = "## 🔍 Diagnosis"
        if marker in new_content:  # noqa: SIM108
            new_content = new_content.replace(marker, insert + marker, 1)
        else:
            new_content = insert + new_content

    if new_content == content:
        return False
    plan_path.write_text(new_content, encoding="utf-8")
    print(f"  ✅ Blueprint patched: {n_tasks} task line(s), doc Linear-Issue → {identifier}")
    return True


def try_attach_existing_linear_issue(
    plan_path: Path,
    *,
    client: LinearClient,
    meta: BlueprintDocMeta,
    dry_run: bool,
    sync: bool,
) -> EnsureLinearResult | None:
    """Blueprint 경로·제목으로 Linear에 이미 있는 이슈를 찾아 패치만 수행(생성 생략)."""
    title = _default_issue_title(meta, plan_path)
    found = search_issues_for_plan(client, plan_path, title or plan_path.stem)
    if not found:
        return None

    prefer = (
        meta.linear_issue
        if meta.linear_issue and not is_linear_placeholder(meta.linear_issue)
        else None
    )
    canonical_id = pick_canonical_identifier(
        found,
        plan_rel=blueprint_rel_path(plan_path),
        prefer=prefer,
    )
    canonical = next(i for i in found if i.identifier == canonical_id)
    if len(found) > 1:
        group = build_duplicate_group(plan_path, found, prefer=prefer)
        if group:
            print(format_duplicate_report(group, apply_hint=False))

    if dry_run:
        return EnsureLinearResult(
            False,
            identifier=canonical_id,
            url=canonical.url or None,
            message=f"dry-run: would attach existing {canonical_id} (skip create)",
        )

    # Linear 상의 제목을 TEM-XXX -> 실제 ID로 교정
    if canonical.title and "TEM-XXX" in canonical.title.upper():
        final_title = re.sub(r"TEM-XXX", canonical_id, canonical.title, flags=re.IGNORECASE)
        try:
            client.update_issue(canonical.id, title=final_title)
            print(f"  ✅ Linear issue title updated for existing issue {canonical_id}: {final_title}")
        except Exception as exc:
            print(f"  ⚠️ Warning: failed to update Linear issue title for existing issue: {exc}")

    if not patch_blueprint_linear_refs(plan_path, canonical_id, canonical.url):
        return EnsureLinearResult(
            False,
            identifier=canonical_id,
            message=(
                f"found existing {canonical_id} but blueprint patch failed — "
                "fix Linear-Issue lines manually before re-running ensure"
            ),
        )

    synced = run_linear_sync(plan_path, dry_run=False) if sync else False
    return EnsureLinearResult(
        False,
        identifier=canonical_id,
        url=canonical.url or None,
        synced=synced,
        message=f"attached existing {canonical_id} (duplicate create prevented)",
    )


def run_linear_sync(plan_path: Path, *, dry_run: bool) -> bool:
    cmd = [
        sys.executable,
        str(_REPO_ROOT / "scripts" / "linear_sync" / "sync_engine.py"),
        "--plan",
        str(plan_path),
    ]
    if dry_run:
        cmd.append("--dry-run")
    proc = subprocess.run(cmd, cwd=_REPO_ROOT, check=False)  # noqa: S603
    return proc.returncode == 0


def ensure_plan_linear_issue(
    plan_path: Path,
    *,
    dry_run: bool = False,
    sync: bool = True,
) -> EnsureLinearResult:
    plan_path = plan_path.resolve()
    if not plan_path.exists():
        return EnsureLinearResult(False, message=f"file not found: {plan_path}")

    content = plan_path.read_text(encoding="utf-8")

    from scripts.linear_sync.lib.plan_metadata import is_project_blueprint_content  # noqa: PLC0415

    if is_project_blueprint_content(content):
        from scripts.linear_sync.lib.label_policy import validate_blueprint_labels  # noqa: PLC0415

        label_issues = validate_blueprint_labels(content)
        if label_issues:
            return EnsureLinearResult(
                False,
                message=f"label allowlist: {label_issues[0]}",
            )

    # : Linear-Issue ID 가 실제 Linear 에 존재하는지 API 검증
    # (ID 패턴만 보고 "기존 이슈"로 판단하면 삭제된/미생성 이슈에서 무한 루프 발생)
    meta = parse_doc_meta(content, plan_path)
    client, api_key = build_client()

    has_real_doc_issue = bool(
        meta.linear_issue and not is_linear_placeholder(meta.linear_issue)
    )
    stale_doc_issue = (
        has_real_doc_issue
        and bool(api_key and client)
        and not client.issue_exists(meta.linear_issue or "")
    )

    if not needs_linear_issue_creation(content, plan_path) and not stale_doc_issue:
        if has_real_doc_issue:
            if client and meta.linear_issue:
                issue = client.get_issue(meta.linear_issue)
                if issue:
                    maybe_repair_stale_linear_title(
                        client, issue, meta, plan_path, dry_run=dry_run
                    )
            if sync:
                ok = run_linear_sync(plan_path, dry_run=dry_run)
                return EnsureLinearResult(
                    False,
                    identifier=meta.linear_issue,
                    synced=ok,
                    message="existing Linear-Issue; metadata sync only",
                )
            return EnsureLinearResult(
                False,
                identifier=meta.linear_issue,
                message="existing Linear-Issue; no sync requested",
            )
        return EnsureLinearResult(False, message="minor plan or no action needed")

    if stale_doc_issue:
        print(
            f"  ⚠️ Linear issue {meta.linear_issue} referenced in plan "
            f"but does NOT exist — searching for existing issue or creating."
        )

    if not api_key:
        return EnsureLinearResult(
            False,
            message=(
                "FATAL: LINEAR_API_KEY not found in .env. "
                "Cannot create Linear issue for this Blueprint.\n"
                "1. Add LINEAR_API_KEY to .env\n"
                "2. Or set Linear-Policy: internal in Blueprint metadata to skip\n"
                "See: .agents/workflows/linear.md §API 키·.env SSOT"
            ),
        )

    if client:
        attached = try_attach_existing_linear_issue(
            plan_path,
            client=client,
            meta=meta,
            dry_run=dry_run,
            sync=sync,
        )
        if attached:
            return attached

    title = _default_issue_title(meta, plan_path)
    description = _default_issue_description(plan_path, meta)
    priority = meta.priority if meta.priority is not None else 3
    try:
        normalized_labels = validate_labels_or_raise(meta.labels) if meta.labels else []
    except Exception as exc:
        return EnsureLinearResult(False, message=f"label allowlist: {exc}")

    try:
        issue = create_linear_issue(
            title=title,
            description=description,
            priority=priority,
            labels=normalized_labels,
            dry_run=dry_run,
            client=client,
        )
    except Exception as exc:
        return EnsureLinearResult(False, message=f"issueCreate failed: {exc}")

    if dry_run or issue is None:
        return EnsureLinearResult(True, message="dry-run: would create issue and patch blueprint")

    ident = str(issue.get("identifier") or "")
    url = str(issue.get("url") or "")

    # Linear 상의 제목을 TEM-XXX -> 실제 ID로 교정
    if "TEM-XXX" in title.upper() and client:
        final_title = re.sub(r"TEM-XXX", ident, title, flags=re.IGNORECASE)
        try:
            client.update_issue(issue["id"], title=final_title)
            print(f"  ✅ Linear issue title updated: {final_title}")
        except Exception as exc:
            print(f"  ⚠️ Warning: failed to update Linear issue title: {exc}")

    if not patch_blueprint_linear_refs(plan_path, ident, url):
        return EnsureLinearResult(
            False,
            identifier=ident,
            url=url or None,
            message=(
                f"created {ident} but blueprint patch failed — "
                "re-run ensure after fixing Linear-Issue lines to avoid duplicates"
            ),
        )

    synced = False
    if sync:
        synced = run_linear_sync(plan_path, dry_run=False)

    return EnsureLinearResult(
        created=True,
        identifier=ident,
        url=url,
        synced=synced,
        message=f"created {ident}",
    )
