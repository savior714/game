from __future__ import annotations

import re
from typing import Optional

EXECUTOR_REQUIRED_FIELDS = (
    "Task-ID",
    "Status",
    "Target",
    "Action",
    "Verify",
    "Dependency",
)

BLUEPRINT_REQUIRED_FIELDS = (
    "Task-ID",
    "Status",
    "Target",
    "Action",
    "Goal",
    "Verify",
    "Conclusion",
    "Dependency",
)

TASK_PREREAD_MARKER = "plan-task-preread:v1"

BLUEPRINT_REQUIRED_DOC_META_FIELDS = (
    "SSOT Check",
    "Architectural Goal",
    "Priority",
)

ALLOWED_STATUS = {"todo", "running", "done", "failed", "blocked"}

ALLOWED_RETRY = {"none", "once_on_flake"}

REQUIRED_SECTIONS = [
    (r"#\s*🗺️\s*Project Blueprint\s*:", "Title"),
    (r"##\s*문서\s*메타", "Meta"),
    (r"##\s*📋\s*업무\s*요약\s*\(\s*협업용\s*\)", "Collaboration Summary"),
    (r"##\s*🎯\s*Origin\s*Intent", "Origin Intent"),
    (r"##\s*⚠️\s*Edge\s*Case\s*Trace", "Edge Case Trace"),
    (r"##\s*🛠️\s*Step-by-Step\s*Execution\s*Plan", "Execution"),
    (r"##\s*🔁\s*Conclusion\s*&\s*Summary", "Conclusion"),
    (r"##\s*✅\s*Definition\s*of\s*Done\s*\(\s*DoD\s*\)", "DoD"),
]

REQUIRED_SECTION_HEADINGS = (
    "# 🗺️ Project Blueprint: [미완성]",
    "## 문서 메타",
    "## 📋 업무 요약 (협업용)",
    "## 🎯 Origin Intent",
    "## ⚠️ Edge Case Trace",
    "## 🛠️ Step-by-Step Execution Plan",
    "## 🔁 Conclusion & Summary",
    "## ✅ Definition of Done (DoD)",
)

BLUEPRINT_TITLE_LINE_RE = re.compile(
    r"^#\s*🗺️\s*Project Blueprint\s*:",
    re.MULTILINE,
)

BLUEPRINT_TITLE_CAPTURE_RE = re.compile(
    r"^#\s*🗺️\s*Project Blueprint:\s*(.*)$",
    re.MULTILINE,
)


def is_blueprint_markdown(text: str) -> bool:
    """True when the document has a Blueprint title line (whitespace-tolerant SSOT)."""
    return bool(BLUEPRINT_TITLE_LINE_RE.search(text))


TASK_HEADING_RE = re.compile(
    r"^####\s+Task(?:\s*:\s*|\s+\d+\.\d+).*?$",
    re.MULTILINE,
)

LETTER_PREFIX_TASK_HEADING_RE = re.compile(
    r"^####\s+Task\s+[A-Za-z]+\.\d+",
    re.MULTILINE,
)

FIELD_RE = re.compile(
    r"^- (?:\*\*(?P<bold_key>[^*]+)\*\*|(?P<plain_key>[A-Za-z\s-]+)):\s*(?P<value>.*)$"
)

CONCLUSION_FIELD_LINE_RE = re.compile(
    r"^- (?:\*\*Conclusion\*\*|Conclusion):\s*",
    re.MULTILINE,
)

EXTRA_TASK_CONCLUSION_HEADING_RE = re.compile(
    r"^#{2,3}\s+Conclusion(?:\s|$)",
    re.MULTILINE,
)

PACKED_TASK_META_RE = re.compile(r"^- Task-ID:\s*(?P<rest>.*)$")

ATOMIC_UNIT_TAG = "[Unit: Atomic]"
EPIC_UNIT_TAG = "[Unit: Epic]"
FEATURE_UNIT_TAG = "[Unit: Feature]"

DEPRECATED_LEVEL_LOW_TAG = "[Level: Low]"

FORBIDDEN_LEVEL_TAG_RE = re.compile(r"\[Level:\s*(Medium|High)\]", re.IGNORECASE)

PIPE_FIELD_RE = re.compile(
    r"^(?:\*\*(?P<bold_key>[^*]+)\*\*|(?P<plain_key>[A-Za-z\s-]+)):\s*(?P<value>.*)$"
)

CSF_HINT_PATTERNS = [
    r"\[해결 건수/잔여 건수 요약\]",
]

CSF_HINT_EXAMPLES = tuple()

BAD_PATTERNS = [
    r"\[TBD\]",
    r"완료 시 기입",
]

TASK_ID_PATTERN = re.compile(r"^\[[A-Z]{2,}(?:-[A-Z0-9]+)*-\d{3,}\]$")

KOREAN_CHAR_RE = re.compile(r"[\uac00-\ud7a3]")

CJK_CHAR_RE = re.compile(r"[\u4E00-\u9FFF\u3400-\u4DBF]")

LANG_KO_RE = re.compile(r"<!--\s*Language:\s*ko\s*-->")

CANONICAL_TODO_CONCLUSION_SLOTS = (
    "[판정 — 비개발자용 요약. 검증 결과]",
    "[판정 — 비개발자용 요약. 검증 결과. 코드 이름 배제]",
    "[완료 시 기입]",
)

PREMATURE_MEASURED_CONCLUSION_RES = (
    re.compile(r"^통과\s*[—\-–]", re.IGNORECASE),
    re.compile(r"^실패\s*[—\-–]", re.IGNORECASE),
    re.compile(r"^부분통과", re.IGNORECASE),
    re.compile(r"테스트\s+\d+\s*건", re.IGNORECASE),
    re.compile(r"전원\s+Green", re.IGNORECASE),
    re.compile(r"lint\s+0\s*오류", re.IGNORECASE),
    re.compile(r"타입\s*오류\s*없음", re.IGNORECASE),
    re.compile(r"typecheck.*성공", re.IGNORECASE),
)

CONCLUSION_ALLOWED_MARKERS = frozenset({
    "[PASS]", "[FAIL]", "[SKIP]", "[ERROR]", "[WARN]", "[OK]",
    "[DONE]", "[SUCCESS]", "[ABORT]", "[CANCELLED]",
    "[성공]", "[실패]", "[중단]", "[생략]",
})


def extract_blueprint_title(text: str) -> Optional[str]:
    match = BLUEPRINT_TITLE_CAPTURE_RE.search(text)
    return match.group(1).strip() if match else None


YAML_FRONTMATTER_KEYS = ("id", "type", "status", "last_verified")


def _parse_yaml_frontmatter(text: str) -> dict[str, str] | None:
    norm = text.replace("\r\n", "\n").replace("\r", "\n")
    start_m = re.search(r"^---\s*$", norm, re.MULTILINE)
    if start_m is None:
        return None
    rest = norm[start_m.end() :]
    end_m = re.search(r"^\s*---\s*$", rest, re.MULTILINE)
    if end_m is None:
        return None
    result: dict[str, str] = {}
    for line in rest[: end_m.start()].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result if result else None


def is_yaml_blueprint_doc(text: str) -> bool:
    if not is_blueprint_markdown(text):
        return False
    fm = _parse_yaml_frontmatter(text)
    if fm is None:
        return False
    if fm.get("type") != "PLAN":
        return False
    return all(key in fm for key in YAML_FRONTMATTER_KEYS)


def _yaml_blueprint_doc_meta_defaults(text: str) -> dict[str, str]:
    title = extract_blueprint_title(text) or "Blueprint"
    return {
        "SSOT Check": "N/A",
        "Architectural Goal": title,
        "Priority": "2",
    }


def _split_task_blocks(text: str) -> list[str]:
    matches = list(TASK_HEADING_RE.finditer(text))
    if not matches:
        return []

    blocks: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append(text[start:end].strip())
    return blocks


def _parse_fields(task_block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    lines = task_block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        packed = PACKED_TASK_META_RE.match(stripped)
        if packed:
            rest = packed.group("rest").strip()
            parts = [p.strip() for p in rest.split("|")]
            if parts:
                fields["Task-ID"] = parts[0].strip()
            for part in parts[1:]:
                if ":" not in part:
                    continue
                k, v = part.split(":", 1)
                fields[k.strip()] = v.strip()
            i += 1
            continue

        parsed = FIELD_RE.match(stripped)
        if not parsed:
            i += 1
            continue

        key = (parsed.group("bold_key") or parsed.group("plain_key") or "").strip()
        value = (parsed.group("value") or "").strip()
        if not key:
            i += 1
            continue

        if value == "":
            collected: list[str] = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.startswith("#### ") or nxt.startswith("### ") or nxt.startswith("## "):
                    break
                if nxt.startswith("- "):
                    break
                if nxt.strip() == "":
                    j += 1
                    continue
                collected.append(nxt.strip())
                j += 1

            if collected:
                fields[key] = "\n".join(collected).strip()
            else:
                fields[key] = ""
            i = j
            continue

        parts = [p.strip() for p in value.split("|")] if "|" in value else [value]
        if parts:
            fields[key] = parts[0].strip()
        for extra in parts[1:]:
            m = PIPE_FIELD_RE.match(extra)
            if not m:
                if fields[key]:
                    fields[key] = f"{fields[key]} {extra}"
                continue
            extra_key = (m.group("bold_key") or m.group("plain_key") or "").strip()
            extra_val = m.group("value").strip()
            if extra_key:
                fields[extra_key] = extra_val
        i += 1

    return fields


def _task_unit_tag(block: str) -> str | None:
    if ATOMIC_UNIT_TAG in block:
        return ATOMIC_UNIT_TAG
    if EPIC_UNIT_TAG in block:
        return EPIC_UNIT_TAG
    if FEATURE_UNIT_TAG in block:
        return FEATURE_UNIT_TAG
    if DEPRECATED_LEVEL_LOW_TAG in block:
        return DEPRECATED_LEVEL_LOW_TAG
    return None


def _is_blueprint_task(block: str, fields: dict[str, str]) -> bool:
    has_blueprint_keys = any(k in fields for k in ("Goal", "Conclusion"))
    has_numbered_heading = bool(re.search(r"^####\s+Task\s+\d", block, flags=re.MULTILINE))
    has_unit_tag = _task_unit_tag(block) is not None
    return has_blueprint_keys or has_numbered_heading or has_unit_tag


def _extract_doc_meta_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    if is_yaml_blueprint_doc(text):
        fields.update(_yaml_blueprint_doc_meta_defaults(text))
    first_task = TASK_HEADING_RE.search(text)
    meta_region = text[: first_task.start()] if first_task else text
    fields.update(_parse_fields(meta_region))
    return fields


def _is_unfilled_csf_hint(value: str) -> bool:
    normalized = value.strip()
    if not normalized:
        return False
    return any(re.search(pattern, normalized) for pattern in CSF_HINT_PATTERNS)


def _is_valid_open_conclusion(value: str) -> bool:
    """True when Conclusion is an allowed CSF slot for todo/running (not measured text)."""
    normalized = value.strip()
    if not normalized:
        return False
    if normalized in CANONICAL_TODO_CONCLUSION_SLOTS:
        return True
    return _is_unfilled_csf_hint(normalized)


def _looks_like_premature_measured_conclusion(value: str) -> bool:
    """Detect completion-style Conclusion on tasks that are not done yet."""
    normalized = value.strip()
    if not normalized or _is_valid_open_conclusion(normalized):
        return False
    if any(pat.search(normalized) for pat in PREMATURE_MEASURED_CONCLUSION_RES):
        return True
    if normalized.startswith("[") and normalized.endswith("]"):
        inner = normalized[1:-1].strip()
        if inner != normalized and any(pat.search(inner) for pat in PREMATURE_MEASURED_CONCLUSION_RES):
            return True
    return False
