"""Blueprint document metadata: Priority, Labels, Linear-Issue placeholders."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from scripts.linear_sync.lib.label_policy import apply_label_policy_drop_unknown

LINEAR_ID_RE = re.compile(r"TEM-\d+", re.IGNORECASE)
TASK_HEADING_RE = re.compile(r"^####\s+Task\b", re.MULTILINE)
BLUEPRINT_TITLE_RE = re.compile(r"^#\s+🗺️\s+Project Blueprint:\s*(.+)$", re.MULTILINE)

# Accepted before ensure_plan_linear replaces with a real identifier.
LINEAR_PLACEHOLDER_IDS = frozenset({"TEM-XXX", "TEM-000", "TEM-999", "XXX", "PENDING", "NONE", "N/A", "NULL"})

# Staff-facing product work only — see PLAN_linear_board_product_policy.md
PRODUCT_LINEAR_LABELS = frozenset(
    {
        "feature",
        "frontend",
        "backend",
        "ui/ux",
        "compliance",
        "medical",
        "refactor",
    }
)

PRIORITY_KEYWORDS: dict[str, int] = {
    "urgent": 1,
    "high": 2,
    "medium": 3,
    "normal": 3,
    "low": 4,
    "parked": 4,
}

PATH_LABEL_HINTS: tuple[tuple[str, str], ...] = (
    ("apps/renderer", "Frontend"),
    ("apps/desktop-tauri", "Frontend"),
    ("apps/sidecar", "Backend"),
    ("src/api", "Backend"),
    ("src/", "Backend"),
    ("scripts/automation", "Backend"),
    ("scripts/observability", "Backend"),
    ("scripts/", "Backend"),
    ("docs/specs/ui", "UI/UX"),
)

META_FIELD_RE = re.compile(
    r"^- \*\*(?P<key>[^*]+)\*\*:\s*(?P<value>.*)$",
    re.MULTILINE,
)

PACKED_TASK_META_RE = re.compile(r"^- Task-ID:\s*(?P<rest>.*)$", re.MULTILINE)


@dataclass
class BlueprintDocMeta:
    linear_issue: str | None = None
    priority: int | None = None
    labels: list[str] = field(default_factory=list)
    title: str | None = None
    linear_policy: str | None = None


def normalize_linear_token(value: str) -> str:
    """Strip brackets, markdown links, and whitespace from a Linear-Issue token."""
    v = value.strip()
    m = re.search(r"\[(TEM-\d+)\]", v, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    m = LINEAR_ID_RE.search(v)
    if m:
        return m.group(0).upper()
    v = re.sub(r"^[\[\(]|[\]\)]$", "", v).strip()
    return v.upper()


def is_linear_placeholder(value: str | None) -> bool:
    if not value or not str(value).strip():
        return True
    token = normalize_linear_token(str(value))
    if token in LINEAR_PLACEHOLDER_IDS:
        return True
    return not LINEAR_ID_RE.fullmatch(token)


def parse_priority(raw: str) -> int | None:
    """Parse Blueprint Priority into Linear API priority (1=Urgent … 4=Low)."""
    if not raw or not raw.strip():
        return None
    text = raw.strip()

    m = re.search(r"\bP([0-4])\b", text, re.IGNORECASE)
    if m:
        p = int(m.group(1))
        # P0→Urgent(1) … P3→Low(4); P4 stays Low
        return min(4, p + 1)

    m = re.search(r"\b(\d)\b", text)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 4:
            return n

    lower = text.lower()
    for word, pri in PRIORITY_KEYWORDS.items():
        if word in lower:
            return pri
    return None


def split_label_tokens(raw: str) -> list[str]:
    """Split a Labels field value without alias/allowlist normalization."""
    if not raw or not raw.strip():
        return []
    out: list[str] = []
    seen: set[str] = set()
    for part in re.split(r"[,|]", raw):
        label = part.strip()
        if not label:
            continue
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(label)
    return out


def parse_labels(raw: str) -> list[str]:
    return apply_label_policy_drop_unknown(split_label_tokens(raw), context="parse_labels")


def iter_blueprint_label_sources(content: str) -> list[tuple[str, str]]:
    """Yield (location, raw Labels value) from doc meta and packed task lines."""
    if not is_project_blueprint_content(content):
        return []

    sources: list[tuple[str, str]] = []
    meta_region = _meta_region(content)
    for match in META_FIELD_RE.finditer(meta_region):
        if match.group("key").strip() == "Labels":
            sources.append(("doc meta Labels", match.group("value").strip()))

    matches = list(TASK_HEADING_RE.finditer(content))
    for index, match in enumerate(matches, start=1):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        block = content[start:end]
        heading = match.group(0).strip()[:48]
        for line in block.splitlines():
            packed = PACKED_TASK_META_RE.match(line.strip())
            if not packed:
                continue
            for part in packed.group("rest").split("|"):
                if ":" not in part:
                    continue
                key, value = part.split(":", 1)
                if key.strip() == "Labels":
                    sources.append((f"Task#{index} Labels ({heading})", value.strip()))
            break

    return sources


def infer_labels_from_plan_path(plan_path: Path) -> list[str]:
    posix = plan_path.as_posix().lower()
    inferred: list[str] = []
    seen: set[str] = set()
    for fragment, label in PATH_LABEL_HINTS:
        if fragment in posix:
            key = label.lower()
            if key not in seen:
                seen.add(key)
                inferred.append(label)
    name = plan_path.name.lower()
    if "risk" in name or "security" in name:
        _add_label(inferred, seen, "Critical-P0")
    if "fhir" in name or "hapi" in name:
        _add_label(inferred, seen, "FHIR")
    if "ui" in name or "layout" in name or "frontend" in name:
        _add_label(inferred, seen, "Frontend")
    if "error" in name or "observability" in name or "infra" in name:
        _add_label(inferred, seen, "Backend")
    return apply_label_policy_drop_unknown(inferred, context="infer_labels_from_plan_path")


def _add_label(bucket: list[str], seen: set[str], label: str) -> None:
    key = label.lower()
    if key not in seen:
        seen.add(key)
        bucket.append(label)


def is_project_blueprint_content(content: str) -> bool:
    """True when content contains a Project Blueprint title (YAML frontmatter allowed)."""
    return BLUEPRINT_TITLE_RE.search(content) is not None


def extract_blueprint_title(content: str) -> str | None:
    m = BLUEPRINT_TITLE_RE.search(content)
    if m:
        return m.group(1).strip()
    return None


def _meta_region(content: str) -> str:
    first_task = TASK_HEADING_RE.search(content)
    return content[: first_task.start()] if first_task else content


def parse_doc_meta(content: str, plan_path: Path | None = None) -> BlueprintDocMeta:
    region = _meta_region(content)
    meta = BlueprintDocMeta(title=extract_blueprint_title(content))

    for m in META_FIELD_RE.finditer(region):
        key = m.group("key").strip()
        value = m.group("value").strip()
        if key == "Linear-Issue":
            token = normalize_linear_token(value.split("(")[0])
            if LINEAR_ID_RE.fullmatch(token) or not is_linear_placeholder(token):
                meta.linear_issue = token
        elif key == "Priority":
            meta.priority = parse_priority(value)
        elif key == "Labels":
            meta.labels = parse_labels(value)
        elif key == "Linear-Policy":
            meta.linear_policy = value.strip().lower()

    if plan_path is not None:
        for label in infer_labels_from_plan_path(plan_path):
            if label.lower() not in {x.lower() for x in meta.labels}:
                meta.labels.append(label)

    meta.labels = apply_label_policy_drop_unknown(meta.labels, context="doc_meta")
    return meta


def collect_linear_ids_from_content(content: str) -> set[str]:
    """Collect TEM-NN ids from authoritative Blueprint fields only.

    Doc meta ``Linear-Issue`` and Task ``Linear-Issue`` metadata are validated;
    narrative mentions (e.g. diagnosis evidence) must not block plan-close.
    """
    ids: set[str] = set()

    meta = parse_doc_meta(content)
    if meta.linear_issue and not is_linear_placeholder(meta.linear_issue):
        ids.add(normalize_linear_token(meta.linear_issue))

    matches = list(TASK_HEADING_RE.finditer(content))
    for index in range(len(matches)):
        start = matches[index].start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        block = content[start:end]
        for line in block.splitlines():
            packed = PACKED_TASK_META_RE.match(line.strip())
            if not packed:
                continue
            for part in packed.group("rest").split("|"):
                if ":" not in part:
                    continue
                key, value = part.split(":", 1)
                key = re.sub(r"\*\*", "", key.strip())
                if key != "Linear-Issue":
                    continue
                token = normalize_linear_token(value)
                if LINEAR_ID_RE.fullmatch(token) and not is_linear_placeholder(token):
                    ids.add(token)
            break

    return ids


def _has_product_linear_label(meta: BlueprintDocMeta) -> bool:
    """True when doc meta labels (after path inference) include a product-facing label."""
    labels_lower = {lbl.lower() for lbl in meta.labels}
    return bool(labels_lower & PRODUCT_LINEAR_LABELS)


def _is_workflow_improvement(meta: BlueprintDocMeta, plan_path: Path) -> bool:
    title = meta.title or plan_path.name
    title_lower = title.lower()

    # Only skip workflow improvement when the plan is purely about workflow
    # governance/tooling (no product-impacting changes like allowlist/baseline fixes)
    if "워크플로우" in title and "개선" in title:
        # Allow plans that fix concrete issues (allowlist, baseline, etc.)
        plan_name_lower = plan_path.name.lower()
        if any(word in plan_name_lower for word in ("allowlist", "baseline", "fix", "env")):
            return False
        return True
    if "workflow" in title_lower and "improve" in title_lower:
        plan_name_lower = plan_path.name.lower()
        if any(word in plan_name_lower for word in ("allowlist", "baseline", "fix", "env")):
            return False
        return True

    labels_lower = {lbl.lower() for lbl in meta.labels}
    return "workflow" in labels_lower or "governance" in labels_lower


INTERNAL_TOOLING_PATH_PREFIXES: tuple[str, ...] = (
    ".agents/",
    "scripts/agent/",
    "scripts/plan_loop/",
    "scripts/discover_loop/",
    "scripts/linear_sync/",
    "scripts/dev_quality/",
)


def _is_internal_tooling_plan(plan_path: Path, meta: BlueprintDocMeta) -> bool:
    """True when the plan is purely internal tooling / agent-ops (no product impact).

    A plan is considered internal when **either** of the following holds:
    1. Its path lives under known agent-tooling directories.
    2. Its doc-meta ``Linear-Policy: internal`` is explicitly set.
    """
    posix = plan_path.as_posix()
    if any(posix.startswith(prefix) for prefix in INTERNAL_TOOLING_PATH_PREFIXES):
        return True
    if meta.linear_policy == "internal":
        return True
    return False


def needs_linear_issue_creation(content: str, plan_path: Path) -> bool:
    """True when a major plan has no real TEM-NN doc-meta identifier yet.

    Only ``## 문서 메타`` ``Linear-Issue`` is authoritative. Narrative references
    (e.g. prior TEM-61) must not block ``ensure_plan_linear``.
    """
    if _is_minor_plan(plan_path):
        return False
    meta = parse_doc_meta(content, plan_path)

    if _is_internal_tooling_plan(plan_path, meta):
        return False

    if _is_workflow_improvement(meta, plan_path):
        return False

    # Allow plans with Improvement label when they fix concrete issues
    # (not purely workflow governance)
    if not _has_product_linear_label(meta):
        plan_name_lower = plan_path.name.lower()
        # Plans with Improvement label that address concrete fixes are valid
        if "Improvement" in meta.labels and any(
            word in plan_name_lower for word in ("fix", "baseline", "allowlist", "env")
        ):
            pass  # Allow creation despite no product label
        else:
            return False

    if meta.linear_issue and not is_linear_placeholder(meta.linear_issue):
        return False
    return True


def _is_minor_plan(plan_path: Path) -> bool:
    """True for hotfix/lint drives and meta auxiliary plans (INDEX, IMPLEMENTATION, steering).

    Meta suffixes use uppercase ``_INDEX`` / ``_IMPLEMENTATION`` so feature archives like
  ``PLAN_*_implementation.md`` are not skipped by mistake.
    """
    name = plan_path.name
    name_lower = name.lower()

    # Only match "fix" when it's the primary purpose (e.g. PLAN-hotfix-xxx, PLAN-lint-fix)
    # Don't match plans like PLAN-git-workflow-fixes where "fix" is part of a compound name
    if any(word in name_lower for word in ("lint", "consistency", "minor", "typo")):
        return True
    if name_lower.startswith("plan-hotfix") or name_lower.startswith("plan-hot-fix"):
        return True
    # "fix" only counts as minor when it's the sole or dominant descriptor
    fix_words = name_lower.replace("plan_", "").replace("-", " ").split()
    if fix_words == ["fix"] or (len(fix_words) <= 2 and "fix" in fix_words and any(w in fix_words for w in ("hot", "lint", "typo"))):
        return True

    if name.endswith("_INDEX.md") or name.endswith("_IMPLEMENTATION.md"):
        return True

    if name_lower == "roadmap_steering.md" or "roadmap_steering" in name_lower:
        return True

    if "pre-read" in name_lower or "pre_read" in name_lower:
        return True

    return False


def is_conclusion_placeholder(text: str) -> bool:
    """Conclusion이 플레이스홀더 패턴이면 True."""
    stripped = text.strip()
    return (
        stripped == "[완료 시 기입]"
        or stripped == "[해결 건수/잔여 건수 요약]"
        or (stripped.startswith("[") and stripped.endswith("]") and len(stripped) < 30)
    )

