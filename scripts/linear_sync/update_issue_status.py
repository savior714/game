#!/usr/bin/env python3
"""Linear 이슈 상태 업데이트 스크립트 (레거시).

이 스크립트는 과거 일괄 업데이트용으로 남아 있으며, 일상 워크플로는
``sync_engine`` + 루트 ``.env``의 ``LINEAR_API_KEY``를 쓴다.

Phase 7~8 Linear 이슈들의 상태를 지정된 상태로 변경합니다.
완료(Done) 상태가 없으면 Todo/In Progress로 변경하거나, Linear UI에서 완료 상태를 추가하세요.

사용법:
    python scripts/linear_sync/update_issue_status.py [--json] [--dry-run] [TEM-7 TEM-10 ...]

환경 변수:
    LINEAR_API_KEY: 프로세스 환경에 두거나(또는 루트 ``.env`` — ``sync_engine``과 동일).

옵션:
    --json         JSON 형식으로 결과 출력
    --dry-run      실제 업데이트 없이 계획만 출력
    --state-uuid   대상 상태 UUID 직접 지정 (자동 추출 실패 시 사용)
    --target-state 타겟 상태 이름 (기본값: Done, 없으면 Todo)
"""

import json
import os
import sys
from datetime import datetime, timezone
from typing import List, Optional, Tuple

# 업데이트할 이슈 ID 목록 (Linear shorthand identifier 기준)
ISSUES_TO_UPDATE = [
    "TEM-7",   # 의원급 핵심 ViewModel 인터페이스 정의
    "TEM-8",   # FHIR-to-ViewModel 매퍼 구현
    "TEM-9",   # ViewModel 기반 TanStack Query Hooks 구축
    "TEM-10",  # 통합 AppShell 및 전역 사이드바 구현
    "TEM-11",  # 진료실 3-Pane 반응형 그리드 컨테이너 구축
    "TEM-12",  # 환자 세션 헤더(SessionHeader) 및 알럿 레인(Alert Lane) 구현
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


def fetch_issue(api_key: str, issue_id: str) -> Optional[dict]:
    """Linear 이슈를 조회합니다."""
    query = """
    query GetIssue($id: String!) {
      issue(id: $id) {
        id
        identifier
        title
        state {
          name
          color
          id
          type
        }
        priority
        createdAt
        updatedAt
      }
    }
    """
    
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
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
                return None
                
            issue = result.get("data", {}).get("issue")
            return issue
            
    except Exception as e:
        print(f"  ⚠️ {issue_id} API 요청 실패: {e}")
        return None


def fetch_all_issues(api_key: str, issue_ids: List[str]) -> dict[str, dict]:
    """여러 이슈를 한 번에 조회합니다. identifier 키로 매핑."""
    issues = {}
    for issue_id in issue_ids:
        issue = fetch_issue(api_key, issue_id)
        if issue:
            identifier = issue.get("identifier", issue_id)
            issues[identifier] = issue
    return issues


def find_target_state_uuid(api_key: str, reference_issue_ids: List[str], target_name: str) -> Tuple[Optional[str], dict]:
    """기존 Linear 이슈들에서 타겟 상태 UUID를 추출합니다.
    
    우선순위로 검색:
    1. 정확히 일치하는 이름 (예: "Done")
    2. 부분 일치 (예: "Active", "Completed")
    3. 첫 번째 이슈의 모든 상태 정보 반환
    """
    # 정확한 일치 먼저 확인
    for issue_id in reference_issue_ids:
        issue = fetch_issue(api_key, issue_id)
        
        if not issue:
            continue
        
        state = issue.get("state")
        if state and state.get("name") == target_name:
            print(f"   ✅ 타겟 상태 UUID 발견: {issue_id} → {target_name}")
            return state["id"], {"source_issue": issue_id, "title": issue.get("title", "")}
    
    # 부분 일치 확인 (Active, Completed 등)
    for issue_id in reference_issue_ids:
        issue = fetch_issue(api_key, issue_id)
        
        if not issue:
            continue
        
        state = issue.get("state")
        if state and target_name.lower() in state.get("name", "").lower():
            print(f"   ✅ 타겟 상태 UUID 발견 (부분 일치): {issue_id} → {state['name']}")
            return state["id"], {"source_issue": issue_id, "title": issue.get("title", ""), "matched_name": state["name"]}
    
    # 찾지 못하면 첫 번째 이슈에서 모든 상태 정보 반환
    for issue_id in reference_issue_ids:
        issue = fetch_issue(api_key, issue_id)
        if issue and issue.get("state"):
            print(f"   ⚠️ '{target_name}' 상태를 찾을 수 없음")
            print(f"      참고 이슈({issue_id}) 상태 정보:")
            print(f"      - 이름: {issue['state'].get('name')}")
            print(f"      - UUID: {issue['state'].get('id', 'N/A')}")
            return None, {"source_issue": issue_id, "current_state": issue["state"]}
    
    return None, {}


def update_issue_status(api_key: str, issue_uuid: str, state_uuid: str) -> bool:
    """Linear 이슈의 상태를 업데이트합니다."""
    query = """
    mutation UpdateIssue($id: String!, $stateId: String!) {
      issueUpdate(id: $id, input: { stateId: $stateId }) {
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
    payload = {
        "query": query,
        "variables": {
            "id": issue_uuid,  # Linear 내부 UUID 필요 (shorthard ID 아님)
            "stateId": state_uuid,
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
                print(f"  ❌ 업데이트 실패: {result['errors'][0].get('message', 'unknown')}")
                return False
                
            success = result.get("data", {}).get("issueUpdate", {}).get("success", False)
            return success
            
    except Exception as e:
        print(f"  ❌ API 요청 실패: {e}")
        return False


def main():
    api_key = get_api_key()
    dry_run = "--dry-run" in sys.argv
    json_output = "--json" in sys.argv
    
    # 옵션 파싱 먼저
    state_uuid_from_cli = None
    target_state_name = "Done"  # 기본값
    
    skip_indices = set()
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--state-uuid" and i < len(sys.argv):
            state_uuid_from_cli = sys.argv[i + 1]  # i+1이 다음 인자 (sys.argv는 0-indexed)
            skip_indices.add(i)
            skip_indices.add(i + 1)
        elif arg == "--target-state" and i < len(sys.argv):
            target_state_name = sys.argv[i + 1]
            skip_indices.add(i)
            skip_indices.add(i + 1)
    
    # 명령줄 인자에서 이슈 ID 받기 (없으면 전체, 옵션 제외)
    cli_issue_ids = [arg for idx, arg in enumerate(sys.argv[1:], 1) if not arg.startswith("--") and idx not in skip_indices]
    
    print("=" * 60)
    print("Linear 이슈 상태 업데이트")
    print(f"모드: {'Dry Run' if dry_run else '실제 업데이트'}")
    print(f"타겟 상태: {target_state_name}")
    print(f"시각: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)
    
    # 1. 타겟 상태 UUID 결정
    print("\n📋 1단계: 타겟 상태(UUID) 확인 중...")
    done_state_uuid = state_uuid_from_cli
    
    if not done_state_uuid:
        print(f"   자동 추출 시도 중 ({target_state_name} 상태)...")
        done_state_uuid, state_info = find_target_state_uuid(api_key, ["TEM-7", "TEM-8", "TEM-9"], target_state_name)
    
    if not done_state_uuid:
        print("\n❌ 타겟 상태 UUID를 찾을 수 없습니다.")
        print("   다음 방법 중 하나를 사용하세요:")
        print(f"   1. Linear UI에서 '{target_state_name}' 상태 추가 후 UUID 확인")
        print(f"   2. 완료 상태 UUID를 직접 입력: python script.py --state-uuid <UUID>")
        
        # dry-run 모드에서는 수동 입력 건너뛰고 에러로 종료
        if dry_run:
            print("\n⚠️ Dry Run 모드에서 타겟 상태 UUID가 필요합니다.")
            print("   실제 업데이트 전에 Linear UI에서 상태를 확인하세요.")
            sys.exit(1)
        
        # interactive 모드에서는 수동 입력 허용
        try:
            manual_uuid = input(f"\n{target_state_name} 상태 UUID를 입력하거나 Enter를 누르세요: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n⚠️ 입력이 취소되었습니다.")
            sys.exit(1)
        
        if not manual_uuid:
            sys.exit(1)
        done_state_uuid = manual_uuid
        print(f"   ✅ 수동으로 타겟 상태 UUID 설정: {done_state_uuid[:8]}...")
    
    # 2. 업데이트할 이슈 결정
    if cli_issue_ids:
        issues_to_process = [iid for iid in ISSUES_TO_UPDATE if iid in cli_issue_ids]
        if not issues_to_process:
            print(f"❌ 지정된 이슈를 찾을 수 없습니다: {cli_issue_ids}")
            sys.exit(1)
    else:
        issues_to_process = ISSUES_TO_UPDATE
    
    # 3. 모든 이슈 한 번에 조회 (성능 최적화 + 정확한 제목 표시)
    print(f"\n📋 2단계: {len(issues_to_process)}개 이슈 업데이트 예정")
    all_issues = fetch_all_issues(api_key, issues_to_process)
    
    updated = []
    failed = []
    already_target = []
    not_found = []
    
    for issue_id in issues_to_process:
        print(f"\n🔍 {issue_id}")
        
        # 이슈 조회 (UUID 확보용)
        if issue_id in all_issues:
            issue = all_issues[issue_id]
        else:
            issue = fetch_issue(api_key, issue_id)
            if issue:
                all_issues[issue_id] = issue
        
        if not issue:
            print(f"  ⚠️ 이슈를 찾을 수 없음 - 건너뜀")
            failed.append({"id": issue_id, "reason": "not_found"})
            continue
        
        current_state = issue.get("state", {}).get("name", "Unknown")
        title = issue.get("title", "(제목 없음)")
        issue_uuid = issue["id"]  # Linear 내부 UUID
        
        print(f"   제목: {title}")
        print(f"   현재 상태: {current_state}")
        
        if current_state == target_state_name:
            print(f"   ✅ 이미 '{target_state_name}' 상태 - 건너뜀")
            already_target.append(issue_id)
            continue
        
        if dry_run:
            print(f"   [Dry Run] → {target_state_name}으로 변경 예정 (UUID: {issue_uuid[:8]}...)")
            updated.append({"id": issue_id, "uuid": issue_uuid, "dry_run": True})
            continue
        
        # 상태 업데이트
        print(f"   🔄 상태를 '{target_state_name}'로 변경 중...")
        success = update_issue_status(api_key, issue_uuid, done_state_uuid)
        
        if success:
            print(f"   ✅ 완료됨!")
            updated.append({"id": issue_id, "uuid": issue_uuid})
        else:
            print(f"   ❌ 실패")
            failed.append({"id": issue_id, "reason": "update_failed"})
    
    # 4. 결과 요약
    print("\n" + "=" * 60)
    print("📊 업데이트 결과:")
    print(f"   완료: {len(updated)}개")
    if already_target:
        print(f"   이미 '{target_state_name}' 상태: {len(already_target)}개 ({', '.join(already_target)})")
    if failed:
        print(f"   실패: {len(failed)}개")
        for f in failed:
            print(f"     - {f['id']}: {f['reason']}")
    
    # JSON 출력 모드
    if json_output or dry_run:
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "dry_run" if dry_run else "update",
            "target_state_uuid": done_state_uuid,
            "target_state_name": target_state_name,
            "total": len(issues_to_process),
            "updated": len(updated),
            "already_target": len(already_target),
            "failed": len(failed),
        }
        
        print("\n--- JSON ---")
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
