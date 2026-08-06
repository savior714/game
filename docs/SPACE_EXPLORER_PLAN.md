# Space Explorer 기술 참고

- **상태:** `PAUSED_REFERENCE_ONLY`
- **현재 실행 권위:** `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`
- **현재 다음 작업:** 없음
- **재개 조건:** 사용자가 현재 요청에서 명시적으로 방향을 변경하거나, 일반 과목 안정화 exit gate 이후 우선순위를 다시 결정한 경우
- **운영 예외:** 현재 배포를 막는 치명적 회귀, 데이터 손상, 보안 문제의 독립 수정

## 1. 이 문서의 역할

이 문서는 Space Explorer의 기존 구현 구조와 검증 경계를 설명하는 기술 참고문서다.
일정, 다음 단계, 완료율 또는 자동 재개 조건을 관리하지 않는다.
과거 단계와 체크리스트는 Git 이력에 남아 있으며 현재 작업 선택의 근거로 사용하지 않는다.

일반 과목 문제풀이 안정화가 완료되기 전에는 다음을 시작하지 않는다.

- 신규 행성·천체 콘텐츠
- 2D/3D 렌더링 고도화
- 추가 제스처나 카메라 기능
- NASA/JPL 등 외부 데이터 연동
- 레이아웃·테마·애니메이션 개선
- 구조 이전 또는 공용 엔진 추출

## 2. 현재 런타임 위치

| 역할 | 경로 |
|---|---|
| 실험 페이지 | `experiments/space-explorer/index.html` |
| 모듈 엔트리 | `experiments/space-explorer/main.js` |
| 상태 | `experiments/space-explorer/state.js` |
| 렌더링 | `experiments/space-explorer/renderer.js` |
| 컨트롤 | `experiments/space-explorer/controls.js` |
| 제스처 | `experiments/space-explorer/interactions.js` |
| 배포 라우팅 | `vercel.json` |

루트 `/space-explorer.html`과 `experiments/space-explorer.html`은 현재 배포 entry가 아니다.
실제 정적 entry와 링크는 코드와 `vercel.json`을 우선한다.

## 3. 현재 구현 개요

기존 구현은 정적 HTML/CSS/JavaScript 기반 실험 모듈이다.

- Canvas 기반 태양계 시각화
- `requestAnimationFrame` 애니메이션 루프
- 재생·일시정지·초기화
- 시간 배속과 행성 라벨 토글
- 2D/3D 표현 모드
- 반응형 캔버스 리사이즈
- visibility 전환 시 시간차 급증 방지
- 멀티터치 핀치와 회전 입력을 위한 분리된 상호작용 모듈

이 목록은 현재 동작을 자동 보증하지 않는다. 재개 시 최신 `origin/main`에서 실제 브라우저 검증으로 다시 확인한다.

## 4. 설계 경계

### 4.1 상태와 렌더링

- 상태 데이터는 렌더 함수와 분리한다.
- 렌더링은 현재 상태를 읽어 화면에 투영한다.
- 사용자 입력은 목표 상태를 변경하고 애니메이션 루프가 표시 상태를 수렴시킨다.
- resize, visibility, pointer/touch lifecycle은 종료 시 정리 가능한 소유권을 가져야 한다.

### 4.2 입력

- 터치 제스처는 브라우저 기본 스크롤·확대와 충돌하지 않아야 한다.
- pointer/touch 종료·취소 경로에서 임시 입력 상태를 정리한다.
- 키보드와 포커스 사용자가 필수 컨트롤을 사용할 수 있어야 한다.

### 4.3 실험 격리

- Space Explorer는 `experiments/`에 유지한다.
- 일반 과목 문제풀이의 공용 런타임으로 자동 승격하지 않는다.
- 검증된 중복 없이 `shared/`로 로직을 이동하지 않는다.

## 5. 유지보수 예외

동결 중에도 다음 문제는 별도 failure domain으로 수정할 수 있다.

- 운영 entry가 열리지 않음
- 현재 배포에서 페이지 오류가 발생함
- 보안 또는 개인정보 노출
- 기존 정적 자산 손상
- 다른 운영 과목 변경으로 인한 명확한 치명적 회귀

예외 수정은 신규 기능이나 구조 개선으로 확장하지 않는다.

## 6. 재개 시 사전 진단

재개가 명시적으로 승인되면 구현 전에 다음을 확인한다.

1. 실제 entry와 배포 경로
2. 페이지 로드와 정적 자산 요청 실패
3. page error와 console error
4. 재생·일시정지·초기화
5. 배속과 라벨 상태
6. resize와 visibility lifecycle
7. pointer/touch 취소와 cleanup
8. 키보드 포커스와 필수 컨트롤 접근성

진단 결과에서 첫 failure domain 하나만 선택한다.
과거 체크리스트나 문서 상태만으로 완료를 선언하지 않는다.

## 7. 검증 참고

- 저장소 통합 검증: `bash ./verify.sh`
- 라우팅 계약: `tests/test_docs_routing_ssot.py`
- 현재 제품 방향: `tests/test_core_quiz_reliability_policy.py`
- 문서 권위 분류: `tests/test_document_authority_classification.py`

실제 재개 작업에서는 변경 위험에 직접 대응하는 focused test와 브라우저 증거를 추가한다.

## 8. 변경 규칙

이 문서는 다음 경우에만 수정한다.

- 실제 entry 또는 모듈 경계가 변경됨
- 유지보수 예외의 제품 계약이 변경됨
- 사용자가 Space Explorer 재개를 명시적으로 결정함

과목별 일정, 다음 작업, 단계별 완료율을 기록하기 위해 수정하지 않는다.
