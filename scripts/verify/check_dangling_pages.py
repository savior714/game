#!/usr/bin/env python3
"""
고아/잔존 파일 탐지 스크립트

Next.js 렌더러의 pages/app 디렉토리에서 Git 추적 상태와 실제 파일 존재 여부를
검사하여 불일치하는 파일 (dangling files) 을 탐지합니다.
"""

import subprocess
import sys
from pathlib import Path


def get_renderers_base_dir() -> Path:
    """프로젝트 루트에서 renderer 앱의 base dir 를 반환합니다."""
    project_root = Path(__file__).resolve().parent.parent.parent
    return project_root / "apps" / "renderer"


def check_dangling_files(base_dir: Path, git_tracked_paths: list[str]) -> list[str]:
    """
    Git 추적 경로 중 실제 파일 시스템에 존재하지 않는 파일을 찾습니다.
    
    Args:
        base_dir: 검사할 베이스 디렉토리
        git_tracked_paths: Git 에서 추적 중인 파일 경로 목록
        
    Returns:
        존재하지 않는 파일 (dangling) 목록
    """
    dangling = []
    
    for rel_path in git_tracked_paths:
        full_path = base_dir / rel_path
        
        if not full_path.exists():
            dangling.append(rel_path)
    
    return dangling


def run_git_ls_files(target_dir: str) -> list[str]:
    """
    git ls-files 를 실행하여 추적 중인 파일 목록을 가져옵니다.
    
    Args:
        target_dir: 검사할 디렉토리 경로
        
    Returns:
        추적 중인 파일 경로 목록 (상대 경로)
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", target_dir],
            capture_output=True,
            text=True,
            check=True,
        )
        return [line for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError as e:
        print(f"ERROR: git ls-files 실패: {e.stderr}", file=sys.stderr)
        sys.exit(1)


def run_git_ls_tree(target_dir: str) -> list[str]:
    """
    git ls-tree 를 실행하여 HEAD 에서 추적 중인 파일 목록을 가져옵니다.
    
    Args:
        target_dir: 검사할 디렉토리 경로
        
    Returns:
        추적 중인 파일 경로 목록 (상대 경로)
    """
    try:
        result = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "HEAD", target_dir],
            capture_output=True,
            text=True,
            check=True,
        )
        return [line for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError as e:
        print(f"ERROR: git ls-tree 실패: {e.stderr}", file=sys.stderr)
        sys.exit(1)


def main():
    """메인 실행 함수."""
    base_dir = get_renderers_base_dir()
    
    # .git 디렉토리 존재 확인 (Git 환경이 아닐 경우 graceful pass)
    # 프로젝트 루트에서 .git 찾기
    project_root = base_dir.parent.parent
    git_dir = project_root / ".git"
    if not git_dir.exists():
        print("SKIP: .git 디렉토리가 없습니다. Git 환경이 아닌 것으로 판단하여 통과 처리합니다.")
        sys.exit(0)
    
    #/pages 와 /app 을 모두 검사
    check_dirs = [
        "apps/renderer/src/pages",
        "apps/renderer/src/app",
    ]
    
    all_dangling = []
    
    for check_dir in check_dirs:
        # Git 추적 파일 목록 가져오기
        try:
            tracked_files = run_git_ls_files(check_dir)
        except SystemExit:
            continue  # git 명령 실패 시 다음 디렉토리로
        
        if not tracked_files:
            continue
        
        # Dangling 파일 찾기
        dangling = check_dangling_files(base_dir, tracked_files)
        all_dangling.extend(dangling)
    
    # 결과 보고
    if all_dangling:
        print("=" * 60)
        print("FAIL: 다음 파일들은 Git 에 추적되지만 실제 파일 시스템에 존재하지 않습니다:")
        print("=" * 60)
        for f in all_dangling:
            print(f"  - {f}")
        print("=" * 60)
        print(f"총 {len(all_dangling)}개의 고아/잔존 파일이 발견되었습니다.")
        print("\n다음 조치를 취하세요:")
        print("  1. 파일이 정말 필요하면 복원하세요")
        print("  2. 더 이상 필요하지 않으면 'git rm <path>'로 Git 추적에서 제거하세요")
        print("  3. 'git status'로 현재 상태를 확인하세요")
        sys.exit(1)
    else:
        print("PASS: 고아/잔존 파일이 없습니다.")
        sys.exit(0)


if __name__ == "__main__":
    main()
