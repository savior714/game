"""build_verify_registry.py — Justfile·verify.sh 호출 트리를 자동 추출해 Markdown 레지스트리를 생성한다."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]  # repo root (scripts/verify/ → scripts/ → emr/)
JUSTFILE_PATH = ROOT / "Justfile"
VERIFY_SH_PATH = ROOT / "verify.sh"
OUTPUT_PATH = ROOT / "artifacts" / "verify" / "verify-call-registry.md"

# The 5 core verification commands
CORE_COMMANDS = ["verify", "lint", "lint-turn-end", "ci", "tdd-fast"]


# ---------------------------------------------------------------------------
# Justfile parser — 1 단계: just <child> 호출 문자열 추출
# ---------------------------------------------------------------------------


def parse_just_recipe(name: str) -> list[str]:
    """Justfile 에서 <name> 레시피 본문에 등장하는 'just <child>' 호출 리스트를 반환한다."""
    content = JUSTFILE_PATH.read_text(encoding="utf-8")
    lines = content.splitlines()

    # Find the recipe: line starting with "name:" (possibly with parameters)
    in_recipe = False
    recipe_lines: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Check if this is the recipe header
        if re.match(rf"^{re.escape(name)}[\s:]", line) and not line.startswith("\t"):
            in_recipe = True
            continue

        if in_recipe:
            # Recipe body lines start with a tab
            if line.startswith("\t"):
                recipe_lines.append(stripped)
            elif stripped == "":
                # Empty line within recipe body — keep it
                continue
            else:
                # Non-tab, non-empty line means recipe ended
                break

    # Extract "just <child>" calls from recipe body
    just_calls: list[str] = []
    for line in recipe_lines:
        match = re.search(r"just\s+(\S+)", line)
        if match:
            just_calls.append(match.group(1))

    return just_calls


# ---------------------------------------------------------------------------
# verify.sh parser — invoke_step 라벨 추출
# ---------------------------------------------------------------------------


def parse_verify_sh_steps() -> list[str]:
    """verify.sh 및 모듈 파일에서 invoke_step 첫 문자열 인자(라벨)를 순서 리스트로 반환한다."""
    content = VERIFY_SH_PATH.read_text(encoding="utf-8")
    labels: list[str] = []

    # Direct invoke_step calls in verify.sh
    for match in re.finditer(
        r'invoke_step\s+"([^"]+)"', content
    ):
        labels.append(match.group(1))

    # Also scan sourced module files
    modules = [
        "scripts/verify/backend.sh",
        "scripts/verify/frontend.sh",
        "scripts/verify/docs.sh",
        "scripts/verify/agentic_env.sh",
    ]
    for mod in modules:
        mod_path = ROOT / mod
        if mod_path.is_file():
            mod_content = mod_path.read_text(encoding="utf-8")
            for match in re.finditer(
                r'invoke_step\s+"([^"]+)"', mod_content
            ):
                labels.append(match.group(1))

    return labels


# ---------------------------------------------------------------------------
# Registry builder
# ---------------------------------------------------------------------------


def build_registry() -> dict[str, Any]:
    """5개 핵심 명령의 호출 트리를 담은 dict 를 반환한다."""
    result: dict[str, Any] = {"commands": {}}

    for cmd in CORE_COMMANDS:
        steps = parse_just_recipe(cmd)
        result["commands"][cmd] = {"steps": steps}

    return result


# ---------------------------------------------------------------------------
# Markdown report writer
# ---------------------------------------------------------------------------


def write_registry_markdown(registry: dict[str, Any], output_path: Path | None = None) -> Path:
    """레지스트리를 Markdown 불릿 트리로 <output_path> 에 기록한다."""
    out = output_path or OUTPUT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# verify", ""]
    for cmd_name, cmd_data in registry["commands"].items():
        lines.append(f"- **{cmd_name}**")
        steps = cmd_data.get("steps", [])
        if steps:
            for step in steps:
                lines.append(f"  - `{step}`")
        else:
            lines.append("  - _(직접 실행 또는 외부 스크립트)_")
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI 진입점 — 레지스트리 생성 후 Markdown 파일로 기록."""
    registry = build_registry()
    write_registry_markdown(registry)
    print(f"✅ Registry written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
