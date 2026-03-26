# 공용 코어 분리 스펙 (2026-03-27)

## 1. 목적

- 과목별 중복 구현을 제거하여 유지보수 비용과 동작 불일치 리스크를 줄인다.
- 비즈니스 규칙은 공용 코어를 SSOT로 삼고, 과목별 파일은 어댑터/위임 계층으로 유지한다.

## 2. 범위

### 2.1 `common/rocket-core.js`
- 포함:
  - 스트릭 갱신, 발사/추락/그물망 시퀀스, 로켓 UI, 파티클 연출
- 연결 방식:
  - 과목별 `rocket.js`는 `RocketCore.install(window)`만 수행

### 2.2 `common/progress-engine.js`
- 포함:
  - `emptyStats`, `loadStats`, `saveStats`
  - `getBaseDiffLevel`, `getDifficultyLevel`
- 연결 방식:
  - 과목별 `engine.js`는 도메인 키/스토리지 키/상태를 인자로 전달

### 2.3 `common/quiz-ui-core.js`
- 포함:
  - 타이머 코어: `startTimer`, `stopTimer`, `updateTimerUI`
  - 모달 코어: `openStats`, `closeStats`, `onModalBackdrop`
  - 정답 처리 코어: `evaluateStandard` (정답/오답 공통 분기, 기록, 후속 UI 노출)
  - 순차 정답 종결 코어: `finalizeSuccess`, `finalizeFailure` (순차 문제의 성공/실패 종결 공통 처리)
- 연결 방식:
  - 과목별 `ui.js`는 콜백/상태 접근자 기반으로 코어를 생성 후 위임

## 3. 비범위 (Out of Scope)

- 과목별 문제 생성 알고리즘 전체 공용화
- 영어 순차 빈칸의 단계 진행(`seqStep`, 선택지 전환) 전체 공용화
- 수학 사운드/숫자 정답 판정 공용화

## 4. 의존성 규칙

- 공용 코어는 과목 DB를 직접 참조하지 않는다.
- 과목 파일은 공용 코어를 재정의하지 않는다.
- HTML 로딩 순서는 공용 코어가 과목 파일보다 먼저 로드되어야 한다.

## 5. 검증 기준

- 정적/시뮬레이션 검증:
  - `node verify_all.js` PASS
- 공용 위임 계약 검증:
  - `node verify_shared_core_contract.js` PASS
- 그물망 연결 검증:
  - `node verify_net_logic.js` PASS
- 품질 기준:
  - lint error 0건

## 6. 단계별 후속 작업

1. `quiz-ui-core`에 정답 처리 골격(공통 분기) 추가 ✅
2. 과목별 `ui.js`를 어댑터 중심 구조로 단순화 ✅
3. 공용 코어 계약을 테스트 스크립트에 추가 검증 항목으로 확장 ✅
4. 영어 순차 빈칸(`checkSeqAnswer`)의 공용 어댑터 추출 여부를 Phase2로 검토 ✅
5. 영어 순차 빈칸의 종결 로직(`success/failure`)을 공용 코어로 추출 (Phase5) ✅
6. 영어 순차 빈칸의 단계 진행 로직(`seqStep` 전개/다음 보기 렌더)은 과목 어댑터로 유지 (Phase5 비범위)
