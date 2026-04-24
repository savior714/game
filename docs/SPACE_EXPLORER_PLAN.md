# 우주 탐험 기능 상세 실행 계획서

## 1) 목표

- 메인 페이지에 `우주 탐험` 메뉴를 신설한다.
- `우주 탐험` 메뉴 진입 시 태양계를 시각적으로 체험할 수 있는 HTML 기반 시뮬레이션(MVP)을 제공한다.
- 초기에는 "빠르게 체험 가능한 데모"에 집중하고, 이후 단계에서 데이터 정확도/3D 고도화를 확장한다.

## 2) 범위 정의

### In Scope (MVP)

- 메인 네비게이션 메뉴 추가: `우주 탐험`
- 우주 탐험 페이지 신설
- 태양 중심 + 8행성 공전 애니메이션 (단순 원궤도)
- 기본 컨트롤: 재생/일시정지, 속도 조절(0.5x, 1x, 2x, 5x), 초기화
- 행성 라벨 표시 토글

### Out of Scope (MVP 이후)

- 실제 천문 단위 기반 정밀 물리 시뮬레이션
- 고해상도 텍스처 기반 사실적 렌더링
- 복잡한 충돌/중력 계산(N-body)
- 멀티플레이어/계정 연동

## 3) 사용자 시나리오

1. 사용자가 메인 페이지를 연다.
2. 상단 메뉴에서 `우주 탐험`을 클릭한다.
3. 태양계 시뮬레이션 화면이 로드된다.
4. 사용자는 속도 조절, 일시정지, 라벨 토글을 통해 탐색한다.
5. 이후 확장 버전에서 행성 상세 정보/실시간 데이터 반영을 경험한다.

## 4) 기술 스택 전략

## 기본안 (권장, MVP)

- 렌더링: `HTML5 Canvas 2D`
- 애니메이션 루프: `requestAnimationFrame`
- UI: Vanilla HTML/CSS/JS (또는 현재 프로젝트가 채택한 최소 프레임워크)

선정 이유:

- 의존성이 적고 초기 구현 속도가 빠르다.
- 태양계 "데모 체험" 목적에는 충분한 성능과 표현력을 제공한다.
- 추후 Three.js 전환 시에도 데이터/상태 구조 재사용이 가능하다.

## 확장안 (고도화)

- 렌더링: `Three.js` (WebGL)
- 카메라 제어: Orbit Controls
- 장점: 3D 공간감, 카메라 이동, 조명/씬그래프 구조가 태양계 표현에 적합

## 데이터 소스 (추후)

- NASA/JPL Horizons API
- 사용 목적: 공전 주기, 상대 거리, 시점 기준 보정값 반영

## 5) 화면/기능 구조

### 메인 페이지

- 상단 네비게이션에 `우주 탐험` 메뉴 추가
- 기존 메뉴와 동일한 스타일/접근성 기준 준수

### 우주 탐험 페이지

- 좌측(또는 중앙): 캔버스 시뮬레이션 뷰
- 우측(또는 하단): 컨트롤 패널
  - 재생/일시정지
  - 속도 조절
  - 라벨 토글
  - 초기화

### 상태 모델 (초안)

- `isPlaying: boolean`
- `timeScale: number`
- `showLabels: boolean`
- `elapsedTime: number`
- `planets[]: { name, color, radius, orbitRadius, orbitSpeed, angle }`

## 6) 구현 단계 (작업 분해)

### Phase 0 - 프로젝트 정합성 확인

- 현재 웹 엔트리/라우팅 구조 확인
- 우주 탐험 페이지 파일 경로와 네비게이션 삽입 지점 확정

산출물 (확정):

- 현재 저장소는 웹 런타임 앱이 아닌 부트스트랩/템플릿 패키지 구조로 확인됨
  - 웹 엔트리 파일(`index.html`, `src/main.*`, `app router`) 미존재
  - 라우팅/네비게이션 구현 코드 미존재
- `우주 탐험` 기능은 본 저장소의 `templates/` 대상에 구현하는 방식으로 진행 필요
- Phase 1 착수 기준 경로를 아래처럼 확정
  - 페이지 템플릿: `templates/src/pages/space-explorer.*` (프레임워크 확정 후 확장자 결정)
  - 메뉴 삽입 지점: `templates/src/components/nav.*` 또는 `templates/src/app/layout.*`
  - 엔트리/라우터: `templates/src/main.*` 또는 `templates/src/app/router.*`

완료 판정:

- [x] 현재 웹 엔트리/라우팅 구조 확인
- [x] 우주 탐험 페이지 경로/네비게이션 삽입 지점 후보 확정

### Phase 1 - UI 뼈대

- 우주 탐험 메뉴 추가
- 신규 페이지 템플릿 생성
- 캔버스 및 컨트롤 UI 배치

산출물:

- 메뉴에서 신규 페이지 정상 진입
- 빈 캔버스 + 컨트롤 UI 렌더링

산출물 (구현 반영):

- `templates/index.html`에 `우주 탐험` 메뉴 추가
- `templates/space-explorer.html` 신규 생성
  - 캔버스(`solar-system-canvas`) 배치
  - 컨트롤 UI(재생/일시정지/초기화, 속도 선택, 라벨 토글) 배치
- `templates/styles.css`로 공통 네비게이션/레이아웃 스타일 적용

완료 판정:

- [x] 우주 탐험 메뉴 추가
- [x] 신규 페이지 템플릿 생성
- [x] 캔버스 및 컨트롤 UI 배치

### Phase 2 - 시뮬레이션 코어

- 태양/행성 렌더 함수 구현
- 공전 업데이트 로직 구현
- `requestAnimationFrame` 루프 구성
- 리사이즈 대응

산출물:

- 8행성이 태양 중심으로 공전
- 창 크기 변경 시 레이아웃/렌더 정상

산출물 (구현 반영):

- `templates/space-explorer.js` 신규 생성
  - 태양 + 8행성 렌더링 (`planets` 배열 기반)
  - 시간 경과 기반 공전 각도 업데이트
  - `requestAnimationFrame` 루프(`tick`) 구성
  - `resizeCanvas()` 기반 반응형 캔버스 리사이즈 적용
- `templates/space-explorer.html`에 스크립트 연결

완료 판정:

- [x] 태양/행성 렌더 함수 구현
- [x] 공전 업데이트 로직 구현
- [x] `requestAnimationFrame` 루프 구성
- [x] 리사이즈 대응

### Phase 3 - 상호작용

- 재생/일시정지
- 배속 변경
- 라벨 토글
- 초기화 버튼

산출물:

- 사용자 입력 기반 상태 변화 정상 반영

산출물 (구현 반영):

- `templates/space-explorer.html`
  - 컨트롤 버튼에 `data-action` 식별자 부여 (`play`, `pause`, `reset`)
  - 상태 배지(`simulation-status`) 추가
- `templates/space-explorer.js`
  - `setPlaying()`으로 재생/일시정지 상태 전환 일원화
  - `updateStatusText()`로 재생 상태/배속 UI 즉시 반영
  - `applyResetState()`로 초기화 시 시간/배속/라벨/행성 각도 초기 상태 복원
  - 라벨 토글/배속 변경 시 렌더 및 상태 텍스트 갱신

완료 판정:

- [x] 재생/일시정지
- [x] 배속 변경
- [x] 라벨 토글
- [x] 초기화 버튼
- [x] 사용자 입력 기반 상태 변화 정상 반영

### Phase 4 - 품질 개선

- 렌더 루프 최적화(불필요 계산 최소화)
- 저사양 대응(디테일 단계 조절)
- 기본 접근성 점검(버튼 라벨, 키보드 포커스)

산출물:

- 체감 성능 안정
- 기본 UX 완성도 확보

산출물 (구현 반영):

- `templates/space-explorer.html`
  - 캔버스에 `aria-describedby="simulation-status"` 연결
  - 디테일 선택 UI(`render-quality`: 높음/낮음) 추가
- `templates/space-explorer.js`
  - `setQualityLevel()` 도입으로 고품질/저품질 렌더 단계 제어
  - 저품질 모드에서 일부 궤도선/텍스트 렌더 경량화
  - 리사이즈 이벤트를 `requestAnimationFrame`으로 스로틀링
  - `visibilitychange` 처리로 백그라운드 전환 후 시간차 급증 방지
- `templates/styles.css`
  - 상태 배지/활성 버튼 스타일로 조작 피드백 강화

완료 판정:

- [x] 렌더 루프 최적화(불필요 계산 최소화)
- [x] 저사양 대응(디테일 단계 조절)
- [x] 기본 접근성 점검(버튼 라벨, 키보드 포커스)
- [x] 체감 성능 안정
- [x] 기본 UX 완성도 확보

### Phase 5 - 유지보수성 개선 (구조 분리)

- 시뮬레이션 코드를 역할별 모듈로 분리
- 엔트리포인트를 `type="module"` 기반으로 전환
- 기존 기능 동작을 보존하면서 테스트 계약 유지

산출물 (구현 반영):

- `templates/space-explorer/main.js`
  - 앱 부트스트랩, 애니메이션 루프, resize/visibility 이벤트 관리
- `templates/space-explorer/state.js`
  - 시뮬레이션 상태 및 행성 데이터 정의
- `templates/space-explorer/renderer.js`
  - 캔버스 렌더/리사이즈 책임 분리
- `templates/space-explorer/controls.js`
  - 컨트롤 이벤트 및 상태 동기화 로직 분리
- `templates/space-explorer.html`
  - `<script type="module" src="./space-explorer/main.js"></script>`로 전환

완료 판정:

- [x] 시뮬레이션 코드 모듈 분리
- [x] 모듈 엔트리포인트 전환
- [x] 기존 상호작용/품질 기능 회귀 없음

## 7) 검증 체크리스트

- [x] 메인 메뉴에 `우주 탐험`이 표시된다.
- [x] 클릭 시 우주 탐험 페이지로 이동한다.
- [ ] 태양 및 8행성이 렌더링된다.
- [x] 태양 및 8행성이 렌더링된다.
- [x] 재생/일시정지 동작이 정상이다.
- [x] 속도 조절이 즉시 반영된다.
- [x] 라벨 토글이 정상 동작한다.
- [x] 창 크기 변경 시 캔버스가 깨지지 않는다.
- [x] 콘솔 오류가 없다.

## 8) 리스크 및 대응

- 라우팅 구조 부재 또는 미정
  - 대응: 최소 단일 HTML 엔트리 + 메뉴 앵커 방식으로 MVP 선진입
- 브라우저/디바이스 성능 편차
  - 대응: 렌더 디테일 옵션과 기본값 보수적 설정
- 사실성 요구 증가
  - 대응: 데이터 계층 분리(렌더와 물리 상수 분리)로 단계적 고도화

## 9) 일정 예시

- Day 1: 정보구조 확정 + 메뉴/페이지 뼈대
- Day 2: 캔버스 공전 MVP 완성
- Day 3: 상호작용 + 품질/반응형 보완
- Day 4: 리뷰 및 다음 단계(Three.js 전환 여부) 결정

## 10) 다음 실행 항목

1. 현재 프로젝트의 웹 엔트리 파일(또는 앱 라우터) 위치를 확정한다.
2. `우주 탐험` 메뉴와 페이지 스캐폴딩을 구현한다.
3. Canvas 기반 태양계 시뮬레이션 MVP를 연결한다.
4. 체크리스트 기준으로 1차 검증한다.
