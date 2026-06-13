#!/usr/bin/env python3
"""Scan renderer TSX components and regenerate component-preview auto catalog.

수동 등록: 컴포넌트 옆 `{Name}.playground.tsx` (playground export)
자동 등록: 본 스크립트 → catalog.auto.generated.tsx

Opt-out: 소스 파일 상단 `@playground-skip`
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_RENDERER_SRC = _REPO / "apps" / "renderer" / "src"
_OUT = _REPO / "apps" / "renderer" / "src" / "app" / "component-preview" / "catalog.auto.generated.tsx"
_MANUAL_OUT = _REPO / "apps" / "renderer" / "src" / "app" / "component-preview" / "sidecars.manual.generated.tsx"

_SCAN_ROOTS = ("components", "features", "app")

_SKIP_DIR_PARTS = {
    "component-preview",
    "api",
    "__tests__",
    "mocks",
    "node_modules",
    "ui",  # shadcn / icons — 프리뷰 대상 아님
    "icons",
}

# 파일명 패턴 — UI 조각·도메인 컴포넌트만 (미매칭은 제외)
_INCLUDE_NAME_RE = re.compile(
    r"(Widget|Panel|State|Modal|Toolbar|Bar|Card|Table|Menu|Shell|Layout|"
    r"Form|Dialog|Sheet|Row|Grid|Chart|List|Hub|Indicator|Banner|Header|"
    r"Footer|Sidebar|Empty|Queue|Block|Section|Settings|Dashboard|Wizard|"
    r"Picker|Editor|Viewer|Overlay|Stub|Catalog|Desk|Action|Receipt|Billing|"
    r"Vital|Prescription|Diagnosis|Patient|Reception|Consultation|Admin|Login)",
)

# app/ 하위는 page.tsx 제외하고 components 폴더만
_APP_SKIP_SEGMENTS = {"component-preview", "api", "login", "design-lab"}

_SKIP_FILE_SUFFIXES = (
    ".test.tsx",
    ".stories.tsx",
    ".playground.tsx",
    ".playground.ts",
)

_SKIP_FILE_NAMES = {
    "page.tsx",
    "layout.tsx",
    "loading.tsx",
    "error.tsx",
    "not-found.tsx",
    "route.ts",
    "middleware.ts",
    "proxy.ts",
}

# (path fragment, page id) — 앞쪽(구체적) 우선
_PAGE_RULES: tuple[tuple[str, str], ...] = (
    ("/app/login/", "login"),
    ("/app/dashboard/admin/", "admin"),
    ("/app/dashboard/reception/", "reception"),
    ("/app/dashboard/billing/", "billing"),
    ("/app/dashboard/labs/", "dashboard"),
    ("/app/dashboard/", "dashboard"),
    ("/components/consultation/", "consultation"),
    ("/features/consultation/", "consultation"),
    ("/components/clinical/", "consultation"),
    ("/features/reception/", "reception"),
    ("/components/consultation/", "consultation"),
    ("/features/billing/", "billing"),
    ("/app/dashboard/billing/", "billing"),
    ("/features/admin/", "admin"),
    ("/app/dashboard/admin/", "admin"),
    ("/components/layout/", "shared"),
    ("/components/common/", "shared"),
    ("/components/auth/", "login"),
    ("/app/login/", "login"),
    ("/features/", "shared"),
    ("/components/", "shared"),
)

_RE_EXPORT_FN = re.compile(r"export\s+function\s+([A-Z][A-Za-z0-9_]*)")
_RE_EXPORT_CONST = re.compile(r"export\s+const\s+([A-Z][A-Za-z0-9_]*)\s*=")
_RE_INTERFACE_HEAD = re.compile(r"(?:export\s+)?interface\s+(\w+)\s*\{")
_RE_EXPORT_INLINE_PROPS = re.compile(
    r"export\s+function\s+(\w+)\s*\(\s*\{([^}]*)\}\s*:\s*\{([^}]*)\}\s*\)",
    re.DOTALL,
)
_RE_EXPORT_TYPED_PROPS = re.compile(
    r"export\s+function\s+(\w+)\s*\(\s*\{([^}]*)\}\s*:\s*(\w+Props)\s*\)",
    re.DOTALL,
)
_RE_EXPORT_SINGLE_PROPS = re.compile(
    r"export\s+function\s+(\w+)\s*\(\s*\w+\s*:\s*(\w+Props)\s*\)",
    re.DOTALL,
)


@dataclass(frozen=True)
class ComponentCandidate:
    name: str
    import_path: str
    page: str
    rel_path: str
    render_mode: str  # bare | mock | stub
    mock_props_jsx: str = ""
    mock_children_jsx: str = ""


def _pascal_to_kebab(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def _infer_page(path_posix: str) -> str:
    for fragment, page_id in _PAGE_RULES:
        if fragment in path_posix:
            return page_id
    return "shared"


def _should_skip_file(path: Path) -> bool:
    name = path.name
    if name in _SKIP_FILE_NAMES:
        return True
    if any(name.endswith(suffix) for suffix in _SKIP_FILE_SUFFIXES):
        return True
    parts = path.parts
    if set(parts) & _SKIP_DIR_PARTS:
        return True
    if "app" in parts and "components" not in parts:
        return True
    if not _INCLUDE_NAME_RE.search(path.stem):
        return True
    return False


def _has_playground_skip(content: str) -> bool:
    head = content[:800]
    return "@playground-skip" in head


def _has_manual_playground(tsx_path: Path) -> bool:
    return tsx_path.with_suffix(".playground.tsx").exists()


def _export_name(content: str, basename: str) -> str | None:
    stem = basename.removesuffix(".tsx")
    for pattern in (_RE_EXPORT_FN, _RE_EXPORT_CONST):
        for match in pattern.finditer(content):
            if match.group(1) == stem:
                return stem
    return None


def _extract_braced_body(content: str, open_brace_index: int) -> str | None:
    """`{` 직후부터 짝이 맞는 `}` 전까지 (중첩 객체 타입 지원)."""
    depth = 1
    pos = open_brace_index
    while pos < len(content) and depth > 0:
        ch = content[pos]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        pos += 1
    if depth != 0:
        return None
    return content[open_brace_index : pos - 1]


def _extract_interface_body(content: str, iface_name: str) -> str | None:
    for match in _RE_INTERFACE_HEAD.finditer(content):
        if match.group(1) != iface_name:
            continue
        return _extract_braced_body(content, match.end())
    return None


def _parse_prop_fields(body: str) -> list[tuple[str, str, bool]]:
    """(name, type_hint, optional) — 한 줄 한 필드 (인라인 객체 타입 허용)."""
    fields: list[tuple[str, str, bool]] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//") or line.startswith("*") or line.startswith("..."):
            continue
        line = line.removesuffix(",").removesuffix(";")
        optional = "?" in line.split(":")[0]
        match = re.match(r"([\w$]+)\??\s*:\s*(.+)$", line)
        if not match:
            continue
        fields.append((match.group(1), match.group(2).strip(), optional))
    return fields


def _required_props_from_interface(content: str, iface_name: str) -> list[tuple[str, str]]:
    body = _extract_interface_body(content, iface_name)
    if body is None:
        return []
    return [(n, t) for n, t, opt in _parse_prop_fields(body) if not opt]


def _required_props_for_component(content: str, component: str) -> list[tuple[str, str]]:
    expected_iface = f"{component}Props"
    required: list[tuple[str, str]] = []

    for match in _RE_INTERFACE_HEAD.finditer(content):
        iface = match.group(1)
        if iface not in (expected_iface, component):
            continue
        body = _extract_braced_body(content, match.end())
        if body is None:
            continue
        required.extend((n, t) for n, t, opt in _parse_prop_fields(body) if not opt)

    inline = _RE_EXPORT_INLINE_PROPS.search(content)
    if inline and inline.group(1) == component:
        required.extend((n, t) for n, t, opt in _parse_prop_fields(inline.group(3)) if not opt)

    typed = _RE_EXPORT_TYPED_PROPS.search(content)
    if typed and typed.group(1) == component:
        required.extend(_required_props_from_interface(content, typed.group(3)))

    single = _RE_EXPORT_SINGLE_PROPS.search(content)
    if single and single.group(1) == component:
        required.extend(_required_props_from_interface(content, single.group(2)))

    # dedupe by name
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for name, typ in required:
        if name in seen:
            continue
        seen.add(name)
        unique.append((name, typ))
    return unique


_RE_PASCAL_TYPE = re.compile(r"^[A-Z][A-Za-z0-9_]*(?:<[^>]+>)?$")

_MODAL_COMPONENT_NAME_RE = re.compile(r"(?:Modal|Dialog|Sheet)$")

_MOCK_OPEN_PROP_RE = re.compile(r"\b(?:isOpen|opened|open)=")

_MOCK_USER = '{ roles: ["doctor"] }'
_MOCK_BILLING_PATIENT = (
    '{ patient_id: "preview", patient_name: "김민준", birth_date: "2018-03-15", '
    'encounter_id: "enc-preview", account_id: "acc-preview", reason: "데모", '
    'waiting_time: 12, insurance_type: "건보" }'
)


def _mock_prop_expr(name: str, typ: str) -> str | None:
    typ_clean = typ.strip()
    typ_lower = typ_clean.lower()
    name_lower = name.lower()

    if typ_clean.startswith("Array<") or typ_clean.endswith("[]"):
        if "patient" in name_lower or "waiting" in name_lower:
            return f"[{_MOCK_BILLING_PATIENT}]"
        return "[]"

    if name == "user":
        return _MOCK_USER
    if name in ("isVisible",) or name.endswith("Visible") or name.startswith("can"):
        if "=>" in typ_clean and "boolean" in typ_lower:
            return "() => true"
    if name in ("opened", "open", "isOpen"):
        return "true"
    if name in ("patient", "selectedPatient", "detailPatient"):
        return _MOCK_BILLING_PATIENT

    if name.startswith("on") or name.startswith("handle") or "=>" in typ_clean:
        if "boolean" in typ_lower:
            return "() => true"
        return "() => {}"
    if name.startswith("set") and ("=>" in typ_clean or "void" in typ_lower):
        return "() => {}"
    if "| null" in typ_lower:
        return "null"
    if "| undefined" in typ_lower:
        return "undefined"
    if name in ("loading", "disabled", "submitting"):
        return "false"
    if "boolean" in typ_lower:
        return "false"
    if "number" in typ_lower:
        return "0"
    if "reactnode" in typ_lower or "react.reactnode" in typ_lower:
        return '"preview"'
    if "string" in typ_lower and "|" not in typ_clean:
        return '"preview"'
    if name.endswith("Id") or name == "id":
        return '"preview"'
    if typ_clean.startswith("Record<") or typ_clean.startswith("Map<") or "record<string" in typ_lower:
        return "{}"
    if "dispatch" in typ_lower or "setstateaction" in typ_lower:
        return "() => {}"
    # string literal union — 첫 리터럴
    if '"' in typ_clean or "'" in typ_clean:
        lit = re.search(r"""['"]([^'"]+)['"]""", typ_clean)
        if lit:
            return f'"{lit.group(1)}"'
    base = re.sub(r"\s*\|\s*(null|undefined)", "", typ_clean, flags=re.I).strip()
    if _RE_PASCAL_TYPE.match(base):
        return f"{{}} as {base}"
    return None


def _children_inner_jsx(expr: str) -> str:
    """Biome noChildrenProp: emit JSX children, not children={...} prop."""
    if expr.startswith('"') and expr.endswith('"'):
        return expr[1:-1]
    return f"{{{expr}}}"


def _analyze_render_mode(content: str, component: str) -> tuple[str, str, str]:
    required = _required_props_for_component(content, component)
    if not required:
        return "bare", "", ""
    mock_parts: list[str] = []
    children_inner = ""
    for name, typ in required:
        if name == "children":
            expr = _mock_prop_expr(name, typ)
            if expr is None:
                return "stub", "", ""
            children_inner = _children_inner_jsx(expr)
            continue
        expr = _mock_prop_expr(name, typ)
        if expr is None:
            return "stub", "", ""
        mock_parts.append(f"{name}={{{expr}}}")
    return "mock", " ".join(mock_parts), children_inner


def _import_path(path: Path) -> str:
    rel = path.relative_to(_RENDERER_SRC).as_posix()
    return f"@/src/{rel.removesuffix('.tsx')}"


def _discover() -> list[ComponentCandidate]:
    found: list[ComponentCandidate] = []
    seen_names: set[str] = set()

    for root_name in _SCAN_ROOTS:
        root = _RENDERER_SRC / root_name
        if not root.is_dir():
            continue
        for tsx in sorted(root.rglob("*.tsx")):
            if _should_skip_file(tsx):
                continue
            if _has_manual_playground(tsx):
                continue
            try:
                content = tsx.read_text(encoding="utf-8")
            except OSError:
                continue
            if _has_playground_skip(content):
                continue
            export_name = _export_name(content, tsx.name)
            if not export_name:
                continue
            rel_posix = tsx.relative_to(_RENDERER_SRC).as_posix()
            if export_name in seen_names:
                continue
            seen_names.add(export_name)
            render_mode, mock_props_jsx, mock_children_jsx = _analyze_render_mode(content, export_name)
            found.append(
                ComponentCandidate(
                    name=export_name,
                    import_path=_import_path(tsx),
                    page=_infer_page(f"/{rel_posix}"),
                    rel_path=rel_posix,
                    render_mode=render_mode,
                    mock_props_jsx=mock_props_jsx,
                    mock_children_jsx=mock_children_jsx,
                )
            )
    return found


def _group_by_page(candidates: list[ComponentCandidate]) -> dict[str, list[ComponentCandidate]]:
    grouped: dict[str, list[ComponentCandidate]] = {}
    for item in candidates:
        grouped.setdefault(item.page, []).append(item)
    for page_items in grouped.values():
        page_items.sort(key=lambda c: c.name)
    return grouped


def _uses_playground_modal_frame(item: ComponentCandidate) -> bool:
    if _MODAL_COMPONENT_NAME_RE.search(item.name):
        return True
    return bool(_MOCK_OPEN_PROP_RE.search(item.mock_props_jsx))


def _render_entry(item: ComponentCandidate) -> str:
    entry_id = _pascal_to_kebab(item.name)
    if item.render_mode == "stub":
        render_body = f"""          <PlaygroundAutostub
            label="{item.name}"
            hint="필수 props를 자동 생성할 수 없습니다. `{item.name}.playground.tsx` 에 mock을 지정하세요."
          />"""
    else:
        props = f" {item.mock_props_jsx}" if item.mock_props_jsx else ""
        if item.mock_children_jsx:
            component_tag = f"<{item.name}{props}>{item.mock_children_jsx}</{item.name}>"
        else:
            component_tag = f"<{item.name}{props} />"
        if _uses_playground_modal_frame(item):
            render_body = f"""          <PlaygroundPreviewBoundary label="{item.name}">
            <PlaygroundModalFrame>
              {component_tag}
            </PlaygroundModalFrame>
          </PlaygroundPreviewBoundary>"""
        else:
            render_body = f"""          <PlaygroundPreviewBoundary label="{item.name}">
            <div className="w-full max-w-3xl border border-border rounded-lg bg-card p-4 overflow-auto">
              {component_tag}
            </div>
          </PlaygroundPreviewBoundary>"""
    return f"""  {{
    page: "{item.page}",
    entries: [
      {{
        id: "{entry_id}",
        label: "{item.name}",
        description: "Auto · {item.rel_path}",
        tokens: PLAYGROUND_DEFAULT_TOKENS,
        render: () => (
{render_body}
        ),
      }},
    ],
  }},"""


def _emit_fixed(candidates: list[ComponentCandidate]) -> str:
    sidecar_blocks = [_render_entry(c) for c in sorted(candidates, key=lambda x: (x.page, x.name))]

    live = [c for c in candidates if c.render_mode in ("bare", "mock")]
    import_pairs = sorted({(c.import_path, c.name) for c in live}, key=lambda pair: pair[1])
    import_lines = [f'import {{ {name} }} from "{path}"' for path, name in import_pairs]

    return (
        "// @generated playground-sync — do not edit (just playground-sync)\n"
        "// @ts-nocheck — auto mock props; 수동 `.playground.tsx` 로 정밀 조정\n"
        '"use client"\n\n'
        'import { PlaygroundAutostub } from "./PlaygroundAutostub"\n'
        'import { PlaygroundModalFrame } from "./PlaygroundModalFrame"\n'
        'import { PlaygroundPreviewBoundary } from "./PlaygroundPreviewBoundary"\n'
        'import type { PlaygroundSidecarExport } from "./playgroundSidecar"\n'
        'import { PLAYGROUND_DEFAULT_TOKENS } from "./playgroundTokens"\n'
        + ("\n".join(import_lines) + "\n" if import_lines else "")
        + "\nexport const autoPlaygroundSidecars: PlaygroundSidecarExport[] = [\n"
        + "\n".join(sidecar_blocks)
        + "\n]\n"
    )


def _discover_playground_sidecars() -> list[Path]:
    found: list[Path] = []
    for root_name in _SCAN_ROOTS:
        root = _RENDERER_SRC / root_name
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.playground.tsx")):
            if "component-preview" in path.parts:
                continue
            found.append(path)
    app_playgrounds = _RENDERER_SRC / "app" / "component-preview" / "playgrounds"
    if app_playgrounds.is_dir():
        for path in sorted(app_playgrounds.glob("*.playground.tsx")):
            found.append(path)
    return found


def _emit_manual_sidecars(paths: list[Path]) -> str:
    header = (
        "// @generated playground-sync — do not edit (just playground-sync)\n"
        '"use client"\n\n'
        'import type { PlaygroundSidecarExport } from "./playgroundSidecar"\n'
    )
    if not paths:
        return header + "\nexport const manualPlaygroundSidecars: PlaygroundSidecarExport[] = []\n"

    import_lines: list[str] = []
    aliases: list[str] = []
    for index, path in enumerate(paths):
        rel = path.relative_to(_RENDERER_SRC).as_posix()
        import_path = f"@/src/{rel.removesuffix('.tsx')}"
        alias = f"playgroundSidecar{index}"
        import_lines.append(f'import {{ playground as {alias} }} from "{import_path}"')
        aliases.append(alias)

    body = ",\n  ".join(aliases)
    return (
        header
        + "\n"
        + "\n".join(import_lines)
        + "\n\nexport const manualPlaygroundSidecars: PlaygroundSidecarExport[] = [\n  "
        + body
        + ",\n]\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate component-preview auto catalog")
    parser.add_argument("--check", action="store_true", help="Fail if catalog would change")
    args = parser.parse_args()

    candidates = _discover()
    sidecar_paths = _discover_playground_sidecars()
    auto_output = _emit_fixed(candidates)
    manual_output = _emit_manual_sidecars(sidecar_paths)

    if args.check:
        stale = False
        if not _OUT.exists() or _OUT.read_text(encoding="utf-8") != auto_output:
            print("catalog.auto.generated.tsx is stale — run just playground-sync", file=sys.stderr)
            stale = True
        if not _MANUAL_OUT.exists() or _MANUAL_OUT.read_text(encoding="utf-8") != manual_output:
            print("sidecars.manual.generated.tsx is stale — run just playground-sync", file=sys.stderr)
            stale = True
        if stale:
            return 1
        print(
            f"playground catalog OK ({len(candidates)} auto, {len(sidecar_paths)} manual sidecars)",
        )
        return 0

    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(auto_output, encoding="utf-8")
    _MANUAL_OUT.write_text(manual_output, encoding="utf-8")
    print(
        f"Wrote {len(candidates)} auto → {_OUT.relative_to(_REPO)}; "
        f"{len(sidecar_paths)} manual → {_MANUAL_OUT.relative_to(_REPO)}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
