"""Apply DX97-A bundle prereads + trim sections (run once)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/plans/archive/frontend/PLAN_diagnosis_widget_domain_deepening.md"

BUNDLES = {
    9: "docs/plans/refs/DX97_A_task_preread_BE.md",
    10: "docs/plans/refs/DX97_A_task_preread_BE10.md",
    11: "docs/plans/refs/DX97_A_task_preread_DOC.md",
    17: "docs/plans/refs/DX97_A_task_preread_FE.md",
}


def extract_target(action_line: str) -> str:
    m = re.search(r"\*\*Target\*\*:\s*`([^`]+)`", action_line)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"\*\*Target\*\*:\s*([^\n]+)", action_line)
    return m2.group(1).strip().split("|")[0].strip() if m2 else "docs/plans/archive/frontend/PLAN_diagnosis_widget_domain_deepening.md"


def compress_prereads_line_based(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("- **Pre-read**:") and "plan-task-preread:v1" in line:
            inst = re.search(r"must_read_installed=(\d+)", line)
            n = int(inst.group(1)) if inst else 0
            bundle = BUNDLES.get(n)
            block_start = i
            i += 1
            while i < len(lines) and not lines[i].startswith("- **Action**"):
                i += 1
            if not bundle:
                out.extend(lines[block_start:i])
                continue
            rest = "".join(lines[i : i + 12])
            am = re.search(r"- \*\*Action\*\*:[^\n]+", rest)
            if not am:
                out.extend(lines[block_start:i])
                continue
            target = extract_target(am.group(0))
            out.append(
                f"- **Pre-read**: [`{bundle}`]({bundle}) **전부** Read 후 `Target` 첫 경로 Read. "
                f"<!-- plan-task-preread:v1 paths=2 must_read_installed=2 -->\n"
                f"  1. `[bundle]` `{bundle}`\n"
                f"  2. `[code]` `{target}`\n"
            )
            continue
        out.append(line)
        i += 1
    return "".join(out)


def trim_sections(text: str) -> str:
    text = re.sub(
        r"## 📐 위젯 UI·Conceptual Sketch \(상세\)\n\n전체:.*?\n\n## 🛡️ Risk & Strategy",
        "## 📜 Conceptual Sketch (의사 코드)\n\n"
        "[`docs/plans/refs/DX97_A_supplement.md`](docs/plans/refs/DX97_A_supplement.md) §2 참조.\n\n"
        "## 📐 위젯 UI 구성 (제품 SSOT)\n\n"
        "[`docs/plans/refs/DX97_A_supplement.md`](docs/plans/refs/DX97_A_supplement.md) §1 참조.\n\n"
        "## 🛡️ Risk & Strategy",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"## 🔍 Impact Scope\n\n\| 파일 \|.*?(?=\n---\n\n## 🛠️ Step-by-Step Execution Plan)",
        "## 🔍 Impact Scope\n\n"
        "표: [`docs/plans/refs/DX97_A_supplement.md`](docs/plans/refs/DX97_A_supplement.md) §3.\n\n"
        "---\n\n"
        "## 🛠️ Step-by-Step Execution Plan",
        text,
        count=1,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"## 🛠️ Step-by-Step\n---\n\n",
        "",
        text,
    )
    text = re.sub(
        r"## 📊 검증 행렬\n\n\| Scope \| Command \|\n.*?(?=\n---\n\n## 📋 단일 실행 경로)",
        "## 📊 검증 행렬\n\n"
        "표: [`docs/plans/refs/DX97_A_supplement.md`](docs/plans/refs/DX97_A_supplement.md) §4.\n\n"
        "---\n\n"
        "## 📋 단일 실행 경로",
        text,
        count=1,
        flags=re.DOTALL,
    )
    return text


def main() -> None:
    text = PLAN.read_text(encoding="utf-8")
    text = compress_prereads_line_based(text)
    text = trim_sections(text)
    text = re.sub(r"^> \*\*Atomic ticket\*\*:.*\n", "", text, flags=re.MULTILINE)
    PLAN.write_text(text, encoding="utf-8")
    print("lines", len(text.splitlines()))


if __name__ == "__main__":
    main()
