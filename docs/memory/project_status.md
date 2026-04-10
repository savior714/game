# Memory Type: project

**현재 프로젝트는 어린이 학습 게임 플랫폼이며, SDD 기반 문서-구현 정합성을 핵심 운영 원칙으로 사용한다.**

## 현재 상태

- 과목(국어/수학/영어/과학) + 보상 소비형 마블 게임이 구현되어 있다.
- 공용 코어(`common/*`)와 전역 로직(`global/*`) 분리 구조를 유지한다.
- Supabase 기반 인증/동기화, 보호자/관리자 화면이 포함되어 있다.
- (2026-04) `common/rocket-core.js`: 엔진 `const`만 있을 때 `window.LAUNCH_STREAK`가 비어 연속 정답 UI·발사가 깨지던 문제를 `install` 기본값과 `getStreakConfig()` 정규화로 수정했다.
- (2026-04) 에이전트 Git 워크플로우는 `.agents/workflows/git.md`를 SSOT로 사용한다(구 `git-commit-push.md` 대체).
- (2026-04) `global/reward.js`에서 보상 숫자 필드(`gems`/`youtube_minutes`/`snacks`/`marble_plays`)를 로드 시 정규화하고 `add()` 누적을 안전 수치 연산으로 고정해 보석 누적 불안정 이슈를 완화했다.
- (2026-04) `tools/verify_reward_logic.js` 경로 해석을 루트 기준으로 수정하고 Node 환경 `alert` mock을 추가해 보상 검증 스크립트가 통합 검증에 포함 가능하도록 복구했다.

## 최근 문서 정비

- `PROJECT_RULES.md` 신규 생성 완료
- 메모리 체계를 `docs/memory/` 타입 분리 방식으로 정렬 시작
- 전 과목(수학/영어/국어/과학) 적응형 난이도 기준을 `MIN_DATA=3`, `up/down=0.85/0.75`로 통일 적용
- 공통 숙련도 기준 변경을 `specs/platform.md`와 `specs/math.md`에 반영 완료
- 전 과목 로켓 그물망(Net Shield) 보호 로직 정합성 확보: `var` 선언으로 스크립트 간 상태 공유 해결 및 중간값 낙하 공식 적용 완료 (`docs/CRITICAL_LOGIC.md` §7 반영)

## Phase 4 완료 (리팩토링)

- 타 과목 단어 DB 외부 분리 (`korean/data/words.json`, `science/data/questions.json`)
- 동적 로더 패턴 (`words.js`, `getDB()`) 적용
- 전 과목 `askQuestion()`에 try/catch 에러 바운더리 적용
- `common/base.css` 통합 + 과목별 `base.css`를 CSS 변수 래퍼로 축소
- `ProgressEngine.createStatsKey()` 헬퍼로 localStorage 키 네임스페이스 통일

## Phase 5.1 완료 (TypeScript 타입 정의)

- `tsconfig.json` 최적화 (`lib: ["ES2020", "DOM"]`, 검증/테스트 파일 제외)
- 공통 모듈 JSDoc 타입 정의: `progress-engine.js`, `rocket-core.js`, `quiz-ui-core.js`
- 과목별 engine.js JSDoc 타입 정의: `english`, `korean`, `math`, `science`
- `npm run typecheck` (`tsc --noEmit`) 파이프라인 구축
- `/git` 워크플로우: `.agents/workflows/git.md` (구 `git-commit-push.md`)

## 진행 제약

- 규칙 문서와 결정 문서의 SSOT 경계를 중복 없이 유지해야 한다.
- 검증 스크립트 실패 상태에서는 후속 병합을 진행하지 않는다.
