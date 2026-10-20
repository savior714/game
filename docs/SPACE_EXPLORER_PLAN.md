# Space Explorer 기술 참고

- **상태:** `PAUSED_REFERENCE_ONLY`
- **제품 방향 SSOT:** `docs/specs/product/ACTIVE_PRODUCT_SCOPE.md`
- **현재 다음 작업:** 없음
- **재개 조건:** 사용자가 제품 방향에서 Space Explorer 재개를 명시적으로 결정한 경우

## 1. 역할

이 문서는 Space Explorer의 기존 runtime 구조와 유지보수 경계를 보존하는 기술 참고다. 일정, 완료율, 자동 재개 조건을 소유하지 않는다.

`ACTIVE_PRODUCT_SCOPE.md`에서 Space Explorer는 현재 동결 surface다. Core Quiz reliability 단계의 종료 여부와 무관하게, 명시적 제품 방향 변경 전에는 다음을 신규 개발하지 않는다.

- 신규 행성·천체 콘텐츠
- 2D/3D 렌더링 고도화
- 추가 제스처·카메라 기능
- 외부 데이터 연동
- 레이아웃·테마·애니메이션 확장
- 구조 이전 또는 공용 엔진 추출

## 2. Runtime 위치

| 역할 | 경로 |
|---|---|
| 실험 페이지 | `experiments/space-explorer/index.html` |
| 모듈 엔트리 | `experiments/space-explorer/main.js` |
| 천체/궤도 데이터 | `experiments/space-explorer/data.js` |
| 상태 | `experiments/space-explorer/state.js` |
| 궤도·자전 계산 | `experiments/space-explorer/simulation.js` |
| 렌더링 | `experiments/space-explorer/renderer.js` |
| 셰이더/머티리얼 | `experiments/space-explorer/shaders.js` |
| 텍스처 로더 | `experiments/space-explorer/textures.js` |
| 컨트롤 | `experiments/space-explorer/controls.js` |
| 제스처 | `experiments/space-explorer/interactions.js` |
| 행성 텍스처 자산 | `experiments/space-explorer/assets/textures/` |
| three.js 번들 | `experiments/space-explorer/vendor/three/` |
| 배포 라우팅 | `vercel.json` |

루트 `/space-explorer.html`과 `experiments/space-explorer.html`은 현재 배포 entry가 아니다. 실제 코드와 `vercel.json`을 우선한다.

### 2.1 3D 텍스처 파이프라인

- 표면 텍스처는 저장소에 커밋된 실제 촬영·공개 지도(Solar System Scope CC BY 4.0, NASA Blue Marble, NASA SDO)를 쓴다.
- 지구는 day/night/normal/specular/cloud 5개 레이어를 각각 셰이더로 합성한다.
- 수성·금성·화성·달은 bump 맵을, 토성은 알파 스트립 고리 텍스처와 행성 그림자를 쓴다.
- 태양은 NASA SDO 텍스처에 절차적 플라스마 노이즈를 더한다.
- 텍스처 로딩은 진행률 UI와 대체(fallback) 텍스처를 함께 제공한다.
- three.js와 애드온은 `vendor/three/`에 고정 번들로 두며 CDN에 의존하지 않는다.

### 2.2 Dino Escape 3D (공룡 추격 탈출)

`dino-escape.html`은 태양계 페이지와 독립된 3D 추격 러너이며, 자체 스타일시트
(`dino-escape.css`)와 폰트(`assets/fonts/`)를 소유한다. 런타임 네트워크 의존성은 없다.

| 역할 | 경로 |
|---|---|
| 페이지 셸 | `experiments/space-explorer/dino-escape.html` |
| 스타일 | `experiments/space-explorer/dino-escape.css` |
| 엔트리(렌더 루프·HUD·오디오 배선) | `experiments/space-explorer/dino-escape.js` |
| 규칙·상수 | `experiments/space-explorer/dino/{constants,run-model,player,spawner,storage,util}.js` |
| 추격 연출(카메라·렉스 스테이징) | `experiments/space-explorer/dino/chase.js` |
| 3D 월드·모델·파티클 | `experiments/space-explorer/dino/{world,models,entities,particles}.js` |
| 프레임 회귀 검사 | `scripts/dino/frame-check.mjs` |

- 카메라와 렉스 위치는 `chase.js`가 단독으로 소유한다. 엔트리에 카메라 수식을 다시 넣지 않는다.
- 프레이밍 규칙을 바꾸면 `node scripts/dino/frame-check.mjs`를 실행하고,
  `tests/test_space_explorer_phase14_dino_escape_page.py`로 계약을 유지한다.
- 한국어 UI는 자체 호스팅 Pretendard를 쓰고, 아이콘은 이모지 글리프 대신 인라인 SVG를 쓴다.

## 3. 보존할 기술 경계

- 상태와 렌더링을 분리한다.
- resize, visibility, pointer/touch lifecycle은 cleanup 가능한 소유권을 가져야 한다.
- 터치 제스처는 브라우저 기본 동작과 충돌하지 않게 한다.
- pointer/touch 종료·취소에서 임시 상태를 정리한다.
- Space Explorer는 `experiments/`에 유지하며 Core Quiz/shared runtime으로 자동 승격하지 않는다.

## 4. 유지보수 예외

동결 중에도 최신 main/production에서 다음이 실제로 재현되면 해당 원인 하나를 독립 repair할 수 있다.

- 배포 entry가 열리지 않는 치명적 회귀
- 기존 사용 흐름이 완전히 막힘
- 데이터 손상
- 보안 또는 개인정보 노출

단순 page error, console error, failed request, 정적 자산 이상만으로 신규 feature 개발을 재개하지 않는다. 해당 신호가 위 치명적 문제를 직접 증명할 때만 수정 범위를 연다.

## 5. 재개 시

사용자가 재개를 명시하면 과거 checklist를 그대로 실행하지 않는다.

1. 최신 `origin/main`의 실제 entry와 module graph 확인
2. 브라우저 baseline 확인
3. 현재 code/test와 이 문서의 stable contract drift 확인
4. 첫 failure domain/제품 목표 하나만 선택
5. 직접 영향 검증 후 게시

## 6. 검증 참고

- 저장소 통합 검증: `bash ./verify.sh`
- 라우팅 계약: `tests/test_docs_routing_ssot.py`
- 현재 제품 방향: `tests/test_active_product_scope_policy.py`
- 문서 권위 분류: `tests/test_document_authority_classification.py`

이 문서는 실제 runtime 경계, 유지보수 예외 또는 Space Explorer의 active/frozen 상태가 바뀔 때만 수정한다.
