#!/usr/bin/env python3
"""Service layer gate — infra/services, application/services, ports_non_shim counts.

Usage:
  python3 scripts/verify/service_layer_gate.py --check
  python3 scripts/verify/service_layer_gate.py --update-baseline
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_VERIFY = Path(__file__).resolve().parent
if str(_SCRIPTS_VERIFY) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_VERIFY))

from baseline_gate import load_baseline, write_baseline

BASELINE_PATH = ROOT / "scripts" / "verify" / "service_layer_baseline.txt"
INFRA_SERVICES_DIR = ROOT / "src" / "infrastructure" / "services"
APPLICATION_SERVICES_DIR = ROOT / "src" / "application" / "services"
APPLICATION_PORTS_DIR = ROOT / "src" / "application" / "ports"

METRIC_KEYS = ("infra_services", "application_services", "ports_non_shim")


def _is_domain_ports_import(node: ast.ImportFrom) -> bool:
    module = node.module or ""
    return module == "src.domain.ports" or module.startswith("src.domain.ports.")


def _is_all_assign(node: ast.Assign) -> bool:
    if len(node.targets) != 1:
        return False
    target = node.targets[0]
    if not isinstance(target, ast.Name) or target.id != "__all__":
        return False
    if not isinstance(node.value, ast.List):
        return False
    return all(
        isinstance(elt, ast.Constant) and isinstance(elt.value, str) for elt in node.value.elts
    )


def is_port_shim(path: Path) -> bool:
    """True when the file only re-exports from src.domain.ports (+ docstring, __all__)."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError):
        return False

    has_domain_import = False
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                continue
            return False
        if isinstance(node, ast.ImportFrom):
            if not _is_domain_ports_import(node):
                return False
            has_domain_import = True
            continue
        if isinstance(node, ast.Assign) and _is_all_assign(node):
            continue
        return False

    return has_domain_import


def count_infra_services() -> int:
    if not INFRA_SERVICES_DIR.is_dir():
        return 0
    return sum(
        1
        for path in INFRA_SERVICES_DIR.glob("*.py")
        if path.name != "__init__.py"
    )


def count_application_services() -> int:
    if not APPLICATION_SERVICES_DIR.is_dir():
        return 0
    return sum(1 for _ in APPLICATION_SERVICES_DIR.rglob("*.py"))


def count_ports_non_shim() -> int:
    if not APPLICATION_PORTS_DIR.is_dir():
        return 0
    return sum(
        1
        for path in APPLICATION_PORTS_DIR.glob("*.py")
        if path.name != "__init__.py" and not is_port_shim(path)
    )


def collect_metrics() -> dict[str, int]:
    return {
        "infra_services": count_infra_services(),
        "application_services": count_application_services(),
        "ports_non_shim": count_ports_non_shim(),
    }


def metrics_fingerprint(metrics: dict[str, int]) -> set[str]:
    return {f"{key}={metrics[key]}" for key in METRIC_KEYS}


def parse_metric_baseline(loaded: set[str]) -> dict[str, int]:
    metrics: dict[str, int] = {}
    for line in loaded:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in METRIC_KEYS:
            metrics[key] = int(value.strip())
    return metrics


def metrics_exceeding_baseline(
    current: dict[str, int], baseline: dict[str, int]
) -> list[tuple[str, int, int]]:
    exceeded: list[tuple[str, int, int]] = []
    for key in METRIC_KEYS:
        cur = current.get(key, 0)
        base = baseline.get(key, 0)
        if cur > base:
            exceeded.append((key, cur, base))
    return exceeded


def main() -> int:
    parser = argparse.ArgumentParser(description="Service layer count gate")
    parser.add_argument("--check", action="store_true", help="Fail when any metric exceeds baseline")
    parser.add_argument("--update-baseline", action="store_true", help="Rewrite baseline snapshot")
    args = parser.parse_args()

    current_metrics = collect_metrics()
    current_fp = metrics_fingerprint(current_metrics)
    loaded = load_baseline(BASELINE_PATH)
    baseline_metrics = parse_metric_baseline(loaded)

    if args.update_baseline:
        write_baseline(BASELINE_PATH, current_fp)
        print(f"[service-layer] Baseline updated → {BASELINE_PATH}")
        for key in METRIC_KEYS:
            print(f"  {key}={current_metrics[key]}")
        return 0

    print("[service-layer] Metrics:")
    for key in METRIC_KEYS:
        base = baseline_metrics.get(key, 0)
        cur = current_metrics[key]
        delta = cur - base
        sign = "+" if delta > 0 else ""
        print(f"  {key}: current={cur}, baseline={base} ({sign}{delta})")

    exceeded = metrics_exceeding_baseline(current_metrics, baseline_metrics)

    if args.check and exceeded:
        print("[service-layer] FAIL — metrics exceed baseline:")
        for key, cur, base in exceeded:
            print(f"  - {key}: {cur} > {base}")
        return 1

    if args.check:
        print("[service-layer] PASS — no metric exceeds baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
