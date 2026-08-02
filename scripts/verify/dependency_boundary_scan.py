#!/usr/bin/env python3
"""정적 참조 경계 위반 스캐너 — Python/TypeScript import 분석.

SPEC_dependency_boundary_guardrails.md §3.1 정의에 따라
서비스(Application)↔도메인(Domain) 경계 위반을 정적 import 문으로 수집한다.

Usage:
  python3 scripts/verify/dependency_boundary_scan.py          # report only
  python3 scripts/verify/dependency_boundary_scan.py --check   # exit 1 on violations
  python3 scripts/verify/dependency_boundary_scan.py --json    # JSON output to stdout
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Layer classification
# ---------------------------------------------------------------------------

# Python layers — relative to ROOT/src/
_PYTHON_LAYERS: dict[str, str] = {
    "src/application/": "application",
    "src/domain/": "domain",
    "src/infrastructure/": "infrastructure",
    "src/main/": "main",
    "src/shared/": "shared",  # exempt
}

# TypeScript layers — relative to ROOT/apps/renderer/src/
_TS_LAYERS: dict[str, str] = {
    "app/": "app",
    "views/": "views",
    "features/": "features",
    "components/": "components",
    "hooks/": "hooks",
    "contexts/": "contexts",
    "stores/": "stores",
    "lib/api": "backend-api",
}

# ---------------------------------------------------------------------------
# Violation rules (SPEC §3.1)
# ---------------------------------------------------------------------------

# (source_layer, target_pattern, violation_type, risk, impact, description)
_PYTHON_RULES: list[tuple[str, re.Pattern[str], str, str, str, str]] = [
    # domain → infrastructure (S1-domain-leak) — Critical / P1-컨텍스트
    (
        "domain",
        re.compile(r"^src\.infrastructure\b"),
        "S1-domain-leak",
        "Critical",
        "P1-컨텍스트",
        "도메인 레이어에 인프라 구현체 유출",
    ),
    # domain → main (S2-domain-reverse) — High / P2-모듈
    (
        "domain",
        re.compile(r"^src\.main\b"),
        "S2-domain-reverse",
        "High",
        "P2-모듈",
        "도메인이 main 설정/어댑터 역참조",
    ),
    # application → main (S2-app-reverse) — High / P2-모듈
    (
        "application",
        re.compile(r"^src\.main\b"),
        "S2-app-reverse",
        "High",
        "P2-모듈",
        "애플리케이션이 main 설정/어댑터 역참조",
    ),
    # application → infrastructure (S1-app-infra-leak) — High / P1-컨텍스트
    (
        "application",
        re.compile(r"^src\.infrastructure\b"),
        "S1-app-infra-leak",
        "High",
        "P1-컨텍스트",
        "애플리케이션 계층에 인프라 구현체 유출",
    ),
    # infrastructure → application (S3-infra-reverse) — High / P2-모듈
    (
        "infrastructure",
        re.compile(r"^src\.application\b"),
        "S3-infra-reverse",
        "High",
        "P2-모듈",
        "인프라가 유스케이스 직접 호출",
    ),
    # cross-context: domain/X → domain/Y (different bounded contexts)
    # Detected as domain file importing another domain submodule outside shared kernel paths
    (
        "domain",
        re.compile(
            r"^src\.domain\.(?!ports|dtos|exceptions|models|rules|contracts|metadata|services|utils|shared"
            r"|billing|fhir|office|alert|medication|observation|auth|reference_data|security|policy)"
        ),
        "S4-cross-context",
        "Medium",
        "P1-컨텍스트",
        "도메인 내 컨텍스트 경계 무단 침범",
    ),
]

# Composition Root — DI wiring may reference application services (SPEC §6, ANALYSIS §7.1)
_COMPOSITION_ROOT_FILES: frozenset[str] = frozenset(
    {
        "src/infrastructure/containers.py",
        "src/infrastructure/containers_services.py",
        "src/infrastructure/containers_repositories.py",
    }
)

# TypeScript rules — import path patterns after @/src/
_TS_RULES: list[tuple[str, re.Pattern[str], str, str, str, str]] = [
    (
        "features",
        re.compile(r"^@/src/lib/api\b"),
        "S5-frontend-api",
        "Low",
        "P3-파일",
        "features가 API lib 직접 참조",
    ),
    (
        "features",
        re.compile(r"^@/src/app/"),
        "S6-features-to-app",
        "Medium",
        "P2-모듈",
        "features가 app 라우트/페이지 직접 import",
    ),
    (
        "components",
        re.compile(r"^@/src/features/"),
        "S7-components-to-features",
        "Medium",
        "P2-모듈",
        "공용 components가 domain features 직접 import",
    ),
    (
        "hooks",
        re.compile(r"^@/src/features/"),
        "S8-hooks-to-features",
        "Medium",
        "P2-모듈",
        "공용 hooks가 domain features 직접 import",
    ),
    (
        "hooks",
        re.compile(r"^@/src/app/"),
        "S9-hooks-to-app",
        "Medium",
        "P2-모듈",
        "hooks가 app 라우트 직접 import",
    ),
    (
        "features",
        re.compile(r"^@/src/components/consultation\b"),
        "S10-features-to-consultation-components",
        "Medium",
        "P2-모듈",
        "features가 consultation 전용 components 직접 import",
    ),
    (
        "features",
        re.compile(r"^@/src/components/dashboard\b"),
        "S11-features-to-dashboard-components",
        "Medium",
        "P2-모듈",
        "features가 dashboard 전용 components 직접 import",
    ),
    (
        "app",
        re.compile(r"^@/src/lib/api\b"),
        "S12-app-to-api",
        "Medium",
        "P2-모듈",
        "app 라우트가 API lib 직접 import",
    ),
]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Violation:
    file: str
    line: int
    type: str
    target: str
    risk: str
    impact: str
    matrix_score: int
    description: str


@dataclass
class ScanResult:
    scan_type: str = "static"
    timestamp: str = ""
    violations: list[Violation] = field(default_factory=list)
    enforcement_mode: str = "report"
    block_on_violation: bool = False
    exception_review: dict[str, int] = field(default_factory=dict)

    @property
    def summary(self) -> dict[str, Any]:
        by_risk: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        by_impact: dict[str, int] = {"P3-파일": 0, "P2-모듈": 0, "P1-컨텍스트": 0, "P0-전사": 0}
        for v in self.violations:
            by_risk[v.risk] = by_risk.get(v.risk, 0) + 1
            by_impact[v.impact] = by_impact.get(v.impact, 0) + 1
        return {
            "total_violations": len(self.violations),
            "by_risk": by_risk,
            "by_impact": by_impact,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "scan_type": self.scan_type,
            "timestamp": self.timestamp,
            "enforcement": {
                "mode": self.enforcement_mode,
                "block_on_violation": self.block_on_violation,
            },
            "exception_review": self.exception_review,
            "violations": [asdict(v) for v in self.violations],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RISK_WEIGHT: dict[str, int] = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
_IMPACT_WEIGHT: dict[str, int] = {"P0-전사": 4, "P1-컨텍스트": 3, "P2-모듈": 2, "P3-파일": 1}


def _matrix_score(risk: str, impact: str) -> int:
    return _RISK_WEIGHT.get(risk, 1) * _IMPACT_WEIGHT.get(impact, 1)


def _classify_python_layer(file_path: Path | str) -> str | None:
    """Path에서 Python 레이어를 분류 — 상대/절대 경로 모두 지원."""
    path_str = str(file_path) if not isinstance(file_path, str) else file_path
    for prefix, layer in _PYTHON_LAYERS.items():
        if prefix in path_str:
            return layer
    return None


def _classify_ts_layer(file_path: Path | str) -> str | None:
    """Path에서 TypeScript 레이어를 분류 — 상대/절대 경로 모두 지원."""
    path_str = str(file_path) if not isinstance(file_path, str) else file_path
    for prefix, layer in _TS_LAYERS.items():
        if prefix in path_str:
            return layer
    return None


def _is_composition_root(file_path: Path) -> bool:
    """Composition Root DI 모듈 — S3(infra→application) 허용."""
    return _rel_path(file_path) in _COMPOSITION_ROOT_FILES


def _is_exempt_python(file_path: Path) -> bool:
    """Python 허용 예외 (§8) 체크."""
    # shared/ 모듈은 모든 계층에서 참조 가능
    if "src/shared/" in str(file_path):
        return True
    # __init__.py 재export
    if file_path.name == "__init__.py":
        return True
    # domain exceptions — infrastructure에서 catch 용으로 참조 가능
    if "src/domain/exceptions.py" in str(file_path):
        return True
    # domain dtos — application에서 직렬화 용도로 참조 가능
    if "/domain/dtos/" in str(file_path):
        return True
    return False


def _is_exempt_ts(file_path: Path) -> bool:
    """TypeScript 허용 예외 체크."""
    if file_path.name in ("__init__.py", "index.ts", "index.tsx"):
        return True
    path_str = str(file_path)
    # features adapter/infrastructure seam — API lib 직접 참조 허용 (burndown §adapters)
    if "/features/" in path_str and ("/adapters/" in path_str or "/infrastructure/" in path_str):
        return True
    return False


# ---------------------------------------------------------------------------
# Scanners
# ---------------------------------------------------------------------------

_IMPORT_PY_RE = re.compile(
    r"""^\s*from\s+([\w.]+)\s+import\s+|^\s*import\s+([\w.]+)""",
    re.MULTILINE,
)

_IMPORT_TS_RE = re.compile(
    r"""(?:from|import)\s+['"](@/[^'"]+)['"]""",
    re.MULTILINE,
)


def _rel_path(file_path: Path) -> str:
    """ROOT 기준 상대 경로, 아니면 절대 경로."""
    try:
        return str(file_path.relative_to(ROOT))
    except ValueError:
        return str(file_path)


def _parse_iso8601(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _load_exception_review(path: Path | None) -> dict[str, int]:
    """긴급 예외 이력에서 사후 검토 현황을 집계."""
    empty = {"total": 0, "pending_review": 0, "overdue_review": 0}
    if path is None or not path.exists():
        return empty

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty

    if not isinstance(payload, list):
        return empty

    now = datetime.now(timezone.utc)
    total = 0
    pending = 0
    overdue = 0
    for row in payload:
        if not isinstance(row, dict):
            continue
        total += 1
        status = str(row.get("review_status", "pending")).strip().lower()
        is_pending = status in {"pending", "approved-temporary", "temporary"}
        if is_pending:
            pending += 1
        due_at = _parse_iso8601(row.get("review_due_at"))
        if is_pending and due_at is not None and due_at < now:
            overdue += 1

    return {
        "total": total,
        "pending_review": pending,
        "overdue_review": overdue,
    }


def scan_python_file(file_path: Path, result: ScanResult) -> None:
    """단일 Python 파일의 import를 분석해 위반을 수집."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    rel_path = _rel_path(file_path)

    if _is_exempt_python(file_path):
        return

    source_layer = _classify_python_layer(file_path)
    if source_layer is None:
        return

    for match in _IMPORT_PY_RE.finditer(text):
        imported_module = match.group(1) or match.group(2) or ""
        line_no = text[: match.start()].count("\n") + 1

        for src_layer, pattern, vtype, risk, impact, desc in _PYTHON_RULES:
            if source_layer == src_layer and pattern.match(imported_module):
                if vtype == "S3-infra-reverse" and _is_composition_root(file_path):
                    continue
                result.violations.append(
                    Violation(
                        file=rel_path,
                        line=line_no,
                        type=vtype,
                        target=imported_module,
                        risk=risk,
                        impact=impact,
                        matrix_score=_matrix_score(risk, impact),
                        description=desc,
                    )
                )


def scan_ts_file(file_path: Path, result: ScanResult) -> None:
    """단일 TypeScript/TSX 파일의 import를 분석해 위반을 수집."""
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    rel_path = _rel_path(file_path)

    if _is_exempt_ts(file_path):
        return

    source_layer = _classify_ts_layer(file_path)
    if source_layer is None:
        return

    for match in _IMPORT_TS_RE.finditer(text):
        imported_path = match.group(1) or ""
        line_no = text[: match.start()].count("\n") + 1

        for src_layer, pattern, vtype, risk, impact, desc in _TS_RULES:
            if source_layer == src_layer and pattern.match(imported_path):
                result.violations.append(
                    Violation(
                        file=rel_path,
                        line=line_no,
                        type=vtype,
                        target=imported_path,
                        risk=risk,
                        impact=impact,
                        matrix_score=_matrix_score(risk, impact),
                        description=desc,
                    )
                )


def scan_directory(path: Path, result: ScanResult) -> None:
    """디렉토리 내 모든 Python/TypeScript 파일을 재귀 스캔."""
    if not path.exists():
        return

    for file_path in sorted(path.rglob("*")):
        if not file_path.is_file():
            continue
        suffix = file_path.suffix
        if suffix == ".py":
            scan_python_file(file_path, result)
        elif suffix in (".ts", ".tsx"):
            scan_ts_file(file_path, result)

    # 정렬: matrix_score 내림차순 → file → line
    result.violations.sort(key=lambda v: (-v.matrix_score, v.file, v.line))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="정적 참조 경계 위반 스캐너",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="위반 사항이 있으면 exit code 1 반환",
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
        "--enforcement-mode",
        choices=("report", "block"),
        default="report",
        help="운영 모드 (report|block). block이면 위반 시 즉시 실패 처리",
    )
    parser.add_argument(
        "--exceptions-log",
        type=str,
        default=None,
        help="긴급 예외 이력 JSON 경로 (review_status/review_due_at 집계)",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=str(ROOT / "src"),
        help="스캔 대상 경로 (기본: src/)",
    )
    args = parser.parse_args()

    result = ScanResult(
        scan_type="static",
        timestamp=datetime.now(timezone.utc).isoformat(),
        enforcement_mode=args.enforcement_mode,
        block_on_violation=args.enforcement_mode == "block",
    )

    scan_directory(Path(args.target), result)
    result.exception_review = _load_exception_review(
        Path(args.exceptions_log) if args.exceptions_log else None
    )

    output_data = json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    if args.as_json or args.output:
        if args.output:
            out_path = Path(args.output)
            out_path.write_text(output_data, encoding="utf-8")
            print(f"[static] JSON output → {out_path}")
        else:
            print(output_data)

    # Human-readable summary
    summary = result.summary
    print(
        f"[static] Total violations: {summary['total_violations']} "
        f"(Critical={summary['by_risk']['Critical']}, "
        f"High={summary['by_risk']['High']}, "
        f"Medium={summary['by_risk']['Medium']}, "
        f"Low={summary['by_risk']['Low']})"
    )
    review = result.exception_review
    print(
        "[static] Exception review: "
        f"total={review.get('total', 0)}, "
        f"pending={review.get('pending_review', 0)}, "
        f"overdue={review.get('overdue_review', 0)}"
    )
    print(
        f"[static] Enforcement mode: {result.enforcement_mode}"
        + (" (block)" if result.block_on_violation else " (report)")
    )

    if result.block_on_violation and summary["total_violations"] > 0:
        print("[static] FAIL — boundary violations blocked by enforcement mode")
        return 1

    if args.check and summary["total_violations"] > 0:
        print("[static] FAIL — boundary violations detected")
        return 1

    print("[static] PASS — no boundary violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
