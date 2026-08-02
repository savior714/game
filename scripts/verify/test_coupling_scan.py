#!/usr/bin/env python3
"""테스트 결합 신호 스캐너 — fixture 공유, import 의존, 통합 누출 분석.

SPEC_dependency_boundary_guardrails.md §3.3 정의에 따라
테스트 파일 간 결합도 신호를 수집한다.

Usage:
  python3 scripts/verify/test_coupling_scan.py          # report only
  python3 scripts/verify/test_coupling_scan.py --check   # exit 1 on high-risk signals
  python3 scripts/verify/test_coupling_scan.py --json    # JSON output to stdout
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = ROOT / "scripts" / "verify" / "test_coupling_baseline.txt"

# ---------------------------------------------------------------------------
# Test directory patterns
# ---------------------------------------------------------------------------

_TEST_DIRS = [
    ROOT / "tests",
    ROOT / "apps" / "renderer" / "src",  # __tests__ dirs within renderer
]

# Fixture names that indicate cross-cutting concern leakage
_INTEGRATION_FIXTURES = re.compile(
    r"^(db_session|async_session|postgresql|redis_client|mock_|fake_|factory_|"
    r"test_client|app_client|container_|di_container)",
    re.IGNORECASE,
)

# Common fixture patterns to track
_FIXTURE_DECORATOR = re.compile(
    r"@pytest\.fixture\s*\(?(\s*\(.*?\))?\s*\)?",
    re.DOTALL,
)

_FIXTURE_NAME = re.compile(r"def\s+(\w+)\s*\(")

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CouplingSignal:
    file: str
    line: int
    type: str
    source: str
    target: str
    risk: str
    impact: str
    matrix_score: int
    description: str


@dataclass
class ScanResult:
    scan_type: str = "test"
    timestamp: str = ""
    signals: list[CouplingSignal] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, Any]:
        by_risk: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        by_type: dict[str, int] = {
            "T1-shared-fixture": 0,
            "T2-test-import-chain": 0,
            "T3-integration-leak": 0,
        }
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
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RISK_WEIGHT: dict[str, int] = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
_IMPACT_WEIGHT: dict[str, int] = {"P0-전사": 4, "P1-컨텍스트": 3, "P2-모듈": 2, "P3-파일": 1}


def _matrix_score(risk: str, impact: str) -> int:
    return _RISK_WEIGHT.get(risk, 1) * _IMPACT_WEIGHT.get(impact, 1)


def signal_fingerprint(signal: CouplingSignal) -> str:
    return f"{signal.risk}|{signal.type}|{signal.file}|{signal.source}|{signal.target}"


def collect_gate_signals(result: ScanResult) -> set[str]:
    """Critical·High 신호만 CI gate 대상."""
    return {
        signal_fingerprint(s)
        for s in result.signals
        if s.risk in {"Critical", "High"}
    }


def _rel_path(file_path: Path) -> str:
    try:
        return str(file_path.relative_to(ROOT))
    except ValueError:
        return str(file_path)


# ---------------------------------------------------------------------------
# Fixture analysis
# ---------------------------------------------------------------------------


def _extract_fixtures(file_path: Path) -> dict[str, int]:
    """파일 내 fixture 정의(name → line)를 추출."""
    try:
        source = file_path.read_text(encoding="utf-8")
    except OSError:
        return {}

    fixtures: dict[str, int] = {}
    for match in _FIXTURE_DECORATOR.finditer(source):
        # Find the next def after the decorator
        start = match.end()
        def_match = _FIXTURE_NAME.search(source, start)
        if def_match:
            fixtures[def_match.group(1)] = def_match.start()

    return fixtures


def _extract_fixture_uses(file_path: Path) -> set[str]:
    """파일 내 fixture 사용 참조를 추출."""
    try:
        source = file_path.read_text(encoding="utf-8")
    except OSError:
        return set()

    uses: set[str] = set()
    # pytest.mark.usefixtures("fixture_name") — 모든 괄호/대괄호 형태 지원
    for m in re.finditer(r'usefixtures\([^)]*?"([^"]+)"', source):
        uses.add(m.group(1))
    # pytest.mark.usefixtures("a", "b") — 복수 fixture
    for m in re.finditer(r'usefixtures\(([^)]+)\)', source):
        for name in re.findall(r'"([^"]+)"', m.group(1)):
            uses.add(name)
    # Function parameter names (implicit fixture injection)
    tree = _safe_parse(source)
    if tree:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in node.args.args + node.args.kwonlyargs:
                    uses.add(arg.arg)

    return uses


def _safe_parse(source: str) -> ast.Module | None:
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _detect_shared_fixtures(
    test_files: list[Path],
    result: ScanResult,
) -> None:
    """T1-shared-fixture: 단일 fixture를 N개 이상 테스트가 참조하는 경우."""
    fixture_users: dict[str, list[str]] = defaultdict(list)

    for f in test_files:
        uses = _extract_fixture_uses(f)
        rel = _rel_path(f)
        for fixture_name in uses:
            fixture_users[fixture_name].append(rel)

    # 3개 이상 테스트가 참조하는 fixture는 결합 신호
    for fixture_name, users in fixture_users.items():
        if len(users) >= 3:
            # fixture가 통합 관련 패턴을 포함하면 위험도 상승
            risk = "High" if _INTEGRATION_FIXTURES.search(fixture_name) else "Medium"
            impact = "P1-컨텍스트" if len(users) >= 10 else "P2-모듈"
            result.signals.append(
                CouplingSignal(
                    file=users[0],
                    line=0,
                    type="T1-shared-fixture",
                    source=fixture_name,
                    target=f"{len(users)} tests",
                    risk=risk,
                    impact=impact,
                    matrix_score=_matrix_score(risk, impact),
                    description=f"fixture '{fixture_name}'이 {len(users)}개 테스트에서 공유 참조",
                )
            )


# ---------------------------------------------------------------------------
# Test import chain analysis
# ---------------------------------------------------------------------------


def _extract_test_imports(file_path: Path) -> dict[str, str]:
    """테스트 파일의 import 의존성(다른 테스트 파일/모듈)을 추출."""
    try:
        source = file_path.read_text(encoding="utf-8")
    except OSError:
        return {}

    imports: dict[str, str] = {}
    tree = _safe_parse(source)
    if not tree:
        return {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports[alias.name] = module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.name] = alias.name

    return imports


def _detect_test_import_chains(
    test_files: list[Path],
    result: ScanResult,
) -> None:
    """T2-test-import-chain: 테스트 파일 간 import 의존 체인 감지."""
    # 테스트 파일 간 import 매핑 구축 (file → set of imported modules)
    test_import_map: dict[str, set[str]] = defaultdict(set)
    # 파일명(확장자 제거) → 상대 경로 매핑
    name_to_rel: dict[str, str] = {}

    for f in test_files:
        rel = _rel_path(f)
        name_to_rel[f.stem] = rel
        imports = _extract_test_imports(f)
        for name, module in imports.items():
            # 다른 테스트 파일이나 테스트 헬퍼를 import하는 경우
            if "test" in module.lower() or "conftest" in module.lower() or "test" in name.lower():
                test_import_map[rel].add(module)

    # 모듈명 → 파일 경로 역매핑 (순환 감지용)
    module_to_rel: dict[str, str] = {}
    for f in test_files:
        rel = _rel_path(f)
        # 모듈명 여러 형태 매핑 (tests.unit.test_b, unit.test_b, test_b 등)
        parts = rel.replace("/", ".").replace(".py", "").split(".")
        for i in range(len(parts)):
            mod = ".".join(parts[i:])
            if mod:
                module_to_rel[mod] = rel

    # 의존 체인 감지 (상호 import 확인)
    checked: set[tuple[str, str]] = set()
    for test_file, deps in test_import_map.items():
        for dep_module in deps:
            # 모듈명을 파일 경로로 변환
            dep_file = module_to_rel.get(dep_module, "")
            if not dep_file or dep_file == test_file:
                continue
            pair = (test_file, dep_file) if test_file <= dep_file else (dep_file, test_file)
            if pair in checked:
                continue
            checked.add(pair)
            # 역방향 의존성 확인: dep_file이 test_file을 import하는지
            dep_deps = test_import_map.get(dep_file, set())
            # test_file의 모듈명 형태를 찾아서 포함 여부 확인
            test_stem = Path(test_file).stem
            test_mod_candidates = [
                test_stem,
                f"test_{test_stem}",
            ]
            is_circular = any(
                tc in dep_deps or module_to_rel.get(tc) == test_file
                for tc in test_mod_candidates
            )
            if is_circular:
                result.signals.append(
                    CouplingSignal(
                        file=test_file,
                        line=0,
                        type="T2-test-import-chain",
                        source=test_file,
                        target=dep_file,
                        risk="Medium",
                        impact="P2-모듈",
                        matrix_score=_matrix_score("Medium", "P2-모듈"),
                        description="테스트 파일 간 상호 import 의존 감지",
                    )
                )


# ---------------------------------------------------------------------------
# Integration leak detection
# ---------------------------------------------------------------------------


def _detect_integration_leaks(
    test_files: list[Path],
    result: ScanResult,
) -> None:
    """T3-integration-leak: 단위 테스트가 인프라/DB fixture를 사용하는 경우."""
    for f in test_files:
        rel = _rel_path(f)
        uses = _extract_fixture_uses(f)

        for fixture_name in uses:
            if _INTEGRATION_FIXTURES.search(fixture_name):
                # conftest.py 내 fixture 정의가 아닌, 테스트 파일 내 직접 사용만 보고
                if "conftest" not in rel:
                    result.signals.append(
                        CouplingSignal(
                            file=rel,
                            line=0,
                            type="T3-integration-leak",
                            source=rel,
                            target=fixture_name,
                            risk="Low",
                            impact="P3-파일",
                            matrix_score=_matrix_score("Low", "P3-파일"),
                            description=f"단위 테스트가 통합 fixture '{fixture_name}' 사용",
                        )
                    )


# ---------------------------------------------------------------------------
# Directory scanner
# ---------------------------------------------------------------------------


def _collect_test_files(paths: list[Path]) -> list[Path]:
    """테스트 파일 경로 수집."""
    files: list[Path] = []
    for base in paths:
        if not base.exists():
            continue
        for f in sorted(base.rglob("*.py")):
            if f.name.startswith("test_") or f.name.endswith("_test.py"):
                files.append(f)
            elif "__tests__" in str(f.parent):
                files.append(f)
    return files


def scan_directories(paths: list[Path] | None = None, result: ScanResult | None = None) -> ScanResult:
    """테스트 결합 신호를 수집하는 메인 엔트리."""
    if result is None:
        result = ScanResult(
            scan_type="test",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    if paths is None:
        paths = _TEST_DIRS

    test_files = _collect_test_files(paths)

    if not test_files:
        return result

    _detect_shared_fixtures(test_files, result)
    _detect_test_import_chains(test_files, result)
    _detect_integration_leaks(test_files, result)

    # 정렬: matrix_score 내림차순 → file
    result.signals.sort(key=lambda s: (-s.matrix_score, s.file, s.line))

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="테스트 결합 신호 스캐너",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Medium 이상 신호가 있으면 exit code 1 반환",
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
        "--update-baseline",
        action="store_true",
        help="Critical·High 신호 baseline 갱신",
    )
    parser.add_argument(
        "--target",
        nargs="+",
        default=None,
        help="스캔 대상 디렉토리 (기본: tests/, apps/renderer/src)",
    )
    args = parser.parse_args()

    paths = [Path(p) for p in args.target] if args.target else None
    result = scan_directories(paths)

    if args.update_baseline:
        sys.path.insert(0, str(ROOT / "scripts" / "verify"))
        from baseline_gate import write_baseline

        gate_signals = collect_gate_signals(result)
        write_baseline(BASELINE_PATH, gate_signals)
        print(f"[test] Baseline updated: {len(gate_signals)} Critical/High entries")
        return 0

    output_data = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    if args.as_json or args.output:
        if args.output:
            out_path = Path(args.output)
            out_path.write_text(output_data, encoding="utf-8")
            print(f"[test] JSON output → {out_path}")
        else:
            print(output_data)

    summary = result.summary
    print(
        f"[test] Total signals: {summary['total_signals']} "
        f"(Critical={summary['by_risk']['Critical']}, "
        f"High={summary['by_risk']['High']}, "
        f"Medium={summary['by_risk']['Medium']}, "
        f"Low={summary['by_risk']['Low']})"
    )
    print(
        f"[test] By type: "
        f"T1={summary['by_type']['T1-shared-fixture']}, "
        f"T2={summary['by_type']['T2-test-import-chain']}, "
        f"T3={summary['by_type']['T3-integration-leak']}"
    )

    if args.check:
        sys.path.insert(0, str(ROOT / "scripts" / "verify"))
        from baseline_gate import filter_new_entries, load_baseline

        gate_signals = collect_gate_signals(result)
        loaded = load_baseline(BASELINE_PATH)
        new_entries = filter_new_entries(gate_signals, loaded)
        print(
            f"[test] Gate (Critical+High): current={len(gate_signals)}, "
            f"baseline={len(loaded)}, new={len(new_entries)}"
        )
        if new_entries:
            print("[test] FAIL — new Critical/High test coupling signals:")
            for entry in new_entries[:20]:
                print(f"  - {entry}")
            if len(new_entries) > 20:
                print(f"  ... and {len(new_entries) - 20} more")
            return 1
        print("[test] PASS — no new Critical/High test coupling signals")
        return 0

    medium_plus = (
        summary["by_risk"].get("Critical", 0)
        + summary["by_risk"].get("High", 0)
        + summary["by_risk"].get("Medium", 0)
    )
    if medium_plus > 0:
        print(f"[test] INFO — {medium_plus} medium+ signals (report-only mode)")

    print("[test] PASS — report complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
