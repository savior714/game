#!/usr/bin/env python3
"""Phase 8 Linear 이슈 생성 스크립트 (레거시).

이 스크립트는 과거 자동 생성용으로 남아 있으며, 신규 이슈는 보통 Linear 웹에서 연다.
일상 동기화는 ``sync_engine`` + 루트 ``.env``의 ``LINEAR_API_KEY``를 쓴다.

PLAN_fhir_phase8_frontend_bridge_blueprint.md의 FBC-000, FBC-006 등
Linear에 없는 세부 태스크를 자동으로 생성합니다.

사용법:
    python scripts/linear_sync/create_phase8_issues.py [--dry-run] [--project-id <id>]

환경 변수:
    LINEAR_API_KEY: 프로세스 환경에 두거나(또는 루트 ``.env`` — ``sync_engine``과 동일).

옵션:
    --dry-run      실제 생성 없이 계획만 출력
    --project-id   대상 프로젝트 ID (기본값: 자동 검색)
"""

import json
import os
import sys
from datetime import datetime, timezone

# Phase 8 Blueprint 태스크 매핑 (PLAN_fhir_phase8_frontend_bridge_blueprint.md 기준)
PHASE8_TASKS = [
    {
        "id": "FBC-000",
        "linear_id": "TEM-6",
        "title": "[FBC-000] Backend Technical Debt Cleanup (Baseline)",
        "description": """백엔드 잔여 린트 에러 및 Any 타입을 제거하여 깨끗한 통합 기반 마련.

**목표**: `ruff check . --select ANN401` 결과 0건 달성
**검증**: `just lint && just ty`

**작업 범위**:
- src/ 전체 ANN401 경고 정리
- SIM 관련 린트 에러 제거
- 타입 힌팅 명확화""",
        "priority": 2,  # Medium
    },
    {
        "id": "FBC-006",
        "linear_id": "TEM-15",
        "title": "[FBC-006] Integrated Bridge & Reliability Verification",
        "description": """BFF 호출 -> Zod 검증 -> Atomic State 업데이트 -> 40px 그리드 렌더링 전 구간 정합성 확인.

**검증**: `just verify` (전 단계 PASS)

**작업 범위**:
- E2E 시나리오 테스트 작성
- 린트/타입 부채 0건 상태 유지 확인
- 통합 파이프라인 안정성 검증""",
        "priority": 1,  # High
    },
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


def find_project(api_key: str, project_name: str = "TemplarEMR") -> dict | None:
    """Linear 프로젝트 ID를 이름으로 검색합니다."""
    query = """
    query FindProject($name: String!) {
      projects(filter: { name: { eq: $name } }) {
        nodes {
          id
          name
        }
      }
    }
    """
    
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    payload = {"query": query, "variables": {"name": project_name}}
    
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
                print(f"❌ API 에러: {result['errors']}")
                return None
                
            nodes = result.get("data", {}).get("projects", {}).get("nodes", [])
            return nodes[0] if nodes else None
            
    except Exception as e:
        print(f"❌ 프로젝트 검색 실패: {e}")
        return None


def create_issue(api_key: str, project_id: str, task: dict) -> dict | None:
    """Linear에 새 이슈를 생성합니다."""
    query = """
    mutation CreateIssue($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue {
          id
          title
          state { name }
        }
      }
    }
    """
    
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    
    # Linear Priority: 0=Urgent, 1=High, 2=Medium, 3=Low, 4=None
    priority_map = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}
    
    payload = {
        "query": query,
        "variables": {
            "input": {
                "title": task["title"],
                "description": task["description"],
                "priority": priority_map.get(task["priority"], 2),
                "teamId": project_id,
            }
        },
    }
    
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
                print(f"   ❌ 생성 실패: {result['errors']}")
                return None
                
            return result.get("data", {}).get("issueCreate", {}).get("issue")
            
    except Exception as e:
        print(f"   ❌ API 요청 실패: {e}")
        return None


def main():
    api_key = get_api_key()
    dry_run = "--dry-run" in sys.argv
    
    # 프로젝트 검색
    project = find_project(api_key)
    
    if not project:
        print("⚠️  'TemplarEMR' 프로젝트를 찾을 수 없습니다.")
        print("   --project-id <ID> 옵션으로 직접 지정하세요.")
        
        # 수동 입력 모드
        manual_id = input("프로젝트 ID를 입력하거나 Enter를 누르세요: ").strip()
        if not manual_id:
            sys.exit(1)
        project = {"id": manual_id, "name": manual_id}
    
    print("=" * 60)
    print(f"Phase 8 Linear 이슈 생성")
    print(f"프로젝트: {project['name']} ({project['id']})")
    print(f"모드: {'Dry Run' if dry_run else '실제 생성'}")
    print(f"시각: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)
    
    created = []
    failed = []
    
    for task in PHASE8_TASKS:
        print(f"\n📋 {task['id']} ({task['linear_id']}): {task['title']}")
        
        if dry_run:
            print(f"   [Dry Run] 생성 예정")
            print(f"   설명: {task['description'][:100]}...")
            created.append({"task": task, "dry_run": True})
            continue
        
        result = create_issue(api_key, project["id"], task)
        
        if result:
            print(f"   ✓ 생성됨: {result.get('title', '')}")
            created.append({"task": task, "linear_id": task["linear_id"]})
        else:
            print(f"   ✗ 실패")
            failed.append(task)
    
    # 요약
    print("\n" + "=" * 60)
    print("📊 생성 결과:")
    print(f"   성공: {len(created)}개")
    if failed:
        print(f"   실패: {len(failed)}개")
        for task in failed:
            print(f"     - {task['id']}: {task['title']}")
    
    # JSON 출력 (dry-run 포함)
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": project["name"],
        "mode": "dry_run" if dry_run else "create",
        "created": len(created),
        "failed": len(failed),
        "issues": [
            {
                "local_id": c["task"]["id"],
                "linear_mapping": c["task"]["linear_id"],
                "title": c["task"]["title"],
                "status": "created" if not c.get("dry_run") else "planned",
                "linear_key": c.get("linear_id"),
            }
            for c in created
        ],
    }
    
    print("\n--- JSON ---")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
