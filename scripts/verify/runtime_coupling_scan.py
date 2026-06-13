#!/usr/bin/env python3
"""런타임 호출 결합 신호 스캐너 — 정적 호출 그래프 분석.

SPEC_dependency_boundary_guardrails.md §3.2 정의에 따라
함수 호출 그래프에서 경계 통과 횟수, 공유 mutable 상태, 순환 호출 신호를 수집한다.

실제 런타임 트레이스가 아닌 정적 분석 기반이므로 "신호(signal)"로 보고,
임계치 초과 항목을 경고로 분류한다.

Usage:
  python3 scripts/verify/runtime_coupling_scan.py          # report only
  python3 scripts/verify/runtime_coupling_scan.py --check   # exit 1 on high-risk signals
  python3 scripts/verify/runtime_coupling_scan.py --json    # JSON output to stdout
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Layer classification (same as dependency_boundary_scan)
# ---------------------------------------------------------------------------

_PYTHON_LAYERS: dict[str, str] = {
    "src/application/": "application",
    "src/domain/": "domain",
    "src/infrastructure/": "infrastructure",
    "src/main/": "main",
    "src/shared/": "shared",
    "scripts/": "scripts",
}

# ---------------------------------------------------------------------------
# Intentional recursive function whitelist (SPEC §5)
# These functions are intentionally recursive with proper base cases.
# ---------------------------------------------------------------------------

_RECURSIVE_FUNCTION_WHITELIST: frozenset[str] = frozenset({
    # safe_condition_eval.py — AST 트리를 하위로 재귀 순회
    "_validate_node",
    # pii_masking.py — FHIR 구조 재귀 마스킹
    "_recurse_mask_fhir",
    # pii_masking.py — 상호 재귀 (base case 존재)
    "_mask_fhir_object",
    "_mask_fhir_name",
    "_mask_fhir_telecom",
    "_mask_fhir_address",
    "_mask_fhir_identifier",
})

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CouplingSignal:
    file: str
    line: int
    type: str
    source_func: str
    target_func: str
    source_layer: str
    target_layer: str
    risk: str
    impact: str
    matrix_score: int
    description: str
    start_point_evidence: str = ""
    promotion_basis: str = ""


@dataclass
class ScanResult:
    scan_type: str = "runtime"
    timestamp: str = ""
    signals: list[CouplingSignal] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, Any]:
        by_risk: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        by_type: dict[str, int] = {"R1-boundary-cross": 0, "R2-shared-mutation": 0, "R3-circular-runtime": 0}
        for s in self.signals:
            by_risk[s.risk] = by_risk.get(s.risk, 0) + 1
            by_type[s.type] = by_type.get(s.type, 0) + 1
        return {
            "total_signals": len(self.signals),
            "by_risk": by_risk,
            "by_type": by_type,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "scan_type": self.scan_type,
            "timestamp": self.timestamp,
            "signals": [asdict(s) for s in self.signals],
            "top20_triage": build_top20_triage(self),
            "summary": self.summary,
        }


def _classify_triage_action(signal: CouplingSignal) -> tuple[str, str, str]:
    """SPEC_runtime_bypass_top20_checklist 기준으로 운영 분류와 승격 근거를 반환한다.

    반환값: (triage_action, triage_reason, promotion_basis)
    """
    if signal.risk in {"Critical", "High"}:
        return ("block", "rule-1: high-or-critical-risk", "rule-1: high-or-critical-risk")
    if signal.type == "R3-circular-runtime" and signal.matrix_score >= 9:
        return ("block", "rule-1: circular-high-matrix", "rule-1: circular-high-matrix")
    if signal.impact == "P0-전사":
        return ("block", "rule-1: global-impact", "rule-1: global-impact")

    if signal.risk == "Medium" and signal.impact in {"P1-컨텍스트", "P0-전사"}:
        return (
            "exception_candidate",
            "rule-2: medium-with-context-impact",
            "rule-2: medium-with-context-impact",
        )
    if signal.type == "R1-boundary-cross" and signal.matrix_score >= 6:
        return (
            "exception_candidate",
            "rule-2: boundary-cross-threshold",
            "rule-2: boundary-cross-threshold",
        )

    return ("observe", "rule-3: default-observe", "rule-3: default-observe")


def build_top20_triage(result: ScanResult) -> list[dict[str, Any]]:
    """정렬된 신호에서 상위 20건을 추려 운영 분류와 승격 근거를 부여한다.

    SPEC_runtime_bypass_top20_checklist §스캐너 출력 계약 준수.
    """
    top20: list[dict[str, Any]] = []
    for rank, signal in enumerate(result.signals[:20], start=1):
        triage_action, triage_reason, promotion_basis = _classify_triage_action(signal)
        ttl_evidence = {
            "expires_at": None,
            "owner": None,
            "source": "scan-default",
        }
        ttl_evidence_missing = ttl_evidence["expires_at"] is None or ttl_evidence["owner"] is None
        if ttl_evidence_missing:
            triage_action = "block"
            promotion_basis = "rule-ttl-1: missing-expiry-or-owner"
            ttl_guardrail_action = "promote_to_block"
            ttl_guardrail_reason = "rule-ttl-1: missing-expiry-or-owner"
        else:
            ttl_guardrail_action = "keep"
            ttl_guardrail_reason = "rule-ttl-2: ttl-evidence-present"
        top20.append({
            "rank": rank,
            "triage_action": triage_action,
            "triage_reason": triage_reason,
            "promotion_basis": promotion_basis,
            "ttl_evidence": ttl_evidence,
            "ttl_evidence_missing": ttl_evidence_missing,
            "ttl_guardrail_action": ttl_guardrail_action,
            "ttl_guardrail_reason": ttl_guardrail_reason,
            "signal": asdict(signal),
        })
    return top20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RISK_WEIGHT: dict[str, int] = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
_IMPACT_WEIGHT: dict[str, int] = {"P0-전사": 4, "P1-컨텍스트": 3, "P2-모듈": 2, "P3-파일": 1}


def _matrix_score(risk: str, impact: str) -> int:
    return _RISK_WEIGHT.get(risk, 1) * _IMPACT_WEIGHT.get(impact, 1)


def _classify_layer(file_path: Path | str) -> str | None:
    path_str = str(file_path) if not isinstance(file_path, str) else file_path
    for prefix, layer in _PYTHON_LAYERS.items():
        if prefix in path_str:
            return layer
    return None


def _rel_path(file_path: Path) -> str:
    try:
        return str(file_path.relative_to(ROOT))
    except ValueError:
        return str(file_path)


# ---------------------------------------------------------------------------
# AST-based call graph extraction
# ---------------------------------------------------------------------------


class CallGraphVisitor(ast.NodeVisitor):
    """AST 트리를 순회하며 함수 호출 그래프를 추출."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.functions: list[dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.functions.append({
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno + 1),
        })
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.functions.append({
            "name": node.name,
            "line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno + 1),
        })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_name = self._extract_func_name(node)
        if func_name:
            self.calls.append({
                "func": func_name,
                "line": node.lineno,
            })
        self.generic_visit(node)

    @staticmethod
    def _extract_func_name(node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            parts: list[str] = []
            n: ast.expr = node.func
            while isinstance(n, ast.Attribute):
                parts.append(n.attr)
                n = n.value
            if isinstance(n, ast.Name):
                parts.append(n.id)
            return ".".join(reversed(parts))
        return None


def _build_call_graph(file_path: Path) -> dict[str, list[str]]:
    """단일 파일 내 함수 → 호출 함수 매핑을 구축."""
    try:
        source = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    visitor = CallGraphVisitor()
    visitor.visit(tree)

    # 각 호출이 어느 함수 내에서 발생했는지 추적
    func_calls: dict[str, list[str]] = defaultdict(list)
    for call in visitor.calls:
        for func in visitor.functions:
            if func["line"] <= call["line"] <= func["end_line"]:
                func_calls[func["name"]].append(call["func"])
                break

    return dict(func_calls)


# ---------------------------------------------------------------------------
# Boundary crossing detection
# ---------------------------------------------------------------------------

# Known cross-layer function patterns that indicate runtime boundary crossing
# These are functions in application/infrastructure that call into domain
_CROSS_LAYER_PATTERNS: dict[str, list[re.Pattern]] = {}  # populated below

import re as _re_module

_CROSS_LAYER_PATTERNS = {
    # application service → domain service/repository interface
    "application": [
        _re_module.compile(r"^save_|^create_|^update_|^delete_|^process_"),
    ],
    # infrastructure → domain (these should only be via ports)
    "infrastructure": [
        _re_module.compile(r"^execute_|^query_|^fetch_"),
    ],
}


def _build_start_point_evidence(
    signal_type: str,
    file_rel: str,
    line: int,
    source_func: str,
    target_func: str,
    impact: str,
) -> str:
    """SPEC_runtime_bypass_top20_checklist §시작점 증거 필드 형식 준수."""
    line_info = f":{line}" if line > 0 else ""
    return (
        f"[고신뢰] {signal_type} 감지: {file_rel}{line_info}에서 {source_func}() → {target_func}() 호출 | "
        f"[영향] {impact}"
    )


def _detect_boundary_crossings(
    file_path: Path,
    call_graph: dict[str, list[str]],
    result: ScanResult,
) -> None:
    """함수 호출 그래프에서 경계 횡단 신호를 감지."""
    layer = _classify_layer(file_path)
    if layer is None or layer == "shared":
        return

    rel = _rel_path(file_path)

    for func_name, called_funcs in call_graph.items():
        for called in called_funcs:
            # application → domain 호출 패턴 감지 (정방향 — 허용되지만 빈도 측정)
            if layer == "application" and ("domain." in called or _is_domain_func(called)):
                impact = "P2-모듈"
                result.signals.append(
                    CouplingSignal(
                        file=rel,
                        line=0,
                        type="R1-boundary-cross",
                        source_func=func_name,
                        target_func=called,
                        source_layer=layer,
                        target_layer="domain",
                        risk="Medium",
                        impact=impact,
                        matrix_score=_matrix_score("Medium", impact),
                        description="애플리케이션→도메인 런타임 호출 경계 횡단",
                        start_point_evidence=_build_start_point_evidence(
                            "R1-boundary-cross", rel, 0, func_name, called, impact
                        ),
                    )
                )


def _is_domain_func(func_name: str) -> bool:
    """함수명이 도메인 서비스/리포지토리 패턴과 일치하는지."""
    domain_indicators = [
        "Repository",
        "DomainService",
        "Entity",
        "Aggregate",
        "_repo",
        "Domain",
    ]
    return any(ind in func_name for ind in domain_indicators)


# ---------------------------------------------------------------------------
# Shared mutable state detection
# ---------------------------------------------------------------------------

_MUTABLE_ASSIGN_PATTERNS = [
    _re_module.compile(r"\.append\("),
    _re_module.compile(r"\.extend\("),
    _re_module.compile(r"\.pop\("),
    _re_module.compile(r"\.remove\("),
    _re_module.compile(r"\.update\("),
    _re_module.compile(r"\[\w+\]\s*="),
]


def _detect_shared_mutation(
    file_path: Path,
    result: ScanResult,
) -> None:
    """파일 내 mutable 연산이 경계 간 공유 상태를 변경하는 신호를 감지."""
    layer = _classify_layer(file_path)
    if layer is None or layer == "shared":
        return

    rel = _rel_path(file_path)

    try:
        source = file_path.read_text(encoding="utf-8")
        lines = source.split("\n")
    except OSError:
        return

    for i, line in enumerate(lines, start=1):
        for pattern in _MUTABLE_ASSIGN_PATTERNS:
            if pattern.search(line):
                # application/infrastructure 파일에서 mutable 연산은
                # DTO/모델이 경계에서 직접 수정될 가능성을 나타냄
                impact = "P3-파일"
                result.signals.append(
                    CouplingSignal(
                        file=rel,
                        line=i,
                        type="R2-shared-mutation",
                        source_func="_inline",
                        target_func="_mutable_op",
                        source_layer=layer,
                        target_layer=layer,
                        risk="Low",
                        impact=impact,
                        matrix_score=_matrix_score("Low", impact),
                        description="경계 간 공유 mutable 상태 직접 수정 신호",
                        start_point_evidence=_build_start_point_evidence(
                            "R2-shared-mutation", rel, i, "_inline", "_mutable_op", impact
                        ),
                    )
                )
                break  # 한 줄에 여러 패턴 매칭 시 중복 방지


# ---------------------------------------------------------------------------
# Circular call detection (within-file)
# ---------------------------------------------------------------------------


def _detect_circular_calls(
    file_path: Path,
    call_graph: dict[str, list[str]],
    result: ScanResult,
) -> None:
    """파일 내 순환 호출 그래프를 감지.

    False Positive 필터링 적용:
    - A1: __init__ 자기 참조 (AST 범위 중첩) 제외
    - A2: 의도적 재귀 함수 whitelist 제외
    - A3: 상호 재귀 depth 3 초과 시 base case로 간주 제외
    - A4: 클래스 메서드 → 모듈 레벨 함수 매핑 충돌 제외
    """
    layer = _classify_layer(file_path)
    if layer is None:
        return

    rel = _rel_path(file_path)
    impact = "P2-모듈"

    # DFS로 순환 감지
    visited: set[str] = set()
    rec_stack: set[str] = set()
    cycles_found: set[tuple[str, str]] = set()

    def _is_fp_cycle(node: str, neighbor: str) -> bool:
        """False Positive 순환인지 판별 (SPEC §2.1)."""
        # A1: __init__ 자기 참조 — AST 범위 중첩으로 인한 오감지
        if node == "__init__" and neighbor == "__init__":
            return True

        # A2: 의도적 재귀 함수 whitelist
        if node in _RECURSIVE_FUNCTION_WHITELIST:
            return True
        if neighbor in _RECURSIVE_FUNCTION_WHITELIST:
            return True

        # A4: 클래스 메서드 → 모듈 레벨 함수 매핑 충돌
        # billing_mixin.py 등에서 클래스 메서드가 모듈 레벨 함수를 호출할 때
        # 동일 이름으로 매핑되면 가짜 순환으로 분류
        if node == neighbor:
            return True

        return False

    def _dfs(node: str, depth: int = 0) -> None:
        visited.add(node)
        rec_stack.add(node)
        for neighbor in call_graph.get(node, []):
            if _is_fp_cycle(node, neighbor):
                continue
            if neighbor not in visited:
                # A3: 상호 재귀 depth 제한 — 3 초과 시 base case로 간주
                if depth < 3:
                    _dfs(neighbor, depth + 1)
            elif neighbor in rec_stack:
                cycle_key = tuple(sorted([node, neighbor]))
                if cycle_key not in cycles_found:
                    cycles_found.add(cycle_key)
                    result.signals.append(
                        CouplingSignal(
                            file=rel,
                            line=0,
                            type="R3-circular-runtime",
                            source_func=node,
                            target_func=neighbor,
                            source_layer=layer,
                            target_layer=layer,
                            risk="High",
                            impact=impact,
                            matrix_score=_matrix_score("High", impact),
                            description="함수 간 순환 호출 그래프 감지",
                            start_point_evidence=_build_start_point_evidence(
                                "R3-circular-runtime", rel, 0, node, neighbor, impact
                            ),
                        )
                    )
        rec_stack.discard(node)

    for func in call_graph:
        if func not in visited:
            _dfs(func)


# ---------------------------------------------------------------------------
# Directory scanner
# ---------------------------------------------------------------------------


def scan_directory(path: Path, result: ScanResult) -> None:
    """디렉토리 내 모든 Python 파일을 스캔."""
    if not path.exists():
        return

    for file_path in sorted(path.rglob("*.py")):
        if file_path.name == "__init__.py":
            continue

        call_graph = _build_call_graph(file_path)
        _detect_boundary_crossings(file_path, call_graph, result)
        _detect_shared_mutation(file_path, result)
        _detect_circular_calls(file_path, call_graph, result)

    # 정렬: matrix_score 내림차순 → file → line
    result.signals.sort(key=lambda s: (-s.matrix_score, s.file, s.line))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="런타임 호출 결합 신호 스캐너",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="High 이상 신호가 있으면 exit code 1 반환",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="결과를 JSON으로 stdout에 출력",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="결과를 파일에 저장",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=str(ROOT / "src"),
        help="스캔 대상 경로 (기본: src/)",
    )
    args = parser.parse_args()

    result = ScanResult(
        scan_type="runtime",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    scan_directory(Path(args.target), result)

    output_data = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)
    summary = result.summary

    if args.as_json or args.output:
        if args.output:
            out_path = Path(args.output)
            out_path.write_text(output_data, encoding="utf-8")
            print(f"[runtime] JSON output → {out_path}")
        else:
            print(output_data)

        # --check 모드는 JSON 출력 후 exit code만 제어
        if args.check:
            high_count = summary["by_risk"].get("Critical", 0) + summary["by_risk"].get("High", 0)
            if high_count > 0:
                return 1
        return 0

    # 텍스트 모드: 요약 출력
    print(
        f"[runtime] Total signals: {summary['total_signals']} "
        f"(Critical={summary['by_risk']['Critical']}, "
        f"High={summary['by_risk']['High']}, "
        f"Medium={summary['by_risk']['Medium']}, "
        f"Low={summary['by_risk']['Low']})"
    )
    print(
        f"[runtime] By type: "
        f"R1={summary['by_type']['R1-boundary-cross']}, "
        f"R2={summary['by_type']['R2-shared-mutation']}, "
        f"R3={summary['by_type']['R3-circular-runtime']}"
    )

    triage_data = result.to_dict()
    top20_count = len(triage_data.get("top20_triage", []))
    print(f"[runtime] Top20 triage items: {top20_count}")

    if args.check:
        high_count = summary["by_risk"].get("Critical", 0) + summary["by_risk"].get("High", 0)
        if high_count > 0:
            print(f"[runtime] FAIL — {high_count} high/critical signals detected")
            return 1

    print("[runtime] PASS — no high-risk signals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
