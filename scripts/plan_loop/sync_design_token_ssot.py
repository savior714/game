#!/usr/bin/env python3
"""Validate design token SSOT alignment across docs, CSS, and component-preview.

SSOT (runtime): apps/renderer/src/styles/tokens.css `:root`
Mirror (spec):  docs/design.md token tables
Playground:     apps/renderer/src/app/component-preview/playgroundTokens.ts defaults

Usage:
  uv run python scripts/plan_loop/sync_design_token_ssot.py --check
  just design-token-sync --check
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_TOKENS_CSS = _REPO / "apps" / "renderer" / "src" / "styles" / "tokens.css"
_DESIGN_MD = _REPO / "docs" / "design.md"
_PLAYGROUND_TOKENS = (
    _REPO / "apps" / "renderer" / "src" / "app" / "component-preview" / "playgroundTokens.ts"
)

_ROOT_BLOCK_RE = re.compile(r":root\s*\{", re.MULTILINE)
_VAR_LINE_RE = re.compile(r"^\s*(--[\w-]+)\s*:\s*([^;]+);", re.MULTILINE)
_GRADIENT_RGB_RE = re.compile(
    r"rgb\(\s*(\d+)\s+(\d+)\s+(\d+)\s*\)",
    re.IGNORECASE,
)
_DESIGN_ROW_RE = re.compile(r"^\|\s*`(--[\w-]+)`\s*\|\s*`([^`]+)`", re.MULTILINE)

_PLAYGROUND_VAR_RE = re.compile(r'varName:\s*"([^"]+)"')
_PLAYGROUND_KIND_RE = re.compile(r'kind:\s*"([^"]+)"')
_PLAYGROUND_DEFAULT_RE = re.compile(r"defaultValue:\s*([0-9.]+)")

# design.md documents simplified stacks; compare only when both sides are hex/rem/number
_SKIP_DESIGN_TOKENS = frozenset(
    {
        "--font-family-main",
        "--font-family-accent",
        "--font-family-mono",
        "--bg-accent-ai-gradient",
    }
)

_RGB_RE = re.compile(
    r"^rgb\(\s*(\d+)\s+(\d+)\s+(\d+)\s*\)$",
    re.IGNORECASE,
)
_VAR_REF_RE = re.compile(r"^var\(\s*(--[\w-]+)\s*\)$", re.IGNORECASE)


@dataclass(frozen=True)
class Drift:
    source: str
    token: str
    expected: str
    actual: str


def _extract_brace_block(css: str, open_brace_index: int) -> str:
    """Return inner text of `{ ... }` starting at open_brace_index."""
    depth = 1
    i = open_brace_index + 1
    while i < len(css) and depth > 0:
        ch = css[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return css[open_brace_index + 1 : i]
        i += 1
    raise ValueError("tokens.css: unclosed CSS block")


def parse_tokens_css_root(css: str) -> dict[str, str]:
    """Merge all `:root` blocks (base tokens + shadcn light mapping)."""
    merged: dict[str, str] = {}
    for match in _ROOT_BLOCK_RE.finditer(css):
        block = _extract_brace_block(css, match.end() - 1)
        for name, value in _VAR_LINE_RE.findall(block):
            merged[name] = value.strip()
    if not merged:
        raise ValueError("tokens.css: :root block not found")
    return merged


def _rgb_to_hex(value: str) -> str | None:
    match = _RGB_RE.match(value.strip())
    if not match:
        return None
    r, g, b = (int(match.group(i)) for i in range(1, 4))
    return f"#{r:02X}{g:02X}{b:02X}"


def _normalize_hex(value: str) -> str:
    v = value.strip().upper()
    if not v.startswith("#"):
        return v
    if len(v) == 4:
        return "#" + "".join(ch * 2 for ch in v[1:])
    return v


def resolve_css_value(vars_map: dict[str, str], name: str, seen: set[str] | None = None) -> str:
    seen = seen or set()
    if name in seen:
        return vars_map.get(name, "")
    seen.add(name)
    raw = vars_map.get(name, "").strip()
    if not raw:
        return ""
    var_match = _VAR_REF_RE.match(raw)
    if var_match:
        return resolve_css_value(vars_map, var_match.group(1), seen)
    return raw


def _normalize_gradient(value: str) -> str:
    def _rgb_sub(match: re.Match[str]) -> str:
        r, g, b = (int(match.group(i)) for i in range(1, 4))
        return f"#{r:02X}{g:02X}{b:02X}"

    normalized = _GRADIENT_RGB_RE.sub(_rgb_sub, value)
    return re.sub(r"\s+", " ", normalized.strip())


def normalize_token_value(raw: str, vars_map: dict[str, str] | None = None) -> str:
    value = raw.strip()
    if vars_map is not None:
        var_match = _VAR_REF_RE.match(value)
        if var_match:
            value = resolve_css_value(vars_map, var_match.group(1))

    hex_value = _normalize_hex(value) if value.startswith("#") else None
    if hex_value:
        return hex_value

    as_hex = _rgb_to_hex(value)
    if as_hex:
        return as_hex

    rem_match = re.match(r"^(-?\d+(?:\.\d+)?)rem$", value)
    if rem_match:
        return f"{float(rem_match.group(1))}rem"

    px_match = re.match(r"^(-?\d+(?:\.\d+)?)px$", value)
    if px_match:
        return f"{float(px_match.group(1))}px"

    num_match = re.match(r"^-?\d+(?:\.\d+)?$", value)
    if num_match:
        num = float(value)
        return str(int(num)) if num.is_integer() else str(num)

    if "linear-gradient" in value or "gradient" in value:
        return _normalize_gradient(value)

    # shadows, tabular-nums — compare collapsed whitespace
    return re.sub(r"\s+", " ", value)


def parse_design_md_tokens(md: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for name, value in _DESIGN_ROW_RE.findall(md):
        if name in _SKIP_DESIGN_TOKENS:
            continue
        tokens[name] = value.strip()
    return tokens


@dataclass(frozen=True)
class PlaygroundToken:
    var_name: str
    kind: str
    default_value: float


def parse_playground_tokens(ts: str) -> list[PlaygroundToken]:
    """Parse PLAYGROUND_DEFAULT_TOKENS object literals (field order may vary)."""
    start = ts.find("export const PLAYGROUND_DEFAULT_TOKENS")
    if start < 0:
        raise ValueError("playgroundTokens.ts: PLAYGROUND_DEFAULT_TOKENS not found")
    slice_ = ts[start:]
    end = slice_.find("]\n\n/**")
    if end < 0:
        end = slice_.find("]\n\nexport")
    if end < 0:
        raise ValueError("playgroundTokens.ts: token array end not found")
    body = slice_[:end]

    tokens: list[PlaygroundToken] = []
    for block in re.findall(r"\{[^{}]+\}", body, re.DOTALL):
        var_match = _PLAYGROUND_VAR_RE.search(block)
        kind_match = _PLAYGROUND_KIND_RE.search(block)
        default_match = _PLAYGROUND_DEFAULT_RE.search(block)
        if not (var_match and kind_match and default_match):
            continue
        tokens.append(
            PlaygroundToken(
                var_name=var_match.group(1),
                kind=kind_match.group(1),
                default_value=float(default_match.group(1)),
            )
        )
    return tokens


def _playground_expected_css(
    token: PlaygroundToken,
    css_vars: dict[str, str],
) -> tuple[str, str] | None:
    """Return (css_var_name, normalized_expected) or None if not mappable."""
    if token.kind == "rgb":
        channel_match = re.match(r"^(.+)-(r|g|b)$", token.var_name)
        if not channel_match:
            return None
        base = channel_match.group(1)
        channel = channel_match.group(2)
        css_name = f"--{base}"
        resolved = resolve_css_value(css_vars, css_name)
        rgb_match = _RGB_RE.match(resolved)
        if not rgb_match:
            return None
        idx = {"r": 1, "g": 2, "b": 3}[channel]
        return css_name, str(int(rgb_match.group(idx)))

    css_name = f"--{token.var_name}"
    resolved = resolve_css_value(css_vars, css_name)
    if token.kind == "rem":
        rem_match = re.match(r"^(-?\d+(?:\.\d+)?)rem$", resolved)
        if not rem_match:
            return None
        return css_name, str(float(rem_match.group(1)))
    if token.kind == "px":
        px_match = re.match(r"^(-?\d+(?:\.\d+)?)px$", resolved)
        if not px_match:
            return None
        return css_name, str(float(px_match.group(1)))
    if token.kind == "unitless":
        num_match = re.match(r"^-?\d+(?:\.\d+)?$", resolved)
        if not num_match:
            return None
        num = float(resolved)
        return css_name, str(int(num)) if num.is_integer() else str(num)
    return None


def diff_design_vs_css(
    design_tokens: dict[str, str],
    css_vars: dict[str, str],
) -> list[Drift]:
    drifts: list[Drift] = []
    for name, doc_value in sorted(design_tokens.items()):
        if name not in css_vars:
            drifts.append(Drift("design.md→tokens.css", name, doc_value, "<missing>"))
            continue
        css_resolved = resolve_css_value(css_vars, name)
        doc_norm = normalize_token_value(doc_value)
        css_norm = normalize_token_value(css_resolved, css_vars)
        if doc_norm != css_norm:
            drifts.append(Drift("design.md→tokens.css", name, doc_norm, css_norm))
    return drifts


def diff_playground_vs_css(
    playground: list[PlaygroundToken],
    css_vars: dict[str, str],
) -> list[Drift]:
    drifts: list[Drift] = []
    for token in playground:
        mapped = _playground_expected_css(token, css_vars)
        if mapped is None:
            drifts.append(
                Drift(
                    "playground→tokens.css",
                    token.var_name,
                    "<unmapped>",
                    resolve_css_value(css_vars, f"--{token.var_name}") or "<missing>",
                )
            )
            continue
        _css_name, expected = mapped
        actual = (
            str(int(token.default_value))
            if token.default_value.is_integer()
            else str(token.default_value)
        )
        # float compare tolerance for rem
        try:
            if abs(float(expected) - float(actual)) < 1e-6:
                continue
        except ValueError:
            pass
        if expected != actual:
            drifts.append(
                Drift(
                    "playground→tokens.css",
                    token.var_name,
                    expected,
                    actual,
                )
            )
    return drifts


def run_check() -> list[Drift]:
    css_text = _TOKENS_CSS.read_text(encoding="utf-8")
    design_text = _DESIGN_MD.read_text(encoding="utf-8")
    playground_text = _PLAYGROUND_TOKENS.read_text(encoding="utf-8")

    css_vars = parse_tokens_css_root(css_text)
    design_tokens = parse_design_md_tokens(design_text)
    playground_tokens = parse_playground_tokens(playground_text)

    drifts: list[Drift] = []
    drifts.extend(diff_design_vs_css(design_tokens, css_vars))
    drifts.extend(diff_playground_vs_css(playground_tokens, css_vars))
    return drifts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Design token SSOT sync check")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when design.md or playground defaults drift from tokens.css",
    )
    args = parser.parse_args(argv)

    if not args.check:
        parser.print_help()
        return 0

    drifts = run_check()
    if not drifts:
        print("✅ design token SSOT aligned (design.md + playground ↔ tokens.css)")
        return 0

    print(f"❌ design token SSOT drift: {len(drifts)} issue(s)")
    for item in drifts:
        print(f"  [{item.source}] {item.token}: expected={item.expected!r} actual={item.actual!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
