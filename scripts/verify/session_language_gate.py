#!/usr/bin/env python3
"""
세션 시작 게이트 — 문서 언어 주석 검증 스크립트

목적:
  - 프로젝트 문서에 <!-- Language: ko --> 주석이 있는지 확인
  - 신규 생성된 .md 파일 중 주석이 없는 경우 경고
  - 세션 시작 전 또는 커밋 전에 실행하여 한국어 우선 정책 준수 확인

실행 방법:
  python scripts/verify/session_language_gate.py [--dir PATH] [--strict]
  
  --dir PATH   : 검증할 디렉토리 (기본값: docs/)
  --strict     : 경고도 실패로 처리 (CI용)

종료 코드:
  0 : PASS (모든 파일에 주석 있음)
  1 : FAIL (주석이 누락된 파일이 있음)
"""

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path


# 검증 대상 확장자
TARGET_EXTENSIONS = {".md"}

# 제외 디렉토리
EXCLUDE_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "dist",
    ".uv_cache",
    "build",
    ".next",
    "coverage",
    ".pytest_cache",
}

# 언어 주석 패턴 (첫 줄 또는 첫 10줄 이내)
LANGUAGE_ANNOTATION_PATTERN = "<!-- Language:"


def is_target_file(filepath: Path) -> bool:
    """검증 대상 파일인지 확인"""
    return filepath.suffix.lower() in TARGET_EXTENSIONS


def should_exclude_dir(dirpath: str) -> bool:
    """제외 대상 디렉토리인지 확인"""
    return any(exclude in Path(dirpath).parts for exclude in EXCLUDE_DIRS)


def check_language_annotation(filepath: Path) -> tuple[bool, str]:
    """파일의 언어 주석 존재 여부 확인 (첫 10줄 이내)"""
    try:
        with filepath.open(encoding="utf-8") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= 10:  # 첫 10줄만 확인
                    break
                lines.append(line.rstrip())
        
        content = "\n".join(lines)
        has_annotation = LANGUAGE_ANNOTATION_PATTERN.lower() in content.lower()
        
        if not has_annotation:
            return False, f"Language 주석 누락 (첫 10줄 내 검색)"
        
        # 주석이 있는지 확인하고 내용 추출
        for line in lines[:5]:
            if "Language:" in line:
                return True, f"주석 발견: {line.strip()}"
        
        return False, "Language 주석 형식 오류"
    except (UnicodeDecodeError, PermissionError) as e:
        return False, f"파일 읽기 오류: {e!s}"


def scan_directory(target_dir: str, strict: bool = False) -> dict:
    """디렉토리 내 모든 파일의 언어 주석 검증"""
    result = {
        "timestamp": datetime.now(UTC).isoformat(),
        "target_dir": os.path.abspath(target_dir),
        "strict_mode": strict,
        "total_files": 0,
        "files_with_annotation": 0,
        "files_without_annotation": [],
        "status": "pass",
        "message": "",
    }

    target_path = Path(target_dir)
    if not target_path.exists():
        result["error"] = f"디렉토리가 존재하지 않습니다: {target_dir}"
        return result

    for root, dirs, files in os.walk(target_dir):
        # 제외 디렉토리 필터링
        dirs[:] = [d for d in dirs if not should_exclude_dir(str(Path(root) / d))]

        for filename in files:
            filepath = Path(root) / filename
            if not is_target_file(filepath):
                continue

            result["total_files"] += 1
            has_annotation, message = check_language_annotation(filepath)

            if has_annotation:
                result["files_with_annotation"] += 1
            else:
                rel_path = os.path.relpath(filepath, target_dir)
                result["files_without_annotation"].append({
                    "file": rel_path,
                    "reason": message,
                })

    # 상태 결정
    if result["files_without_annotation"]:
        result["status"] = "fail"
        count = len(result["files_without_annotation"])
        if strict:
            result["message"] = f"FAIL (strict): {count}개 파일에 Language 주석 누락"
        else:
            result["message"] = f"WARNING: {count}개 파일에 Language 주석 누락 (권고)"
    else:
        result["status"] = "pass"
        result["message"] = f"PASS: 모든 {result['total_files']}개 파일에 Language 주석 있음"

    return result


def print_report(result: dict) -> None:
    """검증 결과를 콘솔에 출력"""
    print("=" * 70)
    print("  [Session Language Gate Check]")
    print("=" * 70)
    print(f"  대상 디렉토리: {result.get('target_dir', 'N/A')}")
    print(f"  전체 파일: {result['total_files']}개")
    print(f"  주석 있음: {result['files_with_annotation']}개")
    print(f"  주석 없음: {len(result['files_without_annotation'])}개")
    print()

    # 상태
    status = result["status"]
    if status == "fail":
        tag = "[FAIL]" if not result.get("strict_mode") else "[FAIL-strict]"
        print(f"  {tag} {result['message']}")
    else:
        print(f"  [PASS] {result['message']}")
    print()

    # 누락 파일 상세
    if result["files_without_annotation"]:
        print("[WARNING] Language 주석이 누락된 파일:")
        print("-" * 50)
        for entry in result["files_without_annotation"][:10]:  # 최대 10개만 표시
            print(f"  - {entry['file']}: {entry['reason']}")
        if len(result["files_without_annotation"]) > 10:
            print(f"  ... 및 {len(result['files_without_annotation']) - 10}개 파일 더")
    print()
    print("=" * 70)


def get_exit_code(result: dict) -> int:
    """검증 결과에 따른 종료 코드 반환"""
    if result["status"] == "fail":
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="프로젝트 문서의 Language 주석 누락을 검증합니다."
    )
    parser.add_argument(
        "--dir", "-d", default="docs/", help="검증할 디렉토리 (기본값: docs/)"
    )
    parser.add_argument(
        "--strict", action="store_true", help="경고를 실패로 처리 (CI용)"
    )

    args = parser.parse_args()

    # 스캔 실행
    result = scan_directory(args.dir, strict=args.strict)

    # 콘솔 출력
    print_report(result)

    # 종료 코드 반환
    sys.exit(get_exit_code(result))


if __name__ == "__main__":
    main()
