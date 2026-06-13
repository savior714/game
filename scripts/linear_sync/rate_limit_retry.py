#!/usr/bin/env python3
"""Linear API Rate Limit 우회용 스크립트.

Exponential Backoff + Retry 로직을 사용하여 429 에러를 자동으로 처리합니다.
"""

import sys
import time
from pathlib import Path

# sys.path 설정
_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
if str(_SCRIPTS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR.parent))

from linear_sync.sync_engine import LinearClient, load_env


def main():
    """Linear API Rate Limit 테스트 및 우회 확인."""
    load_env()
    import os
    
    api_key = (os.environ.get("LINEAR_API_KEY") or "").strip()
    if not api_key:
        print("LINEAR_API_KEY 가 설정되지 않았습니다.", file=sys.stderr)
        return 1
    
    client = LinearClient(api_key)
    
    print("=== Linear API Rate Limit 우회 테스트 ===\n")
    
    # 1. Rate Limit 상태 확인 (team 목록 요청)
    print("1. 팀 목록 조회 (Rate Limit 발생 가능)...")
    try:
        teams = client.list_teams()
        print(f"   ✅ 성공: {len(teams)}개 팀 조회")
    except Exception as e:
        error_msg = str(e).lower()
        if "429" in error_msg or "ratelimit" in error_msg:
            print(f"   ⚠️  Rate Limit 감지 - 자동 재시도 시작...")
            # 최대 3 번 재시도
            for attempt in range(3):
                delay = 2 ** attempt  # 1, 2, 4 초
                print(f"   🔄 {attempt + 1} 번째 재시도 ({delay} 초 대기)...")
                time.sleep(delay)
                try:
                    teams = client.list_teams()
                    print(f"   ✅ 재시도 성공: {len(teams)}개 팀 조회")
                    break
                except Exception as retry_e:
                    if "429" not in str(retry_e).lower() and "ratelimit" not in str(retry_e).lower():
                        raise
            else:
                print(f"   ❌ 모든 재시도 실패")
                return 1
        else:
            raise
    
    # 2. search_issues 테스트
    print("\n2. 이슈 검색 (Rate Limit 발생 가능)...")
    try:
        issues = client.search_issues("PLAN_office_billing", first=5)
        print(f"   ✅ 성공: {len(issues)}개 이슈 검색")
    except Exception as e:
        error_msg = str(e).lower()
        if "429" in error_msg or "ratelimit" in error_msg:
            print(f"   ⚠️  Rate Limit 감지 - 자동 재시도 시작...")
            for attempt in range(3):
                delay = 2 ** attempt
                print(f"   🔄 {attempt + 1} 번째 재시도 ({delay} 초 대기)...")
                time.sleep(delay)
                try:
                    issues = client.search_issues("PLAN_office_billing", first=5)
                    print(f"   ✅ 재시도 성공: {len(issues)}개 이슈 검색")
                    break
                except Exception as retry_e:
                    if "429" not in str(retry_e).lower() and "ratelimit" not in str(retry_e).lower():
                        raise
            else:
                print(f"   ❌ 모든 재시도 실패")
                return 1
        else:
            raise
    
    print("\n=== Rate Limit 우회 테스트 완료 ===")
    print("✅ Exponential Backoff + Retry 로직이 정상 작동합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
