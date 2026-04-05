# 🗂️ Git Commit & Push 워크플로우 (/git)

이 워크플로우는 현재 세션의 모든 변경 사항을 SSOT 문서에 반영하고, 최종적으로 Git에 커밋·푸시하여 작업을 마무리합니다.

> **환경 호환성**: 이 워크플로우는 **Claude Code(VS Code)** 및 **Google Antigravity** 양쪽 환경에서 동일하게 동작합니다.
> 파일 조작은 환경에서 제공하는 파일 읽기/수정 도구를 사용하고, Git 명령어는 터미널에서 실행하십시오.

---

## 📋 실행 체크리스트

### 1단계: 세션 변경 사항 분석 및 SSOT 식별

- [ ] `docs/memory/MEMORY.md`와 현재 대화 기록을 검토하여 수정된 기능, 로직, 스펙을 추출한다.
- [ ] 업데이트가 필요한 SSOT 대상 문서를 결정한다 (`PROJECT_RULES.md` §1.1 준수):
  - 운영 규칙 / 프로토콜 → `PROJECT_RULES.md`
  - 설계 결정 / 핵심 불변 정책 → `docs/CRITICAL_LOGIC.md`
  - 기능 요구사항 및 명세 / 인터페이스 → `docs/specs/*.md`
  - 진행 상황 (세션 정보) → `docs/memory/MEMORY.md` (및 필요 시 하위 모듈)

### 2단계: 문서 업데이트 (Surgical Edit)

- [ ] 식별된 문서들을 **외과적으로 정밀 수정**한다. 기존 구조와 포맷팅을 보존하며 새로운 정보만 병합한다.
- [ ] `docs/memory/MEMORY.md`의 완료된 작업 섹션을 최신화한다.
- [ ] **Memory Density 준수**: `MEMORY.md`가 200라인(또는 25KB)을 초과하면 50라인 이내 요약으로 재작성하고, 세부 내용은 `docs/memory/` 하위 모듈(`user`, `feedback`, `project`, `reference`)로 분리/아카이브한다.

### 3단계: 통합 검증 및 결과 분석

- [ ] 통합 검증 스크립트를 실행한다 (`PROJECT_RULES.md` §4.0):
  ```powershell
  .\verify.bat
  ```
  또는
  ```bash
  node verify_all.js
  ```
- [ ] `Read` 도구로 결과를 확인한다:
  - `verify-last-result.json` (exitCode 및 failedStep 확인)
  - (실패 시) `verify-pytest-failures.txt` (상세 실패 요약 확인)
- [ ] 오류 발생 시 커밋 전 반드시 수정하고 재검증한다.

### 4단계: Git Commit & Push

- [ ] 변경된 파일을 **파일명을 명시하여** 스테이징한다. (`git add .` 지양)
  ```powershell
  git add src/foo.ts docs/memory/MEMORY.md docs/CRITICAL_LOGIC.md
  ```
- [ ] 시니어 아키텍트 톤의 커밋 메시지를 작성한다 (`PROJECT_RULES.md` §5 준수).
  - 형식: `feat(scope): summary` / `fix(scope): summary` / `docs(scope): summary`
  - 예시: `docs(memory): Archive session context and update MEMORY.md index`

  ```powershell
  git commit -m "feat(scope): [핵심 변경 요약]"
  ```
- [ ] 원격 저장소로 푸시한다.
  ```powershell
  git push origin [현재 브랜치명]
  ```

### 5단계: 최종 보고

- [ ] `PROJECT_RULES.md` §4.4의 `Verify Report` 형식에 맞춰 최종 보고를 작성한다.
  - `통합 검증`, `변경 파일`, `정적 검증`, `테스트`, `스모크 검증`, `리스크/후속` 항목 포함
- [ ] 업데이트된 SSOT 문서 목록과 Git 푸시 성공 여부를 사용자에게 보고하며 세션을 마친다.
