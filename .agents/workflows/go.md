---
name: go
description: 세션 이관 - 세션 산출물 문서 동기화 및 다음 에이전트 이관 프롬프트 생성
---

# 🚀 세션 이관 워크플로우 (/go)

이 워크플로우는 현재 세션의 모든 산출물을 문서 위계에 따라 동기화하고, 다음 에이전트가 **즉시 작업을 이어받을 수 있는 이관 프롬프트**를 생성하기 위한 **필수 실행 지침**입니다.

> 환경 호환성: Claude Code(Visual Studio Code) 및 기타 에이전트 환경에서 동일하게 동작합니다. 파일 조작은 환경이 제공하는 읽기/쓰기 도구를 사용합니다.

---

## 1. SDD 준수 및 Fatal Constraints 검증 (Compliance)

- **Design First**: 모든 기능 변경(신규/수정/리팩터링/삭제)이 `docs/specs/` 내 명세 갱신에 **선행 반영**되었는지 확인합니다.
- **Line Count Guard**: 수정된 단일 파일이 **500라인**을 초과하면 즉시 하위 모듈로 기능 분리 후 완료 보고를 금지합니다.
- **Memory SSOT Guard (최우선)**: `docs/memory/MEMORY.md`가 **200라인(또는 25KB)을 초과**한다면
  - 즉시 작업을 중단하고
  - **50라인 이내 요약본**으로 축약한 뒤
  - 세부 지식은 `docs/memory/` 하위 모듈(`user`, `feedback`, `project`, `reference`)로 분리/아카이브합니다.
- **MEMORY Anti-Drift**: 라인 수와 무관하게 `MEMORY.md`에 **장문 요약·Task 서술·긴 괄호·기술 메모**를 넣지 않는다. 상세는 `project_changelog_*.md` / `project_*.md` / `docs/plans/`에 두고 인덱스에는 **링크만** 남긴다(`AGENTS.md` §2.1.1).

---

## 2. 응답 직전 Verify 프로토콜 (필수)

모든 작업 완료 후, **사용자 응답 직전** 아래 체크리스트를 내부적으로 확인합니다.

- [ ] **Line Count**: 수정된 파일이 500라인 초과 없음
- [ ] **Memory Density / Anti-Drift**: `docs/memory/MEMORY.md` 200라인(25KB) 이내, §2.1.1 금지 항목 없음
- [ ] **Language Consistency**: 모든 Artifact가 **한국어**로 작성됨
- [ ] **State Sync**: 수정된 파일의 실재 여부 및 도구 사용 적정성 확인
- [ ] **Latest Sync**: 신규 기술/로직 수정 시 최신 공식 문서 및 `docs/knowledge/` 참조

### 2.1 통합 검증 실행 (verify.ps1)

- **단일 진입**: 저장소 루트에서 `.\verify.bat` (또는 `.\verify.ps1`) 실행
- **결과 확인**:
  - `verify-last-result.json`을 읽어 **exitCode**, **failedStep** 확인
  - 실패 시 `verify-pytest-failures.txt` 또는 JSON의 `pytestFailedTests` 요약 확인 (전체 로그 읽기 금지)
- **원칙**: 검증 실패 상태에서 이관/완료 보고를 금지합니다.

---

## 3. 핵심 SSOT 동기화(문서 업데이트)

다음 파일을 "이번 세션에서 실제로 바뀐 내용" 기준으로 최신화합니다.

- `docs/memory/MEMORY.md`: **인덱스(링크·최소 메타)만** 유지/갱신. **금지**: `Recent Summary` 블록, 링크 뒤 긴 괄호, em-dash 기술 설명, 서술형 공지 단락(→ `project_changelog_*.md` 등으로 이관).
- `docs/memory/*.md`: 세션 상세 변경은 타입별 파일(`project_*`, `reference_*`, `feedback_*`, `user_*`)에 기록
- `docs/CRITICAL_LOGIC.md`: 본 세션에서 결정된 **설계 결정(Design Decisions)** 및 아키텍처 규칙 즉시 기록
- `docs/specs/`: 구현된 기능/규칙 변경에 맞춰 스펙 문서 현행화
- `README.md`: 프로젝트 개요 및 실행 환경 설정 최신 상태 확인(필요 시 갱신)

### 3.1 문서 경계(SSOT) 강제 체크

- **규칙/운영 변경**은 `PROJECT_RULES.md`에 기록하고, 다른 문서에는 링크만 둡니다.
- **설계 결정/불변 정책**은 `docs/CRITICAL_LOGIC.md`에 기록합니다.
- **요구사항/계약(AC)**은 `docs/specs/`에 기록합니다.
- **세션 지식**은 `docs/memory/`에 기록하되, `MEMORY.md`는 인덱스 전용으로 유지합니다.
- 동일 내용의 중복 서술을 금지하고, SSOT 본문 1곳 + 참조 링크로 정리합니다.

### 3.2 신규 문서 생성 규약

- 신규 문서는 `docs/templates/DOC_SSOT_HEADER_TEMPLATE.md` 헤더를 기본으로 시작합니다.
- 메타 헤더는 `Last Verified -> Tested Version -> Min Supported -> Reference` 순서를 유지합니다.

---

## 4. 최신 문서/Best Practice 동기화(선행 확인)

- 신규 라이브러리 사용 또는 주요 로직 수정이 포함된 경우,
  - 해당 기술 스택 **최신 공식 문서(Latest Documentation)** 기준으로 API/Best Practice를 재확인합니다.
  - 필요 시 웹 검색을 수행합니다.

---

## 5. 지식 자산화(필수: 웹 검색 결과가 새로 생긴 경우)

- `docs/knowledge/{topic_name}.md`로 아카이빙합니다.
- 포함 내용: 제목, 핵심 코드/해결책, **출처 URL**, 작성일.
- 웹 검색이 없다면 `N/A`로 처리합니다.

---

## 6. 자기 최적화 분석 (Self-Optimization)

- **패턴 분석**: 세션 중 반복된 수동 작업이나 결정 패턴이 **3회 이상** 발견되었는지 확인합니다.
- **워크플로우 제안**: 발견된 패턴을 자동화할 수 있는 신규 워크플로우(`.md`) 생성을 검토하고, 이관 프롬프트에 기록합니다.

---

## 7. 이관 프롬프트 출력(반드시 포함)

아래 HANDOFF TEMPLATE을 **응답 최하단**에 채워서 코드 블록으로 출력합니다.

```markdown
# 🔄 Session Transition: [Project/Phase Name]

- 다음 에이전트는 다음 순서로 컨텍스트를 로드합니다.
  1. Global Rules(예: `AGENTS.md`) 및 관련 운영 문서
  2. `docs/CRITICAL_LOGIC.md`
  3. `docs/memory/MEMORY.md`
  4. 필요 시 관련 `docs/specs/*`

## ✅ SSOT Sync 완료 현황

- **memory.md**(`docs/memory/MEMORY.md`): [업데이트 내용 한 줄 요약 또는 "변경 없음"]
- **CRITICAL_LOGIC.md**: [추가된 설계 결정 또는 "변경 없음"]
- **README.md**: [업데이트 내용 또는 "변경 없음"]
- **세션 추가 문서**: [이번 세션에서 수정한 기타 docs/ 문서 목록 또는 "N/A"]

## 🧠 Architectural Context & Intent

- **현재 상태**: [현재 작업 요약 및 아키텍처 의도]
- **SDD Alignment**: [설계 준수 여부: "Docs-First 완료", "500라인 준수" 등]
- **물리적 변경 (Business Logic)**: [비즈니스 로직 수정 파일 및 목적]
- **물리적 변경 (Infrastructure)**: [인프라/UI/설동 보조 파일 및 목적]

## ✅ Verify Report (필수)

- **통합 검증**: `verify.ps1` **exitCode** + `failedStep` (실패 시 원인 요약)
- **변경 파일**: [경론 목록]
- **정적 검증**: [통합 검증 결과 인용]
- **테스트**: [실행 범위 및 결과]
- **스모크 검증**: [시나리오 및 결과]
- **리스크/후속**: [잔여 리스크 및 후속 작업]

## 💡 Self-Optimization & Insights

- **패턴 탐지**: [반복된 작업/패턴 요약 또는 "없음"]
- **제안**: [신규 워크플로우(.md) 또는 자동화 제안]

## 🚀 Immediate Next Steps (최대 1개)

1. [다음 세션에서 즉시 실행 가능한 첫 번째 물리적 작업]
```
