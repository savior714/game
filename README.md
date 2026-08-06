# 🎮 어린이 학습 게임 놀이터 (AidenGame)

아이들의 성취감과 자기주도 학습을 최우선으로 하는 적응형 학습 게임 플랫폼입니다.  
현재 런타임은 루트 기반 정적 HTML/CSS/JavaScript 구조로 운영됩니다.

## 🚀 핵심 기능

- **4대 과목**: 국어, 수학, 영어, 과학 학습 게임 제공
- **적응형 난이도**: 실력 변화에 따라 문제 난이도 자동 조정
- **보상 루프**: 연속 정답 기반 로켓/보석 보상과 보호자 상점 연동
- **공용 코어**: 과목별 엔진이 공통 로직(`shared/`)을 재사용
- **실험 모듈**: Space Explorer와 Ocean Rescue의 별도 런타임·도구 경계 유지

## 🎯 현재 개발 초점

현재는 신규 기능·콘텐츠·게임성 확장보다 **국어·수학·영어·과학 문제풀이의 신뢰성 안정화**를 우선합니다.

- 네 과목에 동일한 브라우저 진단을 적용해 현재 실패 또는 검증 공백이 가장 큰 과목부터 처리합니다.
- 각 과목은 상태 계약과 실제 브라우저 흐름을 모두 통과해야 완료됩니다.
- 첫 과목은 기존 구조 안에서 안정화하고, 두 번째 과목에서 반복이 확인된 경우에만 공용 로직을 추출합니다.
- 과목 하나가 완료될 때마다 `origin/main`에 게시한 뒤 다음 과목으로 이동합니다.
- 이 단계가 끝날 때까지 Ocean Rescue와 실험 기능의 신규 개발·구조 이전은 중단합니다. 치명적 회귀·데이터 손상·보안 문제만 별도 예외입니다.

현재 제품·검증 계약: [`docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`](docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md)  
문서 권위와 동결 상태 색인: [`docs/README.md`](docs/README.md)

## 🧭 현재 엔트리/라우팅 (SSOT)

- 메인 허브: `index.html`
- 보호자 관리: `domains/reward/guardian/index.html`
- 우주 탐험 페이지: `experiments/space-explorer/index.html`
- 우주 탐험 모듈 엔트리: `experiments/space-explorer/main.js`
- 배포 라우팅 설정: `vercel.json`
  - 별도 rewrite 없이 정적 파일 경로를 그대로 제공
  - 루트 허브 링크: `/experiments/space-explorer/index.html`

### 운영 / 실험 / 레거시 경로 구분표

| 구분 | 경로 | 상태 | 용도 |
| --- | --- | --- | --- |
| 메인 운영 엔트리 | `index.html` | 운영중 | 과목 선택 허브 및 공용 진입점 |
| 과목별 페이지 | `domains/{math,english,korean,science}/index.html` | 운영중·현재 우선 | 학습 루프 본편 |
| 보호자 관리 페이지 | `domains/reward/guardian/index.html` | 운영중 | 난이도, 주간 영단어, 보상 상점 및 성장 요약 관리 |
| 우주 탐험 실험 페이지 | `experiments/space-explorer/index.html` | 운영중·개발 동결 | 2D/3D 우주 시뮬레이션 및 터치 제스처 실험 |
| Ocean Rescue standalone | `ocean-rescue/index.html` | 운영중·마이그레이션 동결 | 생성된 production artifact |
| 과거 보호자/관리 alias | `guardian/index.html`, `admin/index.html` | 없음 | rewrite가 없으므로 사용하지 않음 |
| 과거 우주 탐험 alias | `/space-explorer.html`, `experiments/space-explorer.html` | 없음 | `vercel.json` rewrite가 없으므로 사용하지 않음 |

## 🛠️ 로컬 개발

- 메인 런타임은 정적 템플릿 파일을 기준으로 동작합니다.
- 프로젝트 검증은 루트 `verify.sh`를 사용합니다.

```bash
bash ./verify.sh
```

## 🎮 Ocean Rescue toolchain 참고 — 현재 개발 동결

아래 명령과 구조는 **현재 작업 목록이 아니라 유지보수·치명적 회귀 대응을 위한 기술 참고**입니다.
일반 과목 안정화 중에는 사용자가 명시적으로 Ocean Rescue를 재개하거나 허용 예외가 재현된 경우에만 사용합니다.

- **Package boundary:** `domains/ocean-rescue`
- **Node pin:** `domains/ocean-rescue/.node-version`
- **Project pnpm:** `packageManager` + `corepack pnpm`
- **Sync:** `just sync-ocean-rescue-node`
- **Toolchain check:** `just check-ocean-rescue-toolchain`
- **Typecheck:** `just typecheck-ocean-rescue`
- **Development server:** `just dev-ocean-rescue`
- **Production build:** `just build-ocean-rescue`
- **Artifact drift:** `just check-ocean-rescue-drift`
- **Operational rollback:** `just rollback-ocean-rescue-to-legacy`
- **Rollback verification:** `just check-ocean-rescue-rollback`

제약:

- Node는 Ocean Rescue build-time 전용입니다. 전체 browser runtime은 Node를 요구하지 않습니다.
- `ocean-rescue/index.html`은 source가 아니라 production build pipeline이 생성하는 artifact입니다.
- legacy ordered-script 경로는 rollback/proof 목적이며 production ESM 경로와 역할이 다릅니다.
- 과거 WP 번호나 계획 상태는 현재 실행 순서를 정하지 않습니다.
- 기술 기준선은 [`docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md`](docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md)에 동결 참고문서로 정리돼 있습니다.

## ✅ 검증 체계

- 테스트: `tests/`
- 통합 검증: `verify.sh`
- 현재 실행 규약: `AGENTS.md`
- 현재 제품 정책: `PROJECT_RULES.md`
- 현재 일반 과목 안정화 계약: `docs/specs/product/CORE_QUIZ_RELIABILITY_STABILIZATION.md`
- 문서 권위 색인: `docs/README.md`
- 동결 참고:
  - `docs/SPACE_EXPLORER_PLAN.md`
  - `docs/plans/PLAN_ocean_rescue_vite_esm_typescript_migration.md`
- 세션 연속성: `docs/agent-context/memory/MEMORY.md`

## 📁 주요 디렉토리

- `/`: 사용자 런타임 HTML/CSS/JS 엔트리
- `shared/`: 과목 공용 코어 로직 (`domain/`, `ui/`)
- `domains/`: 과목별 게임 (`math/`, `english/`, `korean/`, `science/`)과 지원 도메인
- `experiments/`: 실험 모듈 — 현재 신규 개발 동결
- `ocean-rescue/`: Ocean Rescue production standalone artifact
- `docs/`: 현재 authority, 기술 참고, 과거 기록
