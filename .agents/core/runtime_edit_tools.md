---
id: runtime_edit_tools
scope:
- .agents/core/**
- AGENTS.md
domain: core
status: active
last_verified: 2026-08-06
verify_with:
- uv run pytest -q tests/test_auxiliary_core_contract_consistency.py
---
<!-- Language: ko -->

# 런타임 편집 도구 원칙

이 문서는 특정 IDE의 도구 이름을 저장소 전역 SSOT로 고정하지 않는다.
에이전트는 **현재 세션에 실제로 노출된 도구 설명과 schema**를 따른다.

## 1. 공통 원칙

- 수정 전에 대상 파일의 최신 내용을 읽는다.
- 파일 존재와 경로를 추측하지 않는다.
- 부분 수정은 현재 내용에서 정확히 식별되는 최소 블록을 사용한다.
- 대상과 결과가 같으면 편집 도구를 호출하지 않는다.
- 실패 후 같은 입력을 반복하지 않고 파일을 다시 읽는다.
- 전체 덮어쓰기는 신규 파일이거나, 부분 수정이 안전하지 않고 원본 계약을 diff로 보존할 수 있을 때만 사용한다.
- 편집 성공 응답 뒤 실제 파일 또는 commit diff를 다시 확인한다.

## 2. 현재 도구 우선

세션마다 제공되는 read, search, edit, shell, repository connector의 이름과 인자는 다를 수 있다.

1. 도구 목록 또는 schema를 확인한다.
2. 현재 제공된 도구만 호출한다.
3. 다른 런타임의 JSON 예시나 pseudo tool marker를 사용자 메시지에 출력하지 않는다.
4. connector 데이터가 필요한 작업은 connector read를 먼저 수행한다.
5. 로컬 실행이 필요한 검증만 실제 checkout과 shell로 보완한다.

도구가 없으면 존재한다고 가장하지 않고 가능한 대체 경로와 한계를 보고한다.

## 3. 부분 수정

부분 수정 전에 다음을 확인한다.

- target file 최신본 확보
- old block 또는 symbol 경계 식별
- 매칭이 의도한 위치 하나인지 확인
- old와 new가 다름
- 변경 범위가 현재 failure domain 안에 있음

패턴 불일치 시 범위를 무작정 넓히지 않는다.
재읽기 후 더 정확한 symbol/block을 선택하거나, 안전한 전체 교체가 필요한 이유를 명시한다.

## 4. 대형 파일과 다중 수정

- 대형 파일을 전체 교체할 때는 원본 blob과 후보 blob의 diff를 확인한다.
- 같은 파일을 여러 도구 호출로 동시에 수정하지 않는다.
- 여러 비연속 변경이 같은 failure domain이면 하나의 원자적 patch로 구성한다.
- unrelated 변경이 함께 보이면 게시하지 않는다.
- 생성 artifact는 authoring source와 build pipeline을 통해 갱신한다.

## 5. 로컬 OpenCode

OpenCode를 사용하는 local LLM은 [`opencode_tools.md`](opencode_tools.md)를 추가로 따른다.
해당 문서는 local LLM의 안정적인 호출 규율만 정의하며, 현재 세션의 실제 tool schema보다 우선하지 않는다.

## 6. 검증

- 문서·규칙 변경: 링크, 실제 명령, 현재 제품 방향, stale tool name 부재
- 코드 변경: 직접 focused test와 정적 진단
- repository connector 변경: 후보 commit diff와 remote fast-forward 확인

편집 자체의 성공을 작업 완료로 간주하지 않는다.
