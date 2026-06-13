#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Language: ko

import os
import sys
import subprocess
import argparse
from typing import List, Set

def get_touched_files() -> List[str]:
    """Git status 및 diff를 사용하여 현재 작업 디렉터리에서 수정/추가된 파일 목록을 구합니다.
    존재하지 않는 파일(삭제된 파일)은 제외합니다.
    """
    touched: Set[str] = set()

    # 1. 스테이징되지 않았거나 스테이징된 변경사항 (M, A, ?? 상태)
    try:
        status_output = subprocess.check_output(
            ["git", "status", "--porcelain"], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8")
        
        for line in status_output.splitlines():
            if not line.strip():
                continue
            # 포맷: XY PATH 또는 XY "PATH" (공백 등 포함 시 따옴표)
            status_part = line[:2]
            path_part = line[3:].strip().strip('"')
            
            # 삭제(D)된 상태가 아닌 파일들만 수집
            if "D" not in status_part:
                touched.add(path_part)
    except subprocess.SubprocessError:
        pass

    # 2. HEAD와의 차이점 (기타 커밋되지 않은 수정사항)
    try:
        diff_output = subprocess.check_output(
            ["git", "diff", "--name-only"], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8")
        for path in diff_output.splitlines():
            if path.strip():
                touched.add(path.strip())
    except subprocess.SubprocessError:
        pass

    # 존재하지 않는 파일(예: 삭제됨) 걸러내기 및 상대 경로 정규화
    valid_files = []
    for f in touched:
        if os.path.exists(f) and os.path.isfile(f):
            valid_files.append(f)
            
    return sorted(valid_files)

def main():
    parser = argparse.ArgumentParser(description="Git 변경 사항 기반 온디맨드 컨텍스트 라우팅 자동화 스크립트")
    parser.add_argument("--dry-run", action="store_true", help="라우팅을 트리거하지 않고 감지된 변경 파일 목록만 출력")
    parser.add_argument("--tight", action="store_true", help="tight 모드 적용 (Always Load 생략, skill cap=2)")
    
    args = parser.parse_args()
    
    touched_files = get_touched_files()
    
    if not touched_files:
        print("ℹ️ 감지된 변경 파일이 없습니다.")
        sys.exit(0)
        
    print(f"🔍 감지된 변경 파일 ({len(touched_files)}개):")
    for f in touched_files:
        print(f"  - {f}")
        
    if args.dry_run:
        print("ℹ️ 드라이런 모드입니다. 라우팅을 실행하지 않고 종료합니다.")
        sys.exit(0)
        
    # scripts/agent/route_context.py 명령어 조합
    cmd = ["python3", "scripts/agent/route_context.py"]
    cmd.extend(touched_files)
    if args.tight:
        cmd.append("--tight")
        
    print(f"🚀 Running: {' '.join(cmd)}")
    
    # route_context 실행 및 결과 반환
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
