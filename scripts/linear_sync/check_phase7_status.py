#!/usr/bin/env python3
"""Phase 7 Linear 이슈 상태 확인 스크립트.

Linear API를 통해 TEM-7~TEM-17 이슈의 현재 상태를 조회하고
완료된 항목을 보고합니다.

사용법:
    python scripts/linear_sync/check_phase7_status.py [--json]

환경 변수:
    LINEAR_API_KEY: Linear Personal Access Token (https://linear.app/settings/api)
"""

import json
import os
import sys
from datetime import datetime, timezone

# Phase 7 이슈 ID 목록 (Linear shorthand identifier 기준)
PHASE7_ISSUES = [
    "TEM-7",   # 의원급 핵심 ViewModel 인터페이스 정의
    "TEM-8",   # FHIR-to-ViewModel 매퍼 구현
    "TEM-9",   # ViewModel 기반 TanStack Query Hooks 구축
    "TEM-10",  # 통합 AppShell 및 전역 사이드바 구현
    "TEM-11",  # 진료실 3-Pane 반응형 그리드 컨테이너 구축
    "TEM-12",  # 환자 세션 헤더 및 알럿 레인 구현
    "TEM-13",  # 상병(KCD/ICD-10) 입력 위젯 이관
    "TEM-14",  # 처방 및 오더 입력 위젯 이관
    "TEM-15",  # 환자 과거력(History) 및 타임라인 위젯 통합
    "TEM-16",  # [Compliance] KR Core V2.0.0 정식판 정합성 재검증
    "TEM-17",  # [Infra] HAPI FHIR 용어 서버 도입 및 로컬 자립화
]

API_URL = "https://api.linear.app/graphql"


def get_api_key() -> str:
    """LINEAR_API_KEY 환경 변수에서 토큰을 가져옵니다."""
    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        print("⚠️  LINEAR_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("   https://linear.app/settings/api 에서 Personal Access Token 생성 후 설정하세요.")
        sys.exit(1)
    return api_key


def fetch_issues(api_key: str, issue_ids: list[str]) -> dict[str, dict]:
    """Linear API를 통해 지정된 이슈들의 상태를 조회합니다.

    Linear 2024 스키마 변경으로 인해 개별 쿼리 방식으로 전환됨.
    filter { id: { in: $ids } }는 shorthand ID(TEM-7 등)를 지원하지 않음.
    
    Returns: dict keyed by identifier (e.g., "TEM-8") -> issue data
    """
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    query = """
    query GetIssue($id: String!) {
      issue(id: $id) {
        id
        identifier
        title
        state {
          name
          type
          color
        }
        priority
        createdAt
        updatedAt
        description
      }
    }
    """

    issues = {}
    for issue_id in issue_ids:
        payload = {"query": query, "variables": {"id": issue_id}}
        
        try:
            import urllib.request
            
            req = urllib.request.Request(
                API_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                
                if "errors" in result:
                    print(f"  ⚠️ {issue_id} 조회 실패: {result['errors'][0].get('message', 'unknown')}")
                    continue
                    
                issue = result.get("data", {}).get("issue")
                if issue:
                    # identifier를 키로 사용 (Linear shorthand ID)
                    identifier = issue.get("identifier", issue_id)
                    issues[identifier] = issue
                else:
                    print(f"  ⚠️ {issue_id} API 응답에 이슈 없음 (삭제되었거나 권한 문제)")
                    
        except Exception as e:
            print(f"  ⚠️ {issue_id} API 요청 실패: {e}")

    return issues


def format_status(status_name: str, status_type: str = "") -> tuple[str, str]:
    """이슈 상태를 이모지 표시와 함께 포맷합니다. (이름, 타입) 반환"""
    # 이름 매핑
    name_map = {
        "Done": ("✓", "완료"),
        "In Progress": ("◐", "진행중"),
        "Todo": ("○", "대기"),
        "Backlog": ("⊘", "백로그"),
        "Canceled": ("✗", "취소됨"),
    }
    
    # 타입 매핑 (더 정확한 분류)
    type_map = {
        "completed": ("✓", "완료"),
        "started": ("◐", "진행중"),
        "in_progress": ("◐", "진행중"),
        "unstarted": ("○", "대기"),
        "backlog": ("⊘", "백로그"),
        "triage": ("△", "트라이지"),
    }
    
    # 타입 우선, 이름 폴백
    emoji, label = type_map.get(status_type) or name_map.get(status_name, ("?", status_name))
    return f"{emoji} {label}", status_type


def main():
    api_key = get_api_key()
    
    print("=" * 60)
    print("Phase 7 Linear 이슈 상태 확인")
    print(f"시각: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)
    
    # API 호출 — identifier 기반 매칭을 위해 전체 조회
    issues = fetch_issues(api_key, PHASE7_ISSUES)
    
    completed = []
    pending = []
    not_found = []
    
    for issue_id in PHASE7_ISSUES:
        if issue_id in issues:
            issue = issues[issue_id]
            status_name = issue.get("state", {}).get("name", "Unknown")
            status_type = issue.get("state", {}).get("type", "")
            
            emoji_label, _ = format_status(status_name, status_type)
            
            display = f"  {issue_id}: {issue['title']}"
            display += f"\n    상태: {emoji_label}"
            display += f"\n    업데이트: {issue.get('updatedAt', 'N/A')[:10]}"
            
            if status_name == "Done" or status_type == "completed":
                completed.append(display)
            else:
                pending.append(display)
        else:
            # API에 없는 경우 (삭제되었거나 권한 문제일 수 있음)
            display = f"  {issue_id}: (이슈 정보 없음)"
            display += "\n    상태: ? (API 응답 없음 — 삭제되었거나 권한 문제일 수 있음)"
            not_found.append(display)
    
    # 보고서 출력
    print(f"\n📊 요약:")
    print(f"   총 이슈: {len(PHASE7_ISSUES)}개")
    print(f"   조회 성공: {len(issues)}개")
    print(f"   완료: {len(completed)}개")
    print(f"   미완료: {len(pending)}개")
    if not_found:
        print(f"   미발견: {len(not_found)}개 ({', '.join(not_found)})")
    
    if completed:
        print("\n✅ 완료된 이슈:")
        for item in completed:
            print(item)
    
    if pending:
        print("\n⏳ 미완료 이슈 (수동 업데이트 필요):")
        for item in pending:
            print(item)
    
    if not_found:
        print("\n❌ API 응답 없음 (삭제되었거나 권한 문제일 수 있음):")
        for item in not_found:
            print(item)
    
    # JSON 출력 모드
    if "--json" in sys.argv:
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": len(PHASE7_ISSUES),
            "found": len(issues),
            "completed": len(completed),
            "pending": len(pending),
            "not_found": len(not_found),
            "issues": [
                {
                    "id": issue_id,
                    "found": issue_id in issues,
                    "status": issues[issue_id].get("state", {}).get("name", "Unknown") if issue_id in issues else None,
                    "title": issues[issue_id].get("title", "") if issue_id in issues else None,
                }
                for issue_id in PHASE7_ISSUES
            ],
        }
        print("\n--- JSON ---")
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
