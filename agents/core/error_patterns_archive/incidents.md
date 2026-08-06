---
scope: archive
domain: core
parent: .agents/core/error_patterns.md
---
<!-- Language: ko -->

# Error Patterns — 희귀 사고 아카이브 (§8~15)

`occurrence_count` 1회·도메인 특화 패턴. frontmatter id는 [error_patterns.md](../error_patterns.md) YAML에 유지.

---

## 8. Python 의존성 실수

### 8.1 dependency-injector DeclarativeContainer mixin 상속 실패

**증상**: Container provider를 CoreContainerMixin → RepositoryContainerMixin → ServiceContainerMixin mixin 체인으로 분할하려 했으나, Python 클래스 본문 평가 시 부모 클래스 속성(db_session, config, signer 등)을 자식 클래스에서 참조할 수 없어 NameError 발생. metaclass __new__/__prepare__ 접근법 모두 실패.

**원인**: dependency-injector DeclarativeContainer은 mixin 상속을 지원하지 않음. Python 클래스 본문은 부모 클래스 속성을 상속받지 않음. metaclass __new__는 본문 평가 이후 호출, __prepare__는 DeclarativeContainerMetaClass 검증과 충돌.

```
factory 함수 패턴 사용: 각 split 파일이 Provider 반환 factory 함수를 정의하고, Container 클래스 본문에서 호출하여 provider 할당. 예: def make_fhir_repo(session): return providers.Factory(HybridFHIRRepository, session=session). Container 클래스: fhir_repo = make_fhir_repo(db_session).
```

---

## 9. 스크립트 경로 계산 오류

### 9.1 Path.parents[N] repo root 오계산

**증상**: `Path(__file__).resolve().parents[3]` 등으로 repo root를 계산하려 했으나, 실제 파일 구조와 parents 깊이가 맞지 않아 `FileNotFoundError: No such file or directory: '/Users/seungjulee/Desktop/Dev/Justfile'` 발생. (실제 경로는 `/Users/seungjulee/Desktop/Dev/emr/Justfile`)

**원인**: `scripts/verify/build_verify_registry.py` 에서 `parents[0]=scripts/verify/`, `parents[1]=scripts/`, `parents[2]=emr/`(root), `parents[3]=Dev/`. `parents[3]`은 repo root가 아닌 상위 디렉토리를 가리킴.

**예방**:
- `Path(__file__).resolve().parents[N]` 로 root 계산 시, 먼저 `python3 -c "from pathlib import Path; p=Path(__file__).resolve(); print([p.parents[i] for i in range(5)])"` 로 실제 깊이 확인
- `scripts/verify/` 하위 스크립트는 `parents[2]`가 repo root (`emr/`)
- `scripts/` 하위 스크립트는 `parents[1]`가 repo root
- 계산 후 `assert ROOT / 'Justfile'.exists()` 등으로 검증

**session_note**: "PLAN_verify_registry_autogen.md Task 1.2 구현 시 발생. `parents[3]` → `parents[2]`로 수정하여 해결."

---

## 10. plan-lint Status 파싱 충돌

### 10.1 문서 레벨 `- **Status**:` 가 마지막 Task 블록 Status 덮어씀

**증상**: `just plan-lint` 가 "Task#6 Status='todo'" 에러를 보고하지만, 파일상 Task#6 의 `- Task-ID: [VREG-006] | ... | Status: done` 은 이미 `done` 으로 설정됨.

**원인**: `_split_task_blocks()` 가 `#### Task` heading 으로 블록을 분할할 때, 마지막 Task 블록은 다음 `#### Task` 가 없어 파일 끝까지 확장됨. 이로 인해 `## Conclusion & Summary` 섹션의 `- **Status**: todo` 가 `_parse_fields()` 에 의해 task-level Status 를 덮어씀.

**예방**:
- Blueprint 파일의 `## Conclusion & Summary` 섹션에서 `- **Status**:` 는 항상 모든 Task 가 완료되면 `done` 으로 유지
- 또는 마지막 Task 블록이 문서 끝까지 확장되는 경우, 문서 레벨 Status 와 task 레벨 Status 가 충돌하지 않도록 구조 변경 고려
- plan-lint 실행 전 `python3 -c "from scripts.plan_loop.plan_lint.shared import _parse_fields, _split_task_blocks; ..."` 로 실제 파싱된 Status 확인 가능

**session_note**: "PLAN_verify_registry_autogen.md Task 1.6 완료 후 plan-lint 실행 시 발생. `## Conclusion & Summary` 의 `- **Status**: todo` → `done` 으로 수정하여 해결."

---

## 11. plan-task-close Conclusion shell 해석

### 11.1 conclusion 인자 내 단어가 bash 명령어로 해석됨

**증상**: `just plan-task-close plan=<file> task=<N> conclusion="...ImportError..."` 실행 시 conclusion 텍스트에서 `ImportError` 등이 bash 에 의해 명령어로 해석되어 텍스트가 손실됨.

**원인**: `just plan-task-close` 스크립트가 conclusion 인자를 shell 환경에서 처리할 때, 인용부호가 제대로 전달되지 않거나 스크립트 내부에서 `eval`/`$()` 등을 사용하면 특수 단어가 명령어로 해석됨.

**예방**:
- `just plan-task-close` 의 conclusion 에는 특수 문자(`<`, `>`, `|`, `&`, `!`)나 이모지(🚫, ✅ 등)를 포함하지 않는다.
- 결론이 길거나 특수 문자가 필요하면 `patch` 로 직접 파일 수정.
- `just plan-task-close` 실행 후 반드시 `Read` 로 Conclusion 이 정확히 기록되었는지 확인.

**session_note**: "PLAN_git_commit_secret_staged_gate.md Task 1.1 완료 시 발생. `ImportError` 가 bash 명령어로 해석되어 Conclusion 이 `ImportError 반환 확인` → ` 반환 확인` 으로 손상됨. `patch` 로 수동 복구."

---

## 12. DISCUSS 파일 YAML 파싱

### 12.1 dual `---` 문서로 yaml.safe_load 실패

**증상**: `yaml.safe_load()` 로 `docs/discussions/DISCUSS_*.md` 파일 파싱 시 `ComposerError: expected a single document in the stream` 발생.

**원인**: DISCUSS 파일은 YAML frontmatter(`---` 시작/끝) 와 본문 내 `---` 구분자(예: 섹션 분리용) 를 모두 포함. `yaml.safe_load()` 는 첫 `---` 문서만 읽고 두 번째 `---` 에서 에러를냄.

**예방**:
- DISCUSS 파일 파싱 시 `yaml.safe_load()` 대신 `str.split('---')` 로 frontmatter 본문만 추출 후 파싱.
- 또는 `yaml.safe_load_all()` 사용하여 여러 문서 모두 읽기.
- YAML 파싱이 필요한 경우: `content = open(path).read().split('---\n')[1].split('---\n')[0]` 로 frontmatter 만 추출.

**session_note**: "PLAN_git_commit_secret_staged_gate.md Task 1.7 검증 시 발생. DISCUSS 파일에 frontmatter `---` 와 본문 `---` 가 모두 있어 `yaml.safe_load()` 실패. `str` 기반 검증으로 우회."

---

## 13. 게이트 검증 오인식

### 13.1 docs-discuss-lifecycle 아카이브 기존 실패 오인

**증상**: `just docs-discuss-lifecycle` 실행 시 아카이브 디렉토리의 기존 실패가 보고되어 "검증 실패"로 오인.

**원인**: 검증 스크립트가 전체 디렉토리(archive 포함)를 스캔하므로, 기존 아카이브 파일의 구조적 문제(누락 필드 등)가 새 변경 사항과 무관하게 실패로 보고됨.

**예방**:
- `just docs-discuss-lifecycle` 실행 후 출력에서 실패 파일 목록이 **새 변경 파일**을 포함하는지 확인.
- 아카이브 디렉토리 실패는 기존 문제이므로 새 작업의 성공/실패 판단에 사용하지 않음.
- 특정 파일만 검증하려면 `python3 -c "..."` 로 직접 확인.

**session_note**: "PLAN_git_commit_secret_staged_gate.md Task 1.7 검증 시 발생. `just docs-discuss-lifecycle` 가 archive 디렉토리 17개 파일의 기존 실패를 보고. 해당 파일들은 새 변경과 무관하므로 PASS 로 판단."

---

## 14. macOS 시스템 Python PATH 우선순위

### 14.1 `python3` → `/usr/bin/python3`(3.9) — 프로젝트 스크립트 ImportError

**증상**: `python3 scripts/archive_plans.py` 실행 시 `ImportError: cannot import name 'UTC' from 'datetime'`.

**원인**: macOS 시스템 Python 3.9(`/usr/bin/python3`)가 homebrew Python 3.14(`/opt/homebrew/bin/python3`)보다 PATH 우선순위가 높음. `python3` 명령어는 항상 시스템 Python 3.9을 실행. `datetime.UTC` 등 3.11+ API가 3.9에서 ImportError 발생.

**예방**:
- 프로젝트 스크립트 실행 시 **항상 `uv run python` 사용**.
- `uv run python scripts/archive_plans.py` — 프로젝트 가상환경(3.14) Python 사용.
- `python3` 명령어는 fallback 용도로만 사용 (스크립트 실행 아님).
- `which python3` 로 현재 python3 경로 확인: `/usr/bin/python3` 이면 시스템 Python.

**session_note**: "PLAN archive workflow 실행 시 발생. `python3` 로 실행 시 Python 3.9 에서 datetime.UTC ImportError. `uv run python` 으로 우회 성공."

---

## 15. MEMORY.md 편집과 memory tool 충돌

### 15.1 patch 도구로 MEMORY.md 수정 → memory tool 캐시 불일치

**증상**: `memory(action='add')` 호출 시 "Refusing to write MEMORY.md: file on disk has content that wouldn't round-trip through the memory tool" 오류.

**원인**: 호스트 부분 수정·쓰기 도구(Cursor `StrReplace`/`Write` 등)로 MEMORY.md를 직접 수정하면 memory tool 내부 캐시가 stale 해짐. memory tool 은 매 턴 시작 시 MEMORY.md 를 읽어서 캐시한 후, write 시도 시 현재 파일과 비교. 외부 편집으로 파일이 변경되면 round-trip 검증이 실패.

**예방**:
- MEMORY.md 수정 시 호스트 파일 I/O 도구 **직접 사용** — memory tool은 읽기 전용으로 간주.
- memory tool 로 새 항목 추가하려면 파일 수정 전 먼저 `memory(action='add')` 완료.
- 이미 `StrReplace` 로 수정한 후 memory tool 이 실패하면 `Write` 로 전체 재작성 후 재시도 (하지만 이 때도 실패할 수 있음 — 파일 직접 편집이 유일한 해결책).
- MEMORY.md drift 발생 시 `.bak` 파일 확인 → 내용 통합 → `Write` 로 clean 재작성.

**session_note**: "PLAN agent_secret_meta_gate.md 에 관련 명세 참조 추가 후 archive 실행. `python3` 로 실행 시 Python 3.9 ImportError → `uv run python`으로 우회. archive 완료 후 MEMORY.md patch 수정 → memory tool drift 발생."
