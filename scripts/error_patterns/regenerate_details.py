#!/usr/bin/env python3
"""error_patterns detail/*.md 전체를 선제 지침 형식(B)으로 재생성."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.error_patterns.detail_template import (  # noqa: E402
    DETAIL_INTRO_DEFAULT,
    DETAIL_INTRO_EDITING,
    DETAIL_INTRO_TOOLS,
    render_detail_file,
)

DETAIL_DIR = REPO_ROOT / ".agents" / "core" / "error_patterns" / "detail"

FILES: dict[str, str] = {}


def _p(
    pid: str,
    title: str,
    situation: str,
    avoid: str,
    instead: str,
    mnemonic: str,
    reference: str | None = None,
) -> tuple:
    return (pid, title, situation, avoid, instead, mnemonic, reference)


def build_files() -> dict[str, str]:
    editing = render_detail_file(
        DETAIL_INTRO_EDITING,
        [
            (
                "1. 파일 편집 실수",
                [
                    _p(
                        "1.1",
                        "Read → Write 직행 (가장 흔함)",
                        "파일 일부만 고치려는데, 읽기 도구 출력 전체를 쓰기 도구에 그대로 넣음.",
                        "Read/read_file 출력(줄 번호 포함)을 Write/write_file 본문으로 사용.",
                        "부분 수정은 호스트 부분 수정 도구(StrReplace/edit/replace_file_content). 전체 교체 시 줄 번호 제거한 디스크 본문만 쓰기 도구로.",
                        "읽기 출력 ≠ 파일 내용 — 줄 번호는 절대 파일에 쓰지 않는다.",
                        "❌ Read → `    111|const x = 1` 그대로 Write\n✅ StrReplace(old_string=`const x = 1`, ...)",
                    ),
                    _p(
                        "1.2",
                        "StrReplace old_string uniqueness 검증 안 함",
                        "부분 수정 시 같은 문장이 파일 여러 곳에 있는데 확인 없이 StrReplace 호출.",
                        "등장 횟수 확인 없이 patch · 실패 후 replace_all로 덮어쓰기.",
                        "patch 전 대상 문자열이 **정확히 1번**인지 확인. 여러 번이면 범위를 넓히거나 Write로 전체 재작성.",
                        "한 번만 나올 때만 부분 수정 — 아니면 전략을 바꾼다.",
                        "❌ `Found 4 matches` 반복\n✅ count==1 확인 후 patch, 아니면 Write",
                    ),
                    _p(
                        "1.3",
                        "StrReplace 실패 후 같은 old_string으로 재시도",
                        "patch가 실패한 뒤(외부 스크립트가 파일을 바꿨을 때 등) 같은 old_string으로 재시도.",
                        "실패 후 재읽기 없이 동일 old_string·동일 전략 반복 (메타 금지 3).",
                        "실패 즉시 Read로 최신본 확인 → placeholder가 이미 채워졌으면 patch 생략.",
                        "실패 = 파일이 바뀌었을 수 있다 — 먼저 다시 읽는다.",
                        "❌ `Could not find a match` × N\n✅ Read → 현재 상태 확인 → 필요할 때만 patch",
                    ),
                    _p(
                        "1.4",
                        "JSX/TSX StrReplace 누적으로 구조 망가짐",
                        "JSX/TSX에서 StrReplace를 연속 적용하다 closing tag 순서가 깨짐.",
                        "같은 파일에서 patch를 2회 이상 실패한 뒤에도 부분 수정만 반복 (메타 금지 4).",
                        "2회 연속 실패 시 Read 후 Write/write_file로 해당 컴포넌트 블록 전체 재작성.",
                        "JSX는 부분 patch 연타 금지 — 두 번 틀리면 통째로 다시 쓴다.",
                        "❌ 실패한 patch 뒤 sibling patch → 태그 꼬임\n✅ Read → Write(fullContent)",
                    ),
                    _p(
                        "1.5",
                        "레거시 regex replace newline corruption (역사 사례)",
                        "구 MCP regex mode로 여러 줄을 치환하면 literal `\\n`이 파일에 기록됨.",
                        "레거시 `replace_content(mode='regex')`로 multi-line 치환.",
                        "현재 SSOT: `StrReplace` / `desktop-commander_edit_block` — 리터럴 old_string만.",
                        "regex multi-line 치환은 쓰지 않는다 — 리터럴 patch만.",
                        "❌ regex repl=`const {\\n ...}`\n✅ edit_block(old_str=실제 파일 텍스트, ...)",
                    ),
                    _p(
                        "1.6",
                        "old_string 누락으로 SchemaError (신규 vs 부분 수정 혼동)",
                        "SchemaError(Missing old_string) 또는 레거시 `edit`/`oldString` 호출.",
                        "신규 파일에 StrReplace · 부분 수정에 old_string 없이 호출 · 레거시 도구명 사용.",
                        "[runtime_edit_tools.md §1](../../runtime_edit_tools.md) 분기: 신규=쓰기 도구, 부분=old/target 필수. Cursor=routing §1.1.",
                        "신규는 쓰기·수정은 부분 수정 — 도구·키는 세션 SSOT(runtime_edit_tools).",
                        "❌ StrReplace(new_string만) / edit(oldString)\n✅ Write(신규) · StrReplace(old_string+new_string)",
                    ),
                ],
            ),
            (
                "7. 파일·git 복구 실수",
                [
                    _p(
                        "7.1",
                        "Write/write_file로 justfile 등 추적되지 않은 파일 덮어쓰기",
                        "git 미추적 파일(justfile 등)을 Write로 '수정'하다 전체 내용이 사라짐.",
                        "Read 없이 Write로 큰 설정 파일 덮어쓰기.",
                        "부분 수정은 StrReplace. Write 시 Read로 전체 본문 확보 후 append/replace.",
                        "Write = 전체 교체 — 먼저 읽고, 복구 불가 파일은 더 조심.",
                        "❌ Write(justfile, 10줄) → 1165줄 소실\n✅ Read → StrReplace 또는 Read 본문+추가",
                    ),
                    _p(
                        "7.2",
                        "git checkout으로 추적되지 않은 파일 복구 시도",
                        "`git checkout -- file`이 untracked 파일에 실패.",
                        "git 추적 여부 확인 없이 checkout으로 복구 시도.",
                        "`git status`로 tracked/untracked 확인. untracked면 stash/reflog/백업·수동 복구.",
                        "checkout은 git이 아는 파일만 되돌린다.",
                        "❌ `pathspec did not match`\n✅ git status → untracked면 다른 복구 경로",
                    ),
                    _p(
                        "7.3",
                        "archive_plans.py — DISCUSS 종속 아카이브 시 plans-index broken reference",
                        "PLAN 아카이브 후 `just plans-index`가 broken reference를 보고.",
                        "DISCUSS 본문의 plan 참조가 단순 텍스트(`PLAN_xxx.md`)로 남아 있음 — 아카이브 실패로 오인.",
                        "아카이브 자체는 성공일 수 있음. DISCUSS 참조를 상대 링크로 수정하거나 미발행 주석. `archive.md` 절차 따름.",
                        "plans-index 경고 ≠ 아카이브 실패 — 참조 링크 형식을 고친다.",
                        "증상: `누락된 플랜 파일을 가리키는 참조` — DISCUSS 내 `PLAN_xxx.md` 텍스트 참조",
                    ),
                ],
            ),
            (
                "3. React 실수",
                [
                    _p(
                        "3.1",
                        "useEffect 내 setTimeout/debounce unmount 누락",
                        "페이지 이탈 후에도 timer/debounce가 실행됨.",
                        "useEffect에서 timer 설정 후 cleanup(return clear) 생략.",
                        "return () => clearTimeout(timer) / debounce.cancel 추가.",
                        "effect에 timer를 넣으면 unmount에서 반드시 끈다.",
                        "❌ setTimeout만\n✅ return () => clearTimeout(timer)",
                    ),
                    _p(
                        "3.2",
                        "Fast Refresh full reload after session expiry",
                        "세션 만료 시 매 mount마다 redirect → full reload.",
                        "isAuthenticated 변화마다 무조건 redirect.",
                        "useRef로 이전 auth 추적 — **true→false** 전환 때만 redirect.",
                        "로그아웃 전환 한 번만 redirect — mount마다 X.",
                        "❌ `if (!isAuthenticated) redirect()`\n✅ prevAuth ref로 전환 감지",
                    ),
                ],
            ),
        ],
    )

    testing = render_detail_file(
        DETAIL_INTRO_DEFAULT,
        [
            (
                "2. 테스트 실수",
                [
                    _p(
                        "2.1",
                        "Vitest mock 누락",
                        "vi.mock 후 `No 'X' export is defined on the 'Y' mock` 에러.",
                        "컴포넌트가 import하는 export 중 일부만 mock에 포함.",
                        "mock factory에 **사용처가 import하는 모든 export** 포함.",
                        "mock = import 목록과 1:1 — 하나라도 빠지면 실패.",
                        "❌ useTabActions만 mock, ensureConsultationTabPresets 누락\n✅ import 전부 vi.fn()으로 포함",
                    ),
                    _p(
                        "2.2",
                        "Vitest localStorage persistent state",
                        "테스트 A의 localStorage 값이 테스트 B에 남음.",
                        "beforeEach에서 localStorage·공유 저장소 초기화 생략.",
                        "SettingsProvider 등 storage 사용 테스트는 beforeEach에서 명시적 초기값 설정.",
                        "테스트마다 저장소를 깨끗이 — 이전 테스트 찌꺼기 금지.",
                        "❌ singleDeskMode: true가 다음 테스트에 잔존\n✅ beforeEach → localStorage.setItem(초기값)",
                    ),
                    _p(
                        "2.3",
                        "Duplicate testId → getAllByTestId",
                        "`getByTestId`가 duplicate test id 에러.",
                        "동일 data-testid가 여러 요소에 있을 때 getByTestId 사용.",
                        "getAllByTestId + expect(length) 또는 testid를 유일하게.",
                        "같은 testid가 여러 개면 getAllByTestId.",
                        "❌ getByTestId('item') → multiple elements\n✅ getAllByTestId + length 검증",
                    ),
                    _p(
                        "2.4",
                        "React destructuring default 값 누락",
                        "mock이 undefined 반환 시 `.map()` 등에서 TypeError.",
                        "destructuring default 없이 optional 필드 사용.",
                        "`const { prescription = [] } = examination` 등 safe default.",
                        "undefined일 수 있는 필드는 default를 준다.",
                        "❌ `prescription.map` (prescription undefined)\n✅ `prescription = []`",
                    ),
                    _p(
                        "2.5",
                        "Vitest split 파일 네이밍 패턴 불일치 (.1/.2/.3)",
                        "`.test.1.ts` 파일이 vitest include에 매칭되지 않아 0 tests.",
                        "`.test.1.ts` / `.test.2.ts` 네이밍.",
                        "`<name>.<category>.test.ts` 패턴 사용 — vitest config include 먼저 확인.",
                        "split 파일 이름은 include 패턴과 맞춘다.",
                        "❌ `dashboard.test.1.ts`\n✅ `dashboard.sanitize.test.ts`",
                    ),
                    _p(
                        "2.6",
                        "vi.mock() 별도 파일 분리 시 hoisting 실패",
                        "utils 파일의 vi.mock이 hoisting되지 않아 AuthProvider 에러.",
                        "vi.mock을 import-only utils 파일에 두고 테스트 파일에서 import.",
                        "vi.mock은 **각 테스트 파일 top-level inline**. utils에는 데이터·헬퍼만.",
                        "mock은 파일마다 inline — utils 분리 금지.",
                        "❌ test-utils.tsx에 vi.mock → import\n✅ 각 *.test.tsx에 vi.mock inline",
                    ),
                    _p(
                        "2.7",
                        "beforeEach/cleanup 누락 → 테스트 간 상태 오염",
                        "테스트 A의 mock/spy/fake timers가 테스트 B에 영향.",
                        "beforeEach만 있고 afterEach cleanup 없음.",
                        "vi.useFakeTimers/spyOn/localStorage 변경은 afterEach에서 정리.",
                        "상태 변경 설정마다 cleanup — 이전 테스트 찌꺼기 금지.",
                        "❌ useFakeTimers만\n✅ afterEach → useRealTimers + clearAllMocks",
                    ),
                    _p(
                        "2.8",
                        "vi.mock() 동적 import vs 정적 hoisting",
                        "vi.mock이 적용 안 되거나 default export mock 불일치.",
                        "ESM default export·동적 import에 hoisting 규칙 미적용.",
                        "default mock에 `__esModule: true` · Promise는 mockResolvedValue · virtual 옵션 검토.",
                        "hoisting은 정적 import만 — default/동적은 패턴 맞춤.",
                        "❌ default mock shape 불일치\n✅ __esModule + default 또는 mockResolvedValue",
                    ),
                ],
            ),
        ],
    )

    tools = render_detail_file(
        DETAIL_INTRO_TOOLS,
        [
            (
                "4. 도구 사용 실수",
                [
                    _p(
                        "4.1",
                        "Write/write_file 부패 (os.getenv corruption / Read 라인 번호 아티팩트)",
                        "Write로 긴 문자열이 잘리거나, Read 줄 번호가 old_string에 들어감.",
                        "Write로 민감·긴 literal 전체 교체 · Read 출력(`560|`)을 old_string에 포함.",
                        "부분 수정은 StrReplace. old_string은 줄 번호 없는 디스크 본문에서 추출.",
                        "Write는 truncation·아티팩트 위험 — patch 우선, 줄 번호는 old_string에 넣지 않는다.",
                        "❌ Write(os.getenv...) 잘림 / old_string=`560|const x`\n✅ StrReplace + 디스크 snippet",
                    ),
                    _p(
                        "4.2",
                        "Biome auto-fix (--auto-fix)로 import 이름 변경",
                        "`frontend_biome_gate.sh --auto-fix` 후 TS import 이름 불일치.",
                        "gate 스크립트에 --auto-fix 사용.",
                        "단일 파일 format: `pnpm exec biome format --write <file>`. baseline은 --update-baseline.",
                        "auto-fix는 import를 바꿀 수 있다 — format만 쓴다.",
                        "❌ --auto-fix → useLayoutPresetStore→useLayoutPreset\n✅ biome format --write 단일 파일",
                    ),
                    _p(
                        "4.3",
                        "read_file 라인 번호 patch old_string 오사용",
                        "read_file/Read 출력의 `NNN|` 접두사를 old_string에 넣어 patch 실패 또는 파일 오염.",
                        "도구 출력 그대로를 old_string으로 사용.",
                        "old_string은 **파일 본문만** — 숫자+| 접두사 제거. [editing §1.1](editing.md)과 동일 원칙.",
                        "줄 번호는 화면용 — patch 대상이 아니다.",
                        "❌ old_string=`    560|const x = 1`\n✅ old_string=`const x = 1`",
                    ),
                    _p(
                        "4.4",
                        "MCP 도구명 underscore/hyphen 불일치",
                        "`desktop_commander_read_text_file` 등 unavailable tool 에러.",
                        "underscore·`_text_` variant·추측 도구명 호출.",
                        "세션 `mcps/<server>/tools/*.json` 또는 `just mcp-tools-validate`로 정확한 이름 확인.",
                        "MCP 이름은 추측 금지 — 디스크립터 SSOT.",
                        "❌ desktop_commander_read_text_file\n✅ desktop-commander_read_file",
                    ),
                    _p(
                        "4.5",
                        "레거시 별칭 호출 + old_string 누락 (SchemaError)",
                        "`read_file` unavailable · SchemaError(Missing old_string).",
                        "레거시 read_file/edit/oldString · StrReplace에 old_string 없음 · 신규 파일에 StrReplace.",
                        "Cursor: Read+StrReplace. MCP: desktop-commander_*. 신규=Write. [routing.md §1.1](../../routing.md).",
                        "별칭·레거시 도구명 쓰지 않는다 — 세션 도구표를 따른다.",
                        "❌ read_file / edit(oldString) / StrReplace(new만)\n✅ Read · StrReplace(old+new) · Write(신규)",
                    ),
                ],
            ),
        ],
    )

    blueprint = render_detail_file(
        DETAIL_INTRO_DEFAULT,
        [
            (
                "5. 계획서 (Blueprint) 실수",
                [
                    _p(
                        "5.1",
                        "plan-lint 통과 전 구현 착수",
                        "Blueprint 검사(plan-lint) 전에 코드를 수정하기 시작함.",
                        "메타 금지 5 — 게이트 PASS 전 구현.",
                        "`just plan-lint` PASS 후 착수.",
                        "검사 통과 전에는 손대지 않는다.",
                    ),
                    _p(
                        "5.2",
                        "Task 상태 역방향 리셋 (done → todo)",
                        "완료 Task를 todo로 되돌려 plan-lint·의존성 깨짐.",
                        "StrReplace로 Status: done → todo.",
                        "되돌리기는 `just plan-reset-gate` — 승인·검증 경로만.",
                        "done Task는 직접 리셋하지 않는다.",
                        "❌ StrReplace Status done→todo\n✅ just plan-reset-gate",
                    ),
                    _p(
                        "5.3",
                        "Verify에 grep/echo 단독 사용",
                        "Verify가 runner 없이 grep/echo만 있어 plan-lint FAIL.",
                        "Verify에 `grep`/`echo` 단독 기재.",
                        "Verify는 `just`/`pytest`/`uv run`/`pnpm run`/`python3` runner 1개.",
                        "Verify = 실행 가능한 검증 명령 — grep만으로 끝내지 않는다.",
                        "❌ Verify: grep ...\n✅ Verify: just lint-be",
                    ),
                    _p(
                        "5.4",
                        "plan-preread 누락으로 Task-level Pre-read FAIL",
                        "Blueprint 저장 후 Task-level Pre-read missing 연쇄 FAIL.",
                        "plan-preread 없이 plan-lint만 실행.",
                        "`just plan-preread docs/plans/<file>.md --write` → plan-lint 순서 고정.",
                        "Blueprint 저장 후 preread → lint.",
                        "❌ Write PLAN → plan-lint\n✅ plan-preread --write → plan-lint",
                    ),
                    _p(
                        "5.5",
                        "todo/running Conclusion에 임의 문구 사용",
                        "미완료 Task에 완료형 Conclusion → plan-lint FAIL.",
                        "Status todo/running인데 «구현 완료»·`[PASS]` 등 작성.",
                        "미완료는 CSF 슬롯 `[판정 — 비개발자용 요약. 검증 결과]` 유지.",
                        "끝나기 전 Task에는 결과 문장을 미리 쓰지 않는다.",
                        "❌ Status: todo + Conclusion: 구현 완료\n✅ CSF 슬롯 placeholder",
                    ),
                    _p(
                        "5.6",
                        "plan-lint WARN을 통과로 오인하고 Blueprint 미수정",
                        "exit 0이어도 stdout [WARN]이 있으면 계약 위반인데 구현 진행.",
                        "exit code만 보고 WARN 무시 · atomicity·Verify runner 경고 방치.",
                        "stdout 전체 스캔 — [WARN]/[FAIL] 있으면 Blueprint 수정 후 재lint. Goal conjunction → Task 분할.",
                        "plan-lint = stdout까지 PASS — WARN도 멈춤.",
                        "❌ exit 0 + [WARN] atomicity → 구현 착수\n✅ WARN 수정 → 재 plan-lint → PASS 후 착수",
                    ),
                ],
            ),
        ],
    )

    workflow = render_detail_file(
        DETAIL_INTRO_DEFAULT,
        [
            (
                "6. 기타 실수",
                [
                    _p(
                        "6.1",
                        "mermaid/긴 표/로드맵 금지 (discuss 워크플로)",
                        "discuss 세션에서 mermaid·긴 표·로드맵 출력.",
                        "discuss SKILL §철칙 위반 — 불릿 A/B만.",
                        "규칙 SSOT: [discuss/SKILL.md](../../../skills/discuss/SKILL.md).",
                        "discuss = 짧은 불릿 — 다이어그램·표 금지.",
                    ),
                    _p(
                        "6.2",
                        "AskQuestion/`question`(병용) 없이 close 종료",
                        "discuss·plan 종료 시 선택 메뉴 없이 «정리 완료»로 턴 종료.",
                        "AskQuestion/`question` 병용 생략.",
                        "close 전 표준 메뉴 A/B — discuss SKILL §close.",
                        "끝날 때는 반드시 선택지.",
                    ),
                    _p(
                        "6.3",
                        "MEMORY.md에 임시 정보 저장",
                        "MEMORY.md에 PR 번호·Phase 완료·커밋 해시 등 임시 로그 기록.",
                        "MEMORY.md를 작업 로그로 사용.",
                        "장기 규칙만 MEMORY — 임시는 session_search·Blueprint·커밋 메시지.",
                        "MEMORY = 장기 기억, 오늘 할 일 장부 아님.",
                        "❌ «PR #123 제출»\n✅ session_search(query=...)",
                    ),
                    _p(
                        "6.4",
                        "converge «계획으로» 직후 Blueprint 재질문 (이중 handoff)",
                        "«계획으로» 선택 직후 Blueprint AskQuestion을 또 띄움.",
                        "same-session plan 직행 후 메뉴 A 재노출.",
                        "plan-lint 후 메뉴 B만 — discuss SKILL §턴 판별.",
                        "«계획» 선택 = Blueprint 재질문 금지.",
                    ),
                    _p(
                        "6.5",
                        "direction·polish 턴에서 Blueprint·메뉴 A 조기 권장",
                        "close 트리거 없이 «Blueprint (권장)»·direction-set 갱신.",
                        "§3 갱신 = close 착각 · Anti-rush 무시.",
                        "direction 턴: discussing 유지, Blueprint 언급 없음. close 트리거에서만 메뉴 A.",
                        "방향 턴 ≠ 계획 턴 — Blueprint는 close 때만.",
                        "❌ §3 채움 → Blueprint (권장)\n✅ direction: 다음 분기 AskQuestion (Blueprint 없음)",
                    ),
                    _p(
                        "6.6",
                        "Workaround(우회책) 사용 후 근본 원인 및 대안 보고 누락",
                        "우회 처리 후 «완료»만 보고하고 종료.",
                        "principles.md Workaround Accountability 생략.",
                        "종료 전: 문제·우회·추정 원인·향후 대안을 AskQuestion으로 보고.",
                        "우회는 끝이 아니다 — 왜 우회했는지 남긴다.",
                        "❌ «B로 우회했습니다. 다음?»\n✅ 우회 내용 + root cause + future resolution",
                    ),
                    _p(
                        "6.7",
                        "AskQuestion(`question` 병용) 스킵 후 텍스트 답 무시·무한 재질문",
                        "사용자가 채팅으로 B를 답했는데 Questions skipped만 보고 동일 카드 반복.",
                        "스킵 = 무응답으로만 처리 · route 맥락으로 (권장) 확정.",
                        "스킵 + «B» → pending_ask 매핑 → [확정]. 모호하면 2지 확인 1회. discuss SKILL §채팅 텍스트 답변.",
                        "채팅 답 = 선택 — 스킵이어도 텍스트를 읽는다.",
                        "❌ 스킵 → 동일 AskQuestion 반복\n✅ «B» → 옵션 b 매핑 → 다음 분기",
                    ),
                ],
            ),
            (
                "16. 프롬프트 라우팅 실패",
                [
                    _p(
                        "16.1",
                        "워크플로 실행 요청 시 파일 Read 누락 → 동일 도구 무한 반복",
                        "«~ workflow 돌려줘» 요청 시 SKILL/workflow md Read 없이 추측 호출 → 동일 도구 반복.",
                        "워크플로 Read 생략 · 동일 도구 3회+ 반복 (TOP 7).",
                        "`.agents/workflows/<name>.md` 또는 `.agents/skills/<name>/SKILL.md` 1회 Read → 단계 실행. 3회 반복 시 중단.",
                        "슬래시·workflow = 먼저 해당 md를 읽는다.",
                        "❌ 추측 Shell 반복\n✅ Read workflow → 단계별 실행",
                    ),
                    _p(
                        "16.2",
                        "텍스트 툴 마커 오용 → 호스트 파싱 실패·턴 정지",
                        "content/reasoning에 [TOOL_REQUEST]·<tool_call>·pseudo JSON 출력 → 실행 0건.",
                        "텍스트로 tool syntax 출력 — native structured tool API 미사용.",
                        "호스트가 제공하는 native tool call만. 불가 시 principles §1.1 markdown A/B/C fallback.",
                        "도구는 말로 부르지 않는다 — structured call만.",
                        "❌ `[TOOL_REQUEST]{...}`\n✅ native Read/Shell/AskQuestion tool call",
                    ),
                ],
            ),
        ],
    )

    return {
        "editing.md": editing,
        "testing.md": testing,
        "tools.md": tools,
        "blueprint.md": blueprint,
        "workflow.md": workflow,
    }


def main() -> int:
    DETAIL_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in build_files().items():
        path = DETAIL_DIR / name
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
